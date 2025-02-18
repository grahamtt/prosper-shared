import sys
from argparse import Namespace
from enum import Enum
from typing import Dict, List, Type

import pytest
from schema import Or, Regex, SchemaError, SchemaWrongKeyError

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
    _fallback_type_builder,
    _realize_config_schemata,
    _realize_input_schemata,
)

PROG_NAME = "test-cli"


class MyEnum(Enum):
    KEY1 = "VALUE1"
    KEY2 = "VALUE2"

    def __str__(self):
        return self.name


class TestType:
    pass


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

    def test_fallback_type_builder_not_found(self):
        with pytest.raises(TypeError):
            _fallback_type_builder([int])("asdf")

    @pytest.mark.xfail(
        sys.version_info < (3, 10) or sys.version_info > (3, 12),
        reason="Argparse behavior changes after 3.9 and after 3.13",
    )
    def test_arg_parse_from_schema(self, mocker, snapshot):
        mocker.patch.object(
            sys,
            "argv",
            [
                PROG_NAME,
                "0123456789abcdef0123456789abcdef",
                "--key5=KEY1",
                "--no-gkey2",
                "--group3-gkey5=asdf",
                "--key6=asdf",
                "--key7=enum.Enum",
            ],
        )
        mocker.patch(
            "prosper_shared.omni_config._define.user_config_dir",
            lambda i: f"/config_dir/dir/{i}",
        )
        mocker.patch("prosper_shared.omni_config._define.getcwd", lambda: "/cwd/dir")

        test_config_schema = {
            ConfigKey("key1", description="key1 desc."): str,
            ConfigKey("key2", "key2 desc"): bool,
            ConfigKey("key3", "key3 desc"): Regex("regex_value"),
            ConfigKey("key4", "key4 desc", False): bool,
            ConfigKey("key5", "key5 desc", default=MyEnum.KEY2): MyEnum,
            ConfigKey("key6", "key6 desc.", default=MyEnum.KEY2): Or(
                MyEnum, Type[TestType], str
            ),
            ConfigKey("key7", "key7 desc"): Type[TestType],
            "group1": {
                ConfigKey("gkey1", description="gkey1 desc"): str,
                ConfigKey("gkey2", "gkey2 desc", True): bool,
                "group2": {
                    ConfigKey("gkey3", "gkey3 desc"): bool,
                    ConfigKey("gkey4", "gkey4 desc.", default="NOOOO"): str,
                },
            },
            "group3": {
                "group4": {ConfigKey("gkey5", "gkey5 desc"): int},
                ConfigKey(
                    "gkey5",
                    description="repeated leaf config name in a different context",
                ): str,
            },
        }
        test_input_schema = {
            ConfigKey("inkey1", "inkey1 desc"): str,
            ConfigKey("inkey2", "inkey2 desc", default="default_value"): str,
        }

        actual_arg_parse = _arg_parse_from_schema(
            test_config_schema, test_input_schema, PROG_NAME
        )

        assert actual_arg_parse.format_help() == snapshot
        assert actual_arg_parse.parse_args() == Namespace(
            key1=None,
            key2=False,
            key3=None,
            key4=False,
            key5="KEY1",
            key6="asdf",
            key7="enum.Enum",
            group1__gkey1=None,
            group1__gkey2=False,
            group1__group2__gkey3=False,
            group1__group2__gkey4=None,
            group3__group4__gkey5=None,
            group3__gkey5="asdf",
            inkey1="0123456789abcdef0123456789abcdef",
            inkey2=None,
        )

    @pytest.mark.xfail(
        sys.version_info < (3, 10), reason="Argparse behavior changes after 3.9"
    )
    def test_arg_parse_from_schema_when_bad_cli_value(self, mocker):
        mocker.patch.object(
            sys,
            "argv",
            ["test-cli", "--key5=KEY3"],
        )

        test_config_schema = {
            ConfigKey("key5", "key5 desc", default=MyEnum.KEY2): MyEnum,
        }
        test_input_schema = {}

        with pytest.raises(SystemExit):
            actual_arg_parse = _arg_parse_from_schema(
                test_config_schema, test_input_schema, "test-prog"
            )
            actual_arg_parse.parse_args()

    def test_arg_parse_from_schema_if_missing_description(self):
        test_schema = {
            "key1": str,
        }

        with pytest.raises(ValueError):
            _arg_parse_from_schema(test_schema, {}, PROG_NAME)

    def test_arg_parse_from_schema_if_type_not_callable(self):
        test_schema = {
            ConfigKey("key1", "key1 desc"): "value",
        }

        with pytest.raises(ValueError):
            _arg_parse_from_schema(test_schema, {}, PROG_NAME)

    def test_config_key_str(self):
        assert (
            str(ConfigKey("key", "value", "default"))
            == "ConfigKey(expected_val=key,description=value,default=default)"
        )
