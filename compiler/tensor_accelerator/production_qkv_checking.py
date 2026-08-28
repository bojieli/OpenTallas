"""Independent inverse checker for production Q/K/V deployments.

This module intentionally does not import the Q/K/V deployment generator.  It
re-derives source semantics, physical dimensions, byte coverage, placement,
command ordering, and counters from the pinned inputs and emitted artifacts.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
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
    Engine,
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    ROPE_ABI_MINOR,
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
from .qkv_qualification import (
    COEFFICIENT_TABLE_SHA256,
    CONTEXT_POSITIONS,
    HEAD_DIM,
    KEY_VALUE_HEADS,
    QKVQualificationError,
    QUERY_HEADS,
    load_qkv_qualification,
)


CHECK_SCHEMA = "opentallas.tensor_accelerator.qkv_independent_check.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qkv_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qkv_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.qkv_source_lock.v1"
HBM_IMAGE_PATH = "memory/hbm_qkv.bin"
COMMAND_PATH = "program/commands.bin"
COMPILER_VERSION = "tensor-accelerator-production-qkv-0.1.0"
LOOKUP_CONTRACT = "bf16_payload_lookup_v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
ROPE_CONTRACT = "qwen3_rope_fp32_bf16_v1"
NUMERIC_CONTRACTS = [
    LOOKUP_CONTRACT,
    MATRIX_CONTRACT,
    RMSNORM_CONTRACT,
    ROPE_CONTRACT,
]
SOURCE_ROLES = (
    "embedding",
    "input_norm_weight",
    "q_projection_weight",
    "k_projection_weight",
    "v_projection_weight",
    "q_norm_weight",
    "k_norm_weight",
)
PROJECTION_ROLES = ("q", "k", "v")


class ProductionQKVCheckError(RuntimeError):
    """Raised when a compiler candidate cannot be independently certified."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionQKVCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionQKVCheckError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProductionQKVCheckError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ProductionQKVCheckError(f"{label} escapes the deployment")
    return path.as_posix()


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: item for key, item in value.items() if key != field}
    expected = sha256_bytes(canonical_json_bytes(body))
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionQKVCheckError(str(exc)) from exc
    if observed != expected:
        raise ProductionQKVCheckError(f"{label} identity differs")


def _binding(
    model: ProductionModelGraph,
    tensor_id: str,
    *,
    checkpoint_lock_id: str,
    rank: int,
) -> tuple[tuple[int, ...], str]:
    tensor = model.tensor_by_id.get(tensor_id)
    if (
        tensor is None
        or tensor.dtype != "bf16"
        or tensor.binding is None
        or len(tensor.shape) != rank
        or any(not isinstance(extent, int) for extent in tensor.shape)
    ):
        raise ProductionQKVCheckError(
            f"production graph lacks bound rank-{rank} BF16 tensor {tensor_id!r}"
        )
    binding = tensor.binding
    if (
        binding.checkpoint_lock_id != checkpoint_lock_id
        or len(binding.sources) != 1
        or binding.transform.get("kind") != "identity"
        or binding.sources[0].tensor_name != tensor_id
        or binding.sources[0].dtype != "bf16"
        or binding.sources[0].shape != tuple(tensor.shape)
        or binding.payload_sha256 != binding.sources[0].payload_sha256
    ):
        raise ProductionQKVCheckError(
            f"tensor {tensor_id!r} is not an identity checkpoint binding"
        )
    return binding.sources[0].shape, binding.sources[0].payload_sha256


def _one_operation(
    model: ProductionModelGraph,
    *,
    kind: str,
    inputs: tuple[str, ...],
    numeric_contract: str,
) -> ProductionOperation:
    matches = [
        operation
        for operation in model.operations
        if operation.kind == kind
        and operation.inputs == inputs
        and operation.numeric_contract == numeric_contract
    ]
    if len(matches) != 1:
        raise ProductionQKVCheckError(
            f"source graph {kind} coverage differs for {inputs!r}"
        )
    return matches[0]


