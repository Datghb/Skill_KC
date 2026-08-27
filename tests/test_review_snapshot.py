from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from vlearn_kc.cli import main
from vlearn_kc.review_snapshot import build_review_snapshot, write_review_snapshot


def _item(code: str, name: str | None = None) -> dict[str, object]:
    return {
        "code": code,
        "name_vi": name or code.replace("_", " ").title(),
        "description_vi": f"Mô tả {code}",
        "primary_capability_vi": f"Năng lực {code}",
        "item_form": "concept",
        "knowledge_role": "core_kc",
        "target_bloom_level": "understand",
        "evidence_section_ids": ["slide:p001"],
        "resolved_evidence": [{"content_unit_id": "slide:p001"}],
    }


def _review(code: str, decision: str, **overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "reviewer_key": "reviewer-02",
        "lesson_day": 4,
        "lesson_slug": "day04-example",
        "kc_code": code,
        "kc_name_vi": code,
        "decision": decision,
        "scores": {"accuracy": 4, "granularity": 4, "naming_clarity": 4},
        "suggested_actions": [],
        "criterion_notes": {},
        "review_note": None,
    }
    return {**review, **overrides}


def _inputs() -> tuple[dict, dict, dict, dict, dict]:
    codes = (
        "accepted",
        "renamed",
        "removed",
        "missing_reason",
        "lab_kc",
        "lab_task",
        "conflicted",
    )
    inventories = {
        "day04-example": {
            "schema_version": "mixed_source_knowledge_inventory_v1",
            "source_slug": "day04-example",
            "knowledge_items": [_item(code) for code in codes],
        }
    }
    reviews = {
        "schema_version": "analysis_ready_teacher_reviews_v1",
        "source_dataset_id": "dataset-v1",
        "reviews": [
            _review("accepted", "pass"),
            _review(
                "renamed",
                "revise",
                review_note="Tên cần rõ hơn",
                suggested_actions=[
                    {
                        "action": "rename_component",
                        "new_name_vi": "Tên KC đã sửa",
                        "reason_tag": "naming",
                    }
                ],
            ),
            _review(
                "removed",
                "reject",
                review_note="Không phải KC",
                suggested_actions=[
                    {"action": "remove_component", "reason_tag": "scope"}
                ],
            ),
            _review("missing_reason", "reject"),
            _review("lab_kc", "reject", review_note="Nằm trong lab"),
            _review("lab_task", "reject", review_note="Nằm trong lab"),
        ],
    }
    normalized = {
        "completed_reviews": reviews["reviews"]
        + [_review("conflicted", "pass", reviewer_key="reviewer-01")],
        "completed_group_reviews": [
            {
                "lesson_day": 4,
                "lesson_slug": "day04-example",
                "group_code": "example_group",
                "group_name_vi": "Nhóm ví dụ",
                "member_kc_codes": list(codes),
                "decision": "pass",
                "scores": {},
                "suggested_actions": [],
                "review_note": None,
            }
        ],
    }
    disagreements = {
        "items": [
            {
                "kc_key": "4:conflicted",
                "reviewer-01": {"decision": "pass"},
                "reviewer-02": {"decision": "reject"},
            }
        ]
    }
    error_analysis = {
        "cases": {
            "missing_rationale": ["missing_reason"],
            "kc_assessment_boundary": ["lab_kc", "lab_task"],
        },
        "lab_resolution": {
            "policy": "Lab là nguồn assessment.",
            "lab_kc": "retain_as_underlying_kc",
            "lab_task": "reclassify_as_assessment_task",
        },
    }
    return reviews, normalized, disagreements, error_analysis, inventories


def test_build_snapshot_classifies_conservatively_and_does_not_mutate() -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()
    original = copy.deepcopy(inventories)

    snapshot = build_review_snapshot(
        reviews=reviews,
        normalized_reviews=normalized,
        disagreements=disagreements,
        error_analysis=error_analysis,
        inventories=inventories,
    )

    assert snapshot["manifest"]["counts"] == {
        "reviewed": 7,
        "accepted": 1,
        "revised": 2,
        "rejected": 2,
        "quarantined": 2,
        "pilot_ready": 3,
    }
    assert [entry["kc_code"] for entry in snapshot["accepted"]] == ["accepted"]
    assert {entry["kc_code"] for entry in snapshot["revised"]} == {
        "renamed",
        "lab_kc",
    }
    renamed = next(
        entry for entry in snapshot["revised"] if entry["kc_code"] == "renamed"
    )
    assert renamed["kc"]["name_vi"] == "Tên KC đã sửa"
    assert {entry["kc_code"] for entry in snapshot["rejected"]} == {
        "removed",
        "lab_task",
    }
    assert {entry["kc_code"] for entry in snapshot["quarantined"]} == {
        "missing_reason",
        "conflicted",
    }
    assert inventories == original


