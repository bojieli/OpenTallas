"""Authenticated, atomic checkpoints for long Qwen simulator sessions."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any

import numpy as np

from compiler.tensor_accelerator.common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.hbm_shards import (
    HBMShardError,
    HBMShardReader,
    HBMShardWriter,
)

from .attention import (
    HEAD_DIM,
    KEY_VALUE_HEADS,
    KVSnapshot,
    make_kv_snapshot,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_runtime_checkpoint.v1"
VERSION = "tensor-accelerator-qwen-full-model-runtime-checkpoint-0.1.0"
SIMULATOR_VERSION = "tensor-accelerator-qwen-full-model-simulator-0.1.0"
MANIFEST_NAME = "checkpoint_manifest.json"
STATE_COUNT = 36
CONTEXT_CAPACITY = 8_192
MAX_NEXT_STEP = 8_031
BF16_BYTES = 2
TOKEN_PLANE_BYTES = KEY_VALUE_HEADS * HEAD_DIM * BF16_BYTES
DEFAULT_SHARD_BYTES = 256 * 1024 * 1024


class QwenFullModelCheckpointError(ArtifactError):
    """Raised when a runtime checkpoint is incomplete, corrupt, or mismatched."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    body = {key: item for key, item in value.items() if key != field}
    if observed != sha256_bytes(canonical_json_bytes(body)):
        raise QwenFullModelCheckpointError(f"{label} identity differs")


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise QwenFullModelCheckpointError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise QwenFullModelCheckpointError(
            f"{label} must be a safe relative POSIX path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise QwenFullModelCheckpointError(
            f"{label} must be a safe relative POSIX path"
        )
    return value


def _canonical_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelCheckpointError(
            f"cannot load runtime checkpoint manifest: {exc}"
        ) from exc
    if canonical_json_bytes(value) != payload:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint manifest is not canonical JSON"
        )
    return value


