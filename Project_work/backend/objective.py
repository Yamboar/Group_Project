"""Objective-selection metadata helpers.

A plain-language objective selection (what the table values represent and which
way the user wants to optimise) is captured on the frontend and converted here
into the internal MIN/MAX objective used by the existing optimisation engines
WITHOUT changing the underlying mathematics. The full decision trail
(intent, value type, recommendation, confirmation/override, effect on the solve)
is recorded as an auditable event surfaced in the XAI explanation.
"""
from typing import Any, Dict, Optional, Tuple

RECOMMEND_MAX_FOR = {"profit", "revenue"}

VALUE_TYPE_LABELS = {
    "cost": "cost",
    "profit": "profit",
    "revenue": "revenue",
    "time": "time",
    "distance": "distance",
    "none": "",
}


def recommend_direction(value_type: Optional[str]) -> str:
    """Heuristic: profit/revenue -> maximise; costs/time/distance -> minimise."""
    if (value_type or "").strip().lower() in RECOMMEND_MAX_FOR:
        return "maximise"
    return "minimise"


def value_type_label(value_type: Optional[str], other_desc: Optional[str] = None) -> str:
    vt = (value_type or "").strip().lower()
    if vt == "other":
        return (other_desc or "").strip() or "other quantities"
    return VALUE_TYPE_LABELS.get(vt, "objective value")


def resolve_direction(
    objective: Optional[Dict[str, Any]],
    fallback: str,  # direction used when no objective is supplied ("minimise"/"maximise")
    locked_to: Optional[str] = None,  # if set, engine can ONLY solve this direction
) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """Resolve the chosen objective direction and build auditable metadata.

    Returns (resolved_direction, objective_metadata, warning_or_none).

    The user's stated intent is preserved in the metadata for transparency.
    When `locked_to` is set (e.g. a minimise-only transportation engine), the
    resolved direction is clamped to that value and a warning is produced if the
    user asked for the opposite.
    """
    warning = None
    if not objective:
        direction = fallback
        meta = {
            "intent": direction,
            "value_type": "none",
            "other_description": None,
            "recommended": recommend_direction(None),
            "confirmed": False,
            "overridden": False,
            "source": "default",
        }
        return direction, meta, warning

    intent = (str(objective.get("intent") or fallback)).strip().lower()
    if intent not in ("minimise", "maximise"):
        intent = fallback

    direction = intent
    if locked_to is not None and direction != locked_to:
        direction = locked_to
        warning = (
            f"The engine supports {locked_to} only, so the requested "
            f"'{intent}' was solved as {locked_to}."
        )

    value_type = (str(objective.get("value_type") or "none")).strip().lower()
    meta = {
        "intent": intent,
        "value_type": value_type,
        "other_description": objective.get("other_description"),
        "recommended": str(objective.get("recommended") or recommend_direction(value_type)),
        "confirmed": bool(objective.get("confirmed", False)),
        "overridden": bool(objective.get("overridden", False)),
        "source": "user",
    }
    return direction, meta, warning


def objective_event(meta: Dict[str, Any], direction: str, algo_locked: bool = False) -> Dict[str, Any]:
    """Build an 'objective' event dict that flows into the event log and XAI."""
    vt = value_type_label(meta.get("value_type"), meta.get("other_description"))
    intent = meta.get("intent", direction)
    recommended = meta.get("recommended", "minimise")
    confirmed = bool(meta.get("confirmed"))
    overridden = bool(meta.get("overridden"))

    what = f"to {intent} the total {vt}" if vt else f"to {intent} the objective value"

    if meta.get("source") == "default":
        decision = (
            "No objective was specified, so the engine solved the problem as "
            "minimisation."
        )
    elif overridden:
        decision = (
            f"You chose to override the recommendation and asked {what}. "
            f"The engine solved the problem as {direction}."
        )
    elif confirmed:
        decision = (
            f"You confirmed the recommended objective: {what}. "
            f"The engine solved the problem as {direction}."
        )
    else:
        decision = (
            f"You chose {what}. The engine solved the problem as {direction}."
        )

    if algo_locked:
        decision += " Note: this engine solves a minimisation problem only."

    return {
        "operation": "objective",
        "intent": intent,
        "direction": direction,
        "value_type": vt,
        "recommended": recommended,
        "confirmed": confirmed,
        "overridden": overridden,
        "concise": f"Objective: {what}.",
        "detailed": decision,
        "technical": (
            f"intent={intent}; direction={direction}; value_type={vt}; "
            f"recommended={recommended}; confirmed={confirmed}; overridden={overridden}."
        ),
        "explanation": decision,
    }
