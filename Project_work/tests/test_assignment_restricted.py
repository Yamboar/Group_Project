"""Tests for restricted cells in the assignment model.

Cell semantics under the restricted design:
- 0            → a valid, allowed zero-cost assignment (participates normally).
- positive     → a valid allowed cost.
- negative     → invalid input, rejected with guidance to mark Restricted.
- None/blank   → missing input, rejected with guidance to mark Restricted.
- Restricted   → a separate cell state (worker/job pair that can never be
  assigned). Never represented by an artificial number, never transformed into
  an attractive zero, and never selected.

Also covers:
- legacy `prohibited_assignments` alias and the `PROHIBITED_COST` sentinel in
  the input matrix still being treated as restricted.
- feasibility gating across balanced (square) matrices with dummies.
- what-if re-solve with modified restrictions.
"""
import pytest
from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import (
    AssignmentProblem,
    AssignmentProblemType,
    PROHIBITED_COST,
)
from engine.assignment.hungarian import solve_hungarian
from engine.assignment.validation import validate_assignment_problem

solver = AssignmentSolver()


def _restricted(cells):
    return set(tuple(c) for c in cells)


def test_zero_cost_is_valid_and_participates_normally():
    """A 0 zip cell must be a normal allowed assignment, not Restricted."""
    # Only one feasible pair has cost 0; the zero-cost cell must be selectable.
    cost = [[0, 5], [5, 0]]
    result = solver.solve(cost_matrix=cost)
    assert result["success"]
    assert result["verification"]["passed"]
    assert result["final_cost"] == pytest.approx(0)
    assert result["problem"].restricted_cells == set()
    # No residual sentinel anywhere in reported data.
    for step in result["result"].steps:
        for row in step.matrix_after:
            assert all(v is None or v < PROHIBITED_COST for v in row)


def test_zero_cost_does_not_block_feasibility():
    """A cell holding 0 must never be treated as 'missing' or Restricted."""
    is_valid, errors = validate_assignment_problem([[0, 2], [3, 4]])
    assert is_valid
    assert errors == []


@pytest.mark.parametrize("bad", [-5, None, "x", True])
def test_invalid_values_rejected_with_restricted_guidance(bad):
    cost = [[bad, 2], [3, 4]]
    result = solver.solve(cost_matrix=cost)
    assert not result["success"]
    assert len(result["errors"]) > 0
    assert any("Restricted" in e for e in result["errors"])


def test_negative_value_guidance_mentions_restricted_explicitly():
    is_valid, errors = validate_assignment_problem([[-1, 2], [3, 4]])
    assert not is_valid
    assert any("mark the cell as Restricted instead" in e for e in errors)


def test_blank_cell_guidance_mentions_restricted_explicitly():
    is_valid, errors = validate_assignment_problem([[None, 2], [3, 4]])
    assert not is_valid
    assert any("mark the cell as Restricted" in e for e in errors)


def test_restricted_cell_exempt_from_value_validation():
    """Restricted cells may hold any placeholder and are ignored."""
    for placeholder in (None, -1, 1e15, "anything", 999999):
        cost = [[placeholder, 2], [3, 4]]
        result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 0]])
        assert result["success"], f"placeholder {placeholder} should be allowed"
        assert result["verification"]["passed"]
        assert (0, 0) in result["problem"].restricted_cells


def test_restricted_cell_out_of_range_rejected():
    is_valid, errors = validate_assignment_problem(
        [[1, 2], [3, 4]], restricted_cells=_restricted([[5, 5]])
    )
    assert not is_valid
    assert any("out-of-range" in e for e in errors)


def test_full_row_restricted_is_infeasible():
    is_valid, errors = validate_assignment_problem(
        [[5, 5, 5], [5, 5, 5]],
        restricted_cells=_restricted([[0, 0], [0, 1], [0, 2]]),
    )
    assert not is_valid
    assert any("Worker 1 cannot be assigned" in e for e in errors)


def test_full_column_restricted_is_infeasible():
    is_valid, errors = validate_assignment_problem(
        [[5, 5], [5, 5], [5, 5]],
        restricted_cells=_restricted([[0, 0], [1, 0], [2, 0]]),
    )
    assert not is_valid
    assert any("Job 1 cannot be assigned" in e for e in errors)


