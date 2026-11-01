from typing import List, Dict, Any, Tuple, Optional, Set
from engine.assignment.models import (
    AssignmentProblem,
    BalancedAssignmentProblem,
    AssignmentResult,
    HungarianStep,
    AssignmentProblemType,
)
import copy


def _balance_problem(problem: AssignmentProblem) -> BalancedAssignmentProblem:
    """
    Balance the assignment problem:
    - If rectangular (rows != cols), add dummy rows or columns with zero costs.
    - If maximization, transform to minimization.
    """
    cost_matrix = [row[:] for row in problem.cost_matrix]
    row_names = list(problem.row_names)
    col_names = list(problem.col_names)
    num_rows = problem.num_rows
    num_cols = problem.num_cols
    dummy_rows = 0
    dummy_cols = 0
    transformed = False
    original_for_cost = [row[:] for row in problem.cost_matrix]

    if problem.problem_type == AssignmentProblemType.MAXIMIZATION:
        max_val = max(max(row) for row in cost_matrix)
        cost_matrix = [[max_val - val for val in row] for row in cost_matrix]
        transformed = True

    if num_rows < num_cols:
        diff = num_cols - num_rows
        for _ in range(diff):
            cost_matrix.append([0.0] * num_cols)
            row_names.append(f"Dummy Row {dummy_rows + 1}")
            dummy_rows += 1
    elif num_cols < num_rows:
        diff = num_rows - num_cols
        for i in range(num_rows):
            cost_matrix[i].extend([0.0] * diff)
        for _ in range(diff):
            col_names.append(f"Dummy Col {dummy_cols + 1}")
            dummy_cols += 1

    return BalancedAssignmentProblem(
        original_problem=problem,
        cost_matrix=cost_matrix,
        row_names=row_names,
        col_names=col_names,
        dummy_rows_added=dummy_rows,
        dummy_cols_added=dummy_cols,
        transformed_for_minimization=transformed,
        original_matrix_for_cost=original_for_cost,
        num_rows=len(cost_matrix),
        num_cols=len(cost_matrix[0]),
    )


def _row_reduce(matrix: List[List[float]]) -> Tuple[List[List[float]], List[float]]:
    """Subtract the minimum of each row from all elements in that row."""
    reduced = [row[:] for row in matrix]
    row_mins = []
    for i in range(len(reduced)):
        row_min = min(reduced[i])
        row_mins.append(row_min)
        for j in range(len(reduced[i])):
            reduced[i][j] -= row_min
    return reduced, row_mins


def _col_reduce(matrix: List[List[float]]) -> Tuple[List[List[float]], List[float]]:
    """Subtract the minimum of each column from all elements in that column."""
    reduced = [row[:] for row in matrix]
    num_rows = len(reduced)
    num_cols = len(reduced[0])
    col_mins = []
    for j in range(num_cols):
        col_min = min(reduced[i][j] for i in range(num_rows))
        col_mins.append(col_min)
        for i in range(num_rows):
            reduced[i][j] -= col_min
    return reduced, col_mins


def _max_matching(
    matrix: List[List[float]],
    num_rows: int,
    num_cols: int,
) -> Tuple[List[int], List[int]]:
    """
    Find a maximum matching on the bipartite graph of zero cells using
    Kuhn's algorithm (alternating paths).

    Returns:
        row_match: row_match[row] = matched column index (or -1)
        col_match: col_match[col] = matched row index (or -1)
    """
    row_match = [-1] * num_rows
    col_match = [-1] * num_cols

    def try_kuhn(row: int, visited: List[bool]) -> bool:
        for col in range(num_cols):
            if abs(matrix[row][col]) > 1e-9:
                continue
            if visited[col]:
                continue
            visited[col] = True
            if col_match[col] == -1 or try_kuhn(col_match[col], visited):
                row_match[row] = col
                col_match[col] = row
                return True
        return False

    for row in range(num_rows):
        visited = [False] * num_cols
        try_kuhn(row, visited)

    return row_match, col_match


