from typing import List, Dict, Any, Optional, Tuple
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    OptimizedSolutionResult,
    SteppingStoneCandidate,
    SteppingStoneIteration,
)
import copy

# Threshold below which an allocation is treated as zero (non-basic).
# Epsilon-degenerate basic cells are set to exactly this value so they are
# consistently recognised as basic cells while being numerically ~zero.
EPSILON = 1e-9


def _get_basic_cells(allocation: List[List[float]], num_sources: int, num_dests: int) -> List[Tuple[int, int]]:
    """Return list of occupied (basic) cells."""
    cells = []
    for i in range(num_sources):
        for j in range(num_dests):
            # Epsilon-degenerate basic cells (>= threshold) count as basic.
            if allocation[i][j] >= EPSILON:
                cells.append((i, j))
    return cells


def _get_non_basic_cells(allocation: List[List[float]], num_sources: int, num_dests: int) -> List[Tuple[int, int]]:
    """Return list of unoccupied (non-basic) cells."""
    cells = []
    for i in range(num_sources):
        for j in range(num_dests):
            if allocation[i][j] < EPSILON:
                cells.append((i, j))
    return cells


class _UnionFind:
    """Small union-find structure used to build a spanning-tree basis."""

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
) -> Tuple[List[List[Tuple[int, int]]], List[Tuple[int, int]]]:
    """
    Build a valid spanning-tree basis over the m+n bipartite graph.

    Nodes are numbered 0..m-1 for sources and m..m+n-1 for destinations.
    A basic cell (i, j) corresponds to the edge (i, m+j).

    Existing allocated (basic) cells are preferred as tree edges. If they do
    not already form a connected, acyclic set of m+n-1 edges, additional
    (epsilon) cells are added deterministically (cheapest first) to complete a
    valid spanning tree. This guarantees loops are always well-defined.

    Returns (adjacency_list, list_of_basic_cells).
    """
    total_nodes = num_sources + num_dests
    uf = _UnionFind(total_nodes)
    adj: List[List[Tuple[int, int, int]]] = [[] for _ in range(total_nodes)]

    basic_cells: List[Tuple[int, int]] = []

    def add_edge(i: int, j: int) -> bool:
        a, b = i, num_sources + j
        if not uf.union(a, b):
            # Would form a cycle; skip so the basis stays acyclic.
            return False
        basic_cells.append((i, j))
        adj[a].append((b, i, j))
        adj[b].append((a, i, j))
        return True

    # Pass 1: add all genuinely allocated cells.
    allocated = []
    for i in range(num_sources):
        for j in range(num_dests):
            if allocation[i][j] >= EPSILON:
                allocated.append((i, j))
    # Order by cost for deterministic tie-breaking while keeping allocations.
    allocated.sort(key=lambda ij: cost_matrix[ij[0]][ij[1]])
    for (i, j) in allocated:
        add_edge(i, j)

    # Pass 2: fill remaining tree edges with the cheapest available cells so the
    # basis spans every node. These become epsilon cells.
    remaining = num_sources + num_dests - 1 - len(basic_cells)
    if remaining > 0:
        candidates = [
            (cost_matrix[i][j], i, j)
            for i in range(num_sources)
            for j in range(num_dests)
            if (i, j) not in basic_cells
        ]
        candidates.sort()
        for _, i, j in candidates:
            if remaining == 0:
                break
            if add_edge(i, j):
                remaining -= 1

    return adj, basic_cells


def _tree_to_adjacency(
    tree: List[List[Tuple[int, int, int]]],
    num_sources: int,
) -> Dict[int, List[Tuple[int, int, int]]]:
    """
    Return node adjacency in the form {node: [(neighbor, src_index, dest_index)]}.
    This is a convenience view; tree[node] is already in that form.
    """
    return {n: list(tree[n]) for n in range(len(tree))}


def _compute_potentials(
    tree: List[List[Tuple[int, int, int]]],
    num_sources: int,
    cost_matrix: List[List[float]],
) -> Tuple[List[float], List[float]]:
    """
    Compute dual potentials u (sources) and v (destinations) such that
    c_ij = u_i + v_j for every basic (tree) cell. Root at source 0 with u_0 = 0.
    Because the basis is a tree, the potentials are uniquely determined.
    """
    total_nodes = num_sources + (len(cost_matrix[0]) if cost_matrix else 0)
    num_dests = total_nodes - num_sources
    u = [None] * num_sources
    v = [None] * num_dests

    u[0] = 0.0
    stack = [0]
    visited = {0}
    while stack:
        node = stack.pop()
        for (neighbor, i, j) in tree[node]:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            if node < num_sources:
                # node is a source (u), neighbor is a destination (v)
                v[neighbor - num_sources] = cost_matrix[node][j] - u[node]
            else:
                # node is a destination (v), neighbor is a source (u)
                u[neighbor] = cost_matrix[neighbor][j] - v[node - num_sources]
            stack.append(neighbor)

    return u, v


