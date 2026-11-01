"""Residual-completion and repair helpers for transportation methods.

Greedy initial methods (North-West Corner, Least Cost, Vogel) allocate against
open cells only. When restricted cells remove routes, a greedy method can
"strand" some supply or demand: the cells that would normally absorb the
residual are no longer reachable because the obvious routes were consumed
first. In that situation the greedy loop simply runs out of usable cells while
supply and demand are still positive.

Two layers fix this, in order of faithfulness to the base method:

1. `complete_residual` adds units to the remaining cheapest open cells. This
   preserves the greedy character and handles the common near-miss where some
   open cell still has both residual supply and residual demand.

2. `repair_allocation` runs a full min-cost max-flow over the open
   (non-restricted) network and replaces the allocation with the computed
   optimum-flow allocation. This is needed when the greedy choices consumed a
   row or column that a stranded side must use: fixing that requires
   re-routing, which additive completion cannot do. Restricted cells are never
   used, and no artificial costs are introduced.
"""

from typing import List, Dict, Any, Tuple, Set
from engine.transportation.models import AllocationDecision

_EPS = 1e-9


def complete_residual(
    allocation: List[List[float]],
    supply: List[float],
    demand: List[float],
    cost_matrix: List[List[float]],
    restricted: Set[Tuple[int, int]],
    method_label: str,
    start_step: int,
    decisions: List[Any],
    events: List[Dict[str, Any]],
    intermediate_states: List[Dict[str, Any]],
) -> Tuple[int, bool]:
    """
    Fill any remaining positive supply/demand using the cheapest open cells.

    Mutates allocation/supply/demand in place. Appends AllocationDecision
    records to `decisions` and XAI events to `events` for the same shapes the
    greedy methods produce.

    Returns (steps_taken, all_consumed).  all_consumed is False when some
    supply or demand remains but no open cell can absorb it — the caller
    should then repair the allocation.
    """
    num_sources = len(supply)
    num_dests = len(demand)
    step = start_step
    steps_taken = 0

    while True:
        total_left = sum(s for s in supply if s > _EPS)
        demand_left = sum(d for d in demand if d > _EPS)
        if total_left <= _EPS or demand_left <= _EPS:
            break

        best_i, best_j, best_cost = -1, -1, None
        for i in range(num_sources):
            if supply[i] <= _EPS:
                continue
            for j in range(num_dests):
                if demand[j] <= _EPS:
                    continue
                if (i, j) in restricted:
                    continue
                c = cost_matrix[i][j]
                if best_cost is None or c < best_cost - _EPS:
                    best_cost = c
                    best_i, best_j = i, j

        if best_i == -1:
            # No open cell with positive supply and demand remains.
            break

        steps_taken += 1
        step += 1
        pre_supply = supply[best_i]
        pre_demand = demand[best_j]
        qty = min(pre_supply, pre_demand)

        allocation[best_i][best_j] += qty
        supply[best_i] -= qty
        demand[best_j] -= qty

        explanation = (
            f"Residual completion (step {step}): the greedy phase could not "
            f"ship all units because restricted cells removed some routes. "
            f"Remaining open cheapest cell ({best_i+1},{best_j+1}) with cost "
            f"{best_cost} is allocated min({pre_supply},{pre_demand}) = {qty}."
        )

        decisions.append(AllocationDecision(
            row=best_i,
            col=best_j,
            quantity=qty,
            supply_remaining=supply[best_i],
            demand_remaining=demand[best_j],
            explanation=explanation,
            tie_broken=False,
            tie_break_reason="",
        ))

        total_so_far = sum(
            allocation[r][c] * cost_matrix[r][c]
            for r in range(num_sources)
            for c in range(num_dests)
        )

        events.append({
            "iteration": step,
            "operation": "residual_completion",
            "cell": [best_i, best_j],
            "quantity": qty,
            "cost_per_unit": best_cost,
            "total_cell_cost": qty * best_cost,
            "supply_before": pre_supply,
            "demand_before": pre_demand,
            "supply_remaining": supply[best_i],
            "demand_remaining": demand[best_j],
            "restricted_note": True,
            "concise": (
                f"Residual completion: allocate {qty} to ({best_i+1},{best_j+1}), "
                f"cost={best_cost}."
            ),
            "detailed": explanation,
            "technical": (
                f"Residual greedy completion: x_{{{best_i+1},{best_j+1}}} = "
                f"min(s_{best_i+1}={pre_supply}, d_{best_j+1}={pre_demand}) = {qty}."
            ),
            "why": (
                f"Restricted cells left supply/demand unshipped after the {method_label} "
                f"greedy phase. The remaining open cell with the lowest cost is used "
                f"so the solution stays feasible. Restricted cells are never used."
            ),
            "explanation": explanation,
        })

        intermediate_states.append({
            "step": step,
            "cell": [best_i, best_j],
            "quantity": qty,
            "allocation": [row[:] for row in allocation],
            "supply": supply[:],
            "demand": demand[:],
            "total_cost_so_far": total_so_far,
            "residual_completion": True,
        })

    leftover_supply = sum(s for s in supply if s > _EPS) > _EPS
    leftover_demand = sum(d for d in demand if d > _EPS) > _EPS
    all_consumed = not (leftover_supply and leftover_demand)
    return steps_taken, all_consumed


