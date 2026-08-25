from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def _validate(schema_name: str, payload_path: Path) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_day01_fixture_matches_public_json_schemas() -> None:
    material = ROOT / "examples/day01/material-bundle"
    recorded = ROOT / "examples/day01/recorded-run"

    _validate("lesson.schema.json", material / "lesson.json")
    _validate("sources.schema.json", material / "sources.json")
    _validate("content-units.schema.json", material / "content_units.json")
    _validate("kc-inventory.schema.json", recorded / "kc-candidates.json")
    _validate("parent-topics.schema.json", recorded / "parent-topics.json")

