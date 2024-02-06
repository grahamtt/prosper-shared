"""Contains utility methods and classes for defining a config schema."""

import argparse
import logging
from argparse import BooleanOptionalAction, MetavarTypeHelpFormatter
from enum import Enum
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import caseconverter
from schema import And
from schema import Optional as SchemaOptional
from schema import Or, Regex, SchemaError, SchemaWrongKeyError

logger = logging.getLogger(__name__)


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
    used_argument_names = set()
    used_short_argument_names = set()
    arg_parser = argparse.ArgumentParser(
        prog_name, formatter_class=_NullRespectingMetavarTypeHelpFormatter, **kwargs
    )
    _arg_group_from_schema(
        "",
        config_schema,
        arg_parser,
        treat_like_cli_exclusive_input=False,
        used_argument_names=used_argument_names,
        used_short_argument_names=used_short_argument_names,
    )
    _arg_group_from_schema(
        "",
        input_schema,
        arg_parser,
        treat_like_cli_exclusive_input=True,
        used_argument_names=used_argument_names,
        used_short_argument_names=used_short_argument_names,
    )
    return arg_parser


def _key_to_enum_validator(enum):
    def key_to_enum(key):
        try:
            assert enum[key] is not None  # Get the compiler off my back
            return key
        except KeyError:
            raise TypeError(f"Unrecognized key {key} for enum {enum}")

    return key_to_enum


def _key_to_type_validator(in_type):
    def key_to_type(key):
        try:
            module_name, _, class_name = key.rpartition(".")
            getattr(import_module(module_name), class_name)
            return key
        except Exception as e:
            raise TypeError(f"Unrecognized type reference for type {in_type}: {key}", e)

    key_to_type.__name__ = repr(in_type)

    return key_to_type


def _fallback_type_builder(types: List[type]) -> Any:
    def _fallback_type(*args, **kwargs):
        for t in types:
            try:
                return t(*args, **kwargs)
            except (TypeError, ValueError):
                logger.debug(
                    f"Type {type.__name__} does not match positional args {args} and named args {kwargs}"
                )
        raise TypeError("None of the given types match")

    return _fallback_type


class _TypeMatchingOption:
    def __init__(self, in_type):
        self.in_type = in_type

    def __str__(self):
        return f"...any {self.in_type.__name__}"

    def __eq__(self, input_val):
        return isinstance(input_val, str)


def _arg_group_from_schema(
    path: str,
    schema: _SchemaType,
    arg_parser,
    treat_like_cli_exclusive_input: bool,
    used_argument_names: set,
    used_short_argument_names: set,
) -> None:
    arg_group = None
    for k, v in schema.items():
        description = ""
        default = None

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
                used_argument_names,
                used_short_argument_names,
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
            v, options, constraint_desc = _resolve_type_options_and_constraint(v)

            action = "store"
            if v == bool and default is True:
                action = BooleanOptionalAction
            elif v == bool:
                action = "store_true"

            helps = [description, f"Type: {constraint_desc}"]
            if default:
                helps.append(f"Default: {default}")

            kwargs = {
                "dest": f"{path}__{k}" if path else k,
                "help": "; ".join(helps),
                "action": action,
            }
            if v != bool:
                kwargs["type"] = v
                kwargs["metavar"] = k.upper()
            if options != -1:
                kwargs["metavar"] = None
                kwargs["choices"] = options

            if default is None and treat_like_cli_exclusive_input:
                # Produce a required positional argument for required input values that are arg-parse exclusive
                arg_group.add_argument(**kwargs)
            else:
                if k in used_argument_names:
                    k = caseconverter.kebabcase(f"{path}__{k}")
                used_argument_names.add(k)
                if k[0] not in used_short_argument_names:
                    used_short_argument_names.add(k[0])
                    arg_group.add_argument(f"-{k[0]}", f"--{k}", **kwargs)
                else:
                    arg_group.add_argument(f"--{k}", **kwargs)


def _resolve_type_options_and_constraint(
    value,
) -> Tuple[_SchemaType, Union[int, List[Any]], str]:
    options = -1
    if isinstance(value, Regex):
        constraint_desc = f"str matching /{value.pattern_str}/"
        value = str
    elif isinstance(value, (Or, And)):
        zipped_result = zip(
            *list(_resolve_type_options_and_constraint(v) for v in value.args)
        )
        values_list, options_list, constraint_desc_list = zipped_result
        value = _fallback_type_builder(values_list)
        options = []
        for o in options_list:
            if isinstance(o, list):
                options += o
        for v in values_list:
            if v.__name__ != "key_to_enum":
                options.append(_TypeMatchingOption(v))
        constraint_desc = " OR ".join(sorted(list(set(constraint_desc_list))))
    elif callable(value):
        constraint_desc = value.__name__
    else:
        raise ValueError(f"Invalid config value type: {type(value)}")

    if hasattr(value, "__mro__") and Enum in value.__mro__:
        constraint_desc = "str"
        options = list(e.name for e in value)
        value = _key_to_enum_validator(value)

    if repr(value).startswith("typing.Type"):
        constraint_desc = repr(value)  # TODO: constrain parent class
        value = _key_to_type_validator(value)

    return value, options, constraint_desc
