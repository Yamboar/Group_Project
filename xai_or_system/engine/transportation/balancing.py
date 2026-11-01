from typing import List, Tuple, Dict, Any
from engine.transportation.models import (
    TransportationProblem,
    BalancedTransportationProblem,
)


def balance_problem(
    problem: TransportationProblem,
) -> Tuple[BalancedTransportationProblem, List[Dict[str, Any]]]:
    """
    Balance a transportation problem.
    - If total supply > total demand: add dummy destination with zero costs.
    - If total demand > total supply: add dummy source with zero costs.
    - If balanced: return as-is.
    Returns the balanced problem and a list of balancing events.
    """
    total_supply = problem.total_supply
    total_demand = problem.total_demand
    events = []

    cost_matrix = [row[:] for row in problem.cost_matrix]
    supply = list(problem.supply)
    demand = list(problem.demand)
    source_names = list(problem.source_names)
    dest_names = list(problem.dest_names)
    dummy_source_added = False
    dummy_destination_added = False
    dummy_source_name = None
    dummy_destination_name = None

    if abs(total_supply - total_demand) < 1e-9:
        events.append({
            "type": "balancing",
            "action": "no_change",
            "explanation": (
                f"The problem is already balanced: Total Supply = {total_supply}, "
                f"Total Demand = {total_demand}. No balancing required."
            ),
        })
    elif total_supply > total_demand:
        deficit = total_supply - total_demand
        dummy_destination_name = "Dummy Destination"
        dummy_destination_added = True
        new_dest_col = [0.0] * problem.num_sources
        for i in range(problem.num_sources):
            cost_matrix[i].append(new_dest_col[i])
        demand.append(deficit)
        dest_names.append(dummy_destination_name)
        events.append({
            "type": "balancing",
            "action": "add_dummy_destination",
            "dummy_name": dummy_destination_name,
            "deficit": deficit,
            "explanation": (
                f"Total Supply ({total_supply}) exceeds Total Demand ({total_demand}) "
                f"by {deficit}. A dummy destination '{dummy_destination_name}' has been "
                f"added with demand = {deficit} and zero transportation costs from all sources. "
                f"This represents unused capacity in the supply chain."
            ),
        })
    else:
        deficit = total_demand - total_supply
        dummy_source_name = "Dummy Source"
        dummy_source_added = True
        new_source_row = [0.0] * problem.num_destinations
        cost_matrix.append(new_source_row)
        supply.append(deficit)
        source_names.append(dummy_source_name)
        events.append({
            "type": "balancing",
            "action": "add_dummy_source",
            "dummy_name": dummy_source_name,
            "deficit": deficit,
            "explanation": (
                f"Total Demand ({total_demand}) exceeds Total Supply ({total_supply}) "
                f"by {deficit}. A dummy source '{dummy_source_name}' has been added with "
                f"supply = {deficit} and zero transportation costs to all destinations. "
                f"This represents unmet demand that must be accounted for mathematically."
            ),
        })

    balanced = BalancedTransportationProblem(
        original_problem=problem,
        cost_matrix=cost_matrix,
        supply=supply,
        demand=demand,
        source_names=source_names,
        dest_names=dest_names,
        dummy_source_added=dummy_source_added,
        dummy_destination_added=dummy_destination_added,
        dummy_source_name=dummy_source_name,
        dummy_destination_name=dummy_destination_name,
    )

    return balanced, events
