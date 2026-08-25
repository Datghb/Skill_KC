from __future__ import annotations

from dataclasses import replace

import pytest

from vlearn_kc.contracts import ContentUnit, MaterialBundle
from vlearn_kc.extraction import validate_kc_response


def _bundle() -> MaterialBundle:
    unit = ContentUnit(
        content_unit_id="day01:p001:text:001",
        source_id="slide-v1",
        source_type="slide",
        content="Attention connects tokens.",
        content_sha256="a" * 64,
        page_no=1,
        start_seconds=None,
        end_seconds=None,
    )
    return MaterialBundle(
        lesson_id="phase1-day01",
        source_slug="day01-source",
        day=1,
        title="Day 1",
        sources=(),
        content_units=(unit,),
        bundle_sha256="b" * 64,
    )


def _response(evidence_ids: list[str]) -> dict:
    return {
        "source_slug": "day01-source",
        "knowledge_items": [
            {
                "code": "attention_contextual_weighting",
                "name_vi": "Attention theo ngữ cảnh",
                "description_vi": "Attention phân bổ trọng số theo liên quan ngữ cảnh.",
                "primary_capability_vi": "Giải thích vai trò của trọng số attention.",
                "item_form": "concept",
                "knowledge_role": "core_kc",
                "target_bloom_level": "understand",
                "evidence_section_ids": evidence_ids,
            }
        ],
    }


def test_validate_kc_response_resolves_only_bundle_evidence() -> None:
    result = validate_kc_response(
        _response(["day01:p001:text:001"]),
        _bundle(),
    )

    assert result["knowledge_items"][0]["resolved_evidence"][0]["page_no"] == 1


def test_validate_kc_response_rejects_unknown_evidence() -> None:
    with pytest.raises(ValueError, match="unknown evidence"):
        validate_kc_response(_response(["missing"]), _bundle())


def test_validate_kc_response_rejects_duplicate_code() -> None:
    response = _response(["day01:p001:text:001"])
    response["knowledge_items"].append(response["knowledge_items"][0].copy())

    with pytest.raises(ValueError, match="duplicate KC code"):
        validate_kc_response(response, _bundle())

