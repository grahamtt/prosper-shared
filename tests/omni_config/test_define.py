import sys
from typing import Dict, List

import pytest
from schema import Regex, SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config import (
    ConfigKey,
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
            ConfigKey("key1", description="key1 desc"): str,
            ConfigKey("key2", "key2 desc"): bool,
            ConfigKey("key3", "key3 desc"): Regex("regex_value"),
            ConfigKey("key4", "key4 desc", False): bool,
            "group1": {
                ConfigKey("gkey1", description="gkey1 desc"): str,
                ConfigKey("gkey2", "gkey3 desc", True): bool,
            },
        }
        test_input_schema = {
            ConfigKey("key6", "key6 desc"): str,
            ConfigKey("key7", "key7 desc", default="default_value"): str,
        }

        actual_arg_parse = _arg_parse_from_schema(
            "pytest", test_config_schema, test_input_schema
        )

        assert actual_arg_parse.format_help() == (
            "usage: pytest [-h] [--key1 KEY1] [--key2] [--key3 KEY3] [--key4]\n"
            "              [--gkey1 GKEY1] [--gkey2] [--key7 KEY7]\n"
            "              KEY6\n"
            "\n"
            "positional arguments:\n"
            "  KEY6           key6 desc; Type: str\n"
            "\n"
            "options:\n"
            "  -h, --help     show this help message and exit\n"
            "  --key1 KEY1    key1 desc; Type: str\n"
            "  --key2         key2 desc; Type: bool\n"
            "  --key3 KEY3    key3 desc; Type: str matching /regex_value/\n"
            "  --key4         key4 desc; Type: bool; Default: False\n"
            "  --key7 KEY7    key7 desc; Type: str; Default: default_value\n"
            "\n"
            "group1:\n"
            "\n"
            "  --gkey1 GKEY1  gkey1 desc; Type: str\n"
            "  --gkey2        gkey3 desc; Type: bool; Default: True\n"
        )

    def test_arg_parse_from_schema_if_missing_description(self):
        test_schema = {
            "key1": str,
        }

        with pytest.raises(ValueError):
            _arg_parse_from_schema("pytest", test_schema, {})

    def test_arg_parse_from_schema_if_type_not_callable(self):
        test_schema = {
            ConfigKey("key1", "key1 desc"): "value",
        }

        with pytest.raises(ValueError):
            _arg_parse_from_schema("pytest", test_schema, {})