def _cover_zeros(matrix: List[List[float]]) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Cover all zeros in the matrix using the minimum number of lines.

    Algorithm (standard Hungarian):
    1. Find a maximum matching of independent zeros (Kuhn's algorithm).
    2. Mark all rows not in the matching.
    3. Mark columns reachable via alternating paths from marked rows.
    4. Draw lines through all unmarked rows and all marked columns.
    The number of lines equals the maximum matching size (min cover = max matching).
    """
    num_rows = len(matrix)
    num_cols = len(matrix[0])

    row_match, col_match = _max_matching(matrix, num_rows, num_cols)

    marked_rows = [False] * num_rows
    marked_cols = [False] * num_cols

    for i in range(num_rows):
        if row_match[i] == -1:
            marked_rows[i] = True

    changed = True
    while changed:
        changed = False
        for i in range(num_rows):
            if marked_rows[i]:
                for j in range(num_cols):
                    if abs(matrix[i][j]) < 1e-9 and not marked_cols[j]:
                        marked_cols[j] = True
                        changed = True
        for j in range(num_cols):
            if marked_cols[j]:
                matched_row = col_match[j]
                if matched_row != -1 and not marked_rows[matched_row]:
                    marked_rows[matched_row] = True
                    changed = True

    lines = []
    for i in range(num_rows):
        if not marked_rows[i]:
            lines.append({"type": "row", "index": i})
    for j in range(num_cols):
        if marked_cols[j]:
            lines.append({"type": "column", "index": j})

    return len(lines), lines


def _find_assignment(
    matrix: List[List[float]],
    num_rows: int,
    num_cols: int,
) -> List[Tuple[int, int]]:
    """
    Find a maximum, and if possible complete, assignment of independent zeros.
    Uses the maximum matching result (guarantees a valid assignment when the
    matrix has a complete zero assignment).
    """
    row_match, _ = _max_matching(matrix, num_rows, num_cols)
    return [(i, row_match[i]) for i in range(num_rows) if row_match[i] != -1]


def solve_hungarian(
    problem: AssignmentProblem,
    max_iterations: int = 100,
) -> AssignmentResult:
    """
    Solve an assignment problem using the Hungarian Method.

    Algorithm:
    1. Balance the problem (add dummy rows/columns if rectangular).
    2. If maximization, transform to minimization.
    3. Row reduction: subtract the minimum of each row from all elements.
    4. Column reduction: subtract the minimum of each column from all elements.
    5. Cover all zeros with the minimum number of lines.
    6. If number of lines equals n (matrix size), an optimal assignment exists.
    7. If not, find the smallest uncovered value, subtract it from all uncovered
       elements, and add it to all elements at the intersection of lines.
    8. Repeat steps 5-7.
    9. Extract the optimal assignment from the final reduced matrix.
    10. Calculate the cost using the original cost matrix.

    Returns an AssignmentResult with assignments, cost, steps, and events.
    """
    balanced = _balance_problem(problem)
    n = balanced.num_rows

    matrix = [row[:] for row in balanced.cost_matrix]
    steps = []
    events = []

    events.append({
        "operation": "start",
        "explanation": (
            f"Starting Hungarian Method with a {n}x{n} matrix. "
            f"{'Maximization problem transformed to minimization. ' if balanced.transformed_for_minimization else ''}"
            f"{'Added ' + str(balanced.dummy_rows_added) + ' dummy rows. ' if balanced.dummy_rows_added > 0 else ''}"
            f"{'Added ' + str(balanced.dummy_cols_added) + ' dummy columns. ' if balanced.dummy_cols_added > 0 else ''}"
        ),
    })

    steps.append(HungarianStep(
        step_number=0,
        operation="initial_matrix",
        matrix_before=[row[:] for row in matrix],
        matrix_after=[row[:] for row in matrix],
        explanation=f"Initial balanced cost matrix ({n}x{n}).",
    ))

    matrix, row_mins = _row_reduce(matrix)
    steps.append(HungarianStep(
        step_number=1,
        operation="row_reduction",
        matrix_before=[row[:] for row in balanced.cost_matrix],
        matrix_after=[row[:] for row in matrix],
        explanation=(
            f"Row reduction: subtracted row minimums {row_mins} from each row. "
            f"This ensures each row has at least one zero."
        ),
    ))
    events.append({
        "operation": "row_reduction",
        "row_minimums": row_mins,
        "explanation": f"Row reduction complete. Row minimums: {row_mins}.",
    })

    matrix, col_mins = _col_reduce(matrix)
    steps.append(HungarianStep(
        step_number=2,
        operation="column_reduction",
        matrix_before=steps[-1].matrix_after,
        matrix_after=[row[:] for row in matrix],
        explanation=(
            f"Column reduction: subtracted column minimums {col_mins} from each column. "
            f"This ensures each column also has at least one zero."
        ),
    ))
    events.append({
        "operation": "column_reduction",
        "col_minimums": col_mins,
        "explanation": f"Column reduction complete. Column minimums: {col_mins}.",
    })

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        num_lines, lines = _cover_zeros(matrix)

        lines_desc = ", ".join(
            f"{'row' if l['type'] == 'row' else 'column'} {l['index']+1}"
            for l in lines
        )
        steps.append(HungarianStep(
            step_number=2 + iteration * 2 - 1,
            operation="cover_zeros",
            matrix_before=steps[-1].matrix_after,
            matrix_after=[row[:] for row in matrix],
            lines_covering_zeros=lines,
            explanation=(
                f"Covered all zeros using {num_lines} line(s): [{lines_desc}]. "
                f"Matrix size = {n}. "
                + ("Optimal assignment possible." if num_lines >= n
                   else f"Lines ({num_lines}) < matrix size ({n}). Must adjust matrix.")
            ),
        ))
        events.append({
            "operation": "cover_zeros",
            "num_lines": num_lines,
            "lines": lines,
            "matrix_size": n,
            "explanation": f"Zero covering: {num_lines} lines needed, matrix size = {n}.",
        })

        if num_lines >= n:
            break

        min_uncovered = float("inf")
        uncovered_rows = set()
        covered_cols = set()
        covered_rows = set()
        for l in lines:
            if l["type"] == "row":
                covered_rows.add(l["index"])
            else:
                covered_cols.add(l["index"])
        for i in range(n):
            if i not in covered_rows:
                uncovered_rows.add(i)
        for i in range(n):
            for j in range(n):
                if i not in covered_rows and j not in covered_cols:
                    if matrix[i][j] < min_uncovered:
                        min_uncovered = matrix[i][j]

        intersection_rows = covered_rows
        intersection_cols = covered_cols

        old_matrix = [row[:] for row in matrix]
        for i in range(n):
            for j in range(n):
                if i not in covered_rows and j not in covered_cols:
                    matrix[i][j] -= min_uncovered
                elif i in covered_rows and j in covered_cols:
                    matrix[i][j] += min_uncovered

        steps.append(HungarianStep(
            step_number=2 + iteration * 2,
            operation="matrix_adjustment",
            matrix_before=old_matrix,
            matrix_after=[row[:] for row in matrix],
            min_uncovered=min_uncovered,
            explanation=(
                f"Smallest uncovered value = {min_uncovered}. "
                f"Subtract {min_uncovered} from all uncovered elements. "
                f"Add {min_uncovered} to elements at intersections of covering lines."
            ),
        ))
        events.append({
            "operation": "matrix_adjustment",
            "min_uncovered": min_uncovered,
            "explanation": (
                f"Matrix adjusted: smallest uncovered value = {min_uncovered}. "
                f"Subtracted from uncovered cells, added to intersection cells."
            ),
        })

    assignment_pairs = _find_assignment(matrix, n, n)

    if not assignment_pairs:
        return AssignmentResult(
            assignments=[],
            total_cost=float("inf"),
            original_total_cost=float("inf"),
            steps=steps,
            final_matrix=matrix,
            is_optimal=False,
            events=events,
        )

    assignments = []
    total_cost_original = 0.0
    total_cost_reduced = 0.0
    original_matrix = balanced.original_matrix_for_cost

    for row_idx, col_idx in assignment_pairs:
        if row_idx < problem.num_rows and col_idx < problem.num_cols:
            orig_cost = original_matrix[row_idx][col_idx]
            reduced_cost = matrix[row_idx][col_idx]
        elif row_idx < problem.num_rows:
            orig_cost = 0.0
            reduced_cost = 0.0
        else:
            orig_cost = 0.0
            reduced_cost = 0.0

        assignments.append({
            "row": row_idx,
            "col": col_idx,
            "row_name": balanced.row_names[row_idx],
            "col_name": balanced.col_names[col_idx],
            "original_cost": orig_cost,
            "reduced_cost": reduced_cost,
        })
        total_cost_original += orig_cost
        total_cost_reduced += reduced_cost

    steps.append(HungarianStep(
        step_number=len(steps) + 1,
        operation="final_assignment",
        matrix_before=steps[-1].matrix_after,
        matrix_after=matrix,
        explanation=(
            f"Optimal assignment found: "
            + ", ".join(f"{a['row_name']} -> {a['col_name']} (cost = {a['original_cost']})"
                       for a in assignments if not a['row_name'].startswith('Dummy')
                       and not a['col_name'].startswith('Dummy'))
            + f". Total cost = {total_cost_original}."
        ),
    ))

    events.append({
        "operation": "complete",
        "assignments": assignments,
        "total_cost": total_cost_original,
        "explanation": (
            f"Hungarian Method complete. Optimal assignment cost = {total_cost_original}."
        ),
    })

    return AssignmentResult(
        assignments=assignments,
        total_cost=total_cost_original,
        original_total_cost=total_cost_original,
        steps=steps,
        final_matrix=matrix,
        is_optimal=True,
        events=events,
    )
