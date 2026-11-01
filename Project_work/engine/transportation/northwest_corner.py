from typing import List, Dict, Any, Set, Tuple
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    AllocationDecision,
    TransportationMethod,
    DegeneracyInfo,
    clean_allocation,
)

_EPS = 1e-9


def _is_available(
    i: int,
    j: int,
    supply: List[float],
    demand: List[float],
    restricted: Set[Tuple[int, int]],
    cost_matrix: List[List[float]],
) -> bool:
    return (
        supply[i] > _EPS
        and demand[j] > _EPS
        and (i, j) not in restricted
    )


def solve_north_west_corner(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using the North-West Corner Method.

    The North-West Corner Method ignores costs entirely; it starts at the
    top-left (north-west) cell and allocates as much as possible before moving
    right (demand satisfied) or down (supply exhausted).

    Restricted cells: if the current north-west cell is restricted, it is
    skipped and the cursor advances (right if demand axis, down if supply axis,
    or diagonally) to find the next available cell.  The skip is recorded as
    an XAI event so it can be explained.

    Degeneracy: detected when the number of basic variables after the full
    allocation phase is less than m + n - 1.  A DegeneracyInfo record is
    attached to the result and an event is emitted.

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
        "concise": "Starting North-West Corner Method.",
        "detailed": (
            "Starting North-West Corner Method on a "
            f"{num_sources}x{num_dests} balanced transportation table. "
            "We start at the top-left (north-west) cell and allocate the minimum of "
            "available supply and demand, moving right when demand is satisfied and "
            "down when supply is exhausted."
        ),
        "technical": (
            f"Initializing NW-Corner on {num_sources}x{num_dests} BTP. "
            f"Cursor starts at (1,1). Allocation rule: x_{{ij}} = min(s_i, d_j)."
        ),
        "explanation": (
            "Starting North-West Corner Method. We begin at the top-left (north-west) "
            "cell of the cost matrix, which is position (1, 1)."
        ),
    })

    i, j = 0, 0
    step = 0

    while i < num_sources and j < num_dests:
        # Advance past restricted or fully satisfied rows/columns.
        if (i, j) in restricted:
            events.append({
                "iteration": step,
                "operation": "skip_restricted",
                "cell": [i, j],
                "concise": f"Skipped restricted cell ({i+1},{j+1}).",
                "detailed": (
                    f"Cell ({i+1},{j+1}) is a restricted route and cannot be used. "
                    f"The North-West Corner cursor advances past this cell."
                ),
                "technical": (
                    f"Cell ({i+1},{j+1}) ∈ restricted set. Cursor advances."
                ),
                "explanation": f"Cell ({i+1},{j+1}) is restricted; skipping.",
            })
            # Advance: try right first, then down.
            if j + 1 < num_dests:
                j += 1
            else:
                i += 1
            continue

        step += 1
        alloc_qty = min(supply[i], demand[j])
        cost = cost_matrix[i][j]

        pre_supply = supply[i]
        pre_demand = demand[j]

        allocation[i][j] = alloc_qty
        supply[i] -= alloc_qty
        demand[j] -= alloc_qty

        cell_i, cell_j = i, j
        simultaneous = abs(supply[cell_i]) < _EPS and abs(demand[cell_j]) < _EPS

        move_reason = ""
        if simultaneous:
            move_reason = (
                f"Both supply at Source {cell_i+1} and demand at Destination {cell_j+1} "
                f"are simultaneously exhausted. This causes degeneracy unless handled. "
                f"Cursor moves diagonally to ({cell_i+2},{cell_j+2})."
            )
            i += 1
            j += 1
        elif abs(supply[cell_i]) < _EPS:
            move_reason = (
                f"Supply at Source {cell_i+1} is exhausted. "
                f"Cursor moves down to row {cell_i+2}."
            )
            i += 1
        elif abs(demand[cell_j]) < _EPS:
            move_reason = (
                f"Demand at Destination {cell_j+1} is satisfied. "
                f"Cursor moves right to column {cell_j+2}."
            )
            j += 1

        explanation = (
            f"Step {step}: Cell ({cell_i+1},{cell_j+1}), cost={cost}. "
            f"Supply available={pre_supply}, demand available={pre_demand}. "
            f"Allocate min({pre_supply},{pre_demand})={alloc_qty}. "
            f"Supply remaining={supply[cell_i] if cell_i < num_sources else 0}, "
            f"Demand remaining={demand[cell_j] if cell_j < num_dests else 0}. "
            + move_reason
        )

        decision = AllocationDecision(
            row=cell_i,
            col=cell_j,
            quantity=alloc_qty,
            supply_remaining=supply[cell_i] if cell_i < num_sources else 0,
            demand_remaining=demand[cell_j] if cell_j < num_dests else 0,
            explanation=explanation,
            tie_broken=False,
            tie_break_reason=(
                "North-West Corner does not use costs; position determines selection."
            ),
        )
        decisions.append(decision)

        events.append({
            "iteration": step,
            "operation": "allocation",
            "cell": [cell_i, cell_j],
            "quantity": alloc_qty,
            "cost_per_unit": cost,
            "total_cell_cost": alloc_qty * cost,
            "supply_before": pre_supply,
            "demand_before": pre_demand,
            "supply_remaining": supply[cell_i] if cell_i < num_sources else 0,
            "demand_remaining": demand[cell_j] if cell_j < num_dests else 0,
            "simultaneous_exhaustion": simultaneous,
            "move_reason": move_reason,
            "concise": (
                f"Allocate {alloc_qty} to ({cell_i+1},{cell_j+1}), cost={cost}."
            ),
            "detailed": explanation,
            "technical": (
                f"x_{{{cell_i+1},{cell_j+1}}} = min(s_{cell_i+1}={pre_supply}, "
                f"d_{cell_j+1}={pre_demand}) = {alloc_qty}. "
                f"Cost contribution = {alloc_qty*cost}."
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
            "cell": [cell_i, cell_j],
            "quantity": alloc_qty,
            "allocation": [row[:] for row in allocation],
            "supply": supply[:],
            "demand": demand[:],
            "total_cost_so_far": total_so_far,
        })

    # ── Residual completion + repair ─────────────────────────────────────────
    # The cursor skip logic can strand supply/demand when restricted cells
    # remove routes (advancing past a restricted cell may skip whole rows or
    # columns that are still usable). Complete the residual with the cheapest
    # open cells; if that is impossible, repair with a min-cost flow.
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
        method_label="North-West Corner",
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
            method_label="North-West Corner",
            start_step=step,
            decisions=decisions,
            events=events,
            intermediate_states=intermediate_states,
        )

    # ── Degeneracy detection ────────────────────────────────────────────────
    required_bv = num_sources + num_dests - 1
    actual_bv = sum(
        1
        for r in range(num_sources)
        for c in range(num_dests)
        if allocation[r][c] >= _EPS
    )
    degenerate = actual_bv < required_bv
    epsilon_cells: List[Tuple[int, int]] = []

    if degenerate:
        # Add epsilon allocations to reach the required basis size.
        # Choose cells in row-major order that do not already have an allocation.
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
            f"Degeneracy detected after North-West Corner allocation: "
            f"only {actual_bv} basic variables, but m+n-1 = {required_bv} are required. "
            f"Added ε allocations to cells "
            f"{[(r+1,c+1) for r,c in epsilon_cells]} to maintain a valid basis."
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
                f"ε-perturbation applied to cells "
                f"{[(r+1,c+1) for r,c in epsilon_cells]} to restore full rank."
            ),
            "why": (
                "When two constraints (supply and demand) are satisfied simultaneously "
                "at a single allocation step, only one basic variable is created instead "
                "of two, leaving the basis short. This degeneracy must be resolved by "
                "introducing a small ε value so that the Stepping Stone loops remain valid."
            ),
            "explanation": deg_explanation,
        })

    degeneracy_info = DegeneracyInfo(
        detected=degenerate,
        stage="initial",
        required_basic_vars=required_bv,
        actual_basic_vars=actual_bv,
        epsilon_cells_added=epsilon_cells,
        explanation=deg_explanation if degenerate else "No degeneracy detected.",
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
        "concise": f"NW Corner complete. Total cost = {total_cost}.",
        "detailed": (
            f"North-West Corner Method complete after {step} allocation step(s). "
            f"Total transportation cost = {total_cost}. "
            f"Basic variables: {actual_bv if not degenerate else required_bv} "
            f"(required: {required_bv})."
        ),
        "technical": (
            f"NW-Corner terminated. Z = {total_cost}. "
            f"|B| = {actual_bv if not degenerate else required_bv}, m+n-1 = {required_bv}."
        ),
        "explanation": (
            f"North-West Corner Method complete. Total cost = {total_cost}. "
            f"Allocated {step} cells total."
        ),
    })

    return InitialSolutionResult(
        method=TransportationMethod.NORTH_WEST,
        allocation=allocation,
        total_cost=total_cost,
        decisions=decisions,
        intermediate_states=intermediate_states,
        events=events,
        degeneracy_info=degeneracy_info,
    )
