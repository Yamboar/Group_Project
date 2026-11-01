import pytest
from engine.transportation.northwest_corner import solve_north_west_corner
from engine.transportation.least_cost import solve_least_cost
from engine.transportation.vogel import solve_vogel
from engine.transportation.stepping_stone import solve_stepping_stone
from tests.conftest import make_balanced


def test_stepping_stone_improves_northwest():
    """Verify Stepping Stone improves the NWC solution."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    initial = solve_north_west_corner(problem)
    optimized = solve_stepping_stone(problem, initial)

    assert optimized.is_optimal
    assert optimized.total_cost <= initial.total_cost
    assert optimized.total_cost >= 0


def test_stepping_stone_optimality_no_negative_indices():
    """After optimization, no non-basic cell should have negative improvement index."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)

    for initial_fn in [solve_north_west_corner, solve_least_cost, solve_vogel]:
        initial = initial_fn(problem)
        optimized = solve_stepping_stone(problem, initial)
        for c in optimized.final_improvement_indices:
            assert c.improvement_index >= -1e-6, \
                f"Cell ({c.row+1},{c.col+1}) has negative index {c.improvement_index}"


def test_stepping_stone_preserves_constraints():
    """Optimized allocation must still satisfy all supply/demand constraints."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    initial = solve_vogel(problem)
    optimized = solve_stepping_stone(problem, initial)

    for i in range(3):
        assert sum(optimized.allocation[i]) == pytest.approx(supply[i])
    for j in range(3):
        assert sum(optimized.allocation[i][j] for i in range(3)) == pytest.approx(demand[j])
    for row in optimized.allocation:
        for val in row:
            assert val >= -1e-6


def test_stepping_stone_known_optimal_cost():
    """Verify a known optimal solution cost for the 3x3 example."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    initial = solve_vogel(problem)
    optimized = solve_stepping_stone(problem, initial)
    # Manually verified optimal: (0,1)=3, (1,2)=3, (2,0)=4
    # Cost = 3*1 + 3*4 + 4*3 = 3+12+12 = 27
    assert optimized.is_optimal
    assert optimized.total_cost == pytest.approx(27.0)


def test_stepping_stone_already_optimal_initial():
    """A case where the initial solution is already optimal (single allocation)."""
    cost = [[5]]
    supply = [5]
    demand = [5]
    problem = make_balanced(cost, supply, demand)
    initial = solve_vogel(problem)
    optimized = solve_stepping_stone(problem, initial)
    # With a 1x1 problem, there are no non-basic cells. Should be cost 25, optimal.
    assert optimized.total_cost == pytest.approx(25.0)
    assert optimized.is_optimal


def test_stepping_stone_multiple_iterations():
    """A case requiring multiple iterations."""
    cost = [[3, 4, 5], [2, 3, 4], [1, 2, 3]]
    supply = [10, 20, 30]
    demand = [10, 25, 25]
    problem = make_balanced(cost, supply, demand)
    # Use NWC which often needs multiple iterations
    initial = solve_north_west_corner(problem)
    optimized = solve_stepping_stone(problem, initial)
    assert optimized.is_optimal
    assert optimized.total_cost <= initial.total_cost
    # Verify constraints
    for i in range(3):
        assert sum(optimized.allocation[i]) == pytest.approx(supply[i])
    for j in range(3):
        assert sum(optimized.allocation[i][j] for i in range(3)) == pytest.approx(demand[j])


def test_stepping_stone_loop_validity():
    """Each recorded loop must start and end at the candidate cell and be valid."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    initial = solve_vogel(problem)
    optimized = solve_stepping_stone(problem, initial)

    for it in optimized.iterations:
        bc = it.best_candidate
        loop = bc.loop
        # Loop must start and end at candidate cell
        assert loop[0] == [bc.row, bc.col]
        assert loop[-1] == [bc.row, bc.col]
        # Must be at least 4 cells (rectangle)
        assert len(loop) >= 4
        # Signs must alternate
        for k in range(1, len(bc.signs)):
            assert bc.signs[k] != bc.signs[k-1]


def test_stepping_stone_improvement_index_recording():
    """Each iteration must record all candidates with their improvement indices."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    initial = solve_north_west_corner(problem)
    optimized = solve_stepping_stone(problem, initial)

    for it in optimized.iterations:
        assert len(it.candidates) > 0
        for c in it.candidates:
            assert hasattr(c, "improvement_index")


def test_stepping_stone_deterministic():
    """Same input must produce same result."""
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    problem = make_balanced(cost, supply, demand)
    init1 = solve_vogel(problem)
    r1 = solve_stepping_stone(problem, init1)
    init2 = solve_vogel(problem)
    r2 = solve_stepping_stone(problem, init2)
    assert r1.allocation == r2.allocation
    assert r1.total_cost == r2.total_cost
