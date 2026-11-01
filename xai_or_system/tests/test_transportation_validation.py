import pytest
from engine.transportation.validation import (
    validate_transportation_problem,
    create_transportation_problem,
    TransportationValidationError,
)


def test_valid_problem():
    cost = [[3, 1, 7], [2, 6, 8], [7, 4, 2]]
    supply = [5, 6, 4]
    demand = [5, 4, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is True
    assert errors == []


def test_empty_matrix():
    result, errors = validate_transportation_problem([], [1], [1])
    assert result is False
    assert any("empty" in e.lower() for e in errors)


def test_mismatched_dimensions():
    cost = [[1, 2], [3, 4]]  # 2x2
    supply = [1, 2, 3]  # 3 sources
    demand = [1, 2]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("rows" in e and "3" in e for e in errors)


def test_negative_cost():
    cost = [[3, 1, 7], [2, -6, 8], [7, 4, 2]]
    supply = [5, 6, 4]
    demand = [5, 4, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("negative" in e for e in errors)


def test_negative_supply():
    cost = [[3, 1], [2, 6]]
    supply = [5, -6]
    demand = [5, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("negative" in e for e in errors)


def test_negative_demand():
    cost = [[3, 1], [2, 6]]
    supply = [5, 6]
    demand = [-5, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False


def test_non_numeric_value():
    cost = [[3, "a"], [2, 6]]
    supply = [5, 6]
    demand = [5, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("not numeric" in e for e in errors)


def test_zero_total_supply():
    cost = [[3, 1], [2, 6]]
    supply = [0, 0]
    demand = [5, 6]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("Total supply is zero" in e for e in errors)


def test_zero_total_demand():
    cost = [[3, 1], [2, 6]]
    supply = [5, 6]
    demand = [0, 0]
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False
    assert any("Total demand is zero" in e for e in errors)


def test_source_names_mismatch():
    cost = [[3, 1], [2, 6]]
    supply = [5, 6]
    demand = [5, 6]
    result, errors = validate_transportation_problem(cost, supply, demand,
                                                     source_names=["A", "B", "C"])
    assert result is False


def test_rectangular_columns_mismatch():
    cost = [[1, 2, 3], [4, 5, 6]]  # 2x3
    supply = [1, 2]
    demand = [1, 2]  # only 2 demands
    result, errors = validate_transportation_problem(cost, supply, demand)
    assert result is False


def test_create_valid_problem():
    cost = [[3, 1], [2, 6]]
    supply = [5, 6]
    demand = [5, 6]
    problem = create_transportation_problem(cost, supply, demand)
    assert problem.num_sources == 2
    assert problem.num_destinations == 2
    assert problem.total_supply == 11
    assert problem.total_demand == 11


def test_create_invalid_problem_raises():
    with pytest.raises(TransportationValidationError):
        create_transportation_problem([[1]], [1], [-1])
