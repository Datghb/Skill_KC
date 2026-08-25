from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from vlearn_kc.contracts import ContractError, load_material_bundle


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_bundle(root: Path) -> Path:
    root.mkdir()
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
    content = "Attention connects tokens by contextual relevance."
    _write_json(
        root / "content_units.json",
        {
            "schema_version": "vlearn_content_units_v1",
            "source_slug": "day01-source",
            "content_units": [
                {
                    "content_unit_id": "day01:p001:text:001",
                    "source_id": "slide-v1",
                    "source_type": "slide",
                    "page_no": 1,
                    "start_seconds": None,
                    "end_seconds": None,
                    "content": content,
                    "content_sha256": _content_hash(content),
                }
            ],
        },
    )
    return root


def test_load_material_bundle_accepts_explicit_self_contained_contract(
    tmp_path: Path,
) -> None:
    bundle = load_material_bundle(build_bundle(tmp_path / "bundle"))

    assert bundle.lesson_id == "phase1-day01"
    assert bundle.source_slug == "day01-source"
    assert bundle.content_units[0].page_no == 1
    assert len(bundle.bundle_sha256) == 64


def test_load_material_bundle_rejects_content_hash_mismatch(tmp_path: Path) -> None:
    root = build_bundle(tmp_path / "bundle")
    payload = json.loads((root / "content_units.json").read_text(encoding="utf-8"))
    payload["content_units"][0]["content_sha256"] = "0" * 64
    _write_json(root / "content_units.json", payload)

    with pytest.raises(ContractError, match="content_sha256 mismatch"):
        load_material_bundle(root)


def test_load_material_bundle_rejects_absolute_source_paths(tmp_path: Path) -> None:
    root = build_bundle(tmp_path / "bundle")
    payload = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    payload["sources"][0]["path"] = "/home/user/Downloads/raw.pdf"
    _write_json(root / "sources.json", payload)

    with pytest.raises(ContractError, match="absolute paths are forbidden"):
        load_material_bundle(root)


def test_load_material_bundle_accepts_stable_derived_locator(tmp_path: Path) -> None:
    root = build_bundle(tmp_path / "bundle")
    payload = json.loads((root / "content_units.json").read_text(encoding="utf-8"))
    payload["content_units"][0]["page_no"] = None
    payload["content_units"][0]["locator"] = "supplemental:001"
    _write_json(root / "content_units.json", payload)

    bundle = load_material_bundle(root)

    assert bundle.content_units[0].locator == "supplemental:001"
