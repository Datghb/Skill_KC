from __future__ import annotations

from vlearn_kc.review_quality import audit_teacher_reviews


def _review(**overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "kc_code": "retrieval_vs_memory",
        "decision": "revise",
        "scores": {
            "accuracy": 4,
            "granularity": 4,
            "naming_clarity": 4,
        },
        "criterion_notes": {
            "accuracy": "",
            "granularity": "",
            "naming_clarity": "",
        },
        "review_note": None,
        "suggested_actions": [],
    }
    return {**review, **overrides}


def test_audit_flags_non_pass_review_without_rationale() -> None:
    report = audit_teacher_reviews({"reviews": [_review()]})

    assert report["quality_gate_pass"] is False
    assert report["issue_counts"] == {
        "missing_rationale": 1,
        "missing_move_target": 0,
        "score_decision_mismatch": 1,
    }


def test_audit_requires_target_and_reason_for_move_action() -> None:
    report = audit_teacher_reviews(
        {
            "reviews": [
                _review(
                    decision="reject",
                    review_note="Sai nhóm",
                    suggested_actions=["move_component"],
                )
            ]
        }
    )

    assert report["issue_counts"]["missing_move_target"] == 1


def test_audit_accepts_action_with_target_and_rationale() -> None:
    report = audit_teacher_reviews(
        {
            "reviews": [
                _review(
                    scores={
                        "accuracy": 4,
                        "granularity": 3,
                        "naming_clarity": 3,
                    },
                    issue_tags=["placement"],
                    suggested_actions=[
                        {
                            "action": "move_component",
                            "target_group_code": "retrieval_foundations",
                            "reason_tag": "placement",
                        }
                    ],
                )
            ]
        }
    )

    assert report["quality_gate_pass"] is True
    assert report["issue_counts"] == {
        "missing_rationale": 0,
        "missing_move_target": 0,
        "score_decision_mismatch": 0,
    }
