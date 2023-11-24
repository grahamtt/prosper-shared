"""Contains utility methods and classes for defining a config schema."""

from typing import Optional

from schema import SchemaError, SchemaWrongKeyError


class ConfigKey:
    """Defines a valid schema config key."""

    def __init__(self, expected_val: str, custom_env_var_prefix: Optional[str] = None):
        """Creates a ConfigKey instance.

        Arguments:
            expected_val (str): The expected key for this config entry.
            custom_env_var_prefix (Optional[str]): Prefix for environment variables rooted at this subtree.
        """
        self._expected_val = expected_val
        self._custom_env_variable_prefix = custom_env_var_prefix

    def validate(self, val: str) -> str:
        """Returns the key iff the key is a string value matching the expected value.

        Args:
            val (str): The config key to validate.

        Raises:
            SchemaError: If the expected key is invalid or the given key is not a string.
            SchemaWrongKeyError: If the given key doesn't match the expected key.

        Returns:
            str: The given key if it matches the expected key.
        """
        if not isinstance(self._expected_val, str) or not self._expected_val:
            raise SchemaError(
                f"Expected key '{self._expected_val}' is not a valid config key"
            )

        if not isinstance(val, str):
            raise SchemaError(
                f"Key {val} is not a valid config key; expected `str` type, got {type(val)}"
            )

        if not val or val != self._expected_val:
            raise SchemaWrongKeyError(
                f"Unexpected config key '{val}'; expected '{self._expected_val}'"
            )

        return val
