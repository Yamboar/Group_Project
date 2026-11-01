from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AssignmentProblemType(Enum):
    MINIMIZATION = "Minimization"
    MAXIMIZATION = "Maximization"


@dataclass
class AssignmentProblem:
    cost_matrix: List[List[float]]
    problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION
    row_names: Optional[List[str]] = None
    col_names: Optional[List[str]] = None
    num_rows: int = 0
    num_cols: int = 0

    def __post_init__(self):
        self.num_rows = len(self.cost_matrix)
        self.num_cols = len(self.cost_matrix[0]) if self.num_rows > 0 else 0
        if self.row_names is None:
            self.row_names = [f"Worker {i+1}" for i in range(self.num_rows)]
        if self.col_names is None:
            self.col_names = [f"Job {j+1}" for j in range(self.num_cols)]


@dataclass
class BalancedAssignmentProblem:
    original_problem: AssignmentProblem
    cost_matrix: List[List[float]]
    row_names: List[str]
    col_names: List[str]
    dummy_rows_added: int = 0
    dummy_cols_added: int = 0
    transformed_for_minimization: bool = False
    original_matrix_for_cost: List[List[float]] = field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0

    def __post_init__(self):
        self.num_rows = len(self.cost_matrix)
        self.num_cols = len(self.cost_matrix[0]) if self.num_rows > 0 else 0


@dataclass
class HungarianStep:
    step_number: int
    operation: str
    matrix_before: List[List[float]]
    matrix_after: List[List[float]]
    lines_covering_zeros: Optional[List[Any]] = None
    min_uncovered: Optional[float] = None
    explanation: str = ""


@dataclass
class AssignmentResult:
    assignments: List[Dict[str, Any]]
    total_cost: float
    original_total_cost: float
    steps: List[HungarianStep]
    final_matrix: List[List[float]]
    is_optimal: bool
    events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AssignmentSolution:
    problem: AssignmentProblem
    balanced_problem: Optional[BalancedAssignmentProblem]
    result: AssignmentResult
    verification_passed: bool
    verification_details: Dict[str, Any]
