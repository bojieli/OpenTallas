"""Governed checkpoint/restart differential for the Qwen long campaign."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from compiler.tensor_accelerator.qwen_full_model_long_acceptance import (
    RUNNER_VERSION,
    build_long_acceptance_request,
    validate_long_acceptance_request,
    validate_long_acceptance_session,
    validate_long_acceptance_transaction_report,
)
from .qwen_full_model_checkpoint import (
    MANIFEST_NAME,
    load_runtime_checkpoint,
    validate_checkpoint_predecessor,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_restart_differential.v1"
VERSION = "tensor-accelerator-qwen-full-model-restart-differential-0.1.0"
RUNNER_PATH = "tools/run_qwen3_tensor_accelerator_long_acceptance.py"
STATE_COUNT = 36
EVIDENCE_FILES = (
    "checkpoint.0001/checkpoint_manifest.json",
    "checkpoint.0001/state/hbm.00000.fd6c50ddbe171c9242f995e3df1bebc3bbafe13321ccf5aef4060e376f4d6218.bin",
    "checkpoint.0002/checkpoint_manifest.json",
    "checkpoint.0002/state/hbm.00000.3a323f2f4465b4e2ca3e4d8cb006166145e84ee8a1c55cc39e99040f9351b584.bin",
    "executions/execution.0000.json",
    "executions/execution.0001.json",
    "requests/request.0000.json",
    "requests/request.0001.json",
)


class QwenRestartDifferentialError(ArtifactError):
    """Raised when restart evidence is incomplete, corrupt, or non-equivalent."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenRestartDifferentialError(f"{label} identity differs")


def _canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenRestartDifferentialError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenRestartDifferentialError(f"{label} is not canonical JSON")
    return value, payload


def _bindings(session: Mapping[str, Any]) -> dict[str, str]:
    return {
        field: str(session[field])
        for field in (
            "build_id",
            "capability_id",
            "checkpoint_lock_id",
            "command_program_sha256",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "physical_plan_id",
            "session_id",
        )
    }


def _assert_regular_tree(root: Path, expected: set[str], label: str) -> None:
    if root.is_symlink() or not root.is_dir():
        raise QwenRestartDifferentialError(f"{label} must be a regular directory")
    observed: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise QwenRestartDifferentialError(f"{label} contains a symbolic link")
        if path.is_file():
            observed.add(relative)
        elif not path.is_dir():
            raise QwenRestartDifferentialError(f"{label} contains a special file")
    if observed != expected:
        raise QwenRestartDifferentialError(f"{label} file inventory differs")


def _campaign_files(*, checkpoint_steps: tuple[int, ...]) -> set[str]:
    result = {
        *(f"requests/request.{step:04d}.json" for step in range(2)),
        *(f"executions/execution.{step:04d}.json" for step in range(2)),
    }
    for step in checkpoint_steps:
        result.add(f"checkpoints/checkpoint.{step:04d}/{MANIFEST_NAME}")
        checkpoint_size = 147_456 * step
        digest = {
            1: "fd6c50ddbe171c9242f995e3df1bebc3bbafe13321ccf5aef4060e376f4d6218",
            2: "3a323f2f4465b4e2ca3e4d8cb006166145e84ee8a1c55cc39e99040f9351b584",
        }[step]
        result.add(
            f"checkpoints/checkpoint.{step:04d}/state/"
            f"hbm.00000.{digest}.bin"
        )
        if checkpoint_size not in {147_456, 294_912}:
            raise AssertionError("unexpected two-step checkpoint size")
    return result


