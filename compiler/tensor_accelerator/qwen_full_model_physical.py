"""Deterministic full-model HBM/SRAM compiler for Qwen3-8B.

The emitted deployment is a one-token-forward command template over the entire
617-operation graph.  Repeated prefill and decode requests reuse the same
immutable weights, SRAM slots, command program, and 36 persistent KV resources.
The compiler streams all 399 locked checkpoint tensors into sparse mmap-backed
HBM shards and never constructs a monolithic model payload in host memory.

This module establishes physical compilation and independent reconstruction.
It does not execute the model or make timing, RTL, physical-node, decoding, or
comparison claims.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE
from runtime.tensor_accelerator.rope import coefficient_table_bf16

from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from .hbm_shards import DEFAULT_SHARD_BYTES, HBMShardError, HBMShardWriter
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
    encode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    ProductionTensor,
    load_production_model_graph,
)


COMPILER_VERSION = "tensor-accelerator-qwen-full-model-physical-0.1.0"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_source_lock.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_physical_plan.v1"
CAPACITY_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_capacity.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_request.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_deployment.v1"

PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
CAPACITY_PATH = "physical/capacity_certificate.json"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
KERNEL_IR_PATH = "ir/tensor_kernel_ir.json"
CHECK_PATH = "checks/independent_check.json"

MODEL_ID = "qwen3-8b"
GRAPH_OPERATION_COUNT = 617
TENSOR_COUNT = 1053
WEIGHT_COUNT = 399
STATE_RESOURCE_COUNT = 36
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
STATE_PAYLOAD_BYTES = CONTEXT_CAPACITY * KV_TOKEN_BYTES
TRANSACTION_ID = 0x5157454E46554C4C

STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")

EXPECTED_COMMAND_COUNT = 924386
EXPECTED_IMMUTABLE_WEIGHT_BYTES = 16381470720
EXPECTED_MUTABLE_KV_BYTES = 1179648000
COEFFICIENT_TABLE_SHA256 = (
    "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
)

CLAIM_BOUNDARY = {
    "complete_graph_physical_lowering": True,
    "complete_checkpoint_payload_deployment": True,
    "complete_command_template": True,
    "full_model_execution": False,
    "timing_or_performance": False,
}

SOURCE_COPIES = {
    "capability": "source/capability.json",
    "checkpoint_lock": "source/checkpoint.lock.json",
    "model_graph": "source/model_graph.v2.json",
    "semantic_check": "source/semantic_independent_check.json",
    "semantic_coverage": "source/semantic_coverage.json",
    "semantic_kernel_ir": "source/semantic_tensor_kernel_ir.json",
}


class QwenFullModelPhysicalError(ArtifactError):
    """Raised when the complete physical deployment cannot be proven."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _safe_relative(value: str) -> str:
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise QwenFullModelPhysicalError(f"unsafe artifact path {value!r}")
    return parsed.as_posix()


