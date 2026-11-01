from typing import List, Optional, Dict, Any, Set, Tuple
from engine.transportation.models import (
    TransportationProblem,
    BalancedTransportationProblem,
    TransportationMethod,
    InitialSolutionResult,
    OptimizedSolutionResult,
    WhatIfTransportationResult,
    EPSILON,
)
from engine.transportation.validation import validate_transportation_problem, TransportationValidationError
from engine.transportation.balancing import balance_problem
from engine.transportation.northwest_corner import solve_north_west_corner
from engine.transportation.least_cost import solve_least_cost
from engine.transportation.vogel import solve_vogel
from engine.transportation.stepping_stone import solve_stepping_stone


class TransportationSolver:
    """
    Orchestrates the complete transportation problem solving pipeline:
    validation → balancing → initial solution → optimization → verification.

    Supports:
    - Restricted cells (routes completely unavailable; kept as a separate cell
      state and never represented by a large artificial cost).
    - Degeneracy detection and reporting at every stage.
    - Alternative optima identification.
    - What-if analysis (re-solve with modified parameters and compare).
    """

    def solve(
        self,
        cost_matrix: List[List[float]],
        supply: List[float],
        demand: List[float],
        method: TransportationMethod,
        source_names: Optional[List[str]] = None,
        dest_names: Optional[List[str]] = None,
        optimize: bool = True,
        restricted_cells: Optional[List[List[int]]] = None,
        prohibited_routes: Optional[List[List[int]]] = None,
    ) -> Dict[str, Any]:
        """
        Solve a transportation problem end-to-end.

        restricted_cells: list of [row, col] pairs (0-indexed) that are
        forbidden.  These cells are excluded from allocation by all methods.
        prohibited_routes is accepted as a backwards-compatible alias.

        Returns a result dict with full XAI event log.
        """
        result: Dict[str, Any] = {
            "success": False,
            "errors": [],
            "warnings": [],
            "validation": None,
            "balancing": None,
            "problem": None,
            "balanced_problem": None,
            "initial_solution": None,
            "optimized_solution": None,
            "verification": None,
            "final_cost": 0.0,
            "is_degenerate": False,
            "has_alternative_optima": False,
            "alternative_optima_cells": [],
            "events": [],
        }

        # Convert restricted_cells (and its legacy alias) to a set of tuples.
        restricted: Set[Tuple[int, int]] = set()
        sources = list(restricted_cells or [])
        if prohibited_routes:
            sources += list(prohibited_routes)
        for pr in sources:
            if isinstance(pr, (list, tuple)) and len(pr) == 2:
                restricted.add((int(pr[0]), int(pr[1])))

        # Keep the cost matrix as the user provided it. Restricted cells stay
        # as a separate state; they are never rewritten to an artificial cost.
        working_matrix = [row[:] for row in cost_matrix]

        is_valid, errors = validate_transportation_problem(
            working_matrix, supply, demand, source_names, dest_names, restricted
        )
        if not is_valid:
            result["errors"] = errors
            result["events"].append({
                "operation": "validation_failed",
                "errors": errors,
                "concise": "Validation failed.",
                "detailed": "Input validation failed: " + "; ".join(errors),
                "technical": "Validation errors: " + "; ".join(errors),
                "explanation": "Validation failed. " + "; ".join(errors),
            })
            return result

        result["validation"] = {"is_valid": True, "errors": []}

        problem = TransportationProblem(
            cost_matrix=working_matrix,
            supply=supply,
            demand=demand,
            source_names=source_names,
            dest_names=dest_names,
            restricted_cells=restricted,
        )

        balanced_problem, balancing_events = balance_problem(problem)
        result["balancing"] = {
            "is_balanced": problem.is_balanced,
            "dummy_source_added": balanced_problem.dummy_source_added,
            "dummy_destination_added": balanced_problem.dummy_destination_added,
            "events": balancing_events,
        }
        result["problem"] = problem
        result["balanced_problem"] = balanced_problem
        result["events"].extend(balancing_events)

        # Zero-capacity sources / destinations are formalised as dummy entries:
        # they get no allocation, but the user is explicitly warned so the
        # behaviour is never silent.
        zero_supply = [
            i for i, s in enumerate(supply) if s <= 1e-9
        ]
        zero_demand = [
            j for j, d in enumerate(demand) if d <= 1e-9
        ]
        result["zero_supply_sources"] = [i+1 for i in zero_supply]
        result["zero_demand_destinations"] = [j+1 for j in zero_demand]
        if zero_supply:
            names = ", ".join(
                f"{problem.source_names[i]} (Source {i+1})" for i in zero_supply
            )
            result["warnings"].append(
                f"Source(s) with 0 supply: {names}. They are treated as dummy — "
                f"no material will be allocated from them."
            )
        if zero_demand:
            names = ", ".join(
                f"{problem.dest_names[j]} (Destination {j+1})" for j in zero_demand
            )
            result["warnings"].append(
                f"Destination(s) with 0 demand: {names}. They are treated as dummy — "
                f"no material will be allocated to them."
            )

        # Initial solution.
        if method == TransportationMethod.NORTH_WEST:
            initial = solve_north_west_corner(balanced_problem)
        elif method == TransportationMethod.LEAST_COST:
            initial = solve_least_cost(balanced_problem)
        elif method == TransportationMethod.VOGEL:
            initial = solve_vogel(balanced_problem)
        else:
            result["errors"] = [f"Unknown method: {method}"]
            return result

        result["initial_solution"] = initial
        result["events"].extend(initial.events)

        if initial.degeneracy_info and initial.degeneracy_info.detected:
            result["is_degenerate"] = True
            result["warnings"].append(initial.degeneracy_info.explanation)
            result["events"].append({
                "operation": "degeneracy_reported",
                "stage": "initial",
                "explanation": initial.degeneracy_info.explanation,
            })

        if optimize:
            optimized = solve_stepping_stone(balanced_problem, initial)
            result["optimized_solution"] = optimized
            result["has_alternative_optima"] = optimized.has_alternative_optima
            result["alternative_optima_cells"] = [
                [r+1, c+1] for r, c in optimized.alternative_optima_cells
            ]
            result["degenerate_pivot_count"] = optimized.degenerate_pivot_count
            result["events"].extend(optimized.events)

            if optimized.hit_iteration_limit:
                result["warnings"].append(
                    f"Stepping Stone reached the iteration limit without proving optimality. "
                    f"The solution cost ({optimized.total_cost}) may not be optimal."
                )

            if optimized.has_alternative_optima:
                result["warnings"].append(
                    f"Alternative optimal solutions exist. Non-basic cells "
                    f"{[[r+1,c+1] for r,c in optimized.alternative_optima_cells]} "
                    f"have zero improvement index and could be entered without "
                    f"changing the total cost."
                )

            # Degeneracy summary — the methodology is fully automatic (ε keeps
            # a valid basis) but must never be silent. Report every stage where
            # a degenerate basis was observed: the initial BFS and any pivots.
            deg_stages = []
            if initial.degeneracy_info and initial.degeneracy_info.detected:
                deg_stages.append("initial solution")
            if optimized.degenerate_pivot_count:
                deg_stages.append(f"{optimized.degenerate_pivot_count} pivot(s)")
            if deg_stages:
                result["warnings"].append(
                    f"Degeneracy was detected and handled at: {', '.join(deg_stages)}. "
                    f"ε-perturbation kept a valid spanning-tree basis throughout. "
                    f"This is expected behaviour, not an error."
                )

            result["events"].append({
                "operation": "optimization",
                "is_optimal": optimized.is_optimal,
                "hit_iteration_limit": optimized.hit_iteration_limit,
                "has_alternative_optima": optimized.has_alternative_optima,
                "degenerate_pivot_count": optimized.degenerate_pivot_count,
                "explanation": optimized.explanation,
            })
            result["final_cost"] = optimized.total_cost
        else:
            result["final_cost"] = initial.total_cost

        final_alloc = (
            result["optimized_solution"].allocation if optimize
            else initial.allocation
        )

        verification = self._verify_solution(
            balanced_problem, final_alloc, result["final_cost"]
        )
        result["verification"] = verification

        if not verification["passed"]:
            result["warnings"].append(
                "Solution verification failed: " + "; ".join(verification["issues"])
            )
            result["events"].append({
                "operation": "verification_failed",
                "issues": verification["issues"],
                "explanation": "Verification: " + "; ".join(verification["issues"]),
            })

        result["success"] = True
        result["events"].append({
            "operation": "complete",
            "final_cost": result["final_cost"],
            "is_degenerate": result["is_degenerate"],
            "degenerate_pivot_count": result.get("degenerate_pivot_count", 0),
            "zero_supply_sources": result.get("zero_supply_sources", []),
            "zero_demand_destinations": result.get("zero_demand_destinations", []),
            "has_alternative_optima": result["has_alternative_optima"],
            "concise": f"Solved. Final cost = {result['final_cost']}.",
            "detailed": (
                f"Transportation problem solved using {method.value}. "
                f"Final cost = {result['final_cost']:.6g}."
                + (" [degenerate]" if result["is_degenerate"] else "")
                + (
                    f" [{result.get('degenerate_pivot_count', 0)} degenerate pivot(s)]"
                    if result.get("degenerate_pivot_count")
                    else ""
                )
                + (" [alternative optima exist]" if result["has_alternative_optima"] else "")
            ),
            "technical": (
                f"Z* = {result['final_cost']}. "
                f"Method: {method.value}. "
                f"Optimized: {optimize}."
            ),
            "explanation": (
                f"Transportation problem solved successfully using {method.value}. "
                f"Final total transportation cost = {result['final_cost']:.2f}."
            ),
        })

        return result

    def solve_what_if(
        self,
        original_result: Dict[str, Any],
        cost_matrix: Optional[List[List[float]]] = None,
        supply: Optional[List[float]] = None,
        demand: Optional[List[float]] = None,
        method: Optional[TransportationMethod] = None,
        source_names: Optional[List[str]] = None,
        dest_names: Optional[List[str]] = None,
        optimize: bool = True,
        restricted_cells: Optional[List[List[int]]] = None,
        prohibited_routes: Optional[List[List[int]]] = None,
        changes_applied: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Re-solve with modified parameters and compare against the original result.

        Any parameter not provided defaults to the original problem's values.
        The return dict includes the new solution plus a 'what_if_comparison'
        key describing what changed.
        """
        orig_problem = original_result.get("problem")
        orig_balanced = original_result.get("balanced_problem")

        if orig_problem is None:
            return {
                "success": False,
                "errors": ["Original result does not contain a valid problem."],
            }

        # Fall back to original values for any unspecified parameter.
        new_cost_matrix = cost_matrix if cost_matrix is not None else orig_problem.cost_matrix
        new_supply = supply if supply is not None else list(orig_problem.supply)
        new_demand = demand if demand is not None else list(orig_problem.demand)
        new_method = method if method is not None else (
            original_result.get("initial_solution").method
            if original_result.get("initial_solution") else TransportationMethod.VOGEL
        )
        new_source_names = source_names if source_names is not None else orig_problem.source_names
        new_dest_names = dest_names if dest_names is not None else orig_problem.dest_names
        new_prohibited = restricted_cells if restricted_cells is not None else (
            [[i, j] for (i, j) in orig_problem.restricted_cells]
        )
        if prohibited_routes is not None:
            new_prohibited = new_prohibited + list(prohibited_routes)

        new_result = self.solve(
            cost_matrix=new_cost_matrix,
            supply=new_supply,
            demand=new_demand,
            method=new_method,
            source_names=new_source_names,
            dest_names=new_dest_names,
            optimize=optimize,
            restricted_cells=new_prohibited,
        )

        orig_cost = original_result.get("final_cost", 0.0)
        new_cost = new_result.get("final_cost", 0.0)
        cost_diff = new_cost - orig_cost

        orig_alloc = (
            original_result.get("optimized_solution").allocation
            if original_result.get("optimized_solution")
            else (
                original_result.get("initial_solution").allocation
                if original_result.get("initial_solution")
                else []
            )
        )
        new_alloc = (
            new_result.get("optimized_solution").allocation
            if new_result.get("optimized_solution")
            else (
                new_result.get("initial_solution").allocation
                if new_result.get("initial_solution")
                else []
            )
        )
        alloc_changed = orig_alloc != new_alloc

        comparison = WhatIfTransportationResult(
            original_cost=orig_cost,
            new_cost=new_cost,
            cost_changed=abs(cost_diff) > 1e-9,
            cost_difference=cost_diff,
            allocation_changed=alloc_changed,
            optimal_solution_changed=(
                new_result.get("optimized_solution") is not None
                and original_result.get("optimized_solution") is not None
                and (
                    new_result["optimized_solution"].allocation
                    != original_result["optimized_solution"].allocation
                )
            ),
            changes_applied=changes_applied or [],
            explanation=(
                f"What-if analysis: applied [{', '.join(changes_applied or [])}]. "
                f"Original cost = {orig_cost:.6g}. New cost = {new_cost:.6g}. "
                + (
                    f"Cost {'increased' if cost_diff > 0 else 'decreased'} "
                    f"by {abs(cost_diff):.6g}."
                    if abs(cost_diff) > 1e-9
                    else "Cost unchanged."
                )
            ),
        )

        new_result["what_if_comparison"] = comparison
        return new_result

    def _verify_solution(
        self,
        problem: BalancedTransportationProblem,
        allocation: List[List[float]],
        reported_cost: float,
    ) -> Dict[str, Any]:
        """Verify supply/demand satisfaction and cost correctness."""
        issues = []
        m = problem.num_sources
        n = problem.num_destinations

        for i in range(m):
            for j in range(n):
                if allocation[i][j] < -1e-9:
                    issues.append(
                        f"Negative allocation at ({i+1},{j+1}): {allocation[i][j]:.6g}"
                    )

        for i in range(m):
            row_sum = sum(allocation[i])
            if abs(row_sum - problem.supply[i]) > 1e-6:
                issues.append(
                    f"Source {i+1}: allocated {row_sum:.6g} but supply = {problem.supply[i]}"
                )

        for j in range(n):
            col_sum = sum(allocation[i][j] for i in range(m))
            if abs(col_sum - problem.demand[j]) > 1e-6:
                issues.append(
                    f"Destination {j+1}: allocated {col_sum:.6g} but demand = {problem.demand[j]}"
                )

        computed_cost = sum(
            allocation[i][j] * problem.cost_matrix[i][j]
            for i in range(m)
            for j in range(n)
            if allocation[i][j] > EPSILON
        )

        if abs(computed_cost - reported_cost) > 1e-6:
            issues.append(
                f"Cost mismatch: reported {reported_cost:.6g}, "
                f"independently computed {computed_cost:.6g}"
            )

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "computed_cost": computed_cost,
            "reported_cost": reported_cost,
        }
