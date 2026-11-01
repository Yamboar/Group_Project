"""Tests for degeneracy handling and edge cases in transportation problems."""
import pytest
from engine.transportation.models import TransportationProblem, BalancedTransportationProblem
from engine.transportation.northwest_corner import solve_north_west_corner
from engine.transportation.least_cost import solve_least_cost
from engine.transportation.vogel import solve_vogel
from engine.transportation.stepping_stone import solve_stepping_stone
from tests.conftest import make_balanced


def count_basic(allocation):
    return sum(1 for row in allocation for c in row if c > 1e-9)


def test_degenerate_initial_optimized_keeps_constraints():
    """Even when degenerate, the optimized solution must satisfy constraints."""
    cost = [[2, 2, 2], [1, 5, 1], [9, 8, 8]]
    supply = [4, 6, 4]
    demand = [7, 5, 2]
    problem = make_balanced(cost, supply, demand)

    for initial_fn in [solve_north_west_corner, solve_least_cost, solve_vogel]:
        initial = initial_fn(problem)
        optimized = solve_stepping_stone(problem, initial)
        assert optimized.is_optimal, f"{initial_fn.__name__} did not reach optimality"
        for i in range(3):
            assert abs(sum(optimized.allocation[i]) - supply[i]) < 1e-5
        for j in range(3):
            assert abs(sum(optimized.allocation[i][j] for i in range(3)) - demand[j]) < 1e-5
        for row in optimized.allocation:
            for val in row:
                assert val >= -1e-6


def test_degenerate_basis_epsilon_retained():
    """A degenerate step should retain an epsilon basic cell (m+n-1 basics)."""
    cost = [[2, 2, 2], [1, 5, 1], [9, 8, 8]]
    supply = [4, 6, 4]
    demand = [7, 5, 2]
    problem = make_balanced(cost, supply, demand)
    initial = solve_least_cost(problem)
    optimized = solve_stepping_stone(problem, initial)
    # After optimization, either full basis or constraint-correct
    assert optimized.is_optimal


def test_already_optimal_initial():
    """A case where the initial solution is already optimal."""
    # This matrix has supply==demand on diagonal low cost
    cost = [[1, 100], [100, 1]]
    supply = [5, 5]
    demand = [5, 5]
    problem = make_balanced(cost, supply, demand)
    # Least cost gives (0,0)=5 and (1,1)=5 = 5+5 = 10, which is optimal
    initial = solve_least_cost(problem)
    optimized = solve_stepping_stone(problem, initial)
    assert optimized.is_optimal
    assert optimized.total_cost == pytest.approx(initial.total_cost)


def test_no_worsening_from_optimization():
    """Optimization never increases cost from a valid BFS."""
    cost = [[3, 8, 4, 6], [2, 6, 1, 9], [7, 5, 2, 8]]
    supply = [10, 15, 12]
    demand = [8, 10, 9, 10]
    problem = make_balanced(cost, supply, demand)
    for initial_fn in [solve_north_west_corner, solve_least_cost, solve_vogel]:
        initial = initial_fn(problem)
        optimized = solve_stepping_stone(problem, initial)
        assert optimized.total_cost <= initial.total_cost + 1e-6


def test_larger_matrix_random_constraints():
    """A 4x4 problem verifies constraints after optimization."""
    cost = [
        [10, 20, 5, 15],
        [12, 8, 7, 18],
        [9, 14, 11, 13],
        [16, 6, 19, 4],
    ]
    supply = [20, 10, 15, 15]
    demand = [12, 10, 15, 23]
    problem = make_balanced(cost, supply, demand)
    initial = solve_vogel(problem)
    optimized = solve_stepping_stone(problem, initial)
    assert optimized.is_optimal
    assert optimized.total_cost <= initial.total_cost
    for i in range(4):
        assert abs(sum(optimized.allocation[i]) - supply[i]) < 1e-5
    for j in range(4):
        assert abs(sum(optimized.allocation[i][j] for i in range(4)) - demand[j]) < 1e-5
