from typing import List, Dict, Any, Tuple, Optional
from engine.transportation.models import (
    BalancedTransportationProblem,
    InitialSolutionResult,
    AllocationDecision,
    TransportationMethod,
)


def _get_two_smallest(values: List[float]) -> Tuple[float, float]:
    """Return the two smallest values from a list. If all same, return (val, val)."""
    finite_vals = [v for v in values if v < float("inf")]
    if len(finite_vals) == 0:
        return float("inf"), float("inf")
    if len(finite_vals) == 1:
        return finite_vals[0], float("inf")
    sorted_vals = sorted(finite_vals)
    return sorted_vals[0], sorted_vals[1]


def _calculate_penalties(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    num_sources: int,
    num_dests: int,
) -> Tuple[List[float], List[float]]:
    """
    Calculate row and column penalties for Vogel's Approximation Method.
    Penalty for a row = difference between the two smallest costs in available cells of that row.
    Penalty for a column = difference between the two smallest costs in available cells of that column.
    A cell is available if its row has remaining supply > 0 and column has remaining demand > 0.
    """
    row_penalties = []
    for i in range(num_sources):
        available_costs = []
        if supply[i] <= 1e-9:
            row_penalties.append(float("inf"))
            continue
        for j in range(num_dests):
            if demand[j] > 1e-9:
                available_costs.append(cost_matrix[i][j])
        if len(available_costs) < 2:
            row_penalties.append(float("inf") if len(available_costs) == 0 else available_costs[0])
        else:
            s1, s2 = _get_two_smallest(available_costs)
            row_penalties.append(s2 - s1)

    col_penalties = []
    for j in range(num_dests):
        available_costs = []
        if demand[j] <= 1e-9:
            col_penalties.append(float("inf"))
            continue
        for i in range(num_sources):
            if supply[i] > 1e-9:
                available_costs.append(cost_matrix[i][j])
        if len(available_costs) < 2:
            col_penalties.append(float("inf") if len(available_costs) == 0 else available_costs[0])
        else:
            s1, s2 = _get_two_smallest(available_costs)
            col_penalties.append(s2 - s1)

    return row_penalties, col_penalties


def _select_best_penalty_cell(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    row_penalties: List[float],
    col_penalties: List[float],
    num_sources: int,
    num_dests: int,
) -> Tuple[Optional[int], Optional[int], str]:
    """
    Select the cell based on Vogel's criterion:
    1. Find the maximum penalty among all rows and columns.
    2. If max penalty is from a row, select the cheapest available cell in that row.
    3. If max penalty is from a column, select the cheapest available cell in that column.
    4. Tie-breaking: prefer rows over columns, and among same-type ties, prefer smaller index.
    """
    max_penalty = -1
    best_source = None  # index if row is selected
    best_dest = None  # index if column is selected
    select_type = "row"

    for i in range(num_sources):
        if row_penalties[i] == float("inf"):
            continue
        if row_penalties[i] > max_penalty:
            max_penalty = row_penalties[i]
            best_source = i
            select_type = "row"

    for j in range(num_dests):
        if col_penalties[j] == float("inf"):
            continue
        if col_penalties[j] > max_penalty:
            max_penalty = col_penalties[j]
            best_dest = j
            select_type = "column"
            best_source = None

    if select_type == "row" and best_source is not None:
        min_cost = float("inf")
        best_j = -1
        for j in range(num_dests):
            if demand[j] > 1e-9 and cost_matrix[best_source][j] < min_cost:
                min_cost = cost_matrix[best_source][j]
                best_j = j
        return best_source, best_j, "row"

    if select_type == "column" and best_dest is not None:
        min_cost = float("inf")
        best_i = -1
        for i in range(num_sources):
            if supply[i] > 1e-9 and cost_matrix[i][best_dest] < min_cost:
                min_cost = cost_matrix[i][best_dest]
                best_i = i
        return best_i, best_dest, "column"

    return None, None, "none"


def solve_vogel(
    problem: BalancedTransportationProblem,
) -> InitialSolutionResult:
    """
    Solve a balanced transportation problem using Vogel's Approximation Method.

    Algorithm:
    1. For each row, calculate the penalty as the difference between the two
       smallest costs in available cells of that row.
    2. For each column, calculate the penalty as the difference between the two
       smallest costs in available cells of that column.
    3. Select the row or column with the maximum penalty.
       Tie-breaking: rows preferred over columns; smaller index preferred.
    4. In the selected row or column, find the cell with the lowest cost.
    5. Allocate min(remaining supply, remaining demand) to that cell.
    6. Update supply and demand. Remove exhausted rows/columns.
    7. Repeat until all supply and demand are satisfied.

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
            "Starting Vogel's Approximation Method. We will calculate penalties "
            "(difference between two smallest costs) for each row and column, "
            "then allocate based on the highest penalty."
        ),
    })

    step = 0
    while True:
        row_penalties, col_penalties = _calculate_penalties(
            cost_matrix, supply, demand, num_sources, num_dests
        )

        i, j, select_type = _select_best_penalty_cell(
            cost_matrix, supply, demand, row_penalties, col_penalties,
            num_sources, num_dests,
        )

        if i is None or j is None:
            break

        step += 1
        alloc_qty = min(supply[i], demand[j])
        cost = cost_matrix[i][j]

        allocation[i][j] = alloc_qty
        supply[i] -= alloc_qty
        demand[j] -= alloc_qty

        penalty_desc = f"Row penalties = {[p if p != float('inf') else 'N/A' for p in row_penalties]}, "
        penalty_desc += f"Column penalties = {[p if p != float('inf') else 'N/A' for p in col_penalties]}"

        explanation_parts = [
            f"Step {step}: {penalty_desc}.",
            f"Maximum penalty is in {'row' if select_type == 'row' else 'column'} "
            f"{'Source' if select_type == 'row' else 'Destination'} "
            f"{i+1 if select_type == 'row' else j+1}.",
            f"Lowest cost cell in this {'row' if select_type == 'row' else 'column'} "
            f"is ({i+1}, {j+1}) with cost = {cost}.",
            f"Available supply = {supply[i] + alloc_qty}, available demand = {demand[j] + alloc_qty}.",
            f"Allocate {alloc_qty} units.",
            f"Remaining supply = {supply[i]}, remaining demand = {demand[j]}.",
        ]

        if abs(supply[i]) < 1e-9:
            explanation_parts.append(f"Source {i+1} supply exhausted.")
        if abs(demand[j]) < 1e-9:
            explanation_parts.append(f"Destination {j+1} demand satisfied.")

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
            "row_penalties": [p if p != float("inf") else None for p in row_penalties],
            "col_penalties": [p if p != float("inf") else None for p in col_penalties],
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
            "row_penalties": row_penalties[:],
            "col_penalties": col_penalties[:],
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
    )
