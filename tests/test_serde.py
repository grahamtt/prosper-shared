from typing import NamedTuple

import pytest

from prosper_shared.serde import Serde, _ModelTreeWalker


class Person(NamedTuple):
    age: int
    name: str


class Order(NamedTuple):
    num_items: int
    customer: Person


class TestSerde:
    @pytest.fixture
    def config_mock(self, mocker):
        return mocker.MagicMock()

    @pytest.mark.parametrize(
        ["json_str", "output_class", "expected_result"],
        [
            (
                '{"age":38,"name": "Sean Spencer"}',
                Person,
                Person(38, "Sean Spencer"),
            ),
            (
                '{"num_items":3,"customer":{"age":38,"name": "Sean Spencer"}}',
                Order,
                Order(3, Person(38, "Sean Spencer")),
            ),
            (
                '{"num_items":3,"customer":{"age":38,"name": "Sean Spencer"},"unknown_key":51}',
                Order,
                {
                    "num_items": 3,
                    "customer": Person(38, "Sean Spencer"),
                    "unknown_key": 51,
                },
            ),
        ],
    )
    def test_serde(self, config_mock, json_str, output_class, expected_result):
        assert Serde(config_mock).deserialize(json_str, output_class) == expected_result

    def test_model_tree_walker(self):
        assert list(_ModelTreeWalker(Order)) == [Order, int, Person, str]
