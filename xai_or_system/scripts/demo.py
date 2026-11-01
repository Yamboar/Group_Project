"""Example problems for quick testing."""
from engine.transportation.solver import TransportationSolver
from engine.transportation.models import TransportationMethod

EXAMPLES = {
    "classic_3x3": {
        "name": "Classic 3x3",
        "cost_matrix": [[3, 1, 7], [4, 2, 4], [3, 3, 8]],
        "supply": [3, 3, 4],
        "demand": [4, 3, 3],
    },
    "unbalanced_supply": {
        "name": "Unbalanced (supply > demand)",
        "cost_matrix": [[3, 1], [2, 6]],
        "supply": [10, 5],
        "demand": [5, 6],
    },
    "assignment_3x3": {
        "name": "Assignment 3x3",
        "cost_matrix": [[4, 1, 3], [2, 0, 5], [3, 2, 2]],
    },
}


def run_demo():
    print("=" * 60)
    print("XAI-OR System - Algorithm Verification Demo")
    print("=" * 60)

    solver = TransportationSolver()

    print("\n1. Classic Transportation Problem (3x3)")
    print("-" * 40)
    ex = EXAMPLES["classic_3x3"]
    result = solver.solve(
        cost_matrix=ex["cost_matrix"],
        supply=ex["supply"],
        demand=ex["demand"],
        method=TransportationMethod.VOGEL,
    )
    print(f"  Success: {result['success']}")
    print(f"  Initial cost: {result['initial_solution'].total_cost:.2f}")
    print(f"  Final cost: {result['final_cost']:.2f}")
    print(f"  Optimal: {result['optimized_solution'].is_optimal}")
    print(f"  Verification passed: {result['verification']['passed']}")

    print("\n2. Unbalanced Transportation Problem")
    print("-" * 40)
    ex = EXAMPLES["unbalanced_supply"]
    result = solver.solve(
        cost_matrix=ex["cost_matrix"],
        supply=ex["supply"],
        demand=ex["demand"],
        method=TransportationMethod.NORTH_WEST,
    )
    bp = result["balanced_problem"]
    print(f"  Success: {result['success']}")
    print(f"  Dummy destination added: {bp.dummy_destination_added}")
    print(f"  Final cost: {result['final_cost']:.2f}")
    print(f"  Verification passed: {result['verification']['passed']}")

    from engine.assignment.solver import AssignmentSolver
    from engine.assignment.models import AssignmentProblemType

    print("\n3. Assignment Problem (3x3)")
    print("-" * 40)
    a_solver = AssignmentSolver()
    ex = EXAMPLES["assignment_3x3"]
    a_result = a_solver.solve(cost_matrix=ex["cost_matrix"])
    print(f"  Success: {a_result['success']}")
    print(f"  Total cost: {a_result['final_cost']:.2f}")
    print(f"  Assignments: {len(a_result['result'].assignments)}")
    print(f"  Verification passed: {a_result['verification']['passed']}")
    for a in a_result["result"].assignments:
        if not a["row_name"].startswith("Dummy") and not a["col_name"].startswith("Dummy"):
            print(f"    {a['row_name']} -> {a['col_name']} (cost: {a['original_cost']})")

    print("\n" + "=" * 60)
    print("All verifications complete.")


if __name__ == "__main__":
    run_demo()
