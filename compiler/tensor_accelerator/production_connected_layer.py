"""Deterministic compiler for one command-connected authentic Qwen layer.

The deployment begins at a runtime token/position pair and ends at ``hidden.1``.
Q/K/V preparation, transactional attention, output projection, and the MLP are
one neutral-kernel graph and one causal ABI 2.4 command program.  Retained slice
reports are admitted only as qualification evidence and initial-state-fixture
provenance; no retained activation is present in the deployed HBM image.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.frontend.checkpoint import CheckpointError, load_checkpoint_lock
from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE
from runtime.tensor_accelerator.rope import coefficient_table_bf16

from . import production_attention as attention_stage
from . import production_layer_downstream as downstream_stage
from . import production_qkv as qkv_stage
from .attention_qualification import (
    AttentionQualificationError,
    load_attention_qualification,
)
from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from .layer_qualification import LayerQualificationError, load_layer_qualification
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
    disassemble,
    encode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)
from .qkv_qualification import QKVQualificationError, load_qkv_qualification


COMPILER_VERSION = "tensor-accelerator-production-connected-layer-0.1.0"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.connected_layer_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.connected_layer_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.connected_layer_source_lock.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.connected_layer_expectations.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.connected_layer_deployment.v1"

HBM_IMAGE_PATH = "memory/hbm_connected_layer.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"

QKV_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qkv_execution.v1"
ATTENTION_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.attention_execution.v1"
DOWNSTREAM_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.layer_downstream_execution.v1"
)

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

CLAIM_BOUNDARY = [
    "one actual Qwen3-8B layer-0 token from embedding lookup through hidden.1",
    "one neutral 19-kernel graph, one HBM image, one SRAM plan, and one ABI 2.4 program",
    "Q/K/V, transactional KV prepare, GQA attention, output projection, residuals, RMSNorm, and MLP connected only by architectural state",
    "uncharacterized one-layer evidence only; not full-model decoding, timing, RTL, 130-nm, performance, energy, or ROM-comparison evidence",
]

DIRECT_SOURCE_ROLES = (
    "embedding",
    "input_norm_weight",
    "q_norm_weight",
    "k_norm_weight",
    "post_attention_norm_weight",
)

PROJECTION_DEFINITIONS = (
    {
        "id": "q",
        "input_region": "attention_norm",
        "kernel_index": 2,
        "output_region": "q_raw",
        "source_role": "q_projection_weight",
    },
    {
        "id": "k",
        "input_region": "attention_norm",
        "kernel_index": 3,
        "output_region": "k_raw",
        "source_role": "k_projection_weight",
    },
    {
        "id": "v",
        "input_region": "attention_norm",
        "kernel_index": 4,
        "output_region": "v",
        "source_role": "v_projection_weight",
    },
    {
        "id": "attention_output",
        "input_region": "attention",
        "kernel_index": 10,
        "output_region": "attention_projected",
        "source_role": "attention_output_weight",
    },
    {
        "id": "gate",
        "input_region": "mlp_norm",
        "kernel_index": 13,
        "output_region": "gate",
        "source_role": "gate_projection_weight",
    },
    {
        "id": "up",
        "input_region": "mlp_norm",
        "kernel_index": 14,
        "output_region": "up",
        "source_role": "up_projection_weight",
    },
    {
        "id": "down",
        "input_region": "gated_mlp",
        "kernel_index": 16,
        "output_region": "down",
        "source_role": "down_projection_weight",
    },
)


class ProductionConnectedLayerBuildError(ArtifactError):
    """Raised when a connected-layer deployment cannot be built exactly."""


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ProductionConnectedLayerBuildError(
            f"unsafe connected-layer artifact path {value!r}"
        )
    return path.as_posix()


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _copy_canonical(source: Path, destination: Path) -> None:
    try:
        payload = source.read_bytes()
        value = load_strict_json(source)
    except (OSError, ArtifactError) as exc:
        raise ProductionConnectedLayerBuildError(
            f"cannot copy canonical source {source}: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise ProductionConnectedLayerBuildError(
            f"source artifact is not canonical: {source}"
        )
    destination.write_bytes(payload)


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _load_report(
    path: Path, *, label: str, schema: str
) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionConnectedLayerBuildError(f"cannot load {label}: {exc}") from exc
    body = {key: item for key, item in value.items() if key != "report_id"}
    if (
        payload != canonical_json_bytes(value)
        or value.get("schema") != schema
        or value.get("status") != "pass"
        or value.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionConnectedLayerBuildError(
            f"{label} is not a canonical passing identified report"
        )
    return value, payload


def _fixture(qualification: Mapping[str, Any]) -> Mapping[str, Any]:
    fixtures = qualification.get("fixtures")
    if not isinstance(fixtures, list):
        raise ProductionConnectedLayerBuildError(
            "attention qualification fixture collection differs"
        )
    matches = [
        item
        for item in fixtures
        if isinstance(item, Mapping)
        and item.get("fixture_id") == attention_stage.FIXTURE_ID
    ]
    if len(matches) != 1:
        raise ProductionConnectedLayerBuildError(
            "attention qualification lacks the connected state fixture"
        )
    return matches[0]


def _output_codes(report: Mapping[str, Any], role: str) -> np.ndarray:
    outputs = report.get("outputs")
    record = outputs.get(role) if isinstance(outputs, Mapping) else None
    expected_shape = {
        "q_rotary": [QUERY_HEADS, HEAD_DIM],
        "k_rotary": [KEY_VALUE_HEADS, HEAD_DIM],
        "v": [KEY_VALUE_HEADS, HEAD_DIM],
    }[role]
    if (
        not isinstance(record, Mapping)
        or record.get("dtype") != "bf16"
        or record.get("shape") != expected_shape
        or record.get("size_bytes") != int(np.prod(expected_shape)) * 2
        or not isinstance(record.get("codes"), list)
        or len(record["codes"]) != int(np.prod(expected_shape))
    ):
        raise ProductionConnectedLayerBuildError(
            f"Q/K/V execution output {role!r} differs"
        )
    values = np.asarray(record["codes"], dtype=np.uint16).reshape(expected_shape)
    if hashlib.sha256(
        values.astype("<u2", copy=False).tobytes()
    ).hexdigest() != record.get("payload_sha256"):
        raise ProductionConnectedLayerBuildError(
            f"Q/K/V execution output {role!r} hash differs"
        )
    return values


def _qualification_bundle(
    *,
    qkv_qualification: Mapping[str, Any],
    qkv_report: Mapping[str, Any],
    qkv_report_payload: bytes,
    attention_qualification: Mapping[str, Any],
    attention_report: Mapping[str, Any],
    attention_report_payload: bytes,
    downstream_qualification: Mapping[str, Any],
    downstream_report: Mapping[str, Any],
) -> tuple[dict[str, str], Mapping[str, Any]]:
    qkv_outputs = {
        role: qkv_report.get("outputs", {}).get(role, {}).get("payload_sha256")
        for role in ("k_rotary", "q_rotary", "v")
    }
    expected_qkv_outputs = {
        role: qkv_qualification["outputs"][role]["payload_sha256"]
        for role in ("k_rotary", "q_rotary", "v")
    }
    source = attention_qualification.get("source")
    if (
        qkv_outputs != expected_qkv_outputs
        or not isinstance(source, Mapping)
        or source.get("qkv_build_id") != qkv_report.get("build_id")
        or source.get("qkv_execution_report_id") != qkv_report.get("report_id")
        or source.get("qkv_execution_payload_sha256")
        != hashlib.sha256(qkv_report_payload).hexdigest()
        or source.get("qkv_output_payload_sha256") != qkv_outputs
    ):
        raise ProductionConnectedLayerBuildError(
            "Q/K/V qualification and execution handoff differs"
        )

    fixture = _fixture(attention_qualification)
    attention_hashes = {
        role: attention_report.get("outputs", {}).get(role, {}).get("payload_sha256")
        for role in ("attention", "probabilities", "scaled_scores")
    }
    expected_attention_hashes = {
        role: fixture["outputs"][role]["payload_sha256"]
        for role in ("attention", "probabilities", "scaled_scores")
    }
    attention_binding = downstream_qualification.get("attention_input")
    if (
        attention_report.get("qualification_report_id")
        != attention_qualification["report_id"]
        or attention_hashes != expected_attention_hashes
        or attention_report.get("state", {}).get("state_sha256")
        != fixture["transaction"]["committed_state_sha256"]
        or not isinstance(attention_binding, Mapping)
        or attention_binding.get("build_id") != attention_report.get("build_id")
        or attention_binding.get("report_id") != attention_report.get("report_id")
        or attention_binding.get("qualification_report_id")
        != attention_qualification["report_id"]
        or attention_binding.get("payload_sha256") != attention_hashes["attention"]
    ):
        raise ProductionConnectedLayerBuildError(
            "attention qualification and execution handoff differs"
        )

    downstream_intermediates = downstream_report.get("intermediate_payload_sha256")
    expected_downstream_intermediates = {
        role: downstream_qualification["intermediates"][role]["payload_sha256"]
        for role in sorted(downstream_qualification["intermediates"])
    }
    if (
        downstream_report.get("qualification_report_id")
        != downstream_qualification["report_id"]
        or downstream_intermediates != expected_downstream_intermediates
        or downstream_report.get("output", {}).get("hidden_1", {}).get("payload_sha256")
        != downstream_qualification["output"]["hidden_1"]["payload_sha256"]
        or downstream_qualification.get("attention_input", {}).get("report_id")
        != attention_report.get("report_id")
    ):
        raise ProductionConnectedLayerBuildError(
            "downstream qualification and execution handoff differs"
        )

    identities = {
        "attention_execution_report_id": attention_report["report_id"],
        "attention_qualification_report_id": attention_qualification["report_id"],
        "downstream_execution_report_id": downstream_report["report_id"],
        "downstream_qualification_report_id": downstream_qualification["report_id"],
        "qkv_execution_report_id": qkv_report["report_id"],
        "qkv_qualification_report_id": qkv_qualification["report_id"],
    }
    bundle_body = {
        "attention_execution_payload_sha256": hashlib.sha256(
            attention_report_payload
        ).hexdigest(),
        **identities,
    }
    return {
        **identities,
        "qualification_bundle_id": sha256_bytes(canonical_json_bytes(bundle_body)),
    }, fixture


def _source_operations(
    model: ProductionModelGraph,
    *,
    qkv_qualification: Mapping[str, Any],
    attention_qualification: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
) -> tuple[ProductionOperation, ...]:
    try:
        qkv = qkv_stage._source_operations(model, qkv_qualification)
        attention = attention_stage._source_operations(model)
        downstream = downstream_stage._source_operations(
            model, downstream_qualification
        )
    except (ArtifactError, ValueError, KeyError) as exc:
        raise ProductionConnectedLayerBuildError(
            f"connected source-operation discovery failed: {exc}"
        ) from exc
    if (
        len(qkv) != 8
        or len(attention) != 3
        or len(downstream) != 8
        or attention[2].kind != "STATE_COMMIT"
    ):
        raise ProductionConnectedLayerBuildError(
            "connected source-operation coverage differs"
        )
    ordered = (*qkv, attention[0], attention[1], *downstream, attention[2])
    if (
        len({operation.operation_id for operation in ordered}) != 19
        or tuple(operation.operation_id for operation in ordered[:18])
        != tuple(f"node.{index:04d}" for index in range(18))
        or ordered[-1].operation_id != "state.commit"
    ):
        raise ProductionConnectedLayerBuildError(
            "connected source operations are not the exact layer-0 plus commit set"
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
    required_contracts = set(NUMERIC_CONTRACTS) - {LOOKUP_CONTRACT}
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
        or not required_contracts <= set(capability.qualified_numeric_contracts)
        or not {"bf16_tensor", "transactional_state", "vector_fp32"}
        <= set(capability.qualified_execution_modes)
    ):
        raise ProductionConnectedLayerBuildError(
            "connected layer exceeds the qualified ABI 2.4 capability"
        )

    qkv_sources = qkv_qualification["sources"]
    downstream_sources = downstream_qualification["sources"]
    shapes = {
        "q": qkv_sources["q_projection_weight"]["shape"],
        "k": qkv_sources["k_projection_weight"]["shape"],
        "v": qkv_sources["v_projection_weight"]["shape"],
        "attention_output": downstream_sources["attention_output_weight"]["shape"],
        "gate": downstream_sources["gate_projection_weight"]["shape"],
        "up": downstream_sources["up_projection_weight"]["shape"],
        "down": downstream_sources["down_projection_weight"]["shape"],
    }
    expected_shapes = {
        "q": [HIDDEN_WIDTH, HIDDEN_WIDTH],
        "k": [KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH],
        "v": [KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH],
        "attention_output": [HIDDEN_WIDTH, HIDDEN_WIDTH],
        "gate": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "up": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "down": [HIDDEN_WIDTH, INTERMEDIATE_WIDTH],
    }
    if shapes != expected_shapes:
        raise ProductionConnectedLayerBuildError(
            "connected projection shapes differ from the frozen layer"
        )
    projections: list[dict[str, Any]] = []
    for definition in PROJECTION_DEFINITIONS:
        n, k = shapes[definition["id"]]
        if n % N_TILE or k % K_TILE:
            raise ProductionConnectedLayerBuildError(
                f"projection {definition['id']!r} is not exactly tileable"
            )
        projections.append(
            {
                **definition,
                "k": k,
                "k_tile": K_TILE,
                "k_tiles": k // K_TILE,
                "n": n,
                "n_tile": N_TILE,
                "n_tiles": n // N_TILE,
                "tile_count": (n // N_TILE) * (k // K_TILE),
            }
        )
    transaction = fixture.get("transaction")
    inputs = fixture.get("inputs")
    if (
        not isinstance(transaction, Mapping)
        or not isinstance(inputs, Mapping)
        or inputs.get("committed_length") != COMMITTED_LENGTH
        or inputs.get("prepared_length") != PREPARED_LENGTH
        or transaction.get("base_generation") != BASE_GENERATION
        or transaction.get("transaction_id") != TRANSACTION_ID
        or qkv_qualification["input"]
        != {
            "embedding_row_payload_sha256": downstream_qualification["input"][
                "embedding_row_payload_sha256"
            ],
            "position_id": CONTEXT_CAPACITY - 1,
            "token_id": downstream_qualification["input"]["token_id"],
        }
    ):
        raise ProductionConnectedLayerBuildError(
            "connected runtime or state-fixture identity differs"
        )
    return {
        "base_generation": BASE_GENERATION,
        "coefficient_row_bytes": 2 * HEAD_DIM * 2,
        "committed_length": COMMITTED_LENGTH,
        "context_capacity": CONTEXT_CAPACITY,
        "fixture_id": attention_stage.FIXTURE_ID,
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


def _sram_plan(capability: ProductionCapability) -> dict[str, Any]:
    specs = (
        ("runtime_ids", 0, 0, "u32", [2], 8),
        ("hidden_0", 1, 0, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("input_norm_weight", 2, 0, "bf16", [HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("attention_norm", 3, 0, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("weight_tile", 4, 0, "bf16", [N_TILE, K_TILE], N_TILE * K_TILE * 2),
        ("accumulator_tile", 5, 0, "fp32", [1, N_TILE], N_TILE * 4),
        ("q_raw", 6, 0, "bf16", [1, HIDDEN_WIDTH], QUERY_BYTES),
        ("k_raw", 7, 0, "bf16", [1, KEY_VALUE_HEADS * HEAD_DIM], TOKEN_BYTES),
        ("v", 8, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], TOKEN_BYTES),
        ("q_norm_weight", 9, 0, "bf16", [HEAD_DIM], HEAD_DIM * 2),
        ("k_norm_weight", 10, 0, "bf16", [HEAD_DIM], HEAD_DIM * 2),
        ("q_norm", 11, 0, "bf16", [QUERY_HEADS, HEAD_DIM], QUERY_BYTES),
        ("k_norm", 12, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], TOKEN_BYTES),
        ("rope_coefficients", 13, 0, "bf16", [2 * HEAD_DIM], 2 * HEAD_DIM * 2),
        ("q_rotary", 14, 0, "bf16", [QUERY_HEADS, HEAD_DIM], QUERY_BYTES),
        ("k_rotary", 15, 0, "bf16", [KEY_VALUE_HEADS, HEAD_DIM], TOKEN_BYTES),
        ("attention", 0, 16, "bf16", [1, HIDDEN_WIDTH], QUERY_BYTES),
        ("attention_projected", 2, 8192, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("post_attention", 3, 8192, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        (
            "post_attention_norm_weight",
            6,
            8192,
            "bf16",
            [HIDDEN_WIDTH],
            HIDDEN_WIDTH * 2,
        ),
        ("mlp_norm", 7, 2048, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("gate", 8, 2048, "bf16", [1, INTERMEDIATE_WIDTH], INTERMEDIATE_WIDTH * 2),
        ("up", 9, 256, "bf16", [1, INTERMEDIATE_WIDTH], INTERMEDIATE_WIDTH * 2),
        ("gated_mlp", 10, 256, "bf16", [1, INTERMEDIATE_WIDTH], INTERMEDIATE_WIDTH * 2),
        ("down", 11, 8192, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
        ("hidden_1", 12, 2048, "bf16", [1, HIDDEN_WIDTH], HIDDEN_WIDTH * 2),
    )
    regions: list[dict[str, Any]] = []
    by_bank: dict[int, list[tuple[int, int, str]]] = {}
    for region_id, bank, offset, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if (
            bank >= capability.sram.banks
            or offset % capability.sram.word_bytes
            or offset + allocated > capability.sram.bytes_per_bank
        ):
            raise ProductionConnectedLayerBuildError(
                f"SRAM region {region_id!r} exceeds its assigned bank"
            )
        for start, end, other in by_bank.setdefault(bank, []):
            if offset < end and start < offset + allocated:
                raise ProductionConnectedLayerBuildError(
                    f"SRAM regions {other!r} and {region_id!r} overlap"
                )
        by_bank[bank].append((offset, offset + allocated, region_id))
        regions.append(
            {
                "address": capability.sram.bank_base(bank) + offset,
                "allocated_bytes": allocated,
                "bank": bank,
                "dtype": dtype,
                "id": region_id,
                "logical_bytes": logical_bytes,
                "offset_bytes": offset,
                "shape": shape,
            }
        )
    if len(regions) > capability.limits["max_sram_regions"]:
        raise ProductionConnectedLayerBuildError(
            "connected SRAM region count exceeds capability"
        )
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _append_region(
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


def _append_state_region(
    image: bytearray,
    *,
    capability: ProductionCapability,
    region_id: str,
    initialized_payload: bytes,
    allocated_bytes: int,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if len(initialized_payload) > allocated_bytes:
        raise ProductionConnectedLayerBuildError(
            f"state region {region_id!r} initialized payload exceeds allocation"
        )
    offset = align_up(len(image), capability.hbm.burst_bytes)
    image.extend(bytes(offset - len(image)))
    payload = initialized_payload + bytes(allocated_bytes - len(initialized_payload))
    image.extend(payload)
    return {
        "address": capability.hbm.base_address + offset,
        "allocated_bytes": allocated_bytes,
        "id": region_id,
        "initialized_payload_sha256": hashlib.sha256(initialized_payload).hexdigest(),
        "initialized_size_bytes": len(initialized_payload),
        "offset_bytes": offset,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "source": dict(source),
    }


def _append_projection(
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
    tiles: list[dict[str, Any]] = []
    for n_start in range(0, definition["n"], definition["n_tile"]):
        for k_start in range(0, definition["k"], definition["k_tile"]):
            tile = np.ascontiguousarray(
                weights[
                    n_start : n_start + definition["n_tile"],
                    k_start : k_start + definition["k_tile"],
                ],
                dtype="<u2",
            ).tobytes(order="C")
            offset = align_up(len(image), capability.hbm.burst_bytes)
            image.extend(bytes(offset - len(image)))
            image.extend(tile)
            tiles.append(
                {
                    "address": capability.hbm.base_address + offset,
                    "k_count": definition["k_tile"],
                    "k_start": k_start,
                    "n_count": definition["n_tile"],
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


def _hbm_image(
    *,
    qkv_payloads: Mapping[str, bytes],
    downstream_payloads: Mapping[str, bytes],
    qkv_qualification: Mapping[str, Any],
    qkv_report: Mapping[str, Any],
    attention_qualification: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
    fixture: Mapping[str, Any],
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    if qkv_payloads["embedding"] != downstream_payloads["hidden_0"]:
        raise ProductionConnectedLayerBuildError(
            "Q/K/V and downstream checkpoint reads disagree on hidden-0"
        )
    _output_codes(qkv_report, "q_rotary")
    k = _output_codes(qkv_report, "k_rotary")
    v = _output_codes(qkv_report, "v")
    try:
        history_k, history_v = attention_stage._history(k, v)
    except (ValueError, TypeError) as exc:
        raise ProductionConnectedLayerBuildError(
            f"initial KV state derivation failed: {exc}"
        ) from exc
    history_key_payload = np.ascontiguousarray(history_k, dtype="<u2").tobytes(
        order="C"
    )
    history_value_payload = np.ascontiguousarray(history_v, dtype="<u2").tobytes(
        order="C"
    )
    if (
        hashlib.sha256(history_key_payload).hexdigest()
        != fixture["inputs"]["committed_key_payload_sha256"]
        or hashlib.sha256(history_value_payload).hexdigest()
        != fixture["inputs"]["committed_value_payload_sha256"]
    ):
        raise ProductionConnectedLayerBuildError(
            "derived initial KV state differs from qualification evidence"
        )

    coefficients = coefficient_table_bf16(CONTEXT_CAPACITY)
    coefficient_payload = np.ascontiguousarray(coefficients, dtype="<u2").tobytes(
        order="C"
    )
    if (
        coefficients.shape != (CONTEXT_CAPACITY, 2 * HEAD_DIM)
        or hashlib.sha256(coefficient_payload).hexdigest()
        != qkv_stage.COEFFICIENT_TABLE_SHA256
        or qkv_qualification["rope"]["coefficient_table_payload_sha256"]
        != qkv_stage.COEFFICIENT_TABLE_SHA256
    ):
        raise ProductionConnectedLayerBuildError(
            "connected RoPE coefficient table identity differs"
        )

    image = bytearray()
    regions: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []
    regions.append(
        _append_region(
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
        )
    )
    regions.append(
        _append_region(
            image,
            capability=capability,
            region_id="input_norm_weight",
            payload=qkv_payloads["input_norm_weight"],
            source=_checkpoint_source(qkv_qualification, "input_norm_weight"),
        )
    )

    projection_problem = {item["id"]: item for item in problem["projections"]}
    for definition in PROJECTION_DEFINITIONS[:3]:
        role = definition["source_role"]
        projections.append(
            _append_projection(
                image,
                capability=capability,
                definition=projection_problem[definition["id"]],
                payload=qkv_payloads[role],
                source=_checkpoint_source(qkv_qualification, role),
            )
        )
    for role in ("q_norm_weight", "k_norm_weight"):
        regions.append(
            _append_region(
                image,
                capability=capability,
                region_id=role,
                payload=qkv_payloads[role],
                source=_checkpoint_source(qkv_qualification, role),
            )
        )
    regions.append(
        _append_region(
            image,
            capability=capability,
            region_id="rope_coefficient_table",
            payload=coefficient_payload,
            source={
                "kind": "derived_constant",
                "numeric_contract": ROPE_CONTRACT,
                "payload_sha256": qkv_stage.COEFFICIENT_TABLE_SHA256,
                "positions": CONTEXT_CAPACITY,
            },
        )
    )

    state_source = {
        "fixture_id": attention_stage.FIXTURE_ID,
        "kind": "qualified_runtime_initial_state",
        "qkv_execution_report_id": qkv_report["report_id"],
        "transform": fixture["inputs"]["transform"],
    }
    key_state = _append_state_region(
        image,
        capability=capability,
        region_id="key_state",
        initialized_payload=history_key_payload,
        allocated_bytes=STATE_REGION_BYTES,
        source=state_source,
    )
    value_state = _append_state_region(
        image,
        capability=capability,
        region_id="value_state",
        initialized_payload=history_value_payload,
        allocated_bytes=STATE_REGION_BYTES,
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
    metadata = _append_region(
        image,
        capability=capability,
        region_id="state_metadata",
        payload=metadata_payload,
        source={
            "fixture_id": attention_stage.FIXTURE_ID,
            "kind": "runtime_initial_state_metadata",
            "resource_id": attention_stage.RESOURCE_ID,
        },
    )
    regions.append(metadata)
    descriptor_payload = TRANSACTION_DESCRIPTOR.pack(
        TRANSACTION_MAGIC,
        TRANSACTION_ID,
        BASE_GENERATION,
        COMMITTED_LENGTH,
        PREPARED_LENGTH,
        1,
        metadata["address"],
        bytes(8),
    )
    regions.append(
        _append_region(
            image,
            capability=capability,
            region_id="transaction_descriptor",
            payload=descriptor_payload,
            source={
                "fixture_id": attention_stage.FIXTURE_ID,
                "kind": "runtime_transaction_descriptor",
                "transaction_id": TRANSACTION_ID,
            },
        )
    )

    regions.append(
        _append_region(
            image,
            capability=capability,
            region_id="post_attention_norm_weight",
            payload=downstream_payloads["post_attention_norm_weight"],
            source=_checkpoint_source(
                downstream_qualification, "post_attention_norm_weight"
            ),
        )
    )
    for definition in PROJECTION_DEFINITIONS[3:]:
        role = definition["source_role"]
        projections.append(
            _append_projection(
                image,
                capability=capability,
                definition=projection_problem[definition["id"]],
                payload=downstream_payloads[role],
                source=_checkpoint_source(downstream_qualification, role),
            )
        )
    padded = align_up(len(image), capability.hbm.burst_bytes)
    image.extend(bytes(padded - len(image)))
    payload = bytes(image)
    if len(payload) > capability.hbm.capacity_bytes:
        raise ProductionConnectedLayerBuildError(
            "connected-layer HBM image exceeds capability"
        )
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
        raise ProductionConnectedLayerBuildError("physical region IDs are not unique")
    return result


def _append_projection_commands(
    commands: list[ProductionCommand],
    *,
    projection: Mapping[str, Any],
    local: Mapping[str, Mapping[str, Any]],
) -> None:
    for tile in projection["tiles"]:
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
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
                index=len(commands),
                opcode=Opcode.MATMUL_BF16_TILE,
                engine=Engine.TENSOR,
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
    commands: list[ProductionCommand] = [
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
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
            index=1,
            opcode=Opcode.DMA_HBM_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=1,
            source0=remote["input_norm_weight"]["address"],
            destination=local["input_norm_weight"]["address"],
            size0=HIDDEN_WIDTH * 2,
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
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
        _append_projection_commands(commands, projection=projections[role], local=local)
    for kernel_index, role in ((5, "q"), (6, "k")):
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=kernel_index,
                source0=remote[f"{role}_norm_weight"]["address"],
                destination=local[f"{role}_norm_weight"]["address"],
                size0=HEAD_DIM * 2,
            )
        )
    for kernel_index, role, rows in ((5, "q", QUERY_HEADS), (6, "k", KEY_VALUE_HEADS)):
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.RMSNORM_BF16,
                engine=Engine.VECTOR,
                kernel_index=kernel_index,
                source0=local[f"{role}_raw"]["address"],
                source1=local[f"{role}_norm_weight"]["address"],
                destination=local[f"{role}_norm"]["address"],
                size0=rows,
                size1=HEAD_DIM,
                size2=EPSILON_CODE,
            )
        )
    commands.extend(
        (
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=7,
                source0=remote["rope_coefficient_table"]["address"],
                source1=local["runtime_ids"]["address"] + 4,
                destination=local["rope_coefficients"]["address"],
                auxiliary=0,
                size0=2 * HEAD_DIM * 2,
                size1=2 * HEAD_DIM * 2,
                size2=CONTEXT_CAPACITY,
                size3=4,
            ),
            ProductionCommand(
                index=len(commands) + 1,
                opcode=Opcode.ROPE_BF16,
                engine=Engine.VECTOR,
                kernel_index=7,
                source0=local["q_norm"]["address"],
                source1=local["k_norm"]["address"],
                destination=local["q_rotary"]["address"],
                auxiliary=local["k_rotary"]["address"],
                size0=QUERY_HEADS,
                size1=KEY_VALUE_HEADS,
                size2=HEAD_DIM,
                size3=local["rope_coefficients"]["address"],
            ),
        )
    )
    commands.extend(
        (
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.KV_PREPARE_BF16,
                engine=Engine.STATE,
                kernel_index=8,
                source0=local["k_rotary"]["address"],
                source1=local["v"]["address"],
                destination=remote["key_state"]["address"],
                auxiliary=remote["value_state"]["address"],
                size0=PREPARED_LENGTH,
                size1=KEY_VALUE_HEADS,
                size2=HEAD_DIM,
            ),
            ProductionCommand(
                index=len(commands) + 1,
                opcode=Opcode.GQA_ATTENTION_BF16,
                engine=Engine.VECTOR,
                kernel_index=9,
                source0=local["q_rotary"]["address"],
                source1=remote["key_state"]["address"],
                destination=local["attention"]["address"],
                auxiliary=remote["value_state"]["address"],
                size0=PREPARED_LENGTH,
                size1=QUERY_HEADS,
                size2=KEY_VALUE_HEADS,
                size3=HEAD_DIM,
            ),
        )
    )
    _append_projection_commands(
        commands, projection=projections["attention_output"], local=local
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.ADD_BF16,
            engine=Engine.VECTOR,
            kernel_index=11,
            source0=local["hidden_0"]["address"],
            source1=local["attention_projected"]["address"],
            destination=local["post_attention"]["address"],
            size0=1,
            size1=HIDDEN_WIDTH,
        )
    )
    commands.extend(
        (
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=12,
                source0=remote["post_attention_norm_weight"]["address"],
                destination=local["post_attention_norm_weight"]["address"],
                size0=HIDDEN_WIDTH * 2,
            ),
            ProductionCommand(
                index=len(commands) + 1,
                opcode=Opcode.RMSNORM_BF16,
                engine=Engine.VECTOR,
                kernel_index=12,
                source0=local["post_attention"]["address"],
                source1=local["post_attention_norm_weight"]["address"],
                destination=local["mlp_norm"]["address"],
                size0=1,
                size1=HIDDEN_WIDTH,
                size2=EPSILON_CODE,
            ),
        )
    )
    _append_projection_commands(commands, projection=projections["gate"], local=local)
    _append_projection_commands(commands, projection=projections["up"], local=local)
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.SILU_MUL_BF16,
            engine=Engine.VECTOR,
            kernel_index=15,
            source0=local["gate"]["address"],
            source1=local["up"]["address"],
            destination=local["gated_mlp"]["address"],
            size0=1,
            size1=INTERMEDIATE_WIDTH,
        )
    )
    _append_projection_commands(commands, projection=projections["down"], local=local)
    commands.extend(
        (
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.ADD_BF16,
                engine=Engine.VECTOR,
                kernel_index=17,
                source0=local["post_attention"]["address"],
                source1=local["down"]["address"],
                destination=local["hidden_1"]["address"],
                size0=1,
                size1=HIDDEN_WIDTH,
            ),
            ProductionCommand(
                index=len(commands) + 1,
                opcode=Opcode.STATE_COMMIT,
                engine=Engine.STATE,
                kernel_index=NO_KERNEL,
                source0=remote["state_metadata"]["address"],
                source1=remote["transaction_descriptor"]["address"],
                size0=CONTEXT_CAPACITY,
                size1=1,
            ),
            ProductionCommand(
                index=len(commands) + 2,
                opcode=Opcode.COMPLETE,
                engine=Engine.CONTROL,
            ),
        )
    )
    if len(commands) != 23570:
        raise ProductionConnectedLayerBuildError(
            f"connected command count differs: observed {len(commands)}"
        )
    return tuple(commands)


def _expected_counters(
    *,
    qkv_report: Mapping[str, Any],
    attention_report: Mapping[str, Any],
    downstream_report: Mapping[str, Any],
) -> dict[str, int]:
    stage_counters = (
        qkv_report.get("counters"),
        attention_report.get("counters"),
        downstream_report.get("counters"),
    )
    if any(
        not isinstance(counters, Mapping)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counters.values()
        )
        for counters in stage_counters
    ):
        raise ProductionConnectedLayerBuildError(
            "retained slice counter evidence differs"
        )
    names = sorted({name for counters in stage_counters for name in counters})
    combined = {
        name: sum(int(counters.get(name, 0)) for counters in stage_counters)
        for name in names
    }
    removed_attention_activation_bytes = QUERY_BYTES + 2 * TOKEN_BYTES
    removed_downstream_activation_bytes = 2 * HIDDEN_WIDTH * 2
    removed_activation_bytes = (
        removed_attention_activation_bytes + removed_downstream_activation_bytes
    )
    combined.update(
        {
            "command_count": 23570,
            "complete_command_count": 1,
            "direct_dma_command_count": 11780,
            "dma_command_count": 11782,
            "dma_sram_bytes_written": combined["dma_sram_bytes_written"]
            - removed_activation_bytes,
            "hbm_transferred_bytes_read": combined["hbm_transferred_bytes_read"]
            - removed_activation_bytes,
            "hbm_useful_bytes_read": combined["hbm_useful_bytes_read"]
            - removed_activation_bytes,
        }
    )
    if (
        combined["indexed_dma_command_count"] != 2
        or combined["matmul_command_count"] != 11776
        or combined["state_commit_command_count"] != 1
        or combined["dma_sram_bytes_written"] != 385901568
        or combined["hbm_useful_bytes_read"] != 385918208
    ):
        raise ProductionConnectedLayerBuildError(
            "connected counter derivation differs from the exact schedule"
        )
    return combined


def _kernel_ir(
    *,
    model: ProductionModelGraph,
    operations: tuple[ProductionOperation, ...],
    problem: Mapping[str, Any],
    bundle_id: str,
    qkv_qualification: Mapping[str, Any],
    attention_qualification: Mapping[str, Any],
    downstream_qualification: Mapping[str, Any],
) -> dict[str, Any]:
    qkv_operations = operations[:8]
    attention_operations = (operations[8], operations[9], operations[-1])
    downstream_operations = operations[10:18]
    qkv_ir = qkv_stage._kernel_ir(
        model=model,
        qualification=qkv_qualification,
        operations=qkv_operations,
        problem={
            "coefficient_row_bytes": problem["coefficient_row_bytes"],
            "context_positions": problem["rope_positions"],
            "head_dim": problem["head_dim"],
            "hidden_width": problem["hidden_width"],
            "key_value_heads": problem["key_value_heads"],
            "projections": [
                {
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
                }
                | {"role": projection["id"]}
                for projection in problem["projections"][:3]
            ],
            "query_heads": problem["query_heads"],
            "resident_embedding_base_token": problem["resident_embedding_base_token"],
            "resident_embedding_rows": problem["resident_embedding_rows"],
        },
    )
    attention_ir = attention_stage._kernel_ir(
        model, attention_qualification, attention_operations
    )
    downstream_ir = downstream_stage._kernel_ir(
        model=model,
        qualification=downstream_qualification,
        operations=downstream_operations,
    )
    kernels: list[dict[str, Any]] = []
    for kernel in qkv_ir["kernels"]:
        kernels.append({**kernel, "index": len(kernels)})
    for kernel in attention_ir["kernels"][:2]:
        kernels.append({**kernel, "index": len(kernels)})
    for kernel in downstream_ir["kernels"]:
        kernels.append({**kernel, "index": len(kernels)})
    commit = {
        **attention_ir["kernels"][2],
        "index": len(kernels),
        "inputs": ["hidden.1"],
        "outputs": ["hidden.1.committed"],
    }
    kernels.append(commit)
    if (
        len(kernels) != 19
        or [kernel["index"] for kernel in kernels] != list(range(19))
        or [kernel["source_operation_id"] for kernel in kernels]
        != [operation.operation_id for operation in operations]
    ):
        raise ProductionConnectedLayerBuildError(
            "connected neutral-kernel order differs"
        )
    body = {
        "graph_id": model.graph_id,
        "kernels": kernels,
        "qualification_report_id": bundle_id,
        "schema": KERNEL_SCHEMA,
    }
    return _identified(body, "kernel_ir_id")


def _request(
    *,
    model: ProductionModelGraph,
    operation_ids: Sequence[str],
    qualification_bundle_id: str,
) -> dict[str, Any]:
    body = {
        "expected_generation": BASE_GENERATION,
        "graph_id": model.graph_id,
        "position_id": CONTEXT_CAPACITY - 1,
        "qualification_bundle_id": qualification_bundle_id,
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": list(operation_ids),
        "span_tokens": PREPARED_LENGTH,
        "state_position_start": COMMITTED_LENGTH,
        "token_id": 0,
        "transaction_id": TRANSACTION_ID,
    }
    return _identified(body, "request_id")


def _source_artifact(path: Path) -> dict[str, Any]:
    digest, size = sha256_file(path)
    return {"path": path.name, "sha256": digest, "size_bytes": size}


def _source_lock(
    *,
    model: ProductionModelGraph,
    checkpoint_lock: Mapping[str, Any],
    capability: ProductionCapability,
    bundle: Mapping[str, str],
    source_paths: Mapping[str, Path],
) -> dict[str, Any]:
    copied_paths = {
        "attention_execution": "source/attention_execution.json",
        "attention_qualification": "source/attention_qualification.json",
        "checkpoint_lock": "source/checkpoint.lock.json",
        "downstream_execution": "source/downstream_execution.json",
        "downstream_qualification": "source/downstream_qualification.json",
        "model_graph": "source/model_graph.v2.json",
        "qkv_execution": "source/qkv_execution.json",
        "qkv_qualification": "source/qkv_qualification.json",
    }
    artifacts: dict[str, dict[str, Any]] = {}
    for role in sorted(copied_paths):
        digest, size = sha256_file(source_paths[role])
        artifacts[role] = {
            "path": copied_paths[role],
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


def _physical_plan(
    *,
    model: ProductionModelGraph,
    capability: ProductionCapability,
    operation_ids: Sequence[str],
    qualification_bundle_id: str,
    problem: Mapping[str, Any],
    sram: Mapping[str, Any],
    hbm: Mapping[str, Any],
    expected_counters: Mapping[str, int],
    command_payload: bytes,
) -> dict[str, Any]:
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": dict(expected_counters),
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
        "qualification_bundle_id": qualification_bundle_id,
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_ids": list(operation_ids),
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
    qualification_bundle_id: str,
    source_lock: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
    physical_plan: Mapping[str, Any],
    independent_check: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = [
        _artifact(root, "capability.json", "capability"),
        _artifact(root, "checks/independent_check.json", "independent_check"),
        _artifact(root, "execution_expectations.json", "execution_expectations"),
        _artifact(root, "ir/tensor_kernel_ir.json", "tensor_kernel_ir"),
        _artifact(root, HBM_IMAGE_PATH, "hbm_image"),
        _artifact(root, PHYSICAL_PLAN_PATH, "physical_plan"),
        _artifact(root, COMMAND_PATH, "command_program"),
        _artifact(root, "program/commands.disasm", "command_disassembly"),
        _artifact(root, REQUEST_PATH, "execution_request"),
        _artifact(root, "source.lock.json", "source_lock"),
    ]
    source_artifacts = source_lock["artifacts"]
    for role in sorted(source_artifacts):
        artifacts.append(
            _artifact(root, source_artifacts[role]["path"], f"source_{role}")
        )
    artifacts.sort(key=lambda item: item["path"])
    body = {
        "artifacts": artifacts,
        "capability_id": capability.capability_id,
        "claim_boundary": CLAIM_BOUNDARY,
        "command_abi": {"major": ABI_MAJOR, "minor": ELEMENTWISE_ABI_MINOR},
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "independent_check_id": independent_check["check_id"],
        "kernel_ir_id": kernel_ir["kernel_ir_id"],
        "physical_plan_id": physical_plan["physical_plan_id"],
        "qualification_bundle_id": qualification_bundle_id,
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
    qkv_qualification_path: Path,
    qkv_execution_path: Path,
    attention_qualification_path: Path,
    attention_execution_path: Path,
    downstream_qualification_path: Path,
    downstream_execution_path: Path,
    root: Path,
) -> dict[str, Any]:
    try:
        checkpoint_lock = load_checkpoint_lock(checkpoint_lock_path)
        model = load_production_model_graph(model_graph_path)
        capability = load_production_capability(capability_path)
        qkv_qualification = load_qkv_qualification(qkv_qualification_path)
        attention_qualification = load_attention_qualification(
            attention_qualification_path
        )
        downstream_qualification = load_layer_qualification(
            downstream_qualification_path
        )
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        QKVQualificationError,
        AttentionQualificationError,
        LayerQualificationError,
    ) as exc:
        raise ProductionConnectedLayerBuildError(
            f"connected source admission failed: {exc}"
        ) from exc
    qkv_report, qkv_report_payload = _load_report(
        qkv_execution_path,
        label="Q/K/V execution report",
        schema=QKV_EXECUTION_SCHEMA,
    )
    attention_report, attention_report_payload = _load_report(
        attention_execution_path,
        label="attention execution report",
        schema=ATTENTION_EXECUTION_SCHEMA,
    )
    downstream_report, _ = _load_report(
        downstream_execution_path,
        label="downstream execution report",
        schema=DOWNSTREAM_EXECUTION_SCHEMA,
    )
    if (
        qkv_qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]
        or downstream_qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]
    ):
        raise ProductionConnectedLayerBuildError(
            "connected qualifications and checkpoint lock differ"
        )
    bundle, fixture = _qualification_bundle(
        qkv_qualification=qkv_qualification,
        qkv_report=qkv_report,
        qkv_report_payload=qkv_report_payload,
        attention_qualification=attention_qualification,
        attention_report=attention_report,
        attention_report_payload=attention_report_payload,
        downstream_qualification=downstream_qualification,
        downstream_report=downstream_report,
    )
    operations = _source_operations(
        model,
        qkv_qualification=qkv_qualification,
        attention_qualification=attention_qualification,
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
        qkv_payloads = qkv_stage._read_locked_sources(
            snapshot, checkpoint_lock, qkv_qualification
        )
        downstream_payloads = downstream_stage._read_locked_sources(
            snapshot, checkpoint_lock, downstream_qualification
        )
    except (CheckpointError, ArtifactError, RuntimeError) as exc:
        raise ProductionConnectedLayerBuildError(
            f"connected locked-checkpoint read failed: {exc}"
        ) from exc
    image, hbm = _hbm_image(
        qkv_payloads=qkv_payloads,
        downstream_payloads=downstream_payloads,
        qkv_qualification=qkv_qualification,
        qkv_report=qkv_report,
        attention_qualification=attention_qualification,
        downstream_qualification=downstream_qualification,
        fixture=fixture,
        problem=problem,
        capability=capability,
    )
    sram = _sram_plan(capability)
    commands = _commands(hbm=hbm, sram=sram, problem=problem)
    if len(commands) > capability.limits["max_commands"]:
        raise ProductionConnectedLayerBuildError(
            "connected command count exceeds capability"
        )
    command_payload = encode(commands, abi_minor=ELEMENTWISE_ABI_MINOR)
    expected_counters = _expected_counters(
        qkv_report=qkv_report,
        attention_report=attention_report,
        downstream_report=downstream_report,
    )
    if len(commands) != expected_counters["command_count"]:
        raise ProductionConnectedLayerBuildError("connected command accounting differs")
    kernel_ir = _kernel_ir(
        model=model,
        operations=operations,
        problem=problem,
        bundle_id=bundle["qualification_bundle_id"],
        qkv_qualification=qkv_qualification,
        attention_qualification=attention_qualification,
        downstream_qualification=downstream_qualification,
    )
    physical_plan = _physical_plan(
        model=model,
        capability=capability,
        operation_ids=operation_ids,
        qualification_bundle_id=bundle["qualification_bundle_id"],
        problem=problem,
        sram=sram,
        hbm=hbm,
        expected_counters=expected_counters,
        command_payload=command_payload,
    )
    source_paths = {
        "attention_execution": attention_execution_path,
        "attention_qualification": attention_qualification_path,
        "checkpoint_lock": checkpoint_lock_path,
        "downstream_execution": downstream_execution_path,
        "downstream_qualification": downstream_qualification_path,
        "model_graph": model_graph_path,
        "qkv_execution": qkv_execution_path,
        "qkv_qualification": qkv_qualification_path,
    }
    source_lock = _source_lock(
        model=model,
        checkpoint_lock=checkpoint_lock,
        capability=capability,
        bundle=bundle,
        source_paths=source_paths,
    )
    request = _request(
        model=model,
        operation_ids=operation_ids,
        qualification_bundle_id=bundle["qualification_bundle_id"],
    )

    for directory in (
        "checks",
        "ir",
        "memory",
        "physical",
        "program",
        "request",
        "source",
    ):
        (root / directory).mkdir()
    write_canonical_json(root / "capability.json", capability.to_dict())
    write_canonical_json(root / "ir/tensor_kernel_ir.json", kernel_ir)
    (root / HBM_IMAGE_PATH).write_bytes(image)
    write_canonical_json(root / PHYSICAL_PLAN_PATH, physical_plan)
    (root / COMMAND_PATH).write_bytes(command_payload)
    _write_text(
        root / "program/commands.disasm",
        disassemble(commands, abi_minor=ELEMENTWISE_ABI_MINOR),
    )
    write_canonical_json(root / REQUEST_PATH, request)
    write_canonical_json(root / "source.lock.json", source_lock)
    for role, record in source_lock["artifacts"].items():
        _copy_canonical(source_paths[role], root / record["path"])

    from .production_connected_layer_checking import check_connected_layer_candidate

    independent_check = check_connected_layer_candidate(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        qkv_qualification_path=qkv_qualification_path,
        qkv_execution_path=qkv_execution_path,
        attention_qualification_path=attention_qualification_path,
        attention_execution_path=attention_execution_path,
        downstream_qualification_path=downstream_qualification_path,
        downstream_execution_path=downstream_execution_path,
        root=root,
    )
    write_canonical_json(root / "checks/independent_check.json", independent_check)
    expectations = _identified(
        {
            "check_id": independent_check["check_id"],
            "counters": independent_check["expected_counters"],
            "intermediate_payload_sha256": independent_check[
                "expected_intermediate_payload_sha256"
            ],
            "output_payload_sha256": independent_check[
                "expected_output_payload_sha256"
            ],
            "qualification_bundle_id": bundle["qualification_bundle_id"],
            "saturated_element_count": independent_check[
                "expected_saturated_element_count"
            ],
            "state_sha256": independent_check["expected_state_sha256"],
            "schema": EXPECTATIONS_SCHEMA,
        },
        "expectations_id",
    )
    write_canonical_json(root / "execution_expectations.json", expectations)
    manifest = _manifest(
        root,
        model=model,
        capability=capability,
        qualification_bundle_id=bundle["qualification_bundle_id"],
        source_lock=source_lock,
        kernel_ir=kernel_ir,
        physical_plan=physical_plan,
        independent_check=independent_check,
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_connected_layer_deployment(
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
    output: Path,
) -> dict[str, Any]:
    """Build and atomically publish one independently checked connected layer."""

    snapshot = Path(snapshot).resolve()
    sources = {
        "checkpoint_lock_path": Path(checkpoint_lock_path).resolve(),
        "model_graph_path": Path(model_graph_path).resolve(),
        "capability_path": Path(capability_path).resolve(),
        "qkv_qualification_path": Path(qkv_qualification_path).resolve(),
        "qkv_execution_path": Path(qkv_execution_path).resolve(),
        "attention_qualification_path": Path(attention_qualification_path).resolve(),
        "attention_execution_path": Path(attention_execution_path).resolve(),
        "downstream_qualification_path": Path(downstream_qualification_path).resolve(),
        "downstream_execution_path": Path(downstream_execution_path).resolve(),
    }
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise ProductionConnectedLayerBuildError(
            f"checkpoint snapshot does not exist: {snapshot}"
        )
    for label, path in sources.items():
        if not path.is_file():
            raise ProductionConnectedLayerBuildError(
                f"connected source {label} does not exist: {path}"
            )
    if output.exists():
        raise ProductionConnectedLayerBuildError(
            f"connected deployment output already exists: {output}"
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
    "CLAIM_BOUNDARY",
    "COMMAND_PATH",
    "COMPILER_VERSION",
    "EXPECTATIONS_SCHEMA",
    "HBM_IMAGE_PATH",
    "KERNEL_SCHEMA",
    "MANIFEST_SCHEMA",
    "PHYSICAL_PLAN_PATH",
    "PHYSICAL_PLAN_SCHEMA",
    "ProductionConnectedLayerBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_connected_layer_deployment",
]
