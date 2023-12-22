from decimal import Decimal
from enum import Enum
from os import getcwd
from os.path import join

import pytest
from platformdirs import user_config_dir
from schema import Optional as SchemaOptional
from schema import Regex, SchemaError

from prosper_shared.omni_config import Config, ConfigKey, get_config_help

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
    }
}


class ContrivedEnum(Enum):
    KEY = "value"


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

    def test_get_as_enum_unhappy(self):
        config = Config(config_dict={"enum_config": "BAD_KEY"})
        with pytest.raises(ValueError):
            config.get_as_enum("enum_config", ContrivedEnum)

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

    def test_autoconfig(self, mocker):
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

        Config.autoconfig(["app_name1", "app_name2"])

        json_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name1"), "config.json"),
                    inject_at="app_name1",
                ),
                mocker.call(
                    join(user_config_dir("app_name2"), "config.json"),
                    inject_at="app_name2",
                ),
                mocker.call(join(getcwd(), ".app_name1.json"), inject_at="app_name1"),
                mocker.call(join(getcwd(), ".app_name2.json"), inject_at="app_name2"),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        yaml_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name1"), "config.yml"),
                    inject_at="app_name1",
                ),
                mocker.call(
                    join(user_config_dir("app_name2"), "config.yml"),
                    inject_at="app_name2",
                ),
                mocker.call(
                    join(user_config_dir("app_name1"), "config.yaml"),
                    inject_at="app_name1",
                ),
                mocker.call(
                    join(user_config_dir("app_name2"), "config.yaml"),
                    inject_at="app_name2",
                ),
                mocker.call(join(getcwd(), ".app_name1.yml"), inject_at="app_name1"),
                mocker.call(join(getcwd(), ".app_name2.yml"), inject_at="app_name2"),
                mocker.call(join(getcwd(), ".app_name1.yaml"), inject_at="app_name1"),
                mocker.call(join(getcwd(), ".app_name2.yaml"), inject_at="app_name2"),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        toml_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name1"), "config.toml"),
                    inject_at="app_name1",
                ),
                mocker.call(
                    join(user_config_dir("app_name2"), "config.toml"),
                    inject_at="app_name2",
                ),
                mocker.call(join(getcwd(), ".app_name1.toml"), inject_at="app_name1"),
                mocker.call(join(getcwd(), ".app_name2.toml"), inject_at="app_name2"),
                mocker.call(
                    join(getcwd(), ".pyproject.toml"),
                    "tools.app_name1",
                    inject_at="app_name1",
                ),
                mocker.call(
                    join(getcwd(), ".pyproject.toml"),
                    "tools.app_name2",
                    inject_at="app_name2",
                ),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        env_config_mock.assert_has_calls(
            [
                mocker.call("APP_NAME1", separator="__"),
                mocker.call("APP_NAME2", separator="__"),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

    def test_autoconfig_single_app(self, mocker):
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

        Config.autoconfig("app_name")

        json_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name"), "config.json"),
                    inject_at="app_name",
                ),
                mocker.call(join(getcwd(), ".app_name.json"), inject_at="app_name"),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        yaml_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name"), "config.yml"),
                    inject_at="app_name",
                ),
                mocker.call(
                    join(user_config_dir("app_name"), "config.yaml"),
                    inject_at="app_name",
                ),
                mocker.call(join(getcwd(), ".app_name.yml"), inject_at="app_name"),
                mocker.call(join(getcwd(), ".app_name.yaml"), inject_at="app_name"),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        toml_config_mock.assert_has_calls(
            [
                mocker.call(
                    join(user_config_dir("app_name"), "config.toml"),
                    inject_at="app_name",
                ),
                mocker.call(join(getcwd(), ".app_name.toml"), inject_at="app_name"),
                mocker.call(
                    join(getcwd(), ".pyproject.toml"),
                    "tools.app_name",
                    inject_at="app_name",
                ),
                mocker.call().read(),
                mocker.call().read(),
                mocker.call().read(),
            ],
            any_order=False,
        )

        env_config_mock.assert_has_calls(
            [
                mocker.call("APP_NAME", separator="__"),
                mocker.call().read(),
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
            "{\n"
            '  "key1": {\n'
            '    "type": "str",\n'
            '    "optional": false,\n'
            '    "description": "key1 desc"\n'
            "  },\n"
            '  "key2": {\n'
            '    "type": "bool",\n'
            '    "optional": true,\n'
            '    "description": "key2 desc"\n'
            "  },\n"
            '  "key3": {\n'
            '    "type": "str",\n'
            '    "optional": false,\n'
            '    "constraint": "regex_value",\n'
            '    "description": "key3 desc"\n'
            "  },\n"
            '  "key4": {\n'
            '    "type": "bool",\n'
            '    "optional": false,\n'
            '    "description": "key4 desc"\n'
            "  },\n"
            '  "group1": {\n'
            '    "gkey1": {\n'
            '      "type": "str",\n'
            '      "optional": false,\n'
            '      "description": "gkey1 desc"\n'
            "    },\n"
            '    "gkey2": {\n'
            '      "type": "bool",\n'
            '      "optional": false,\n'
            '      "default": true,\n'
            '      "description": "gkey3 desc"\n'
            "    }\n"
            "  },\n"
            '  "key6": {\n'
            '    "type": "str",\n'
            '    "optional": false,\n'
            '    "description": "key6 desc"\n'
            "  },\n"
            '  "key7": {\n'
            '    "type": "str",\n'
            '    "optional": false,\n'
            '    "default": "default_value",\n'
            '    "description": "key7 desc"\n'
            "  }\n"
            "}"
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
