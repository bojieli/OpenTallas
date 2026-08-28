"""Independent inverse checker for attention/KV deployment artifacts.

This module intentionally does not import the attention compiler or its lowering
helpers.  It reconstructs source payloads, placement, neutral kernels, commands,
and counter formulae from the external handoff and frozen contracts.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import struct
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
)
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_command import (
    ABI_MAJOR,
    ABI_MINOR,
    Engine,
    NO_KERNEL,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi,
    decode,
    disassemble,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)


COMPILER_VERSION = "tensor-accelerator-production-attention-0.1.0"
CHECK_SCHEMA = "opentallas.tensor_accelerator.attention_independent_check.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.attention_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.attention_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.attention_source_lock.v1"
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


class ProductionAttentionCheckError(ArtifactError):
    """Raised when any candidate artifact cannot be independently reconstructed."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    canonical = dict(body)
    return {**canonical, field: sha256_bytes(canonical_json_bytes(canonical))}


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionAttentionCheckError(str(exc)) from exc
    if observed != expected:
        raise ProductionAttentionCheckError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ProductionAttentionCheckError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionAttentionCheckError(f"{label} must be a safe relative path")
    return path.as_posix()


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionAttentionCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionAttentionCheckError(f"{label} is not canonical JSON")
    return value, payload


def _external_copy(root: Path, internal: str, external: Path, label: str) -> bytes:
    try:
        candidate = (root / internal).read_bytes()
        source = external.read_bytes()
    except OSError as exc:
        raise ProductionAttentionCheckError(f"cannot read {label}: {exc}") from exc
    if candidate != source:
        raise ProductionAttentionCheckError(f"retained {label} differs from its source")
    return source


def _output_codes(report: Mapping[str, Any], role: str) -> np.ndarray:
    outputs = report.get("outputs")
    if not isinstance(outputs, Mapping) or set(outputs) != {"k_rotary", "q_rotary", "v"}:
        raise ProductionAttentionCheckError("Q/K/V output coverage differs")
    record = outputs[role]
    expected_shape = {
        "q_rotary": [QUERY_HEADS, HEAD_DIM],
        "k_rotary": [KEY_VALUE_HEADS, HEAD_DIM],
        "v": [KEY_VALUE_HEADS, HEAD_DIM],
    }[role]
    if (
        not isinstance(record, Mapping)
        or record.get("dtype") != "bf16"
        or record.get("shape") != expected_shape
        or record.get("size_bytes") != 2 * int(np.prod(expected_shape))
        or record.get("payload_sha256") != EXPECTED_QKV_PAYLOAD_SHA256[role]
    ):
        raise ProductionAttentionCheckError(f"Q/K/V {role} metadata differs")
    raw = record.get("codes")
    if not isinstance(raw, list) or len(raw) != int(np.prod(expected_shape)):
        raise ProductionAttentionCheckError(f"Q/K/V {role} code coverage differs")
    codes = np.asarray(
        [
            require_int(code, f"Q/K/V {role}.codes[{index}]", minimum=0, maximum=0xFFFF)
            for index, code in enumerate(raw)
        ],
        dtype=np.uint16,
    ).reshape(tuple(expected_shape))
    payload = np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")
    if hashlib.sha256(payload).hexdigest() != record["payload_sha256"]:
        raise ProductionAttentionCheckError(f"Q/K/V {role} payload differs")
    return np.ascontiguousarray(codes)


def _operations(model: ProductionModelGraph) -> tuple[ProductionOperation, ProductionOperation, ProductionOperation]:
    prepares = [op for op in model.operations if op.kind == "KV_PREPARE" and op.attributes.get("layer") == 0]
    attentions = [op for op in model.operations if op.kind == "ATTENTION" and op.attributes.get("layer") == 0]
    commits = [op for op in model.operations if op.kind == "STATE_COMMIT"]
    if len(prepares) != 1 or len(attentions) != 1 or len(commits) != 1:
        raise ProductionAttentionCheckError("source operation coverage differs")
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
    ):
        raise ProductionAttentionCheckError("source operation semantics differ")
    return prepare, attention, commit


