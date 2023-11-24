"""Contains utility methods and classes for parsing configs from different sources."""

import argparse
import os
from abc import abstractmethod
from typing import Dict, List, Union

import dpath
import toml


class ConfigurationSource:
    """Basic definition of an arbitrary configuration source."""

    @abstractmethod
    def read(self) -> dict:
        """Reads the configuration source by creating keys and values.

        Returns:
            dict: The configuration values.
        """


class TomlConfigurationSource(ConfigurationSource):
    """Configuration source that can read TOML files."""

    def __init__(self, config_file_path, config_root_path=""):
        """Creates a new TomlConfigurationSource instance."""
        self._config_file_path = config_file_path
        self._config_root_path = config_root_path

    def read(self) -> dict:
        """Reads the given TOML file and extracts the contents into a dict.

        Returns:
            dict: The configuration values.

        Raises:
            ValueError: If the config root path references a terminal value instead of a config tree.
        """
        if not os.path.exists(self._config_file_path):
            return {}

        with open(self._config_file_path) as config_file:
            config = toml.load(config_file)

        if self._config_root_path:
            # Find first value matching given root path and replace the config with that value. A little bit hacky,
            # since it relies on `dpath` always returning the root obj before all the children.
            _, v = next(
                dpath.search(
                    config, self._config_root_path + ".**", separator=".", yielded=True
                )
            )
            config = v

            if not isinstance(config, dict):
                raise ValueError(
                    f"Expected to find `dict` at path {self._config_root_path}; found {type(config)} instead."
                )

        return config


class ArgParseSource(ConfigurationSource):
    """ArgParse source that merges the values with the other config."""

    def __init__(self, argument_parser: argparse.ArgumentParser):
        """Creates a new ArgParseSource instance.

        Arguments:
            argument_parser (argparse.ArgumentParser): Configure argument parser to pull configs out of.
        """
        self._argument_parser = argument_parser

    def read(self) -> dict:
        """Reads the arguments and produces a nested dict.

        Returns:
            dict: The args parsed into a nested dict.
        """
        raw_namespace = self._argument_parser.parse_args()
        nested_config = {}

        for key, val in raw_namespace.__dict__.items():
            # TODO: This can cause weird behavior if a key is explicitly set to the default value
            if val is None or any(
                a
                for a in self._argument_parser._actions
                if key == a.dest and val == a.default
            ):
                continue
            key_components = key.split("__")
            config_namespace = nested_config
            for key_component in key_components[:-1]:
                if key_component not in config_namespace:
                    config_namespace[key_component] = {}
                config_namespace = config_namespace[key_component]
            config_namespace[key_components[-1]] = str(val)

        return nested_config


class EnvironmentVariableSource(ConfigurationSource):
    """A configuration source for environment variables."""

    def __init__(
        self, prefix: str, separator: str = "__", list_separator: str = ","
    ) -> None:
        """Creates a new instance of the EnvironmentVariableSource.

        Args:
            prefix (str): The unique prefix for the environment variables.
            separator (str, optional): The value separator. Defaults to "_".
            list_separator (str, optional): If a value can be interpreted as a
                list, this will be used as separator.. Defaults to ",".
        """
        self.__prefix = prefix or ""
        self.__separator = separator
        self.__list_item_separator = list_separator
        super().__init__()

    def read(self) -> dict:
        """Reads the environment variables and produces a nested dict.

        Returns:
            dict: The mapped environment variables.
        """
        result = dict()
        value_map: Dict[str, str] = EnvironmentVariableSource.__get_value_map()
        matching_variables: List[str] = [
            key for (key, _) in value_map.items() if key.startswith(self.__prefix)
        ]
        for key in matching_variables:
            value = value_map[key]
            sanitized: List[str] = self.__sanitize_key(key)
            items: dict = result
            for key_part in sanitized[:-1]:
                key_part_lower = key_part.lower()
                if key_part_lower not in items.keys():
                    items[key_part_lower] = dict()
                items = items[key_part_lower]

            last_key: str = sanitized[-1]

            # TODO: parse into expected type
            items[last_key.lower()] = self.__sanitize_value(value)

        return result

    @staticmethod
    def __get_value_map() -> Dict[str, str]:
        return os.environ.copy()

    def __sanitize_key(self, key: str) -> List[str]:
        return key[len(self.__prefix) + 1 :].split(self.__separator)

    def __sanitize_value(self, value: str) -> Union[str, List[str]]:
        if self.__list_item_separator in value:
            return value.split(self.__list_item_separator)

        return value
