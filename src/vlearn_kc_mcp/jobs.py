from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from threading import Lock
from typing import Any, Callable, Protocol

from vlearn_kc.contracts import ContractError, load_material_bundle
from vlearn_kc.io import read_json, write_json
from vlearn_kc.replay import replay_run


REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
OWNER_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
JOB_ID_RE = re.compile(r"^kc-[0-9a-f]{32}$")
MAX_BUNDLE_BYTES = 25 * 1024 * 1024
EXPECTED_BUNDLE_KEYS = {"lesson", "sources", "content_units"}
PUBLIC_MANIFEST_KEYS = {
    "schema_version",
    "source_slug",
    "material_bundle_sha256",
    "prompt_sha256",
    "artifact_sha256",
    "counts",
    "knowledge_roles",
    "release",
}


class JobError(ValueError):
    """A safe, client-facing MCP job error."""


class KCRunner(Protocol):
    def run(self, *, input_dir: Path, output_dir: Path) -> None: ...


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _validate_payload_shape(material_bundle: dict[str, Any]) -> None:
    if set(material_bundle) != EXPECTED_BUNDLE_KEYS:
        raise JobError(
            "invalid material bundle: expected lesson, sources, and content_units"
        )
    if any(not isinstance(material_bundle[key], dict) for key in EXPECTED_BUNDLE_KEYS):
        raise JobError("invalid material bundle: each bundle member must be an object")
    try:
        encoded = json.dumps(
            material_bundle,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise JobError("invalid material bundle: payload must be finite JSON") from None
    if len(encoded) > MAX_BUNDLE_BYTES:
        raise JobError("invalid material bundle: payload exceeds the 25 MB limit")


def _write_bundle(root: Path, material_bundle: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for key in sorted(EXPECTED_BUNDLE_KEYS):
        write_json(root / f"{key}.json", material_bundle[key])


def _validate_inline_bundle(material_bundle: dict[str, Any]) -> dict[str, Any]:
    _validate_payload_shape(material_bundle)
    try:
        with tempfile.TemporaryDirectory(prefix="vlearn-kc-mcp-validate-") as temporary:
            root = Path(temporary) / "material-bundle"
            _write_bundle(root, material_bundle)
            bundle = load_material_bundle(root)
    except (ContractError, TypeError, ValueError) as error:
        message = str(error).replace(str(root), "<material-bundle>")
        raise JobError(f"invalid material bundle: {message}") from None
    except OSError:
        raise JobError("invalid material bundle: bundle could not be read") from None
    return {
        "schema_version": "vlearn_material_validation_v1",
        "valid": True,
        "verified": True,
        "source_slug": bundle.source_slug,
        "lesson_id": bundle.lesson_id,
        "sources": len(bundle.sources),
        "content_units": len(bundle.content_units),
        "bundle_sha256": bundle.bundle_sha256,
    }


def _public_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: manifest[key] for key in PUBLIC_MANIFEST_KEYS if key in manifest}


class KCJobService:
    def __init__(
        self,
        *,
        root: Path | str,
        runner: KCRunner,
        executor: Executor | None = None,
        max_workers: int = 2,
        owner_namespace: str = "local",
        max_active_jobs: int = 4,
        max_stored_jobs: int = 200,
        max_content_units: int = 5_000,
        verifier: Callable[..., dict[str, Any]] = replay_run,
    ) -> None:
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError("jobs root must not be a symbolic link")
        if not OWNER_NAMESPACE_RE.fullmatch(owner_namespace):
            raise ValueError("invalid owner namespace")
        for name, value in {
            "max_active_jobs": max_active_jobs,
            "max_stored_jobs": max_stored_jobs,
            "max_content_units": max_content_units,
        }.items():
            if value < 1:
                raise ValueError(f"{name} must be positive")
        if max_active_jobs > max_stored_jobs:
            raise ValueError("max_active_jobs must not exceed max_stored_jobs")
        self.owner_hash = hashlib.sha256(owner_namespace.encode("utf-8")).hexdigest()
        self.max_active_jobs = max_active_jobs
        self.max_stored_jobs = max_stored_jobs
        self.max_content_units = max_content_units
        self.runner = runner
        self.executor = executor or ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="vlearn-kc",
        )
        self._owns_executor = executor is None
        self.verifier = verifier
        self._lock = Lock()
        self._recover_interrupted_jobs()

    def _recover_interrupted_jobs(self) -> None:
        if not self.root.is_dir():
            return
        for job_dir in sorted(self.root.iterdir()):
            if (
                job_dir.is_symlink()
                or not job_dir.is_dir()
                or not JOB_ID_RE.fullmatch(job_dir.name)
            ):
                continue
            state_path = job_dir / "job.json"
            if state_path.is_symlink() or not state_path.is_file():
                continue
            try:
                state = read_json(state_path)
            except (OSError, TypeError, ValueError):
                continue
            if (
                state.get("owner_hash") != self.owner_hash
                or state.get("status") not in {"queued", "running"}
            ):
                continue
            _atomic_write_json(
                state_path,
                {
                    **state,
                    "status": "failed",
                    "stage": "failed",
                    "error": {
                        "code": "KC_JOB_INTERRUPTED",
                        "message": "KC job was interrupted by server restart",
                    },
                    "updated_at": _utc_now(),
                },
            )

    def close(self) -> None:
        if self._owns_executor:
            self.executor.shutdown(wait=False, cancel_futures=False)

    def validate_material_bundle(
        self, material_bundle: dict[str, Any]
    ) -> dict[str, Any]:
        return _validate_inline_bundle(material_bundle)

    @staticmethod
    def _validate_request_id(request_id: str) -> str:
        value = str(request_id or "")
        if not REQUEST_ID_RE.fullmatch(value):
            raise JobError("invalid request_id")
        return value

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        value = str(job_id or "")
        if not JOB_ID_RE.fullmatch(value):
            raise JobError("invalid job_id")
        return value

    def _job_id(self, request_id: str) -> str:
        digest = hashlib.sha256(
            f"{self.owner_hash}\0{request_id}".encode("utf-8")
        ).hexdigest()
        return f"kc-{digest[:32]}"

    def _job_dir(self, job_id: str) -> Path:
        path = self.root / self._validate_job_id(job_id)
        if path.is_symlink():
            raise JobError("job not found")
        return path

    def _read_state(self, job_id: str) -> dict[str, Any]:
        path = self._job_dir(job_id) / "job.json"
        if path.is_symlink() or not path.is_file():
            raise JobError("job not found")
        try:
            state = read_json(path)
        except (OSError, TypeError, ValueError):
            raise JobError("job state is unavailable") from None
        if state.get("owner_hash") != self.owner_hash:
            raise JobError("job not found")
        return state

    def _write_state(self, job_id: str, state: dict[str, Any]) -> None:
        _atomic_write_json(self._job_dir(job_id) / "job.json", state)

    def _owned_states(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        states: list[dict[str, Any]] = []
        for job_dir in self.root.iterdir():
            if (
                job_dir.is_symlink()
                or not job_dir.is_dir()
                or not JOB_ID_RE.fullmatch(job_dir.name)
            ):
                continue
            state_path = job_dir / "job.json"
            if state_path.is_symlink() or not state_path.is_file():
                continue
            try:
                state = read_json(state_path)
            except (OSError, TypeError, ValueError):
                continue
            if state.get("owner_hash") == self.owner_hash:
                states.append(state)
        return states

    @staticmethod
    def _public_state(state: dict[str, Any]) -> dict[str, Any]:
        result = {
            "schema_version": "vlearn_kc_job_status_v1",
            "job_id": state["job_id"],
            "status": state["status"],
            "stage": state["stage"],
            "bundle_sha256": state["bundle_sha256"],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"],
        }
        if state.get("error"):
            result["error"] = state["error"]
        if state.get("counts"):
            result["counts"] = state["counts"]
        return result

    def start_kc_generation(
        self, *, material_bundle: dict[str, Any], request_id: str
    ) -> dict[str, Any]:
        request_id = self._validate_request_id(request_id)
        validation = _validate_inline_bundle(material_bundle)
        if validation["content_units"] > self.max_content_units:
            raise JobError("material bundle exceeds the content unit limit")
        job_id = self._job_id(request_id)
        should_submit = False
        with self._lock:
            job_dir = self._job_dir(job_id)
            state_path = job_dir / "job.json"
            if state_path.is_file():
                state = self._read_state(job_id)
                if state.get("bundle_sha256") != validation["bundle_sha256"]:
                    raise JobError(
                        "request_id is already associated with a different material bundle"
                    )
                return {
                    "schema_version": "vlearn_kc_job_start_v1",
                    "job_id": job_id,
                    "status": state["status"],
                    "idempotent_replay": True,
                }
            if job_dir.exists():
                raise JobError("job state is unavailable")
            owned_states = self._owned_states()
            if len(owned_states) >= self.max_stored_jobs:
                raise JobError("job storage limit reached")
            active_jobs = sum(
                state.get("status") in {"queued", "running"}
                for state in owned_states
            )
            if active_jobs >= self.max_active_jobs:
                raise JobError("job queue is full")
            job_dir.mkdir(parents=True, exist_ok=False)
            _write_bundle(job_dir / "input", material_bundle)
            now = _utc_now()
            state = {
                "schema_version": "vlearn_kc_job_v1",
                "job_id": job_id,
                "request_id": request_id,
                "owner_hash": self.owner_hash,
                "bundle_sha256": validation["bundle_sha256"],
                "status": "queued",
                "stage": "queued",
                "created_at": now,
                "updated_at": now,
                "error": None,
            }
            self._write_state(job_id, state)
            should_submit = True
        if should_submit:
            try:
                self.executor.submit(self._run_job, job_id)
            except Exception:
                with self._lock:
                    state = self._read_state(job_id)
                    self._write_state(
                        job_id,
                        {
                            **state,
                            "status": "failed",
                            "stage": "failed",
                            "error": {
                                "code": "KC_JOB_SUBMISSION_FAILED",
                                "message": "KC job could not be queued",
                            },
                            "updated_at": _utc_now(),
                        },
                    )
                raise JobError("KC job could not be queued") from None
        return {
            "schema_version": "vlearn_kc_job_start_v1",
            "job_id": job_id,
            "status": "queued",
            "idempotent_replay": False,
        }

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            state = self._read_state(job_id)
            state = {
                **state,
                "status": "running",
                "stage": "kc_pipeline",
                "updated_at": _utc_now(),
            }
            self._write_state(job_id, state)
        job_dir = self._job_dir(job_id)
        try:
            self.runner.run(
                input_dir=job_dir / "input",
                output_dir=job_dir / "output",
            )
            manifest = read_json(job_dir / "output" / "run-manifest.json")
            release = manifest.get("release") or {}
            if release != {"auto_publish": False, "production_write": False}:
                raise ValueError("run manifest does not enforce draft-only release")
            with self._lock:
                state = self._read_state(job_id)
                self._write_state(
                    job_id,
                    {
                        **state,
                        "status": "succeeded",
                        "stage": "complete",
                        "counts": manifest.get("counts") or {},
                        "updated_at": _utc_now(),
                    },
                )
        except Exception:  # Provider and artifact errors are intentionally sanitized.
            with self._lock:
                state = self._read_state(job_id)
                self._write_state(
                    job_id,
                    {
                        **state,
                        "status": "failed",
                        "stage": "failed",
                        "error": {
                            "code": "KC_GENERATION_FAILED",
                            "message": "KC generation failed",
                        },
                        "updated_at": _utc_now(),
                    },
                )

    def get_kc_job_status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            return self._public_state(self._read_state(job_id))

    def _require_succeeded(self, job_id: str) -> tuple[dict[str, Any], Path]:
        state = self._read_state(job_id)
        if state.get("status") != "succeeded":
            raise JobError("job is not succeeded")
        return state, self._job_dir(job_id)

    def get_kc_draft(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            state, job_dir = self._require_succeeded(job_id)
            try:
                inventory_path = job_dir / "output" / "kc-candidates.json"
                topics_path = job_dir / "output" / "parent-topics.json"
                manifest_path = job_dir / "output" / "run-manifest.json"
                if any(
                    path.is_symlink()
                    for path in (inventory_path, topics_path, manifest_path)
                ):
                    raise OSError("symbolic-link artifact")
                inventory = read_json(inventory_path)
                topics = read_json(topics_path)
                manifest = read_json(manifest_path)
            except (OSError, TypeError, ValueError):
                raise JobError("job artifacts are unavailable") from None
        release = manifest.get("release") or {}
        if release != {"auto_publish": False, "production_write": False}:
            raise JobError("job is not a draft-only run")
        return {
            "schema_version": "vlearn_kc_draft_v1",
            "job_id": state["job_id"],
            "status": "draft",
            "release": release,
            "kc_candidates": inventory,
            "parent_topics": topics,
            "run_manifest": _public_manifest(manifest),
        }

    def verify_kc_run(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            _, job_dir = self._require_succeeded(job_id)
        try:
            return self.verifier(
                input_dir=job_dir / "input",
                recorded_dir=job_dir / "output",
            )
        except (OSError, TypeError, ValueError):
            raise JobError("KC run verification failed") from None
