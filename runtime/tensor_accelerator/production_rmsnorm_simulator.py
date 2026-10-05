"""Artifact-only causal simulator for embedding-to-RMSNorm ABI 2.1."""

from __future__ import annotations

from dataclasses import dataclass
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
    Opcode,
    ProductionCommandError,
    RMSNORM_ABI_MINOR,
    command_abi,
    decode,
)

from .rmsnorm import RMSNormKernelError, rms_norm_bf16


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_deployment.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_request.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_expectations.v1"
REPORT_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_execution.v1"
EXPECTED_ROLES = {
    "capability.json": "hardware_capability",
    "checks/independent_check.json": "independent_check",
    "execution_expectations.json": "execution_expectations",
    "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
    "memory/hbm_embedding_rmsnorm.bin": "hbm_image",
    "physical/physical_plan.json": "physical_plan",
    "program/commands.bin": "command_program",
    "program/commands.disasm": "command_disassembly",
    "request/execution_request.json": "known_request",
    "source.lock.json": "source_lock",
    "source/checkpoint.lock.json": "checkpoint_lock",
    "source/model_graph.v2.json": "model_graph",
    "source/qualification.json": "qualification_report",
}
EXPECTED_CLAIM_BOUNDARY = [
    "one authenticated Qwen3-8B token embedding row through layer-0 input RMSNorm",
    "runtime-indexed HBM lookup, explicit banked SRAM placement, and causal vector execution",
    "uncharacterized functional evidence only",
    "not a complete Qwen layer, model, decode, timing, RTL, 130-nm, HBM PHY, performance, or energy result",
]
COUNTER_NAMES = (
    "command_count",
    "complete_command_count",
    "direct_dma_command_count",
    "dma_command_count",
    "dma_sram_bytes_written",
    "epsilon_additions",
    "final_weight_multiplications",
    "hbm_transferred_bytes_read",
    "hbm_useful_bytes_read",
    "indexed_dma_command_count",
    "input_square_multiplications",
    "input_sram_bytes_read",
    "mean_divisions",
    "normalization_multiplications",
    "output_sram_bytes_written",
    "reciprocal_square_roots",
    "reduction_additions",
    "rmsnorm_command_count",
    "runtime_request_sram_bytes_written",
    "weight_sram_bytes_read",
)


