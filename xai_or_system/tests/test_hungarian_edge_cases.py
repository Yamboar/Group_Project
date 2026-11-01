"""Tests for the Hungarian method with multiple optimal solutions and edge cases."""
import pytest
from engine.assignment.hungarian import solve_hungarian
from engine.assignment.models import AssignmentProblem, AssignmentProblemType


def make_problem(cost, ptype=AssignmentProblemType.MINIMIZATION):
    return AssignmentProblem(cost_matrix=cost, problem_type=ptype)


def test_unique_optimal_solution():
    """A matrix with a unique optimal assignment."""
    cost = [
        [1, 100, 100],
        [100, 2, 100],
        [100, 100, 3],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    assert result.total_cost == pytest.approx(6)
    assert len(result.assignments) == 3


def test_multiple_optimal_solutions_valid():
    """With multiple optimal solutions, any returned assignment must still be optimal."""
    # All costs equal -> any assignment is optimal with cost = 3*value
    cost = [
        [5, 5, 5],
        [5, 5, 5],
        [5, 5, 5],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    assert result.total_cost == pytest.approx(15)
    # verify it's a valid one-to-one assignment
    rows = [a["row"] for a in result.assignments]
    cols = [a["col"] for a in result.assignments]
    assert len(set(rows)) == 3
    assert len(set(cols)) == 3


def test_duplicate_ties():
    """A matrix with symetric ties - must still give valid complete assignment."""
    cost = [
        [2, 2, 7],
        [2, 2, 7],
        [7, 7, 8],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    # verify complete one-to-one
    assert len({a["row"] for a in result.assignments}) == 3
    assert len({a["col"] for a in result.assignments}) == 3
    # Verify cost is from original matrix
    selected = {(a["row"], a["col"]) for a in result.assignments}
    assert result.total_cost == pytest.approx(sum(cost[r][c] for r, c in selected))


def test_rectangular_dummy_assignment_correct():
    """Dummy assignments should not be counted as real costs."""
    cost = [
        [2, 3],
        [4, 1],
        [5, 6],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    # 3 workers, 2 jobs -> one worker gets a dummy (excluded from real cost)
    real = [a for a in result.assignments
            if not a["row_name"].startswith("Dummy")
            and not a["col_name"].startswith("Dummy")]
    real_total = sum(a["original_cost"] for a in real)
    assert real_total == result.total_cost


def test_larger_assignment_brute_force_check():
    """Verify Hungarian matches brute force on a 4x4 problem."""
    import itertools
    cost = [
        [10, 5, 13, 15],
        [3, 9, 18, 13],
        [10, 7, 2, 2],
        [7, 11, 9, 7],
    ]
    n = 4
    brute_best = min(
        sum(cost[i][perm[i]] for i in range(n))
        for perm in itertools.permutations(range(n))
    )
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    assert result.total_cost == pytest.approx(brute_best)


def test_assignment_with_maximization_matches_brute_force():
    import itertools
    cost = [
        [10, 5, 7],
        [8, 12, 6],
        [4, 9, 11],
    ]
    n = 3
    brute_best = max(
        sum(cost[i][perm[i]] for i in range(n))
        for perm in itertools.permutations(range(n))
    )
    problem = make_problem(cost, AssignmentProblemType.MAXIMIZATION)
    result = solve_hungarian(problem)
    assert result.is_optimal
    assert result.total_cost == pytest.approx(brute_best)