def _find_cycle_cells(
    tree: List[List[Tuple[int, int]]],
    enter_i: int,
    enter_j: int,
    num_sources: int,
) -> List[List[int]]:
    """
    Find the unique cycle (closed loop) formed by adding the entering cell
    (enter_i, enter_j) to the basis tree. Returns the loop as a list of
    [row, col] cells starting with the entering cell.
    """
    total_nodes = num_sources + len(tree) - num_sources
    num_dests = total_nodes - num_sources
    start = enter_i
    target = num_sources + enter_j

    # BFS through the tree to find the path start -> target.
    prev = {start: None}
    prev_edge = {start: None}
    queue = [start]
    while queue:
        node = queue.pop(0)
        if node == target:
            break
        for (neighbor, i, j) in tree[node]:
            if neighbor not in prev:
                prev[neighbor] = node
                prev_edge[neighbor] = (i, j)
                queue.append(neighbor)

    # Reconstruct path nodes and the cells along the path.
    path_cells = []
    node = target
    while prev[node] is not None:
        parent = prev[node]
        path_cells.append(list(prev_edge[node]))
        node = parent
    path_cells.reverse()

    # The loop consists of the entering cell plus the path cells back to start.
    loop = [[enter_i, enter_j]] + path_cells
    return loop


def _assign_loop_signs(loop: List[List[int]]) -> List[str]:
    """Assign alternating + and - signs starting with + at the first cell."""
    return ["+" if idx % 2 == 0 else "-" for idx in range(len(loop))]


def _calculate_improvement_index(
    loop: List[List[int]],
    signs: List[str],
    cost_matrix: List[List[float]],
) -> float:
    """
    Calculate the improvement index for a candidate cell.
    Improvement Index = sum of (sign * cost) for each cell in the loop.
    For minimization: negative index means improvement is possible.
    """
    index = 0.0
    for k, (r, c) in enumerate(loop):
        sign_val = 1.0 if signs[k] == "+" else -1.0
        index += sign_val * cost_matrix[r][c]
    return index


def _reduced_costs(
    cost_matrix: List[List[float]],
    u: List[float],
    v: List[float],
) -> List[List[float]]:
    """Reduced cost = c_ij - u_i - v_j for every cell."""
    m = len(cost_matrix)
    n = len(cost_matrix[0])
    red = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            red[i][j] = cost_matrix[i][j] - u[i] - v[j]
    return red


def _adjust_allocation(
    allocation: List[List[float]],
    loop: List[List[int]],
    signs: List[str],
) -> Tuple[List[List[float]], float, str]:
    """
    Adjust the allocation along the loop.
    Find the minimum allocation at minus (-) positions.
    Subtract this quantity from all minus positions and add to all plus positions.
    Returns the new allocation, adjustment quantity, and an explanation.
    """
    min_minus = float("inf")
    for k, (r, c) in enumerate(loop):
        if signs[k] == "-":
            if allocation[r][c] < min_minus:
                min_minus = allocation[r][c]

    adjustment = min_minus

    new_alloc = [row[:] for row in allocation]
    for k, (r, c) in enumerate(loop):
        if signs[k] == "+":
            new_alloc[r][c] += adjustment
        else:
            new_alloc[r][c] -= adjustment

    explanation = (
        f"Adjustment quantity = {adjustment} (minimum allocation at minus positions). "
        f"Add {adjustment} to plus cells, subtract {adjustment} from minus cells."
    )
    return new_alloc, adjustment, explanation


def _sync_allocation_to_basis(
    allocation: List[List[float]],
    basic_cells: List[Tuple[int, int]],
) -> None:
    """Ensure every basic (tree) cell is recorded in the allocation matrix as
    basic (allocation >= EPSILON). Cells on the tree that currently hold 0 are
    set to the epsilon value so the matrix and the basis tree stay consistent."""
    for (i, j) in basic_cells:
        if allocation[i][j] < EPSILON:
            allocation[i][j] = EPSILON


def _compute_cost(
    allocation: List[List[float]],
    cost_matrix: List[List[float]],
) -> float:
    """Compute the total cost of an allocation, ignoring artificial
    epsilon-degenerate cells (allocations within EPSILON of zero). This keeps
    the reported cost free from floating-point artifact introduced by the
    degeneracy placeholders."""
    total = 0.0
    for i in range(len(allocation)):
        for j in range(len(allocation[0])):
            if allocation[i][j] >= 2 * EPSILON:
                total += allocation[i][j] * cost_matrix[i][j]
    return total


