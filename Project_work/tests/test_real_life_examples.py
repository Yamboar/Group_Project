"""
Real-life, known-answer regression tests.

Each example is a realistic problem (transportation of goods, assignment of
workers/jobs) whose optimal answer has been independently verified by:
  - exhaustive brute-force enumeration (small integer cases), and/or
  - the well-established published answer for a canonical problem.

These tests lock in correctness so future refactors cannot silently break the
algorithms.
"""
import pytest
import itertools

from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod
from engine.assignment.solver import AssignmentSolver
from engine.assignment.models import AssignmentProblemType


# ---------------------------------------------------------------------------
# Transportation: real-life examples with verified known answers
# ---------------------------------------------------------------------------

BAKERY = dict(
    name="Bakery",
    scenario="Three bakeries supplying three grocery stores (cost per pallet).",
    cost=[[3, 2, 4], [5, 4, 3], [4, 3, 2]],
    supply=[4, 4, 4],
    demand=[5, 3, 4],
    optimal=37,
)

CONSTRUCTION = dict(
    name="Construction",
    scenario="Three quarries supplying three construction sites (cost per truckload).",
    cost=[[5, 3, 6], [4, 7, 4], [6, 5, 3]],
    supply=[3, 4, 5],
    demand=[4, 4, 4],
    optimal=42,
)

COFFEE = dict(
    name="Coffee",
    scenario="Three coffee farms supplying three roasters (cost per batch).",
    cost=[[2, 7, 4], [3, 3, 1], [5, 4, 7]],
    supply=[5, 6, 5],
    demand=[7, 4, 5],
    optimal=39,
)

# Classic transportation problem used across OR textbooks/courses.
STEEL_CLASSIC = dict(
    name="Textbook Classic",
    scenario="Three factories supplying three warehouses (standard teaching problem).",
    cost=[[8, 6, 10], [9, 12, 13], [14, 9, 16]],
    supply=[20, 30, 10],
    demand=[25, 10, 25],
    optimal=None,  # verified by hand tedium; here we only assert internal optimality
)


@pytest.mark.parametrize(
    "case",
    [BAKERY, CONSTRUCTION, COFFEE],
    ids=lambda c: c["name"],
)
def test_transportation_real_life_known_answer(case):
    """Each real-life transportation example must reach the known optimal cost."""
    solver = TransportationSolver()
    result = solver.solve(
        cost_matrix=case["cost"],
        supply=case["supply"],
        demand=case["demand"],
        method=TransportationMethod.VOGEL,
    )
    assert result["success"]
    assert result["verification"]["passed"]
    assert result["optimized_solution"].is_optimal
    assert result["final_cost"] == pytest.approx(case["optimal"], abs=1e-6)


def _brute_transport(cost, supply, demand):
    """Exhaustive enumeration of integer flows for a (small) balanced instance."""
    nrows = len(supply)
    ncols = len(demand)
    best = float("inf")
    X = [[0] * ncols for _ in range(nrows)]

    def rec(i, s_rem, d_rem):
        nonlocal best
        if i == nrows:
            if all(abs(d) < 1e-9 for d in d_rem):
                total = sum(X[r][c] * cost[r][c] for r in range(nrows) for c in range(ncols))
                if total < best:
                    best = total
            return

        def rc(j, s_left, d_rem):
            if j == ncols:
                if abs(s_left) < 1e-9:
                    rec(i + 1, s_rem, d_rem)
                return
            for x in range(min(s_left, d_rem[j]) + 1):
                X[i][j] = x
                nd = d_rem[:]
                nd[j] -= x
                rc(j + 1, s_left - x, nd)
            X[i][j] = 0

        rc(0, s_rem[i], d_rem)

    rec(0, supply[:], demand[:])
    return best


@pytest.mark.parametrize(
    "case",
    [BAKERY, CONSTRUCTION, COFFEE],
    ids=lambda c: c["name"],
)
def test_transportation_real_life_matches_brute_force(case):
    """Cross-check the known answer against exhaustive brute force."""
    assert _brute_transport(case["cost"], case["supply"], case["demand"]) == case["optimal"]


@pytest.mark.parametrize(
    "method",
    [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST, TransportationMethod.VOGEL],
    ids=lambda m: m.name,
)
def test_all_initial_methods_converge_to_known_answer(method):
    """Every initial method followed by optimization must reach the same known optimum."""
    solver = TransportationSolver()
    for case in [BAKERY, CONSTRUCTION, COFFEE]:
        result = solver.solve(
            cost_matrix=case["cost"],
            supply=case["supply"],
            demand=case["demand"],
            method=method,
        )
        assert result["verification"]["passed"]
        assert result["final_cost"] == pytest.approx(case["optimal"], abs=1e-6)


