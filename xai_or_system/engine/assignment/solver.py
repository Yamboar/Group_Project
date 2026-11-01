from typing import List, Optional, Dict, Any
from engine.assignment.models import (
    AssignmentProblem,
    AssignmentProblemType,
    AssignmentResult,
)
from engine.assignment.validation import validate_assignment_problem, AssignmentValidationError
from engine.assignment.hungarian import solve_hungarian


class AssignmentSolver:
    """
    Orchestrates the complete assignment problem solving pipeline:
    validation -> balancing -> Hungarian Method -> verification.
    """

    def solve(
        self,
        cost_matrix: List[List[float]],
        row_names: Optional[List[str]] = None,
        col_names: Optional[List[str]] = None,
        problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION,
    ) -> Dict[str, Any]:
        """
        Solve an assignment problem end-to-end.

        Args:
            cost_matrix: Cost matrix (m x n or n x n).
            row_names: Optional names for rows (workers/resources).
            col_names: Optional names for columns (jobs/tasks).
            problem_type: MINIMIZATION or MAXIMIZATION.

        Returns:
            A dictionary containing the complete solution.
        """
        result = {
            "success": False,
            "errors": [],
            "warnings": [],
            "validation": None,
            "problem": None,
            "result": None,
            "verification": None,
            "final_cost": 0.0,
            "events": [],
        }

        is_valid, errors = validate_assignment_problem(cost_matrix, row_names, col_names)
        if not is_valid:
            result["errors"] = errors
            result["events"].append({
                "operation": "validation_failed",
                "errors": errors,
                "explanation": "Validation failed. " + "; ".join(errors),
            })
            return result

        result["validation"] = {"is_valid": True, "errors": []}

        problem = AssignmentProblem(
            cost_matrix=cost_matrix,
            row_names=row_names,
            col_names=col_names,
            problem_type=problem_type,
        )
        result["problem"] = problem

        hungarian_result = solve_hungarian(problem)
        result["result"] = hungarian_result
        result["events"].extend(hungarian_result.events)

        verification = self._verify_solution(problem, hungarian_result)
        result["verification"] = verification
        result["final_cost"] = hungarian_result.total_cost

        if not verification["passed"]:
            result["warnings"].append(
                "Solution verification failed: " + "; ".join(verification["issues"])
            )

        result["success"] = True
        return result

    def _verify_solution(
        self,
        problem: AssignmentProblem,
        result: AssignmentResult,
    ) -> Dict[str, Any]:
        """Verify that the assignment solution is valid."""
        issues = []

        non_dummy_assignments = [
            a for a in result.assignments
            if not a["row_name"].startswith("Dummy")
            and not a["col_name"].startswith("Dummy")
        ]

        assigned_rows = set()
        assigned_cols = set()
        for a in non_dummy_assignments:
            if a["row"] in assigned_rows:
                issues.append(f"Row {a['row']+1} is assigned multiple times.")
            if a["col"] in assigned_cols:
                issues.append(f"Column {a['col']+1} is assigned multiple times.")
            assigned_rows.add(a["row"])
            assigned_cols.add(a["col"])

        computed_cost = 0.0
        for a in non_dummy_assignments:
            computed_cost += a["original_cost"]

        if abs(computed_cost - result.total_cost) > 1e-6:
            issues.append(
                f"Cost mismatch: reported {result.total_cost:.2f}, computed {computed_cost:.2f}"
            )

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "computed_cost": computed_cost,
        }
