"""Independent inverse checker for one command-connected Qwen layer.

This module intentionally does not import the connected-layer compiler.  It
authenticates all external evidence, rereads the locked checkpoint, rediscovers
the layer operations, reconstructs every HBM byte and SRAM range, rebuilds the
ABI program, and derives the value, state, saturation, and counter expectations.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import struct
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.frontend.checkpoint import CheckpointError, load_checkpoint_lock
from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE
from runtime.tensor_accelerator.rope import coefficient_table_bf16

from .attention_qualification import (
    AttentionQualificationError,
    load_attention_qualification,
)
from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    load_strict_json,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
from .layer_qualification import LayerQualificationError, load_layer_qualification
from .production_attention_checking import (
    ProductionAttentionCheckError,
    _counters as attention_counters,
    _fixture as discover_attention_fixture,
    _operations as discover_attention_operations,
)
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_command import (
    ABI_MAJOR,
    ELEMENTWISE_ABI_MINOR,
    Engine,
    MATMUL_FINAL,
    MATMUL_INIT,
    NO_KERNEL,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi,
    decode,
    disassemble,
)
from .production_layer_downstream_checking import (
    ProductionLayerDownstreamCheckError,
    _checkpoint_payloads as read_downstream_payloads,
    _counters as downstream_counters,
    _operations as discover_downstream_operations,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)
from .production_qkv_checking import (
    ProductionQKVCheckError,
    _expected_counters as qkv_counters,
    _read_sources as read_qkv_payloads,
    _source_semantics as discover_qkv_operations,
)
from .qkv_qualification import QKVQualificationError, load_qkv_qualification


COMPILER_VERSION = "tensor-accelerator-production-connected-layer-0.1.0"
CHECK_SCHEMA = "opentallas.tensor_accelerator.connected_layer_independent_check.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.connected_layer_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.connected_layer_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.connected_layer_source_lock.v1"
QKV_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qkv_execution.v1"
ATTENTION_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.attention_execution.v1"
DOWNSTREAM_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.layer_downstream_execution.v1"
)

HBM_IMAGE_PATH = "memory/hbm_connected_layer.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"

LOOKUP_CONTRACT = "bf16_payload_lookup_v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
ROPE_CONTRACT = "qwen3_rope_fp32_bf16_v1"
STATE_CONTRACT = "bf16_byte_preserving_state_v1"
ATTENTION_CONTRACT = "qwen3_gqa_fp32_softmax_bf16_v1"
ADD_CONTRACT = "bf16_add_rne_v1"
SILU_CONTRACT = "qwen3_silu_mul_bf16_v1"
NUMERIC_CONTRACTS = [
    ADD_CONTRACT,
    LOOKUP_CONTRACT,
    MATRIX_CONTRACT,
    STATE_CONTRACT,
    ATTENTION_CONTRACT,
    RMSNORM_CONTRACT,
    ROPE_CONTRACT,
    SILU_CONTRACT,
]

HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
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
N_TILE = 64
K_TILE = 256

STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")
COEFFICIENT_TABLE_SHA256 = (
    "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
)
FIXTURE_ID = "checkpoint_derived_nonempty_history"
RESOURCE_ID = "kv.layer.0"

PROJECTION_SPECS = (
    ("q", "attention_norm", 2, "q_raw", "q_projection_weight"),
    ("k", "attention_norm", 3, "k_raw", "k_projection_weight"),
    ("v", "attention_norm", 4, "v", "v_projection_weight"),
    (
        "attention_output",
        "attention",
        10,
        "attention_projected",
        "attention_output_weight",
    ),
    ("gate", "mlp_norm", 13, "gate", "gate_projection_weight"),
    ("up", "mlp_norm", 14, "up", "up_projection_weight"),
    ("down", "gated_mlp", 16, "down", "down_projection_weight"),
)


class ProductionConnectedLayerCheckError(ArtifactError):
    """Raised when the connected-layer candidate cannot be reconstructed."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = dict(body)
    return {**value, field: sha256_bytes(canonical_json_bytes(value))}


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionConnectedLayerCheckError(str(exc)) from exc
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionConnectedLayerCheckError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise ProductionConnectedLayerCheckError(
            f"{label} must be a safe relative path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProductionConnectedLayerCheckError(
            f"{label} must be a safe relative path"
        )
    return path.as_posix()


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionConnectedLayerCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionConnectedLayerCheckError(f"{label} is not canonical JSON")
    return value, payload


def _passing_report(
    path: Path, label: str, schema: str
) -> tuple[dict[str, Any], bytes]:
    report, payload = _load_canonical(path, label)
    _identity(report, "report_id", label)
    if report.get("schema") != schema or report.get("status") != "pass":
        raise ProductionConnectedLayerCheckError(f"{label} schema or status differs")
    return report, payload


def _external_copy(root: Path, internal: str, external: Path, label: str) -> bytes:
    try:
        retained = (root / internal).read_bytes()
        source = external.read_bytes()
    except OSError as exc:
        raise ProductionConnectedLayerCheckError(f"cannot read {label}: {exc}") from exc
    if retained != source:
        raise ProductionConnectedLayerCheckError(
            f"retained {label} differs from its external source"
        )
    return source


def _output_codes(report: Mapping[str, Any], role: str) -> np.ndarray:
    shape = {
        "q_rotary": [QUERY_HEADS, HEAD_DIM],
        "k_rotary": [KEY_VALUE_HEADS, HEAD_DIM],
        "v": [KEY_VALUE_HEADS, HEAD_DIM],
    }[role]
    record = report.get("outputs", {}).get(role)
    if (
        not isinstance(record, Mapping)
        or record.get("dtype") != "bf16"
        or record.get("shape") != shape
        or not isinstance(record.get("codes"), list)
        or len(record["codes"]) != int(np.prod(shape))
    ):
        raise ProductionConnectedLayerCheckError(
            f"Q/K/V output {role!r} coverage differs"
        )
    values = np.asarray(record["codes"], dtype=np.uint16).reshape(shape)
    if hashlib.sha256(
        values.astype("<u2", copy=False).tobytes()
    ).hexdigest() != record.get("payload_sha256"):
        raise ProductionConnectedLayerCheckError(
            f"Q/K/V output {role!r} payload differs"
        )
    return values


