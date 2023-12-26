"""Contains utility methods and classes for defining a config schema."""

import argparse
from argparse import BooleanOptionalAction, MetavarTypeHelpFormatter
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from schema import Optional as SchemaOptional
from schema import Regex, SchemaError, SchemaWrongKeyError


class _ConfigKey:
    """Defines a valid schema config key."""

    def __init__(
        self, expected_val: str, description: str, default: Optional[Any] = None
    ):
        """Creates a ConfigKey instance.

        Arguments:
            expected_val (str): The expected key for this config entry.
            description (str): The description for this config entry.
            default (Optional[Any]): Return this value if the key isn't present in the realized config.
        """
        self._expected_val = expected_val
        self._description = description
        self._default = default

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

    def __repr__(self):
        return f"ConfigKey(expected_val={self._expected_val},description={self._description},default={self._default})"

    def __str__(self):
        return self.__repr__()

    @property
    def schema(self):
        return self._expected_val

    @property
    def default(self):
        return self._default

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


_InputType = Dict[
    Union[str, _ConfigKey, SchemaOptional],
    Union[str, int, float, dict, list, bool, Regex, "_SchemaType"],
]

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

    def _get_default_metavar_for_positional(self, action):
        return action.dest if action.dest else action.type.__name__


def _arg_parse_from_schema(
    config_schema: _SchemaType,
    input_schema: _SchemaType,
    prog_name: Optional[str] = None,
    **kwargs,
) -> argparse.ArgumentParser:
    """Really simple schema->argparse converter."""
    arg_parser = argparse.ArgumentParser(
        prog_name, formatter_class=_NullRespectingMetavarTypeHelpFormatter, **kwargs
    )
    _arg_group_from_schema(
        "", config_schema, arg_parser, treat_like_cli_exclusive_input=False
    )
    _arg_group_from_schema(
        "", input_schema, arg_parser, treat_like_cli_exclusive_input=True
    )
    return arg_parser


def _key_to_enum_converter(enum):
    def key_to_enum(key):
        try:
            return enum[key]
        except KeyError:
            raise TypeError(f"Unrecognized key {key} for enum {enum}")

    return key_to_enum


def _arg_group_from_schema(
    path: str,
    schema: _SchemaType,
    arg_parser,
    treat_like_cli_exclusive_input: bool,
) -> None:
    arg_group = None
    for k, v in schema.items():
        description = ""
        default = None
        options = None

        while isinstance(k, (_ConfigKey, SchemaOptional)):
            description = (
                k.description
                if hasattr(k, "description") and k.description
                else description
            )
            default = k.default if hasattr(k, "default") else default
            k = k.schema
        if isinstance(v, dict):
            _arg_group_from_schema(
                f"{path}__{k}" if path else k,
                v,
                arg_parser,
                treat_like_cli_exclusive_input,
            )
        else:
            if not arg_group and path:
                arg_group = arg_parser.add_argument_group(path.replace("__", "."))
            elif not arg_group:
                arg_group = arg_parser
            if not description:
                raise ValueError(
                    f"No description provided for leaf config key {path}.{k}"
                )
            if isinstance(v, Regex):
                constraint_desc = f"Type: str matching /{v.pattern_str}/"
                v = str
            elif callable(v):
                constraint_desc = f"Type: {v.__name__}"
            else:
                raise ValueError(f"Invalid config value type: {type(v)}")

            if Enum in v.__mro__:
                constraint_desc = "Type: str"
                options = list(e for e in v)
                v = _key_to_enum_converter(v)

            helps = [description, constraint_desc]
            if default:
                helps.append(f"Default: {default}")

            action = "store"
            if v == bool and default is True:
                action = BooleanOptionalAction
            elif v == bool:
                action = "store_true"

            kwargs = {
                "dest": f"{path}__{k}" if path else k,
                "help": "; ".join(helps),
                "action": action,
            }
            if v != bool:
                kwargs["type"] = v
                kwargs["metavar"] = k.upper()
            if options:
                kwargs["metavar"] = None
                kwargs["choices"] = options

            if default is None and treat_like_cli_exclusive_input:
                # Produce a required positional argument for required input values that are arg-parse exclusive
                arg_group.add_argument(**kwargs)
            else:
                arg_group.add_argument(f"--{k}", **kwargs)
