"""Deterministic Qwen attention and transactional-KV deployment compiler.

The compiler consumes the retained authentic Q/K/V execution report rather than
the checkpoint.  It emits a neutral kernel artifact, an explicit HBM/SRAM plan,
an ABI 2.3 command stream, and a request that exercises nonempty committed KV.
The terminal state operation is deliberately identified as a one-resource
qualification of the 36-resource model-forward commit; it is not represented as
complete-model state evidence.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import tempfile
from typing import Any, Mapping

import numpy as np

from .attention_qualification import (
    AttentionQualificationError,
    EXPECTED_QKV_PAYLOAD_SHA256,
    PINNED_QKV_BUILD_ID,
    PINNED_QKV_REPORT_ID,
    load_attention_qualification,
)
from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_command import (
    ATTENTION_ABI_MINOR,
    Engine,
    NO_KERNEL,
    Opcode,
    ProductionCommand,
    disassemble,
    encode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)


COMPILER_VERSION = "tensor-accelerator-production-attention-0.1.0"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.attention_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.attention_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.attention_source_lock.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.attention_expectations.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.attention_deployment.v1"
QKV_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qkv_execution.v1"

HBM_IMAGE_PATH = "memory/hbm_attention.bin"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"

NUMERIC_CONTRACT = "qwen3_gqa_fp32_softmax_bf16_v1"
STATE_CONTRACT = "bf16_byte_preserving_state_v1"
FIXTURE_ID = "checkpoint_derived_nonempty_history"
RESOURCE_ID = "kv.layer.0"
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
CONTEXT_CAPACITY = 8000
COMMITTED_LENGTH = 3
PREPARED_LENGTH = 1
BASE_GENERATION = 4
TRANSACTION_ID = 0x4154544E0002
TOKEN_BYTES = KEY_VALUE_HEADS * HEAD_DIM * 2
QUERY_BYTES = QUERY_HEADS * HEAD_DIM * 2
STATE_REGION_BYTES = CONTEXT_CAPACITY * TOKEN_BYTES
STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")

if STATE_METADATA.size != 64 or TRANSACTION_DESCRIPTOR.size != 64:
    raise RuntimeError("attention state descriptor widths differ")


class ProductionAttentionBuildError(ArtifactError):
    """Raised when an attention deployment cannot be built exactly."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    canonical = dict(body)
    return {**canonical, field: sha256_bytes(canonical_json_bytes(canonical))}


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionAttentionBuildError(f"{label} identity differs")


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionAttentionBuildError("artifact path must be a safe relative path")
    return path.as_posix()


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise ProductionAttentionBuildError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionAttentionBuildError(f"{label} is not canonical JSON")
    return value, payload


def _copy_canonical(source: Path, destination: Path) -> None:
    value, payload = _load_canonical(source, destination.name)
    if payload != canonical_json_bytes(value):
        raise ProductionAttentionBuildError(f"{source} is not canonical JSON")
    destination.write_bytes(payload)


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _output_codes(report: Mapping[str, Any], role: str) -> np.ndarray:
    outputs = report.get("outputs")
    if not isinstance(outputs, Mapping) or set(outputs) != {
        "k_rotary",
        "q_rotary",
        "v",
    }:
        raise ProductionAttentionBuildError("Q/K/V output coverage differs")
    record = outputs[role]
    if not isinstance(record, Mapping):
        raise ProductionAttentionBuildError(f"Q/K/V {role} output is malformed")
    expected_shape = {
        "q_rotary": [QUERY_HEADS, HEAD_DIM],
        "k_rotary": [KEY_VALUE_HEADS, HEAD_DIM],
        "v": [KEY_VALUE_HEADS, HEAD_DIM],
    }[role]
    if (
        record.get("dtype") != "bf16"
        or record.get("shape") != expected_shape
        or record.get("size_bytes") != 2 * int(np.prod(expected_shape))
        or record.get("payload_sha256") != EXPECTED_QKV_PAYLOAD_SHA256[role]
    ):
        raise ProductionAttentionBuildError(f"Q/K/V {role} metadata differs")
    raw = record.get("codes")
    if not isinstance(raw, list) or len(raw) != int(np.prod(expected_shape)):
        raise ProductionAttentionBuildError(f"Q/K/V {role} code coverage differs")
    codes = np.asarray(
        [
            require_int(code, f"Q/K/V {role}.codes[{index}]", minimum=0, maximum=0xFFFF)
            for index, code in enumerate(raw)
        ],
        dtype=np.uint16,
    ).reshape(tuple(expected_shape))
    payload = np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")
    if hashlib.sha256(payload).hexdigest() != record["payload_sha256"]:
        raise ProductionAttentionBuildError(f"Q/K/V {role} payload differs")
    if np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise ProductionAttentionBuildError(f"Q/K/V {role} contains nonfinite BF16")
    return np.ascontiguousarray(codes)