def _bundle(
    *,
    qkv_qualification: Mapping[str, Any],
    qkv_report: Mapping[str, Any],
    qkv_payload: bytes,
    attention_qualification: Mapping[str, Any],
    attention_report: Mapping[str, Any],
    attention_payload: bytes,
    downstream_qualification: Mapping[str, Any],
    downstream_report: Mapping[str, Any],
) -> tuple[dict[str, str], Mapping[str, Any]]:
    try:
        fixture = discover_attention_fixture(attention_qualification)
    except ProductionAttentionCheckError as exc:
        raise ProductionConnectedLayerCheckError(str(exc)) from exc
    qkv_hashes = {
        role: qkv_report["outputs"][role]["payload_sha256"]
        for role in ("k_rotary", "q_rotary", "v")
    }
    attention_hashes = {
        role: attention_report["outputs"][role]["payload_sha256"]
        for role in ("attention", "probabilities", "scaled_scores")
    }
    source = attention_qualification.get("source", {})
    binding = downstream_qualification.get("attention_input", {})
    if (
        qkv_hashes
        != {
            role: qkv_qualification["outputs"][role]["payload_sha256"]
            for role in qkv_hashes
        }
        or source.get("qkv_build_id") != qkv_report.get("build_id")
        or source.get("qkv_execution_report_id") != qkv_report.get("report_id")
        or source.get("qkv_execution_payload_sha256")
        != hashlib.sha256(qkv_payload).hexdigest()
        or source.get("qkv_output_payload_sha256") != qkv_hashes
        or attention_report.get("qualification_report_id")
        != attention_qualification["report_id"]
        or attention_hashes
        != {
            role: fixture["outputs"][role]["payload_sha256"]
            for role in attention_hashes
        }
        or attention_report.get("state", {}).get("state_sha256")
        != fixture["transaction"]["committed_state_sha256"]
        or binding.get("build_id") != attention_report.get("build_id")
        or binding.get("report_id") != attention_report.get("report_id")
        or binding.get("qualification_report_id")
        != attention_qualification["report_id"]
        or binding.get("payload_sha256") != attention_hashes["attention"]
        or downstream_report.get("qualification_report_id")
        != downstream_qualification["report_id"]
        or downstream_report.get("intermediate_payload_sha256")
        != {
            role: downstream_qualification["intermediates"][role]["payload_sha256"]
            for role in sorted(downstream_qualification["intermediates"])
        }
        or downstream_report.get("output", {}).get("hidden_1", {}).get("payload_sha256")
        != downstream_qualification["output"]["hidden_1"]["payload_sha256"]
    ):
        raise ProductionConnectedLayerCheckError(
            "qualification and retained execution evidence do not form one chain"
        )
    identities = {
        "attention_execution_report_id": attention_report["report_id"],
        "attention_qualification_report_id": attention_qualification["report_id"],
        "downstream_execution_report_id": downstream_report["report_id"],
        "downstream_qualification_report_id": downstream_qualification["report_id"],
        "qkv_execution_report_id": qkv_report["report_id"],
        "qkv_qualification_report_id": qkv_qualification["report_id"],
    }
    body = {
        "attention_execution_payload_sha256": hashlib.sha256(
            attention_payload
        ).hexdigest(),
        **identities,
    }
    return {
        **identities,
        "qualification_bundle_id": sha256_bytes(canonical_json_bytes(body)),
    }, fixture


def _operations(
    model: ProductionModelGraph,
    *,
    lock_id: str,
    qkv_qualification: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
) -> tuple[ProductionOperation, ...]:
    try:
        qkv = discover_qkv_operations(model, qkv_qualification, lock_id)
        attention = discover_attention_operations(model)
        downstream = discover_downstream_operations(model, downstream_qualification)
    except (
        ProductionQKVCheckError,
        ProductionAttentionCheckError,
        ProductionLayerDownstreamCheckError,
    ) as exc:
        raise ProductionConnectedLayerCheckError(
            f"connected source semantics differ: {exc}"
        ) from exc
    ordered = (*qkv, attention[0], attention[1], *downstream, attention[2])
    expected = (*tuple(f"node.{index:04d}" for index in range(18)), "state.commit")
    if (
        len(ordered) != 19
        or len({operation.operation_id for operation in ordered}) != 19
        or tuple(operation.operation_id for operation in ordered) != expected
    ):
        raise ProductionConnectedLayerCheckError(
            "connected source-operation identity or order differs"
        )
    return ordered


def _problem(
    *,
    qkv_qualification: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
    fixture: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, Any]:
    vector = capability.vector_engine
    state = capability.state_engine
    required = set(NUMERIC_CONTRACTS) - {LOOKUP_CONTRACT}
    if (
        (capability.command_abi_major, capability.command_abi_minor)
        != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
        or vector is None
        or state is None
        or capability.tensor_engine.max_m < 1
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
        or vector.max_rows < QUERY_HEADS + KEY_VALUE_HEADS
        or vector.max_width < INTERMEDIATE_WIDTH
        or vector.max_rope_positions is None
        or vector.max_rope_positions < CONTEXT_CAPACITY
        or vector.max_query_heads is None
        or vector.max_query_heads < QUERY_HEADS
        or vector.max_key_value_heads is None
        or vector.max_key_value_heads < KEY_VALUE_HEADS
        or vector.rope_head_dim != HEAD_DIM
        or vector.max_attention_context_tokens is None
        or vector.max_attention_context_tokens < CONTEXT_CAPACITY
        or vector.attention_head_dim != HEAD_DIM
        or vector.softmax_reduction_lanes != 8
        or state.max_resources_per_transaction < 36
        or not required <= set(capability.qualified_numeric_contracts)
        or not {"bf16_tensor", "transactional_state", "vector_fp32"}
        <= set(capability.qualified_execution_modes)
    ):
        raise ProductionConnectedLayerCheckError(
            "capability does not admit the complete connected layer"
        )
    source_shapes = {
        "q": qkv_qualification["sources"]["q_projection_weight"]["shape"],
        "k": qkv_qualification["sources"]["k_projection_weight"]["shape"],
        "v": qkv_qualification["sources"]["v_projection_weight"]["shape"],
        "attention_output": downstream_qualification["sources"][
            "attention_output_weight"
        ]["shape"],
        "gate": downstream_qualification["sources"]["gate_projection_weight"]["shape"],
        "up": downstream_qualification["sources"]["up_projection_weight"]["shape"],
        "down": downstream_qualification["sources"]["down_projection_weight"]["shape"],
    }
    if source_shapes != {
        "q": [4096, 4096],
        "k": [1024, 4096],
        "v": [1024, 4096],
        "attention_output": [4096, 4096],
        "gate": [12288, 4096],
        "up": [12288, 4096],
        "down": [4096, 12288],
    }:
        raise ProductionConnectedLayerCheckError(
            "connected projection source shapes differ"
        )
    projections = []
    for (
        projection_id,
        input_region,
        kernel_index,
        output_region,
        source_role,
    ) in PROJECTION_SPECS:
        n, k = source_shapes[projection_id]
        if n % N_TILE or k % K_TILE:
            raise ProductionConnectedLayerCheckError(
                f"projection {projection_id!r} is not exactly tileable"
            )
        projections.append(
            {
                "id": projection_id,
                "input_region": input_region,
                "k": k,
                "k_tile": K_TILE,
                "k_tiles": k // K_TILE,
                "kernel_index": kernel_index,
                "n": n,
                "n_tile": N_TILE,
                "n_tiles": n // N_TILE,
                "output_region": output_region,
                "source_role": source_role,
                "tile_count": n // N_TILE * (k // K_TILE),
            }
        )
    if (
        fixture.get("inputs", {}).get("committed_length") != COMMITTED_LENGTH
        or fixture.get("inputs", {}).get("prepared_length") != PREPARED_LENGTH
        or fixture.get("transaction", {}).get("base_generation") != BASE_GENERATION
        or fixture.get("transaction", {}).get("transaction_id") != TRANSACTION_ID
        or qkv_qualification["input"]["position_id"] != CONTEXT_CAPACITY - 1
        or qkv_qualification["input"]["token_id"]
        != downstream_qualification["input"]["token_id"]
        or qkv_qualification["input"]["embedding_row_payload_sha256"]
        != downstream_qualification["input"]["embedding_row_payload_sha256"]
    ):
        raise ProductionConnectedLayerCheckError(
            "runtime request and state fixture do not connect"
        )
    return {
        "base_generation": BASE_GENERATION,
        "coefficient_row_bytes": 2 * HEAD_DIM * 2,
        "committed_length": COMMITTED_LENGTH,
        "context_capacity": CONTEXT_CAPACITY,
        "fixture_id": FIXTURE_ID,
        "head_dim": HEAD_DIM,
        "hidden_width": HIDDEN_WIDTH,
        "intermediate_width": INTERMEDIATE_WIDTH,
        "key_value_heads": KEY_VALUE_HEADS,
        "prepared_length": PREPARED_LENGTH,
        "projections": projections,
        "qualified_state_resources": 1,
        "query_heads": QUERY_HEADS,
        "resident_embedding_base_token": qkv_qualification["input"]["token_id"],
        "resident_embedding_rows": 1,
        "rope_positions": CONTEXT_CAPACITY,
        "rows": 1,
        "source_atomic_state_count": 36,
        "transaction_id": TRANSACTION_ID,
    }


