import argparse
from typing import Dict, List

import pytest
from schema import Optional, Regex, SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config import (
    ConfigKey,
    InputType,
    SchemaType,
    config_schema,
    input_schema,
    realize_config_schemata,
    realize_input_schemata,
)
from prosper_shared.omni_config._define import _arg_parse_from_schema


class TestDefine:
    @pytest.mark.parametrize(["key"], [("valid_key",)])
    def test_config_key_validate_positive(self, key):
        assert ConfigKey(key).validate(key) == key

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
            ConfigKey(expected_key).validate(given_key)

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

    def test_arg_parse_from_schema(self):
        test_schema = {
            "key1": str,
            Optional("key2"): int,
            ConfigKey("key3", "prefix_"): bool,
            "key4": Regex("regex_value"),
            "group1": {
                "gkey1": str,
                Optional("gkey2"): int,
                ConfigKey("gkey3", "prefix_"): bool,
            },
        }

        actual_arg_parse = _arg_parse_from_schema(test_schema)
        expect_arg_parse = argparse.ArgumentParser()
        expect_arg_parse.add_argument("--key1", dest="key1", help="str")
        expect_arg_parse.add_argument("--key2", dest="key2", help="int")
        expect_arg_parse.add_argument(
            "--key3", dest="key3", help="bool", action="store_true"
        )
        expect_arg_parse.add_argument(
            "--key4", dest="key4", help="String matching regex /regex_value/"
        )
        expected_group = expect_arg_parse.add_argument_group("group1")
        expected_group.add_argument("--gkey1", dest="group1__gkey1", help="str")
        expected_group.add_argument("--gkey2", dest="group1__gkey2", help="int")
        expected_group.add_argument(
            "--gkey3", dest="group1__gkey3", help="bool", action="store_true"
        )

        assert actual_arg_parse.format_help() == expect_arg_parse.format_help()
