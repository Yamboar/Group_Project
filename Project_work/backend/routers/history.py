"""FastAPI router for saved problems / solution history endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from backend.schemas import (
    TransportationHistoryItem,
    AssignmentHistoryItem,
    TransportSolutionDetail,
    AssignmentSolutionDetail,
)

from database.repository import Repository

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
)


def _get_repo() -> Repository:
    try:
        return Repository()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database is not available: {e}",
        )


@router.get("/transportation", response_model=List[TransportationHistoryItem])
def get_transportation_history() -> List[Dict[str, Any]]:
    """List all saved transportation problems (metadata only)."""
    repo = _get_repo()
    return repo.get_transportation_problems()


@router.get("/transportation/{problem_id}", response_model=TransportationHistoryItem)
def get_transportation_problem_detail(problem_id: int) -> Dict[str, Any]:
    """Get metadata for a specific transportation problem."""
    repo = _get_repo()
    problems = repo.get_transportation_problems()
    match = [p for p in problems if p["id"] == problem_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"Transportation problem {problem_id} not found.")
    return match[0]


@router.delete("/transportation/{problem_id}")
def delete_transportation_problem(problem_id: int) -> Dict[str, Any]:
    """Delete a saved transportation problem and its solutions."""
    repo = _get_repo()
    deleted = repo.delete_transportation_problem(problem_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Transportation problem {problem_id} not found.")
    return {"deleted": True, "id": problem_id}


@router.get("/assignment", response_model=List[AssignmentHistoryItem])
def get_assignment_history() -> List[Dict[str, Any]]:
    """List all saved assignment problems (metadata only)."""
    repo = _get_repo()
    return repo.get_assignment_problems()


@router.get("/assignment/{problem_id}", response_model=AssignmentHistoryItem)
def get_assignment_problem_detail(problem_id: int) -> Dict[str, Any]:
    """Get metadata for a specific assignment problem."""
    repo = _get_repo()
    problems = repo.get_assignment_problems()
    match = [p for p in problems if p["id"] == problem_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"Assignment problem {problem_id} not found.")
    return match[0]


@router.get("/transportation/{problem_id}/details")
def get_transportation_problem_details(problem_id: int) -> Dict[str, Any]:
    """Get the full saved transportation problem and all its solutions."""
    repo = _get_repo()
    problem = repo.get_transportation_problem(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail=f"Transportation problem {problem_id} not found.")
    return {"problem": problem, "solutions": repo.get_transportation_solutions(problem_id)}


@router.get("/assignment/{problem_id}/details")
def get_assignment_problem_details(problem_id: int) -> Dict[str, Any]:
    """Get the full saved assignment problem and all its solutions."""
    repo = _get_repo()
    problem = repo.get_assignment_problem(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail=f"Assignment problem {problem_id} not found.")
    return {"problem": problem, "solutions": repo.get_assignment_solutions(problem_id)}


@router.delete("/assignment/{problem_id}")
def delete_assignment_problem(problem_id: int) -> Dict[str, Any]:
    """Delete a saved assignment problem and its solutions."""
    repo = _get_repo()
    deleted = repo.delete_assignment_problem(problem_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Assignment problem {problem_id} not found.")
    return {"deleted": True, "id": problem_id}


# ----- Solution detail endpoints -----
# NOTE: These use distinct prefixes (transportation-solutions / assignment-solutions)
# to avoid FastAPI matching "/transportation/solutions/{id}" as
# "/transportation/{problem_id}" where problem_id = "solutions".

@router.get("/transportation-solutions/{solution_id}", response_model=TransportSolutionDetail)
def get_transportation_solution(solution_id: int) -> Dict[str, Any]:
    """Get details for a saved transportation solution."""
    repo = _get_repo()
    sol = repo.get_transportation_solution(solution_id)
    if not sol:
        raise HTTPException(status_code=404, detail=f"Transportation solution {solution_id} not found.")
    return sol


@router.get("/assignment-solutions/{solution_id}", response_model=AssignmentSolutionDetail)
def get_assignment_solution(solution_id: int) -> Dict[str, Any]:
    """Get details for a saved assignment solution."""
    repo = _get_repo()
    sol = repo.get_assignment_solution(solution_id)
    if not sol:
        raise HTTPException(status_code=404, detail=f"Assignment solution {solution_id} not found.")
    return sol
