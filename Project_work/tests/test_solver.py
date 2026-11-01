import pytest
from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod


def test_solver_balanced_problem():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        supply=[3, 3, 4],
        demand=[4, 3, 3],
        method=TransportationMethod.VOGEL,
    )
    assert result["success"]
    assert result["final_cost"] >= 0
    assert result["verification"]["passed"]
    assert result["initial_solution"] is not None
    assert result["optimized_solution"] is not None
    assert result["problem"] is not None


def test_solver_unbalanced_supply_greater():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[10, 5],
        demand=[5, 6],
        method=TransportationMethod.NORTH_WEST,
    )
    assert result["success"]
    bp = result["balanced_problem"]
    assert bp.dummy_destination_added is True
    assert result["verification"]["passed"]


def test_solver_unbalanced_demand_greater():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[10, 5],
        method=TransportationMethod.NORTH_WEST,
    )
    assert result["success"]
    bp = result["balanced_problem"]
    assert bp.dummy_source_added is True
    assert result["verification"]["passed"]


def test_solver_invalid_input():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[-5, 6],
        method=TransportationMethod.NORTH_WEST,
    )
    assert not result["success"]
    assert len(result["errors"]) > 0


def test_solver_verify_constraints():
    """Verify all methods produce solutions satisfying constraints."""
    solver = TransportationSolver()
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]

    for method in [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST,
                   TransportationMethod.VOGEL]:
        result = solver.solve(cost_matrix=cost, supply=supply, demand=demand,
                              method=method)
        assert result["success"], f"Method {method} failed"
        assert result["verification"]["passed"], f"Verification failed for {method}"


def test_solver_optimization_improves_all_methods():
    """Optimization with Stepping Stone must not worsen any initial solution."""
    solver = TransportationSolver()
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]

    for method in [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST,
                   TransportationMethod.VOGEL]:
        result = solver.solve(cost_matrix=cost, supply=supply, demand=demand,
                              method=method, optimize=True)
        opt = result["optimized_solution"]
        init = result["initial_solution"]
        assert opt.total_cost <= init.total_cost + 1e-6


def test_solver_events_recorded():
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.LEAST_COST,
    )
    assert len(result["events"]) > 0
    # Should include allocation events
    alloc_events = [e for e in result["events"] if e.get("operation") == "allocation"]
    assert len(alloc_events) > 0


def test_solver_reproducible():
    solver1 = TransportationSolver()
    solver2 = TransportationSolver()
    r1 = solver1.solve(
        cost_matrix=[[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        supply=[3, 3, 4],
        demand=[4, 3, 3],
        method=TransportationMethod.VOGEL,
    )
    r2 = solver2.solve(
        cost_matrix=[[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        supply=[3, 3, 4],
        demand=[4, 3, 3],
        method=TransportationMethod.VOGEL,
    )
    assert r1["final_cost"] == r2["final_cost"]
    assert r1["optimized_solution"].allocation == r2["optimized_solution"].allocation
