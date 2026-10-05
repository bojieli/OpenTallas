"""Artifact-only causal simulator for the production BF16 projection ABI."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
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
    SUPPORTED_ABI_MINORS,
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    ProductionCommandError,
    command_abi,
    decode,
)

from .bf16 import (
    BF16KernelError,
    NUMERIC_CONTRACT,
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
)


MANIFEST_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_deployment.v1"
)
PHYSICAL_PLAN_SCHEMA = (
    "opentallas.tensor_accelerator.bf16_projection_physical_plan.v1"
)
REQUEST_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_request.v1"
REPORT_SCHEMA = "opentallas.tensor_accelerator.bf16_projection_execution.v1"
EXPECTED_ROLES = {
    "capability.json": "hardware_capability",
    "checks/independent_check.json": "independent_check",
    "execution_expectations.json": "execution_expectations",
    "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
    "memory/hbm_weights_tiled.bin": "hbm_image",
    "physical/physical_plan.json": "physical_plan",
    "program/commands.bin": "command_program",
    "program/commands.disasm": "command_disassembly",
    "request/execution_request.json": "known_request",
    "request/input.bf16.bin": "known_request_input",
    "source.lock.json": "source_lock",
    "source/checkpoint.lock.json": "checkpoint_lock",
    "source/model_graph.v2.json": "model_graph",
    "source/qualification.json": "qualification_report",
}
EXPECTED_CLAIM_BOUNDARY = [
    "one real Qwen3-8B BF16 projection with an authenticated input fixture",
    "causal HBM-to-SRAM DMA and ordered tiled matrix execution",
    "uncharacterized functional evidence only",
    "not a complete Qwen layer, model, decode, RTL, 130-nm, HBM PHY, performance, or energy result",
]
COUNTER_NAMES = (
    "accumulator_sram_bytes_read",
    "accumulator_sram_bytes_written",
    "command_count",
    "complete_command_count",
    "dma_command_count",
    "dma_sram_bytes_written",
    "hbm_transferred_bytes_read",
    "hbm_useful_bytes_read",
    "input_sram_bytes_read",
    "matmul_command_count",
    "output_sram_bytes_written",
    "runtime_input_sram_bytes_written",
    "scalar_accumulation_additions",
    "scalar_multiplications",
    "weight_sram_bytes_read",
)


class ProductionSimulationError(RuntimeError):
    """Raised when deployment loading or causal execution fails closed."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionSimulationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionSimulationError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductionSimulationError(f"{label} must be a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionSimulationError(f"{label} must be a safe relative path")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionSimulationError(f"{label} {field} differs from content")


@dataclass
class _Region:
    region_id: str
    address: int
    logical_bytes: int
    allocated_bytes: int
    data: bytearray
    initialized: bytearray

    @classmethod
    def create(cls, record: Mapping[str, Any]) -> _Region:
        allocated = record["allocated_bytes"]
        return cls(
            region_id=record["id"],
            address=record["address"],
            logical_bytes=record["logical_bytes"],
            allocated_bytes=allocated,
            data=bytearray(allocated),
            initialized=bytearray(allocated),
        )

    def _offset(self, address: int, size: int, *, logical: bool) -> tuple[int, int]:
        if size < 0:
            raise ProductionSimulationError("memory access has negative size")
        start = address - self.address
        end = start + size
        limit = self.logical_bytes if logical else self.allocated_bytes
        if start < 0 or end > limit:
            raise ProductionSimulationError(
                f"memory access escapes SRAM region {self.region_id!r}"
            )
        return start, end

    def write(self, address: int, payload: bytes, *, logical: bool = True) -> None:
        start, end = self._offset(address, len(payload), logical=logical)
        self.data[start:end] = payload
        self.initialized[start:end] = b"\x01" * len(payload)

    def read(self, address: int, size: int, *, logical: bool = True) -> bytes:
        start, end = self._offset(address, size, logical=logical)
        if not all(self.initialized[start:end]):
            raise ProductionSimulationError(
                f"read of uninitialized SRAM region {self.region_id!r}"
            )
        return bytes(self.data[start:end])


