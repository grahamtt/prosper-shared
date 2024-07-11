import enum
from decimal import Decimal
from enum import Enum
from os import getcwd
from os.path import join
from typing import List

import pytest
from caseconverter import camelcase, kebabcase, macrocase, snakecase
from platformdirs import user_config_dir
from schema import Optional as SchemaOptional
from schema import Regex, SchemaError

from prosper_shared.omni_config import Config, ConfigKey, config_schema, get_config_help

TEST_CONFIG = {
    "testSection": {
        "testString": "stringValue",
        "testNumber": 123,
        "testBoolTrue": True,
        "testBoolFalse": False,
        "testBoolStringTrue": "Y",
        "testBoolStringFalse": "N",
        "testBoolNumberTrue": 1,
        "testBoolNumberFalse": 0,
        "testBoolOther": {},
        "testDecimalString": "123.456",
        "testDecimalFloat": 123.456,
        "testType": "enum.Enum",
    }
}

TEST_SCHEMA = {
    "testSection": {
        "testString": "stringValue",
        "testNumber": 123,
        "testBoolTrue": True,
        "testBoolFalse": False,
        "testBoolStringTrue": "Y",
        "testBoolStringFalse": "N",
        "testBoolNumberTrue": 1,
        "testBoolNumberFalse": 0,
        "testBoolOther": {},
        "testDecimalString": "123.456",
        "testDecimalFloat": 123.456,
        "testType": "enum.Enum",
    }
}


@config_schema
def register_test_schema():
    return {
        "prosper-shared": {
            "test-schema": {
                ConfigKey(
                    "fly-a-kite",
                    "Enjoyable side-effect.",
                    default=True,
                ): bool,
            }
        }
    }


class ContrivedEnum(Enum):
    KEY = "value"

    def contrived_method(self):
        return self.value