def _sram(capability: ProductionCapability) -> dict[str, Any]:
    specs = (
        ("runtime_ids", 0, 0, "u32", [2], 8),
        ("hidden_0", 1, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("input_norm_weight", 2, 0, "bf16", [HIDDEN_WIDTH], 8192),
        ("attention_norm", 3, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("weight_tile", 4, 0, "bf16", [N_TILE, K_TILE], 32768),
        ("accumulator_tile", 5, 0, "fp32", [1, N_TILE], 256),
        ("q_raw", 6, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("k_raw", 7, 0, "bf16", [1, 1024], 2048),
        ("v", 8, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], 2048),
        ("q_norm_weight", 9, 0, "bf16", [HEAD_DIM], 256),
        ("k_norm_weight", 10, 0, "bf16", [HEAD_DIM], 256),
        ("q_norm", 11, 0, "bf16", [QUERY_HEADS, HEAD_DIM], 8192),
        ("k_norm", 12, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], 2048),
        ("rope_coefficients", 13, 0, "bf16", [2 * HEAD_DIM], 512),
        ("q_rotary", 14, 0, "bf16", [QUERY_HEADS, HEAD_DIM], 8192),
        ("k_rotary", 15, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], 2048),
        ("attention", 0, 16, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("attention_projected", 2, 8192, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("post_attention", 3, 8192, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("post_attention_norm_weight", 6, 8192, "bf16", [HIDDEN_WIDTH], 8192),
        ("mlp_norm", 7, 2048, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("gate", 8, 2048, "bf16", [1, INTERMEDIATE_WIDTH], 24576),
        ("up", 9, 256, "bf16", [1, INTERMEDIATE_WIDTH], 24576),
        ("gated_mlp", 10, 256, "bf16", [1, INTERMEDIATE_WIDTH], 24576),
        ("down", 11, 8192, "bf16", [1, HIDDEN_WIDTH], 8192),
        ("hidden_1", 12, 2048, "bf16", [1, HIDDEN_WIDTH], 8192),
    )
    regions = []
    intervals: dict[int, list[tuple[int, int, str]]] = {}
    for region_id, bank, offset, dtype, shape, logical in specs:
        allocated = align_up(logical, capability.sram.word_bytes)
        if (
            bank >= capability.sram.banks
            or offset + allocated > capability.sram.bytes_per_bank
        ):
            raise ProductionConnectedLayerCheckError(
                f"SRAM region {region_id!r} exceeds capability"
            )
        for start, end, other in intervals.setdefault(bank, []):
            if offset < end and start < offset + allocated:
                raise ProductionConnectedLayerCheckError(
                    f"SRAM regions {other!r} and {region_id!r} overlap"
                )
        intervals[bank].append((offset, offset + allocated, region_id))
        regions.append(
            {
                "address": capability.sram.bank_base(bank) + offset,
                "allocated_bytes": allocated,
                "bank": bank,
                "dtype": dtype,
                "id": region_id,
                "logical_bytes": logical,
                "offset_bytes": offset,
                "shape": shape,
            }
        )
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _place(
    image: bytearray,
    *,
    capability: ProductionCapability,
    region_id: str,
    payload: bytes,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    offset = align_up(len(image), capability.hbm.burst_bytes)
    image.extend(bytes(offset - len(image)))
    image.extend(payload)
    return {
        "address": capability.hbm.base_address + offset,
        "id": region_id,
        "offset_bytes": offset,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "source": dict(source),
    }


def _place_state(
    image: bytearray,
    *,
    capability: ProductionCapability,
    region_id: str,
    initialized: bytes,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    offset = align_up(len(image), capability.hbm.burst_bytes)
    image.extend(bytes(offset - len(image)))
    payload = initialized + bytes(STATE_REGION_BYTES - len(initialized))
    image.extend(payload)
    return {
        "address": capability.hbm.base_address + offset,
        "allocated_bytes": STATE_REGION_BYTES,
        "id": region_id,
        "initialized_payload_sha256": hashlib.sha256(initialized).hexdigest(),
        "initialized_size_bytes": len(initialized),
        "offset_bytes": offset,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "source": dict(source),
    }


def _place_projection(
    image: bytearray,
    *,
    capability: ProductionCapability,
    definition: Mapping[str, Any],
    payload: bytes,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    weights = np.frombuffer(payload, dtype="<u2").reshape(
        definition["n"], definition["k"]
    )
    tiles = []
    for n_start in range(0, definition["n"], N_TILE):
        for k_start in range(0, definition["k"], K_TILE):
            tile = np.ascontiguousarray(
                weights[n_start : n_start + N_TILE, k_start : k_start + K_TILE],
                dtype="<u2",
            ).tobytes(order="C")
            offset = align_up(len(image), capability.hbm.burst_bytes)
            image.extend(bytes(offset - len(image)))
            image.extend(tile)
            tiles.append(
                {
                    "address": capability.hbm.base_address + offset,
                    "k_count": K_TILE,
                    "k_start": k_start,
                    "n_count": N_TILE,
                    "n_start": n_start,
                    "offset_bytes": offset,
                    "payload_sha256": hashlib.sha256(tile).hexdigest(),
                    "size_bytes": len(tile),
                    "tile_index": len(tiles),
                }
            )
    return {
        "id": definition["id"],
        "input_region": definition["input_region"],
        "kernel_index": definition["kernel_index"],
        "output_region": definition["output_region"],
        "source": dict(source),
        "tiles": tiles,
    }


def _checkpoint_source(qualification: Mapping[str, Any], role: str) -> dict[str, Any]:
    source = qualification["sources"][role]
    return {
        "kind": "checkpoint_tensor",
        "payload_sha256": source["payload_sha256"],
        "shape": source["shape"],
        "tensor_name": source["tensor"],
    }


def _hbm(
    *,
    qkv_payloads: Mapping[str, bytes],
    downstream_payloads: Mapping[str, bytes],
    qkv_qualification: Mapping[str, Any],
    qkv_report: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
    fixture: Mapping[str, Any],
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    if qkv_payloads["embedding"] != downstream_payloads["hidden_0"]:
        raise ProductionConnectedLayerCheckError(
            "independent checkpoint readers disagree on hidden-0"
        )
    _output_codes(qkv_report, "q_rotary")
    k = _output_codes(qkv_report, "k_rotary")
    v = _output_codes(qkv_report, "v")
    history_k = np.stack((np.roll(k, 1, axis=0), k[:, ::-1], np.roll(k, 17, axis=1)))
    history_v = np.stack((np.roll(v, 1, axis=0), v[:, ::-1], np.roll(v, 23, axis=1)))
    history_key = np.ascontiguousarray(history_k, dtype="<u2").tobytes(order="C")
    history_value = np.ascontiguousarray(history_v, dtype="<u2").tobytes(order="C")
    if (
        hashlib.sha256(history_key).hexdigest()
        != fixture["inputs"]["committed_key_payload_sha256"]
        or hashlib.sha256(history_value).hexdigest()
        != fixture["inputs"]["committed_value_payload_sha256"]
    ):
        raise ProductionConnectedLayerCheckError(
            "independently derived initial KV state differs"
        )
    coefficients = coefficient_table_bf16(CONTEXT_CAPACITY)
    coefficient_payload = np.ascontiguousarray(coefficients, dtype="<u2").tobytes(
        order="C"
    )
    if hashlib.sha256(coefficient_payload).hexdigest() != COEFFICIENT_TABLE_SHA256:
        raise ProductionConnectedLayerCheckError(
            "independent RoPE coefficient table differs"
        )

    definitions = {item["id"]: item for item in problem["projections"]}
    image = bytearray()
    regions = [
        _place(
            image,
            capability=capability,
            region_id="embedding_rows",
            payload=qkv_payloads["embedding"],
            source={
                "kind": "checkpoint_row",
                "payload_sha256": qkv_qualification["input"][
                    "embedding_row_payload_sha256"
                ],
                "row": qkv_qualification["input"]["token_id"],
                "tensor_name": qkv_qualification["sources"]["embedding"]["tensor"],
                "tensor_payload_sha256": qkv_qualification["sources"]["embedding"][
                    "payload_sha256"
                ],
            },
        ),
        _place(
            image,
            capability=capability,
            region_id="input_norm_weight",
            payload=qkv_payloads["input_norm_weight"],
            source=_checkpoint_source(qkv_qualification, "input_norm_weight"),
        ),
    ]
    projections = []
    for projection_id, _, _, _, role in PROJECTION_SPECS[:3]:
        projections.append(
            _place_projection(
                image,
                capability=capability,
                definition=definitions[projection_id],
                payload=qkv_payloads[role],
                source=_checkpoint_source(qkv_qualification, role),
            )
        )
    for role in ("q_norm_weight", "k_norm_weight"):
        regions.append(
            _place(
                image,
                capability=capability,
                region_id=role,
                payload=qkv_payloads[role],
                source=_checkpoint_source(qkv_qualification, role),
            )
        )
    regions.append(
        _place(
            image,
            capability=capability,
            region_id="rope_coefficient_table",
            payload=coefficient_payload,
            source={
                "kind": "derived_constant",
                "numeric_contract": ROPE_CONTRACT,
                "payload_sha256": COEFFICIENT_TABLE_SHA256,
                "positions": CONTEXT_CAPACITY,
            },
        )
    )
    state_source = {
        "fixture_id": FIXTURE_ID,
        "kind": "qualified_runtime_initial_state",
        "qkv_execution_report_id": qkv_report["report_id"],
        "transform": fixture["inputs"]["transform"],
    }
    key_state = _place_state(
        image,
        capability=capability,
        region_id="key_state",
        initialized=history_key,
        source=state_source,
    )
    value_state = _place_state(
        image,
        capability=capability,
        region_id="value_state",
        initialized=history_value,
        source=state_source,
    )
    regions.extend((key_state, value_state))
    metadata_payload = STATE_METADATA.pack(
        STATE_MAGIC,
        BASE_GENERATION,
        COMMITTED_LENGTH,
        CONTEXT_CAPACITY,
        key_state["address"],
        value_state["address"],
        0,
        bytes(8),
    )
    metadata = _place(
        image,
        capability=capability,
        region_id="state_metadata",
        payload=metadata_payload,
        source={
            "fixture_id": FIXTURE_ID,
            "kind": "runtime_initial_state_metadata",
            "resource_id": RESOURCE_ID,
        },
    )
    regions.append(metadata)
    regions.append(
        _place(
            image,
            capability=capability,
            region_id="transaction_descriptor",
            payload=TRANSACTION_DESCRIPTOR.pack(
                TRANSACTION_MAGIC,
                TRANSACTION_ID,
                BASE_GENERATION,
                COMMITTED_LENGTH,
                PREPARED_LENGTH,
                1,
                metadata["address"],
                bytes(8),
            ),
            source={
                "fixture_id": FIXTURE_ID,
                "kind": "runtime_transaction_descriptor",
                "transaction_id": TRANSACTION_ID,
            },
        )
    )
    regions.append(
        _place(
            image,
            capability=capability,
            region_id="post_attention_norm_weight",
            payload=downstream_payloads["post_attention_norm_weight"],
            source=_checkpoint_source(
                downstream_qualification, "post_attention_norm_weight"
            ),
        )
    )
    for projection_id, _, _, _, role in PROJECTION_SPECS[3:]:
        projections.append(
            _place_projection(
                image,
                capability=capability,
                definition=definitions[projection_id],
                payload=downstream_payloads[role],
                source=_checkpoint_source(downstream_qualification, role),
            )
        )
    padded = align_up(len(image), capability.hbm.burst_bytes)
    image.extend(bytes(padded - len(image)))
    payload = bytes(image)
    return payload, {
        "image": {
            "base_address": capability.hbm.base_address,
            "path": HBM_IMAGE_PATH,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "projections": projections,
        "regions": regions,
    }


def _by_id(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {str(record["id"]): record for record in records}
    if len(result) != len(records):
        raise ProductionConnectedLayerCheckError("physical record IDs alias")
    return result


def _projection_commands(
    commands: list[ProductionCommand],
    *,
    projection: Mapping[str, Any],
    local: Mapping[str, Mapping[str, Any]],
) -> None:
    for tile in projection["tiles"]:
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=projection["kernel_index"],
                source0=tile["address"],
                destination=local["weight_tile"]["address"],
                size0=tile["size_bytes"],
            )
        )
        flags = 0
        if tile["k_start"] == 0:
            flags |= MATMUL_INIT
        if tile["k_start"] + tile["k_count"] == projection["source"]["shape"][1]:
            flags |= MATMUL_FINAL
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.MATMUL_BF16_TILE,
                Engine.TENSOR,
                flags=flags,
                kernel_index=projection["kernel_index"],
                source0=local[projection["input_region"]]["address"]
                + tile["k_start"] * 2,
                source1=local["weight_tile"]["address"],
                destination=local["accumulator_tile"]["address"],
                auxiliary=local[projection["output_region"]]["address"]
                + tile["n_start"] * 2,
                size0=1,
                size1=tile["n_count"],
                size2=tile["k_count"],
            )
        )


def _commands(
    *,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    problem: Mapping[str, Any],
) -> tuple[ProductionCommand, ...]:
    local = _by_id(sram["regions"])
    remote = _by_id(hbm["regions"])
    projections = _by_id(hbm["projections"])
    commands = [
        ProductionCommand(
            0,
            Opcode.DMA_HBM_INDEXED_TO_SRAM,
            Engine.DMA,
            kernel_index=0,
            source0=remote["embedding_rows"]["address"],
            source1=local["runtime_ids"]["address"],
            destination=local["hidden_0"]["address"],
            auxiliary=problem["resident_embedding_base_token"],
            size0=HIDDEN_WIDTH * 2,
            size1=HIDDEN_WIDTH * 2,
            size2=problem["resident_embedding_rows"],
            size3=4,
        ),
        ProductionCommand(
            1,
            Opcode.DMA_HBM_TO_SRAM,
            Engine.DMA,
            kernel_index=1,
            source0=remote["input_norm_weight"]["address"],
            destination=local["input_norm_weight"]["address"],
            size0=HIDDEN_WIDTH * 2,
        ),
        ProductionCommand(
            2,
            Opcode.RMSNORM_BF16,
            Engine.VECTOR,
            kernel_index=1,
            source0=local["hidden_0"]["address"],
            source1=local["input_norm_weight"]["address"],
            destination=local["attention_norm"]["address"],
            size0=1,
            size1=HIDDEN_WIDTH,
            size2=EPSILON_CODE,
        ),
    ]
    for role in ("q", "k", "v"):
        _projection_commands(commands, projection=projections[role], local=local)
    for kernel_index, role in ((5, "q"), (6, "k")):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=kernel_index,
                source0=remote[f"{role}_norm_weight"]["address"],
                destination=local[f"{role}_norm_weight"]["address"],
                size0=HEAD_DIM * 2,
            )
        )
    for kernel_index, role, rows in ((5, "q", QUERY_HEADS), (6, "k", KEY_VALUE_HEADS)):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.RMSNORM_BF16,
                Engine.VECTOR,
                kernel_index=kernel_index,
                source0=local[f"{role}_raw"]["address"],
                source1=local[f"{role}_norm_weight"]["address"],
                destination=local[f"{role}_norm"]["address"],
                size0=rows,
                size1=HEAD_DIM,
                size2=EPSILON_CODE,
            )
        )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.DMA_HBM_INDEXED_TO_SRAM,
            Engine.DMA,
            kernel_index=7,
            source0=remote["rope_coefficient_table"]["address"],
            source1=local["runtime_ids"]["address"] + 4,
            destination=local["rope_coefficients"]["address"],
            size0=2 * HEAD_DIM * 2,
            size1=2 * HEAD_DIM * 2,
            size2=CONTEXT_CAPACITY,
            size3=4,
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.ROPE_BF16,
            Engine.VECTOR,
            kernel_index=7,
            source0=local["q_norm"]["address"],
            source1=local["k_norm"]["address"],
            destination=local["q_rotary"]["address"],
            auxiliary=local["k_rotary"]["address"],
            size0=QUERY_HEADS,
            size1=KEY_VALUE_HEADS,
            size2=HEAD_DIM,
            size3=local["rope_coefficients"]["address"],
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.KV_PREPARE_BF16,
            Engine.STATE,
            kernel_index=8,
            source0=local["k_rotary"]["address"],
            source1=local["v"]["address"],
            destination=remote["key_state"]["address"],
            auxiliary=remote["value_state"]["address"],
            size0=PREPARED_LENGTH,
            size1=KEY_VALUE_HEADS,
            size2=HEAD_DIM,
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.GQA_ATTENTION_BF16,
            Engine.VECTOR,
            kernel_index=9,
            source0=local["q_rotary"]["address"],
            source1=remote["key_state"]["address"],
            destination=local["attention"]["address"],
            auxiliary=remote["value_state"]["address"],
            size0=PREPARED_LENGTH,
            size1=QUERY_HEADS,
            size2=KEY_VALUE_HEADS,
            size3=HEAD_DIM,
        )
    )
    _projection_commands(
        commands, projection=projections["attention_output"], local=local
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.ADD_BF16,
            Engine.VECTOR,
            kernel_index=11,
            source0=local["hidden_0"]["address"],
            source1=local["attention_projected"]["address"],
            destination=local["post_attention"]["address"],
            size0=1,
            size1=HIDDEN_WIDTH,
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.DMA_HBM_TO_SRAM,
            Engine.DMA,
            kernel_index=12,
            source0=remote["post_attention_norm_weight"]["address"],
            destination=local["post_attention_norm_weight"]["address"],
            size0=HIDDEN_WIDTH * 2,
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.RMSNORM_BF16,
            Engine.VECTOR,
            kernel_index=12,
            source0=local["post_attention"]["address"],
            source1=local["post_attention_norm_weight"]["address"],
            destination=local["mlp_norm"]["address"],
            size0=1,
            size1=HIDDEN_WIDTH,
            size2=EPSILON_CODE,
        )
    )
    for role in ("gate", "up"):
        _projection_commands(commands, projection=projections[role], local=local)
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.SILU_MUL_BF16,
            Engine.VECTOR,
            kernel_index=15,
            source0=local["gate"]["address"],
            source1=local["up"]["address"],
            destination=local["gated_mlp"]["address"],
            size0=1,
            size1=INTERMEDIATE_WIDTH,
        )
    )
    _projection_commands(commands, projection=projections["down"], local=local)
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.ADD_BF16,
            Engine.VECTOR,
            kernel_index=17,
            source0=local["post_attention"]["address"],
            source1=local["down"]["address"],
            destination=local["hidden_1"]["address"],
            size0=1,
            size1=HIDDEN_WIDTH,
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.STATE_COMMIT,
            Engine.STATE,
            kernel_index=NO_KERNEL,
            source0=remote["state_metadata"]["address"],
            source1=remote["transaction_descriptor"]["address"],
            size0=CONTEXT_CAPACITY,
            size1=1,
        )
    )
    commands.append(ProductionCommand(len(commands), Opcode.COMPLETE, Engine.CONTROL))
    if len(commands) != 23570:
        raise ProductionConnectedLayerCheckError(
            "independently reconstructed command count differs"
        )
    return tuple(commands)


