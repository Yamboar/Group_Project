from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ExplanationLevel(Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"


class ExplanationCategory(Enum):
    VALIDATION = "validation"
    BALANCING = "balancing"
    ALLOCATION = "allocation"
    OPTIMIZATION = "optimization"
    VERIFICATION = "verification"
    COMPLETE = "complete"


@dataclass
class SolutionEvent:
    """A structured event produced by the algorithm engine."""
    event_id: int
    algorithm: str
    iteration: int
    operation: str
    category: ExplanationCategory
    cell: Optional[List[int]] = None
    quantity: Optional[float] = None
    cost_per_unit: Optional[float] = None
    total_cell_cost: Optional[float] = None
    improvement_index: Optional[float] = None
    adjustment_quantity: Optional[float] = None
    old_cost: Optional[float] = None
    new_cost: Optional[float] = None
    explanation_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Explanation:
    """A human-readable explanation for a solution event."""
    event_id: int
    level: ExplanationLevel
    concise: str = ""
    detailed: str = ""
    technical: str = ""


@dataclass
class SolutionExplanation:
    """Complete explanation for a solved problem."""
    algorithm: str
    problem_type: str
    events: List[SolutionEvent]
    explanations: List[Explanation]
    summary: str = ""
    key_decisions: List[str] = field(default_factory=list)
    optimality_reason: str = ""
