"""Causal artifact-only simulator for production Q/K/V deployments.

The simulator parses only emitted deployment artifacts and runtime inputs.  It
does not import the Q/K/V compiler, independent checker, Model Graph, framework,
or scalar oracle.  Every output byte is produced by decoded ABI commands.
"""

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
    ABI_MINOR,
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    ProductionCommandError,
    command_abi,
    decode,
)

from .bf16 import (
    BF16KernelError,
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
)
from .rmsnorm import RMSNormKernelError, rms_norm_bf16
from .rope import RoPEKernelError, rope_bf16


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.qkv_deployment.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.qkv_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qkv_request.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.qkv_expectations.v1"
REPORT_SCHEMA = "opentallas.tensor_accelerator.qkv_execution.v1"
EXPECTED_ROLES = {
    "capability.json": "hardware_capability",
    "checks/independent_check.json": "independent_check",
    "execution_expectations.json": "execution_expectations",
    "ir/tensor_kernel_ir.json": "tensor_kernel_ir",
    "memory/hbm_qkv.bin": "hbm_image",
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
    "one authenticated Qwen3-8B token through layer-0 Q/K/V preparation",
    "embedding, RMSNorm, segmented Q/K/V projection, per-head normalization, and position-indexed RoPE",
    "deterministic HBM image, explicit 16-bank SRAM plan, independently checked ABI 2.2 program, and artifact-only functional execution",
    "uncharacterized functional evidence only; not attention, KV state, a complete layer, model decoding, timing, RTL, 130-nm, performance, or energy evidence",
]
NUMERIC_CONTRACTS = [
    "bf16_payload_lookup_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "qwen3_rmsnorm_fp32_bf16_v1",
    "qwen3_rope_fp32_bf16_v1",
]
COUNTER_NAMES = (
    "accumulator_sram_bytes_read",
    "accumulator_sram_bytes_written",
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
    "matmul_command_count",
    "matmul_input_sram_bytes_read",
    "matmul_output_sram_bytes_written",
    "matmul_weight_sram_bytes_read",
    "mean_divisions",
    "normalization_multiplications",
    "reciprocal_square_roots",
    "reduction_additions",
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
)
SRAM_REGION_IDS = {
    "runtime_ids",
    "embedding",
    "input_norm_weight",
    "attention_norm",
    "weight_tile",
    "accumulator_tile",
    "q_raw",
    "k_raw",
    "v",
    "q_norm_weight",
    "k_norm_weight",
    "q_norm",
    "k_norm",
    "rope_coefficients",
    "q_rotary",
    "k_rotary",
}