class ProductionRMSNormSimulationError(RuntimeError):
    """Raised when artifact admission or causal execution fails closed."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionRMSNormSimulationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionRMSNormSimulationError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductionRMSNormSimulationError(f"{label} must be a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionRMSNormSimulationError(f"{label} must be a safe relative path")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionRMSNormSimulationError(f"{label} {field} differs")


@dataclass
class _SRAMRegion:
    region_id: str
    address: int
    logical_bytes: int
    allocated_bytes: int
    data: bytearray
    initialized: bytearray

    @classmethod
    def create(cls, record: Mapping[str, Any]) -> _SRAMRegion:
        allocated = record["allocated_bytes"]
        return cls(
            region_id=record["id"],
            address=record["address"],
            logical_bytes=record["logical_bytes"],
            allocated_bytes=allocated,
            data=bytearray(allocated),
            initialized=bytearray(allocated),
        )

    def contains(self, address: int, size: int, *, logical: bool = True) -> bool:
        limit = self.logical_bytes if logical else self.allocated_bytes
        offset = address - self.address
        return size >= 0 and offset >= 0 and offset + size <= limit

    def write(self, address: int, payload: bytes) -> None:
        if not self.contains(address, len(payload)):
            raise ProductionRMSNormSimulationError(
                f"write escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + len(payload)
        self.data[start:end] = payload
        self.initialized[start:end] = b"\x01" * len(payload)

    def read(self, address: int, size: int) -> bytes:
        if not self.contains(address, size):
            raise ProductionRMSNormSimulationError(
                f"read escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + size
        if not all(self.initialized[start:end]):
            raise ProductionRMSNormSimulationError(
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
        raise ProductionRMSNormSimulationError("manifest schema differs")
    for field in (
        "capability_id",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_report_id",
        "source_lock_id",
    ):
        require_sha256(value[field], f"manifest.{field}")
    if value["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY:
        raise ProductionRMSNormSimulationError("manifest claim boundary differs")
    if value["command_abi"] != {
        "major": ABI_MAJOR,
        "minor": RMSNORM_ABI_MINOR,
    }:
        raise ProductionRMSNormSimulationError("manifest command ABI differs")
    if value["compiler"] != {
        "deterministic": True,
        "name": "OpenTallas tensor-accelerator RMSNorm compiler",
        "version": "tensor-accelerator-production-rmsnorm-0.1.0",
    }:
        raise ProductionRMSNormSimulationError("manifest compiler identity differs")
    if value["entrypoint"] != {
        "capability": "capability.json",
        "command_program": "program/commands.bin",
        "hbm_image": "memory/hbm_embedding_rmsnorm.bin",
        "physical_plan": "physical/physical_plan.json",
        "request": "request/execution_request.json",
    }:
        raise ProductionRMSNormSimulationError("manifest entrypoint differs")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_ROLES):
        raise ProductionRMSNormSimulationError("manifest artifact coverage differs")
    paths: list[str] = []
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionRMSNormSimulationError(f"artifact {index} is malformed")
        exact_keys(record, {"path", "role", "sha256", "size_bytes"}, set(), f"artifact {index}")
        path = _safe_relative(record["path"], f"artifact {index}.path")
        if EXPECTED_ROLES.get(path) != record["role"]:
            raise ProductionRMSNormSimulationError(f"artifact role differs for {path!r}")
        payload = (root / path).read_bytes()
        if (
            record["size_bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ProductionRMSNormSimulationError(f"artifact identity differs for {path!r}")
        paths.append(path)
    if paths != sorted(EXPECTED_ROLES):
        raise ProductionRMSNormSimulationError("manifest artifacts are not canonical")
    return value


def _problem(raw: Any, capability: ProductionCapability) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormSimulationError("problem must be an object")
    exact_keys(
        raw,
        {
            "resident_embedding_base_token",
            "resident_embedding_rows",
            "row_bytes",
            "rows",
            "width",
        },
        set(),
        "problem",
    )
    result = {
        key: require_int(raw[key], f"problem.{key}", minimum=0)
        for key in raw
    }
    if (
        result["resident_embedding_rows"] < 1
        or result["rows"] < 1
        or result["width"] < 1
        or result["row_bytes"] != result["width"] * 2
        or capability.vector_engine is None
        or result["rows"] > capability.vector_engine.max_rows
        or result["width"] > capability.vector_engine.max_width
    ):
        raise ProductionRMSNormSimulationError("problem exceeds capability")
    return result


def _regions(
    raw: Any,
    capability: ProductionCapability,
) -> tuple[dict[str, _SRAMRegion], dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormSimulationError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionRMSNormSimulationError("SRAM addressing differs")
    records = raw["regions"]
    if not isinstance(records, list) or not 1 <= len(records) <= capability.limits[
        "max_sram_regions"
    ]:
        raise ProductionRMSNormSimulationError("SRAM region count is illegal")
    parsed: dict[str, dict[str, Any]] = {}
    intervals: list[tuple[int, int, str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ProductionRMSNormSimulationError(f"SRAM region {index} is malformed")
        exact_keys(
            record,
            {"address", "allocated_bytes", "bank", "dtype", "id", "logical_bytes", "shape"},
            set(),
            f"SRAM region {index}",
        )
        region_id = record["id"]
        if not isinstance(region_id, str) or not region_id or region_id in parsed:
            raise ProductionRMSNormSimulationError("SRAM region IDs are invalid")
        bank = require_int(record["bank"], f"SRAM region {index}.bank", minimum=0)
        address = require_int(record["address"], f"SRAM region {index}.address", minimum=0)
        logical = require_int(record["logical_bytes"], f"SRAM region {index}.logical_bytes", minimum=1)
        allocated = require_int(record["allocated_bytes"], f"SRAM region {index}.allocated_bytes", minimum=1)
        if (
            bank >= capability.sram.banks
            or address != capability.sram.bank_base(bank)
            or allocated != align_up(logical, capability.sram.word_bytes)
            or allocated > capability.sram.bytes_per_bank
            or not isinstance(record["dtype"], str)
            or not isinstance(record["shape"], list)
        ):
            raise ProductionRMSNormSimulationError(f"SRAM region {region_id!r} is illegal")
        intervals.append((address, address + allocated, region_id))
        parsed[region_id] = dict(record)
    intervals.sort()
    if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
        raise ProductionRMSNormSimulationError("SRAM regions overlap")
    required = {"token_id", "embedding", "rmsnorm_weight", "output"}
    if set(parsed) != required:
        raise ProductionRMSNormSimulationError("SRAM semantic regions differ")
    return ({key: _SRAMRegion.create(value) for key, value in parsed.items()}, parsed)


def _hbm(
    raw: Any,
    root: Path,
    capability: ProductionCapability,
) -> tuple[bytes, dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormSimulationError("HBM plan must be an object")
    exact_keys(raw, {"image", "regions"}, set(), "HBM plan")
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionRMSNormSimulationError("HBM image record is malformed")
    exact_keys(image_record, {"base_address", "path", "sha256", "size_bytes"}, set(), "HBM image")
    path = _safe_relative(image_record["path"], "HBM image path")
    image = (root / path).read_bytes()
    if (
        path != "memory/hbm_embedding_rmsnorm.bin"
        or image_record["base_address"] != capability.hbm.base_address
        or image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) % capability.hbm.burst_bytes
    ):
        raise ProductionRMSNormSimulationError("HBM image identity differs")
    raw_regions = raw["regions"]
    if not isinstance(raw_regions, list) or len(raw_regions) != 2:
        raise ProductionRMSNormSimulationError("HBM region coverage differs")
    regions: dict[str, dict[str, Any]] = {}
    covered = bytearray(len(image))
    for index, record in enumerate(raw_regions):
        if not isinstance(record, dict):
            raise ProductionRMSNormSimulationError(f"HBM region {index} is malformed")
        exact_keys(record, {"address", "id", "offset_bytes", "payload_sha256", "size_bytes", "source"}, set(), f"HBM region {index}")
        region_id = record["id"]
        offset = require_int(record["offset_bytes"], f"HBM region {index}.offset", minimum=0)
        size = require_int(record["size_bytes"], f"HBM region {index}.size", minimum=1)
        if (
            not isinstance(region_id, str)
            or region_id in regions
            or offset % capability.hbm.burst_bytes
            or record["address"] != capability.hbm.base_address + offset
            or offset + size > len(image)
            or record["payload_sha256"]
            != hashlib.sha256(image[offset : offset + size]).hexdigest()
            or not isinstance(record["source"], dict)
            or any(covered[offset : offset + size])
        ):
            raise ProductionRMSNormSimulationError(f"HBM region {region_id!r} is illegal")
        covered[offset : offset + size] = b"\x01" * size
        regions[region_id] = dict(record)
    if set(regions) != {"embedding_rows", "rmsnorm_weight"}:
        raise ProductionRMSNormSimulationError("HBM semantic regions differ")
    if any(byte and not marked for byte, marked in zip(image, covered, strict=True)):
        raise ProductionRMSNormSimulationError("HBM uncovered padding is nonzero")
    return image, regions


def _plan(
    root: Path,
    manifest: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[
    dict[str, Any],
    dict[str, _SRAMRegion],
    dict[str, dict[str, Any]],
    bytes,
    dict[str, dict[str, Any]],
    tuple[Any, ...],
]:
    value = _load_canonical(root / "physical/physical_plan.json", "physical plan")
    exact_keys(
        value,
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
    _identity(value, "physical_plan_id", "physical plan")
    if (
        value["schema"] != PHYSICAL_PLAN_SCHEMA
        or value["physical_plan_id"] != manifest["physical_plan_id"]
        or value["capability_id"] != capability.capability_id
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
        or value["numeric_contracts"]
        != ["bf16_payload_lookup_v1", "qwen3_rmsnorm_fp32_bf16_v1"]
        or not isinstance(value["source_operation_ids"], list)
        or len(value["source_operation_ids"]) != 2
    ):
        raise ProductionRMSNormSimulationError("physical-plan identities differ")
    problem = _problem(value["problem"], capability)
    value["problem"] = problem
    regions, records = _regions(value["sram"], capability)
    image, hbm_regions = _hbm(value["hbm"], root, capability)
    program = value["program"]
    if not isinstance(program, dict):
        raise ProductionRMSNormSimulationError("program record is malformed")
    exact_keys(program, {"command_count", "path", "sha256", "size_bytes"}, set(), "program")
    program_path = _safe_relative(program["path"], "program path")
    payload = (root / program_path).read_bytes()
    if (
        program_path != "program/commands.bin"
        or program["size_bytes"] != len(payload)
        or program["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise ProductionRMSNormSimulationError("program identity differs")
    try:
        commands = decode(payload)
        observed_abi = command_abi(payload)
    except ProductionCommandError as exc:
        raise ProductionRMSNormSimulationError(f"command decode failed: {exc}") from exc
    if observed_abi != (capability.command_abi_major, capability.command_abi_minor):
        raise ProductionRMSNormSimulationError("program and capability ABI differ")
    if program["command_count"] != len(commands):
        raise ProductionRMSNormSimulationError("program command count differs")
    counters = value["expected_counters"]
    if not isinstance(counters, dict) or tuple(sorted(counters)) != tuple(sorted(COUNTER_NAMES)):
        raise ProductionRMSNormSimulationError("counter expectation names differ")
    for name in COUNTER_NAMES:
        require_int(counters[name], f"counter {name}", minimum=0)
    return value, regions, records, image, hbm_regions, commands


def _expectations(root: Path, manifest: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    value = _load_canonical(root / "execution_expectations.json", "execution expectations")
    exact_keys(
        value,
        {
            "check_id",
            "counters",
            "expectations_id",
            "normalized_payload_sha256",
            "output_payload_sha256",
            "qualification_report_id",
            "schema",
        },
        set(),
        "execution expectations",
    )
    _identity(value, "expectations_id", "execution expectations")
    if (
        value["schema"] != EXPECTATIONS_SCHEMA
        or value["check_id"] != manifest["independent_check_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
        or value["counters"] != plan["expected_counters"]
    ):
        raise ProductionRMSNormSimulationError("execution expectations differ")
    require_sha256(value["normalized_payload_sha256"], "normalized output hash")
    require_sha256(value["output_payload_sha256"], "output hash")
    return value


def _request(path: Path, plan: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    value = _load_canonical(path, "execution request")
    exact_keys(value, {"graph_id", "request_id", "schema", "source_operation_ids", "token"}, set(), "execution request")
    _identity(value, "request_id", "execution request")
    if (
        value["schema"] != REQUEST_SCHEMA
        or value["graph_id"] != plan["graph_id"]
        or value["source_operation_ids"] != plan["source_operation_ids"]
        or not isinstance(value["token"], dict)
        or set(value["token"]) != {"dtype", "token_id"}
        or value["token"]["dtype"] != "u32"
    ):
        raise ProductionRMSNormSimulationError("execution request identity differs")
    token_id = require_int(value["token"]["token_id"], "token_id", minimum=0, maximum=0xFFFFFFFF)
    return value, token_id


def _region_for(
    regions: Mapping[str, _SRAMRegion], address: int, size: int
) -> _SRAMRegion:
    matches = [region for region in regions.values() if region.contains(address, size)]
    if len(matches) != 1:
        raise ProductionRMSNormSimulationError("SRAM address resolves to zero or multiple regions")
    return matches[0]


class ProductionRMSNormSimulator:
    """Immutable deployment whose commands causally produce RMSNorm output."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: dict[str, Any],
        capability: ProductionCapability,
        plan: dict[str, Any],
        region_records: dict[str, dict[str, Any]],
        image: bytes,
        hbm_regions: dict[str, dict[str, Any]],
        commands: tuple[Any, ...],
        expectations: dict[str, Any],
    ):
        self._root = root
        self._manifest = manifest
        self._capability = capability
        self._plan = plan
        self._region_records = region_records
        self._image = image
        self._hbm_regions = hbm_regions
        self._commands = commands
        self._expectations = expectations

    @classmethod
    def load(cls, root: Path) -> ProductionRMSNormSimulator:
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionRMSNormSimulationError(
                f"deployment directory does not exist: {deployment}"
            )
        manifest = _manifest(deployment)
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionRMSNormSimulationError(f"capability load failed: {exc}") from exc
        if (
            capability.capability_id != manifest["capability_id"]
            or (capability.command_abi_major, capability.command_abi_minor)
            != (ABI_MAJOR, RMSNORM_ABI_MINOR)
        ):
            raise ProductionRMSNormSimulationError("manifest capability identity differs")
        plan, _, records, image, hbm_regions, commands = _plan(
            deployment, manifest, capability
        )
        expectations = _expectations(deployment, manifest, plan)
        return cls(
            root=deployment,
            manifest=manifest,
            capability=capability,
            plan=plan,
            region_records=records,
            image=image,
            hbm_regions=hbm_regions,
            commands=commands,
            expectations=expectations,
        )

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        request_file = (
            self._root / self._manifest["entrypoint"]["request"]
            if request_path is None
            else Path(request_path).resolve()
        )
        request, token_id = _request(request_file, self._plan)
        regions = {
            region_id: _SRAMRegion.create(record)
            for region_id, record in self._region_records.items()
        }
        token_payload = struct.pack("<I", token_id)
        regions["token_id"].write(regions["token_id"].address, token_payload)
        counters = {name: 0 for name in COUNTER_NAMES}
        counters["runtime_request_sram_bytes_written"] = len(token_payload)
        trace: list[dict[str, Any]] = []
        output_written = False
        completed = False
        normalized_payload: bytes | None = None
        mean_square_code: int | None = None
        inverse_rms_code: int | None = None
        normalized_saturations = 0
        output_saturations = 0
        hbm_base = self._capability.hbm.base_address

        for command in self._commands:
            counters["command_count"] += 1
            if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                if (
                    command.source0 < hbm_base
                    or command.source0 % self._capability.hbm.burst_bytes
                    or command.size0 % self._capability.hbm.burst_bytes
                ):
                    raise ProductionRMSNormSimulationError("direct DMA alignment is illegal")
                offset = command.source0 - hbm_base
                end = offset + command.size0
                if end > len(self._image):
                    raise ProductionRMSNormSimulationError("direct DMA escapes HBM image")
                payload = self._image[offset:end]
                destination = _region_for(regions, command.destination, len(payload))
                destination.write(command.destination, payload)
                counters["direct_dma_command_count"] += 1
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

            if command.opcode == Opcode.DMA_HBM_INDEXED_TO_SRAM:
                index_region = _region_for(regions, command.source1, command.size3)
                index_payload = index_region.read(command.source1, command.size3)
                logical_index = struct.unpack("<I", index_payload)[0]
                relative_index = logical_index - command.auxiliary
                if not 0 <= relative_index < command.size2 or command.size1 < command.size0:
                    raise ProductionRMSNormSimulationError("indexed DMA index or stride is illegal")
                source = command.source0 + relative_index * command.size1
                if (
                    source < hbm_base
                    or source % self._capability.hbm.burst_bytes
                    or command.size0 % self._capability.hbm.burst_bytes
                ):
                    raise ProductionRMSNormSimulationError("indexed DMA alignment is illegal")
                offset = source - hbm_base
                end = offset + command.size0
                if end > len(self._image):
                    raise ProductionRMSNormSimulationError("indexed DMA escapes HBM image")
                payload = self._image[offset:end]
                destination = _region_for(regions, command.destination, len(payload))
                destination.write(command.destination, payload)
                counters["indexed_dma_command_count"] += 1
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
                        "logical_index": logical_index,
                        "opcode": command.opcode.name,
                        "payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "size_bytes": len(payload),
                        "source": source,
                    }
                )
                continue

            if command.opcode == Opcode.RMSNORM_BF16:
                if output_written:
                    raise ProductionRMSNormSimulationError("RMSNorm output is written twice")
                element_count = command.size0 * command.size1
                input_bytes = _region_for(
                    regions, command.source0, element_count * 2
                ).read(command.source0, element_count * 2)
                weight_bytes = _region_for(
                    regions, command.source1, command.size1 * 2
                ).read(command.source1, command.size1 * 2)
                destination = _region_for(
                    regions, command.destination, element_count * 2
                )
                inputs = np.frombuffer(input_bytes, dtype="<u2").reshape(
                    command.size0, command.size1
                )
                weights = np.frombuffer(weight_bytes, dtype="<u2")
                try:
                    result = rms_norm_bf16(
                        inputs, weights, epsilon_code=command.size2
                    )
                except RMSNormKernelError as exc:
                    raise ProductionRMSNormSimulationError(
                        f"RMSNorm numeric execution failed: {exc}"
                    ) from exc
                output_payload = result.values.astype(
                    "<u2", copy=False
                ).tobytes(order="C")
                normalized_payload = result.normalized_values.astype(
                    "<u2", copy=False
                ).tobytes(order="C")
                destination.write(command.destination, output_payload)
                output_written = True
                mean_square_code = int(result.mean_square_codes[0])
                inverse_rms_code = int(result.inverse_rms_codes[0])
                normalized_saturations = result.normalized_saturated_element_count
                output_saturations = result.output_saturated_element_count
                counters["rmsnorm_command_count"] += 1
                counters["input_square_multiplications"] += element_count
                counters["reduction_additions"] += command.size0 * (command.size1 - 1)
                counters["mean_divisions"] += command.size0
                counters["epsilon_additions"] += command.size0
                counters["reciprocal_square_roots"] += command.size0
                counters["normalization_multiplications"] += element_count
                counters["final_weight_multiplications"] += element_count
                counters["input_sram_bytes_read"] += len(input_bytes)
                counters["weight_sram_bytes_read"] += len(weight_bytes)
                counters["output_sram_bytes_written"] += len(output_payload)
                trace.append(
                    {
                        "command_index": command.index,
                        "inverse_rms_binary32_code": inverse_rms_code,
                        "mean_square_binary32_code": mean_square_code,
                        "normalized_payload_sha256": hashlib.sha256(
                            normalized_payload
                        ).hexdigest(),
                        "opcode": command.opcode.name,
                        "output_payload_sha256": hashlib.sha256(
                            output_payload
                        ).hexdigest(),
                    }
                )
                continue

            if command.opcode == Opcode.COMPLETE:
                if not output_written or completed:
                    raise ProductionRMSNormSimulationError(
                        "COMPLETE observes missing or duplicate output"
                    )
                completed = True
                counters["complete_command_count"] += 1
                trace.append({"command_index": command.index, "opcode": command.opcode.name})
                continue
            raise ProductionRMSNormSimulationError(
                f"unsupported production opcode {command.opcode!r}"
            )

        if not completed or counters != self._plan["expected_counters"]:
            raise ProductionRMSNormSimulationError(
                "completion or observed counters differ from expectations"
            )
        output_region = regions["output"]
        output_payload = output_region.read(output_region.address, output_region.logical_bytes)
        if normalized_payload is None:
            raise ProductionRMSNormSimulationError("normalized diagnostic is missing")
        if (
            hashlib.sha256(normalized_payload).hexdigest()
            != self._expectations["normalized_payload_sha256"]
            or hashlib.sha256(output_payload).hexdigest()
            != self._expectations["output_payload_sha256"]
        ):
            raise ProductionRMSNormSimulationError(
                "causal output differs from independent expectations"
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
                "inverse_rms_binary32_code": inverse_rms_code,
                "mean_square_binary32_code": mean_square_code,
                "normalized_payload_sha256": hashlib.sha256(
                    normalized_payload
                ).hexdigest(),
                "normalized_saturated_element_count": normalized_saturations,
                "payload_sha256": hashlib.sha256(output_payload).hexdigest(),
                "saturated_element_count": output_saturations,
                "shape": [self._plan["problem"]["rows"], self._plan["problem"]["width"]],
                "size_bytes": len(output_payload),
            },
            "physical_plan_id": self._plan["physical_plan_id"],
            "request_id": request["request_id"],
            "schema": REPORT_SCHEMA,
            "status": "pass",
            "timing": {"reason": "capability_uncharacterized", "status": "unavailable"},
            "trace": trace,
            "trace_sha256": hashlib.sha256(canonical_json_bytes(trace)).hexdigest(),
        }
        return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def publish_rmsnorm_execution_report(
    report: Mapping[str, Any], output_path: Path
) -> None:
    """Atomically retain one authenticated execution report without overwrite."""

    if not isinstance(report, Mapping):
        raise ProductionRMSNormSimulationError("execution report must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionRMSNormSimulationError("execution report identity differs")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent, prefix=f".{output.name}.", suffix=".tmp"
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
            raise ProductionRMSNormSimulationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "ProductionRMSNormSimulationError",
    "ProductionRMSNormSimulator",
    "publish_rmsnorm_execution_report",
]
