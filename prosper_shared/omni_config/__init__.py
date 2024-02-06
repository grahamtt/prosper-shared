"""Utility for declaring, parsing, merging, and validating configs."""

import argparse
from copy import deepcopy
from decimal import Decimal
from enum import Enum
from importlib import import_module
from importlib.util import find_spec
from numbers import Number
from os import getcwd
from os.path import join
from typing import List, Optional, Type, TypeVar, Union

import dpath
from caseconverter import camelcase, kebabcase, macrocase, snakecase
from platformdirs import user_config_dir
from schema import Optional as SchemaOptional
from schema import Regex, Schema

from prosper_shared.omni_config._define import (
    _arg_parse_from_schema as arg_parse_from_schema,
)
from prosper_shared.omni_config._define import _config_schema as config_schema
from prosper_shared.omni_config._define import _ConfigKey as ConfigKey
from prosper_shared.omni_config._define import _input_schema as input_schema
from prosper_shared.omni_config._define import _InputType as InputType
from prosper_shared.omni_config._define import (
    _realize_config_schemata,
    _realize_input_schemata,
)
from prosper_shared.omni_config._define import _SchemaType as SchemaType
from prosper_shared.omni_config._merge import _merge_config as merge_config
from prosper_shared.omni_config._parse import _ArgParseSource as ArgParseSource
from prosper_shared.omni_config._parse import (
    _ConfigurationSource as ConfigurationSource,
)
from prosper_shared.omni_config._parse import (
    _EnvironmentVariableSource as EnvironmentVariableSource,
)
from prosper_shared.omni_config._parse import _extract_defaults_from_schema
from prosper_shared.omni_config._parse import (
    _FileConfigurationSource as FileConfigurationSource,
)
from prosper_shared.omni_config._parse import (
    _JsonConfigurationSource as JsonConfigurationSource,
)
from prosper_shared.omni_config._parse import (
    _TomlConfigurationSource as TomlConfigurationSource,
)
from prosper_shared.omni_config._parse import (
    _YamlConfigurationSource as YamlConfigurationSource,
)

__all__ = [
    "Config",
    "config_schema",
    "ConfigKey",
    "input_schema",
    "InputType",
    "merge_config",
    "ArgParseSource",
    "ConfigurationSource",
    "EnvironmentVariableSource",
    "FileConfigurationSource",
    "JsonConfigurationSource",
    "TomlConfigurationSource",
    "YamlConfigurationSource",
    "get_config_help",
]

_T = TypeVar("_T", Enum, object)


