"""FastAPI router for assignment problem endpoints."""
from fastapi import APIRouter, HTTPException

from backend.schemas import AssignmentSolveRequest, SolveResponse, ExplanationResponse
from backend.serializers import serialize_assignment_solution, serialize_solution_explanation

from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType
from xai.explanation_engine import ExplanationEngine
from backend.objective import resolve_direction, objective_event
from database.repository import Repository

router = APIRouter(
    prefix="/api/assignment",
    tags=["assignment"],
)

solver = AssignmentSolver()
explanation_engine = ExplanationEngine()
repo = Repository()


def _parse_problem_type(problem_type: str) -> AssignmentProblemType:
    pt = problem_type.strip().lower()
    if pt in ("minimization", "min"):
        return AssignmentProblemType.MINIMIZATION
    if pt in ("maximization", "max"):
        return AssignmentProblemType.MAXIMIZATION
    raise HTTPException(
        status_code=400,
        detail=f"Unknown problem_type '{problem_type}'. Must be 'Minimization' or 'Maximization'.",
    )


def _resolve_objective(request: AssignmentSolveRequest):
    """Resolve the guided objective into a problem_type and record the trail.

    When a guided `objective` is provided, its intent determines the solve
    direction (maximise = 'maximisation', minimise = 'minimisation'). Otherwise
    fall back to the legacy `problem_type` field.
    Returns (problem_type, objective_metadata, warning_or_none).
    """
    objective_dict = request.objective.model_dump() if request.objective is not None else None
    if not objective_dict:
        ptype = _parse_problem_type(request.problem_type)
        direction = (
            "maximise"
            if ptype == AssignmentProblemType.MAXIMIZATION
            else "minimise"
        )
        return ptype, direction, None, None

    direction, meta, warning = resolve_direction(
        objective_dict, fallback="minimise", locked_to=None
    )
    problem_type = (
        AssignmentProblemType.MAXIMIZATION
        if direction == "maximise"
        else AssignmentProblemType.MINIMIZATION
    )
    return problem_type, direction, meta, warning


def _attach_objective(result: dict, meta: dict, direction: str) -> None:
    if meta is None:
        return
    result["objective_selection"] = {**meta, "resolved_direction": direction}
    result["events"].insert(
        0,
        objective_event(meta, direction, algo_locked=False),
    )


def _persist_solution(request: AssignmentSolveRequest, result: dict) -> None:
    """Persist the problem and its solution to the database (best-effort).

    Raises on failure so the caller can surface a warning without failing the
    solve itself. The stored events already capture the objective selection.
    """
    restricted = list(request.restricted_cells or [])
    if request.prohibited_assignments:
        for cell in request.prohibited_assignments:
            if cell not in restricted:
                restricted.append(cell)

    problem_id = repo.save_assignment_problem(
        cost_matrix=request.cost_matrix,
        problem_type=request.problem_type,
        row_names=request.row_names,
        col_names=request.col_names,
        restricted_cells=restricted,
        name=None,
    )
    repo.save_assignment_solution(problem_id, result)


@router.post("/solve", response_model=SolveResponse)
def solve_assignment(request: AssignmentSolveRequest) -> dict:
    """Solve an assignment problem with the Hungarian Method."""
    problem_type, direction, meta, warning = _resolve_objective(request)

    result = solver.solve(
        cost_matrix=request.cost_matrix,
        row_names=request.row_names,
        col_names=request.col_names,
        problem_type=problem_type,
        restricted_cells=request.restricted_cells,
        prohibited_assignments=request.prohibited_assignments,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": result.get("errors", []),
                "message": "Assignment problem validation failed.",
            },
        )

    if meta is not None:
        _attach_objective(result, meta, direction)
    if warning:
        result["warnings"].append(warning)

    try:
        _persist_solution(request, result)
    except Exception as e:  # noqa: BLE001 - persistence must not break solving
        result["warnings"].append(f"Could not save solution to database: {e}")

    return serialize_assignment_solution(result)


@router.post("/explain", response_model=ExplanationResponse)
def explain_assignment(request: AssignmentSolveRequest) -> dict:
    """Solve an assignment problem and return full XAI explanations."""
    problem_type, direction, meta, warning = _resolve_objective(request)

    result = solver.solve(
        cost_matrix=request.cost_matrix,
        row_names=request.row_names,
        col_names=request.col_names,
        problem_type=problem_type,
        restricted_cells=request.restricted_cells,
        prohibited_assignments=request.prohibited_assignments,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": result.get("errors", []),
                "message": "Assignment problem validation failed.",
            },
        )

    if meta is not None:
        _attach_objective(result, meta, direction)
    if warning:
        result["warnings"].append(warning)

    explanation = explanation_engine.generate_assignment_explanation(result)
    return serialize_solution_explanation(explanation)