def _counters(problem: Mapping[str, Any], fixture: Mapping[str, Any]) -> dict[str, int]:
    qkv_problem = {
        "coefficient_row_bytes": problem["coefficient_row_bytes"],
        "context_positions": problem["rope_positions"],
        "head_dim": HEAD_DIM,
        "hidden_width": HIDDEN_WIDTH,
        "key_value_heads": KEY_VALUE_HEADS,
        "projections": [
            {
                **{
                    key: projection[key]
                    for key in (
                        "k",
                        "k_tile",
                        "k_tiles",
                        "n",
                        "n_tile",
                        "n_tiles",
                        "tile_count",
                    )
                },
                "role": projection["id"],
            }
            for projection in problem["projections"][:3]
        ],
        "query_heads": QUERY_HEADS,
        "resident_embedding_base_token": problem["resident_embedding_base_token"],
        "resident_embedding_rows": 1,
    }
    downstream_problem = {
        "hidden_width": HIDDEN_WIDTH,
        "intermediate_width": INTERMEDIATE_WIDTH,
        "projections": problem["projections"][3:],
        "rows": 1,
    }
    try:
        groups = (
            qkv_counters(qkv_problem),
            attention_counters(fixture),
            downstream_counters(downstream_problem),
        )
    except (ArtifactError, ValueError, KeyError) as exc:
        raise ProductionConnectedLayerCheckError(
            f"independent counter derivation failed: {exc}"
        ) from exc
    names = sorted({name for group in groups for name in group})
    result = {name: sum(group.get(name, 0) for group in groups) for name in names}
    removed = QUERY_BYTES + 2 * TOKEN_BYTES + 2 * HIDDEN_WIDTH * 2
    result.update(
        {
            "command_count": 23570,
            "complete_command_count": 1,
            "direct_dma_command_count": 11780,
            "dma_command_count": 11782,
            "dma_sram_bytes_written": result["dma_sram_bytes_written"] - removed,
            "hbm_transferred_bytes_read": result["hbm_transferred_bytes_read"]
            - removed,
            "hbm_useful_bytes_read": result["hbm_useful_bytes_read"] - removed,
        }
    )
    if (
        len(result) != 72
        or result["matmul_command_count"] != 11776
        or result["dma_sram_bytes_written"] != 385901568
        or result["hbm_useful_bytes_read"] != 385918208
        or result["state_commit_command_count"] != 1
    ):
        raise ProductionConnectedLayerCheckError(
            "independent connected counter identities differ"
        )
    return result


