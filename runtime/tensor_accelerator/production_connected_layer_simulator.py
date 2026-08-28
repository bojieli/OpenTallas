"""Artifact-only interpreter for one command-connected authentic Qwen layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import struct
import tempfile
from typing import Any, Mapping

import numpy as np

from compiler.tensor_accelerator.common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from compiler.tensor_accelerator.production_command import (
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

from .attention import (
    AttentionKernelError,
    KVSnapshot,
    PreparedKV,
    commit_kv_append,
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)
from .bf16 import (
    BF16KernelError,
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
)
from .elementwise import (
    ElementwiseKernelError,
    bf16_add_rne,
    qwen3_silu_mul_bf16,
)
from .rmsnorm import RMSNormKernelError, rms_norm_bf16
from .rope import RoPEKernelError, rope_bf16


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.connected_layer_deployment.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.connected_layer_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.connected_layer_request.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.connected_layer_expectations.v1"
CHECK_SCHEMA = "opentallas.tensor_accelerator.connected_layer_independent_check.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.connected_layer_source_lock.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.connected_layer_execution.v1"

HBM_IMAGE_PATH = "memory/hbm_connected_layer.bin"
COMMAND_PATH = "program/commands.bin"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
REQUEST_PATH = "request/execution_request.json"

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
ROWS = 1
N_TILE = 64
K_TILE = 256
EPSILON_CODE = 0x358637BD

STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")
RESOURCE_ID = "kv.layer.0"

NUMERIC_CONTRACTS = [
    "bf16_add_rne_v1",
    "bf16_payload_lookup_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "bf16_byte_preserving_state_v1",
    "qwen3_gqa_fp32_softmax_bf16_v1",
    "qwen3_rmsnorm_fp32_bf16_v1",
    "qwen3_rope_fp32_bf16_v1",
    "qwen3_silu_mul_bf16_v1",
]

SOURCE_OPERATION_IDS = [
    *(f"node.{index:04d}" for index in range(18)),
    "state.commit",
]

COUNTER_NAMES = (
    "accumulator_sram_bytes_read",
    "accumulator_sram_bytes_written",
    "add_command_count",
    "add_input_sram_bytes_read",
    "add_output_sram_bytes_written",
    "attention_command_count",
    "attention_output_sram_bytes_written",
    "attention_query_sram_bytes_read",
    "command_count",
    "complete_command_count",
    "direct_dma_command_count",
    "dma_command_count",
    "dma_sram_bytes_written",
    "epsilon_additions",
    "exponential_evaluations",
    "final_weight_multiplications",
    "hbm_transferred_bytes_read",
    "hbm_transferred_bytes_written",
    "hbm_useful_bytes_read",
    "hbm_useful_bytes_written",
    "indexed_dma_command_count",
    "input_square_multiplications",
    "kv_prepare_command_count",
    "kv_prepare_sram_bytes_read",
    "mask_additions",
    "matmul_command_count",
    "matmul_input_sram_bytes_read",
    "matmul_output_sram_bytes_written",
    "matmul_weight_sram_bytes_read",
    "matrix_input_sram_bytes_read",
    "matrix_output_sram_bytes_written",
    "mean_divisions",
    "normalization_multiplications",
    "probability_multiplications",
    "projection_accumulation_additions",
    "projection_multiplications",
    "reciprocal_square_roots",
    "reduction_additions",
    "residual_additions",
    "rmsnorm_command_count",
    "rmsnorm_input_sram_bytes_read",
    "rmsnorm_output_sram_bytes_written",
    "rmsnorm_weight_sram_bytes_read",
    "rope_additions",
    "rope_command_count",
    "rope_input_sram_bytes_read",
    "rope_multiplications",
    "rope_output_sram_bytes_written",
    "runtime_request_sram_bytes_written",
    "scalar_accumulation_additions",
    "scalar_multiplications",
    "scaling_multiplications",
    "score_accumulation_additions",
    "score_multiplications",
    "sigmoid_denominator_additions",
    "sigmoid_divisions",
    "sigmoid_exponentials",
    "silu_command_count",
    "silu_input_sram_bytes_read",
    "silu_multiplications",
    "silu_output_sram_bytes_written",
    "softmax_reciprocal_divisions",
    "softmax_reduction_additions",
    "state_commit_command_count",
    "state_metadata_bytes_read",
    "state_metadata_bytes_written",
    "state_payload_bytes_read",
    "state_payload_bytes_written",
    "up_gate_multiplications",
    "value_accumulation_additions",
    "value_multiplications",
    "weight_sram_bytes_read",
)

INTERMEDIATE_ROLES = (
    "attention",
    "attention_norm",
    "attention_projected",
    "down",
    "gate",
    "gated_mlp",
    "hidden_0",
    "k_norm",
    "k_raw",
    "k_rotary",
    "mlp_norm",
    "post_attention",
    "probabilities",
    "q_norm",
    "q_raw",
    "q_rotary",
    "scaled_scores",
    "silu_activation",
    "up",
    "v",
)

DIRECT_HBM_ROLES = {
    "embedding_rows",
    "input_norm_weight",
    "q_norm_weight",
    "k_norm_weight",
    "rope_coefficient_table",
    "key_state",
    "value_state",
    "state_metadata",
    "transaction_descriptor",
    "post_attention_norm_weight",
}

PROJECTION_SPECS = (
    ("q", 2, "attention_norm", "q_raw", HIDDEN_WIDTH, HIDDEN_WIDTH),
    ("k", 3, "attention_norm", "k_raw", KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH),
    ("v", 4, "attention_norm", "v", KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH),
    (
        "attention_output",
        10,
        "attention",
        "attention_projected",
        HIDDEN_WIDTH,
        HIDDEN_WIDTH,
    ),
    ("gate", 13, "mlp_norm", "gate", INTERMEDIATE_WIDTH, HIDDEN_WIDTH),
    ("up", 14, "mlp_norm", "up", INTERMEDIATE_WIDTH, HIDDEN_WIDTH),
    ("down", 16, "gated_mlp", "down", HIDDEN_WIDTH, INTERMEDIATE_WIDTH),
)

SRAM_SPECS = (
    ("runtime_ids", 0, 0, "u32", [2], 8),
    ("hidden_0", 1, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
    ("input_norm_weight", 2, 0, "bf16", [HIDDEN_WIDTH], 8192),
    ("attention_norm", 3, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
    ("weight_tile", 4, 0, "bf16", [N_TILE, K_TILE], 32768),
    ("accumulator_tile", 5, 0, "fp32", [1, N_TILE], 256),
    ("q_raw", 6, 0, "bf16", [1, HIDDEN_WIDTH], 8192),
    ("k_raw", 7, 0, "bf16", [1, KEY_VALUE_HEADS * HEAD_DIM], 2048),
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

EXPECTED_CLAIM_BOUNDARY = [
    "one actual Qwen3-8B layer-0 token from embedding lookup through hidden.1",
    "one neutral 19-kernel graph, one HBM image, one SRAM plan, and one ABI 2.4 program",
    "Q/K/V, transactional KV prepare, GQA attention, output projection, residuals, RMSNorm, and MLP connected only by architectural state",
    "uncharacterized one-layer evidence only; not full-model decoding, timing, RTL, 130-nm, performance, energy, or ROM-comparison evidence",
]

EXPECTED_ROLES = {
    "capability.json": "capability",
    "checks/independent_check.json": "independent_check",
    "execution_expectations.json": "execution_expectations",
    "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
    HBM_IMAGE_PATH: "hbm_image",
    PHYSICAL_PLAN_PATH: "physical_plan",
    COMMAND_PATH: "command_program",
    "program/commands.disasm": "command_disassembly",
    REQUEST_PATH: "execution_request",
    "source.lock.json": "source_lock",
    "source/attention_execution.json": "source_attention_execution",
    "source/attention_qualification.json": "source_attention_qualification",
    "source/checkpoint.lock.json": "source_checkpoint_lock",
    "source/downstream_execution.json": "source_downstream_execution",
    "source/downstream_qualification.json": "source_downstream_qualification",
    "source/model_graph.v2.json": "source_model_graph",
    "source/qkv_execution.json": "source_qkv_execution",
    "source/qkv_qualification.json": "source_qkv_qualification",
}


class ProductionConnectedLayerSimulationError(RuntimeError):
    """Raised when artifacts or commands violate the connected-layer machine."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionConnectedLayerSimulationError(
            f"cannot load {label}: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise ProductionConnectedLayerSimulationError(f"{label} is not canonical JSON")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionConnectedLayerSimulationError(str(exc)) from exc
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionConnectedLayerSimulationError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise ProductionConnectedLayerSimulationError(
            f"{label} must be a safe relative path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProductionConnectedLayerSimulationError(
            f"{label} must be a safe relative path"
        )
    return path.as_posix()