def _fixture(qualification: Mapping[str, Any]) -> Mapping[str, Any]:
    fixtures = qualification.get("fixtures")
    if not isinstance(fixtures, list):
        raise ProductionAttentionCheckError("qualification fixture coverage differs")
    selected = [item for item in fixtures if isinstance(item, Mapping) and item.get("fixture_id") == FIXTURE_ID]
    if len(selected) != 1:
        raise ProductionAttentionCheckError("nonempty fixture identity differs")
    fixture = selected[0]
    if (
        fixture.get("status") != "exact_match"
        or fixture.get("inputs", {}).get("committed_length") != COMMITTED_LENGTH
        or fixture.get("inputs", {}).get("prepared_length") != PREPARED_LENGTH
        or fixture.get("transaction", {}).get("base_generation") != BASE_GENERATION
        or fixture.get("transaction", {}).get("transaction_id") != TRANSACTION_ID
    ):
        raise ProductionAttentionCheckError("nonempty fixture metadata differs")
    return fixture


def _problem(capability: ProductionCapability) -> dict[str, Any]:
    vector = capability.vector_engine
    state = capability.state_engine
    if (
        (capability.command_abi_major, capability.command_abi_minor) != (ABI_MAJOR, ABI_MINOR)
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
        or not {NUMERIC_CONTRACT, STATE_CONTRACT} <= set(capability.qualified_numeric_contracts)
    ):
        raise ProductionAttentionCheckError("capability bounds differ")
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


def _payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _reconstruct_hbm(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    *,
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, int], list[dict[str, Any]]]:
    history_k = np.stack((np.roll(k, 1, axis=0), k[:, ::-1], np.roll(k, 17, axis=1)))
    history_v = np.stack((np.roll(v, 1, axis=0), v[:, ::-1], np.roll(v, 23, axis=1)))
    cursor = align_up(capability.hbm.base_address + 4096, capability.hbm.burst_bytes)
    image = bytearray(cursor - capability.hbm.base_address)
    placements: dict[str, int] = {}
    records: list[dict[str, Any]] = []

    def place(role: str, raw: bytes, allocated: int | None = None) -> None:
        nonlocal cursor
        cursor = align_up(cursor, capability.hbm.burst_bytes)
        offset = cursor - capability.hbm.base_address
        size = len(raw) if allocated is None else allocated
        if len(image) < offset + size:
            image.extend(bytes(offset + size - len(image)))
        image[offset : offset + len(raw)] = raw
        placements[role] = cursor
        records.append(
            {
                "address": cursor,
                "allocated_size_bytes": size,
                "id": role,
                "offset_bytes": offset,
                "payload_sha256": hashlib.sha256(bytes(image[offset : offset + size])).hexdigest(),
                "payload_size_bytes": len(raw),
            }
        )
        cursor += size

    place("query", _payload(q))
    place("current_key", _payload(k))
    place("current_value", _payload(v))
    cursor = align_up(cursor, 4096)
    place("key_state", _payload(history_k), STATE_REGION_BYTES)
    cursor = align_up(cursor, 4096)
    place("value_state", _payload(history_v), STATE_REGION_BYTES)
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
    descriptor = TRANSACTION_DESCRIPTOR.pack(
        TRANSACTION_MAGIC,
        TRANSACTION_ID,
        BASE_GENERATION,
        COMMITTED_LENGTH,
        PREPARED_LENGTH,
        1,
        placements["state_metadata"],
        bytes(8),
    )
    place("transaction_descriptor", descriptor)
    return bytes(image), placements, records


def _sram(capability: ProductionCapability) -> dict[str, Any]:
    sizes = {
        "query": QUERY_BYTES,
        "current_key": TOKEN_BYTES,
        "current_value": TOKEN_BYTES,
        "attention_output": QUERY_BYTES,
    }
    return {
        "addressing": "bank_base_plus_byte_offset",
        "regions": [
            {
                "address": capability.sram.bank_base(bank) + capability.sram.word_bytes,
                "bank": bank,
                "id": role,
                "offset_bytes": capability.sram.word_bytes,
                "size_bytes": size,
            }
            for bank, (role, size) in enumerate(sizes.items())
        ],
    }


