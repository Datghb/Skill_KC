#!/usr/bin/env python3
"""Safe command wrapper for the VLearn KC extraction engine."""

from __future__ import annotations

import argparse
from importlib.util import find_spec
import json
from os import environ as process_environ
from os import pathsep
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


REQUIRED_FILES = ("lesson.json", "sources.json", "content_units.json")
SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def _local_source_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "src" / "vlearn_kc"
        if candidate.is_dir():
            return parent / "src"
    return None


LOCAL_SOURCE_ROOT = _local_source_root()
if LOCAL_SOURCE_ROOT is not None and str(LOCAL_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(LOCAL_SOURCE_ROOT))


def engine_command(*arguments: str) -> list[str]:
    return [sys.executable, "-m", "vlearn_kc", *arguments]


def _check_python(version_info: Sequence[int]) -> None:
    if tuple(version_info[:2]) < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required")


def _check_bundle_files(bundle: Path | str) -> Path:
    bundle_path = Path(bundle)
    if not bundle_path.is_dir():
        raise ValueError(f"material bundle directory does not exist: {bundle_path}")
    missing = [name for name in REQUIRED_FILES if not (bundle_path / name).is_file()]
    if missing:
        raise ValueError(f"material bundle is missing required files: {missing}")
    return bundle_path


def _provider_secrets(environ: Mapping[str, str]) -> tuple[str, ...]:
    values = [environ.get("OPENAI_API_KEY", "")]
    values.extend(environ.get("GEMINI_API_KEYS", "").split(","))
    values.append(environ.get("GEMINI_API_KEY", ""))
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def preflight(
    bundle: Path | str,
    *,
    environ: Mapping[str, str],
    version_info: Sequence[int] = sys.version_info,
) -> MappingProxyType:
    """Validate local prerequisites without changing caller-owned state."""
    _check_python(version_info)
    bundle_path = _check_bundle_files(bundle)
    if not environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is required")
    if not (
        environ.get("GEMINI_API_KEYS", "").strip()
        or environ.get("GEMINI_API_KEY", "").strip()
    ):
        raise RuntimeError("GEMINI_API_KEYS or GEMINI_API_KEY is required")
    return MappingProxyType(
        {
            "ok": True,
            "bundle": str(bundle_path),
            "required_files": REQUIRED_FILES,
            "providers": ("openai", "gemini"),
        }
    )


def redact(text: str, secrets: Sequence[str]) -> str:
    """Remove non-empty secret values from diagnostic output."""
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _subprocess_environ(environ: Mapping[str, str]) -> dict[str, str]:
    child_environ = dict(environ)
    if LOCAL_SOURCE_ROOT is None:
        return child_environ
    existing = child_environ.get("PYTHONPATH", "")
    entries = [item for item in existing.split(pathsep) if item]
    local_source = str(LOCAL_SOURCE_ROOT)
    if local_source not in entries:
        child_environ["PYTHONPATH"] = pathsep.join([local_source, *entries])
    return child_environ


def run_command(
    command: list[str],
    *,
    runner: SubprocessRunner = subprocess.run,
    secrets: Sequence[str] = (),
    environ: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "check": False,
    }
    kwargs["env"] = _subprocess_environ(process_environ if environ is None else environ)
    try:
        result = runner(command, **kwargs)
    except OSError as exc:
        safe_error = redact(str(exc), secrets)
        raise RuntimeError(f"KC engine could not start: {safe_error}") from None
    if result.returncode != 0:
        details = "\n".join(
            value.strip() for value in (result.stdout, result.stderr) if value.strip()
        )
        safe_details = redact(details or "command failed without diagnostics", secrets)
        raise RuntimeError(f"KC engine command failed: {safe_details}")
    return result