class TestConfig:
    def test_get(self):
        config = Config(config_dict=TEST_CONFIG, schema=TEST_SCHEMA)

        assert config.get("testSection.testString") == "stringValue"
        assert config.get("testSection.testNumber") == 123

    def test_get_as_str(self):
        config = Config(config_dict=TEST_CONFIG, schema=TEST_SCHEMA)

        assert config.get_as_str("testSection.testString") == "stringValue"
        assert (
            config.get_as_str("testSection.testNonexistent", default="stringValue")
            == "stringValue"
        )

    def test_get_as_bool(self):
        config = Config(config_dict=TEST_CONFIG)

        assert config.get_as_bool("testSection.testBoolTrue") is True
        assert config.get_as_bool("testSection.testBoolFalse") is False
        assert config.get_as_bool("testSection.testBoolStringTrue") is True
        assert config.get_as_bool("testSection.testBoolStringFalse") is False
        assert config.get_as_bool("testSection.testBoolNumberTrue") is True
        assert config.get_as_bool("testSection.testBoolNumberFalse") is False
        assert config.get_as_bool("testSection.testBoolOther") is False
        assert config.get_as_bool("testSection.testBoolNotFound") is False
        assert config.get_as_bool("testSection.testBoolNotFound", True) is True

    def test_get_as_decimal(self):
        config = Config(config_dict=TEST_CONFIG)

        assert config.get_as_decimal("testSection.testDecimalString") == Decimal(
            "123.456"
        )
        assert config.get_as_decimal("testSection.testDecimalFloat") == pytest.approx(
            Decimal("123.456")
        )
        assert config.get_as_decimal("testSection.testDecimalNotFound") is None
        assert config.get_as_decimal(
            "testSection.testDecimalNotFound", Decimal("0")
        ) == Decimal("0")

    @pytest.mark.parametrize(
        ["config_value", "given_default", "expected_value"],
        [
            ("KEY", None, ContrivedEnum.KEY),
            ("value", None, ContrivedEnum.KEY),
            (None, ContrivedEnum.KEY, ContrivedEnum.KEY),
        ],
    )
    def test_get_as_enum_happy(self, config_value, given_default, expected_value):
        config = Config(config_dict={"enum_config": config_value})
        actual_value = config.get_as_enum(
            "enum_config", ContrivedEnum, default=given_default
        )
        assert actual_value == expected_value
        assert actual_value.contrived_method() == "value"

    def test_get_as_enum_unhappy(self):
        config = Config(config_dict={"enum_config": "BAD_KEY"})
        with pytest.raises(ValueError):
            config.get_as_enum("enum_config", ContrivedEnum)

    def test_get_as_type(self):
        config = Config(config_dict=TEST_CONFIG)

        assert config.get_as_type("testSection.testType") == enum.Enum
        assert (
            config.get_as_type("testSection.nonexistentTypeKey", enum.Enum) == enum.Enum
        )

    def test_get_invalid_key(self):
        config = Config(config_dict=TEST_CONFIG)

        assert config.get("invalidSection.testString") is None
        assert config.get("testSection.invalidKey") is None

    def test_init_with_config_dict(self):
        config = Config(
            config_dict={"section": {"key1": "value1", "key2": "value2"}},
        )

        assert config.get_as_str("section.key1") == "value1"
        assert config.get_as_str("section.key2") == "value2"

    def test_config_schema_validate_positive(self):
        Config(config_dict=TEST_CONFIG, schema=TEST_SCHEMA)

    def test_config_schema_validate_invalid_key(self):
        with pytest.raises(SchemaError):
            Config(
                config_dict={**TEST_CONFIG, "invalidKey": "value"},
                schema=TEST_SCHEMA,
            )

    def test_config_schema_validate_invalid_value(self):
        with pytest.raises(SchemaError):
            Config(
                config_dict={**TEST_CONFIG, "testString": 123},
                schema=TEST_SCHEMA,
            )

    @pytest.mark.parametrize(
        ["given_app_names", "expected_app_names"],
        [
            ("app-name", ["app-name"]),
        ],
    )
    def test_autoconfig(self, mocker, given_app_names, expected_app_names):
        register_test_schema()
        mocker.patch("sys.exit")
        json_config_mock = mocker.patch(
            "prosper_shared.omni_config.JsonConfigurationSource"
        )
        toml_config_mock = mocker.patch(
            "prosper_shared.omni_config.TomlConfigurationSource"
        )
        yaml_config_mock = mocker.patch(
            "prosper_shared.omni_config.YamlConfigurationSource"
        )
        env_config_mock = mocker.patch(
            "prosper_shared.omni_config.EnvironmentVariableSource"
        )

        Config.autoconfig(given_app_names)

        json_config_mock.assert_has_calls(
            *self._expand_equivalent_files(mocker, expected_app_names, ["json"]),
            any_order=len(expected_app_names)
            != 1,  # TODO: Minor issue with ordering :P
        )

        yaml_config_mock.assert_has_calls(
            *self._expand_equivalent_files(
                mocker,
                expected_app_names,
                [
                    "yml",
                    "yaml",
                ],
            ),
            any_order=True,  # TODO: Minor issue with ordering :P
        )

        toml_config_mock.assert_has_calls(
            *self._expand_equivalent_files(mocker, expected_app_names, ["toml"]),
            any_order=len(expected_app_names)
            != 1,  # TODO: Minor issue with ordering :P
        )

        env_config_mock.assert_has_calls(
            [
                *[
                    mocker.call(macrocase(app_name), separator="__")
                    for app_name in expected_app_names
                ],
                *[mocker.call().read() for _ in expected_app_names],
            ],
            any_order=False,
        )

    @pytest.mark.parametrize(
        ["given_app_names", "expected_app_names"],
        [
            ("app-name", ["app-name"]),
        ],
    )
    def test_autoconfig_dont_search_equivalent_files(
        self, mocker, given_app_names, expected_app_names
    ):
        register_test_schema()
        mocker.patch("sys.exit")
        json_config_mock = mocker.patch(
            "prosper_shared.omni_config.JsonConfigurationSource"
        )
        toml_config_mock = mocker.patch(
            "prosper_shared.omni_config.TomlConfigurationSource"
        )
        yaml_config_mock = mocker.patch(
            "prosper_shared.omni_config.YamlConfigurationSource"
        )
        env_config_mock = mocker.patch(
            "prosper_shared.omni_config.EnvironmentVariableSource"
        )

        Config.autoconfig(given_app_names, search_equivalent_names=False)

        json_config_mock.assert_has_calls(
            *self._expand_files(mocker, expected_app_names, ["json"]),
            any_order=len(expected_app_names)
            != 1,  # TODO: Minor issue with ordering :P
        )

        yaml_config_mock.assert_has_calls(
            *self._expand_files(
                mocker,
                expected_app_names,
                [
                    "yml",
                    "yaml",
                ],
            ),
            any_order=True,  # TODO: Minor issue with ordering :P
        )

        toml_config_mock.assert_has_calls(
            *self._expand_files(mocker, expected_app_names, ["toml"]),
            any_order=len(expected_app_names)
            != 1,  # TODO: Minor issue with ordering :P
        )

        env_config_mock.assert_has_calls(
            [
                *[
                    mocker.call(macrocase(app_name), separator="__")
                    for app_name in expected_app_names
                ],
                *[mocker.call().read() for _ in expected_app_names],
            ],
            any_order=False,
        )

    def test_get_config_help(self, mocker):
        test_config_schema = {
            ConfigKey("key1", description="key1 desc"): str,
            SchemaOptional(ConfigKey("key2", "key2 desc", default=False)): bool,
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
        realize_config_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_config_schemata"
        )
        realize_input_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_input_schemata"
        )
        realize_config_schemata_mock.return_value = [test_config_schema]
        realize_input_schemata_mock.return_value = [test_input_schema]

        assert get_config_help() == (
            ".key1:\n"
            "  description: key1 desc\n"
            "  optional: false\n"
            "  type: str\n"
            ".key2:\n"
            "  description: key2 desc\n"
            "  optional: true\n"
            "  type: bool\n"
            ".key3:\n"
            "  constraint: regex_value\n"
            "  description: key3 desc\n"
            "  optional: false\n"
            "  type: str\n"
            ".key4:\n"
            "  description: key4 desc\n"
            "  optional: false\n"
            "  type: bool\n"
            ".key6:\n"
            "  description: key6 desc\n"
            "  optional: false\n"
            "  type: str\n"
            ".key7:\n"
            "  default: default_value\n"
            "  description: key7 desc\n"
            "  optional: false\n"
            "  type: str\n"
            "group1.gkey1:\n"
            "  description: gkey1 desc\n"
            "  optional: false\n"
            "  type: str\n"
            "group1.gkey2:\n"
            "  default: true\n"
            "  description: gkey3 desc\n"
            "  optional: false\n"
            "  type: bool\n"
        )

    def test_get_config_help_no_description(self, mocker):
        test_config_schema = {
            "key1": str,
        }
        test_input_schema = {}
        realize_config_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_config_schemata"
        )
        realize_input_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_input_schemata"
        )
        realize_config_schemata_mock.return_value = [test_config_schema]
        realize_input_schemata_mock.return_value = [test_input_schema]

        with pytest.raises(ValueError):
            get_config_help()

    def test_get_config_help_bad_value(self, mocker):
        test_config_schema = {
            ConfigKey("key1", description="key1 desc"): "bad_value",
        }
        test_input_schema = {}
        realize_config_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_config_schemata"
        )
        realize_input_schemata_mock = mocker.patch(
            "prosper_shared.omni_config._realize_input_schemata"
        )
        realize_config_schemata_mock.return_value = [test_config_schema]
        realize_input_schemata_mock.return_value = [test_input_schema]

        with pytest.raises(ValueError):
            get_config_help()

    def _expand_equivalent_files(self, mocker, app_names, extensions: List[str]):
        calls = []
        for app_name in app_names:
            app_name = kebabcase(app_name)
            for extension in extensions:
                calls.append(
                    mocker.call(
                        join(
                            user_config_dir(camelcase(app_name)), f"config.{extension}"
                        ),
                    )
                )
                calls.append(
                    mocker.call(
                        join(
                            user_config_dir(snakecase(app_name)), f"config.{extension}"
                        ),
                    )
                )
                calls.append(
                    mocker.call(
                        join(
                            user_config_dir(kebabcase(app_name)), f"config.{extension}"
                        ),
                    )
                )
                calls.append(
                    mocker.call(
                        join(getcwd(), f".{camelcase(app_name)}.{extension}"),
                    )
                )
                calls.append(
                    mocker.call(
                        join(getcwd(), f".{snakecase(app_name)}.{extension}"),
                    )
                )
                calls.append(
                    mocker.call(
                        join(getcwd(), f".{kebabcase(app_name)}.{extension}"),
                    )
                )
                if extension == "toml":
                    calls.append(
                        mocker.call(
                            join(getcwd(), ".pyproject.toml"),
                            f"tools.{camelcase(app_name)}",
                            inject_at=app_name,
                        )
                    )
                    calls.append(
                        mocker.call(
                            join(getcwd(), ".pyproject.toml"),
                            f"tools.{snakecase(app_name)}",
                            inject_at=app_name,
                        )
                    )
                    calls.append(
                        mocker.call(
                            join(getcwd(), ".pyproject.toml"),
                            f"tools.{kebabcase(app_name)}",
                            inject_at=app_name,
                        )
                    )
        calls += [mocker.call().read() for _ in calls]
        return [calls]

    def _expand_files(self, mocker, app_names, extensions: List[str]):
        calls = []
        for app_name in app_names:
            for extension in extensions:
                calls.append(
                    mocker.call(
                        join(user_config_dir(app_name), f"config.{extension}"),
                    )
                )
                calls.append(
                    mocker.call(
                        join(getcwd(), f".{app_name}.{extension}"),
                    )
                )
                if extension == "toml":
                    calls.append(
                        mocker.call(
                            join(getcwd(), ".pyproject.toml"),
                            f"tools.{app_name}",
                            inject_at=kebabcase(app_name),
                        )
                    )
        calls += [mocker.call().read() for _ in calls]
        return [calls]
