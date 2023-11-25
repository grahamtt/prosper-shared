import pytest

from prosper_shared.omni_config import merge_config


class TestMerge:
    @pytest.mark.parametrize(
        ["conf1", "conf2", "expected_config"],
        [
            ({}, {}, {}),
            ({"key1": "value1"}, {}, {"key1": "value1"}),
            ({"key1": "value1"}, {"key1": "value2"}, {"key1": "value2"}),
            (
                {"key1": "value1"},
                {"key2": "value2"},
                {"key1": "value1", "key2": "value2"},
            ),
            ({"key1": "value1"}, {"key1": None}, {"key1": None}),
        ],
    )
    def test_merge_config(self, conf1, conf2, expected_config):
        assert merge_config([conf1, conf2]) == expected_config
