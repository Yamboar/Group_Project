import pytest
from engine.transportation.models import TransportationProblem
from engine.transportation.balancing import balance_problem


def make_problem(cost, supply, demand):
    """Helper to create a TransportationProblem."""
    return TransportationProblem(
        cost_matrix=cost, supply=supply, demand=demand
    )


def test_balanced_problem_no_change():
    problem = make_problem([[3, 1], [2, 6]], [5, 6], [5, 6])
    balanced, events = balance_problem(problem)
    assert balanced.dummy_source_added is False
    assert balanced.dummy_destination_added is False
    assert len(events) == 1
    assert events[0]["action"] == "no_change"
    assert balanced.num_sources == 2
    assert balanced.num_destinations == 2


def test_supply_exceeds_demand_adds_dummy_destination():
    problem = make_problem([[3, 1], [2, 6]], [10, 5], [5, 6])
    balanced, events = balance_problem(problem)
    assert balanced.dummy_destination_added is True
    assert balanced.dummy_source_added is False
    # New destination added with deficit = 15 - 11 = 4
    assert balanced.num_destinations == 3
    assert balanced.demand[-1] == pytest.approx(4)
    # Zero cost column for dummy
    for i in range(problem.num_sources):
        assert balanced.cost_matrix[i][-1] == 0
    # Find the balancing event
    bal_event = [e for e in events if e["action"] == "add_dummy_destination"]
    assert len(bal_event) == 1
    assert bal_event[0]["deficit"] == pytest.approx(4)


def test_demand_exceeds_supply_adds_dummy_source():
    problem = make_problem([[3, 1], [2, 6]], [5, 6], [10, 5])
    balanced, events = balance_problem(problem)
    assert balanced.dummy_source_added is True
    assert balanced.dummy_destination_added is False
    # New source added with deficit = 15 - 11 = 4
    assert balanced.num_sources == 3
    assert balanced.supply[-1] == pytest.approx(4)
    # Zero cost row for dummy
    for j in range(problem.num_destinations):
        assert balanced.cost_matrix[-1][j] == 0
    bal_event = [e for e in events if e["action"] == "add_dummy_source"]
    assert len(bal_event) == 1
    assert bal_event[0]["deficit"] == pytest.approx(4)


def test_zero_deficit_balanced():
    problem = make_problem([[3, 1], [2, 6]], [5, 6], [5, 6])
    balanced, _ = balance_problem(problem)
    # No dummy added
    assert not balanced.dummy_source_added and not balanced.dummy_destination_added


def test_original_problem_preserved():
    cost = [[3, 1], [2, 6]]
    supply = [10, 5]
    demand = [5, 6]
    problem = make_problem(cost, supply, demand)
    balanced, _ = balance_problem(problem)
    # Original problem unchanged
    assert problem.cost_matrix == cost
    assert problem.supply == supply
    assert problem.demand == demand
    # Balanced differs
    assert balanced.cost_matrix != cost
    assert isinstance(balanced.original_problem, TransportationProblem)


def test_large_imbalance():
    problem = make_problem([[3, 1], [2, 6]], [100, 2], [5, 6])
    balanced, _ = balance_problem(problem)
    assert balanced.dummy_destination_added is True
    assert balanced.demand[-1] == pytest.approx(91)
