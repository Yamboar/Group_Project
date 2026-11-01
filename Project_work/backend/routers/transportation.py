"""FastAPI router for transportation problem endpoints."""
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from backend.schemas import (
    TransportationSolveRequest,
    SolveResponse,
    ExplanationResponse,
)
from backend.serializers import (
    serialize_transportation_solution,
    serialize_solution_explanation,
)

from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod
from xai.explanation_engine import ExplanationEngine
from backend.objective import resolve_direction, objective_event
from database.repository import Repository

router = APIRouter(
    prefix="/api/transportation",
    tags=["transportation"],
)

solver = TransportationSolver()
explanation_engine = ExplanationEngine()
repo = Repository()

METHOD_MAP = {
    "North-West Corner Method": TransportationMethod.NORTH_WEST,
    "Least Cost Method": TransportationMethod.LEAST_COST,
    "Vogel's Approximation Method": TransportationMethod.VOGEL,
}


def _attach_objective(result: dict, objective) -> dict:
    """Resolve the confirmed objective and record an auditable event.

    The transportation engine is minimisation-only, so the solved direction is
    always 'minimise'; the user's stated intent is preserved in the trail.
    Returns the possibly-warning string, appended to result warnings.
    """
    objective_dict = objective.model_dump() if objective is not None else None
    direction, meta, warning = resolve_direction(
        objective_dict, fallback="minimise", locked_to="minimise"
    )
    result["objective_selection"] = {
        **meta,
        "resolved_direction": direction,
        "algo_locked": True,
    }
    result["events"].insert(
        0,
        objective_event(meta, direction, algo_locked=True),
    )
    return warning


def _persist_solution(request: TransportationSolveRequest, result: dict) -> None:
    """Persist the problem and its solution to the database (best-effort).

    Raises on failure so the caller can surface a warning without failing the
    solve itself. The stored events already capture the objective selection.
    """
    problem_id = repo.save_transportation_problem(
        cost_matrix=request.cost_matrix,
        supply=request.supply,
        demand=request.demand,
        source_names=request.source_names,
        dest_names=request.dest_names,
        name=None,
        restricted_cells=request.restricted_cells,
    )
    repo.save_transportation_solution(problem_id, request.method, result)


@router.post("/solve", response_model=SolveResponse)
def solve_transportation(request: TransportationSolveRequest) -> dict:
    """Solve a transportation problem end-to-end with explanations."""
    if request.method not in METHOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown method '{request.method}'. Must be one of: "
                f"'North-West Corner Method', 'Least Cost Method', "
                f"\"Vogel's Approximation Method\"."
            ),
        )

    method = METHOD_MAP[request.method]

    result = solver.solve(
        cost_matrix=request.cost_matrix,
        supply=request.supply,
        demand=request.demand,
        method=method,
        source_names=request.source_names,
        dest_names=request.dest_names,
        optimize=request.optimize,
        restricted_cells=request.restricted_cells,
        prohibited_routes=request.restricted_routes,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": result.get("errors", []),
                "message": "Transportation problem validation failed.",
            },
        )

    warning = _attach_objective(result, request.objective)
    if warning:
        result["warnings"].append(warning)

    try:
        _persist_solution(request, result)
    except Exception as e:  # noqa: BLE001 - persistence must not break solving
        result["warnings"].append(f"Could not save solution to database: {e}")

    return serialize_transportation_solution(result)


@router.post("/explain", response_model=ExplanationResponse)
def explain_transportation(request: TransportationSolveRequest) -> dict:
    """Solve a transportation problem and return full XAI explanations."""
    if request.method not in METHOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown method '{request.method}'. Must be one of: "
                f"'North-West Corner Method', 'Least Cost Method', "
                f"\"Vogel's Approximation Method\"."
            ),
        )

    method = METHOD_MAP[request.method]

    result = solver.solve(
        cost_matrix=request.cost_matrix,
        supply=request.supply,
        demand=request.demand,
        method=method,
        source_names=request.source_names,
        dest_names=request.dest_names,
        optimize=request.optimize,
        restricted_cells=request.restricted_cells,
        prohibited_routes=request.restricted_routes,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": result.get("errors", []),
                "message": "Transportation problem validation failed.",
            },
        )

    warning = _attach_objective(result, request.objective)
    if warning:
        result["warnings"].append(warning)

    explanation = explanation_engine.generate_transportation_explanation(result)
    return serialize_solution_explanation(explanation)