def _json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("KC engine returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("KC engine must return a JSON object")
    return payload


def build_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    counts = manifest.get("counts") or {}
    release = manifest.get("release") or {}
    if release.get("auto_publish") is not False or release.get("production_write") is not False:
        raise RuntimeError("run manifest release safety flags are missing or unsafe")
    return {
        "source_slug": manifest.get("source_slug"),
        "content_units": counts.get("content_units", 0),
        "knowledge_items": counts.get("knowledge_items", 0),
        "trackable_kcs": counts.get("trackable_kcs", 0),
        "parent_topics": counts.get("parent_topics", 0),
        "review_required": True,
        "publish_allowed": False,
    }


def _ensure_fresh_output(output: Path) -> None:
    if output.exists() and not output.is_dir():
        raise ValueError(f"output path is not a directory: {output}")
    existing = tuple(path.name for path in output.iterdir()) if output.is_dir() else ()
    if existing:
        raise ValueError(f"output directory must be empty: {sorted(existing)}")


def _engine_available() -> bool:
    return find_spec("vlearn_kc") is not None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_kc.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local prerequisites")
    doctor.add_argument("input")

    validate = subparsers.add_parser("validate", help="Validate a material bundle offline")
    validate.add_argument("input")

    replay = subparsers.add_parser("replay", help="Verify recorded artifacts offline")
    replay.add_argument("input")
    replay.add_argument("recorded")

    run = subparsers.add_parser("run", help="Run provider-backed KC extraction")
    run.add_argument("input")
    run.add_argument("output")
    run.add_argument(
        "--embedding-cache",
        help="Reuse an embedding cache outside the new output directory",
    )
    run.add_argument(
        "--acknowledge-external-processing",
        action="store_true",
        help="Confirm course data may be sent to OpenAI and Gemini",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    runner: SubprocessRunner = subprocess.run,
) -> int:
    args = build_parser().parse_args(argv)
    active_environ = process_environ if environ is None else environ
    _check_python(sys.version_info)
    bundle = _check_bundle_files(args.input)

    if args.command == "doctor":
        report = {
            "ok": _engine_available(),
            "python": ".".join(map(str, sys.version_info[:3])),
            "engine_available": _engine_available(),
            "bundle": str(bundle),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    if args.command == "validate":
        result = run_command(
            engine_command("validate", str(bundle)),
            runner=runner,
            environ=active_environ,
        )
        print(json.dumps(_json_stdout(result), ensure_ascii=False, indent=2))
        return 0

    if args.command == "replay":
        recorded = Path(args.recorded)
        if not recorded.is_dir():
            raise ValueError(f"recorded run directory does not exist: {recorded}")
        result = run_command(
            engine_command("replay", str(bundle), str(recorded)),
            runner=runner,
            environ=active_environ,
        )
        print(json.dumps(_json_stdout(result), ensure_ascii=False, indent=2))
        return 0

    if not args.acknowledge_external_processing:
        build_parser().error(
            "run requires --acknowledge-external-processing after user consent"
        )
    validation_result = run_command(
        engine_command("validate", str(bundle)),
        runner=runner,
        secrets=_provider_secrets(active_environ),
        environ=active_environ,
    )
    _json_stdout(validation_result)
    preflight(bundle, environ=active_environ)
    output = Path(args.output)
    _ensure_fresh_output(output)
    secrets = _provider_secrets(active_environ)
    run_arguments = ["run", str(bundle), str(output)]
    if args.embedding_cache:
        run_arguments.extend(["--embedding-cache", args.embedding_cache])
    run_result = run_command(
        engine_command(*run_arguments),
        runner=runner,
        secrets=secrets,
        environ=active_environ,
    )
    manifest = _json_stdout(run_result)
    replay_result = run_command(
        engine_command("replay", str(bundle), str(output)),
        runner=runner,
        secrets=secrets,
        environ=active_environ,
    )
    replay_payload = _json_stdout(replay_result)
    summary = {
        **build_summary(manifest),
        "verified": replay_payload.get("verified") is True,
        "status": "draft",
        "output_dir": str(output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from None