def _commands(placements: Mapping[str, int], sram: Mapping[str, Any]) -> tuple[ProductionCommand, ...]:
    regions = {record["id"]: record for record in sram["regions"]}
    return (
        ProductionCommand(0, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=1, source0=placements["query"], destination=regions["query"]["address"], size0=QUERY_BYTES),
        ProductionCommand(1, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=0, source0=placements["current_key"], destination=regions["current_key"]["address"], size0=TOKEN_BYTES),
        ProductionCommand(2, Opcode.DMA_HBM_TO_SRAM, Engine.DMA, kernel_index=0, source0=placements["current_value"], destination=regions["current_value"]["address"], size0=TOKEN_BYTES),
        ProductionCommand(3, Opcode.KV_PREPARE_BF16, Engine.STATE, kernel_index=0, source0=regions["current_key"]["address"], source1=regions["current_value"]["address"], destination=placements["key_state"], auxiliary=placements["value_state"], size0=PREPARED_LENGTH, size1=KEY_VALUE_HEADS, size2=HEAD_DIM),
        ProductionCommand(4, Opcode.GQA_ATTENTION_BF16, Engine.VECTOR, kernel_index=1, source0=regions["query"]["address"], source1=placements["key_state"], destination=regions["attention_output"]["address"], auxiliary=placements["value_state"], size0=PREPARED_LENGTH, size1=QUERY_HEADS, size2=KEY_VALUE_HEADS, size3=HEAD_DIM),
        ProductionCommand(5, Opcode.STATE_COMMIT, Engine.STATE, kernel_index=NO_KERNEL, source0=placements["state_metadata"], source1=placements["transaction_descriptor"], size0=CONTEXT_CAPACITY, size1=1),
        ProductionCommand(6, Opcode.COMPLETE, Engine.CONTROL),
    )


def _counters(fixture: Mapping[str, Any]) -> dict[str, int]:
    accounting = fixture.get("accounting")
    if not isinstance(accounting, Mapping):
        raise ProductionAttentionCheckError("qualification accounting differs")
    arithmetic = {
        key: require_int(value, f"accounting.{key}", minimum=0)
        for key, value in accounting.items()
    }
    visible = (COMMITTED_LENGTH + PREPARED_LENGTH) * 2 * TOKEN_BYTES
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
        "hbm_transferred_bytes_read": QUERY_BYTES + 2 * TOKEN_BYTES + visible + descriptor_reads,
        "hbm_transferred_bytes_written": 2 * TOKEN_BYTES + 64,
        "hbm_useful_bytes_read": QUERY_BYTES + 2 * TOKEN_BYTES + visible + descriptor_reads,
        "hbm_useful_bytes_written": 2 * TOKEN_BYTES + 64,
        "kv_prepare_command_count": 1,
        "kv_prepare_sram_bytes_read": 2 * TOKEN_BYTES,
        "state_commit_command_count": 1,
        "state_metadata_bytes_read": descriptor_reads,
        "state_metadata_bytes_written": 64,
        "state_payload_bytes_read": visible,
        "state_payload_bytes_written": 2 * TOKEN_BYTES,
    }
    return {**fixed, **arithmetic}


def _kernel_expected(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ProductionOperation, ProductionOperation],
) -> dict[str, Any]:
    prepare, attention, commit = operations
    body = {
        "graph_id": model.graph_id,
        "kernels": [
            {
                "attributes": {"append_position_symbol": "position_start", "generation_check": "exact_expected_generation", "state_resource": RESOURCE_ID, "transaction_scope": "model_forward_request", "visibility": "transaction_private_until_commit"},
                "index": 0,
                "inputs": list(prepare.inputs),
                "kind": "KV_PREPARE",
                "numeric_contract": STATE_CONTRACT,
                "outputs": list(prepare.outputs),
                "shape": {"head_dim": HEAD_DIM, "key_value_heads": KEY_VALUE_HEADS, "max_context_tokens": CONTEXT_CAPACITY, "tokens_symbol": "span_tokens"},
                "source_operation_id": prepare.operation_id,
            },
            {
                "attributes": {"causal_mask_bf16_code": 0xFF7F, "prepared_state_visibility": "transaction_private", "probability_dtype": "bf16", "query_heads_per_key_value_head": 4, "scale_bf16_code": 0x3DB5, "score_reduction_order": "strictly_increasing_head_dimension", "softmax_compute_dtype": "fp32", "softmax_reduction_lanes": 8, "value_reduction_order": "strictly_increasing_context"},
                "index": 1,
                "inputs": list(attention.inputs),
                "kind": "ATTENTION",
                "numeric_contract": NUMERIC_CONTRACT,
                "outputs": list(attention.outputs),
                "shape": {"head_dim": HEAD_DIM, "key_value_heads": KEY_VALUE_HEADS, "max_context_tokens": CONTEXT_CAPACITY, "query_heads": QUERY_HEADS, "query_tokens_symbol": "span_tokens"},
                "source_operation_id": attention.operation_id,
            },
            {
                "attributes": {"atomic": True, "coverage": "qualified_resource_subset", "generation_increment": 1, "source_atomic_state_count": 36, "transaction_scope": "model_forward_request"},
                "index": 2,
                "inputs": list(commit.inputs),
                "kind": "STATE_COMMIT",
                "numeric_contract": STATE_CONTRACT,
                "outputs": list(commit.outputs),
                "shape": {"atomic_state_count": 1},
                "source_operation_id": commit.operation_id,
                "state_resources": [RESOURCE_ID],
            },
        ],
        "qualification_report_id": qualification["report_id"],
        "schema": KERNEL_SCHEMA,
    }
    return _identified(body, "kernel_ir_id")


