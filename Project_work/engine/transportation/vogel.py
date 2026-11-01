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
_INF = float("inf")


def _two_smallest(values: List[float]) -> Tuple[float, float]:
    """Return the two smallest finite values. Returns (v, inf) if only one exists."""
    finite = sorted(v for v in values if v < _INF)
    if len(finite) == 0:
        return _INF, _INF
    if len(finite) == 1:
        return finite[0], _INF
    return finite[0], finite[1]


def _calculate_penalties(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    num_sources: int,
    num_dests: int,
    restricted: Set[Tuple[int, int]],
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """
    Calculate Vogel row and column penalties.

    Penalty = difference between the two smallest costs in available cells.
    An available cell (i,j) requires supply[i]>0, demand[j]>0, and (i,j) not
    restricted.

    Returns (row_penalties, col_penalties) where None means the row/col is
    fully exhausted (inactive).
    """
    row_penalties: List[Optional[float]] = []
    for i in range(num_sources):
        if supply[i] <= _EPS:
            row_penalties.append(None)
            continue
        costs = [
            cost_matrix[i][j]
            for j in range(num_dests)
            if demand[j] > _EPS
            and (i, j) not in restricted
        ]
        if len(costs) == 0:
            row_penalties.append(None)
        elif len(costs) == 1:
            row_penalties.append(costs[0])
        else:
            s1, s2 = _two_smallest(costs)
            row_penalties.append(s2 - s1)

    col_penalties: List[Optional[float]] = []
    for j in range(num_dests):
        if demand[j] <= _EPS:
            col_penalties.append(None)
            continue
        costs = [
            cost_matrix[i][j]
            for i in range(num_sources)
            if supply[i] > _EPS
            and (i, j) not in restricted
        ]
        if len(costs) == 0:
            col_penalties.append(None)
        elif len(costs) == 1:
            col_penalties.append(costs[0])
        else:
            s1, s2 = _two_smallest(costs)
            col_penalties.append(s2 - s1)

    return row_penalties, col_penalties


def _select_cell(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    row_penalties: List[Optional[float]],
    col_penalties: List[Optional[float]],
    num_sources: int,
    num_dests: int,
    restricted: Set[Tuple[int, int]],
) -> Tuple[Optional[int], Optional[int], str, str, bool]:
    """
    Select the row or column with the maximum penalty, then the cheapest
    available cell within it.

    Tie-breaking: rows are preferred over columns.  Among equal-penalty rows,
    the smallest index is preferred (and vice-versa for columns).

    Returns (row_idx, col_idx, select_type, tie_break_note, tie_broken).
    select_type is "row" or "column".
    """
    best_penalty = -_INF
    best_type = None
    best_idx = -1
    tie_broken = False
    tie_candidates: List[str] = []

    # Scan rows first.
    for i, p in enumerate(row_penalties):
        if p is None:
            continue
        if p > best_penalty + _EPS:
            best_penalty = p
            best_type = "row"
            best_idx = i
            tie_candidates = [f"row {i+1}"]
        elif abs(p - best_penalty) <= _EPS:
            tie_candidates.append(f"row {i+1}")

    # Scan columns; a column beats a row only if strictly greater.
    for j, p in enumerate(col_penalties):
        if p is None:
            continue
        if p > best_penalty + _EPS:
            best_penalty = p
            best_type = "column"
            best_idx = j
            tie_candidates = [f"column {j+1}"]
        elif abs(p - best_penalty) <= _EPS:
            tie_candidates.append(f"column {j+1}")

    if best_type is None:
        return None, None, "none", "", False

    # Among ties: rows preferred over columns; smaller index within same type.
    row_tied = [tc for tc in tie_candidates if tc.startswith("row")]
    if row_tied:
        # Pick smallest row index.
        idx = min(int(tc.split()[1]) - 1 for tc in row_tied)
        if best_type != "row" or best_idx != idx:
            tie_broken = True
        best_type = "row"
        best_idx = idx
    # else keep best_type == "column" with smallest index already found.

    tie_note = ""
    if len(tie_candidates) > 1:
        tie_note = (
            f"Tie in maximum penalty ({best_penalty}) among: "
            f"{', '.join(tie_candidates)}. "
            f"Selected {'row' if best_type=='row' else 'column'} {best_idx+1} "
            f"(rows preferred over columns; smallest index within same type)."
        )

    # Find the cheapest available cell in the selected row or column.
    if best_type == "row":
        min_cost = _INF
        best_j = -1
        for j in range(num_dests):
            if (
                demand[j] > _EPS
                and (best_idx, j) not in restricted
            ):
                if cost_matrix[best_idx][j] < min_cost - _EPS:
                    min_cost = cost_matrix[best_idx][j]
                    best_j = j
        return best_idx, best_j, "row", tie_note, tie_broken

    else:
        min_cost = _INF
        best_i = -1
        for i in range(num_sources):
            if (
                supply[i] > _EPS
                and (i, best_idx) not in restricted
            ):
                if cost_matrix[i][best_idx] < min_cost - _EPS:
                    min_cost = cost_matrix[i][best_idx]
                    best_i = i
        return best_i, best_idx, "column", tie_note, tie_broken


def solve_vogel(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using Vogel's Approximation Method.

    Vogel computes a "penalty" for each row and column as the difference between
    the two cheapest available costs, then allocates to the cheapest cell in the
    row/column with the highest penalty.  This generally produces a near-optimal
    initial solution.

    Restricted cells are skipped when computing penalties and when selecting
    the allocation cell.

    Degeneracy is detected and corrected via ε-perturbation.

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
        "concise": "Starting Vogel's Approximation Method.",
        "detailed": (
            f"Starting Vogel's Approximation Method on a {num_sources}x{num_dests} "
            "balanced transportation table. "
            "At each step, row and column penalties (difference between the two cheapest "
            "available costs) are computed. The row or column with the highest penalty is "
            "selected and the cheapest available cell within it is allocated."
        ),
        "technical": (
            f"Initializing VAM on {num_sources}x{num_dests} BTP. "
            "Penalty_i = min2(c_ij for available j) - min1(c_ij). "
            "Select max penalty; allocate to argmin_j c_{{best_i,j}}."
        ),
        "explanation": (
            "Starting Vogel's Approximation Method. We will calculate penalties "
            "(difference between two smallest costs) for each row and column, "
            "then allocate based on the highest penalty."
        ),
    })

    step = 0
    while True:
        row_penalties, col_penalties = _calculate_penalties(
            cost_matrix, supply, demand, num_sources, num_dests, restricted
        )

        sel_i, sel_j, select_type, tie_note, tie_broken = _select_cell(
            cost_matrix, supply, demand,
            row_penalties, col_penalties,
            num_sources, num_dests, restricted,
        )

        if sel_i is None or sel_j is None:
            break

        step += 1
        pre_supply = supply[sel_i]
        pre_demand = demand[sel_j]
        alloc_qty = min(pre_supply, pre_demand)
        cost = cost_matrix[sel_i][sel_j]

        allocation[sel_i][sel_j] = alloc_qty
        supply[sel_i] -= alloc_qty
        demand[sel_j] -= alloc_qty

        simultaneous = abs(supply[sel_i]) < _EPS and abs(demand[sel_j]) < _EPS

        # Build human-readable penalty table string.
        rp_str = [
            f"{p:.4g}" if p is not None else "N/A"
            for p in row_penalties
        ]
        cp_str = [
            f"{p:.4g}" if p is not None else "N/A"
            for p in col_penalties
        ]

        penalty_table_note = (
            f"Row penalties = [{', '.join(rp_str)}], "
            f"Column penalties = [{', '.join(cp_str)}]."
        )

        entity_label = (
            f"Source {sel_i+1}" if select_type == "row"
            else f"Destination {sel_j+1}"
        )
        max_penalty_val = (
            row_penalties[sel_i] if select_type == "row" else col_penalties[sel_j]
        )

        explanation = (
            f"Step {step}: {penalty_table_note} "
            f"Maximum penalty = {max_penalty_val} at {select_type} ({entity_label}). "
            f"Cheapest cell in that {select_type}: ({sel_i+1},{sel_j+1}) with cost={cost}. "
            f"Allocate min({pre_supply},{pre_demand})={alloc_qty}."
            + (f" {tie_note}" if tie_note else "")
            + (" Simultaneous exhaustion — potential degeneracy." if simultaneous else "")
        )

        decision = AllocationDecision(
            row=sel_i,
            col=sel_j,
            quantity=alloc_qty,
            supply_remaining=supply[sel_i],
            demand_remaining=demand[sel_j],
            explanation=explanation,
            tie_broken=tie_broken,
            tie_break_reason=tie_note,
        )
        decisions.append(decision)

        events.append({
            "iteration": step,
            "operation": "allocation",
            "cell": [sel_i, sel_j],
            "quantity": alloc_qty,
            "cost_per_unit": cost,
            "total_cell_cost": alloc_qty * cost,
            "supply_before": pre_supply,
            "demand_before": pre_demand,
            "supply_remaining": supply[sel_i],
            "demand_remaining": demand[sel_j],
            "row_penalties": [p for p in row_penalties],
            "col_penalties": [p for p in col_penalties],
            "selected_type": select_type,
            "selected_index": sel_i if select_type == "row" else sel_j,
            "max_penalty": max_penalty_val,
            "simultaneous_exhaustion": simultaneous,
            "tie_broken": tie_broken,
            "tie_break_reason": tie_note,
            "concise": f"Allocate {alloc_qty} to ({sel_i+1},{sel_j+1}), cost={cost}.",
            "detailed": explanation,
            "technical": (
                f"Penalty({select_type} {sel_i+1 if select_type=='row' else sel_j+1}) "
                f"= {max_penalty_val}. "
                f"x_{{{sel_i+1},{sel_j+1}}} = min({pre_supply},{pre_demand}) = {alloc_qty}. "
                f"Z += {alloc_qty * cost}."
            ),
            "why_selected": (
                f"{select_type.capitalize()} {entity_label} has the highest penalty "
                f"({max_penalty_val}), meaning the regret of not using the cheapest cell "
                f"here is greatest. Cell ({sel_i+1},{sel_j+1}) has the lowest cost ({cost}) "
                f"in that {select_type}."
                + (f" {tie_note}" if tie_note else "")
            ),
            "explanation": explanation,
        })

        total_so_far = sum(
            allocation[r][c] * cost_matrix[r][c]
            for r in range(num_sources)
            for c in range(num_dests)
        )
        intermediate_states.append({
            "step": step,
            "cell": [sel_i, sel_j],
            "quantity": alloc_qty,
            "row_penalties": [p for p in row_penalties],
            "col_penalties": [p for p in col_penalties],
            "allocation": [row[:] for row in allocation],
            "supply": supply[:],
            "demand": demand[:],
            "total_cost_so_far": total_so_far,
        })

    # ── Residual completion + repair ─────────────────────────────────────────
    # The penalty loop can strand supply/demand when restricted cells remove
    # routes (a row/column may turn "inactive" while another still needs it).
    # Complete the residual with the cheapest open cells; if that is
    # impossible, repair with a min-cost flow.
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
        method_label="Vogel",
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
            method_label="Vogel",
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
            f"Degeneracy detected after Vogel allocation: "
            f"only {actual_bv} basic variables, but m+n-1 = {required_bv} required. "
            f"Added ε to cells {[(r+1,c+1) for r,c in epsilon_cells]}."
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
                f"ε-perturbation to {[(r+1,c+1) for r,c in epsilon_cells]}."
            ),
            "why": (
                "A simultaneous row-and-column exhaustion at one step creates only one "
                "basic variable instead of two, leaving the basis short by the deficit. "
                "ε-values restore the required m+n-1 basic variables."
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
        "concise": f"Vogel's Method complete. Total cost = {total_cost}.",
        "detailed": (
            f"Vogel's Approximation Method complete after {step} step(s). "
            f"Total transportation cost = {total_cost}."
        ),
        "technical": (
            f"VAM terminated. Z = {total_cost}. "
            f"|B| = {actual_bv if not degenerate else required_bv}, m+n-1 = {required_bv}."
        ),
        "explanation": (
            f"Vogel's Approximation Method complete. Total cost = {total_cost}. "
            f"Allocated {step} cells total."
        ),
    })

    return InitialSolutionResult(
        method=TransportationMethod.VOGEL,
        allocation=allocation,
        total_cost=total_cost,
        decisions=decisions,
        intermediate_states=intermediate_states,
        events=events,
        degeneracy_info=degeneracy_info,
    )
