import pytest
from schema import SchemaError, SchemaWrongKeyError

from prosper_shared.omni_config.define import ConfigKey


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
