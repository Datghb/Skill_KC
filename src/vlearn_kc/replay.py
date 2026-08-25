from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .clustering import trackable_items, ward_candidates
from .contracts import load_material_bundle
from .extraction import validate_kc_response
from .io import read_json, sha256_json
from .refinement import validate_move_without_merge

def _ward_candidates_match(
    recorded: dict[str, Any], recomputed: dict[str, Any]
) -> bool:
    exact_fields = (
        "schema_version",
        "algorithm",
        "trackable_kc_count",
        "candidate_k_range",
    )
    if any(recorded.get(key) != recomputed.get(key) for key in exact_fields):
        return False
    recorded_cuts = recorded.get("candidate_cuts")
    recomputed_cuts = recomputed.get("candidate_cuts")
    if not isinstance(recorded_cuts, list) or not isinstance(recomputed_cuts, list):
        return False
    if len(recorded_cuts) != len(recomputed_cuts):
        return False
    for expected, actual in zip(recorded_cuts, recomputed_cuts):
        expected_without_score = {
            key: value for key, value in expected.items() if key != "silhouette_cosine"
        }
        actual_without_score = {
            key: value for key, value in actual.items() if key != "silhouette_cosine"
        }
        if expected_without_score != actual_without_score:
            return False
        if not np.isclose(
            float(expected["silhouette_cosine"]),
            float(actual["silhouette_cosine"]),
            rtol=1e-12,
            atol=1e-12,
        ):
            return False
    try:
        recorded_linkage = np.asarray(recorded.get("ward_linkage"), dtype=float)
        recomputed_linkage = np.asarray(recomputed.get("ward_linkage"), dtype=float)
    except (TypeError, ValueError):
        return False
    return recorded_linkage.shape == recomputed_linkage.shape and bool(
        np.allclose(
            recorded_linkage,
            recomputed_linkage,
            rtol=1e-12,
            atol=1e-12,
            equal_nan=False,
        )
    )


def replay_run(
    *, input_dir: Path | str, recorded_dir: Path | str
) -> dict[str, Any]:
    recorded_dir = Path(recorded_dir)
    bundle = load_material_bundle(input_dir)
    inventory_raw = read_json(recorded_dir / "kc-candidates.json")
    inventory = validate_kc_response(inventory_raw, bundle)
    items = trackable_items(list(inventory["knowledge_items"]))
    expected_codes = [str(item["code"]) for item in items]

    embedding_payload = read_json(recorded_dir / "embeddings.json")
    if embedding_payload.get("schema_version") != "vlearn_kc_embeddings_v1":
        raise ValueError("unsupported embedding schema")
    embedding_items = embedding_payload.get("items")
    if not isinstance(embedding_items, list):
        raise ValueError("embeddings.items must be a list")
    embedding_codes = [str(value.get("code") or "") for value in embedding_items]
    if embedding_codes != expected_codes:
        raise ValueError("embedding codes do not match trackable KC order")
    vectors = np.asarray([value.get("vector") for value in embedding_items], dtype=float)
    if vectors.ndim != 2 or not np.isfinite(vectors).all():
        raise ValueError("recorded embeddings are invalid")

    recorded_ward = read_json(recorded_dir / "ward-candidates.json")
    recomputed_ward = ward_candidates(
        items,
        vectors,
        max_k=int(recorded_ward["candidate_k_range"][1]),
    )
    if not _ward_candidates_match(recorded_ward, recomputed_ward):
        raise ValueError("recorded Ward candidates do not match embeddings")

    raw_topics = read_json(recorded_dir / "parent-topics.json")
    topics = validate_move_without_merge(
        raw_topics,
        source_slug=bundle.source_slug,
        frozen_codes=set(expected_codes),
        candidate_cuts=recorded_ward["candidate_cuts"],
    )
    manifest = read_json(recorded_dir / "run-manifest.json")
    if manifest.get("material_bundle_sha256") != bundle.bundle_sha256:
        raise ValueError("run manifest material hash mismatch")
    expected_hashes = manifest.get("artifact_sha256") or {}
    actual_hashes = {
        "kc_candidates": sha256_json(inventory),
        "embeddings": sha256_json(embedding_payload),
        "ward_candidates": sha256_json(recorded_ward),
        "parent_topics": sha256_json(topics),
    }
    if expected_hashes != actual_hashes:
        raise ValueError("run manifest artifact hash mismatch")
    return {
        "schema_version": "vlearn_kc_replay_result_v1",
        "source_slug": bundle.source_slug,
        "content_units": len(bundle.content_units),
        "knowledge_items": len(inventory["knowledge_items"]),
        "trackable_kcs": len(items),
        "parent_topics": topics["final_k"],
        "leaf_moves": len(topics["move_lineage"]),
        "verified": True,
    }
