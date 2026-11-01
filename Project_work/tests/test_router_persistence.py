"""Tests for solve-router persistence wiring.

Solving must persist the problem + solution to the database when available, and
must degrade gracefully (return the result with a warning) when the database is
unreachable instead of failing the solve.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database.repository import Repository

from backend.schemas import TransportationSolveRequest, AssignmentSolveRequest
from backend.routers import transportation as transport_router
from backend.routers import assignment as assignment_router
from backend.routers import history as history_router


@pytest.fixture(autouse=True)
def sqlite_db(monkeypatch):
    """Replace the global engine/session with an in-memory SQLite DB."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr("database.repository.get_session", TestSession)
    monkeypatch.setattr("database.connection._engine", engine)
    return TestSession


def _transport_request():
    return TransportationSolveRequest(
        cost_matrix=[[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        supply=[3, 3, 4],
        demand=[4, 3, 3],
        method="Vogel's Approximation Method",
        optimize=True,
    )


def test_transportation_solve_persists_record():
    repo = Repository()
    result = transport_router.solve_transportation(_transport_request())
    assert result["success"] is True
    problems = repo.get_transportation_problems()
    assert len(problems) == 1
    assert problems[0]["num_sources"] == 3
    assert problems[0]["is_balanced"] is True
    assert problems[0]["created_at"] is not None


def test_transportation_solve_survives_db_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("MySQL is down")

    monkeypatch.setattr(
        transport_router.repo, "save_transportation_problem", boom
    )
    result = transport_router.solve_transportation(_transport_request())
    assert result["success"] is True
    assert any("database" in w.lower() for w in result["warnings"])


def test_assignment_solve_persists_record():
    repo = Repository()
    request = AssignmentSolveRequest(
        cost_matrix=[[4, 1, 3], [2, 0, 5], [3, 2, 2]],
        problem_type="Minimization",
    )
    result = assignment_router.solve_assignment(request)
    assert result["success"] is True
    problems = repo.get_assignment_problems()
    assert len(problems) == 1
    assert problems[0]["num_rows"] == 3
    assert problems[0]["num_cols"] == 3


def test_assignment_solve_survives_db_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("MySQL is down")

    monkeypatch.setattr(
        assignment_router.repo, "save_assignment_problem", boom
    )
    request = AssignmentSolveRequest(
        cost_matrix=[[4, 1, 3], [2, 0, 5], [3, 2, 2]],
        problem_type="Minimization",
    )
    result = assignment_router.solve_assignment(request)
    assert result["success"] is True
    assert any("database" in w.lower() for w in result["warnings"])


def test_transportation_details_endpoint_returns_data():
    repo = Repository()
    transport_router.solve_transportation(_transport_request())
    problem_id = repo.get_transportation_problems()[0]["id"]
    details = history_router.get_transportation_problem_details(problem_id)
    assert details["problem"]["id"] == problem_id
    assert details["problem"]["cost_matrix"] == [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    assert len(details["solutions"]) == 1
    sol = details["solutions"][0]
    assert sol["method"] == "Vogel's Approximation Method"
    assert sol["is_optimal"] is True
    assert sol["verification_passed"] is True


def test_assignment_details_endpoint_returns_data():
    repo = Repository()
    request = AssignmentSolveRequest(
        cost_matrix=[[4, 1, 3], [2, 0, 5], [3, 2, 2]],
        problem_type="Minimization",
    )
    assignment_router.solve_assignment(request)
    problem_id = repo.get_assignment_problems()[0]["id"]
    details = history_router.get_assignment_problem_details(problem_id)
    assert details["problem"]["id"] == problem_id
    assert details["problem"]["cost_matrix"] == [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
    assert len(details["solutions"]) == 1
    assert details["solutions"][0]["total_cost"] >= 0
    assert details["solutions"][0]["verification_passed"] is True


def test_transportation_details_endpoint_404():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        history_router.get_transportation_problem_details(99999)
    assert exc.value.status_code == 404
