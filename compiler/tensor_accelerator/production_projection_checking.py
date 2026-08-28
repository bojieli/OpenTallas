"""Independent inverse and legality checker for BF16 projection deployments.

This module does not import the projection planner or its helper functions.  It
derives layouts, commands, coverage, and counters again from source artifacts
and the independently parsed hardware capability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)

from .bf16_qualification import (
    BF16QualificationError,
    NUMERIC_CONTRACT,
    load_qualification_report,
)
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
    Engine,
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    ProductionCommandError,
    decode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    load_production_model_graph,
)


CHECK_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_independent_check.v1"
KERNEL_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_kernel.v1"
PHYSICAL_PLAN_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_physical_plan.v1"
)
REQUEST_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_request.v1"
SOURCE_LOCK_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_source_lock.v1"
)
HBM_IMAGE_PATH = "memory/hbm_weights_tiled.bin"
COMMAND_PATH = "program/commands.bin"


class ProductionProjectionCheckError(RuntimeError):
    """Raised when generated artifacts fail independent reconstruction."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise ProductionProjectionCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionProjectionCheckError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductionProjectionCheckError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionProjectionCheckError(f"{label} must be a safe relative path")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionProjectionCheckError(
            f"{label} {field} differs from canonical content"
        )


def _problem(
    raw: Any,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ProductionProjectionCheckError("problem must be an object")
    names = {"k", "k_tile", "k_tiles", "m", "n", "n_tile", "n_tiles", "tile_count"}
    exact_keys(raw, names, set(), "problem")
    values = {
        name: require_int(raw[name], f"problem.{name}", minimum=1)
        for name in names
    }
    n, k = qualification["weight"]["shape"]
    m = qualification["output"]["shape"][0]
    expected_n_tile = min(64, n, capability.tensor_engine.max_n)
    expected_k_tile = min(256, k, capability.tensor_engine.max_k)
    expected = {
        "k": k,
        "k_tile": expected_k_tile,
        "k_tiles": k // expected_k_tile,
        "m": m,
        "n": n,
        "n_tile": expected_n_tile,
        "n_tiles": n // expected_n_tile,
        "tile_count": (n // expected_n_tile) * (k // expected_k_tile),
    }
    if (
        m != 1
        or n % expected_n_tile
        or k % expected_k_tile
        or expected_n_tile > capability.tensor_engine.max_n
        or expected_k_tile > capability.tensor_engine.max_k
        or expected != values
    ):
        raise ProductionProjectionCheckError(
            "problem dimensions or tiling differ from source and capability"
        )
    return values


def _expected_counters(problem: Mapping[str, int]) -> dict[str, int]:
    tile_count = problem["tile_count"]
    accumulator_elements = problem["m"] * problem["n_tile"]
    weight_bytes = problem["n"] * problem["k"] * 2
    return {
        "accumulator_sram_bytes_read": (
            problem["n_tiles"]
            * (problem["k_tiles"] - 1)
            * accumulator_elements
            * 4
        ),
        "accumulator_sram_bytes_written": tile_count * accumulator_elements * 4,
        "command_count": 2 * tile_count + 1,
        "complete_command_count": 1,
        "dma_command_count": tile_count,
        "dma_sram_bytes_written": weight_bytes,
        "hbm_transferred_bytes_read": weight_bytes,
        "hbm_useful_bytes_read": weight_bytes,
        "input_sram_bytes_read": (
            tile_count * problem["m"] * problem["k_tile"] * 2
        ),
        "matmul_command_count": tile_count,
        "output_sram_bytes_written": problem["m"] * problem["n"] * 2,
        "runtime_input_sram_bytes_written": problem["m"] * problem["k"] * 2,
        "scalar_accumulation_additions": (
            problem["m"] * problem["n"] * problem["k"]
        ),
        "scalar_multiplications": problem["m"] * problem["n"] * problem["k"],
        "weight_sram_bytes_read": weight_bytes,
    }


def _capture_row(shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = shape[1] * 2
    start = row * row_bytes
    result = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        left = max(cursor, start)
        right = min(end, start + row_bytes)
        if left < right:
            result.extend(chunk[left - cursor : right - cursor])
        cursor = end

    return result, consume


def _read_locked_sources(
    snapshot: Path,
    lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> tuple[bytes, bytes]:
    input_info = qualification["input"]
    weight_info = qualification["weight"]
    try:
        with LockedCheckpointReader(Path(snapshot), dict(lock)) as reader:
            input_record = reader.tensor_record(input_info["tensor"])
            input_shape = tuple(input_record["shape"])
            if len(input_shape) != 2:
                raise ProductionProjectionCheckError(
                    "source input tensor is not rank two"
                )
            captured, consumer = _capture_row(input_shape, input_info["row"])
            reader.consume_tensor_payload(input_info["tensor"], consumer)
            weight = bytearray()
            weight_record = reader.consume_tensor_payload(
                weight_info["tensor"], weight.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionProjectionCheckError(
            f"independent locked checkpoint read failed: {exc}"
        ) from exc
    input_payload = bytes(captured)
    weight_payload = bytes(weight)
    if (
        input_record["payload_sha256"] != input_info["source_payload_sha256"]
        or input_record["shape"] != input_info["source_shape"]
        or hashlib.sha256(input_payload).hexdigest()
        != input_info["row_payload_sha256"]
        or weight_record["payload_sha256"] != weight_info["payload_sha256"]
        or weight_record["shape"] != weight_info["shape"]
    ):
        raise ProductionProjectionCheckError(
            "independent source payloads differ from qualification"
        )
    return input_payload, weight_payload


def _check_graph_bindings(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    lock_id: str,
) -> str:
    for section in ("input", "weight"):
        tensor_id = qualification[section]["tensor"]
        tensor = model.tensor_by_id.get(tensor_id)
        if tensor is None or tensor.dtype != "bf16" or tensor.binding is None:
            raise ProductionProjectionCheckError(
                f"graph lacks qualification tensor {tensor_id!r}"
            )
        binding = tensor.binding
        expected_shape = (
            qualification["input"]["source_shape"]
            if section == "input"
            else qualification["weight"]["shape"]
        )
        expected_hash = (
            qualification["input"]["source_payload_sha256"]
            if section == "input"
            else qualification["weight"]["payload_sha256"]
        )
        if (
            binding.checkpoint_lock_id != lock_id
            or len(binding.sources) != 1
            or binding.sources[0].tensor_name != tensor_id
            or binding.sources[0].dtype != "bf16"
            or list(binding.sources[0].shape) != expected_shape
            or binding.sources[0].payload_sha256 != expected_hash
            or binding.transform != {"kind": "identity"}
            or binding.payload_sha256 != binding.sources[0].payload_sha256
        ):
            raise ProductionProjectionCheckError(
                f"graph checkpoint binding for {tensor_id!r} differs"
            )
    weight_id = qualification["weight"]["tensor"]
    operations = [
        operation
        for operation in model.operations
        if operation.kind == "MATMUL"
        and weight_id in operation.inputs
        and operation.numeric_contract == NUMERIC_CONTRACT
        and operation.attributes.get("transpose_weight") is True
    ]
    if len(operations) != 1:
        raise ProductionProjectionCheckError(
            "graph has no unique qualified source projection"
        )
    return operations[0].operation_id


def _check_source_copies(
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
    pairs = (
        (model_graph_path, root / "source/model_graph.v2.json", "model_graph"),
        (checkpoint_lock_path, root / "source/checkpoint.lock.json", "checkpoint_lock"),
        (qualification_path, root / "source/qualification.json", "qualification_report"),
    )
    for source, copied, label in pairs:
        if source.read_bytes() != copied.read_bytes():
            raise ProductionProjectionCheckError(f"copied {label} bytes differ")
    capability = _load_canonical(root / "capability.json", "emitted capability")
    if capability != _load_canonical(capability_path, "source capability"):
        raise ProductionProjectionCheckError("emitted capability differs from source")
    lock = _load_canonical(root / "source.lock.json", "source lock")
    exact_keys(
        lock,
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
    _identity(lock, "source_lock_id", "source lock")
    if (
        lock["schema"] != SOURCE_LOCK_SCHEMA
        or lock["capability_id"] != capability_id
        or lock["checkpoint_lock_id"] != lock_id
        or lock["graph_id"] != graph_id
        or lock["qualification_report_id"] != qualification_id
        or not isinstance(lock["compiler_version"], str)
        or not lock["compiler_version"]
    ):
        raise ProductionProjectionCheckError("source lock identities differ")
    raw_sources = lock["sources"]
    if not isinstance(raw_sources, list) or len(raw_sources) != 4:
        raise ProductionProjectionCheckError("source lock coverage differs")
    expected_paths = {
        "model_graph": model_graph_path,
        "checkpoint_lock": checkpoint_lock_path,
        "hardware_capability": capability_path,
        "qualification_report": qualification_path,
    }
    for index, record in enumerate(raw_sources):
        if not isinstance(record, dict):
            raise ProductionProjectionCheckError(
                f"source lock record {index} is malformed"
            )
        exact_keys(record, {"role", "sha256", "size_bytes"}, set(), f"source {index}")
        path = expected_paths.get(record["role"])
        if path is None:
            raise ProductionProjectionCheckError("source lock has unknown role")
        digest, size = sha256_file(path)
        if record["sha256"] != digest or record["size_bytes"] != size:
            raise ProductionProjectionCheckError("source lock digest differs")
    if [record["role"] for record in raw_sources] != list(expected_paths):
        raise ProductionProjectionCheckError("source lock record order differs")
    return lock["source_lock_id"]


def _check_kernel(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operation_id: str,
    problem: Mapping[str, int],
) -> str:
    kernel = _load_canonical(root / "ir/tensor_kernel_ir.json", "kernel IR")
    exact_keys(
        kernel,
        {
            "graph_id",
            "input_fixture",
            "kernel_index",
            "kernel_ir_id",
            "numeric_contract",
            "operation",
            "problem",
            "qualification_report_id",
            "reduction_order",
            "schema",
            "source_operation_id",
            "weight_tensor_id",
        },
        set(),
        "kernel IR",
    )
    _identity(kernel, "kernel_ir_id", "kernel IR")
    expected_input = {
        "row": qualification["input"]["row"],
        "row_payload_sha256": qualification["input"]["row_payload_sha256"],
        "tensor_id": qualification["input"]["tensor"],
    }
    if (
        kernel["schema"] != KERNEL_SCHEMA
        or kernel["graph_id"] != model.graph_id
        or kernel["input_fixture"] != expected_input
        or kernel["kernel_index"] != 0
        or kernel["numeric_contract"] != NUMERIC_CONTRACT
        or kernel["operation"] != "MATMUL_BF16_TILE"
        or kernel["problem"] != problem
        or kernel["qualification_report_id"] != qualification["report_id"]
        or kernel["reduction_order"] != "strictly_increasing_k"
        or kernel["source_operation_id"] != operation_id
        or kernel["weight_tensor_id"] != qualification["weight"]["tensor"]
    ):
        raise ProductionProjectionCheckError("kernel IR differs from source semantics")
    return kernel["kernel_ir_id"]


def _check_sram(
    raw: Any,
    problem: Mapping[str, int],
    capability: ProductionCapability,
) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ProductionProjectionCheckError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionProjectionCheckError("SRAM addressing differs")
    specs = (
        ("input", 0, "bf16", [problem["m"], problem["k"]], problem["m"] * problem["k"] * 2),
        ("weight_tile", 1, "bf16", [problem["n_tile"], problem["k_tile"]], problem["n_tile"] * problem["k_tile"] * 2),
        ("accumulator_tile", 2, "fp32", [problem["m"], problem["n_tile"]], problem["m"] * problem["n_tile"] * 4),
        ("output", 3, "bf16", [problem["m"], problem["n"]], problem["m"] * problem["n"] * 2),
    )
    regions = raw["regions"]
    if not isinstance(regions, list) or len(regions) != len(specs):
        raise ProductionProjectionCheckError("SRAM region coverage differs")
    result: dict[str, dict[str, Any]] = {}
    occupied: list[tuple[int, int, str]] = []
    for index, (record, spec) in enumerate(zip(regions, specs, strict=True)):
        if not isinstance(record, dict):
            raise ProductionProjectionCheckError(f"SRAM region {index} is malformed")
        exact_keys(
            record,
            {"address", "allocated_bytes", "bank", "dtype", "id", "logical_bytes", "shape"},
            set(),
            f"SRAM region {index}",
        )
        region_id, bank, dtype, shape, logical = spec
        allocated = align_up(logical, capability.sram.word_bytes)
        expected = {
            "address": capability.sram.bank_base(bank),
            "allocated_bytes": allocated,
            "bank": bank,
            "dtype": dtype,
            "id": region_id,
            "logical_bytes": logical,
            "shape": shape,
        }
        if record != expected or allocated > capability.sram.bytes_per_bank:
            raise ProductionProjectionCheckError(
                f"SRAM region {region_id!r} differs or exceeds its bank"
            )
        start = record["address"]
        end = start + record["allocated_bytes"]
        if any(start < other_end and other_start < end for other_start, other_end, _ in occupied):
            raise ProductionProjectionCheckError("SRAM regions overlap")
        occupied.append((start, end, region_id))
        result[region_id] = record
    return result


def _check_hbm_and_reconstruct(
    raw: Any,
    root: Path,
    *,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    problem: Mapping[str, int],
    source_weight: bytes,
) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(raw, dict):
        raise ProductionProjectionCheckError("HBM plan must be an object")
    exact_keys(
        raw,
        {"image", "source_weight", "tile_layout", "tile_order", "tiles"},
        set(),
        "HBM plan",
    )
    if raw["tile_layout"] != "row_major_nk" or raw["tile_order"] != "n_major_k_minor":
        raise ProductionProjectionCheckError("HBM tile layout or order differs")
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionProjectionCheckError("HBM image record is malformed")
    exact_keys(
        image_record,
        {"base_address", "path", "sha256", "size_bytes"},
        set(),
        "HBM image",
    )
    image_path = _safe_relative(image_record["path"], "HBM image path")
    if image_path != HBM_IMAGE_PATH or image_record["base_address"] != capability.hbm.base_address:
        raise ProductionProjectionCheckError("HBM image placement differs")
    image = (root / image_path).read_bytes()
    if (
        image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) != len(source_weight)
        or len(image) > capability.hbm.capacity_bytes
    ):
        raise ProductionProjectionCheckError("HBM image identity or capacity differs")
    expected_source = {
        "checkpoint_lock_id": qualification["checkpoint_lock_id"],
        "dtype": "bf16",
        "payload_sha256": qualification["weight"]["payload_sha256"],
        "shape": qualification["weight"]["shape"],
        "tensor_name": qualification["weight"]["tensor"],
    }
    if raw["source_weight"] != expected_source:
        raise ProductionProjectionCheckError("HBM source-weight identity differs")
    tiles = raw["tiles"]
    if not isinstance(tiles, list) or len(tiles) != problem["tile_count"]:
        raise ProductionProjectionCheckError("HBM tile count differs")
    reconstructed = bytearray(len(source_weight))
    covered: set[tuple[int, int]] = set()
    expected_offset = 0
    parsed_tiles: list[dict[str, Any]] = []
    tile_index = 0
    tile_size = problem["n_tile"] * problem["k_tile"] * 2
    for n_start in range(0, problem["n"], problem["n_tile"]):
        for k_start in range(0, problem["k"], problem["k_tile"]):
            record = tiles[tile_index]
            if not isinstance(record, dict):
                raise ProductionProjectionCheckError(f"HBM tile {tile_index} is malformed")
            exact_keys(
                record,
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
                f"HBM tile {tile_index}",
            )
            expected = {
                "address": capability.hbm.base_address + expected_offset,
                "k_count": problem["k_tile"],
                "k_start": k_start,
                "n_count": problem["n_tile"],
                "n_start": n_start,
                "offset_bytes": expected_offset,
                "size_bytes": tile_size,
                "tile_index": tile_index,
            }
            if any(record[key] != value for key, value in expected.items()):
                raise ProductionProjectionCheckError(
                    f"HBM tile {tile_index} placement or coverage differs"
                )
            if record["address"] % capability.hbm.burst_bytes or tile_size % capability.hbm.burst_bytes:
                raise ProductionProjectionCheckError(f"HBM tile {tile_index} is not burst aligned")
            payload = image[expected_offset : expected_offset + tile_size]
            if record["payload_sha256"] != hashlib.sha256(payload).hexdigest():
                raise ProductionProjectionCheckError(f"HBM tile {tile_index} payload differs")
            for local_n in range(problem["n_tile"]):
                source_start = local_n * problem["k_tile"] * 2
                destination_start = (
                    (n_start + local_n) * problem["k"] + k_start
                ) * 2
                reconstructed[
                    destination_start : destination_start + problem["k_tile"] * 2
                ] = payload[source_start : source_start + problem["k_tile"] * 2]
            coordinate = (n_start, k_start)
            if coordinate in covered:
                raise ProductionProjectionCheckError("HBM tile coverage overlaps")
            covered.add(coordinate)
            parsed_tiles.append(record)
            expected_offset += tile_size
            tile_index += 1
    if expected_offset != len(image) or len(covered) != problem["tile_count"]:
        raise ProductionProjectionCheckError("HBM tile coverage is incomplete")
    reconstructed_hash = hashlib.sha256(reconstructed).hexdigest()
    if bytes(reconstructed) != source_weight or reconstructed_hash != qualification["weight"]["payload_sha256"]:
        raise ProductionProjectionCheckError(
            "inverse-reconstructed weight differs from locked row-major payload"
        )
    return parsed_tiles, reconstructed_hash


def _check_program(
    raw: Any,
    root: Path,
    *,
    problem: Mapping[str, int],
    tiles: list[dict[str, Any]],
    regions: Mapping[str, Mapping[str, Any]],
) -> int:
    if not isinstance(raw, dict):
        raise ProductionProjectionCheckError("program record must be an object")
    exact_keys(raw, {"command_count", "path", "sha256", "size_bytes"}, set(), "program")
    path = _safe_relative(raw["path"], "program.path")
    if path != COMMAND_PATH:
        raise ProductionProjectionCheckError("command program path differs")
    payload = (root / path).read_bytes()
    if (
        raw["size_bytes"] != len(payload)
        or raw["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise ProductionProjectionCheckError("command program identity differs")
    try:
        commands = decode(payload)
    except ProductionCommandError as exc:
        raise ProductionProjectionCheckError(
            f"command program is malformed: {exc}"
        ) from exc
    if len(commands) != 2 * len(tiles) + 1 or raw["command_count"] != len(commands):
        raise ProductionProjectionCheckError("command count differs from tile schedule")
    for tile_index, tile in enumerate(tiles):
        dma = commands[2 * tile_index]
        matmul = commands[2 * tile_index + 1]
        expected_dma = {
            "auxiliary": 0,
            "destination": regions["weight_tile"]["address"],
            "engine": Engine.DMA,
            "flags": 0,
            "index": 2 * tile_index,
            "kernel_index": 0,
            "opcode": Opcode.DMA_HBM_TO_SRAM,
            "size0": tile["size_bytes"],
            "size1": 0,
            "size2": 0,
            "size3": 0,
            "source0": tile["address"],
            "source1": 0,
        }
        if any(getattr(dma, key) != value for key, value in expected_dma.items()):
            raise ProductionProjectionCheckError(
                f"DMA command for tile {tile_index} differs"
            )
        flags = 0
        if tile["k_start"] == 0:
            flags |= MATMUL_INIT
        if tile["k_start"] + tile["k_count"] == problem["k"]:
            flags |= MATMUL_FINAL
        expected_matmul = {
            "auxiliary": regions["output"]["address"] + tile["n_start"] * 2,
            "destination": regions["accumulator_tile"]["address"],
            "engine": Engine.TENSOR,
            "flags": flags,
            "index": 2 * tile_index + 1,
            "kernel_index": 0,
            "opcode": Opcode.MATMUL_BF16_TILE,
            "size0": problem["m"],
            "size1": tile["n_count"],
            "size2": tile["k_count"],
            "size3": 0,
            "source0": regions["input"]["address"] + tile["k_start"] * 2,
            "source1": regions["weight_tile"]["address"],
        }
        if any(getattr(matmul, key) != value for key, value in expected_matmul.items()):
            raise ProductionProjectionCheckError(
                f"MATMUL command for tile {tile_index} differs"
            )
    terminal = commands[-1]
    if terminal.opcode != Opcode.COMPLETE or terminal.engine != Engine.CONTROL:
        raise ProductionProjectionCheckError("terminal completion command differs")
    return len(commands)


def _check_request(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operation_id: str,
    input_payload: bytes,
) -> str:
    request = _load_canonical(root / "request/execution_request.json", "request")
    exact_keys(
        request,
        {"graph_id", "input", "request_id", "schema", "source_operation_id"},
        set(),
        "request",
    )
    _identity(request, "request_id", "request")
    expected_input = {
        "dtype": "bf16",
        "path": "input.bf16.bin",
        "payload_sha256": hashlib.sha256(input_payload).hexdigest(),
        "shape": [1, qualification["weight"]["shape"][1]],
        "size_bytes": len(input_payload),
        "source_row": qualification["input"]["row"],
        "source_tensor": qualification["input"]["tensor"],
    }
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["graph_id"] != model.graph_id
        or request["source_operation_id"] != operation_id
        or request["input"] != expected_input
    ):
        raise ProductionProjectionCheckError("request differs from source fixture")
    emitted_input = (root / "request/input.bf16.bin").read_bytes()
    if emitted_input != input_payload:
        raise ProductionProjectionCheckError("emitted runtime input differs")
    return request["request_id"]


def check_projection_candidate(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct and validate one compiler candidate."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
        qualification = load_qualification_report(Path(qualification_path))
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        BF16QualificationError,
    ) as exc:
        raise ProductionProjectionCheckError(
            f"independent source admission failed: {exc}"
        ) from exc
    root = Path(root)
    if qualification["checkpoint_lock_id"] != lock["lock_id"]:
        raise ProductionProjectionCheckError(
            "qualification checkpoint identity differs"
        )
    operation_id = _check_graph_bindings(model, qualification, lock["lock_id"])
    input_payload, source_weight = _read_locked_sources(
        Path(snapshot), lock, qualification
    )
    source_lock_id = _check_source_copies(
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
            "numeric_contract",
            "physical_plan_id",
            "problem",
            "program",
            "qualification_report_id",
            "schema",
            "source_operation_id",
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
        or plan["numeric_contract"] != NUMERIC_CONTRACT
        or plan["qualification_report_id"] != qualification["report_id"]
        or plan["source_operation_id"] != operation_id
    ):
        raise ProductionProjectionCheckError("physical-plan identities differ")
    problem = _problem(plan["problem"], qualification, capability)
    kernel_ir_id = _check_kernel(
        root,
        model=model,
        qualification=qualification,
        operation_id=operation_id,
        problem=problem,
    )
    regions = _check_sram(plan["sram"], problem, capability)
    tiles, reconstructed_hash = _check_hbm_and_reconstruct(
        plan["hbm"],
        root,
        qualification=qualification,
        capability=capability,
        problem=problem,
        source_weight=source_weight,
    )
    command_count = _check_program(
        plan["program"], root, problem=problem, tiles=tiles, regions=regions
    )
    request_id = _check_request(
        root,
        model=model,
        qualification=qualification,
        operation_id=operation_id,
        input_payload=input_payload,
    )
    counters = _expected_counters(problem)
    if plan["expected_counters"] != counters:
        raise ProductionProjectionCheckError(
            "physical-plan counters differ from independent accounting"
        )
    body = {
        "capability_id": capability.capability_id,
        "command_count": command_count,
        "expected_counters": counters,
        "graph_id": model.graph_id,
        "kernel_ir_id": kernel_ir_id,
        "physical_plan_id": plan["physical_plan_id"],
        "qualification_report_id": qualification["report_id"],
        "reconstructed_weight": {
            "payload_sha256": reconstructed_hash,
            "size_bytes": len(source_weight),
            "source_tensor": qualification["weight"]["tensor"],
            "tile_count": len(tiles),
        },
        "request_id": request_id,
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock_id,
        "status": "pass",
    }
    return {**body, "check_id": sha256_bytes(canonical_json_bytes(body))}


__all__ = [
    "CHECK_SCHEMA",
    "ProductionProjectionCheckError",
    "check_projection_candidate",
]