def _copy_canonical(source: Path, destination: Path) -> None:
    try:
        payload = Path(source).read_bytes()
        value = load_strict_json(source)
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelPhysicalError(
            f"cannot copy canonical source {source}: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise QwenFullModelPhysicalError(f"source {source} is not canonical JSON")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = value.get(field)
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelPhysicalError(f"{label} identity differs")


def _load_semantic_sources(
    *,
    coverage_path: Path,
    kernel_ir_path: Path,
    semantic_check_path: Path,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    checkpoint_lock_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        coverage = load_strict_json(coverage_path)
        kernel_ir = load_strict_json(kernel_ir_path)
        semantic_check = load_strict_json(semantic_check_path)
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelPhysicalError(
            f"cannot load complete semantic bundle: {exc}"
        ) from exc
    _identity(coverage, "report_id", "semantic coverage")
    _identity(kernel_ir, "kernel_ir_id", "semantic Kernel IR")
    _identity(semantic_check, "check_id", "semantic independent check")
    if (
        coverage.get("schema")
        != "opentallas.tensor_accelerator.qwen_full_model_semantic_coverage.v1"
        or coverage.get("status") != "pass"
        or coverage.get("graph_id") != model.graph_id
        or coverage.get("checkpoint_lock_id") != checkpoint_lock_id
        or coverage.get("capability", {}).get("capability_id")
        != capability.capability_id
        or coverage.get("operation_count") != GRAPH_OPERATION_COUNT
        or coverage.get("kernel_count") != GRAPH_OPERATION_COUNT
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
        raise QwenFullModelPhysicalError("semantic coverage boundary differs")
    kernels = kernel_ir.get("kernels")
    if (
        kernel_ir.get("schema") != "opentallas.production_tensor_kernel_ir.v1"
        or kernel_ir.get("graph_id") != model.graph_id
        or kernel_ir.get("qualification_report_id") != coverage["report_id"]
        or not isinstance(kernels, list)
        or len(kernels) != GRAPH_OPERATION_COUNT
        or [item.get("source_operation_id") for item in kernels]
        != [operation.operation_id for operation in model.operations]
    ):
        raise QwenFullModelPhysicalError("complete semantic Kernel IR differs")
    if (
        semantic_check.get("schema")
        != "opentallas.tensor_accelerator.qwen_full_model_semantic_check.v1"
        or semantic_check.get("status") != "pass"
        or semantic_check.get("graph_id") != model.graph_id
        or semantic_check.get("coverage_report_id") != coverage["report_id"]
        or semantic_check.get("kernel_ir_id") != kernel_ir["kernel_ir_id"]
        or semantic_check.get("capability_id") != capability.capability_id
        or semantic_check.get("operation_count") != GRAPH_OPERATION_COUNT
        or semantic_check.get("state_resource_count") != STATE_RESOURCE_COUNT
        or not all(semantic_check.get("checks", {}).values())
    ):
        raise QwenFullModelPhysicalError("semantic independent check differs")
    return coverage, kernel_ir, semantic_check


def _validate_model_capability(
    model: ProductionModelGraph,
    capability: ProductionCapability,
) -> None:
    vector = capability.vector_engine
    state = capability.state_engine
    if (
        model.model_id != MODEL_ID
        or len(model.operations) != GRAPH_OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_RESOURCE_COUNT
        or (capability.command_abi_major, capability.command_abi_minor)
        != (ABI_MAJOR, SELECTION_ABI_MINOR)
        or capability.tensor_engine.max_m < 1
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
        or vector is None
        or vector.max_rows < QUERY_HEADS + KEY_VALUE_HEADS
        or vector.max_width < INTERMEDIATE_WIDTH
        or vector.max_rope_positions != CONTEXT_CAPACITY
        or vector.max_attention_context_tokens != CONTEXT_CAPACITY
        or vector.max_query_heads != QUERY_HEADS
        or vector.max_key_value_heads != KEY_VALUE_HEADS
        or vector.rope_head_dim != HEAD_DIM
        or vector.attention_head_dim != HEAD_DIM
        or vector.softmax_reduction_lanes != 8
        or state is None
        or state.max_resources_per_transaction < STATE_RESOURCE_COUNT
        or capability.hbm.external_at_130nm_boundary is not True
    ):
        raise QwenFullModelPhysicalError(
            "model or capability does not cover the Qwen full-model deployment"
        )


def _weight_consumers(model: ProductionModelGraph) -> dict[str, ProductionOperation]:
    weights = {tensor.tensor_id for tensor in model.tensors if tensor.role == "weight"}
    consumers: dict[str, list[ProductionOperation]] = defaultdict(list)
    for operation in model.operations:
        for tensor_id in operation.inputs:
            if tensor_id in weights:
                consumers[tensor_id].append(operation)
    if set(consumers) != weights or any(
        len(items) != 1 for items in consumers.values()
    ):
        raise QwenFullModelPhysicalError(
            "every Qwen weight must have exactly one physical consumer"
        )
    return {tensor_id: items[0] for tensor_id, items in consumers.items()}


def _weight_source(tensor: ProductionTensor) -> dict[str, Any]:
    binding = tensor.binding
    if (
        tensor.role != "weight"
        or tensor.dtype != "bf16"
        or binding is None
        or binding.transform != {"kind": "identity"}
        or len(binding.sources) != 1
    ):
        raise QwenFullModelPhysicalError(
            f"weight {tensor.tensor_id!r} is not one identity-bound BF16 payload"
        )
    source = binding.sources[0]
    if (
        source.dtype != "bf16"
        or source.shape != tensor.shape
        or source.payload_sha256 != binding.payload_sha256
    ):
        raise QwenFullModelPhysicalError(
            f"weight {tensor.tensor_id!r} source binding differs"
        )
    return {
        "checkpoint_lock_id": binding.checkpoint_lock_id,
        "dtype": "BF16",
        "payload_sha256": binding.payload_sha256,
        "shape": list(source.shape),
        "tensor_name": source.tensor_name,
    }


def _place(
    cursor: int,
    *,
    size: int,
    alignment: int,
    shard_bytes: int,
    no_cross_shard: bool,
) -> tuple[int, int]:
    offset = align_up(cursor, alignment)
    if (
        no_cross_shard
        and size <= shard_bytes
        and offset // shard_bytes != (offset + size - 1) // shard_bytes
    ):
        offset = align_up(offset, shard_bytes)
    return offset, offset + size


def _physical_layout(
    model: ProductionModelGraph,
    capability: ProductionCapability,
    checkpoint_lock: Mapping[str, Any],
) -> dict[str, Any]:
    consumers = _weight_consumers(model)
    weights = sorted(
        (tensor for tensor in model.tensors if tensor.role == "weight"),
        key=lambda tensor: consumers[tensor.tensor_id].index,
    )
    if len(weights) != WEIGHT_COUNT:
        raise QwenFullModelPhysicalError("Qwen physical weight count differs")
    lock_tensors = {
        tensor["name"]: tensor
        for shard in checkpoint_lock["shards"]
        for tensor in shard["tensors"]
    }
    cursor = 0
    padding = 0
    weight_records: list[dict[str, Any]] = []
    immutable_bytes = 0
    for tensor in weights:
        operation = consumers[tensor.tensor_id]
        source = _weight_source(tensor)
        locked = lock_tensors.get(source["tensor_name"])
        size = int(np.prod(tensor.shape, dtype=np.int64)) * BF16_BYTES
        if (
            locked is None
            or locked["dtype"] != "BF16"
            or locked["shape"] != source["shape"]
            or locked["size_bytes"] != size
            or locked["payload_sha256"] != source["payload_sha256"]
        ):
            raise QwenFullModelPhysicalError(
                f"weight {tensor.tensor_id!r} differs from the checkpoint lock"
            )
        if operation.kind == "EMBEDDING_LOOKUP":
            layout = "direct_row_major_bf16"
            alignment = EMBEDDING_ROW_BYTES
            access_unit = EMBEDDING_ROW_BYTES
            no_cross = False
            details: dict[str, Any] = {
                "row_bytes": EMBEDDING_ROW_BYTES,
                "rows": VOCABULARY_SIZE,
            }
        elif operation.kind == "RMS_NORM":
            layout = "direct_vector_bf16"
            alignment = capability.hbm.burst_bytes
            access_unit = size
            no_cross = True
            details = {"elements": size // BF16_BYTES}
        elif operation.kind == "MATMUL":
            n, k = tensor.shape
            if (
                not isinstance(n, int)
                or not isinstance(k, int)
                or n % N_TILE
                or k % K_TILE
            ):
                raise QwenFullModelPhysicalError(
                    f"matrix weight {tensor.tensor_id!r} is not exactly tileable"
                )
            layout = "n_major_k_minor_tiles_bf16"
            alignment = TILE_BYTES
            access_unit = TILE_BYTES
            no_cross = False
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
            raise QwenFullModelPhysicalError(
                f"weight consumer {operation.kind!r} has no physical layout"
            )
        offset, end = _place(
            cursor,
            size=size,
            alignment=alignment,
            shard_bytes=DEFAULT_SHARD_BYTES,
            no_cross_shard=no_cross,
        )
        padding += offset - cursor
        record = {
            "access_unit_bytes": access_unit,
            "address": capability.hbm.base_address + offset,
            "consumer_kernel_index": operation.index,
            "consumer_operation_id": operation.operation_id,
            "deployed_payload_sha256": None,
            "layout": layout,
            "layout_details": details,
            "offset_bytes": offset,
            "size_bytes": size,
            "source": source,
            "tensor_id": tensor.tensor_id,
        }
        weight_records.append(record)
        immutable_bytes += size
        cursor = end
    if immutable_bytes != EXPECTED_IMMUTABLE_WEIGHT_BYTES:
        raise QwenFullModelPhysicalError("Qwen immutable weight-byte count differs")

    coefficient_size = CONTEXT_CAPACITY * 2 * HEAD_DIM * BF16_BYTES
    coefficient_offset, cursor_after_coefficient = _place(
        cursor,
        size=coefficient_size,
        alignment=2 * HEAD_DIM * BF16_BYTES,
        shard_bytes=DEFAULT_SHARD_BYTES,
        no_cross_shard=True,
    )
    padding += coefficient_offset - cursor
    coefficient = {
        "address": capability.hbm.base_address + coefficient_offset,
        "layout": "position_major_cos_then_sin_bf16",
        "offset_bytes": coefficient_offset,
        "payload_sha256": COEFFICIENT_TABLE_SHA256,
        "positions": CONTEXT_CAPACITY,
        "row_bytes": 2 * HEAD_DIM * BF16_BYTES,
        "size_bytes": coefficient_size,
    }
    cursor = cursor_after_coefficient

    states: list[dict[str, Any]] = []
    for layer in range(LAYER_COUNT):
        key_offset, key_end = _place(
            cursor,
            size=STATE_PAYLOAD_BYTES,
            alignment=capability.hbm.burst_bytes,
            shard_bytes=DEFAULT_SHARD_BYTES,
            no_cross_shard=True,
        )
        padding += key_offset - cursor
        value_offset, value_end = _place(
            key_end,
            size=STATE_PAYLOAD_BYTES,
            alignment=capability.hbm.burst_bytes,
            shard_bytes=DEFAULT_SHARD_BYTES,
            no_cross_shard=True,
        )
        padding += value_offset - key_end
        states.append(
            {
                "head_dim": HEAD_DIM,
                "key_address": capability.hbm.base_address + key_offset,
                "key_offset_bytes": key_offset,
                "key_value_heads": KEY_VALUE_HEADS,
                "layer": layer,
                "max_context_tokens": CONTEXT_CAPACITY,
                "resource_id": f"kv.layer.{layer}",
                "size_bytes_per_plane": STATE_PAYLOAD_BYTES,
                "value_address": capability.hbm.base_address + value_offset,
                "value_offset_bytes": value_offset,
            }
        )
        cursor = value_end
    mutable_kv_bytes = len(states) * 2 * STATE_PAYLOAD_BYTES
    if mutable_kv_bytes != EXPECTED_MUTABLE_KV_BYTES:
        raise QwenFullModelPhysicalError("Qwen mutable KV-byte count differs")

    table_bytes = LAYER_COUNT * STATE_METADATA.size
    metadata_offset, metadata_end = _place(
        cursor,
        size=table_bytes,
        alignment=capability.hbm.burst_bytes,
        shard_bytes=DEFAULT_SHARD_BYTES,
        no_cross_shard=True,
    )
    padding += metadata_offset - cursor
    descriptor_offset, descriptor_end = _place(
        metadata_end,
        size=table_bytes,
        alignment=capability.hbm.burst_bytes,
        shard_bytes=DEFAULT_SHARD_BYTES,
        no_cross_shard=True,
    )
    padding += descriptor_offset - metadata_end
    total_size = align_up(descriptor_end, capability.hbm.burst_bytes)
    padding += total_size - descriptor_end
    if total_size > capability.hbm.capacity_bytes:
        raise QwenFullModelPhysicalError("Qwen logical HBM image exceeds capability")
    return {
        "alignment_padding_bytes": padding,
        "base_address": capability.hbm.base_address,
        "coefficient_table": coefficient,
        "descriptor_table": {
            "address": capability.hbm.base_address + descriptor_offset,
            "entry_bytes": TRANSACTION_DESCRIPTOR.size,
            "entry_count": LAYER_COUNT,
            "offset_bytes": descriptor_offset,
            "payload_sha256": None,
            "size_bytes": table_bytes,
        },
        "immutable_weight_bytes": immutable_bytes,
        "metadata_table": {
            "address": capability.hbm.base_address + metadata_offset,
            "entry_bytes": STATE_METADATA.size,
            "entry_count": LAYER_COUNT,
            "offset_bytes": metadata_offset,
            "payload_sha256": None,
            "size_bytes": table_bytes,
        },
        "mutable_kv_bytes": mutable_kv_bytes,
        "shard_bytes": DEFAULT_SHARD_BYTES,
        "states": states,
        "total_size_bytes": total_size,
        "weights": weight_records,
    }


def _slot(
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
        raise QwenFullModelPhysicalError(f"SRAM slot {slot_id!r} exceeds its bank")
    return {
        "address": capability.sram.bank_base(bank) + offset,
        "allocated_bytes": allocated,
        "bank": bank,
        "capacity_bytes": capacity,
        "id": slot_id,
        "offset_bytes": offset,
    }


def _physical_tensor_bytes(tensor: ProductionTensor) -> int:
    elements = 1
    for dimension in tensor.shape:
        elements *= 1 if dimension == "span_tokens" else int(dimension)
    bytes_per_element = 4 if tensor.dtype == "u32" else 2
    return elements * bytes_per_element


def _tensor_slot(operation_index: int, output_index: int = 0) -> str | None:
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
        if isinstance(selected, tuple):
            return selected[output_index]
        return selected
    return {
        613: "vector_a",
        614: "norm_stage",
        615: "wide_a",
        616: "wide_a",
    }.get(operation_index)


def _sram_plan(
    model: ProductionModelGraph,
    capability: ProductionCapability,
) -> dict[str, Any]:
    slots = [
        _slot(capability, "runtime_ids", 0, 0, 16),
        _slot(capability, "attention", 0, 16, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "hidden_even", 1, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "norm_stage", 2, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "vector_a", 3, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "weight_tile", 4, 0, TILE_BYTES),
        _slot(capability, "accumulator", 5, 0, N_TILE * 4),
        _slot(capability, "wide_a", 6, 0, VOCABULARY_SIZE * BF16_BYTES),
        _slot(capability, "vector_b", 7, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "wide_b", 8, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot(capability, "wide_c", 9, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot(capability, "wide_d", 10, 0, INTERMEDIATE_WIDTH * BF16_BYTES),
        _slot(capability, "q_norm_or_down", 11, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "hidden_odd", 12, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "k_norm", 12, HIDDEN_WIDTH * BF16_BYTES, KV_TOKEN_BYTES),
        _slot(capability, "rope_coefficients", 13, 0, 2 * HEAD_DIM * BF16_BYTES),
        _slot(capability, "q_rotary", 14, 0, HIDDEN_WIDTH * BF16_BYTES),
        _slot(capability, "k_rotary", 15, 0, KV_TOKEN_BYTES),
    ]
    by_bank: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    for slot in slots:
        start = slot["offset_bytes"]
        end = start + slot["allocated_bytes"]
        for other_start, other_end, other_id in by_bank[slot["bank"]]:
            if start < other_end and other_start < end:
                raise QwenFullModelPhysicalError(
                    f"SRAM slots {other_id!r} and {slot['id']!r} overlap"
                )
        by_bank[slot["bank"]].append((start, end, slot["id"]))

    producer: dict[str, int] = {}
    consumers: dict[str, list[int]] = defaultdict(list)
    for operation in model.operations:
        for tensor_id in operation.inputs:
            consumers[tensor_id].append(operation.index)
        for tensor_id in operation.outputs:
            producer[tensor_id] = operation.index
    assignments: list[dict[str, Any]] = []
    state_handles: list[dict[str, Any]] = []
    for tensor in model.tensors:
        if tensor.role not in {"activation", "output"}:
            continue
        first = producer[tensor.tensor_id]
        slot_id = _tensor_slot(
            first, model.operations[first].outputs.index(tensor.tensor_id)
        )
        last = max(consumers.get(tensor.tensor_id, [first]))
        if slot_id is None:
            layer = (first - 1) // 17
            state_handles.append(
                {
                    "first_kernel_index": first,
                    "last_kernel_index": last,
                    "resource_id": f"kv.layer.{layer}",
                    "tensor_id": tensor.tensor_id,
                }
            )
            continue
        assignments.append(
            {
                "alias_of": "output.logits"
                if tensor.tensor_id == "output.committed_logits"
                else None,
                "first_kernel_index": first,
                "last_kernel_index": last,
                "logical_bytes": _physical_tensor_bytes(tensor),
                "slot_id": slot_id,
                "tensor_id": tensor.tensor_id,
            }
        )

    staged_weights: list[dict[str, Any]] = []
    workspaces: list[dict[str, Any]] = []
    for operation in model.operations:
        weights = [
            model.tensor_by_id[tensor_id]
            for tensor_id in operation.inputs
            if model.tensor_by_id[tensor_id].role == "weight"
        ]
        if operation.kind == "RMS_NORM":
            if len(weights) != 1:
                raise QwenFullModelPhysicalError("RMSNorm staged weight count differs")
            relative = (operation.index - 1) % 17 if operation.index <= 612 else None
            slot_id = {4: "wide_c", 5: "wide_d", 11: "wide_a"}.get(
                relative, "norm_stage"
            )
            staged_weights.append(
                {
                    "kernel_index": operation.index,
                    "logical_bytes": _physical_tensor_bytes(weights[0]),
                    "slot_id": slot_id,
                    "tensor_id": weights[0].tensor_id,
                }
            )
        elif operation.kind == "MATMUL":
            workspaces.extend(
                (
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
                )
            )
        elif operation.kind == "ROPE":
            workspaces.append(
                {
                    "kernel_index": operation.index,
                    "role": "rope_coefficient_row",
                    "slot_id": "rope_coefficients",
                }
            )

    intervals: dict[str, list[tuple[int, int, str, str | None]]] = defaultdict(list)
    for item in assignments:
        intervals[item["slot_id"]].append(
            (
                item["first_kernel_index"],
                item["last_kernel_index"],
                item["tensor_id"],
                item["alias_of"],
            )
        )
    for item in staged_weights:
        intervals[item["slot_id"]].append(
            (item["kernel_index"], item["kernel_index"], item["tensor_id"], None)
        )
    for slot_id, records in intervals.items():
        ordered = sorted(records)
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] <= previous[1] and current[3] != previous[2]:
                raise QwenFullModelPhysicalError(
                    f"SRAM slot {slot_id!r} has overlapping live ranges "
                    f"{previous[2]!r} and {current[2]!r}"
                )
    slot_capacity = {item["id"]: item["capacity_bytes"] for item in slots}
    for item in assignments:
        if item["logical_bytes"] > slot_capacity[item["slot_id"]]:
            raise QwenFullModelPhysicalError(
                f"tensor {item['tensor_id']!r} exceeds SRAM slot capacity"
            )
    for item in staged_weights:
        if item["logical_bytes"] > slot_capacity[item["slot_id"]]:
            raise QwenFullModelPhysicalError(
                f"staged weight {item['tensor_id']!r} exceeds SRAM slot capacity"
            )
    return {
        "addressing": "bank_base_plus_byte_offset",
        "physical_profile": "single_token_forward",
        "slots": slots,
        "staged_weight_assignments": staged_weights,
        "state_handle_assignments": state_handles,
        "tensor_assignments": assignments,
        "workspace_assignments": workspaces,
    }


def _slot_by_id(sram: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result = {item["id"]: item for item in sram["slots"]}
    if len(result) != len(sram["slots"]):
        raise QwenFullModelPhysicalError("SRAM slot identifiers are not unique")
    return result


def _assignment_by_tensor(sram: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result = {item["tensor_id"]: item for item in sram["tensor_assignments"]}
    if len(result) != len(sram["tensor_assignments"]):
        raise QwenFullModelPhysicalError("SRAM tensor assignments are not unique")
    return result


def _append_matrix_commands(
    commands: list[ProductionCommand],
    *,
    operation: ProductionOperation,
    record: Mapping[str, Any],
    input_address: int,
    output_address: int,
    slots: Mapping[str, Mapping[str, Any]],
) -> None:
    details = record["layout_details"]
    tile_index = 0
    for n_index in range(details["n_tiles"]):
        n_start = n_index * details["n_tile"]
        for k_index in range(details["k_tiles"]):
            k_start = k_index * details["k_tile"]
            tile_address = record["address"] + tile_index * details["tile_bytes"]
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=tile_address,
                    destination=slots["weight_tile"]["address"],
                    size0=details["tile_bytes"],
                )
            )
            flags = 0
            if k_index == 0:
                flags |= MATMUL_INIT
            if k_index + 1 == details["k_tiles"]:
                flags |= MATMUL_FINAL
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.MATMUL_BF16_TILE,
                    engine=Engine.TENSOR,
                    flags=flags,
                    kernel_index=operation.index,
                    source0=input_address + k_start * BF16_BYTES,
                    source1=slots["weight_tile"]["address"],
                    destination=slots["accumulator"]["address"],
                    auxiliary=output_address + n_start * BF16_BYTES,
                    size0=1,
                    size1=details["n_tile"],
                    size2=details["k_tile"],
                )
            )
            tile_index += 1
    if tile_index != details["tile_count"]:
        raise QwenFullModelPhysicalError(
            f"matrix kernel {operation.operation_id!r} tile count differs"
        )


def _commands(
    *,
    model: ProductionModelGraph,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
) -> tuple[tuple[ProductionCommand, ...], list[dict[str, Any]], dict[str, int]]:
    slots = _slot_by_id(sram)
    assignments = _assignment_by_tensor(sram)
    weights = {item["consumer_kernel_index"]: item for item in hbm["weights"]}
    states = {item["layer"]: item for item in hbm["states"]}
    staged = {item["kernel_index"]: item for item in sram["staged_weight_assignments"]}

    def tensor_address(tensor_id: str) -> int:
        assignment = assignments[tensor_id]
        return int(slots[assignment["slot_id"]]["address"])

    commands: list[ProductionCommand] = []
    ranges: list[dict[str, Any]] = []
    for operation in model.operations:
        begin = len(commands)
        if operation.kind == "EMBEDDING_LOOKUP":
            record = weights[operation.index]
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=record["address"],
                    source1=slots["runtime_ids"]["address"],
                    destination=tensor_address(operation.outputs[0]),
                    auxiliary=0,
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=VOCABULARY_SIZE,
                    size3=4,
                )
            )
        elif operation.kind == "RMS_NORM":
            record = weights[operation.index]
            stage = staged[operation.index]
            stage_address = slots[stage["slot_id"]]["address"]
            rows = QUERY_HEADS if operation.index % 17 == 5 else 1
            if operation.index % 17 == 6 and operation.index <= 612:
                rows = KEY_VALUE_HEADS
            width = operation.attributes["normalization_width"]
            commands.extend(
                (
                    ProductionCommand(
                        index=len(commands),
                        opcode=Opcode.DMA_HBM_TO_SRAM,
                        engine=Engine.DMA,
                        kernel_index=operation.index,
                        source0=record["address"],
                        destination=stage_address,
                        size0=record["size_bytes"],
                    ),
                    ProductionCommand(
                        index=len(commands) + 1,
                        opcode=Opcode.RMSNORM_BF16,
                        engine=Engine.VECTOR,
                        kernel_index=operation.index,
                        source0=tensor_address(operation.inputs[0]),
                        source1=stage_address,
                        destination=tensor_address(operation.outputs[0]),
                        size0=rows,
                        size1=width,
                        size2=EPSILON_CODE,
                    ),
                )
            )
        elif operation.kind == "MATMUL":
            _append_matrix_commands(
                commands,
                operation=operation,
                record=weights[operation.index],
                input_address=tensor_address(operation.inputs[0]),
                output_address=tensor_address(operation.outputs[0]),
                slots=slots,
            )
        elif operation.kind == "ROPE":
            commands.extend(
                (
                    ProductionCommand(
                        index=len(commands),
                        opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                        engine=Engine.DMA,
                        kernel_index=operation.index,
                        source0=hbm["coefficient_table"]["address"],
                        source1=slots["runtime_ids"]["address"] + 4,
                        destination=slots["rope_coefficients"]["address"],
                        auxiliary=0,
                        size0=hbm["coefficient_table"]["row_bytes"],
                        size1=hbm["coefficient_table"]["row_bytes"],
                        size2=CONTEXT_CAPACITY,
                        size3=4,
                    ),
                    ProductionCommand(
                        index=len(commands) + 1,
                        opcode=Opcode.ROPE_BF16,
                        engine=Engine.VECTOR,
                        kernel_index=operation.index,
                        source0=tensor_address(operation.inputs[0]),
                        source1=tensor_address(operation.inputs[1]),
                        destination=tensor_address(operation.outputs[0]),
                        auxiliary=tensor_address(operation.outputs[1]),
                        size0=QUERY_HEADS,
                        size1=KEY_VALUE_HEADS,
                        size2=HEAD_DIM,
                        size3=slots["rope_coefficients"]["address"],
                    ),
                )
            )
        elif operation.kind == "KV_PREPARE":
            layer = (operation.index - 1) // 17
            state = states[layer]
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.KV_PREPARE_BF16,
                    engine=Engine.STATE,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=state["key_address"],
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=KEY_VALUE_HEADS,
                    size2=HEAD_DIM,
                )
            )
        elif operation.kind == "ATTENTION":
            layer = (operation.index - 1) // 17
            state = states[layer]
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.GQA_ATTENTION_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=state["key_address"],
                    destination=tensor_address(operation.outputs[0]),
                    auxiliary=state["value_address"],
                    size0=1,
                    size1=QUERY_HEADS,
                    size2=KEY_VALUE_HEADS,
                    size3=HEAD_DIM,
                )
            )
        elif operation.kind == "ADD":
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.ADD_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=tensor_address(operation.outputs[0]),
                    size0=1,
                    size1=HIDDEN_WIDTH,
                )
            )
        elif operation.kind == "SILU_MUL":
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.SILU_MUL_BF16,
                    engine=Engine.VECTOR,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=tensor_address(operation.inputs[1]),
                    destination=tensor_address(operation.outputs[0]),
                    size0=1,
                    size1=INTERMEDIATE_WIDTH,
                )
            )
        elif operation.kind == "LAST_TOKEN_SELECT":
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.DMA_SRAM_INDEXED_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=operation.index,
                    source0=tensor_address(operation.inputs[0]),
                    source1=slots["runtime_ids"]["address"] + 8,
                    destination=tensor_address(operation.outputs[0]),
                    auxiliary=0,
                    size0=EMBEDDING_ROW_BYTES,
                    size1=EMBEDDING_ROW_BYTES,
                    size2=1,
                    size3=4,
                )
            )
        elif operation.kind == "STATE_COMMIT":
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.STATE_COMMIT,
                    engine=Engine.STATE,
                    kernel_index=NO_KERNEL,
                    source0=hbm["metadata_table"]["address"],
                    source1=hbm["descriptor_table"]["address"],
                    size0=CONTEXT_CAPACITY,
                    size1=STATE_RESOURCE_COUNT,
                )
            )
        else:
            raise QwenFullModelPhysicalError(
                f"operation {operation.operation_id!r} has no physical command lowering"
            )
        if len(commands) == begin:
            raise QwenFullModelPhysicalError(
                f"operation {operation.operation_id!r} emitted no command"
            )
        ranges.append(
            {
                "command_count": len(commands) - begin,
                "command_start": begin,
                "kernel_index": operation.index,
                "operation_id": operation.operation_id,
            }
        )
    commands.append(
        ProductionCommand(
            index=len(commands), opcode=Opcode.COMPLETE, engine=Engine.CONTROL
        )
    )
    if len(commands) != EXPECTED_COMMAND_COUNT:
        raise QwenFullModelPhysicalError(
            f"full-model command count differs: {len(commands)}"
        )
    counts = Counter(command.opcode.name for command in commands)
    if (
        counts["MATMUL_BF16_TILE"] != 461920
        or counts["DMA_HBM_TO_SRAM"] != 462065
        or counts["DMA_HBM_INDEXED_TO_SRAM"] != 37
        or counts["DMA_SRAM_INDEXED_TO_SRAM"] != 1
        or counts["STATE_COMMIT"] != 1
        or counts["COMPLETE"] != 1
    ):
        raise QwenFullModelPhysicalError("full-model command-family counts differ")
    return tuple(commands), ranges, dict(sorted(counts.items()))