def _source_semantics(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    lock_id: str,
) -> tuple[ProductionOperation, ...]:
    sources = qualification["sources"]
    for role in SOURCE_ROLES:
        source = sources[role]
        shape, digest = _binding(
            model,
            source["tensor"],
            checkpoint_lock_id=lock_id,
            rank=len(source["shape"]),
        )
        if list(shape) != source["shape"] or digest != source["payload_sha256"]:
            raise ProductionQKVCheckError(
                f"qualified {role} differs from graph binding"
            )
    lookup = _one_operation(
        model,
        kind="EMBEDDING_LOOKUP",
        inputs=("input.token_ids", sources["embedding"]["tensor"]),
        numeric_contract=LOOKUP_CONTRACT,
    )
    if len(lookup.outputs) != 1:
        raise ProductionQKVCheckError("embedding lookup output arity differs")
    input_norm = _one_operation(
        model,
        kind="RMS_NORM",
        inputs=(lookup.outputs[0], sources["input_norm_weight"]["tensor"]),
        numeric_contract=RMSNORM_CONTRACT,
    )
    if (
        len(input_norm.outputs) != 1
        or input_norm.attributes.get("epsilon") != 1e-6
        or input_norm.attributes.get("normalization_width") != 4096
        or input_norm.attributes.get("layer") != 0
    ):
        raise ProductionQKVCheckError("input RMSNorm source attributes differ")
    projections: list[ProductionOperation] = []
    for role in PROJECTION_ROLES:
        operation = _one_operation(
            model,
            kind="MATMUL",
            inputs=(
                input_norm.outputs[0],
                sources[f"{role}_projection_weight"]["tensor"],
            ),
            numeric_contract=MATRIX_CONTRACT,
        )
        if (
            len(operation.outputs) != 1
            or operation.attributes.get("transpose_weight") is not True
            or operation.attributes.get("layer") != 0
        ):
            raise ProductionQKVCheckError(
                f"{role.upper()} projection source attributes differ"
            )
        projections.append(operation)
    q_norm = _one_operation(
        model,
        kind="RMS_NORM",
        inputs=(projections[0].outputs[0], sources["q_norm_weight"]["tensor"]),
        numeric_contract=RMSNORM_CONTRACT,
    )
    k_norm = _one_operation(
        model,
        kind="RMS_NORM",
        inputs=(projections[1].outputs[0], sources["k_norm_weight"]["tensor"]),
        numeric_contract=RMSNORM_CONTRACT,
    )
    for operation in (q_norm, k_norm):
        if (
            len(operation.outputs) != 1
            or operation.attributes.get("epsilon") != 1e-6
            or operation.attributes.get("normalization_width") != HEAD_DIM
            or operation.attributes.get("layer") != 0
        ):
            raise ProductionQKVCheckError("head RMSNorm source attributes differ")
    rope = _one_operation(
        model,
        kind="ROPE",
        inputs=(q_norm.outputs[0], k_norm.outputs[0]),
        numeric_contract=ROPE_CONTRACT,
    )
    if (
        len(rope.outputs) != 2
        or rope.attributes.get("head_dim") != HEAD_DIM
        or rope.attributes.get("layer") != 0
        or rope.attributes.get("position_symbol") != "position_start"
    ):
        raise ProductionQKVCheckError("RoPE source attributes differ")
    result = (lookup, input_norm, *projections, q_norm, k_norm, rope)
    if len({operation.operation_id for operation in result}) != 8:
        raise ProductionQKVCheckError("source-operation identity coverage differs")
    return result