def test_snapshot_filters_parent_members_to_pilot_ready_kcs() -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()

    snapshot = build_review_snapshot(
        reviews=reviews,
        normalized_reviews=normalized,
        disagreements=disagreements,
        error_analysis=error_analysis,
        inventories=inventories,
    )

    group = snapshot["parent_topics"]["groups"][0]
    assert group["pilot_member_kc_codes"] == ["accepted", "renamed", "lab_kc"]
    assert group["excluded_member_kc_codes"] == [
        "removed",
        "missing_reason",
        "lab_task",
        "conflicted",
    ]


def test_snapshot_applies_structured_content_edit_and_group_move() -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()
    inventories["day04-example"]["knowledge_items"].append(_item("edited_and_moved"))
    review = _review(
        "edited_and_moved",
        "revise",
        review_note="Cần sửa nội dung và chuyển nhóm",
        suggested_actions=[
            {
                "action": "edit_content",
                "new_description_vi": "Nội dung đã được giảng viên yêu cầu sửa",
                "reason_tag": "content",
            },
            {
                "action": "move_component",
                "target_group_code": "better_group",
                "reason_tag": "placement",
            },
        ],
    )
    reviews["reviews"].append(review)
    normalized["completed_reviews"].append(review)

    snapshot = build_review_snapshot(
        reviews=reviews,
        normalized_reviews=normalized,
        disagreements=disagreements,
        error_analysis=error_analysis,
        inventories=inventories,
    )

    entry = next(
        item for item in snapshot["revised"] if item["kc_code"] == "edited_and_moved"
    )
    assert entry["kc"]["description_vi"] == "Nội dung đã được giảng viên yêu cầu sửa"
    assert entry["applied_actions"][1]["target_group_code"] == "better_group"


def test_snapshot_rejects_review_without_matching_inventory_item() -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()
    reviews["reviews"].append(_review("not_in_inventory", "pass"))

    with pytest.raises(ValueError, match="not_in_inventory"):
        build_review_snapshot(
            reviews=reviews,
            normalized_reviews=normalized,
            disagreements=disagreements,
            error_analysis=error_analysis,
            inventories=inventories,
        )


def test_write_snapshot_creates_auditable_files(tmp_path: Path) -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()
    snapshot = build_review_snapshot(
        reviews=reviews,
        normalized_reviews=normalized,
        disagreements=disagreements,
        error_analysis=error_analysis,
        inventories=inventories,
    )

    write_review_snapshot(tmp_path, snapshot)

    expected = {
        "accepted-kcs.json",
        "revised-kcs.json",
        "rejected-kcs.json",
        "quarantined-kcs.json",
        "reviewed-kc-inventory.json",
        "reviewed-parent-topics.json",
        "applied-actions.json",
        "manifest.json",
        "REPORT_VI.md",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["pilot_ready"] == 3
    report = (tmp_path / "REPORT_VI.md").read_text(encoding="utf-8")
    assert "3 KC sẵn sàng pilot" in report


def test_review_snapshot_cli_builds_snapshot_from_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reviews, normalized, disagreements, error_analysis, inventories = _inputs()
    input_paths: dict[str, Path] = {}
    for name, payload in {
        "reviews": reviews,
        "normalized": normalized,
        "disagreements": disagreements,
        "error_analysis": error_analysis,
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        input_paths[name] = path
    inventory_dir = tmp_path / "inventories" / "day04"
    inventory_dir.mkdir(parents=True)
    inventory_dir.joinpath("kc_candidates.json").write_text(
        json.dumps(inventories["day04-example"]), encoding="utf-8"
    )
    output = tmp_path / "snapshot"

    exit_code = main(
        [
            "review-snapshot",
            str(tmp_path / "inventories"),
            str(input_paths["reviews"]),
            str(input_paths["normalized"]),
            str(input_paths["disagreements"]),
            str(input_paths["error_analysis"]),
            str(output),
        ]
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["counts"]["pilot_ready"] == 3
    assert (output / "reviewed-kc-inventory.json").is_file()