class Config:
    """Holds and allows access to prosper-api config values."""

    def __init__(
        self,
        config_dict: dict = None,
        schema: SchemaType = None,
    ):
        """Builds a config class instance.

        Args:
            config_dict (dict): A Python dict representing the config.
            schema (SchemaType): Validate the config against this schema. Unexpected or missing values will cause a validation error.
        """
        self._config_dict = deepcopy(config_dict)

        if schema:
            self._config_dict = Schema(schema, ignore_extra_keys=False).validate(
                self._config_dict
            )

    def get(self, key: str) -> object:
        """Get the specified config value.

        Args:
            key (str): The '.' separated path to the config value.

        Returns:
            object: The stored config value for the given key, or None if it doesn't
                exist.
        """
        return dpath.get(self._config_dict, key, separator=".", default=None)

    def get_as_str(self, key, default: Union[str, None] = None):
        """Get the specified value interpreted as a string."""
        value = self.get(key)
        if value is None:
            return default

        return str(value)

    def get_as_decimal(self, key, default: Union[Decimal, None] = None):
        """Get the specified value interpreted as a decimal."""
        value = self.get(key)
        if value is None:
            return default

        return Decimal(value)

    def get_as_bool(self, key: str, default: bool = False):
        """Get the specified value interpreted as a boolean.

        Specifically, the literal value `true`, string values 'true', 't', 'yes', and 'y' (case-insensitive), and any
        numeric value != 0 will return True, otherwise, False is returned.
        """
        value = self.get(key)
        if value is None:
            return default

        truthy_strings = {"true", "t", "yes", "y"}
        if isinstance(value, str) and value.lower() in truthy_strings:
            return True

        if isinstance(value, Number) and value != 0:
            return True

        return False

    def get_as_enum(
        self, key: str, enum_type: Type[_T], default: Optional[_T] = None
    ) -> Optional[_T]:
        """Gets a config value by enum name or value.

        Args:
            key (str): The named config to get.
            enum_type (Type[_T]): Interpret the resulting value as an enum of this type.
            default (Optional[_T]): The value to return if the config key doesn't exist.

        Returns:
            Optional[_T]: The config value interpreted as the given enum type or the default value.
        """
        value = self.get(key)
        if value is None:
            return default

        if value in enum_type.__members__.keys():
            return enum_type[value]

        return enum_type(value)

    def get_as_type(self, key: str, default: Optional[Type[_T]] = None) -> Optional[_T]:
        """Gets a config value by enum name or value.

        Args:
            key (str): The named config to get.
            default (Optional[Type[_T]]): The value to return if the config key doesn't exist.

        Returns:
            Optional[_T]: The config value interpreted as a type.
        """
        value = self.get(key)
        if value is None:
            return default

        module_name, _, class_name = value.rpartition(".")
        return getattr(import_module(module_name), class_name)

    @classmethod
    def autoconfig(
        cls,
        app_names: Union[None, str, List[str]] = None,
        arg_parse: argparse.ArgumentParser = None,
        validate: bool = False,
        search_equivalent_names: bool = True,
    ) -> "Config":
        """Sets up a Config with default configuration sources.

        Gets config files from the following locations:
        1. The default config directory for the given app name.
        2. The working directory, including searching `pyproject.toml` for a `tools.{app_name}` section, if present.
        3. Environment variables prefixed by 'APP_NAME_' for each of the given app names.
        4. The given argparse instance.

        If `search_equivalent_names` is set, search for config locations with equivalent names in different casing
        styles, e.g. 'config-name` -> `configName` and `config_name`.

        Config values found lower in the chain will override previous values for the same key.

        Args:
            app_names (Union[None, str, List[str]]): An ordered list of app names for which look for configs.
            arg_parse (argparse.ArgumentParser): A pre-configured argparse instance.
            validate (bool): Whether to validate the config prior to returning it.
            search_equivalent_names (bool): Whether equivalent names to the given app names should be included in the
                config location search.

        Returns:
            Config: A configured Config instance.
        """
        config_schemata = merge_config(_realize_config_schemata())
        input_schemata = merge_config(_realize_input_schemata())
        schema = merge_config([config_schemata, input_schemata])

        if app_names is None:
            app_names = [k for k in config_schemata]
        elif isinstance(app_names, str):
            app_names = [app_names]

        if search_equivalent_names:
            file_app_name_dedup = {}
            for app_name in app_names:
                file_app_name_dedup[camelcase(app_name)] = None
                file_app_name_dedup[snakecase(app_name)] = None
                file_app_name_dedup[kebabcase(app_name)] = None
            file_app_names = list(file_app_name_dedup.keys())
        else:
            file_app_names = app_names

        conf_sources: List[ConfigurationSource] = [
            _extract_defaults_from_schema(schema)
        ]

        conf_sources += [
            JsonConfigurationSource(
                join(user_config_dir(app_name), "config.json"),
                inject_at=kebabcase(app_name),
            )
            for app_name in file_app_names
        ]
        if _has_yaml():
            conf_sources += [
                YamlConfigurationSource(
                    join(user_config_dir(app_name), "config.yml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]
            conf_sources += [
                YamlConfigurationSource(
                    join(user_config_dir(app_name), "config.yaml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]

        if _has_toml():
            conf_sources += [
                TomlConfigurationSource(
                    join(user_config_dir(app_name), "config.toml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]

        conf_sources += [
            JsonConfigurationSource(
                join(getcwd(), f".{app_name}.json"),
                inject_at=kebabcase(app_name),
            )
            for app_name in file_app_names
        ]

        if _has_yaml():
            conf_sources += [
                YamlConfigurationSource(
                    join(getcwd(), f".{app_name}.yml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]
            conf_sources += [
                YamlConfigurationSource(
                    join(getcwd(), f".{app_name}.yaml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]

        if _has_toml():
            conf_sources += [
                TomlConfigurationSource(
                    join(getcwd(), f".{app_name}.toml"),
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]
            conf_sources += [
                TomlConfigurationSource(
                    join(getcwd(), ".pyproject.toml"),
                    f"tools.{app_name}",
                    inject_at=kebabcase(app_name),
                )
                for app_name in file_app_names
            ]

        conf_sources += [
            EnvironmentVariableSource(macrocase(app_name), separator="__")
            for app_name in app_names
        ]
        conf_sources.append(
            ArgParseSource(
                arg_parse
                if arg_parse
                else arg_parse_from_schema(
                    config_schemata,
                    input_schemata,
                )
            )
        )

        config_dict = merge_config(
            [(c.read() if not isinstance(c, dict) else c) for c in conf_sources]
        )

        config_dict = (
            Schema(schema, ignore_extra_keys=True).validate(config_dict)
            if validate
            else config_dict
        )

        return Config(config_dict=config_dict)


def _has_yaml():
    """Tests whether the 'yaml' package is available."""
    return find_spec("yaml")


def _has_toml():
    """Tests whether the 'toml' package is available."""
    return find_spec("toml")


def get_config_help():
    """Returns a JSON string representing the config values available.

    Returns
        str: JSON string representing the available config values.
    """
    import yaml  # noqa: autoimport

    config_schemata = merge_config(_realize_config_schemata())
    input_schemata = merge_config(_realize_input_schemata())
    schema = merge_config([config_schemata, input_schemata])
    help_struct = _build_help_struct(schema)

    return yaml.dump(help_struct, width=94)


def _build_help_struct(
    schema: SchemaType, path: Optional[str] = None, help_struct=None
):
    if help_struct is None:
        help_struct = {}
    if path is None:
        path = ""
    for k, v in schema.items():
        is_optional = False
        description = None
        constraint = None
        default = None
        while isinstance(k, (ConfigKey, SchemaOptional)):
            if isinstance(k, SchemaOptional):
                is_optional = True
            description = k.description if hasattr(k, "description") else description
            default = k.default if hasattr(k, "default") else default
            k = k.schema

        if isinstance(v, dict):
            _build_help_struct(v, f"{path}.{k}" if path else k, help_struct)
        else:
            if not description:
                raise ValueError(f"No description provided for leaf config key {k}")
            if isinstance(v, Regex):
                type_name = "str"
                constraint = v.pattern_str
            elif callable(v):
                type_name = v.__name__
            else:
                raise ValueError(f"Invalid config value type: {type(v)}")
            key = f"{path}.{k}"
            help_struct[key] = {"type": type_name, "optional": is_optional}
            if default:
                help_struct[key]["default"] = default
            if constraint:
                help_struct[key]["constraint"] = constraint
            if description:
                help_struct[key]["description"] = description

    return help_struct
