from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


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
    num_sources: int = 0
    num_destinations: int = 0

    def __post_init__(self):
        self.num_sources = len(self.cost_matrix)
        self.num_destinations = len(self.cost_matrix[0]) if self.num_sources > 0 else 0
        if self.source_names is None:
            self.source_names = [f"Source {i+1}" for i in range(self.num_sources)]
        if self.dest_names is None:
            self.dest_names = [f"Destination {j+1}" for j in range(self.num_destinations)]

    @property
    def total_supply(self) -> float:
        return sum(self.supply)

    @property
    def total_demand(self) -> float:
        return sum(self.demand)

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_supply - self.total_demand) < 1e-9

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_matrix": self.cost_matrix,
            "supply": self.supply,
            "demand": self.demand,
            "source_names": self.source_names,
            "dest_names": self.dest_names,
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
    num_sources: int = 0
    num_destinations: int = 0

    def __post_init__(self):
        self.num_sources = len(self.cost_matrix)
        self.num_destinations = len(self.cost_matrix[0]) if self.num_sources > 0 else 0


@dataclass
class AllocationDecision:
    row: int
    col: int
    quantity: float
    supply_remaining: float
    demand_remaining: float
    explanation: str = ""


@dataclass
class InitialSolutionResult:
    method: TransportationMethod
    allocation: List[List[float]]
    total_cost: float
    decisions: List[AllocationDecision]
    intermediate_states: List[Dict[str, Any]]
    events: List[Dict[str, Any]]


@dataclass
class SteppingStoneCandidate:
    row: int
    col: int
    loop: List[List[int]]
    signs: List[str]
    improvement_index: float
    explanation: str = ""


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


@dataclass
class OptimizedSolutionResult:
    allocation: List[List[float]]
    total_cost: float
    iterations: List[SteppingStoneIteration]
    is_optimal: bool
    final_improvement_indices: List[SteppingStoneCandidate]
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