def _manifest(root: Path) -> dict[str, Any]:
    value = _load_canonical(root / "deployment_manifest.json", "deployment manifest")
    exact_keys(
        value,
        {
            "artifacts",
            "build_id",
            "capability_id",
            "claim_boundary",
            "command_abi",
            "compiler",
            "entrypoint",
            "graph_id",
            "independent_check_id",
            "kernel_ir_id",
            "physical_plan_id",
            "qualification_report_id",
            "schema",
            "source_lock_id",
        },
        set(),
        "deployment manifest",
    )
    _identity(value, "build_id", "deployment manifest")
    if value["schema"] != MANIFEST_SCHEMA:
        raise ProductionSimulationError("deployment manifest schema differs")
    for identity_field in (
        "capability_id",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_report_id",
        "source_lock_id",
    ):
        require_sha256(value[identity_field], f"manifest.{identity_field}")
    if value["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY:
        raise ProductionSimulationError("deployment claim boundary differs")
    manifest_abi = value["command_abi"]
    if (
        not isinstance(manifest_abi, dict)
        or set(manifest_abi) != {"major", "minor"}
        or manifest_abi["major"] != ABI_MAJOR
        or manifest_abi["minor"] not in SUPPORTED_ABI_MINORS
    ):
        raise ProductionSimulationError("deployment command ABI differs")
    compiler = value["compiler"]
    if (
        not isinstance(compiler, dict)
        or set(compiler) != {"deterministic", "name", "version"}
        or compiler["deterministic"] is not True
        or compiler["name"] != "OpenTallas tensor-accelerator projection compiler"
        or not isinstance(compiler["version"], str)
        or not compiler["version"]
    ):
        raise ProductionSimulationError("deployment compiler identity differs")
    entrypoint = value["entrypoint"]
    expected_entrypoint = {
        "capability": "capability.json",
        "command_program": "program/commands.bin",
        "hbm_image": "memory/hbm_weights_tiled.bin",
        "physical_plan": "physical/physical_plan.json",
        "request": "request/execution_request.json",
    }
    if entrypoint != expected_entrypoint:
        raise ProductionSimulationError("deployment entrypoint differs")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_ROLES):
        raise ProductionSimulationError("deployment artifact coverage differs")
    observed_paths: list[str] = []
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionSimulationError(f"artifact {index} is malformed")
        exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            set(),
            f"artifact {index}",
        )
        path = _safe_relative(record["path"], f"artifact {index}.path")
        if EXPECTED_ROLES.get(path) != record["role"]:
            raise ProductionSimulationError(f"artifact {index} role differs")
        artifact_path = root / path
        try:
            payload = artifact_path.read_bytes()
        except OSError as exc:
            raise ProductionSimulationError(
                f"cannot read manifested artifact {path!r}: {exc}"
            ) from exc
        if (
            record["size_bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ProductionSimulationError(
                f"manifested artifact {path!r} SHA-256 or size differs"
            )
        observed_paths.append(path)
    if observed_paths != sorted(EXPECTED_ROLES):
        raise ProductionSimulationError("deployment artifacts are not canonical")
    return value


def _parse_problem(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ProductionSimulationError("physical problem must be an object")
    keys = {"k", "k_tile", "k_tiles", "m", "n", "n_tile", "n_tiles", "tile_count"}
    exact_keys(raw, keys, set(), "physical problem")
    result = {
        key: require_int(raw[key], f"physical problem.{key}", minimum=1)
        for key in keys
    }
    if (
        result["m"] != 1
        or result["n"] != result["n_tile"] * result["n_tiles"]
        or result["k"] != result["k_tile"] * result["k_tiles"]
        or result["tile_count"] != result["n_tiles"] * result["k_tiles"]
    ):
        raise ProductionSimulationError("physical problem tiling is inconsistent")
    return result


def _parse_regions(
    raw: Any,
    capability: ProductionCapability,
    problem: Mapping[str, int],
) -> tuple[dict[str, _Region], dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionSimulationError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionSimulationError("SRAM addressing differs")
    raw_regions = raw["regions"]
    if not isinstance(raw_regions, list) or len(raw_regions) != 4:
        raise ProductionSimulationError("SRAM region coverage differs")
    expected_ids = ("input", "weight_tile", "accumulator_tile", "output")
    expected_shapes = {
        "input": [problem["m"], problem["k"]],
        "weight_tile": [problem["n_tile"], problem["k_tile"]],
        "accumulator_tile": [problem["m"], problem["n_tile"]],
        "output": [problem["m"], problem["n"]],
    }
    expected_dtypes = {
        "input": "bf16",
        "weight_tile": "bf16",
        "accumulator_tile": "fp32",
        "output": "bf16",
    }
    element_bytes = {"bf16": 2, "fp32": 4}
    regions: dict[str, _Region] = {}
    records: dict[str, dict[str, Any]] = {}
    occupied: list[tuple[int, int]] = []
    for index, record in enumerate(raw_regions):
        if not isinstance(record, dict):
            raise ProductionSimulationError(f"SRAM region {index} is malformed")
        exact_keys(
            record,
            {"address", "allocated_bytes", "bank", "dtype", "id", "logical_bytes", "shape"},
            set(),
            f"SRAM region {index}",
        )
        region_id = record["id"]
        if region_id != expected_ids[index]:
            raise ProductionSimulationError("SRAM region order differs")
        bank = require_int(record["bank"], f"SRAM {region_id}.bank", minimum=0)
        dtype = record["dtype"]
        shape = record["shape"]
        if (
            bank >= capability.sram.banks
            or record["address"] != capability.sram.bank_base(bank)
            or dtype != expected_dtypes[region_id]
            or shape != expected_shapes[region_id]
        ):
            raise ProductionSimulationError(f"SRAM region {region_id!r} differs")
        logical = element_bytes[dtype]
        for dimension in shape:
            logical *= dimension
        allocated = align_up(logical, capability.sram.word_bytes)
        if (
            record["logical_bytes"] != logical
            or record["allocated_bytes"] != allocated
            or allocated > capability.sram.bytes_per_bank
        ):
            raise ProductionSimulationError(
                f"SRAM region {region_id!r} extent differs"
            )
        start = record["address"]
        end = start + allocated
        if any(start < other_end and other_start < end for other_start, other_end in occupied):
            raise ProductionSimulationError("SRAM regions overlap")
        occupied.append((start, end))
        records[region_id] = dict(record)
        regions[region_id] = _Region.create(record)
    return regions, records


def _parse_plan(
    root: Path,
    manifest: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[dict[str, Any], dict[str, _Region], dict[str, dict[str, Any]], bytes, tuple[Any, ...]]:
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
        or plan["capability_id"] != manifest["capability_id"]
        or plan["graph_id"] != manifest["graph_id"]
        or plan["physical_plan_id"] != manifest["physical_plan_id"]
        or plan["qualification_report_id"] != manifest["qualification_report_id"]
        or plan["numeric_contract"] != NUMERIC_CONTRACT
    ):
        raise ProductionSimulationError("physical-plan identities differ")
    problem = _parse_problem(plan["problem"])
    if (
        problem["m"] > capability.tensor_engine.max_m
        or problem["n_tile"] > capability.tensor_engine.max_n
        or problem["k_tile"] > capability.tensor_engine.max_k
    ):
        raise ProductionSimulationError("physical problem exceeds tensor capability")
    counters = plan["expected_counters"]
    if not isinstance(counters, dict) or set(counters) != set(COUNTER_NAMES):
        raise ProductionSimulationError("expected counter coverage differs")
    for name in COUNTER_NAMES:
        require_int(counters[name], f"expected counter {name}", minimum=0)
    regions, region_records = _parse_regions(plan["sram"], capability, problem)

    hbm = plan["hbm"]
    if not isinstance(hbm, dict):
        raise ProductionSimulationError("HBM plan must be an object")
    exact_keys(
        hbm,
        {"image", "source_weight", "tile_layout", "tile_order", "tiles"},
        set(),
        "HBM plan",
    )
    if hbm["tile_layout"] != "row_major_nk" or hbm["tile_order"] != "n_major_k_minor":
        raise ProductionSimulationError("HBM tile layout differs")
    source_weight = hbm["source_weight"]
    if not isinstance(source_weight, dict):
        raise ProductionSimulationError("HBM source-weight record is malformed")
    exact_keys(
        source_weight,
        {"checkpoint_lock_id", "dtype", "payload_sha256", "shape", "tensor_name"},
        set(),
        "HBM source weight",
    )
    if (
        source_weight["dtype"] != "bf16"
        or source_weight["shape"] != [problem["n"], problem["k"]]
        or not isinstance(source_weight["tensor_name"], str)
        or not source_weight["tensor_name"]
    ):
        raise ProductionSimulationError("HBM source-weight semantics differ")
    require_sha256(
        source_weight["checkpoint_lock_id"], "HBM source checkpoint_lock_id"
    )
    require_sha256(source_weight["payload_sha256"], "HBM source payload_sha256")
    image_record = hbm["image"]
    if not isinstance(image_record, dict):
        raise ProductionSimulationError("HBM image record is malformed")
    exact_keys(
        image_record,
        {"base_address", "path", "sha256", "size_bytes"},
        set(),
        "HBM image",
    )
    image_path = _safe_relative(image_record["path"], "HBM image path")
    if (
        image_path != "memory/hbm_weights_tiled.bin"
        or image_record["base_address"] != capability.hbm.base_address
    ):
        raise ProductionSimulationError("HBM image placement differs")
    image = (root / image_path).read_bytes()
    if (
        image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) > capability.hbm.capacity_bytes
    ):
        raise ProductionSimulationError("HBM image identity or capacity differs")
    tiles = hbm["tiles"]
    if not isinstance(tiles, list) or len(tiles) != problem["tile_count"]:
        raise ProductionSimulationError("HBM tile count differs")
    expected_offset = 0
    tile_bytes = problem["n_tile"] * problem["k_tile"] * 2
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise ProductionSimulationError(f"HBM tile {index} is malformed")
        exact_keys(
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
            f"HBM tile {index}",
        )
        payload = image[expected_offset : expected_offset + tile_bytes]
        expected_n_start = (index // problem["k_tiles"]) * problem["n_tile"]
        expected_k_start = (index % problem["k_tiles"]) * problem["k_tile"]
        if (
            tile["tile_index"] != index
            or tile["offset_bytes"] != expected_offset
            or tile["address"] != capability.hbm.base_address + expected_offset
            or tile["size_bytes"] != tile_bytes
            or tile["n_count"] != problem["n_tile"]
            or tile["k_count"] != problem["k_tile"]
            or tile["n_start"] != expected_n_start
            or tile["k_start"] != expected_k_start
            or tile["payload_sha256"] != hashlib.sha256(payload).hexdigest()
            or tile["address"] % capability.hbm.burst_bytes
        ):
            raise ProductionSimulationError(f"HBM tile {index} identity differs")
        expected_offset += tile_bytes
    if expected_offset != len(image):
        raise ProductionSimulationError("HBM image has uncovered bytes")

    program = plan["program"]
    if not isinstance(program, dict):
        raise ProductionSimulationError("program record is malformed")
    exact_keys(program, {"command_count", "path", "sha256", "size_bytes"}, set(), "program")
    program_path = _safe_relative(program["path"], "program path")
    if program_path != "program/commands.bin":
        raise ProductionSimulationError("program path differs")
    program_payload = (root / program_path).read_bytes()
    if (
        program["size_bytes"] != len(program_payload)
        or program["sha256"] != hashlib.sha256(program_payload).hexdigest()
    ):
        raise ProductionSimulationError("program identity differs")
    try:
        commands = decode(program_payload)
        observed_abi = command_abi(program_payload)
    except ProductionCommandError as exc:
        raise ProductionSimulationError(f"command decode failed: {exc}") from exc
    if observed_abi != (
        capability.command_abi_major,
        capability.command_abi_minor,
    ):
        raise ProductionSimulationError("program and capability command ABI differ")
    if program["command_count"] != len(commands):
        raise ProductionSimulationError("program command count differs")
    return plan, regions, region_records, image, commands


def _request(path: Path, plan: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    request = _load_canonical(path, "projection request")
    exact_keys(
        request,
        {"graph_id", "input", "request_id", "schema", "source_operation_id"},
        set(),
        "projection request",
    )
    _identity(request, "request_id", "projection request")
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["graph_id"] != plan["graph_id"]
        or request["source_operation_id"] != plan["source_operation_id"]
    ):
        raise ProductionSimulationError("projection request identity differs")
    input_record = request["input"]
    if not isinstance(input_record, dict):
        raise ProductionSimulationError("projection input record is malformed")
    exact_keys(
        input_record,
        {
            "dtype",
            "path",
            "payload_sha256",
            "shape",
            "size_bytes",
            "source_row",
            "source_tensor",
        },
        set(),
        "projection input",
    )
    problem = plan["problem"]
    input_path = _safe_relative(input_record["path"], "projection input path")
    try:
        payload = (path.parent / input_path).read_bytes()
    except OSError as exc:
        raise ProductionSimulationError(f"cannot read projection input: {exc}") from exc
    if (
        input_record["dtype"] != "bf16"
        or input_record["shape"] != [problem["m"], problem["k"]]
        or input_record["size_bytes"] != len(payload)
        or input_record["size_bytes"] != problem["m"] * problem["k"] * 2
        or input_record["payload_sha256"] != hashlib.sha256(payload).hexdigest()
        or not isinstance(input_record["source_tensor"], str)
        or not input_record["source_tensor"]
    ):
        raise ProductionSimulationError("projection input payload or shape differs")
    require_int(input_record["source_row"], "projection input source_row", minimum=0)
    codes = np.frombuffer(payload, dtype="<u2")
    if np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise ProductionSimulationError("projection input contains BF16 NaN or infinity")
    return request, payload


class ProductionProjectionSimulator:
    """Loaded immutable deployment whose commands causally produce output bytes."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: dict[str, Any],
        capability: ProductionCapability,
        plan: dict[str, Any],
        region_records: dict[str, dict[str, Any]],
        image: bytes,
        commands: tuple[Any, ...],
    ):
        self._root = root
        self._manifest = manifest
        self._capability = capability
        self._plan = plan
        self._region_records = region_records
        self._image = image
        self._commands = commands

    @classmethod
    def load(cls, root: Path) -> ProductionProjectionSimulator:
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionSimulationError(
                f"deployment directory does not exist: {deployment}"
            )
        manifest = _manifest(deployment)
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionSimulationError(f"capability load failed: {exc}") from exc
        if capability.capability_id != manifest["capability_id"]:
            raise ProductionSimulationError("manifest capability identity differs")
        if manifest["command_abi"] != {
            "major": capability.command_abi_major,
            "minor": capability.command_abi_minor,
        }:
            raise ProductionSimulationError("manifest and capability command ABI differ")
        plan, _, region_records, image, commands = _parse_plan(
            deployment, manifest, capability
        )
        return cls(
            root=deployment,
            manifest=manifest,
            capability=capability,
            plan=plan,
            region_records=region_records,
            image=image,
            commands=commands,
        )

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        request_file = (
            self._root / self._manifest["entrypoint"]["request"]
            if request_path is None
            else Path(request_path).resolve()
        )
        request, input_payload = _request(request_file, self._plan)
        regions = {
            region_id: _Region.create(record)
            for region_id, record in self._region_records.items()
        }
        regions["input"].write(regions["input"].address, input_payload)
        counters = {name: 0 for name in COUNTER_NAMES}
        counters["runtime_input_sram_bytes_written"] = len(input_payload)
        trace: list[dict[str, Any]] = []
        fresh_dma = False
        active_n: int | None = None
        next_k = 0
        completed_n: set[int] = set()
        saturation_count = 0
        problem = self._plan["problem"]
        hbm_base = self._capability.hbm.base_address
        input_base = regions["input"].address
        output_base = regions["output"].address

        for command in self._commands:
            counters["command_count"] += 1
            if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                if fresh_dma:
                    raise ProductionSimulationError(
                        "DMA overwrote an unconsumed SRAM weight tile"
                    )
                if (
                    command.destination != regions["weight_tile"].address
                    or command.source0 < hbm_base
                    or command.source0 % self._capability.hbm.burst_bytes
                    or command.size0 % self._capability.hbm.burst_bytes
                ):
                    raise ProductionSimulationError("DMA address or alignment is illegal")
                image_offset = command.source0 - hbm_base
                image_end = image_offset + command.size0
                if image_offset < 0 or image_end > len(self._image):
                    raise ProductionSimulationError("DMA reads outside HBM image")
                payload = self._image[image_offset:image_end]
                regions["weight_tile"].write(command.destination, payload)
                fresh_dma = True
                counters["dma_command_count"] += 1
                counters["hbm_useful_bytes_read"] += len(payload)
                counters["hbm_transferred_bytes_read"] += align_up(
                    len(payload), self._capability.hbm.burst_bytes
                )
                counters["dma_sram_bytes_written"] += len(payload)
                trace.append(
                    {
                        "command_index": command.index,
                        "destination": command.destination,
                        "opcode": command.opcode.name,
                        "payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "size_bytes": len(payload),
                        "source": command.source0,
                    }
                )
                continue

            if command.opcode == Opcode.MATMUL_BF16_TILE:
                if not fresh_dma:
                    raise ProductionSimulationError(
                        "MATMUL lacks a fresh causally preceding DMA"
                    )
                fresh_dma = False
                if (
                    command.size0 != problem["m"]
                    or command.size1 != problem["n_tile"]
                    or command.size2 != problem["k_tile"]
                    or command.source1 != regions["weight_tile"].address
                    or command.destination != regions["accumulator_tile"].address
                    or (command.source0 - input_base) % 2
                    or (command.auxiliary - output_base) % 2
                ):
                    raise ProductionSimulationError("MATMUL shape or SRAM address is illegal")
                k_start = (command.source0 - input_base) // 2
                n_start = (command.auxiliary - output_base) // 2
                if (
                    k_start < 0
                    or k_start + command.size2 > problem["k"]
                    or n_start < 0
                    or n_start + command.size1 > problem["n"]
                    or k_start % problem["k_tile"]
                    or n_start % problem["n_tile"]
                ):
                    raise ProductionSimulationError("MATMUL logical tile coordinate is illegal")
                is_init = bool(command.flags & MATMUL_INIT)
                is_final = bool(command.flags & MATMUL_FINAL)
                if is_init:
                    if active_n is not None or k_start != 0 or n_start in completed_n:
                        raise ProductionSimulationError("MATMUL INIT ordering is illegal")
                    active_n = n_start
                    next_k = 0
                    accumulator = None
                else:
                    if active_n != n_start:
                        raise ProductionSimulationError(
                            "MATMUL accumulation has no matching active output tile"
                        )
                    accumulator_payload = regions["accumulator_tile"].read(
                        regions["accumulator_tile"].address,
                        command.size0 * command.size1 * 4,
                    )
                    accumulator = np.frombuffer(
                        accumulator_payload, dtype="<u4"
                    ).reshape(command.size0, command.size1)
                    counters["accumulator_sram_bytes_read"] += len(
                        accumulator_payload
                    )
                if k_start != next_k:
                    raise ProductionSimulationError(
                        "MATMUL K segments are not strictly increasing"
                    )
                input_bytes = regions["input"].read(
                    command.source0, command.size0 * command.size2 * 2
                )
                weight_bytes = regions["weight_tile"].read(
                    command.source1, command.size1 * command.size2 * 2
                )
                inputs = np.frombuffer(input_bytes, dtype="<u2").reshape(
                    command.size0, command.size2
                )
                weights = np.frombuffer(weight_bytes, dtype="<u2").reshape(
                    command.size1, command.size2
                )
                try:
                    accumulated = accumulate_bf16_tile_fp32(
                        inputs, weights, accumulator
                    )
                except BF16KernelError as exc:
                    raise ProductionSimulationError(
                        f"MATMUL numeric execution failed: {exc}"
                    ) from exc
                accumulator_bytes = accumulated.values.astype(
                    "<u4", copy=False
                ).tobytes(order="C")
                regions["accumulator_tile"].write(
                    regions["accumulator_tile"].address, accumulator_bytes
                )
                counters["matmul_command_count"] += 1
                counters["input_sram_bytes_read"] += len(input_bytes)
                counters["weight_sram_bytes_read"] += len(weight_bytes)
                counters["accumulator_sram_bytes_written"] += len(
                    accumulator_bytes
                )
                scalar_operations = command.size0 * command.size1 * command.size2
                counters["scalar_multiplications"] += scalar_operations
                counters["scalar_accumulation_additions"] += scalar_operations
                next_k += command.size2
                trace_record: dict[str, Any] = {
                    "accumulator_sha256": hashlib.sha256(
                        accumulator_bytes
                    ).hexdigest(),
                    "command_index": command.index,
                    "flags": command.flags,
                    "k_start": k_start,
                    "n_start": n_start,
                    "opcode": command.opcode.name,
                }
                if is_final:
                    if next_k != problem["k"] or active_n != n_start:
                        raise ProductionSimulationError("MATMUL FINAL ordering is illegal")
                    try:
                        finalized = finalize_bf16_accumulator(accumulated.values)
                    except BF16KernelError as exc:
                        raise ProductionSimulationError(
                            f"MATMUL finalization failed: {exc}"
                        ) from exc
                    output_bytes = finalized.values.astype(
                        "<u2", copy=False
                    ).tobytes(order="C")
                    regions["output"].write(command.auxiliary, output_bytes)
                    counters["output_sram_bytes_written"] += len(output_bytes)
                    saturation_count += finalized.output_saturated_element_count
                    trace_record["output_sha256"] = hashlib.sha256(
                        output_bytes
                    ).hexdigest()
                    completed_n.add(n_start)
                    active_n = None
                    next_k = 0
                elif next_k == problem["k"]:
                    raise ProductionSimulationError(
                        "last MATMUL K segment lacks FINAL"
                    )
                trace.append(trace_record)
                continue

            if command.opcode == Opcode.COMPLETE:
                if fresh_dma or active_n is not None:
                    raise ProductionSimulationError(
                        "COMPLETE observes unconsumed DMA or unfinished accumulation"
                    )
                expected_outputs = set(range(0, problem["n"], problem["n_tile"]))
                if completed_n != expected_outputs:
                    raise ProductionSimulationError(
                        "COMPLETE observes incomplete output-tile coverage"
                    )
                counters["complete_command_count"] += 1
                trace.append(
                    {"command_index": command.index, "opcode": command.opcode.name}
                )
                continue
            raise ProductionSimulationError(
                f"unsupported production opcode {command.opcode!r}"
            )

        if counters != self._plan["expected_counters"]:
            raise ProductionSimulationError(
                "observed execution counters differ from physical-plan expectations"
            )
        output_payload = regions["output"].read(
            regions["output"].address, regions["output"].logical_bytes
        )
        output_codes = np.frombuffer(output_payload, dtype="<u2")
        body = {
            "build_id": self._manifest["build_id"],
            "capability_id": self._capability.capability_id,
            "counter_reconciliation": "exact",
            "counters": counters,
            "mode": "artifact_only_data_bearing_functional",
            "output": {
                "codes": [int(value) for value in output_codes],
                "dtype": "bf16",
                "payload_sha256": hashlib.sha256(output_payload).hexdigest(),
                "saturated_element_count": saturation_count,
                "shape": [problem["m"], problem["n"]],
                "size_bytes": len(output_payload),
            },
            "physical_plan_id": self._plan["physical_plan_id"],
            "request_id": request["request_id"],
            "schema": REPORT_SCHEMA,
            "status": "pass",
            "timing": {
                "reason": "capability_uncharacterized",
                "status": "unavailable",
            },
            "trace": trace,
            "trace_sha256": hashlib.sha256(canonical_json_bytes(trace)).hexdigest(),
        }
        return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def publish_execution_report(report: Mapping[str, Any], output_path: Path) -> None:
    """Atomically retain one authenticated execution report without overwrite."""

    if not isinstance(report, Mapping):
        raise ProductionSimulationError("execution report must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionSimulationError("execution report identity or status differs")
    output = Path(output_path)
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
            raise ProductionSimulationError(
                f"execution report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "ProductionProjectionSimulator",
    "ProductionSimulationError",
    "REPORT_SCHEMA",
    "publish_execution_report",
]
