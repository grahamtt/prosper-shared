"""Contains utility methods and classes for parsing configs from different sources."""

import argparse
import os
from abc import abstractmethod
from typing import Dict, List, Optional, Union

import dpath
from schema import Optional as SchemaOptional

from prosper_shared.omni_config._define import _ConfigKey, _SchemaType


class _ConfigurationSource:
    """Basic definition of an arbitrary configuration source."""

    @abstractmethod
    def read(self) -> dict:
        """Reads the configuration source by creating keys and values.

        Returns:
            dict: The configuration values.
        """


class _FileConfigurationSource(_ConfigurationSource):
    def __init__(self, config_file_path, config_root=""):
        self._config_file_path = config_file_path
        self._config_root = config_root

    def read(self) -> dict:
        """Reads the given file and extracts the contents into a dict. It returns the subtree rooted at `config_root`.

        Returns:
            dict: The configuration values.

        Raises:
            ValueError: If the config root path references a terminal value instead of a config tree.
        """
        if not os.path.exists(self._config_file_path):
            return {}

        config = self._read_file(self._config_file_path)

        if self._config_root:
            # Find first value matching given root path and replace the config with that value. A little bit hacky,
            # since it relies on `dpath` always returning the root obj before all the children.
            _, v = next(
                dpath.search(
                    config, self._config_root + ".**", separator=".", yielded=True
                )
            )
            config = v

            if not isinstance(config, dict):
                raise ValueError(
                    f"Expected to find `dict` at path {self._config_root}; found {type(config)} instead."
                )

        return config

    @abstractmethod
    def _read_file(self, file_path: str) -> dict:
        """Reads the given file and extracts the contents into a dict.

        Args:
            file_path (str): The path to the config file.

        Returns:
            dict: The configuration values.
        """
        pass


class _TomlConfigurationSource(_FileConfigurationSource):
    """Configuration source that can read TOML files."""

    def _read_file(self, file_path) -> dict:
        import toml  # noqa: autoimport

        with open(self._config_file_path) as config_file:
            return toml.load(config_file)


class _JsonConfigurationSource(_FileConfigurationSource):
    """Configuration source that can read JSON files."""

    def _read_file(self, file_path) -> dict:
        import json  # noqa: autoimport

        with open(self._config_file_path) as config_file:
            return json.load(config_file)


class _YamlConfigurationSource(_FileConfigurationSource):
    """Configuration source that can read YAML files."""

    def _read_file(self, file_path) -> dict:
        import yaml  # noqa: autoimport

        with open(self._config_file_path) as config_file:
            return yaml.safe_load(config_file)


class _ArgParseSource(_ConfigurationSource):
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
            config_namespace[key_components[-1]] = val

        return nested_config


class _EnvironmentVariableSource(_ConfigurationSource):
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
        value_map: Dict[str, str] = _EnvironmentVariableSource.__get_value_map()
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


def _extract_defaults_from_schema(
    schema: _SchemaType, defaults: Optional[dict] = None
) -> dict:
    if defaults is None:
        defaults = {}

    if not hasattr(schema, "items"):
        return defaults

    for k, v in schema.items():
        if isinstance(k, (SchemaOptional, _ConfigKey)):
            defaults[k.schema] = k.default if hasattr(k, "default") else None
            _extract_defaults_from_schema(schema[k], defaults)

    return defaults
