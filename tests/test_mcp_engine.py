from __future__ import annotations

from pathlib import Path

import pytest

import vlearn_kc_mcp.engine as engine
from vlearn_kc_mcp.__main__ import build_parser, main
from vlearn_kc_mcp.engine import ProviderPipelineRunner


def test_provider_runner_builds_pipeline_and_closes_embedder(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class FakeGenerator:
        def __init__(self, **kwargs) -> None:
            captured["generator"] = kwargs

    class FakeEmbedder:
        def __init__(self, **kwargs) -> None:
            captured["embedder"] = kwargs

        def close(self) -> None:
            captured["closed"] = True

    class FakePipeline:
        def __init__(self, **kwargs) -> None:
            captured["pipeline"] = kwargs

        def run(self, *, input_dir, output_dir) -> None:
            captured["run"] = (input_dir, output_dir)

    monkeypatch.setattr(engine, "GatewayJsonGenerator", FakeGenerator)
    monkeypatch.setattr(engine, "GeminiEmbedder", FakeEmbedder)
    monkeypatch.setattr(engine, "KCPipeline", FakePipeline)
    runner = ProviderPipelineRunner(
        generation_api_key="openai-secret",
        gemini_api_keys=["gemini-secret"],
    )
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    runner.run(input_dir=input_dir, output_dir=output_dir)

    assert captured["generator"]["api_key"] == "openai-secret"
    assert captured["embedder"]["api_keys"] == ["gemini-secret"]
    assert captured["embedder"]["cache_path"] == output_dir / "embedding-cache.json"
    assert captured["run"] == (input_dir, output_dir)
    assert captured["closed"] is True


def test_provider_runner_closes_embedder_when_pipeline_fails(
    monkeypatch, tmp_path: Path
) -> None:
    closed: list[bool] = []

    class FakeGenerator:
        def __init__(self, **kwargs) -> None:
            pass

    class FakeEmbedder:
        def __init__(self, **kwargs) -> None:
            pass

        def close(self) -> None:
            closed.append(True)

    class FailingPipeline:
        def __init__(self, **kwargs) -> None:
            pass

        def run(self, **kwargs) -> None:
            raise RuntimeError("pipeline failed")

    monkeypatch.setattr(engine, "GatewayJsonGenerator", FakeGenerator)
    monkeypatch.setattr(engine, "GeminiEmbedder", FakeEmbedder)
    monkeypatch.setattr(engine, "KCPipeline", FailingPipeline)
    runner = ProviderPipelineRunner(
        generation_api_key="openai-secret",
        gemini_api_keys=["gemini-secret"],
    )

    with pytest.raises(RuntimeError, match="pipeline failed"):
        runner.run(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    assert closed == [True]


def test_provider_configuration_requires_keys(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        ProviderPipelineRunner.from_environment()


def test_entrypoint_defaults_to_stdio_and_refuses_unprotected_remote_bind(
    monkeypatch,
) -> None:
    args = build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"

    monkeypatch.setenv("OPENAI_API_KEY", "openai")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini")
    with pytest.raises(SystemExit, match="refusing unauthenticated remote bind"):
        main(["--transport", "streamable-http", "--host", "0.0.0.0"])

    with pytest.raises(SystemExit):
        build_parser().parse_args(["--allow-unauthenticated-remote"])


def test_entrypoint_exposes_resource_and_owner_limits() -> None:
    args = build_parser().parse_args(
        [
            "--owner-namespace",
            "tenant-a",
            "--max-active-jobs",
            "3",
            "--max-stored-jobs",
            "50",
            "--max-content-units",
            "1000",
        ]
    )

    assert args.owner_namespace == "tenant-a"
    assert args.max_active_jobs == 3
    assert args.max_stored_jobs == 50
    assert args.max_content_units == 1000