def repair_allocation(
    allocation: List[List[float]],
    supply: List[float],
    demand: List[float],
    original_supply: List[float],
    original_demand: List[float],
    cost_matrix: List[List[float]],
    restricted: Set[Tuple[int, int]],
    method_label: str,
    start_step: int,
    decisions: List[Any],
    events: List[Dict[str, Any]],
    intermediate_states: List[Dict[str, Any]],
) -> int:
    """
    Replace the (stranded) allocation with the min-cost-flow optimum over open
    routes. Used only when additive residual completion could not consume all
    supply and demand.

    IMPORTANT: the greedy phase may have consumed a source on the wrong
    destination, so the mutated supply/demand can no longer express the real
    problem. The repair therefore re-solves over the ORIGINAL supply and
    demand vectors (original_supply/original_demand).

    Mutates allocation/supply/demand in place. Appends an XAI "repair" record.
    Returns the number of steps consumed (1 if a repair ran, else 0).
    """
    num_sources = len(supply)
    num_dests = len(demand)

    if all(s <= _EPS for s in supply) and all(d <= _EPS for d in demand):
        return 0

    flow_alloc = _min_cost_flow_allocation(
        original_supply, original_demand, cost_matrix, restricted
    )
    if flow_alloc is None:
        # Should be unreachable after the validation max-flow gate, but keep
        # the defensive guard: leave the current allocation untouched.
        return 0

    repaired_cost = sum(
        flow_alloc[r][c] * cost_matrix[r][c]
        for r in range(num_sources)
        for c in range(num_dests)
    )
    previous_cost = sum(
        allocation[r][c] * cost_matrix[r][c]
        for r in range(num_sources)
        for c in range(num_dests)
    )

    allocation[:] = flow_alloc
    for i in range(num_sources):
        supply[i] = 0.0
    for j in range(num_dests):
        demand[j] = 0.0

    step = start_step + 1
    delta = repaired_cost - previous_cost

    explanation = (
        f"Repair (step {step}): restricted cells left supply and demand stranded "
        f"after the {method_label} greedy phase, and no open cell could absorb the "
        f"residual directly. The allocation was recomputed over the open "
        f"(non-restricted) network with a minimum-cost flow so that every source "
        f"ships its supply and every destination receives its demand. "
        f"Previous partial allocation cost ≈ {previous_cost:.6g}; "
        f"repaired allocation cost = {repaired_cost:.6g} "
        f"({delta:+.6g}). Restricted cells are never used."
    )

    decisions.append(AllocationDecision(
        row=0,
        col=0,
        quantity=0.0,
        supply_remaining=0.0,
        demand_remaining=0.0,
        explanation=explanation,
        tie_broken=False,
        tie_break_reason="",
    ))

    events.append({
        "iteration": step,
        "operation": "repair",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": repaired_cost,
        "previous_cost": previous_cost,
        "cost_delta": delta,
        "concise": (
            f"Repair via min-cost flow: stranded supply/demand recomputed, "
            f"cost = {repaired_cost:.6g}."
        ),
        "detailed": explanation,
        "technical": (
            f"Residual infeasible -> min-cost max-flow over open routes "
            f"(restricted edges excluded). Z_past = {previous_cost:.6g}, "
            f"Z_repair = {repaired_cost:.6g}."
        ),
        "why": (
            "Greedy initial methods allocate to whatever open cell is selected "
            "next; with restricted routes this can consume a row or column that "
            "another destination/source uniquely depends on, stranding units. "
            "Additive completion then cannot help because no simultaneous "
            "supply/demand remains on any open cell. A min-cost flow is the "
            "exact way to re-route so all supply and demand are satisfied."
        ),
        "explanation": explanation,
    })

    intermediate_states.append({
        "step": step,
        "cell": None,
        "quantity": None,
        "allocation": [row[:] for row in allocation],
        "supply": supply[:],
        "demand": demand[:],
        "total_cost_so_far": repaired_cost,
        "repair": True,
    })

    return 1