def _rms_kernel(
    index: int, operation: ProductionOperation, rows: int, width: int
) -> dict[str, Any]:
    return {
        "attributes": {
            "epsilon_binary32_code": EPSILON_CODE,
            "final_weight_product": "bf16_multiply_then_bf16_rne",
            "normalized_boundary": "bf16_rne_before_weight",
            "reduction_order": "canonical_balanced_binary32_tree",
            "rsqrt": "correctly_rounded_binary32_rne",
        },
        "index": index,
        "inputs": list(operation.inputs),
        "kind": "RMS_NORM",
        "numeric_contract": RMSNORM_CONTRACT,
        "outputs": list(operation.outputs),
        "shape": {"rows": rows, "width": width},
        "source_operation_id": operation.operation_id,
    }


def _matmul_kernel(
    index: int, operation: ProductionOperation, width: int, reduction_width: int
) -> dict[str, Any]:
    return {
        "attributes": {
            "accumulator_dtype": "fp32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "reduction_order": "strictly_increasing_k",
            "transpose_weight": True,
        },
        "index": index,
        "inputs": list(operation.inputs),
        "kind": "MATMUL",
        "numeric_contract": MATRIX_CONTRACT,
        "outputs": list(operation.outputs),
        "shape": {"reduction_width": reduction_width, "rows": 1, "width": width},
        "source_operation_id": operation.operation_id,
    }