def _manifest(root: Path) -> dict[str, Any]:
    value = _load_canonical(root / "deployment_manifest.json", "deployment manifest")
    _identity(value, "build_id", "deployment manifest")
    exact_keys(
        value,
        {
            "artifacts",
            "build_id",
            "capability_id",
            "claim_boundary",
            "command_abi",
            "compiler_version",
            "graph_id",
            "independent_check_id",
            "kernel_ir_id",
            "physical_plan_id",
            "qualification_bundle_id",
            "schema",
            "source_lock_id",
        },
        set(),
        "connected deployment manifest",
    )
    if (
        value["schema"] != MANIFEST_SCHEMA
        or value["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY
        or value["command_abi"] != {"major": ABI_MAJOR, "minor": ELEMENTWISE_ABI_MINOR}
        or value["compiler_version"]
        != "tensor-accelerator-production-connected-layer-0.1.0"
    ):
        raise ProductionConnectedLayerSimulationError(
            "deployment manifest contract differs"
        )
    for field in (
        "build_id",
        "capability_id",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_bundle_id",
        "source_lock_id",
    ):
        try:
            require_sha256(value[field], f"manifest.{field}")
        except ArtifactError as exc:
            raise ProductionConnectedLayerSimulationError(str(exc)) from exc
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_ROLES):
        raise ProductionConnectedLayerSimulationError(
            "deployment artifact coverage differs"
        )
    observed_paths = []
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionConnectedLayerSimulationError(
                f"manifest artifact {index} is malformed"
            )
        exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            set(),
            f"manifest artifact {index}",
        )
        path = _safe_relative(record["path"], f"artifact {index}.path")
        if EXPECTED_ROLES.get(path) != record["role"]:
            raise ProductionConnectedLayerSimulationError(
                f"artifact role differs for {path!r}"
            )
        try:
            payload = (root / path).read_bytes()
        except OSError as exc:
            raise ProductionConnectedLayerSimulationError(
                f"cannot read artifact {path!r}: {exc}"
            ) from exc
        if (
            record["size_bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ProductionConnectedLayerSimulationError(
                f"artifact identity differs for {path!r}"
            )
        observed_paths.append(path)
    if set(observed_paths) != set(EXPECTED_ROLES) or len(observed_paths) != len(
        set(observed_paths)
    ):
        raise ProductionConnectedLayerSimulationError("manifest artifact paths differ")
    return value


@dataclass
class _SRAMRegion:
    region_id: str
    address: int
    logical_bytes: int
    allocated_bytes: int
    data: bytearray
    initialized: bytearray

    @classmethod
    def create(cls, record: Mapping[str, Any]) -> "_SRAMRegion":
        allocated = int(record["allocated_bytes"])
        return cls(
            region_id=str(record["id"]),
            address=int(record["address"]),
            logical_bytes=int(record["logical_bytes"]),
            allocated_bytes=allocated,
            data=bytearray(allocated),
            initialized=bytearray(allocated),
        )

    def contains(self, address: int, size: int) -> bool:
        offset = address - self.address
        return size >= 0 and offset >= 0 and offset + size <= self.logical_bytes

    def write(self, address: int, payload: bytes) -> None:
        if not self.contains(address, len(payload)):
            raise ProductionConnectedLayerSimulationError(
                f"write escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + len(payload)
        self.data[start:end] = payload
        self.initialized[start:end] = b"\x01" * len(payload)

    def read(self, address: int, size: int) -> bytes:
        if not self.contains(address, size):
            raise ProductionConnectedLayerSimulationError(
                f"read escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + size
        if not all(self.initialized[start:end]):
            raise ProductionConnectedLayerSimulationError(
                f"read of uninitialized SRAM region {self.region_id!r}"
            )
        return bytes(self.data[start:end])


def _region_for(
    regions: Mapping[str, _SRAMRegion], address: int, size: int
) -> _SRAMRegion:
    matches = [region for region in regions.values() if region.contains(address, size)]
    if len(matches) != 1:
        raise ProductionConnectedLayerSimulationError(
            "SRAM address does not select exactly one declared region"
        )
    return matches[0]


def _bf16_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _u32_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u4").tobytes(order="C")


def _state_record(state: KVSnapshot) -> dict[str, Any]:
    key_payload = _bf16_payload(state.key_values)
    value_payload = _bf16_payload(state.value_values)
    body = {
        "capacity": state.capacity,
        "generation": state.generation,
        "key_payload_sha256": hashlib.sha256(key_payload).hexdigest(),
        "length": state.length,
        "resource_id": state.resource_id,
        "value_payload_sha256": hashlib.sha256(value_payload).hexdigest(),
    }
    return {**body, "state_sha256": sha256_bytes(canonical_json_bytes(body))}


def _keys(
    value: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    try:
        exact_keys(value, required, optional, label)
    except ArtifactError as exc:
        raise ProductionConnectedLayerSimulationError(str(exc)) from exc


def _required_int(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    try:
        return require_int(value, label, minimum=minimum, maximum=maximum)
    except ArtifactError as exc:
        raise ProductionConnectedLayerSimulationError(str(exc)) from exc


def _required_sha(value: object, label: str) -> str:
    try:
        return require_sha256(value, label)
    except ArtifactError as exc:
        raise ProductionConnectedLayerSimulationError(str(exc)) from exc


def _records_by_id(
    value: object,
    label: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ProductionConnectedLayerSimulationError(
            f"{label} must be an object array"
        )
    records = {str(item.get("id")): item for item in value}
    if len(records) != len(value) or "None" in records:
        raise ProductionConnectedLayerSimulationError(f"{label} IDs differ")
    return records


def _source_lock(
    root: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    value = _load_canonical(root / "source.lock.json", "source lock")
    _identity(value, "source_lock_id", "source lock")
    _keys(
        value,
        {
            "artifacts",
            "capability_id",
            "checkpoint_lock_id",
            "compiler_version",
            "graph_id",
            "qualification_bundle",
            "schema",
            "source_lock_id",
        },
        set(),
        "source lock",
    )
    if (
        value["schema"] != SOURCE_LOCK_SCHEMA
        or value["source_lock_id"] != manifest["source_lock_id"]
        or value["capability_id"] != manifest["capability_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["compiler_version"] != manifest["compiler_version"]
    ):
        raise ProductionConnectedLayerSimulationError("source-lock binding differs")

    expected_paths = {
        "attention_execution": "source/attention_execution.json",
        "attention_qualification": "source/attention_qualification.json",
        "checkpoint_lock": "source/checkpoint.lock.json",
        "downstream_execution": "source/downstream_execution.json",
        "downstream_qualification": "source/downstream_qualification.json",
        "model_graph": "source/model_graph.v2.json",
        "qkv_execution": "source/qkv_execution.json",
        "qkv_qualification": "source/qkv_qualification.json",
    }
    artifacts = value["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != set(expected_paths):
        raise ProductionConnectedLayerSimulationError(
            "source-lock artifact coverage differs"
        )
    for role, expected_path in expected_paths.items():
        record = artifacts[role]
        if not isinstance(record, dict):
            raise ProductionConnectedLayerSimulationError(
                f"source-lock artifact {role!r} is malformed"
            )
        _keys(record, {"path", "sha256", "size_bytes"}, set(), f"source-lock {role}")
        path = _safe_relative(record["path"], f"source-lock {role}.path")
        if path != expected_path:
            raise ProductionConnectedLayerSimulationError(
                f"source-lock path differs for {role!r}"
            )
        payload = (root / path).read_bytes()
        if (
            record["size_bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ProductionConnectedLayerSimulationError(
                f"source-lock identity differs for {role!r}"
            )

    source_specs = {
        "qkv_qualification": (
            "opentallas.tensor_accelerator.qkv_qualification.v1",
            "qkv_qualification_report_id",
        ),
        "qkv_execution": (
            "opentallas.tensor_accelerator.qkv_execution.v1",
            "qkv_execution_report_id",
        ),
        "attention_qualification": (
            "opentallas.tensor_accelerator.attention_qualification.v1",
            "attention_qualification_report_id",
        ),
        "attention_execution": (
            "opentallas.tensor_accelerator.attention_execution.v1",
            "attention_execution_report_id",
        ),
        "downstream_qualification": (
            "opentallas.tensor_accelerator.layer_qualification.v1",
            "downstream_qualification_report_id",
        ),
        "downstream_execution": (
            "opentallas.tensor_accelerator.layer_downstream_execution.v1",
            "downstream_execution_report_id",
        ),
    }
    bundle = value["qualification_bundle"]
    if not isinstance(bundle, dict) or set(bundle) != {
        *(field for _, field in source_specs.values()),
        "qualification_bundle_id",
    }:
        raise ProductionConnectedLayerSimulationError(
            "qualification bundle fields differ"
        )
    reports: dict[str, dict[str, Any]] = {}
    for role, (schema, bundle_field) in source_specs.items():
        report = _load_canonical(root / expected_paths[role], role.replace("_", " "))
        _identity(report, "report_id", role.replace("_", " "))
        if (
            report.get("schema") != schema
            or report.get("status") != "pass"
            or report.get("report_id") != bundle[bundle_field]
        ):
            raise ProductionConnectedLayerSimulationError(
                f"source report binding differs for {role!r}"
            )
        reports[role] = report

    bundle_body = {
        "attention_execution_payload_sha256": hashlib.sha256(
            (root / expected_paths["attention_execution"]).read_bytes()
        ).hexdigest(),
        **{field: bundle[field] for _, field in source_specs.values()},
    }
    if (
        bundle["qualification_bundle_id"]
        != sha256_bytes(canonical_json_bytes(bundle_body))
        or bundle["qualification_bundle_id"] != manifest["qualification_bundle_id"]
    ):
        raise ProductionConnectedLayerSimulationError(
            "qualification bundle identity differs"
        )

    checkpoint = _load_canonical(
        root / expected_paths["checkpoint_lock"], "checkpoint lock"
    )
    _identity(checkpoint, "lock_id", "checkpoint lock")
    if (
        checkpoint.get("schema") != "opentallas.checkpoint_lock.v1"
        or checkpoint.get("lock_id") != value["checkpoint_lock_id"]
    ):
        raise ProductionConnectedLayerSimulationError("checkpoint-lock binding differs")

    graph = _load_canonical(root / expected_paths["model_graph"], "model graph")
    _identity(graph, "graph_id", "model graph")
    if (
        graph.get("schema") != "opentallas.model_graph.v2"
        or graph.get("graph_id") != value["graph_id"]
    ):
        raise ProductionConnectedLayerSimulationError("model-graph binding differs")
    operations = graph.get("operations")
    if not isinstance(operations, list):
        raise ProductionConnectedLayerSimulationError("model graph operations differ")
    by_operation = {
        item.get("id"): item for item in operations if isinstance(item, dict)
    }
    if any(operation_id not in by_operation for operation_id in SOURCE_OPERATION_IDS):
        raise ProductionConnectedLayerSimulationError(
            "model graph lacks a connected-layer source operation"
        )
    return value, graph


def _kernel_ir(
    root: Path,
    manifest: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(root / "ir/tensor_kernel_ir.json", "tensor kernel IR")
    _identity(value, "kernel_ir_id", "tensor kernel IR")
    _keys(
        value,
        {"graph_id", "kernel_ir_id", "kernels", "qualification_report_id", "schema"},
        set(),
        "tensor kernel IR",
    )
    if (
        value["schema"] != KERNEL_SCHEMA
        or value["kernel_ir_id"] != manifest["kernel_ir_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_report_id"] != manifest["qualification_bundle_id"]
    ):
        raise ProductionConnectedLayerSimulationError(
            "tensor-kernel IR binding differs"
        )
    kernels = value["kernels"]
    if not isinstance(kernels, list) or len(kernels) != 19:
        raise ProductionConnectedLayerSimulationError("tensor-kernel coverage differs")
    kinds = [
        "EMBEDDING_LOOKUP",
        "RMS_NORM",
        "MATMUL",
        "MATMUL",
        "MATMUL",
        "RMS_NORM",
        "RMS_NORM",
        "ROPE",
        "KV_PREPARE",
        "ATTENTION",
        "MATMUL",
        "ADD",
        "RMS_NORM",
        "MATMUL",
        "MATMUL",
        "SILU_MUL",
        "MATMUL",
        "ADD",
        "STATE_COMMIT",
    ]
    contracts = [
        "bf16_payload_lookup_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        *(["bf16_bf16_fp32_sequential_rne_v1"] * 3),
        *(["qwen3_rmsnorm_fp32_bf16_v1"] * 2),
        "qwen3_rope_fp32_bf16_v1",
        "bf16_byte_preserving_state_v1",
        "qwen3_gqa_fp32_softmax_bf16_v1",
        "bf16_bf16_fp32_sequential_rne_v1",
        "bf16_add_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        *(["bf16_bf16_fp32_sequential_rne_v1"] * 2),
        "qwen3_silu_mul_bf16_v1",
        "bf16_bf16_fp32_sequential_rne_v1",
        "bf16_add_rne_v1",
        "bf16_byte_preserving_state_v1",
    ]
    operations = {
        item.get("id"): item for item in graph["operations"] if isinstance(item, dict)
    }

    forbidden_keys = {
        "address",
        "bank",
        "destination",
        "engine",
        "hbm",
        "offset_bytes",
        "opcode",
        "physical_plan",
        "source0",
        "source1",
        "sram",
    }

    def reject_physical_leak(item: object) -> None:
        if isinstance(item, Mapping):
            if forbidden_keys & set(item):
                raise ProductionConnectedLayerSimulationError(
                    "tensor-kernel IR contains physical execution fields"
                )
            for child in item.values():
                reject_physical_leak(child)
        elif isinstance(item, list):
            for child in item:
                reject_physical_leak(child)

    reject_physical_leak(value)
    for index, kernel in enumerate(kernels):
        if not isinstance(kernel, dict):
            raise ProductionConnectedLayerSimulationError(
                f"tensor kernel {index} is malformed"
            )
        required = {
            "attributes",
            "index",
            "inputs",
            "kind",
            "numeric_contract",
            "outputs",
            "shape",
            "source_operation_id",
        }
        if index == 18:
            required.add("state_resources")
        _keys(kernel, required, set(), f"tensor kernel {index}")
        if (
            kernel["index"] != index
            or kernel["kind"] != kinds[index]
            or kernel["numeric_contract"] != contracts[index]
            or kernel["source_operation_id"] != SOURCE_OPERATION_IDS[index]
        ):
            raise ProductionConnectedLayerSimulationError(
                f"tensor kernel {index} semantic identity differs"
            )
        if index < 18:
            source = operations[SOURCE_OPERATION_IDS[index]]
            if kernel["inputs"] != source.get("inputs") or kernel[
                "outputs"
            ] != source.get("outputs"):
                raise ProductionConnectedLayerSimulationError(
                    f"tensor kernel {index} graph dataflow differs"
                )
        elif (
            kernel["inputs"] != ["hidden.1"]
            or kernel["outputs"] != ["hidden.1.committed"]
            or kernel["state_resources"] != [RESOURCE_ID]
        ):
            raise ProductionConnectedLayerSimulationError(
                "state-commit kernel boundary differs"
            )
    return value


def _expected_problem() -> dict[str, Any]:
    source_roles = {
        "q": "q_projection_weight",
        "k": "k_projection_weight",
        "v": "v_projection_weight",
        "attention_output": "attention_output_weight",
        "gate": "gate_projection_weight",
        "up": "up_projection_weight",
        "down": "down_projection_weight",
    }
    projections = []
    for role, kernel, input_region, output_region, n, k in PROJECTION_SPECS:
        projections.append(
            {
                "id": role,
                "input_region": input_region,
                "k": k,
                "k_tile": K_TILE,
                "k_tiles": k // K_TILE,
                "kernel_index": kernel,
                "n": n,
                "n_tile": N_TILE,
                "n_tiles": n // N_TILE,
                "output_region": output_region,
                "source_role": source_roles[role],
                "tile_count": (n // N_TILE) * (k // K_TILE),
            }
        )
    return {
        "base_generation": BASE_GENERATION,
        "coefficient_row_bytes": 2 * HEAD_DIM * 2,
        "committed_length": COMMITTED_LENGTH,
        "context_capacity": CONTEXT_CAPACITY,
        "fixture_id": "checkpoint_derived_nonempty_history",
        "head_dim": HEAD_DIM,
        "hidden_width": HIDDEN_WIDTH,
        "intermediate_width": INTERMEDIATE_WIDTH,
        "key_value_heads": KEY_VALUE_HEADS,
        "prepared_length": PREPARED_LENGTH,
        "projections": projections,
        "qualified_state_resources": 1,
        "query_heads": QUERY_HEADS,
        "resident_embedding_base_token": 0,
        "resident_embedding_rows": 1,
        "rope_positions": CONTEXT_CAPACITY,
        "rows": ROWS,
        "source_atomic_state_count": 36,
        "transaction_id": TRANSACTION_ID,
    }


def _expected_sram(capability: ProductionCapability) -> dict[str, Any]:
    regions = []
    for region_id, bank, offset, dtype, shape, logical in SRAM_SPECS:
        allocated = align_up(logical, capability.sram.word_bytes)
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


def _validate_hbm(
    raw: object,
    image: bytes,
    capability: ProductionCapability,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionConnectedLayerSimulationError("physical HBM plan is malformed")
    _keys(raw, {"image", "projections", "regions"}, set(), "physical HBM plan")
    image_record = raw["image"]
    expected_image = {
        "base_address": capability.hbm.base_address,
        "path": HBM_IMAGE_PATH,
        "sha256": hashlib.sha256(image).hexdigest(),
        "size_bytes": len(image),
    }
    if image_record != expected_image or len(image) > capability.hbm.capacity_bytes:
        raise ProductionConnectedLayerSimulationError("HBM image metadata differs")

    direct = _records_by_id(raw["regions"], "HBM regions")
    if set(direct) != DIRECT_HBM_ROLES:
        raise ProductionConnectedLayerSimulationError(
            "HBM region roles differ or include retained activations"
        )
    expected_sizes = {
        "embedding_rows": HIDDEN_WIDTH * 2,
        "input_norm_weight": HIDDEN_WIDTH * 2,
        "q_norm_weight": HEAD_DIM * 2,
        "k_norm_weight": HEAD_DIM * 2,
        "rope_coefficient_table": CONTEXT_CAPACITY * 2 * HEAD_DIM * 2,
        "state_metadata": STATE_METADATA.size,
        "transaction_descriptor": TRANSACTION_DESCRIPTOR.size,
        "post_attention_norm_weight": HIDDEN_WIDTH * 2,
    }
    intervals: list[tuple[int, int, str]] = []
    for role, record in direct.items():
        source = record.get("source")
        if not isinstance(source, Mapping):
            raise ProductionConnectedLayerSimulationError(
                f"HBM source metadata differs for {role!r}"
            )
        if role in {"key_state", "value_state"}:
            _keys(
                record,
                {
                    "address",
                    "allocated_bytes",
                    "id",
                    "initialized_payload_sha256",
                    "initialized_size_bytes",
                    "offset_bytes",
                    "payload_sha256",
                    "source",
                },
                set(),
                f"HBM region {role}",
            )
            size = _required_int(record["allocated_bytes"], f"{role}.allocated_bytes")
            initialized = _required_int(
                record["initialized_size_bytes"], f"{role}.initialized_size_bytes"
            )
            if (
                size != CONTEXT_CAPACITY * TOKEN_BYTES
                or initialized != COMMITTED_LENGTH * TOKEN_BYTES
                or source.get("kind") != "qualified_runtime_initial_state"
            ):
                raise ProductionConnectedLayerSimulationError(
                    f"HBM state-region contract differs for {role!r}"
                )
        else:
            _keys(
                record,
                {
                    "address",
                    "id",
                    "offset_bytes",
                    "payload_sha256",
                    "size_bytes",
                    "source",
                },
                set(),
                f"HBM region {role}",
            )
            size = _required_int(record["size_bytes"], f"{role}.size_bytes")
            initialized = size
            if size != expected_sizes[role]:
                raise ProductionConnectedLayerSimulationError(
                    f"HBM region size differs for {role!r}"
                )
        offset = _required_int(record["offset_bytes"], f"{role}.offset_bytes")
        address = _required_int(record["address"], f"{role}.address")
        if (
            offset % capability.hbm.burst_bytes
            or address != capability.hbm.base_address + offset
            or offset + size > len(image)
        ):
            raise ProductionConnectedLayerSimulationError(
                f"HBM placement differs for {role!r}"
            )
        payload = image[offset : offset + size]
        if record["payload_sha256"] != hashlib.sha256(payload).hexdigest():
            raise ProductionConnectedLayerSimulationError(
                f"HBM payload hash differs for {role!r}"
            )
        if role in {"key_state", "value_state"}:
            if record["initialized_payload_sha256"] != hashlib.sha256(
                payload[:initialized]
            ).hexdigest() or any(payload[initialized:]):
                raise ProductionConnectedLayerSimulationError(
                    f"HBM initial-state payload differs for {role!r}"
                )
        intervals.append((offset, offset + size, role))

    projections = _records_by_id(raw["projections"], "HBM projections")
    expected_projection_ids = {spec[0] for spec in PROJECTION_SPECS}
    if set(projections) != expected_projection_ids:
        raise ProductionConnectedLayerSimulationError("HBM projection roles differ")
    for role, kernel, input_region, output_region, n, k in PROJECTION_SPECS:
        projection = projections[role]
        _keys(
            projection,
            {"id", "input_region", "kernel_index", "output_region", "source", "tiles"},
            set(),
            f"HBM projection {role}",
        )
        source = projection["source"]
        tiles = projection["tiles"]
        if (
            projection["kernel_index"] != kernel
            or projection["input_region"] != input_region
            or projection["output_region"] != output_region
            or not isinstance(source, dict)
            or source.get("kind") != "checkpoint_tensor"
            or source.get("shape") != [n, k]
            or not isinstance(tiles, list)
            or len(tiles) != (n // N_TILE) * (k // K_TILE)
        ):
            raise ProductionConnectedLayerSimulationError(
                f"HBM projection contract differs for {role!r}"
            )
        _required_sha(source.get("payload_sha256"), f"{role}.source.payload_sha256")
        tile_index = 0
        for n_start in range(0, n, N_TILE):
            for k_start in range(0, k, K_TILE):
                tile = tiles[tile_index]
                if not isinstance(tile, dict):
                    raise ProductionConnectedLayerSimulationError(
                        f"HBM projection tile {role}[{tile_index}] is malformed"
                    )
                _keys(
                    tile,
                    {
                        "address",
                        "k_count",
                        "k_start",
                        "n_count",
                        "n_start",
                        "offset_bytes",
                        "payload_sha256",
                        "size_bytes",
                        "tile_index",
                    },
                    set(),
                    f"HBM projection tile {role}[{tile_index}]",
                )
                offset = _required_int(tile["offset_bytes"], f"{role}.tile.offset")
                size = N_TILE * K_TILE * 2
                if (
                    tile["tile_index"] != tile_index
                    or tile["n_start"] != n_start
                    or tile["k_start"] != k_start
                    or tile["n_count"] != N_TILE
                    or tile["k_count"] != K_TILE
                    or tile["size_bytes"] != size
                    or offset % capability.hbm.burst_bytes
                    or tile["address"] != capability.hbm.base_address + offset
                    or offset + size > len(image)
                ):
                    raise ProductionConnectedLayerSimulationError(
                        f"HBM projection tile geometry differs for {role}[{tile_index}]"
                    )
                payload = image[offset : offset + size]
                if tile["payload_sha256"] != hashlib.sha256(payload).hexdigest():
                    raise ProductionConnectedLayerSimulationError(
                        f"HBM projection tile hash differs for {role}[{tile_index}]"
                    )
                intervals.append((offset, offset + size, f"{role}[{tile_index}]"))
                tile_index += 1

    intervals.sort()
    cursor = 0
    for start, end, label in intervals:
        if start < cursor:
            raise ProductionConnectedLayerSimulationError(
                f"HBM region {label!r} overlaps another region"
            )
        if any(image[cursor:start]):
            raise ProductionConnectedLayerSimulationError(
                "HBM alignment padding is nonzero"
            )
        cursor = end
    if any(image[cursor:]):
        raise ProductionConnectedLayerSimulationError("HBM trailing padding is nonzero")
    return direct, projections


def _append_projection_commands(
    commands: list[ProductionCommand],
    projection: Mapping[str, Any],
    sram: Mapping[str, Mapping[str, Any]],
) -> None:
    source_shape = projection["source"]["shape"]
    for tile in projection["tiles"]:
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=projection["kernel_index"],
                source0=tile["address"],
                destination=sram["weight_tile"]["address"],
                size0=tile["size_bytes"],
            )
        )
        flags = 0
        if tile["k_start"] == 0:
            flags |= MATMUL_INIT
        if tile["k_start"] + tile["k_count"] == source_shape[1]:
            flags |= MATMUL_FINAL
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.MATMUL_BF16_TILE,
                engine=Engine.TENSOR,
                flags=flags,
                kernel_index=projection["kernel_index"],
                source0=sram[projection["input_region"]]["address"]
                + tile["k_start"] * 2,
                source1=sram["weight_tile"]["address"],
                destination=sram["accumulator_tile"]["address"],
                auxiliary=sram[projection["output_region"]]["address"]
                + tile["n_start"] * 2,
                size0=ROWS,
                size1=tile["n_count"],
                size2=tile["k_count"],
            )
        )


def _expected_commands(
    direct: Mapping[str, Mapping[str, Any]],
    projections: Mapping[str, Mapping[str, Any]],
    sram: Mapping[str, Mapping[str, Any]],
) -> tuple[ProductionCommand, ...]:
    commands = [
        ProductionCommand(
            0,
            Opcode.DMA_HBM_INDEXED_TO_SRAM,
            Engine.DMA,
            kernel_index=0,
            source0=direct["embedding_rows"]["address"],
            source1=sram["runtime_ids"]["address"],
            destination=sram["hidden_0"]["address"],
            auxiliary=0,
            size0=HIDDEN_WIDTH * 2,
            size1=HIDDEN_WIDTH * 2,
            size2=1,
            size3=4,
        ),
        ProductionCommand(
            1,
            Opcode.DMA_HBM_TO_SRAM,
            Engine.DMA,
            kernel_index=1,
            source0=direct["input_norm_weight"]["address"],
            destination=sram["input_norm_weight"]["address"],
            size0=HIDDEN_WIDTH * 2,
        ),
        ProductionCommand(
            2,
            Opcode.RMSNORM_BF16,
            Engine.VECTOR,
            kernel_index=1,
            source0=sram["hidden_0"]["address"],
            source1=sram["input_norm_weight"]["address"],
            destination=sram["attention_norm"]["address"],
            size0=ROWS,
            size1=HIDDEN_WIDTH,
            size2=EPSILON_CODE,
        ),
    ]
    for role in ("q", "k", "v"):
        _append_projection_commands(commands, projections[role], sram)
    for kernel, role in ((5, "q"), (6, "k")):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=kernel,
                source0=direct[f"{role}_norm_weight"]["address"],
                destination=sram[f"{role}_norm_weight"]["address"],
                size0=HEAD_DIM * 2,
            )
        )
    for kernel, role, rows in ((5, "q", QUERY_HEADS), (6, "k", KEY_VALUE_HEADS)):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.RMSNORM_BF16,
                Engine.VECTOR,
                kernel_index=kernel,
                source0=sram[f"{role}_raw"]["address"],
                source1=sram[f"{role}_norm_weight"]["address"],
                destination=sram[f"{role}_norm"]["address"],
                size0=rows,
                size1=HEAD_DIM,
                size2=EPSILON_CODE,
            )
        )
    commands.extend(
        (
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_INDEXED_TO_SRAM,
                Engine.DMA,
                kernel_index=7,
                source0=direct["rope_coefficient_table"]["address"],
                source1=sram["runtime_ids"]["address"] + 4,
                destination=sram["rope_coefficients"]["address"],
                size0=2 * HEAD_DIM * 2,
                size1=2 * HEAD_DIM * 2,
                size2=CONTEXT_CAPACITY,
                size3=4,
            ),
            ProductionCommand(
                len(commands) + 1,
                Opcode.ROPE_BF16,
                Engine.VECTOR,
                kernel_index=7,
                source0=sram["q_norm"]["address"],
                source1=sram["k_norm"]["address"],
                destination=sram["q_rotary"]["address"],
                auxiliary=sram["k_rotary"]["address"],
                size0=QUERY_HEADS,
                size1=KEY_VALUE_HEADS,
                size2=HEAD_DIM,
                size3=sram["rope_coefficients"]["address"],
            ),
            ProductionCommand(
                len(commands) + 2,
                Opcode.KV_PREPARE_BF16,
                Engine.STATE,
                kernel_index=8,
                source0=sram["k_rotary"]["address"],
                source1=sram["v"]["address"],
                destination=direct["key_state"]["address"],
                auxiliary=direct["value_state"]["address"],
                size0=PREPARED_LENGTH,
                size1=KEY_VALUE_HEADS,
                size2=HEAD_DIM,
            ),
            ProductionCommand(
                len(commands) + 3,
                Opcode.GQA_ATTENTION_BF16,
                Engine.VECTOR,
                kernel_index=9,
                source0=sram["q_rotary"]["address"],
                source1=direct["key_state"]["address"],
                destination=sram["attention"]["address"],
                auxiliary=direct["value_state"]["address"],
                size0=PREPARED_LENGTH,
                size1=QUERY_HEADS,
                size2=KEY_VALUE_HEADS,
                size3=HEAD_DIM,
            ),
        )
    )
    _append_projection_commands(commands, projections["attention_output"], sram)
    commands.extend(
        (
            ProductionCommand(
                len(commands),
                Opcode.ADD_BF16,
                Engine.VECTOR,
                kernel_index=11,
                source0=sram["hidden_0"]["address"],
                source1=sram["attention_projected"]["address"],
                destination=sram["post_attention"]["address"],
                size0=ROWS,
                size1=HIDDEN_WIDTH,
            ),
            ProductionCommand(
                len(commands) + 1,
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=12,
                source0=direct["post_attention_norm_weight"]["address"],
                destination=sram["post_attention_norm_weight"]["address"],
                size0=HIDDEN_WIDTH * 2,
            ),
            ProductionCommand(
                len(commands) + 2,
                Opcode.RMSNORM_BF16,
                Engine.VECTOR,
                kernel_index=12,
                source0=sram["post_attention"]["address"],
                source1=sram["post_attention_norm_weight"]["address"],
                destination=sram["mlp_norm"]["address"],
                size0=ROWS,
                size1=HIDDEN_WIDTH,
                size2=EPSILON_CODE,
            ),
        )
    )
    for role in ("gate", "up"):
        _append_projection_commands(commands, projections[role], sram)
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.SILU_MUL_BF16,
            Engine.VECTOR,
            kernel_index=15,
            source0=sram["gate"]["address"],
            source1=sram["up"]["address"],
            destination=sram["gated_mlp"]["address"],
            size0=ROWS,
            size1=INTERMEDIATE_WIDTH,
        )
    )
    _append_projection_commands(commands, projections["down"], sram)
    commands.extend(
        (
            ProductionCommand(
                len(commands),
                Opcode.ADD_BF16,
                Engine.VECTOR,
                kernel_index=17,
                source0=sram["post_attention"]["address"],
                source1=sram["down"]["address"],
                destination=sram["hidden_1"]["address"],
                size0=ROWS,
                size1=HIDDEN_WIDTH,
            ),
            ProductionCommand(
                len(commands) + 1,
                Opcode.STATE_COMMIT,
                Engine.STATE,
                kernel_index=NO_KERNEL,
                source0=direct["state_metadata"]["address"],
                source1=direct["transaction_descriptor"]["address"],
                size0=CONTEXT_CAPACITY,
                size1=1,
            ),
            ProductionCommand(
                len(commands) + 2,
                Opcode.COMPLETE,
                Engine.CONTROL,
            ),
        )
    )
    if len(commands) != 23570:
        raise ProductionConnectedLayerSimulationError(
            "reconstructed command count differs"
        )
    return tuple(commands)


def _physical_plan(
    root: Path,
    manifest: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    bytes,
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    tuple[ProductionCommand, ...],
]:
    plan = _load_canonical(root / PHYSICAL_PLAN_PATH, "physical plan")
    _identity(plan, "physical_plan_id", "physical plan")
    _keys(
        plan,
        {
            "capability_id",
            "expected_counters",
            "graph_id",
            "hbm",
            "numeric_contracts",
            "physical_plan_id",
            "problem",
            "program",
            "qualification_bundle_id",
            "schema",
            "source_operation_ids",
            "sram",
        },
        set(),
        "physical plan",
    )
    if (
        plan["schema"] != PHYSICAL_PLAN_SCHEMA
        or plan["physical_plan_id"] != manifest["physical_plan_id"]
        or plan["capability_id"] != capability.capability_id
        or plan["graph_id"] != manifest["graph_id"]
        or plan["qualification_bundle_id"] != manifest["qualification_bundle_id"]
        or plan["source_operation_ids"] != SOURCE_OPERATION_IDS
        or plan["numeric_contracts"] != NUMERIC_CONTRACTS
        or plan["problem"] != _expected_problem()
        or plan["sram"] != _expected_sram(capability)
    ):
        raise ProductionConnectedLayerSimulationError("physical-plan contract differs")

    counters = plan["expected_counters"]
    if (
        not isinstance(counters, dict)
        or set(counters) != set(COUNTER_NAMES)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in counters.values()
        )
        or counters["command_count"] != 23570
        or counters["dma_command_count"] != 11782
        or counters["direct_dma_command_count"] != 11780
        or counters["indexed_dma_command_count"] != 2
        or counters["matmul_command_count"] != 11776
        or counters["state_commit_command_count"] != 1
    ):
        raise ProductionConnectedLayerSimulationError("physical-plan counters differ")

    try:
        image = (root / HBM_IMAGE_PATH).read_bytes()
    except OSError as exc:
        raise ProductionConnectedLayerSimulationError(
            f"cannot load connected-layer HBM image: {exc}"
        ) from exc
    direct, projections = _validate_hbm(plan["hbm"], image, capability)
    sram = _records_by_id(plan["sram"]["regions"], "SRAM regions")

    try:
        command_payload = (root / COMMAND_PATH).read_bytes()
        commands = decode(command_payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionConnectedLayerSimulationError(
            f"cannot load connected-layer command program: {exc}"
        ) from exc
    program = plan["program"]
    expected_program = {
        "command_count": len(commands),
        "path": COMMAND_PATH,
        "sha256": hashlib.sha256(command_payload).hexdigest(),
        "size_bytes": len(command_payload),
    }
    if (
        program != expected_program
        or command_abi(command_payload) != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
        or len(commands) != 23570
        or commands != _expected_commands(direct, projections, sram)
    ):
        raise ProductionConnectedLayerSimulationError("command program differs")
    try:
        disassembly = (root / "program/commands.disasm").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProductionConnectedLayerSimulationError(
            f"cannot load command disassembly: {exc}"
        ) from exc
    if disassembly != disassemble(commands, abi_minor=ELEMENTWISE_ABI_MINOR):
        raise ProductionConnectedLayerSimulationError("command disassembly differs")
    return plan, sram, image, direct, projections, commands


def _independent_check(
    root: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(root / "checks/independent_check.json", "independent check")
    _identity(value, "check_id", "independent check")
    _keys(
        value,
        {
            "capability_id",
            "check_id",
            "command_count",
            "command_program_sha256",
            "expected_counters",
            "expected_intermediate_payload_sha256",
            "expected_output_payload_sha256",
            "expected_saturated_element_count",
            "expected_state_sha256",
            "graph_id",
            "hbm_image_sha256",
            "kernel_ir_id",
            "no_retained_activation_regions",
            "physical_plan_id",
            "qualification_bundle_id",
            "schema",
            "source_lock_id",
            "status",
        },
        set(),
        "independent check",
    )
    if (
        value["schema"] != CHECK_SCHEMA
        or value["status"] != "pass"
        or value["check_id"] != manifest["independent_check_id"]
        or value["capability_id"] != manifest["capability_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["kernel_ir_id"] != kernel_ir["kernel_ir_id"]
        or value["physical_plan_id"] != plan["physical_plan_id"]
        or value["qualification_bundle_id"] != manifest["qualification_bundle_id"]
        or value["source_lock_id"] != manifest["source_lock_id"]
        or value["command_count"] != plan["program"]["command_count"]
        or value["command_program_sha256"] != plan["program"]["sha256"]
        or value["hbm_image_sha256"] != plan["hbm"]["image"]["sha256"]
        or value["expected_counters"] != plan["expected_counters"]
        or value["no_retained_activation_regions"] is not True
    ):
        raise ProductionConnectedLayerSimulationError(
            "independent-check binding differs"
        )
    return value


def _expectations(
    root: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    check: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(
        root / "execution_expectations.json", "execution expectations"
    )
    _identity(value, "expectations_id", "execution expectations")
    _keys(
        value,
        {
            "check_id",
            "counters",
            "expectations_id",
            "intermediate_payload_sha256",
            "output_payload_sha256",
            "qualification_bundle_id",
            "saturated_element_count",
            "schema",
            "state_sha256",
        },
        set(),
        "execution expectations",
    )
    if (
        value["schema"] != EXPECTATIONS_SCHEMA
        or value["check_id"] != manifest["independent_check_id"]
        or value["qualification_bundle_id"] != manifest["qualification_bundle_id"]
        or value["counters"] != plan["expected_counters"]
        or value["intermediate_payload_sha256"]
        != check["expected_intermediate_payload_sha256"]
        or value["output_payload_sha256"] != check["expected_output_payload_sha256"]
        or value["saturated_element_count"] != check["expected_saturated_element_count"]
        or value["state_sha256"] != check["expected_state_sha256"]
        or set(value["intermediate_payload_sha256"]) != set(INTERMEDIATE_ROLES)
        or set(value["output_payload_sha256"]) != {"hidden_1"}
    ):
        raise ProductionConnectedLayerSimulationError("execution expectations differ")
    for role, digest in value["intermediate_payload_sha256"].items():
        _required_sha(digest, f"expected intermediate {role}")
    _required_sha(value["output_payload_sha256"]["hidden_1"], "expected hidden_1")
    _required_sha(value["state_sha256"], "expected state")

    expected_saturation_shape = {
        "attention": {"mask", "output", "probability", "scaling", "score"},
        "projection": {spec[0] for spec in PROJECTION_SPECS},
        "rmsnorm": {"attention_norm", "q_norm", "k_norm", "mlp_norm"},
        "rope": {"addition", "multiplication"},
        "vector": {
            "attention_residual",
            "final_residual",
            "silu_activation",
            "silu_output",
        },
    }
    saturation = value["saturated_element_count"]
    if not isinstance(saturation, dict) or set(saturation) != set(
        expected_saturation_shape
    ):
        raise ProductionConnectedLayerSimulationError(
            "saturation expectation groups differ"
        )
    for group, roles in expected_saturation_shape.items():
        records = saturation[group]
        if not isinstance(records, dict) or set(records) != roles:
            raise ProductionConnectedLayerSimulationError(
                f"saturation expectation roles differ for {group!r}"
            )
        for role, count in records.items():
            if group == "rmsnorm":
                if (
                    not isinstance(count, dict)
                    or set(count) != {"normalized", "output"}
                    or any(
                        isinstance(item, bool) or not isinstance(item, int) or item < 0
                        for item in count.values()
                    )
                ):
                    raise ProductionConnectedLayerSimulationError(
                        f"RMSNorm saturation expectation differs for {role!r}"
                    )
            elif isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ProductionConnectedLayerSimulationError(
                    f"saturation expectation differs for {group}.{role}"
                )
    return value


def _request(
    path: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(path, "execution request")
    _identity(value, "request_id", "execution request")
    _keys(
        value,
        {
            "expected_generation",
            "graph_id",
            "position_id",
            "qualification_bundle_id",
            "request_id",
            "schema",
            "source_operation_ids",
            "span_tokens",
            "state_position_start",
            "token_id",
            "transaction_id",
        },
        set(),
        "execution request",
    )
    token_id = _required_int(value["token_id"], "request.token_id", maximum=0xFFFFFFFF)
    position_id = _required_int(
        value["position_id"], "request.position_id", maximum=CONTEXT_CAPACITY - 1
    )
    if (
        value["schema"] != REQUEST_SCHEMA
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_bundle_id"] != manifest["qualification_bundle_id"]
        or value["source_operation_ids"] != SOURCE_OPERATION_IDS
        or value["expected_generation"] != BASE_GENERATION
        or value["state_position_start"] != COMMITTED_LENGTH
        or value["span_tokens"] != PREPARED_LENGTH
        or value["transaction_id"] != TRANSACTION_ID
        or not plan["problem"]["resident_embedding_base_token"]
        <= token_id
        < plan["problem"]["resident_embedding_base_token"]
        + plan["problem"]["resident_embedding_rows"]
        or not 0 <= position_id < plan["problem"]["rope_positions"]
    ):
        raise ProductionConnectedLayerSimulationError(
            "execution request contract differs"
        )
    return value


class ProductionConnectedLayerSimulator:
    """Immutable deployment whose commands causally execute one Qwen layer."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: dict[str, Any],
        source_lock: dict[str, Any],
        capability: ProductionCapability,
        kernel_ir: dict[str, Any],
        plan: dict[str, Any],
        sram_records: dict[str, dict[str, Any]],
        image: bytes,
        direct: dict[str, dict[str, Any]],
        projections: dict[str, dict[str, Any]],
        commands: tuple[ProductionCommand, ...],
        expectations: dict[str, Any],
        known_request: dict[str, Any],
    ) -> None:
        self._root = root
        self._manifest = manifest
        self._source_lock = source_lock
        self._capability = capability
        self._kernel_ir = kernel_ir
        self._plan = plan
        self._sram_records = sram_records
        self._image = image
        self._direct = direct
        self._projections = projections
        self._commands = commands
        self._expectations = expectations
        self._known_request = known_request

    @classmethod
    def load(cls, root: Path) -> "ProductionConnectedLayerSimulator":
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionConnectedLayerSimulationError(
                f"deployment directory does not exist: {deployment}"
            )
        manifest = _manifest(deployment)
        source_lock, graph = _source_lock(deployment, manifest)
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionConnectedLayerSimulationError(
                f"capability admission failed: {exc}"
            ) from exc
        vector = capability.vector_engine
        state = capability.state_engine
        required_contracts = set(NUMERIC_CONTRACTS) - {"bf16_payload_lookup_v1"}
        if (
            capability.capability_id != manifest["capability_id"]
            or (capability.command_abi_major, capability.command_abi_minor)
            != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
            or not required_contracts <= set(capability.qualified_numeric_contracts)
            or not {"bf16_tensor", "transactional_state", "vector_fp32"}
            <= set(capability.qualified_execution_modes)
            or capability.hbm.external_at_130nm_boundary is not True
            or capability.tensor_engine.max_m < ROWS
            or capability.tensor_engine.max_n < N_TILE
            or capability.tensor_engine.max_k < K_TILE
            or vector is None
            or vector.max_rows < QUERY_HEADS
            or vector.max_width < INTERMEDIATE_WIDTH
            or vector.max_rope_positions != CONTEXT_CAPACITY
            or vector.max_attention_context_tokens != CONTEXT_CAPACITY
            or vector.max_query_heads != QUERY_HEADS
            or vector.max_key_value_heads != KEY_VALUE_HEADS
            or vector.rope_head_dim != HEAD_DIM
            or vector.attention_head_dim != HEAD_DIM
            or state is None
            or state.max_resources_per_transaction < 1
            or state.max_inflight_transactions < 1
        ):
            raise ProductionConnectedLayerSimulationError(
                "capability identity or connected-layer bounds differ"
            )
        kernel_ir = _kernel_ir(deployment, manifest, graph)
        plan, sram, image, direct, projections, commands = _physical_plan(
            deployment, manifest, capability
        )
        check = _independent_check(deployment, manifest, plan, kernel_ir)
        expectations = _expectations(deployment, manifest, plan, check)
        known_request = _request(deployment / REQUEST_PATH, manifest, plan)
        return cls(
            root=deployment,
            manifest=manifest,
            source_lock=source_lock,
            capability=capability,
            kernel_ir=kernel_ir,
            plan=plan,
            sram_records=sram,
            image=image,
            direct=direct,
            projections=projections,
            commands=commands,
            expectations=expectations,
            known_request=known_request,
        )

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        """Execute every decoded command with fresh mutable SRAM and KV state."""

        request = (
            self._known_request
            if request_path is None
            else _request(Path(request_path).resolve(), self._manifest, self._plan)
        )
        regions = {
            role: _SRAMRegion.create(record)
            for role, record in self._sram_records.items()
        }
        runtime_payload = struct.pack(
            "<II", request["token_id"], request["position_id"]
        )
        regions["runtime_ids"].write(regions["runtime_ids"].address, runtime_payload)
        hbm = bytearray(self._image)
        hbm_base = self._capability.hbm.base_address
        counters = {name: 0 for name in COUNTER_NAMES}
        counters["runtime_request_sram_bytes_written"] = len(runtime_payload)
        trace: list[dict[str, Any]] = []
        intermediate_hashes: dict[str, str] = {}
        saturation: dict[str, Any] = {
            "attention": {
                "mask": 0,
                "output": 0,
                "probability": 0,
                "scaling": 0,
                "score": 0,
            },
            "projection": {role: 0 for role, *_ in PROJECTION_SPECS},
            "rmsnorm": {
                role: {"normalized": 0, "output": 0}
                for role in ("attention_norm", "q_norm", "k_norm", "mlp_norm")
            },
            "rope": {"addition": 0, "multiplication": 0},
            "vector": {
                "attention_residual": 0,
                "final_residual": 0,
                "silu_activation": 0,
                "silu_output": 0,
            },
        }
        rmsnorm_diagnostics: dict[str, dict[str, Any]] = {}
        rope_diagnostics: dict[str, Any] | None = None
        attention_diagnostics: dict[str, Any] | None = None
        loaded_static: set[str] = set()
        projection_progress = {role: 0 for role in self._projections}
        projection_by_kernel = {
            projection["kernel_index"]: (role, projection)
            for role, projection in self._projections.items()
        }
        tile_by_address: dict[int, tuple[str, Mapping[str, Any]]] = {}
        for role, projection in self._projections.items():
            for tile in projection["tiles"]:
                address = tile["address"]
                if address in tile_by_address:
                    raise ProductionConnectedLayerSimulationError(
                        "two projection tiles share an HBM address"
                    )
                tile_by_address[address] = (role, tile)
        direct_by_address = {
            record["address"]: role for role, record in self._direct.items()
        }
        fresh_weight: tuple[str, Mapping[str, Any]] | None = None
        snapshot: KVSnapshot | None = None
        prepared: PreparedKV | None = None
        attention_result: Any = None
        committed: KVSnapshot | None = None
        hidden_output: bytes | None = None
        completed = False

        def capture(role: str, payload: bytes) -> str:
            if role in intermediate_hashes:
                raise ProductionConnectedLayerSimulationError(
                    f"intermediate {role!r} was produced more than once"
                )
            digest = hashlib.sha256(payload).hexdigest()
            intermediate_hashes[role] = digest
            return digest

        def hbm_offset(address: int, size: int) -> int:
            offset = address - hbm_base
            if size < 0 or offset < 0 or offset + size > len(hbm):
                raise ProductionConnectedLayerSimulationError(
                    "command HBM access escapes the deployment image"
                )
            return offset

        def hbm_read(address: int, size: int) -> bytes:
            offset = hbm_offset(address, size)
            return bytes(hbm[offset : offset + size])

        def state_metadata() -> tuple[int, int, int, int, int]:
            record = self._direct["state_metadata"]
            payload = hbm_read(record["address"], STATE_METADATA.size)
            (
                magic,
                generation,
                length,
                capacity,
                key_base,
                value_base,
                resource_index,
                reserved,
            ) = STATE_METADATA.unpack(payload)
            if (
                magic != STATE_MAGIC
                or resource_index != 0
                or reserved != bytes(8)
                or capacity != CONTEXT_CAPACITY
                or key_base != self._direct["key_state"]["address"]
                or value_base != self._direct["value_state"]["address"]
            ):
                raise ProductionConnectedLayerSimulationError(
                    "state metadata encoding differs"
                )
            return generation, length, capacity, key_base, value_base

        def transaction_descriptor() -> tuple[int, int, int, int, int, int]:
            record = self._direct["transaction_descriptor"]
            payload = hbm_read(record["address"], TRANSACTION_DESCRIPTOR.size)
            (
                magic,
                transaction_id,
                expected_generation,
                position,
                span,
                resources_count,
                metadata_address,
                reserved,
            ) = TRANSACTION_DESCRIPTOR.unpack(payload)
            if magic != TRANSACTION_MAGIC or reserved != bytes(8):
                raise ProductionConnectedLayerSimulationError(
                    "transaction descriptor encoding differs"
                )
            return (
                transaction_id,
                expected_generation,
                position,
                span,
                resources_count,
                metadata_address,
            )

        try:
            for command in self._commands:
                if completed:
                    raise ProductionConnectedLayerSimulationError(
                        "command appears after COMPLETE"
                    )
                counters["command_count"] += 1
                event: dict[str, Any] = {
                    "engine": command.engine.name,
                    "index": command.index,
                    "kernel_index": command.kernel_index,
                    "opcode": command.opcode.name,
                }

                if command.opcode in {
                    Opcode.DMA_HBM_TO_SRAM,
                    Opcode.DMA_HBM_INDEXED_TO_SRAM,
                }:
                    if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                        source_address = command.source0
                        counters["direct_dma_command_count"] += 1
                        logical_index: int | None = None
                    else:
                        index_region = _region_for(
                            regions, command.source1, command.size3
                        )
                        index_payload = index_region.read(
                            command.source1, command.size3
                        )
                        logical_index = struct.unpack("<I", index_payload)[0]
                        relative_index = logical_index - command.auxiliary
                        if (
                            relative_index < 0
                            or relative_index >= command.size2
                            or command.size1 < command.size0
                        ):
                            raise ProductionConnectedLayerSimulationError(
                                "indexed DMA index or stride is illegal"
                            )
                        source_address = (
                            command.source0 + relative_index * command.size1
                        )
                        counters["indexed_dma_command_count"] += 1
                    if (
                        source_address % self._capability.hbm.burst_bytes
                        or command.size0 % self._capability.hbm.burst_bytes
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "DMA HBM alignment differs"
                        )
                    payload = hbm_read(source_address, command.size0)
                    destination = _region_for(
                        regions, command.destination, command.size0
                    )
                    tile_binding = tile_by_address.get(source_address)
                    if destination.region_id == "weight_tile":
                        if fresh_weight is not None or tile_binding is None:
                            raise ProductionConnectedLayerSimulationError(
                                "weight DMA overwrites an unconsumed or unknown tile"
                            )
                        if (
                            self._projections[tile_binding[0]]["kernel_index"]
                            != command.kernel_index
                        ):
                            raise ProductionConnectedLayerSimulationError(
                                "weight DMA kernel binding differs"
                            )
                        fresh_weight = tile_binding
                        event.update(
                            {
                                "k_start": tile_binding[1]["k_start"],
                                "n_start": tile_binding[1]["n_start"],
                                "projection": tile_binding[0],
                                "tile_index": tile_binding[1]["tile_index"],
                            }
                        )
                    else:
                        if (
                            tile_binding is not None
                            or destination.region_id in loaded_static
                        ):
                            raise ProductionConnectedLayerSimulationError(
                                "static DMA is duplicated or consumes a weight tile"
                            )
                        loaded_static.add(destination.region_id)
                        if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                            role = direct_by_address.get(source_address)
                            if role != destination.region_id:
                                raise ProductionConnectedLayerSimulationError(
                                    "direct DMA HBM and SRAM roles differ"
                                )
                        elif command.kernel_index == 0:
                            role = "embedding_rows"
                            if destination.region_id != "hidden_0":
                                raise ProductionConnectedLayerSimulationError(
                                    "embedding DMA destination differs"
                                )
                        elif command.kernel_index == 7:
                            role = "rope_coefficient_table"
                            if destination.region_id != "rope_coefficients":
                                raise ProductionConnectedLayerSimulationError(
                                    "RoPE coefficient DMA destination differs"
                                )
                        else:
                            raise ProductionConnectedLayerSimulationError(
                                "indexed DMA kernel differs"
                            )
                        event["role"] = role
                    destination.write(command.destination, payload)
                    counters["dma_command_count"] += 1
                    counters["dma_sram_bytes_written"] += len(payload)
                    counters["hbm_useful_bytes_read"] += len(payload)
                    counters["hbm_transferred_bytes_read"] += align_up(
                        len(payload), self._capability.hbm.burst_bytes
                    )
                    event["payload_sha256"] = hashlib.sha256(payload).hexdigest()
                    if logical_index is not None:
                        event["logical_index"] = logical_index
                    if destination.region_id == "hidden_0":
                        event["output_payload_sha256"] = capture("hidden_0", payload)

                elif command.opcode == Opcode.MATMUL_BF16_TILE:
                    binding = projection_by_kernel.get(command.kernel_index)
                    if binding is None or fresh_weight is None:
                        raise ProductionConnectedLayerSimulationError(
                            "matrix command lacks a fresh causal weight DMA"
                        )
                    role, projection = binding
                    dma_role, tile = fresh_weight
                    progress = projection_progress[role]
                    if (
                        dma_role != role
                        or progress >= len(projection["tiles"])
                        or projection["tiles"][progress] != tile
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "matrix projection or tile order differs"
                        )
                    input_region = regions[projection["input_region"]]
                    weight_region = regions["weight_tile"]
                    accumulator_region = regions["accumulator_tile"]
                    output_region = regions[projection["output_region"]]
                    if (
                        command.source0 != input_region.address + tile["k_start"] * 2
                        or command.source1 != weight_region.address
                        or command.destination != accumulator_region.address
                        or command.auxiliary
                        != output_region.address + tile["n_start"] * 2
                        or command.size0 != ROWS
                        or command.size1 != tile["n_count"]
                        or command.size2 != tile["k_count"]
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "matrix SRAM address or shape differs"
                        )
                    initialized = bool(command.flags & MATMUL_INIT)
                    final = bool(command.flags & MATMUL_FINAL)
                    if initialized != (tile["k_start"] == 0) or final != (
                        tile["k_start"] + tile["k_count"]
                        == projection["source"]["shape"][1]
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "matrix reduction flags differ"
                        )
                    input_payload = input_region.read(
                        command.source0, command.size0 * command.size2 * 2
                    )
                    weight_payload = weight_region.read(
                        command.source1, command.size1 * command.size2 * 2
                    )
                    input_codes = np.frombuffer(input_payload, dtype="<u2").reshape(
                        command.size0, command.size2
                    )
                    weight_codes = np.frombuffer(weight_payload, dtype="<u2").reshape(
                        command.size1, command.size2
                    )
                    accumulator_codes = None
                    accumulator_size = command.size0 * command.size1 * 4
                    if not initialized:
                        accumulator_payload = accumulator_region.read(
                            command.destination, accumulator_size
                        )
                        accumulator_codes = np.frombuffer(
                            accumulator_payload, dtype="<u4"
                        ).reshape(command.size0, command.size1)
                        counters["accumulator_sram_bytes_read"] += accumulator_size
                    accumulated = accumulate_bf16_tile_fp32(
                        input_codes, weight_codes, accumulator_codes
                    )
                    accumulator_payload = _u32_payload(accumulated.values)
                    accumulator_region.write(command.destination, accumulator_payload)
                    counters["accumulator_sram_bytes_written"] += accumulator_size
                    counters["matmul_command_count"] += 1
                    scalar_operations = command.size0 * command.size1 * command.size2
                    if role in {"q", "k", "v"}:
                        counters["matmul_input_sram_bytes_read"] += len(input_payload)
                        counters["matmul_weight_sram_bytes_read"] += len(weight_payload)
                        counters["scalar_multiplications"] += scalar_operations
                        counters["scalar_accumulation_additions"] += scalar_operations
                    else:
                        counters["matrix_input_sram_bytes_read"] += len(input_payload)
                        counters["weight_sram_bytes_read"] += len(weight_payload)
                        counters["projection_multiplications"] += scalar_operations
                        counters["projection_accumulation_additions"] += (
                            scalar_operations
                        )
                    event.update(
                        {
                            "accumulator_sha256": hashlib.sha256(
                                accumulator_payload
                            ).hexdigest(),
                            "final": final,
                            "k_start": tile["k_start"],
                            "n_start": tile["n_start"],
                            "projection": role,
                            "tile_index": tile["tile_index"],
                        }
                    )
                    if final:
                        finalized = finalize_bf16_accumulator(accumulated.values)
                        payload = _bf16_payload(finalized.values)
                        output_region.write(command.auxiliary, payload)
                        saturation["projection"][role] += (
                            finalized.output_saturated_element_count
                        )
                        counter = (
                            "matmul_output_sram_bytes_written"
                            if role in {"q", "k", "v"}
                            else "matrix_output_sram_bytes_written"
                        )
                        counters[counter] += len(payload)
                        if progress + 1 == len(projection["tiles"]):
                            complete_payload = output_region.read(
                                output_region.address, output_region.logical_bytes
                            )
                            event["output_payload_sha256"] = capture(
                                projection["output_region"], complete_payload
                            )
                    projection_progress[role] += 1
                    fresh_weight = None

                elif command.opcode == Opcode.RMSNORM_BF16:
                    if fresh_weight is not None:
                        raise ProductionConnectedLayerSimulationError(
                            "RMSNorm bypasses a pending weight DMA"
                        )
                    specs = {
                        1: (
                            "hidden_0",
                            "input_norm_weight",
                            "attention_norm",
                            ROWS,
                            HIDDEN_WIDTH,
                        ),
                        5: ("q_raw", "q_norm_weight", "q_norm", QUERY_HEADS, HEAD_DIM),
                        6: (
                            "k_raw",
                            "k_norm_weight",
                            "k_norm",
                            KEY_VALUE_HEADS,
                            HEAD_DIM,
                        ),
                        12: (
                            "post_attention",
                            "post_attention_norm_weight",
                            "mlp_norm",
                            ROWS,
                            HIDDEN_WIDTH,
                        ),
                    }
                    spec = specs.get(command.kernel_index)
                    if spec is None:
                        raise ProductionConnectedLayerSimulationError(
                            "RMSNorm kernel index differs"
                        )
                    source_role, weight_role, output_role, rows, width = spec
                    if output_role in rmsnorm_diagnostics:
                        raise ProductionConnectedLayerSimulationError(
                            "RMSNorm output is produced more than once"
                        )
                    source = regions[source_role]
                    weight = regions[weight_role]
                    output = regions[output_role]
                    if (
                        command.source0 != source.address
                        or command.source1 != weight.address
                        or command.destination != output.address
                        or command.size0 != rows
                        or command.size1 != width
                        or command.size2 != EPSILON_CODE
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "RMSNorm address or shape differs"
                        )
                    input_size = rows * width * 2
                    weight_size = width * 2
                    input_payload = source.read(command.source0, input_size)
                    weight_payload = weight.read(command.source1, weight_size)
                    inputs = np.frombuffer(input_payload, dtype="<u2").reshape(
                        rows, width
                    )
                    weights = np.frombuffer(weight_payload, dtype="<u2")
                    result = rms_norm_bf16(inputs, weights, epsilon_code=command.size2)
                    payload = _bf16_payload(result.values)
                    output.write(command.destination, payload)
                    counters["rmsnorm_command_count"] += 1
                    counters["rmsnorm_input_sram_bytes_read"] += input_size
                    counters["rmsnorm_weight_sram_bytes_read"] += weight_size
                    counters["rmsnorm_output_sram_bytes_written"] += len(payload)
                    elements = rows * width
                    counters["input_square_multiplications"] += elements
                    counters["reduction_additions"] += rows * (width - 1)
                    counters["mean_divisions"] += rows
                    counters["epsilon_additions"] += rows
                    counters["reciprocal_square_roots"] += rows
                    counters["normalization_multiplications"] += elements
                    counters["final_weight_multiplications"] += elements
                    saturation["rmsnorm"][output_role] = {
                        "normalized": result.normalized_saturated_element_count,
                        "output": result.output_saturated_element_count,
                    }
                    diagnostics = {
                        "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                            _u32_payload(result.inverse_rms_codes)
                        ).hexdigest(),
                        "mean_square_binary32_codes_sha256": hashlib.sha256(
                            _u32_payload(result.mean_square_codes)
                        ).hexdigest(),
                        "normalized_payload_sha256": hashlib.sha256(
                            _bf16_payload(result.normalized_values)
                        ).hexdigest(),
                    }
                    rmsnorm_diagnostics[output_role] = diagnostics
                    event.update(
                        {
                            "output": output_role,
                            "output_payload_sha256": capture(output_role, payload),
                            **diagnostics,
                        }
                    )

                elif command.opcode == Opcode.ROPE_BF16:
                    if fresh_weight is not None or rope_diagnostics is not None:
                        raise ProductionConnectedLayerSimulationError(
                            "RoPE is duplicated or bypasses a pending weight DMA"
                        )
                    query_payload = regions["q_norm"].read(command.source0, QUERY_BYTES)
                    key_payload = regions["k_norm"].read(command.source1, TOKEN_BYTES)
                    coefficient_payload = regions["rope_coefficients"].read(
                        command.size3, 2 * HEAD_DIM * 2
                    )
                    result = rope_bf16(
                        np.frombuffer(query_payload, dtype="<u2").reshape(
                            QUERY_HEADS, HEAD_DIM
                        ),
                        np.frombuffer(key_payload, dtype="<u2").reshape(
                            KEY_VALUE_HEADS, HEAD_DIM
                        ),
                        np.frombuffer(coefficient_payload, dtype="<u2"),
                    )
                    query_output = _bf16_payload(result.query_values)
                    key_output = _bf16_payload(result.key_values)
                    regions["q_rotary"].write(command.destination, query_output)
                    regions["k_rotary"].write(command.auxiliary, key_output)
                    elements = (QUERY_HEADS + KEY_VALUE_HEADS) * HEAD_DIM
                    counters["rope_command_count"] += 1
                    counters["rope_multiplications"] += 2 * elements
                    counters["rope_additions"] += elements
                    counters["rope_input_sram_bytes_read"] += (
                        len(query_payload) + len(key_payload) + len(coefficient_payload)
                    )
                    counters["rope_output_sram_bytes_written"] += len(
                        query_output
                    ) + len(key_output)
                    saturation["rope"] = {
                        "addition": result.addition_saturated_element_count,
                        "multiplication": result.multiplication_saturated_element_count,
                    }
                    rope_diagnostics = {
                        "coefficient_row_payload_sha256": hashlib.sha256(
                            coefficient_payload
                        ).hexdigest(),
                    }
                    event.update(
                        {
                            **rope_diagnostics,
                            "key_output_payload_sha256": capture(
                                "k_rotary", key_output
                            ),
                            "query_output_payload_sha256": capture(
                                "q_rotary", query_output
                            ),
                        }
                    )

                elif command.opcode == Opcode.KV_PREPARE_BF16:
                    if fresh_weight is not None or prepared is not None:
                        raise ProductionConnectedLayerSimulationError(
                            "KV prepare is duplicated or bypasses a pending weight DMA"
                        )
                    generation, length, capacity, key_base, value_base = (
                        state_metadata()
                    )
                    descriptor = transaction_descriptor()
                    if (
                        (generation, length, capacity)
                        != (
                            request["expected_generation"],
                            request["state_position_start"],
                            CONTEXT_CAPACITY,
                        )
                        or descriptor
                        != (
                            request["transaction_id"],
                            request["expected_generation"],
                            request["state_position_start"],
                            request["span_tokens"],
                            1,
                            self._direct["state_metadata"]["address"],
                        )
                        or command.destination != key_base
                        or command.auxiliary != value_base
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "KV prepare state or descriptor differs"
                        )
                    committed_keys = (
                        np.frombuffer(
                            hbm_read(key_base, length * TOKEN_BYTES), dtype="<u2"
                        )
                        .copy()
                        .reshape(length, KEY_VALUE_HEADS, HEAD_DIM)
                    )
                    committed_values = (
                        np.frombuffer(
                            hbm_read(value_base, length * TOKEN_BYTES), dtype="<u2"
                        )
                        .copy()
                        .reshape(length, KEY_VALUE_HEADS, HEAD_DIM)
                    )
                    current_keys = (
                        np.frombuffer(
                            regions["k_rotary"].read(command.source0, TOKEN_BYTES),
                            dtype="<u2",
                        )
                        .copy()
                        .reshape(PREPARED_LENGTH, KEY_VALUE_HEADS, HEAD_DIM)
                    )
                    current_values = (
                        np.frombuffer(
                            regions["v"].read(command.source1, TOKEN_BYTES), dtype="<u2"
                        )
                        .copy()
                        .reshape(PREPARED_LENGTH, KEY_VALUE_HEADS, HEAD_DIM)
                    )
                    snapshot = make_kv_snapshot(
                        resource_id=RESOURCE_ID,
                        generation=generation,
                        capacity=capacity,
                        key_values=committed_keys,
                        value_values=committed_values,
                    )
                    prepared = prepare_kv_append(
                        snapshot,
                        transaction_id=request["transaction_id"],
                        expected_generation=request["expected_generation"],
                        position_start=request["state_position_start"],
                        key_values=current_keys,
                        value_values=current_values,
                    )
                    metadata_before = hbm_read(
                        self._direct["state_metadata"]["address"], STATE_METADATA.size
                    )
                    key_offset = hbm_offset(
                        key_base + length * TOKEN_BYTES, TOKEN_BYTES
                    )
                    value_offset = hbm_offset(
                        value_base + length * TOKEN_BYTES, TOKEN_BYTES
                    )
                    hbm[key_offset : key_offset + TOKEN_BYTES] = _bf16_payload(
                        current_keys
                    )
                    hbm[value_offset : value_offset + TOKEN_BYTES] = _bf16_payload(
                        current_values
                    )
                    if (
                        hbm_read(
                            self._direct["state_metadata"]["address"],
                            STATE_METADATA.size,
                        )
                        != metadata_before
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "KV prepare published committed state metadata"
                        )
                    counters["kv_prepare_command_count"] += 1
                    counters["kv_prepare_sram_bytes_read"] += 2 * TOKEN_BYTES
                    counters["state_payload_bytes_written"] += 2 * TOKEN_BYTES
                    counters["state_metadata_bytes_read"] += 2 * STATE_METADATA.size
                    counters["hbm_useful_bytes_read"] += 2 * STATE_METADATA.size
                    counters["hbm_transferred_bytes_read"] += 2 * STATE_METADATA.size
                    counters["hbm_useful_bytes_written"] += 2 * TOKEN_BYTES
                    counters["hbm_transferred_bytes_written"] += 2 * TOKEN_BYTES
                    event.update(
                        {
                            "base_generation": snapshot.generation,
                            "position_start": prepared.position_start,
                            "transaction_private": True,
                        }
                    )

                elif command.opcode == Opcode.GQA_ATTENTION_BF16:
                    if (
                        fresh_weight is not None
                        or snapshot is None
                        or prepared is None
                        or attention_result is not None
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "attention lacks causal prepared state or is duplicated"
                        )
                    query_payload = regions["q_rotary"].read(
                        command.source0, QUERY_BYTES
                    )
                    query = (
                        np.frombuffer(query_payload, dtype="<u2")
                        .copy()
                        .reshape(PREPARED_LENGTH, QUERY_HEADS, HEAD_DIM)
                    )
                    attention_result = gqa_causal_attention_bf16(
                        query, snapshot, prepared
                    )
                    output_payload = _bf16_payload(attention_result.output_values)
                    probability_payload = _bf16_payload(
                        attention_result.probability_values
                    )
                    score_payload = _bf16_payload(attention_result.scaled_score_values)
                    regions["attention"].write(command.destination, output_payload)
                    counters["attention_command_count"] += 1
                    counters["attention_query_sram_bytes_read"] += QUERY_BYTES
                    counters["attention_output_sram_bytes_written"] += len(
                        output_payload
                    )
                    visible_bytes = (
                        (snapshot.length + prepared.length) * 2 * TOKEN_BYTES
                    )
                    counters["state_payload_bytes_read"] += visible_bytes
                    counters["hbm_useful_bytes_read"] += visible_bytes
                    counters["hbm_transferred_bytes_read"] += visible_bytes
                    for name, count in asdict(attention_result.accounting).items():
                        counters[name] += count
                    saturation["attention"] = {
                        "mask": attention_result.mask_saturated_element_count,
                        "output": attention_result.output_saturated_element_count,
                        "probability": attention_result.probability_saturated_element_count,
                        "scaling": attention_result.scaling_saturated_element_count,
                        "score": attention_result.score_saturated_element_count,
                    }
                    attention_diagnostics = {
                        "probability_payload_sha256": capture(
                            "probabilities", probability_payload
                        ),
                        "scaled_score_payload_sha256": capture(
                            "scaled_scores", score_payload
                        ),
                    }
                    event.update(
                        {
                            **attention_diagnostics,
                            "output_payload_sha256": capture(
                                "attention", output_payload
                            ),
                            "transaction_private": True,
                        }
                    )

                elif command.opcode == Opcode.ADD_BF16:
                    if fresh_weight is not None:
                        raise ProductionConnectedLayerSimulationError(
                            "residual add bypasses a pending weight DMA"
                        )
                    size = command.size0 * command.size1 * 2
                    left = _region_for(regions, command.source0, size)
                    right = _region_for(regions, command.source1, size)
                    output = _region_for(regions, command.destination, size)
                    result = bf16_add_rne(
                        np.frombuffer(
                            left.read(command.source0, size), dtype="<u2"
                        ).reshape(command.size0, command.size1),
                        np.frombuffer(
                            right.read(command.source1, size), dtype="<u2"
                        ).reshape(command.size0, command.size1),
                    )
                    payload = _bf16_payload(result.values)
                    output.write(command.destination, payload)
                    counters["add_command_count"] += 1
                    counters["add_input_sram_bytes_read"] += 2 * size
                    counters["add_output_sram_bytes_written"] += size
                    counters["residual_additions"] += command.size0 * command.size1
                    if (
                        command.kernel_index == 11
                        and output.region_id == "post_attention"
                    ):
                        saturation_role = "attention_residual"
                        digest = capture("post_attention", payload)
                    elif command.kernel_index == 17 and output.region_id == "hidden_1":
                        saturation_role = "final_residual"
                        if hidden_output is not None:
                            raise ProductionConnectedLayerSimulationError(
                                "hidden_1 is produced more than once"
                            )
                        hidden_output = payload
                        digest = hashlib.sha256(payload).hexdigest()
                    else:
                        raise ProductionConnectedLayerSimulationError(
                            "residual-add kernel or destination differs"
                        )
                    saturation["vector"][saturation_role] = (
                        result.output_saturated_element_count
                    )
                    event.update(
                        {"output": output.region_id, "output_payload_sha256": digest}
                    )

                elif command.opcode == Opcode.SILU_MUL_BF16:
                    if fresh_weight is not None:
                        raise ProductionConnectedLayerSimulationError(
                            "SiLU multiply bypasses a pending weight DMA"
                        )
                    size = command.size0 * command.size1 * 2
                    gate = regions["gate"].read(command.source0, size)
                    up = regions["up"].read(command.source1, size)
                    result = qwen3_silu_mul_bf16(
                        np.frombuffer(gate, dtype="<u2").reshape(
                            command.size0, command.size1
                        ),
                        np.frombuffer(up, dtype="<u2").reshape(
                            command.size0, command.size1
                        ),
                    )
                    activation_payload = _bf16_payload(result.activation_values)
                    output_payload = _bf16_payload(result.values)
                    regions["gated_mlp"].write(command.destination, output_payload)
                    counters["silu_command_count"] += 1
                    counters["silu_input_sram_bytes_read"] += 2 * size
                    counters["silu_output_sram_bytes_written"] += size
                    elements = command.size0 * command.size1
                    counters["sigmoid_exponentials"] += elements
                    counters["sigmoid_denominator_additions"] += elements
                    counters["sigmoid_divisions"] += elements
                    counters["silu_multiplications"] += elements
                    counters["up_gate_multiplications"] += elements
                    saturation["vector"]["silu_activation"] = (
                        result.activation_saturated_element_count
                    )
                    saturation["vector"]["silu_output"] = (
                        result.output_saturated_element_count
                    )
                    event.update(
                        {
                            "activation_payload_sha256": capture(
                                "silu_activation", activation_payload
                            ),
                            "output": "gated_mlp",
                            "output_payload_sha256": capture(
                                "gated_mlp", output_payload
                            ),
                        }
                    )

                elif command.opcode == Opcode.STATE_COMMIT:
                    if (
                        fresh_weight is not None
                        or snapshot is None
                        or prepared is None
                        or attention_result is None
                        or hidden_output is None
                        or committed is not None
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "state commit occurs before successful hidden_1 production"
                        )
                    generation, length, capacity, key_base, value_base = (
                        state_metadata()
                    )
                    descriptor = transaction_descriptor()
                    if (
                        (generation, length, capacity)
                        != (BASE_GENERATION, COMMITTED_LENGTH, CONTEXT_CAPACITY)
                        or descriptor[0] != TRANSACTION_ID
                        or command.source0 != self._direct["state_metadata"]["address"]
                        or command.source1
                        != self._direct["transaction_descriptor"]["address"]
                        or (command.size0, command.size1) != (CONTEXT_CAPACITY, 1)
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "state-commit descriptor differs"
                        )
                    committed = commit_kv_append(snapshot, prepared)
                    metadata = STATE_METADATA.pack(
                        STATE_MAGIC,
                        committed.generation,
                        committed.length,
                        committed.capacity,
                        key_base,
                        value_base,
                        0,
                        bytes(8),
                    )
                    offset = hbm_offset(command.source0, len(metadata))
                    hbm[offset : offset + len(metadata)] = metadata
                    counters["state_commit_command_count"] += 1
                    counters["state_metadata_bytes_read"] += 2 * STATE_METADATA.size
                    counters["state_metadata_bytes_written"] += STATE_METADATA.size
                    counters["hbm_useful_bytes_read"] += 2 * STATE_METADATA.size
                    counters["hbm_transferred_bytes_read"] += 2 * STATE_METADATA.size
                    counters["hbm_useful_bytes_written"] += STATE_METADATA.size
                    counters["hbm_transferred_bytes_written"] += STATE_METADATA.size
                    event.update(
                        {
                            "state_generation": committed.generation,
                            "state_length": committed.length,
                            "transaction_private": False,
                        }
                    )

                elif command.opcode == Opcode.COMPLETE:
                    if (
                        fresh_weight is not None
                        or command.index != len(self._commands) - 1
                        or hidden_output is None
                        or committed is None
                        or attention_result is None
                        or set(intermediate_hashes) != set(INTERMEDIATE_ROLES)
                        or projection_progress
                        != {
                            role: len(projection["tiles"])
                            for role, projection in self._projections.items()
                        }
                    ):
                        raise ProductionConnectedLayerSimulationError(
                            "COMPLETE observes unfinished connected-layer work"
                        )
                    counters["complete_command_count"] += 1
                    completed = True

                else:
                    raise ProductionConnectedLayerSimulationError(
                        f"unsupported connected-layer opcode {command.opcode.name}"
                    )
                trace.append(event)
        except (
            AttentionKernelError,
            BF16KernelError,
            ElementwiseKernelError,
            RMSNormKernelError,
            RoPEKernelError,
        ) as exc:
            raise ProductionConnectedLayerSimulationError(
                f"target numerical execution failed: {exc}"
            ) from exc

        if (
            not completed
            or hidden_output is None
            or committed is None
            or rope_diagnostics is None
            or attention_diagnostics is None
            or set(rmsnorm_diagnostics)
            != {"attention_norm", "q_norm", "k_norm", "mlp_norm"}
        ):
            raise ProductionConnectedLayerSimulationError(
                "program retired without every connected-layer result"
            )
        output_hash = hashlib.sha256(hidden_output).hexdigest()
        state = _state_record(committed)
        if counters != self._expectations["counters"]:
            differences = {
                name: (counters[name], self._expectations["counters"][name])
                for name in COUNTER_NAMES
                if counters[name] != self._expectations["counters"][name]
            }
            raise ProductionConnectedLayerSimulationError(
                f"observed counters differ from expectations: {differences}"
            )
        if intermediate_hashes != self._expectations["intermediate_payload_sha256"]:
            raise ProductionConnectedLayerSimulationError(
                "observed intermediate hashes differ from expectations"
            )
        if {"hidden_1": output_hash} != self._expectations["output_payload_sha256"]:
            raise ProductionConnectedLayerSimulationError(
                "observed hidden_1 hash differs from expectations"
            )
        if saturation != self._expectations["saturated_element_count"]:
            raise ProductionConnectedLayerSimulationError(
                "observed saturation counts differ from expectations"
            )
        if state["state_sha256"] != self._expectations["state_sha256"]:
            raise ProductionConnectedLayerSimulationError(
                "observed committed state differs from expectations"
            )
        trace_sha256 = hashlib.sha256(canonical_json_bytes(trace)).hexdigest()
        body = {
            "build_id": self._manifest["build_id"],
            "capability_id": self._capability.capability_id,
            "command_abi": {"major": ABI_MAJOR, "minor": ELEMENTWISE_ABI_MINOR},
            "command_count": len(self._commands),
            "counter_reconciliation": "exact",
            "counters": counters,
            "intermediate_payload_sha256": intermediate_hashes,
            "kernel_ir_id": self._kernel_ir["kernel_ir_id"],
            "mode": "artifact_only_data_bearing_functional",
            "numeric_diagnostics": {
                "attention": attention_diagnostics,
                "rmsnorm": rmsnorm_diagnostics,
                "rope": rope_diagnostics,
            },
            "output": {
                "hidden_1": {
                    "codes": [
                        int(code) for code in np.frombuffer(hidden_output, dtype="<u2")
                    ],
                    "dtype": "bf16",
                    "payload_sha256": output_hash,
                    "shape": [ROWS, HIDDEN_WIDTH],
                    "size_bytes": len(hidden_output),
                }
            },
            "physical_plan_id": self._plan["physical_plan_id"],
            "qualification_bundle_id": self._manifest["qualification_bundle_id"],
            "request_id": request["request_id"],
            "saturated_element_count": saturation,
            "schema": EXECUTION_SCHEMA,
            "source_lock_id": self._source_lock["source_lock_id"],
            "state": state,
            "status": "pass",
            "timing": {
                "reason": "capability_uncharacterized",
                "status": "unavailable",
            },
            "trace": trace,
            "trace_sha256": trace_sha256,
        }
        return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def publish_connected_layer_execution_report(
    report: Mapping[str, Any],
    output_path: Path,
) -> None:
    """Atomically retain one canonical report without overwriting evidence."""

    if not isinstance(report, Mapping):
        raise ProductionConnectedLayerSimulationError(
            "execution report must be an object"
        )
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionConnectedLayerSimulationError(
            "execution report identity differs"
        )
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(dict(report)))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise ProductionConnectedLayerSimulationError(
                f"execution report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "EXECUTION_SCHEMA",
    "ProductionConnectedLayerSimulationError",
    "ProductionConnectedLayerSimulator",
    "publish_connected_layer_execution_report",
]
