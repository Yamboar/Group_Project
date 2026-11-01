"""Tests for the objective-selection metadata and its effect on solving."""
import pytest

from backend.objective import (
    recommend_direction,
    value_type_label,
    resolve_direction,
    objective_event,
)
from backend.schemas import AssignmentSolveRequest, ObjectiveSelection
from backend.routers.assignment import _resolve_objective, _attach_objective
from engine.assignment.models import AssignmentProblemType


class _FakeObjective:
    def __init__(self, data):
        self._data = data

    def model_dump(self):
        return dict(self._data)


class _FakeRequest:
    def __init__(self, objective, problem_type="Minimization"):
        self.objective = objective
        self.problem_type = problem_type


class _FakeResult(dict):
    def __init__(self):
        super().__init__(success=True, events=[], warnings=[])


# ── recommend_direction / value_type_label ───────────────────────────────────

def test_recommend_cost_minimise():
    assert recommend_direction("cost") == "minimise"
    assert recommend_direction("time") == "minimise"
    assert recommend_direction("distance") == "minimise"
    assert recommend_direction(None) == "minimise"


def test_recommend_profit_maximise():
    assert recommend_direction("profit") == "maximise"
    assert recommend_direction("revenue") == "maximise"


def test_value_type_label_other():
    assert value_type_label("other", "carbon tonnes") == "carbon tonnes"
    assert value_type_label("cost") == "cost"
    assert value_type_label("none") == ""


# ── resolve_direction ────────────────────────────────────────────────────────

def test_resolve_no_objective_defaults():
    direction, meta, warning = resolve_direction(None, "minimise")
    assert direction == "minimise"
    assert meta["source"] == "default"
    assert warning is None


def test_resolve_transport_forced_minimise():
    direction, meta, warning = resolve_direction(
        {
            "intent": "maximise",
            "value_type": "profit",
            "recommended": "maximise",
            "confirmed": True,
            "overridden": False,
        },
        fallback="minimise",
        locked_to="minimise",  # minimise-only transportation engine
    )
    assert direction == "minimise"
    assert meta["intent"] == "maximise"  # user intent preserved for the trail
    assert warning is not None


def test_resolve_assignment_respects_intent():
    direction, meta, warning = resolve_direction(
        {
            "intent": "maximise",
            "value_type": "profit",
            "recommended": "maximise",
            "confirmed": True,
            "overridden": False,
        },
        fallback="minimise",
        locked_to=None,  # assignment engine can maximise, so no clamp
    )
    assert direction == "maximise"
    assert warning is None
    assert meta["intent"] == "maximise"


# ── event text ───────────────────────────────────────────────────────────────

def test_objective_event_confirmed():
    ev = objective_event(
        {
            "intent": "minimise",
            "value_type": "cost",
            "recommended": "minimise",
            "confirmed": True,
            "overridden": False,
        },
        "minimise",
    )
    assert ev["operation"] == "objective"
    assert "minimise the total cost" in ev["concise"]
    assert "confirmed" in ev["detailed"]


def test_objective_event_overridden():
    ev = objective_event(
        {
            "intent": "maximise",
            "value_type": "profit",
            "recommended": "minimise",
            "confirmed": False,
            "overridden": True,
        },
        "maximise",
    )
    assert "override" in ev["detailed"]


# ── assignment routing integration ───────────────────────────────────────────

def test_assignment_resolve_maximise_objective():
    req = _FakeRequest(_FakeObjective({
        "intent": "maximise",
        "value_type": "profit",
        "recommended": "maximise",
        "confirmed": True,
        "overridden": False,
    }))
    ptype, direction, meta, warning = _resolve_objective(req)
    assert ptype == AssignmentProblemType.MAXIMIZATION
    assert direction == "maximise"
    assert meta is not None
    assert warning is None


def test_assignment_resolve_minimise_objective():
    req = _FakeRequest(_FakeObjective({
        "intent": "minimise",
        "value_type": "cost",
        "recommended": "minimise",
        "confirmed": True,
        "overridden": False,
    }))
    ptype, direction, meta, warning = _resolve_objective(req)
    assert ptype == AssignmentProblemType.MINIMIZATION
    assert direction == "minimise"


def test_assignment_resolve_fallback_problem_type():
    req = _FakeRequest(None, problem_type="Maximization")
    ptype, direction, meta, warning = _resolve_objective(req)
    assert ptype == AssignmentProblemType.MAXIMIZATION
    assert direction == "maximise"
    assert meta is None


def test_attach_objective_records_event_and_trail():
    result = _FakeResult()
    meta = {
        "intent": "minimise",
        "value_type": "cost",
        "other_description": None,
        "recommended": "minimise",
        "confirmed": True,
        "overridden": False,
        "source": "user",
    }
    _attach_objective(result, meta, "minimise")
    assert result["events"][0]["operation"] == "objective"
    assert result["objective_selection"]["resolved_direction"] == "minimise"


def test_attach_objective_none_is_noop():
    result = _FakeResult()
    _attach_objective(result, None, "minimise")
    assert result["events"] == []
