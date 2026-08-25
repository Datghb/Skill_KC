from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .clustering import embedding_text, trackable_items, ward_candidates
from .contracts import load_material_bundle
from .extraction import build_extraction_request, validate_kc_response
from .io import sha256_json, sha256_text, write_json
from .providers import Embedder, JsonGenerator
from .refinement import validate_move_without_merge
from .reporting import summarize_knowledge_roles


def build_refinement_request(
    inventory: dict[str, Any], ward: dict[str, Any]
) -> dict[str, Any]:
    items = trackable_items(list(inventory["knowledge_items"]))
    return {
        "task": "Select a Ward baseline, split and move individual leaves without parent merge.",
        "source_slug": inventory["source_slug"],
        "frozen_leaf_count": len(items),
        "frozen_leaf_codes": [str(item["code"]) for item in items],
        "frozen_leaves": [
            {
                "code": item["code"],
                "name_vi": item["name_vi"],
                "description_vi": item["description_vi"],
                "primary_capability_vi": item["primary_capability_vi"],
                "item_form": item["item_form"],
                "knowledge_role": item["knowledge_role"],
                "target_bloom_level": item.get("target_bloom_level"),
                "evidence": item["resolved_evidence"],
            }
            for item in items
        ],
        "ward_reference_partitions": [
            {
                key: value
                for key, value in cut.items()
                if key
                in {
                    "k",
                    "silhouette_cosine",
                    "singleton_count",
                    "min_cluster_size",
                    "median_cluster_size",
                    "max_cluster_size",
                    "membership",
                }
            }
            for cut in ward["candidate_cuts"]
        ],
    }


def _retry_telemetry(
    first: dict[str, Any],
    second: dict[str, Any],
    error: ValueError,
    *,
    stage: str,
) -> dict[str, Any]:
    usage_keys = {
        key
        for attempt in (first, second)
        for key in (attempt.get("usage") or {})
    }
    usage = {
        key: sum(
            int((attempt.get("usage") or {}).get(key) or 0)
            for attempt in (first, second)
        )
        for key in sorted(usage_keys)
    }
    return {
        **second,
        "stage": stage,
        "attempts": 2,
        "api_calls": int(first.get("api_calls") or 0)
        + int(second.get("api_calls") or 0),
        "latency_seconds": round(
            float(first.get("latency_seconds") or 0)
            + float(second.get("latency_seconds") or 0),
            3,
        ),
        "usage": usage,
        "repair_trigger": str(error),
        "attempt_telemetry": [first, second],
    }


