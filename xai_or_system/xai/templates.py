from typing import Dict, Any

TRANSPORTATION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "start": {
        "concise": "Starting {method} algorithm.",
        "detailed": "Starting {method} to find an initial basic feasible solution for the transportation problem with {num_sources} sources and {num_destinations} destinations.",
        "technical": "Initializing {method} on a {num_sources}x{num_destinations} balanced transportation problem.",
    },
    "allocation": {
        "concise": "Allocate {quantity} units to cell ({row}, {col}) at cost {cost}.",
        "detailed": (
            "At cell ({row}, {col}) with cost per unit = {cost}: "
            "Available supply = {available_supply}, available demand = {available_demand}. "
            "Allocate {quantity} units (minimum of {available_supply} and {available_demand}). "
            "Remaining supply = {supply_remaining}, remaining demand = {demand_remaining}."
        ),
        "technical": (
            "Cell ({row},{col}): min(supply={available_supply}, demand={available_demand}) = {quantity}. "
            "x[{row},{col}] = {quantity}. Supply remaining = {supply_remaining}, "
            "demand remaining = {demand_remaining}."
        ),
    },
    "complete": {
        "concise": "Algorithm complete. Total cost = {total_cost}.",
        "detailed": "{method} complete. Total transportation cost = {total_cost}.",
        "technical": "{method} terminated. Z = Σ(c_ij * x_ij) = {total_cost}.",
    },
}

BALANCING_TEMPLATES: Dict[str, Dict[str, str]] = {
    "no_change": {
        "concise": "Problem is balanced (Supply = Demand = {total}).",
        "detailed": "Total supply ({total_supply}) equals total demand ({total_demand}). No balancing required.",
        "technical": "ΣS_i = ΣD_j = {total}. Problem is balanced; no dummy rows/columns needed.",
    },
    "add_dummy_destination": {
        "concise": "Added dummy destination with demand = {deficit}.",
        "detailed": (
            "Total Supply ({total_supply}) exceeds Total Demand ({total_demand}) by {deficit}. "
            "A dummy destination '{dummy_name}' has been added with demand = {deficit} "
            "and zero costs to represent unused capacity."
        ),
        "technical": (
            "ΣS_i ({total_supply}) > ΣD_j ({total_demand}). "
            "Deficit = {deficit}. Added dummy destination D_n+1 with d_{n+1} = {deficit}, "
            "c_i,n+1 = 0 ∀i."
        ),
    },
    "add_dummy_source": {
        "concise": "Added dummy source with supply = {deficit}.",
        "detailed": (
            "Total Demand ({total_demand}) exceeds Total Supply ({total_supply}) by {deficit}. "
            "A dummy source '{dummy_name}' has been added with supply = {deficit} "
            "and zero costs to represent unmet demand."
        ),
        "technical": (
            "ΣD_j ({total_demand}) > ΣS_i ({total_supply}). "
            "Deficit = {deficit}. Added dummy source S_m+1 with s_{m+1} = {deficit}, "
            "c_m+1,j = 0 ∀j."
        ),
    },
}

STEPPING_STONE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "start_optimization": {
        "concise": "Starting Stepping Stone optimization from cost = {initial_cost}.",
        "detailed": (
            "Starting Stepping Stone method to improve the initial feasible solution. "
            "Initial cost = {initial_cost}. We will examine all unoccupied cells."
        ),
        "technical": (
            "Initializing MODI/Stepping Stone on BFS with Z_0 = {initial_cost}. "
            "Will evaluate improvement indices for all non-basic cells."
        ),
    },
    "iteration": {
        "concise": "Iteration {iteration}: Enter ({entering_row}, {entering_col}), cost reduction = {cost_reduction}.",
        "detailed": (
            "Iteration {iteration}: Selected entering cell ({entering_row}, {entering_col}) "
            "with improvement index = {improvement_index:.2f}. "
            "Closed loop: {loop}. Adjustment quantity = {adjustment_quantity}. "
            "Cost: {old_cost:.2f} -> {new_cost:.2f} (reduction = {cost_reduction:.2f})."
        ),
        "technical": (
            "Iteration {iteration}: Candidate ({entering_row},{entering_col}) has "
            "ΔZ = {improvement_index:.2f} < 0. Loop: {loop}. "
            "θ = min(x at '-' positions) = {adjustment_quantity}. "
            "Updated Z: {old_cost:.2f} → {new_cost:.2f}."
        ),
    },
    "optimality_reached": {
        "concise": "Solution is optimal at cost = {total_cost}.",
        "detailed": (
            "No improving candidates remain. All non-basic cells have non-negative "
            "improvement indices. The solution with cost = {total_cost} is optimal."
        ),
        "technical": (
            "Optimality test passed: ΔZ_k ≥ 0 for all non-basic cells k. "
            "Current BFS is optimal with Z* = {total_cost}."
        ),
    },
}

HUNGARIAN_TEMPLATES: Dict[str, Dict[str, str]] = {
    "start": {
        "concise": "Starting Hungarian Method.",
        "detailed": "Starting Hungarian Method for the assignment problem.",
        "technical": "Initializing Hungarian algorithm on balanced assignment matrix.",
    },
    "row_reduction": {
        "concise": "Row reduction complete.",
        "detailed": "Subtracted the minimum value of each row from all elements in that row.",
        "technical": "Row reduction: a'_ij = a_ij - min_i(a_ij). Row minimums: {row_minimums}.",
    },
    "column_reduction": {
        "concise": "Column reduction complete.",
        "detailed": "Subtracted the minimum value of each column from all elements in that column.",
        "technical": "Column reduction: a''_ij = a'_ij - min_j(a'_ij). Column minimums: {col_minimums}.",
    },
    "cover_zeros": {
        "concise": "Covered zeros with {num_lines} line(s).",
        "detailed": "Covered all zeros using {num_lines} line(s). Matrix size = {matrix_size}.",
        "technical": "Minimum line cover = {num_lines}. {'Optimal assignment possible.' if {num_lines} >= {matrix_size} else 'Matrix adjustment required.'}",
    },
    "matrix_adjustment": {
        "concise": "Adjusted matrix with min uncovered = {min_uncovered}.",
        "detailed": (
            "Smallest uncovered value = {min_uncovered}. "
            "Subtract from uncovered cells, add to intersection cells."
        ),
        "technical": (
            "δ = min uncovered = {min_uncovered}. "
            "a_ij -= δ for uncovered cells; a_ij += δ for intersection cells."
        ),
    },
    "complete": {
        "concise": "Optimal assignment cost = {total_cost}.",
        "detailed": "Hungarian Method complete. Optimal total assignment cost = {total_cost}.",
        "technical": "Hungarian algorithm terminated. Z* = {total_cost}.",
    },
}