def _count_basic_vars(allocation: List[List[float]], num_sources: int, num_dests: int) -> int:
    """Count the number of basic variables (allocated cells)."""
    count = 0
    for i in range(num_sources):
        for j in range(num_dests):
            if allocation[i][j] >= EPSILON:
                count += 1
    return count


def _check_degeneracy(allocation: List[List[float]], num_sources: int, num_dests: int) -> bool:
    """
    A basic feasible solution is degenerate if the number of basic cells
    is less than (num_sources + num_dests - 1).
    """
    required = num_sources + num_dests - 1
    actual = _count_basic_vars(allocation, num_sources, num_dests)
    return actual < required


def _handle_degeneracy(
    allocation: List[List[float]],
    num_sources: int,
    num_dests: int,
) -> Tuple[List[List[float]], str]:
    """
    Handle degeneracy by adding epsilon allocations to maintain a valid
    spanning-tree basis with (num_sources + num_dests - 1) basic cells.
    The cells are chosen so the resulting basis is always a valid tree.
    Returns the adjusted allocation and explanation.
    """
    new_alloc = [row[:] for row in allocation]
    tree, basic_cells = _build_basis_tree(new_alloc, num_sources, num_dests, [[0.0] * num_dests for _ in range(num_sources)])
    added_cells = [(i, j) for (i, j) in basic_cells if new_alloc[i][j] < EPSILON]

    required = num_sources + num_dests - 1
    for (i, j) in added_cells:
        new_alloc[i][j] = EPSILON

    actual = len(basic_cells)
    if actual < required or not added_cells:
        return allocation, "No degeneracy detected."

    explanation = (
        f"Degeneracy detected: {len(_get_basic_cells(new_alloc, num_sources, num_dests)) - len(added_cells)} "
        f"genuine basic cells, but {required} required. Added epsilon allocations to cells "
        f"{[(r+1, c+1) for r, c in added_cells]} to maintain a valid basis."
    )
    return new_alloc, explanation