def _add_kernel(index: int, operation: ProductionOperation) -> dict[str, Any]:
    return {
        "attributes": {
            "addition": "binary32_rne",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "zero_canonicalization": "positive",
        },
        "index": index,
        "inputs": list(operation.inputs),
        "kind": "ADD",
        "numeric_contract": ADD_CONTRACT,
        "outputs": list(operation.outputs),
        "shape": {"rows": 1, "width": HIDDEN_WIDTH},
        "source_operation_id": operation.operation_id,
    }


def _kernel_ir(
    *,
    model: ProductionModelGraph,
    operations: tuple[ProductionOperation, ...],
    qkv_qualification: Mapping[str, Any],
    bundle_id: str,
) -> dict[str, Any]:
    kernels: list[dict[str, Any]] = [
        {
            "attributes": {
                "index_dtype": "u32",
                "output_dtype": "bf16",
                "source_index_max_exclusive": qkv_qualification["sources"]["embedding"][
                    "shape"
                ][0],
                "source_index_min": 0,
            },
            "index": 0,
            "inputs": list(operations[0].inputs),
            "kind": "EMBEDDING_LOOKUP",
            "numeric_contract": LOOKUP_CONTRACT,
            "outputs": list(operations[0].outputs),
            "shape": {"rows": 1, "width": HIDDEN_WIDTH},
            "source_operation_id": operations[0].operation_id,
        },
        _rms_kernel(1, operations[1], 1, HIDDEN_WIDTH),
        _matmul_kernel(2, operations[2], HIDDEN_WIDTH, HIDDEN_WIDTH),
        _matmul_kernel(3, operations[3], KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH),
        _matmul_kernel(4, operations[4], KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH),
        _rms_kernel(5, operations[5], QUERY_HEADS, HEAD_DIM),
        _rms_kernel(6, operations[6], KEY_VALUE_HEADS, HEAD_DIM),
        {
            "attributes": {
                "coefficient_layout": "cos_head_dim_then_sin_head_dim",
                "key_value_heads": KEY_VALUE_HEADS,
                "max_positions": CONTEXT_CAPACITY,
                "position_symbol": "position_start",
                "query_heads": QUERY_HEADS,
                "rotation": "concat_neg_second_half_first_half",
            },
            "index": 7,
            "inputs": list(operations[7].inputs),
            "kind": "ROPE",
            "numeric_contract": ROPE_CONTRACT,
            "outputs": list(operations[7].outputs),
            "shape": {"head_dim": HEAD_DIM},
            "source_operation_id": operations[7].operation_id,
        },
        {
            "attributes": {
                "append_position_symbol": "position_start",
                "generation_check": "exact_expected_generation",
                "state_resource": RESOURCE_ID,
                "transaction_scope": "model_forward_request",
                "visibility": "transaction_private_until_commit",
            },
            "index": 8,
            "inputs": list(operations[8].inputs),
            "kind": "KV_PREPARE",
            "numeric_contract": STATE_CONTRACT,
            "outputs": list(operations[8].outputs),
            "shape": {
                "head_dim": HEAD_DIM,
                "key_value_heads": KEY_VALUE_HEADS,
                "max_context_tokens": CONTEXT_CAPACITY,
                "tokens_symbol": "span_tokens",
            },
            "source_operation_id": operations[8].operation_id,
        },
        {
            "attributes": {
                "causal_mask_bf16_code": 0xFF7F,
                "prepared_state_visibility": "transaction_private",
                "probability_dtype": "bf16",
                "query_heads_per_key_value_head": 4,
                "scale_bf16_code": 0x3DB5,
                "score_reduction_order": "strictly_increasing_head_dimension",
                "softmax_compute_dtype": "fp32",
                "softmax_reduction_lanes": 8,
                "value_reduction_order": "strictly_increasing_context",
            },
            "index": 9,
            "inputs": list(operations[9].inputs),
            "kind": "ATTENTION",
            "numeric_contract": ATTENTION_CONTRACT,
            "outputs": list(operations[9].outputs),
            "shape": {
                "head_dim": HEAD_DIM,
                "key_value_heads": KEY_VALUE_HEADS,
                "max_context_tokens": CONTEXT_CAPACITY,
                "query_heads": QUERY_HEADS,
                "query_tokens_symbol": "span_tokens",
            },
            "source_operation_id": operations[9].operation_id,
        },
        _matmul_kernel(10, operations[10], HIDDEN_WIDTH, HIDDEN_WIDTH),
        _add_kernel(11, operations[11]),
        _rms_kernel(12, operations[12], 1, HIDDEN_WIDTH),
        _matmul_kernel(13, operations[13], INTERMEDIATE_WIDTH, HIDDEN_WIDTH),
        _matmul_kernel(14, operations[14], INTERMEDIATE_WIDTH, HIDDEN_WIDTH),
        {
            "attributes": {
                "activation_boundary": "bf16_rne_before_up_multiply",
                "exponential": "correctly_rounded_binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "sigmoid": "stable_sign_selected_binary32",
                "zero_canonicalization": "positive",
            },
            "index": 15,
            "inputs": list(operations[15].inputs),
            "kind": "SILU_MUL",
            "numeric_contract": SILU_CONTRACT,
            "outputs": list(operations[15].outputs),
            "shape": {"rows": 1, "width": INTERMEDIATE_WIDTH},
            "source_operation_id": operations[15].operation_id,
        },
        _matmul_kernel(16, operations[16], HIDDEN_WIDTH, INTERMEDIATE_WIDTH),
        _add_kernel(17, operations[17]),
        {
            "attributes": {
                "atomic": True,
                "coverage": "qualified_resource_subset",
                "generation_increment": 1,
                "source_atomic_state_count": 36,
                "transaction_scope": "model_forward_request",
            },
            "index": 18,
            "inputs": ["hidden.1"],
            "kind": "STATE_COMMIT",
            "numeric_contract": STATE_CONTRACT,
            "outputs": ["hidden.1.committed"],
            "shape": {"atomic_state_count": 1},
            "source_operation_id": operations[18].operation_id,
            "state_resources": [RESOURCE_ID],
        },
    ]
    body = {
        "graph_id": model.graph_id,
        "kernels": kernels,
        "qualification_report_id": bundle_id,
        "schema": KERNEL_SCHEMA,
    }
    return _identified(body, "kernel_ir_id")


