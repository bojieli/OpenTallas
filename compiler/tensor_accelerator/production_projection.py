"""Deterministic compiler for one real BF16 HBM/SRAM projection slice."""

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

from .bf16_qualification import (
    BF16QualificationError,
    NUMERIC_CONTRACT,
    load_qualification_report,
)
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
    ABI_MAJOR,
    Engine,
    LEGACY_ABI_MINOR,
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
    load_production_model_graph,
)


COMPILER_VERSION = "tensor-accelerator-production-projection-0.1.0"
KERNEL_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_kernel.v1"
PHYSICAL_PLAN_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_physical_plan.v1"
)
REQUEST_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_request.v1"
SOURCE_LOCK_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_source_lock.v1"
)
EXPECTATIONS_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_expectations.v1"
)
MANIFEST_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_deployment.v1"
)
HBM_IMAGE_PATH = "memory/hbm_weights_tiled.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
INPUT_PATH = "request/input.bf16.bin"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"


class ProductionProjectionBuildError(RuntimeError):
    """Raised when the real-payload projection cannot be compiled safely."""


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionProjectionBuildError(
            f"compiler artifact path is unsafe: {value!r}"
        )
    return value


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _copy_canonical(source: Path, destination: Path) -> None:
    destination.write_bytes(Path(source).read_bytes())


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    parsed = dict(body)
    parsed[field] = sha256_bytes(canonical_json_bytes(body))
    return parsed


def _tensor_binding(
    model: ProductionModelGraph,
    tensor_id: str,
    *,
    checkpoint_lock_id: str,
) -> tuple[tuple[int, ...], str]:
    tensor = model.tensor_by_id.get(tensor_id)
    if tensor is None or tensor.dtype != "bf16" or tensor.binding is None:
        raise ProductionProjectionBuildError(
            f"production graph lacks bound BF16 tensor {tensor_id!r}"
        )
    binding = tensor.binding
    if binding.checkpoint_lock_id != checkpoint_lock_id:
        raise ProductionProjectionBuildError(
            f"tensor {tensor_id!r} checkpoint binding differs"
        )
    if (
        len(binding.sources) != 1
        or binding.transform.get("kind") != "identity"
        or binding.sources[0].tensor_name != tensor_id
        or binding.sources[0].dtype != "bf16"
        or binding.sources[0].shape != tuple(tensor.shape)
        or binding.payload_sha256 != binding.sources[0].payload_sha256
    ):
        raise ProductionProjectionBuildError(
            f"tensor {tensor_id!r} is not an identity checkpoint binding"
        )
    return binding.sources[0].shape, binding.sources[0].payload_sha256


def _source_operation(
    model: ProductionModelGraph,
    weight_tensor_id: str,
) -> str:
    matches = [
        operation
        for operation in model.operations
        if operation.kind == "MATMUL"
        and weight_tensor_id in operation.inputs
        and operation.numeric_contract == NUMERIC_CONTRACT
    ]
    if len(matches) != 1:
        raise ProductionProjectionBuildError(
            "production graph must contain exactly one qualified source MATMUL"
        )
    operation = matches[0]
    if operation.attributes.get("transpose_weight") is not True:
        raise ProductionProjectionBuildError(
            "source MATMUL does not declare transposed row-major weight semantics"
        )
    return operation.operation_id


