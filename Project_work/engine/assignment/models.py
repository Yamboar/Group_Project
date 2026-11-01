from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum

# Sentinel cost used ONLY inside the Hungarian working matrix to keep restricted
# cells out of the reduction / zero / covering / matching steps. Restricted
# cells are tracked separately (restricted_cells) and are NEVER encoded with
# this value in the user's cost matrix or in any reported matrix.
PROHIBITED_COST = 1e15


class AssignmentProblemType(Enum):
    MINIMIZATION = "Minimization"
    MAXIMIZATION = "Maximization"


@dataclass
class AssignmentProblem:
    cost_matrix: List[List[float]]
    problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION
    row_names: Optional[List[str]] = None
    col_names: Optional[List[str]] = None
    # Set of (row, col) pairs that are Restricted (the worker cannot be assigned
    # to that job). Separate cell state — never represented by a number.
    restricted_cells: Optional[Set[Tuple[int, int]]] = None
    num_rows: int = 0
    num_cols: int = 0

    def __post_init__(self):
        self.num_rows = len(self.cost_matrix)
        self.num_cols = len(self.cost_matrix[0]) if self.num_rows > 0 else 0
        if self.row_names is None:
            self.row_names = [f"Worker {i+1}" for i in range(self.num_rows)]
        if self.col_names is None:
            self.col_names = [f"Job {j+1}" for j in range(self.num_cols)]
        self.restricted_cells = self._coerce_restricted(self.restricted_cells)

    @staticmethod
    def _coerce_restricted(value) -> Set[Tuple[int, int]]:
        """Accept a set of tuples OR a list of [row, col] lists."""
        if not value:
            return set()
        return {
            tuple(cell) if isinstance(cell, (list, tuple)) else cell
            for cell in value
        }

    # Backwards-compatible alias for legacy callers that used `prohibited_assignments`.
    @property
    def prohibited_assignments(self) -> Set[Tuple[int, int]]:
        return self.restricted_cells

    @prohibited_assignments.setter
    def prohibited_assignments(self, value) -> None:
        self.restricted_cells = self._coerce_restricted(value)

    def is_restricted(self, i: int, j: int) -> bool:
        return (i, j) in self.restricted_cells

    def is_prohibited(self, i: int, j: int) -> bool:
        return self.is_restricted(i, j)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "problem_type": self.problem_type.value,
            "row_names": self.row_names,
            "col_names": self.col_names,
            "restricted_cells": [
                list(cell) for cell in self.restricted_cells
            ] if self.restricted_cells else [],
            "prohibited_assignments": [
                list(cell) for cell in self.restricted_cells
            ] if self.restricted_cells else [],
        }


@dataclass
class BalancedAssignmentProblem:
    original_problem: AssignmentProblem
    cost_matrix: List[List[float]]
    row_names: List[str]
    col_names: List[str]
    dummy_rows_added: int = 0
    dummy_cols_added: int = 0
    transformed_for_minimization: bool = False
    # The original (pre-transformation, full balanced-size) cost matrix used
    # to look up true costs when reporting the final assignment.
    original_matrix_for_cost: List[List[float]] = field(default_factory=list)
    # Restricted assignments in the balanced problem's coordinate space.
    restricted_cells: Set[Tuple[int, int]] = field(default_factory=set)
    num_rows: int = 0
    num_cols: int = 0

    def __post_init__(self):
        self.num_rows = len(self.cost_matrix)
        self.num_cols = len(self.cost_matrix[0]) if self.num_rows > 0 else 0

    @property
    def prohibited_assignments(self) -> Set[Tuple[int, int]]:
        return self.restricted_cells

    @prohibited_assignments.setter
    def prohibited_assignments(self, value) -> None:
        self.restricted_cells = AssignmentProblem._coerce_restricted(value)

    def is_restricted(self, i: int, j: int) -> bool:
        return (i, j) in self.restricted_cells

    def is_prohibited(self, i: int, j: int) -> bool:
        return self.is_restricted(i, j)


@dataclass
class HungarianStep:
    step_number: int
    operation: str
    matrix_before: List[List[float]]
    matrix_after: List[List[float]]
    lines_covering_zeros: Optional[List[Any]] = None
    min_uncovered: Optional[float] = None
    explanation: str = ""
    # XAI: three-level explanations
    concise: str = ""
    detailed: str = ""
    technical: str = ""
    # XAI: zeros present in the matrix after this step
    zero_positions: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class AssignmentResult:
    assignments: List[Dict[str, Any]]
    total_cost: float
    original_total_cost: float
    steps: List[HungarianStep]
    final_matrix: List[List[float]]
    is_optimal: bool
    events: List[Dict[str, Any]] = field(default_factory=list)
    # True when alternative assignments exist (multiple zero cells allow
    # a different complete assignment with the same cost).
    has_alternative_optima: bool = False
    alternative_assignment_cells: List[Tuple[int, int]] = field(default_factory=list)
    # Enumeration of ALL optimal assignment plans (perfect matchings on the
    # final reduced matrix's zero cells). number_of_optimal_assignments counts
    # distinct real plans; all_optimal_assignments lists (up to a cap) each plan
    # over the balanced matrix as [(row, col), ...]; optimal_assignments_truncated
    # is True when the listing (or the count) is capped. Classic exam topic and
    # a headline XAI fact ("there are 4 different optimal plans").
    number_of_optimal_assignments: int = 1
    all_optimal_assignments: List[List[Tuple[int, int]]] = field(default_factory=list)
    optimal_assignments_truncated: bool = False
    # False when the count is only a lower bound (heavily rectangular problems
    # with more than the enumeration cap of plans).
    optimal_assignments_count_exact: bool = True


@dataclass
class WhatIfAssignmentResult:
    """Comparison between the original assignment solution and a modified scenario."""
    original_cost: float
    new_cost: float
    cost_changed: bool
    cost_difference: float
    assignment_changed: bool
    changes_applied: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class AssignmentSolution:
    problem: AssignmentProblem
    balanced_problem: Optional[BalancedAssignmentProblem]
    result: AssignmentResult
    verification_passed: bool
    verification_details: Dict[str, Any]
