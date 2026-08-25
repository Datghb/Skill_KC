from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType

import pytest


RUNNER_PATH = (
    Path(__file__).parents[1]
    / "skills"
    / "vlearn-kc-extractor"
    / "scripts"
    / "run_kc.py"
)


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("vlearn_kc_skill_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load skill runner from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runner_module():
    return _load_runner_module()


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    bundle_path = tmp_path / "bundle"
    bundle_path.mkdir()
    for filename in ("lesson.json", "sources.json", "content_units.json"):
        (bundle_path / filename).write_text("{}\n", encoding="utf-8")
    return bundle_path


def test_preflight_rejects_bundle_missing_any_required_file(
    runner_module, bundle: Path
) -> None:
    (bundle / "sources.json").unlink()

    with pytest.raises(ValueError, match=r"sources\.json"):
        runner_module.preflight(
            bundle,
            environ={"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"},
            version_info=(3, 12, 0),
        )


def test_preflight_requires_python_3_12(runner_module, bundle: Path) -> None:
    with pytest.raises(RuntimeError, match=r"Python 3\.12"):
        runner_module.preflight(
            bundle,
            environ={"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"},
            version_info=(3, 11, 9),
        )


@pytest.mark.parametrize(
    ("environ", "missing_name"),
    [
        ({"GEMINI_API_KEY": "gemini"}, "OPENAI_API_KEY"),
        ({"OPENAI_API_KEY": "gateway"}, "GEMINI_API_KEYS"),
    ],
)
def test_preflight_requires_provider_credentials(
    runner_module, bundle: Path, environ: dict[str, str], missing_name: str
) -> None:
    with pytest.raises(RuntimeError, match=missing_name):
        runner_module.preflight(bundle, environ=environ, version_info=(3, 12, 0))


def test_preflight_accepts_singular_gemini_key_and_returns_immutable_report(
    runner_module, bundle: Path
) -> None:
    environ = {"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"}
    original = dict(environ)

    report = runner_module.preflight(
        bundle, environ=environ, version_info=(3, 12, 0)
    )

    assert environ == original
    assert isinstance(report, MappingProxyType)
    assert report["ok"] is True
    assert report["required_files"] == (
        "lesson.json",
        "sources.json",
        "content_units.json",
    )
    with pytest.raises(TypeError):
        report["ok"] = False


def test_run_command_uses_injected_subprocess_runner(runner_module) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout='{"verified": true}', stderr="")

    result = runner_module.run_command(
        runner_module.engine_command("validate", "/tmp/bundle"), runner=fake_run
    )

    assert json.loads(result.stdout)["verified"] is True
    assert calls[0][0] == runner_module.engine_command(
        "validate", "/tmp/bundle"
    )
    assert calls[0][1]["capture_output"] is True
    assert calls[0][1]["text"] is True
    assert calls[0][1]["check"] is False


def test_run_command_adds_local_src_to_subprocess_pythonpath(runner_module) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    environ = {"PYTHONPATH": "/already/there"}
    original = dict(environ)

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 0, stdout='{"verified": true}', stderr=""
        )

    runner_module.run_command(
        runner_module.engine_command("validate", "/tmp/bundle"),
        runner=fake_run,
        environ=environ,
    )

    child_env = calls[0][1]["env"]
    pythonpath = child_env["PYTHONPATH"].split(":")
    assert environ == original
    assert str(Path(__file__).parents[1] / "src") in pythonpath
    assert "/already/there" in pythonpath


def test_run_command_redacts_every_secret_from_failure(runner_module) -> None:
    secrets = ("gateway-super-secret", "gemini-super-secret")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=f"request used {secrets[0]}",
            stderr=f"provider rejected {secrets[1]}",
        )

    with pytest.raises(RuntimeError) as exc_info:
        runner_module.run_command(
            ["vlearn-kc", "run", "bundle", "output"],
            runner=fake_run,
            secrets=secrets,
        )

    message = str(exc_info.value)
    assert "[REDACTED]" in message
    assert all(secret not in message for secret in secrets)

def test_provider_secrets_split_multi_key_value_for_redaction(runner_module) -> None:
    secrets = runner_module._provider_secrets(
        {
            "OPENAI_API_KEY": "gateway-secret",
            "GEMINI_API_KEYS": "gemini-one, gemini-two",
        }
    )

    message = runner_module.redact(
        "gateway-secret gemini-one gemini-two", secrets
    )

    assert message == "[REDACTED] [REDACTED] [REDACTED]"

