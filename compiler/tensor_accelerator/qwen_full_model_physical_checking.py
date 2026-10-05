"""Independent inverse checker for the complete Qwen physical deployment.

This module intentionally does not import :mod:`qwen_full_model_physical`.
It authenticates the admitted semantic bundle, walks the 617-operation graph,
reconstructs checkpoint-derived HBM payloads, proves SRAM lifetimes, and
derives every ABI command from the candidate's independently checked physical
records.  A generator success is therefore insufficient to publish a build.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from pathlib import Path, PurePosixPath
import struct
from typing import Any, Mapping

import numpy as np

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE

from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from .hbm_shards import DEFAULT_SHARD_BYTES, HBMShardError, HBMShardReader
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_command import (
    ABI_MAJOR,
    MATMUL_FINAL,
    MATMUL_INIT,
    NO_KERNEL,
    SELECTION_ABI_MINOR,
    Engine,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    decode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    ProductionTensor,
    load_production_model_graph,
)


COMPILER_VERSION = "tensor-accelerator-qwen-full-model-physical-0.1.0"
CHECKER_VERSION = "tensor-accelerator-qwen-full-model-physical-check-0.1.0"

SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_source_lock.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_physical_plan.v1"
CAPACITY_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_capacity.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_request.v1"
CHECK_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_physical_check.v1"

PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
CAPACITY_PATH = "physical/capacity_certificate.json"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
KERNEL_IR_PATH = "ir/tensor_kernel_ir.json"
CHECK_PATH = "checks/independent_check.json"
MANIFEST_PATH = "deployment_manifest.json"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_deployment.v1"

SOURCE_COPIES = {
    "capability": "source/capability.json",
    "checkpoint_lock": "source/checkpoint.lock.json",
    "model_graph": "source/model_graph.v2.json",
    "semantic_check": "source/semantic_independent_check.json",
    "semantic_coverage": "source/semantic_coverage.json",
    "semantic_kernel_ir": "source/semantic_tensor_kernel_ir.json",
}

MODEL_ID = "qwen3-8b"
OPERATION_COUNT = 617
TENSOR_COUNT = 1053
WEIGHT_COUNT = 399
STATE_COUNT = 36
LAYER_COUNT = 36
CONTEXT_CAPACITY = 8000
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
VOCABULARY_SIZE = 151936
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
N_TILE = 64
K_TILE = 256
BF16_BYTES = 2
TILE_BYTES = N_TILE * K_TILE * BF16_BYTES
EMBEDDING_ROW_BYTES = HIDDEN_WIDTH * BF16_BYTES
KV_TOKEN_BYTES = KEY_VALUE_HEADS * HEAD_DIM * BF16_BYTES
STATE_PLANE_BYTES = CONTEXT_CAPACITY * KV_TOKEN_BYTES
TRANSACTION_ID = 0x5157454E46554C4C

STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")

EXPECTED_COMMAND_COUNT = 924386
EXPECTED_WEIGHT_BYTES = 16381470720
EXPECTED_KV_BYTES = 1179648000
EXPECTED_OPCODE_COUNTS = {
    "ADD_BF16": 72,
    "COMPLETE": 1,
    "DMA_HBM_INDEXED_TO_SRAM": 37,
    "DMA_HBM_TO_SRAM": 462065,
    "DMA_SRAM_INDEXED_TO_SRAM": 1,
    "GQA_ATTENTION_BF16": 36,
    "KV_PREPARE_BF16": 36,
    "MATMUL_BF16_TILE": 461920,
    "RMSNORM_BF16": 145,
    "ROPE_BF16": 36,
    "SILU_MUL_BF16": 36,
    "STATE_COMMIT": 1,
}
COEFFICIENT_TABLE_SHA256 = (
    "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
)
QUALIFIED_COEFFICIENT_TABLE_SHA256 = {
    8000: COEFFICIENT_TABLE_SHA256,
    8192: "aeaab0b9af138b2f7464ed38c925ca4ab2faa6de294a49d3e579003e70f7051b",
}

CLAIM_BOUNDARY = {
    "complete_graph_physical_lowering": True,
    "complete_checkpoint_payload_deployment": True,
    "complete_command_template": True,
    "full_model_execution": False,
    "timing_or_performance": False,
}


class QwenFullModelPhysicalCheckError(ArtifactError):
    """Raised when a QW-FM2 candidate cannot be reconstructed exactly."""


def _context_capacity(model: ProductionModelGraph) -> int:
    symbol = model.symbol_by_id.get("context_capacity")
    if (
        symbol is None
        or symbol.binding != {"kind": "compile_time"}
        or symbol.minimum != symbol.maximum
        or symbol.default != symbol.maximum
        or symbol.multiple_of != symbol.maximum
        or symbol.maximum not in QUALIFIED_COEFFICIENT_TABLE_SHA256
    ):
        raise QwenFullModelPhysicalCheckError(
            "independent Qwen physical context is not qualified"
        )
    return symbol.maximum


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = dict(body)
    value[field] = sha256_bytes(canonical_json_bytes(body))
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelPhysicalCheckError(f"{label} identity differs")


def _canonical(path: Path, label: str) -> dict[str, Any]:
    value = load_strict_json(path)
    if path.read_bytes() != canonical_json_bytes(value):
        raise QwenFullModelPhysicalCheckError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise QwenFullModelPhysicalCheckError(
            f"{label} must be a safe relative POSIX path"
        )
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or parsed.as_posix() != value
    ):
        raise QwenFullModelPhysicalCheckError(
            f"{label} must be a safe relative POSIX path"
        )
    return value


def _artifact(root: Path, relative: str, label: str) -> Path:
    path = root / _safe_relative(relative, label)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise QwenFullModelPhysicalCheckError(f"cannot resolve {label}: {exc}") from exc
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise QwenFullModelPhysicalCheckError(f"{label} escapes the deployment")
    if path.is_symlink() or not resolved.is_file():
        raise QwenFullModelPhysicalCheckError(f"{label} is not a regular file")
    return resolved


def _admit_semantic_bundle(
    coverage: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
    semantic_check: Mapping[str, Any],
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    checkpoint_lock_id: str,
) -> None:
    _identity(coverage, "report_id", "semantic coverage")
    _identity(kernel_ir, "kernel_ir_id", "semantic Kernel IR")
    _identity(semantic_check, "check_id", "semantic independent check")
    kernels = kernel_ir.get("kernels")
    if (
        coverage.get("schema")
        != "opentallas.tensor_accelerator.qwen_full_model_semantic_coverage.v1"
        or coverage.get("status") != "pass"
        or coverage.get("graph_id") != model.graph_id
        or coverage.get("checkpoint_lock_id") != checkpoint_lock_id
        or coverage.get("capability", {}).get("capability_id")
        != capability.capability_id
        or coverage.get("operation_count") != OPERATION_COUNT
        or coverage.get("kernel_count") != OPERATION_COUNT
        or coverage.get("unknown_operation_count") != 0
        or coverage.get("claim_boundary")
        != {
            "complete_graph_operation_coverage": True,
            "complete_graph_state_contract_coverage": True,
            "complete_neutral_kernel_lowering": True,
            "full_model_execution": False,
            "physical_plan": False,
            "timing_or_performance": False,
        }
    ):
        raise QwenFullModelPhysicalCheckError("semantic coverage boundary differs")
    if (
        kernel_ir.get("schema") != "opentallas.production_tensor_kernel_ir.v1"
        or kernel_ir.get("graph_id") != model.graph_id
        or kernel_ir.get("qualification_report_id") != coverage["report_id"]
        or not isinstance(kernels, list)
        or len(kernels) != OPERATION_COUNT
        or [item.get("source_operation_id") for item in kernels]
        != [operation.operation_id for operation in model.operations]
    ):
        raise QwenFullModelPhysicalCheckError("semantic Kernel IR differs")
    checks = semantic_check.get("checks")
    if (
        semantic_check.get("schema")
        != "opentallas.tensor_accelerator.qwen_full_model_semantic_check.v1"
        or semantic_check.get("status") != "pass"
        or semantic_check.get("graph_id") != model.graph_id
        or semantic_check.get("coverage_report_id") != coverage["report_id"]
        or semantic_check.get("kernel_ir_id") != kernel_ir["kernel_ir_id"]
        or semantic_check.get("capability_id") != capability.capability_id
        or semantic_check.get("operation_count") != OPERATION_COUNT
        or semantic_check.get("state_resource_count") != STATE_COUNT
        or not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise QwenFullModelPhysicalCheckError("semantic independent check differs")


def _admit_model_and_capability(
    model: ProductionModelGraph, capability: ProductionCapability
) -> None:
    context_capacity = _context_capacity(model)
    vector = capability.vector_engine
    state = capability.state_engine
    if (
        model.model_id != MODEL_ID
        or len(model.operations) != OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_COUNT
        or (capability.command_abi_major, capability.command_abi_minor)
        != (ABI_MAJOR, SELECTION_ABI_MINOR)
        or capability.tensor_engine.max_m < 1
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
        or vector is None
        or vector.max_rows < QUERY_HEADS + KEY_VALUE_HEADS
        or vector.max_width < INTERMEDIATE_WIDTH
        or vector.max_rope_positions != context_capacity
        or vector.max_attention_context_tokens != context_capacity
        or vector.max_query_heads != QUERY_HEADS
        or vector.max_key_value_heads != KEY_VALUE_HEADS
        or vector.rope_head_dim != HEAD_DIM
        or vector.attention_head_dim != HEAD_DIM
        or vector.softmax_reduction_lanes != 8
        or state is None
        or state.max_resources_per_transaction < STATE_COUNT
        or capability.hbm.external_at_130nm_boundary is not True
    ):
        raise QwenFullModelPhysicalCheckError(
            "model/capability cannot represent the full Qwen deployment"
        )


def _load_sources(
    *,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    semantic_coverage_path: Path,
    semantic_kernel_ir_path: Path,
    semantic_check_path: Path,
) -> tuple[
    dict[str, Any],
    ProductionModelGraph,
    ProductionCapability,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
]:
    source_paths = {
        "capability": capability_path,
        "checkpoint_lock": checkpoint_lock_path,
        "model_graph": model_graph_path,
        "semantic_check": semantic_check_path,
        "semantic_coverage": semantic_coverage_path,
        "semantic_kernel_ir": semantic_kernel_ir_path,
    }
    for role, path in source_paths.items():
        _canonical(path, f"source {role}")
    checkpoint_lock = load_checkpoint_lock(checkpoint_lock_path)
    model = load_production_model_graph(model_graph_path)
    capability = load_production_capability(capability_path)
    coverage = load_strict_json(semantic_coverage_path)
    kernel_ir = load_strict_json(semantic_kernel_ir_path)
    semantic_check = load_strict_json(semantic_check_path)
    _admit_model_and_capability(model, capability)
    _admit_semantic_bundle(
        coverage,
        kernel_ir,
        semantic_check,
        model=model,
        capability=capability,
        checkpoint_lock_id=checkpoint_lock["lock_id"],
    )
    return (
        checkpoint_lock,
        model,
        capability,
        coverage,
        kernel_ir,
        semantic_check,
        source_paths,
    )


def _expected_source_lock(
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    checkpoint_lock: Mapping[str, Any],
    coverage: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
    semantic_check: Mapping[str, Any],
    source_paths: Mapping[str, Path],
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    for role in sorted(SOURCE_COPIES):
        digest, size = sha256_file(source_paths[role])
        artifacts[role] = {
            "path": SOURCE_COPIES[role],
            "sha256": digest,
            "size_bytes": size,
        }
    return _identified(
        {
            "artifacts": artifacts,
            "capability_id": capability.capability_id,
            "checkpoint_lock_id": checkpoint_lock["lock_id"],
            "compiler_version": COMPILER_VERSION,
            "graph_id": model.graph_id,
            "schema": SOURCE_LOCK_SCHEMA,
            "semantic_check_id": semantic_check["check_id"],
            "semantic_coverage_report_id": coverage["report_id"],
            "semantic_kernel_ir_id": kernel_ir["kernel_ir_id"],
        },
        "source_lock_id",
    )


def _expected_request(model: ProductionModelGraph) -> dict[str, Any]:
    return _identified(
        {
            "expected_generations": [0] * STATE_COUNT,
            "graph_id": model.graph_id,
            "last_row_index": 0,
            "phase": "prefill",
            "position_end": 1,
            "position_start": 0,
            "schema": REQUEST_SCHEMA,
            "span_tokens": 1,
            "token_id": 0,
            "transaction_id": TRANSACTION_ID,
        },
        "request_id",
    )


def _weight_consumers(
    model: ProductionModelGraph,
) -> dict[str, ProductionOperation]:
    weight_ids = {
        tensor.tensor_id for tensor in model.tensors if tensor.role == "weight"
    }
    found: dict[str, list[ProductionOperation]] = defaultdict(list)
    for operation in model.operations:
        for tensor_id in operation.inputs:
            if tensor_id in weight_ids:
                found[tensor_id].append(operation)
    if set(found) != weight_ids or any(len(items) != 1 for items in found.values()):
        raise QwenFullModelPhysicalCheckError(
            "each checkpoint weight must have one graph consumer"
        )
    return {tensor_id: items[0] for tensor_id, items in found.items()}


def _weight_source(tensor: ProductionTensor, checkpoint_lock_id: str) -> dict[str, Any]:
    binding = tensor.binding
    if (
        tensor.role != "weight"
        or tensor.dtype != "bf16"
        or binding is None
        or binding.checkpoint_lock_id != checkpoint_lock_id
        or binding.transform != {"kind": "identity"}
        or len(binding.sources) != 1
    ):
        raise QwenFullModelPhysicalCheckError(
            f"weight {tensor.tensor_id!r} binding differs"
        )
    source = binding.sources[0]
    if (
        source.dtype != "bf16"
        or source.shape != tensor.shape
        or source.payload_sha256 != binding.payload_sha256
    ):
        raise QwenFullModelPhysicalCheckError(
            f"weight {tensor.tensor_id!r} source differs"
        )
    return {
        "checkpoint_lock_id": checkpoint_lock_id,
        "dtype": "BF16",
        "payload_sha256": source.payload_sha256,
        "shape": list(source.shape),
        "tensor_name": source.tensor_name,
    }


def _reserved_extent(
    cursor: int,
    size: int,
    alignment: int,
    *,
    keep_within_shard: bool,
) -> tuple[int, int]:
    start = align_up(cursor, alignment)
    if (
        keep_within_shard
        and size <= DEFAULT_SHARD_BYTES
        and start // DEFAULT_SHARD_BYTES != (start + size - 1) // DEFAULT_SHARD_BYTES
    ):
        start = align_up(start, DEFAULT_SHARD_BYTES)
    return start, start + size


def _derive_hbm(
    model: ProductionModelGraph,
    capability: ProductionCapability,
    checkpoint_lock: Mapping[str, Any],
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    state_plane_bytes = context_capacity * KV_TOKEN_BYTES
    coefficient_sha256 = QUALIFIED_COEFFICIENT_TABLE_SHA256[context_capacity]
    consumers = _weight_consumers(model)
    weights = sorted(
        (tensor for tensor in model.tensors if tensor.role == "weight"),
        key=lambda tensor: consumers[tensor.tensor_id].index,
    )
    if len(weights) != WEIGHT_COUNT:
        raise QwenFullModelPhysicalCheckError("weight count differs")
    locked = {
        tensor["name"]: tensor
        for shard in checkpoint_lock["shards"]
        for tensor in shard["tensors"]
    }
    cursor = 0
    padding = 0
    immutable = 0
    records: list[dict[str, Any]] = []
    for tensor in weights:
        operation = consumers[tensor.tensor_id]
        source = _weight_source(tensor, checkpoint_lock["lock_id"])
        elements = 1
        for extent in tensor.shape:
            elements *= int(extent)
        size = elements * BF16_BYTES
        lock_record = locked.get(source["tensor_name"])
        if (
            lock_record is None
            or lock_record["dtype"] != "BF16"
            or lock_record["shape"] != source["shape"]
            or lock_record["size_bytes"] != size
            or lock_record["payload_sha256"] != source["payload_sha256"]
        ):
            raise QwenFullModelPhysicalCheckError(
                f"checkpoint record for {tensor.tensor_id!r} differs"
            )
        if operation.kind == "EMBEDDING_LOOKUP":
            layout = "direct_row_major_bf16"
            alignment = EMBEDDING_ROW_BYTES
            access = EMBEDDING_ROW_BYTES
            keep = False
            details: dict[str, Any] = {
                "row_bytes": EMBEDDING_ROW_BYTES,
                "rows": VOCABULARY_SIZE,
            }
        elif operation.kind == "RMS_NORM":
            layout = "direct_vector_bf16"
            alignment = capability.hbm.burst_bytes
            access = size
            keep = True
            details = {"elements": elements}
        elif operation.kind == "MATMUL":
            if len(tensor.shape) != 2:
                raise QwenFullModelPhysicalCheckError("matrix weight rank differs")
            n, k = (int(value) for value in tensor.shape)
            if n % N_TILE or k % K_TILE:
                raise QwenFullModelPhysicalCheckError(
                    f"matrix {tensor.tensor_id!r} is not tileable"
                )
            layout = "n_major_k_minor_tiles_bf16"
            alignment = TILE_BYTES
            access = TILE_BYTES
            keep = False
            details = {
                "k": k,
                "k_tile": K_TILE,
                "k_tiles": k // K_TILE,
                "n": n,
                "n_tile": N_TILE,
                "n_tiles": n // N_TILE,
                "order": "n_tile_then_k_tile",
                "tile_bytes": TILE_BYTES,
                "tile_count": (n // N_TILE) * (k // K_TILE),
            }
        else:
            raise QwenFullModelPhysicalCheckError(
                f"weight consumer {operation.kind!r} is unsupported"
            )
        start, end = _reserved_extent(cursor, size, alignment, keep_within_shard=keep)
        padding += start - cursor
        records.append(
            {
                "access_unit_bytes": access,
                "address": capability.hbm.base_address + start,
                "consumer_kernel_index": operation.index,
                "consumer_operation_id": operation.operation_id,
                "deployed_payload_sha256": None,
                "layout": layout,
                "layout_details": details,
                "offset_bytes": start,
                "size_bytes": size,
                "source": source,
                "tensor_id": tensor.tensor_id,
            }
        )
        immutable += size
        cursor = end
    if immutable != EXPECTED_WEIGHT_BYTES:
        raise QwenFullModelPhysicalCheckError("immutable byte count differs")

    coefficient_size = context_capacity * 2 * HEAD_DIM * BF16_BYTES
    coefficient_start, coefficient_end = _reserved_extent(
        cursor,
        coefficient_size,
        2 * HEAD_DIM * BF16_BYTES,
        keep_within_shard=True,
    )
    padding += coefficient_start - cursor
    coefficient = {
        "address": capability.hbm.base_address + coefficient_start,
        "layout": "position_major_cos_then_sin_bf16",
        "offset_bytes": coefficient_start,
        "payload_sha256": coefficient_sha256,
        "positions": context_capacity,
        "row_bytes": 2 * HEAD_DIM * BF16_BYTES,
        "size_bytes": coefficient_size,
    }
    cursor = coefficient_end

    states: list[dict[str, Any]] = []
    for layer in range(LAYER_COUNT):
        key_start, key_end = _reserved_extent(
            cursor,
            state_plane_bytes,
            capability.hbm.burst_bytes,
            keep_within_shard=True,
        )
        value_start, value_end = _reserved_extent(
            key_end,
            state_plane_bytes,
            capability.hbm.burst_bytes,
            keep_within_shard=True,
        )
        padding += key_start - cursor + value_start - key_end
        states.append(
            {
                "head_dim": HEAD_DIM,
                "key_address": capability.hbm.base_address + key_start,
                "key_offset_bytes": key_start,
                "key_value_heads": KEY_VALUE_HEADS,
                "layer": layer,
                "max_context_tokens": context_capacity,
                "resource_id": f"kv.layer.{layer}",
                "size_bytes_per_plane": state_plane_bytes,
                "value_address": capability.hbm.base_address + value_start,
                "value_offset_bytes": value_start,
            }
        )
        cursor = value_end
    mutable = len(states) * 2 * state_plane_bytes
    if mutable != STATE_COUNT * 2 * context_capacity * KV_TOKEN_BYTES:
        raise QwenFullModelPhysicalCheckError("mutable KV byte count differs")

    table_size = LAYER_COUNT * STATE_METADATA.size
    metadata_start, metadata_end = _reserved_extent(
        cursor,
        table_size,
        capability.hbm.burst_bytes,
        keep_within_shard=True,
    )
    descriptor_start, descriptor_end = _reserved_extent(
        metadata_end,
        table_size,
        capability.hbm.burst_bytes,
        keep_within_shard=True,
    )
    padding += metadata_start - cursor + descriptor_start - metadata_end
    total = align_up(descriptor_end, capability.hbm.burst_bytes)
    padding += total - descriptor_end
    if total > capability.hbm.capacity_bytes:
        raise QwenFullModelPhysicalCheckError("logical HBM image exceeds capability")
    return {
        "alignment_padding_bytes": padding,
        "base_address": capability.hbm.base_address,
        "coefficient_table": coefficient,
        "descriptor_table": {
            "address": capability.hbm.base_address + descriptor_start,
            "entry_bytes": TRANSACTION_DESCRIPTOR.size,
            "entry_count": LAYER_COUNT,
            "offset_bytes": descriptor_start,
            "payload_sha256": None,
            "size_bytes": table_size,
        },
        "immutable_weight_bytes": immutable,
        "metadata_table": {
            "address": capability.hbm.base_address + metadata_start,
            "entry_bytes": STATE_METADATA.size,
            "entry_count": LAYER_COUNT,
            "offset_bytes": metadata_start,
            "payload_sha256": None,
            "size_bytes": table_size,
        },
        "mutable_kv_bytes": mutable,
        "shard_bytes": DEFAULT_SHARD_BYTES,
        "states": states,
        "total_size_bytes": total,
        "weights": records,
    }


def _logical_tensor_bytes(tensor: ProductionTensor) -> int:
    elements = 1
    for extent in tensor.shape:
        elements *= 1 if extent == "span_tokens" else int(extent)
    if tensor.dtype == "bf16":
        width = 2
    elif tensor.dtype == "u32":
        width = 4
    else:
        raise QwenFullModelPhysicalCheckError(
            f"physical tensor {tensor.tensor_id!r} has unsupported dtype"
        )
    return elements * width


def _output_slot(operation_index: int, output_index: int) -> str | None:
    if operation_index == 0:
        return "hidden_even"
    if 1 <= operation_index <= 612:
        relative = (operation_index - 1) % 17
        layer = (operation_index - 1) // 17
        mapping: dict[int, str | tuple[str, str] | None] = {
            0: "vector_a",
            1: "wide_a",
            2: "vector_b",
            3: "wide_b",
            4: "q_norm_or_down",
            5: "k_norm",
            6: ("q_rotary", "k_rotary"),
            7: None,
            8: "attention",
            9: "norm_stage",
            10: "vector_a",
            11: "vector_b",
            12: "wide_b",
            13: "wide_c",
            14: "wide_d",
            15: "q_norm_or_down",
            16: "hidden_odd" if layer % 2 == 0 else "hidden_even",
        }
        selected = mapping[relative]
        return selected[output_index] if isinstance(selected, tuple) else selected
    final = {613: "vector_a", 614: "norm_stage", 615: "wide_a", 616: "wide_a"}
    return final.get(operation_index)


def _slot_record(
    capability: ProductionCapability,
    slot_id: str,
    bank: int,
    offset: int,
    capacity: int,
) -> dict[str, Any]:
    allocated = align_up(capacity, capability.sram.word_bytes)
    if (
        bank >= capability.sram.banks
        or offset % capability.sram.word_bytes
        or offset + allocated > capability.sram.bytes_per_bank
    ):
        raise QwenFullModelPhysicalCheckError(f"SRAM slot {slot_id!r} is illegal")
    return {
        "address": capability.sram.bank_base(bank) + offset,
        "allocated_bytes": allocated,
        "bank": bank,
        "capacity_bytes": capacity,
        "id": slot_id,
        "offset_bytes": offset,
    }


def _derive_sram(
    model: ProductionModelGraph, capability: ProductionCapability
) -> dict[str, Any]:
    slots = [
        _slot_record(capability, "runtime_ids", 0, 0, 16),
        _slot_record(capability, "attention", 0, 16, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "hidden_even", 1, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "norm_stage", 2, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "vector_a", 3, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "weight_tile", 4, 0, TILE_BYTES),
        _slot_record(capability, "accumulator", 5, 0, N_TILE * 4),
        _slot_record(capability, "wide_a", 6, 0, VOCABULARY_SIZE * BF16_BYTES),
        _slot_record(capability, "vector_b", 7, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "wide_b", 8, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot_record(capability, "wide_c", 9, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot_record(capability, "wide_d", 10, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot_record(capability, "q_norm_or_down", 11, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "hidden_odd", 12, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(
            capability,
            "k_norm",
            12,
            HIDDEN_WIDTH * BF16_BYTES,
            KV_TOKEN_BYTES,
        ),
        _slot_record(
            capability,
            "rope_coefficients",
            13,
            0,
            2 * HEAD_DIM * BF16_BYTES,
        ),
        _slot_record(capability, "q_rotary", 14, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot_record(capability, "k_rotary", 15, 0, KV_TOKEN_BYTES),
    ]
    by_bank: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    for slot in slots:
        start = slot["offset_bytes"]
        end = start + slot["allocated_bytes"]
        for other_start, other_end, other_id in by_bank[slot["bank"]]:
            if start < other_end and other_start < end:
                raise QwenFullModelPhysicalCheckError(
                    f"SRAM slots {other_id!r} and {slot['id']!r} overlap"
                )
        by_bank[slot["bank"]].append((start, end, slot["id"]))

    producers: dict[str, int] = {}
    consumers: dict[str, list[int]] = defaultdict(list)
    for operation in model.operations:
        for tensor_id in operation.inputs:
            consumers[tensor_id].append(operation.index)
        for tensor_id in operation.outputs:
            if tensor_id in producers:
                raise QwenFullModelPhysicalCheckError(
                    f"tensor {tensor_id!r} has multiple producers"
                )
            producers[tensor_id] = operation.index
    assignments: list[dict[str, Any]] = []
    handles: list[dict[str, Any]] = []
    for tensor in model.tensors:
        if tensor.role not in {"activation", "output"}:
            continue
        first = producers[tensor.tensor_id]
        operation = model.operations[first]
        slot_id = _output_slot(first, operation.outputs.index(tensor.tensor_id))
        last = max(consumers.get(tensor.tensor_id, [first]))
        if slot_id is None:
            effects = [
                effect.state_id
                for effect in operation.effects
                if effect.action == "prepare"
            ]
            if operation.kind != "KV_PREPARE" or len(effects) != 1:
                raise QwenFullModelPhysicalCheckError(
                    f"unmaterialized tensor {tensor.tensor_id!r} is not a state handle"
                )
            handles.append(
                {
                    "first_kernel_index": first,
                    "last_kernel_index": last,
                    "resource_id": effects[0],
                    "tensor_id": tensor.tensor_id,
                }
            )
        else:
            assignments.append(
                {
                    "alias_of": "output.logits"
                    if tensor.tensor_id == "output.committed_logits"
                    else None,
                    "first_kernel_index": first,
                    "last_kernel_index": last,
                    "logical_bytes": _logical_tensor_bytes(tensor),
                    "slot_id": slot_id,
                    "tensor_id": tensor.tensor_id,
                }
            )

    staged: list[dict[str, Any]] = []
    workspaces: list[dict[str, Any]] = []
    for operation in model.operations:
        weights = [
            model.tensor_by_id[tensor_id]
            for tensor_id in operation.inputs
            if model.tensor_by_id[tensor_id].role == "weight"
        ]
        if operation.kind == "RMS_NORM":
            if len(weights) != 1:
                raise QwenFullModelPhysicalCheckError("RMSNorm weight arity differs")
            weight = weights[0]
            if ".q_norm." in weight.tensor_id:
                slot_id = "wide_c"
            elif ".k_norm." in weight.tensor_id:
                slot_id = "wide_d"
            elif ".post_attention_layernorm." in weight.tensor_id:
                slot_id = "wide_a"
            else:
                slot_id = "norm_stage"
            staged.append(
                {
                    "kernel_index": operation.index,
                    "logical_bytes": _logical_tensor_bytes(weight),
                    "slot_id": slot_id,
                    "tensor_id": weight.tensor_id,
                }
            )
        elif operation.kind == "MATMUL":
            workspaces.extend(
                [
                    {
                        "kernel_index": operation.index,
                        "role": "weight_tile",
                        "slot_id": "weight_tile",
                    },
                    {
                        "kernel_index": operation.index,
                        "role": "fp32_accumulator",
                        "slot_id": "accumulator",
                    },
                ]
            )
        elif operation.kind == "ROPE":
            workspaces.append(
                {
                    "kernel_index": operation.index,
                    "role": "rope_coefficient_row",
                    "slot_id": "rope_coefficients",
                }
            )

    capacities = {slot["id"]: slot["capacity_bytes"] for slot in slots}
    intervals: dict[str, list[tuple[int, int, str, str | None]]] = defaultdict(list)
    for item in assignments:
        if item["logical_bytes"] > capacities[item["slot_id"]]:
            raise QwenFullModelPhysicalCheckError(
                f"tensor {item['tensor_id']!r} exceeds its SRAM slot"
            )
        intervals[item["slot_id"]].append(
            (
                item["first_kernel_index"],
                item["last_kernel_index"],
                item["tensor_id"],
                item["alias_of"],
            )
        )
    for item in staged:
        if item["logical_bytes"] > capacities[item["slot_id"]]:
            raise QwenFullModelPhysicalCheckError(
                f"weight {item['tensor_id']!r} exceeds its staging slot"
            )
        intervals[item["slot_id"]].append(
            (item["kernel_index"], item["kernel_index"], item["tensor_id"], None)
        )
    for slot_id, raw in intervals.items():
        ordered = sorted(raw)
        for index, current in enumerate(ordered):
            for previous in ordered[:index]:
                if current[0] > previous[1] or previous[0] > current[1]:
                    continue
                if current[3] != previous[2] and previous[3] != current[2]:
                    raise QwenFullModelPhysicalCheckError(
                        f"SRAM slot {slot_id!r} has overlapping values "
                        f"{previous[2]!r} and {current[2]!r}"
                    )
    return {
        "addressing": "bank_base_plus_byte_offset",
        "physical_profile": "single_token_forward",
        "slots": slots,
        "staged_weight_assignments": staged,
        "state_handle_assignments": handles,
        "tensor_assignments": assignments,
        "workspace_assignments": workspaces,
    }


def _verify_source_copies(
    root: Path,
    source_lock: Mapping[str, Any],
    source_paths: Mapping[str, Path],
) -> None:
    for role in sorted(SOURCE_COPIES):
        record = source_lock["artifacts"][role]
        candidate = _artifact(root, record["path"], f"source copy {role}")
        source_payload = source_paths[role].read_bytes()
        candidate_payload = candidate.read_bytes()
        if candidate_payload != source_payload:
            raise QwenFullModelPhysicalCheckError(
                f"source copy {role!r} differs byte-for-byte"
            )
        digest, size = sha256_file(candidate)
        if (digest, size) != (record["sha256"], record["size_bytes"]):
            raise QwenFullModelPhysicalCheckError(
                f"source copy {role!r} identity differs"
            )


def _verify_hbm_structure(
    candidate: Mapping[str, Any], expected: dict[str, Any]
) -> Mapping[str, Any]:
    if not isinstance(candidate, dict):
        raise QwenFullModelPhysicalCheckError("physical_plan.hbm must be an object")
    exact_keys(
        candidate,
        {
            "alignment_padding_bytes",
            "base_address",
            "coefficient_table",
            "descriptor_table",
            "image",
            "immutable_weight_bytes",
            "metadata_table",
            "mutable_kv_bytes",
            "shard_bytes",
            "states",
            "total_size_bytes",
            "weights",
        },
        set(),
        "physical_plan.hbm",
    )
    image = candidate["image"]
    if not isinstance(image, dict):
        raise QwenFullModelPhysicalCheckError("physical_plan.hbm.image differs")
    candidate_without_image = dict(candidate)
    candidate_without_image.pop("image")
    if not isinstance(candidate_without_image.get("weights"), list):
        raise QwenFullModelPhysicalCheckError("HBM weight table differs")
    if len(candidate_without_image["weights"]) != len(expected["weights"]):
        raise QwenFullModelPhysicalCheckError("HBM weight record count differs")
    for index, (observed, derived) in enumerate(
        zip(candidate_without_image["weights"], expected["weights"], strict=True)
    ):
        if not isinstance(observed, dict):
            raise QwenFullModelPhysicalCheckError(
                f"HBM weight record {index} is not an object"
            )
        deployed = require_sha256(
            observed.get("deployed_payload_sha256"),
            f"HBM weight {index}.deployed_payload_sha256",
        )
        derived["deployed_payload_sha256"] = deployed
    for table_name in ("metadata_table", "descriptor_table"):
        table = candidate_without_image.get(table_name)
        if not isinstance(table, dict):
            raise QwenFullModelPhysicalCheckError(f"HBM {table_name} differs")
        expected[table_name]["payload_sha256"] = require_sha256(
            table.get("payload_sha256"), f"HBM {table_name}.payload_sha256"
        )
    if candidate_without_image != expected:
        raise QwenFullModelPhysicalCheckError(
            "HBM region map differs from the independent graph/checkpoint walk"
        )
    return image


def _verify_hbm_image(
    root: Path,
    image: Mapping[str, Any],
    *,
    expected_size: int,
) -> None:
    if not isinstance(image, dict):
        raise QwenFullModelPhysicalCheckError("HBM image record must be an object")
    exact_keys(
        image,
        {"logical_sha256", "shard_bytes", "shards", "size_bytes"},
        set(),
        "HBM image",
    )
    logical_identity = require_sha256(
        image["logical_sha256"], "HBM image.logical_sha256"
    )
    shards = image["shards"]
    if (
        image["shard_bytes"] != DEFAULT_SHARD_BYTES
        or image["size_bytes"] != expected_size
        or not isinstance(shards, list)
        or len(shards)
        != (expected_size + DEFAULT_SHARD_BYTES - 1) // DEFAULT_SHARD_BYTES
    ):
        raise QwenFullModelPhysicalCheckError("HBM shard geometry differs")
    logical = hashlib.sha256()
    cursor = 0
    seen: set[str] = set()
    for expected_index, record in enumerate(shards):
        if not isinstance(record, dict):
            raise QwenFullModelPhysicalCheckError(
                f"HBM shard {expected_index} must be an object"
            )
        exact_keys(
            record,
            {"index", "logical_offset", "path", "sha256", "size_bytes"},
            set(),
            f"HBM shard {expected_index}",
        )
        digest = require_sha256(record["sha256"], f"HBM shard {expected_index}.sha256")
        size = min(DEFAULT_SHARD_BYTES, expected_size - cursor)
        expected_path = f"memory/hbm/hbm.{expected_index:05d}.{digest}.bin"
        if (
            record["index"] != expected_index
            or record["logical_offset"] != cursor
            or record["size_bytes"] != size
            or record["path"] != expected_path
            or expected_path in seen
        ):
            raise QwenFullModelPhysicalCheckError(
                f"HBM shard {expected_index} record differs"
            )
        seen.add(expected_path)
        path = _artifact(root, expected_path, f"HBM shard {expected_index}")
        shard_digest = hashlib.sha256()
        observed_size = 0
        try:
            with path.open("rb") as handle:
                while payload := handle.read(8 * 1024 * 1024):
                    shard_digest.update(payload)
                    logical.update(payload)
                    observed_size += len(payload)
        except OSError as exc:
            raise QwenFullModelPhysicalCheckError(
                f"cannot hash HBM shard {expected_index}: {exc}"
            ) from exc
        if observed_size != size or shard_digest.hexdigest() != digest:
            raise QwenFullModelPhysicalCheckError(
                f"HBM shard {expected_index} content differs"
            )
        cursor += size
    if cursor != expected_size or logical.hexdigest() != logical_identity:
        raise QwenFullModelPhysicalCheckError("logical HBM image identity differs")


def _checkpoint_deployed_digest(
    reader: LockedCheckpointReader, record: Mapping[str, Any]
) -> str:
    deployed = hashlib.sha256()
    if str(record["layout"]).startswith("direct_"):
        reader.consume_tensor_payload(record["source"]["tensor_name"], deployed.update)
        return deployed.hexdigest()

    details = record["layout_details"]
    block_bytes = details["n_tile"] * details["k"] * BF16_BYTES
    pending = bytearray()
    blocks = 0

    def consume(payload: bytes) -> None:
        nonlocal blocks
        pending.extend(payload)
        while len(pending) >= block_bytes:
            raw = bytes(pending[:block_bytes])
            del pending[:block_bytes]
            rows = np.frombuffer(raw, dtype="<u2").reshape(
                details["n_tile"], details["k"]
            )
            for k_start in range(0, details["k"], details["k_tile"]):
                tile = np.ascontiguousarray(
                    rows[:, k_start : k_start + details["k_tile"]], dtype="<u2"
                ).tobytes(order="C")
                if len(tile) != details["tile_bytes"]:
                    raise QwenFullModelPhysicalCheckError(
                        f"reconstructed tile for {record['tensor_id']!r} differs"
                    )
                deployed.update(tile)
            blocks += 1

    reader.consume_tensor_payload(
        record["source"]["tensor_name"], consume, chunk_bytes=block_bytes
    )
    if pending or blocks != details["n_tiles"]:
        raise QwenFullModelPhysicalCheckError(
            f"checkpoint reconstruction for {record['tensor_id']!r} is incomplete"
        )
    return deployed.hexdigest()


def _metadata_payload(hbm: Mapping[str, Any]) -> bytes:
    return b"".join(
        STATE_METADATA.pack(
            STATE_MAGIC,
            0,
            0,
            state["max_context_tokens"],
            state["key_address"],
            state["value_address"],
            state["layer"],
            bytes(8),
        )
        for state in hbm["states"]
    )


def _descriptor_payload(hbm: Mapping[str, Any]) -> bytes:
    metadata_base = hbm["metadata_table"]["address"]
    return b"".join(
        TRANSACTION_DESCRIPTOR.pack(
            TRANSACTION_MAGIC,
            TRANSACTION_ID,
            0,
            0,
            1,
            1,
            metadata_base + state["layer"] * STATE_METADATA.size,
            bytes(8),
        )
        for state in hbm["states"]
    )


def _require_payload(
    reader: HBMShardReader,
    offset: int,
    expected: bytes,
    label: str,
) -> None:
    observed = reader.read(offset, len(expected))
    if observed != expected:
        raise QwenFullModelPhysicalCheckError(f"{label} payload differs")


def _verify_hbm_payloads(
    *,
    root: Path,
    snapshot: Path,
    checkpoint_lock: Mapping[str, Any],
    hbm: Mapping[str, Any],
) -> None:
    image = hbm["image"]
    occupied: list[tuple[int, int, str]] = []
    try:
        with HBMShardReader(root, image["shards"], verify_hashes=False) as hbm_reader:
            if hbm_reader.total_size != hbm["total_size_bytes"]:
                raise QwenFullModelPhysicalCheckError("HBM reader extent differs")
            with LockedCheckpointReader(snapshot, dict(checkpoint_lock)) as checkpoint:
                for record in hbm["weights"]:
                    expected_digest = _checkpoint_deployed_digest(checkpoint, record)
                    actual_digest = hbm_reader.sha256(
                        record["offset_bytes"], record["size_bytes"]
                    )
                    if (
                        expected_digest != record["deployed_payload_sha256"]
                        or actual_digest != expected_digest
                    ):
                        raise QwenFullModelPhysicalCheckError(
                            f"deployed weight {record['tensor_id']!r} differs"
                        )
                    occupied.append(
                        (
                            record["offset_bytes"],
                            record["offset_bytes"] + record["size_bytes"],
                            record["tensor_id"],
                        )
                    )
                if len(checkpoint.accessed_tensor_names) != WEIGHT_COUNT:
                    raise QwenFullModelPhysicalCheckError(
                        "checker did not consume all 399 checkpoint weights"
                    )

            coefficient_record = hbm["coefficient_table"]
            coefficient_positions = coefficient_record["positions"]
            coefficient_sha256 = QUALIFIED_COEFFICIENT_TABLE_SHA256.get(
                coefficient_positions
            )
            if (
                coefficient_sha256 is None
                or coefficient_record["size_bytes"]
                != coefficient_positions * 2 * HEAD_DIM * BF16_BYTES
                or hbm_reader.sha256(
                    coefficient_record["offset_bytes"],
                    coefficient_record["size_bytes"],
                )
                != coefficient_sha256
            ):
                raise QwenFullModelPhysicalCheckError(
                    "authenticated RoPE coefficient table differs"
                )
            occupied.append(
                (
                    coefficient_record["offset_bytes"],
                    coefficient_record["offset_bytes"]
                    + coefficient_record["size_bytes"],
                    "rope.coefficients",
                )
            )

            for state in hbm["states"]:
                for plane in ("key", "value"):
                    start = state[f"{plane}_offset_bytes"]
                    size = state["size_bytes_per_plane"]
                    hbm_reader.require_zero(start, size)
                    occupied.append(
                        (start, start + size, f"{state['resource_id']}.{plane}")
                    )

            metadata = _metadata_payload(hbm)
            descriptors = _descriptor_payload(hbm)
            for table_name, payload in (
                ("metadata_table", metadata),
                ("descriptor_table", descriptors),
            ):
                record = hbm[table_name]
                if (
                    len(payload) != record["size_bytes"]
                    or hashlib.sha256(payload).hexdigest() != record["payload_sha256"]
                ):
                    raise QwenFullModelPhysicalCheckError(
                        f"derived {table_name} identity differs"
                    )
                _require_payload(
                    hbm_reader,
                    record["offset_bytes"],
                    payload,
                    table_name,
                )
                occupied.append(
                    (
                        record["offset_bytes"],
                        record["offset_bytes"] + record["size_bytes"],
                        table_name,
                    )
                )

            cursor = 0
            for start, end, label in sorted(occupied):
                if start < cursor or end <= start:
                    raise QwenFullModelPhysicalCheckError(
                        f"HBM extent {label!r} overlaps or is empty"
                    )
                hbm_reader.require_zero(cursor, start - cursor)
                cursor = end
            hbm_reader.require_zero(cursor, hbm["total_size_bytes"] - cursor)
    except (CheckpointError, HBMShardError, OSError, ValueError) as exc:
        if isinstance(exc, QwenFullModelPhysicalCheckError):
            raise
        raise QwenFullModelPhysicalCheckError(
            f"HBM inverse reconstruction failed: {exc}"
        ) from exc


def _state_for_operation(operation: ProductionOperation, action: str) -> str:
    resources = [
        effect.state_id for effect in operation.effects if effect.action == action
    ]
    if len(resources) != 1:
        raise QwenFullModelPhysicalCheckError(
            f"operation {operation.operation_id!r} has an ambiguous {action} effect"
        )
    return resources[0]


def _verify_command_program(
    *,
    model: ProductionModelGraph,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    payload: bytes,
    candidate_program: Mapping[str, Any],
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    try:
        observed = decode(payload)
    except ProductionCommandError as exc:
        raise QwenFullModelPhysicalCheckError(
            f"command program is malformed: {exc}"
        ) from exc
    _, major, minor = struct.unpack_from("<8sHH", payload)
    if (major, minor) != (ABI_MAJOR, SELECTION_ABI_MINOR):
        raise QwenFullModelPhysicalCheckError("command ABI differs")

    slots = {record["id"]: record for record in sram["slots"]}
    assignments = {record["tensor_id"]: record for record in sram["tensor_assignments"]}
    weights = {record["consumer_kernel_index"]: record for record in hbm["weights"]}
    states = {record["resource_id"]: record for record in hbm["states"]}
    staged = {
        record["kernel_index"]: record for record in sram["staged_weight_assignments"]
    }
    if (
        len(slots) != len(sram["slots"])
        or len(assignments) != len(sram["tensor_assignments"])
        or len(weights) != WEIGHT_COUNT
        or len(states) != STATE_COUNT
        or len(staged) != 145
    ):
        raise QwenFullModelPhysicalCheckError("physical lookup tables are ambiguous")

    def address(tensor_id: str) -> int:
        try:
            return int(slots[assignments[tensor_id]["slot_id"]]["address"])
        except KeyError as exc:
            raise QwenFullModelPhysicalCheckError(
                f"tensor {tensor_id!r} has no physical address"
            ) from exc

    cursor = 0
    counts: Counter[str] = Counter()

    def expect(command: ProductionCommand) -> None:
        nonlocal cursor
        if command.index != cursor:
            raise QwenFullModelPhysicalCheckError(
                "independent command derivation lost index causality"
            )
        if cursor >= len(observed) or observed[cursor] != command:
            actual = observed[cursor].to_dict() if cursor < len(observed) else None
            raise QwenFullModelPhysicalCheckError(
                f"command {cursor} differs: observed={actual!r}, "
                f"expected={command.to_dict()!r}"
            )
        counts[command.opcode.name] += 1
        cursor += 1

    ranges: list[dict[str, Any]] = []
    for operation in model.operations:
        begin = cursor
        if operation.kind == "EMBEDDING_LOOKUP":
            record = weights[operation.index]
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=record["address"],
                    source1=slots["runtime_ids"]["address"],
                    destination=address(operation.outputs[0]),
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=VOCABULARY_SIZE,
                    size3=4,
                )
            )
        elif operation.kind == "RMS_NORM":
            record = weights[operation.index]
            stage_address = slots[staged[operation.index]["slot_id"]]["address"]
            width = operation.attributes.get("normalization_width")
            output_width = model.tensor_by_id[operation.outputs[0]].shape[-1]
            if (
                isinstance(width, bool)
                or not isinstance(width, int)
                or not isinstance(output_width, int)
                or output_width % width
            ):
                raise QwenFullModelPhysicalCheckError(
                    f"RMSNorm {operation.operation_id!r} row derivation differs"
                )
            rows = output_width // width
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=record["address"],
                    destination=stage_address,
                    size0=record["size_bytes"],
                )
            )
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.RMSNORM_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=stage_address,
                    destination=address(operation.outputs[0]),
                    size0=rows,
                    size1=width,
                    size2=EPSILON_CODE,
                )
            )
        elif operation.kind == "MATMUL":
            record = weights[operation.index]
            details = record["layout_details"]
            tile_index = 0
            for n_index in range(details["n_tiles"]):
                n_start = n_index * details["n_tile"]
                for k_index in range(details["k_tiles"]):
                    k_start = k_index * details["k_tile"]
                    expect(
                        ProductionCommand(
                            index=cursor,
                            opcode=Opcode.DMA_HBM_TO_SRAM,
                            engine=Engine.DMA,
                            kernel_index=operation.index,
                            source0=record["address"]
                            + tile_index * details["tile_bytes"],
                            destination=slots["weight_tile"]["address"],
                            size0=details["tile_bytes"],
                        )
                    )
                    flags = (MATMUL_INIT if k_index == 0 else 0) | (
                        MATMUL_FINAL if k_index + 1 == details["k_tiles"] else 0
                    )
                    expect(
                        ProductionCommand(
                            index=cursor,
                            opcode=Opcode.MATMUL_BF16_TILE,
                            engine=Engine.TENSOR,
                            flags=flags,
                            kernel_index=operation.index,
                            source0=address(operation.inputs[0]) + k_start * BF16_BYTES,
                            source1=slots["weight_tile"]["address"],
                            destination=slots["accumulator"]["address"],
                            auxiliary=address(operation.outputs[0])
                            + n_start * BF16_BYTES,
                            size0=1,
                            size1=details["n_tile"],
                            size2=details["k_tile"],
                        )
                    )
                    tile_index += 1
            if tile_index != details["tile_count"]:
                raise QwenFullModelPhysicalCheckError(
                    f"matrix {operation.operation_id!r} tile derivation differs"
                )
        elif operation.kind == "ROPE":
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=hbm["coefficient_table"]["address"],
                    source1=slots["runtime_ids"]["address"] + 4,
                    destination=slots["rope_coefficients"]["address"],
                    size0=hbm["coefficient_table"]["row_bytes"],
                    size1=hbm["coefficient_table"]["row_bytes"],
                    size2=context_capacity,
                    size3=4,
                )
            )
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.ROPE_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=address(operation.inputs[1]),
                    destination=address(operation.outputs[0]),
                    auxiliary=address(operation.outputs[1]),
                    size0=QUERY_HEADS,
                    size1=KEY_VALUE_HEADS,
                    size2=HEAD_DIM,
                    size3=slots["rope_coefficients"]["address"],
                )
            )
        elif operation.kind == "KV_PREPARE":
            state = states[_state_for_operation(operation, "prepare")]
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.KV_PREPARE_BF16,
                    engine=Engine.STATE,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=address(operation.inputs[1]),
                    destination=state["key_address"],
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=KEY_VALUE_HEADS,
                    size2=HEAD_DIM,
                )
            )
        elif operation.kind == "ATTENTION":
            state = states[_state_for_operation(operation, "read_prepared")]
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.GQA_ATTENTION_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=state["key_address"],
                    destination=address(operation.outputs[0]),
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=QUERY_HEADS,
                    size2=KEY_VALUE_HEADS,
                    size3=HEAD_DIM,
                )
            )
        elif operation.kind == "ADD":
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.ADD_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=address(operation.inputs[1]),
                    destination=address(operation.outputs[0]),
                    size0=1,
                    size1=HIDDEN_WIDTH,
                )
            )
        elif operation.kind == "SILU_MUL":
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.SILU_MUL_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=address(operation.inputs[1]),
                    destination=address(operation.outputs[0]),
                    size0=1,
                    size1=INTERMEDIATE_WIDTH,
                )
            )
        elif operation.kind == "LAST_TOKEN_SELECT":
            input_assignment = assignments[operation.inputs[0]]
            if (
                input_assignment["last_kernel_index"] != operation.index
                or model.tensor_by_id[operation.inputs[0]].shape[1] != "span_tokens"
            ):
                raise QwenFullModelPhysicalCheckError(
                    "last-token selection does not consume the live final row"
                )
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.DMA_SRAM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=address(operation.inputs[0]),
                    source1=slots["runtime_ids"]["address"] + 8,
                    destination=address(operation.outputs[0]),
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=1,
                    size3=4,
                )
            )
        elif operation.kind == "STATE_COMMIT":
            committed = [
                effect.state_id
                for effect in operation.effects
                if effect.action == "commit"
            ]
            if operation.index != OPERATION_COUNT - 1 or committed != [
                f"kv.layer.{layer}" for layer in range(LAYER_COUNT)
            ]:
                raise QwenFullModelPhysicalCheckError(
                    "terminal atomic state-effect set differs"
                )
            expect(
                ProductionCommand(
                    index=cursor,
                    opcode=Opcode.STATE_COMMIT,
                    engine=Engine.STATE,
                    kernel_index=NO_KERNEL,
                    source0=hbm["metadata_table"]["address"],
                    source1=hbm["descriptor_table"]["address"],
                    size0=context_capacity,
                    size1=STATE_COUNT,
                )
            )
        else:
            raise QwenFullModelPhysicalCheckError(
                f"operation {operation.operation_id!r} has no command contract"
            )
        ranges.append(
            {
                "command_count": cursor - begin,
                "command_start": begin,
                "kernel_index": operation.index,
                "operation_id": operation.operation_id,
            }
        )
    expect(
        ProductionCommand(
            index=cursor,
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        )
    )
    if cursor != len(observed) or cursor != EXPECTED_COMMAND_COUNT:
        raise QwenFullModelPhysicalCheckError("command count differs")
    opcode_counts = dict(sorted(counts.items()))
    if opcode_counts != EXPECTED_OPCODE_COUNTS:
        raise QwenFullModelPhysicalCheckError("command-family counts differ")
    expected_program = {
        "abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
        "command_count": EXPECTED_COMMAND_COUNT,
        "kernel_command_ranges": ranges,
        "opcode_counts": opcode_counts,
        "path": COMMAND_PATH,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if candidate_program != expected_program:
        raise QwenFullModelPhysicalCheckError(
            "physical-plan command record differs from independent derivation"
        )
    return expected_program


def _derive_capacity(
    *,
    capability: ProductionCapability,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
) -> dict[str, Any]:
    allocated = [0] * capability.sram.banks
    for slot in sram["slots"]:
        allocated[slot["bank"]] += slot["allocated_bytes"]
    return _identified(
        {
            "command_capacity": {
                "available": capability.limits["max_commands"],
                "margin": capability.limits["max_commands"] - EXPECTED_COMMAND_COUNT,
                "required": EXPECTED_COMMAND_COUNT,
            },
            "context_capacity_tokens": hbm["coefficient_table"]["positions"],
            "hbm_capacity": {
                "alignment_padding_bytes": hbm["alignment_padding_bytes"],
                "available_bytes": capability.hbm.capacity_bytes,
                "immutable_weight_bytes": hbm["immutable_weight_bytes"],
                "margin_bytes": capability.hbm.capacity_bytes - hbm["total_size_bytes"],
                "metadata_and_descriptor_bytes": hbm["metadata_table"]["size_bytes"]
                + hbm["descriptor_table"]["size_bytes"],
                "mutable_kv_bytes": hbm["mutable_kv_bytes"],
                "required_bytes": hbm["total_size_bytes"],
                "rope_coefficient_bytes": hbm["coefficient_table"]["size_bytes"],
            },
            "no_host_paging": True,
            "physical_profile": "single_token_forward",
            "schema": CAPACITY_SCHEMA,
            "sram_capacity": {
                "available_bytes": capability.sram.capacity_bytes,
                "bank_allocated_bytes": allocated,
                "max_bank_allocated_bytes": max(allocated),
                "slots": len(sram["slots"]),
            },
            "state_resource_count": STATE_COUNT,
            "weight_count": WEIGHT_COUNT,
        },
        "capacity_certificate_id",
    )


def _verify_candidate_file_set(
    root: Path,
    *,
    source_lock: Mapping[str, Any],
    hbm_image: Mapping[str, Any],
) -> bool:
    expected = {
        "capability.json",
        KERNEL_IR_PATH,
        PHYSICAL_PLAN_PATH,
        CAPACITY_PATH,
        COMMAND_PATH,
        REQUEST_PATH,
        "source.lock.json",
    }
    expected.update(record["path"] for record in source_lock["artifacts"].values())
    expected.update(record["path"] for record in hbm_image["shards"])
    observed: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise QwenFullModelPhysicalCheckError(
                f"deployment contains a symbolic link: {path.relative_to(root)}"
            )
        if path.is_file():
            observed.add(path.relative_to(root).as_posix())
    published = {CHECK_PATH, MANIFEST_PATH}
    if observed == expected:
        return False
    if observed == expected | published:
        return True
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    raise QwenFullModelPhysicalCheckError(
        f"candidate file set differs: missing={missing}, extra={extra}"
    )


def _manifest_artifact(root: Path, relative: str, role: str) -> dict[str, Any]:
    path = _artifact(root, relative, f"manifest artifact {relative}")
    digest, size = sha256_file(path)
    return {
        "path": _safe_relative(relative, f"manifest artifact {relative}.path"),
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _expected_manifest(
    root: Path,
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    source_lock: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
    physical_plan: Mapping[str, Any],
    capacity: Mapping[str, Any],
    independent_check: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = [
        _manifest_artifact(root, "capability.json", "capability"),
        _manifest_artifact(root, CHECK_PATH, "independent_check"),
        _manifest_artifact(root, KERNEL_IR_PATH, "tensor_kernel_ir"),
        _manifest_artifact(root, PHYSICAL_PLAN_PATH, "physical_plan"),
        _manifest_artifact(root, CAPACITY_PATH, "capacity_certificate"),
        _manifest_artifact(root, COMMAND_PATH, "command_program"),
        _manifest_artifact(root, REQUEST_PATH, "execution_request"),
        _manifest_artifact(root, "source.lock.json", "source_lock"),
    ]
    for role, record in source_lock["artifacts"].items():
        artifacts.append(_manifest_artifact(root, record["path"], f"source_{role}"))
    for shard in physical_plan["hbm"]["image"]["shards"]:
        artifacts.append(
            {
                "path": shard["path"],
                "role": "hbm_shard",
                "sha256": shard["sha256"],
                "size_bytes": shard["size_bytes"],
            }
        )
    artifacts.sort(key=lambda item: item["path"])
    return _identified(
        {
            "artifacts": artifacts,
            "build_class": "independently_reconstructed_physical_deployment",
            "capability_id": capability.capability_id,
            "capacity_certificate_id": capacity["capacity_certificate_id"],
            "claim_boundary": CLAIM_BOUNDARY,
            "command_abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
            "compiler_version": COMPILER_VERSION,
            "graph_id": model.graph_id,
            "independent_check_id": independent_check["check_id"],
            "kernel_ir_id": kernel_ir["kernel_ir_id"],
            "physical_plan_id": physical_plan["physical_plan_id"],
            "schema": MANIFEST_SCHEMA,
            "source_lock_id": source_lock["source_lock_id"],
        },
        "build_id",
    )


def check_qwen_full_model_physical_deployment(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    semantic_coverage_path: Path,
    semantic_kernel_ir_path: Path,
    semantic_check_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct a QW-FM2 candidate before or after publish."""

    try:
        snapshot = Path(snapshot).resolve(strict=True)
        root = Path(root).resolve(strict=True)
        if not snapshot.is_dir() or not root.is_dir():
            raise QwenFullModelPhysicalCheckError(
                "snapshot and candidate root must be directories"
            )
        source_arguments = {
            "checkpoint_lock_path": Path(checkpoint_lock_path).resolve(strict=True),
            "model_graph_path": Path(model_graph_path).resolve(strict=True),
            "capability_path": Path(capability_path).resolve(strict=True),
            "semantic_coverage_path": Path(semantic_coverage_path).resolve(strict=True),
            "semantic_kernel_ir_path": Path(semantic_kernel_ir_path).resolve(
                strict=True
            ),
            "semantic_check_path": Path(semantic_check_path).resolve(strict=True),
        }
        (
            checkpoint_lock,
            model,
            capability,
            coverage,
            semantic_kernel_ir,
            semantic_check,
            source_paths,
        ) = _load_sources(**source_arguments)

        source_lock = _canonical(
            _artifact(root, "source.lock.json", "source lock"), "source lock"
        )
        expected_source_lock = _expected_source_lock(
            model=model,
            capability=capability,
            checkpoint_lock=checkpoint_lock,
            coverage=coverage,
            kernel_ir=semantic_kernel_ir,
            semantic_check=semantic_check,
            source_paths=source_paths,
        )
        if source_lock != expected_source_lock:
            raise QwenFullModelPhysicalCheckError("source lock differs")
        _identity(source_lock, "source_lock_id", "source lock")

        deployed_capability = _canonical(
            _artifact(root, "capability.json", "deployed capability"),
            "deployed capability",
        )
        if deployed_capability != capability.to_dict():
            raise QwenFullModelPhysicalCheckError("deployed capability differs")
        deployed_kernel_ir = _canonical(
            _artifact(root, KERNEL_IR_PATH, "deployed Kernel IR"),
            "deployed Kernel IR",
        )
        if deployed_kernel_ir != semantic_kernel_ir:
            raise QwenFullModelPhysicalCheckError("deployed Kernel IR differs")
        request = _canonical(
            _artifact(root, REQUEST_PATH, "execution request"),
            "execution request",
        )
        if request != _expected_request(model):
            raise QwenFullModelPhysicalCheckError("execution request differs")
        _identity(request, "request_id", "execution request")

        capacity = _canonical(
            _artifact(root, CAPACITY_PATH, "capacity certificate"),
            "capacity certificate",
        )
        physical_plan = _canonical(
            _artifact(root, PHYSICAL_PLAN_PATH, "physical plan"), "physical plan"
        )
        _identity(capacity, "capacity_certificate_id", "capacity certificate")
        _identity(physical_plan, "physical_plan_id", "physical plan")
        exact_keys(
            physical_plan,
            {
                "capability_id",
                "capacity_certificate_id",
                "claim_boundary",
                "command_program",
                "graph_id",
                "hbm",
                "physical_plan_id",
                "physical_profile",
                "schema",
                "semantic_kernel_ir_id",
                "source_lock_id",
                "sram",
            },
            set(),
            "physical plan",
        )
        if (
            physical_plan["schema"] != PHYSICAL_PLAN_SCHEMA
            or physical_plan["capability_id"] != capability.capability_id
            or physical_plan["capacity_certificate_id"]
            != capacity["capacity_certificate_id"]
            or physical_plan["claim_boundary"] != CLAIM_BOUNDARY
            or physical_plan["graph_id"] != model.graph_id
            or physical_plan["physical_profile"] != "single_token_forward"
            or physical_plan["semantic_kernel_ir_id"]
            != semantic_kernel_ir["kernel_ir_id"]
            or physical_plan["source_lock_id"] != source_lock["source_lock_id"]
        ):
            raise QwenFullModelPhysicalCheckError("physical-plan binding differs")

        derived_hbm = _derive_hbm(model, capability, checkpoint_lock)
        image = _verify_hbm_structure(physical_plan["hbm"], derived_hbm)
        derived_hbm["image"] = image
        derived_sram = _derive_sram(model, capability)
        if physical_plan["sram"] != derived_sram:
            raise QwenFullModelPhysicalCheckError(
                "SRAM plan differs from independent lifetime allocation"
            )

        command_path = _artifact(root, COMMAND_PATH, "command program")
        command_payload = command_path.read_bytes()
        _verify_command_program(
            model=model,
            hbm=derived_hbm,
            sram=derived_sram,
            payload=command_payload,
            candidate_program=physical_plan["command_program"],
        )
        expected_capacity = _derive_capacity(
            capability=capability, hbm=derived_hbm, sram=derived_sram
        )
        if capacity != expected_capacity:
            raise QwenFullModelPhysicalCheckError("capacity certificate differs")
        if (
            capacity["no_host_paging"] is not True
            or capacity["hbm_capacity"]["margin_bytes"] < 0
            or capacity["command_capacity"]["margin"] < 0
            or capacity["sram_capacity"]["max_bank_allocated_bytes"]
            > capability.sram.bytes_per_bank
        ):
            raise QwenFullModelPhysicalCheckError(
                "capacity certificate relies on overflow or host paging"
            )

        _verify_source_copies(root, source_lock, source_paths)
        published = _verify_candidate_file_set(
            root, source_lock=source_lock, hbm_image=image
        )
        _verify_hbm_image(root, image, expected_size=derived_hbm["total_size_bytes"])
        _verify_hbm_payloads(
            root=root,
            snapshot=snapshot,
            checkpoint_lock=checkpoint_lock,
            hbm=derived_hbm,
        )

        body = {
            "capability_id": capability.capability_id,
            "capacity_certificate_id": capacity["capacity_certificate_id"],
            "checker_version": CHECKER_VERSION,
            "checks": {
                "canonical_and_exact_file_set": True,
                "capacity_and_no_host_paging": True,
                "checkpoint_payload_reconstruction": True,
                "command_and_kernel_range_derivation": True,
                "complete_graph_and_semantic_binding": True,
                "hbm_region_and_shard_integrity": True,
                "independent_inverse_reconstruction": True,
                "rope_and_state_table_payloads": True,
                "source_lock_and_immutable_copies": True,
                "sram_bank_capacity_and_liveness": True,
                "terminal_36_resource_atomic_commit": True,
                "zero_initialized_transactional_state": True,
            },
            "command_count": EXPECTED_COMMAND_COUNT,
            "graph_id": model.graph_id,
            "hbm_logical_sha256": image["logical_sha256"],
            "operation_count": OPERATION_COUNT,
            "physical_plan_id": physical_plan["physical_plan_id"],
            "schema": CHECK_SCHEMA,
            "source_lock_id": source_lock["source_lock_id"],
            "state_resource_count": STATE_COUNT,
            "status": "pass",
            "tensor_count": TENSOR_COUNT,
            "weight_count": WEIGHT_COUNT,
        }
        result = _identified(body, "check_id")
        if published:
            retained_check = _canonical(
                _artifact(root, CHECK_PATH, "retained independent check"),
                "retained independent check",
            )
            if retained_check != result:
                raise QwenFullModelPhysicalCheckError(
                    "retained independent check differs from fresh reconstruction"
                )
            _identity(retained_check, "check_id", "retained independent check")
            manifest = _canonical(
                _artifact(root, MANIFEST_PATH, "deployment manifest"),
                "deployment manifest",
            )
            expected_manifest = _expected_manifest(
                root,
                model=model,
                capability=capability,
                source_lock=source_lock,
                kernel_ir=semantic_kernel_ir,
                physical_plan=physical_plan,
                capacity=capacity,
                independent_check=result,
            )
            if manifest != expected_manifest:
                raise QwenFullModelPhysicalCheckError(
                    "deployment manifest differs from fresh reconstruction"
                )
            _identity(manifest, "build_id", "deployment manifest")
        return result
    except QwenFullModelPhysicalCheckError:
        raise
    except (
        ArtifactError,
        CheckpointError,
        HBMShardError,
        OSError,
        ProductionCapabilityError,
        ProductionCommandError,
        ProductionModelGraphError,
        TypeError,
        ValueError,
    ) as exc:
        raise QwenFullModelPhysicalCheckError(
            f"independent Qwen physical check failed: {exc}"
        ) from exc


__all__ = [
    "CHECKER_VERSION",
    "CHECK_SCHEMA",
    "QwenFullModelPhysicalCheckError",
    "check_qwen_full_model_physical_deployment",
]
