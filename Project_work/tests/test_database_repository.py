"""Tests for the database repository layer.

These tests run against an in-memory SQLite database so they are independent
of a live MySQL server. The same ORM models work with MySQL when configured.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database.repository import Repository


@pytest.fixture(autouse=True)
def sqlite_db(monkeypatch):
    """Replace the global engine/session with an in-memory SQLite DB."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr("database.repository.get_session", TestSession)
    monkeypatch.setattr("database.connection._engine", engine)
    return TestSession


def test_save_and_get_transportation_problem():
    repo = Repository()
    pid = repo.save_transportation_problem(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        name="Test Problem",
    )
    assert pid is not None
    problems = repo.get_transportation_problems()
    assert len(problems) == 1
    assert problems[0]["name"] == "Test Problem"
    assert problems[0]["num_sources"] == 2
    assert problems[0]["is_balanced"] is True


def test_save_and_get_transportation_problem_with_restricted_cells():
    repo = Repository()
    pid = repo.save_transportation_problem(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        name="Restricted",
        restricted_cells=[[0, 1], [1, 0]],
    )
    assert pid is not None
    prob = repo.get_transportation_problem(pid)
    assert prob["restricted_cells"] == [[0, 1], [1, 0]]


def test_save_transportation_solution():
    repo = Repository()
    pid = repo.save_transportation_problem(
        cost_matrix=[[3, 1], [2, 6]], supply=[5, 6], demand=[5, 6],
    )
    solution_data = {
        "problem": None,
        "balanced_problem": None,
        "initial_solution": type("S", (), {
            "allocation": [[5, 0], [0, 6]],
            "total_cost": 15,
        })(),
        "optimized_solution": type("O", (), {
            "allocation": [[0, 5], [5, 1]],
            "total_cost": 16,
            "is_optimal": True,
            "iterations": [],
        })(),
        "events": [{"operation": "complete", "explanation": "done"}],
        "verification": {"passed": True, "issues": []},
    }
    sid = repo.save_transportation_solution(pid, "Vogel's Approximation Method", solution_data)
    assert sid is not None
    sol = repo.get_transportation_solution(sid)
    assert sol is not None
    assert sol["method"] == "Vogel's Approximation Method"
    assert sol["initial_total_cost"] == 15
    assert sol["is_optimal"] is True


def test_save_assignment_problem_and_solution():
    repo = Repository()
    pid = repo.save_assignment_problem(
        cost_matrix=[[2, 3], [3, 2]],
        problem_type="Minimization",
    )
    assert pid is not None
    problems = repo.get_assignment_problems()
    assert len(problems) == 1
    assert problems[0]["problem_type"] == "Minimization"

    result_type = type("R", (), {
        "assignments": [{
            "row": 0, "col": 1, "row_name": "Worker 1", "col_name": "Job 2",
            "original_cost": 3, "reduced_cost": 0,
        }],
        "total_cost": 4.0,
        "final_matrix": [[0, 1], [1, 0]],
        "steps": [],
    })
    solution_data = {
        "result": result_type(),
        "events": [{"operation": "complete", "explanation": "done"}],
        "verification": {"passed": True},
    }
    sid = repo.save_assignment_solution(pid, solution_data)
    assert sid is not None
    sol = repo.get_assignment_solution(sid)
    assert sol is not None
    assert sol["total_cost"] == 4.0


def test_save_assignment_problem_with_restricted_cells_round_trip():
    repo = Repository()
    pid = repo.save_assignment_problem(
        cost_matrix=[[3, 1], [2, 6]],
        problem_type="Minimization",
        row_names=["A", "B"],
        col_names=["X", "Y"],
        restricted_cells=[[0, 1], [1, 0]],
    )
    assert pid is not None
    prob = repo.get_assignment_problem(pid)
    assert prob["restricted_cells"] == [[0, 1], [1, 0]]
    assert prob["row_names"] == ["A", "B"]
    assert prob["col_names"] == ["X", "Y"]


def test_delete_transportation_problem():
    repo = Repository()
    pid = repo.save_transportation_problem(
        cost_matrix=[[1]], supply=[1], demand=[1],
    )
    assert repo.delete_transportation_problem(pid) is True
    assert repo.get_transportation_problems() == []


def test_delete_nonexistent_returns_false():
    repo = Repository()
    assert repo.delete_transportation_problem(99999) is False


def test_connection_url_uses_mysql():
    """The production connection string must point to MySQL (not SQLite)."""
    import os
    from database.connection import get_database_url
    url = get_database_url()
    assert "mysql" in url.lower()
    assert "pymysql" in url.lower()