def _metadata_payload(hbm: Mapping[str, Any]) -> bytes:
    return b"".join(
        STATE_METADATA.pack(
            STATE_MAGIC,
            0,
            0,
            CONTEXT_CAPACITY,
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


def _write_direct_weight(
    reader: LockedCheckpointReader,
    writer: HBMShardWriter,
    record: dict[str, Any],
) -> None:
    digest = hashlib.sha256()

    def consume(chunk: bytes) -> None:
        digest.update(chunk)
        writer.write(chunk)

    reader.consume_tensor_payload(record["source"]["tensor_name"], consume)
    if digest.hexdigest() != record["source"]["payload_sha256"]:
        raise QwenFullModelPhysicalError(
            f"direct deployment for {record['tensor_id']!r} differs"
        )
    record["deployed_payload_sha256"] = digest.hexdigest()


def _write_tiled_weight(
    reader: LockedCheckpointReader,
    writer: HBMShardWriter,
    record: dict[str, Any],
) -> None:
    details = record["layout_details"]
    block_bytes = details["n_tile"] * details["k"] * BF16_BYTES
    pending = bytearray()
    deployed = hashlib.sha256()
    block_count = 0

    def consume(chunk: bytes) -> None:
        nonlocal block_count
        pending.extend(chunk)
        while len(pending) >= block_bytes:
            block_payload = bytes(pending[:block_bytes])
            del pending[:block_bytes]
            block = np.frombuffer(block_payload, dtype="<u2").reshape(
                details["n_tile"], details["k"]
            )
            for k_start in range(0, details["k"], details["k_tile"]):
                tile = np.ascontiguousarray(
                    block[:, k_start : k_start + details["k_tile"]],
                    dtype="<u2",
                ).tobytes(order="C")
                if len(tile) != details["tile_bytes"]:
                    raise QwenFullModelPhysicalError("matrix tile byte count differs")
                writer.write(tile)
                deployed.update(tile)
            block_count += 1

    reader.consume_tensor_payload(
        record["source"]["tensor_name"], consume, chunk_bytes=block_bytes
    )
    if pending or block_count != details["n_tiles"]:
        raise QwenFullModelPhysicalError(
            f"tiled deployment for {record['tensor_id']!r} is incomplete"
        )
    record["deployed_payload_sha256"] = deployed.hexdigest()


def _publish_hbm(
    *,
    root: Path,
    snapshot: Path,
    checkpoint_lock: Mapping[str, Any],
    hbm: dict[str, Any],
) -> dict[str, Any]:
    try:
        with LockedCheckpointReader(snapshot, dict(checkpoint_lock)) as reader:
            with HBMShardWriter(
                root,
                total_size=hbm["total_size_bytes"],
                shard_bytes=hbm["shard_bytes"],
            ) as writer:
                for record in hbm["weights"]:
                    writer.advance_to(record["offset_bytes"])
                    if record["layout"].startswith("direct_"):
                        _write_direct_weight(reader, writer, record)
                    else:
                        _write_tiled_weight(reader, writer, record)
                    if writer.cursor != record["offset_bytes"] + record["size_bytes"]:
                        raise QwenFullModelPhysicalError(
                            f"weight {record['tensor_id']!r} HBM extent differs"
                        )
                if len(reader.accessed_tensor_names) != WEIGHT_COUNT:
                    raise QwenFullModelPhysicalError(
                        "full-model compiler did not consume all checkpoint weights"
                    )
                coefficient = coefficient_table_bf16(CONTEXT_CAPACITY)
                coefficient_payload = np.ascontiguousarray(
                    coefficient, dtype="<u2"
                ).tobytes(order="C")
                if (
                    coefficient.shape != (CONTEXT_CAPACITY, 2 * HEAD_DIM)
                    or hashlib.sha256(coefficient_payload).hexdigest()
                    != COEFFICIENT_TABLE_SHA256
                ):
                    raise QwenFullModelPhysicalError(
                        "full-model RoPE coefficient table differs"
                    )
                coefficient_record = hbm["coefficient_table"]
                writer.advance_to(coefficient_record["offset_bytes"])
                writer.write(coefficient_payload)
                for state in hbm["states"]:
                    writer.advance_to(state["key_offset_bytes"])
                    writer.skip_zeros(state["size_bytes_per_plane"])
                    writer.advance_to(state["value_offset_bytes"])
                    writer.skip_zeros(state["size_bytes_per_plane"])
                metadata = _metadata_payload(hbm)
                descriptors = _descriptor_payload(hbm)
                hbm["metadata_table"]["payload_sha256"] = hashlib.sha256(
                    metadata
                ).hexdigest()
                hbm["descriptor_table"]["payload_sha256"] = hashlib.sha256(
                    descriptors
                ).hexdigest()
                writer.advance_to(hbm["metadata_table"]["offset_bytes"])
                writer.write(metadata)
                writer.advance_to(hbm["descriptor_table"]["offset_bytes"])
                writer.write(descriptors)
                writer.advance_to(hbm["total_size_bytes"])
                image = writer.finish()
    except (CheckpointError, HBMShardError, OSError, ValueError) as exc:
        raise QwenFullModelPhysicalError(
            f"full-model HBM publication failed: {exc}"
        ) from exc
    return image


def _request(model: ProductionModelGraph) -> dict[str, Any]:
    body = {
        "expected_generations": [0] * STATE_RESOURCE_COUNT,
        "graph_id": model.graph_id,
        "last_row_index": 0,
        "phase": "prefill",
        "position_end": 1,
        "position_start": 0,
        "schema": REQUEST_SCHEMA,
        "span_tokens": 1,
        "token_id": 0,
        "transaction_id": TRANSACTION_ID,
    }
    return _identified(body, "request_id")


def _source_lock(
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
    body = {
        "artifacts": artifacts,
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": checkpoint_lock["lock_id"],
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "schema": SOURCE_LOCK_SCHEMA,
        "semantic_check_id": semantic_check["check_id"],
        "semantic_coverage_report_id": coverage["report_id"],
        "semantic_kernel_ir_id": kernel_ir["kernel_ir_id"],
    }
    return _identified(body, "source_lock_id")


def _capacity_certificate(
    *,
    capability: ProductionCapability,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    command_count: int,
) -> dict[str, Any]:
    per_bank = {bank: 0 for bank in range(capability.sram.banks)}
    for slot in sram["slots"]:
        per_bank[slot["bank"]] += slot["allocated_bytes"]
    body = {
        "command_capacity": {
            "available": capability.limits["max_commands"],
            "margin": capability.limits["max_commands"] - command_count,
            "required": command_count,
        },
        "context_capacity_tokens": CONTEXT_CAPACITY,
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
            "bank_allocated_bytes": [per_bank[index] for index in sorted(per_bank)],
            "max_bank_allocated_bytes": max(per_bank.values()),
            "slots": len(sram["slots"]),
        },
        "state_resource_count": STATE_RESOURCE_COUNT,
        "weight_count": WEIGHT_COUNT,
    }
    return _identified(body, "capacity_certificate_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    source_lock: Mapping[str, Any],
    semantic_kernel_ir: Mapping[str, Any],
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    command_payload: bytes,
    command_ranges: Sequence[Mapping[str, Any]],
    opcode_counts: Mapping[str, int],
    capacity: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "capability_id": capability.capability_id,
        "capacity_certificate_id": capacity["capacity_certificate_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "command_program": {
            "abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
            "command_count": EXPECTED_COMMAND_COUNT,
            "kernel_command_ranges": list(command_ranges),
            "opcode_counts": dict(opcode_counts),
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "graph_id": model.graph_id,
        "hbm": dict(hbm),
        "physical_profile": "single_token_forward",
        "schema": PHYSICAL_PLAN_SCHEMA,
        "semantic_kernel_ir_id": semantic_kernel_ir["kernel_ir_id"],
        "source_lock_id": source_lock["source_lock_id"],
        "sram": dict(sram),
    }
    return _identified(body, "physical_plan_id")


def _artifact(root: Path, path: str, role: str) -> dict[str, Any]:
    relative = _safe_relative(path)
    digest, size = sha256_file(root / relative)
    return {"path": relative, "role": role, "sha256": digest, "size_bytes": size}


def _manifest(
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
        _artifact(root, "capability.json", "capability"),
        _artifact(root, CHECK_PATH, "independent_check"),
        _artifact(root, KERNEL_IR_PATH, "tensor_kernel_ir"),
        _artifact(root, PHYSICAL_PLAN_PATH, "physical_plan"),
        _artifact(root, CAPACITY_PATH, "capacity_certificate"),
        _artifact(root, COMMAND_PATH, "command_program"),
        _artifact(root, REQUEST_PATH, "execution_request"),
        _artifact(root, "source.lock.json", "source_lock"),
    ]
    for role, record in source_lock["artifacts"].items():
        artifacts.append(_artifact(root, record["path"], f"source_{role}"))
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
    body = {
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
    }
    return _identified(body, "build_id")


def _build_into(
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
    try:
        checkpoint_lock = load_checkpoint_lock(checkpoint_lock_path)
        model = load_production_model_graph(model_graph_path)
        capability = load_production_capability(capability_path)
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
    ) as exc:
        raise QwenFullModelPhysicalError(
            f"full-model physical source admission failed: {exc}"
        ) from exc
    _validate_model_capability(model, capability)
    coverage, kernel_ir, semantic_check = _load_semantic_sources(
        coverage_path=semantic_coverage_path,
        kernel_ir_path=semantic_kernel_ir_path,
        semantic_check_path=semantic_check_path,
        model=model,
        capability=capability,
        checkpoint_lock_id=checkpoint_lock["lock_id"],
    )
    hbm = _physical_layout(model, capability, checkpoint_lock)
    sram = _sram_plan(model, capability)
    commands, command_ranges, opcode_counts = _commands(model=model, hbm=hbm, sram=sram)
    command_payload = encode(commands, abi_minor=SELECTION_ABI_MINOR)

    source_paths = {
        "capability": capability_path,
        "checkpoint_lock": checkpoint_lock_path,
        "model_graph": model_graph_path,
        "semantic_check": semantic_check_path,
        "semantic_coverage": semantic_coverage_path,
        "semantic_kernel_ir": semantic_kernel_ir_path,
    }
    source_lock = _source_lock(
        model=model,
        capability=capability,
        checkpoint_lock=checkpoint_lock,
        coverage=coverage,
        kernel_ir=kernel_ir,
        semantic_check=semantic_check,
        source_paths=source_paths,
    )
    request = _request(model)

    for directory in ("checks", "ir", "physical", "program", "request", "source"):
        (root / directory).mkdir(parents=True, exist_ok=False)
    write_canonical_json(root / "capability.json", capability.to_dict())
    write_canonical_json(root / KERNEL_IR_PATH, kernel_ir)
    write_canonical_json(root / REQUEST_PATH, request)
    write_canonical_json(root / "source.lock.json", source_lock)
    for role, record in source_lock["artifacts"].items():
        _copy_canonical(source_paths[role], root / record["path"])
    (root / COMMAND_PATH).write_bytes(command_payload)

    image = _publish_hbm(
        root=root,
        snapshot=snapshot,
        checkpoint_lock=checkpoint_lock,
        hbm=hbm,
    )
    hbm["image"] = image
    capacity = _capacity_certificate(
        capability=capability,
        hbm=hbm,
        sram=sram,
        command_count=len(commands),
    )
    physical_plan = _physical_plan(
        model=model,
        capability=capability,
        source_lock=source_lock,
        semantic_kernel_ir=kernel_ir,
        hbm=hbm,
        sram=sram,
        command_payload=command_payload,
        command_ranges=command_ranges,
        opcode_counts=opcode_counts,
        capacity=capacity,
    )
    write_canonical_json(root / CAPACITY_PATH, capacity)
    write_canonical_json(root / PHYSICAL_PLAN_PATH, physical_plan)

    from .qwen_full_model_physical_checking import (
        check_qwen_full_model_physical_deployment,
    )

    independent_check = check_qwen_full_model_physical_deployment(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        semantic_coverage_path=semantic_coverage_path,
        semantic_kernel_ir_path=semantic_kernel_ir_path,
        semantic_check_path=semantic_check_path,
        root=root,
    )
    write_canonical_json(root / CHECK_PATH, independent_check)
    manifest = _manifest(
        root,
        model=model,
        capability=capability,
        source_lock=source_lock,
        kernel_ir=kernel_ir,
        physical_plan=physical_plan,
        capacity=capacity,
        independent_check=independent_check,
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_qwen_full_model_physical_deployment(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    semantic_coverage_path: Path,
    semantic_kernel_ir_path: Path,
    semantic_check_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Build, independently reconstruct, and atomically publish QW-FM2/3."""

    snapshot = Path(snapshot).resolve()
    sources = {
        "checkpoint_lock_path": Path(checkpoint_lock_path).resolve(),
        "model_graph_path": Path(model_graph_path).resolve(),
        "capability_path": Path(capability_path).resolve(),
        "semantic_coverage_path": Path(semantic_coverage_path).resolve(),
        "semantic_kernel_ir_path": Path(semantic_kernel_ir_path).resolve(),
        "semantic_check_path": Path(semantic_check_path).resolve(),
    }
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise QwenFullModelPhysicalError(
            f"checkpoint snapshot does not exist: {snapshot}"
        )
    for label, path in sources.items():
        if not path.is_file():
            raise QwenFullModelPhysicalError(
                f"physical source {label} is missing: {path}"
            )
    if output.exists():
        raise QwenFullModelPhysicalError(
            f"full-model deployment output already exists: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        manifest = _build_into(
            snapshot=snapshot,
            root=temporary,
            **sources,
        )
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "CAPACITY_PATH",
    "CAPACITY_SCHEMA",
    "CHECK_PATH",
    "COMMAND_PATH",
    "COMPILER_VERSION",
    "EXPECTED_COMMAND_COUNT",
    "HBMShardError",
    "KERNEL_IR_PATH",
    "MANIFEST_SCHEMA",
    "PHYSICAL_PLAN_PATH",
    "PHYSICAL_PLAN_SCHEMA",
    "QwenFullModelPhysicalError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_qwen_full_model_physical_deployment",
]
