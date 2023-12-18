import sys
from typing import Dict, List

import pytest
from schema import Optional, Regex, SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config import (
    ConfigKey,
    ConfigValue,
    InputType,
    SchemaType,
    _define,
    config_schema,
    input_schema,
)
from prosper_shared.omni_config._define import (
    _arg_parse_from_schema,
    _realize_config_schemata,
    _realize_input_schemata,
)


class TestDefine:
    @pytest.fixture
    def mock_config_registry(self, mocker):
        return mocker.patch.object(_define, "_config_registry", [])

    @pytest.fixture
    def mock_input_registry(self, mocker):
        return mocker.patch.object(_define, "_input_registry", [])

    @pytest.mark.parametrize(
        ["key", "description"], [("valid_key", "valid description")]
    )
    def test_config_key_validate_positive(self, key, description):
        assert ConfigKey(key, description).validate(key) == key

    @pytest.mark.parametrize(
        ["given_schema", "given_key", "expected_exception"],
        [
            ("valid_key", "invalid_key", SchemaWrongKeyError),
            ("valid_key", 123, SchemaError),
            (1, 1, SchemaError),
            ("", "", SchemaError),
        ],
    )
    def test_config_key_validate_negative(
        self, given_schema, given_key, expected_exception
    ):
        with pytest.raises(expected_exception):
            ConfigKey(given_schema, "description").validate(given_key)

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

    def test_realize_configs(self, mock_config_registry):
        @config_schema
        def config_method() -> SchemaType:
            return self.TEST_SCHEMA

        assert _realize_config_schemata() == [self.TEST_SCHEMA]

    def test_realize_inputs(self, mock_input_registry):
        @input_schema
        def input_method() -> InputType:
            return self.TEST_INPUTS

        assert _realize_input_schemata() == [self.TEST_INPUTS]

    @pytest.mark.skipif(
        sys.version_info < (3, 10), reason="Argparse behavior changes after 3.9"
    )
    def test_arg_parse_from_schema(self):
        test_config_schema = {
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
        test_input_schema = {
            "key6": str,
            Optional("key7", default="default_value"): str,
            ConfigKey("key8", "key8 description"): str,
        }

        actual_arg_parse = _arg_parse_from_schema(
            "pytest", test_config_schema, test_input_schema
        )

        assert actual_arg_parse.format_help() == (
            "usage: pytest [-h] [--key1 key1] [--key2 key2] [--key3] [--key4 key4] "
            "[--key5]\n"
            "              [--gkey1 group1__gkey1] [--gkey2 group1__gkey2] [--gkey3]\n"
            "              [--key7 key7]\n"
            "              str str\n"
            "\n"
            "positional arguments:\n"
            "  str                   str\n"
            "  str                   str\n"
            "\n"
            "options:\n"
            "  -h, --help            show this help message and exit\n"
            "  --key1 key1           str\n"
            "  --key2 key2           int\n"
            "  --key3                bool\n"
            "  --key4 key4           String matching regex /regex_value/\n"
            "  --key5                Good value\n"
            "  --key7 key7           str\n"
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
            _arg_parse_from_schema("pytest", test_schema, {})
