"""Independent inverse and deployment checks for Qwen3 physical images."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Any, BinaryIO, Mapping

from compiler.frontend.checkpoint import validate_checkpoint_lock
from compiler.ir.model import canonical_json_bytes, load_strict_json

from .adapter import (
    build_tensor_specs,
    load_official_config,
    validate_official_checkpoint_lock,
)
from .constants import (
    LAYER_COUNT,
    MODEL_ID,
    PAYLOAD_BYTES,
    REVISION,
    TARGET_CONTEXT_TOKENS,
    TENSOR_COUNT,
)
from .graph import GraphNode
from .isa import NO_INDEX, NO_LAYER, Opcode, Program
from .schedule import SCHEDULE_CERTIFICATE_SCHEMA, SCHEDULE_SCHEMA


PHYSICAL_MAP_SCHEMA = "opentallas.qwen3.physical_map.v1"
INVERSE_REPORT_SCHEMA = "opentallas.qwen3.inverse_report.v1"
DEPLOYMENT_SCHEMA = "opentallas.qwen3.deployment.v1"
CHUNK_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Qwen3CheckError(RuntimeError):
    """Raised when emitted bytes cannot independently reconstruct the source."""


def _exact(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Qwen3CheckError(f"{label} must be an object")
    observed = set(value)
    if observed != fields:
        raise Qwen3CheckError(
            f"{label} fields differ: missing={sorted(fields - observed)}, "
            f"unknown={sorted(observed - fields)}"
        )
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise Qwen3CheckError(f"{label} must be an integer >= {minimum}")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise Qwen3CheckError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _safe_file(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise Qwen3CheckError(f"{label} must be a safe relative POSIX path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise Qwen3CheckError(f"{label} must be a safe relative POSIX path")
    path = root.joinpath(*pure.parts)
    if not path.is_file():
        raise Qwen3CheckError(f"{label} is missing: {value}")
    return path


def _read_exact(handle: BinaryIO, size: int, label: str) -> bytes:
    payload = handle.read(size)
    if len(payload) != size:
        raise Qwen3CheckError(f"short read while checking {label}")
    return payload


def _hash_region(
    handle: BinaryIO,
    size: int,
    image_digest: Any,
    *,
    require_zero: bool,
    label: str,
) -> str:
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = _read_exact(handle, min(remaining, CHUNK_BYTES), label)
        if require_zero and any(chunk):
            raise Qwen3CheckError(f"{label} contains nonzero alignment padding")
        digest.update(chunk)
        image_digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def _locked_tensor_table(lock: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for shard in lock["shards"]:
        for tensor in shard["tensors"]:
            result[tensor["name"]] = tensor
    return result


def _expected_stage(name: str, layer: int | None) -> int:
    if layer is not None:
        return layer
    if name == "model.embed_tokens.weight":
        return 0
    if name in {"model.norm.weight", "lm_head.weight"}:
        return LAYER_COUNT - 1
    raise Qwen3CheckError(f"tensor {name!r} has no independently defined stage")


def verify_physical_images(
    root: Path,
    physical_map: Mapping[str, Any],
    lock: dict[str, Any],
) -> dict[str, Any]:
    """Read every image byte, reject padding changes, and hash each source tensor."""

    root = Path(root).resolve()
    try:
        validate_checkpoint_lock(lock)
        validate_official_checkpoint_lock(lock)
    except Exception as exc:
        raise Qwen3CheckError(
            f"checkpoint lock is not official Qwen3-8B: {exc}"
        ) from exc
    record = _exact(
        physical_map,
        {"coverage", "layout", "model", "physical_map_id", "schema", "stages"},
        "physical map",
    )
    if record["schema"] != PHYSICAL_MAP_SCHEMA:
        raise Qwen3CheckError("unsupported physical map schema")
    body = {key: record[key] for key in record if key != "physical_map_id"}
    if (
        _digest(record["physical_map_id"], "physical_map_id")
        != hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    ):
        raise Qwen3CheckError("physical_map_id does not bind the map")
    model = _exact(
        record["model"],
        {"checkpoint_lock_id", "id", "revision", "target_context_tokens"},
        "physical map model",
    )
    if model != {
        "checkpoint_lock_id": lock["lock_id"],
        "id": MODEL_ID,
        "revision": REVISION,
        "target_context_tokens": TARGET_CONTEXT_TOKENS,
    }:
        raise Qwen3CheckError("physical map model identity differs")
    layout = _exact(
        record["layout"],
        {"address_unit", "alignment_bytes", "stage_count"},
        "physical map layout",
    )
    alignment = _integer(layout["alignment_bytes"], "alignment_bytes", 1)
    if alignment & (alignment - 1) or alignment > 1024 * 1024:
        raise Qwen3CheckError("alignment must be a power of two no larger than 1 MiB")
    if layout["address_unit"] != "byte" or layout["stage_count"] != LAYER_COUNT:
        raise Qwen3CheckError("physical layout address unit or stage count differs")

    specs = build_tensor_specs(load_official_config())
    expected_specs = {spec.name: spec for spec in specs}
    locked = _locked_tensor_table(lock)
    stages = record["stages"]
    if not isinstance(stages, list) or len(stages) != LAYER_COUNT:
        raise Qwen3CheckError("physical map must contain exactly 36 stages")
    seen: set[str] = set()
    total_image_bytes = total_payload = total_padding = 0
    image_digests: list[dict[str, Any]] = []
    for expected_stage, raw_stage in enumerate(stages):
        stage = _exact(
            raw_stage,
            {
                "image_path",
                "image_sha256",
                "image_size_bytes",
                "padding_bytes",
                "payload_bytes",
                "stage",
                "tensors",
            },
            f"stage[{expected_stage}]",
        )
        if stage["stage"] != expected_stage:
            raise Qwen3CheckError("physical stages are not ordered and contiguous")
        image_size = _integer(stage["image_size_bytes"], "image_size_bytes", 1)
        if image_size % alignment:
            raise Qwen3CheckError(f"stage {expected_stage} image is not aligned")
        expected_image_digest = _digest(stage["image_sha256"], "image_sha256")
        tensors = stage["tensors"]
        if not isinstance(tensors, list) or not tensors:
            raise Qwen3CheckError(f"stage {expected_stage} has no tensors")
        image_path = _safe_file(root, stage["image_path"], "stage image_path")
        if image_path.stat().st_size != image_size:
            raise Qwen3CheckError(f"stage {expected_stage} image size differs")
        cursor = stage_payload = stage_padding = 0
        image_digest = hashlib.sha256()
        with image_path.open("rb") as handle:
            for tensor_index, raw_tensor in enumerate(tensors):
                tensor = _exact(
                    raw_tensor,
                    {
                        "dtype",
                        "layer",
                        "name",
                        "offset_bytes",
                        "payload_sha256",
                        "role",
                        "shape",
                        "size_bytes",
                    },
                    f"stage[{expected_stage}].tensors[{tensor_index}]",
                )
                name = tensor["name"]
                if (
                    not isinstance(name, str)
                    or name not in expected_specs
                    or name in seen
                ):
                    raise Qwen3CheckError(
                        f"invalid or duplicate mapped tensor {name!r}"
                    )
                spec = expected_specs[name]
                locked_tensor = locked[name]
                if _expected_stage(name, spec.layer) != expected_stage:
                    raise Qwen3CheckError(
                        f"tensor {name!r} is assigned to the wrong stage"
                    )
                offset = _integer(tensor["offset_bytes"], "offset_bytes")
                size = _integer(tensor["size_bytes"], "size_bytes", 1)
                if offset % alignment or offset < cursor:
                    raise Qwen3CheckError(f"tensor {name!r} has an illegal address")
                padding = offset - cursor
                _hash_region(
                    handle,
                    padding,
                    image_digest,
                    require_zero=True,
                    label=f"padding before {name}",
                )
                observed_payload_digest = _hash_region(
                    handle,
                    size,
                    image_digest,
                    require_zero=False,
                    label=name,
                )
                expected_tensor_record = {
                    "dtype": spec.dtype,
                    "layer": spec.layer,
                    "name": name,
                    "offset_bytes": offset,
                    "payload_sha256": locked_tensor["payload_sha256"],
                    "role": spec.role,
                    "shape": list(spec.shape),
                    "size_bytes": spec.size_bytes,
                }
                if dict(tensor) != expected_tensor_record:
                    raise Qwen3CheckError(
                        f"mapped metadata differs for tensor {name!r}"
                    )
                if observed_payload_digest != locked_tensor["payload_sha256"]:
                    raise Qwen3CheckError(
                        f"inverse payload hash differs for tensor {name!r}"
                    )
                seen.add(name)
                cursor = offset + size
                stage_payload += size
                stage_padding += padding
            trailing = image_size - cursor
            if trailing < 0:
                raise Qwen3CheckError(f"stage {expected_stage} image overflows")
            _hash_region(
                handle,
                trailing,
                image_digest,
                require_zero=True,
                label=f"stage {expected_stage} trailing padding",
            )
            stage_padding += trailing
            if handle.read(1):
                raise Qwen3CheckError(f"stage {expected_stage} contains trailing bytes")
        if image_digest.hexdigest() != expected_image_digest:
            raise Qwen3CheckError(f"stage {expected_stage} image SHA-256 differs")
        if (
            stage["payload_bytes"] != stage_payload
            or stage["padding_bytes"] != stage_padding
            or stage_payload + stage_padding != image_size
        ):
            raise Qwen3CheckError(f"stage {expected_stage} byte accounting differs")
        total_image_bytes += image_size
        total_payload += stage_payload
        total_padding += stage_padding
        image_digests.append(
            {
                "path": stage["image_path"],
                "sha256": expected_image_digest,
                "size_bytes": image_size,
                "stage": expected_stage,
            }
        )
    if seen != set(expected_specs):
        raise Qwen3CheckError(
            f"physical images do not cover all tensors: {sorted(set(expected_specs) - seen)[:8]}"
        )
    coverage = _exact(
        record["coverage"],
        {
            "all_padding_zero",
            "all_tensors_inverse_reconstructed",
            "image_bytes",
            "image_count",
            "padding_bytes",
            "payload_bytes",
            "tensor_count",
        },
        "physical map coverage",
    )
    expected_coverage = {
        "all_padding_zero": True,
        "all_tensors_inverse_reconstructed": True,
        "image_bytes": total_image_bytes,
        "image_count": LAYER_COUNT,
        "padding_bytes": total_padding,
        "payload_bytes": PAYLOAD_BYTES,
        "tensor_count": TENSOR_COUNT,
    }
    if dict(coverage) != expected_coverage or total_payload != PAYLOAD_BYTES:
        raise Qwen3CheckError("physical map aggregate coverage differs")
    report_body = {
        "checkpoint_lock_id": lock["lock_id"],
        "image_bytes_checked": total_image_bytes,
        "images": image_digests,
        "padding_bytes_checked_zero": total_padding,
        "payload_bytes_reconstructed": total_payload,
        "physical_map_id": record["physical_map_id"],
        "schema": INVERSE_REPORT_SCHEMA,
        "tensor_count_reconstructed": len(seen),
    }
    return {
        **report_body,
        "report_id": hashlib.sha256(canonical_json_bytes(report_body)).hexdigest(),
    }


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def verify_deployment_artifacts(root: Path, manifest: Mapping[str, Any]) -> None:
    """Verify the canonical manifest and every runtime-visible artifact hash."""

    root = Path(root).resolve()
    record = _exact(
        manifest,
        {"artifacts", "build_id", "compiler", "model", "runtime", "schema"},
        "deployment manifest",
    )
    if record["schema"] != DEPLOYMENT_SCHEMA:
        raise Qwen3CheckError("unsupported deployment schema")
    body = {key: record[key] for key in record if key != "build_id"}
    if (
        _digest(record["build_id"], "build_id")
        != hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    ):
        raise Qwen3CheckError("build_id does not bind the deployment manifest")
    artifacts = record["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise Qwen3CheckError("deployment artifacts must be a nonempty array")
    paths: list[str] = []
    for index, raw in enumerate(artifacts):
        artifact = _exact(
            raw, {"path", "role", "sha256", "size_bytes"}, f"artifact[{index}]"
        )
        path = _safe_file(root, artifact["path"], f"artifact[{index}].path")
        paths.append(artifact["path"])
        digest, size = _hash_file(path)
        if digest != _digest(artifact["sha256"], "artifact sha256") or size != _integer(
            artifact["size_bytes"], "artifact size_bytes"
        ):
            raise Qwen3CheckError(
                f"artifact {artifact['path']!r} differs from its manifest"
            )
        if not isinstance(artifact["role"], str) or not artifact["role"]:
            raise Qwen3CheckError("artifact role must be a nonempty string")
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise Qwen3CheckError("deployment artifact paths must be unique and sorted")


def verify_schedule(
    schedule: Mapping[str, Any],
    program: Program,
    nodes: tuple[GraphNode, ...],
    physical_map: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently prove dependency, placement, liveness, and terminal legality."""

    record = _exact(
        schedule,
        {
            "graph_id",
            "microcode_instruction_count",
            "model_id",
            "physical_map_id",
            "policy",
            "schedule_id",
            "schema",
            "slots",
            "summary",
        },
        "schedule",
    )
    if record["schema"] != SCHEDULE_SCHEMA:
        raise Qwen3CheckError("unsupported Qwen3 schedule schema")
    schedule_body = {key: record[key] for key in record if key != "schedule_id"}
    if (
        _digest(record["schedule_id"], "schedule_id")
        != hashlib.sha256(canonical_json_bytes(schedule_body)).hexdigest()
    ):
        raise Qwen3CheckError("schedule_id does not bind the schedule")
    if (
        record["graph_id"] != program.graph_id
        or record["model_id"] != MODEL_ID
        or record["physical_map_id"] != physical_map.get("physical_map_id")
        or record["microcode_instruction_count"] != len(program.instructions)
        or len(program.instructions) != len(nodes) + 1
    ):
        raise Qwen3CheckError("schedule identities or instruction coverage differ")
    stage_by_weight: dict[str, int] = {}
    for expected_stage, stage in enumerate(physical_map.get("stages", [])):
        if not isinstance(stage, Mapping) or stage.get("stage") != expected_stage:
            raise Qwen3CheckError(
                "physical stage ordering differs during schedule check"
            )
        for tensor in stage.get("tensors", []):
            name = tensor.get("name") if isinstance(tensor, Mapping) else None
            if not isinstance(name, str) or name in stage_by_weight:
                raise Qwen3CheckError(
                    "physical weight table is invalid during schedule check"
                )
            stage_by_weight[name] = expected_stage
    slots = record["slots"]
    if not isinstance(slots, list) or len(slots) != len(program.instructions):
        raise Qwen3CheckError("schedule slots do not cover every instruction")
    available: dict[str, int] = {"input.token_ids": -1}
    last_uses: dict[str, int] = {}
    for index, instruction in enumerate(program.instructions):
        for source in (instruction.source0, instruction.source1):
            if source != NO_INDEX:
                last_uses[program.buffers[source]] = index
    live = {"input.token_ids"}
    maximum_live = 1
    commit_layers: list[int] = []
    read_layers: list[int] = []
    transitions = 0
    previous_stage: int | None = None
    for index, (raw_slot, instruction) in enumerate(zip(slots, program.instructions)):
        slot = _exact(
            raw_slot,
            {
                "dependencies",
                "instruction_index",
                "kv_action",
                "layer",
                "node_id",
                "opcode",
                "reads",
                "slot",
                "stage",
                "weight",
                "writes",
            },
            f"schedule slot {index}",
        )
        reads = [
            program.buffers[source]
            for source in (instruction.source0, instruction.source1)
            if source != NO_INDEX
        ]
        writes = [
            program.buffers[destination]
            for destination in (instruction.destination0, instruction.destination1)
            if destination != NO_INDEX
        ]
        weight = (
            None
            if instruction.weight == NO_INDEX
            else program.weights[instruction.weight]
        )
        expected_dependencies = sorted(
            {
                available[name]
                for name in reads
                if name in available and available[name] >= 0
            }
        )
        missing = sorted(set(reads) - set(available))
        if missing:
            raise Qwen3CheckError(
                f"schedule slot {index} reads unavailable values {missing}"
            )
        if weight is not None:
            stage = stage_by_weight.get(weight)
        elif instruction.layer != NO_LAYER:
            stage = instruction.layer
        elif instruction.opcode == Opcode.TOKEN_EMBEDDING_LOOKUP:
            stage = 0
        else:
            stage = LAYER_COUNT - 1
        expected_node_id = (
            "COMPLETE"
            if instruction.opcode == Opcode.COMPLETE
            else nodes[index].node_id
        )
        expected_action = (
            "commit"
            if instruction.opcode == Opcode.KV_COMMIT
            else "read"
            if instruction.opcode == Opcode.GQA_CAUSAL_ATTENTION
            else "none"
        )
        expected_slot = {
            "dependencies": expected_dependencies,
            "instruction_index": index,
            "kv_action": expected_action,
            "layer": None if instruction.layer == NO_LAYER else instruction.layer,
            "node_id": expected_node_id,
            "opcode": instruction.opcode.name,
            "reads": reads,
            "slot": index,
            "stage": stage,
            "weight": weight,
            "writes": writes,
        }
        if dict(slot) != expected_slot:
            raise Qwen3CheckError(
                f"schedule slot {index} differs from microcode/dependencies"
            )
        if instruction.layer != NO_LAYER and stage != instruction.layer:
            raise Qwen3CheckError(f"schedule slot {index} crosses a layer stage")
        if previous_stage is not None and previous_stage != stage:
            transitions += 1
        previous_stage = stage
        for name in writes:
            available[name] = index
            live.add(name)
        maximum_live = max(maximum_live, len(live))
        for name in reads:
            if last_uses[name] == index and name not in writes:
                live.discard(name)
        if expected_action == "commit":
            commit_layers.append(instruction.layer)
        elif expected_action == "read":
            read_layers.append(instruction.layer)
    if commit_layers != list(range(LAYER_COUNT)) or read_layers != list(
        range(LAYER_COUNT)
    ):
        raise Qwen3CheckError("schedule does not commit/read KV exactly once per layer")
    if program.instructions[-1].opcode != Opcode.COMPLETE:
        raise Qwen3CheckError("schedule program is not terminal")
    expected_summary = {
        "complete_count": 1,
        "kv_commit_count": LAYER_COUNT,
        "kv_read_count": LAYER_COUNT,
        "matrix_instruction_count": 253,
        "slot_count": len(slots),
        "stage_transition_count": transitions,
    }
    if record["summary"] != expected_summary:
        raise Qwen3CheckError("schedule summary differs from independent counts")
    body = {
        "conflict_free": True,
        "dependency_complete": True,
        "graph_id": program.graph_id,
        "kv_layer_commit_count": len(commit_layers),
        "maximum_live_buffers": maximum_live,
        "physical_map_id": physical_map["physical_map_id"],
        "schedule_id": record["schedule_id"],
        "schema": SCHEDULE_CERTIFICATE_SCHEMA,
        "slot_count": len(slots),
        "status": "pass",
        "terminal_complete_count": 1,
    }
    return {
        **body,
        "certificate_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def load_physical_map(path: Path) -> dict[str, Any]:
    try:
        value = load_strict_json(Path(path))
    except (OSError, ValueError) as exc:
        raise Qwen3CheckError(f"cannot load physical map {path}: {exc}") from exc
    return value


__all__ = [
    "DEPLOYMENT_SCHEMA",
    "INVERSE_REPORT_SCHEMA",
    "PHYSICAL_MAP_SCHEMA",
    "Qwen3CheckError",
    "load_physical_map",
    "verify_deployment_artifacts",
    "verify_physical_images",
    "verify_schedule",
]
