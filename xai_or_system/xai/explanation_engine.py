from typing import List, Dict, Any, Optional
from xai.events import (
    SolutionEvent,
    Explanation,
    SolutionExplanation,
    ExplanationLevel,
    ExplanationCategory,
)
from xai.templates import (
    TRANSPORTATION_TEMPLATES,
    BALANCING_TEMPLATES,
    STEPPING_STONE_TEMPLATES,
    HUNGARIAN_TEMPLATES,
)


class ExplanationEngine:
    """
    Generates human-readable explanations from structured algorithmic events.
    The mathematical engine produces verified events; this engine converts
    them into natural-language explanations at different levels of detail.
    """

    def __init__(self):
        self.event_counter = 0

    def _create_event(
        self,
        algorithm: str,
        iteration: int,
        operation: str,
        category: ExplanationCategory,
        **kwargs,
    ) -> SolutionEvent:
        self.event_counter += 1
        return SolutionEvent(
            event_id=self.event_counter,
            algorithm=algorithm,
            iteration=iteration,
            operation=operation,
            category=category,
            cell=kwargs.get("cell"),
            quantity=kwargs.get("quantity"),
            cost_per_unit=kwargs.get("cost_per_unit"),
            total_cell_cost=kwargs.get("total_cell_cost"),
            improvement_index=kwargs.get("improvement_index"),
            adjustment_quantity=kwargs.get("adjustment_quantity"),
            old_cost=kwargs.get("old_cost"),
            new_cost=kwargs.get("new_cost"),
            metadata=kwargs.get("metadata", {}),
        )

    def generate_transportation_explanation(
        self,
        solution_data: Dict[str, Any],
    ) -> SolutionExplanation:
        """Generate explanations for a complete transportation problem solution."""
        events_raw = solution_data.get("events", [])
        algorithm = solution_data.get("initial_solution", {})
        if hasattr(algorithm, "method"):
            algo_name = algorithm.method.value
        elif isinstance(algorithm, dict) and "method" in algorithm:
            algo_name = str(algorithm["method"])
        else:
            algo_name = "Transportation Algorithm"

        events = []
        explanations = []
        self.event_counter = 0

        for evt in events_raw:
            op = evt.get("operation", "")

            if op == "balancing" or evt.get("type") == "balancing":
                category = ExplanationCategory.BALANCING
            elif op in ("allocation",):
                category = ExplanationCategory.ALLOCATION
            elif op in ("iteration", "start_optimization", "optimality_reached"):
                category = ExplanationCategory.OPTIMIZATION
            elif op == "complete":
                category = ExplanationCategory.COMPLETE
            elif op in ("validation_failed",):
                category = ExplanationCategory.VALIDATION
            else:
                category = ExplanationCategory.ALLOCATION

            se = self._create_event(
                algorithm=algo_name,
                iteration=evt.get("iteration", 0),
                operation=op,
                category=category,
                cell=evt.get("cell"),
                quantity=evt.get("quantity"),
                cost_per_unit=evt.get("cost_per_unit"),
                total_cell_cost=evt.get("total_cell_cost"),
                improvement_index=evt.get("improvement_index"),
                adjustment_quantity=evt.get("adjustment_quantity"),
                old_cost=evt.get("old_cost"),
                new_cost=evt.get("new_cost"),
                metadata=evt,
            )

            explanation_text = self._format_transportation_event(evt, algo_name)
            ex = Explanation(
                event_id=se.event_id,
                level=ExplanationLevel.DETAILED,
                concise=self._get_concise_transportation(evt, algo_name),
                detailed=explanation_text,
                technical=self._get_technical_transportation(evt, algo_name),
            )

            events.append(se)
            explanations.append(ex)

        summary = self._generate_transportation_summary(solution_data, algo_name)
        key_decisions = self._extract_key_decisions(solution_data, algo_name)
        optimality_reason = self._get_optimality_reason(solution_data)

        return SolutionExplanation(
            algorithm=algo_name,
            problem_type="Transportation",
            events=events,
            explanations=explanations,
            summary=summary,
            key_decisions=key_decisions,
            optimality_reason=optimality_reason,
        )

    def generate_assignment_explanation(
        self,
        solution_data: Dict[str, Any],
    ) -> SolutionExplanation:
        """Generate explanations for a complete assignment problem solution."""
        events_raw = solution_data.get("events", [])
        result = solution_data.get("result")
        algo_name = "Hungarian Method"

        events = []
        explanations = []
        self.event_counter = 0

        for evt in events_raw:
            op = evt.get("operation", "")
            if op in ("row_reduction", "column_reduction"):
                category = ExplanationCategory.ALLOCATION
            elif op == "cover_zeros":
                category = ExplanationCategory.OPTIMIZATION
            elif op == "matrix_adjustment":
                category = ExplanationCategory.OPTIMIZATION
            elif op == "complete":
                category = ExplanationCategory.COMPLETE
            else:
                category = ExplanationCategory.ALLOCATION

            se = self._create_event(
                algorithm=algo_name,
                iteration=0,
                operation=op,
                category=category,
                metadata=evt,
            )

            explanation_text = self._format_assignment_event(evt)
            ex = Explanation(
                event_id=se.event_id,
                level=ExplanationLevel.DETAILED,
                concise=explanation_text[:100] + "..." if len(explanation_text) > 100 else explanation_text,
                detailed=explanation_text,
                technical=explanation_text,
            )

            events.append(se)
            explanations.append(ex)

        summary = self._generate_assignment_summary(solution_data, algo_name)
        key_decisions = self._extract_assignment_decisions(solution_data)

        return SolutionExplanation(
            algorithm=algo_name,
            problem_type="Assignment",
            events=events,
            explanations=explanations,
            summary=summary,
            key_decisions=key_decisions,
            optimality_reason="The Hungarian Method guarantees an optimal assignment.",
        )

    def _format_transportation_event(self, evt: Dict[str, Any], algo_name: str) -> str:
        op = evt.get("operation", "")
        if op == "start":
            return evt.get("explanation", "Starting algorithm.")
        elif op == "allocation":
            return evt.get("explanation", "Allocation step.")
        elif op == "complete":
            return evt.get("explanation", "Algorithm complete.")
        elif op == "start_optimization":
            return evt.get("explanation", "Starting optimization.")
        elif op == "iteration":
            return evt.get("explanation", "Optimization iteration.")
        elif op == "optimality_reached":
            return evt.get("explanation", "Optimality reached.")
        elif op == "balancing":
            return evt.get("explanation", "Balancing step.")
        elif op == "validation_failed":
            return evt.get("explanation", "Validation failed.")
        return evt.get("explanation", "")

    def _get_concise_transportation(self, evt: Dict[str, Any], algo_name: str) -> str:
        op = evt.get("operation", "")
        if op == "allocation":
            cell = evt.get("cell", [0, 0])
            qty = evt.get("quantity", 0)
            cost = evt.get("cost_per_unit", 0)
            return f"Allocate {qty} units to cell ({cell[0]+1}, {cell[1]+1}) at cost {cost}."
        elif op == "complete":
            total = evt.get("total_cell_cost", 0) or evt.get("explanation", "").split("cost = ")[-1].split(".")[0] if "cost = " in evt.get("explanation", "") else "?"
            return f"Complete. Total cost = {total}."
        elif op == "iteration":
            idx = evt.get("improvement_index", 0)
            cell = evt.get("entering_cell", evt.get("cell", [0, 0]))
            if isinstance(cell, list) and len(cell) >= 2:
                return f"Iteration: enter ({cell[0]+1}, {cell[1]+1}), improvement = {idx:.2f}."
            return f"Iteration complete, improvement = {idx:.2f}."
        return evt.get("explanation", "")[:100]

    def _get_technical_transportation(self, evt: Dict[str, Any], algo_name: str) -> str:
        return self._format_transportation_event(evt, algo_name)

    def _generate_transportation_summary(self, data: Dict[str, Any], algo_name: str) -> str:
        parts = []
        initial = data.get("initial_solution")
        if initial:
            cost = initial.total_cost if hasattr(initial, "total_cost") else initial.get("total_cost", "?")
            parts.append(f"Initial solution ({algo_name}): cost = {cost}.")

        optimized = data.get("optimized_solution")
        if optimized:
            cost = optimized.total_cost if hasattr(optimized, "total_cost") else optimized.get("total_cost", "?")
            parts.append(f"After Stepping Stone optimization: cost = {cost}.")
            is_opt = optimized.is_optimal if hasattr(optimized, "is_optimal") else optimized.get("is_optimal", False)
            if is_opt:
                parts.append("The final solution is optimal.")
        else:
            if initial:
                cost = initial.total_cost if hasattr(initial, "total_cost") else initial.get("total_cost", "?")
                parts.append(f"Final cost = {cost} (no optimization applied).")

        return " ".join(parts)

    def _extract_key_decisions(self, data: Dict[str, Any], algo_name: str) -> List[str]:
        decisions = []
        initial = data.get("initial_solution")
        if initial and hasattr(initial, "decisions"):
            for d in initial.decisions[:3]:
                decisions.append(d.explanation[:150])
            if len(initial.decisions) > 3:
                decisions.append(f"... and {len(initial.decisions) - 3} more allocation decisions.")
        return decisions

    def _get_optimality_reason(self, data: Dict[str, Any]) -> str:
        optimized = data.get("optimized_solution")
        if optimized and hasattr(optimized, "explanation"):
            return optimized.explanation
        if optimized and isinstance(optimized, dict):
            return optimized.get("explanation", "Optimality not verified.")
        return "No optimization performed; initial solution presented as-is."

    def _format_assignment_event(self, evt: Dict[str, Any]) -> str:
        return evt.get("explanation", "")

    def _generate_assignment_summary(self, data: Dict[str, Any], algo_name: str) -> str:
        result = data.get("result")
        if result:
            cost = result.total_cost if hasattr(result, "total_cost") else result.get("total_cost", "?")
            return f"Assignment problem solved using {algo_name}. Optimal cost = {cost}."
        return "Assignment problem solved."

    def _extract_assignment_decisions(self, data: Dict[str, Any]) -> List[str]:
        result = data.get("result")
        if result and hasattr(result, "assignments"):
            return [
                f"{a['row_name']} assigned to {a['col_name']} (cost = {a['original_cost']})"
                for a in result.assignments
                if not a.get("row_name", "").startswith("Dummy")
                and not a.get("col_name", "").startswith("Dummy")
            ]
        return []

    def get_step_explanation(
        self,
        events: List[Dict[str, Any]],
        step_index: int,
        level: ExplanationLevel = ExplanationLevel.DETAILED,
    ) -> str:
        """Get explanation for a specific step."""
        if step_index < 0 or step_index >= len(events):
            return "Invalid step index."
        evt = events[step_index]
        if level == ExplanationLevel.CONCISE:
            return self._get_concise_transportation(evt, "")
        elif level == ExplanationLevel.TECHNICAL:
            return self._get_technical_transportation(evt, "")
        return self._format_transportation_event(evt, "")
