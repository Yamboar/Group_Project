from typing import List, Dict, Any, Optional, Tuple, Set
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    OptimizedSolutionResult,
    SteppingStoneCandidate,
    SteppingStoneIteration,
    DegeneracyInfo,
    EPSILON,
    clean_allocation,
)

# An allocation >= EPSILON is treated as a basic (occupied) cell.
# Epsilon-degenerate cells are set to exactly this value.
EPSILON = 1e-9


# ── Basis helpers ────────────────────────────────────────────────────────────

def _get_basic_cells(
    allocation: List[List[float]], m: int, n: int
) -> List[Tuple[int, int]]:
    return [
        (i, j)
        for i in range(m)
        for j in range(n)
        if allocation[i][j] >= EPSILON
    ]


def _get_non_basic_cells(
    allocation: List[List[float]], m: int, n: int
) -> List[Tuple[int, int]]:
    return [
        (i, j)
        for i in range(m)
        for j in range(n)
        if allocation[i][j] < EPSILON
    ]


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[ra] = rb
        return True


def _build_basis_tree(
    allocation: List[List[float]],
    num_sources: int,
    num_dests: int,
    cost_matrix: List[List[float]],
    restricted: Optional[Set[Tuple[int, int]]] = None,
) -> Tuple[List[List[Tuple[int, int, int]]], List[Tuple[int, int]]]:
    """
    Build a spanning-tree basis over the m+n bipartite graph.

    Source nodes: 0..m-1.  Destination nodes: m..m+n-1.
    Edge (i, m+j) corresponds to basic cell (i, j).

    Existing allocated cells (>= EPSILON) are preferred.  If the allocation
    does not yet form a spanning tree, additional cheapest available
    (non-restricted) cells are added as epsilon edges to complete it.

    Returns (adjacency_list, list_of_basic_cells).
    """
    restricted = restricted or set()
    total = num_sources + num_dests
    uf = _UnionFind(total)
    adj: List[List[Tuple[int, int, int]]] = [[] for _ in range(total)]
    basic: List[Tuple[int, int]] = []

    def add_edge(i: int, j: int) -> bool:
        if not uf.union(i, num_sources + j):
            return False
        basic.append((i, j))
        adj[i].append((num_sources + j, i, j))
        adj[num_sources + j].append((i, i, j))
        return True

    # Pass 1 — genuinely allocated cells (cheapest first for determinism).
    allocated = sorted(
        [(i, j) for i in range(num_sources) for j in range(num_dests)
         if allocation[i][j] >= EPSILON],
        key=lambda ij: cost_matrix[ij[0]][ij[1]],
    )
    for (i, j) in allocated:
        add_edge(i, j)

    # Pass 2 — fill gaps with cheapest available (non-restricted) cells.
    remaining = num_sources + num_dests - 1 - len(basic)
    if remaining > 0:
        candidates = sorted(
            [(cost_matrix[i][j], i, j)
             for i in range(num_sources)
             for j in range(num_dests)
             if (i, j) not in basic and (i, j) not in restricted],
        )
        for _, i, j in candidates:
            if remaining == 0:
                break
            if add_edge(i, j):
                remaining -= 1

    return adj, basic


def _compute_potentials(
    tree: List[List[Tuple[int, int, int]]],
    num_sources: int,
    cost_matrix: List[List[float]],
) -> Tuple[List[float], List[float]]:
    """
    Compute MODI dual potentials u_i, v_j such that c_ij = u_i + v_j for
    every basic cell.  Root at source 0 with u_0 = 0.
    """
    num_dests = len(cost_matrix[0]) if cost_matrix else 0
    u: List[Optional[float]] = [None] * num_sources
    v: List[Optional[float]] = [None] * num_dests
    u[0] = 0.0

    stack = [0]
    visited: Set[int] = {0}
    while stack:
        node = stack.pop()
        for (nbr, i, j) in tree[node]:
            if nbr in visited:
                continue
            visited.add(nbr)
            if node < num_sources:
                v[nbr - num_sources] = cost_matrix[node][j] - u[node]
            else:
                u[nbr] = cost_matrix[nbr][j] - v[node - num_sources]
            stack.append(nbr)

    # Fill any unvisited node with 0 (safety for disconnected components).
    u = [x if x is not None else 0.0 for x in u]
    v = [x if x is not None else 0.0 for x in v]
    return u, v


