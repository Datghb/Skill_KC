from __future__ import annotations

import json
from pathlib import Path

from vlearn_kc.contracts import load_material_bundle


ROOT = Path(__file__).resolve().parents[1]


def test_all_phase1_material_bundles_are_self_contained() -> None:
    root = ROOT / "material-bundles/phase1"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bundles = [load_material_bundle(root / f"day{day:02d}") for day in range(1, 16)]

    assert len(bundles) == manifest["totals"]["days"] == 15
    assert sum(len(bundle.content_units) for bundle in bundles) == manifest["totals"][
        "content_units"
    ]
    assert all(len(bundle.bundle_sha256) == 64 for bundle in bundles)


def test_phase1_leaf_snapshot_has_expected_day_and_kc_totals() -> None:
    root = ROOT / "artifacts/phase1-leaf-review-snapshot"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["totals"] == {"days": 15, "knowledge_items": 526}
    assert all((root / f"day{day:02d}/kc_candidates.json").is_file() for day in range(1, 16))
    assert all(
        (root / f"day{day:02d}/judged_kc_candidates.json").is_file()
        for day in range(1, 16)
    )

