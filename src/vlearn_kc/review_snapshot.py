from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .io import read_json, sha256_json, write_json


SNAPSHOT_FILES = {
    "accepted": "accepted-kcs.json",
    "revised": "revised-kcs.json",
    "rejected": "rejected-kcs.json",
    "quarantined": "quarantined-kcs.json",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _review_key(day: object, code: object) -> str:
    return f"{int(day)}:{_text(code)}"


def _list_of_mappings(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return [item for item in value if isinstance(item, Mapping)]


def _inventory_index(
    inventories: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for fallback_slug, inventory in inventories.items():
        slug = _text(inventory.get("source_slug")) or fallback_slug
        for item in _list_of_mappings(inventory, "knowledge_items"):
            code = _text(item.get("code"))
            if not code:
                raise ValueError(f"inventory {slug} contains a KC without a code")
            key = (slug, code)
            if key in result:
                raise ValueError(f"duplicate inventory KC: {slug}:{code}")
            result[key] = item
    return result


def _find_item(
    index: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    lesson_slug: str,
    kc_code: str,
) -> Mapping[str, Any]:
    item = index.get((lesson_slug, kc_code))
    if item is None:
        raise ValueError(f"reviewed KC is missing from inventories: {lesson_slug}:{kc_code}")
    return item


def _case_categories(error_analysis: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    cases = error_analysis.get("cases", {})
    if not isinstance(cases, Mapping):
        return result
    for category, codes in cases.items():
        if isinstance(codes, list):
            for code in codes:
                result[_text(code)] = _text(category)
    return result


def _structured_actions(review: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    actions = review.get("suggested_actions", [])
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, Mapping)]


def _apply_revision(
    item: Mapping[str, Any], review: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    actions = _structured_actions(review)
    if not actions:
        return None
    revised = deepcopy(dict(item))
    applied: list[dict[str, Any]] = []
    for action in actions:
        action_name = _text(action.get("action"))
        reason = _text(action.get("reason_tag")) or _text(action.get("note_vi"))
        if not reason:
            return None
        if action_name == "rename_component":
            new_name = _text(action.get("new_name_vi"))
            if not new_name:
                return None
            before = revised.get("name_vi")
            revised = {**revised, "name_vi": new_name}
            applied.append(
                {
                    "action": action_name,
                    "field": "name_vi",
                    "before": before,
                    "after": new_name,
                    "reason": reason,
                }
            )
        elif action_name == "edit_content":
            new_description = _text(action.get("new_description_vi"))
            if not new_description:
                return None
            before = revised.get("description_vi")
            revised = {**revised, "description_vi": new_description}
            applied.append(
                {
                    "action": action_name,
                    "field": "description_vi",
                    "before": before,
                    "after": new_description,
                    "reason": reason,
                }
            )
        elif action_name == "move_component":
            target = _text(action.get("target_group_code"))
            if not target:
                return None
            applied.append(
                {
                    "action": action_name,
                    "target_group_code": target,
                    "reason": reason,
                }
            )
        else:
            return None
    return revised, applied


def _has_actionable_removal(review: Mapping[str, Any]) -> bool:
    return any(
        _text(action.get("action")) == "remove_component"
        and bool(_text(action.get("reason_tag")) or _text(action.get("note_vi")))
        for action in _structured_actions(review)
    )


def _entry(
    *,
    review: Mapping[str, Any],
    item: Mapping[str, Any],
    status: str,
    reason: str,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "review_key": _review_key(review.get("lesson_day"), review.get("kc_code")),
        "lesson_day": int(review["lesson_day"]),
        "lesson_slug": _text(review.get("lesson_slug")),
        "kc_code": _text(review.get("kc_code")),
        "status": status,
        "reason": reason,
        "applied_actions": actions or [],
        "review": deepcopy(dict(review)),
        "kc": deepcopy(dict(item)),
    }


def build_review_snapshot(
    *,
    reviews: Mapping[str, Any],
    normalized_reviews: Mapping[str, Any],
    disagreements: Mapping[str, Any],
    error_analysis: Mapping[str, Any],
    inventories: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    index = _inventory_index(inventories)
    categories = _case_categories(error_analysis)
    lab_resolution = error_analysis.get("lab_resolution", {})
    if not isinstance(lab_resolution, Mapping):
        lab_resolution = {}

    buckets: dict[str, list[dict[str, Any]]] = {
        name: [] for name in SNAPSHOT_FILES
    }
    seen_keys: set[str] = set()

    for review in _list_of_mappings(reviews, "reviews"):
        slug = _text(review.get("lesson_slug"))
        code = _text(review.get("kc_code"))
        key = _review_key(review.get("lesson_day"), code)
        if key in seen_keys:
            raise ValueError(f"duplicate analysis-ready review: {key}")
        seen_keys.add(key)
        item = _find_item(index, lesson_slug=slug, kc_code=code)
        decision = _text(review.get("decision")).lower()
        resolution = _text(lab_resolution.get(code))

        if decision == "pass":
            buckets["accepted"].append(
                _entry(
                    review=review,
                    item=item,
                    status="accepted",
                    reason="teacher_pass",
                )
            )
        elif resolution == "retain_as_underlying_kc":
            buckets["revised"].append(
                _entry(
                    review=review,
                    item=item,
                    status="revised",
                    reason="retained_as_underlying_kc_after_lab_boundary_review",
                    actions=[
                        {
                            "action": "retain_as_underlying_kc",
                            "reason": _text(lab_resolution.get("policy")),
                        }
                    ],
                )
            )
        elif resolution == "reclassify_as_assessment_task":
            buckets["rejected"].append(
                _entry(
                    review=review,
                    item=item,
                    status="rejected",
                    reason="reclassified_as_assessment_task",
                    actions=[
                        {
                            "action": "reclassify_as_assessment_task",
                            "reason": _text(lab_resolution.get("policy")),
                        }
                    ],
                )
            )
        elif decision == "revise":
            result = _apply_revision(item, review)
            if result is None:
                buckets["quarantined"].append(
                    _entry(
                        review=review,
                        item=item,
                        status="quarantined",
                        reason=f"revision_not_actionable:{categories.get(code, 'unknown')}",
                    )
                )
            else:
                revised, actions = result
                buckets["revised"].append(
                    _entry(
                        review=review,
                        item=revised,
                        status="revised",
                        reason="structured_revision_applied",
                        actions=actions,
                    )
                )
        elif decision == "reject" and _has_actionable_removal(review):
            buckets["rejected"].append(
                _entry(
                    review=review,
                    item=item,
                    status="rejected",
                    reason="actionable_teacher_rejection",
                    actions=[deepcopy(dict(action)) for action in _structured_actions(review)],
                )
            )
        else:
            buckets["quarantined"].append(
                _entry(
                    review=review,
                    item=item,
                    status="quarantined",
                    reason=f"non_pass_not_actionable:{categories.get(code, 'unknown')}",
                )
            )

    normalized_by_key = {
        _review_key(review.get("lesson_day"), review.get("kc_code")): review
        for review in _list_of_mappings(normalized_reviews, "completed_reviews")
        if _text(review.get("kc_code"))
    }
    for disagreement in _list_of_mappings(disagreements, "items"):
        key = _text(disagreement.get("kc_key"))
        review = normalized_by_key.get(key)
        if review is None:
            raise ValueError(f"disagreement is missing its normalized review: {key}")
        slug = _text(review.get("lesson_slug"))
        code = _text(review.get("kc_code"))
        item = _find_item(index, lesson_slug=slug, kc_code=code)
        buckets["quarantined"].append(
            _entry(
                review={**dict(review), "disagreement": deepcopy(dict(disagreement))},
                item=item,
                status="quarantined",
                reason="reviewer_conflict_needs_adjudication",
            )
        )

    for entries in buckets.values():
        entries.sort(key=lambda entry: (entry["lesson_day"], entry["kc_code"]))

    pilot_entries = buckets["accepted"] + buckets["revised"]
    pilot_codes_by_slug: dict[str, set[str]] = {}
    for entry in pilot_entries:
        pilot_codes_by_slug.setdefault(entry["lesson_slug"], set()).add(entry["kc_code"])

    groups: list[dict[str, Any]] = []
    for group in _list_of_mappings(normalized_reviews, "completed_group_reviews"):
        slug = _text(group.get("lesson_slug"))
        members = [_text(code) for code in group.get("member_kc_codes", [])]
        pilot_codes = pilot_codes_by_slug.get(slug, set())
        groups.append(
            {
                **deepcopy(dict(group)),
                "pilot_member_kc_codes": [code for code in members if code in pilot_codes],
                "excluded_member_kc_codes": [code for code in members if code not in pilot_codes],
            }
        )

    counts = {name: len(entries) for name, entries in buckets.items()}
    counts = {
        "reviewed": sum(counts.values()),
        **counts,
        "pilot_ready": len(pilot_entries),
    }
    dataset_id = _text(reviews.get("source_dataset_id"))
    manifest = {
        "schema_version": "reviewed_kc_snapshot_manifest_v1",
        "source_dataset_id": dataset_id,
        "policy": {
            "preserve_source_artifacts": True,
            "exclude_conflicts": True,
            "exclude_inactionable_non_pass_reviews": True,
            "pilot_statuses": ["accepted", "revised"],
        },
        "counts": counts,
        "input_hashes": {
            "analysis_ready_reviews": sha256_json(reviews),
            "normalized_reviews": sha256_json(normalized_reviews),
            "disagreements": sha256_json(disagreements),
            "error_analysis": sha256_json(error_analysis),
            "inventories": sha256_json(inventories),
        },
    }
    reviewed_items = [
        {
            **entry["kc"],
            "lesson_day": entry["lesson_day"],
            "lesson_slug": entry["lesson_slug"],
            "review_status": entry["status"],
            "review_reason": entry["reason"],
        }
        for entry in sorted(
            pilot_entries, key=lambda entry: (entry["lesson_day"], entry["kc_code"])
        )
    ]
    actions = [
        {
            "review_key": entry["review_key"],
            "kc_code": entry["kc_code"],
            "status": entry["status"],
            "reason": entry["reason"],
            "actions": entry["applied_actions"],
        }
        for bucket in ("revised", "rejected")
        for entry in buckets[bucket]
    ]
    return {
        **buckets,
        "inventory": {
            "schema_version": "reviewed_kc_inventory_v1",
            "source_dataset_id": dataset_id,
            "status": "pilot_draft",
            "knowledge_items": reviewed_items,
        },
        "parent_topics": {
            "schema_version": "reviewed_parent_topics_v1",
            "source_dataset_id": dataset_id,
            "status": "review_audit_only",
            "groups": groups,
        },
        "actions": actions,
        "manifest": manifest,
    }


def load_review_inventories(root: Path) -> dict[str, Mapping[str, Any]]:
    inventories: dict[str, Mapping[str, Any]] = {}
    for path in sorted(root.glob("day*/kc_candidates.json")):
        payload = read_json(path)
        slug = _text(payload.get("source_slug"))
        if not slug:
            raise ValueError(f"inventory has no source_slug: {path}")
        inventories[slug] = payload
    if not inventories:
        raise ValueError(f"no day*/kc_candidates.json inventories found under {root}")
    return inventories


def _report(snapshot: Mapping[str, Any]) -> str:
    counts = snapshot["manifest"]["counts"]
    return f"""# Báo cáo Reviewed KC Snapshot v1

## Kết quả

- {counts['pilot_ready']} KC sẵn sàng pilot.
- {counts['accepted']} KC được giảng viên chấp nhận.
- {counts['revised']} KC đã áp dụng phương án xử lý rõ ràng.
- {counts['rejected']} KC không đưa vào pilot.
- {counts['quarantined']} KC được cách ly để chờ làm rõ.

## Cách sử dụng

Chỉ dùng `reviewed-kc-inventory.json` cho pilot có giám sát. Không dùng các KC
trong `quarantined-kcs.json` cho LMS hoặc để chỉnh prompt. Dữ liệu review và KC
nguồn không bị sửa đổi.

`reviewed-parent-topics.json` là báo cáo thành viên group sau lọc, chưa phải cấu
trúc parent topic đã được giảng viên duyệt lại hoàn chỉnh.
"""


def write_review_snapshot(output: Path, snapshot: Mapping[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for key, filename in SNAPSHOT_FILES.items():
        write_json(
            output / filename,
            {
                "schema_version": f"reviewed_kc_{key}_v1",
                "items": snapshot[key],
            },
        )
    write_json(output / "reviewed-kc-inventory.json", snapshot["inventory"])
    write_json(output / "reviewed-parent-topics.json", snapshot["parent_topics"])
    write_json(
        output / "applied-actions.json",
        {"schema_version": "reviewed_kc_actions_v1", "actions": snapshot["actions"]},
    )
    write_json(output / "manifest.json", snapshot["manifest"])
    (output / "REPORT_VI.md").write_text(_report(snapshot), encoding="utf-8")
