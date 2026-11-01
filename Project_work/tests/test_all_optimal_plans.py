"""All-optimal-plans enumeration tests for the assignment module.

Every perfect matching on the final reduced matrix's zero cells is an optimal
plan. These tests check the count, the listing, dummy de-duplication, the
truncation cap, and that every listed plan really achieves the optimal cost.
"""
import itertools
import json

import pytest

from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType
from backend.serializers import serialize_assignment_solution

solver = AssignmentSolver()


def _brute_force_optima(matrix, problem_type=AssignmentProblemType.MINIMIZATION):
    """Reference oracle for small square problems: return (min_cost, count)."""
    rows = len(matrix)
    cols = len(matrix[0])
    if problem_type == AssignmentProblemType.MAXIMIZATION:
        value = -1.0  # treat as maximisation over costs
    else:
        value = 1.0
    best = None
    count = 0
    for perm in itertools.permutations(range(cols)):
        total = value * sum(matrix[r][perm[r]] for r in range(rows))
        if best is None or total < best - 1e-9:
            best = total
            count = 1
        elif abs(total - best) < 1e-9:
            count += 1
    return best, count


def _cost_of_plan(matrix, plan):
    """Cost of a balanced plan against the ORIGINAL matrix (dummy rows/cols
    contribute 0); only rows/cols present in the original matrix count."""
    rows = len(matrix)
    cols = len(matrix[0])
    real = [(r, c) for (r, c) in plan if r < rows and c < cols]
    assert len(real) == min(rows, cols)
    return sum(matrix[r][c] for r, c in real)


def test_unique_optimum_reports_single_plan():
    matrix = [[9, 11, 14, 11], [6, 15, 13, 10], [12, 7, 10, 10], [12, 16, 8, 9]]
    r = solver.solve(matrix, problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["has_alternative_optima"] is False
    assert r["number_of_optimal_assignments"] == 1
    assert r["all_optimal_assignments"] == [[[0, 3], [1, 0], [2, 1], [3, 2]]]
    assert r["optimal_assignments_truncated"] is False


def test_two_identical_plans_enumerated():
    r = solver.solve([[1, 1], [1, 1]], problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 2
    assert r["has_alternative_optima"] is True
    assert sorted(r["all_optimal_assignments"]) == [
        [[0, 0], [1, 1]],
        [[0, 1], [1, 0]],
    ]


def test_all_equal_3x3_counts_six():
    r = solver.solve([[5, 5, 5], [5, 5, 5], [5, 5, 5]],
                     problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 6
    assert len(r["all_optimal_assignments"]) == 6
    assert r["optimal_assignments_truncated"] is False
    # every plan is a perfect matching on all three rows/cols
    for plan in r["all_optimal_assignments"]:
        assert len(plan) == 3
        assert sorted(r for r, _ in plan) == [0, 1, 2]
        assert sorted(c for _, c in plan) == [0, 1, 2]


@pytest.mark.parametrize("n", [2, 3, 4])
def test_count_matches_brute_force(n):
    matrix = [[1] * n for _ in range(n)]
    _, expected = _brute_force_optima(matrix)
    r = solver.solve(matrix, problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == expected


def test_count_with_restricted_cell_matches_brute_force():
    matrix = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
    # forbid (0,0): number of optimal = 4! - 3! = 18
    r = solver.solve(matrix, restricted_cells=[[0, 0]],
                     problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 18
    assert all([0, 0] not in plan for plan in r["all_optimal_assignments"])


def test_every_plan_reaches_the_optimal_cost():
    matrix = [[5, 3, 2, 8], [7, 9, 1, 6], [6, 4, 3, 7], [8, 5, 2, 4]]
    r = solver.solve(matrix, problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] > 1
    for plan in r["all_optimal_assignments"]:
        assert abs(_cost_of_plan(matrix, plan) - r["final_cost"]) < 1e-9


def test_cap_truncates_listing_but_keeps_exact_count():
    matrix = [[1] * 6 for _ in range(6)]  # 720 optimal plans
    r = solver.solve(matrix, problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 720
    assert len(r["all_optimal_assignments"]) == 100
    assert r["optimal_assignments_truncated"] is True


def test_maximization_multiplicity():
    r = solver.solve([[2, 2], [2, 2]], problem_type=AssignmentProblemType.MAXIMIZATION)
    assert r["number_of_optimal_assignments"] == 2


def test_rectangular_plans_deduped_on_real_rows():
    # 2 rows x 3 cols: one dummy column. The real rows each land on a real
    # column; the leftover job goes to the dummy. Both real plans:
    #   row0→job2 (1) + row1→job1 (2)   and   row0→job2 (1) + row1→job3 (2)
    r = solver.solve([[3, 1, 3], [2, 4, 2]],
                     problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 2
    real_pairings = {
        tuple(sorted((rr, c) for (rr, c) in plan if rr < 2))
        for plan in r["all_optimal_assignments"]
    }
    assert real_pairings == {
        ((0, 1), (1, 0)),
        ((0, 1), (1, 2)),
    }


def test_rectangular_more_rows_deduped():
    # 3 rows x 2 cols: one dummy row. Every optimal plan picks 2 of the 3
    # workers for the 2 jobs and dumps the third onto the dummy column:
    # 2 job permutations x 3 idle-worker choices = 6 distinct real plans.
    r = solver.solve([[1, 1], [1, 1], [1, 1]],
                     problem_type=AssignmentProblemType.MINIMIZATION)
    assert r["number_of_optimal_assignments"] == 6
    for plan in r["all_optimal_assignments"]:
        assert len(plan) == 3
        real_pairings = [(rr, c) for (rr, c) in plan if rr < 3 and c < 2]
        assert len(real_pairings) == 2
        assert sorted(c for _, c in real_pairings) == [0, 1]


def test_result_serializes_to_json():
    r = solver.solve([[1, 1], [1, 1]], problem_type=AssignmentProblemType.MINIMIZATION)
    ser = serialize_assignment_solution(r)
    json.dumps(ser)  # must not raise
    assert ser["number_of_optimal_assignments"] == 2
    assert isinstance(ser["all_optimal_assignments"][0][0], list)


def test_xai_summary_mentions_count():
    from xai.explanation_engine import ExplanationEngine

    r = solver.solve([[1, 1], [1, 1]], problem_type=AssignmentProblemType.MINIMIZATION)
    exp = ExplanationEngine().generate_assignment_explanation(r)
    assert "2 different optimal assignment plans" in exp.summary


def test_warning_mentions_count():
    r = solver.solve([[1, 1], [1, 1]], problem_type=AssignmentProblemType.MINIMIZATION)
    assert any("2 different optimal assignment plans" in w for w in r["warnings"])