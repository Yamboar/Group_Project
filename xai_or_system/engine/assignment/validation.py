from typing import List, Tuple, Optional
from engine.assignment.models import AssignmentProblem, AssignmentProblemType


class AssignmentValidationError(Exception):
    """Custom exception for assignment problem validation errors."""
    pass


def validate_assignment_problem(
    cost_matrix: List[List[float]],
    row_names: Optional[List[str]] = None,
    col_names: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate an assignment problem input.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []

    if not cost_matrix:
        errors.append("Cost matrix is empty.")
        return False, errors

    if not isinstance(cost_matrix, list):
        errors.append("Cost matrix must be a list of lists.")
        return False, errors

    num_rows = len(cost_matrix)

    for i, row in enumerate(cost_matrix):
        if not isinstance(row, list):
            errors.append(f"Row {i} is not a list.")
            continue
        for j, val in enumerate(row):
            if not isinstance(val, (int, float)):
                errors.append(f"Cell [{i}][{j}] = '{val}' is not numeric.")

    if len(cost_matrix) == 0:
        return False, errors

    num_cols = len(cost_matrix[0])
    for i, row in enumerate(cost_matrix):
        if len(row) != num_cols:
            errors.append(
                f"Row {i} has {len(row)} columns, but row 0 has {num_cols}. "
                f"All rows must have the same number of columns."
            )
            return False, errors

    if row_names and len(row_names) != num_rows:
        errors.append(
            f"Row names has {len(row_names)} entries but matrix has {num_rows} rows."
        )
    if col_names and len(col_names) != num_cols:
        errors.append(
            f"Column names has {len(col_names)} entries but matrix has {num_cols} columns."
        )

    return len(errors) == 0, errors


def create_assignment_problem(
    cost_matrix: List[List[float]],
    row_names: Optional[List[str]] = None,
    col_names: Optional[List[str]] = None,
    problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION,
) -> AssignmentProblem:
    """Create a validated AssignmentProblem or raise an error."""
    is_valid, errors = validate_assignment_problem(cost_matrix, row_names, col_names)
    if not is_valid:
        raise AssignmentValidationError(
            "Assignment problem validation failed:\n" + "\n".join(errors)
        )
    return AssignmentProblem(
        cost_matrix=cost_matrix,
        problem_type=problem_type,
        row_names=row_names,
        col_names=col_names,
    )
