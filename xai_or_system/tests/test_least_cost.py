import pytest
from engine.transportation.models import TransportationProblem, BalancedTransportationProblem
from engine.transportation.least_cost import solve_least_cost


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


def test_least_cost_basic():
    # Classic example where least cost gives known result
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)

    # Verify supply and demand constraints are met
    for i in range(3):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(3)) == demand[j]

    # Verify all allocations non-negative
    for row in result.allocation:
        for val in row:
            assert val >= 0

    # Least cost cell is (0,1) cost=1, allocate min(3,3)=3
    assert result.allocation[0][1] == 3


def test_least_cost_small():
    cost = [[3, 8], [4, 1]]
    supply = [3, 3]
    demand = [3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    # Lowest cost = 1 at (1,1). Allocate min(3,3)=3.
    # Then remaining: (0,0) cost=3 allocate 3.
    assert result.allocation[1][1] == 3
    assert result.allocation[0][0] == 3
    assert result.total_cost == pytest.approx(3*1 + 3*3)


def test_least_cost_ties_top_left():
    # Two cells with same lowest cost; tie-break to smallest row then col
    cost = [[1, 5], [1, 5]]
    supply = [2, 2]
    demand = [2, 2]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    # Lowest cost = 1 at (0,0) [prioritized over (1,0)].
    # Allocate min(2,2)=2 at (0,0). Then (1,1) cost=5 allocate 2.
    assert result.allocation[0][0] == 2
    assert result.allocation[1][1] == 2
    assert result.total_cost == pytest.approx(2*1 + 2*5)


def test_least_cost_ties_same_row_col():
    # Ties within same row: choose smaller column
    cost = [[1, 1], [5, 5]]
    supply = [2, 2]
    demand = [2, 2]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    # Lowest = 1 at (0,0) or (0,1). Choose (0,0). Allocate 2.
    # Then (1,1) cost=5 allocate 2.
    assert result.allocation[0][0] == 2
    assert result.allocation[1][1] == 2


def test_least_cost_round_robin():
    cost = [[1, 2, 3], [4, 5, 6]]
    supply = [5, 5]
    demand = [3, 4, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    # Lowest = 1 at (0,0): allocate min(5,3)=3
    assert result.allocation[0][0] == 3
    # Verify constraints
    for i in range(2):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(2)) == demand[j]


def test_least_cost_3x3_constraints():
    cost = [[4, 6, 8], [6, 8, 6], [8, 6, 4]]
    supply = [50, 60, 40]
    demand = [50, 40, 60]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    for i in range(3):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(3)) == demand[j]


def test_least_cost_matches_northwest_for_single_cell():
    cost = [[5]]
    supply = [5]
    demand = [5]
    problem = make_balanced(cost, supply, demand)
    result = solve_least_cost(problem)
    assert result.allocation[0][0] == 5
    assert result.total_cost == pytest.approx(25)