def _min_cost_flow_allocation(
    supply: List[float],
    demand: List[float],
    cost_matrix: List[List[float]],
    restricted: Set[Tuple[int, int]],
) -> List[List[float]]:
    """
    Minimum-cost flow allocation over open (non-restricted) cells.

    Successive shortest paths with exact shortest-path recomputation (SPFA, so
    negative residual edges are handled exactly). Returns an allocation matrix
    that satisfies every source and destination, or None if the required flow
    is not achievable.
    """
    num_sources = len(supply)
    num_dests = len(demand)
    S = num_sources + num_dests
    T = S + 1
    n_nodes = T + 1
    graph: List[List[List]] = [[] for _ in range(n_nodes)]

    def add_edge(u: int, v: int, cap: float, cost: float) -> None:
        # edge = [to, residual_cap, cost, rev_index, flow, forward]
        graph[u].append([v, cap, cost, len(graph[v]), 0.0, True])
        graph[v].append([u, 0.0, -cost, len(graph[u]) - 1, 0.0, False])

    for i in range(num_sources):
        if supply[i] > _EPS:
            add_edge(S, i, supply[i], 0.0)
    for j in range(num_dests):
        if demand[j] > _EPS:
            add_edge(num_sources + j, T, demand[j], 0.0)
    for i in range(num_sources):
        for j in range(num_dests):
            if (i, j) in restricted:
                continue
            add_edge(i, num_sources + j, float("inf"), cost_matrix[i][j])

    total_flow = 0.0
    total_demand = sum(d for d in demand if d > _EPS)
    while total_flow < total_demand - _EPS:
        dist = [float("inf")] * n_nodes
        parent_node = [-1] * n_nodes
        parent_edge = [-1] * n_nodes
        dist[S] = 0.0
        queue = [S]
        in_queue = [False] * n_nodes
        in_queue[S] = True
        while queue:
            u = queue.pop(0)
            in_queue[u] = False
            for ei, e in enumerate(graph[u]):
                v, cap, cost, _, _, _ = e
                if cap > _EPS and dist[v] > dist[u] + cost + 1e-12:
                    dist[v] = dist[u] + cost
                    parent_node[v] = u
                    parent_edge[v] = ei
                    if not in_queue[v]:
                        in_queue[v] = True
                        queue.append(v)
        if dist[T] == float("inf"):
            return None

        bottleneck = float("inf")
        v = T
        while v != S:
            u = parent_node[v]
            bottleneck = min(bottleneck, graph[u][parent_edge[v]][1])
            v = u
        v = T
        while v != S:
            u = parent_node[v]
            e = graph[u][parent_edge[v]]
            e[1] -= bottleneck
            reverse = graph[v][e[3]]
            reverse[1] += bottleneck
            if e[5]:
                e[4] += bottleneck
            else:
                graph[v][e[3]][4] -= bottleneck
            v = u
        total_flow += bottleneck

    allocation = [[0.0] * num_dests for _ in range(num_sources)]
    for i in range(num_sources):
        for e in graph[i]:
            v, _, _, _, flow, _ = e
            if num_sources <= v < num_sources + num_dests:
                allocation[i][v - num_sources] = flow
    return allocation