from typing import Dict, List

import pytest
from schema import SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config import (
    ConfigKey,
    InputType,
    SchemaType,
    config,
    inputs,
    realize_configs,
    realize_inputs,
)


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
        @config
        def config_method() -> SchemaType:
            return self.TEST_SCHEMA

        assert realize_configs() == [self.TEST_SCHEMA]

    def test_realize_inputs(self):
        @inputs
        def input_method() -> InputType:
            return self.TEST_INPUTS

        assert realize_inputs() == [self.TEST_INPUTS]
