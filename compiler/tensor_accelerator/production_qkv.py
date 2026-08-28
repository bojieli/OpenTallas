"""Deterministic production compiler for connected Qwen Q/K/V preparation.

The compiler consumes an authenticated production Model Graph, checkpoint lock,
ABI 2.2 capability, and independently retained numeric qualification.  It emits
one physical HBM/SRAM deployment whose command stream causally executes the
embedding, input RMSNorm, three projections, per-head Q/K RMSNorm, and RoPE.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Mapping

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
    ABI_MINOR,
    Engine,
    MATMUL_FINAL,
    MATMUL_INIT,
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
from .qkv_qualification import (
    COEFFICIENT_TABLE_SHA256,
    CONTEXT_POSITIONS,
    HEAD_DIM,
    KEY_VALUE_HEADS,
    QKVQualificationError,
    QUERY_HEADS,
    load_qkv_qualification,
)


COMPILER_VERSION = "tensor-accelerator-production-qkv-0.1.0"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qkv_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qkv_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.qkv_source_lock.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.qkv_expectations.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.qkv_deployment.v1"
HBM_IMAGE_PATH = "memory/hbm_qkv.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"

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


class ProductionQKVBuildError(RuntimeError):
    """Raised when a Q/K/V deployment cannot be built without ambiguity."""


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ProductionQKVBuildError(f"unsafe artifact path {value!r}")
    return path.as_posix()


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _copy_canonical(source: Path, destination: Path) -> None:
    payload = source.read_bytes()
    if not payload.endswith(b"\n"):
        raise ProductionQKVBuildError(f"source artifact is not canonical: {source}")
    destination.write_bytes(payload)


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _identity_binding(
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
        raise ProductionQKVBuildError(
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
        raise ProductionQKVBuildError(
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
        raise ProductionQKVBuildError(
            f"production graph must contain exactly one {kind} over {inputs!r}"
        )
    return matches[0]


def _source_operations(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
) -> tuple[ProductionOperation, ...]:
    sources = qualification["sources"]
    lookup = _one_operation(
        model,
        kind="EMBEDDING_LOOKUP",
        inputs=("input.token_ids", sources["embedding"]["tensor"]),
        numeric_contract=LOOKUP_CONTRACT,
    )
    if len(lookup.outputs) != 1:
        raise ProductionQKVBuildError("embedding lookup output arity differs")
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
        raise ProductionQKVBuildError("layer-input RMSNorm source semantics differ")

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
            raise ProductionQKVBuildError(f"{role.upper()} projection semantics differ")
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
    for role, operation in (("Q", q_norm), ("K", k_norm)):
        if (
            len(operation.outputs) != 1
            or operation.attributes.get("epsilon") != 1e-6
            or operation.attributes.get("normalization_width") != HEAD_DIM
            or operation.attributes.get("layer") != 0
        ):
            raise ProductionQKVBuildError(f"{role} RMSNorm source semantics differ")
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
        raise ProductionQKVBuildError("RoPE source semantics differ")
    result = (lookup, input_norm, *projections, q_norm, k_norm, rope)
    if len({operation.operation_id for operation in result}) != len(result):
        raise ProductionQKVBuildError("Q/K/V source operations are not unique")
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


def _read_locked_sources(
    snapshot: Path,
    lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> dict[str, bytes]:
    sources = qualification["sources"]
    payloads: dict[str, bytes] = {}
    try:
        with LockedCheckpointReader(snapshot, dict(lock)) as reader:
            embedding_source = sources["embedding"]
            embedding_record = reader.tensor_record(embedding_source["tensor"])
            shape = tuple(embedding_record["shape"])
            token_id = qualification["input"]["token_id"]
            if len(shape) != 2 or not 0 <= token_id < shape[0]:
                raise ProductionQKVBuildError(
                    "qualified token is outside the embedding tensor"
                )
            captured, consumer = _capture_row(shape, token_id)
            reader.consume_tensor_payload(embedding_source["tensor"], consumer)
            payloads["embedding"] = bytes(captured)
            if (
                embedding_record["shape"] != embedding_source["shape"]
                or embedding_record["payload_sha256"]
                != embedding_source["payload_sha256"]
                or hashlib.sha256(payloads["embedding"]).hexdigest()
                != qualification["input"]["embedding_row_payload_sha256"]
            ):
                raise ProductionQKVBuildError(
                    "locked embedding differs from qualification evidence"
                )
            for role in SOURCE_ROLES[1:]:
                source = sources[role]
                captured_payload = bytearray()
                record = reader.consume_tensor_payload(
                    source["tensor"], captured_payload.extend
                )
                payload = bytes(captured_payload)
                if (
                    record["shape"] != source["shape"]
                    or record["payload_sha256"] != source["payload_sha256"]
                    or hashlib.sha256(payload).hexdigest() != source["payload_sha256"]
                ):
                    raise ProductionQKVBuildError(
                        f"locked {role} differs from qualification evidence"
                    )
                payloads[role] = payload
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionQKVBuildError(
            f"locked checkpoint payload read failed: {exc}"
        ) from exc
    return payloads


def _problem(
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
        raise ProductionQKVBuildError(
            "Q/K/V source shapes differ from the frozen graph"
        )
    vector = capability.vector_engine
    if (
        capability.command_abi_minor != ABI_MINOR
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
        or not {"bf16_tensor", "vector_fp32"}
        <= set(capability.qualified_execution_modes)
    ):
        raise ProductionQKVBuildError(
            "capability does not qualify the complete Q/K/V operation union"
        )
    projections: list[dict[str, int | str]] = []
    for role, heads in (
        ("q", QUERY_HEADS),
        ("k", KEY_VALUE_HEADS),
        ("v", KEY_VALUE_HEADS),
    ):
        n = heads * HEAD_DIM
        k = 4096
        n_tile = min(64, n, capability.tensor_engine.max_n)
        k_tile = min(256, k, capability.tensor_engine.max_k)
        if (
            capability.tensor_engine.max_m < 1
            or n % n_tile
            or k % k_tile
            or n_tile * k_tile * 2 % capability.hbm.burst_bytes
        ):
            raise ProductionQKVBuildError(
                f"{role.upper()} projection is not exactly tileable"
            )
        projections.append(
            {
                "k": k,
                "k_tile": k_tile,
                "k_tiles": k // k_tile,
                "n": n,
                "n_tile": n_tile,
                "n_tiles": n // n_tile,
                "role": role,
                "tile_count": (n // n_tile) * (k // k_tile),
            }
        )
    return {
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


def _append_region(
    image: bytearray,
    regions: list[dict[str, Any]],
    *,
    capability: ProductionCapability,
    region_id: str,
    source_role: str,
    payload: bytes,
) -> None:
    offset = align_up(len(image), capability.hbm.burst_bytes)
    if offset > len(image):
        image.extend(bytes(offset - len(image)))
    image.extend(payload)
    regions.append(
        {
            "address": capability.hbm.base_address + offset,
            "id": region_id,
            "offset_bytes": offset,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "source_role": source_role,
        }
    )


def _append_projection_tiles(
    image: bytearray,
    tiles: list[dict[str, Any]],
    *,
    capability: ProductionCapability,
    payload: bytes,
    projection: Mapping[str, Any],
) -> None:
    role = projection["role"]
    weights = np.frombuffer(payload, dtype="<u2").reshape(
        projection["n"], projection["k"]
    )
    role_tile_index = 0
    for n_start in range(0, projection["n"], projection["n_tile"]):
        for k_start in range(0, projection["k"], projection["k_tile"]):
            tile = np.ascontiguousarray(
                weights[
                    n_start : n_start + projection["n_tile"],
                    k_start : k_start + projection["k_tile"],
                ],
                dtype="<u2",
            ).tobytes(order="C")
            offset = align_up(len(image), capability.hbm.burst_bytes)
            if offset > len(image):
                image.extend(bytes(offset - len(image)))
            image.extend(tile)
            tiles.append(
                {
                    "address": capability.hbm.base_address + offset,
                    "k_count": projection["k_tile"],
                    "k_start": k_start,
                    "n_count": projection["n_tile"],
                    "n_start": n_start,
                    "offset_bytes": offset,
                    "payload_sha256": hashlib.sha256(tile).hexdigest(),
                    "projection_role": role,
                    "size_bytes": len(tile),
                    "tile_index": role_tile_index,
                }
            )
            role_tile_index += 1


def _hbm_image(
    payloads: Mapping[str, bytes],
    coefficient_payload: bytes,
    *,
    qualification: Mapping[str, Any],
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    image = bytearray()
    regions: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    _append_region(
        image,
        regions,
        capability=capability,
        region_id="embedding_rows",
        source_role="embedding",
        payload=payloads["embedding"],
    )
    _append_region(
        image,
        regions,
        capability=capability,
        region_id="input_norm_weight",
        source_role="input_norm_weight",
        payload=payloads["input_norm_weight"],
    )
    projection_sources: list[dict[str, Any]] = []
    for projection in problem["projections"]:
        role = projection["role"]
        source_role = f"{role}_projection_weight"
        source = qualification["sources"][source_role]
        projection_sources.append(
            {
                "payload_sha256": source["payload_sha256"],
                "projection_role": role,
                "shape": source["shape"],
                "tensor_name": source["tensor"],
            }
        )
        _append_projection_tiles(
            image,
            tiles,
            capability=capability,
            payload=payloads[source_role],
            projection=projection,
        )
    for role in ("q_norm_weight", "k_norm_weight"):
        _append_region(
            image,
            regions,
            capability=capability,
            region_id=role,
            source_role=role,
            payload=payloads[role],
        )
    _append_region(
        image,
        regions,
        capability=capability,
        region_id="rope_coefficient_table",
        source_role="rope_coefficients",
        payload=coefficient_payload,
    )
    if len(image) % capability.hbm.burst_bytes:
        image.extend(
            bytes(align_up(len(image), capability.hbm.burst_bytes) - len(image))
        )
    if len(regions) + len(tiles) > capability.limits["max_hbm_regions"]:
        raise ProductionQKVBuildError("Q/K/V HBM region count exceeds capability")
    return bytes(image), {
        "projection_sources": projection_sources,
        "projection_tiles": tiles,
        "regions": regions,
    }


def _sram_plan(
    problem: Mapping[str, Any], capability: ProductionCapability
) -> dict[str, Any]:
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
    regions: list[dict[str, Any]] = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if bank >= capability.sram.banks or allocated > capability.sram.bytes_per_bank:
            raise ProductionQKVBuildError(
                f"SRAM region {region_id!r} exceeds assigned bank"
            )
        regions.append(
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
    if len(regions) > capability.limits["max_sram_regions"]:
        raise ProductionQKVBuildError("Q/K/V SRAM region count exceeds capability")
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _regions_by_id(sram: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {region["id"]: region for region in sram["regions"]}


def _commands(
    *,
    hbm: Mapping[str, Any],
    sram: Mapping[str, Any],
    problem: Mapping[str, Any],
) -> tuple[ProductionCommand, ...]:
    local = _regions_by_id(sram)
    hbm_regions = {region["id"]: region for region in hbm["regions"]}
    commands: list[ProductionCommand] = [
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=0,
            source0=hbm_regions["embedding_rows"]["address"],
            source1=local["runtime_ids"]["address"],
            destination=local["embedding"]["address"],
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
            destination=local["input_norm_weight"]["address"],
            size0=problem["hidden_width"] * 2,
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
            kernel_index=1,
            source0=local["embedding"]["address"],
            source1=local["input_norm_weight"]["address"],
            destination=local["attention_norm"]["address"],
            size0=1,
            size1=problem["hidden_width"],
            size2=EPSILON_CODE,
        ),
    ]
    tiles_by_role = {
        role: [
            tile for tile in hbm["projection_tiles"] if tile["projection_role"] == role
        ]
        for role in PROJECTION_ROLES
    }
    output_region = {"q": "q_raw", "k": "k_raw", "v": "v"}
    for kernel_index, projection in enumerate(problem["projections"], start=2):
        role = projection["role"]
        for tile in tiles_by_role[role]:
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=kernel_index,
                    source0=tile["address"],
                    destination=local["weight_tile"]["address"],
                    size0=tile["size_bytes"],
                )
            )
            flags = 0
            if tile["k_start"] == 0:
                flags |= MATMUL_INIT
            if tile["k_start"] + tile["k_count"] == projection["k"]:
                flags |= MATMUL_FINAL
            commands.append(
                ProductionCommand(
                    index=len(commands),
                    opcode=Opcode.MATMUL_BF16_TILE,
                    engine=Engine.TENSOR,
                    flags=flags,
                    kernel_index=kernel_index,
                    source0=local["attention_norm"]["address"] + tile["k_start"] * 2,
                    source1=local["weight_tile"]["address"],
                    destination=local["accumulator_tile"]["address"],
                    auxiliary=local[output_region[role]]["address"]
                    + tile["n_start"] * 2,
                    size0=1,
                    size1=tile["n_count"],
                    size2=tile["k_count"],
                )
            )
    for kernel_index, role in ((5, "q"), (6, "k")):
        weight = hbm_regions[f"{role}_norm_weight"]
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=kernel_index,
                source0=weight["address"],
                destination=local[f"{role}_norm_weight"]["address"],
                size0=problem["head_dim"] * 2,
            )
        )
    for kernel_index, role, rows in (
        (5, "q", problem["query_heads"]),
        (6, "k", problem["key_value_heads"]),
    ):
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
                size1=problem["head_dim"],
                size2=EPSILON_CODE,
            )
        )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=7,
            source0=hbm_regions["rope_coefficient_table"]["address"],
            source1=local["runtime_ids"]["address"] + 4,
            destination=local["rope_coefficients"]["address"],
            auxiliary=0,
            size0=problem["coefficient_row_bytes"],
            size1=problem["coefficient_row_bytes"],
            size2=problem["context_positions"],
            size3=4,
        )
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.ROPE_BF16,
            engine=Engine.VECTOR,
            kernel_index=7,
            source0=local["q_norm"]["address"],
            source1=local["k_norm"]["address"],
            destination=local["q_rotary"]["address"],
            auxiliary=local["k_rotary"]["address"],
            size0=problem["query_heads"],
            size1=problem["key_value_heads"],
            size2=problem["head_dim"],
            size3=local["rope_coefficients"]["address"],
        )
    )
    commands.append(
        ProductionCommand(
            index=len(commands), opcode=Opcode.COMPLETE, engine=Engine.CONTROL
        )
    )
    return tuple(commands)


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


def _rmsnorm_kernel(
    *,
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


def _kernel_ir(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ...],
    problem: Mapping[str, Any],
) -> dict[str, Any]:
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
    kernels: list[dict[str, Any]] = [
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
        _rmsnorm_kernel(
            index=1,
            operation=input_norm,
            rows=1,
            width=problem["hidden_width"],
        ),
    ]
    for index, operation, projection in zip(
        (2, 3, 4),
        (q_projection, k_projection, v_projection),
        problem["projections"],
        strict=True,
    ):
        kernels.append(
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
    kernels.extend(
        (
            _rmsnorm_kernel(
                index=5,
                operation=q_norm,
                rows=problem["query_heads"],
                width=problem["head_dim"],
            ),
            _rmsnorm_kernel(
                index=6,
                operation=k_norm,
                rows=problem["key_value_heads"],
                width=problem["head_dim"],
            ),
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
    body = {
        "graph_id": model.graph_id,
        "kernels": kernels,
        "qualification_report_id": qualification["report_id"],
        "schema": KERNEL_SCHEMA,
    }
    return _identified(body, "kernel_ir_id")


def _source_lock(
    *,
    model_graph_path: Path,
    checkpoint_lock_path: Path,
    capability_path: Path,
    qualification_path: Path,
    model: ProductionModelGraph,
    checkpoint_lock: Mapping[str, Any],
    capability: ProductionCapability,
    qualification: Mapping[str, Any],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for role, path in (
        ("model_graph", model_graph_path),
        ("checkpoint_lock", checkpoint_lock_path),
        ("hardware_capability", capability_path),
        ("qualification_report", qualification_path),
    ):
        digest, size = sha256_file(path)
        sources.append({"role": role, "sha256": digest, "size_bytes": size})
    body = {
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": checkpoint_lock["lock_id"],
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "qualification_report_id": qualification["report_id"],
        "schema": SOURCE_LOCK_SCHEMA,
        "sources": sources,
    }
    return _identified(body, "source_lock_id")


def _request(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    source_operation_ids: tuple[str, ...],
) -> dict[str, Any]:
    body = {
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
    return _identified(body, "request_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    source_operation_ids: tuple[str, ...],
    problem: Mapping[str, Any],
    sram: Mapping[str, Any],
    hbm: Mapping[str, Any],
    image: bytes,
    command_payload: bytes,
) -> dict[str, Any]:
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": _expected_counters(problem),
        "graph_id": model.graph_id,
        "hbm": {
            "image": {
                "base_address": capability.hbm.base_address,
                "path": HBM_IMAGE_PATH,
                "sha256": hashlib.sha256(image).hexdigest(),
                "size_bytes": len(image),
            },
            **dict(hbm),
        },
        "numeric_contracts": NUMERIC_CONTRACTS,
        "problem": dict(problem),
        "program": {
            "command_count": len(command_payload[32:]) // 64,
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "qualification_report_id": qualification["report_id"],
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_ids": list(source_operation_ids),
        "sram": dict(sram),
    }
    return _identified(body, "physical_plan_id")


def _artifact(root: Path, path: str, role: str) -> dict[str, Any]:
    relative = _safe_relative(path)
    digest, size = sha256_file(root / relative)
    return {
        "path": relative,
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _manifest(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    kernel_ir: Mapping[str, Any],
    physical_plan: Mapping[str, Any],
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
        "source/checkpoint.lock.json": "checkpoint_lock",
        "source/model_graph.v2.json": "model_graph",
        "source/qualification.json": "qualification_report",
    }
    artifacts = [_artifact(root, path, roles[path]) for path in sorted(roles)]
    body = {
        "artifacts": artifacts,
        "capability_id": capability.capability_id,
        "claim_boundary": [
            "one authenticated Qwen3-8B token through layer-0 Q/K/V preparation",
            "embedding, RMSNorm, segmented Q/K/V projection, per-head normalization, and position-indexed RoPE",
            "deterministic HBM image, explicit 16-bank SRAM plan, independently checked ABI 2.2 program, and artifact-only functional execution",
            "uncharacterized functional evidence only; not attention, KV state, a complete layer, model decoding, timing, RTL, 130-nm, performance, or energy evidence",
        ],
        "command_abi": {
            "major": capability.command_abi_major,
            "minor": capability.command_abi_minor,
        },
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator Q/K/V compiler",
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
        "physical_plan_id": physical_plan["physical_plan_id"],
        "qualification_report_id": qualification["report_id"],
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
    qualification_path: Path,
    root: Path,
) -> dict[str, Any]:
    try:
        checkpoint_lock = load_checkpoint_lock(checkpoint_lock_path)
        model = load_production_model_graph(model_graph_path)
        capability = load_production_capability(capability_path)
        qualification = load_qkv_qualification(qualification_path)
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        QKVQualificationError,
    ) as exc:
        raise ProductionQKVBuildError(f"source admission failed: {exc}") from exc
    if qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]:
        raise ProductionQKVBuildError(
            "qualification and checkpoint lock identities differ"
        )
    for role in SOURCE_ROLES:
        source = qualification["sources"][role]
        shape, digest = _identity_binding(
            model,
            source["tensor"],
            checkpoint_lock_id=checkpoint_lock["lock_id"],
            rank=len(source["shape"]),
        )
        if list(shape) != source["shape"] or digest != source["payload_sha256"]:
            raise ProductionQKVBuildError(
                f"qualification {role} differs from production graph binding"
            )
    operations = _source_operations(model, qualification)
    operation_ids = tuple(operation.operation_id for operation in operations)
    problem = _problem(qualification, capability)
    payloads = _read_locked_sources(snapshot, checkpoint_lock, qualification)
    coefficient_table = coefficient_table_bf16(problem["context_positions"])
    coefficient_payload = np.ascontiguousarray(coefficient_table, dtype="<u2").tobytes(
        order="C"
    )
    if (
        coefficient_table.shape
        != (problem["context_positions"], 2 * problem["head_dim"])
        or hashlib.sha256(coefficient_payload).hexdigest() != COEFFICIENT_TABLE_SHA256
        or qualification["rope"]["coefficient_table_payload_sha256"]
        != COEFFICIENT_TABLE_SHA256
    ):
        raise ProductionQKVBuildError("RoPE coefficient table identity differs")
    image, hbm = _hbm_image(
        payloads,
        coefficient_payload,
        qualification=qualification,
        problem=problem,
        capability=capability,
    )
    if len(image) > capability.hbm.capacity_bytes:
        raise ProductionQKVBuildError("Q/K/V HBM image exceeds capability")
    sram = _sram_plan(problem, capability)
    commands = _commands(hbm=hbm, sram=sram, problem=problem)
    if len(commands) > capability.limits["max_commands"]:
        raise ProductionQKVBuildError("Q/K/V command count exceeds capability")
    expected = _expected_counters(problem)
    if len(commands) != expected["command_count"]:
        raise ProductionQKVBuildError("Q/K/V command count accounting differs")
    command_payload = encode(commands, abi_minor=capability.command_abi_minor)
    kernel_ir = _kernel_ir(
        model=model,
        qualification=qualification,
        operations=operations,
        problem=problem,
    )
    plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        source_operation_ids=operation_ids,
        problem=problem,
        sram=sram,
        hbm=hbm,
        image=image,
        command_payload=command_payload,
    )
    source_lock = _source_lock(
        model_graph_path=model_graph_path,
        checkpoint_lock_path=checkpoint_lock_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        model=model,
        checkpoint_lock=checkpoint_lock,
        capability=capability,
        qualification=qualification,
    )
    request = _request(
        model=model,
        qualification=qualification,
        source_operation_ids=operation_ids,
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
    write_canonical_json(root / PHYSICAL_PLAN_PATH, plan)
    (root / COMMAND_PATH).write_bytes(command_payload)
    _write_text(
        root / "program/commands.disasm",
        disassemble(commands, abi_minor=capability.command_abi_minor),
    )
    write_canonical_json(root / REQUEST_PATH, request)
    write_canonical_json(root / "source.lock.json", source_lock)
    _copy_canonical(checkpoint_lock_path, root / "source/checkpoint.lock.json")
    _copy_canonical(model_graph_path, root / "source/model_graph.v2.json")
    _copy_canonical(qualification_path, root / "source/qualification.json")

    from .production_qkv_checking import check_qkv_candidate

    independent_check = check_qkv_candidate(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        root=root,
    )
    write_canonical_json(root / "checks/independent_check.json", independent_check)
    expectations_body = {
        "check_id": independent_check["check_id"],
        "counters": independent_check["expected_counters"],
        "intermediate_payload_sha256": {
            role: qualification["intermediates"][role]["payload_sha256"]
            for role in sorted(qualification["intermediates"])
        },
        "output_payload_sha256": {
            role: qualification["outputs"][role]["payload_sha256"]
            for role in sorted(qualification["outputs"])
        },
        "qualification_report_id": qualification["report_id"],
        "schema": EXPECTATIONS_SCHEMA,
    }
    write_canonical_json(
        root / "execution_expectations.json",
        _identified(expectations_body, "expectations_id"),
    )
    manifest = _manifest(
        root,
        model=model,
        qualification=qualification,
        capability=capability,
        kernel_ir=kernel_ir,
        physical_plan=plan,
        source_lock=source_lock,
        independent_check=independent_check,
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_qkv_deployment(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Build and atomically publish one independently checked Q/K/V deployment."""

    snapshot = Path(snapshot).resolve()
    checkpoint_lock_path = Path(checkpoint_lock_path).resolve()
    model_graph_path = Path(model_graph_path).resolve()
    capability_path = Path(capability_path).resolve()
    qualification_path = Path(qualification_path).resolve()
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise ProductionQKVBuildError(f"checkpoint snapshot does not exist: {snapshot}")
    for label, path in (
        ("checkpoint lock", checkpoint_lock_path),
        ("model graph", model_graph_path),
        ("capability", capability_path),
        ("qualification report", qualification_path),
    ):
        if not path.is_file():
            raise ProductionQKVBuildError(f"{label} does not exist: {path}")
    if output.exists():
        raise ProductionQKVBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        manifest = _build_into(
            snapshot=snapshot,
            checkpoint_lock_path=checkpoint_lock_path,
            model_graph_path=model_graph_path,
            capability_path=capability_path,
            qualification_path=qualification_path,
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
    "ProductionQKVBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_qkv_deployment",
]
