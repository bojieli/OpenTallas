"""Independent inverse checker for the Qwen layer-0 downstream deployment.

This module intentionally does not import the downstream compiler or any of its
lowering helpers.  It independently authenticates the source handoff, rereads
the locked checkpoint, rediscovers the neutral operations, rebuilds HBM/SRAM
placement and the ABI program, and derives all declared expectations.
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
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
    sha256_file,
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
    ABI_MAJOR,
    ELEMENTWISE_ABI_MINOR,
    Engine,
    MATMUL_FINAL,
    MATMUL_INIT,
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


COMPILER_VERSION = "tensor-accelerator-production-layer-downstream-0.1.0"
CHECK_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_independent_check.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_source_lock.v1"
ATTENTION_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.attention_execution.v1"

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

PROJECTION_SPECS = (
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


class ProductionLayerDownstreamCheckError(ArtifactError):
    """Raised when a candidate cannot be independently reconstructed."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = dict(body)
    return {**value, field: sha256_bytes(canonical_json_bytes(value))}


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionLayerDownstreamCheckError(str(exc)) from exc
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionLayerDownstreamCheckError(f"{label} identity differs")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise ProductionLayerDownstreamCheckError(
            f"{label} must be a safe relative path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProductionLayerDownstreamCheckError(
            f"{label} must be a safe relative path"
        )
    return path.as_posix()


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionLayerDownstreamCheckError(
            f"cannot load {label}: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise ProductionLayerDownstreamCheckError(f"{label} is not canonical JSON")
    return value, payload


def _external_copy(root: Path, internal: str, external: Path, label: str) -> bytes:
    try:
        retained = (root / internal).read_bytes()
        source = external.read_bytes()
    except OSError as exc:
        raise ProductionLayerDownstreamCheckError(
            f"cannot read {label}: {exc}"
        ) from exc
    if retained != source:
        raise ProductionLayerDownstreamCheckError(
            f"retained {label} differs from its source"
        )
    return source


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
        raise ProductionLayerDownstreamCheckError(
            f"graph tensor {tensor_id!r} is not bound rank-{rank} BF16"
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
        raise ProductionLayerDownstreamCheckError(
            f"graph binding differs for {tensor_id!r}"
        )
    return binding.sources[0].shape, binding.sources[0].payload_sha256


def _one_operation(
    model: ProductionModelGraph,
    *,
    kind: str,
    inputs: tuple[str, ...],
    contract: str,
) -> ProductionOperation:
    matches = [
        operation
        for operation in model.operations
        if operation.kind == kind
        and operation.inputs == inputs
        and operation.numeric_contract == contract
    ]
    if len(matches) != 1:
        raise ProductionLayerDownstreamCheckError(
            f"graph must contain one {kind} over {inputs!r}"
        )
    return matches[0]


def _operations(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
) -> tuple[ProductionOperation, ...]:
    sources = qualification["sources"]
    output_projection = _one_operation(
        model,
        kind="MATMUL",
        inputs=(
            "layer.0.attention",
            sources["attention_output_weight"]["tensor"],
        ),
        contract=MATRIX_CONTRACT,
    )
    first_add = _one_operation(
        model,
        kind="ADD",
        inputs=("hidden.0", output_projection.outputs[0]),
        contract=ADD_CONTRACT,
    )
    norm = _one_operation(
        model,
        kind="RMS_NORM",
        inputs=(
            first_add.outputs[0],
            sources["post_attention_norm_weight"]["tensor"],
        ),
        contract=RMSNORM_CONTRACT,
    )
    gate = _one_operation(
        model,
        kind="MATMUL",
        inputs=(norm.outputs[0], sources["gate_projection_weight"]["tensor"]),
        contract=MATRIX_CONTRACT,
    )
    up = _one_operation(
        model,
        kind="MATMUL",
        inputs=(norm.outputs[0], sources["up_projection_weight"]["tensor"]),
        contract=MATRIX_CONTRACT,
    )
    silu = _one_operation(
        model,
        kind="SILU_MUL",
        inputs=(gate.outputs[0], up.outputs[0]),
        contract=SILU_CONTRACT,
    )
    down = _one_operation(
        model,
        kind="MATMUL",
        inputs=(silu.outputs[0], sources["down_projection_weight"]["tensor"]),
        contract=MATRIX_CONTRACT,
    )
    final_add = _one_operation(
        model,
        kind="ADD",
        inputs=(first_add.outputs[0], down.outputs[0]),
        contract=ADD_CONTRACT,
    )
    result = (
        output_projection,
        first_add,
        norm,
        gate,
        up,
        silu,
        down,
        final_add,
    )
    expected_ids = tuple(f"node.{index:04d}" for index in range(10, 18))
    widths = (
        HIDDEN_WIDTH,
        HIDDEN_WIDTH,
        HIDDEN_WIDTH,
        INTERMEDIATE_WIDTH,
        INTERMEDIATE_WIDTH,
        INTERMEDIATE_WIDTH,
        HIDDEN_WIDTH,
        HIDDEN_WIDTH,
    )
    if tuple(operation.operation_id for operation in result) != expected_ids:
        raise ProductionLayerDownstreamCheckError(
            "downstream graph operation IDs differ"
        )
    for operation, width in zip(result, widths, strict=True):
        output = (
            model.tensor_by_id.get(operation.outputs[0])
            if len(operation.outputs) == 1
            else None
        )
        if (
            operation.attributes.get("layer") != 0
            or output is None
            or output.dtype != "bf16"
            or output.shape != (1, "span_tokens", width)
        ):
            raise ProductionLayerDownstreamCheckError(
                f"source semantics differ for {operation.operation_id}"
            )
    if any(
        operation.attributes.get("transpose_weight") is not True
        for operation in (output_projection, gate, up, down)
    ):
        raise ProductionLayerDownstreamCheckError(
            "projection transpose semantics differ"
        )
    if (
        norm.attributes.get("epsilon") != 1e-6
        or norm.attributes.get("normalization_width") != HIDDEN_WIDTH
    ):
        raise ProductionLayerDownstreamCheckError("RMSNorm semantics differ")
    return result


def _attention_payload(
    path: Path,
    qualification: Mapping[str, Any],
) -> bytes:
    report, _ = _load_canonical(path, "attention execution")
    _identity(report, "report_id", "attention execution")
    binding = qualification["attention_input"]
    output = report.get("outputs", {}).get("attention")
    if (
        report.get("schema") != ATTENTION_EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != binding["report_id"]
        or report.get("build_id") != binding["build_id"]
        or report.get("qualification_report_id") != binding["qualification_report_id"]
        or not isinstance(output, Mapping)
        or output.get("dtype") != "bf16"
        or output.get("shape") != [1, 32, 128]
        or output.get("size_bytes") != HIDDEN_WIDTH * 2
        or output.get("payload_sha256") != binding["payload_sha256"]
    ):
        raise ProductionLayerDownstreamCheckError("attention execution handoff differs")
    raw = output.get("codes")
    if not isinstance(raw, list) or len(raw) != HIDDEN_WIDTH:
        raise ProductionLayerDownstreamCheckError("attention code coverage differs")
    codes = np.asarray(
        [
            require_int(
                code,
                f"attention.codes[{index}]",
                minimum=0,
                maximum=0xFFFF,
            )
            for index, code in enumerate(raw)
        ],
        dtype=np.uint16,
    )
    payload = codes.astype("<u2", copy=False).tobytes(order="C")
    if hashlib.sha256(payload).hexdigest() != binding["payload_sha256"]:
        raise ProductionLayerDownstreamCheckError("attention payload identity differs")
    return payload


def _capture_embedding(
    reader: LockedCheckpointReader,
    tensor_name: str,
    *,
    token_id: int,
) -> tuple[Mapping[str, Any], bytes]:
    row_bytes = HIDDEN_WIDTH * 2
    start = token_id * row_bytes
    end = start + row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        chunk_end = cursor + len(chunk)
        lower = max(cursor, start)
        upper = min(chunk_end, end)
        if lower < upper:
            captured.extend(chunk[lower - cursor : upper - cursor])
        cursor = chunk_end

    record = reader.consume_tensor_payload(tensor_name, consume)
    if len(captured) != row_bytes:
        raise ProductionLayerDownstreamCheckError("embedding row coverage differs")
    return record, bytes(captured)


def _checkpoint_payloads(
    snapshot: Path,
    checkpoint_lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    try:
        with LockedCheckpointReader(snapshot, checkpoint_lock) as reader:
            embedding = qualification["sources"]["embedding"]
            record, payload = _capture_embedding(
                reader,
                embedding["tensor"],
                token_id=qualification["input"]["token_id"],
            )
            if (
                record.get("dtype") != "BF16"
                or record.get("shape") != embedding["shape"]
                or record.get("payload_sha256") != embedding["payload_sha256"]
                or hashlib.sha256(payload).hexdigest()
                != qualification["input"]["embedding_row_payload_sha256"]
            ):
                raise ProductionLayerDownstreamCheckError(
                    "embedding checkpoint source differs"
                )
            result["hidden_0"] = payload
            for role in SOURCE_ROLES[1:]:
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
                    raise ProductionLayerDownstreamCheckError(
                        f"{role} checkpoint source differs"
                    )
                result[role] = payload
    except CheckpointError as exc:
        raise ProductionLayerDownstreamCheckError(
            f"locked checkpoint read failed: {exc}"
        ) from exc
    return result


def _problem(
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, Any]:
    if (
        (capability.command_abi_major, capability.command_abi_minor)
        != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
        or capability.vector_engine is None
        or capability.vector_engine.max_rows < ROWS
        or capability.vector_engine.max_width < INTERMEDIATE_WIDTH
        or capability.tensor_engine.max_m < ROWS
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
        or not set(NUMERIC_CONTRACTS) <= set(capability.qualified_numeric_contracts)
    ):
        raise ProductionLayerDownstreamCheckError(
            "capability does not admit the downstream problem"
        )
    expected_shapes = {
        "attention_output": [HIDDEN_WIDTH, HIDDEN_WIDTH],
        "gate": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "up": [INTERMEDIATE_WIDTH, HIDDEN_WIDTH],
        "down": [HIDDEN_WIDTH, INTERMEDIATE_WIDTH],
    }
    projections: list[dict[str, Any]] = []
    for spec in PROJECTION_SPECS:
        source = qualification["sources"][spec["source_role"]]
        if source["shape"] != expected_shapes[spec["id"]]:
            raise ProductionLayerDownstreamCheckError(
                f"{spec['id']} source shape differs"
            )
        n, k = source["shape"]
        if n % N_TILE or k % K_TILE:
            raise ProductionLayerDownstreamCheckError(
                f"{spec['id']} is not exactly tileable"
            )
        projections.append(
            {
                **spec,
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


def _sram(capability: ProductionCapability) -> dict[str, Any]:
    hidden_bytes = HIDDEN_WIDTH * 2
    intermediate_bytes = INTERMEDIATE_WIDTH * 2
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
    intervals: list[tuple[int, int]] = []
    for region_id, bank, dtype, shape, logical in specs:
        allocated = align_up(logical, capability.sram.word_bytes)
        address = capability.sram.bank_base(bank)
        if bank >= capability.sram.banks or allocated > capability.sram.bytes_per_bank:
            raise ProductionLayerDownstreamCheckError(
                f"SRAM region {region_id!r} exceeds capability"
            )
        intervals.append((address, address + allocated))
        regions.append(
            {
                "address": address,
                "allocated_bytes": allocated,
                "bank": bank,
                "dtype": dtype,
                "id": region_id,
                "logical_bytes": logical,
                "shape": shape,
            }
        )
    intervals.sort()
    if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
        raise ProductionLayerDownstreamCheckError("SRAM regions overlap")
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _place_region(
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
    tiles: list[dict[str, Any]] = []
    for n_start in range(0, definition["n"], N_TILE):
        for k_start in range(0, definition["k"], K_TILE):
            tile = np.ascontiguousarray(
                weights[
                    n_start : n_start + N_TILE,
                    k_start : k_start + K_TILE,
                ],
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


def _hbm(
    *,
    payloads: Mapping[str, bytes],
    attention: bytes,
    qualification: Mapping[str, Any],
    problem: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, Any]]:
    image = bytearray()
    regions = [
        _place_region(
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
        _place_region(
            image,
            capability=capability,
            region_id="attention",
            payload=attention,
            source={
                "build_id": qualification["attention_input"]["build_id"],
                "kind": "retained_execution_output",
                "report_id": qualification["attention_input"]["report_id"],
            },
        ),
        _place_region(
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
    definitions = {item["id"]: item for item in problem["projections"]}
    projections: list[dict[str, Any]] = []
    for spec in PROJECTION_SPECS:
        definition = definitions[spec["id"]]
        source = qualification["sources"][spec["source_role"]]
        projections.append(
            _place_projection(
                image,
                capability=capability,
                definition=definition,
                payload=payloads[spec["source_role"]],
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
    raw = bytes(image)
    return raw, {
        "image": {
            "base_address": capability.hbm.base_address,
            "path": HBM_IMAGE_PATH,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
        "projections": projections,
        "regions": regions,
    }


def _records_by_id(records: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {record["id"]: record for record in records}


def _projection_commands(
    commands: list[ProductionCommand],
    *,
    projection: Mapping[str, Any],
    definition: Mapping[str, Any],
    sram: Mapping[str, Mapping[str, Any]],
) -> None:
    for tile in projection["tiles"]:
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
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
                len(commands),
                Opcode.MATMUL_BF16_TILE,
                Engine.TENSOR,
                flags=flags,
                kernel_index=projection["kernel_index"],
                source0=sram[projection["input_region"]]["address"]
                + tile["k_start"] * 2,
                source1=sram["weight_tile"]["address"],
                destination=sram["accumulator_tile"]["address"],
                auxiliary=sram[projection["output_region"]]["address"]
                + tile["n_start"] * 2,
                size0=ROWS,
                size1=N_TILE,
                size2=K_TILE,
            )
        )


def _commands(
    *,
    hbm: Mapping[str, Any],
    sram_plan: Mapping[str, Any],
    problem: Mapping[str, Any],
) -> tuple[ProductionCommand, ...]:
    sram = _records_by_id(sram_plan["regions"])
    direct = _records_by_id(hbm["regions"])
    projections = _records_by_id(hbm["projections"])
    definitions = {item["id"]: item for item in problem["projections"]}
    commands: list[ProductionCommand] = []
    for region_id, kernel_index in (("hidden_0", 1), ("attention", 0)):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=kernel_index,
                source0=direct[region_id]["address"],
                destination=sram[region_id]["address"],
                size0=direct[region_id]["size_bytes"],
            )
        )
    _projection_commands(
        commands,
        projection=projections["attention_output"],
        definition=definitions["attention_output"],
        sram=sram,
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.ADD_BF16,
            Engine.VECTOR,
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
            len(commands),
            Opcode.DMA_HBM_TO_SRAM,
            Engine.DMA,
            kernel_index=2,
            source0=norm["address"],
            destination=sram["post_attention_norm_weight"]["address"],
            size0=norm["size_bytes"],
        )
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.RMSNORM_BF16,
            Engine.VECTOR,
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
        _projection_commands(
            commands,
            projection=projections[role],
            definition=definitions[role],
            sram=sram,
        )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.SILU_MUL_BF16,
            Engine.VECTOR,
            kernel_index=5,
            source0=sram["gate"]["address"],
            source1=sram["up"]["address"],
            destination=sram["gated_mlp"]["address"],
            size0=ROWS,
            size1=INTERMEDIATE_WIDTH,
        )
    )
    _projection_commands(
        commands,
        projection=projections["down"],
        definition=definitions["down"],
        sram=sram,
    )
    commands.append(
        ProductionCommand(
            len(commands),
            Opcode.ADD_BF16,
            Engine.VECTOR,
            kernel_index=7,
            source0=sram["post_attention"]["address"],
            source1=sram["down"]["address"],
            destination=sram["hidden_1"]["address"],
            size0=ROWS,
            size1=HIDDEN_WIDTH,
        )
    )
    commands.append(ProductionCommand(len(commands), Opcode.COMPLETE, Engine.CONTROL))
    return tuple(commands)


def _counters(problem: Mapping[str, Any]) -> dict[str, int]:
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
    return {
        "accumulator_sram_bytes_read": accumulator_reads,
        "accumulator_sram_bytes_written": accumulator_writes,
        "add_command_count": 2,
        "add_input_sram_bytes_read": 4 * HIDDEN_WIDTH * 2,
        "add_output_sram_bytes_written": 2 * HIDDEN_WIDTH * 2,
        "command_count": 2 * tile_count + 8,
        "complete_command_count": 1,
        "dma_command_count": tile_count + 3,
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


def _matrix_kernel(
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


def _add_kernel(operation: ProductionOperation, index: int) -> dict[str, Any]:
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
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ...],
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
        "kernels": [
            _matrix_kernel(operations[0], index=0, n=HIDDEN_WIDTH, k=HIDDEN_WIDTH),
            _add_kernel(operations[1], 1),
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
            _matrix_kernel(
                operations[3],
                index=3,
                n=INTERMEDIATE_WIDTH,
                k=HIDDEN_WIDTH,
            ),
            _matrix_kernel(
                operations[4],
                index=4,
                n=INTERMEDIATE_WIDTH,
                k=HIDDEN_WIDTH,
            ),
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
            _matrix_kernel(
                operations[6],
                index=6,
                n=HIDDEN_WIDTH,
                k=INTERMEDIATE_WIDTH,
            ),
            _add_kernel(operations[7], 7),
        ],
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
    return _identified(
        {
            "attention_execution_report_id": qualification["attention_input"][
                "report_id"
            ],
            "capability_id": capability.capability_id,
            "checkpoint_lock_id": checkpoint_lock["lock_id"],
            "compiler_version": COMPILER_VERSION,
            "graph_id": model.graph_id,
            "qualification_report_id": qualification["report_id"],
            "schema": SOURCE_LOCK_SCHEMA,
            "sources": sources,
        },
        "source_lock_id",
    )


def _request(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operations: tuple[ProductionOperation, ...],
) -> dict[str, Any]:
    return _identified(
        {
            "graph_id": model.graph_id,
            "inputs": {
                "attention_execution_report_id": qualification["attention_input"][
                    "report_id"
                ],
                "token_id": qualification["input"]["token_id"],
            },
            "schema": REQUEST_SCHEMA,
            "source_operation_ids": [
                operation.operation_id for operation in operations
            ],
        },
        "request_id",
    )


def _physical_plan(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    operations: tuple[ProductionOperation, ...],
    problem: Mapping[str, Any],
    sram: Mapping[str, Any],
    hbm: Mapping[str, Any],
    command_payload: bytes,
) -> dict[str, Any]:
    counters = _counters(problem)
    return _identified(
        {
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
            "source_operation_ids": [
                operation.operation_id for operation in operations
            ],
            "sram": dict(sram),
        },
        "physical_plan_id",
    )


def _expected_hashes(
    qualification: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    intermediates = {
        role: qualification["intermediates"][role]["payload_sha256"]
        for role in (
            "attention_projected",
            "down",
            "gate",
            "gated_mlp",
            "mlp_norm",
            "post_attention",
            "silu_activation",
            "up",
        )
    }
    outputs = {"hidden_1": qualification["output"]["hidden_1"]["payload_sha256"]}
    saturation = {
        "projection": dict(qualification["projection_saturated_element_count"]),
        "rmsnorm": dict(qualification["rmsnorm_saturated_element_count"]),
        "vector": dict(qualification["vector_saturated_element_count"]),
    }
    return intermediates, outputs, saturation


def check_layer_downstream_candidate(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    attention_execution_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct and validate a downstream candidate."""

    root = Path(root).resolve()
    snapshot = Path(snapshot).resolve()
    checkpoint_lock_path = Path(checkpoint_lock_path).resolve()
    model_graph_path = Path(model_graph_path).resolve()
    capability_path = Path(capability_path).resolve()
    qualification_path = Path(qualification_path).resolve()
    attention_execution_path = Path(attention_execution_path).resolve()
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
        raise ProductionLayerDownstreamCheckError(
            f"external source admission failed: {exc}"
        ) from exc
    if qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]:
        raise ProductionLayerDownstreamCheckError(
            "qualification and checkpoint lock differ"
        )
    _external_copy(
        root,
        "source/checkpoint.lock.json",
        checkpoint_lock_path,
        "checkpoint lock",
    )
    _external_copy(
        root,
        "source/model_graph.v2.json",
        model_graph_path,
        "model graph",
    )
    _external_copy(
        root,
        "source/qualification.json",
        qualification_path,
        "qualification report",
    )
    _external_copy(
        root,
        "source/attention_execution.json",
        attention_execution_path,
        "attention execution",
    )
    candidate_capability, _ = _load_canonical(
        root / "capability.json", "candidate capability"
    )
    if candidate_capability != capability.to_dict():
        raise ProductionLayerDownstreamCheckError(
            "candidate capability differs from its external source"
        )
    for role in SOURCE_ROLES:
        source = qualification["sources"][role]
        shape, digest = _binding(
            model,
            source["tensor"],
            checkpoint_lock_id=checkpoint_lock["lock_id"],
            rank=len(source["shape"]),
        )
        if list(shape) != source["shape"] or digest != source["payload_sha256"]:
            raise ProductionLayerDownstreamCheckError(
                f"qualification binding differs for {role}"
            )
    operations = _operations(model, qualification)
    problem = _problem(qualification, capability)
    payloads = _checkpoint_payloads(snapshot, checkpoint_lock, qualification)
    attention = _attention_payload(attention_execution_path, qualification)
    image, hbm = _hbm(
        payloads=payloads,
        attention=attention,
        qualification=qualification,
        problem=problem,
        capability=capability,
    )
    if len(image) > capability.hbm.capacity_bytes:
        raise ProductionLayerDownstreamCheckError(
            "reconstructed HBM image exceeds capability"
        )
    candidate_image = (root / HBM_IMAGE_PATH).read_bytes()
    if candidate_image != image:
        raise ProductionLayerDownstreamCheckError(
            "HBM image differs from independent reconstruction"
        )
    sram = _sram(capability)
    commands = _commands(hbm=hbm, sram_plan=sram, problem=problem)
    try:
        command_payload = (root / COMMAND_PATH).read_bytes()
        decoded = decode(command_payload)
        abi = command_abi(command_payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionLayerDownstreamCheckError(
            f"candidate command program is invalid: {exc}"
        ) from exc
    if abi != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR) or decoded != commands:
        raise ProductionLayerDownstreamCheckError(
            "command program differs from independent schedule"
        )
    expected_disassembly = disassemble(commands, abi_minor=ELEMENTWISE_ABI_MINOR)
    try:
        observed_disassembly = (root / "program/commands.disasm").read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise ProductionLayerDownstreamCheckError(
            f"cannot read command disassembly: {exc}"
        ) from exc
    if observed_disassembly != expected_disassembly:
        raise ProductionLayerDownstreamCheckError(
            "command disassembly differs from independent schedule"
        )
    expected_kernel = _kernel_ir(model, qualification, operations)
    candidate_kernel, _ = _load_canonical(
        root / "ir/tensor_kernel_ir.json", "candidate Kernel IR"
    )
    _identity(candidate_kernel, "kernel_ir_id", "candidate Kernel IR")
    if candidate_kernel != expected_kernel:
        raise ProductionLayerDownstreamCheckError(
            "neutral Kernel IR differs from independent reconstruction"
        )
    serialized_kernel = canonical_json_bytes(candidate_kernel).lower()
    if b"address" in serialized_kernel or b"sram" in serialized_kernel:
        raise ProductionLayerDownstreamCheckError(
            "neutral Kernel IR leaks physical placement"
        )
    expected_plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        operations=operations,
        problem=problem,
        sram=sram,
        hbm=hbm,
        command_payload=command_payload,
    )
    candidate_plan, _ = _load_canonical(
        root / PHYSICAL_PLAN_PATH, "candidate physical plan"
    )
    _identity(candidate_plan, "physical_plan_id", "candidate physical plan")
    if candidate_plan != expected_plan:
        raise ProductionLayerDownstreamCheckError(
            "physical plan differs from independent reconstruction"
        )
    expected_request = _request(model, qualification, operations)
    candidate_request, _ = _load_canonical(root / REQUEST_PATH, "candidate request")
    _identity(candidate_request, "request_id", "candidate request")
    if candidate_request != expected_request:
        raise ProductionLayerDownstreamCheckError(
            "request differs from independent reconstruction"
        )
    expected_lock = _source_lock(
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
    candidate_lock, _ = _load_canonical(
        root / "source.lock.json", "candidate source lock"
    )
    _identity(candidate_lock, "source_lock_id", "candidate source lock")
    if candidate_lock != expected_lock:
        raise ProductionLayerDownstreamCheckError(
            "source lock differs from independent reconstruction"
        )
    intermediates, outputs, saturation = _expected_hashes(qualification)
    checks = [
        "external_sources_authenticated",
        "graph_chain_rediscovered",
        "checkpoint_payloads_reread",
        "hbm_image_and_tiles_reconstructed",
        "hbm_alignment_coverage_and_zero_padding_proved",
        "sram_roles_bounds_and_nonoverlap_proved",
        "abi_2_4_program_reconstructed",
        "neutral_kernel_ir_reconstructed",
        "counters_and_output_expectations_derived",
    ]
    return _identified(
        {
            "capability_id": capability.capability_id,
            "checks": checks,
            "command_abi": {"major": abi[0], "minor": abi[1]},
            "command_count": len(commands),
            "expected_counters": _counters(problem),
            "expected_intermediate_payload_sha256": intermediates,
            "expected_output_payload_sha256": outputs,
            "expected_saturated_element_count": saturation,
            "graph_id": model.graph_id,
            "hbm_image_sha256": hashlib.sha256(image).hexdigest(),
            "hbm_size_bytes": len(image),
            "kernel_ir_id": expected_kernel["kernel_ir_id"],
            "physical_plan_id": expected_plan["physical_plan_id"],
            "qualification_report_id": qualification["report_id"],
            "schema": CHECK_SCHEMA,
            "source_lock_id": expected_lock["source_lock_id"],
            "status": "pass",
        },
        "check_id",
    )


__all__ = [
    "CHECK_SCHEMA",
    "ProductionLayerDownstreamCheckError",
    "check_layer_downstream_candidate",
]