def check_attention_candidate(
    *,
    qkv_execution_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct and validate one candidate deployment."""

    root = Path(root).resolve()
    try:
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
        qualification = load_attention_qualification(Path(qualification_path))
    except (ProductionModelGraphError, ProductionCapabilityError, AttentionQualificationError) as exc:
        raise ProductionAttentionCheckError(f"external source admission failed: {exc}") from exc
    _external_copy(root, "source/model_graph.v2.json", Path(model_graph_path), "model graph")
    qkv_payload = _external_copy(root, "source/qkv_execution.json", Path(qkv_execution_path), "Q/K/V execution report")
    _external_copy(root, "source/qualification.json", Path(qualification_path), "attention qualification")
    candidate_capability, _ = _load_canonical(root / "capability.json", "candidate capability")
    if candidate_capability != capability.to_dict():
        raise ProductionAttentionCheckError("candidate capability differs")
    qkv_report, external_payload = _load_canonical(Path(qkv_execution_path), "external Q/K/V execution report")
    _identity(qkv_report, "report_id", "Q/K/V execution report")
    if (
        qkv_payload != external_payload
        or qkv_report.get("schema") != QKV_EXECUTION_SCHEMA
        or qkv_report.get("status") != "pass"
        or qkv_report.get("build_id") != PINNED_QKV_BUILD_ID
        or qkv_report.get("report_id") != PINNED_QKV_REPORT_ID
        or qualification["source"]["qkv_execution_payload_sha256"] != hashlib.sha256(qkv_payload).hexdigest()
    ):
        raise ProductionAttentionCheckError("Q/K/V handoff identity differs")
    operations = _operations(model)
    fixture = _fixture(qualification)
    problem = _problem(capability)
    q = _output_codes(qkv_report, "q_rotary")
    k = _output_codes(qkv_report, "k_rotary")
    v = _output_codes(qkv_report, "v")
    image, placements, hbm_regions = _reconstruct_hbm(q, k, v, capability=capability)
    try:
        candidate_image = (root / HBM_IMAGE_PATH).read_bytes()
    except OSError as exc:
        raise ProductionAttentionCheckError(f"cannot read HBM image: {exc}") from exc
    if candidate_image != image:
        raise ProductionAttentionCheckError("HBM image differs from independent reconstruction")
    sram = _sram(capability)
    commands = _commands(placements, sram)
    try:
        command_payload = (root / COMMAND_PATH).read_bytes()
        decoded = decode(command_payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionAttentionCheckError(f"cannot decode command program: {exc}") from exc
    if decoded != commands or command_abi(command_payload) != (ABI_MAJOR, ABI_MINOR):
        raise ProductionAttentionCheckError("command program differs from independent schedule")
    try:
        emitted_disassembly = (root / "program/commands.disasm").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProductionAttentionCheckError(f"cannot read command disassembly: {exc}") from exc
    if emitted_disassembly != disassemble(commands, abi_minor=ABI_MINOR):
        raise ProductionAttentionCheckError("command disassembly differs")
    kernel, _ = _load_canonical(root / "ir/tensor_kernel_ir.json", "kernel IR")
    _identity(kernel, "kernel_ir_id", "kernel IR")
    expected_kernel = _kernel_expected(model, qualification, operations)
    if kernel != expected_kernel:
        raise ProductionAttentionCheckError("kernel IR differs from neutral source semantics")
    request, _ = _load_canonical(root / REQUEST_PATH, "execution request")
    _identity(request, "request_id", "execution request")
    expected_request = _identified(
        {
            "expected_generation": BASE_GENERATION,
            "fixture_id": FIXTURE_ID,
            "graph_id": model.graph_id,
            "position_start": COMMITTED_LENGTH,
            "schema": REQUEST_SCHEMA,
            "source_operation_ids": [op.operation_id for op in operations],
            "span_tokens": PREPARED_LENGTH,
            "state_resource": RESOURCE_ID,
            "transaction_id": TRANSACTION_ID,
        },
        "request_id",
    )
    if request != expected_request:
        raise ProductionAttentionCheckError("execution request differs")
    counters = _counters(fixture)
    plan, _ = _load_canonical(root / PHYSICAL_PLAN_PATH, "physical plan")
    _identity(plan, "physical_plan_id", "physical plan")
    expected_plan = _identified(
        {
            "capability_id": capability.capability_id,
            "expected_counters": counters,
            "graph_id": model.graph_id,
            "hbm": {
                "image": {"base_address": capability.hbm.base_address, "path": HBM_IMAGE_PATH, "sha256": hashlib.sha256(image).hexdigest(), "size_bytes": len(image)},
                "regions": hbm_regions,
            },
            "numeric_contracts": [STATE_CONTRACT, NUMERIC_CONTRACT],
            "problem": problem,
            "program": {"command_count": len(commands), "path": COMMAND_PATH, "sha256": hashlib.sha256(command_payload).hexdigest(), "size_bytes": len(command_payload)},
            "qualification_report_id": qualification["report_id"],
            "schema": PHYSICAL_PLAN_SCHEMA,
            "source_operation_ids": [op.operation_id for op in operations],
            "sram": sram,
        },
        "physical_plan_id",
    )
    if plan != expected_plan:
        raise ProductionAttentionCheckError("physical plan differs from reconstruction")
    source_lock, _ = _load_canonical(root / "source.lock.json", "source lock")
    _identity(source_lock, "source_lock_id", "source lock")
    source_records = []
    for role, path in (
        ("model_graph", Path(model_graph_path)),
        ("qkv_execution_report", Path(qkv_execution_path)),
        ("hardware_capability", Path(capability_path)),
        ("qualification_report", Path(qualification_path)),
    ):
        digest, size = sha256_file(path)
        source_records.append({"role": role, "sha256": digest, "size_bytes": size})
    expected_lock = _identified(
        {
            "capability_id": capability.capability_id,
            "compiler_version": COMPILER_VERSION,
            "graph_id": model.graph_id,
            "qkv_execution_report_id": qkv_report["report_id"],
            "qualification_report_id": qualification["report_id"],
            "schema": SOURCE_LOCK_SCHEMA,
            "sources": source_records,
        },
        "source_lock_id",
    )
    if source_lock != expected_lock:
        raise ProductionAttentionCheckError("source lock differs")
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": counters,
        "graph_id": model.graph_id,
        "hbm_image_sha256": hashlib.sha256(image).hexdigest(),
        "kernel_ir_id": kernel["kernel_ir_id"],
        "physical_plan_id": plan["physical_plan_id"],
        "qualification_report_id": qualification["report_id"],
        "request_id": request["request_id"],
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock["source_lock_id"],
        "status": "pass",
        "verified": {
            "abi_backward_boundary": "2.3 only; frozen 2.0, 2.1, and 2.2 artifacts remain separately replayed",
            "attention_state_causality": True,
            "hbm_payload_reconstruction": True,
            "neutral_kernel_no_physical_fields": True,
            "state_commit_scope": "one_resource_qualification_of_36_resource_terminal_commit",
        },
    }
    return _identified(body, "check_id")


__all__ = [
    "CHECK_SCHEMA",
    "ProductionAttentionCheckError",
    "check_attention_candidate",
]
