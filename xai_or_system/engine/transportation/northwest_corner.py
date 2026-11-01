from typing import List, Dict, Any
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    AllocationDecision,
    TransportationMethod,
)


def solve_north_west_corner(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using the North-West Corner Method.

    Algorithm:
    1. Start at the top-left (north-west) cell of the cost matrix.
    2. Allocate the minimum of available supply and remaining demand.
    3. Update supply and demand, then move:
       - If supply is exhausted, move to the next row (down).
       - If demand is exhausted, move to the next column (right).
       - If both are exhausted simultaneously, move diagonally (down-right).
    4. Repeat until all supply and demand are satisfied.

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

    i, j = 0, 0
    step = 0

    events.append({
        "iteration": 0,
        "operation": "start",
        "cell": None,
        "quantity": None,
        "cost_per_unit": None,
        "total_cell_cost": None,
        "explanation": (
            "Starting North-West Corner Method. We begin at the top-left (north-west) "
            "cell of the cost matrix, which is position (1, 1)."
        ),
    })

    while i < num_sources and j < num_dests:
        step += 1
        alloc_qty = min(supply[i], demand[j])
        cost = cost_matrix[i][j]

        allocation[i][j] = alloc_qty
        supply[i] -= alloc_qty
        demand[j] -= alloc_qty

        cell_i, cell_j = i, j

        explanation_parts = [
            f"Step {step}: At cell ({cell_i+1}, {cell_j+1}) with cost per unit = {cost}.",
            f"Available supply at Source {cell_i+1} = {supply[cell_i] + alloc_qty}.",
            f"Remaining demand at Destination {cell_j+1} = {demand[cell_j] + alloc_qty}.",
            f"Allocate {alloc_qty} units (minimum of {supply[cell_i] + alloc_qty} and {demand[cell_j] + alloc_qty}).",
            f"After allocation: Supply remaining = {supply[cell_i]}, Demand remaining = {demand[cell_j]}.",
        ]

        if abs(supply[cell_i]) < 1e-9 and abs(demand[cell_j]) < 1e-9:
            explanation_parts.append(
                f"Both supply and demand are exactly zero. Move diagonally to cell ({cell_i+2}, {cell_j+2})."
            )
            i += 1
            j += 1
        elif abs(supply[cell_i]) < 1e-9:
            explanation_parts.append(
                f"Supply for Source {cell_i+1} is exhausted. Move down to row {cell_i+2}."
            )
            i += 1
        elif abs(demand[cell_j]) < 1e-9:
            explanation_parts.append(
                f"Demand for Destination {cell_j+1} is satisfied. Move right to column {cell_j+2}."
            )
            j += 1

        explanation = " ".join(explanation_parts)

        decision = AllocationDecision(
            row=cell_i,
            col=cell_j,
            quantity=alloc_qty,
            supply_remaining=supply[cell_i] if cell_i < num_sources else 0,
            demand_remaining=demand[cell_j] if cell_j < num_dests else 0,
            explanation=explanation,
        )
        decisions.append(decision)

        events.append({
            "iteration": step,
            "operation": "allocation",
            "cell": [cell_i, cell_j],
            "quantity": alloc_qty,
            "cost_per_unit": cost,
            "total_cell_cost": alloc_qty * cost,
            "supply_remaining": supply[cell_i] if cell_i < num_sources else 0,
            "demand_remaining": demand[cell_j] if cell_j < num_dests else 0,
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
    )
