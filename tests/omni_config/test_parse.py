import argparse
import sys
from os.path import dirname, join

import pytest
from schema import Optional as SchemaOptional

from prosper_shared.omni_config import (
    ArgParseSource,
    EnvironmentVariableSource,
    FileConfigurationSource,
    JsonConfigurationSource,
    TomlConfigurationSource,
    YamlConfigurationSource,
)
from prosper_shared.omni_config._parse import _extract_defaults_from_schema


class TestParse:
    def test_toml_read(self):
        toml_config_source = TomlConfigurationSource(
            join(dirname(__file__), "data", "test_parse.toml")
        )

        assert {
            "section1": {
                "float_config": 123.456,
                "int_config": 123,
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == toml_config_source.read()

    def test_toml_read_with_config_root(self):
        toml_config_source = TomlConfigurationSource(
            join(dirname(__file__), "data", "test_parse_config.toml"), "tool.lib-name"
        )

        assert {
            "section1": {
                "float_config": 123.456,
                "int_config": 123,
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == toml_config_source.read()

    def test_toml_read_with_config_root_invalid(self):
        toml_config_source = TomlConfigurationSource(
            join(dirname(__file__), "data", "test_parse_config_invalid.toml"),
            "tool.lib-name",
        )

        with pytest.raises(ValueError):
            toml_config_source.read()

    def test_toml_read_not_exists(self):
        toml_config_source = TomlConfigurationSource(
            join(dirname(__file__), "non_existent.toml")
        )

        assert {} == toml_config_source.read()

    def test_json_read(self):
        json_config_source = JsonConfigurationSource(
            join(dirname(__file__), "data", "test_parse.json")
        )

        assert {
            "section1": {
                "float_config": 123.456,
                "int_config": 123,
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == json_config_source.read()

    def test_yaml_read(self):
        yaml_config_source = YamlConfigurationSource(
            join(dirname(__file__), "data", "test_parse.yaml")
        )

        assert {
            "section1": {
                "float_config": 123.456,
                "int_config": 123,
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == yaml_config_source.read()

    def test_abstract_file_read(self):
        yaml_config_source = FileConfigurationSource(
            join(dirname(__file__), "data", "test_parse.yaml")
        )

        assert yaml_config_source.read() is None

    def test_env_read(self, monkeypatch):
        monkeypatch.setenv("TEST_PARSE_SECTION1__FLOAT_CONFIG", "123.456")
        monkeypatch.setenv("TEST_PARSE_SECTION1__INT_CONFIG", "123")
        monkeypatch.setenv("TEST_PARSE_SECTION1__LIST_CONFIG", "asdf,qwer")
        monkeypatch.setenv("TEST_PARSE_SECTION1__STRING_CONFIG", "string value")
        env_config_source = EnvironmentVariableSource("TEST_PARSE")

        assert {
            "section1": {
                "float_config": "123.456",
                "int_config": "123",
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == env_config_source.read()

    def test_argparse_read(self, mocker):
        parser = argparse.ArgumentParser()
        parser.add_argument("--float-config", dest="section1__float_config", type=float)
        parser.add_argument("--int-config", dest="section1__int_config", type=int)
        parser.add_argument(
            "--list-config", dest="section1__list_config", action="append"
        )
        parser.add_argument("--string-config", dest="section1__string_config")
        parser.add_argument(
            "--other-string-config",
            dest="section1__other_string_config",
            default="asdf",
        )

        argparse_config_source = ArgParseSource(parser)

        mocker.patch.object(
            sys,
            "argv",
            [
                "prog",
                "--float-config=123.456",
                "--int-config=123",
                "--list-config=asdf",
                "--list-config=qwer",
                "--string-config",
                "string value",
                "--other-string-config",
                "asdf",
            ],
        )
        assert {
            "section1": {
                "float_config": 123.456,
                "int_config": 123,
                "list_config": ["asdf", "qwer"],
                "string_config": "string value",
            }
        } == argparse_config_source.read()

    @pytest.mark.parametrize(
        ["schema", "expected_defaults"],
        (
            ("x", {}),
            (
                {SchemaOptional("x", default="y"): str},
                {"x": "y"},
            ),
            (
                {SchemaOptional("x"): str},
                {},
            ),
            (
                {SchemaOptional("x", default=False): bool},
                {"x": False},
            ),
            ({"x": {"z": SchemaOptional("z", default="1")}}, {"x": {}}),
            ({"x": {SchemaOptional("z", default=1): int}}, {"x": {"z": 1}}),
        ),
    )
    def test_extract_defaults_from_schema(self, schema, expected_defaults):
        assert _extract_defaults_from_schema(schema) == expected_defaults
