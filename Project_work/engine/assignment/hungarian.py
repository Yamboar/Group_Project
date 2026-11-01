from typing import List, Dict, Any, Tuple, Optional, Set
from engine.assignment.models import (
    AssignmentProblem,
    BalancedAssignmentProblem,
    AssignmentResult,
    HungarianStep,
    AssignmentProblemType,
    PROHIBITED_COST,
)

_EPS = 1e-9


# ── Balancing / setup ────────────────────────────────────────────────────────

def _balance_problem(problem: AssignmentProblem) -> BalancedAssignmentProblem:
    """
    Prepare the assignment problem for the Hungarian Method.

    1. If maximisation: transform to minimisation via M - c_ij (where M is the
       maximum non-restricted value in the matrix).  The original values are
       stored in original_matrix_for_cost so the final reported cost is correct.
    2. If rectangular (rows ≠ cols): add dummy rows or columns with cost 0.
       Dummy rows/cols are never added to the restricted set.
    3. Restricted cells stay as a separate state: in the *reported* balanced
       matrix they are represented by None so no artificial large number ever
       appears.  The Hungarian working matrix encodes them with the internal
       sentinel so they can never become zeros or be selected.

    Returns BalancedAssignmentProblem.
    """
    cost_matrix = [row[:] for row in problem.cost_matrix]
    row_names = list(problem.row_names)
    col_names = list(problem.col_names)
    num_rows = problem.num_rows
    num_cols = problem.num_cols
    restricted = set(problem.restricted_cells or set())
    dummy_rows = 0
    dummy_cols = 0
    transformed = False

    def _is_restricted(i: int, j: int) -> bool:
        return i < num_rows and j < num_cols and (i, j) in restricted

    # Step 1: maximisation transform — use the max among non-restricted cells.
    # Restricted cells are never transformed, so they can never accidentally
    # become an attractive zero or high-value cell.
    if problem.problem_type == AssignmentProblemType.MAXIMIZATION:
        real_vals = [
            cost_matrix[i][j]
            for i in range(num_rows)
            for j in range(num_cols)
            if not _is_restricted(i, j)
        ]
        max_val = max(real_vals) if real_vals else 0.0
        for i in range(num_rows):
            for j in range(num_cols):
                if not _is_restricted(i, j):
                    cost_matrix[i][j] = max_val - cost_matrix[i][j]
        transformed = True

    # Step 2: balance (make square).
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

    balanced_n = len(cost_matrix)

    # Build original_matrix_for_cost at full balanced size.
    # Contains the true original (pre-transform) costs for real cells, 0 for dummies.
    original_for_cost = [row[:] for row in problem.cost_matrix]
    # Extend existing rows for any added dummy columns.
    for i in range(num_rows):
        extra = balanced_n - len(original_for_cost[i])
        if extra > 0:
            original_for_cost[i].extend([0.0] * extra)
    # Append zero rows for any added dummy rows.
    while len(original_for_cost) < balanced_n:
        original_for_cost.append([0.0] * balanced_n)

    # Restricted cells in the reported matrix carry no number (None).
    # The working sentinel is applied only inside solve_hungarian.
    for (i, j) in restricted:
        if 0 <= i < balanced_n and 0 <= j < balanced_n:
            cost_matrix[i][j] = None

    # Restricted set in balanced coordinate space (unchanged; dummy rows/cols
    # are never restricted).
    balanced_restricted = set(restricted)

    return BalancedAssignmentProblem(
        original_problem=problem,
        cost_matrix=cost_matrix,
        row_names=row_names,
        col_names=col_names,
        dummy_rows_added=dummy_rows,
        dummy_cols_added=dummy_cols,
        transformed_for_minimization=transformed,
        original_matrix_for_cost=original_for_cost,
        restricted_cells=balanced_restricted,
        num_rows=balanced_n,
        num_cols=balanced_n,
    )


