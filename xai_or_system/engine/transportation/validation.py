from typing import List, Tuple, Optional, Dict, Any
from engine.transportation.models import TransportationProblem


class TransportationValidationError(Exception):
    """Custom exception for transportation problem validation errors."""
    pass


def validate_transportation_problem(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    source_names: Optional[List[str]] = None,
    dest_names: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate a transportation problem input.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []

    if not cost_matrix:
        errors.append("Cost matrix is empty.")
        return False, errors

    if not supply:
        errors.append("Supply vector is empty.")
        return False, errors

    if not demand:
        errors.append("Demand vector is empty.")
        return False, errors

    num_sources = len(supply)
    num_destinations = len(demand)

    if len(cost_matrix) != num_sources:
        errors.append(
            f"Cost matrix has {len(cost_matrix)} rows but {num_sources} supply values provided."
        )
        return False, errors

    for i, row in enumerate(cost_matrix):
        if len(row) != num_destinations:
            errors.append(
                f"Cost matrix row {i} has {len(row)} columns but {num_destinations} demand values provided."
            )
            return False, errors

    for i, row in enumerate(cost_matrix):
        for j, val in enumerate(row):
            if not isinstance(val, (int, float)):
                errors.append(f"Cost matrix[{i}][{j}] = '{val}' is not numeric.")
            elif val < 0:
                errors.append(f"Cost matrix[{i}][{j}] = {val} is negative. Costs must be non-negative.")

    for i, val in enumerate(supply):
        if not isinstance(val, (int, float)):
            errors.append(f"Supply[{i}] = '{val}' is not numeric.")
        elif val < 0:
            errors.append(f"Supply[{i}] = {val} is negative. Supply must be non-negative.")

    for j, val in enumerate(demand):
        if not isinstance(val, (int, float)):
            errors.append(f"Demand[{j}] = '{val}' is not numeric.")
        elif val < 0:
            errors.append(f"Demand[{j}] = {val} is negative. Demand must be non-negative.")

    total_supply = sum(supply)
    total_demand = sum(demand)

    if total_supply == 0:
        errors.append("Total supply is zero. At least one source must have positive supply.")
    if total_demand == 0:
        errors.append("Total demand is zero. At least one destination must have positive demand.")

    if source_names and len(source_names) != num_sources:
        errors.append(
            f"Source names list has {len(source_names)} entries but {num_sources} sources exist."
        )
    if dest_names and len(dest_names) != num_destinations:
        errors.append(
            f"Destination names list has {len(dest_names)} entries but {num_destinations} destinations exist."
        )

    return len(errors) == 0, errors


def create_transportation_problem(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    source_names: Optional[List[str]] = None,
    dest_names: Optional[List[str]] = None,
) -> TransportationProblem:
    """Create a validated TransportationProblem instance or raise an error."""
    is_valid, errors = validate_transportation_problem(cost_matrix, supply, demand, source_names, dest_names)
    if not is_valid:
        raise TransportationValidationError(
            "Transportation problem validation failed:\n" + "\n".join(errors)
        )
    return TransportationProblem(
        cost_matrix=cost_matrix,
        supply=supply,
        demand=demand,
        source_names=source_names,
        dest_names=dest_names,
    )
