from __future__ import annotations

import argparse
from importlib.resources import files
import json
import os
from pathlib import Path
from typing import Sequence

from .contracts import load_material_bundle
from .pipeline import KCPipeline
from .providers import GatewayJsonGenerator, GeminiEmbedder
from .replay import replay_run


def _prompt(name: str, override: str | None) -> str:
    if override:
        return Path(override).read_text(encoding="utf-8")
    return files("vlearn_kc.prompts").joinpath(name).read_text(encoding="utf-8")


def _gemini_keys(env_name: str) -> list[str]:
    value = os.getenv(env_name, "").strip()
    if not value and env_name == "GEMINI_API_KEYS":
        value = os.getenv("GEMINI_API_KEY", "").strip()
    return [item.strip() for item in value.split(",") if item.strip()]


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vlearn-kc")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a material bundle")
    validate.add_argument("input")

    replay = subparsers.add_parser("replay", help="Replay and verify recorded artifacts")
    replay.add_argument("input")
    replay.add_argument("recorded")

    run = subparsers.add_parser("run", help="Run extraction and clustering")
    run.add_argument("input")
    run.add_argument("output")
    run.add_argument(
        "--generation-key-env",
        "--gateway-key-env",
        dest="gateway_key_env",
        default="OPENAI_API_KEY",
    )
    run.add_argument(
        "--generation-base-url",
        "--gateway-base-url",
        dest="gateway_base_url",
        default="https://api.openai.com/v1",
    )
    run.add_argument(
        "--generation-model",
        "--gateway-model",
        dest="gateway_model",
        default="gpt-5.6-luna",
    )
    run.add_argument("--reasoning-effort", default="high")
    run.add_argument("--gemini-keys-env", default="GEMINI_API_KEYS")
    run.add_argument(
        "--gemini-base-url",
        default="https://generativelanguage.googleapis.com/v1beta",
    )
    run.add_argument("--embedding-model", default="gemini-embedding-2")
    run.add_argument("--embedding-cache")
    run.add_argument("--extraction-prompt")
    run.add_argument("--refinement-prompt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        bundle = load_material_bundle(args.input)
        _print(
            {
                "schema_version": "vlearn_material_validation_v1",
                "source_slug": bundle.source_slug,
                "lesson_id": bundle.lesson_id,
                "sources": len(bundle.sources),
                "content_units": len(bundle.content_units),
                "bundle_sha256": bundle.bundle_sha256,
                "verified": True,
            }
        )
        return 0
    if args.command == "replay":
        _print(replay_run(input_dir=args.input, recorded_dir=args.recorded))
        return 0

    api_key = os.getenv(args.gateway_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"{args.gateway_key_env} is required")
    keys = _gemini_keys(args.gemini_keys_env)
    if not keys:
        raise RuntimeError(
            f"{args.gemini_keys_env} or GEMINI_API_KEY is required"
        )
    output = Path(args.output)
    cache_path = (
        Path(args.embedding_cache)
        if args.embedding_cache
        else output / "embedding-cache.json"
    )
    generator = GatewayJsonGenerator(
        api_key=api_key,
        model=args.gateway_model,
        base_url=args.gateway_base_url,
        reasoning_effort=args.reasoning_effort,
    )
    embedder = GeminiEmbedder(
        api_keys=keys,
        model=args.embedding_model,
        base_url=args.gemini_base_url,
        cache_path=cache_path,
    )
    try:
        pipeline = KCPipeline(
            generator=generator,
            embedder=embedder,
            extraction_prompt=_prompt("kc-extraction.md", args.extraction_prompt),
            refinement_prompt=_prompt(
                "parent-refinement.md", args.refinement_prompt
            ),
        )
        result = pipeline.run(input_dir=args.input, output_dir=output)
    finally:
        embedder.close()
    _print(result["manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