def _capture_row(total_shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = total_shape[1] * 2
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


def _read_locked_payloads(
    snapshot: Path,
    checkpoint_lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> tuple[bytes, bytes]:
    input_record = qualification["input"]
    weight_record = qualification["weight"]
    input_name = input_record["tensor"]
    weight_name = weight_record["tensor"]
    row = input_record["row"]
    try:
        with LockedCheckpointReader(Path(snapshot), dict(checkpoint_lock)) as reader:
            input_metadata = reader.tensor_record(input_name)
            input_shape = tuple(input_metadata["shape"])
            if len(input_shape) != 2 or not 0 <= row < input_shape[0]:
                raise ProductionProjectionBuildError(
                    "qualification input row is outside its locked tensor"
                )
            captured, consumer = _capture_row(input_shape, row)
            reader.consume_tensor_payload(input_name, consumer)
            weight_payload = bytearray()
            weight_metadata = reader.consume_tensor_payload(
                weight_name, weight_payload.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionProjectionBuildError(
            f"locked checkpoint payload read failed: {exc}"
        ) from exc
    input_payload = bytes(captured)
    weight_bytes = bytes(weight_payload)
    if (
        input_metadata["payload_sha256"]
        != input_record["source_payload_sha256"]
        or input_metadata["shape"] != input_record["source_shape"]
        or hashlib.sha256(input_payload).hexdigest()
        != input_record["row_payload_sha256"]
        or weight_metadata["payload_sha256"] != weight_record["payload_sha256"]
        or weight_metadata["shape"] != weight_record["shape"]
    ):
        raise ProductionProjectionBuildError(
            "locked checkpoint payloads differ from qualification evidence"
        )
    return input_payload, weight_bytes


def _problem(
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, int]:
    weight_shape = qualification["weight"]["shape"]
    output_shape = qualification["output"]["shape"]
    n, k = weight_shape
    m = output_shape[0]
    if output_shape != [m, n] or m != 1:
        raise ProductionProjectionBuildError(
            "projection qualification must describe [1,K] by [N,K]"
        )
    n_tile = min(64, n, capability.tensor_engine.max_n)
    k_tile = min(256, k, capability.tensor_engine.max_k)
    if (
        capability.tensor_engine.max_m < m
        or n % n_tile
        or k % k_tile
    ):
        raise ProductionProjectionBuildError(
            "projection dimensions are not exactly tileable by the capability"
        )
    tile_bytes = n_tile * k_tile * 2
    if tile_bytes % capability.hbm.burst_bytes:
        raise ProductionProjectionBuildError(
            "one weight tile must contain a whole number of HBM bursts"
        )
    return {
        "k": k,
        "k_tile": k_tile,
        "k_tiles": k // k_tile,
        "m": m,
        "n": n,
        "n_tile": n_tile,
        "n_tiles": n // n_tile,
        "tile_count": (n // n_tile) * (k // k_tile),
    }


def _sram_plan(
    problem: Mapping[str, int],
    capability: ProductionCapability,
) -> dict[str, Any]:
    specs = (
        ("input", 0, "bf16", [problem["m"], problem["k"]], problem["m"] * problem["k"] * 2),
        ("weight_tile", 1, "bf16", [problem["n_tile"], problem["k_tile"]], problem["n_tile"] * problem["k_tile"] * 2),
        ("accumulator_tile", 2, "fp32", [problem["m"], problem["n_tile"]], problem["m"] * problem["n_tile"] * 4),
        ("output", 3, "bf16", [problem["m"], problem["n"]], problem["m"] * problem["n"] * 2),
    )
    regions: list[dict[str, Any]] = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if bank >= capability.sram.banks or allocated > capability.sram.bytes_per_bank:
            raise ProductionProjectionBuildError(
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
    return {
        "addressing": "bank_base_plus_byte_offset",
        "regions": regions,
    }


def _tile_weight_image(
    payload: bytes,
    problem: Mapping[str, int],
    capability: ProductionCapability,
) -> tuple[bytes, list[dict[str, Any]]]:
    weights = np.frombuffer(payload, dtype="<u2").reshape(
        problem["n"], problem["k"]
    )
    image = bytearray()
    tiles: list[dict[str, Any]] = []
    for n_start in range(0, problem["n"], problem["n_tile"]):
        for k_start in range(0, problem["k"], problem["k_tile"]):
            tile = np.ascontiguousarray(
                weights[
                    n_start : n_start + problem["n_tile"],
                    k_start : k_start + problem["k_tile"],
                ],
                dtype="<u2",
            ).tobytes(order="C")
            offset = len(image)
            if offset % capability.hbm.burst_bytes:
                raise ProductionProjectionBuildError("HBM tile offset is misaligned")
            image.extend(tile)
            tile_index = len(tiles)
            tiles.append(
                {
                    "address": capability.hbm.base_address + offset,
                    "k_count": problem["k_tile"],
                    "k_start": k_start,
                    "n_count": problem["n_tile"],
                    "n_start": n_start,
                    "offset_bytes": offset,
                    "payload_sha256": hashlib.sha256(tile).hexdigest(),
                    "size_bytes": len(tile),
                    "tile_index": tile_index,
                }
            )
    return bytes(image), tiles


def _regions_by_id(sram: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {region["id"]: region for region in sram["regions"]}


def _commands(
    tiles: list[dict[str, Any]],
    problem: Mapping[str, int],
    sram: Mapping[str, Any],
) -> tuple[ProductionCommand, ...]:
    regions = _regions_by_id(sram)
    commands: list[ProductionCommand] = []
    for tile in tiles:
        kernel_index = 0
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.DMA_HBM_TO_SRAM,
                engine=Engine.DMA,
                kernel_index=kernel_index,
                source0=tile["address"],
                destination=regions["weight_tile"]["address"],
                size0=tile["size_bytes"],
            )
        )
        flags = 0
        if tile["k_start"] == 0:
            flags |= MATMUL_INIT
        if tile["k_start"] + tile["k_count"] == problem["k"]:
            flags |= MATMUL_FINAL
        commands.append(
            ProductionCommand(
                index=len(commands),
                opcode=Opcode.MATMUL_BF16_TILE,
                engine=Engine.TENSOR,
                flags=flags,
                kernel_index=kernel_index,
                source0=regions["input"]["address"] + tile["k_start"] * 2,
                source1=regions["weight_tile"]["address"],
                destination=regions["accumulator_tile"]["address"],
                auxiliary=regions["output"]["address"] + tile["n_start"] * 2,
                size0=problem["m"],
                size1=tile["n_count"],
                size2=tile["k_count"],
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


def _expected_counters(problem: Mapping[str, int]) -> dict[str, int]:
    tile_count = problem["tile_count"]
    tile_elements = problem["m"] * problem["n_tile"]
    weight_bytes = problem["n"] * problem["k"] * 2
    return {
        "accumulator_sram_bytes_read": (
            problem["n_tiles"] * (problem["k_tiles"] - 1) * tile_elements * 4
        ),
        "accumulator_sram_bytes_written": tile_count * tile_elements * 4,
        "command_count": 2 * tile_count + 1,
        "complete_command_count": 1,
        "dma_command_count": tile_count,
        "dma_sram_bytes_written": weight_bytes,
        "hbm_transferred_bytes_read": weight_bytes,
        "hbm_useful_bytes_read": weight_bytes,
        "input_sram_bytes_read": tile_count * problem["m"] * problem["k_tile"] * 2,
        "matmul_command_count": tile_count,
        "output_sram_bytes_written": problem["m"] * problem["n"] * 2,
        "runtime_input_sram_bytes_written": problem["m"] * problem["k"] * 2,
        "scalar_accumulation_additions": problem["m"] * problem["n"] * problem["k"],
        "scalar_multiplications": problem["m"] * problem["n"] * problem["k"],
        "weight_sram_bytes_read": weight_bytes,
    }


def _kernel_ir(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operation_id: str,
    problem: Mapping[str, int],
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
        "input_fixture": {
            "row": qualification["input"]["row"],
            "row_payload_sha256": qualification["input"]["row_payload_sha256"],
            "tensor_id": qualification["input"]["tensor"],
        },
        "kernel_index": 0,
        "numeric_contract": NUMERIC_CONTRACT,
        "operation": "MATMUL_BF16_TILE",
        "problem": dict(problem),
        "qualification_report_id": qualification["report_id"],
        "reduction_order": "strictly_increasing_k",
        "schema": KERNEL_SCHEMA,
        "source_operation_id": operation_id,
        "weight_tensor_id": qualification["weight"]["tensor"],
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
        sources.append(
            {"role": role, "sha256": digest, "size_bytes": size}
        )
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
    input_payload: bytes,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    operation_id: str,
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
        "input": {
            "dtype": "bf16",
            "path": "input.bf16.bin",
            "payload_sha256": hashlib.sha256(input_payload).hexdigest(),
            "shape": [1, qualification["weight"]["shape"][1]],
            "size_bytes": len(input_payload),
            "source_row": qualification["input"]["row"],
            "source_tensor": qualification["input"]["tensor"],
        },
        "schema": REQUEST_SCHEMA,
        "source_operation_id": operation_id,
    }
    return _identified(body, "request_id")


def _physical_plan(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    operation_id: str,
    problem: Mapping[str, int],
    sram: Mapping[str, Any],
    tiles: list[dict[str, Any]],
    image: bytes,
    command_payload: bytes,
) -> dict[str, Any]:
    counters = _expected_counters(problem)
    body = {
        "capability_id": capability.capability_id,
        "expected_counters": counters,
        "graph_id": model.graph_id,
        "hbm": {
            "image": {
                "base_address": capability.hbm.base_address,
                "path": HBM_IMAGE_PATH,
                "sha256": hashlib.sha256(image).hexdigest(),
                "size_bytes": len(image),
            },
            "source_weight": {
                "checkpoint_lock_id": qualification["checkpoint_lock_id"],
                "dtype": "bf16",
                "payload_sha256": qualification["weight"]["payload_sha256"],
                "shape": qualification["weight"]["shape"],
                "tensor_name": qualification["weight"]["tensor"],
            },
            "tile_layout": "row_major_nk",
            "tile_order": "n_major_k_minor",
            "tiles": tiles,
        },
        "numeric_contract": NUMERIC_CONTRACT,
        "problem": dict(problem),
        "program": {
            "command_count": counters["command_count"],
            "path": COMMAND_PATH,
            "sha256": hashlib.sha256(command_payload).hexdigest(),
            "size_bytes": len(command_payload),
        },
        "qualification_report_id": qualification["report_id"],
        "schema": PHYSICAL_PLAN_SCHEMA,
        "source_operation_id": operation_id,
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
        INPUT_PATH: "known_request_input",
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
            "one real Qwen3-8B BF16 projection with an authenticated input fixture",
            "causal HBM-to-SRAM DMA and ordered tiled matrix execution",
            "uncharacterized functional evidence only",
            "not a complete Qwen layer, model, decode, RTL, 130-nm, HBM PHY, performance, or energy result",
        ],
        "command_abi": {"major": ABI_MAJOR, "minor": LEGACY_ABI_MINOR},
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator projection compiler",
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
        qualification = load_qualification_report(qualification_path)
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        BF16QualificationError,
    ) as exc:
        raise ProductionProjectionBuildError(f"source admission failed: {exc}") from exc
    if qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]:
        raise ProductionProjectionBuildError(
            "qualification and checkpoint lock identities differ"
        )
    input_tensor_id = qualification["input"]["tensor"]
    weight_tensor_id = qualification["weight"]["tensor"]
    input_shape, input_hash = _tensor_binding(
        model, input_tensor_id, checkpoint_lock_id=checkpoint_lock["lock_id"]
    )
    weight_shape, weight_hash = _tensor_binding(
        model, weight_tensor_id, checkpoint_lock_id=checkpoint_lock["lock_id"]
    )
    if (
        list(input_shape) != qualification["input"]["source_shape"]
        or input_hash != qualification["input"]["source_payload_sha256"]
        or list(weight_shape) != qualification["weight"]["shape"]
        or weight_hash != qualification["weight"]["payload_sha256"]
    ):
        raise ProductionProjectionBuildError(
            "qualification tensors differ from production graph bindings"
        )
    operation_id = _source_operation(model, weight_tensor_id)
    input_payload, weight_payload = _read_locked_payloads(
        snapshot, checkpoint_lock, qualification
    )
    problem = _problem(qualification, capability)
    if len(input_payload) != problem["m"] * problem["k"] * 2:
        raise ProductionProjectionBuildError("runtime input byte size differs")
    if len(weight_payload) != problem["n"] * problem["k"] * 2:
        raise ProductionProjectionBuildError("weight byte size differs")
    sram = _sram_plan(problem, capability)
    image, tiles = _tile_weight_image(weight_payload, problem, capability)
    commands = _commands(tiles, problem, sram)
    if len(commands) > capability.limits["max_commands"]:
        raise ProductionProjectionBuildError("command count exceeds capability")
    if capability.command_abi_minor != LEGACY_ABI_MINOR:
        raise ProductionProjectionBuildError(
            "projection evidence requires its frozen ABI 2.0 capability"
        )
    command_payload = encode(commands, abi_minor=LEGACY_ABI_MINOR)
    kernel_ir = _kernel_ir(model, qualification, operation_id, problem)
    plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        operation_id=operation_id,
        problem=problem,
        sram=sram,
        tiles=tiles,
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
    request = _request(input_payload, model, qualification, operation_id)

    for directory in ("checks", "ir", "memory", "physical", "program", "request", "source"):
        (root / directory).mkdir()
    write_canonical_json(root / "capability.json", capability.to_dict())
    write_canonical_json(root / "ir/tensor_kernel_ir.json", kernel_ir)
    (root / HBM_IMAGE_PATH).write_bytes(image)
    write_canonical_json(root / PHYSICAL_PLAN_PATH, plan)
    (root / COMMAND_PATH).write_bytes(command_payload)
    _write_text(
        root / "program/commands.disasm",
        disassemble(commands, abi_minor=LEGACY_ABI_MINOR),
    )
    (root / INPUT_PATH).write_bytes(input_payload)
    write_canonical_json(root / REQUEST_PATH, request)
    write_canonical_json(root / "source.lock.json", source_lock)
    _copy_canonical(checkpoint_lock_path, root / "source/checkpoint.lock.json")
    _copy_canonical(model_graph_path, root / "source/model_graph.v2.json")
    _copy_canonical(qualification_path, root / "source/qualification.json")

    from .production_projection_checking import check_projection_candidate

    independent_check = check_projection_candidate(
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
        "output_payload_sha256": qualification["output"]["payload_sha256"],
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


def build_projection_deployment(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    qualification_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Build and atomically publish one independently checked deployment."""

    snapshot = Path(snapshot).resolve()
    checkpoint_lock_path = Path(checkpoint_lock_path).resolve()
    model_graph_path = Path(model_graph_path).resolve()
    capability_path = Path(capability_path).resolve()
    qualification_path = Path(qualification_path).resolve()
    output = Path(output).resolve()
    if not snapshot.is_dir():
        raise ProductionProjectionBuildError(
            f"checkpoint snapshot does not exist: {snapshot}"
        )
    for label, path in (
        ("checkpoint lock", checkpoint_lock_path),
        ("model graph", model_graph_path),
        ("capability", capability_path),
        ("qualification report", qualification_path),
    ):
        if not path.is_file():
            raise ProductionProjectionBuildError(f"{label} does not exist: {path}")
    if output.exists():
        raise ProductionProjectionBuildError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent)
    )
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
    "INPUT_PATH",
    "KERNEL_SCHEMA",
    "MANIFEST_SCHEMA",
    "PHYSICAL_PLAN_PATH",
    "PHYSICAL_PLAN_SCHEMA",
    "ProductionProjectionBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_projection_deployment",
]