class ProductionQKVSimulationError(RuntimeError):
    """Raised when artifact loading or causal Q/K/V execution fails."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionQKVSimulationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionQKVSimulationError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProductionQKVSimulationError(f"{label} must be a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ProductionQKVSimulationError(f"{label} escapes the deployment")
    return path.as_posix()


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: item for key, item in value.items() if key != field}
    expected = sha256_bytes(canonical_json_bytes(body))
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionQKVSimulationError(str(exc)) from exc
    if observed != expected:
        raise ProductionQKVSimulationError(f"{label} identity differs")


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

    def contains(self, address: int, size: int) -> bool:
        offset = address - self.address
        return size >= 0 and offset >= 0 and offset + size <= self.logical_bytes

    def write(self, address: int, payload: bytes) -> None:
        if not self.contains(address, len(payload)):
            raise ProductionQKVSimulationError(
                f"write escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + len(payload)
        self.data[start:end] = payload
        self.initialized[start:end] = b"\x01" * len(payload)

    def read(self, address: int, size: int) -> bytes:
        if not self.contains(address, size):
            raise ProductionQKVSimulationError(
                f"read escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + size
        if not all(self.initialized[start:end]):
            raise ProductionQKVSimulationError(
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
        raise ProductionQKVSimulationError("manifest schema differs")
    for field in (
        "capability_id",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_report_id",
        "source_lock_id",
    ):
        try:
            require_sha256(value[field], f"manifest.{field}")
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
    if value["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY:
        raise ProductionQKVSimulationError("manifest claim boundary differs")
    if value["command_abi"] != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        raise ProductionQKVSimulationError("manifest command ABI differs")
    if value["compiler"] != {
        "deterministic": True,
        "name": "OpenTallas tensor-accelerator Q/K/V compiler",
        "version": "tensor-accelerator-production-qkv-0.1.0",
    }:
        raise ProductionQKVSimulationError("manifest compiler identity differs")
    if value["entrypoint"] != {
        "capability": "capability.json",
        "command_program": "program/commands.bin",
        "hbm_image": "memory/hbm_qkv.bin",
        "physical_plan": "physical/physical_plan.json",
        "request": "request/execution_request.json",
    }:
        raise ProductionQKVSimulationError("manifest entrypoint differs")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_ROLES):
        raise ProductionQKVSimulationError("manifest artifact coverage differs")
    paths: list[str] = []
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError(f"artifact {index} is malformed")
        exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            set(),
            f"artifact {index}",
        )
        path = _safe_relative(record["path"], f"artifact {index}.path")
        if EXPECTED_ROLES.get(path) != record["role"]:
            raise ProductionQKVSimulationError(f"artifact role differs for {path!r}")
        try:
            payload = (root / path).read_bytes()
        except OSError as exc:
            raise ProductionQKVSimulationError(
                f"cannot read artifact {path!r}: {exc}"
            ) from exc
        if (
            record["size_bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ProductionQKVSimulationError(
                f"artifact identity differs for {path!r}"
            )
        paths.append(path)
    if paths != sorted(EXPECTED_ROLES):
        raise ProductionQKVSimulationError("manifest artifacts are not canonical")
    return value


def _problem(raw: Any, capability: ProductionCapability) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProductionQKVSimulationError("problem must be an object")
    exact_keys(
        raw,
        {
            "coefficient_row_bytes",
            "context_positions",
            "head_dim",
            "hidden_width",
            "key_value_heads",
            "projections",
            "query_heads",
            "resident_embedding_base_token",
            "resident_embedding_rows",
        },
        set(),
        "problem",
    )
    integer_fields = (
        "coefficient_row_bytes",
        "context_positions",
        "head_dim",
        "hidden_width",
        "key_value_heads",
        "query_heads",
        "resident_embedding_base_token",
        "resident_embedding_rows",
    )
    try:
        result = dict(raw)
        for field in integer_fields:
            result[field] = require_int(raw[field], f"problem.{field}", minimum=0)
    except ArtifactError as exc:
        raise ProductionQKVSimulationError(str(exc)) from exc
    vector = capability.vector_engine
    if (
        result["coefficient_row_bytes"] != result["head_dim"] * 4
        or result["context_positions"] < 1
        or result["head_dim"] < 2
        or result["hidden_width"] < 1
        or result["query_heads"] < 1
        or result["key_value_heads"] < 1
        or result["resident_embedding_rows"] < 1
        or vector is None
        or result["hidden_width"] > vector.max_width
        or result["query_heads"] + result["key_value_heads"] > vector.max_rows
        or vector.max_rope_positions is None
        or result["context_positions"] > vector.max_rope_positions
        or vector.max_query_heads is None
        or result["query_heads"] > vector.max_query_heads
        or vector.max_key_value_heads is None
        or result["key_value_heads"] > vector.max_key_value_heads
        or result["head_dim"] != vector.rope_head_dim
    ):
        raise ProductionQKVSimulationError("problem exceeds capability")
    projections = raw["projections"]
    if not isinstance(projections, list) or len(projections) != 3:
        raise ProductionQKVSimulationError("projection problem coverage differs")
    parsed_projections = []
    for index, record in enumerate(projections):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError("projection problem is malformed")
        exact_keys(
            record,
            {
                "k",
                "k_tile",
                "k_tiles",
                "n",
                "n_tile",
                "n_tiles",
                "role",
                "tile_count",
            },
            set(),
            f"projection problem {index}",
        )
        try:
            parsed = {
                field: require_int(record[field], f"projection.{field}", minimum=1)
                for field in (
                    "k",
                    "k_tile",
                    "k_tiles",
                    "n",
                    "n_tile",
                    "n_tiles",
                    "tile_count",
                )
            }
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
        parsed["role"] = record["role"]
        if (
            parsed["role"] not in {"q", "k", "v"}
            or parsed["k"] != result["hidden_width"]
            or parsed["k"] != parsed["k_tile"] * parsed["k_tiles"]
            or parsed["n"] != parsed["n_tile"] * parsed["n_tiles"]
            or parsed["tile_count"] != parsed["k_tiles"] * parsed["n_tiles"]
            or parsed["k_tile"] > capability.tensor_engine.max_k
            or parsed["n_tile"] > capability.tensor_engine.max_n
        ):
            raise ProductionQKVSimulationError("projection problem is illegal")
        parsed_projections.append(parsed)
    if [item["role"] for item in parsed_projections] != ["q", "k", "v"]:
        raise ProductionQKVSimulationError("projection role order differs")
    if parsed_projections[0]["n"] != result["query_heads"] * result["head_dim"] or any(
        item["n"] != result["key_value_heads"] * result["head_dim"]
        for item in parsed_projections[1:]
    ):
        raise ProductionQKVSimulationError("projection shape and head bounds differ")
    result["projections"] = parsed_projections
    return result


def _regions(raw: Any, capability: ProductionCapability) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ProductionQKVSimulationError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionQKVSimulationError("SRAM addressing differs")
    records = raw["regions"]
    if (
        not isinstance(records, list)
        or not 1 <= len(records) <= capability.limits["max_sram_regions"]
    ):
        raise ProductionQKVSimulationError("SRAM region count is illegal")
    parsed: dict[str, dict[str, Any]] = {}
    intervals: list[tuple[int, int, str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError(f"SRAM region {index} is malformed")
        exact_keys(
            record,
            {
                "address",
                "allocated_bytes",
                "bank",
                "dtype",
                "id",
                "logical_bytes",
                "shape",
            },
            set(),
            f"SRAM region {index}",
        )
        region_id = record["id"]
        try:
            bank = require_int(record["bank"], f"SRAM region {index}.bank", minimum=0)
            address = require_int(
                record["address"], f"SRAM region {index}.address", minimum=0
            )
            logical = require_int(
                record["logical_bytes"],
                f"SRAM region {index}.logical_bytes",
                minimum=1,
            )
            allocated = require_int(
                record["allocated_bytes"],
                f"SRAM region {index}.allocated_bytes",
                minimum=1,
            )
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
        if (
            not isinstance(region_id, str)
            or not region_id
            or region_id in parsed
            or bank >= capability.sram.banks
            or address != capability.sram.bank_base(bank)
            or allocated != align_up(logical, capability.sram.word_bytes)
            or allocated > capability.sram.bytes_per_bank
            or record["dtype"] not in {"bf16", "fp32", "u32"}
            or not isinstance(record["shape"], list)
            or not record["shape"]
        ):
            raise ProductionQKVSimulationError(f"SRAM region {region_id!r} is illegal")
        intervals.append((address, address + allocated, region_id))
        parsed[region_id] = dict(record)
    intervals.sort()
    if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
        raise ProductionQKVSimulationError("SRAM regions overlap")
    if set(parsed) != SRAM_REGION_IDS:
        raise ProductionQKVSimulationError("SRAM semantic regions differ")
    if {record["bank"] for record in parsed.values()} != set(range(16)):
        raise ProductionQKVSimulationError("Q/K/V SRAM bank coverage differs")
    return parsed


def _hbm(
    raw: Any,
    root: Path,
    capability: ProductionCapability,
    problem: Mapping[str, Any],
) -> tuple[bytes, dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionQKVSimulationError("HBM plan must be an object")
    exact_keys(
        raw,
        {"image", "projection_sources", "projection_tiles", "regions"},
        set(),
        "HBM plan",
    )
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionQKVSimulationError("HBM image record is malformed")
    exact_keys(
        image_record,
        {"base_address", "path", "sha256", "size_bytes"},
        set(),
        "HBM image",
    )
    path = _safe_relative(image_record["path"], "HBM image path")
    try:
        image = (root / path).read_bytes()
    except OSError as exc:
        raise ProductionQKVSimulationError(f"cannot read HBM image: {exc}") from exc
    if (
        path != "memory/hbm_qkv.bin"
        or image_record["base_address"] != capability.hbm.base_address
        or image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) % capability.hbm.burst_bytes
        or len(image) > capability.hbm.capacity_bytes
    ):
        raise ProductionQKVSimulationError("HBM image identity differs")
    covered = bytearray(len(image))

    def cover(record: Mapping[str, Any], label: str) -> bytes:
        try:
            offset = require_int(record["offset_bytes"], f"{label}.offset", minimum=0)
            size = require_int(record["size_bytes"], f"{label}.size", minimum=1)
            address = require_int(record["address"], f"{label}.address", minimum=0)
            digest = require_sha256(record["payload_sha256"], f"{label}.hash")
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
        if (
            offset % capability.hbm.burst_bytes
            or address != capability.hbm.base_address + offset
            or offset + size > len(image)
            or any(covered[offset : offset + size])
        ):
            raise ProductionQKVSimulationError(f"{label} range is illegal")
        payload = image[offset : offset + size]
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ProductionQKVSimulationError(f"{label} identity differs")
        covered[offset : offset + size] = b"\x01" * size
        return payload

    raw_regions = raw["regions"]
    if not isinstance(raw_regions, list) or len(raw_regions) != 5:
        raise ProductionQKVSimulationError("HBM region coverage differs")
    regions: dict[str, dict[str, Any]] = {}
    expected_roles = {
        "embedding_rows": "embedding",
        "input_norm_weight": "input_norm_weight",
        "q_norm_weight": "q_norm_weight",
        "k_norm_weight": "k_norm_weight",
        "rope_coefficient_table": "rope_coefficients",
    }
    for index, record in enumerate(raw_regions):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError(f"HBM region {index} is malformed")
        exact_keys(
            record,
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
        region_id = record["id"]
        if (
            not isinstance(region_id, str)
            or region_id in regions
            or expected_roles.get(region_id) != record["source_role"]
        ):
            raise ProductionQKVSimulationError("HBM semantic region differs")
        payload = cover(record, f"HBM region {index}")
        if (
            region_id == "rope_coefficient_table"
            and len(payload)
            != problem["context_positions"] * problem["coefficient_row_bytes"]
        ):
            raise ProductionQKVSimulationError("RoPE coefficient table size differs")
        regions[region_id] = dict(record)
    if set(regions) != set(expected_roles):
        raise ProductionQKVSimulationError("HBM semantic region IDs differ")
    sources = raw["projection_sources"]
    if not isinstance(sources, list) or len(sources) != 3:
        raise ProductionQKVSimulationError("projection source coverage differs")
    source_roles = []
    for index, record in enumerate(sources):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError("projection source is malformed")
        exact_keys(
            record,
            {"payload_sha256", "projection_role", "shape", "tensor_name"},
            set(),
            f"projection source {index}",
        )
        try:
            require_sha256(record["payload_sha256"], "projection source hash")
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
        if (
            record["projection_role"] not in {"q", "k", "v"}
            or not isinstance(record["shape"], list)
            or not isinstance(record["tensor_name"], str)
        ):
            raise ProductionQKVSimulationError("projection source differs")
        source_roles.append(record["projection_role"])
    if source_roles != ["q", "k", "v"]:
        raise ProductionQKVSimulationError("projection source role order differs")
    projection_by_role = {item["role"]: item for item in problem["projections"]}
    raw_tiles = raw["projection_tiles"]
    expected_count = sum(item["tile_count"] for item in problem["projections"])
    if not isinstance(raw_tiles, list) or len(raw_tiles) != expected_count:
        raise ProductionQKVSimulationError("projection tile count differs")
    coordinates = set()
    for index, record in enumerate(raw_tiles):
        if not isinstance(record, dict):
            raise ProductionQKVSimulationError("projection tile is malformed")
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
                "projection_role",
                "size_bytes",
                "tile_index",
            },
            set(),
            f"projection tile {index}",
        )
        role = record["projection_role"]
        if role not in projection_by_role:
            raise ProductionQKVSimulationError("projection tile role differs")
        projection = projection_by_role[role]
        try:
            n_start = require_int(record["n_start"], "tile.n_start", minimum=0)
            k_start = require_int(record["k_start"], "tile.k_start", minimum=0)
            n_count = require_int(record["n_count"], "tile.n_count", minimum=1)
            k_count = require_int(record["k_count"], "tile.k_count", minimum=1)
            tile_index = require_int(record["tile_index"], "tile.index", minimum=0)
        except ArtifactError as exc:
            raise ProductionQKVSimulationError(str(exc)) from exc
        if (
            n_count != projection["n_tile"]
            or k_count != projection["k_tile"]
            or n_start % n_count
            or k_start % k_count
            or n_start + n_count > projection["n"]
            or k_start + k_count > projection["k"]
            or tile_index
            != n_start // n_count * projection["k_tiles"] + k_start // k_count
        ):
            raise ProductionQKVSimulationError("projection tile coordinate differs")
        cover(record, f"projection tile {index}")
        coordinate = (role, n_start, k_start)
        if coordinate in coordinates:
            raise ProductionQKVSimulationError("projection tile coordinate repeats")
        coordinates.add(coordinate)
    expected_coordinates = {
        (projection["role"], n_start, k_start)
        for projection in problem["projections"]
        for n_start in range(0, projection["n"], projection["n_tile"])
        for k_start in range(0, projection["k"], projection["k_tile"])
    }
    if coordinates != expected_coordinates:
        raise ProductionQKVSimulationError("projection tile coverage differs")
    if any(byte and not mark for byte, mark in zip(image, covered, strict=True)):
        raise ProductionQKVSimulationError("HBM uncovered padding is nonzero")
    return image, regions


def _plan(
    root: Path,
    manifest: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[
    dict[str, Any],
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
        or value["numeric_contracts"] != NUMERIC_CONTRACTS
        or not isinstance(value["source_operation_ids"], list)
        or len(value["source_operation_ids"]) != 8
        or len(set(value["source_operation_ids"])) != 8
    ):
        raise ProductionQKVSimulationError("physical-plan identities differ")
    problem = _problem(value["problem"], capability)
    value["problem"] = problem
    records = _regions(value["sram"], capability)
    image, hbm_regions = _hbm(value["hbm"], root, capability, problem)
    program = value["program"]
    if not isinstance(program, dict):
        raise ProductionQKVSimulationError("program record is malformed")
    exact_keys(
        program,
        {"command_count", "path", "sha256", "size_bytes"},
        set(),
        "program",
    )
    program_path = _safe_relative(program["path"], "program path")
    try:
        payload = (root / program_path).read_bytes()
    except OSError as exc:
        raise ProductionQKVSimulationError(
            f"cannot read command program: {exc}"
        ) from exc
    if (
        program_path != "program/commands.bin"
        or program["size_bytes"] != len(payload)
        or program["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise ProductionQKVSimulationError("program identity differs")
    try:
        commands = decode(payload)
        observed_abi = command_abi(payload)
    except ProductionCommandError as exc:
        raise ProductionQKVSimulationError(f"command decode failed: {exc}") from exc
    if observed_abi != (capability.command_abi_major, capability.command_abi_minor):
        raise ProductionQKVSimulationError("program and capability ABI differ")
    if program["command_count"] != len(commands):
        raise ProductionQKVSimulationError("program command count differs")
    counters = value["expected_counters"]
    if not isinstance(counters, dict) or tuple(sorted(counters)) != tuple(
        sorted(COUNTER_NAMES)
    ):
        raise ProductionQKVSimulationError("counter expectation names differ")
    try:
        for name in COUNTER_NAMES:
            require_int(counters[name], f"counter {name}", minimum=0)
    except ArtifactError as exc:
        raise ProductionQKVSimulationError(str(exc)) from exc
    return value, records, image, hbm_regions, commands


def _expectations(
    root: Path, manifest: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    value = _load_canonical(
        root / "execution_expectations.json", "execution expectations"
    )
    exact_keys(
        value,
        {
            "check_id",
            "counters",
            "expectations_id",
            "intermediate_payload_sha256",
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
        or set(value["intermediate_payload_sha256"])
        != {"attention_norm", "k_norm", "k_raw", "q_norm", "q_raw"}
        or set(value["output_payload_sha256"]) != {"k_rotary", "q_rotary", "v"}
    ):
        raise ProductionQKVSimulationError("execution expectations differ")
    try:
        for category in (
            value["intermediate_payload_sha256"],
            value["output_payload_sha256"],
        ):
            for role, digest in category.items():
                require_sha256(digest, f"expected {role} hash")
    except (AttributeError, ArtifactError) as exc:
        raise ProductionQKVSimulationError(
            f"execution expectation hash differs: {exc}"
        ) from exc
    return value


def _request(path: Path, plan: Mapping[str, Any]) -> tuple[dict[str, Any], int, int]:
    value = _load_canonical(path, "execution request")
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
    if (
        value["schema"] != REQUEST_SCHEMA
        or value["graph_id"] != plan["graph_id"]
        or value["source_operation_ids"] != plan["source_operation_ids"]
        or not isinstance(value["token"], dict)
        or set(value["token"]) != {"dtype", "token_id"}
        or value["token"]["dtype"] != "u32"
        or not isinstance(value["position"], dict)
        or set(value["position"]) != {"dtype", "position_id"}
        or value["position"]["dtype"] != "u32"
    ):
        raise ProductionQKVSimulationError("execution request identity differs")
    try:
        token_id = require_int(
            value["token"]["token_id"], "token_id", minimum=0, maximum=0xFFFFFFFF
        )
        position_id = require_int(
            value["position"]["position_id"],
            "position_id",
            minimum=0,
            maximum=0xFFFFFFFF,
        )
    except ArtifactError as exc:
        raise ProductionQKVSimulationError(str(exc)) from exc
    return value, token_id, position_id


def _region_for(
    regions: Mapping[str, _SRAMRegion], address: int, size: int
) -> _SRAMRegion:
    matches = [region for region in regions.values() if region.contains(address, size)]
    if len(matches) != 1:
        raise ProductionQKVSimulationError(
            "SRAM address resolves to zero or multiple regions"
        )
    return matches[0]


class ProductionQKVSimulator:
    """Immutable deployment whose ABI commands causally produce Q, K, and V."""

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
    def load(cls, root: Path) -> ProductionQKVSimulator:
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionQKVSimulationError(
                f"deployment directory does not exist: {deployment}"
            )
        manifest = _manifest(deployment)
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionQKVSimulationError(
                f"capability load failed: {exc}"
            ) from exc
        if capability.capability_id != manifest["capability_id"] or (
            capability.command_abi_major,
            capability.command_abi_minor,
        ) != (ABI_MAJOR, ABI_MINOR):
            raise ProductionQKVSimulationError(
                "manifest capability identity or ABI differs"
            )
        plan, records, image, hbm_regions, commands = _plan(
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
        request, token_id, position_id = _request(request_file, self._plan)
        regions = {
            region_id: _SRAMRegion.create(record)
            for region_id, record in self._region_records.items()
        }
        runtime_payload = struct.pack("<II", token_id, position_id)
        regions["runtime_ids"].write(regions["runtime_ids"].address, runtime_payload)
        counters = {name: 0 for name in COUNTER_NAMES}
        counters["runtime_request_sram_bytes_written"] = len(runtime_payload)
        trace: list[dict[str, Any]] = []
        loaded_static: set[str] = set()
        fresh_weight_tile = False
        fresh_weight_kernel: int | None = None
        active_projection: tuple[str, int] | None = None
        next_k = 0
        completed_tiles = {role: set() for role in ("q", "k", "v")}
        projection_saturations = {role: 0 for role in ("q", "k", "v")}
        rmsnorm_diagnostics: dict[str, dict[str, Any]] = {}
        rope_diagnostics: dict[str, Any] | None = None
        norm_done: set[str] = set()
        rope_done = False
        complete = False
        problem = self._plan["problem"]
        projection_by_kernel = {
            index: item for index, item in enumerate(problem["projections"], start=2)
        }
        hbm_base = self._capability.hbm.base_address
        output_region = {"q": "q_raw", "k": "k_raw", "v": "v"}

        for command in self._commands:
            counters["command_count"] += 1
            if command.opcode in {
                Opcode.DMA_HBM_TO_SRAM,
                Opcode.DMA_HBM_INDEXED_TO_SRAM,
            }:
                if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                    source = command.source0
                    counters["direct_dma_command_count"] += 1
                    logical_index: int | None = None
                else:
                    index_region = _region_for(regions, command.source1, command.size3)
                    index_payload = index_region.read(command.source1, command.size3)
                    logical_index = struct.unpack("<I", index_payload)[0]
                    relative_index = logical_index - command.auxiliary
                    if (
                        not 0 <= relative_index < command.size2
                        or command.size1 < command.size0
                    ):
                        raise ProductionQKVSimulationError(
                            "indexed DMA index or stride is illegal"
                        )
                    source = command.source0 + relative_index * command.size1
                    counters["indexed_dma_command_count"] += 1
                if (
                    source < hbm_base
                    or source % self._capability.hbm.burst_bytes
                    or command.size0 % self._capability.hbm.burst_bytes
                ):
                    raise ProductionQKVSimulationError("DMA alignment is illegal")
                offset = source - hbm_base
                end = offset + command.size0
                if end > len(self._image):
                    raise ProductionQKVSimulationError("DMA escapes HBM image")
                payload = self._image[offset:end]
                destination = _region_for(regions, command.destination, len(payload))
                if destination.region_id == "weight_tile":
                    if fresh_weight_tile:
                        raise ProductionQKVSimulationError(
                            "DMA overwrote an unconsumed weight tile"
                        )
                    fresh_weight_tile = True
                    fresh_weight_kernel = command.kernel_index
                elif destination.region_id in loaded_static:
                    raise ProductionQKVSimulationError(
                        f"DMA rewrites static SRAM region {destination.region_id!r}"
                    )
                else:
                    loaded_static.add(destination.region_id)
                destination.write(command.destination, payload)
                counters["dma_command_count"] += 1
                counters["hbm_useful_bytes_read"] += len(payload)
                counters["hbm_transferred_bytes_read"] += align_up(
                    len(payload), self._capability.hbm.burst_bytes
                )
                counters["dma_sram_bytes_written"] += len(payload)
                record: dict[str, Any] = {
                    "command_index": command.index,
                    "destination": command.destination,
                    "opcode": command.opcode.name,
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "source": source,
                }
                if logical_index is not None:
                    record["logical_index"] = logical_index
                trace.append(record)
                continue

            if command.opcode == Opcode.MATMUL_BF16_TILE:
                projection = projection_by_kernel.get(command.kernel_index)
                if projection is None:
                    raise ProductionQKVSimulationError(
                        "MATMUL kernel index does not name a projection"
                    )
                role = projection["role"]
                if not fresh_weight_tile or fresh_weight_kernel != command.kernel_index:
                    raise ProductionQKVSimulationError(
                        "MATMUL lacks a matching fresh causally preceding DMA"
                    )
                fresh_weight_tile = False
                fresh_weight_kernel = None
                input_base = regions["attention_norm"].address
                output_base = regions[output_region[role]].address
                if (
                    command.size0 != 1
                    or command.size1 != projection["n_tile"]
                    or command.size2 != projection["k_tile"]
                    or command.source1 != regions["weight_tile"].address
                    or command.destination != regions["accumulator_tile"].address
                    or (command.source0 - input_base) % 2
                    or (command.auxiliary - output_base) % 2
                ):
                    raise ProductionQKVSimulationError(
                        "MATMUL shape or SRAM address is illegal"
                    )
                k_start = (command.source0 - input_base) // 2
                n_start = (command.auxiliary - output_base) // 2
                if (
                    k_start < 0
                    or k_start + command.size2 > projection["k"]
                    or n_start < 0
                    or n_start + command.size1 > projection["n"]
                    or k_start % projection["k_tile"]
                    or n_start % projection["n_tile"]
                ):
                    raise ProductionQKVSimulationError(
                        "MATMUL logical tile coordinate is illegal"
                    )
                is_init = bool(command.flags & MATMUL_INIT)
                is_final = bool(command.flags & MATMUL_FINAL)
                if is_init:
                    if (
                        active_projection is not None
                        or k_start != 0
                        or n_start in completed_tiles[role]
                    ):
                        raise ProductionQKVSimulationError(
                            "MATMUL INIT ordering is illegal"
                        )
                    active_projection = (role, n_start)
                    next_k = 0
                    accumulator = None
                else:
                    if active_projection != (role, n_start):
                        raise ProductionQKVSimulationError(
                            "MATMUL accumulation has no active output tile"
                        )
                    accumulator_payload = regions["accumulator_tile"].read(
                        regions["accumulator_tile"].address,
                        command.size0 * command.size1 * 4,
                    )
                    accumulator = np.frombuffer(
                        accumulator_payload, dtype="<u4"
                    ).reshape(command.size0, command.size1)
                    counters["accumulator_sram_bytes_read"] += len(accumulator_payload)
                if k_start != next_k:
                    raise ProductionQKVSimulationError(
                        "MATMUL K segments are not strictly increasing"
                    )
                input_bytes = regions["attention_norm"].read(
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
                    raise ProductionQKVSimulationError(
                        f"MATMUL numeric execution failed: {exc}"
                    ) from exc
                accumulator_bytes = accumulated.values.astype(
                    "<u4", copy=False
                ).tobytes(order="C")
                regions["accumulator_tile"].write(
                    regions["accumulator_tile"].address, accumulator_bytes
                )
                counters["matmul_command_count"] += 1
                counters["matmul_input_sram_bytes_read"] += len(input_bytes)
                counters["matmul_weight_sram_bytes_read"] += len(weight_bytes)
                counters["accumulator_sram_bytes_written"] += len(accumulator_bytes)
                operations = command.size0 * command.size1 * command.size2
                counters["scalar_multiplications"] += operations
                counters["scalar_accumulation_additions"] += operations
                next_k += command.size2
                trace_record: dict[str, Any] = {
                    "accumulator_sha256": hashlib.sha256(accumulator_bytes).hexdigest(),
                    "command_index": command.index,
                    "flags": command.flags,
                    "k_start": k_start,
                    "n_start": n_start,
                    "opcode": command.opcode.name,
                    "projection_role": role,
                }
                if is_final:
                    if next_k != projection["k"] or active_projection != (
                        role,
                        n_start,
                    ):
                        raise ProductionQKVSimulationError(
                            "MATMUL FINAL ordering is illegal"
                        )
                    try:
                        finalized = finalize_bf16_accumulator(accumulated.values)
                    except BF16KernelError as exc:
                        raise ProductionQKVSimulationError(
                            f"MATMUL finalization failed: {exc}"
                        ) from exc
                    output_payload = finalized.values.astype("<u2", copy=False).tobytes(
                        order="C"
                    )
                    regions[output_region[role]].write(
                        command.auxiliary, output_payload
                    )
                    counters["matmul_output_sram_bytes_written"] += len(output_payload)
                    projection_saturations[role] += (
                        finalized.output_saturated_element_count
                    )
                    trace_record["output_sha256"] = hashlib.sha256(
                        output_payload
                    ).hexdigest()
                    completed_tiles[role].add(n_start)
                    active_projection = None
                    next_k = 0
                elif next_k == projection["k"]:
                    raise ProductionQKVSimulationError(
                        "last MATMUL K segment lacks FINAL"
                    )
                trace.append(trace_record)
                continue

            if command.opcode == Opcode.RMSNORM_BF16:
                norm_specs = {
                    1: (
                        "attention_norm",
                        "embedding",
                        "input_norm_weight",
                        1,
                        problem["hidden_width"],
                    ),
                    5: (
                        "q_norm",
                        "q_raw",
                        "q_norm_weight",
                        problem["query_heads"],
                        problem["head_dim"],
                    ),
                    6: (
                        "k_norm",
                        "k_raw",
                        "k_norm_weight",
                        problem["key_value_heads"],
                        problem["head_dim"],
                    ),
                }
                spec = norm_specs.get(command.kernel_index)
                if spec is None:
                    raise ProductionQKVSimulationError(
                        "RMSNorm kernel index does not name a qualified norm"
                    )
                role, input_role, weight_role, rows, width = spec
                if role in norm_done:
                    raise ProductionQKVSimulationError(
                        "RMSNorm output is written twice"
                    )
                if (
                    command.source0 != regions[input_role].address
                    or command.source1 != regions[weight_role].address
                    or command.destination != regions[role].address
                    or command.size0 != rows
                    or command.size1 != width
                ):
                    raise ProductionQKVSimulationError(
                        "RMSNorm shape or SRAM address is illegal"
                    )
                element_count = rows * width
                input_bytes = regions[input_role].read(
                    command.source0, element_count * 2
                )
                weight_bytes = regions[weight_role].read(command.source1, width * 2)
                inputs = np.frombuffer(input_bytes, dtype="<u2").reshape(rows, width)
                weights = np.frombuffer(weight_bytes, dtype="<u2")
                try:
                    result = rms_norm_bf16(inputs, weights, epsilon_code=command.size2)
                except RMSNormKernelError as exc:
                    raise ProductionQKVSimulationError(
                        f"RMSNorm numeric execution failed: {exc}"
                    ) from exc
                output_payload = result.values.astype("<u2", copy=False).tobytes(
                    order="C"
                )
                normalized_payload = result.normalized_values.astype(
                    "<u2", copy=False
                ).tobytes(order="C")
                mean_payload = result.mean_square_codes.astype(
                    "<u4", copy=False
                ).tobytes(order="C")
                inverse_payload = result.inverse_rms_codes.astype(
                    "<u4", copy=False
                ).tobytes(order="C")
                regions[role].write(command.destination, output_payload)
                norm_done.add(role)
                rmsnorm_diagnostics[role] = {
                    "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                        inverse_payload
                    ).hexdigest(),
                    "mean_square_binary32_codes_sha256": hashlib.sha256(
                        mean_payload
                    ).hexdigest(),
                    "normalized_payload_sha256": hashlib.sha256(
                        normalized_payload
                    ).hexdigest(),
                    "normalized_saturated_element_count": (
                        result.normalized_saturated_element_count
                    ),
                    "output_saturated_element_count": (
                        result.output_saturated_element_count
                    ),
                }
                counters["rmsnorm_command_count"] += 1
                counters["input_square_multiplications"] += element_count
                counters["reduction_additions"] += rows * (width - 1)
                counters["mean_divisions"] += rows
                counters["epsilon_additions"] += rows
                counters["reciprocal_square_roots"] += rows
                counters["normalization_multiplications"] += element_count
                counters["final_weight_multiplications"] += element_count
                counters["rmsnorm_input_sram_bytes_read"] += len(input_bytes)
                counters["rmsnorm_weight_sram_bytes_read"] += len(weight_bytes)
                counters["rmsnorm_output_sram_bytes_written"] += len(output_payload)
                trace.append(
                    {
                        "command_index": command.index,
                        "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                            inverse_payload
                        ).hexdigest(),
                        "mean_square_binary32_codes_sha256": hashlib.sha256(
                            mean_payload
                        ).hexdigest(),
                        "normalized_payload_sha256": hashlib.sha256(
                            normalized_payload
                        ).hexdigest(),
                        "opcode": command.opcode.name,
                        "output_payload_sha256": hashlib.sha256(
                            output_payload
                        ).hexdigest(),
                        "role": role,
                    }
                )
                continue

            if command.opcode == Opcode.ROPE_BF16:
                if rope_done or not {"q_norm", "k_norm"} <= norm_done:
                    raise ProductionQKVSimulationError(
                        "RoPE observes duplicate or missing normalized inputs"
                    )
                if (
                    command.source0 != regions["q_norm"].address
                    or command.source1 != regions["k_norm"].address
                    or command.destination != regions["q_rotary"].address
                    or command.auxiliary != regions["k_rotary"].address
                    or command.size0 != problem["query_heads"]
                    or command.size1 != problem["key_value_heads"]
                    or command.size2 != problem["head_dim"]
                    or command.size3 != regions["rope_coefficients"].address
                ):
                    raise ProductionQKVSimulationError(
                        "RoPE shape or SRAM address is illegal"
                    )
                q_bytes = command.size0 * command.size2 * 2
                k_bytes = command.size1 * command.size2 * 2
                coefficient_bytes = command.size2 * 4
                query_payload = regions["q_norm"].read(command.source0, q_bytes)
                key_payload = regions["k_norm"].read(command.source1, k_bytes)
                coefficient_payload = regions["rope_coefficients"].read(
                    command.size3, coefficient_bytes
                )
                query = np.frombuffer(query_payload, dtype="<u2").reshape(
                    command.size0, command.size2
                )
                key = np.frombuffer(key_payload, dtype="<u2").reshape(
                    command.size1, command.size2
                )
                coefficients = np.frombuffer(coefficient_payload, dtype="<u2")
                try:
                    result = rope_bf16(query, key, coefficients)
                except RoPEKernelError as exc:
                    raise ProductionQKVSimulationError(
                        f"RoPE numeric execution failed: {exc}"
                    ) from exc
                query_output = result.query_values.astype("<u2", copy=False).tobytes(
                    order="C"
                )
                key_output = result.key_values.astype("<u2", copy=False).tobytes(
                    order="C"
                )
                regions["q_rotary"].write(command.destination, query_output)
                regions["k_rotary"].write(command.auxiliary, key_output)
                rope_done = True
                rope_diagnostics = {
                    "addition_saturated_element_count": (
                        result.addition_saturated_element_count
                    ),
                    "coefficient_row_payload_sha256": hashlib.sha256(
                        coefficient_payload
                    ).hexdigest(),
                    "multiplication_saturated_element_count": (
                        result.multiplication_saturated_element_count
                    ),
                }
                rope_elements = (command.size0 + command.size1) * command.size2
                counters["rope_command_count"] += 1
                counters["rope_multiplications"] += 2 * rope_elements
                counters["rope_additions"] += rope_elements
                counters["rope_input_sram_bytes_read"] += (
                    len(query_payload) + len(key_payload) + len(coefficient_payload)
                )
                counters["rope_output_sram_bytes_written"] += len(query_output) + len(
                    key_output
                )
                trace.append(
                    {
                        "command_index": command.index,
                        "coefficient_row_payload_sha256": hashlib.sha256(
                            coefficient_payload
                        ).hexdigest(),
                        "key_output_payload_sha256": hashlib.sha256(
                            key_output
                        ).hexdigest(),
                        "opcode": command.opcode.name,
                        "query_output_payload_sha256": hashlib.sha256(
                            query_output
                        ).hexdigest(),
                    }
                )
                continue

            if command.opcode == Opcode.COMPLETE:
                expected_tiles = {
                    item["role"]: set(range(0, item["n"], item["n_tile"]))
                    for item in problem["projections"]
                }
                if (
                    complete
                    or fresh_weight_tile
                    or active_projection is not None
                    or completed_tiles != expected_tiles
                    or norm_done != {"attention_norm", "q_norm", "k_norm"}
                    or not rope_done
                ):
                    raise ProductionQKVSimulationError(
                        "COMPLETE observes unfinished or duplicate Q/K/V work"
                    )
                complete = True
                counters["complete_command_count"] += 1
                trace.append(
                    {"command_index": command.index, "opcode": command.opcode.name}
                )
                continue
            raise ProductionQKVSimulationError(
                f"unsupported production opcode {command.opcode!r}"
            )

        if not complete or counters != self._plan["expected_counters"]:
            raise ProductionQKVSimulationError(
                "completion or observed counters differ from expectations"
            )
        intermediate_regions = {
            "attention_norm": "attention_norm",
            "k_norm": "k_norm",
            "k_raw": "k_raw",
            "q_norm": "q_norm",
            "q_raw": "q_raw",
        }
        output_regions = {
            "k_rotary": "k_rotary",
            "q_rotary": "q_rotary",
            "v": "v",
        }

        def region_payload(region_id: str) -> bytes:
            region = regions[region_id]
            return region.read(region.address, region.logical_bytes)

        intermediate_payloads = {
            role: region_payload(region_id)
            for role, region_id in intermediate_regions.items()
        }
        output_payloads = {
            role: region_payload(region_id)
            for role, region_id in output_regions.items()
        }
        observed_intermediates = {
            role: hashlib.sha256(payload).hexdigest()
            for role, payload in intermediate_payloads.items()
        }
        observed_outputs = {
            role: hashlib.sha256(payload).hexdigest()
            for role, payload in output_payloads.items()
        }
        if (
            observed_intermediates != self._expectations["intermediate_payload_sha256"]
            or observed_outputs != self._expectations["output_payload_sha256"]
        ):
            raise ProductionQKVSimulationError(
                "causal Q/K/V values differ from independent expectations"
            )
        if rope_diagnostics is None:
            raise ProductionQKVSimulationError("RoPE diagnostics are missing")
        shapes = {
            role: self._region_records[region_id]["shape"]
            for role, region_id in {**intermediate_regions, **output_regions}.items()
        }
        output_records = {}
        for role, payload in output_payloads.items():
            output_records[role] = {
                "codes": [int(value) for value in np.frombuffer(payload, dtype="<u2")],
                "dtype": "bf16",
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "shape": shapes[role],
                "size_bytes": len(payload),
            }
        intermediate_records = {
            role: {
                "dtype": "bf16",
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "shape": shapes[role],
                "size_bytes": len(payload),
            }
            for role, payload in intermediate_payloads.items()
        }
        body = {
            "build_id": self._manifest["build_id"],
            "capability_id": self._capability.capability_id,
            "counter_reconciliation": "exact",
            "counters": counters,
            "intermediates": intermediate_records,
            "mode": "artifact_only_data_bearing_functional",
            "outputs": output_records,
            "physical_plan_id": self._plan["physical_plan_id"],
            "projection_saturated_element_count": projection_saturations,
            "request_id": request["request_id"],
            "rmsnorm": rmsnorm_diagnostics,
            "rope": rope_diagnostics,
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


def publish_qkv_execution_report(report: Mapping[str, Any], output_path: Path) -> None:
    """Atomically retain one authenticated Q/K/V report without overwrite."""

    if not isinstance(report, Mapping):
        raise ProductionQKVSimulationError("execution report must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionQKVSimulationError("execution report identity differs")
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
            raise ProductionQKVSimulationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "ProductionQKVSimulationError",
    "ProductionQKVSimulator",
    "publish_qkv_execution_report",
]