def _source_lock(
    *,
    model: ProductionModelGraph,
    checkpoint_lock: Mapping[str, Any],
    capability: ProductionCapability,
    bundle: Mapping[str, str],
    source_paths: Mapping[str, Path],
) -> dict[str, Any]:
    internal = {
        "attention_execution": "source/attention_execution.json",
        "attention_qualification": "source/attention_qualification.json",
        "checkpoint_lock": "source/checkpoint.lock.json",
        "downstream_execution": "source/downstream_execution.json",
        "downstream_qualification": "source/downstream_qualification.json",
        "model_graph": "source/model_graph.v2.json",
        "qkv_execution": "source/qkv_execution.json",
        "qkv_qualification": "source/qkv_qualification.json",
    }
    artifacts = {}
    for role in sorted(internal):
        digest, size = sha256_file(source_paths[role])
        artifacts[role] = {
            "path": internal[role],
            "sha256": digest,
            "size_bytes": size,
        }
    body = {
        "artifacts": artifacts,
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": checkpoint_lock["lock_id"],
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "qualification_bundle": dict(bundle),
        "schema": SOURCE_LOCK_SCHEMA,
    }
    return _identified(body, "source_lock_id")


def _request(
    *, model: ProductionModelGraph, operation_ids: Sequence[str], bundle_id: str
) -> dict[str, Any]:
    body = {
        "expected_generation": BASE_GENERATION,
        "graph_id": model.graph_id,
        "position_id": CONTEXT_CAPACITY - 1,
        "qualification_bundle_id": bundle_id,
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": list(operation_ids),
        "span_tokens": PREPARED_LENGTH,
        "state_position_start": COMMITTED_LENGTH,
        "token_id": 0,
        "transaction_id": TRANSACTION_ID,
    }
    return _identified(body, "request_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    operation_ids: Sequence[str],
    bundle_id: str,
    problem: Mapping[str, Any],
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    counters: Mapping[str, int],
    command_payload: bytes,
) -> dict[str, Any]:
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": dict(counters),
        "graph_id": model.graph_id,
        "hbm": dict(hbm),
        "numeric_contracts": NUMERIC_CONTRACTS,
        "problem": dict(problem),
        "program": {
            "command_count": 23570,
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "qualification_bundle_id": bundle_id,
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_ids": list(operation_ids),
        "sram": dict(sram),
    }
    return _identified(body, "physical_plan_id")


def _expectations(
    *,
    qkv_qualification: Mapping[str, Any],
    qkv_report: Mapping[str, Any],
    attention_report: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
    downstream_report: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, str], dict[str, Any], str]:
    intermediates = {
        "hidden_0": qkv_qualification["input"]["embedding_row_payload_sha256"],
        **{
            role: record["payload_sha256"]
            for role, record in qkv_report["intermediates"].items()
        },
        **{
            role: qkv_report["outputs"][role]["payload_sha256"]
            for role in ("k_rotary", "q_rotary", "v")
        },
        **{
            role: attention_report["outputs"][role]["payload_sha256"]
            for role in ("attention", "probabilities", "scaled_scores")
        },
        **{
            role: record["payload_sha256"]
            for role, record in downstream_qualification["intermediates"].items()
        },
    }
    if len(intermediates) != 20:
        raise ProductionConnectedLayerCheckError(
            "connected intermediate expectation coverage differs"
        )
    output = {
        "hidden_1": downstream_qualification["output"]["hidden_1"]["payload_sha256"]
    }
    saturation = {
        "attention": dict(attention_report["saturation"]),
        "projection": {
            **dict(qkv_report["projection_saturated_element_count"]),
            **dict(downstream_report["saturated_element_count"]["projection"]),
        },
        "rmsnorm": {
            role: {
                "normalized": record["normalized_saturated_element_count"],
                "output": record["output_saturated_element_count"],
            }
            for role, record in qkv_report["rmsnorm"].items()
        }
        | {"mlp_norm": dict(downstream_report["saturated_element_count"]["rmsnorm"])},
        "rope": {
            "addition": qkv_report["rope"]["addition_saturated_element_count"],
            "multiplication": qkv_report["rope"][
                "multiplication_saturated_element_count"
            ],
        },
        "vector": dict(downstream_report["saturated_element_count"]["vector"]),
    }
    state_hash = attention_report["state"]["state_sha256"]
    return intermediates, output, saturation, state_hash


