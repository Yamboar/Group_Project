from typing import List, Optional, Dict, Any, Set, Tuple
from engine.assignment.models import (
    AssignmentProblem,
    AssignmentProblemType,
    AssignmentResult,
    WhatIfAssignmentResult,
    PROHIBITED_COST,
)
from engine.assignment.validation import validate_assignment_problem, AssignmentValidationError
from engine.assignment.hungarian import solve_hungarian, _balance_problem


class AssignmentSolver:
    """
    Orchestrates the complete assignment problem solving pipeline:
    validation → Hungarian Method → verification.

    Supports:
    - Restricted assignments (cells that can never be selected).
    - Both minimisation and maximisation objectives.
    - Alternative optima detection.
    - What-if analysis (re-solve with modified parameters and compare).
    """

    def solve(
        self,
        cost_matrix: List[List[float]],
        row_names: Optional[List[str]] = None,
        col_names: Optional[List[str]] = None,
        problem_type: AssignmentProblemType = AssignmentProblemType.MINIMIZATION,
        restricted_cells: Optional[List[List[int]]] = None,
        prohibited_assignments: Optional[List[List[int]]] = None,
    ) -> Dict[str, Any]:
        """
        Solve an assignment problem end-to-end.

        restricted_cells: list of [row, col] pairs (0-indexed) that are
        forbidden. These cells are encoded as PROHIBITED_COST internally and
        never appear in the final assignment.

        prohibited_assignments: legacy alias for restricted_cells. Both are
        merged; cells marked in either set are treated as Restricted. Cells in
        the input matrix whose value is >= PROHIBITED_COST are also treated as
        Restricted for backwards compatibility with the old sentinel encoding.

        Returns a result dict with full XAI event log.
        """
        result: Dict[str, Any] = {
            "success": False,
            "errors": [],
            "warnings": [],
            "validation": None,
            "problem": None,
            "result": None,
            "verification": None,
            "final_cost": 0.0,
            "has_alternative_optima": False,
            "alternative_assignment_cells": [],
            "events": [],
        }

        # Merge restricted_cells + prohibited_assignments into one set.
        restricted: Set[Tuple[int, int]] = set()
        for cells in (restricted_cells, prohibited_assignments):
            if cells:
                for cell in cells:
                    if isinstance(cell, (list, tuple)) and len(cell) == 2:
                        restricted.add((int(cell[0]), int(cell[1])))

        # Legacy sentinel compatibility: matrix values >= PROHIBITED_COST are
        # also treated as Restricted (the old encoding for forbidden cells).
        for i, row in enumerate(cost_matrix):
            for j, val in enumerate(row):
                if isinstance(val, (int, float)) and val >= PROHIBITED_COST:
                    restricted.add((i, j))

        is_valid, errors = validate_assignment_problem(
            cost_matrix, row_names, col_names, restricted
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

        problem = AssignmentProblem(
            cost_matrix=cost_matrix,
            row_names=row_names,
            col_names=col_names,
            problem_type=problem_type,
            restricted_cells=restricted,
        )
        result["problem"] = problem

        hungarian_result = solve_hungarian(problem)
        result["result"] = hungarian_result
        result["balanced_problem"] = _balance_problem(problem)
        result["events"].extend(hungarian_result.events)
        result["has_alternative_optima"] = hungarian_result.has_alternative_optima
        result["alternative_assignment_cells"] = [
            [r+1, c+1] for r, c in hungarian_result.alternative_assignment_cells
        ]
        result["number_of_optimal_assignments"] = (
            hungarian_result.number_of_optimal_assignments
        )
        result["all_optimal_assignments"] = [
            [[r, c] for r, c in plan]
            for plan in hungarian_result.all_optimal_assignments
        ]
        result["optimal_assignments_truncated"] = (
            hungarian_result.optimal_assignments_truncated
        )

        if hungarian_result.has_alternative_optima:
            prefix = (
                "At least" if not hungarian_result.optimal_assignments_count_exact
                else "There are"
            )
            plural = "" if hungarian_result.number_of_optimal_assignments == 1 else "s"
            result["warnings"].append(
                f"{prefix} {hungarian_result.number_of_optimal_assignments} "
                f"different optimal assignment plan{plural}. Cells "
                f"{[[r+1,c+1] for r,c in hungarian_result.alternative_assignment_cells]} "
                f"are also zero in the final reduced matrix and could be used instead "
                f"without changing the total cost."
            )

        verification = self._verify_solution(problem, hungarian_result)
        result["verification"] = verification
        result["final_cost"] = hungarian_result.total_cost

        if not verification["passed"]:
            result["warnings"].append(
                "Solution verification failed: " + "; ".join(verification["issues"])
            )

        result["success"] = True
        return result

    def solve_what_if(
        self,
        original_result: Dict[str, Any],
        cost_matrix: Optional[List[List[float]]] = None,
        row_names: Optional[List[str]] = None,
        col_names: Optional[List[str]] = None,
        problem_type: Optional[AssignmentProblemType] = None,
        restricted_cells: Optional[List[List[int]]] = None,
        prohibited_assignments: Optional[List[List[int]]] = None,
        changes_applied: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Re-solve with modified parameters and compare against the original result.
        Any parameter not provided defaults to the original problem's values.
        """
        orig_problem = original_result.get("problem")
        if orig_problem is None:
            return {
                "success": False,
                "errors": ["Original result does not contain a valid problem."],
            }

        new_cost_matrix = cost_matrix if cost_matrix is not None else orig_problem.cost_matrix
        new_row_names = row_names if row_names is not None else orig_problem.row_names
        new_col_names = col_names if col_names is not None else orig_problem.col_names
        new_problem_type = problem_type if problem_type is not None else orig_problem.problem_type
        new_restricted = (
            restricted_cells if restricted_cells is not None
            else [[i, j] for (i, j) in orig_problem.restricted_cells]
        )

        new_result = self.solve(
            cost_matrix=new_cost_matrix,
            row_names=new_row_names,
            col_names=new_col_names,
            problem_type=new_problem_type,
            restricted_cells=new_restricted,
            prohibited_assignments=prohibited_assignments,
        )

        orig_cost = original_result.get("final_cost", 0.0)
        new_cost = new_result.get("final_cost", 0.0)
        cost_diff = new_cost - orig_cost

        orig_assignments = (
            original_result.get("result").assignments
            if original_result.get("result")
            else []
        )
        new_assignments = (
            new_result.get("result").assignments
            if new_result.get("result")
            else []
        )
        assign_changed = (
            [(a["row"], a["col"]) for a in orig_assignments]
            != [(a["row"], a["col"]) for a in new_assignments]
        )

        comparison = WhatIfAssignmentResult(
            original_cost=orig_cost,
            new_cost=new_cost,
            cost_changed=abs(cost_diff) > 1e-9,
            cost_difference=cost_diff,
            assignment_changed=assign_changed,
            changes_applied=changes_applied or [],
            explanation=(
                f"What-if analysis: [{', '.join(changes_applied or [])}]. "
                f"Original cost = {orig_cost:.6g}. New cost = {new_cost:.6g}. "
                + (
                    f"Cost {'increased' if cost_diff > 0 else 'decreased'} by {abs(cost_diff):.6g}."
                    if abs(cost_diff) > 1e-9
                    else "Cost unchanged."
                )
            ),
        )

        new_result["what_if_comparison"] = comparison
        return new_result

    def _verify_solution(
        self,
        problem: AssignmentProblem,
        result: AssignmentResult,
    ) -> Dict[str, Any]:
        """
        Verify the assignment:
        - Every non-dummy row and column appears at most once.
        - No restricted cell is selected.
        - Independently computed cost matches reported cost.
        """
        issues: List[str] = []

        real_assignments = [
            a for a in result.assignments
            if not a.get("is_dummy", False)
        ]

        assigned_rows: Set[int] = set()
        assigned_cols: Set[int] = set()
        for a in real_assignments:
            if a["row"] in assigned_rows:
                issues.append(f"Row {a['row']+1} is assigned more than once.")
            if a["col"] in assigned_cols:
                issues.append(f"Column {a['col']+1} is assigned more than once.")
            assigned_rows.add(a["row"])
            assigned_cols.add(a["col"])

            if a.get("is_restricted", False) or a.get("is_prohibited", False):
                issues.append(
                    f"Restricted cell selected in the final assignment: "
                    f"({a['row_name']} → {a['col_name']})."
                )

        computed_cost = sum(a["original_cost"] for a in real_assignments)
        if abs(computed_cost - result.total_cost) > 1e-6:
            issues.append(
                f"Cost mismatch: reported {result.total_cost:.6g}, "
                f"independently computed {computed_cost:.6g}."
            )

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "computed_cost": computed_cost,
        }
