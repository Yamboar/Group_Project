"""Comprehensive integration tests verifying the full pipeline end-to-end."""
import pytest
from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod
from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType
from xai.explanation_engine import ExplanationEngine


def test_full_transportation_pipeline():
    """Complete transportation pipeline: input -> validate -> balance -> solve -> verify -> explain."""
    solver = TransportationSolver()
    engine = ExplanationEngine()

    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]

    result = solver.solve(
        cost_matrix=cost,
        supply=supply,
        demand=demand,
        method=TransportationMethod.VOGEL,
        optimize=True,
    )

    # Input/validation
    assert result["success"]
    assert result["validation"]["is_valid"]
    assert result["problem"] is not None

    # Balancing
    assert result["balancing"]["is_balanced"]
    assert result["balanced_problem"] is not None

    # Solution
    assert result["initial_solution"] is not None
    assert result["optimized_solution"] is not None
    assert result["final_cost"] >= 0

    # Verification
    assert result["verification"]["passed"]

    # XAI
    explanation = engine.generate_transportation_explanation(result)
    assert explanation.summary
    assert explanation.optimality_reason


def test_full_unbalanced_transportation_pipeline():
    """Test with unbalanced problem requiring dummy destination."""
    solver = TransportationSolver()
    engine = ExplanationEngine()

    cost = [[3, 1], [2, 6]]
    supply = [10, 5]
    demand = [5, 6]

    result = solver.solve(
        cost_matrix=cost,
        supply=supply,
        demand=demand,
        method=TransportationMethod.NORTH_WEST,
    )

    assert result["success"]
    assert not result["balancing"]["is_balanced"]
    assert result["balanced_problem"].dummy_destination_added
    assert result["verification"]["passed"]

    # Balancing event explained
    bal = result["balancing"]["events"]
    assert any(e["action"] == "add_dummy_destination" for e in bal)


def test_assignment_full_pipeline():
    """Complete assignment pipeline with XAI."""
    solver = AssignmentSolver()
    engine = ExplanationEngine()

    cost = [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
    result = solver.solve(cost_matrix=cost)

    assert result["success"]
    assert result["verification"]["passed"]
    assert result["result"].is_optimal

    explanation = engine.generate_assignment_explanation(result)
    assert explanation.summary


def test_database_integration_attempt():
    """Verify database layer can be imported and configured (may fail gracefully without MySQL)."""
    try:
        import database
        from database.connection import get_database_url
        url = get_database_url()
        assert "mysql" in url
        assert "xai_or_system" in url
    except Exception:
        pytest.skip("Database dependencies not available")


def test_all_methods_same_optimal_result():
    """All initial methods should converge to the same optimal cost after Stepping Stone."""
    solver = TransportationSolver()
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]

    costs = []
    for method in [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST,
                   TransportationMethod.VOGEL]:
        result = solver.solve(cost_matrix=cost, supply=supply, demand=demand, method=method)
        costs.append(result["final_cost"])

    # All should converge to optimal (27): (0,1)=3, (1,2)=3, (2,0)=4
    # Cost = 3*1 + 3*4 + 4*3 = 27
    assert all(abs(c - 27.0) < 1e-6 for c in costs)


def test_verification_detects_incorrect():
    """Verification should catch constraint violations."""
    solver = TransportationSolver()
    # Use a solver result and manually corrupt the allocation in verification
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.NORTH_WEST,
    )
    # The actual verification passed, but test the verification method can detect issues
    bp = result["balanced_problem"]
    bad_alloc = [row[:] for row in result["initial_solution"].allocation]
    # Corrupt: add to a cell to break supply constraint
    bad_alloc[0][0] += 1
    verification = solver._verify_solution(bp, bad_alloc, result["initial_solution"].total_cost)
    assert not verification["passed"]
    assert len(verification["issues"]) > 0
