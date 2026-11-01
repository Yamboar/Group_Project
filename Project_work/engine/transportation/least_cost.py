from typing import List, Dict, Any, Tuple, Optional, Set
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    AllocationDecision,
    TransportationMethod,
    DegeneracyInfo,
    clean_allocation,
)

_EPS = 1e-9


def _find_least_cost_cell(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    num_sources: int,
    num_dests: int,
    restricted: Set[Tuple[int, int]],
) -> Tuple[int, int, float, List[Dict[str, Any]]]:
    """
    Find the cell with the lowest cost among all available (non-restricted,
    non-exhausted) cells.

    Tie-breaking rule (documented for XAI): when multiple cells share the
    same minimum cost, the cell with the smallest row index is chosen; among
    row ties, the smallest column index is chosen (top-left preference).

    Returns (best_i, best_j, min_cost, all_candidates_info).
    all_candidates_info is a list of every evaluated cell for XAI reporting.
    """
    min_cost = float("inf")
    best_i, best_j = -1, -1
    all_candidates: List[Dict[str, Any]] = []

    for i in range(num_sources):
        if supply[i] <= _EPS:
            continue
        for j in range(num_dests):
            if demand[j] <= _EPS:
                continue
            if (i, j) in restricted:
                continue
            c = cost_matrix[i][j]
            is_tie = abs(c - min_cost) < _EPS
            is_new_min = c < min_cost - _EPS
            all_candidates.append({
                "cell": [i, j],
                "cost": c,
                "supply_available": supply[i],
                "demand_available": demand[j],
                "selected": False,
            })
            if is_new_min or (is_tie and best_i == -1):
                min_cost = c
                best_i, best_j = i, j

    # Mark the selected candidate.
    for cand in all_candidates:
        if cand["cell"] == [best_i, best_j]:
            cand["selected"] = True

    return best_i, best_j, min_cost, all_candidates