def test_hall_condition_shortfall_group_message():
    """Rows 0,1 can only reach column 0 → at most 2 of the 3 jobs can be filled."""
    is_valid, errors = validate_assignment_problem(
        [[5, 5, 5], [5, 5, 5], [5, 5, 5]],
        restricted_cells=_restricted([[0, 1], [0, 2], [1, 1], [1, 2]]),
    )
    assert not is_valid
    assert any("at most 2 of the 3 required job(s)" in e for e in errors)


def test_restricted_cell_never_selected_minimization():
    cost = [
        [1, 100],
        [100, 1],
    ]
    result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 0], [1, 1]])
    assert result["success"]
    assert result["verification"]["passed"]
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert not selected & _restricted([[0, 0], [1, 1]])
    # Only remaining pairing: (0,1) + (1,0) = 200
    assert result["final_cost"] == pytest.approx(200)


def test_restricted_cell_forces_cheaper_route_change():
    cost = [
        [1, 2],
        [3, 4],
    ]
    # Without restriction the natural pick is (0,0)+(1,1) = 5.
    base = solver.solve(cost_matrix=cost)
    assert base["final_cost"] == pytest.approx(5)
    # Restricting (0,0) forces (0,1)+(1,0) = 5 as well (tie).
    result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 0]])
    assert result["success"]
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert (0, 0) not in selected
    assert result["final_cost"] == pytest.approx(5)


def test_restricted_cell_never_becomes_zero_after_maximization_transform():
    """Under M - c, a restricted cell must stay restricted, not become a zero."""
    cost = [
        [10, 1],
        [1, 10],
    ]
    # Restrict (0,1): row 0 can only take (0,0). Then (1,1) -> profit 10+10=20
    result = solver.solve(
        cost_matrix=cost,
        problem_type=AssignmentProblemType.MAXIMIZATION,
        restricted_cells=[[0, 1]],
    )
    assert result["success"]
    assert result["verification"]["passed"]
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert (0, 1) not in selected
    assert result["final_cost"] == pytest.approx(20)
    # In the balanced (transformed) matrix the restricted cell must be None.
    balanced = result["balanced_problem"]
    assert balanced.cost_matrix[0][1] is None
    # In every reported Hungarian step the restricted cell shows None, never 0.
    for step in result["result"].steps:
        assert step.matrix_after[0][1] is None
    # Zero positions never include the restricted cell.
    for step in result["result"].steps:
        assert (0, 1) not in step.zero_positions


def test_restricted_cells_respected_in_all_hungarian_steps():
    cost = [
        [4, 1, 3],
        [2, 0, 5],
        [3, 2, 2],
    ]
    restricted = _restricted([[1, 2]])
    result = solver.solve(cost_matrix=cost, restricted_cells=[[1, 2]])
    assert result["success"]
    # Every reported step matrix shows None at the restricted cell.
    for step in result["result"].steps:
        assert step.matrix_after[1][2] is None
        assert step.matrix_before[1][2] is None
    # Final matrix keeps it None.
    assert result["result"].final_matrix[1][2] is None
    # zero positions never include the restricted cell.
    for step in result["result"].steps:
        assert (1, 2) not in step.zero_positions
    # The solution never selects it.
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert (1, 2) not in selected


def test_balanced_matrix_reports_none_not_sentinel():
    cost = [[1, 2], [3, 4]]
    result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 1]])
    balanced = result["balanced_problem"]
    assert balanced.cost_matrix[0][1] is None
    for i, j in [(0, 0), (1, 0), (1, 1)]:
        assert balanced.cost_matrix[i][j] is not None
    assert balanced.restricted_cells == _restricted([[0, 1]])


def test_rectangular_with_restrictions_and_dummies():
    # 2 workers, 3 jobs. Restricting (0,0),(0,1) leaves only (0,2) for worker 0.
    cost = [
        [1, 2, 3],
        [4, 5, 6],
    ]
    result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 0], [0, 1]])
    assert result["success"]
    assert result["verification"]["passed"]
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert (0, 0) not in selected and (0, 1) not in selected
    # dummy column assignment carries 0 cost and is not counted.
    real_rows = sorted({a["row"] for a in result["result"].assignments
                        if not a["is_dummy"]})
    assert real_rows == [0, 1]


def test_prohibited_assignments_legacy_alias():
    result = solver.solve(cost_matrix=[[1, 2], [3, 4]], prohibited_assignments=[[0, 0]])
    assert result["success"]
    assert (0, 0) in result["problem"].restricted_cells
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert (0, 0) not in selected
    assert result["verification"]["passed"]


