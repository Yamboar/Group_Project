from typing import List, Tuple, Dict, Any, Set
from engine.transportation.models import (
    TransportationProblem,
    BalancedTransportationProblem,
    PROHIBITED_COST,
)


def balance_problem(
    problem: TransportationProblem,
) -> Tuple[BalancedTransportationProblem, List[Dict[str, Any]]]:
    """
    Balance a transportation problem so that total supply == total demand.

    Rules:
    - If total_supply > total_demand: add a dummy *destination* absorbing the
      surplus.  All routes from real sources to the dummy destination have cost 0.
      Restricted cells are NOT extended to the dummy column (dummy is always
      available as a "slack" absorber).
    - If total_demand > total_supply: add a dummy *source* covering the shortfall.
      All routes from the dummy source to real destinations have cost 0.
      Same rationale for not restricting dummy rows.
    - If already balanced: return as-is with an explanatory event.

    Any restricted cells from the original problem are preserved in the balanced
    problem's coordinate space (indices are unchanged; the dummy row/column is
    appended at the end and is always index m or n in the balanced matrix).

    Returns (BalancedTransportationProblem, list_of_xai_events).
    """
    total_supply = problem.total_supply
    total_demand = problem.total_demand
    events: List[Dict[str, Any]] = []

    cost_matrix = [row[:] for row in problem.cost_matrix]
    supply = list(problem.supply)
    demand = list(problem.demand)
    source_names = list(problem.source_names)
    dest_names = list(problem.dest_names)
    # Copy restricted cells; dummy rows/cols will never be added to this set.
    restricted_cells: Set[Tuple[int, int]] = set(problem.restricted_cells or set())
    dummy_source_added = False
    dummy_destination_added = False
    dummy_source_name = None
    dummy_destination_name = None

    if abs(total_supply - total_demand) < 1e-9:
        events.append({
            "type": "balancing",
            "operation": "balancing",
            "action": "no_change",
            "total_supply": total_supply,
            "total_demand": total_demand,
            "concise": f"Problem is balanced (Supply = Demand = {total_supply}).",
            "detailed": (
                f"Total supply ({total_supply}) equals total demand ({total_demand}). "
                f"No dummy row or column is required. The problem can be solved directly."
            ),
            "technical": (
                f"ΣS_i = ΣD_j = {total_supply}. "
                f"Balanced condition satisfied; no augmentation needed."
            ),
            "explanation": (
                f"The problem is already balanced: Total Supply = {total_supply}, "
                f"Total Demand = {total_demand}. No balancing required."
            ),
        })

    elif total_supply > total_demand:
        deficit = round(total_supply - total_demand, 10)
        dummy_destination_name = "Dummy Destination"
        dummy_destination_added = True
        # Append a zero-cost column for each source row.
        for i in range(problem.num_sources):
            cost_matrix[i].append(0.0)
        demand.append(deficit)
        dest_names.append(dummy_destination_name)
        events.append({
            "type": "balancing",
            "operation": "balancing",
            "action": "add_dummy_destination",
            "dummy_name": dummy_destination_name,
            "deficit": deficit,
            "total_supply": total_supply,
            "total_demand": total_demand,
            "new_dummy_index": len(demand) - 1,
            "concise": f"Added dummy destination with demand = {deficit}.",
            "detailed": (
                f"Total Supply ({total_supply}) exceeds Total Demand ({total_demand}) "
                f"by {deficit}. A dummy destination '{dummy_destination_name}' has been "
                f"added as column {len(demand)} with demand = {deficit} and zero "
                f"transportation costs from all sources. "
                f"This represents {deficit} units of unused supply capacity."
            ),
            "technical": (
                f"ΣS_i ({total_supply}) > ΣD_j ({total_demand}). "
                f"Surplus = {deficit}. "
                f"Added dummy destination D_{len(demand)} with d_{len(demand)} = {deficit}, "
                f"c_{{i,{len(demand)}}} = 0 ∀i ∈ {{1..{problem.num_sources}}}."
            ),
            "what_if": (
                f"If this dummy destination were not added, the supply/demand imbalance "
                f"of {deficit} units would make the problem mathematically unsolvable as a "
                f"standard transportation problem. The dummy allows allocation of excess supply."
            ),
            "explanation": (
                f"Total Supply ({total_supply}) exceeds Total Demand ({total_demand}) "
                f"by {deficit}. A dummy destination '{dummy_destination_name}' has been "
                f"added with demand = {deficit} and zero transportation costs from all sources."
            ),
        })

    else:
        deficit = round(total_demand - total_supply, 10)
        dummy_source_name = "Dummy Source"
        dummy_source_added = True
        # Append a zero-cost row for each destination column.
        new_source_row = [0.0] * len(demand)
        cost_matrix.append(new_source_row)
        supply.append(deficit)
        source_names.append(dummy_source_name)
        events.append({
            "type": "balancing",
            "operation": "balancing",
            "action": "add_dummy_source",
            "dummy_name": dummy_source_name,
            "deficit": deficit,
            "total_supply": total_supply,
            "total_demand": total_demand,
            "new_dummy_index": len(supply) - 1,
            "concise": f"Added dummy source with supply = {deficit}.",
            "detailed": (
                f"Total Demand ({total_demand}) exceeds Total Supply ({total_supply}) "
                f"by {deficit}. A dummy source '{dummy_source_name}' has been added as "
                f"row {len(supply)} with supply = {deficit} and zero transportation costs "
                f"to all destinations. "
                f"This represents {deficit} units of unmet demand that must be tracked mathematically."
            ),
            "technical": (
                f"ΣD_j ({total_demand}) > ΣS_i ({total_supply}). "
                f"Shortfall = {deficit}. "
                f"Added dummy source S_{len(supply)} with s_{len(supply)} = {deficit}, "
                f"c_{{{len(supply)},j}} = 0 ∀j ∈ {{1..{problem.num_destinations}}}."
            ),
            "what_if": (
                f"If this dummy source were not added, the {deficit} units of excess demand "
                f"could not be allocated and the transportation table would not balance. "
                f"The dummy represents destinations that will receive nothing."
            ),
            "explanation": (
                f"Total Demand ({total_demand}) exceeds Total Supply ({total_supply}) "
                f"by {deficit}. A dummy source '{dummy_source_name}' has been added with "
                f"supply = {deficit} and zero transportation costs to all destinations."
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
        restricted_cells=restricted_cells,
    )

    return balanced, events
