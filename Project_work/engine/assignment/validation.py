from typing import List, Tuple, Optional, Set
from engine.assignment.models import AssignmentProblem, AssignmentProblemType


class AssignmentValidationError(Exception):
    """Custom exception for assignment problem validation errors."""
    pass


def _check_feasibility(
    num_rows: int,
    num_cols: int,
    restricted: Set[Tuple[int, int]],
) -> Tuple[bool, List[str]]:
    """
    Verify a complete one-to-one assignment is possible with the current
    restrictions (bipartite maximum-matching check, Kuhn's algorithm).

    The check runs on the balanced (square) matrix so dummy workers/jobs,
    which are never restricted, are taken into account. If the matching size
    equals the matrix size n, a feasible assignment exists.

    Returns (is_feasible, list_of_issue_messages).
    """
    n = max(num_rows, num_cols)
    issues: List[str] = []

    def available(i: int, j: int) -> bool:
        # Dummy rows/columns are always available and never restricted.
        if i >= num_rows or j >= num_cols:
            return True
        return (i, j) not in restricted

    # Structural checks: every real worker needs at least one reachable job.
    for i in range(num_rows):
        if not any(available(i, j) for j in range(num_cols)):
            issues.append(
                f"No feasible assignment exists with the current restrictions. "
                f"Worker {i+1} cannot be assigned to any available job — every "
                f"cell in row {i+1} is Restricted."
            )

    for j in range(num_cols):
        if not any(available(i, j) for i in range(num_rows)):
            issues.append(
                f"No feasible assignment exists with the current restrictions. "
                f"Job {j+1} cannot be assigned to any available worker — every "
                f"cell in column {j+1} is Restricted."
            )

    if issues:
        return False, issues

    row_match = [-1] * n
    col_match = [-1] * n

    def try_augment(row: int, visited: List[bool]) -> bool:
        for col in range(n):
            if visited[col]:
                continue
            if not available(row, col):
                continue
            visited[col] = True
            if col_match[col] == -1 or try_augment(col_match[col], visited):
                row_match[row] = col
                col_match[col] = row
                return True
        return False

    for i in range(n):
        visited = [False] * n
        try_augment(i, visited)

    matched = sum(1 for x in row_match if x != -1)
    if matched < n:
        issues.append(
            f"No feasible assignment exists with the current restrictions. "
            f"A group of workers can be assigned to at most {matched} of the "
            f"{n} required job(s) because too many cells are Restricted. "
            f"Unrestrict some cells so every worker can be assigned to an "
            f"available job."
        )

    return len(issues) == 0, issues