def _inject_sentinel(
    matrix: List[List[float]],
    restricted: Set[Tuple[int, int]],
    n: int,
) -> List[List[float]]:
    """
    Build the internal working matrix: restricted cells are encoded with the
    PROHIBITED_COST sentinel so the algorithm never treats them as zeros,
    never reduces them, and never selects them.  All other cells keep their
    reported value.
    """
    return [
        [
            PROHIBITED_COST if (i, j) in restricted else matrix[i][j]
            for j in range(n)
        ]
        for i in range(n)
    ]


def _display_matrix(
    matrix: List[List[float]],
    restricted: Set[Tuple[int, int]],
    n: int,
) -> List[List[Any]]:
    """Reported version of the working matrix: restricted cells appear as None."""
    return [
        [None if (i, j) in restricted else matrix[i][j] for j in range(n)]
        for i in range(n)
    ]


# ── Matrix reduction ─────────────────────────────────────────────────────────

def _row_reduce(matrix: List[List[float]]) -> Tuple[List[List[float]], List[float]]:
    """
    Row reduction: subtract the minimum of each row from every element in that row.
    Restricted cells (>= PROHIBITED_COST) are ignored when finding the row minimum
    so they are not incorrectly reduced and never become zeros.
    """
    n = len(matrix)
    reduced = [row[:] for row in matrix]
    row_mins: List[float] = []
    for i in range(n):
        real_vals = [reduced[i][j] for j in range(n) if reduced[i][j] < PROHIBITED_COST]
        row_min = min(real_vals) if real_vals else 0.0
        row_mins.append(row_min)
        for j in range(n):
            if reduced[i][j] < PROHIBITED_COST:
                reduced[i][j] -= row_min
    return reduced, row_mins


def _col_reduce(matrix: List[List[float]]) -> Tuple[List[List[float]], List[float]]:
    """
    Column reduction: subtract the minimum of each column from every element.
    Restricted cells are ignored when finding the column minimum.
    """
    n = len(matrix)
    reduced = [row[:] for row in matrix]
    col_mins: List[float] = []
    for j in range(n):
        real_vals = [reduced[i][j] for i in range(n) if reduced[i][j] < PROHIBITED_COST]
        col_min = min(real_vals) if real_vals else 0.0
        col_mins.append(col_min)
        for i in range(n):
            if reduced[i][j] < PROHIBITED_COST:
                reduced[i][j] -= col_min
    return reduced, col_mins


def _zero_positions(matrix: List[List[float]]) -> List[Tuple[int, int]]:
    """Return all (i, j) where matrix[i][j] == 0 (not restricted)."""
    n = len(matrix)
    return [
        (i, j)
        for i in range(n)
        for j in range(n)
        if abs(matrix[i][j]) < _EPS and matrix[i][j] < PROHIBITED_COST
    ]


# ── Matching / zero covering ─────────────────────────────────────────────────

def _max_matching(
    matrix: List[List[float]], n: int
) -> Tuple[List[int], List[int]]:
    """
    Maximum bipartite matching on zero cells (Kuhn's algorithm).
    Restricted cells are never considered as zero candidates.
    Returns (row_match, col_match) where -1 means unmatched.
    """
    row_match = [-1] * n
    col_match = [-1] * n

    def try_kuhn(row: int, visited: List[bool]) -> bool:
        for col in range(n):
            if visited[col]:
                continue
            if abs(matrix[row][col]) > _EPS or matrix[row][col] >= PROHIBITED_COST:
                continue
            visited[col] = True
            if col_match[col] == -1 or try_kuhn(col_match[col], visited):
                row_match[row] = col
                col_match[col] = row
                return True
        return False

    for row in range(n):
        visited = [False] * n
        try_kuhn(row, visited)

    return row_match, col_match