def _source_operations(
    model: ProductionModelGraph,
) -> tuple[ProductionOperation, ProductionOperation, ProductionOperation]:
    prepares = [
        operation
        for operation in model.operations
        if operation.kind == "KV_PREPARE" and operation.attributes.get("layer") == 0
    ]
    attentions = [
        operation
        for operation in model.operations
        if operation.kind == "ATTENTION" and operation.attributes.get("layer") == 0
    ]
    commits = [operation for operation in model.operations if operation.kind == "STATE_COMMIT"]
    if len(prepares) != 1 or len(attentions) != 1 or len(commits) != 1:
        raise ProductionAttentionBuildError("source attention operation coverage differs")
    prepare, attention, commit = prepares[0], attentions[0], commits[0]
    if (
        prepare.inputs != ("layer.0.k_rotary", "layer.0.v")
        or prepare.outputs != ("state.kv.0",)
        or prepare.numeric_contract != STATE_CONTRACT
        or attention.inputs != ("layer.0.q_rotary", "state.kv.0")
        or attention.outputs != ("layer.0.attention",)
        or attention.numeric_contract != NUMERIC_CONTRACT
        or commit.operation_id != "state.commit"
        or commit.attributes.get("atomic_state_count") != 36
        or commit.numeric_contract != STATE_CONTRACT
    ):
        raise ProductionAttentionBuildError("source attention semantics differ")
    return prepare, attention, commit


def _problem(capability: ProductionCapability) -> dict[str, Any]:
    vector = capability.vector_engine
    state = capability.state_engine
    if (
        capability.command_abi_minor != ATTENTION_ABI_MINOR
        or vector is None
        or state is None
        or vector.max_attention_context_tokens is None
        or vector.max_attention_context_tokens < CONTEXT_CAPACITY
        or vector.max_query_heads is None
        or vector.max_query_heads < QUERY_HEADS
        or vector.max_key_value_heads is None
        or vector.max_key_value_heads < KEY_VALUE_HEADS
        or vector.attention_head_dim != HEAD_DIM
        or vector.softmax_reduction_lanes != 8
        or state.max_resources_per_transaction < 36
        or not {NUMERIC_CONTRACT, STATE_CONTRACT}
        <= set(capability.qualified_numeric_contracts)
        or not {"transactional_state", "vector_fp32"}
        <= set(capability.qualified_execution_modes)
    ):
        raise ProductionAttentionBuildError(
            "capability does not qualify attention and transactional state"
        )
    return {
        "base_generation": BASE_GENERATION,
        "committed_length": COMMITTED_LENGTH,
        "context_capacity": CONTEXT_CAPACITY,
        "fixture_id": FIXTURE_ID,
        "head_dim": HEAD_DIM,
        "key_value_heads": KEY_VALUE_HEADS,
        "prepared_length": PREPARED_LENGTH,
        "qualified_state_resources": 1,
        "query_heads": QUERY_HEADS,
        "source_atomic_state_count": 36,
        "transaction_id": TRANSACTION_ID,
    }


