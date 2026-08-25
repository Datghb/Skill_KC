from __future__ import annotations

import pytest

from vlearn_kc.refinement import validate_move_without_merge


def _group(code: str, home: int, members: list[str]) -> dict:
    return {
        "parent_code": code,
        "ward_home_cluster_index": home,
        "name_vi": code,
        "name_en": code,
        "description_vi": f"Description {code}",
        "boundary_notes_vi": "Boundary",
        "member_codes": members,
        "coherence": "high",
        "pg_readiness_reason_vi": "One parent family.",
        "singleton_justification_vi": "Independent" if len(members) == 1 else "",
    }


def _response() -> dict:
    return {
        "source_slug": "day01-source",
        "ward_reference_k": 2,
        "ward_reference_reason_vi": "Two baseline families.",
        "final_k": 2,
        "cluster_count_reason_vi": "Two final families.",
        "overall_change_summary_vi": "Move C.",
        "post_selection_audit_vi": "C fits target family.",
        "modifications": [
            {
                "action": "move",
                "affected_member_codes": ["c"],
                "source_ward_cluster_index": 1,
                "target_parent_code": "group_b",
                "rationale_vi": "C belongs to B.",
            }
        ],
        "groups": [
            _group("group_a", 1, ["a", "b"]),
            _group("group_b", 2, ["c", "d", "e"]),
        ],
        "unresolved_issues_vi": [],
    }


def test_move_without_merge_accepts_explicit_leaf_move() -> None:
    result = validate_move_without_merge(
        _response(),
        source_slug="day01-source",
        frozen_codes={"a", "b", "c", "d", "e"},
        candidate_cuts=[
            {"k": 2, "membership": [["a", "b", "c"], ["d", "e"]]}
        ],
    )

    assert result["move_lineage"][0]["leaf_code"] == "c"


def test_move_without_merge_rejects_merge_action() -> None:
    response = _response()
    response["modifications"][0]["action"] = "merge"

    with pytest.raises(ValueError, match="disallowed action"):
        validate_move_without_merge(
            response,
            source_slug="day01-source",
            frozen_codes={"a", "b", "c", "d", "e"},
            candidate_cuts=[
                {"k": 2, "membership": [["a", "b", "c"], ["d", "e"]]}
            ],
        )

