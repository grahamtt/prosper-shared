from copy import deepcopy

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
            (
                {"key1": {"nestedkey1": "nestedvalue1"}},
                {"key1": {"nestedkey2": "nestedvalue2"}},
                {"key1": {"nestedkey1": "nestedvalue1", "nestedkey2": "nestedvalue2"}},
            ),
        ],
    )
    def test_merge_config(self, conf1, conf2, expected_config):
        original_conf1 = deepcopy(conf1)
        original_conf2 = deepcopy(conf2)
        assert merge_config([conf1, conf2]) == expected_config
        assert conf1 == original_conf1
        assert conf2 == original_conf2
