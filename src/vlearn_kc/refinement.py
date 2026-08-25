from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Any, Mapping


PARENT_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
COHERENCE = {"high", "medium", "low"}
ALLOWED_ACTIONS = {"keep", "split", "move", "rename"}


def _required_text(value: Mapping[str, Any], field: str, context: str) -> str:
    result = str(value.get(field) or "").strip()
    if not result:
        raise ValueError(f"{context}: {field} is required")
    return result


def validate_move_without_merge(
    response: Mapping[str, Any],
    *,
    source_slug: str,
    frozen_codes: set[str],
    candidate_cuts: list[dict[str, Any]],
) -> dict[str, Any]:
    if response.get("source_slug") != source_slug:
        raise ValueError("source_slug mismatch")
    candidate_by_k = {int(cut["k"]): cut for cut in candidate_cuts}
    ward_k = response.get("ward_reference_k")
    if isinstance(ward_k, bool) or not isinstance(ward_k, int) or ward_k not in candidate_by_k:
        raise ValueError("invalid ward_reference_k")
    groups = response.get("groups")
    final_k = response.get("final_k")
    if not isinstance(groups, list) or not groups or final_k != len(groups):
        raise ValueError("final_k must equal non-empty group count")
    if final_k < ward_k:
        raise ValueError("final_k cannot be smaller than Ward baseline")

    parent_codes: set[str] = set()
    member_counts: Counter[str] = Counter()
    normalized_groups = []
    unjustified_singletons: list[str] = []
    for index, raw in enumerate(groups, start=1):
        group = deepcopy(dict(raw))
        code = _required_text(group, "parent_code", f"group {index}")
        if not PARENT_CODE_RE.fullmatch(code) or code in parent_codes:
            raise ValueError(f"invalid or duplicate parent_code: {code}")
        parent_codes.add(code)
        for field in (
            "name_vi",
            "name_en",
            "description_vi",
            "boundary_notes_vi",
            "pg_readiness_reason_vi",
        ):
            group[field] = _required_text(group, field, code)
        if group.get("coherence") not in COHERENCE:
            raise ValueError(f"{code}: invalid coherence")
        members = [str(value) for value in group.get("member_codes") or []]
        if not members:
            raise ValueError(f"{code}: empty member_codes")
        if len(members) == 1 and not str(group.get("singleton_justification_vi") or "").strip():
            unjustified_singletons.append(code)
        for member in members:
            member_counts[member] += 1
        group["member_codes"] = members
        normalized_groups.append(group)
    unknown = sorted(set(member_counts) - frozen_codes)
    duplicates = sorted(code for code, count in member_counts.items() if count > 1)
    missing = sorted(frozen_codes - set(member_counts))
    if unknown:
        raise ValueError(f"unknown leaf codes: {unknown}")
    if duplicates:
        raise ValueError(f"duplicate leaf codes: {duplicates}")
    if missing:
        raise ValueError(f"missing leaf codes: {missing}")
    if unjustified_singletons:
        raise ValueError(
            f"singleton justification is required: {unjustified_singletons}"
        )

    modifications = response.get("modifications")
    if not isinstance(modifications, list):
        raise ValueError("modifications must be a list")
    normalized_modifications = []
    for index, raw in enumerate(modifications, start=1):
        action = str(raw.get("action") or "")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"disallowed action: {action}")
        affected = [str(value) for value in raw.get("affected_member_codes") or []]
        if not affected or set(affected) - frozen_codes:
            raise ValueError(f"modification {index}: invalid affected members")
        item = {
            "action": action,
            "affected_member_codes": affected,
            "rationale_vi": _required_text(raw, "rationale_vi", f"modification {index}"),
        }
        if raw.get("source_ward_cluster_index") is not None:
            item["source_ward_cluster_index"] = raw["source_ward_cluster_index"]
        if raw.get("target_parent_code") is not None:
            item["target_parent_code"] = str(raw["target_parent_code"])
        normalized_modifications.append(item)

    selected = candidate_by_k[ward_k]
    raw_homes = {group.get("ward_home_cluster_index") for group in normalized_groups}
    normalization = "none"
    if raw_homes == set(range(len(selected["membership"]))):
        normalization = "zero_based_to_one_based"
        for group in normalized_groups:
            group["ward_home_cluster_index"] = int(group["ward_home_cluster_index"]) + 1
        for item in normalized_modifications:
            if item.get("source_ward_cluster_index") is not None:
                item["source_ward_cluster_index"] = int(item["source_ward_cluster_index"]) + 1

    baseline_by_leaf = {
        str(code): index
        for index, members in enumerate(selected["membership"], start=1)
        for code in members
    }
    expected_homes = set(range(1, len(selected["membership"]) + 1))
    seen_homes: set[int] = set()
    actual_moves = []
    for group in normalized_groups:
        home = group.get("ward_home_cluster_index")
        if isinstance(home, bool) or not isinstance(home, int) or home not in expected_homes:
            raise ValueError(f"{group['parent_code']}: invalid Ward home")
        if not any(baseline_by_leaf[code] == home for code in group["member_codes"]):
            raise ValueError(f"{group['parent_code']}: no member from Ward home")
        seen_homes.add(home)
        for code in group["member_codes"]:
            source = baseline_by_leaf[code]
            if source != home:
                actual_moves.append(
                    {
                        "leaf_code": code,
                        "source_ward_cluster_index": source,
                        "target_parent_code": group["parent_code"],
                    }
                )
    if seen_homes != expected_homes:
        raise ValueError(f"Ward baseline clusters disappeared: {sorted(expected_homes - seen_homes)}")

    declared_moves = []
    for item in normalized_modifications:
        if item["action"] != "move":
            continue
        source = item.get("source_ward_cluster_index")
        target = str(item.get("target_parent_code") or "")
        if isinstance(source, bool) or not isinstance(source, int) or not target:
            raise ValueError("move requires source Ward index and target parent")
        for code in item["affected_member_codes"]:
            declared_moves.append(
                {
                    "leaf_code": code,
                    "source_ward_cluster_index": source,
                    "target_parent_code": target,
                }
            )
    key = lambda value: (
        value["leaf_code"],
        value["source_ward_cluster_index"],
        value["target_parent_code"],
    )
    if sorted(actual_moves, key=key) != sorted(declared_moves, key=key):
        raise ValueError("move declarations do not match membership")

    return {
        "schema_version": "vlearn_parent_topics_v1",
        "source_slug": source_slug,
        "ward_reference_k": ward_k,
        "final_k": final_k,
        "ward_reference_reason_vi": _required_text(response, "ward_reference_reason_vi", "response"),
        "cluster_count_reason_vi": _required_text(response, "cluster_count_reason_vi", "response"),
        "overall_change_summary_vi": _required_text(response, "overall_change_summary_vi", "response"),
        "post_selection_audit_vi": _required_text(response, "post_selection_audit_vi", "response"),
        "groups": normalized_groups,
        "modifications": normalized_modifications,
        "move_lineage": sorted(actual_moves, key=key),
        "home_index_normalization": normalization,
        "unresolved_issues_vi": [str(value) for value in response.get("unresolved_issues_vi") or []],
    }
