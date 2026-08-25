from __future__ import annotations

from typing import Any, Mapping, Sequence


KNOWLEDGE_ROLE_ORDER = ("core_kc", "extension_kc", "reference_concept")


def summarize_knowledge_roles(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return compact, deterministic role statistics without mutating inventory."""
    groups: dict[str, dict[str, Any]] = {
        role: {"count": 0, "items": []} for role in KNOWLEDGE_ROLE_ORDER
    }
    for item in items:
        role = str(item.get("knowledge_role") or "")
        if role not in groups:
            raise ValueError(f"unsupported knowledge role: {role}")
        detail = {
            "code": str(item.get("code") or ""),
            "name_vi": str(item.get("name_vi") or ""),
            "description_vi": str(item.get("description_vi") or ""),
            "primary_capability_vi": str(item.get("primary_capability_vi") or ""),
            "item_form": str(item.get("item_form") or ""),
            "target_bloom_level": item.get("target_bloom_level"),
            "bloom_learning_objective_vi": str(
                item.get("bloom_learning_objective_vi") or ""
            ),
            "role_reason_vi": str(item.get("role_reason_vi") or ""),
            "evidence_section_ids": [
                str(value) for value in item.get("evidence_section_ids") or []
            ],
        }
        groups[role]["items"].append(detail)
        groups[role]["count"] += 1
    return groups
