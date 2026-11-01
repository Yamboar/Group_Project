import pytest
from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType


def test_assignment_solver_minimization():
    solver = AssignmentSolver()
    result = solver.solve(
        cost_matrix=[[2, 3], [3, 2]],
    )
    assert result["success"]
    assert result["verification"]["passed"]
    assert result["final_cost"] == pytest.approx(4)


def test_assignment_solver_maximization():
    solver = AssignmentSolver()
    result = solver.solve(
        cost_matrix=[[10, 5], [5, 10]],
        problem_type=AssignmentProblemType.MAXIMIZATION,
    )
    assert result["success"]
    assert result["final_cost"] == pytest.approx(20)


def test_assignment_solver_rectangular():
    solver = AssignmentSolver()
    result = solver.solve(
        cost_matrix=[[4, 6, 8], [6, 8, 6]],
    )
    assert result["success"]
    assert result["verification"]["passed"]


def test_assignment_solver_invalid():
    solver = AssignmentSolver()
    result = solver.solve(cost_matrix=[["a", "b"], [1, 2]])
    assert not result["success"]
    assert len(result["errors"]) > 0


def test_assignment_solver_empty():
    solver = AssignmentSolver()
    result = solver.solve(cost_matrix=[])
    assert not result["success"]


def test_assignment_solver_one_to_one():
    solver = AssignmentSolver()
    result = solver.solve(
        cost_matrix=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
    )
    assert result["success"]
    assignments = result["result"].assignments
    rows = [a["row"] for a in assignments]
    cols = [a["col"] for a in assignments]
    assert len(set(rows)) == 3
    assert len(set(cols)) == 3
