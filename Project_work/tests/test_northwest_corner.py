import pytest
from engine.transportation.models import TransportationProblem, BalancedTransportationProblem
from engine.transportation.northwest_corner import solve_north_west_corner


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


def test_classic_northwest_corner():
    # Standard textbook example
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)

    assert result.allocation[0][0] == 3  # (1,1): min(3,4)=3
    assert result.allocation[0][1] == 0  # (1,2): supply exhausted
    assert result.allocation[1][0] == 1  # (2,1): min(3,1)=1
    assert result.allocation[1][1] == 2  # (2,2): min(2,3)=2
    assert result.allocation[2][2] == 3  # (3,3): min(4,3)=3
    assert result.allocation[2][1] == 1  # (3,2): remaining

    # Verify total cost = 3*3 + 1*4 + 2*2 + 1*3 + 3*8 = 9+4+4+3+24 = 44
    assert result.total_cost == pytest.approx(44)


def test_northwest_small():
    cost = [[3, 1], [2, 6]]
    supply = [5, 6]
    demand = [5, 6]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)
    # (1,1): 5, then (2,2): 6
    assert result.allocation[0][0] == 5
    assert result.allocation[0][1] == 0
    assert result.allocation[1][0] == 0
    assert result.allocation[1][1] == 6
    assert result.total_cost == pytest.approx(5*3 + 6*6)


def test_northwest_equal_row_col_exhaust():
    cost = [[2, 4], [4, 2]]
    supply = [3, 3]
    demand = [3, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)
    # (1,1): 3, both exhausted, diagonal to (2,2): 3
    assert result.allocation[0][0] == 3
    assert result.allocation[0][1] == 0
    assert result.allocation[1][0] == 0
    assert result.allocation[1][1] == 3
    assert result.total_cost == pytest.approx(3*2 + 3*2)


def test_northwest_round_robin():
    cost = [[1, 2, 3], [4, 5, 6]]
    supply = [5, 5]
    demand = [3, 4, 3]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)
    # (1,1): 3, (1,2): 2, (2,2): 2, (2,3): 3
    assert result.allocation[0][0] == 3
    assert result.allocation[0][1] == 2
    assert result.allocation[0][2] == 0
    assert result.allocation[1][0] == 0
    assert result.allocation[1][1] == 2
    assert result.allocation[1][2] == 3
    assert result.total_cost == pytest.approx(3*1 + 2*2 + 2*5 + 3*6)

    # Verify supply/demand constraints
    for i in range(2):
        assert sum(result.allocation[i]) == supply[i]
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(2)) == demand[j]


def test_northwest_1x1():
    cost = [[7]]
    supply = [5]
    demand = [5]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)
    assert result.allocation[0][0] == 5
    assert result.total_cost == pytest.approx(35)


def test_northwest_3x3_full():
    """3x3 problem with balanced supply/demand — NWC must satisfy all constraints."""
    cost = [[19, 30, 50], [70, 30, 40], [40, 8, 70]]
    supply = [7, 9, 18]
    demand = [7, 9, 18]  # balanced: total = 34 each
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)

    # Supply constraints
    for i in range(3):
        assert sum(result.allocation[i]) == pytest.approx(supply[i])
    # Demand constraints
    for j in range(3):
        assert sum(result.allocation[i][j] for i in range(3)) == pytest.approx(demand[j])
    # NWC allocates along the diagonal path: (0,0)->7, (1,1)->9, (2,2)->18
    assert result.allocation[0][0] == pytest.approx(7)
    assert result.allocation[1][1] == pytest.approx(9)
    assert result.allocation[2][2] == pytest.approx(18)
    assert result.total_cost == pytest.approx(7*19 + 9*30 + 18*70)


def test_northwest_non_integer():
    cost = [[2.5, 3.2], [4.1, 1.8]]
    supply = [4.5, 5.5]
    demand = [4.5, 5.5]
    problem = make_balanced(cost, supply, demand)
    result = solve_north_west_corner(problem)
    assert result.allocation[0][0] == pytest.approx(4.5)
    assert result.allocation[1][1] == pytest.approx(5.5)
