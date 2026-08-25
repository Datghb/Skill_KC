from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .io import read_json, sha256_json, sha256_text


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_DISPOSITIONS = {"lecture", "lab", "assessment", "reference"}


class ContractError(ValueError):
    """Raised when a material bundle violates the public input contract."""


@dataclass(frozen=True)
class SourceArtifact:
    source_id: str
    source_type: str
    sha256: str
    uri: str | None = None
    source_disposition: str = "lecture"


@dataclass(frozen=True)
class ContentUnit:
    content_unit_id: str
    source_id: str
    source_type: str
    content: str
    content_sha256: str
    page_no: int | None
    start_seconds: float | None
    end_seconds: float | None
    locator: str | None = None
    source_disposition: str = "lecture"

    def as_dict(self) -> dict[str, Any]:
        return {
            "content_unit_id": self.content_unit_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_disposition": self.source_disposition,
            "page_no": self.page_no,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "locator": self.locator,
            "content": self.content,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class MaterialBundle:
    lesson_id: str
    source_slug: str
    day: int
    title: str
    sources: tuple[SourceArtifact, ...]
    content_units: tuple[ContentUnit, ...]
    bundle_sha256: str


def _required_text(value: dict[str, Any], field: str, context: str) -> str:
    result = str(value.get(field) or "").strip()
    if not result:
        raise ContractError(f"{context}: {field} is required")
    return result


def _validate_schema(value: dict[str, Any], expected: str, path: Path) -> None:
    if value.get("schema_version") != expected:
        raise ContractError(f"{path}: expected schema_version {expected}")


def _validate_source(raw: dict[str, Any], index: int) -> SourceArtifact:
    context = f"sources[{index}]"
    path_value = raw.get("path")
    if path_value and Path(str(path_value)).is_absolute():
        raise ContractError(f"{context}: absolute paths are forbidden")
    digest = _required_text(raw, "sha256", context)
    if not SHA256_RE.fullmatch(digest):
        raise ContractError(f"{context}: sha256 must be 64 lowercase hex chars")
    source_type = _required_text(raw, "source_type", context)
    disposition = str(raw.get("source_disposition") or "").strip()
    if not disposition:
        disposition = _default_disposition(source_type)
    if disposition not in SOURCE_DISPOSITIONS:
        raise ContractError(f"{context}: invalid source_disposition {disposition!r}")
    return SourceArtifact(
        source_id=_required_text(raw, "source_id", context),
        source_type=source_type,
        sha256=digest,
        uri=str(raw.get("uri") or "").strip() or None,
        source_disposition=disposition,
    )


def _default_disposition(source_type: str) -> str:
    normalized = source_type.strip().lower()
    if normalized in {"lab", "hands_on", "exercise"}:
        return "lab"
    if normalized in {"assessment", "quiz", "exam"}:
        return "assessment"
    if normalized in {"reference", "reading"}:
        return "reference"
    return "lecture"


def _optional_number(value: Any, field: str, context: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{context}: {field} must be numeric or null")
    return float(value)


def _validate_unit(
    raw: dict[str, Any], index: int, sources: dict[str, SourceArtifact]
) -> ContentUnit:
    context = f"content_units[{index}]"
    source_id = _required_text(raw, "source_id", context)
    if source_id not in sources:
        raise ContractError(f"{context}: unknown source_id {source_id!r}")
    content = _required_text(raw, "content", context)
    digest = _required_text(raw, "content_sha256", context)
    if digest != sha256_text(content):
        raise ContractError(f"{context}: content_sha256 mismatch")
    page = raw.get("page_no")
    if page is not None and (
        isinstance(page, bool) or not isinstance(page, int) or page < 1
    ):
        raise ContractError(f"{context}: page_no must be a positive integer or null")
    start = _optional_number(raw.get("start_seconds"), "start_seconds", context)
    end = _optional_number(raw.get("end_seconds"), "end_seconds", context)
    if (start is None) != (end is None):
        raise ContractError(f"{context}: timestamps must both be present or null")
    if start is not None and (start < 0 or end is None or end <= start):
        raise ContractError(f"{context}: invalid timestamp range")
    locator = str(raw.get("locator") or "").strip() or None
    if page is None and start is None and locator is None:
        raise ContractError(
            f"{context}: page_no, timestamp range or stable locator is required"
        )
    disposition = str(raw.get("source_disposition") or "").strip()
    if not disposition:
        disposition = sources[source_id].source_disposition
    if disposition not in SOURCE_DISPOSITIONS:
        raise ContractError(f"{context}: invalid source_disposition {disposition!r}")
    return ContentUnit(
        content_unit_id=_required_text(raw, "content_unit_id", context),
        source_id=source_id,
        source_type=_required_text(raw, "source_type", context),
        content=content,
        content_sha256=digest,
        page_no=page,
        start_seconds=start,
        end_seconds=end,
        locator=locator,
        source_disposition=disposition,
    )


def load_material_bundle(root: Path | str) -> MaterialBundle:
    root = Path(root)
    lesson_path = root / "lesson.json"
    sources_path = root / "sources.json"
    units_path = root / "content_units.json"
    missing = [path.name for path in (lesson_path, sources_path, units_path) if not path.is_file()]
    if missing:
        raise ContractError(f"material bundle is missing files: {missing}")

    lesson = read_json(lesson_path)
    source_payload = read_json(sources_path)
    unit_payload = read_json(units_path)
    _validate_schema(lesson, "vlearn_lesson_v1", lesson_path)
    _validate_schema(source_payload, "vlearn_sources_v1", sources_path)
    _validate_schema(unit_payload, "vlearn_content_units_v1", units_path)
    source_slug = _required_text(lesson, "source_slug", "lesson")
    for payload, name in ((source_payload, "sources"), (unit_payload, "content_units")):
        if payload.get("source_slug") != source_slug:
            raise ContractError(f"{name}: source_slug mismatch")

    raw_sources = source_payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ContractError("sources: non-empty sources list is required")
    sources = tuple(_validate_source(raw, index) for index, raw in enumerate(raw_sources))
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ContractError("sources: duplicate source_id")

    raw_units = unit_payload.get("content_units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ContractError("content_units: non-empty content_units list is required")
    source_index = {source.source_id: source for source in sources}
    units = tuple(
        _validate_unit(raw, index, source_index) for index, raw in enumerate(raw_units)
    )
    unit_ids = [unit.content_unit_id for unit in units]
    if len(unit_ids) != len(set(unit_ids)):
        raise ContractError("content_units: duplicate content_unit_id")

    day = lesson.get("day")
    if isinstance(day, bool) or not isinstance(day, int) or day < 1:
        raise ContractError("lesson: day must be a positive integer")
    bundle_hash = sha256_json(
        {
            "lesson": lesson,
            "sources": source_payload,
            "content_units": unit_payload,
        }
    )
    return MaterialBundle(
        lesson_id=_required_text(lesson, "lesson_id", "lesson"),
        source_slug=source_slug,
        day=day,
        title=_required_text(lesson, "title", "lesson"),
        sources=sources,
        content_units=units,
        bundle_sha256=bundle_hash,
    )