def _find_cycle_cells(
    tree: List[List[Tuple[int, int, int]]],
    enter_i: int,
    enter_j: int,
    num_sources: int,
) -> List[List[int]]:
    """
    Find the unique cycle formed by adding edge (enter_i, enter_j) to the tree.
    Returns a closed list: [entering_cell, ...path_cells..., entering_cell].
    """
    start = enter_i
    target = num_sources + enter_j

    prev: Dict[int, Optional[int]] = {start: None}
    prev_edge: Dict[int, Optional[Tuple[int, int]]] = {start: None}
    queue = [start]
    found = False

    while queue:
        node = queue.pop(0)
        if node == target:
            found = True
            break
        for (nbr, i, j) in tree[node]:
            if nbr not in prev:
                prev[nbr] = node
                prev_edge[nbr] = (i, j)
                queue.append(nbr)

    if not found:
        # Should not happen with a valid spanning tree; return minimal fallback.
        return [[enter_i, enter_j], [enter_i, enter_j]]

    path_cells: List[List[int]] = []
    node = target
    while prev[node] is not None:
        path_cells.append(list(prev_edge[node]))
        node = prev[node]
    path_cells.reverse()

    return [[enter_i, enter_j]] + path_cells + [[enter_i, enter_j]]


def _assign_loop_signs(loop: List[List[int]]) -> List[str]:
    """Alternating +/- starting with + at index 0."""
    return ["+" if k % 2 == 0 else "-" for k in range(len(loop))]


def _loop_unique_cells(loop: List[List[int]]) -> List[List[int]]:
    """Return the unique cells of a closed loop (drops the trailing duplicate)."""
    if len(loop) >= 2 and loop[0] == loop[-1]:
        return loop[:-1]
    return loop


def _calculate_improvement_index(
    loop: List[List[int]],
    signs: List[str],
    cost_matrix: List[List[float]],
) -> float:
    cells = _loop_unique_cells(loop)
    return sum(
        (1.0 if signs[k] == "+" else -1.0) * cost_matrix[r][c]
        for k, (r, c) in enumerate(cells)
    )


def _reduced_costs(
    cost_matrix: List[List[float]],
    u: List[float],
    v: List[float],
) -> List[List[float]]:
    m, n = len(cost_matrix), len(cost_matrix[0])
    return [
        [cost_matrix[i][j] - u[i] - v[j] for j in range(n)]
        for i in range(m)
    ]


def _adjust_allocation(
    allocation: List[List[float]],
    loop: List[List[int]],
    signs: List[str],
) -> Tuple[List[List[float]], float, str]:
    """
    Perform the Stepping Stone allocation adjustment along the loop.
    θ = min allocation at minus-sign positions.
    Add θ to plus positions; subtract θ from minus positions.
    """
    cells = _loop_unique_cells(loop)
    signs_slice = signs[:len(cells)]

    theta = min(
        allocation[r][c]
        for k, (r, c) in enumerate(cells)
        if signs_slice[k] == "-"
    )

    new_alloc = [row[:] for row in allocation]
    for k, (r, c) in enumerate(cells):
        if signs_slice[k] == "+":
            new_alloc[r][c] += theta
        else:
            new_alloc[r][c] -= theta

    explanation = (
        f"θ = {theta} (minimum allocation at minus positions). "
        f"Add θ to plus cells, subtract θ from minus cells."
    )
    return new_alloc, theta, explanation


def _sync_basis(
    allocation: List[List[float]],
    basic_cells: List[Tuple[int, int]],
) -> None:
    """Ensure every tree cell has allocation >= EPSILON (mark epsilon cells)."""
    for (i, j) in basic_cells:
        if allocation[i][j] < EPSILON:
            allocation[i][j] = EPSILON


def _compute_cost(
    allocation: List[List[float]],
    cost_matrix: List[List[float]],
) -> float:
    """Sum allocation * cost for all real cells (excludes ε degeneracy cells)."""
    return sum(
        allocation[i][j] * cost_matrix[i][j]
        for i in range(len(allocation))
        for j in range(len(allocation[0]))
        if allocation[i][j] > EPSILON
    )


def _check_degeneracy_post_pivot(
    allocation: List[List[float]],
    num_sources: int,
    num_dests: int,
) -> Tuple[bool, int, int]:
    required = num_sources + num_dests - 1
    actual = sum(
        1 for i in range(num_sources) for j in range(num_dests)
        if allocation[i][j] >= EPSILON
    )
    return actual < required, required, actual


# ── Main solver ──────────────────────────────────────────────────────────────