def _load_campaign(
    root: Path,
    session: Mapping[str, Any],
    *,
    checkpoint_steps: tuple[int, ...],
    label: str,
) -> dict[str, Any]:
    campaign = Path(root).resolve(strict=True)
    _assert_regular_tree(campaign, _campaign_files(checkpoint_steps=checkpoint_steps), label)
    requests: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    request_payloads: list[bytes] = []
    report_payloads: list[bytes] = []
    previous: dict[str, Any] | None = None
    for step in range(2):
        request, request_payload = _canonical(
            campaign / f"requests/request.{step:04d}.json",
            f"{label} request {step}",
        )
        report, report_payload = _canonical(
            campaign / f"executions/execution.{step:04d}.json",
            f"{label} execution {step}",
        )
        expected_request = build_long_acceptance_request(session, previous)
        if request != expected_request:
            raise QwenRestartDifferentialError(f"{label} request {step} differs")
        validate_long_acceptance_request(request, session, previous)
        validate_long_acceptance_transaction_report(report, session, request, previous)
        requests.append(request)
        reports.append(report)
        request_payloads.append(request_payload)
        report_payloads.append(report_payload)
        previous = report

    manifests: dict[int, dict[str, Any]] = {}
    for step in checkpoint_steps:
        checkpoint = campaign / f"checkpoints/checkpoint.{step:04d}"
        manifest, states = load_runtime_checkpoint(
            checkpoint, expected_bindings=_bindings(session)
        )
        if set(states) != {f"kv.layer.{layer}" for layer in range(STATE_COUNT)}:
            raise QwenRestartDifferentialError(
                f"{label} checkpoint {step} state coverage differs"
            )
        validate_checkpoint_predecessor(manifest, reports[step - 1])
        manifests[step] = manifest
    return {
        "root": campaign,
        "requests": requests,
        "reports": reports,
        "request_payloads": request_payloads,
        "report_payloads": report_payloads,
        "manifests": manifests,
    }


def _checkpoint_payloads(root: Path, step: int) -> dict[str, bytes]:
    checkpoint = root / f"checkpoints/checkpoint.{step:04d}"
    return {
        path.relative_to(checkpoint).as_posix(): path.read_bytes()
        for path in checkpoint.rglob("*")
        if path.is_file()
    }