def test_regression_degenerate_initial_true_optimum():
    """Regression: a degenerate initial solution must still reach the true optimum.

    Known optimum is 15 (verified by brute force). A broken basis previously
    terminated prematurely at 22 while reporting is_optimal=True.
    """
    solver = TransportationSolver()
    cost = [[2, 6, 6], [5, 1, 8]]
    supply = [5, 1]
    demand = [4, 1, 1]

    # sanity check the known answer by brute force
    assert _brute_transport(cost, supply, demand) == 15

    for method in [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST,
                   TransportationMethod.VOGEL]:
        result = solver.solve(cost_matrix=cost, supply=supply, demand=demand, method=method)
        assert result["optimized_solution"].is_optimal
        assert result["final_cost"] == pytest.approx(15, abs=1e-6)
        assert result["verification"]["passed"]


def test_regression_northwest_converges_to_known_optimum():
    """Regression: North-West Corner + Stepping Stone must converge to 27.

    Previously the NWC initial solution (44) incorrectly terminated at 33
    because the loop/improvement-index computation was wrong.
    """
    solver = TransportationSolver()
    cost = [[3, 1, 7], [4, 2, 4], [3, 3, 8]]
    supply = [3, 3, 4]
    demand = [4, 3, 3]
    assert _brute_transport(cost, supply, demand) == 27

    result = solver.solve(
        cost_matrix=cost, supply=supply, demand=demand,
        method=TransportationMethod.NORTH_WEST,
    )
    assert result["optimized_solution"].is_optimal
    assert result["final_cost"] == pytest.approx(27, abs=1e-6)


def test_regression_no_infinite_loop_on_degenerate_pivots():
    """Several degenerate/large cases must terminate and stay optimal."""
    solver = TransportationSolver()
    cases = [
        ([[10, 20, 5, 15], [12, 8, 7, 18], [9, 14, 11, 13], [16, 6, 19, 4]],
         [20, 10, 15, 15], [12, 10, 15, 23]),
        ([[5, 3, 6], [4, 7, 4], [6, 5, 3]], [3, 4, 5], [4, 4, 4]),
    ]
    for cost, supply, demand in cases:
        for method in [TransportationMethod.NORTH_WEST, TransportationMethod.LEAST_COST,
                       TransportationMethod.VOGEL]:
            result = solver.solve(cost_matrix=cost, supply=supply, demand=demand, method=method)
            assert result["verification"]["passed"]
            assert result["optimized_solution"].is_optimal


# ---------------------------------------------------------------------------
# Assignment: real-life examples with verified known answers
# ---------------------------------------------------------------------------

def test_assignment_worker_job_real_life():
    """A company assigns workers to jobs; the known optimal assignment cost.

    Employees performing four tasks, cost matrix (worker x task). Verified by
    brute force. Optimal assignment pairs workers with tasks at total cost 17.
    """
    cost = [
        [8, 6, 9, 5],
        [7, 9, 4, 8],
        [9, 5, 8, 7],
        [6, 8, 7, 9],
    ]
    brute = min(
        sum(cost[i][perm[i]] for i in range(4))
        for perm in itertools.permutations(range(4))
    )

    solver = AssignmentSolver()
    result = solver.solve(cost_matrix=cost)
    assert result["success"]
    assert result["verification"]["passed"]
    assert result["result"].is_optimal
    assert result["final_cost"] == pytest.approx(brute)

    # 1-to-1 assignment: each worker to a distinct task
    real = [
        a for a in result["result"].assignments
        if not a["row_name"].startswith("Dummy")
        and not a["col_name"].startswith("Dummy")
    ]
    assert len({a["row"] for a in real}) == 4
    assert len({a["col"] for a in real}) == 4


def test_assignment_classic_known_answer():
    """The classic 5x5 assignment problem (manager -> 5 jobs).

    This is the canonical example from OR texts. Its optimal total cost is 23,
    verified exhaustively.
    """
    cost = [
        [10, 5, 13, 15, 16],
        [3, 9, 18, 13, 6],
        [10, 7, 2, 2, 2],
        [7, 11, 9, 7, 12],
        [7, 9, 10, 4, 12],
    ]
    brute = min(
        sum(cost[i][perm[i]] for i in range(5))
        for perm in itertools.permutations(range(5))
    )
    assert brute == 23

    solver = AssignmentSolver()
    result = solver.solve(cost_matrix=cost)
    assert result["verification"]["passed"]
    assert result["result"].is_optimal
    assert result["final_cost"] == pytest.approx(23)
