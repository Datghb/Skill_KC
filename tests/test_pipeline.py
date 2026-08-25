from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from vlearn_kc.io import sha256_json
from vlearn_kc.pipeline import KCPipeline
from vlearn_kc.replay import replay_run


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _material_bundle(root: Path) -> Path:
    root.mkdir()
    content = "A compact lesson about four reusable concepts."
    _write_json(
        root / "lesson.json",
        {
            "schema_version": "vlearn_lesson_v1",
            "lesson_id": "phase1-day01",
            "source_slug": "day01-source",
            "day": 1,
            "title": "Day 1",
        },
    )
    _write_json(
        root / "sources.json",
        {
            "schema_version": "vlearn_sources_v1",
            "source_slug": "day01-source",
            "sources": [
                {
                    "source_id": "slide-v1",
                    "source_type": "slide",
                    "sha256": "a" * 64,
                }
            ],
        },
    )
    _write_json(
        root / "content_units.json",
        {
            "schema_version": "vlearn_content_units_v1",
            "source_slug": "day01-source",
            "content_units": [
                {
                    "content_unit_id": "unit-1",
                    "source_id": "slide-v1",
                    "source_type": "slide",
                    "page_no": 1,
                    "start_seconds": None,
                    "end_seconds": None,
                    "content": content,
                    "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                }
            ],
        },
    )
    return root


def _kc(code: str) -> dict:
    return {
        "code": code,
        "name_vi": f"KC {code}",
        "description_vi": f"Description {code}",
        "primary_capability_vi": f"Capability {code}",
        "item_form": "concept",
        "knowledge_role": "core_kc",
        "target_bloom_level": "understand",
        "evidence_section_ids": ["unit-1"],
    }


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, *, prompt: str, request: dict, stage: str):
        self.calls.append({"prompt": prompt, "request": request, "stage": stage})
        if stage == "kc_extraction":
            return (
                {
                    "source_slug": "day01-source",
                    "knowledge_items": [_kc("a"), _kc("b"), _kc("c"), _kc("d")],
                },
                {"provider": "fake", "api_calls": 1},
            )
        assert stage == "parent_refinement"
        return (
            {
                "source_slug": "day01-source",
                "ward_reference_k": 2,
                "ward_reference_reason_vi": "Two coherent baseline families.",
                "final_k": 2,
                "cluster_count_reason_vi": "Two coherent final families.",
                "overall_change_summary_vi": "Keep both families.",
                "post_selection_audit_vi": "No move required.",
                "modifications": [
                    {
                        "action": "keep",
                        "affected_member_codes": ["a", "b"],
                        "rationale_vi": "First family is coherent.",
                    },
                    {
                        "action": "keep",
                        "affected_member_codes": ["c", "d"],
                        "rationale_vi": "Second family is coherent.",
                    },
                ],
                "groups": [
                    {
                        "parent_code": "group_a",
                        "ward_home_cluster_index": 1,
                        "name_vi": "Group A",
                        "name_en": "Group A",
                        "description_vi": "First family",
                        "boundary_notes_vi": "Excludes second family",
                        "member_codes": ["a", "b"],
                        "coherence": "high",
                        "pg_readiness_reason_vi": "One family",
                        "singleton_justification_vi": "",
                    },
                    {
                        "parent_code": "group_b",
                        "ward_home_cluster_index": 2,
                        "name_vi": "Group B",
                        "name_en": "Group B",
                        "description_vi": "Second family",
                        "boundary_notes_vi": "Excludes first family",
                        "member_codes": ["c", "d"],
                        "coherence": "high",
                        "pg_readiness_reason_vi": "One family",
                        "singleton_justification_vi": "",
                    },
                ],
                "unresolved_issues_vi": [],
            },
            {"provider": "fake", "api_calls": 1},
        )


class FakeEmbedder:
    def embed(self, texts: list[str], *, kind: str):
        assert kind == "document"
        assert len(texts) == 4
        return (
            [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.0, 1.0],
                [0.1, 0.9],
            ],
            {"provider": "fake", "embedded_items": 4},
        )


