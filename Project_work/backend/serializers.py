"""Serialization helpers to convert solver dataclass results into JSON-serializable dicts."""
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import is_dataclass, fields


def _to_serializable(obj: Any) -> Any:
    """Recursively convert dataclasses and enums into JSON-serializable values.

    Also converts float('inf') / float('-inf') / float('nan') to None so the
    JSON serializer never encounters a non-finite float.
    """
    if obj is None:
        return None
    if isinstance(obj, float):
        import math
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        result = {}
        for f in fields(obj):
            key = f.name
            value = _to_serializable(getattr(obj, f.name))
            result[key] = value
        return result
    if isinstance(obj, dict):
        return {str(k): _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, set):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, (int, bool, str)):
        return obj
    if hasattr(obj, "to_dict"):
        return _to_serializable(obj.to_dict())
    return str(obj)


def serialize_transportation_problem(problem: Any) -> Dict[str, Any]:
    """Serialize a TransportationProblem or BalancedTransportationProblem."""
    return _to_serializable(problem)


def serialize_initial_solution(initial: Any) -> Dict[str, Any]:
    """Serialize an InitialSolutionResult."""
    if initial is None:
        return None
    return _to_serializable(initial)


def serialize_optimized_solution(optimized: Any) -> Dict[str, Any]:
    """Serialize an OptimizedSolutionResult."""
    if optimized is None:
        return None
    return _to_serializable(optimized)


def serialize_assignment_result(result: Any) -> Dict[str, Any]:
    """Serialize an AssignmentResult."""
    if result is None:
        return None
    return _to_serializable(result)


def serialize_solution_explanation(explanation: Any) -> Dict[str, Any]:
    """Serialize a SolutionExplanation."""
    if explanation is None:
        return None
    return _to_serializable(explanation)


def serialize_transportation_solution(solution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize the full transportation solver result dict for JSON response."""
    return _to_serializable(solution_data)


def serialize_assignment_solution(solution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize the full assignment solver result dict for JSON response."""
    return _to_serializable(solution_data)
