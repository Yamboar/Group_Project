from typing import List, Tuple, Optional, Dict, Any, Set
from engine.transportation.models import TransportationProblem, PROHIBITED_COST


class TransportationValidationError(Exception):
    """Custom exception for transportation problem validation errors."""
    pass


def _active_open_cell_graph(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    restricted_cells: Set[Tuple[int, int]],
) -> Tuple[List[int], List[int], Set[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    """Return active source/destination indices and open edges of the
    non-restricted transportation graph.

    Active sources have positive supply; active destinations have positive
    demand. An edge (source, dest) exists when the cell is not restricted.
    Cells already carrying the legacy PROHIBITED_COST sentinel are also left
    out so old inputs keep behaving as restricted.
    """
    num_sources = len(supply)
    num_dests = len(demand)
    active_rows = [
        i for i in range(num_sources) if supply[i] > 1e-9
    ]
    active_cols = [
        j for j in range(num_dests) if demand[j] > 1e-9
    ]
    edges: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
    for i in active_rows:
        for j in active_cols:
            if (i, j) in restricted_cells:
                continue
            if cost_matrix[i][j] >= PROHIBITED_COST:
                continue
            edges.add(("s", i, "d", j))
    return active_rows, active_cols, edges


def _check_feasibility_with_restrictions(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    restricted_cells: Set[Tuple[int, int]],
) -> Tuple[bool, List[str]]:
    """
    Verify that a feasible solution exists despite restricted cells.

    The authoritative check is a max-flow over the bipartite network of open
    (non-restricted) routes: the problem is feasible exactly when the maximum
    flow saturates total demand. Before that we also emit the practical,
    human-readable diagnostics (cut-off sources/destinations, capacity
    shortfalls) because they explain the failure much better than a bare
    max-flow result. Finally, if a feasible flow exists but the open network
    is disconnected, the problem is reported as infeasible *for the
    optimizing solver*: Stepping Stone needs a connected basis, so a problem
    whose open routes split into balanced components cannot be optimized and
    the message says so explicitly.
    """
    issues = []
    num_sources = len(supply)
    num_dests = len(demand)

    # Feasibility is evaluated on the BALANCED problem: when totals differ,
    # the balancing stage appends a dummy source or dummy destination with
    # zero-cost, never-restricted routes. Without this, the max-flow test
    # would wrongly reject an unbalanced-but-feasible problem.
    bal_supply = list(supply)
    bal_demand = list(demand)
    bal_costs = [row[:] for row in cost_matrix]
    total_supply = sum(bal_supply)
    total_demand = sum(bal_demand)
    bal_restricted = set(restricted_cells)
    if total_supply < total_demand:
        bal_supply.append(total_demand - total_supply)
        bal_costs.append([0.0] * num_dests)
        num_sources += 1
    elif total_demand < total_supply:
        bal_demand.append(total_supply - total_demand)
        for row in bal_costs:
            row.append(0.0)
        num_dests += 1

    def _open(i: int, j: int) -> bool:
        return (
            (i, j) not in bal_restricted
            and bal_costs[i][j] < PROHIBITED_COST
        )

    # Check every source has at least one available destination.
    for i in range(num_sources):
        if bal_supply[i] <= 1e-9:
            continue
        if not any(_open(i, j) for j in range(num_dests)):
            issues.append(
                f"Source {i+1} has positive supply ({bal_supply[i]}) but all routes from it "
                f"are restricted. No feasible solution exists."
            )

    # Check every destination has at least one available source.
    for j in range(num_dests):
        if bal_demand[j] <= 1e-9:
            continue
        if not any(_open(i, j) for i in range(num_sources)):
            issues.append(
                f"Destination {j+1} has positive demand ({bal_demand[j]}) but all routes "
                f"to it are restricted. No feasible solution exists."
            )

    # Capacity-reachability check: for each destination j, the maximum
    # supply that can flow into it is sum of supply[i] for non-restricted (i,j).
    # If that maximum < demand[j], the problem is infeasible.
    for j in range(num_dests):
        if bal_demand[j] <= 1e-9:
            continue
        max_inflow = sum(
            bal_supply[i] for i in range(num_sources) if _open(i, j)
        )
        if max_inflow < bal_demand[j] - 1e-9:
            issues.append(
                f"Destination {j+1} requires {bal_demand[j]} units but only {max_inflow:.6g} "
                f"units of supply can reach it through available (non-restricted) routes. "
                f"No feasible solution exists."
            )

    # Symmetric check for sources.
    for i in range(num_sources):
        if bal_supply[i] <= 1e-9:
            continue
        max_outflow = sum(
            bal_demand[j] for j in range(num_dests) if _open(i, j)
        )
        if max_outflow < bal_supply[i] - 1e-9:
            issues.append(
                f"Source {i+1} has {bal_supply[i]} units of supply but can only send "
                f"{max_outflow:.6g} units through available (non-restricted) routes. "
                f"No feasible solution exists."
            )

    # Authoritative max-flow feasibility test over the open bipartite network.
    total_demand_bal = sum(bal_demand)
    if len(issues) == 0 and total_demand_bal > 1e-9:
        maxflow = _max_open_flow(
            bal_costs, bal_supply, bal_demand, bal_restricted
        )
        if maxflow < total_demand_bal - 1e-9:
            issues.append(
                f"The open (non-restricted) routes can carry at most "
                f"{maxflow:.6g} units in total, but total demand is "
                f"{total_demand_bal:.6g}. No feasible solution exists with the "
                f"current restrictions."
            )

    # Connectivity check for the optimizing solver. A feasible transportation
    # problem whose open network is disconnected CANNOT be solved by the
    # Stepping Stone method, which needs a single connected basis.
    if len(issues) == 0:
        active_rows, active_cols, edges = _active_open_cell_graph(
            bal_costs, bal_supply, bal_demand, bal_restricted
        )
        active_nodes = set(("s", i) for i in active_rows) | set(("d", j) for j in active_cols)
        if active_rows and active_cols:
            adjacency: Dict[Tuple[str, int], List[Tuple[str, int]]] = {
                node: [] for node in active_nodes
            }
            for (kind_i, i, kind_j, j) in edges:
                adjacency[("s", i)].append(("d", j))
                adjacency[("d", j)].append(("s", i))
            seen: Set[Tuple[str, int]] = set()
            stack = [next(iter(active_nodes))]
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(adjacency[node])
            if len(seen) < len(active_nodes):
                missing = sorted(
                    active_nodes - seen, key=lambda n: (n[0], n[1])
                )
                missing_parts = []
                for (k, idx) in missing:
                    label = f"Source {idx+1}" if k == "s" else f"Destination {idx+1}"
                    missing_parts.append(label)
                issues.append(
                    "The transportation table splits into isolated components: "
                    + ", ".join(missing_parts)
                    + " cannot be reached through any open route. Although a "
                    "feasible cost exists per component, the Stepping Stone "
                    "optimization requires a single connected network of open "
                    "routes. Add an open route linking the components, or "
                    "remove a restriction, then re-run."
                )

    return len(issues) == 0, issues


def _max_open_flow(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    restricted_cells: Set[Tuple[int, int]],
) -> float:
    """
    Maximum amount of flow deliverable through open (non-restricted) routes.

    Simple Edmonds-Karp over the bipartite network:
      super-source -> source_i (cap supply[i])
      source_i -> dest_j (cap inf) for every open cell
      dest_j -> super-sink (cap demand[j])
    Returns the total flow when no more augmenting paths exist.
    """
    num_sources = len(supply)
    num_dests = len(demand)
    S = num_sources + num_dests
    T = S + 1
    n_nodes = T + 1
    cap = [[0.0] * n_nodes for _ in range(n_nodes)]

    for i in range(num_sources):
        if supply[i] > 1e-9:
            cap[S][i] = supply[i]
    for j in range(num_dests):
        if demand[j] > 1e-9:
            cap[num_sources + j][T] = demand[j]
    for i in range(num_sources):
        for j in range(num_dests):
            if (i, j) in restricted_cells:
                continue
            if cost_matrix[i][j] >= PROHIBITED_COST:
                continue
            cap[i][num_sources + j] = float("inf")

    total_flow = 0.0
    while True:
        parent = [-1] * n_nodes
        parent[S] = S
        queue = [S]
        found = False
        while queue:
            u = queue.pop(0)
            if u == T:
                found = True
                break
            for v in range(n_nodes):
                if cap[u][v] > 1e-9 and parent[v] == -1:
                    parent[v] = u
                    queue.append(v)
        if not found:
            break
        # Find bottleneck along the path.
        bottleneck = float("inf")
        v = T
        while v != S:
            u = parent[v]
            bottleneck = min(bottleneck, cap[u][v])
            v = u
        v = T
        while v != S:
            u = parent[v]
            cap[u][v] -= bottleneck
            cap[v][u] += bottleneck
            v = u
        total_flow += bottleneck
        # Stop early once all demand is satisfied.
        if total_flow >= sum(demand) - 1e-9:
            break

    return total_flow


def validate_transportation_problem(
    cost_matrix: List[List[Optional[float]]],
    supply: List[float],
    demand: List[float],
    source_names: Optional[List[str]] = None,
    dest_names: Optional[List[str]] = None,
    restricted_cells: Optional[Set[Tuple[int, int]]] = None,
    prohibited_routes: Optional[Set[Tuple[int, int]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate a transportation problem input.

    Checks:
    - Non-empty cost matrix, supply, demand.
    - Consistent dimensions.
    - All values numeric; blanks are rejected with guidance.
    - Costs are 0 or greater; negatives are rejected with guidance to use
      Restricted instead.
    - Non-negative supply and demand.
    - Non-zero total supply and total demand.
    - Restricted cells are in-bounds and the problem stays feasible.
    - Duplicate name warnings (appended as warnings, not errors).

    Returns (is_valid, list_of_error_messages).
    Errors are fatal; callers should check len(errors) == 0 for validity.
    """
    errors = []

    # Merge the legacy alias into the canonical restricted set.
    restricted = set(restricted_cells or set())
    if prohibited_routes:
        restricted |= set(prohibited_routes)

    if not isinstance(cost_matrix, list) or not cost_matrix:
        errors.append("Cost matrix is empty.")
        return False, errors

    if not isinstance(supply, list) or not supply:
        errors.append("Supply vector is empty.")
        return False, errors

    if not isinstance(demand, list) or not demand:
        errors.append("Demand vector is empty.")
        return False, errors

    num_sources = len(supply)
    num_destinations = len(demand)

    if len(cost_matrix) != num_sources:
        errors.append(
            f"Cost matrix has {len(cost_matrix)} rows but {num_sources} supply values provided."
        )
        return False, errors

    expected_cols = len(cost_matrix[0]) if cost_matrix else 0
    if expected_cols == 0:
        errors.append("Cost matrix row 0 is empty.")
        return False, errors

    for i, row in enumerate(cost_matrix):
        if not isinstance(row, list):
            errors.append(f"Cost matrix row {i} is not a list.")
            return False, errors
        if len(row) != num_destinations:
            errors.append(
                f"Cost matrix row {i} has {len(row)} columns but {num_destinations} "
                f"demand values provided."
            )
            return False, errors

    # Validate restricted route indices are within bounds.
    bad_routes = [
        (i, j) for (i, j) in restricted
        if i < 0 or i >= num_sources or j < 0 or j >= num_destinations
    ]
    if bad_routes:
        errors.append(
            f"Restricted cells contain out-of-range indices: {bad_routes}. "
            f"Valid range: rows 0..{num_sources-1}, cols 0..{num_destinations-1}."
        )
        return False, errors

    # Validate individual cell values. Restricted cells are exempt: their cost
    # value is irrelevant because the route is not usable.
    for i, row in enumerate(cost_matrix):
        for j, val in enumerate(row):
            if (i, j) in restricted:
                continue
            if val is None:
                errors.append(
                    f"Cost matrix[{i+1}][{j+1}] is blank. "
                    f"Enter a cost of 0 or greater, or mark the cell as Restricted "
                    f"if transportation on that route is not allowed."
                )
            elif not isinstance(val, (int, float)):
                errors.append(
                    f"Cost matrix[{i+1}][{j+1}] = '{val}' is not numeric. "
                    f"Enter a cost of 0 or greater, or mark the cell as Restricted."
                )
            elif val < 0:
                errors.append(
                    f"Cost matrix[{i+1}][{j+1}] = {val} is negative. "
                    f"Transportation costs must be 0 or greater. "
                    f"If transportation on that route is not allowed, mark the cell "
                    f"as Restricted instead of entering a negative value."
                )

    # Validate supply values.
    for i, val in enumerate(supply):
        if not isinstance(val, (int, float)):
            errors.append(f"Supply[{i+1}] = '{val}' is not numeric.")
        elif val < 0:
            errors.append(
                f"Supply[{i+1}] = {val} is negative. Supply must be non-negative."
            )

    # Validate demand values.
    for j, val in enumerate(demand):
        if not isinstance(val, (int, float)):
            errors.append(f"Demand[{j+1}] = '{val}' is not numeric.")
        elif val < 0:
            errors.append(
                f"Demand[{j+1}] = {val} is negative. Demand must be non-negative."
            )

    # Validate restricted cells only reference numeric cost rows (structure is
    # already validated above; nothing more needed here).

    # If any structural errors so far, stop before totals check.
    if errors:
        return False, errors

    total_supply = sum(supply)
    total_demand = sum(demand)

    if total_supply <= 1e-9:
        errors.append(
            "Total supply is zero. At least one source must have positive supply."
        )
    if total_demand <= 1e-9:
        errors.append(
            "Total demand is zero. At least one destination must have positive demand."
        )

    # Name dimension checks.
    if source_names is not None and len(source_names) != num_sources:
        errors.append(
            f"Source names list has {len(source_names)} entries but {num_sources} sources exist."
        )
    if dest_names is not None and len(dest_names) != num_destinations:
        errors.append(
            f"Destination names list has {len(dest_names)} entries but {num_destinations} "
            f"destinations exist."
        )

    # Duplicate name warnings (treated as errors to surface to the user).
    if source_names is not None:
        seen = {}
        for idx, name in enumerate(source_names):
            if name in seen:
                errors.append(
                    f"Duplicate source name '{name}' at positions {seen[name]+1} and {idx+1}."
                )
            seen[name] = idx
    if dest_names is not None:
        seen = {}
        for idx, name in enumerate(dest_names):
            if name in seen:
                errors.append(
                    f"Duplicate destination name '{name}' at positions {seen[name]+1} and {idx+1}."
                )
            seen[name] = idx

    if errors:
        return False, errors

    # Restricted-route feasibility check.
    feasible, feasibility_issues = _check_feasibility_with_restrictions(
        cost_matrix, supply, demand, restricted
    )
    if not feasible:
        errors.extend(feasibility_issues)

    return len(errors) == 0, errors


def create_transportation_problem(
    cost_matrix: List[List[float]],
    supply: List[float],
    demand: List[float],
    source_names: Optional[List[str]] = None,
    dest_names: Optional[List[str]] = None,
    restricted_cells: Optional[Set[Tuple[int, int]]] = None,
    prohibited_routes: Optional[Set[Tuple[int, int]]] = None,
) -> TransportationProblem:
    """Create a validated TransportationProblem instance or raise an error."""
    is_valid, errors = validate_transportation_problem(
        cost_matrix, supply, demand, source_names, dest_names,
        restricted_cells, prohibited_routes,
    )
    if not is_valid:
        raise TransportationValidationError(
            "Transportation problem validation failed:\n" + "\n".join(errors)
        )
    merged = set(restricted_cells or set())
    if prohibited_routes:
        merged |= set(prohibited_routes)
    return TransportationProblem(
        cost_matrix=cost_matrix,
        supply=supply,
        demand=demand,
        source_names=source_names,
        dest_names=dest_names,
        restricted_cells=merged,
    )