def check_connected_layer_candidate(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qkv_qualification_path: Path,
    qkv_execution_path: Path,
    attention_qualification_path: Path,
    attention_execution_path: Path,
    downstream_qualification_path: Path,
    downstream_execution_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct and validate one connected-layer candidate."""

    root = Path(root).resolve()
    snapshot = Path(snapshot).resolve()
    source_paths = {
        "attention_execution": Path(attention_execution_path).resolve(),
        "attention_qualification": Path(attention_qualification_path).resolve(),
        "checkpoint_lock": Path(checkpoint_lock_path).resolve(),
        "downstream_execution": Path(downstream_execution_path).resolve(),
        "downstream_qualification": Path(downstream_qualification_path).resolve(),
        "model_graph": Path(model_graph_path).resolve(),
        "qkv_execution": Path(qkv_execution_path).resolve(),
        "qkv_qualification": Path(qkv_qualification_path).resolve(),
    }
    capability_path = Path(capability_path).resolve()
    try:
        checkpoint_lock = load_checkpoint_lock(source_paths["checkpoint_lock"])
        model = load_production_model_graph(source_paths["model_graph"])
        capability = load_production_capability(capability_path)
        qkv_qualification = load_qkv_qualification(source_paths["qkv_qualification"])
        attention_qualification = load_attention_qualification(
            source_paths["attention_qualification"]
        )
        downstream_qualification = load_layer_qualification(
            source_paths["downstream_qualification"]
        )
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        QKVQualificationError,
        AttentionQualificationError,
        LayerQualificationError,
    ) as exc:
        raise ProductionConnectedLayerCheckError(
            f"external source admission failed: {exc}"
        ) from exc
    qkv_report, qkv_payload = _passing_report(
        source_paths["qkv_execution"], "Q/K/V execution", QKV_EXECUTION_SCHEMA
    )
    attention_report, attention_payload = _passing_report(
        source_paths["attention_execution"],
        "attention execution",
        ATTENTION_EXECUTION_SCHEMA,
    )
    downstream_report, _ = _passing_report(
        source_paths["downstream_execution"],
        "downstream execution",
        DOWNSTREAM_EXECUTION_SCHEMA,
    )
    if (
        qkv_qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]
        or downstream_qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]
    ):
        raise ProductionConnectedLayerCheckError(
            "qualification checkpoint locks differ"
        )
    for role, path in source_paths.items():
        expected_internal = {
            "attention_execution": "source/attention_execution.json",
            "attention_qualification": "source/attention_qualification.json",
            "checkpoint_lock": "source/checkpoint.lock.json",
            "downstream_execution": "source/downstream_execution.json",
            "downstream_qualification": "source/downstream_qualification.json",
            "model_graph": "source/model_graph.v2.json",
            "qkv_execution": "source/qkv_execution.json",
            "qkv_qualification": "source/qkv_qualification.json",
        }[role]
        _external_copy(root, expected_internal, path, role.replace("_", " "))
    candidate_capability, _ = _load_canonical(
        root / "capability.json", "candidate capability"
    )
    if candidate_capability != capability.to_dict():
        raise ProductionConnectedLayerCheckError(
            "candidate capability differs from external capability"
        )
    bundle, fixture = _bundle(
        qkv_qualification=qkv_qualification,
        qkv_report=qkv_report,
        qkv_payload=qkv_payload,
        attention_qualification=attention_qualification,
        attention_report=attention_report,
        attention_payload=attention_payload,
        downstream_qualification=downstream_qualification,
        downstream_report=downstream_report,
    )
    operations = _operations(
        model,
        lock_id=checkpoint_lock["lock_id"],
        qkv_qualification=qkv_qualification,
        downstream_qualification=downstream_qualification,
    )
    operation_ids = tuple(operation.operation_id for operation in operations)
    problem = _problem(
        qkv_qualification=qkv_qualification,
        downstream_qualification=downstream_qualification,
        fixture=fixture,
        capability=capability,
    )
    try:
        qkv_payloads = read_qkv_payloads(snapshot, checkpoint_lock, qkv_qualification)
        downstream_payloads = read_downstream_payloads(
            snapshot, checkpoint_lock, downstream_qualification
        )
    except (ProductionQKVCheckError, ProductionLayerDownstreamCheckError) as exc:
        raise ProductionConnectedLayerCheckError(
            f"independent checkpoint reconstruction failed: {exc}"
        ) from exc
    image, hbm = _hbm(
        qkv_payloads=qkv_payloads,
        downstream_payloads=downstream_payloads,
        qkv_qualification=qkv_qualification,
        qkv_report=qkv_report,
        downstream_qualification=downstream_qualification,
        fixture=fixture,
        problem=problem,
        capability=capability,
    )
    try:
        candidate_image = (root / HBM_IMAGE_PATH).read_bytes()
    except OSError as exc:
        raise ProductionConnectedLayerCheckError(
            f"cannot read candidate HBM image: {exc}"
        ) from exc
    if candidate_image != image:
        raise ProductionConnectedLayerCheckError(
            "candidate HBM image differs from independent reconstruction"
        )
    sram = _sram(capability)
    commands = _commands(hbm=hbm, sram=sram, problem=problem)
    try:
        command_payload = (root / COMMAND_PATH).read_bytes()
        decoded = decode(command_payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionConnectedLayerCheckError(
            f"candidate command program is invalid: {exc}"
        ) from exc
    if (
        command_abi(command_payload) != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
        or decoded != commands
    ):
        raise ProductionConnectedLayerCheckError(
            "candidate commands differ from independent schedule"
        )
    expected_disassembly = disassemble(commands, abi_minor=ELEMENTWISE_ABI_MINOR)
    try:
        observed_disassembly = (root / "program/commands.disasm").read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        raise ProductionConnectedLayerCheckError(
            f"cannot read command disassembly: {exc}"
        ) from exc
    if observed_disassembly != expected_disassembly:
        raise ProductionConnectedLayerCheckError(
            "command disassembly differs from independent schedule"
        )
    counters = _counters(problem, fixture)
    kernel_ir = _kernel_ir(
        model=model,
        operations=operations,
        qkv_qualification=qkv_qualification,
        bundle_id=bundle["qualification_bundle_id"],
    )
    candidate_kernel, _ = _load_canonical(
        root / "ir/tensor_kernel_ir.json", "candidate Tensor Kernel IR"
    )
    _identity(candidate_kernel, "kernel_ir_id", "candidate Tensor Kernel IR")
    if candidate_kernel != kernel_ir:
        raise ProductionConnectedLayerCheckError(
            "candidate neutral Kernel IR differs from independent lowering"
        )
    source_lock = _source_lock(
        model=model,
        checkpoint_lock=checkpoint_lock,
        capability=capability,
        bundle=bundle,
        source_paths=source_paths,
    )
    candidate_source_lock, _ = _load_canonical(
        root / "source.lock.json", "candidate source lock"
    )
    _identity(candidate_source_lock, "source_lock_id", "candidate source lock")
    if candidate_source_lock != source_lock:
        raise ProductionConnectedLayerCheckError(
            "candidate source lock differs from independent reconstruction"
        )
    request = _request(
        model=model,
        operation_ids=operation_ids,
        bundle_id=bundle["qualification_bundle_id"],
    )
    candidate_request, _ = _load_canonical(
        root / REQUEST_PATH, "candidate execution request"
    )
    _identity(candidate_request, "request_id", "candidate execution request")
    if candidate_request != request:
        raise ProductionConnectedLayerCheckError(
            "candidate request differs from independent reconstruction"
        )
    plan = _physical_plan(
        model=model,
        capability=capability,
        operation_ids=operation_ids,
        bundle_id=bundle["qualification_bundle_id"],
        problem=problem,
        hbm=hbm,
        sram=sram,
        counters=counters,
        command_payload=command_payload,
    )
    candidate_plan, _ = _load_canonical(
        root / PHYSICAL_PLAN_PATH, "candidate physical plan"
    )
    _identity(candidate_plan, "physical_plan_id", "candidate physical plan")
    if candidate_plan != plan:
        raise ProductionConnectedLayerCheckError(
            "candidate physical plan differs from independent reconstruction"
        )
    intermediates, outputs, saturation, state_hash = _expectations(
        qkv_qualification=qkv_qualification,
        qkv_report=qkv_report,
        attention_report=attention_report,
        downstream_qualification=downstream_qualification,
        downstream_report=downstream_report,
    )
    body = {
        "capability_id": capability.capability_id,
        "command_count": len(commands),
        "command_program_sha256": hashlib.sha256(command_payload).hexdigest(),
        "expected_counters": counters,
        "expected_intermediate_payload_sha256": intermediates,
        "expected_output_payload_sha256": outputs,
        "expected_saturated_element_count": saturation,
        "expected_state_sha256": state_hash,
        "graph_id": model.graph_id,
        "hbm_image_sha256": hashlib.sha256(image).hexdigest(),
        "kernel_ir_id": kernel_ir["kernel_ir_id"],
        "no_retained_activation_regions": True,
        "physical_plan_id": plan["physical_plan_id"],
        "qualification_bundle_id": bundle["qualification_bundle_id"],
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock["source_lock_id"],
        "status": "pass",
    }
    return _identified(body, "check_id")


__all__ = [
    "CHECK_SCHEMA",
    "ProductionConnectedLayerCheckError",
    "check_connected_layer_candidate",
]
