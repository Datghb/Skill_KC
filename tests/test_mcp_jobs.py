from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import json
from pathlib import Path
import shutil
from threading import Event, Lock, Thread
import time

import pytest

from vlearn_kc.io import read_json, write_json
from vlearn_kc_mcp.jobs import JobError, KCJobService


ROOT = Path(__file__).resolve().parents[1]


class ImmediateExecutor:
    def submit(self, function, *args):
        future: Future[object] = Future()
        try:
            future.set_result(function(*args))
        except Exception as error:  # pragma: no cover - executor contract
            future.set_exception(error)
        return future

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        pass


class RecordedRunner:
    def __init__(self, recorded: Path) -> None:
        self.recorded = recorded
        self.calls = 0

    def run(self, *, input_dir: Path, output_dir: Path) -> None:
        self.calls += 1
        output_dir.mkdir(parents=True)
        for name in (
            "kc-candidates.json",
            "embeddings.json",
            "ward-candidates.json",
            "parent-topics.json",
            "run-manifest.json",
        ):
            shutil.copyfile(self.recorded / name, output_dir / name)


class FailingRunner:
    def run(self, *, input_dir: Path, output_dir: Path) -> None:
        raise RuntimeError("provider secret should never leave the server")


class BlockingRecordedRunner(RecordedRunner):
    def __init__(self, recorded: Path) -> None:
        super().__init__(recorded)
        self.started = Event()
        self.release = Event()
        self._calls_lock = Lock()

    def run(self, *, input_dir: Path, output_dir: Path) -> None:
        with self._calls_lock:
            self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=5)
        output_dir.mkdir(parents=True)
        for name in (
            "kc-candidates.json",
            "embeddings.json",
            "ward-candidates.json",
            "parent-topics.json",
            "run-manifest.json",
        ):
            shutil.copyfile(self.recorded / name, output_dir / name)


def bundle_payload() -> dict[str, dict]:
    root = ROOT / "examples/day01/material-bundle"
    return {
        "lesson": read_json(root / "lesson.json"),
        "sources": read_json(root / "sources.json"),
        "content_units": read_json(root / "content_units.json"),
    }


def service(tmp_path: Path, runner=None, **kwargs) -> KCJobService:
    return KCJobService(
        root=tmp_path / "jobs",
        runner=runner or RecordedRunner(ROOT / "examples/day01/recorded-run"),
        executor=ImmediateExecutor(),
        verifier=lambda **kwargs: {
            "schema_version": "vlearn_kc_replay_result_v1",
            "verified": True,
        },
        **kwargs,
    )


def test_validate_inline_material_bundle_without_exposing_server_paths(
    tmp_path: Path,
) -> None:
    result = service(tmp_path).validate_material_bundle(bundle_payload())

    assert result["valid"] is True
    assert result["lesson_id"] == "phase1-day01"
    assert result["content_units"] == 261
    assert len(result["bundle_sha256"]) == 64
    assert str(tmp_path) not in json.dumps(result)


def test_start_is_idempotent_and_produces_verified_draft(tmp_path: Path) -> None:
    runner = RecordedRunner(ROOT / "examples/day01/recorded-run")
    jobs = service(tmp_path, runner)

    first = jobs.start_kc_generation(
        material_bundle=bundle_payload(), request_id="lms-request-001"
    )
    second = jobs.start_kc_generation(
        material_bundle=bundle_payload(), request_id="lms-request-001"
    )

    assert first["job_id"] == second["job_id"]
    assert second["idempotent_replay"] is True
    assert runner.calls == 1
    status = jobs.get_kc_job_status(first["job_id"])
    assert status["status"] == "succeeded"
    assert status["stage"] == "complete"
    draft = jobs.get_kc_draft(first["job_id"])
    assert draft["status"] == "draft"
    assert draft["release"] == {
        "auto_publish": False,
        "production_write": False,
    }
    assert draft["kc_candidates"]["knowledge_items"]
    assert draft["parent_topics"]["groups"]
    assert "telemetry" not in draft["run_manifest"]
    assert jobs.verify_kc_run(first["job_id"])["verified"] is True


