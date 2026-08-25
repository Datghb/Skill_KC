from __future__ import annotations

import numpy as np

from vlearn_kc.clustering import embedding_text, ward_candidates


def _item(code: str, page: int) -> dict:
    return {
        "code": code,
        "name_vi": code,
        "description_vi": f"Description {code}",
        "primary_capability_vi": f"Capability {code}",
        "knowledge_role": "core_kc",
        "target_bloom_level": "understand",
        "resolved_evidence": [
            {
                "content_unit_id": f"unit-{code}",
                "page_no": page,
                "content": f"Evidence {code}",
            }
        ],
    }


def test_embedding_text_contains_semantic_fields_and_evidence() -> None:
    value = embedding_text(_item("attention", 3))

    assert "Description attention" in value
    assert "Capability attention" in value
    assert "Evidence attention" in value


def test_ward_candidates_are_deterministic_and_cover_every_leaf() -> None:
    items = [_item("a", 1), _item("b", 2), _item("c", 3), _item("d", 4)]
    vectors = np.asarray(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.1, 0.9],
        ]
    )

    result = ward_candidates(items, vectors, max_k=3)

    assert result["candidate_k_range"] == [2, 3]
    for cut in result["candidate_cuts"]:
        assert sorted(code for group in cut["membership"] for code in group) == [
            "a",
            "b",
            "c",
            "d",
        ]

