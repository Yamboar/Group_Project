from xai.explanation_engine import ExplanationEngine
from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod
from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType


def test_explanation_generation_transportation():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        supply=[3, 3, 4],
        demand=[4, 3, 3],
        method=TransportationMethod.NORTH_WEST,
    )
    engine = ExplanationEngine()
    explanation = engine.generate_transportation_explanation(result)

    assert explanation.algorithm == "North-West Corner Method"
    assert explanation.problem_type == "Transportation"
    assert explanation.summary
    assert len(explanation.key_decisions) > 0
    assert explanation.optimality_reason


def test_explanation_events_from_calculation():
    """Explanations must be traceable to actual events."""
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.LEAST_COST,
    )
    engine = ExplanationEngine()
    explanation = engine.generate_transportation_explanation(result)
    # Each explanation corresponds to a real event
    assert len(explanation.events) == len(explanation.explanations)
    for e in explanation.explanations:
        assert e.event_id >= 1


def test_explanation_assignment():
    solver = AssignmentSolver()
    result = solver.solve(cost_matrix=[[2, 3], [3, 2]])
    engine = ExplanationEngine()
    explanation = engine.generate_assignment_explanation(result)
    assert explanation.algorithm == "Hungarian Method"
    assert explanation.problem_type == "Assignment"
    assert explanation.summary
    assert explanation.optimality_reason


def test_concise_vs_detailed():
    """Concise and detailed explanations should differ."""
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.NORTH_WEST,
    )
    engine = ExplanationEngine()
    explanation = engine.generate_transportation_explanation(result)
    # At least some concise/detailed differ
    has_difference = any(e.concise != e.detailed for e in explanation.explanations)
    assert has_difference


def test_balancing_explanation_included():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[10, 5],
        demand=[5, 6],
        method=TransportationMethod.NORTH_WEST,
    )
    engine = ExplanationEngine()
    explanation = engine.generate_transportation_explanation(result)
    # Balancing event should be recorded
    bal_exps = [e for e in explanation.explanations
                if "dummy" in (e.detailed or "").lower() or "balance" in (e.detailed or "").lower()]
    assert len(bal_exps) > 0