def _inventory(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    roles = {
        "checkpoint.0001": "restart_checkpoint",
        "checkpoint.0002": "post_restart_checkpoint",
        "executions": "transaction_execution",
        "requests": "transaction_request",
    }
    for relative in EVIDENCE_FILES:
        digest, size = sha256_file(root / relative)
        records.append(
            {
                "path": relative,
                "role": roles[relative.split("/", 1)[0]],
                "sha256": digest,
                "size_bytes": size,
            }
        )
    return records


def validate_restart_differential(
    value: Mapping[str, Any],
    *,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the exact two-transaction interrupted/restarted differential."""

    report = dict(value)
    exact_keys(
        report,
        {
            "artifact_inventory",
            "build_id",
            "campaign_protocol",
            "checkpoint_restore",
            "claim_boundary",
            "command_program_sha256",
            "comparison",
            "differential_id",
            "differential_version",
            "final_checkpoint",
            "graph_id",
            "runner",
            "schema",
            "session_id",
            "status",
            "transactions",
        },
        set(),
        "Qwen restart differential",
    )
    _identity(report, "differential_id", "Qwen restart differential")
    for field in (
        "build_id",
        "command_program_sha256",
        "graph_id",
        "session_id",
    ):
        require_sha256(report[field], f"Qwen restart differential.{field}")
    if (
        report["schema"] != SCHEMA
        or report["differential_version"] != VERSION
        or report["status"] != "byte_exact_restart_equivalence"
        or report["claim_boundary"]
        != {
            "exact_8000_token_acceptance": False,
            "independent_reference_verified": False,
            "restart_after_one_transaction_verified": True,
            "timing_or_performance": False,
            "two_full_model_transactions_verified": True,
        }
        or report["campaign_protocol"]
        != {
            "interrupted_then_restored": {
                "checkpoint_interval": 1,
                "invocation_transaction_counts": [1, 1],
                "restore_step": 1,
            },
            "uninterrupted": {
                "checkpoint_interval": 2,
                "invocation_transaction_counts": [2],
            },
        }
        or report["comparison"]
        != {
            "all_36_kv_resources_restored": True,
            "all_checkpoint_bytes_authenticated": True,
            "command_counters_byte_equal": True,
            "final_checkpoint_tree_byte_equal": True,
            "greedy_tokens_equal": True,
            "logit_records_byte_equal": True,
            "request_files_byte_equal": True,
            "runtime_bindings_byte_equal": True,
            "state_records_byte_equal": True,
            "transaction_reports_byte_equal": True,
        }
    ):
        raise QwenRestartDifferentialError("Qwen restart differential boundary differs")

    runner = report["runner"]
    if not isinstance(runner, dict) or runner != {
        "path": RUNNER_PATH,
        "runner_version": RUNNER_VERSION,
        "sha256": runner.get("sha256"),
        "size_bytes": runner.get("size_bytes"),
    }:
        raise QwenRestartDifferentialError("Qwen restart runner record differs")
    require_sha256(runner["sha256"], "Qwen restart runner SHA-256")
    if not isinstance(runner["size_bytes"], int) or runner["size_bytes"] < 1:
        raise QwenRestartDifferentialError("Qwen restart runner size differs")

    transactions = report["transactions"]
    if not isinstance(transactions, list) or len(transactions) != 2:
        raise QwenRestartDifferentialError("Qwen restart transaction coverage differs")
    previous_report: str | None = None
    for step, transaction in enumerate(transactions):
        if not isinstance(transaction, dict):
            raise QwenRestartDifferentialError("Qwen restart transaction must be an object")
        exact_keys(
            transaction,
            {
                "greedy_token_id",
                "logits_sha256",
                "previous_report_id",
                "report_id",
                "report_sha256",
                "report_size_bytes",
                "request_id",
                "request_sha256",
                "request_size_bytes",
                "state_generation",
                "state_length",
                "step_index",
            },
            set(),
            f"Qwen restart transaction {step}",
        )
        for field in (
            "logits_sha256",
            "report_id",
            "report_sha256",
            "request_id",
            "request_sha256",
        ):
            require_sha256(transaction[field], f"restart transaction {step}.{field}")
        if (
            transaction["step_index"] != step
            or transaction["previous_report_id"] != previous_report
            or transaction["greedy_token_id"] != 33_975
            or transaction["state_generation"] != step + 1
            or transaction["state_length"] != step + 1
            or not isinstance(transaction["request_size_bytes"], int)
            or transaction["request_size_bytes"] < 1
            or not isinstance(transaction["report_size_bytes"], int)
            or transaction["report_size_bytes"] < 1
        ):
            raise QwenRestartDifferentialError("Qwen restart transaction chain differs")
        previous_report = transaction["report_id"]

    for name, step in (("checkpoint_restore", 1), ("final_checkpoint", 2)):
        record = report[name]
        if not isinstance(record, dict):
            raise QwenRestartDifferentialError(f"Qwen restart {name} must be an object")
        exact_keys(
            record,
            {
                "checkpoint_id",
                "logical_state_sha256",
                "manifest_sha256",
                "manifest_size_bytes",
                "next_step_index",
                "state_image_size_bytes",
            },
            set(),
            f"Qwen restart {name}",
        )
        for field in ("checkpoint_id", "logical_state_sha256", "manifest_sha256"):
            require_sha256(record[field], f"Qwen restart {name}.{field}")
        if (
            record["next_step_index"] != step
            or record["state_image_size_bytes"] != 147_456 * step
            or not isinstance(record["manifest_size_bytes"], int)
            or record["manifest_size_bytes"] < 1
        ):
            raise QwenRestartDifferentialError(f"Qwen restart {name} geometry differs")

    inventory = report["artifact_inventory"]
    if not isinstance(inventory, list) or len(inventory) != len(EVIDENCE_FILES):
        raise QwenRestartDifferentialError("Qwen restart inventory coverage differs")
    previous_path = ""
    for expected_path, record in zip(EVIDENCE_FILES, inventory, strict=True):
        if not isinstance(record, dict):
            raise QwenRestartDifferentialError("Qwen restart inventory record differs")
        exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            set(),
            "Qwen restart inventory record",
        )
        require_sha256(record["sha256"], "Qwen restart inventory SHA-256")
        if (
            record["path"] != expected_path
            or record["path"] <= previous_path
            or record["role"]
            not in {
                "post_restart_checkpoint",
                "restart_checkpoint",
                "transaction_execution",
                "transaction_request",
            }
            or not isinstance(record["size_bytes"], int)
            or record["size_bytes"] < 1
        ):
            raise QwenRestartDifferentialError("Qwen restart inventory ordering differs")
        previous_path = record["path"]
    if evidence_root is not None:
        root = Path(evidence_root)
        expected = set(EVIDENCE_FILES) | {"restart_differential.json"}
        _assert_regular_tree(root, expected, "retained Qwen restart evidence")
        if inventory != _inventory(root):
            raise QwenRestartDifferentialError("retained restart evidence differs")
        runner_digest, runner_size = sha256_file(root.parents[2] / RUNNER_PATH)
        if (runner_digest, runner_size) != (runner["sha256"], runner["size_bytes"]):
            raise QwenRestartDifferentialError("retained restart runner differs")
    return report


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise QwenRestartDifferentialError(f"unsafe restart evidence source: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_handle, destination.open("xb") as output_handle:
        shutil.copyfileobj(source_handle, output_handle, length=8 * 1024 * 1024)
        output_handle.flush()
        os.fsync(output_handle.fileno())


def publish_restart_differential(
    *,
    session_path: Path,
    interrupted_root: Path,
    uninterrupted_root: Path,
    repository_root: Path,
    output: Path,
) -> dict[str, Any]:
    """Authenticate, compare, and atomically retain one restart differential."""

    session, _ = _canonical(session_path, "Qwen long acceptance session")
    session = validate_long_acceptance_session(session)
    interrupted = _load_campaign(
        interrupted_root,
        session,
        checkpoint_steps=(1, 2),
        label="interrupted/restored campaign",
    )
    uninterrupted = _load_campaign(
        uninterrupted_root,
        session,
        checkpoint_steps=(2,),
        label="uninterrupted campaign",
    )
    if (
        interrupted["request_payloads"] != uninterrupted["request_payloads"]
        or interrupted["report_payloads"] != uninterrupted["report_payloads"]
        or _checkpoint_payloads(interrupted["root"], 2)
        != _checkpoint_payloads(uninterrupted["root"], 2)
    ):
        raise QwenRestartDifferentialError(
            "interrupted and uninterrupted campaign bytes differ"
        )

    destination = Path(output).resolve()
    if destination.exists() or destination.is_symlink():
        raise QwenRestartDifferentialError(
            f"restart differential output already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent)
    )
    try:
        source = interrupted["root"]
        source_map = {
            "checkpoint.0001": source / "checkpoints/checkpoint.0001",
            "checkpoint.0002": source / "checkpoints/checkpoint.0002",
            "executions": source / "executions",
            "requests": source / "requests",
        }
        for relative in EVIDENCE_FILES:
            prefix, suffix = relative.split("/", 1)
            _copy_file(source_map[prefix] / suffix, temporary / relative)

        runner_path = Path(repository_root).resolve(strict=True) / RUNNER_PATH
        runner_sha256, runner_size = sha256_file(runner_path)
        transactions: list[dict[str, Any]] = []
        for step, (request, report, request_payload, report_payload) in enumerate(
            zip(
                interrupted["requests"],
                interrupted["reports"],
                interrupted["request_payloads"],
                interrupted["report_payloads"],
                strict=True,
            )
        ):
            transactions.append(
                {
                    "greedy_token_id": report["outputs"]["committed_logits"][
                        "greedy_token_id"
                    ],
                    "logits_sha256": report["outputs"]["committed_logits"][
                        "payload_sha256"
                    ],
                    "previous_report_id": report["previous_report_id"],
                    "report_id": report["report_id"],
                    "report_sha256": hashlib.sha256(report_payload).hexdigest(),
                    "report_size_bytes": len(report_payload),
                    "request_id": request["request_id"],
                    "request_sha256": hashlib.sha256(request_payload).hexdigest(),
                    "request_size_bytes": len(request_payload),
                    "state_generation": report["state"][0]["generation"],
                    "state_length": report["state"][0]["length"],
                    "step_index": step,
                }
            )

        checkpoint_one = interrupted["manifests"][1]
        checkpoint_two = interrupted["manifests"][2]
        body: dict[str, Any] = {
            "artifact_inventory": _inventory(temporary),
            "build_id": session["build_id"],
            "campaign_protocol": {
                "interrupted_then_restored": {
                    "checkpoint_interval": 1,
                    "invocation_transaction_counts": [1, 1],
                    "restore_step": 1,
                },
                "uninterrupted": {
                    "checkpoint_interval": 2,
                    "invocation_transaction_counts": [2],
                },
            },
            "checkpoint_restore": {
                "checkpoint_id": checkpoint_one["checkpoint_id"],
                "logical_state_sha256": checkpoint_one["state_image"][
                    "logical_sha256"
                ],
                "manifest_sha256": sha256_file(
                    temporary / "checkpoint.0001/checkpoint_manifest.json"
                )[0],
                "manifest_size_bytes": sha256_file(
                    temporary / "checkpoint.0001/checkpoint_manifest.json"
                )[1],
                "next_step_index": 1,
                "state_image_size_bytes": checkpoint_one["state_image"]["size_bytes"],
            },
            "claim_boundary": {
                "exact_8000_token_acceptance": False,
                "independent_reference_verified": False,
                "restart_after_one_transaction_verified": True,
                "timing_or_performance": False,
                "two_full_model_transactions_verified": True,
            },
            "command_program_sha256": session["command_program_sha256"],
            "comparison": {
                "all_36_kv_resources_restored": True,
                "all_checkpoint_bytes_authenticated": True,
                "command_counters_byte_equal": True,
                "final_checkpoint_tree_byte_equal": True,
                "greedy_tokens_equal": True,
                "logit_records_byte_equal": True,
                "request_files_byte_equal": True,
                "runtime_bindings_byte_equal": True,
                "state_records_byte_equal": True,
                "transaction_reports_byte_equal": True,
            },
            "differential_version": VERSION,
            "final_checkpoint": {
                "checkpoint_id": checkpoint_two["checkpoint_id"],
                "logical_state_sha256": checkpoint_two["state_image"][
                    "logical_sha256"
                ],
                "manifest_sha256": sha256_file(
                    temporary / "checkpoint.0002/checkpoint_manifest.json"
                )[0],
                "manifest_size_bytes": sha256_file(
                    temporary / "checkpoint.0002/checkpoint_manifest.json"
                )[1],
                "next_step_index": 2,
                "state_image_size_bytes": checkpoint_two["state_image"]["size_bytes"],
            },
            "graph_id": session["graph_id"],
            "runner": {
                "path": RUNNER_PATH,
                "runner_version": RUNNER_VERSION,
                "sha256": runner_sha256,
                "size_bytes": runner_size,
            },
            "schema": SCHEMA,
            "session_id": session["session_id"],
            "status": "byte_exact_restart_equivalence",
            "transactions": transactions,
        }
        report = validate_restart_differential(
            _identified(body, "differential_id")
        )
        report_path = temporary / "restart_differential.json"
        with report_path.open("xb") as handle:
            handle.write(canonical_json_bytes(report))
            handle.flush()
            os.fsync(handle.fileno())
        for directory in sorted(
            (path for path in temporary.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            _fsync_directory(directory)
        _fsync_directory(temporary)
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
        validate_restart_differential(
            _canonical(destination / "restart_differential.json", "restart report")[0],
            evidence_root=destination,
        )
        return report
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "QwenRestartDifferentialError",
    "SCHEMA",
    "VERSION",
    "publish_restart_differential",
    "validate_restart_differential",
]
