from typing import List, Optional, Dict, Any
from engine.transportation.models import (
    TransportationProblem,
    BalancedTransportationProblem,
    TransportationMethod,
    InitialSolutionResult,
    OptimizedSolutionResult,
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
    validation -> balancing -> initial solution -> optimization -> verification.
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
    ) -> Dict[str, Any]:
        """
        Solve a transportation problem end-to-end.

        Args:
            cost_matrix: m x n cost matrix.
            supply: Supply for each source (length m).
            demand: Demand for each destination (length n).
            method: Initial solution method to use.
            source_names: Optional names for sources.
            dest_names: Optional names for destinations.
            optimize: Whether to apply Stepping Stone optimization.

        Returns:
            A dictionary containing the complete solution with all intermediate data.
        """
        result = {
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
            "events": [],
        }

        is_valid, errors = validate_transportation_problem(
            cost_matrix, supply, demand, source_names, dest_names
        )
        if not is_valid:
            result["errors"] = errors
            result["events"].append({
                "operation": "validation_failed",
                "errors": errors,
                "explanation": "Validation failed. " + "; ".join(errors),
            })
            return result

        result["validation"] = {"is_valid": True, "errors": []}

        problem = TransportationProblem(
            cost_matrix=cost_matrix,
            supply=supply,
            demand=demand,
            source_names=source_names,
            dest_names=dest_names,
        )

        balanced_problem, balancing_events = balance_problem(problem)
        result["balancing"] = {
            "is_balanced": problem.is_balanced,
            "events": balancing_events,
        }
        result["problem"] = problem
        result["balanced_problem"] = balanced_problem
        result["events"].extend(balancing_events)

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

        if optimize:
            optimized = solve_stepping_stone(balanced_problem, initial)
            result["optimized_solution"] = optimized
            result["events"].append({
                "operation": "optimization",
                "explanation": optimized.explanation,
            })
            result["final_cost"] = optimized.total_cost
        else:
            result["final_cost"] = initial.total_cost

        verification = self._verify_solution(
            balanced_problem,
            result["optimized_solution"].allocation if optimize else initial.allocation,
            result["final_cost"],
        )
        result["verification"] = verification

        if not verification["passed"]:
            result["warnings"].append(
                "Solution verification failed: " + "; ".join(verification["issues"])
            )
            result["events"].append({
                "operation": "verification_failed",
                "issues": verification["issues"],
                "explanation": "Verification failed: " + "; ".join(verification["issues"]),
            })

        result["success"] = True
        result["events"].append({
            "operation": "complete",
            "final_cost": result["final_cost"],
            "explanation": (
                f"Transportation problem solved successfully using {method.value}. "
                f"Final total transportation cost = {result['final_cost']:.2f}."
            ),
        })

        return result

    def _verify_solution(
        self,
        problem: BalancedTransportationProblem,
        allocation: List[List[float]],
        reported_cost: float,
    ) -> Dict[str, Any]:
        """Verify that the solution is valid and correct."""
        issues = []
        num_sources = problem.num_sources
        num_dests = problem.num_destinations

        for i in range(num_sources):
            for j in range(num_dests):
                if allocation[i][j] < -1e-9:
                    issues.append(
                        f"Negative allocation at ({i+1}, {j+1}): {allocation[i][j]}"
                    )

        for i in range(num_sources):
            row_sum = sum(allocation[i])
            if abs(row_sum - problem.supply[i]) > 1e-6:
                issues.append(
                    f"Source {i+1}: allocated {row_sum:.6f} but supply is {problem.supply[i]}"
                )

        for j in range(num_dests):
            col_sum = sum(allocation[i][j] for i in range(num_sources))
            if abs(col_sum - problem.demand[j]) > 1e-6:
                issues.append(
                    f"Destination {j+1}: allocated {col_sum:.6f} but demand is {problem.demand[j]}"
                )

        computed_cost = 0.0
        for i in range(num_sources):
            for j in range(num_dests):
                computed_cost += allocation[i][j] * problem.cost_matrix[i][j]

        if abs(computed_cost - reported_cost) > 1e-6:
            issues.append(
                f"Reported cost {reported_cost:.6f} does not match computed cost {computed_cost:.6f}"
            )

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "computed_cost": computed_cost,
            "reported_cost": reported_cost,
        }