def test_draft_manifest_does_not_expose_internal_telemetry(tmp_path: Path) -> None:
    jobs = service(tmp_path)
    result = jobs.start_kc_generation(
        material_bundle=bundle_payload(), request_id="manifest-redaction"
    )
    manifest_path = (
        tmp_path / "jobs" / result["job_id"] / "output" / "run-manifest.json"
    )
    manifest = read_json(manifest_path)
    write_json(
        manifest_path,
        {
            **manifest,
            "telemetry": {
                "provider_base_url": "https://internal.example",
                "secret": "TOP_SECRET",
            },
        },
    )

    draft = jobs.get_kc_draft(result["job_id"])

    assert "telemetry" not in draft["run_manifest"]
    assert "TOP_SECRET" not in json.dumps(draft)
    assert "internal.example" not in json.dumps(draft)


def test_same_request_id_with_changed_bundle_is_rejected(tmp_path: Path) -> None:
    jobs = service(tmp_path)
    jobs.start_kc_generation(
        material_bundle=bundle_payload(), request_id="lms-request-001"
    )
    changed = bundle_payload()
    changed["lesson"] = {**changed["lesson"], "title": "Changed title"}

    with pytest.raises(JobError, match="different material bundle"):
        jobs.start_kc_generation(
            material_bundle=changed, request_id="lms-request-001"
        )


@pytest.mark.parametrize(
    "job_id",
    ["../outside", "/tmp/job", "job/child", "", "a" * 129],
)
def test_job_lookup_rejects_unsafe_identifiers(tmp_path: Path, job_id: str) -> None:
    with pytest.raises(JobError, match="invalid job_id"):
        service(tmp_path).get_kc_job_status(job_id)


def test_failed_job_exposes_sanitized_error_and_no_draft(tmp_path: Path) -> None:
    jobs = service(tmp_path, FailingRunner())
    result = jobs.start_kc_generation(
        material_bundle=bundle_payload(), request_id="failure-case"
    )

    status = jobs.get_kc_job_status(result["job_id"])
    assert status["status"] == "failed"
    assert status["error"] == {
        "code": "KC_GENERATION_FAILED",
        "message": "KC generation failed",
    }
    assert "secret" not in json.dumps(status)
    persisted = (
        tmp_path / "jobs" / result["job_id"] / "job.json"
    ).read_text(encoding="utf-8")
    assert "secret" not in persisted
    assert str(tmp_path) not in persisted
    with pytest.raises(JobError, match="not succeeded"):
        jobs.get_kc_draft(result["job_id"])


def test_invalid_bundle_and_request_id_are_rejected_before_job_creation(
    tmp_path: Path,
) -> None:
    jobs = service(tmp_path)
    invalid = bundle_payload()
    invalid["content_units"] = {
        **invalid["content_units"],
        "content_units": [],
    }

    with pytest.raises(JobError, match="invalid material bundle"):
        jobs.start_kc_generation(material_bundle=invalid, request_id="valid-id")
    with pytest.raises(JobError, match="invalid request_id"):
        jobs.start_kc_generation(
            material_bundle=bundle_payload(), request_id="../escape"
        )
    assert not (tmp_path / "jobs").exists() or not any(
        (tmp_path / "jobs").iterdir()
    )


def test_validation_error_does_not_expose_temporary_server_path(tmp_path: Path) -> None:
    invalid = bundle_payload()
    invalid["lesson"] = {**invalid["lesson"], "schema_version": "wrong"}

    with pytest.raises(JobError) as raised:
        service(tmp_path).validate_material_bundle(invalid)

    assert "/private/" not in str(raised.value)
    assert "vlearn-kc-mcp-validate-" not in str(raised.value)


def test_start_is_nonblocking_and_draft_waits_for_success(tmp_path: Path) -> None:
    runner = BlockingRecordedRunner(ROOT / "examples/day01/recorded-run")
    executor = ThreadPoolExecutor(max_workers=1)
    jobs = KCJobService(root=tmp_path / "jobs", runner=runner, executor=executor)
    try:
        started_at = time.monotonic()
        result = jobs.start_kc_generation(
            material_bundle=bundle_payload(), request_id="async-job"
        )
        elapsed = time.monotonic() - started_at

        assert elapsed < 1
        assert runner.started.wait(timeout=2)
        assert jobs.get_kc_job_status(result["job_id"])["status"] == "running"
        with pytest.raises(JobError, match="not succeeded"):
            jobs.get_kc_draft(result["job_id"])
        with pytest.raises(JobError, match="not succeeded"):
            jobs.verify_kc_run(result["job_id"])
        runner.release.set()
        for _ in range(100):
            if jobs.get_kc_job_status(result["job_id"])["status"] == "succeeded":
                break
            time.sleep(0.01)
        assert jobs.get_kc_job_status(result["job_id"])["status"] == "succeeded"
    finally:
        runner.release.set()
        executor.shutdown(wait=True)


