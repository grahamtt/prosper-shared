import sys
from typing import Dict, List

import pytest
from schema import Optional, Regex, SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config import (
    ConfigKey,
    ConfigValue,
    InputType,
    SchemaType,
    config_schema,
    input_schema,
    realize_config_schemata,
    realize_input_schemata,
)
from prosper_shared.omni_config._define import _arg_parse_from_schema


class TestDefine:
    @pytest.mark.parametrize(
        ["key", "description"], [("valid_key", "valid description")]
    )
    def test_config_key_validate_positive(self, key, description):
        assert ConfigKey(key, description).validate(key) == key

    @pytest.mark.parametrize(
        ["expected_key", "given_key", "exception_type"],
        [
            ("valid_key", "invalid_key", SchemaWrongKeyError),
            ("valid_key", 123, SchemaError),
            ("", "", SchemaError),
        ],
    )
    def test_config_key_validate_negative(
        self, expected_key, given_key, exception_type
    ):
        with pytest.raises(exception_type):
            ConfigKey(expected_key, "description").validate(given_key)

    TEST_SCHEMA = {
        ConfigKey("section1", "prefix"): {
            "int_val": int,
            "str_val": str,
            "list_val": List[str],
            "bool_val": bool,
            "dict_val": Dict[str, SchemaType],
            "any_val": SchemaType,
        },
        "section2": {
            "int_val2": int,
            "str_val2": str,
            "list_val2": List[str],
            "bool_val2": bool,
            "dict_val2": Dict[str, SchemaType],
            "any_val2": SchemaType,
        },
        "top_level_key": bool,
    }

    TEST_INPUTS = {
        "input1": str,
        "input2": int,
        "input3": bool,
        "input4": List[str],
    }

    def test_realize_configs(self):
        @config_schema
        def config_method() -> SchemaType:
            return self.TEST_SCHEMA

        assert realize_config_schemata() == [self.TEST_SCHEMA]

    def test_realize_inputs(self):
        @input_schema
        def input_method() -> InputType:
            return self.TEST_INPUTS

        assert realize_input_schemata() == [self.TEST_INPUTS]

    @pytest.mark.skipif(
        sys.version_info < (3, 10), reason="Argparse behavior changes after 3.9"
    )
    def test_arg_parse_from_schema(self):
        test_schema = {
            "key1": str,
            Optional("key2"): int,
            ConfigKey("key3", "prefix_"): bool,
            "key4": Regex("regex_value"),
            ConfigKey("key5", description="Good stuff"): ConfigValue(
                bool, "Good value"
            ),
            "group1": {
                "gkey1": str,
                Optional("gkey2"): int,
                ConfigKey("gkey3", "prefix_"): bool,
            },
        }

        actual_arg_parse = _arg_parse_from_schema("pytest", test_schema)

        assert actual_arg_parse.format_help() == (
            "usage: pytest [-h] [--key1 key1] [--key2 key2] [--key3] [--key4 key4] "
            "[--key5]\n"
            "              [--gkey1 group1__gkey1] [--gkey2 group1__gkey2] [--gkey3]\n"
            "\n"
            "options:\n"
            "  -h, --help            show this help message and exit\n"
            "  --key1 key1           str\n"
            "  --key2 key2           int\n"
            "  --key3                bool\n"
            "  --key4 key4           String matching regex /regex_value/\n"
            "  --key5                Good value\n"
            "\n"
            "group1:\n"
            "  --gkey1 group1__gkey1\n"
            "                        str\n"
            "  --gkey2 group1__gkey2\n"
            "                        int\n"
            "  --gkey3               bool\n"
        )

    def test_arg_parse_from_schema_if_type_not_callable(self):
        test_schema = {
            "key1": "value",
        }

        with pytest.raises(ValueError):
            _arg_parse_from_schema("pytest", test_schema)
