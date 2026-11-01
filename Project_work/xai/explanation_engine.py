from typing import List, Dict, Any, Optional
from xai.events import (
    SolutionEvent,
    Explanation,
    SolutionExplanation,
    ExplanationLevel,
    ExplanationCategory,
)


class ExplanationEngine:
    """
    Generates human-readable explanations from the structured event logs
    produced by the transportation and assignment engine solvers.

    The engine itself performs all mathematical decisions; this class reads
    the verified event records and produces Concise, Detailed, and Technical
    explanations at three distinct levels.

    It answers questions such as:
    - "Why was this cell selected?"
    - "Why was a dummy added?"
    - "Why did the algorithm continue / stop?"
    - "Why is the solution optimal?"
    - "What would happen if another option had been chosen?"
    - "Why was ε introduced?"
    - "Why does an alternative optimum exist?"
    """

    def __init__(self) -> None:
        self.event_counter = 0

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self.event_counter += 1
        return self.event_counter

    def _category_for_op(self, op: str, is_transport: bool = True) -> ExplanationCategory:
        if op in ("balancing",):
            return ExplanationCategory.BALANCING
        if op in ("allocation", "skip_prohibited"):
            return ExplanationCategory.ALLOCATION
        if op in (
            "start_optimization", "iteration", "optimality_reached",
            "cover_zeros", "matrix_adjustment", "no_progress", "cycle_detected",
            "degeneracy", "degeneracy_reported",
        ):
            return ExplanationCategory.OPTIMIZATION
        if op in ("complete", "final_assignment"):
            return ExplanationCategory.COMPLETE
        if op in ("validation_failed",):
            return ExplanationCategory.VALIDATION
        if op in ("row_reduction", "column_reduction"):
            return ExplanationCategory.ALLOCATION
        return ExplanationCategory.ALLOCATION

    def _evt_text(self, evt: Dict[str, Any], level: str) -> str:
        """Return the appropriate level of explanation text from an event dict."""
        if level == "concise":
            return evt.get("concise") or evt.get("explanation", "")
        if level == "technical":
            return evt.get("technical") or evt.get("explanation", "")
        return evt.get("detailed") or evt.get("explanation", "")

    def _make_explanation(
        self,
        event_id: int,
        evt: Dict[str, Any],
    ) -> Explanation:
        return Explanation(
            event_id=event_id,
            level=ExplanationLevel.DETAILED,
            concise=self._evt_text(evt, "concise"),
            detailed=self._evt_text(evt, "detailed"),
            technical=self._evt_text(evt, "technical"),
        )

    def _make_event(
        self,
        evt: Dict[str, Any],
        algo_name: str,
        category: ExplanationCategory,
    ) -> SolutionEvent:
        eid = self._next_id()
        return SolutionEvent(
            event_id=eid,
            algorithm=algo_name,
            iteration=evt.get("iteration", 0),
            operation=evt.get("operation", ""),
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

    # ── Transportation explanations ──────────────────────────────────────────

    def _objective_summary(self, data: Dict[str, Any]) -> str:
        """Build a plain-language sentence from the objective-selection trail."""
        obj = data.get("objective_selection")
        if not obj:
            return ""
        direction = obj.get("resolved_direction")
        intent = obj.get("intent")
        vt = obj.get("value_type", "")
        recommended = obj.get("recommended")
        overridden = obj.get("overridden")

        value_word = vt or "objective value"
        verb = "maximise" if direction == "maximise" else "minimise"

        explainer = "The problem was solved to "
        sentence = f"{explainer}{verb} the total {value_word}."

        if obj.get("source") == "default":
            return (
                "No objective was specified, so the problem was solved as a "
                "minimisation."
            )
        if overridden:
            return (
                f"You chose to {intent} the total {value_word}, overriding the "
                f"recommended '{recommended}'. The problem was solved to {verb} "
                f"the total {value_word}."
            )
        if obj.get("confirmed"):
            return sentence + (
                f" This confirmed the recommended '{recommended}' objective."
            )
        return sentence

    def generate_transportation_explanation(
        self,
        solution_data: Dict[str, Any],
    ) -> SolutionExplanation:
        """
        Generate a three-level SolutionExplanation for a transportation solution.

        Covers: balancing, initial solution (NW/LC/Vogel), degeneracy handling,
        Stepping Stone optimization, optimality, alternative optima, what-if.
        """
        events_raw: List[Dict[str, Any]] = solution_data.get("events", [])

        # Determine algorithm name from initial solution.
        initial = solution_data.get("initial_solution")
        if initial and hasattr(initial, "method"):
            algo_name = initial.method.value
        elif isinstance(initial, dict) and "method" in initial:
            algo_name = str(initial["method"])
        else:
            algo_name = "Transportation Algorithm"

        self.event_counter = 0
        events: List[SolutionEvent] = []
        explanations: List[Explanation] = []

        for evt in events_raw:
            op = evt.get("operation", "")
            # Also handle the "type" key used by balancing events.
            if evt.get("type") == "balancing":
                op = "balancing"
                evt = dict(evt, operation="balancing")

            category = self._category_for_op(op, is_transport=True)
            se = self._make_event(evt, algo_name, category)
            ex = self._make_explanation(se.event_id, evt)
            events.append(se)
            explanations.append(ex)

        summary = self._transportation_summary(solution_data, algo_name)
        key_decisions = self._transportation_key_decisions(solution_data, algo_name)
        optimality_reason = self._transportation_optimality_reason(solution_data)

        return SolutionExplanation(
            algorithm=algo_name,
            problem_type="Transportation",
            events=events,
            explanations=explanations,
            summary=summary,
            key_decisions=key_decisions,
            optimality_reason=optimality_reason,
        )

    def _transportation_summary(
        self, data: Dict[str, Any], algo_name: str
    ) -> str:
        parts: List[str] = []

        # Objective-selection trail.
        obj_line = self._objective_summary(data)
        if obj_line:
            parts.append(obj_line)

        # Balancing.
        balancing = data.get("balancing", {})
        if balancing:
            if balancing.get("dummy_source_added"):
                parts.append("A dummy source was added to balance the problem.")
            elif balancing.get("dummy_destination_added"):
                parts.append("A dummy destination was added to balance the problem.")
            else:
                parts.append("Problem was already balanced.")

        # Initial solution.
        initial = data.get("initial_solution")
        if initial:
            cost = (
                initial.total_cost if hasattr(initial, "total_cost")
                else initial.get("total_cost", "?")
            )
            deg = (
                initial.degeneracy_info.detected
                if hasattr(initial, "degeneracy_info") and initial.degeneracy_info
                else False
            )
            parts.append(
                f"Initial solution ({algo_name}): cost = {cost}."
                + (" [degenerate — ε applied]" if deg else "")
            )

        if data.get("zero_supply_sources"):
            parts.append(
                "Source(s) with zero supply "
                f"{data['zero_supply_sources']} were treated as dummy and received no "
                "allocation."
            )
        if data.get("zero_demand_destinations"):
            parts.append(
                "Destination(s) with zero demand "
                f"{data['zero_demand_destinations']} were treated as dummy and "
                "received no allocation."
            )

        # Optimized solution.
        optimized = data.get("optimized_solution")
        if optimized:
            cost = (
                optimized.total_cost if hasattr(optimized, "total_cost")
                else optimized.get("total_cost", "?")
            )
            is_opt = (
                optimized.is_optimal if hasattr(optimized, "is_optimal")
                else optimized.get("is_optimal", False)
            )
            hit_lim = (
                optimized.hit_iteration_limit
                if hasattr(optimized, "hit_iteration_limit")
                else False
            )
            has_alt = (
                optimized.has_alternative_optima
                if hasattr(optimized, "has_alternative_optima")
                else False
            )
            iters = (
                len(optimized.iterations) if hasattr(optimized, "iterations")
                else "?"
            )
            parts.append(
                f"After {iters} Stepping Stone iteration(s): cost = {cost}."
            )
            n_deg_pivots = (
                optimized.degenerate_pivot_count
                if hasattr(optimized, "degenerate_pivot_count")
                else 0
            )
            if n_deg_pivots:
                parts.append(
                    f"{n_deg_pivots} pivot(s) were degenerate and handled with an "
                    "ε-perturbation (a valid basis was always maintained)."
                )
            if is_opt:
                parts.append("Solution is optimal (no negative improvement indices).")
            elif hit_lim:
                parts.append(
                    "Iteration limit reached; solution may not be globally optimal."
                )
            if has_alt:
                alt = (
                    optimized.alternative_optima_cells
                    if hasattr(optimized, "alternative_optima_cells")
                    else []
                )
                parts.append(
                    f"Alternative optimal solutions exist at cells "
                    f"{[[r+1,c+1] for r,c in alt]}."
                )
        else:
            if initial:
                cost = (
                    initial.total_cost if hasattr(initial, "total_cost")
                    else initial.get("total_cost", "?")
                )
                parts.append(f"No Stepping Stone optimization applied. Final cost = {cost}.")

        return " ".join(parts)

    def _transportation_key_decisions(
        self, data: Dict[str, Any], algo_name: str
    ) -> List[str]:
        decisions: List[str] = []
        initial = data.get("initial_solution")
        if initial and hasattr(initial, "decisions"):
            for d in initial.decisions[:5]:
                line = d.explanation[:200] if d.explanation else ""
                if d.tie_broken and d.tie_break_reason:
                    line += f" [Tie: {d.tie_break_reason[:100]}]"
                decisions.append(line)
            rem = len(initial.decisions) - 5
            if rem > 0:
                decisions.append(f"…and {rem} more allocation decision(s).")

        optimized = data.get("optimized_solution")
        if optimized and hasattr(optimized, "iterations"):
            for it in optimized.iterations[:3]:
                decisions.append(it.explanation[:200])
            rem = len(optimized.iterations) - 3
            if rem > 0:
                decisions.append(f"…and {rem} more Stepping Stone iteration(s).")

        return decisions

    def _transportation_optimality_reason(self, data: Dict[str, Any]) -> str:
        optimized = data.get("optimized_solution")
        if optimized is None:
            return "Stepping Stone optimization was not applied."
        if hasattr(optimized, "explanation"):
            return optimized.explanation
        if isinstance(optimized, dict):
            return optimized.get("explanation", "")
        return "Optimality status unknown."

    # ── Assignment explanations ──────────────────────────────────────────────

    def generate_assignment_explanation(
        self,
        solution_data: Dict[str, Any],
    ) -> SolutionExplanation:
        """
        Generate a three-level SolutionExplanation for an assignment solution.

        Covers: balancing (dummy rows/cols), row/column reduction, zero covering,
        matrix adjustment, final assignment, alternative optima.
        """
        events_raw: List[Dict[str, Any]] = solution_data.get("events", [])
        algo_name = "Hungarian Method"

        self.event_counter = 0
        events: List[SolutionEvent] = []
        explanations: List[Explanation] = []

        for evt in events_raw:
            op = evt.get("operation", "")
            category = self._category_for_op(op, is_transport=False)
            se = self._make_event(evt, algo_name, category)
            ex = self._make_explanation(se.event_id, evt)
            events.append(se)
            explanations.append(ex)

        summary = self._assignment_summary(solution_data)
        key_decisions = self._assignment_key_decisions(solution_data)
        optimality_reason = self._assignment_optimality_reason(solution_data)

        return SolutionExplanation(
            algorithm=algo_name,
            problem_type="Assignment",
            events=events,
            explanations=explanations,
            summary=summary,
            key_decisions=key_decisions,
            optimality_reason=optimality_reason,
        )

    def _assignment_summary(self, data: Dict[str, Any]) -> str:
        parts: List[str] = []
        result = data.get("result")
        if not result:
            return "No assignment result available."

        obj_line = self._objective_summary(data)
        if obj_line:
            parts.append(obj_line)

        problem = data.get("problem")
        ptype = (
            problem.problem_type.value
            if problem and hasattr(problem, "problem_type")
            else "Minimization"
        )
        cost = (
            result.total_cost if hasattr(result, "total_cost")
            else result.get("total_cost", "?")
        )
        parts.append(
            f"Hungarian Method solved a {ptype.lower()} assignment problem. "
            f"Optimal {'cost' if 'min' in ptype.lower() else 'profit'} = {cost}."
        )

        real = [
            a for a in (
                result.assignments if hasattr(result, "assignments")
                else result.get("assignments", [])
            )
            if not a.get("is_dummy", False)
        ]
        pairs = ", ".join(
            f"{a['row_name']} → {a['col_name']}"
            for a in real
        )
        if pairs:
            parts.append(f"Assignments: {pairs}.")

        has_alt = (
            result.has_alternative_optima
            if hasattr(result, "has_alternative_optima")
            else False
        )
        if has_alt:
            alt = (
                result.alternative_assignment_cells
                if hasattr(result, "alternative_assignment_cells")
                else []
            )
            n_plans = getattr(result, "number_of_optimal_assignments", 0) or 0
            exact = getattr(result, "optimal_assignments_count_exact", True)
            prefix = "There are" if exact else "There are at least"
            plan_word = "plan" if n_plans == 1 else "plans"
            parts.append(
                f"{prefix} {n_plans} different optimal assignment {plan_word}. "
                f"Alternative optimal assignment(s) possible at cells "
                f"{[[r+1,c+1] for r,c in alt]}."
            )

        restricted = data.get("problem")
        if restricted and hasattr(restricted, "prohibited_assignments"):
            n_rest = len(restricted.prohibited_assignments)
            if n_rest:
                parts.append(f"{n_rest} cell(s) were marked as Restricted (forbidden).")

        return " ".join(parts)

    def _assignment_key_decisions(self, data: Dict[str, Any]) -> List[str]:
        decisions: List[str] = []
        events_raw = data.get("events", [])
        for evt in events_raw:
            op = evt.get("operation", "")
            why = evt.get("why") or evt.get("why_optimal") or evt.get("why_selected")
            if why:
                decisions.append(f"[{op}] {why[:200]}")
            elif op in ("row_reduction", "column_reduction", "cover_zeros",
                        "matrix_adjustment", "complete"):
                decisions.append(
                    f"[{op}] {self._evt_text(evt, 'concise')}"
                )
        return decisions[:10]  # cap at 10 for readability

    def _assignment_optimality_reason(self, data: Dict[str, Any]) -> str:
        result = data.get("result")
        if result and hasattr(result, "is_optimal") and result.is_optimal:
            return (
                "The Hungarian Method guarantees an optimal assignment. "
                "After row and column reductions and iterative matrix adjustments, "
                "the minimum line cover equalled the matrix size, confirming that a "
                "complete independent zero assignment (and hence optimal solution) exists."
            )
        return "The Hungarian Method was applied; optimality status could not be confirmed."

    # ── Step-level query API ─────────────────────────────────────────────────

    def get_step_explanation(
        self,
        events: List[Dict[str, Any]],
        step_index: int,
        level: ExplanationLevel = ExplanationLevel.DETAILED,
    ) -> str:
        """Return the explanation for a specific event index at the requested level."""
        if step_index < 0 or step_index >= len(events):
            return "Invalid step index."
        evt = events[step_index]
        lvl = level.value if hasattr(level, "value") else str(level)
        if lvl == "concise":
            return self._evt_text(evt, "concise")
        if lvl == "technical":
            return self._evt_text(evt, "technical")
        return self._evt_text(evt, "detailed")

    def answer_why(
        self,
        events: List[Dict[str, Any]],
        step_index: int,
        question: str,
    ) -> str:
        """
        Answer a 'why' question about a specific step.

        question can be one of:
          "selected", "rejected", "stopped", "continued", "optimal",
          "dummy", "epsilon", "alternative", "loop", "what_if"
        """
        if step_index < 0 or step_index >= len(events):
            return "Invalid step index."
        evt = events[step_index]
        q = question.lower()

        if q == "selected":
            return evt.get("why_selected") or evt.get("explanation", "No selection detail available.")
        if q == "rejected":
            rej = evt.get("why_rejected", [])
            if isinstance(rej, list):
                return "; ".join(
                    str(r.get("reason", "")) for r in rej
                ) or "No rejection detail available."
            return str(rej)
        if q in ("stopped", "optimal"):
            return evt.get("why_stopped") or evt.get("why_optimal") or evt.get("explanation", "")
        if q == "continued":
            return (
                evt.get("why_continued")
                or f"The algorithm continued because: {evt.get('explanation', '')}"
            )
        if q == "dummy":
            return evt.get("what_if") or evt.get("detailed") or evt.get("explanation", "")
        if q == "epsilon":
            return evt.get("why") or evt.get("explanation", "")
        if q == "alternative":
            return (
                f"Alternative optima exist when non-basic cells have a zero improvement "
                f"index (transportation) or when additional zero cells exist in the final "
                f"reduced assignment matrix. "
                + evt.get("explanation", "")
            )
        if q == "loop":
            return (
                evt.get("loop_display")
                or str(evt.get("loop", "Loop not recorded for this step."))
            )
        if q == "what_if":
            wif = evt.get("what_if", {})
            if isinstance(wif, dict):
                desc = wif.get("description", "")
                alts = wif.get("alternatives", [])
                if alts:
                    alt_str = "; ".join(
                        f"Cell {a.get('cell')}: idx={a.get('improvement_index')}"
                        for a in alts
                    )
                    return f"{desc} Alternatives: {alt_str}"
                return desc or "No what-if detail available."
            return str(wif) or "No what-if detail available."

        return evt.get("explanation", "No detail available for this question.")
