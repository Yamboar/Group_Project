"""Tests for restricted-cell handling in the transportation problem.

Covers:
- zero-cost cells are valid routes (never blank/restricted/invalid)
- negative / blank / non-numeric cells are rejected with guidance
- restricted cells are a separate state (never encoded as 0, negative, or a
  big artificial cost)
- every initial method and the Stepping Stone optimizer respect restrictions
- feasibility checks report meaningful cut-off / capacity / connectivity errors
- legacy `prohibited_routes` alias and `PROHIBITED_COST` sentinel still work
"""
import pytest

from engine.transportation.models import (
    TransportationProblem,
    TransportationMethod,
    PROHIBITED_COST,
)
from engine.transportation.validation import (
    validate_transportation_problem,
)
from engine.transportation.solver import TransportationSolver

solver = TransportationSolver()


def _restricted(cells):
    return [list(c) for c in cells]


# ── Validation semantics ────────────────────────────────────────────────────

def test_zero_cost_cell_is_valid():
    cost = [[0, 1], [2, 0]]
    supply = [5, 5]
    demand = [5, 5]
    ok, errors = validate_transportation_problem(cost, supply, demand)
    assert ok
    assert errors == []


def test_zero_cost_cell_is_not_treated_as_restricted():
    result = solver.solve(
        cost_matrix=[[0, 5], [5, 0]],
        supply=[5, 5],
        demand=[5, 5],
        method=TransportationMethod.LEAST_COST,
    )
    assert result["success"]
    assert result["problem"].restricted_cells == set()
    # zero-cost routes ARE used (never skipped as if they were restricted)
    alloc = result["optimized_solution"].allocation
    assert alloc[0][0] == 5.0


def test_negative_cost_rejected_with_restricted_guidance():
    cost = [[3, 1], [2, -6]]
    ok, errors = validate_transportation_problem(cost, [5, 6], [5, 6])
    assert not ok
    assert any("negative" in e and "Restricted" in e for e in errors)


def test_blank_cell_rejected_with_restricted_guidance():
    cost = [[3, 1], [2, None]]
    ok, errors = validate_transportation_problem(cost, [5, 6], [5, 6])
    assert not ok
    assert any("blank" in e and "Restricted" in e for e in errors)


def test_non_numeric_cell_rejected():
    cost = [[3, "x"], [2, 6]]
    ok, errors = validate_transportation_problem(cost, [5, 6], [5, 6])
    assert not ok
    assert any("not numeric" in e for e in errors)


def test_restricted_cell_value_is_exempt_from_validation():
    # A restricted cell may hold any placeholder (negative, blank, sentinel)
    # because its cost is irrelevant — it is never used.
    # Restricting (0,0) keeps the [[3,1],[2,6]] network feasible.
    for val in (-5, None, "x", PROHIBITED_COST):
        cost = [[3, 1], [2, 6]]
        cost[0][0] = val
        ok, errors = validate_transportation_problem(
            cost, [5, 6], [5, 6], restricted_cells={(0, 0)}
        )
        assert ok, f"restricted cell with {val!r} should be exempt: {errors}"
        assert errors == []


def test_out_of_bounds_restricted_cell_rejected():
    ok, errors = validate_transportation_problem(
        [[3, 1], [2, 6]], [5, 6], [5, 6], restricted_cells={(5, 5)}
    )
    assert not ok
    assert any("out-of-range" in e for e in errors)


def test_prohibited_routes_alias_merged():
    ok, errors = validate_transportation_problem(
        [[3, 1], [2, 6]], [5, 6], [5, 6], prohibited_routes={(0, 1)}
    )
    assert ok


# ── Method behaviour ▁with restrictions ──────────────────────────────────────

def test_all_methods_respect_restrictions():
    cost = [[3, 1, 7], [2, 6, 8], [9, 4, 2]]
    supply = [5, 6, 4]
    demand = [5, 4, 6]
    restricted = {(0, 0), (2, 1)}
    for method in TransportationMethod:
        result = solver.solve(
            cost_matrix=cost, supply=supply, demand=demand, method=method,
            optimize=True, restricted_cells=_restricted(restricted),
        )
        assert result["success"], (method, result["errors"])
        alloc = result["optimized_solution"].allocation
        initial = result["initial_solution"].allocation
        for alloc_matrix in (initial, alloc):
            for (i, j) in restricted:
                assert abs(alloc_matrix[i][j]) < 1e-6, (method, (i, j))
        assert abs(result["final_cost"] - 37.0) < 1e-6, (method, result["final_cost"])