def solve_least_cost(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using the Least Cost Method.

    At each step the globally cheapest available (non-restricted) cell is
    chosen and allocated as much as possible.  Restricted cells are skipped
    entirely and noted in the XAI events.

    Tie-breaking: smallest row index, then smallest column index.  The
    tie-breaking decision is recorded in the AllocationDecision so the XAI
    layer can report it.

    Degeneracy is detected and handled at the end (same epsilon-perturbation
    strategy as NW Corner).

    Returns an InitialSolutionResult.
    """
    num_sources = problem.num_sources
    num_dests = problem.num_destinations
    cost_matrix = problem.cost_matrix
    restricted = problem.restricted_cells or set()
    supply = list(problem.supply)
    demand = list(problem.demand)

    allocation = [[0.0] * num_dests for _ in range(num_sources)]
    decisions: List[AllocationDecision] = []
    intermediate_states: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

    events.append({
        "iteration": 0,
        "operation": "start",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": None,
        "concise": "Starting Least Cost Method.",
        "detailed": (
            f"Starting Least Cost Method on a {num_sources}x{num_dests} balanced "
            "transportation table. At each step, the cell with the lowest cost among "
            "all available (non-restricted, non-exhausted) cells is selected. "
            "Tie-breaking: smallest row index, then smallest column index."
        ),
        "technical": (
            f"Initializing Least Cost Method on {num_sources}x{num_dests} BTP. "
            "Selection rule: argmin_{{(i,j) available}} c_{{ij}}. "
            "Tie-break: lexicographic (i, j) ascending."
        ),
        "explanation": (
            "Starting Least Cost Method. We will repeatedly identify the cell "
            "with the lowest transportation cost and allocate as much as possible."
        ),
    })

    step = 0
    while True:
        best_i, best_j, min_cost, candidates = _find_least_cost_cell(
            cost_matrix, supply, demand, num_sources, num_dests, restricted
        )
        if best_i == -1:
            break

        step += 1

        # Detect ties for XAI reporting.
        tied_cells = [
            c for c in candidates
            if abs(c["cost"] - min_cost) < _EPS and c["cell"] != [best_i, best_j]
        ]
        tie_broken = len(tied_cells) > 0
        tie_break_reason = ""
        if tie_broken:
            tied_str = ", ".join(
                f"({t['cell'][0]+1},{t['cell'][1]+1})" for t in tied_cells
            )
            tie_break_reason = (
                f"Tie detected: cells {tied_str} also have cost {min_cost}. "
                f"Selected ({best_i+1},{best_j+1}) because it has the smallest row "
                f"index, then smallest column index (top-left preference)."
            )

        pre_supply = supply[best_i]
        pre_demand = demand[best_j]
        alloc_qty = min(pre_supply, pre_demand)
        cost = cost_matrix[best_i][best_j]

        allocation[best_i][best_j] = alloc_qty
        supply[best_i] -= alloc_qty
        demand[best_j] -= alloc_qty

        simultaneous = abs(supply[best_i]) < _EPS and abs(demand[best_j]) < _EPS
        exhaust_note = ""
        if simultaneous:
            exhaust_note = (
                f" Both Source {best_i+1} and Destination {best_j+1} are "
                f"simultaneously exhausted — potential degeneracy."
            )
        elif abs(supply[best_i]) < _EPS:
            exhaust_note = f" Source {best_i+1} is now exhausted."
        elif abs(demand[best_j]) < _EPS:
            exhaust_note = f" Destination {best_j+1} demand is now satisfied."

        explanation = (
            f"Step {step}: Lowest cost among available cells = {cost} at "
            f"({best_i+1},{best_j+1}). "
            f"Supply available = {pre_supply}, demand available = {pre_demand}. "
            f"Allocate min({pre_supply},{pre_demand}) = {alloc_qty}.{exhaust_note}"
            + (f" {tie_break_reason}" if tie_broken else "")
        )

        decision = AllocationDecision(
            row=best_i,
            col=best_j,
            quantity=alloc_qty,
            supply_remaining=supply[best_i],
            demand_remaining=demand[best_j],
            explanation=explanation,
            alternatives_considered=[
                {"cell": [c["cell"][0]+1, c["cell"][1]+1], "cost": c["cost"]}
                for c in candidates if not c["selected"]
            ],
            tie_broken=tie_broken,
            tie_break_reason=tie_break_reason,
        )
        decisions.append(decision)

        events.append({
            "iteration": step,
            "operation": "allocation",
            "cell": [best_i, best_j],
            "quantity": alloc_qty,
            "cost_per_unit": cost,
            "total_cell_cost": alloc_qty * cost,
            "supply_before": pre_supply,
            "demand_before": pre_demand,
            "supply_remaining": supply[best_i],
            "demand_remaining": demand[best_j],
            "simultaneous_exhaustion": simultaneous,
            "tie_broken": tie_broken,
            "tie_break_reason": tie_break_reason,
            "all_candidates": candidates,
            "concise": f"Allocate {alloc_qty} to ({best_i+1},{best_j+1}), cost={cost}.",
            "detailed": explanation,
            "technical": (
                f"x_{{{best_i+1},{best_j+1}}} = min(s_{best_i+1}={pre_supply}, "
                f"d_{best_j+1}={pre_demand}) = {alloc_qty}. "
                f"c_{{{best_i+1},{best_j+1}}} = {cost}. "
                f"Cost contribution = {alloc_qty*cost}."
            ),
            "why_selected": (
                f"Cell ({best_i+1},{best_j+1}) was selected because its cost {cost} "
                f"is the lowest among all available cells."
                + (f" {tie_break_reason}" if tie_broken else "")
            ),
            "why_rejected": [
                {
                    "cell": [c["cell"][0]+1, c["cell"][1]+1],
                    "cost": c["cost"],
                    "reason": (
                        f"Cost {c['cost']} > minimum cost {min_cost}."
                        if abs(c["cost"] - min_cost) > _EPS
                        else f"Same cost {c['cost']} but ({best_i+1},{best_j+1}) chosen by tie-break rule."
                    ),
                }
                for c in candidates if not c["selected"]
            ],
            "explanation": explanation,
        })

        total_so_far = sum(
            allocation[r][c] * cost_matrix[r][c]
            for r in range(num_sources)
            for c in range(num_dests)
        )
        intermediate_states.append({
            "step": step,
            "cell": [best_i, best_j],
            "quantity": alloc_qty,
            "allocation": [row[:] for row in allocation],
            "supply": supply[:],
            "demand": demand[:],
            "total_cost_so_far": total_so_far,
        })

    # ── Residual completion + repair ─────────────────────────────────────────
    # The greedy phase can strand supply/demand when the cheapest open cells
    # consume a row/column that uniquely serves another column/row via a
    # restricted-cell-free route. Complete the residual with the cheapest open
    # cells; if that is impossible, repair with a min-cost flow.
    from engine.transportation._residual import (
        complete_residual,
        repair_allocation,
    )

    residual_steps, all_consumed = complete_residual(
        allocation=allocation,
        supply=supply,
        demand=demand,
        cost_matrix=cost_matrix,
        restricted=restricted,
        method_label="Least Cost",
        start_step=step,
        decisions=decisions,
        events=events,
        intermediate_states=intermediate_states,
    )
    step += residual_steps
    if not all_consumed:
        step += repair_allocation(
            allocation=allocation,
            supply=supply,
            demand=demand,
            original_supply=list(problem.supply),
            original_demand=list(problem.demand),
            cost_matrix=cost_matrix,
            restricted=restricted,
            method_label="Least Cost",
            start_step=step,
            decisions=decisions,
            events=events,
            intermediate_states=intermediate_states,
        )

    # ── Degeneracy detection ────────────────────────────────────────────────
    required_bv = num_sources + num_dests - 1
    actual_bv = sum(
        1 for r in range(num_sources)
        for c in range(num_dests)
        if allocation[r][c] >= _EPS
    )
    degenerate = actual_bv < required_bv
    epsilon_cells: List[Tuple[int, int]] = []

    if degenerate:
        needed = required_bv - actual_bv
        for r in range(num_sources):
            if needed == 0:
                break
            for c in range(num_dests):
                if needed == 0:
                    break
                if allocation[r][c] < _EPS and (r, c) not in restricted:
                    allocation[r][c] = _EPS
                    epsilon_cells.append((r, c))
                    needed -= 1

        deg_explanation = (
            f"Degeneracy detected after Least Cost allocation: "
            f"only {actual_bv} basic variables, but m+n-1 = {required_bv} are required. "
            f"Added ε allocations to cells "
            f"{[(r+1,c+1) for r,c in epsilon_cells]}."
        )
        events.append({
            "operation": "degeneracy",
            "stage": "initial",
            "required_basic_vars": required_bv,
            "actual_basic_vars": actual_bv,
            "epsilon_cells": [(r+1, c+1) for r, c in epsilon_cells],
            "concise": f"Degeneracy: added ε to {len(epsilon_cells)} cell(s).",
            "detailed": deg_explanation,
            "technical": (
                f"Degenerate BFS: |B| = {actual_bv} < m+n-1 = {required_bv}. "
                f"ε-perturbation applied to {[(r+1,c+1) for r,c in epsilon_cells]}."
            ),
            "why": (
                "Simultaneous exhaustion of supply and demand at one step creates fewer "
                "basic variables than required for a non-degenerate basis. "
                "An ε value is introduced so the Stepping Stone method can construct "
                "valid closed loops."
            ),
            "explanation": deg_explanation,
        })
    else:
        deg_explanation = "No degeneracy detected."

    degeneracy_info = DegeneracyInfo(
        detected=degenerate,
        stage="initial",
        required_basic_vars=required_bv,
        actual_basic_vars=actual_bv,
        epsilon_cells_added=epsilon_cells,
        explanation=deg_explanation,
    )

    # Strip degeneracy ε artifacts so the reported allocation is clean.
    allocation = clean_allocation(allocation)

    total_cost = sum(
        allocation[r][c] * cost_matrix[r][c]
        for r in range(num_sources)
        for c in range(num_dests)
        if allocation[r][c] > _EPS
    )

    events.append({
        "iteration": step + 1,
        "operation": "complete",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": None,
        "final_cost": total_cost,
        "num_basic_vars": actual_bv if not degenerate else required_bv,
        "degenerate": degenerate,
        "concise": f"Least Cost Method complete. Total cost = {total_cost}.",
        "detailed": (
            f"Least Cost Method complete after {step} allocation step(s). "
            f"Total transportation cost = {total_cost}."
        ),
        "technical": (
            f"LCM terminated. Z = {total_cost}. "
            f"|B| = {actual_bv if not degenerate else required_bv}, m+n-1 = {required_bv}."
        ),
        "explanation": (
            f"Least Cost Method complete. Total cost = {total_cost}. "
            f"Allocated {step} cells total."
        ),
    })

    return InitialSolutionResult(
        method=TransportationMethod.LEAST_COST,
        allocation=allocation,
        total_cost=total_cost,
        decisions=decisions,
        intermediate_states=intermediate_states,
        events=events,
        degeneracy_info=degeneracy_info,
    )
