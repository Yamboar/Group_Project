import pytest
from engine.transportation.models import TransportationProblem, BalancedTransportationProblem
from engine.transportation.vogel import solve_vogel


def make_balanced(cost, supply, demand):
    problem = TransportationProblem(cost_matrix=cost, supply=supply, demand=demand)
    return BalancedTransportationProblem(
        original_problem=problem,
        cost_matrix=cost,
        supply=supply,
        demand=demand,
        source_names=problem.source_names,
        dest_names=problem.dest_names,
    )


def test_vogel_constraints_3x3():
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    for i in range(3):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(3)) == demand[j]
    for row in result.allocation:
        for val in row:
            assert val >= 0


def test_vogel_small():
    cost = [[3, 8], [4, 1]]
    supply = [3, 3]
    demand = [3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    for i in range(2):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(2):
        assert sum(result.allocation[i][j] for i in range(2)) == demand[j]


def test_vogel_prefers_low_cost():
    cost = [[8, 1], [1, 8]]
    supply = [5, 5]
    demand = [5, 5]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    # Row penalties: row0: 8-1=7, row1: 8-1=7.
    # Col0: 8-1=7, col1: 8-1=7.
    # Max penalty=7, row0 first. Cheapest cell (0,1) cost=1: allocate 5.
    # Then remaining (1,0) cost=1: allocate 5.
    assert result.allocation[0][1] == 5
    assert result.allocation[1][0] == 5
    assert result.total_cost == pytest.approx(10)


def test_vogel_round_robin():
    cost = [[1, 2, 3], [4, 5, 6]]
    supply = [5, 5]
    demand = [3, 4, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    for i in range(2):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(2)) == demand[j]


def test_vogel_balanced_example():
    cost = [[19, 30, 50, 10], [70, 30, 40, 60], [40, 8, 70, 20]]
    supply = [7, 9, 18]
    demand = [5, 8, 7, 14]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    for i in range(3):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(4):
        assert sum(result.allocation[i][j] for i in range(3)) == demand[j]


def test_vogel_single():
    cost = [[5]]
    supply = [5]
    demand = [5]
    problem = make_balanced(cost, supply, demand)
    result = solve_vogel(problem)
    assert result.allocation[0][0] == 5
    assert result.total_cost == pytest.approx(25)


def test_vogel_deterministic_repeatability():
    cost = [[4, 6, 8], [6, 8, 6], [8, 6, 4]]
    supply = [50, 60, 40]
    demand = [50, 40, 60]
    problem = make_balanced(cost, supply, demand)
    r1 = solve_vogel(problem)
    r2 = solve_vogel(problem)
    assert r1.allocation == r2.allocation
    assert r1.total_cost == r2.total_cost