def test_both_aliases_merge():
    result = solver.solve(
        cost_matrix=[[1, 2], [3, 4]],
        restricted_cells=[[0, 0]],
        prohibited_assignments=[[1, 1]],
    )
    assert result["success"]
    assert result["problem"].restricted_cells == _restricted([[0, 0], [1, 1]])
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert not selected & _restricted([[0, 0], [1, 1]])


def test_prohibited_cost_sentinel_in_matrix_treated_as_restricted():
    cost = [[1, 2], [3, 4]]
    cost[0][0] = PROHIBITED_COST
    result = solver.solve(cost_matrix=cost)
    assert result["success"]
    assert (0, 0) in result["problem"].restricted_cells
    assert result["problem"].restricted_cells == _restricted([[0, 0]])
    # Reported matrices must not leak the sentinel.
    for step in result["result"].steps:
        for i, j in [(0, 0)]:
            v = step.matrix_after[i][j]
            assert v is None or v < 1e12
    assert result["result"].final_matrix[0][0] is None


def test_assignment_model_to_dict_emits_lists():
    problem = AssignmentProblem(
        cost_matrix=[[1, 2], [3, 4]],
        restricted_cells=_restricted([[0, 1]]),
    )
    d = problem.to_dict()
    assert [0, 1] in d["restricted_cells"]
    assert [0, 1] in d["prohibited_assignments"]
    assert d["restricted_cells"] == [[0, 1]]


def test_assignment_problem_legacy_attribute_alias():
    problem = AssignmentProblem(cost_matrix=[[1, 2], [3, 4]])
    problem.prohibited_assignments = {(1, 0)}
    assert problem.restricted_cells == _restricted([[1, 0]])
    problem2 = AssignmentProblem(
        cost_matrix=[[1, 2], [3, 4]], restricted_cells=[[0, 0]]
    )
    assert problem2.prohibited_assignments == _restricted([[0, 0]])


def test_what_if_with_restricted_cells():
    original = solver.solve(cost_matrix=[[1, 2], [3, 4]])
    # Optimal [[1,2],[3,4]] cost: min(1+4, 2+3) = 5.
    assert original["final_cost"] == pytest.approx(5)
    comparison = solver.solve_what_if(
        original, restricted_cells=[[0, 1], [1, 0]], changes_applied=["Restrict (0,1)"]
    )
    assert comparison["success"]
    assert (0, 1) in comparison["problem"].restricted_cells
    assert (1, 0) in comparison["problem"].restricted_cells
    # With both off-diagonal cells restricted, only the diagonal is feasible (5).
    assert comparison["final_cost"] == pytest.approx(5)
    assert comparison["what_if_comparison"].cost_changed is False


def test_hungarian_direct_with_restricted_cells():
    problem = AssignmentProblem(
        cost_matrix=[[1, 2], [3, 4]], restricted_cells=_restricted([[0, 0]])
    )
    result = solve_hungarian(problem)
    assert result.is_optimal
    selected = {(a["row"], a["col"]) for a in result.assignments}
    assert (0, 0) not in selected
    # Only feasible pairing with (0,0) restricted: (0,1)+(1,0) = 5.
    assert result.total_cost == pytest.approx(5)
    assert all(a["is_restricted"] is False for a in result.assignments)


def test_zero_cost_allowed_cell_chosen_over_restricted():
    """Where 0 is allowed it must be used; restricted cells never anchor a 0."""
    cost = [
        [0, 100],   # (0,0) allowed zero
        [100, 0],   # (1,1) allowed zero
    ]
    # Restrict (0,1) and (1,0) so the natural zero assignment is (0,0)+(1,1).
    result = solver.solve(cost_matrix=cost, restricted_cells=[[0, 1], [1, 0]])
    assert result["success"]
    assert result["final_cost"] == pytest.approx(0)
    selected = {(a["row"], a["col"]) for a in result["result"].assignments}
    assert selected == _restricted([[0, 0], [1, 1]])


def test_no_restricted_cell_in_final_verification_clean():
    result = solver.solve(cost_matrix=[[1, 2], [3, 4]], restricted_cells=[[1, 1]])
    assert result["verification"]["passed"]
    assert result["verification"]["issues"] == []
    computed = result["verification"]["computed_cost"]
    assert computed == result["final_cost"]
    for a in result["result"].assignments:
        assert a["original_cost"] < 1e12