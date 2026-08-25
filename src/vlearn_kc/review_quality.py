from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


ISSUE_TYPES = (
    "missing_rationale",
    "missing_move_target",
    "score_decision_mismatch",
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _reviews(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("reviews", "completed_reviews"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    raise ValueError("review payload must contain reviews or completed_reviews")


def _has_rationale(review: Mapping[str, Any]) -> bool:
    if _text(review.get("review_note")) or _text(review.get("comment_vi")):
        return True
    notes = review.get("criterion_notes")
    if isinstance(notes, Mapping) and any(_text(value) for value in notes.values()):
        return True
    tags = review.get("issue_tags")
    if isinstance(tags, list) and any(_text(value) for value in tags):
        return True
    actions = review.get("suggested_actions")
    if isinstance(actions, list):
        return any(
            isinstance(action, Mapping)
            and (_text(action.get("reason_tag")) or _text(action.get("note_vi")))
            for action in actions
        )
    return False


def _move_without_target(review: Mapping[str, Any]) -> bool:
    actions = review.get("suggested_actions")
    if not isinstance(actions, list):
        return False
    for action in actions:
        if action == "move_component":
            return True
        if (
            isinstance(action, Mapping)
            and action.get("action") == "move_component"
            and not _text(action.get("target_group_code"))
        ):
            return True
    return False


def _high_scores_with_non_pass(review: Mapping[str, Any], decision: str) -> bool:
    if decision not in {"revise", "reject"}:
        return False
    scores = review.get("scores")
    if not isinstance(scores, Mapping) or not scores:
        return False
    numeric_scores = [
        value
        for value in scores.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    return len(numeric_scores) == len(scores) and min(numeric_scores) >= 4


def audit_teacher_reviews(payload: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    reviews = _reviews(payload)
    for index, review in enumerate(reviews):
        code = _text(review.get("kc_code")) or f"review[{index}]"
        decision = _text(review.get("decision")).lower()
        has_rationale = _has_rationale(review)
        if decision in {"revise", "reject"} and not has_rationale:
            issues.append({"kc_code": code, "issue": "missing_rationale"})
        if _move_without_target(review):
            issues.append({"kc_code": code, "issue": "missing_move_target"})
        if _high_scores_with_non_pass(review, decision) and not has_rationale:
            issues.append({"kc_code": code, "issue": "score_decision_mismatch"})

    counts = Counter(issue["issue"] for issue in issues)
    return {
        "schema_version": "vlearn_teacher_review_audit_v1",
        "review_count": len(reviews),
        "quality_gate_pass": not issues,
        "issue_counts": {name: counts[name] for name in ISSUE_TYPES},
        "issues": issues,
    }