def test_restricted_cells_force_route_changes_and_are_optimal():
    # (1,1) restricted forces col1 to be served by row0 and col0 by row1.
    cost = [[0, 5], [5, 0]]
    supply = [5, 5]
    demand = [5, 5]
    restricted = {(1, 1)}
    for method in TransportationMethod:
        result = solver.solve(
            cost_matrix=cost, supply=supply, demand=demand, method=method,
            optimize=True, restricted_cells=_restricted(restricted),
        )
        assert result["success"]
        alloc = result["optimized_solution"].allocation
        assert alloc[1][1] == 0.0
        assert abs(result["final_cost"] - 50.0) < 1e-6, (method, result["final_cost"])


def test_cells_only_reachable_through_restricted_still_feasible():
    # A greedy method alone would strand this; the pipeline must repair it.
    cost = [[3, 2], [8, 1]]
    supply = [5, 2]
    demand = [4, 3]
    restricted = {(1, 1)}
    for method in TransportationMethod:
        result = solver.solve(
            cost_matrix=cost, supply=supply, demand=demand, method=method,
            optimize=True, restricted_cells=_restricted(restricted),
        )
        assert result["success"], (method, result["errors"])
        assert result["verification"]["passed"], result["verification"]["issues"]
        assert abs(result["final_cost"] - 28.0) < 1e-6, (method, result["final_cost"])


def test_unbalanced_with_restrictions():
    # supply 14 < demand 20; dummy source added. col2 open only through dummy.
    cost = [[0, 1, 2], [1, 3, 3], [0, 8, 0], [5, 5, 2]]
    supply = [6, 4, 3, 5]
    demand = [1, 1, 5]
    restricted = {(1, 1), (1, 2), (2, 0), (2, 2)}
    for method in TransportationMethod:
        result = solver.solve(
            cost_matrix=cost, supply=supply, demand=demand, method=method,
            optimize=True, restricted_cells=_restricted(restricted),
        )
        assert result["success"], (method, result["errors"])
        assert result["verification"]["passed"]


# ── Feasibility failures ─────────────────────────────────────────────────────

def test_source_cut_off_reported():
    cost = [[3, 1], [2, 6], [9, 8]]
    ok, errors = validate_transportation_problem(
        cost, [5, 6, 4], [5, 10], restricted_cells={(2, 0), (2, 1)}
    )
    assert not ok
    assert any("all routes from it" in e for e in errors)


def test_destination_cut_off_reported():
    cost = [[3, 1], [2, 6]]
    ok, errors = validate_transportation_problem(
        cost, [5, 6], [5, 6], restricted_cells={(0, 1), (1, 1)}
    )
    assert not ok
    assert any("all routes to it" in e or "all routes" in e for e in errors)


def test_capacity_shortfall_reported():
    # Destination 2 needs 7, but only 6 units can reach it post-balancing.
    cost = [[5, 3, 3], [3, 3, 0]]
    supply = [7, 7]
    demand = [7, 6, 7]
    ok, errors = validate_transportation_problem(
        cost, supply, demand, restricted_cells={(0, 2), (1, 2)}
    )
    assert not ok
    assert any("only" in e and "can reach it" in e for e in errors)


def test_disconnected_open_network_reported():
    cost = [[1, 8], [8, 1]]
    ok, errors = validate_transportation_problem(
        cost, [5, 5], [5, 5], restricted_cells={(0, 1), (1, 0)}
    )
    assert not ok
    assert any("isolated components" in e for e in errors)


# ── Legacy support ──────────────────────────────────────────────────────────

def test_prohibited_routes_alias_in_solver():
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.LEAST_COST,
        prohibited_routes=[[0, 0]],
    )
    assert result["success"]
    assert (0, 0) in result["problem"].restricted_cells
    assert result["optimized_solution"].allocation[0][0] == 0.0


def test_legacy_prohibited_cost_sentinel_treated_as_restricted():
    cost = [[PROHIBITED_COST, 1], [2, 6]]
    result = solver.solve(
        cost_matrix=cost,
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.LEAST_COST,
    )
    assert result["success"]
    alloc = result["optimized_solution"].allocation
    assert alloc[0][0] == 0.0


def test_solution_model_exposes_restricted_cells():
    result = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.VOGEL,
        restricted_cells=[[1, 0]],
    )
    assert result["success"]
    problem = result["problem"]
    assert (1, 0) in problem.restricted_cells
    assert problem.is_restricted(1, 0)
    d = problem.to_dict()
    assert [0, 1] in d["restricted_cells"] or [1, 0] in d["restricted_cells"]
    assert "prohibited_routes" in d

def test_what_if_with_restrictions():
    original = solver.solve(
        cost_matrix=[[3, 1], [2, 6]],
        supply=[5, 6],
        demand=[5, 6],
        method=TransportationMethod.VOGEL,
    )
    comparison = solver.solve_what_if(
        original,
        restricted_cells=[[0, 0]],
        changes_applied=["Restricted cell (1,1)"],
    )
    assert comparison["success"]
    assert (0, 0) in comparison["problem"].restricted_cells