def _capture_row(shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = shape[1] * 2
    start = row * row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        overlap_start = max(cursor, start)
        overlap_end = min(end, start + row_bytes)
        if overlap_start < overlap_end:
            captured.extend(chunk[overlap_start - cursor : overlap_end - cursor])
        cursor = end

    return captured, consume


def _read_sources(
    snapshot: Path,
    lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    sources = qualification["sources"]
    try:
        with LockedCheckpointReader(snapshot, dict(lock)) as reader:
            source = sources["embedding"]
            record = reader.tensor_record(source["tensor"])
            shape = tuple(record["shape"])
            token_id = qualification["input"]["token_id"]
            if len(shape) != 2 or not 0 <= token_id < shape[0]:
                raise ProductionQKVCheckError("qualified embedding row is illegal")
            captured, consumer = _capture_row(shape, token_id)
            reader.consume_tensor_payload(source["tensor"], consumer)
            payloads["embedding"] = bytes(captured)
            if (
                record["shape"] != source["shape"]
                or record["payload_sha256"] != source["payload_sha256"]
                or hashlib.sha256(payloads["embedding"]).hexdigest()
                != qualification["input"]["embedding_row_payload_sha256"]
            ):
                raise ProductionQKVCheckError(
                    "locked embedding differs from qualification"
                )
            for role in SOURCE_ROLES[1:]:
                source = sources[role]
                raw = bytearray()
                record = reader.consume_tensor_payload(source["tensor"], raw.extend)
                payload = bytes(raw)
                if (
                    record["shape"] != source["shape"]
                    or record["payload_sha256"] != source["payload_sha256"]
                    or hashlib.sha256(payload).hexdigest() != source["payload_sha256"]
                ):
                    raise ProductionQKVCheckError(
                        f"locked {role} differs from qualification"
                    )
                payloads[role] = payload
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionQKVCheckError(
            f"independent locked checkpoint read failed: {exc}"
        ) from exc
    return payloads


def _problem(
    raw: Any,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, Any]:
    sources = qualification["sources"]
    expected_shapes = {
        "embedding": [151936, 4096],
        "input_norm_weight": [4096],
        "q_projection_weight": [QUERY_HEADS * HEAD_DIM, 4096],
        "k_projection_weight": [KEY_VALUE_HEADS * HEAD_DIM, 4096],
        "v_projection_weight": [KEY_VALUE_HEADS * HEAD_DIM, 4096],
        "q_norm_weight": [HEAD_DIM],
        "k_norm_weight": [HEAD_DIM],
    }
    if any(sources[role]["shape"] != shape for role, shape in expected_shapes.items()):
        raise ProductionQKVCheckError("qualified source shapes differ")
    vector = capability.vector_engine
    if (
        capability.command_abi_minor != ROPE_ABI_MINOR
        or vector is None
        or vector.max_rows < QUERY_HEADS + KEY_VALUE_HEADS
        or vector.max_width < 4096
        or vector.max_rope_positions is None
        or vector.max_rope_positions < CONTEXT_POSITIONS
        or vector.max_query_heads is None
        or vector.max_query_heads < QUERY_HEADS
        or vector.max_key_value_heads is None
        or vector.max_key_value_heads < KEY_VALUE_HEADS
        or vector.rope_head_dim != HEAD_DIM
        or not {MATRIX_CONTRACT, RMSNORM_CONTRACT, ROPE_CONTRACT}
        <= set(capability.qualified_numeric_contracts)
    ):
        raise ProductionQKVCheckError("capability lacks qualified Q/K/V bounds")
    projections: list[dict[str, int | str]] = []
    for role, heads in (
        ("q", QUERY_HEADS),
        ("k", KEY_VALUE_HEADS),
        ("v", KEY_VALUE_HEADS),
    ):
        n = heads * HEAD_DIM
        n_tile = min(64, n, capability.tensor_engine.max_n)
        k_tile = min(256, 4096, capability.tensor_engine.max_k)
        if (
            n % n_tile
            or 4096 % k_tile
            or n_tile * k_tile * 2 % capability.hbm.burst_bytes
        ):
            raise ProductionQKVCheckError(f"{role.upper()} tiling is illegal")
        projections.append(
            {
                "k": 4096,
                "k_tile": k_tile,
                "k_tiles": 4096 // k_tile,
                "n": n,
                "n_tile": n_tile,
                "n_tiles": n // n_tile,
                "role": role,
                "tile_count": n // n_tile * (4096 // k_tile),
            }
        )
    expected = {
        "coefficient_row_bytes": 2 * HEAD_DIM * 2,
        "context_positions": CONTEXT_POSITIONS,
        "head_dim": HEAD_DIM,
        "hidden_width": 4096,
        "key_value_heads": KEY_VALUE_HEADS,
        "projections": projections,
        "query_heads": QUERY_HEADS,
        "resident_embedding_base_token": qualification["input"]["token_id"],
        "resident_embedding_rows": 1,
    }
    if raw != expected:
        raise ProductionQKVCheckError("physical-plan problem differs")
    return expected


def _rmsnorm_kernel(
    index: int,
    operation: ProductionOperation,
    rows: int,
    width: int,
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


def _kernel(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ...],
    problem: Mapping[str, Any],
) -> str:
    value = _load_canonical(root / "ir/tensor_kernel_ir.json", "Tensor Kernel IR")
    exact_keys(
        value,
        {
            "graph_id",
            "kernel_ir_id",
            "kernels",
            "qualification_report_id",
            "schema",
        },
        set(),
        "Tensor Kernel IR",
    )
    _identity(value, "kernel_ir_id", "Tensor Kernel IR")
    (
        lookup,
        input_norm,
        q_projection,
        k_projection,
        v_projection,
        q_norm,
        k_norm,
        rope,
    ) = operations
    expected: list[dict[str, Any]] = [
        {
            "attributes": {
                "index_dtype": "u32",
                "output_dtype": "bf16",
                "source_index_max_exclusive": qualification["sources"]["embedding"][
                    "shape"
                ][0],
                "source_index_min": 0,
            },
            "index": 0,
            "inputs": list(lookup.inputs),
            "kind": "EMBEDDING_LOOKUP",
            "numeric_contract": LOOKUP_CONTRACT,
            "outputs": list(lookup.outputs),
            "shape": {"rows": 1, "width": problem["hidden_width"]},
            "source_operation_id": lookup.operation_id,
        },
        _rmsnorm_kernel(1, input_norm, 1, problem["hidden_width"]),
    ]
    for index, operation, projection in zip(
        (2, 3, 4),
        (q_projection, k_projection, v_projection),
        problem["projections"],
        strict=True,
    ):
        expected.append(
            {
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
                "shape": {
                    "reduction_width": projection["k"],
                    "rows": 1,
                    "width": projection["n"],
                },
                "source_operation_id": operation.operation_id,
            }
        )
    expected.extend(
        (
            _rmsnorm_kernel(5, q_norm, problem["query_heads"], problem["head_dim"]),
            _rmsnorm_kernel(6, k_norm, problem["key_value_heads"], problem["head_dim"]),
            {
                "attributes": {
                    "coefficient_layout": "cos_head_dim_then_sin_head_dim",
                    "key_value_heads": problem["key_value_heads"],
                    "max_positions": problem["context_positions"],
                    "position_symbol": "position_start",
                    "query_heads": problem["query_heads"],
                    "rotation": "concat_neg_second_half_first_half",
                },
                "index": 7,
                "inputs": list(rope.inputs),
                "kind": "ROPE",
                "numeric_contract": ROPE_CONTRACT,
                "outputs": list(rope.outputs),
                "shape": {"head_dim": problem["head_dim"]},
                "source_operation_id": rope.operation_id,
            },
        )
    )
    if (
        value["schema"] != KERNEL_SCHEMA
        or value["graph_id"] != model.graph_id
        or value["qualification_report_id"] != qualification["report_id"]
        or value["kernels"] != expected
    ):
        raise ProductionQKVCheckError(
            "Tensor Kernel IR differs from independent source lowering"
        )
    return value["kernel_ir_id"]


def _source_copies(
    root: Path,
    *,
    model_graph_path: Path,
    checkpoint_lock_path: Path,
    capability_path: Path,
    qualification_path: Path,
    graph_id: str,
    lock_id: str,
    capability_id: str,
    qualification_id: str,
) -> str:
    value = _load_canonical(root / "source.lock.json", "source lock")
    exact_keys(
        value,
        {
            "capability_id",
            "checkpoint_lock_id",
            "compiler_version",
            "graph_id",
            "qualification_report_id",
            "schema",
            "source_lock_id",
            "sources",
        },
        set(),
        "source lock",
    )
    _identity(value, "source_lock_id", "source lock")
    paths = {
        "model_graph": model_graph_path,
        "checkpoint_lock": checkpoint_lock_path,
        "hardware_capability": capability_path,
        "qualification_report": qualification_path,
    }
    expected_sources = []
    for role in (
        "model_graph",
        "checkpoint_lock",
        "hardware_capability",
        "qualification_report",
    ):
        digest, size = sha256_file(paths[role])
        expected_sources.append({"role": role, "sha256": digest, "size_bytes": size})
    if (
        value["schema"] != SOURCE_LOCK_SCHEMA
        or value["compiler_version"] != COMPILER_VERSION
        or value["graph_id"] != graph_id
        or value["checkpoint_lock_id"] != lock_id
        or value["capability_id"] != capability_id
        or value["qualification_report_id"] != qualification_id
        or value["sources"] != expected_sources
    ):
        raise ProductionQKVCheckError("source-lock identities differ")
    copies = {
        root / "source/model_graph.v2.json": model_graph_path,
        root / "source/checkpoint.lock.json": checkpoint_lock_path,
        root / "source/qualification.json": qualification_path,
        root / "capability.json": capability_path,
    }
    for copy, source in copies.items():
        try:
            if copy.read_bytes() != source.read_bytes():
                raise ProductionQKVCheckError(
                    f"deployed source copy differs: {copy.relative_to(root)}"
                )
        except OSError as exc:
            raise ProductionQKVCheckError(
                f"cannot read deployed source copy: {exc}"
            ) from exc
    return value["source_lock_id"]


def _expected_sram(
    problem: Mapping[str, Any], capability: ProductionCapability
) -> list[dict[str, Any]]:
    hidden_bytes = problem["hidden_width"] * 2
    q_bytes = problem["query_heads"] * problem["head_dim"] * 2
    kv_bytes = problem["key_value_heads"] * problem["head_dim"] * 2
    specs = (
        ("runtime_ids", 0, "u32", [2], 8),
        ("embedding", 1, "bf16", [1, problem["hidden_width"]], hidden_bytes),
        ("input_norm_weight", 2, "bf16", [problem["hidden_width"]], hidden_bytes),
        ("attention_norm", 3, "bf16", [1, problem["hidden_width"]], hidden_bytes),
        ("weight_tile", 4, "bf16", [64, 256], 64 * 256 * 2),
        ("accumulator_tile", 5, "fp32", [1, 64], 64 * 4),
        (
            "q_raw",
            6,
            "bf16",
            [1, problem["query_heads"] * problem["head_dim"]],
            q_bytes,
        ),
        (
            "k_raw",
            7,
            "bf16",
            [1, problem["key_value_heads"] * problem["head_dim"]],
            kv_bytes,
        ),
        ("v", 8, "bf16", [problem["key_value_heads"], problem["head_dim"]], kv_bytes),
        ("q_norm_weight", 9, "bf16", [problem["head_dim"]], problem["head_dim"] * 2),
        ("k_norm_weight", 10, "bf16", [problem["head_dim"]], problem["head_dim"] * 2),
        ("q_norm", 11, "bf16", [problem["query_heads"], problem["head_dim"]], q_bytes),
        (
            "k_norm",
            12,
            "bf16",
            [problem["key_value_heads"], problem["head_dim"]],
            kv_bytes,
        ),
        (
            "rope_coefficients",
            13,
            "bf16",
            [2 * problem["head_dim"]],
            problem["coefficient_row_bytes"],
        ),
        (
            "q_rotary",
            14,
            "bf16",
            [problem["query_heads"], problem["head_dim"]],
            q_bytes,
        ),
        (
            "k_rotary",
            15,
            "bf16",
            [problem["key_value_heads"], problem["head_dim"]],
            kv_bytes,
        ),
    )
    result = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if allocated > capability.sram.bytes_per_bank:
            raise ProductionQKVCheckError(f"SRAM region {region_id!r} exceeds bank")
        result.append(
            {
                "address": capability.sram.bank_base(bank),
                "allocated_bytes": allocated,
                "bank": bank,
                "dtype": dtype,
                "id": region_id,
                "logical_bytes": logical_bytes,
                "shape": shape,
            }
        )
    return result


def _sram(
    raw: Any,
    *,
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ProductionQKVCheckError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    expected = _expected_sram(problem, capability)
    if raw["addressing"] != "bank_base_plus_byte_offset" or raw["regions"] != expected:
        raise ProductionQKVCheckError("SRAM region allocation differs")
    return {record["id"]: record for record in expected}


def _expected_counters(problem: Mapping[str, Any]) -> dict[str, int]:
    projections = problem["projections"]
    tile_count = sum(item["tile_count"] for item in projections)
    projection_weight_bytes = sum(item["n"] * item["k"] * 2 for item in projections)
    projection_output_bytes = sum(item["n"] * 2 for item in projections)
    matmul_input_bytes = sum(
        item["tile_count"] * item["k_tile"] * 2 for item in projections
    )
    accumulator_writes = tile_count * 64 * 4
    accumulator_reads = sum(
        item["n_tiles"] * (item["k_tiles"] - 1) * 64 * 4 for item in projections
    )
    hidden_bytes = problem["hidden_width"] * 2
    q_bytes = problem["query_heads"] * problem["head_dim"] * 2
    kv_bytes = problem["key_value_heads"] * problem["head_dim"] * 2
    rms_elements = (
        problem["hidden_width"]
        + problem["query_heads"] * problem["head_dim"]
        + problem["key_value_heads"] * problem["head_dim"]
    )
    rms_rows = 1 + problem["query_heads"] + problem["key_value_heads"]
    rms_reductions = (
        problem["hidden_width"]
        - 1
        + (problem["query_heads"] + problem["key_value_heads"])
        * (problem["head_dim"] - 1)
    )
    direct_dma_bytes = projection_weight_bytes + hidden_bytes + 4 * problem["head_dim"]
    indexed_dma_bytes = hidden_bytes + problem["coefficient_row_bytes"]
    rope_elements = (problem["query_heads"] + problem["key_value_heads"]) * problem[
        "head_dim"
    ]
    return {
        "accumulator_sram_bytes_read": accumulator_reads,
        "accumulator_sram_bytes_written": accumulator_writes,
        "command_count": 2 * tile_count + 10,
        "complete_command_count": 1,
        "direct_dma_command_count": tile_count + 3,
        "dma_command_count": tile_count + 5,
        "dma_sram_bytes_written": direct_dma_bytes + indexed_dma_bytes,
        "epsilon_additions": rms_rows,
        "final_weight_multiplications": rms_elements,
        "hbm_transferred_bytes_read": direct_dma_bytes + indexed_dma_bytes,
        "hbm_useful_bytes_read": direct_dma_bytes + indexed_dma_bytes,
        "indexed_dma_command_count": 2,
        "input_square_multiplications": rms_elements,
        "matmul_command_count": tile_count,
        "matmul_input_sram_bytes_read": matmul_input_bytes,
        "matmul_output_sram_bytes_written": projection_output_bytes,
        "matmul_weight_sram_bytes_read": projection_weight_bytes,
        "mean_divisions": rms_rows,
        "normalization_multiplications": rms_elements,
        "reciprocal_square_roots": rms_rows,
        "reduction_additions": rms_reductions,
        "rmsnorm_command_count": 3,
        "rmsnorm_input_sram_bytes_read": hidden_bytes + q_bytes + kv_bytes,
        "rmsnorm_output_sram_bytes_written": hidden_bytes + q_bytes + kv_bytes,
        "rmsnorm_weight_sram_bytes_read": hidden_bytes + 4 * problem["head_dim"],
        "rope_additions": rope_elements,
        "rope_command_count": 1,
        "rope_input_sram_bytes_read": q_bytes
        + kv_bytes
        + problem["coefficient_row_bytes"],
        "rope_multiplications": 2 * rope_elements,
        "rope_output_sram_bytes_written": q_bytes + kv_bytes,
        "runtime_request_sram_bytes_written": 8,
        "scalar_accumulation_additions": sum(
            item["n"] * item["k"] for item in projections
        ),
        "scalar_multiplications": sum(item["n"] * item["k"] for item in projections),
    }


def _hbm(
    raw: Any,
    root: Path,
    *,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    payloads: Mapping[str, bytes],
    problem: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[tuple[str, int, int], dict[str, Any]],
    str,
    int,
]:
    if not isinstance(raw, dict):
        raise ProductionQKVCheckError("HBM plan must be an object")
    exact_keys(
        raw,
        {"image", "projection_sources", "projection_tiles", "regions"},
        set(),
        "HBM plan",
    )
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionQKVCheckError("HBM image record must be an object")
    exact_keys(
        image_record,
        {"base_address", "path", "sha256", "size_bytes"},
        set(),
        "HBM image record",
    )
    if (
        image_record["base_address"] != capability.hbm.base_address
        or _safe_relative(image_record["path"], "HBM image path") != HBM_IMAGE_PATH
    ):
        raise ProductionQKVCheckError("HBM image identity differs")
    image_path = root / HBM_IMAGE_PATH
    try:
        image = image_path.read_bytes()
    except OSError as exc:
        raise ProductionQKVCheckError(f"cannot read HBM image: {exc}") from exc
    image_digest = hashlib.sha256(image).hexdigest()
    if (
        image_record["sha256"] != image_digest
        or image_record["size_bytes"] != len(image)
        or len(image) > capability.hbm.capacity_bytes
        or len(image) % capability.hbm.burst_bytes
    ):
        raise ProductionQKVCheckError("HBM image size, identity, or alignment differs")
    covered = bytearray(len(image))

    def payload_for(record: Mapping[str, Any], label: str) -> bytes:
        try:
            offset = require_int(
                record["offset_bytes"], f"{label}.offset_bytes", minimum=0
            )
            size = require_int(record["size_bytes"], f"{label}.size_bytes", minimum=1)
            address = require_int(record["address"], f"{label}.address", minimum=0)
            digest = require_sha256(record["payload_sha256"], f"{label}.payload_sha256")
        except ArtifactError as exc:
            raise ProductionQKVCheckError(str(exc)) from exc
        if (
            offset % capability.hbm.burst_bytes
            or address != capability.hbm.base_address + offset
            or offset + size > len(image)
        ):
            raise ProductionQKVCheckError(f"{label} address or range is illegal")
        if any(covered[offset : offset + size]):
            raise ProductionQKVCheckError(f"{label} overlaps another HBM region")
        covered[offset : offset + size] = b"\x01" * size
        result = image[offset : offset + size]
        if hashlib.sha256(result).hexdigest() != digest:
            raise ProductionQKVCheckError(f"{label} payload identity differs")
        return result

    region_values = raw["regions"]
    if not isinstance(region_values, list) or len(region_values) != 5:
        raise ProductionQKVCheckError("HBM non-projection region coverage differs")
    regions: dict[str, dict[str, Any]] = {}
    expected_region_roles = {
        "embedding_rows": "embedding",
        "input_norm_weight": "input_norm_weight",
        "q_norm_weight": "q_norm_weight",
        "k_norm_weight": "k_norm_weight",
        "rope_coefficient_table": "rope_coefficients",
    }
    for index, candidate in enumerate(region_values):
        if not isinstance(candidate, dict):
            raise ProductionQKVCheckError("HBM region must be an object")
        exact_keys(
            candidate,
            {
                "address",
                "id",
                "offset_bytes",
                "payload_sha256",
                "size_bytes",
                "source_role",
            },
            set(),
            f"HBM region {index}",
        )
        payload = payload_for(candidate, f"HBM region {index}")
        region_id = candidate.get("id")
        source_role = candidate.get("source_role")
        if (
            not isinstance(region_id, str)
            or region_id in regions
            or expected_region_roles.get(region_id) != source_role
        ):
            raise ProductionQKVCheckError("HBM region ID or source role differs")
        if source_role == "rope_coefficients":
            expected_size = (
                problem["context_positions"] * problem["coefficient_row_bytes"]
            )
            if (
                len(payload) != expected_size
                or hashlib.sha256(payload).hexdigest() != COEFFICIENT_TABLE_SHA256
                or qualification["rope"]["coefficient_table_payload_sha256"]
                != COEFFICIENT_TABLE_SHA256
            ):
                raise ProductionQKVCheckError(
                    "RoPE coefficient table differs from qualified payload"
                )
        elif source_role == "embedding":
            if payload != payloads["embedding"]:
                raise ProductionQKVCheckError(
                    "HBM embedding row differs from locked source"
                )
        elif payload != payloads[source_role]:
            raise ProductionQKVCheckError(
                f"HBM {source_role} differs from locked source"
            )
        regions[region_id] = candidate
    if set(regions) != set(expected_region_roles):
        raise ProductionQKVCheckError("HBM non-projection region IDs differ")

    expected_sources = [
        {
            "payload_sha256": qualification["sources"][f"{role}_projection_weight"][
                "payload_sha256"
            ],
            "projection_role": role,
            "shape": qualification["sources"][f"{role}_projection_weight"]["shape"],
            "tensor_name": qualification["sources"][f"{role}_projection_weight"][
                "tensor"
            ],
        }
        for role in PROJECTION_ROLES
    ]
    if raw["projection_sources"] != expected_sources:
        raise ProductionQKVCheckError("HBM projection source inventory differs")

    raw_tiles = raw["projection_tiles"]
    expected_tile_count = sum(item["tile_count"] for item in problem["projections"])
    if not isinstance(raw_tiles, list) or len(raw_tiles) != expected_tile_count:
        raise ProductionQKVCheckError("HBM projection tile count differs")
    projection_by_role = {item["role"]: item for item in problem["projections"]}
    source_arrays = {
        role: np.frombuffer(payloads[f"{role}_projection_weight"], dtype="<u2").reshape(
            projection_by_role[role]["n"], projection_by_role[role]["k"]
        )
        for role in PROJECTION_ROLES
    }
    tiles: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, candidate in enumerate(raw_tiles):
        if not isinstance(candidate, dict):
            raise ProductionQKVCheckError("projection tile must be an object")
        exact_keys(
            candidate,
            {
                "address",
                "k_count",
                "k_start",
                "n_count",
                "n_start",
                "offset_bytes",
                "payload_sha256",
                "projection_role",
                "size_bytes",
                "tile_index",
            },
            set(),
            f"projection tile {index}",
        )
        role = candidate["projection_role"]
        if role not in projection_by_role:
            raise ProductionQKVCheckError("projection tile role differs")
        projection = projection_by_role[role]
        try:
            n_start = require_int(candidate["n_start"], "tile.n_start", minimum=0)
            k_start = require_int(candidate["k_start"], "tile.k_start", minimum=0)
            n_count = require_int(candidate["n_count"], "tile.n_count", minimum=1)
            k_count = require_int(candidate["k_count"], "tile.k_count", minimum=1)
            tile_index = require_int(
                candidate["tile_index"], "tile.tile_index", minimum=0
            )
        except ArtifactError as exc:
            raise ProductionQKVCheckError(str(exc)) from exc
        expected_index = (
            n_start // projection["n_tile"] * projection["k_tiles"]
            + k_start // projection["k_tile"]
        )
        if (
            n_count != projection["n_tile"]
            or k_count != projection["k_tile"]
            or n_start % n_count
            or k_start % k_count
            or n_start + n_count > projection["n"]
            or k_start + k_count > projection["k"]
            or tile_index != expected_index
        ):
            raise ProductionQKVCheckError("projection tile coordinate differs")
        payload = payload_for(candidate, f"projection tile {index}")
        expected_payload = np.ascontiguousarray(
            source_arrays[role][
                n_start : n_start + n_count,
                k_start : k_start + k_count,
            ],
            dtype="<u2",
        ).tobytes(order="C")
        if payload != expected_payload:
            raise ProductionQKVCheckError(
                f"HBM {role.upper()} tile differs from locked source"
            )
        key = (role, n_start, k_start)
        if key in tiles:
            raise ProductionQKVCheckError("projection tile coordinate is duplicated")
        tiles[key] = candidate
    expected_keys = {
        (projection["role"], n_start, k_start)
        for projection in problem["projections"]
        for n_start in range(0, projection["n"], projection["n_tile"])
        for k_start in range(0, projection["k"], projection["k_tile"])
    }
    if set(tiles) != expected_keys:
        raise ProductionQKVCheckError("projection tile coordinate coverage differs")
    if any(byte and not mark for byte, mark in zip(image, covered, strict=True)):
        raise ProductionQKVCheckError("HBM padding or unassigned bytes are nonzero")
    return regions, tiles, image_digest, len(image)


def _program(
    raw: Any,
    root: Path,
    *,
    capability: ProductionCapability,
    problem: Mapping[str, Any],
    hbm_regions: Mapping[str, Mapping[str, Any]],
    tiles: Mapping[tuple[str, int, int], Mapping[str, Any]],
    sram: Mapping[str, Mapping[str, Any]],
) -> int:
    if not isinstance(raw, dict):
        raise ProductionQKVCheckError("program record must be an object")
    exact_keys(
        raw,
        {"command_count", "path", "sha256", "size_bytes"},
        set(),
        "program record",
    )
    if _safe_relative(raw["path"], "command path") != COMMAND_PATH:
        raise ProductionQKVCheckError("command path differs")
    try:
        payload = (root / COMMAND_PATH).read_bytes()
        commands = decode(payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionQKVCheckError(f"cannot decode command program: {exc}") from exc
    if (
        command_abi(payload) != (ABI_MAJOR, ROPE_ABI_MINOR)
        or raw["command_count"] != len(commands)
        or raw["size_bytes"] != len(payload)
        or raw["sha256"] != hashlib.sha256(payload).hexdigest()
        or len(commands) > capability.limits["max_commands"]
    ):
        raise ProductionQKVCheckError("command program metadata differs")
    expected: list[ProductionCommand] = [
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=0,
            source0=hbm_regions["embedding_rows"]["address"],
            source1=sram["runtime_ids"]["address"],
            destination=sram["embedding"]["address"],
            auxiliary=problem["resident_embedding_base_token"],
            size0=problem["hidden_width"] * 2,
            size1=problem["hidden_width"] * 2,
            size2=problem["resident_embedding_rows"],
            size3=4,
        ),
        ProductionCommand(
            index=1,
            opcode=Opcode.DMA_HBM_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=1,
            source0=hbm_regions["input_norm_weight"]["address"],
            destination=sram["input_norm_weight"]["address"],
            size0=problem["hidden_width"] * 2,
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
            kernel_index=1,
            source0=sram["embedding"]["address"],
            source1=sram["input_norm_weight"]["address"],
            destination=sram["attention_norm"]["address"],
            size0=1,
            size1=problem["hidden_width"],
            size2=EPSILON_CODE,
        ),
    ]
    output_region = {"q": "q_raw", "k": "k_raw", "v": "v"}
    for kernel_index, projection in enumerate(problem["projections"], start=2):
        role = projection["role"]
        for n_start in range(0, projection["n"], projection["n_tile"]):
            for k_start in range(0, projection["k"], projection["k_tile"]):
                tile = tiles[(role, n_start, k_start)]
                expected.append(
                    ProductionCommand(
                        index=len(expected),
                        opcode=Opcode.DMA_HBM_TO_SRAM,
                        engine=Engine.DMA,
                        kernel_index=kernel_index,
                        source0=tile["address"],
                        destination=sram["weight_tile"]["address"],
                        size0=tile["size_bytes"],
                    )
                )
                flags = 0
                if k_start == 0:
                    flags |= MATMUL_INIT
                if k_start + projection["k_tile"] == projection["k"]:
                    flags |= MATMUL_FINAL
                expected.append(
                    ProductionCommand(
                        index=len(expected),
                        opcode=Opcode.MATMUL_BF16_TILE,
                        engine=Engine.TENSOR,
                        flags=flags,
                        kernel_index=kernel_index,
                        source0=sram["attention_norm"]["address"] + k_start * 2,
                        source1=sram["weight_tile"]["address"],
                        destination=sram["accumulator_tile"]["address"],
                        auxiliary=sram[output_region[role]]["address"] + n_start * 2,
                        size0=1,
                        size1=projection["n_tile"],
                        size2=projection["k_tile"],
                    )
                )
    for kernel_index, role in ((5, "q"), (6, "k")):
        expected.append(
            ProductionCommand(
                index=len(expected),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=kernel_index,
                source0=hbm_regions[f"{role}_norm_weight"]["address"],
                destination=sram[f"{role}_norm_weight"]["address"],
                size0=problem["head_dim"] * 2,
            )
        )
    for kernel_index, role, rows in (
        (5, "q", problem["query_heads"]),
        (6, "k", problem["key_value_heads"]),
    ):
        expected.append(
            ProductionCommand(
                index=len(expected),
                opcode=Opcode.RMSNORM_BF16,
                engine=Engine.VECTOR,
                kernel_index=kernel_index,
                source0=sram[f"{role}_raw"]["address"],
                source1=sram[f"{role}_norm_weight"]["address"],
                destination=sram[f"{role}_norm"]["address"],
                size0=rows,
                size1=problem["head_dim"],
                size2=EPSILON_CODE,
            )
        )
    expected.extend(
        (
            ProductionCommand(
                index=len(expected),
                opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=7,
                source0=hbm_regions["rope_coefficient_table"]["address"],
                source1=sram["runtime_ids"]["address"] + 4,
                destination=sram["rope_coefficients"]["address"],
                auxiliary=0,
                size0=problem["coefficient_row_bytes"],
                size1=problem["coefficient_row_bytes"],
                size2=problem["context_positions"],
                size3=4,
            ),
            ProductionCommand(
                index=len(expected) + 1,
                opcode=Opcode.ROPE_BF16,
                engine=Engine.VECTOR,
                kernel_index=7,
                source0=sram["q_norm"]["address"],
                source1=sram["k_norm"]["address"],
                destination=sram["q_rotary"]["address"],
                auxiliary=sram["k_rotary"]["address"],
                size0=problem["query_heads"],
                size1=problem["key_value_heads"],
                size2=problem["head_dim"],
                size3=sram["rope_coefficients"]["address"],
            ),
            ProductionCommand(
                index=len(expected) + 2,
                opcode=Opcode.COMPLETE,
                engine=Engine.CONTROL,
            ),
        )
    )
    if commands != tuple(expected):
        raise ProductionQKVCheckError(
            "command program is not the independently legal Q/K/V schedule"
        )
    try:
        emitted_disassembly = (root / "program/commands.disasm").read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        raise ProductionQKVCheckError(
            f"cannot read command disassembly: {exc}"
        ) from exc
    if emitted_disassembly != disassemble(commands, abi_minor=ROPE_ABI_MINOR):
        raise ProductionQKVCheckError("command disassembly differs from binary")
    return len(commands)


def _request(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    source_operation_ids: tuple[str, ...],
) -> str:
    value = _load_canonical(
        root / "request/execution_request.json", "execution request"
    )
    exact_keys(
        value,
        {
            "graph_id",
            "position",
            "request_id",
            "schema",
            "source_operation_ids",
            "token",
        },
        set(),
        "execution request",
    )
    _identity(value, "request_id", "execution request")
    expected = {
        "graph_id": model.graph_id,
        "position": {
            "dtype": "u32",
            "position_id": qualification["input"]["position_id"],
        },
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": list(source_operation_ids),
        "token": {
            "dtype": "u32",
            "token_id": qualification["input"]["token_id"],
        },
    }
    if {key: item for key, item in value.items() if key != "request_id"} != expected:
        raise ProductionQKVCheckError("execution request differs from qualification")
    return value["request_id"]


def check_qkv_candidate(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct and validate one Q/K/V compiler candidate."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
        qualification = load_qkv_qualification(Path(qualification_path))
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        QKVQualificationError,
    ) as exc:
        raise ProductionQKVCheckError(
            f"independent source admission failed: {exc}"
        ) from exc
    root = Path(root)
    if qualification["checkpoint_lock_id"] != lock["lock_id"]:
        raise ProductionQKVCheckError("qualification checkpoint identity differs")
    operations = _source_semantics(model, qualification, lock["lock_id"])
    operation_ids = tuple(operation.operation_id for operation in operations)
    payloads = _read_sources(Path(snapshot), lock, qualification)
    source_lock_id = _source_copies(
        root,
        model_graph_path=Path(model_graph_path),
        checkpoint_lock_path=Path(checkpoint_lock_path),
        capability_path=Path(capability_path),
        qualification_path=Path(qualification_path),
        graph_id=model.graph_id,
        lock_id=lock["lock_id"],
        capability_id=capability.capability_id,
        qualification_id=qualification["report_id"],
    )
    plan = _load_canonical(root / "physical/physical_plan.json", "physical plan")
    exact_keys(
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
            "qualification_report_id",
            "schema",
            "source_operation_ids",
            "sram",
        },
        set(),
        "physical plan",
    )
    _identity(plan, "physical_plan_id", "physical plan")
    if (
        plan["schema"] != PHYSICAL_PLAN_SCHEMA
        or plan["capability_id"] != capability.capability_id
        or plan["graph_id"] != model.graph_id
        or plan["numeric_contracts"] != NUMERIC_CONTRACTS
        or plan["qualification_report_id"] != qualification["report_id"]
        or plan["source_operation_ids"] != list(operation_ids)
    ):
        raise ProductionQKVCheckError("physical-plan identities differ")
    problem = _problem(plan["problem"], qualification, capability)
    kernel_ir_id = _kernel(
        root,
        model=model,
        qualification=qualification,
        operations=operations,
        problem=problem,
    )
    sram = _sram(plan["sram"], problem=problem, capability=capability)
    hbm_regions, tiles, image_digest, image_size = _hbm(
        plan["hbm"],
        root,
        qualification=qualification,
        capability=capability,
        payloads=payloads,
        problem=problem,
    )
    command_count = _program(
        plan["program"],
        root,
        capability=capability,
        problem=problem,
        hbm_regions=hbm_regions,
        tiles=tiles,
        sram=sram,
    )
    request_id = _request(
        root,
        model=model,
        qualification=qualification,
        source_operation_ids=operation_ids,
    )
    counters = _expected_counters(problem)
    if plan["expected_counters"] != counters:
        raise ProductionQKVCheckError(
            "physical-plan counters differ from independent accounting"
        )
    reconstructed_sources = []
    for role in SOURCE_ROLES:
        source = qualification["sources"][role]
        reconstructed_sources.append(
            {
                "payload_sha256": hashlib.sha256(payloads[role]).hexdigest(),
                "role": "embedding_row" if role == "embedding" else role,
                "size_bytes": len(payloads[role]),
                "source_tensor": source["tensor"],
            }
        )
    coefficient_size = problem["context_positions"] * problem["coefficient_row_bytes"]
    reconstructed_sources.append(
        {
            "payload_sha256": COEFFICIENT_TABLE_SHA256,
            "role": "rope_coefficient_table",
            "size_bytes": coefficient_size,
            "source_tensor": "qualified.rope.coefficient_table",
        }
    )
    body = {
        "capability_id": capability.capability_id,
        "command_count": command_count,
        "expected_counters": counters,
        "graph_id": model.graph_id,
        "hbm_image_sha256": image_digest,
        "hbm_image_size_bytes": image_size,
        "kernel_ir_id": kernel_ir_id,
        "physical_plan_id": plan["physical_plan_id"],
        "qualification_report_id": qualification["report_id"],
        "reconstructed_sources": reconstructed_sources,
        "request_id": request_id,
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock_id,
        "status": "pass",
    }
    return {**body, "check_id": sha256_bytes(canonical_json_bytes(body))}


__all__ = [
    "CHECK_SCHEMA",
    "ProductionQKVCheckError",
    "check_qkv_candidate",
]
