import pytest

from orchestrator_agent.tools.math_tools import add, divide, multiply, subtract


def test_add_operation():
    assert add.invoke({"a": 5, "b": 10}) == 15
    assert add.invoke({"a": -1, "b": 1}) == 0
    assert add.invoke({"a": 2.5, "b": 3.5}) == 6.0


def test_subtract_operation():
    assert subtract.invoke({"a": 10, "b": 4}) == 6
    assert subtract.invoke({"a": 5, "b": 10}) == -5


def test_multiply_operation():
    assert multiply.invoke({"a": 4, "b": 5}) == 20
    assert multiply.invoke({"a": -2, "b": 3}) == -6


def test_divide_operation():
    assert divide.invoke({"a": 10, "b": 2}) == 5.0
    assert divide.invoke({"a": 5, "b": 2}) == 2.5

    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide.invoke({"a": 5, "b": 0})
