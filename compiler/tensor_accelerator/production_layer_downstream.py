"""Deterministic compiler for the authentic Qwen layer-0 downstream path.

The deployment begins with the retained attention result and authentic hidden-0
residual, then executes output projection, residual add, post-attention RMSNorm,
gate/up projections, materialized-BF16 SiLU multiply, down projection, and the
final residual.  Physical addresses appear only after the neutral Kernel IR.
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

from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from .layer_qualification import (
    LayerQualificationError,
    load_layer_qualification,
)
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_command import (
    ELEMENTWISE_ABI_MINOR,
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


COMPILER_VERSION = "tensor-accelerator-production-layer-downstream-0.1.0"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_source_lock.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_expectations.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_deployment.v1"
HBM_IMAGE_PATH = "memory/hbm_layer_downstream.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"

ADD_CONTRACT = "bf16_add_rne_v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
SILU_CONTRACT = "qwen3_silu_mul_bf16_v1"
NUMERIC_CONTRACTS = [
    ADD_CONTRACT,
    MATRIX_CONTRACT,
    RMSNORM_CONTRACT,
    SILU_CONTRACT,
]
CLAIM_BOUNDARY = [
    "authenticated Qwen3-8B layer-0 attention output and hidden residual through the complete post-attention and MLP path",
    "output projection, two BF16 residual adds, post-attention RMSNorm, gate/up/down projections, and materialized-BF16 SiLU multiply",
    "neutral kernels, explicit 13-bank SRAM placement, tiled HBM weights, independently checked ABI 2.4 commands, and artifact-only functional execution",
    "uncharacterized downstream-slice evidence only; not a connected complete layer, model decode, timing, RTL, 130-nm, performance, or energy claim",
]
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
ROWS = 1
N_TILE = 64
K_TILE = 256

SOURCE_ROLES = (
    "embedding",
    "attention_output_weight",
    "post_attention_norm_weight",
    "gate_projection_weight",
    "up_projection_weight",
    "down_projection_weight",
)

PROJECTION_DEFINITIONS = (
    {
        "id": "attention_output",
        "input_region": "attention",
        "kernel_index": 0,
        "output_region": "attention_projected",
        "source_role": "attention_output_weight",
    },
    {
        "id": "gate",
        "input_region": "mlp_norm",
        "kernel_index": 3,
        "output_region": "gate",
        "source_role": "gate_projection_weight",
    },
    {
        "id": "up",
        "input_region": "mlp_norm",
        "kernel_index": 4,
        "output_region": "up",
        "source_role": "up_projection_weight",
    },
    {
        "id": "down",
        "input_region": "gated_mlp",
        "kernel_index": 6,
        "output_region": "down",
        "source_role": "down_projection_weight",
    },
)


class ProductionLayerDownstreamBuildError(ArtifactError):
    """Raised when the downstream deployment cannot be built exactly."""


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ProductionLayerDownstreamBuildError(f"unsafe artifact path {value!r}")
    return path.as_posix()


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _copy_canonical(source: Path, destination: Path) -> None:
    payload = source.read_bytes()
    value = load_strict_json(source)
    if payload != canonical_json_bytes(value):
        raise ProductionLayerDownstreamBuildError(
            f"source artifact is not canonical: {source}"
        )
    destination.write_bytes(payload)


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


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
        raise ProductionLayerDownstreamBuildError(
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
        raise ProductionLayerDownstreamBuildError(
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
        raise ProductionLayerDownstreamBuildError(
            f"production graph must contain exactly one {kind} over {inputs!r}"
        )
    return matches[0]


def _source_operations(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
) -> tuple[ProductionOperation, ...]:
    sources = qualification["sources"]
    attention_output = _one_operation(
        model,
        kind="MATMUL",
        inputs=(
            "layer.0.attention",
            sources["attention_output_weight"]["tensor"],
        ),
        numeric_contract=MATRIX_CONTRACT,
    )
    first_add = _one_operation(
        model,
        kind="ADD",
        inputs=("hidden.0", attention_output.outputs[0]),
        numeric_contract=ADD_CONTRACT,
    )
    rmsnorm = _one_operation(
        model,
        kind="RMS_NORM",
        inputs=(
            first_add.outputs[0],
            sources["post_attention_norm_weight"]["tensor"],
        ),
        numeric_contract=RMSNORM_CONTRACT,
    )
    gate = _one_operation(
        model,
        kind="MATMUL",
        inputs=(rmsnorm.outputs[0], sources["gate_projection_weight"]["tensor"]),
        numeric_contract=MATRIX_CONTRACT,
    )
    up = _one_operation(
        model,
        kind="MATMUL",
        inputs=(rmsnorm.outputs[0], sources["up_projection_weight"]["tensor"]),
        numeric_contract=MATRIX_CONTRACT,
    )
    silu = _one_operation(
        model,
        kind="SILU_MUL",
        inputs=(gate.outputs[0], up.outputs[0]),
        numeric_contract=SILU_CONTRACT,
    )
    down = _one_operation(
        model,
        kind="MATMUL",
        inputs=(silu.outputs[0], sources["down_projection_weight"]["tensor"]),
        numeric_contract=MATRIX_CONTRACT,
    )
    final_add = _one_operation(
        model,
        kind="ADD",
        inputs=(first_add.outputs[0], down.outputs[0]),
        numeric_contract=ADD_CONTRACT,
    )
    operations = (
        attention_output,
        first_add,
        rmsnorm,
        gate,
        up,
        silu,
        down,
        final_add,
    )
    expected_ids = tuple(f"node.{index:04d}" for index in range(10, 18))
    if tuple(operation.operation_id for operation in operations) != expected_ids:
        raise ProductionLayerDownstreamBuildError(
            "layer-0 downstream operation sequence differs"
        )
    widths = (4096, 4096, 4096, 12288, 12288, 12288, 4096, 4096)
    for operation, width in zip(operations, widths, strict=True):
        output = (
            model.tensor_by_id.get(operation.outputs[0])
            if len(operation.outputs) == 1
            else None
        )
        if (
            len(operation.outputs) != 1
            or operation.attributes.get("layer") != 0
            or output is None
            or output.dtype != "bf16"
            or output.shape != (1, "span_tokens", width)
        ):
            raise ProductionLayerDownstreamBuildError(
                f"source semantics differ for {operation.operation_id}"
            )
    if any(
        operation.attributes.get("transpose_weight") is not True
        for operation in (attention_output, gate, up, down)
    ):
        raise ProductionLayerDownstreamBuildError(
            "downstream projection transpose semantics differ"
        )
    if (
        rmsnorm.attributes.get("epsilon") != 1e-6
        or rmsnorm.attributes.get("normalization_width") != HIDDEN_WIDTH
    ):
        raise ProductionLayerDownstreamBuildError(
            "post-attention RMSNorm semantics differ"
        )
    return operations


def _load_attention(
    path: Path,
    qualification: Mapping[str, Any],
) -> bytes:
    try:
        raw = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionLayerDownstreamBuildError(
            f"cannot load attention execution: {exc}"
        ) from exc
    if raw != canonical_json_bytes(value):
        raise ProductionLayerDownstreamBuildError(
            "attention execution is not canonical JSON"
        )
    body = {key: item for key, item in value.items() if key != "report_id"}
    binding = qualification["attention_input"]
    attention = value.get("outputs", {}).get("attention")
    if (
        value.get("schema") != "opentallas.tensor_accelerator.attention_execution.v1"
        or value.get("status") != "pass"
        or value.get("report_id") != sha256_bytes(canonical_json_bytes(body))
        or value.get("report_id") != binding["report_id"]
        or value.get("build_id") != binding["build_id"]
        or value.get("qualification_report_id") != binding["qualification_report_id"]
        or not isinstance(attention, dict)
        or attention.get("dtype") != "bf16"
        or attention.get("shape") != [1, 32, 128]
        or attention.get("size_bytes") != HIDDEN_WIDTH * 2
        or attention.get("payload_sha256") != binding["payload_sha256"]
        or not isinstance(attention.get("codes"), list)
        or len(attention["codes"]) != HIDDEN_WIDTH
    ):
        raise ProductionLayerDownstreamBuildError(
            "attention execution identity or output differs"
        )
    raw_codes = attention["codes"]
    if any(
        isinstance(code, bool) or not isinstance(code, int) or code < 0 or code > 0xFFFF
        for code in raw_codes
    ):
        raise ProductionLayerDownstreamBuildError(
            "attention output codes are malformed"
        )
    codes = np.asarray(raw_codes, dtype=np.uint16)
    payload = codes.astype("<u2", copy=False).tobytes(order="C")
    if hashlib.sha256(payload).hexdigest() != binding["payload_sha256"]:
        raise ProductionLayerDownstreamBuildError(
            "attention output payload identity differs"
        )
    return payload


def _capture_embedding_row(
    reader: LockedCheckpointReader,
    tensor_name: str,
    *,
    token_id: int,
    row_bytes: int,
) -> tuple[Mapping[str, Any], bytes]:
    start = token_id * row_bytes
    end = start + row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        chunk_end = cursor + len(chunk)
        overlap_start = max(cursor, start)
        overlap_end = min(chunk_end, end)
        if overlap_start < overlap_end:
            captured.extend(chunk[overlap_start - cursor : overlap_end - cursor])
        cursor = chunk_end

    record = reader.consume_tensor_payload(tensor_name, consume)
    if len(captured) != row_bytes:
        raise ProductionLayerDownstreamBuildError(
            "locked embedding row coverage differs"
        )
    return record, bytes(captured)


def _read_locked_sources(
    snapshot: Path,
    checkpoint_lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    try:
        with LockedCheckpointReader(snapshot, checkpoint_lock) as reader:
            embedding = qualification["sources"]["embedding"]
            record, payload = _capture_embedding_row(
                reader,
                embedding["tensor"],
                token_id=qualification["input"]["token_id"],
                row_bytes=HIDDEN_WIDTH * 2,
            )
            if (
                record.get("dtype") != "BF16"
                or record.get("shape") != embedding["shape"]
                or record.get("payload_sha256") != embedding["payload_sha256"]
                or hashlib.sha256(payload).hexdigest()
                != qualification["input"]["embedding_row_payload_sha256"]
            ):
                raise ProductionLayerDownstreamBuildError(
                    "locked embedding identity differs"
                )
            payloads["hidden_0"] = payload
            for role in SOURCE_ROLES:
                if role == "embedding":
                    continue
                source = qualification["sources"][role]
                captured = bytearray()
                record = reader.consume_tensor_payload(
                    source["tensor"], captured.extend
                )
                payload = bytes(captured)
                if (
                    record.get("dtype") != "BF16"
                    or record.get("shape") != source["shape"]
                    or record.get("payload_sha256") != source["payload_sha256"]
                    or hashlib.sha256(payload).hexdigest() != source["payload_sha256"]
                ):
                    raise ProductionLayerDownstreamBuildError(
                        f"locked {role} identity differs"
                    )
                payloads[role] = payload
    except CheckpointError as exc:
        raise ProductionLayerDownstreamBuildError(
            f"locked checkpoint read failed: {exc}"
        ) from exc
    return payloads


def _problem(
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, Any]:
    expected_shapes = {
        "attention_output": [HIDDEN_WIDTH, HIDDEN_WIDTH],
        "gate": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "up": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "down": [HIDDEN_WIDTH, INTERMEDIATE_WIDTH],
    }
    if (
        capability.command_abi_minor != ELEMENTWISE_ABI_MINOR
        or capability.vector_engine is None
        or capability.vector_engine.max_rows < ROWS
        or capability.vector_engine.max_width < INTERMEDIATE_WIDTH
        or not set(NUMERIC_CONTRACTS) <= set(capability.qualified_numeric_contracts)
        or capability.tensor_engine.max_m < ROWS
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
    ):
        raise ProductionLayerDownstreamBuildError(
            "downstream problem exceeds the qualified capability"
        )
    projections: list[dict[str, Any]] = []
    for definition in PROJECTION_DEFINITIONS:
        source = qualification["sources"][definition["source_role"]]
        n, k = source["shape"]
        if source["shape"] != expected_shapes[definition["id"]]:
            raise ProductionLayerDownstreamBuildError(
                f"{definition['id']} projection shape differs"
            )
        if n % N_TILE or k % K_TILE:
            raise ProductionLayerDownstreamBuildError(
                f"{definition['id']} projection is not exactly tileable"
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
    return {
        "hidden_width": HIDDEN_WIDTH,
        "intermediate_width": INTERMEDIATE_WIDTH,
        "projections": projections,
        "rows": ROWS,
    }


def _sram_plan(
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, Any]:
    hidden_bytes = problem["hidden_width"] * 2
    intermediate_bytes = problem["intermediate_width"] * 2
    specs = (
        ("hidden_0", 0, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("attention", 1, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("weight_tile", 2, "bf16", [N_TILE, K_TILE], N_TILE * K_TILE * 2),
        ("accumulator_tile", 3, "fp32", [1, N_TILE], N_TILE * 4),
        ("attention_projected", 4, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("post_attention", 5, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("post_attention_norm_weight", 6, "bf16", [HIDDEN_WIDTH], hidden_bytes),
        ("mlp_norm", 7, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("gate", 8, "bf16", [1, INTERMEDIATE_WIDTH], intermediate_bytes),
        ("up", 9, "bf16", [1, INTERMEDIATE_WIDTH], intermediate_bytes),
        ("gated_mlp", 10, "bf16", [1, INTERMEDIATE_WIDTH], intermediate_bytes),
        ("down", 11, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
        ("hidden_1", 12, "bf16", [1, HIDDEN_WIDTH], hidden_bytes),
    )
    regions: list[dict[str, Any]] = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if bank >= capability.sram.banks or allocated > capability.sram.bytes_per_bank:
            raise ProductionLayerDownstreamBuildError(
                f"SRAM region {region_id!r} exceeds its assigned bank"
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
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _append_hbm_region(
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


def _hbm_image(
    *,
    payloads: Mapping[str, bytes],
    attention_payload: bytes,
    qualification: Mapping[str, Any],
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    image = bytearray()
    regions = [
        _append_hbm_region(
            image,
            capability=capability,
            region_id="hidden_0",
            payload=payloads["hidden_0"],
            source={
                "kind": "checkpoint_row",
                "payload_sha256": qualification["input"][
                    "embedding_row_payload_sha256"
                ],
                "row": qualification["input"]["token_id"],
                "tensor_name": qualification["sources"]["embedding"]["tensor"],
            },
        ),
        _append_hbm_region(
            image,
            capability=capability,
            region_id="attention",
            payload=attention_payload,
            source={
                "build_id": qualification["attention_input"]["build_id"],
                "kind": "retained_execution_output",
                "report_id": qualification["attention_input"]["report_id"],
            },
        ),
        _append_hbm_region(
            image,
            capability=capability,
            region_id="post_attention_norm_weight",
            payload=payloads["post_attention_norm_weight"],
            source={
                "kind": "checkpoint_tensor",
                "payload_sha256": qualification["sources"][
                    "post_attention_norm_weight"
                ]["payload_sha256"],
                "shape": [HIDDEN_WIDTH],
                "tensor_name": qualification["sources"]["post_attention_norm_weight"][
                    "tensor"
                ],
            },
        ),
    ]
    by_id = {item["id"]: item for item in problem["projections"]}
    projections: list[dict[str, Any]] = []
    for definition in PROJECTION_DEFINITIONS:
        problem_definition = by_id[definition["id"]]
        source = qualification["sources"][definition["source_role"]]
        projections.append(
            _append_projection(
                image,
                capability=capability,
                definition=problem_definition,
                payload=payloads[definition["source_role"]],
                source={
                    "kind": "checkpoint_tensor",
                    "payload_sha256": source["payload_sha256"],
                    "shape": source["shape"],
                    "tensor_name": source["tensor"],
                },
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


def _by_id(records: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {record["id"]: record for record in records}


def _append_projection_commands(
    commands: list[ProductionCommand],
    *,
    projection: Mapping[str, Any],
    problem: Mapping[str, Any],
    sram: Mapping[str, Mapping[str, Any]],
) -> None:
    definition = next(
        item for item in problem["projections"] if item["id"] == projection["id"]
    )
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
        if tile["k_start"] + tile["k_count"] == definition["k"]:
            flags |= MATMUL_FINAL
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.MATMUL_BF16_TILE,
                engine=Engine.TENSOR,
                flags=flags,
                kernel_index=projection["kernel_index"],
                source0=(
                    sram[projection["input_region"]]["address"] + tile["k_start"] * 2
                ),
                source1=sram["weight_tile"]["address"],
                destination=sram["accumulator_tile"]["address"],
                auxiliary=(
                    sram[projection["output_region"]]["address"] + tile["n_start"] * 2
                ),
                size0=ROWS,
                size1=tile["n_count"],
                size2=tile["k_count"],
            )
        )


def _commands(
    *,
    hbm: Mapping[str, Any],
    sram_plan: Mapping[str, Any],
    problem: Mapping[str, Any],
) -> tuple[ProductionCommand, ...]:
    sram = _by_id(sram_plan["regions"])
    direct = _by_id(hbm["regions"])
    projections = _by_id(hbm["projections"])
    commands: list[ProductionCommand] = []
    for region_id, kernel_index in (("hidden_0", 1), ("attention", 0)):
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=kernel_index,
                source0=direct[region_id]["address"],
                destination=sram[region_id]["address"],
                size0=direct[region_id]["size_bytes"],
            )
        )
    _append_projection_commands(
        commands,
        projection=projections["attention_output"],
        problem=problem,
        sram=sram,
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.ADD_BF16,
            engine=Engine.VECTOR,
            kernel_index=1,
            source0=sram["hidden_0"]["address"],
            source1=sram["attention_projected"]["address"],
            destination=sram["post_attention"]["address"],
            size0=ROWS,
            size1=HIDDEN_WIDTH,
        )
    )
    norm = direct["post_attention_norm_weight"]
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.DMA_HBM_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=2,
            source0=norm["address"],
            destination=sram["post_attention_norm_weight"]["address"],
            size0=norm["size_bytes"],
        )
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
            kernel_index=2,
            source0=sram["post_attention"]["address"],
            source1=sram["post_attention_norm_weight"]["address"],
            destination=sram["mlp_norm"]["address"],
            size0=ROWS,
            size1=HIDDEN_WIDTH,
            size2=EPSILON_CODE,
        )
    )
    for role in ("gate", "up"):
        _append_projection_commands(
            commands,
            projection=projections[role],
            problem=problem,
            sram=sram,
        )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.SILU_MUL_BF16,
            engine=Engine.VECTOR,
            kernel_index=5,
            source0=sram["gate"]["address"],
            source1=sram["up"]["address"],
            destination=sram["gated_mlp"]["address"],
            size0=ROWS,
            size1=INTERMEDIATE_WIDTH,
        )
    )
    _append_projection_commands(
        commands,
        projection=projections["down"],
        problem=problem,
        sram=sram,
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.ADD_BF16,
            engine=Engine.VECTOR,
            kernel_index=7,
            source0=sram["post_attention"]["address"],
            source1=sram["down"]["address"],
            destination=sram["hidden_1"]["address"],
            size0=ROWS,
            size1=HIDDEN_WIDTH,
        )
    )
    commands.append(
        ProductionCommand(
            index=len(commands),
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        )
    )
    return tuple(commands)


def _expected_counters(problem: Mapping[str, Any]) -> dict[str, int]:
    projections = problem["projections"]
    tile_count = sum(item["tile_count"] for item in projections)
    weight_bytes = sum(item["n"] * item["k"] * 2 for item in projections)
    direct_bytes = 3 * HIDDEN_WIDTH * 2
    accumulator_writes = sum(
        item["tile_count"] * ROWS * item["n_tile"] * 4 for item in projections
    )
    accumulator_reads = sum(
        item["n_tiles"] * (item["k_tiles"] - 1) * ROWS * item["n_tile"] * 4
        for item in projections
    )
    matrix_input_reads = sum(
        item["tile_count"] * ROWS * item["k_tile"] * 2 for item in projections
    )
    matrix_output_writes = sum(item["n"] * 2 for item in projections)
    scalar_operations = sum(item["n"] * item["k"] for item in projections)
    dma_count = tile_count + 3
    return {
        "accumulator_sram_bytes_read": accumulator_reads,
        "accumulator_sram_bytes_written": accumulator_writes,
        "add_command_count": 2,
        "add_input_sram_bytes_read": 4 * HIDDEN_WIDTH * 2,
        "add_output_sram_bytes_written": 2 * HIDDEN_WIDTH * 2,
        "command_count": 2 * tile_count + 8,
        "complete_command_count": 1,
        "dma_command_count": dma_count,
        "dma_sram_bytes_written": weight_bytes + direct_bytes,
        "epsilon_additions": 1,
        "final_weight_multiplications": HIDDEN_WIDTH,
        "hbm_transferred_bytes_read": weight_bytes + direct_bytes,
        "hbm_useful_bytes_read": weight_bytes + direct_bytes,
        "input_square_multiplications": HIDDEN_WIDTH,
        "matrix_input_sram_bytes_read": matrix_input_reads,
        "matrix_output_sram_bytes_written": matrix_output_writes,
        "matmul_command_count": tile_count,
        "mean_divisions": 1,
        "normalization_multiplications": HIDDEN_WIDTH,
        "projection_accumulation_additions": scalar_operations,
        "projection_multiplications": scalar_operations,
        "reciprocal_square_roots": 1,
        "reduction_additions": HIDDEN_WIDTH - 1,
        "residual_additions": 2 * HIDDEN_WIDTH,
        "rmsnorm_command_count": 1,
        "rmsnorm_input_sram_bytes_read": HIDDEN_WIDTH * 2,
        "rmsnorm_output_sram_bytes_written": HIDDEN_WIDTH * 2,
        "rmsnorm_weight_sram_bytes_read": HIDDEN_WIDTH * 2,
        "sigmoid_denominator_additions": INTERMEDIATE_WIDTH,
        "sigmoid_divisions": INTERMEDIATE_WIDTH,
        "sigmoid_exponentials": INTERMEDIATE_WIDTH,
        "silu_command_count": 1,
        "silu_input_sram_bytes_read": 2 * INTERMEDIATE_WIDTH * 2,
        "silu_multiplications": INTERMEDIATE_WIDTH,
        "silu_output_sram_bytes_written": INTERMEDIATE_WIDTH * 2,
        "up_gate_multiplications": INTERMEDIATE_WIDTH,
        "weight_sram_bytes_read": weight_bytes,
    }


def _matmul_kernel(
    operation: ProductionOperation,
    *,
    index: int,
    n: int,
    k: int,
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
        "shape": {"reduction_width": k, "rows": ROWS, "width": n},
        "source_operation_id": operation.operation_id,
    }


def _add_kernel(operation: ProductionOperation, *, index: int) -> dict[str, Any]:
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
        "shape": {"rows": ROWS, "width": HIDDEN_WIDTH},
        "source_operation_id": operation.operation_id,
    }


def _kernel_ir(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ...],
) -> dict[str, Any]:
    kernels = [
        _matmul_kernel(operations[0], index=0, n=HIDDEN_WIDTH, k=HIDDEN_WIDTH),
        _add_kernel(operations[1], index=1),
        {
            "attributes": {
                "epsilon_binary32_code": EPSILON_CODE,
                "final_weight_product": "bf16_multiply_then_bf16_rne",
                "normalized_boundary": "bf16_rne_before_weight",
                "reduction_order": "canonical_balanced_binary32_tree",
                "rsqrt": "correctly_rounded_binary32_rne",
            },
            "index": 2,
            "inputs": list(operations[2].inputs),
            "kind": "RMS_NORM",
            "numeric_contract": RMSNORM_CONTRACT,
            "outputs": list(operations[2].outputs),
            "shape": {"rows": ROWS, "width": HIDDEN_WIDTH},
            "source_operation_id": operations[2].operation_id,
        },
        _matmul_kernel(operations[3], index=3, n=INTERMEDIATE_WIDTH, k=HIDDEN_WIDTH),
        _matmul_kernel(operations[4], index=4, n=INTERMEDIATE_WIDTH, k=HIDDEN_WIDTH),
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
            "index": 5,
            "inputs": list(operations[5].inputs),
            "kind": "SILU_MUL",
            "numeric_contract": SILU_CONTRACT,
            "outputs": list(operations[5].outputs),
            "shape": {"rows": ROWS, "width": INTERMEDIATE_WIDTH},
            "source_operation_id": operations[5].operation_id,
        },
        _matmul_kernel(operations[6], index=6, n=HIDDEN_WIDTH, k=INTERMEDIATE_WIDTH),
        _add_kernel(operations[7], index=7),
    ]
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
    attention_execution_path: Path,
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
        ("attention_execution", attention_execution_path),
    ):
        digest, size = sha256_file(path)
        sources.append({"role": role, "sha256": digest, "size_bytes": size})
    body = {
        "attention_execution_report_id": qualification["attention_input"]["report_id"],
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
    operation_ids: tuple[str, ...],
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
        "inputs": {
            "attention_execution_report_id": qualification["attention_input"][
                "report_id"
            ],
            "token_id": qualification["input"]["token_id"],
        },
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": list(operation_ids),
    }
    return _identified(body, "request_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    operation_ids: tuple[str, ...],
    problem: Mapping[str, Any],
    sram: Mapping[str, Any],
    hbm: Mapping[str, Any],
    command_payload: bytes,
) -> dict[str, Any]:
    counters = _expected_counters(problem)
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": counters,
        "graph_id": model.graph_id,
        "hbm": dict(hbm),
        "numeric_contracts": NUMERIC_CONTRACTS,
        "problem": dict(problem),
        "program": {
            "command_count": counters["command_count"],
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "qualification_report_id": qualification["report_id"],
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_ids": list(operation_ids),
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
        "source/attention_execution.json": "attention_execution_report",
        "source/checkpoint.lock.json": "checkpoint_lock",
        "source/model_graph.v2.json": "model_graph",
        "source/qualification.json": "qualification_report",
    }
    body = {
        "artifacts": [_artifact(root, path, roles[path]) for path in sorted(roles)],
        "capability_id": capability.capability_id,
        "claim_boundary": CLAIM_BOUNDARY,
        "command_abi": {
            "major": capability.command_abi_major,
            "minor": capability.command_abi_minor,
        },
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator layer-downstream compiler",
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
    attention_execution_path: Path,
    root: Path,
) -> dict[str, Any]:
    try:
        checkpoint_lock = load_checkpoint_lock(checkpoint_lock_path)
        model = load_production_model_graph(model_graph_path)
        capability = load_production_capability(capability_path)
        qualification = load_layer_qualification(qualification_path)
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        LayerQualificationError,
    ) as exc:
        raise ProductionLayerDownstreamBuildError(
            f"source admission failed: {exc}"
        ) from exc
    if qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]:
        raise ProductionLayerDownstreamBuildError(
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
            raise ProductionLayerDownstreamBuildError(
                f"qualification {role} differs from production graph binding"
            )
    operations = _source_operations(model, qualification)
    operation_ids = tuple(operation.operation_id for operation in operations)
    problem = _problem(qualification, capability)
    payloads = _read_locked_sources(snapshot, checkpoint_lock, qualification)
    attention_payload = _load_attention(attention_execution_path, qualification)
    image, hbm = _hbm_image(
        payloads=payloads,
        attention_payload=attention_payload,
        qualification=qualification,
        problem=problem,
        capability=capability,
    )
    if len(image) > capability.hbm.capacity_bytes:
        raise ProductionLayerDownstreamBuildError(
            "layer-downstream HBM image exceeds capability"
        )
    sram = _sram_plan(problem, capability)
    commands = _commands(hbm=hbm, sram_plan=sram, problem=problem)
    if len(commands) > capability.limits["max_commands"]:
        raise ProductionLayerDownstreamBuildError(
            "layer-downstream command count exceeds capability"
        )
    expected_counters = _expected_counters(problem)
    if len(commands) != expected_counters["command_count"]:
        raise ProductionLayerDownstreamBuildError(
            "layer-downstream command accounting differs"
        )
    command_payload = encode(commands, abi_minor=ELEMENTWISE_ABI_MINOR)
    kernel_ir = _kernel_ir(
        model=model,
        qualification=qualification,
        operations=operations,
    )
    physical_plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        operation_ids=operation_ids,
        problem=problem,
        sram=sram,
        hbm=hbm,
        command_payload=command_payload,
    )
    source_lock = _source_lock(
        model_graph_path=model_graph_path,
        checkpoint_lock_path=checkpoint_lock_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        attention_execution_path=attention_execution_path,
        model=model,
        checkpoint_lock=checkpoint_lock,
        capability=capability,
        qualification=qualification,
    )
    request = _request(
        model=model,
        qualification=qualification,
        operation_ids=operation_ids,
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
    _copy_canonical(
        attention_execution_path,
        root / "source/attention_execution.json",
    )
    _copy_canonical(checkpoint_lock_path, root / "source/checkpoint.lock.json")
    _copy_canonical(model_graph_path, root / "source/model_graph.v2.json")
    _copy_canonical(qualification_path, root / "source/qualification.json")

    from .production_layer_downstream_checking import (
        check_layer_downstream_candidate,
    )

    independent_check = check_layer_downstream_candidate(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        qualification_path=qualification_path,
        attention_execution_path=attention_execution_path,
        root=root,
    )
    write_canonical_json(
        root / "checks/independent_check.json",
        independent_check,
    )
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
            "qualification_report_id": qualification["report_id"],
            "saturated_element_count": independent_check[
                "expected_saturated_element_count"
            ],
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
        physical_plan=physical_plan,
        source_lock=source_lock,
        independent_check=independent_check,
    )
    write_canonical_json(root / "deployment_manifest.json", manifest)
    return manifest


def build_layer_downstream_deployment(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    attention_execution_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Build and atomically publish one independently checked downstream slice."""

    sources = {
        "checkpoint snapshot": Path(snapshot).resolve(),
        "checkpoint lock": Path(checkpoint_lock_path).resolve(),
        "model graph": Path(model_graph_path).resolve(),
        "capability": Path(capability_path).resolve(),
        "qualification report": Path(qualification_path).resolve(),
        "attention execution report": Path(attention_execution_path).resolve(),
    }
    output = Path(output).resolve()
    if not sources["checkpoint snapshot"].is_dir():
        raise ProductionLayerDownstreamBuildError(
            f"checkpoint snapshot does not exist: {sources['checkpoint snapshot']}"
        )
    for label, path in sources.items():
        if label != "checkpoint snapshot" and not path.is_file():
            raise ProductionLayerDownstreamBuildError(f"{label} does not exist: {path}")
    if output.exists():
        raise ProductionLayerDownstreamBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        manifest = _build_into(
            snapshot=sources["checkpoint snapshot"],
            checkpoint_lock_path=sources["checkpoint lock"],
            model_graph_path=sources["model graph"],
            capability_path=sources["capability"],
            qualification_path=sources["qualification report"],
            attention_execution_path=sources["attention execution report"],
            root=temporary,
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
    "ProductionLayerDownstreamBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_layer_downstream_deployment",
]
