import argparse
import sys
from os.path import dirname, join

import pytest

from prosper_shared.omni_config.parse import (
    ArgParseSource,
    EnvironmentVariableSource,
    TomlConfigurationSource,
)


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
                "float_config": "123.456",
                "int_config": "123",
                "list_config": "['asdf', 'qwer']",
                "string_config": "string value",
            }
        } == argparse_config_source.read()