def test_run_command_reports_missing_engine_without_traceback(runner_module) -> None:
    def fake_run(command, **kwargs):
        raise FileNotFoundError("engine executable missing")

    with pytest.raises(RuntimeError, match="could not start"):
        runner_module.run_command(
            runner_module.engine_command("validate", "/tmp/bundle"),
            runner=fake_run,
        )


def test_validate_and_replay_are_offline_and_need_no_credentials_or_ack(
    runner_module, bundle: Path, tmp_path: Path
) -> None:
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        payload = {"verified": True}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    assert runner_module.main(
        ["validate", str(bundle)], environ={}, runner=fake_run
    ) == 0
    assert runner_module.main(
        ["replay", str(bundle), str(recorded)], environ={}, runner=fake_run
    ) == 0
    assert calls == [
        runner_module.engine_command("validate", str(bundle)),
        runner_module.engine_command("replay", str(bundle), str(recorded)),
    ]


def test_run_requires_explicit_external_processing_acknowledgement(
    runner_module, bundle: Path, tmp_path: Path
) -> None:
    called = False

    def fake_run(command, **kwargs):
        nonlocal called
        called = True
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    with pytest.raises(SystemExit) as exc_info:
        runner_module.main(
            ["run", str(bundle), str(tmp_path / "output")],
            environ={"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"},
            runner=fake_run,
        )

    assert exc_info.value.code != 0
    assert called is False

def test_run_rejects_nonempty_output_directory_before_provider_call(
    runner_module, bundle: Path, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "unrelated.txt").write_text("preserve", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, stdout='{"verified": true}', stderr=""
        )

    with pytest.raises(ValueError, match="must be empty"):
        runner_module.main(
            [
                "run",
                str(bundle),
                str(output),
                "--acknowledge-external-processing",
            ],
            environ={"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"},
            runner=fake_run,
        )

    assert [command[3] for command in calls] == ["validate"]
    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "preserve"

def test_run_validates_bundle_before_checking_provider_credentials(
    runner_module, bundle: Path, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="content hash mismatch"
        )

    with pytest.raises(RuntimeError, match="content hash mismatch"):
        runner_module.main(
            [
                "run",
                str(bundle),
                str(tmp_path / "output"),
                "--acknowledge-external-processing",
            ],
            environ={},
            runner=fake_run,
        )

    assert calls == [runner_module.engine_command("validate", str(bundle))]

def test_successful_run_validates_runs_replays_and_returns_draft_summary(
    runner_module, bundle: Path, tmp_path: Path, capsys
) -> None:
    output = tmp_path / "output"
    calls: list[list[str]] = []
    manifest = {
        "source_slug": "course-a",
        "counts": {
            "content_units": 18,
            "knowledge_items": 7,
            "trackable_kcs": 6,
            "parent_topics": 3,
        },
        "release": {"auto_publish": False, "production_write": False},
    }

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[3] == "run":
            payload = manifest
        else:
            payload = {"verified": True}
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(payload), stderr=""
        )

    exit_code = runner_module.main(
        [
            "run",
            str(bundle),
            str(output),
            "--embedding-cache",
            str(tmp_path / "shared-cache.json"),
            "--acknowledge-external-processing",
        ],
        environ={"OPENAI_API_KEY": "gateway", "GEMINI_API_KEY": "gemini"},
        runner=fake_run,
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [command[3] for command in calls] == ["validate", "run", "replay"]
    assert calls[1][-2:] == [
        "--embedding-cache",
        str(tmp_path / "shared-cache.json"),
    ]
    assert summary["status"] == "draft"
    assert summary["verified"] is True
    assert summary["review_required"] is True
    assert summary["publish_allowed"] is False


def test_build_summary_always_requires_human_review_and_disallows_publish(
    runner_module,
) -> None:
    manifest = {
        "source_slug": "course-a",
        "counts": {
            "content_units": 18,
            "knowledge_items": 7,
            "trackable_kcs": 6,
            "parent_topics": 3,
            "leaf_moves": 1,
        },
        "release": {"auto_publish": False, "production_write": False},
    }

    summary = runner_module.build_summary(manifest)

    assert summary == {
        "source_slug": "course-a",
        "content_units": 18,
        "knowledge_items": 7,
        "trackable_kcs": 6,
        "parent_topics": 3,
        "review_required": True,
        "publish_allowed": False,
    }

def test_build_summary_rejects_manifest_that_allows_release(runner_module) -> None:
    with pytest.raises(RuntimeError, match="release safety flags"):
        runner_module.build_summary(
            {
                "source_slug": "course-a",
                "counts": {},
                "release": {"auto_publish": True, "production_write": False},
            }
        )
