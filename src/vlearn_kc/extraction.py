from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .contracts import MaterialBundle


ITEM_FORMS = {"concept", "principle", "criterion", "procedure", "reference_topic"}
KNOWLEDGE_ROLES = {"core_kc", "extension_kc", "reference_concept"}
BLOOM_LEVELS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
GENERATOR_CONFIDENCE_FIELDS = {
    "confidence",
    "extraction_confidence",
    "boundary_confidence",
    "role_confidence",
    "bloom_confidence",
    "llm_proposal_confidence",
}


def build_extraction_request(bundle: MaterialBundle) -> dict[str, Any]:
    return {
        "source_slug": bundle.source_slug,
        "lesson": {
            "lesson_id": bundle.lesson_id,
            "day": bundle.day,
            "title": bundle.title,
        },
        "content_units": [unit.as_dict() for unit in bundle.content_units],
    }


def _required_text(value: Mapping[str, Any], field: str, context: str) -> str:
    result = str(value.get(field) or "").strip()
    if not result:
        raise ValueError(f"{context}: {field} is required")
    return result


def validate_kc_response(
    response: Mapping[str, Any], bundle: MaterialBundle
) -> dict[str, Any]:
    if response.get("source_slug") != bundle.source_slug:
        raise ValueError("KC source_slug mismatch")
    items = response.get("knowledge_items")
    if not isinstance(items, list) or not items:
        raise ValueError("KC response has no knowledge_items")
    unit_index = {unit.content_unit_id: unit for unit in bundle.content_units}
    seen_codes: set[str] = set()
    normalized = []
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError(f"knowledge_items[{index}] must be an object")
        item = {
            key: deepcopy(value)
            for key, value in raw.items()
            if key not in GENERATOR_CONFIDENCE_FIELDS
        }
        code = _required_text(item, "code", f"knowledge_items[{index}]")
        if code in seen_codes:
            raise ValueError(f"duplicate KC code: {code}")
        seen_codes.add(code)
        for field in ("name_vi", "description_vi", "primary_capability_vi"):
            item[field] = _required_text(item, field, code)
        if item.get("item_form") not in ITEM_FORMS:
            raise ValueError(f"{code}: invalid item_form")
        role = str(item.get("knowledge_role") or "")
        if role not in KNOWLEDGE_ROLES:
            raise ValueError(f"{code}: invalid knowledge_role")
        bloom = item.get("target_bloom_level")
        if role == "reference_concept":
            if bloom is not None:
                raise ValueError(f"{code}: reference_concept must have null Bloom")
        elif bloom not in BLOOM_LEVELS:
            raise ValueError(f"{code}: invalid target_bloom_level")
        evidence_ids = [str(value) for value in item.get("evidence_section_ids") or []]
        if not evidence_ids:
            raise ValueError(f"{code}: evidence_section_ids is required")
        unknown = sorted(set(evidence_ids) - set(unit_index))
        if unknown:
            raise ValueError(f"{code}: unknown evidence {unknown}")
        item["evidence_section_ids"] = evidence_ids
        item["resolved_evidence"] = [unit_index[value].as_dict() for value in evidence_ids]
        normalized.append(item)
    return {
        "schema_version": "vlearn_kc_inventory_v1",
        "source_slug": bundle.source_slug,
        "material_bundle_sha256": bundle.bundle_sha256,
        "knowledge_items": normalized,
    }

