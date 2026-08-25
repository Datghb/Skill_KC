from __future__ import annotations

import json

from test_contracts import build_bundle
import pytest
import vlearn_kc.cli as cli
from vlearn_kc.cli import main


def test_run_defaults_to_direct_openai_api() -> None:
    args = cli.build_parser().parse_args(["run", "bundle", "output"])

    assert args.gateway_base_url == "https://api.openai.com/v1"
    assert args.gateway_model == "gpt-5.6-luna"
    assert args.gateway_key_env == "OPENAI_API_KEY"


def test_validate_command_reports_bundle_without_external_paths(
    tmp_path, capsys
) -> None:
    bundle = build_bundle(tmp_path / "bundle")

    exit_code = main(["validate", str(bundle)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["source_slug"] == "day01-source"
    assert output["content_units"] == 1
    assert output["verified"] is True


def test_replay_command_prints_replay_result(monkeypatch, capsys, tmp_path) -> None:
    expected = {"schema_version": "replay_v1", "verified": True}
    calls: list[tuple[str, str]] = []

    def fake_replay_run(*, input_dir, recorded_dir):
        calls.append((input_dir, recorded_dir))
        return expected

    monkeypatch.setattr(cli, "replay_run", fake_replay_run)

    assert main(["replay", str(tmp_path / "bundle"), str(tmp_path / "run")]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert calls == [(str(tmp_path / "bundle"), str(tmp_path / "run"))]


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"GEMINI_API_KEY": "gemini"}, "OPENAI_API_KEY is required"),
        ({"OPENAI_API_KEY": "gateway"}, "GEMINI_API_KEYS or GEMINI_API_KEY"),
    ],
)
def test_run_command_requires_provider_keys(
    monkeypatch, tmp_path, environment: dict[str, str], message: str
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=message):
        main(["run", str(tmp_path / "bundle"), str(tmp_path / "output")])


def test_run_command_uses_prompt_overrides_and_closes_embedder(
    monkeypatch, tmp_path, capsys
) -> None:
    extraction_prompt = tmp_path / "extraction.md"
    refinement_prompt = tmp_path / "refinement.md"
    extraction_prompt.write_text("custom extraction", encoding="utf-8")
    refinement_prompt.write_text("custom refinement", encoding="utf-8")
    cache_path = tmp_path / "custom-cache.json"
    captured: dict[str, object] = {}

    class FakeGenerator:
        def __init__(self, **kwargs) -> None:
            captured["generator"] = kwargs

    class FakeEmbedder:
        def __init__(self, **kwargs) -> None:
            captured["embedder"] = kwargs
            self.closed = False
            captured["embedder_instance"] = self

        def close(self) -> None:
            self.closed = True

    class FakePipeline:
        def __init__(self, **kwargs) -> None:
            captured["pipeline"] = kwargs

        def run(self, *, input_dir, output_dir):
            captured["run"] = (input_dir, output_dir)
            return {"manifest": {"schema_version": "manifest_v1", "counts": {}}}

    monkeypatch.setenv("CUSTOM_GATEWAY_KEY", "gateway-secret")
    monkeypatch.setenv("CUSTOM_GEMINI_KEYS", " first-key, second-key ")
    monkeypatch.setattr(cli, "GatewayJsonGenerator", FakeGenerator)
    monkeypatch.setattr(cli, "GeminiEmbedder", FakeEmbedder)
    monkeypatch.setattr(cli, "KCPipeline", FakePipeline)

    output = tmp_path / "output"
    exit_code = main(
        [
            "run",
            str(tmp_path / "bundle"),
            str(output),
            "--gateway-key-env",
            "CUSTOM_GATEWAY_KEY",
            "--gateway-base-url",
            "https://gateway.example/v1",
            "--gateway-model",
            "test-model",
            "--reasoning-effort",
            "medium",
            "--gemini-keys-env",
            "CUSTOM_GEMINI_KEYS",
            "--gemini-base-url",
            "https://gemini.example/v1",
            "--embedding-model",
            "embed-model",
            "--embedding-cache",
            str(cache_path),
            "--extraction-prompt",
            str(extraction_prompt),
            "--refinement-prompt",
            str(refinement_prompt),
        ]
    )

    assert exit_code == 0
    assert captured["generator"] == {
        "api_key": "gateway-secret",
        "model": "test-model",
        "base_url": "https://gateway.example/v1",
        "reasoning_effort": "medium",
    }
    assert captured["embedder"] == {
        "api_keys": ["first-key", "second-key"],
        "model": "embed-model",
        "base_url": "https://gemini.example/v1",
        "cache_path": cache_path,
    }
    assert captured["pipeline"]["extraction_prompt"] == "custom extraction"
    assert captured["pipeline"]["refinement_prompt"] == "custom refinement"
    assert captured["run"] == (str(tmp_path / "bundle"), output)
    assert captured["embedder_instance"].closed is True
    assert json.loads(capsys.readouterr().out)["schema_version"] == "manifest_v1"


def test_run_command_closes_embedder_when_pipeline_fails(monkeypatch, tmp_path) -> None:
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

        def run(self, **kwargs):
            raise RuntimeError("pipeline failed")

    monkeypatch.setenv("OPENAI_API_KEY", "gateway")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.setattr(cli, "GatewayJsonGenerator", FakeGenerator)
    monkeypatch.setattr(cli, "GeminiEmbedder", FakeEmbedder)
    monkeypatch.setattr(cli, "KCPipeline", FailingPipeline)

    with pytest.raises(RuntimeError, match="pipeline failed"):
        main(["run", str(tmp_path / "bundle"), str(tmp_path / "output")])

    assert closed == [True]