class RepairingFakeGenerator(FakeGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.refinement_attempts = 0

    def generate(self, *, prompt: str, request: dict, stage: str):
        response, telemetry = super().generate(
            prompt=prompt,
            request=request,
            stage="parent_refinement" if stage == "parent_refinement_repair" else stage,
        )
        if stage.startswith("parent_refinement"):
            self.calls[-1]["stage"] = stage
            self.refinement_attempts += 1
            if self.refinement_attempts == 1:
                response["groups"][0]["member_codes"] = ["a"]
                response["groups"][1]["member_codes"] = ["b", "c", "d"]
        return response, {**telemetry, "stage": stage}


class ExtractionRepairFakeGenerator(FakeGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.extraction_attempts = 0

    def generate(self, *, prompt: str, request: dict, stage: str):
        response, telemetry = super().generate(
            prompt=prompt,
            request=request,
            stage="kc_extraction" if stage == "kc_extraction_repair" else stage,
        )
        if stage.startswith("kc_extraction"):
            self.calls[-1]["stage"] = stage
            self.extraction_attempts += 1
            if self.extraction_attempts == 1:
                response["knowledge_items"][0]["primary_capability_vi"] = ""
        return response, {**telemetry, "stage": stage}


def test_pipeline_runs_without_repo_or_hidden_input_paths(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    generator = FakeGenerator()
    pipeline = KCPipeline(
        generator=generator,
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )

    result = pipeline.run(input_dir=input_dir, output_dir=output_dir)

    assert result["parent_topics"]["final_k"] == 2
    assert [call["stage"] for call in generator.calls] == [
        "kc_extraction",
        "parent_refinement",
    ]
    assert (output_dir / "kc-candidates.json").is_file()
    assert (output_dir / "ward-candidates.json").is_file()
    assert (output_dir / "parent-topics.json").is_file()
    manifest_text = (output_dir / "run-manifest.json").read_text(encoding="utf-8")
    assert "VLEARN_REPO_ROOT" not in manifest_text
    assert "/home/" not in manifest_text

    replay = replay_run(input_dir=input_dir, recorded_dir=output_dir)
    assert replay["trackable_kcs"] == 4
    assert replay["parent_topics"] == 2


def test_pipeline_repairs_invalid_parent_refinement_once(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    generator = RepairingFakeGenerator()
    pipeline = KCPipeline(
        generator=generator,
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )

    result = pipeline.run(input_dir=input_dir, output_dir=output_dir)

    assert [call["stage"] for call in generator.calls] == [
        "kc_extraction",
        "parent_refinement",
        "parent_refinement_repair",
    ]
    telemetry = result["manifest"]["telemetry"]["parent_refinement"]
    assert telemetry["attempts"] == 2
    assert "singleton justification" in telemetry["repair_trigger"]
    assert replay_run(input_dir=input_dir, recorded_dir=output_dir)["verified"] is True


def test_pipeline_repairs_invalid_kc_extraction_once(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    generator = ExtractionRepairFakeGenerator()
    pipeline = KCPipeline(
        generator=generator,
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )

    result = pipeline.run(input_dir=input_dir, output_dir=output_dir)

    assert [call["stage"] for call in generator.calls] == [
        "kc_extraction",
        "kc_extraction_repair",
        "parent_refinement",
    ]
    telemetry = result["manifest"]["telemetry"]["kc_extraction"]
    assert telemetry["attempts"] == 2
    assert "primary_capability_vi" in telemetry["repair_trigger"]


def test_replay_detects_tampered_parent_membership(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    pipeline = KCPipeline(
        generator=FakeGenerator(),
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )
    pipeline.run(input_dir=input_dir, output_dir=output_dir)
    topics = json.loads((output_dir / "parent-topics.json").read_text(encoding="utf-8"))
    topics["groups"][0]["member_codes"].remove("a")
    _write_json(output_dir / "parent-topics.json", topics)

    try:
        replay_run(input_dir=input_dir, recorded_dir=output_dir)
    except ValueError as exc:
        assert "missing leaf codes" in str(exc)
    else:
        raise AssertionError("tampered replay must fail")

def test_replay_tolerates_machine_precision_in_ward_linkage(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    pipeline = KCPipeline(
        generator=FakeGenerator(),
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )
    pipeline.run(input_dir=input_dir, output_dir=output_dir)
    ward = json.loads((output_dir / "ward-candidates.json").read_text(encoding="utf-8"))
    ward["ward_linkage"][0][2] += 1e-14
    _write_json(output_dir / "ward-candidates.json", ward)
    manifest = json.loads((output_dir / "run-manifest.json").read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["ward_candidates"] = sha256_json(ward)
    _write_json(output_dir / "run-manifest.json", manifest)

    replay = replay_run(input_dir=input_dir, recorded_dir=output_dir)

    assert replay["verified"] is True

def test_replay_rejects_material_change_in_ward_linkage(tmp_path: Path) -> None:
    input_dir = _material_bundle(tmp_path / "material")
    output_dir = tmp_path / "run"
    pipeline = KCPipeline(
        generator=FakeGenerator(),
        embedder=FakeEmbedder(),
        extraction_prompt="extract",
        refinement_prompt="refine",
    )
    pipeline.run(input_dir=input_dir, output_dir=output_dir)
    ward = json.loads((output_dir / "ward-candidates.json").read_text(encoding="utf-8"))
    ward["ward_linkage"][0][2] += 0.01
    _write_json(output_dir / "ward-candidates.json", ward)
    manifest = json.loads((output_dir / "run-manifest.json").read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["ward_candidates"] = sha256_json(ward)
    _write_json(output_dir / "run-manifest.json", manifest)

    with pytest.raises(ValueError, match="Ward candidates"):
        replay_run(input_dir=input_dir, recorded_dir=output_dir)