def validate_assignment_problem(
    cost_matrix: List[List[float]],
    row_names: Optional[List[str]] = None,
    col_names: Optional[List[str]] = None,
    restricted_cells: Optional[Set[Tuple[int, int]]] = None,
    prohibited_assignments: Optional[Set[Tuple[int, int]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate an assignment problem input.

    Cell semantics:
    - 0  → a valid, allowed assignment with zero cost.
    - >0 → a valid allowed assignment with positive cost.
    - <0 → invalid input for the standard cost model (rejected with guidance
      to mark the cell as Restricted instead).
    - None/blank → missing input (rejected with guidance to enter a valid cost
      or mark the cell as Restricted).
    - Restricted cells are exempt from value validation: their cost is
      irrelevant because they can never be assigned.

    Checks:
    - Non-empty matrix, uniform row lengths.
    - Values numeric and >= 0 (restricted cells exempt).
    - Name dimension / duplicate checks.
    - Restricted-cell range check.
    - Feasibility (complete one-to-one assignment possible) via bipartite
      matching on the balanced matrix.

    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    if not isinstance(cost_matrix, list) or not cost_matrix:
        errors.append("Cost matrix is empty.")
        return False, errors

    num_rows = len(cost_matrix)

    restricted: Set[Tuple[int, int]] = set(restricted_cells or set())
    if prohibited_assignments:
        restricted |= set(prohibited_assignments)

    for i, row in enumerate(cost_matrix):
        if not isinstance(row, list):
            errors.append(f"Row {i+1} is not a list.")
            return False, errors
        for j, val in enumerate(row):
            if (i, j) in restricted:
                continue  # restricted cells are exempt from value validation
            if val is None:
                errors.append(
                    f"Cell [{i+1}][{j+1}] is blank. Assignment costs must be 0 or "
                    f"greater. Enter a valid cost, or mark the cell as Restricted "
                    f"if this worker cannot perform that job."
                )
            elif isinstance(val, bool) or not isinstance(val, (int, float)):
                errors.append(
                    f"Cell [{i+1}][{j+1}] = '{val}' is not numeric. Enter a cost of 0 "
                    f"or greater, or mark the cell as Restricted if this worker "
                    f"cannot perform that job."
                )
            elif val < 0:
                errors.append(
                    f"Cell [{i+1}][{j+1}] = {val} is negative. Assignment costs must "
                    f"be 0 or greater. If this worker cannot perform that job, mark "
                    f"the cell as Restricted instead of entering a negative value."
                )

    if errors:
        return False, errors

    num_cols = len(cost_matrix[0])
    if num_cols == 0:
        errors.append("Cost matrix row 1 is empty.")
        return False, errors

    for i, row in enumerate(cost_matrix):
        if len(row) != num_cols:
            errors.append(
                f"Row {i+1} has {len(row)} columns but row 1 has {num_cols}. "
                f"All rows must have the same number of columns."
            )
            return False, errors

    # Name dimension checks.
    if row_names is not None and len(row_names) != num_rows:
        errors.append(
            f"Row names has {len(row_names)} entries but matrix has {num_rows} rows."
        )
    if col_names is not None and len(col_names) != num_cols:
        errors.append(
            f"Column names has {len(col_names)} entries but matrix has {num_cols} columns."
        )

    # Duplicate name checks.
    if row_names is not None:
        seen: dict = {}
        for idx, name in enumerate(row_names):
            if name in seen:
                errors.append(
                    f"Duplicate row name '{name}' at positions {seen[name]+1} and {idx+1}."
                )
            seen[name] = idx
    if col_names is not None:
        seen = {}
        for idx, name in enumerate(col_names):
            if name in seen:
                errors.append(
                    f"Duplicate column name '{name}' at positions {seen[name]+1} and {idx+1}."
                )
            seen[name] = idx

    if errors:
        return False, errors

    # Restricted cells range check + feasibility.
    if restricted:
        bad = [
            (i, j) for (i, j) in restricted
            if i < 0 or i >= num_rows or j < 0 or j >= num_cols
        ]
        if bad:
            errors.append(
                f"Restricted cells contain out-of-range indices: {bad}. "
                f"Valid range: rows 0..{num_rows-1}, cols 0..{num_cols-1}."
            )
            return False, errors

        feasible, feas_issues = _check_feasibility(num_rows, num_cols, restricted)
        if not feasible:
            errors.extend(feas_issues)

    return len(errors) == 0, errors


def create_assignment_problem(
    cost_matrix: List[List[float]],
    row_names: Optional[List[str]] = None,
    col_names: Optional[List[str]] = None,
    problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION,
    restricted_cells: Optional[Set[Tuple[int, int]]] = None,
    prohibited_assignments: Optional[Set[Tuple[int, int]]] = None,
) -> AssignmentProblem:
    """Create a validated AssignmentProblem or raise an error."""
    is_valid, errors = validate_assignment_problem(
        cost_matrix, row_names, col_names, restricted_cells, prohibited_assignments
    )
    if not is_valid:
        raise AssignmentValidationError(
            "Assignment problem validation failed:\n" + "\n".join(errors)
        )
    merged = set(restricted_cells or set())
    if prohibited_assignments:
        merged |= set(prohibited_assignments)
    return AssignmentProblem(
        cost_matrix=cost_matrix,
        problem_type=problem_type,
        row_names=row_names,
        col_names=col_names,
        restricted_cells=merged,
    )