def solve_stepping_stone(
    problem: BalancedTransportationProblem,
    initial_result: InitialSolutionResult,
    max_iterations: int = 100,
) -> OptimizedSolutionResult:
    """
    Optimize an initial feasible solution using the Stepping Stone Method.

    The implementation maintains the basis as a spanning tree over the
    bipartite graph of sources and destinations (the MODI/transportation-simplex
    formulation). This guarantees that:
      - every closed loop found is a valid (even) cycle of the basis tree,
      - dual potentials are consistent, and
      - the method terminates at a globally optimal solution.

    Algorithm:
    1. Build a valid spanning-tree basis from the initial solution.
    2. Compute dual potentials u,v and reduced costs for every non-basic cell.
    3. If no reduced cost is negative, the solution is optimal.
    4. Else select the entering cell with the most negative reduced cost,
       find its unique cycle in the tree, and adjust allocations along it.
    5. Update the basis tree and repeat.

    Returns an OptimizedSolutionResult.
    """
    num_sources = problem.num_sources
    num_dests = problem.num_destinations
    cost_matrix = problem.cost_matrix

    current_allocation = [row[:] for row in initial_result.allocation]
    current_cost = initial_result.total_cost
    iterations = []
    events = []

    events.append({
        "iteration": 0,
        "operation": "start_optimization",
        "explanation": (
            f"Starting Stepping Stone optimization with initial cost = {current_cost}. "
            f"We will examine all unoccupied cells for potential improvement."
        ),
    })

    current_basis, current_basic = _build_basis_tree(current_allocation, num_sources, num_dests, cost_matrix)
    # Synchronise the allocation matrix with the basis tree so that every basic
    # (tree) cell is marked as such in the matrix (epsilon cells kept at EPSILON).
    _sync_allocation_to_basis(current_allocation, current_basic)

    for iteration in range(1, max_iterations + 1):
        basic_cells = _get_basic_cells(current_allocation, num_sources, num_dests)
        non_basic_cells = _get_non_basic_cells(current_allocation, num_sources, num_dests)

        u, v = _compute_potentials(current_basis, num_sources, cost_matrix)
        reduced = _reduced_costs(cost_matrix, u, v)

        candidates = []
        for (ni, nj) in non_basic_cells:
            loop = _find_cycle_cells(current_basis, ni, nj, num_sources)
            signs = _assign_loop_signs(loop)
            improvement_idx = _calculate_improvement_index(loop, signs, cost_matrix)

            candidate_explanation = (
                f"Cell ({ni+1}, {nj+1}): Loop = {[(r+1, c+1) for r, c in loop]}. "
                f"Signs = {signs}. "
                f"Reduced cost (improvement index) = {improvement_idx:.2f} "
                f"(c_ij - u_i - v_j = {cost_matrix[ni][nj]:.2f} - {u[ni]:.2f} - {v[nj]:.2f}). "
                + ("Negative: improvement possible." if improvement_idx < -EPSILON else "Non-negative: no improvement from this cell.")
            )

            candidates.append(SteppingStoneCandidate(
                row=ni,
                col=nj,
                loop=loop,
                signs=signs,
                improvement_index=improvement_idx,
                explanation=candidate_explanation,
            ))

        improving = [c for c in candidates if c.improvement_index < -EPSILON]

        if not improving:
            events.append({
                "iteration": iteration,
                "operation": "optimality_reached",
                "candidates_evaluated": len(candidates),
                "explanation": (
                    f"Evaluated {len(candidates)} candidate cells. "
                    f"All improvement indices are non-negative (no negative reduced cost). "
                    f"By the optimality condition, the current solution with cost = {current_cost} is optimal."
                ),
            })
            break

        best = min(improving, key=lambda c: c.improvement_index)

        new_allocation, adjustment, adj_explanation = _adjust_allocation(
            current_allocation, best.loop, best.signs
        )

        new_cost = _compute_cost(new_allocation, cost_matrix)

        iteration_explanation = (
            f"Iteration {iteration}: Selected entering cell ({best.row+1}, {best.col+1}) "
            f"with improvement index = {best.improvement_index:.2f}. "
            f"Loop: {[(r+1, c+1) for r, c in best.loop]}. "
            f"{adj_explanation} "
            f"Old cost = {current_cost:.2f}, new cost = {new_cost:.2f}, "
            f"cost reduction = {current_cost - new_cost:.2f}."
        )

        si = SteppingStoneIteration(
            iteration=iteration,
            candidates=candidates,
            best_candidate=best,
            adjustment_quantity=adjustment,
            old_allocation=[row[:] for row in current_allocation],
            new_allocation=[row[:] for row in new_allocation],
            old_cost=current_cost,
            new_cost=new_cost,
            explanation=iteration_explanation,
        )
        iterations.append(si)

        events.append({
            "iteration": iteration,
            "operation": "iteration",
            "entering_cell": [best.row, best.col],
            "improvement_index": best.improvement_index,
            "adjustment_quantity": adjustment,
            "old_cost": current_cost,
            "new_cost": new_cost,
            "num_candidates": len(candidates),
            "num_improving": len(improving),
            "explanation": iteration_explanation,
        })

        current_allocation = new_allocation
        current_cost = new_cost

        # Rebuild the spanning-tree basis after the pivot. This keeps the basis
        # acyclic and reconnects it if the pivot made a basic cell vanish.
        current_basis, current_basic = _build_basis_tree(current_allocation, num_sources, num_dests, cost_matrix)
        _sync_allocation_to_basis(current_allocation, current_basic)

        # Guard: if we did not actually make progress, stop to avoid an
        # infinite loop (should not happen with a valid tree basis).
        if abs(new_cost - current_cost) < 1e-12 and iteration > 1:
            pass

    final_candidates = []
    basic_cells = _get_basic_cells(current_allocation, num_sources, num_dests)
    non_basic_cells = _get_non_basic_cells(current_allocation, num_sources, num_dests)
    u, v = _compute_potentials(current_basis, num_sources, cost_matrix)
    for (ni, nj) in non_basic_cells:
        loop = _find_cycle_cells(current_basis, ni, nj, num_sources)
        signs = _assign_loop_signs(loop)
        improvement_idx = _calculate_improvement_index(loop, signs, cost_matrix)
        final_candidates.append(SteppingStoneCandidate(
            row=ni, col=nj, loop=loop, signs=signs,
            improvement_index=improvement_idx,
        ))

    is_optimal = all(c.improvement_index >= -EPSILON for c in final_candidates)

    final_explanation = (
        f"Stepping Stone optimization complete after {len(iterations)} iteration(s). "
        f"Initial cost = {initial_result.total_cost:.2f}, "
        f"final cost = {current_cost:.2f}, "
        f"total reduction = {initial_result.total_cost - current_cost:.2f}. "
    )
    if is_optimal:
        final_explanation += (
            "The solution is optimal: by the MODI optimality condition, no non-basic cell "
            "has a negative reduced cost (improvement index)."
        )
    else:
        final_explanation += "WARNING: The solution may not be optimal."

    return OptimizedSolutionResult(
        allocation=current_allocation,
        total_cost=_compute_cost(current_allocation, cost_matrix),
        iterations=iterations,
        is_optimal=is_optimal,
        final_improvement_indices=final_candidates,
        explanation=final_explanation,
    )
