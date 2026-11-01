"""Shared fixtures and benchmark data for tests."""
import pytest
from engine.transportation.models import TransportationProblem, BalancedTransportationProblem


def make_balanced(cost, supply, demand):
    """Create a balanced transportation problem for testing."""
    problem = TransportationProblem(cost_matrix=cost, supply=supply, demand=demand)
    return BalancedTransportationProblem(
        original_problem=problem,
        cost_matrix=cost,
        supply=supply,
        demand=demand,
        source_names=problem.source_names,
        dest_names=problem.dest_names,
    )


@pytest.fixture
def balanced_3x3():
    """A standard 3x3 balanced transportation problem."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    return make_balanced(cost, supply, demand)


@pytest.fixture
def balanced_3x4():
    """A 3x4 balanced transportation problem."""
    cost = [[19, 30, 50, 10], [70, 30, 40, 60], [40, 8, 70, 20]]
    supply = [7, 9, 18]
    demand = [5, 8, 7, 14]
    return make_balanced(cost, supply, demand)


@pytest.fixture
def transportation_problem():
    """Classic transportation problem for optimization tests."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    return make_balanced(cost, supply, demand)