class KCPipeline:
    def __init__(
        self,
        *,
        generator: JsonGenerator,
        embedder: Embedder,
        extraction_prompt: str,
        refinement_prompt: str,
        max_ward_k: int = 15,
    ) -> None:
        self.generator = generator
        self.embedder = embedder
        self.extraction_prompt = extraction_prompt
        self.refinement_prompt = refinement_prompt
        self.max_ward_k = max_ward_k

    def run(self, *, input_dir: Path | str, output_dir: Path | str) -> dict[str, Any]:
        output_dir = Path(output_dir)
        bundle = load_material_bundle(input_dir)
        extraction_request = build_extraction_request(bundle)
        raw_inventory, extraction_telemetry = self.generator.generate(
            prompt=self.extraction_prompt,
            request=extraction_request,
            stage="kc_extraction",
        )
        try:
            inventory = validate_kc_response(raw_inventory, bundle)
        except ValueError as error:
            repair_request = {
                **extraction_request,
                "validation_feedback": {
                    "error": str(error),
                    "instruction": "Correct the response using only exact content-unit evidence.",
                },
                "previous_response": raw_inventory,
            }
            repaired_inventory, repair_telemetry = self.generator.generate(
                prompt=self.extraction_prompt,
                request=repair_request,
                stage="kc_extraction_repair",
            )
            inventory = validate_kc_response(repaired_inventory, bundle)
            extraction_telemetry = _retry_telemetry(
                extraction_telemetry,
                repair_telemetry,
                error,
                stage="kc_extraction",
            )
        items = trackable_items(list(inventory["knowledge_items"]))
        knowledge_roles = summarize_knowledge_roles(inventory["knowledge_items"])
        if len(items) < 3:
            raise ValueError("at least three trackable KCs are required for clustering")
        texts = [embedding_text(item) for item in items]
        vectors, embedding_telemetry = self.embedder.embed(texts, kind="document")
        ward = ward_candidates(
            items,
            np.asarray(vectors, dtype=float),
            max_k=self.max_ward_k,
        )
        refinement_request = build_refinement_request(inventory, ward)
        raw_topics, refinement_telemetry = self.generator.generate(
            prompt=self.refinement_prompt,
            request=refinement_request,
            stage="parent_refinement",
        )
        try:
            topics = validate_move_without_merge(
                raw_topics,
                source_slug=bundle.source_slug,
                frozen_codes=set(refinement_request["frozen_leaf_codes"]),
                candidate_cuts=refinement_request["ward_reference_partitions"],
            )
        except ValueError as error:
            repair_request = {
                **refinement_request,
                "validation_feedback": {
                    "error": str(error),
                    "instruction": "Correct the response without changing frozen leaves or Ward constraints.",
                },
                "previous_response": raw_topics,
            }
            repaired_topics, repair_telemetry = self.generator.generate(
                prompt=self.refinement_prompt,
                request=repair_request,
                stage="parent_refinement_repair",
            )
            topics = validate_move_without_merge(
                repaired_topics,
                source_slug=bundle.source_slug,
                frozen_codes=set(refinement_request["frozen_leaf_codes"]),
                candidate_cuts=refinement_request["ward_reference_partitions"],
            )
            refinement_telemetry = _retry_telemetry(
                refinement_telemetry,
                repair_telemetry,
                error,
                stage="parent_refinement",
            )

        embeddings = {
            "schema_version": "vlearn_kc_embeddings_v1",
            "source_slug": bundle.source_slug,
            "items": [
                {
                    "code": item["code"],
                    "text_sha256": sha256_text(text),
                    "vector": [float(value) for value in vector],
                }
                for item, text, vector in zip(items, texts, vectors)
            ],
        }
        write_json(output_dir / "kc-candidates.json", inventory)
        write_json(output_dir / "embeddings.json", embeddings)
        write_json(output_dir / "ward-candidates.json", ward)
        write_json(output_dir / "parent-topics.json", topics)
        manifest = {
            "schema_version": "vlearn_kc_run_manifest_v1",
            "source_slug": bundle.source_slug,
            "material_bundle_sha256": bundle.bundle_sha256,
            "prompt_sha256": {
                "kc_extraction": sha256_text(self.extraction_prompt),
                "parent_refinement": sha256_text(self.refinement_prompt),
            },
            "artifact_sha256": {
                "kc_candidates": sha256_json(inventory),
                "embeddings": sha256_json(embeddings),
                "ward_candidates": sha256_json(ward),
                "parent_topics": sha256_json(topics),
            },
            "counts": {
                "content_units": len(bundle.content_units),
                "knowledge_items": len(inventory["knowledge_items"]),
                "trackable_kcs": len(items),
                "core_kcs": knowledge_roles["core_kc"]["count"],
                "extension_kcs": knowledge_roles["extension_kc"]["count"],
                "reference_concepts": knowledge_roles["reference_concept"]["count"],
                "parent_topics": topics["final_k"],
                "leaf_moves": len(topics["move_lineage"]),
            },
            "knowledge_roles": knowledge_roles,
            "telemetry": {
                "kc_extraction": extraction_telemetry,
                "embedding": embedding_telemetry,
                "parent_refinement": refinement_telemetry,
            },
            "release": {
                "auto_publish": False,
                "production_write": False,
            },
        }
        write_json(output_dir / "run-manifest.json", manifest)
        return {
            "inventory": inventory,
            "ward": ward,
            "parent_topics": topics,
            "manifest": manifest,
        }