def solve_stepping_stone(
    problem: BalancedTransportationProblem,
    initial_result: InitialSolutionResult,
    max_iterations: int = 100,
) -> OptimizedSolutionResult:
    """
    Optimize an initial feasible solution using the Stepping Stone / MODI method.

    Steps per iteration:
    1. Build (or rebuild) the spanning-tree basis.
    2. Compute dual potentials u, v.
    3. Compute reduced costs for every non-basic cell.
    4. If all reduced costs >= 0 → optimal.  Check for zero-cost non-basic cells
       to identify alternative optima.
    5. Enter the cell with the most negative reduced cost.
    6. Find its unique cycle in the basis tree.
    7. Compute θ and adjust allocations.
    8. Rebuild basis, detect degeneracy, repeat.

    Guards:
    - Iteration limit: terminates and flags hit_iteration_limit if max_iterations
      is reached without proving optimality.
    - No-progress guard: stops if cost does not decrease (avoids cycling).
    - Previous-allocation hash set: detects cycling through identical states.

    Returns an OptimizedSolutionResult with full XAI event log.
    """
    m = problem.num_sources
    n = problem.num_destinations
    cost_matrix = problem.cost_matrix
    restricted = problem.restricted_cells or set()

    current_alloc = [row[:] for row in initial_result.allocation]
    current_cost = initial_result.total_cost
    iterations: List[SteppingStoneIteration] = []
    events: List[Dict[str, Any]] = []
    seen_states: Set[str] = set()

    events.append({
        "iteration": 0,
        "operation": "start_optimization",
        "initial_cost": current_cost,
        "concise": f"Starting Stepping Stone optimization from cost = {current_cost}.",
        "detailed": (
            f"Starting Stepping Stone / MODI method with initial cost = {current_cost}. "
            f"We will evaluate every unoccupied cell by computing its improvement index "
            f"(reduced cost) and enter the best improving cell until no improvement is possible."
        ),
        "technical": (
            f"Initializing MODI on BFS with Z_0 = {current_cost}. "
            f"Will iterate: compute potentials u,v; evaluate ΔZ_{{ij}} = c_{{ij}} - u_i - v_j "
            f"for all non-basic (i,j); enter argmin{{ΔZ < 0}}."
        ),
        "explanation": (
            f"Starting Stepping Stone optimization with initial cost = {current_cost}. "
            f"We will examine all unoccupied cells for potential improvement."
        ),
    })

    # Initial basis.
    basis, basic_cells = _build_basis_tree(
        current_alloc, m, n, cost_matrix, restricted
    )
    _sync_basis(current_alloc, basic_cells)

    hit_limit = False
    deg_info: Optional[DegeneracyInfo] = None
    degenerate_pivot_count = 0

    for iteration in range(1, max_iterations + 1):

        # Cycle detection via allocation fingerprint.
        state_key = str([[round(current_alloc[i][j], 10) for j in range(n)] for i in range(m)])
        if state_key in seen_states:
            events.append({
                "iteration": iteration,
                "operation": "cycle_detected",
                "explanation": (
                    f"Iteration {iteration}: Repeated allocation state detected. "
                    f"Stopping to prevent infinite loop."
                ),
            })
            break
        seen_states.add(state_key)

        non_basic = _get_non_basic_cells(current_alloc, m, n)
        u, v = _compute_potentials(basis, m, cost_matrix)
        reduced = _reduced_costs(cost_matrix, u, v)

        candidates: List[SteppingStoneCandidate] = []
        for (ni, nj) in non_basic:
            if (ni, nj) in restricted:
                continue
            loop = _find_cycle_cells(basis, ni, nj, m)
            signs = _assign_loop_signs(loop)
            idx = _calculate_improvement_index(loop, signs, cost_matrix)
            loop_display = (
                " → ".join(
                    f"({'+'if s=='+'else'-'}){r+1},{c+1}"
                    for (r, c), s in zip(_loop_unique_cells(loop), signs)
                )
            )
            is_alt = abs(idx) <= EPSILON

            cand_exp = (
                f"Cell ({ni+1},{nj+1}): reduced cost = {idx:.6g} "
                f"(c_{{ij}}-u_i-v_j = {cost_matrix[ni][nj]:.6g}-{u[ni]:.6g}-{v[nj]:.6g}). "
                f"Loop: {loop_display}. "
                + ("Negative → improvement possible." if idx < -EPSILON
                   else ("Zero → alternative optimum candidate." if is_alt
                         else "Non-negative → no improvement."))
            )

            candidates.append(SteppingStoneCandidate(
                row=ni, col=nj,
                loop=loop, signs=signs,
                improvement_index=idx,
                explanation=cand_exp,
                loop_display=loop_display,
                is_alternative_optimum=is_alt,
            ))

        improving = [c for c in candidates if c.improvement_index < -EPSILON]

        if not improving:
            # Check for alternative optima: non-basic cells with index == 0.
            alt_cells = [
                (c.row, c.col)
                for c in candidates
                if abs(c.improvement_index) <= EPSILON
            ]
            events.append({
                "iteration": iteration,
                "operation": "optimality_reached",
                "current_cost": current_cost,
                "candidates_evaluated": len(candidates),
                "all_candidates": [
                    {
                        "cell": [c.row+1, c.col+1],
                        "improvement_index": c.improvement_index,
                        "is_alternative_optimum": c.is_alternative_optimum,
                        "explanation": c.explanation,
                    }
                    for c in candidates
                ],
                "alternative_optima_cells": [(r+1, c+1) for r, c in alt_cells],
                "has_alternative_optima": len(alt_cells) > 0,
                "concise": f"Optimal at cost = {current_cost}.",
                "detailed": (
                    f"All {len(candidates)} non-basic cells evaluated. "
                    f"No negative improvement indices. "
                    f"Solution with cost = {current_cost} is optimal."
                    + (
                        f" {len(alt_cells)} cell(s) have improvement index = 0, "
                        f"indicating alternative optimal solutions exist: "
                        f"{[(r+1,c+1) for r,c in alt_cells]}."
                        if alt_cells else ""
                    )
                ),
                "technical": (
                    f"ΔZ_{{ij}} ≥ 0 ∀ non-basic (i,j). "
                    f"Z* = {current_cost}. "
                    + (f"Alternative optima: {[(r+1,c+1) for r,c in alt_cells]}." if alt_cells else "")
                ),
                "why_stopped": (
                    "The optimality condition is satisfied: no non-basic cell has a "
                    "negative reduced cost, so no reallocation can reduce the total cost."
                ),
                "explanation": (
                    f"Evaluated {len(candidates)} candidate cells. "
                    f"All improvement indices are non-negative. "
                    f"Current solution with cost = {current_cost} is optimal."
                ),
            })
            deg_info = DegeneracyInfo(
                detected=False, stage="final",
                required_basic_vars=m+n-1,
                actual_basic_vars=len(_get_basic_cells(current_alloc, m, n)),
            )
            final_alloc = clean_allocation(current_alloc)
            return OptimizedSolutionResult(
                allocation=final_alloc,
                total_cost=_compute_cost(final_alloc, cost_matrix),
                iterations=iterations,
                is_optimal=True,
                final_improvement_indices=candidates,
                explanation=(
                    f"Stepping Stone complete after {iteration-1} iteration(s). "
                    f"Optimal cost = {_compute_cost(final_alloc, cost_matrix)}."
                    + (
                        f" Alternative optima exist at cells "
                        f"{[(r+1,c+1) for r,c in alt_cells]}."
                        if alt_cells else ""
                    )
                ),
                has_alternative_optima=len(alt_cells) > 0,
                alternative_optima_cells=alt_cells,
                degeneracy_info=deg_info,
                degenerate_pivot_count=degenerate_pivot_count,
                hit_iteration_limit=False,
                events=events,
            )

        # Select entering cell: most negative improvement index.
        # Tie-break: smallest row, then smallest column.
        min_idx = min(c.improvement_index for c in improving)
        best_candidates = [
            c for c in improving if abs(c.improvement_index - min_idx) <= EPSILON
        ]
        best_candidates.sort(key=lambda c: (c.row, c.col))
        best = best_candidates[0]
        tie_in_selection = len(best_candidates) > 1

        new_alloc, theta, adj_exp = _adjust_allocation(current_alloc, best.loop, best.signs)
        new_cost = _compute_cost(new_alloc, cost_matrix)

        # Summarise all candidates for XAI.
        all_cand_summary = sorted(
            [
                {
                    "cell": [c.row+1, c.col+1],
                    "improvement_index": c.improvement_index,
                    "loop_display": c.loop_display,
                    "is_alternative_optimum": c.is_alternative_optimum,
                    "selected": (c.row == best.row and c.col == best.col),
                    "explanation": c.explanation,
                }
                for c in candidates
            ],
            key=lambda x: x["improvement_index"],
        )

        iter_exp = (
            f"Iteration {iteration}: Entering cell ({best.row+1},{best.col+1}) "
            f"with improvement index = {best.improvement_index:.6g}. "
            f"Loop: {best.loop_display}. "
            f"{adj_exp} "
            f"Cost: {current_cost:.6g} → {new_cost:.6g} "
            f"(reduction = {current_cost - new_cost:.6g})."
            + (
                f" Tie-break applied among {len(best_candidates)} equally improving cells; "
                f"selected top-left."
                if tie_in_selection else ""
            )
        )

        si = SteppingStoneIteration(
            iteration=iteration,
            candidates=candidates,
            best_candidate=best,
            adjustment_quantity=theta,
            old_allocation=[row[:] for row in current_alloc],
            new_allocation=[row[:] for row in new_alloc],
            old_cost=current_cost,
            new_cost=new_cost,
            explanation=iter_exp,
            all_candidates_summary=all_cand_summary,
        )

        events.append({
            "iteration": iteration,
            "operation": "iteration",
            "entering_cell": [best.row, best.col],
            "improvement_index": best.improvement_index,
            "loop": [list(cell) for cell in best.loop],
            "loop_display": best.loop_display,
            "signs": best.signs,
            "adjustment_quantity": theta,
            "old_cost": current_cost,
            "new_cost": new_cost,
            "cost_reduction": current_cost - new_cost,
            "num_improving": len(improving),
            "tie_in_selection": tie_in_selection,
            "all_candidates": all_cand_summary,
            "concise": (
                f"Iter {iteration}: enter ({best.row+1},{best.col+1}), "
                f"Δcost = -{current_cost - new_cost:.6g}."
            ),
            "detailed": iter_exp,
            "technical": (
                f"Iter {iteration}: ΔZ_{{({best.row+1},{best.col+1})}} = "
                f"{best.improvement_index:.6g}. "
                f"θ = {theta}. Z: {current_cost:.6g} → {new_cost:.6g}."
            ),
            "why_selected": (
                f"Cell ({best.row+1},{best.col+1}) was selected because it has the most "
                f"negative improvement index ({best.improvement_index:.6g}), meaning "
                f"entering it produces the greatest cost reduction per unit reallocated."
                + (
                    f" Tie-break applied (top-left among {len(best_candidates)} equal cells)."
                    if tie_in_selection else ""
                )
            ),
            "why_rejected": [
                {
                    "cell": [c.row+1, c.col+1],
                    "improvement_index": c.improvement_index,
                    "reason": (
                        "Non-negative improvement index; entering would not reduce cost."
                        if c.improvement_index >= -EPSILON
                        else f"Improvement index {c.improvement_index:.6g} is not as negative "
                             f"as the selected cell ({best.improvement_index:.6g})."
                    ),
                }
                for c in candidates
                if not (c.row == best.row and c.col == best.col)
            ],
            "what_if": {
                "description": (
                    "If a different improving cell had been entered instead, the cost "
                    "reduction would have been smaller (or zero for alternative optima)."
                ),
                "alternatives": [
                    {
                        "cell": [c.row+1, c.col+1],
                        "improvement_index": c.improvement_index,
                        "would_reduce_cost_by": abs(c.improvement_index) * theta
                        if c.improvement_index < -EPSILON else 0,
                    }
                    for c in improving
                    if not (c.row == best.row and c.col == best.col)
                ],
            },
            "explanation": iter_exp,
        })

        prev_cost = current_cost
        current_alloc = new_alloc
        current_cost = new_cost

        iterations.append(si)

        # Detect degeneracy immediately after the pivot, on the raw adjusted
        # allocation and BEFORE the ε-sync inflates the basis. A pivot is
        # degenerate when two (or more) minus-loop cells tie at θ and BOTH
        # drop to zero, leaving fewer than m+n-1 positive cells. (Detecting
        # here is essential: after _sync_basis injects ε into every tree cell
        # the count is always "full" and degenerate pivots would be silently
        # invisible.) The ε-perturbation itself is NOT applied here — the
        # cheapest-cell tree rebuild below injects ε exactly as before, so the
        # basis (and hence the solution path) is identical to the classic
        # implementation. Degeneracy is purely *observed* and reported.
        is_deg, req, act = _check_degeneracy_post_pivot(new_alloc, m, n)
        if is_deg:
            iterations[-1].degeneracy_after = True
            degenerate_pivot_count += 1
            # Which cells will receive the ε-perturbation: the tree's basic-cell
            # fill-ins (cells the tree uses that carry no real flow yet).
            basis, basic_cells = _build_basis_tree(
                current_alloc, m, n, cost_matrix, restricted
            )
            added_eps = [
                (i, j) for (i, j) in basic_cells
                if current_alloc[i][j] < EPSILON
            ]
            _sync_basis(current_alloc, basic_cells)
            events.append({
                "iteration": iteration,
                "operation": "degeneracy",
                "stage": f"iteration_{iteration}",
                "required_basic_vars": req,
                "actual_basic_vars": act,
                "epsilon_cells": [(r+1, c+1) for r, c in added_eps],
                "concise": f"Post-pivot degeneracy: ε applied to {len(added_eps)} cell(s).",
                "detailed": (
                    f"After iteration {iteration} pivot, the basis has {act} basic variables "
                    f"(m+n-1 = {req} required). "
                    f"ε-perturbation applied to {[(r+1,c+1) for r,c in added_eps]}."
                ),
                "technical": (
                    f"Post-pivot degenerate BFS: |B| = {act} < {req}. "
                    f"ε injection to {[(r+1,c+1) for r,c in added_eps]}."
                ),
                "why": (
                    "A leaving basic variable dropped to exactly zero, creating a "
                    "degenerate pivot. ε is added to maintain a valid spanning-tree basis."
                ),
                "explanation": (
                    f"Degeneracy after iteration {iteration}: added ε to "
                    f"{[(r+1,c+1) for r,c in added_eps]}."
                ),
            })
        else:
            # Perfect-basis pivot: rebuild and re-sync for the next iteration.
            basis, basic_cells = _build_basis_tree(
                current_alloc, m, n, cost_matrix, restricted
            )
            _sync_basis(current_alloc, basic_cells)

        # No-progress guard.
        if abs(new_cost - prev_cost) < 1e-12 and iteration > 1:
            events.append({
                "iteration": iteration,
                "operation": "no_progress",
                "explanation": (
                    f"Iteration {iteration}: No cost improvement detected. "
                    f"Stopping to prevent cycling."
                ),
            })
            break

    else:
        hit_limit = True
        events.append({
            "iteration": max_iterations,
            "operation": "iteration_limit",
            "explanation": (
                f"Reached maximum iteration limit ({max_iterations}). "
                f"Solution may not be optimal. Final cost = {current_cost}."
            ),
        })

    # Final optimality check for the non-converged case.
    final_candidates: List[SteppingStoneCandidate] = []
    u, v = _compute_potentials(basis, m, cost_matrix)
    for (ni, nj) in _get_non_basic_cells(current_alloc, m, n):
        if (ni, nj) in restricted:
            continue
        loop = _find_cycle_cells(basis, ni, nj, m)
        signs = _assign_loop_signs(loop)
        idx = _calculate_improvement_index(loop, signs, cost_matrix)
        final_candidates.append(SteppingStoneCandidate(
            row=ni, col=nj, loop=loop, signs=signs,
            improvement_index=idx,
            is_alternative_optimum=abs(idx) <= EPSILON,
        ))

    is_optimal = all(c.improvement_index >= -EPSILON for c in final_candidates)
    alt_cells = [
        (c.row, c.col) for c in final_candidates
        if abs(c.improvement_index) <= EPSILON
    ]

    final_cost = _compute_cost(current_alloc, cost_matrix)
    final_alloc = clean_allocation(current_alloc)

    return OptimizedSolutionResult(
        allocation=final_alloc,
        total_cost=final_cost,
        iterations=iterations,
        is_optimal=is_optimal,
        final_improvement_indices=final_candidates,
        explanation=(
            f"Stepping Stone complete after {len(iterations)} iteration(s). "
            f"{'Optimal' if is_optimal else 'Sub-optimal (iteration limit reached)'} "
            f"cost = {final_cost}."
            + (f" Alternative optima at {[(r+1,c+1) for r,c in alt_cells]}." if alt_cells else "")
        ),
        has_alternative_optima=len(alt_cells) > 0,
        alternative_optima_cells=alt_cells,
        degeneracy_info=DegeneracyInfo(
            detected=False, stage="final",
            required_basic_vars=m+n-1,
            actual_basic_vars=len(_get_basic_cells(final_alloc, m, n)),
        ),
        degenerate_pivot_count=degenerate_pivot_count,
        hit_iteration_limit=hit_limit,
        events=events,
    )