def test_concurrent_idempotent_starts_run_provider_once(tmp_path: Path) -> None:
    runner = BlockingRecordedRunner(ROOT / "examples/day01/recorded-run")
    executor = ThreadPoolExecutor(max_workers=1)
    jobs = KCJobService(root=tmp_path / "jobs", runner=runner, executor=executor)
    results: list[dict] = []

    def start() -> None:
        results.append(
            jobs.start_kc_generation(
                material_bundle=bundle_payload(), request_id="concurrent-request"
            )
        )

    callers = [Thread(target=start), Thread(target=start)]
    try:
        for caller in callers:
            caller.start()
        for caller in callers:
            caller.join(timeout=3)
        assert len(results) == 2
        assert results[0]["job_id"] == results[1]["job_id"]
        assert sum(bool(result["idempotent_replay"]) for result in results) == 1
        assert runner.started.wait(timeout=2)
        assert runner.calls == 1
    finally:
        runner.release.set()
        executor.shutdown(wait=True)


def test_service_marks_incomplete_job_as_interrupted_after_restart(
    tmp_path: Path,
) -> None:
    first = service(tmp_path)
    result = first.start_kc_generation(
        material_bundle=bundle_payload(), request_id="restart-case"
    )
    state_path = tmp_path / "jobs" / result["job_id"] / "job.json"
    state = read_json(state_path)
    write_json(state_path, {**state, "status": "running", "stage": "kc_pipeline"})

    second = service(tmp_path)
    status = second.get_kc_job_status(result["job_id"])

    assert status["status"] == "failed"
    assert status["error"]["code"] == "KC_JOB_INTERRUPTED"


def test_owner_namespaces_isolate_jobs_in_shared_storage(tmp_path: Path) -> None:
    owner_a = service(tmp_path, owner_namespace="tenant-a")
    owner_b = service(tmp_path, owner_namespace="tenant-b")

    result_a = owner_a.start_kc_generation(
        material_bundle=bundle_payload(), request_id="same-request"
    )
    result_b = owner_b.start_kc_generation(
        material_bundle=bundle_payload(), request_id="same-request"
    )

    assert result_a["job_id"] != result_b["job_id"]
    with pytest.raises(JobError, match="job not found"):
        owner_b.get_kc_job_status(result_a["job_id"])


def test_active_job_limit_rejects_excess_provider_work(tmp_path: Path) -> None:
    runner = BlockingRecordedRunner(ROOT / "examples/day01/recorded-run")
    executor = ThreadPoolExecutor(max_workers=1)
    jobs = KCJobService(
        root=tmp_path / "jobs",
        runner=runner,
        executor=executor,
        max_active_jobs=1,
    )
    try:
        jobs.start_kc_generation(
            material_bundle=bundle_payload(), request_id="active-one"
        )
        assert runner.started.wait(timeout=2)
        with pytest.raises(JobError, match="queue is full"):
            jobs.start_kc_generation(
                material_bundle=bundle_payload(), request_id="active-two"
            )
    finally:
        runner.release.set()
        executor.shutdown(wait=True)


def test_storage_and_content_unit_limits_are_enforced(tmp_path: Path) -> None:
    storage_limited = service(tmp_path, max_active_jobs=1, max_stored_jobs=1)
    storage_limited.start_kc_generation(
        material_bundle=bundle_payload(), request_id="stored-one"
    )
    with pytest.raises(JobError, match="storage limit"):
        storage_limited.start_kc_generation(
            material_bundle=bundle_payload(), request_id="stored-two"
        )

    unit_limited = service(tmp_path / "units", max_content_units=100)
    with pytest.raises(JobError, match="content unit limit"):
        unit_limited.start_kc_generation(
            material_bundle=bundle_payload(), request_id="too-many-units"
        )
