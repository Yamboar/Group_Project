"""Pydantic request/response schemas for the XAI-OR API."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ObjectiveSelection(BaseModel):
    """Plain-language objective selection captured by the guided UI.

    The user states what the matrix values represent and which way they want the
    system to optimise. The backend converts the confirmed choice into the
    internal MIN/MAX objective and records the full decision trail here so the
    XAI layer can explain the objective, not just the result.
    """
    intent: Optional[str] = Field(
        None,
        description="Final resolved direction the user chose: 'minimise' or 'maximise'.",
    )
    value_type: Optional[str] = Field(
        None,
        description="What the values represent: cost, profit, revenue, time, distance, other.",
    )
    other_description: Optional[str] = Field(
        None,
        description="Free-text description when value_type is 'other'.",
    )
    recommended: Optional[str] = Field(
        None,
        description="Direction the system recommended: 'minimise' or 'maximise'.",
    )
    confirmed: Optional[bool] = Field(
        False,
        description="True if the user confirmed the system's recommendation.",
    )
    overridden: Optional[bool] = Field(
        False,
        description="True if the user overrode the system's recommendation.",
    )


class TransportationSolveRequest(BaseModel):
    cost_matrix: List[List[float]] = Field(..., description="m x n cost matrix")
    supply: List[float] = Field(..., description="Supply for each source, length m")
    demand: List[float] = Field(..., description="Demand for each destination, length n")
    method: str = Field(
        ...,
        description="Initial solution method: 'North-West Corner Method', "
                    "'Least Cost Method', or \"Vogel's Approximation Method\"",
    )
    source_names: Optional[List[str]] = None
    dest_names: Optional[List[str]] = None
    optimize: bool = Field(True, description="Apply Stepping Stone optimization")
    restricted_cells: Optional[List[List[int]]] = Field(
        None,
        description="List of [row, col] pairs (0-indexed) that are restricted: "
                    "routes that cannot be used. These cells are excluded from "
                    "allocation by every method and never contribute to the "
                    "objective. Backwards-compatible alias: restricted_routes.",
    )
    restricted_routes: Optional[List[List[int]]] = Field(
        None,
        description="Legacy alias for restricted_cells (kept for backcompat).",
    )
    objective: Optional[ObjectiveSelection] = None


class AssignmentSolveRequest(BaseModel):
    cost_matrix: List[List[Optional[float]]] = Field(
        ...,
        description="Cost matrix (m x n). 0 is a valid allowed assignment. "
                    "Restricted cells may hold any placeholder value and are "
                    "ignored by the solver.",
    )
    problem_type: str = Field("Minimization", description="'Minimization' or 'Maximization'")
    row_names: Optional[List[str]] = None
    col_names: Optional[List[str]] = None
    restricted_cells: Optional[List[List[int]]] = Field(
        None,
        description="List of [row, col] pairs (0-indexed) that are restricted: "
                    "assignments that cannot be made. These cells are required "
                    "to use and can never appear in the final assignment. "
                    "Backwards-compatible alias: prohibited_assignments.",
    )
    prohibited_assignments: Optional[List[List[int]]] = Field(
        None,
        description="Legacy alias for restricted_cells (kept for backcompat).",
    )
    objective: Optional[ObjectiveSelection] = None


class SolveResponse(BaseModel):
    success: bool
    errors: List[str] = []
    warnings: List[str] = []
    validation: Optional[Dict[str, Any]] = None
    balancing: Optional[Dict[str, Any]] = None
    problem: Optional[Dict[str, Any]] = None
    balanced_problem: Optional[Dict[str, Any]] = None
    initial_solution: Optional[Dict[str, Any]] = None
    optimized_solution: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    final_cost: float = 0.0
    objective_selection: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []


class ExplanationResponse(BaseModel):
    algorithm: str
    problem_type: str
    events: List[Dict[str, Any]] = []
    explanations: List[Dict[str, Any]] = []
    summary: str = ""
    key_decisions: List[str] = []
    optimality_reason: str = ""


class HistoryItem(BaseModel):
    id: int
    name: Optional[str] = None
    created_at: Optional[str] = None


class TransportationHistoryItem(HistoryItem):
    num_sources: int
    num_destinations: int
    is_balanced: bool


class AssignmentHistoryItem(HistoryItem):
    num_rows: int
    num_cols: int
    problem_type: str


class TransportSolutionDetail(BaseModel):
    id: int
    problem_id: int
    method: str
    initial_total_cost: float
    optimized_total_cost: Optional[float] = None
    is_optimized: bool
    is_optimal: bool
    verification_passed: bool
    created_at: Optional[str] = None


class AssignmentSolutionDetail(BaseModel):
    id: int
    problem_id: int
    total_cost: float
    verification_passed: bool
    created_at: Optional[str] = None
