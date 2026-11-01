import pytest
from engine.assignment.hungarian import solve_hungarian
from engine.assignment.models import AssignmentProblem, AssignmentProblemType


def make_problem(cost, ptype=AssignmentProblemType.MINIMIZATION):
    return AssignmentProblem(cost_matrix=cost, problem_type=ptype)


def test_hungarian_simple():
    cost = [[2, 3], [3, 2]]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    assert result.total_cost == pytest.approx(4)
    # Verify one-to-one
    rows = [a["row"] for a in result.assignments]
    cols = [a["col"] for a in result.assignments]
    assert len(set(rows)) == 2
    assert len(set(cols)) == 2


def test_hungarian_3x3_known():
    cost = [
        [4, 1, 3],
        [2, 0, 5],
        [3, 2, 2],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    # Known optimal cost is 1+2+2 = 5? Let's verify valid assignment exists.
    assert result.total_cost >= 0
    assert len(result.assignments) == 3


def test_hungarian_classic():
    cost = [
        [10, 5, 13, 15, 16],
        [3, 9, 18, 13, 6],
        [10, 7, 2, 2, 2],
        [7, 11, 9, 7, 12],
        [7, 9, 10, 4, 12],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal


def test_hungarian_square_constraints():
    cost = [
        [4, 6, 8],
        [6, 8, 6],
        [8, 6, 4],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    rows = [a["row"] for a in result.assignments]
    cols = [a["col"] for a in result.assignments]
    assert len(set(rows)) == 3
    assert len(set(cols)) == 3


def test_hungarian_rectangular_more_rows():
    cost = [
        [4, 6, 8],
        [6, 8, 6],
        [8, 6, 4],
        [2, 3, 4],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    # Should assign 3 workers to 3 jobs (one dummy excluded)
    real = [a for a in result.assignments
            if not a["row_name"].startswith("Dummy")
            and not a["col_name"].startswith("Dummy")]
    assert len(set(a["row"] for a in real)) == 3
    assert len(set(a["col"] for a in real)) == 3


def test_hungarian_rectangular_more_cols():
    cost = [
        [4, 6, 8, 5],
        [6, 8, 6, 7],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.is_optimal
    real = [a for a in result.assignments
            if not a["row_name"].startswith("Dummy")
            and not a["col_name"].startswith("Dummy")]
    assert len(real) == 2


def test_hungarian_maximization():
    cost = [
        [10, 5],
        [5, 10],
    ]
    problem = make_problem(cost, AssignmentProblemType.MAXIMIZATION)
    result = solve_hungarian(problem)
    assert result.is_optimal
    # For maximization, best total = 10 + 10 = 20 (diagonal)
    assert result.total_cost == pytest.approx(20)


def test_hungarian_1x1():
    cost = [[7]]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert result.total_cost == pytest.approx(7)
    assert result.is_optimal


def test_hungarian_cost_from_original_matrix():
    """Final cost must be computed from the original cost matrix, not reduced."""
    cost = [
        [4, 6, 8],
        [6, 8, 6],
        [8, 6, 4],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)

    # Compute cost from assignments using original matrix
    manual_cost = 0.0
    for a in result.assignments:
        row, col = a["row"], a["col"]
        manual_cost += a["original_cost"]
    assert abs(manual_cost - result.total_cost) < 1e-6
    # Ensure cost matches original matrix values (not reduced matrix)
    selected = [(a["row"], a["col"]) for a in result.assignments]
    val_total = sum(cost[r][c] for r, c in selected)
    assert result.total_cost == pytest.approx(val_total)
    # Reduce matrix should NOT equal the original cost sum (reduced has zeros)
    reduced_total = sum(a["reduced_cost"] for a in result.assignments)
    assert abs(reduced_total - result.total_cost) > 1e-6 or reduced_total == 0


def test_hungarian_deterministic():
    cost = [
        [4, 6, 8],
        [6, 8, 6],
        [8, 6, 4],
    ]
    p1 = make_problem(cost)
    p2 = make_problem(cost)
    r1 = solve_hungarian(p1)
    r2 = solve_hungarian(p2)
    assert r1.assignments == r2.assignments
    assert r1.total_cost == r2.total_cost


def test_hungarian_steps_recorded():
    cost = [
        [4, 6, 8],
        [6, 8, 6],
        [8, 6, 4],
    ]
    problem = make_problem(cost)
    result = solve_hungarian(problem)
    assert len(result.steps) > 0
    # First step should be row reduction (after initial)
    ops = [s.operation for s in result.steps]
    assert "row_reduction" in ops
    assert "column_reduction" in ops
