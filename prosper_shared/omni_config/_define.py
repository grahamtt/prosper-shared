"""Contains utility methods and classes for defining a config schema."""

import argparse
from argparse import MetavarTypeHelpFormatter
from typing import Callable, Dict, List, Optional, Union

from schema import Optional as SchemaOptional
from schema import Regex, SchemaError, SchemaWrongKeyError


class _ConfigKey:
    """Defines a valid schema config key."""

    def __init__(
        self, expected_val: str, description: str, prefix: Optional[str] = None
    ):
        """Creates a ConfigKey instance.

        Arguments:
            expected_val (str): The expected key for this config entry.
            description (str): The description for this config entry.
            prefix (Optional[str]): Prefix for environment variables rooted at this subtree.
        """
        self._expected_val = expected_val
        self._custom_env_variable_prefix = prefix

    def validate(self, val: str) -> str:
        """Returns the key iff the key is a string value matching the expected value.

        Args:
            val (str): The config key to validate.

        Raises:
            SchemaError: If the expected key is invalid or the given key is not a string.
            SchemaWrongKeyError: If the given key doesn't match the expected key.

        Returns:
            str: The given key if it matches the expected key.
        """
        if not isinstance(self._expected_val, str) or not self._expected_val:
            raise SchemaError(
                f"Expected key '{self._expected_val}' is not a valid config key"
            )

        if not isinstance(val, str):
            raise SchemaError(
                f"Key {val} is not a valid config key; expected `str` type, got {type(val)}"
            )

        if not val or val != self._expected_val:
            raise SchemaWrongKeyError(
                f"Unexpected config key '{val}'; expected '{self._expected_val}'"
            )

        return val

    @property
    def schema(self):
        return self._expected_val


class _ConfigValue:
    """Defines a valid schema config value."""

    def __init__(self, schema: str, description: str):
        """Creates a ConfigKey instance.

        Arguments:
            schema (str): The schema for this entry.
            description (str): The description for this entry.
        """
        self._schema = schema
        self._description = description

    @property
    def schema(self):
        return self._schema

    @property
    def description(self):
        return self._description


_SchemaType = Dict[
    Union[str, _ConfigKey, SchemaOptional],
    Union[str, int, float, dict, list, bool, Regex, "_SchemaType"],
]

_config_registry = []


def _config_schema(
    raw_schema_func: Callable[[], _SchemaType]
) -> Callable[[], _SchemaType]:
    _config_registry.append(raw_schema_func)
    return raw_schema_func


def _realize_config_schemata() -> List[_SchemaType]:
    return [c() for c in _config_registry]


_InputType = Dict[str, str]

_input_registry = []


def _input_schema(
    raw_schema_func: Callable[[], _InputType]
) -> Callable[[], _InputType]:
    _input_registry.append(raw_schema_func)
    return raw_schema_func


def _realize_input_schemata() -> List[_InputType]:
    return [i() for i in _input_registry]


class _NullRespectingMetavarTypeHelpFormatter(MetavarTypeHelpFormatter):
    """Help message formatter which uses the argument 'type' as the default metavar value (instead of the argument 'dest').

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_default_metavar_for_optional(self, action):
        return action.dest if action.dest else action.type.__name__


def _arg_parse_from_schema(
    prog_name: str, schema: _SchemaType
) -> argparse.ArgumentParser:
    """Really simple schema->argparse converter."""
    arg_parser = argparse.ArgumentParser(
        prog_name, formatter_class=_NullRespectingMetavarTypeHelpFormatter
    )
    _arg_group_from_schema("", schema, arg_parser)
    return arg_parser


def _arg_group_from_schema(path: str, schema: _SchemaType, arg_group) -> None:
    for k, v in schema.items():
        if isinstance(k, (SchemaOptional, _ConfigKey)):
            k = k.schema
        if isinstance(v, dict):
            _arg_group_from_schema(
                f"{path}__{k}" if path else k, v, arg_group.add_argument_group(k)
            )
        else:
            if isinstance(v, Regex):
                help_str = f"String matching regex /{v.pattern_str}/"
                v = str
            elif isinstance(v, _ConfigValue):
                help_str = v.description
                v = v.schema
            else:
                help_str = v.__name__
            kwargs = {
                "dest": f"{path}__{k}" if path else k,
                "help": help_str,
                "action": "store_true" if v == bool else "store",
            }
            if v != bool:
                kwargs["type"] = v
            arg_group.add_argument(f"--{k}", **kwargs)
