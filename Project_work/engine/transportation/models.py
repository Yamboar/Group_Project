"""Core data structures for transportation problems.

Semantics (formalised edge cases)
--------------------------------
* Zero supply / zero demand rows or columns are *accepted* and treated as
  dummy entries: they never receive an allocation. Callers (solver) surface
  a warning so the behaviour is never silent.
* Negative transportation costs are *rejected* by validation with guidance
  (use Restricted for a forbidden route). This matches the assignment module
  and avoids accidentally signing a profit route as a cost. Negative costs
  are mathematically well-defined but not supported by design.
* Degenerate pivots (a pivot drops more than one basic cell to zero, leaving
  fewer than m+n-1 positive cells) are *handled automatically* with an
  ε-perturbation so a valid spanning-tree basis is preserved. Every incidence
  is recorded (stepping_stone degenerate_pivot_count / events) and the solver
  reports a warning; it is never silent.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum

# Backwards-compatible sentinel. Restricted cells are now represented by the
# separate `restricted_cells` state (a set of (row, col) pairs), never by an
# artificial large cost value. PROHIBITED_COST is retained only so legacy
# callers that still mark matrices with it keep working.
PROHIBITED_COST = 1e15

# Tolerance for treating an allocation as "empty". Values at or below this
# magnitude are degeneracy artifacts (ε-perturbations) and carry zero real
# shipment, so they are stripped from the reported solution.
EPSILON = 1e-9


def clean_allocation(allocation):
    """Return a copy of an allocation matrix with sub-epsilon values zeroed.

    Degeneracy handling injects tiny ε values (EPSILON) into cells purely to
    keep a valid basis. These cells represent zero real shipment, so they are
    reset to 0.0 for reporting so that costs, constraint sums, and the UI
    display are all accurate.
    """
    return [
        [0.0 if abs(v) <= EPSILON else float(v) for v in row]
        for row in allocation
    ]


class TransportationMethod(Enum):
    NORTH_WEST = "North-West Corner Method"
    LEAST_COST = "Least Cost Method"
    VOGEL = "Vogel's Approximation Method"


@dataclass
class TransportationProblem:
    cost_matrix: List[List[float]]
    supply: List[float]
    demand: List[float]
    source_names: Optional[List[str]] = None
    dest_names: Optional[List[str]] = None
    # Set of (row, col) pairs whose routes are completely restricted.
    # A restricted cell carries no cost value in the matrix and can never be
    # allocated; it is entirely separate from a normal zero-cost cell.
    restricted_cells: Optional[Set[Tuple[int, int]]] = None
    num_sources: int = 0
    num_destinations: int = 0

    def __post_init__(self):
        self.num_sources = len(self.cost_matrix)
        self.num_destinations = len(self.cost_matrix[0]) if self.num_sources > 0 else 0
        if self.source_names is None:
            self.source_names = [f"Source {i+1}" for i in range(self.num_sources)]
        if self.dest_names is None:
            self.dest_names = [f"Destination {j+1}" for j in range(self.num_destinations)]
        if self.restricted_cells is None:
            self.restricted_cells = set()
        else:
            self.restricted_cells = set(self.restricted_cells)

    # Backwards-compatible alias for legacy callers that used `prohibited_routes`.
    @property
    def prohibited_routes(self) -> Set[Tuple[int, int]]:
        return self.restricted_cells

    @prohibited_routes.setter
    def prohibited_routes(self, value) -> None:
        self.restricted_cells = set(value or [])

    @property
    def total_supply(self) -> float:
        return sum(self.supply)

    @property
    def total_demand(self) -> float:
        return sum(self.demand)

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_supply - self.total_demand) < 1e-9

    def is_restricted(self, i: int, j: int) -> bool:
        return (i, j) in self.restricted_cells

    def is_prohibited(self, i: int, j: int) -> bool:
        return self.is_restricted(i, j)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_matrix": self.cost_matrix,
            "supply": self.supply,
            "demand": self.demand,
            "source_names": self.source_names,
            "dest_names": self.dest_names,
            "restricted_cells": [
                list(cell) for cell in self.restricted_cells
            ] if self.restricted_cells else [],
            "prohibited_routes": [
                list(cell) for cell in self.restricted_cells
            ] if self.restricted_cells else [],
        }


@dataclass
class BalancedTransportationProblem:
    original_problem: TransportationProblem
    cost_matrix: List[List[float]]
    supply: List[float]
    demand: List[float]
    source_names: List[str]
    dest_names: List[str]
    dummy_source_added: bool = False
    dummy_destination_added: bool = False
    dummy_source_name: Optional[str] = None
    dummy_destination_name: Optional[str] = None
    # Restricted cells in the balanced problem's coordinate space.
    restricted_cells: Set[Tuple[int, int]] = field(default_factory=set)
    num_sources: int = 0
    num_destinations: int = 0

    def __post_init__(self):
        self.num_sources = len(self.cost_matrix)
        self.num_destinations = len(self.cost_matrix[0]) if self.num_sources > 0 else 0

    # Backwards-compatible alias for legacy callers.
    @property
    def prohibited_routes(self) -> Set[Tuple[int, int]]:
        return self.restricted_cells

    @prohibited_routes.setter
    def prohibited_routes(self, value) -> None:
        self.restricted_cells = set(value or [])

    def is_restricted(self, i: int, j: int) -> bool:
        return (i, j) in self.restricted_cells

    def is_prohibited(self, i: int, j: int) -> bool:
        return self.is_restricted(i, j)


@dataclass
class AllocationDecision:
    row: int
    col: int
    quantity: float
    supply_remaining: float
    demand_remaining: float
    explanation: str = ""
    # XAI: alternatives that were considered but not selected
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    tie_broken: bool = False
    tie_break_reason: str = ""


@dataclass
class DegeneracyInfo:
    """Records degeneracy detection and handling at any stage."""
    detected: bool = False
    stage: str = ""          # "initial", "iteration_N", "final"
    required_basic_vars: int = 0
    actual_basic_vars: int = 0
    epsilon_cells_added: List[Tuple[int, int]] = field(default_factory=list)
    explanation: str = ""


@dataclass
class InitialSolutionResult:
    method: TransportationMethod
    allocation: List[List[float]]
    total_cost: float
    decisions: List[AllocationDecision]
    intermediate_states: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    degeneracy_info: Optional[DegeneracyInfo] = None


@dataclass
class SteppingStoneCandidate:
    row: int
    col: int
    loop: List[List[int]]
    signs: List[str]
    improvement_index: float
    explanation: str = ""
    # XAI: full loop path for display
    loop_display: str = ""
    # Whether this candidate represents an alternative optimum (index == 0)
    is_alternative_optimum: bool = False


@dataclass
class SteppingStoneIteration:
    iteration: int
    candidates: List[SteppingStoneCandidate]
    best_candidate: Optional[SteppingStoneCandidate]
    adjustment_quantity: float
    old_allocation: List[List[float]]
    new_allocation: List[List[float]]
    old_cost: float
    new_cost: float
    explanation: str = ""
    # All candidates sorted by improvement index for XAI
    all_candidates_summary: List[Dict[str, Any]] = field(default_factory=list)
    degeneracy_after: bool = False


@dataclass
class OptimizedSolutionResult:
    allocation: List[List[float]]
    total_cost: float
    iterations: List[SteppingStoneIteration]
    is_optimal: bool
    final_improvement_indices: List[SteppingStoneCandidate]
    explanation: str = ""
    # True when one or more non-basic cells have improvement_index == 0 at optimality
    has_alternative_optima: bool = False
    alternative_optima_cells: List[Tuple[int, int]] = field(default_factory=list)
    degeneracy_info: Optional[DegeneracyInfo] = None
    # How many Stepping Stone pivots produced a degenerate basis (fewer than
    # m+n-1 positive cells), each handled with an ε-perturbation.
    degenerate_pivot_count: int = 0
    # Full XAI event log for the optimization phase (start, iterations,
    # degeneracy events, alternative-optimum detection, completion).
    events: List[Dict[str, Any]] = field(default_factory=list)
    # Whether we hit the iteration limit without proving optimality
    hit_iteration_limit: bool = False


@dataclass
class WhatIfTransportationResult:
    """Comparison result between original solution and a modified scenario."""
    original_cost: float
    new_cost: float
    cost_changed: bool
    cost_difference: float
    allocation_changed: bool
    optimal_solution_changed: bool
    changes_applied: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class TransportationSolution:
    problem: TransportationProblem
    balanced_problem: Optional[BalancedTransportationProblem]
    initial_solution: InitialSolutionResult
    optimized_solution: Optional[OptimizedSolutionResult]
    verification_passed: bool
    verification_details: Dict[str, Any]
    total_cost: float
    is_optimized: bool
