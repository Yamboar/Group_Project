from typing import List, Dict, Any, Tuple
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    AllocationDecision,
    TransportationMethod,
)


def _find_least_cost_cell(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    num_sources: int,
    num_dests: int,
) -> Tuple[int, int]:
    """
    Find the cell with the lowest cost among available (unsatisfied) cells.
    A cell is available if its row has remaining supply > 0 and its column
    has remaining demand > 0.

    Tie-breaking rule: choose the cell with the smallest row index,
    and among ties, the smallest column index (most top-left).
    """
    min_cost = float("inf")
    best_i, best_j = -1, -1
    for i in range(num_sources):
        if supply[i] <= 1e-9:
            continue
        for j in range(num_dests):
            if demand[j] <= 1e-9:
                continue
            if cost_matrix[i][j] < min_cost:
                min_cost = cost_matrix[i][j]
                best_i, best_j = i, j
    return best_i, best_j


def solve_least_cost(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using the Least Cost Method.

    Algorithm:
    1. Identify the cell with the lowest transportation cost among all
       available (unallocated) cells.
    2. Allocate the maximum permissible quantity: min(remaining supply, remaining demand).
    3. Update the remaining supply and demand for the corresponding row/column.
    4. If a row's supply is fully exhausted, that row becomes unavailable.
       If a column's demand is fully satisfied, that column becomes unavailable.
    5. Repeat steps 1-4 until all supply and demand are fully satisfied.

    Tie-breaking: If multiple cells share the same minimum cost, select the
    one with the smallest row index first, then smallest column index.

    Returns an InitialSolutionResult with allocation, cost, decisions, and events.
    """
    num_sources = problem.num_sources
    num_dests = problem.num_destinations
    cost_matrix = problem.cost_matrix
    supply = list(problem.supply)
    demand = list(problem.demand)

    allocation = [[0.0] * num_dests for _ in range(num_sources)]
    decisions = []
    intermediate_states = []
    events = []

    events.append({
        "iteration": 0,
        "operation": "start",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": None,
        "explanation": (
            "Starting Least Cost Method. We will repeatedly identify the cell "
            "with the lowest transportation cost and allocate as much as possible."
        ),
    })

    step = 0
    while True:
        i, j = _find_least_cost_cell(cost_matrix, supply, demand, num_sources, num_dests)
        if i == -1:
            break

        step += 1
        alloc_qty = min(supply[i], demand[j])
        cost = cost_matrix[i][j]

        allocation[i][j] = alloc_qty
        supply[i] -= alloc_qty
        demand[j] -= alloc_qty

        available_supply = supply[i] + alloc_qty
        available_demand = demand[j] + alloc_qty

        explanation_parts = [
            f"Step {step}: The lowest cost among available cells is {cost} at cell ({i+1}, {j+1}).",
            f"Available supply = {available_supply}, available demand = {available_demand}.",
            f"Allocate {alloc_qty} units to cell ({i+1}, {j+1}).",
            f"Remaining supply = {supply[i]}, remaining demand = {demand[j]}.",
        ]

        if abs(supply[i]) < 1e-9 and abs(demand[j]) < 1e-9:
            explanation_parts.append(
                f"Both the row (Source {i+1}) and column (Destination {j+1}) are exhausted."
            )
        elif abs(supply[i]) < 1e-9:
            explanation_parts.append(
                f"Source {i+1} supply is exhausted; row {i+1} is no longer available."
            )
        elif abs(demand[j]) < 1e-9:
            explanation_parts.append(
                f"Destination {j+1} demand is satisfied; column {j+1} is no longer available."
            )

        explanation = " ".join(explanation_parts)

        decision = AllocationDecision(
            row=i,
            col=j,
            quantity=alloc_qty,
            supply_remaining=supply[i],
            demand_remaining=demand[j],
            explanation=explanation,
        )
        decisions.append(decision)

        events.append({
            "iteration": step,
            "operation": "allocation",
            "cell": [i, j],
            "quantity": alloc_qty,
            "cost_per_unit": cost,
            "total_cell_cost": alloc_qty * cost,
            "supply_remaining": supply[i],
            "demand_remaining": demand[j],
            "explanation": explanation,
        })

        total_so_far = sum(
            allocation[r][c] * cost_matrix[r][c]
            for r in range(num_sources)
            for c in range(num_dests)
        )
        intermediate_states.append({
            "step": step,
            "cell": [i, j],
            "quantity": alloc_qty,
            "allocation": [row[:] for row in allocation],
            "supply": supply[:],
            "demand": demand[:],
            "total_cost_so_far": total_so_far,
        })

    total_cost = 0.0
    for r in range(num_sources):
        for c in range(num_dests):
            total_cost += allocation[r][c] * cost_matrix[r][c]

    events.append({
        "iteration": step + 1,
        "operation": "complete",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": None,
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
    )