def _plane_payload(
    values: np.ndarray[Any, np.dtype[np.uint16]],
) -> memoryview:
    raw = np.asarray(values)
    if (
        raw.dtype != np.dtype(np.uint16)
        or raw.ndim != 3
        or raw.shape[1:] != (KEY_VALUE_HEADS, HEAD_DIM)
        or not raw.flags.c_contiguous
    ):
        raise QwenFullModelCheckpointError(
            "checkpoint KV plane must be contiguous native uint16 [tokens,8,128]"
        )
    little = np.ascontiguousarray(raw, dtype="<u2")
    return memoryview(little).cast("B")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_checkpoint_manifest(
    value: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Validate manifest structure and optional deployment/session bindings."""

    manifest = dict(value)
    exact_keys(
        manifest,
        {
            "build_id",
            "capability_id",
            "checkpoint_id",
            "checkpoint_lock_id",
            "checkpoint_version",
            "claim_boundary",
            "command_program_sha256",
            "context_capacity",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "next_step_index",
            "physical_plan_id",
            "previous_greedy_token_id",
            "previous_report_id",
            "schema",
            "session_id",
            "simulator_version",
            "state_count",
            "state_image",
            "states",
        },
        set(),
        "runtime checkpoint manifest",
    )
    _identity(manifest, "checkpoint_id", "runtime checkpoint manifest")
    for field in (
        "build_id",
        "capability_id",
        "checkpoint_lock_id",
        "command_program_sha256",
        "graph_id",
        "hbm_logical_sha256",
        "kernel_ir_id",
        "physical_plan_id",
        "previous_report_id",
        "session_id",
    ):
        require_sha256(manifest[field], f"runtime checkpoint.{field}")
    next_step = _integer(
        manifest["next_step_index"],
        "runtime checkpoint.next_step_index",
        1,
        MAX_NEXT_STEP,
    )
    _integer(
        manifest["previous_greedy_token_id"],
        "runtime checkpoint.previous_greedy_token_id",
        0,
        151_935,
    )
    if (
        manifest["schema"] != SCHEMA
        or manifest["checkpoint_version"] != VERSION
        or manifest["simulator_version"] != SIMULATOR_VERSION
        or manifest["context_capacity"] != CONTEXT_CAPACITY
        or manifest["state_count"] != STATE_COUNT
        or manifest["claim_boundary"]
        != {
            "acceptance_execution_complete": False,
            "restart_state_only": True,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
        }
    ):
        raise QwenFullModelCheckpointError("runtime checkpoint boundary differs")
    if expected_bindings is not None:
        required = {
            "build_id",
            "capability_id",
            "checkpoint_lock_id",
            "command_program_sha256",
            "graph_id",
            "hbm_logical_sha256",
            "kernel_ir_id",
            "physical_plan_id",
            "session_id",
        }
        if set(expected_bindings) != required or any(
            manifest[field] != expected_bindings[field] for field in required
        ):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint deployment or session binding differs"
            )

    states = manifest["states"]
    if not isinstance(states, list) or len(states) != STATE_COUNT:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint state coverage differs"
        )
    cursor = 0
    plane_size = next_step * TOKEN_PLANE_BYTES
    for layer, state in enumerate(states):
        if not isinstance(state, dict):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint state record must be an object"
            )
        exact_keys(
            state,
            {
                "capacity",
                "generation",
                "key",
                "layer",
                "length",
                "resource_id",
                "value",
            },
            set(),
            f"runtime checkpoint state[{layer}]",
        )
        if (
            state["layer"] != layer
            or state["resource_id"] != f"kv.layer.{layer}"
            or state["generation"] != next_step
            or state["length"] != next_step
            or state["capacity"] != CONTEXT_CAPACITY
        ):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint state ordering or metadata differs"
            )
        for plane_name in ("key", "value"):
            plane = state[plane_name]
            if not isinstance(plane, dict):
                raise QwenFullModelCheckpointError(
                    "runtime checkpoint plane record must be an object"
                )
            exact_keys(
                plane,
                {"logical_offset", "sha256", "size_bytes"},
                set(),
                f"runtime checkpoint state[{layer}].{plane_name}",
            )
            require_sha256(
                plane["sha256"],
                f"runtime checkpoint state[{layer}].{plane_name}.sha256",
            )
            if plane != {
                "logical_offset": cursor,
                "sha256": plane["sha256"],
                "size_bytes": plane_size,
            }:
                raise QwenFullModelCheckpointError(
                    "runtime checkpoint plane geometry differs"
                )
            cursor += plane_size
    image = manifest["state_image"]
    if not isinstance(image, dict):
        raise QwenFullModelCheckpointError(
            "runtime checkpoint state image must be an object"
        )
    exact_keys(
        image,
        {"logical_sha256", "shard_bytes", "shards", "size_bytes"},
        set(),
        "runtime checkpoint state image",
    )
    require_sha256(image["logical_sha256"], "runtime checkpoint image SHA-256")
    if image["shard_bytes"] != DEFAULT_SHARD_BYTES or image["size_bytes"] != cursor:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint state-image geometry differs"
        )
    shards = image["shards"]
    expected_shards = (cursor + DEFAULT_SHARD_BYTES - 1) // DEFAULT_SHARD_BYTES
    if not isinstance(shards, list) or len(shards) != expected_shards:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint shard coverage differs"
        )
    shard_cursor = 0
    for index, shard in enumerate(shards):
        if not isinstance(shard, dict):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint shard record must be an object"
            )
        exact_keys(
            shard,
            {"index", "logical_offset", "path", "sha256", "size_bytes"},
            set(),
            f"runtime checkpoint shard[{index}]",
        )
        require_sha256(shard["sha256"], f"runtime checkpoint shard[{index}].sha256")
        path = _safe_relative(shard["path"], f"runtime checkpoint shard[{index}].path")
        size = min(DEFAULT_SHARD_BYTES, cursor - shard_cursor)
        if (
            shard["index"] != index
            or shard["logical_offset"] != shard_cursor
            or shard["size_bytes"] != size
            or not path.startswith("state/hbm.")
            or not path.endswith(f".{shard['sha256']}.bin")
        ):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint shard geometry or name differs"
            )
        shard_cursor += size
    return manifest


def validate_checkpoint_predecessor(
    manifest_value: Mapping[str, Any],
    report_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind every persisted K/V plane to the checkpoint's predecessor report."""

    manifest = validate_checkpoint_manifest(manifest_value)
    report = dict(report_value)
    report_id = require_sha256(
        report.get("report_id"), "runtime checkpoint predecessor report ID"
    )
    report_body = {key: item for key, item in report.items() if key != "report_id"}
    step = report.get("step_index")
    outputs = report.get("outputs")
    logits = outputs.get("committed_logits") if isinstance(outputs, dict) else None
    report_states = report.get("state")
    if (
        report_id != sha256_bytes(canonical_json_bytes(report_body))
        or isinstance(step, bool)
        or not isinstance(step, int)
        or step + 1 != manifest["next_step_index"]
        or not isinstance(logits, dict)
        or logits.get("greedy_token_id") != manifest["previous_greedy_token_id"]
        or report_id != manifest["previous_report_id"]
        or not isinstance(report_states, list)
        or len(report_states) != STATE_COUNT
    ):
        raise QwenFullModelCheckpointError(
            "runtime checkpoint predecessor boundary differs"
        )
    for layer, (checkpoint_state, report_state) in enumerate(
        zip(manifest["states"], report_states, strict=True)
    ):
        if (
            not isinstance(report_state, dict)
            or report_state.get("layer") != layer
            or report_state.get("resource_id") != f"kv.layer.{layer}"
            or report_state.get("generation") != manifest["next_step_index"]
            or report_state.get("length") != manifest["next_step_index"]
            or checkpoint_state["key"]["sha256"]
            != report_state.get("key_payload_sha256")
            or checkpoint_state["value"]["sha256"]
            != report_state.get("value_payload_sha256")
        ):
            raise QwenFullModelCheckpointError(
                "runtime checkpoint state differs from predecessor report"
            )
    return manifest


def publish_runtime_checkpoint(
    *,
    output: Path,
    bindings: Mapping[str, str],
    next_step_index: int,
    previous_report_id: str,
    previous_greedy_token_id: int,
    states: Mapping[str, KVSnapshot],
) -> dict[str, Any]:
    """Write every active K/V byte and atomically publish one checkpoint root."""

    destination = Path(output).resolve()
    if destination.exists() or destination.is_symlink():
        raise QwenFullModelCheckpointError(
            f"runtime checkpoint output already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    next_step = _integer(
        next_step_index, "runtime checkpoint next step", 1, MAX_NEXT_STEP
    )
    require_sha256(previous_report_id, "runtime checkpoint previous report ID")
    previous_token = _integer(
        previous_greedy_token_id,
        "runtime checkpoint previous greedy token",
        0,
        151_935,
    )
    expected_resources = {f"kv.layer.{layer}" for layer in range(STATE_COUNT)}
    if set(states) != expected_resources:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint state resources differ"
        )
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.tmp-", dir=destination.parent
        )
    )
    try:
        state_records: list[dict[str, Any]] = []
        total_size = STATE_COUNT * 2 * next_step * TOKEN_PLANE_BYTES
        with HBMShardWriter(
            temporary,
            total_size=total_size,
            shard_bytes=DEFAULT_SHARD_BYTES,
            relative_directory="state",
        ) as writer:
            for layer in range(STATE_COUNT):
                resource = f"kv.layer.{layer}"
                state = states[resource]
                if (
                    not isinstance(state, KVSnapshot)
                    or state.resource_id != resource
                    or state.generation != next_step
                    or state.length != next_step
                    or state.capacity != CONTEXT_CAPACITY
                ):
                    raise QwenFullModelCheckpointError(
                        f"runtime checkpoint state {resource!r} differs"
                    )
                planes: dict[str, dict[str, Any]] = {}
                for name, values in (
                    ("key", state.key_values),
                    ("value", state.value_values),
                ):
                    payload = _plane_payload(values)
                    offset = writer.cursor
                    digest = hashlib.sha256(payload).hexdigest()
                    writer.write(payload)
                    planes[name] = {
                        "logical_offset": offset,
                        "sha256": digest,
                        "size_bytes": len(payload),
                    }
                state_records.append(
                    {
                        "capacity": state.capacity,
                        "generation": state.generation,
                        "key": planes["key"],
                        "layer": layer,
                        "length": state.length,
                        "resource_id": resource,
                        "value": planes["value"],
                    }
                )
            image = writer.finish()
        body: dict[str, Any] = {
            **dict(bindings),
            "checkpoint_version": VERSION,
            "claim_boundary": {
                "acceptance_execution_complete": False,
                "restart_state_only": True,
                "target_precision_reference_verified": False,
                "timing_or_performance": False,
            },
            "context_capacity": CONTEXT_CAPACITY,
            "next_step_index": next_step,
            "previous_greedy_token_id": previous_token,
            "previous_report_id": previous_report_id,
            "schema": SCHEMA,
            "simulator_version": SIMULATOR_VERSION,
            "state_count": STATE_COUNT,
            "state_image": image,
            "states": state_records,
        }
        manifest = validate_checkpoint_manifest(
            _identified(body, "checkpoint_id"), expected_bindings=bindings
        )
        manifest_path = temporary / MANIFEST_NAME
        with manifest_path.open("xb") as handle:
            handle.write(canonical_json_bytes(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(temporary / "state")
        _fsync_directory(temporary)
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
        return manifest
    except (HBMShardError, OSError, ValueError) as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        if isinstance(exc, QwenFullModelCheckpointError):
            raise
        raise QwenFullModelCheckpointError(
            f"cannot publish runtime checkpoint: {exc}"
        ) from exc
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def load_runtime_checkpoint(
    root: Path,
    *,
    expected_bindings: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, KVSnapshot]]:
    """Authenticate all shards and reconstruct all 36 immutable KV snapshots."""

    try:
        checkpoint_root = Path(root).resolve(strict=True)
    except OSError as exc:
        raise QwenFullModelCheckpointError(
            f"cannot resolve runtime checkpoint: {exc}"
        ) from exc
    if not checkpoint_root.is_dir():
        raise QwenFullModelCheckpointError("runtime checkpoint must be a directory")
    manifest_path = checkpoint_root / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise QwenFullModelCheckpointError(
            "runtime checkpoint manifest must be a regular file"
        )
    manifest = validate_checkpoint_manifest(
        _canonical_manifest(manifest_path), expected_bindings=expected_bindings
    )
    image = manifest["state_image"]
    expected_files = {MANIFEST_NAME}
    resolved_root = checkpoint_root.resolve(strict=True)
    for index, shard in enumerate(image["shards"]):
        relative = _safe_relative(shard["path"], f"runtime checkpoint shard[{index}]")
        candidate = checkpoint_root / relative
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise QwenFullModelCheckpointError(
                f"cannot resolve runtime checkpoint shard {index}: {exc}"
            ) from exc
        if (
            candidate.is_symlink()
            or not resolved.is_file()
            or resolved_root not in resolved.parents
        ):
            raise QwenFullModelCheckpointError(
                f"runtime checkpoint shard {index} is unsafe"
            )
        expected_files.add(relative)
    observed_files = {
        path.relative_to(checkpoint_root).as_posix()
        for path in checkpoint_root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if observed_files != expected_files:
        raise QwenFullModelCheckpointError(
            "runtime checkpoint file inventory differs"
        )

    snapshots: dict[str, KVSnapshot] = {}
    try:
        with HBMShardReader(
            checkpoint_root, image["shards"], verify_hashes=True
        ) as reader:
            if (
                reader.total_size != image["size_bytes"]
                or reader.sha256(0, reader.total_size) != image["logical_sha256"]
            ):
                raise QwenFullModelCheckpointError(
                    "runtime checkpoint logical image differs"
                )
            for state in manifest["states"]:
                planes: dict[str, np.ndarray[Any, np.dtype[np.uint16]]] = {}
                for name in ("key", "value"):
                    record = state[name]
                    if (
                        reader.sha256(record["logical_offset"], record["size_bytes"])
                        != record["sha256"]
                    ):
                        raise QwenFullModelCheckpointError(
                            f"runtime checkpoint {state['resource_id']} {name} differs"
                        )
                    payload = reader.read(
                        record["logical_offset"], record["size_bytes"]
                    )
                    values = np.frombuffer(payload, dtype="<u2").reshape(
                        state["length"], KEY_VALUE_HEADS, HEAD_DIM
                    )
                    planes[name] = np.ascontiguousarray(values, dtype=np.uint16)
                snapshots[state["resource_id"]] = make_kv_snapshot(
                    resource_id=state["resource_id"],
                    generation=state["generation"],
                    capacity=state["capacity"],
                    key_values=planes["key"],
                    value_values=planes["value"],
                )
    except (HBMShardError, OSError, ValueError) as exc:
        if isinstance(exc, QwenFullModelCheckpointError):
            raise
        raise QwenFullModelCheckpointError(
            f"cannot reconstruct runtime checkpoint: {exc}"
        ) from exc
    return manifest, snapshots


__all__ = [
    "DEFAULT_SHARD_BYTES",
    "MANIFEST_NAME",
    "QwenFullModelCheckpointError",
    "SCHEMA",
    "VERSION",
    "load_runtime_checkpoint",
    "publish_runtime_checkpoint",
    "validate_checkpoint_predecessor",
    "validate_checkpoint_manifest",
]