def _fixture(qualification: Mapping[str, Any]) -> Mapping[str, Any]:
    fixtures = qualification.get("fixtures")
    if not isinstance(fixtures, list):
        raise ProductionAttentionBuildError("attention qualification fixtures differ")
    matches = [item for item in fixtures if isinstance(item, Mapping) and item.get("fixture_id") == FIXTURE_ID]
    if len(matches) != 1:
        raise ProductionAttentionBuildError("qualified nonempty attention fixture differs")
    fixture = matches[0]
    inputs = fixture.get("inputs")
    transaction = fixture.get("transaction")
    if (
        fixture.get("status") != "exact_match"
        or not isinstance(inputs, Mapping)
        or inputs.get("committed_length") != COMMITTED_LENGTH
        or inputs.get("prepared_length") != PREPARED_LENGTH
        or not isinstance(transaction, Mapping)
        or transaction.get("base_generation") != BASE_GENERATION
        or transaction.get("transaction_id") != TRANSACTION_ID
        or transaction.get("committed_length") != COMMITTED_LENGTH + PREPARED_LENGTH
        or transaction.get("next_generation") != BASE_GENERATION + 1
    ):
        raise ProductionAttentionBuildError("qualified nonempty fixture metadata differs")
    return fixture


def _history(k: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    keys = np.stack((np.roll(k, 1, axis=0), k[:, ::-1], np.roll(k, 17, axis=1)))
    values = np.stack((np.roll(v, 1, axis=0), v[:, ::-1], np.roll(v, 23, axis=1)))
    return np.ascontiguousarray(keys), np.ascontiguousarray(values)


def _region_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _hbm_image(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    history_k: np.ndarray,
    history_v: np.ndarray,
    *,
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    cursor = align_up(capability.hbm.base_address + 4096, capability.hbm.burst_bytes)
    records: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {
        "query": _region_payload(q),
        "current_key": _region_payload(k),
        "current_value": _region_payload(v),
    }
    placements: dict[str, int] = {}
    image = bytearray(cursor - capability.hbm.base_address)

    def place(role: str, payload: bytes, allocated: int | None = None) -> None:
        nonlocal cursor
        cursor = align_up(cursor, capability.hbm.burst_bytes)
        offset = cursor - capability.hbm.base_address
        size = len(payload) if allocated is None else allocated
        if len(image) < offset + size:
            image.extend(bytes(offset + size - len(image)))
        image[offset : offset + len(payload)] = payload
        placements[role] = cursor
        records.append(
            {
                "address": cursor,
                "allocated_size_bytes": size,
                "id": role,
                "offset_bytes": offset,
                "payload_sha256": hashlib.sha256(bytes(image[offset : offset + size])).hexdigest(),
                "payload_size_bytes": len(payload),
            }
        )
        cursor += size

    place("query", payloads["query"])
    place("current_key", payloads["current_key"])
    place("current_value", payloads["current_value"])
    cursor = align_up(cursor, 4096)
    place("key_state", _region_payload(history_k), STATE_REGION_BYTES)
    cursor = align_up(cursor, 4096)
    place("value_state", _region_payload(history_v), STATE_REGION_BYTES)
    metadata = STATE_METADATA.pack(
        STATE_MAGIC,
        BASE_GENERATION,
        COMMITTED_LENGTH,
        CONTEXT_CAPACITY,
        placements["key_state"],
        placements["value_state"],
        0,
        bytes(8),
    )
    place("state_metadata", metadata)
    transaction = TRANSACTION_DESCRIPTOR.pack(
        TRANSACTION_MAGIC,
        TRANSACTION_ID,
        BASE_GENERATION,
        COMMITTED_LENGTH,
        PREPARED_LENGTH,
        1,
        placements["state_metadata"],
        bytes(8),
    )
    place("transaction_descriptor", transaction)
    return bytes(image), {"placements": placements, "regions": records}


def _sram_plan(capability: ProductionCapability) -> dict[str, Any]:
    sizes = {
        "query": QUERY_BYTES,
        "current_key": TOKEN_BYTES,
        "current_value": TOKEN_BYTES,
        "attention_output": QUERY_BYTES,
    }
    regions = []
    for bank, role in enumerate(sizes):
        address = capability.sram.bank_base(bank) + capability.sram.word_bytes
        if sizes[role] + capability.sram.word_bytes > capability.sram.bytes_per_bank:
            raise ProductionAttentionBuildError(f"SRAM region {role} exceeds its bank")
        regions.append(
            {
                "address": address,
                "bank": bank,
                "id": role,
                "offset_bytes": capability.sram.word_bytes,
                "size_bytes": sizes[role],
            }
        )
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _by_id(records: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(record["id"]): record for record in records}


def _commands(hbm: Mapping[str, Any], sram: Mapping[str, Any]) -> tuple[ProductionCommand, ...]:
    hp = hbm["placements"]
    sp = _by_id(sram["regions"])
    return (
        ProductionCommand(0, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=1, source0=hp["query"], destination=sp["query"]["address"], size0=QUERY_BYTES),
        ProductionCommand(1, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=0, source0=hp["current_key"], destination=sp["current_key"]["address"], size0=TOKEN_BYTES),
        ProductionCommand(2, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=0, source0=hp["current_value"], destination=sp["current_value"]["address"], size0=TOKEN_BYTES),
        ProductionCommand(3, Opcode.KV_PREPARE_BF16, Engine.STATE, kernel_index=0, source0=sp["current_key"]["address"], source1=sp["current_value"]["address"], destination=hp["key_state"], auxiliary=hp["value_state"], size0=PREPARED_LENGTH, size1=KEY_VALUE_HEADS, size2=HEAD_DIM),
        ProductionCommand(4, Opcode.GQA_ATTENTION_BF16, Engine.VECTOR, kernel_index=1, source0=sp["query"]["address"], source1=hp["key_state"], destination=sp["attention_output"]["address"], auxiliary=hp["value_state"], size0=PREPARED_LENGTH, size1=QUERY_HEADS, size2=KEY_VALUE_HEADS, size3=HEAD_DIM),
        ProductionCommand(5, Opcode.STATE_COMMIT, Engine.STATE, kernel_index=NO_KERNEL, source0=hp["state_metadata"], source1=hp["transaction_descriptor"], size0=CONTEXT_CAPACITY, size1=1),
        ProductionCommand(6, Opcode.COMPLETE, Engine.CONTROL),
    )


def _expected_counters(fixture: Mapping[str, Any]) -> dict[str, int]:
    accounting = fixture.get("accounting")
    if not isinstance(accounting, Mapping):
        raise ProductionAttentionBuildError("attention accounting differs")
    expected_arithmetic = {
        key: require_int(value, f"attention accounting.{key}", minimum=0)
        for key, value in accounting.items()
    }
    visible_state_bytes = (COMMITTED_LENGTH + PREPARED_LENGTH) * 2 * TOKEN_BYTES
    descriptor_reads = 4 * 64
    fixed = {
        "attention_command_count": 1,
        "attention_output_sram_bytes_written": QUERY_BYTES,
        "attention_query_sram_bytes_read": QUERY_BYTES,
        "command_count": 7,
        "complete_command_count": 1,
        "direct_dma_command_count": 3,
        "dma_command_count": 3,
        "dma_sram_bytes_written": QUERY_BYTES + 2 * TOKEN_BYTES,
        "hbm_transferred_bytes_read": QUERY_BYTES + 2 * TOKEN_BYTES + visible_state_bytes + descriptor_reads,
        "hbm_transferred_bytes_written": 2 * TOKEN_BYTES + 64,
        "hbm_useful_bytes_read": QUERY_BYTES + 2 * TOKEN_BYTES + visible_state_bytes + descriptor_reads,
        "hbm_useful_bytes_written": 2 * TOKEN_BYTES + 64,
        "kv_prepare_command_count": 1,
        "kv_prepare_sram_bytes_read": 2 * TOKEN_BYTES,
        "state_commit_command_count": 1,
        "state_metadata_bytes_read": descriptor_reads,
        "state_metadata_bytes_written": 64,
        "state_payload_bytes_read": visible_state_bytes,
        "state_payload_bytes_written": 2 * TOKEN_BYTES,
    }
    return {**fixed, **expected_arithmetic}


def _kernel_ir(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ProductionOperation, ProductionOperation],
) -> dict[str, Any]:
    prepare, attention, commit = operations
    kernels = [
        {
            "attributes": {
                "append_position_symbol": "position_start",
                "generation_check": "exact_expected_generation",
                "state_resource": RESOURCE_ID,
                "transaction_scope": "model_forward_request",
                "visibility": "transaction_private_until_commit",
            },
            "index": 0,
            "inputs": list(prepare.inputs),
            "kind": "KV_PREPARE",
            "numeric_contract": STATE_CONTRACT,
            "outputs": list(prepare.outputs),
            "shape": {
                "head_dim": HEAD_DIM,
                "key_value_heads": KEY_VALUE_HEADS,
                "max_context_tokens": CONTEXT_CAPACITY,
                "tokens_symbol": "span_tokens",
            },
            "source_operation_id": prepare.operation_id,
        },
        {
            "attributes": {
                "causal_mask_bf16_code": 0xFF7F,
                "prepared_state_visibility": "transaction_private",
                "probability_dtype": "bf16",
                "query_heads_per_key_value_head": QUERY_HEADS // KEY_VALUE_HEADS,
                "scale_bf16_code": 0x3DB5,
                "score_reduction_order": "strictly_increasing_head_dimension",
                "softmax_compute_dtype": "fp32",
                "softmax_reduction_lanes": 8,
                "value_reduction_order": "strictly_increasing_context",
            },
            "index": 1,
            "inputs": list(attention.inputs),
            "kind": "ATTENTION",
            "numeric_contract": NUMERIC_CONTRACT,
            "outputs": list(attention.outputs),
            "shape": {
                "head_dim": HEAD_DIM,
                "key_value_heads": KEY_VALUE_HEADS,
                "max_context_tokens": CONTEXT_CAPACITY,
                "query_heads": QUERY_HEADS,
                "query_tokens_symbol": "span_tokens",
            },
            "source_operation_id": attention.operation_id,
        },
        {
            "attributes": {
                "atomic": True,
                "coverage": "qualified_resource_subset",
                "generation_increment": 1,
                "source_atomic_state_count": 36,
                "transaction_scope": "model_forward_request",
            },
            "index": 2,
            "inputs": list(commit.inputs),
            "kind": "STATE_COMMIT",
            "numeric_contract": STATE_CONTRACT,
            "outputs": list(commit.outputs),
            "shape": {"atomic_state_count": 1},
            "source_operation_id": commit.operation_id,
            "state_resources": [RESOURCE_ID],
        },
    ]
    body = {
        "graph_id": model.graph_id,
        "kernels": kernels,
        "qualification_report_id": qualification["report_id"],
        "schema": KERNEL_SCHEMA,
    }
    return _identified(body, "kernel_ir_id")


def _request(model: ProductionModelGraph, operations: tuple[ProductionOperation, ...]) -> dict[str, Any]:
    body = {
        "expected_generation": BASE_GENERATION,
        "fixture_id": FIXTURE_ID,
        "graph_id": model.graph_id,
        "position_start": COMMITTED_LENGTH,
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": [operation.operation_id for operation in operations],
        "span_tokens": PREPARED_LENGTH,
        "state_resource": RESOURCE_ID,
        "transaction_id": TRANSACTION_ID,
    }
    return _identified(body, "request_id")


def _source_lock(
    *,
    model_graph_path: Path,
    qkv_execution_path: Path,
    capability_path: Path,
    qualification_path: Path,
    model: ProductionModelGraph,
    qkv_report: Mapping[str, Any],
    capability: ProductionCapability,
    qualification: Mapping[str, Any],
) -> dict[str, Any]:
    roles = (
        ("model_graph", model_graph_path),
        ("qkv_execution_report", qkv_execution_path),
        ("hardware_capability", capability_path),
        ("qualification_report", qualification_path),
    )
    sources = []
    for role, path in roles:
        digest, size = sha256_file(path)
        sources.append({"role": role, "sha256": digest, "size_bytes": size})
    body = {
        "capability_id": capability.capability_id,
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "qkv_execution_report_id": qkv_report["report_id"],
        "qualification_report_id": qualification["report_id"],
        "schema": SOURCE_LOCK_SCHEMA,
        "sources": sources,
    }
    return _identified(body, "source_lock_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    operations: tuple[ProductionOperation, ...],
    problem: Mapping[str, Any],
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    image: bytes,
    command_payload: bytes,
    fixture: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": _expected_counters(fixture),
        "graph_id": model.graph_id,
        "hbm": {
            "image": {
                "base_address": capability.hbm.base_address,
                "path": HBM_IMAGE_PATH,
                "sha256": hashlib.sha256(image).hexdigest(),
                "size_bytes": len(image),
            },
            "regions": list(hbm["regions"]),
        },
        "numeric_contracts": [STATE_CONTRACT, NUMERIC_CONTRACT],
        "problem": dict(problem),
        "program": {
            "command_count": (len(command_payload) - 32) // 64,
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "qualification_report_id": qualification["report_id"],
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_ids": [operation.operation_id for operation in operations],
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
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    kernel_ir: Mapping[str, Any],
    plan: Mapping[str, Any],
    source_lock: Mapping[str, Any],
    independent_check: Mapping[str, Any],
) -> dict[str, Any]:
    roles = {
        "capability.json": "hardware_capability",
        "checks/independent_check.json": "independent_check",
        "execution_expectations.json": "execution_expectations",
        HBM_IMAGE_PATH: "hbm_image",
        "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
        PHYSICAL_PLAN_PATH: "physical_plan",
        COMMAND_PATH: "command_program",
        "program/commands.disasm": "command_disassembly",
        REQUEST_PATH: "known_request",
        "source.lock.json": "source_lock",
        "source/model_graph.v2.json": "model_graph",
        "source/qkv_execution.json": "qkv_execution_report",
        "source/qualification.json": "qualification_report",
    }
    body = {
        "artifacts": [_artifact(root, path, roles[path]) for path in sorted(roles)],
        "capability_id": capability.capability_id,
        "claim_boundary": [
            "authenticated Qwen layer-0 Q/K/V through nonempty causal GQA and one transactional KV append",
            "neutral attention/state kernels, explicit HBM/SRAM placement, independently checked ABI 2.3 commands, and artifact-only functional execution",
            "one-resource qualification of the 36-resource terminal model-forward commit; not complete terminal-state coverage",
            "uncharacterized functional evidence only; not a complete layer, model decode, timing, RTL, 130-nm, performance, or energy claim",
        ],
        "command_abi": {"major": capability.command_abi_major, "minor": capability.command_abi_minor},
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator attention compiler",
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "capability": "capability.json",
            "command_program": COMMAND_PATH,
            "hbm_image": HBM_IMAGE_PATH,
            "physical_plan": PHYSICAL_PLAN_PATH,
            "request": REQUEST_PATH,
        },
        "graph_id": model.graph_id,
        "independent_check_id": independent_check["check_id"],
        "kernel_ir_id": kernel_ir["kernel_ir_id"],
        "physical_plan_id": plan["physical_plan_id"],
        "qualification_report_id": qualification["report_id"],
        "schema": MANIFEST_SCHEMA,
        "source_lock_id": source_lock["source_lock_id"],
    }
    return _identified(body, "build_id")


def _build_into(
    *,
    qkv_execution_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    root: Path,
) -> dict[str, Any]:
    try:
        model = load_production_model_graph(model_graph_path)
        capability = load_production_capability(capability_path)
        qualification = load_attention_qualification(qualification_path)
    except (
        ProductionModelGraphError,
        ProductionCapabilityError,
        AttentionQualificationError,
    ) as exc:
        raise ProductionAttentionBuildError(f"source admission failed: {exc}") from exc
    qkv_report, qkv_payload = _load_canonical(qkv_execution_path, "Q/K/V execution report")
    _identity(qkv_report, "report_id", "Q/K/V execution report")
    if (
        qkv_report.get("schema") != QKV_EXECUTION_SCHEMA
        or qkv_report.get("status") != "pass"
        or qkv_report.get("build_id") != PINNED_QKV_BUILD_ID
        or qkv_report.get("report_id") != PINNED_QKV_REPORT_ID
        or qualification["source"]["qkv_execution_payload_sha256"]
        != hashlib.sha256(qkv_payload).hexdigest()
        or qualification["source"]["qkv_execution_report_id"] != qkv_report["report_id"]
    ):
        raise ProductionAttentionBuildError("Q/K/V execution handoff differs")
    operations = _source_operations(model)
    problem = _problem(capability)
    fixture = _fixture(qualification)
    q = _output_codes(qkv_report, "q_rotary")
    k = _output_codes(qkv_report, "k_rotary")
    v = _output_codes(qkv_report, "v")
    history_k, history_v = _history(k, v)
    if (
        hashlib.sha256(_region_payload(history_k)).hexdigest()
        != fixture["inputs"]["committed_key_payload_sha256"]
        or hashlib.sha256(_region_payload(history_v)).hexdigest()
        != fixture["inputs"]["committed_value_payload_sha256"]
    ):
        raise ProductionAttentionBuildError("derived committed history differs")
    image, hbm = _hbm_image(q, k, v, history_k, history_v, capability=capability)
    if len(image) > capability.hbm.capacity_bytes:
        raise ProductionAttentionBuildError("attention HBM image exceeds capability")
    sram = _sram_plan(capability)
    commands = _commands(hbm, sram)
    command_payload = encode(commands, abi_minor=capability.command_abi_minor)
    kernel_ir = _kernel_ir(model, qualification, operations)
    plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        operations=operations,
        problem=problem,
        hbm=hbm,
        sram=sram,
        image=image,
        command_payload=command_payload,
        fixture=fixture,
    )
    request = _request(model, operations)
    source_lock = _source_lock(
        model_graph_path=model_graph_path,
        qkv_execution_path=qkv_execution_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        model=model,
        qkv_report=qkv_report,
        capability=capability,
        qualification=qualification,
    )
    for directory in ("checks", "ir", "memory", "physical", "program", "request", "source"):
        (root / directory).mkdir()
    write_canonical_json(root / "capability.json", capability.to_dict())
    write_canonical_json(root / "ir/tensor_kernel_ir.json", kernel_ir)
    (root / HBM_IMAGE_PATH).write_bytes(image)
    write_canonical_json(root / PHYSICAL_PLAN_PATH, plan)
    (root / COMMAND_PATH).write_bytes(command_payload)
    _write_text(
        root / "program/commands.disasm",
        disassemble(commands, abi_minor=ATTENTION_ABI_MINOR),
    )
    write_canonical_json(root / REQUEST_PATH, request)
    write_canonical_json(root / "source.lock.json", source_lock)
    _copy_canonical(model_graph_path, root / "source/model_graph.v2.json")
    _copy_canonical(qkv_execution_path, root / "source/qkv_execution.json")
    _copy_canonical(qualification_path, root / "source/qualification.json")

    from .production_attention_checking import check_attention_candidate

    independent = check_attention_candidate(
        qkv_execution_path=qkv_execution_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        root=root,
    )
    write_canonical_json(root / "checks/independent_check.json", independent)
    expectations = _identified(
        {
            "check_id": independent["check_id"],
            "committed_state_sha256": fixture["transaction"]["committed_state_sha256"],
            "counters": independent["expected_counters"],
            "output_payload_sha256": {
                role: fixture["outputs"][role]["payload_sha256"]
                for role in ("attention", "probabilities", "scaled_scores")
            },
            "qualification_report_id": qualification["report_id"],
            "schema": EXPECTATIONS_SCHEMA,
        },
        "expectations_id",
    )
    write_canonical_json(root / "execution_expectations.json", expectations)
    manifest = _manifest(
        root,
        model=model,
        qualification=qualification,
        capability=capability,
        kernel_ir=kernel_ir,
        plan=plan,
        source_lock=source_lock,
        independent_check=independent,
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_attention_deployment(
    *,
    qkv_execution_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Build and atomically publish one independently checked attention slice."""

    sources = {
        "Q/K/V execution report": Path(qkv_execution_path).resolve(),
        "model graph": Path(model_graph_path).resolve(),
        "capability": Path(capability_path).resolve(),
        "qualification report": Path(qualification_path).resolve(),
    }
    output = Path(output).resolve()
    for label, path in sources.items():
        if not path.is_file():
            raise ProductionAttentionBuildError(f"{label} does not exist: {path}")
    if output.exists():
        raise ProductionAttentionBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        manifest = _build_into(
            qkv_execution_path=sources["Q/K/V execution report"],
            model_graph_path=sources["model graph"],
            capability_path=sources["capability"],
            qualification_path=sources["qualification report"],
            root=temporary,
        )
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


__all__ = [
    "COMMAND_PATH",
    "COMPILER_VERSION",
    "EXPECTATIONS_SCHEMA",
    "HBM_IMAGE_PATH",
    "KERNEL_SCHEMA",
    "MANIFEST_SCHEMA",
    "PHYSICAL_PLAN_PATH",
    "PHYSICAL_PLAN_SCHEMA",
    "ProductionAttentionBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_attention_deployment",
]