def _cover_zeros(
    matrix: List[List[float]], n: int
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Cover all zeros using the minimum number of lines (König's theorem).

    Algorithm:
    1. Find a maximum matching of independent zeros.
    2. Mark all unmatched rows.
    3. Alternating-path mark: if a marked row has a zero in column j, mark j;
       if column j is marked and its matched row exists, mark that row.
    4. Lines: through all *unmarked* rows and all *marked* columns.
    """
    row_match, col_match = _max_matching(matrix, n)

    marked_rows = [row_match[i] == -1 for i in range(n)]
    marked_cols = [False] * n

    changed = True
    while changed:
        changed = False
        for i in range(n):
            if not marked_rows[i]:
                continue
            for j in range(n):
                if abs(matrix[i][j]) < _EPS and matrix[i][j] < PROHIBITED_COST:
                    if not marked_cols[j]:
                        marked_cols[j] = True
                        changed = True
        for j in range(n):
            if not marked_cols[j]:
                continue
            r = col_match[j]
            if r != -1 and not marked_rows[r]:
                marked_rows[r] = True
                changed = True

    lines = (
        [{"type": "row", "index": i} for i in range(n) if not marked_rows[i]]
        + [{"type": "column", "index": j} for j in range(n) if marked_cols[j]]
    )
    return len(lines), lines


def _find_assignment(matrix: List[List[float]], n: int) -> List[Tuple[int, int]]:
    """Return a maximum matching on zero cells (the final assignment)."""
    row_match, _ = _max_matching(matrix, n)
    return [(i, row_match[i]) for i in range(n) if row_match[i] != -1]


def _detect_alternative_optima(
    matrix: List[List[float]],
    n: int,
    assignment_pairs: List[Tuple[int, int]],
) -> Tuple[bool, List[Tuple[int, int]]]:
    """
    After the final assignment, check whether any non-assigned cell also
    contains a zero (after reduction). Such cells could be entered into
    the assignment without changing total cost — they are alternative optima.
    """
    assigned_set = set(assignment_pairs)
    alt_cells = [
        (i, j)
        for i in range(n)
        for j in range(n)
        if abs(matrix[i][j]) < _EPS
        and matrix[i][j] < PROHIBITED_COST
        and (i, j) not in assigned_set
    ]
    return len(alt_cells) > 0, alt_cells


# ── Enumeration of all optimal assignment plans ──────────────────────────────

_MAX_OPTIMAL_PLANS = 100


def _count_perfect_matchings_dp(zero_bits: List[int], n: int) -> int:
    """
    Exact number of perfect matchings on the zero graph via DP over column
    bitmasks (a permanent computation). Used when the DFS enumeration cap is
    reached, so the count stays exact for square (dummy-free) problems.
    """
    dp = {0: 1}
    for row in range(n):
        nxt = {}
        cols = zero_bits[row]
        for mask, cnt in dp.items():
            rem = cols & ~mask
            while rem:
                lb = rem & -rem
                nm = mask | lb
                nxt[nm] = nxt.get(nm, 0) + cnt
                rem -= lb
        dp = nxt
    return dp.get((1 << n) - 1, 0)


def _enumerate_optimal_assignments(
    matrix: List[List[float]],
    n: int,
    real_row_count: int,
    has_dummies: bool,
    max_plans: int = _MAX_OPTIMAL_PLANS,
) -> Tuple[int, List[List[Tuple[int, int]]], bool, bool]:
    """
    Enumerate every perfect matching on the zero cells of the final reduced
    matrix — every one of them is an optimal assignment with the same total
    cost. Restricted cells can never be zeros, so they are excluded implicitly.

    Two balanced plans represent the same *real* plan when they agree on the
    real rows (dummy rows only fill residual slots), so plans are de-duplicated
    on that key.

    Returns (count, plans, truncated, count_exact):
      count       — number of distinct real optimal plans;
      plans       — one representative per plan, full balanced size, as lists
                    of (row, col) pairs (0-based);
      truncated   — True when the enumeration stopped early at `max_plans`
                    matchings, so `plans` may be an incomplete listing;
      count_exact — False only when `count` is a lower bound (heavily
                    rectangular problems above the cap).
    """
    zero_bits = [
        sum(
            (1 << j) for j in range(n)
            if abs(matrix[i][j]) < _EPS and matrix[i][j] < PROHIBITED_COST
        )
        for i in range(n)
    ]
    all_mask = (1 << n) - 1
    raw: List[Tuple[Tuple[int, int], ...]] = []
    truncated = [False]

    def dfs(row: int, used: int, current: List[Tuple[int, int]]) -> None:
        if truncated[0]:
            return
        free = all_mask ^ used
        # Hall-style prune: every remaining row must still have a free zero
        # column, otherwise no completion of this partial assignment exists.
        for r in range(row, n):
            if zero_bits[r] & free == 0:
                return
        if row == n:
            raw.append(tuple(current))
            if len(raw) >= max_plans:
                truncated[0] = True
            return
        rem = zero_bits[row] & free
        while rem:
            lb = rem & -rem
            j = lb.bit_length() - 1
            current.append((row, j))
            dfs(row + 1, used | lb, current)
            current.pop()
            if truncated[0]:
                return
            rem -= lb

    if n >= 1:
        dfs(0, 0, [])

    # De-duplicate balanced matchings that agree on all real rows.
    distinct: Dict[Tuple[int, ...], Tuple[Tuple[int, int], ...]] = {}
    for plan in raw:
        key = tuple(col for (r, col) in plan if r < real_row_count)
        distinct.setdefault(key, plan)
    plans = [list(p) for p in distinct.values()]
    plans.sort()

    if not truncated[0]:
        # Enumerated everything → the de-duplicated list is exact.
        return len(plans), plans, False, True

    # Enumeration capped. For square (dummy-free) problems, use the DP
    # permanent for an EXACT count of the distinct real plans (all rows real).
    if not has_dummies and n <= 16:
        exact = _count_perfect_matchings_dp(zero_bits, n)
        return exact, plans, True, True
    # Otherwise the count is a lower bound (dummy permutations or size).
    return len(plans), plans, True, False


# ── Main solver ──────────────────────────────────────────────────────────────

def solve_hungarian(
    problem: AssignmentProblem,
    max_iterations: int = 100,
) -> AssignmentResult:
    """
    Solve an assignment problem using the Hungarian Method.

    Full algorithm:
    0. Balance the matrix (add dummies) and apply maximisation transform if needed.
    1. Encode restricted cells with an internal sentinel so they can never be zero.
    2. Row reduction (ignoring restricted cells for the row-min calculation).
    3. Column reduction (ignoring restricted cells for the col-min calculation).
    4. Cover all zeros with the minimum number of lines.
       If #lines == n → optimal assignment exists; go to step 7.
    5. Find the smallest uncovered non-restricted value δ.
    6. Subtract δ from all uncovered cells; add δ to all intersection cells.
       Repeat from step 4.
    7. Extract assignment from zero cells (maximum matching).
    8. Map assignment back to original costs.  For maximisation, use the
       *original* profit values (not transformed values).
    9. Detect alternative optima (additional zero cells in final reduced matrix).

    All reported matrices (steps and final_matrix) show restricted cells as
    None — never as an artificial large number.

    Returns AssignmentResult with full XAI event log.
    """
    balanced = _balance_problem(problem)
    n = balanced.num_rows
    restricted = balanced.restricted_cells

    # Internal working matrix: restricted cells get the sentinel.
    display_base = [row[:] for row in balanced.cost_matrix]
    work = _inject_sentinel(display_base, restricted, n)

    steps: List[HungarianStep] = []
    events: List[Dict[str, Any]] = []

    # ── Step 0: Start event ──────────────────────────────────────────────────
    restricted_note = (
        f" {len(balanced.restricted_cells)} cell(s) are Restricted (forbidden)."
        if balanced.restricted_cells else ""
    )
    start_exp = (
        f"Starting Hungarian Method with a {n}×{n} matrix."
        f"{' Maximisation problem transformed to minimisation.' if balanced.transformed_for_minimization else ''}"
        f"{' Added ' + str(balanced.dummy_rows_added) + ' dummy row(s).' if balanced.dummy_rows_added > 0 else ''}"
        f"{' Added ' + str(balanced.dummy_cols_added) + ' dummy column(s).' if balanced.dummy_cols_added > 0 else ''}"
        f"{restricted_note}"
    )
    events.append({
        "operation": "start",
        "matrix_size": n,
        "dummy_rows": balanced.dummy_rows_added,
        "dummy_cols": balanced.dummy_cols_added,
        "transformed": balanced.transformed_for_minimization,
        "num_prohibited": len(balanced.restricted_cells),
        "num_restricted": len(balanced.restricted_cells),
        "concise": f"Hungarian Method: {n}×{n} matrix.",
        "detailed": start_exp,
        "technical": (
            f"Initializing Hungarian algorithm on {n}×{n} balanced "
            f"{'minimisation' if not balanced.transformed_for_minimization else 'transformed-minimisation'} matrix. "
            f"Restricted cells are excluded from all calculations."
        ),
        "explanation": start_exp,
    })

    initial_display = _display_matrix(work, restricted, n)
    steps.append(HungarianStep(
        step_number=0,
        operation="initial_matrix",
        matrix_before=[row[:] for row in initial_display],
        matrix_after=[row[:] for row in initial_display],
        explanation=f"Initial balanced {'(transformed) ' if balanced.transformed_for_minimization else ''}"
                    f"cost matrix ({n}×{n}).",
        concise=f"Initial {n}×{n} matrix.",
        detailed=start_exp,
        technical=f"Working matrix initialised. Restricted cells are excluded from all steps.",
        zero_positions=_zero_positions(work),
    ))

    # ── Step 1: Row reduction ────────────────────────────────────────────────
    matrix_before_rr = _display_matrix(work, restricted, n)
    work, row_mins = _row_reduce(work)
    zeros_after_rr = _zero_positions(work)

    rr_exp = (
        f"Row reduction: subtracted row minimums {[round(v,6) for v in row_mins]} from each row. "
        f"Each row now has at least one zero. "
        f"Restricted cells were excluded from the row-minimum calculation."
    )
    steps.append(HungarianStep(
        step_number=1,
        operation="row_reduction",
        matrix_before=matrix_before_rr,
        matrix_after=_display_matrix(work, restricted, n),
        explanation=rr_exp,
        concise="Row reduction complete.",
        detailed=rr_exp,
        technical=(
            f"a'_{{ij}} = a_{{ij}} - min_j(a_{{ij}}) for non-restricted cells. "
            f"Row minimums: {[round(v,6) for v in row_mins]}."
        ),
        zero_positions=zeros_after_rr,
    ))
    events.append({
        "operation": "row_reduction",
        "row_minimums": row_mins,
        "zero_positions_after": zeros_after_rr,
        "concise": "Row reduction complete.",
        "detailed": rr_exp,
        "technical": f"Row mins: {[round(v,6) for v in row_mins]}.",
        "why": (
            "Subtracting the row minimum ensures each row contributes at least one zero, "
            "providing candidate assignment cells without changing the optimal solution "
            "(we only shift all costs by a constant per row). Restricted cells are "
            "never reduced, so a Restricted cell can never become a zero."
        ),
        "explanation": rr_exp,
    })

    # ── Step 2: Column reduction ─────────────────────────────────────────────
    matrix_before_cr = _display_matrix(work, restricted, n)
    work, col_mins = _col_reduce(work)
    zeros_after_cr = _zero_positions(work)

    cr_exp = (
        f"Column reduction: subtracted column minimums {[round(v,6) for v in col_mins]} from each column. "
        f"Each column now has at least one zero."
    )
    steps.append(HungarianStep(
        step_number=2,
        operation="column_reduction",
        matrix_before=matrix_before_cr,
        matrix_after=_display_matrix(work, restricted, n),
        explanation=cr_exp,
        concise="Column reduction complete.",
        detailed=cr_exp,
        technical=(
            f"a''_{{ij}} = a'_{{ij}} - min_i(a'_{{ij}}) for non-restricted cells. "
            f"Column minimums: {[round(v,6) for v in col_mins]}."
        ),
        zero_positions=zeros_after_cr,
    ))
    events.append({
        "operation": "column_reduction",
        "col_minimums": col_mins,
        "zero_positions_after": zeros_after_cr,
        "concise": "Column reduction complete.",
        "detailed": cr_exp,
        "technical": f"Col mins: {[round(v,6) for v in col_mins]}.",
        "why": (
            "Column reduction ensures every column also has at least one zero. "
            "Together with row reduction, this maximises the number of candidate "
            "zero cells before zero-covering begins."
        ),
        "explanation": cr_exp,
    })

    # ── Steps 3+: Iterative cover + adjust ───────────────────────────────────
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        num_lines, lines = _cover_zeros(work, n)
        zeros_now = _zero_positions(work)

        lines_desc = ", ".join(
            f"{'row' if l['type']=='row' else 'col'} {l['index']+1}"
            for l in lines
        )
        cover_exp = (
            f"Covered all zeros using {num_lines} line(s): [{lines_desc}]. "
            f"Matrix size = {n}. "
            + (
                f"Number of lines equals matrix size → an optimal assignment exists."
                if num_lines >= n
                else f"{num_lines} lines < {n} (matrix size) → matrix adjustment required."
            )
        )
        steps.append(HungarianStep(
            step_number=2 + iteration * 2 - 1,
            operation="cover_zeros",
            matrix_before=steps[-1].matrix_after,
            matrix_after=_display_matrix(work, restricted, n),
            lines_covering_zeros=lines,
            explanation=cover_exp,
            concise=f"Covered zeros with {num_lines} line(s).",
            detailed=cover_exp,
            technical=(
                f"Min-line cover = {num_lines} (= max matching by König). "
                f"{'Optimal.' if num_lines >= n else 'Adjust required.'}"
            ),
            zero_positions=zeros_now,
        ))
        events.append({
            "operation": "cover_zeros",
            "num_lines": num_lines,
            "lines": lines,
            "matrix_size": n,
            "zero_positions": zeros_now,
            "optimal_possible": num_lines >= n,
            "concise": f"Covered with {num_lines} line(s).",
            "detailed": cover_exp,
            "technical": f"König: min cover = max matching = {num_lines}.",
            "why": (
                "By König's theorem, the minimum number of lines needed to cover all "
                "zeros equals the maximum number of independent zeros (the maximum "
                "matching). When this equals n, a complete independent zero assignment "
                "— and hence an optimal solution — has been found."
            ),
            "explanation": (
                f"Zero covering: {num_lines} lines needed, matrix size = {n}."
            ),
        })

        if num_lines >= n:
            break

        # Find the smallest uncovered non-restricted value.
        covered_rows: Set[int] = set()
        covered_cols: Set[int] = set()
        for l in lines:
            if l["type"] == "row":
                covered_rows.add(l["index"])
            else:
                covered_cols.add(l["index"])

        min_uncovered: Optional[float] = None
        for i in range(n):
            for j in range(n):
                if i in covered_rows or j in covered_cols:
                    continue
                if work[i][j] >= PROHIBITED_COST:
                    continue
                if min_uncovered is None or work[i][j] < min_uncovered:
                    min_uncovered = work[i][j]

        if min_uncovered is None:
            min_uncovered = 0.0

        old_work = [row[:] for row in work]
        for i in range(n):
            for j in range(n):
                if work[i][j] >= PROHIBITED_COST:
                    continue
                if i not in covered_rows and j not in covered_cols:
                    work[i][j] -= min_uncovered
                elif i in covered_rows and j in covered_cols:
                    work[i][j] += min_uncovered

        zeros_after_adj = _zero_positions(work)
        adj_exp = (
            f"Smallest uncovered value δ = {round(min_uncovered, 6)}. "
            f"Subtract δ from all uncovered cells; add δ to all intersection cells. "
            f"Restricted cells are unchanged. "
            f"New zero positions: {[(r+1,c+1) for r,c in zeros_after_adj]}."
        )
        steps.append(HungarianStep(
            step_number=2 + iteration * 2,
            operation="matrix_adjustment",
            matrix_before=_display_matrix(old_work, restricted, n),
            matrix_after=_display_matrix(work, restricted, n),
            min_uncovered=min_uncovered,
            explanation=adj_exp,
            concise=f"Adjusted matrix: δ = {round(min_uncovered,6)}.",
            detailed=adj_exp,
            technical=(
                f"δ = {round(min_uncovered,6)}. "
                f"a_{{ij}} -= δ (uncovered); a_{{ij}} += δ (intersection). "
                f"Restricted cells excluded."
            ),
            zero_positions=zeros_after_adj,
        ))
        events.append({
            "operation": "matrix_adjustment",
            "min_uncovered": min_uncovered,
            "zero_positions_after": zeros_after_adj,
            "concise": f"Matrix adjusted: δ = {round(min_uncovered,6)}.",
            "detailed": adj_exp,
            "technical": f"δ = {round(min_uncovered,6)}.",
            "why": (
                f"Subtracting δ from uncovered cells creates new zeros without "
                f"invalidating existing ones (intersection cells gain δ to compensate). "
                f"Restricted cells are never adjusted, so they can never become "
                f"attractive zeros."
            ),
            "explanation": (
                f"Matrix adjusted: smallest uncovered value = {round(min_uncovered,6)}. "
                f"Subtracted from uncovered cells, added to intersection cells."
            ),
        })

    # ── Step N: Extract assignment ────────────────────────────────────────────
    assignment_pairs = _find_assignment(work, n)

    if not assignment_pairs:
        return AssignmentResult(
            assignments=[],
            total_cost=0.0,
            original_total_cost=0.0,
            steps=steps,
            final_matrix=_display_matrix(work, restricted, n),
            is_optimal=False,
            events=events,
            has_alternative_optima=False,
            number_of_optimal_assignments=0,
            all_optimal_assignments=[],
        )

    # Enumerate ALL optimal plans from the final reduced matrix's zero cells,
    # and detect alternative optima before building the result.
    has_dummies = (
        balanced.dummy_rows_added > 0 or balanced.dummy_cols_added > 0
    )
    num_plans, all_plans, plans_truncated, count_exact = (
        _enumerate_optimal_assignments(work, n, problem.num_rows, has_dummies)
    )
    has_alt = num_plans > 1
    _, alt_cells = _detect_alternative_optima(work, n, assignment_pairs)

    assignments: List[Dict[str, Any]] = []
    total_cost_original = 0.0
    original_matrix = balanced.original_matrix_for_cost

    for row_idx, col_idx in assignment_pairs:
        # Use true original cost (pre-transform, with 0 for dummy cells).
        orig_cost = original_matrix[row_idx][col_idx]
        reduced_cost = work[row_idx][col_idx]
        is_dummy = (
            balanced.row_names[row_idx].startswith("Dummy")
            or balanced.col_names[col_idx].startswith("Dummy")
        )
        is_restricted = (row_idx, col_idx) in balanced.restricted_cells

        assignments.append({
            "row": row_idx,
            "col": col_idx,
            "row_name": balanced.row_names[row_idx],
            "col_name": balanced.col_names[col_idx],
            "original_cost": orig_cost,
            "reduced_cost": reduced_cost,
            "is_dummy": is_dummy,
            "is_restricted": is_restricted,
            "is_prohibited": is_restricted,
        })
        if not is_dummy:
            total_cost_original += orig_cost

    # Build final assignment description for XAI.
    real_assignments = [a for a in assignments if not a["is_dummy"]]
    assign_desc = ", ".join(
        f"{a['row_name']} → {a['col_name']} (cost={a['original_cost']})"
        for a in real_assignments
    )

    final_step_exp = (
        f"Optimal assignment found: {assign_desc}. "
        f"Total {'cost' if not balanced.transformed_for_minimization else 'profit'} "
        f"= {total_cost_original}."
        + (
            f" There are {num_plans} different optimal "
            f"{'plans' if not has_dummies else 'assignment matching(s)'}."
            if has_alt else ""
        )
        + (
            f" (showing the first {len(all_plans)} plan(s).)"
            if plans_truncated and has_alt else ""
        )
    )
    steps.append(HungarianStep(
        step_number=len(steps) + 1,
        operation="final_assignment",
        matrix_before=steps[-1].matrix_after,
        matrix_after=_display_matrix(work, restricted, n),
        explanation=final_step_exp,
        concise=f"Total cost = {total_cost_original}.",
        detailed=final_step_exp,
        technical=(
            f"Final matching: {[(r+1,c+1) for r,c in assignment_pairs]}. "
            f"Z* = {total_cost_original}. "
            f"#optimal plans = {num_plans}."
        ),
        zero_positions=_zero_positions(work),
    ))

    alt_desc = (
        f" Alternative optimal assignments possible at cells "
        f"{[(r+1,c+1) for r,c in alt_cells]}."
        if has_alt else ""
    )
    plan_word = "plan" if num_plans == 1 else "plans"
    plan_desc = (
        f"{' At least' if not count_exact else ''} There "
        f"{'are' if num_plans != 1 else 'is'} {num_plans} different optimal "
        f"assignment {plan_word}."
        if has_alt else ""
    )
    complete_exp = (
        f"Hungarian Method complete. "
        f"Optimal {'cost' if not balanced.transformed_for_minimization else 'profit'} "
        f"= {total_cost_original}.{alt_desc}{plan_desc}"
    )
    events.append({
        "operation": "complete",
        "assignments": assignments,
        "total_cost": total_cost_original,
        "problem_type": problem.problem_type.value,
        "has_alternative_optima": has_alt,
        "alternative_cells": [(r+1, c+1) for r, c in alt_cells],
        "number_of_optimal_assignments": num_plans,
        "all_optimal_assignments": [
            [[r, c] for r, c in plan] for plan in all_plans
        ],
        "optimal_assignments_truncated": plans_truncated,
        "concise": f"Optimal {'cost' if not balanced.transformed_for_minimization else 'profit'} = {total_cost_original}.",
        "detailed": complete_exp,
        "technical": (
            f"Z* = {total_cost_original}. "
            f"Matching: {[(r+1,c+1) for r,c in assignment_pairs]}. "
            f"#optimal plans = {num_plans}."
            + (f" Alternatives: {[(r+1,c+1) for r,c in alt_cells]}." if has_alt else "")
        ),
        "why_optimal": (
            "The Hungarian Method guarantees optimality: after row and column reductions "
            "and iterative matrix adjustments, the final independent zero assignment "
            "corresponds to the globally optimal cost."
        ),
        "explanation": (
            f"Hungarian Method complete. Optimal assignment cost = {total_cost_original}."
        ),
    })

    return AssignmentResult(
        assignments=assignments,
        total_cost=total_cost_original,
        original_total_cost=total_cost_original,
        steps=steps,
        final_matrix=_display_matrix(work, restricted, n),
        is_optimal=True,
        events=events,
        has_alternative_optima=has_alt,
        alternative_assignment_cells=alt_cells,
        number_of_optimal_assignments=num_plans,
        all_optimal_assignments=all_plans,
        optimal_assignments_truncated=plans_truncated,
        optimal_assignments_count_exact=count_exact,
    )
