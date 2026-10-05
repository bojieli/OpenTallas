"""Causal artifact-only simulator for a Qwen layer downstream deployment.

Only emitted deployment artifacts and the optimized target kernels are loaded.
There is no checkpoint, framework, qualification-time computation, compiler, or
scalar-oracle fallback.  Every reported output byte is produced by decoded ABI
commands operating on initialized HBM/SRAM state.
"""

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
    sha256_file,
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
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi,
    decode,
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


MANIFEST_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_deployment.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_request.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_expectations.v1"
CHECK_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_independent_check.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_source_lock.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.layer_downstream_execution.v1"

HBM_IMAGE_PATH = "memory/hbm_layer_downstream.bin"
COMMAND_PATH = "program/commands.bin"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
REQUEST_PATH = "request/execution_request.json"

HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
ROWS = 1
N_TILE = 64
K_TILE = 256
EPSILON_CODE = 0x358637BD

NUMERIC_CONTRACTS = [
    "bf16_add_rne_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "qwen3_rmsnorm_fp32_bf16_v1",
    "qwen3_silu_mul_bf16_v1",
]
EXPECTED_CLAIM_BOUNDARY = [
    "authenticated Qwen3-8B layer-0 attention output and hidden residual through the complete post-attention and MLP path",
    "output projection, two BF16 residual adds, post-attention RMSNorm, gate/up/down projections, and materialized-BF16 SiLU multiply",
    "neutral kernels, explicit 13-bank SRAM placement, tiled HBM weights, independently checked ABI 2.4 commands, and artifact-only functional execution",
    "uncharacterized downstream-slice evidence only; not a connected complete layer, model decode, timing, RTL, 130-nm, performance, or energy claim",
]
EXPECTED_ROLES = {
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

COUNTER_NAMES = (
    "accumulator_sram_bytes_read",
    "accumulator_sram_bytes_written",
    "add_command_count",
    "add_input_sram_bytes_read",
    "add_output_sram_bytes_written",
    "command_count",
    "complete_command_count",
    "dma_command_count",
    "dma_sram_bytes_written",
    "epsilon_additions",
    "final_weight_multiplications",
    "hbm_transferred_bytes_read",
    "hbm_useful_bytes_read",
    "input_square_multiplications",
    "matrix_input_sram_bytes_read",
    "matrix_output_sram_bytes_written",
    "matmul_command_count",
    "mean_divisions",
    "normalization_multiplications",
    "projection_accumulation_additions",
    "projection_multiplications",
    "reciprocal_square_roots",
    "reduction_additions",
    "residual_additions",
    "rmsnorm_command_count",
    "rmsnorm_input_sram_bytes_read",
    "rmsnorm_output_sram_bytes_written",
    "rmsnorm_weight_sram_bytes_read",
    "sigmoid_denominator_additions",
    "sigmoid_divisions",
    "sigmoid_exponentials",
    "silu_command_count",
    "silu_input_sram_bytes_read",
    "silu_multiplications",
    "silu_output_sram_bytes_written",
    "up_gate_multiplications",
    "weight_sram_bytes_read",
)

INTERMEDIATE_ROLES = (
    "attention_projected",
    "down",
    "gate",
    "gated_mlp",
    "mlp_norm",
    "post_attention",
    "silu_activation",
    "up",
)

PROJECTION_SPECS = (
    {
        "id": "attention_output",
        "input_region": "attention",
        "kernel_index": 0,
        "output_region": "attention_projected",
        "source_role": "attention_output_weight",
        "n": HIDDEN_WIDTH,
        "k": HIDDEN_WIDTH,
    },
    {
        "id": "gate",
        "input_region": "mlp_norm",
        "kernel_index": 3,
        "output_region": "gate",
        "source_role": "gate_projection_weight",
        "n": INTERMEDIATE_WIDTH,
        "k": HIDDEN_WIDTH,
    },
    {
        "id": "up",
        "input_region": "mlp_norm",
        "kernel_index": 4,
        "output_region": "up",
        "source_role": "up_projection_weight",
        "n": INTERMEDIATE_WIDTH,
        "k": HIDDEN_WIDTH,
    },
    {
        "id": "down",
        "input_region": "gated_mlp",
        "kernel_index": 6,
        "output_region": "down",
        "source_role": "down_projection_weight",
        "n": HIDDEN_WIDTH,
        "k": INTERMEDIATE_WIDTH,
    },
)


class ProductionLayerDownstreamSimulationError(RuntimeError):
    """Raised when deployment loading or causal execution fails."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionLayerDownstreamSimulationError(
            f"cannot load {label}: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise ProductionLayerDownstreamSimulationError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductionLayerDownstreamSimulationError(
            f"{label} must be a safe relative path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionLayerDownstreamSimulationError(
            f"{label} must be a safe relative path"
        )
    return path.as_posix()


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    try:
        observed = require_sha256(value.get(field), f"{label}.{field}")
    except ArtifactError as exc:
        raise ProductionLayerDownstreamSimulationError(str(exc)) from exc
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionLayerDownstreamSimulationError(f"{label} identity differs")


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
        raise ProductionLayerDownstreamSimulationError(str(exc)) from exc


def _required_sha(value: object, label: str) -> str:
    try:
        return require_sha256(value, label)
    except ArtifactError as exc:
        raise ProductionLayerDownstreamSimulationError(str(exc)) from exc


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
            raise ProductionLayerDownstreamSimulationError(
                f"write escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + len(payload)
        self.data[start:end] = payload
        self.initialized[start:end] = b"\x01" * len(payload)

    def read(self, address: int, size: int) -> bytes:
        if not self.contains(address, size):
            raise ProductionLayerDownstreamSimulationError(
                f"read escapes SRAM region {self.region_id!r}"
            )
        start = address - self.address
        end = start + size
        if not all(self.initialized[start:end]):
            raise ProductionLayerDownstreamSimulationError(
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
    if (
        value["schema"] != MANIFEST_SCHEMA
        or value["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY
        or value["command_abi"] != {"major": ABI_MAJOR, "minor": ELEMENTWISE_ABI_MINOR}
        or value["compiler"]
        != {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator layer-downstream compiler",
            "version": "tensor-accelerator-production-layer-downstream-0.1.0",
        }
        or value["entrypoint"]
        != {
            "capability": "capability.json",
            "command_program": COMMAND_PATH,
            "hbm_image": HBM_IMAGE_PATH,
            "physical_plan": PHYSICAL_PLAN_PATH,
            "request": REQUEST_PATH,
        }
    ):
        raise ProductionLayerDownstreamSimulationError(
            "deployment manifest contract differs"
        )
    for field in (
        "build_id",
        "capability_id",
        "graph_id",
        "independent_check_id",
        "kernel_ir_id",
        "physical_plan_id",
        "qualification_report_id",
        "source_lock_id",
    ):
        _required_sha(value[field], f"manifest.{field}")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(EXPECTED_ROLES):
        raise ProductionLayerDownstreamSimulationError(
            "manifest artifact coverage differs"
        )
    paths: list[str] = []
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise ProductionLayerDownstreamSimulationError(
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
            raise ProductionLayerDownstreamSimulationError(
                f"artifact role differs for {path!r}"
            )
        try:
            digest, size = sha256_file(root / path)
        except OSError as exc:
            raise ProductionLayerDownstreamSimulationError(
                f"cannot authenticate artifact {path!r}: {exc}"
            ) from exc
        if record["sha256"] != digest or record["size_bytes"] != size:
            raise ProductionLayerDownstreamSimulationError(
                f"artifact identity differs for {path!r}"
            )
        paths.append(path)
    if paths != sorted(EXPECTED_ROLES):
        raise ProductionLayerDownstreamSimulationError(
            "manifest artifact order or paths differ"
        )
    return value


def _source_lock(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    value = _load_canonical(root / "source.lock.json", "source lock")
    exact_keys(
        value,
        {
            "attention_execution_report_id",
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
    if (
        value["schema"] != SOURCE_LOCK_SCHEMA
        or value["source_lock_id"] != manifest["source_lock_id"]
        or value["capability_id"] != manifest["capability_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
        or value["compiler_version"]
        != "tensor-accelerator-production-layer-downstream-0.1.0"
    ):
        raise ProductionLayerDownstreamSimulationError("source-lock identities differ")
    sources = value["sources"]
    if not isinstance(sources, list) or [
        item.get("role") if isinstance(item, Mapping) else None for item in sources
    ] != [
        "model_graph",
        "checkpoint_lock",
        "hardware_capability",
        "qualification_report",
        "attention_execution",
    ]:
        raise ProductionLayerDownstreamSimulationError("source-lock coverage differs")
    for index, record in enumerate(sources):
        if not isinstance(record, dict):
            raise ProductionLayerDownstreamSimulationError(
                f"source-lock record {index} is malformed"
            )
        exact_keys(
            record,
            {"role", "sha256", "size_bytes"},
            set(),
            f"source-lock record {index}",
        )
        _required_sha(record["sha256"], f"source-lock record {index}.sha256")
        _required_int(
            record["size_bytes"],
            f"source-lock record {index}.size_bytes",
            minimum=1,
        )
    return value


def _problem(raw: object, capability: ProductionCapability) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProductionLayerDownstreamSimulationError(
            "physical problem must be an object"
        )
    exact_keys(
        raw,
        {"hidden_width", "intermediate_width", "projections", "rows"},
        set(),
        "physical problem",
    )
    if (
        raw["hidden_width"] != HIDDEN_WIDTH
        or raw["intermediate_width"] != INTERMEDIATE_WIDTH
        or raw["rows"] != ROWS
        or capability.vector_engine is None
        or capability.vector_engine.max_width < INTERMEDIATE_WIDTH
        or capability.vector_engine.max_rows < ROWS
        or capability.tensor_engine.max_m < ROWS
        or capability.tensor_engine.max_n < N_TILE
        or capability.tensor_engine.max_k < K_TILE
    ):
        raise ProductionLayerDownstreamSimulationError(
            "physical problem exceeds the capability"
        )
    projections = raw["projections"]
    if not isinstance(projections, list) or len(projections) != 4:
        raise ProductionLayerDownstreamSimulationError(
            "projection problem coverage differs"
        )
    expected: list[dict[str, Any]] = []
    for spec in PROJECTION_SPECS:
        n = spec["n"]
        k = spec["k"]
        expected.append(
            {
                **spec,
                "k_tile": K_TILE,
                "k_tiles": k // K_TILE,
                "n_tile": N_TILE,
                "n_tiles": n // N_TILE,
                "tile_count": (n // N_TILE) * (k // K_TILE),
            }
        )
    if projections != expected:
        raise ProductionLayerDownstreamSimulationError(
            "projection problem definitions differ"
        )
    return dict(raw)


def _sram(
    raw: object,
    capability: ProductionCapability,
) -> tuple[dict[str, _SRAMRegion], dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise ProductionLayerDownstreamSimulationError("SRAM plan is malformed")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionLayerDownstreamSimulationError("SRAM addressing differs")
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
    expected = [
        {
            "address": capability.sram.bank_base(bank),
            "allocated_bytes": align_up(logical, capability.sram.word_bytes),
            "bank": bank,
            "dtype": dtype,
            "id": region_id,
            "logical_bytes": logical,
            "shape": shape,
        }
        for region_id, bank, dtype, shape, logical in specs
    ]
    if raw["regions"] != expected:
        raise ProductionLayerDownstreamSimulationError(
            "SRAM semantic placement differs"
        )
    intervals = sorted(
        (
            record["address"],
            record["address"] + record["allocated_bytes"],
        )
        for record in expected
    )
    if any(left[1] > right[0] for left, right in zip(intervals, intervals[1:])):
        raise ProductionLayerDownstreamSimulationError("SRAM regions overlap")
    records = {record["id"]: record for record in expected}
    return (
        {key: _SRAMRegion.create(record) for key, record in records.items()},
        records,
    )


def _hbm(
    raw: object,
    root: Path,
    capability: ProductionCapability,
    problem: Mapping[str, Any],
) -> tuple[
    bytes,
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    if not isinstance(raw, dict):
        raise ProductionLayerDownstreamSimulationError("HBM plan is malformed")
    exact_keys(raw, {"image", "projections", "regions"}, set(), "HBM plan")
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionLayerDownstreamSimulationError("HBM image record is malformed")
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
        raise ProductionLayerDownstreamSimulationError(
            f"cannot read HBM image: {exc}"
        ) from exc
    if (
        path != HBM_IMAGE_PATH
        or image_record["base_address"] != capability.hbm.base_address
        or image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) % capability.hbm.burst_bytes
        or len(image) > capability.hbm.capacity_bytes
    ):
        raise ProductionLayerDownstreamSimulationError("HBM image identity differs")
    intervals: list[tuple[int, int, str]] = []

    def cover(record: Mapping[str, Any], label: str) -> bytes:
        offset = _required_int(record.get("offset_bytes"), f"{label}.offset")
        size = _required_int(record.get("size_bytes"), f"{label}.size", minimum=1)
        address = _required_int(record.get("address"), f"{label}.address")
        digest = _required_sha(record.get("payload_sha256"), f"{label}.sha256")
        if (
            offset % capability.hbm.burst_bytes
            or address != capability.hbm.base_address + offset
            or offset + size > len(image)
        ):
            raise ProductionLayerDownstreamSimulationError(f"{label} range is illegal")
        payload = image[offset : offset + size]
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ProductionLayerDownstreamSimulationError(
                f"{label} payload identity differs"
            )
        intervals.append((offset, offset + size, label))
        return payload

    raw_regions = raw["regions"]
    if not isinstance(raw_regions, list) or len(raw_regions) != 3:
        raise ProductionLayerDownstreamSimulationError(
            "direct HBM region coverage differs"
        )
    expected_direct = (
        ("hidden_0", HIDDEN_WIDTH * 2, "checkpoint_row"),
        ("attention", HIDDEN_WIDTH * 2, "retained_execution_output"),
        ("post_attention_norm_weight", HIDDEN_WIDTH * 2, "checkpoint_tensor"),
    )
    direct: dict[str, dict[str, Any]] = {}
    for index, (record, expected) in enumerate(
        zip(raw_regions, expected_direct, strict=True)
    ):
        if not isinstance(record, dict):
            raise ProductionLayerDownstreamSimulationError(
                f"direct HBM region {index} is malformed"
            )
        exact_keys(
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
            f"direct HBM region {index}",
        )
        region_id, size, source_kind = expected
        source = record["source"]
        if (
            record["id"] != region_id
            or record["size_bytes"] != size
            or not isinstance(source, dict)
            or source.get("kind") != source_kind
        ):
            raise ProductionLayerDownstreamSimulationError(
                f"direct HBM region {region_id!r} differs"
            )
        if source_kind == "checkpoint_row":
            exact_keys(
                source,
                {"kind", "payload_sha256", "row", "tensor_name"},
                set(),
                "hidden source",
            )
            _required_sha(source["payload_sha256"], "hidden source hash")
            _required_int(source["row"], "hidden source row")
        elif source_kind == "retained_execution_output":
            exact_keys(
                source,
                {"build_id", "kind", "report_id"},
                set(),
                "attention source",
            )
            _required_sha(source["build_id"], "attention source build ID")
            _required_sha(source["report_id"], "attention source report ID")
        else:
            exact_keys(
                source,
                {"kind", "payload_sha256", "shape", "tensor_name"},
                set(),
                "normalization-weight source",
            )
            _required_sha(source["payload_sha256"], "normalization-weight source hash")
            if source["shape"] != [HIDDEN_WIDTH]:
                raise ProductionLayerDownstreamSimulationError(
                    "normalization-weight source shape differs"
                )
        if not isinstance(source.get("tensor_name", ""), str):
            raise ProductionLayerDownstreamSimulationError(
                f"direct HBM source name differs for {region_id!r}"
            )
        cover(record, f"direct HBM region {index}")
        direct[region_id] = dict(record)

    raw_projections = raw["projections"]
    if not isinstance(raw_projections, list) or len(raw_projections) != 4:
        raise ProductionLayerDownstreamSimulationError(
            "HBM projection coverage differs"
        )
    problem_by_id = {
        projection["id"]: projection for projection in problem["projections"]
    }
    projections: dict[str, dict[str, Any]] = {}
    for projection_index, (record, spec) in enumerate(
        zip(raw_projections, PROJECTION_SPECS, strict=True)
    ):
        if not isinstance(record, dict):
            raise ProductionLayerDownstreamSimulationError(
                f"HBM projection {projection_index} is malformed"
            )
        exact_keys(
            record,
            {
                "id",
                "input_region",
                "kernel_index",
                "output_region",
                "source",
                "tiles",
            },
            set(),
            f"HBM projection {projection_index}",
        )
        projection_id = spec["id"]
        if any(
            record[field] != spec[field]
            for field in (
                "id",
                "input_region",
                "kernel_index",
                "output_region",
            )
        ):
            raise ProductionLayerDownstreamSimulationError(
                f"HBM projection {projection_id!r} semantics differ"
            )
        source = record["source"]
        if not isinstance(source, dict):
            raise ProductionLayerDownstreamSimulationError(
                f"HBM projection {projection_id!r} source is malformed"
            )
        exact_keys(
            source,
            {"kind", "payload_sha256", "shape", "tensor_name"},
            set(),
            f"HBM projection {projection_id} source",
        )
        if (
            source["kind"] != "checkpoint_tensor"
            or source["shape"] != [spec["n"], spec["k"]]
            or not isinstance(source["tensor_name"], str)
            or not source["tensor_name"]
        ):
            raise ProductionLayerDownstreamSimulationError(
                f"HBM projection {projection_id!r} source differs"
            )
        _required_sha(
            source["payload_sha256"],
            f"HBM projection {projection_id} source hash",
        )
        definition = problem_by_id[projection_id]
        tiles = record["tiles"]
        if not isinstance(tiles, list) or len(tiles) != definition["tile_count"]:
            raise ProductionLayerDownstreamSimulationError(
                f"HBM projection {projection_id!r} tile count differs"
            )
        expected_index = 0
        for n_start in range(0, definition["n"], N_TILE):
            for k_start in range(0, definition["k"], K_TILE):
                tile = tiles[expected_index]
                if not isinstance(tile, dict):
                    raise ProductionLayerDownstreamSimulationError(
                        f"HBM projection {projection_id!r} tile is malformed"
                    )
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
                    f"HBM projection {projection_id} tile {expected_index}",
                )
                if (
                    tile["tile_index"] != expected_index
                    or tile["n_start"] != n_start
                    or tile["k_start"] != k_start
                    or tile["n_count"] != N_TILE
                    or tile["k_count"] != K_TILE
                    or tile["size_bytes"] != N_TILE * K_TILE * 2
                ):
                    raise ProductionLayerDownstreamSimulationError(
                        f"HBM projection {projection_id!r} tile order differs"
                    )
                cover(
                    tile,
                    f"HBM projection {projection_id} tile {expected_index}",
                )
                expected_index += 1
        projections[projection_id] = dict(record)

    intervals.sort()
    cursor = 0
    for start, end, label in intervals:
        if start < cursor:
            raise ProductionLayerDownstreamSimulationError(
                f"HBM range overlap reaches {label}"
            )
        if any(image[cursor:start]):
            raise ProductionLayerDownstreamSimulationError(
                "HBM uncovered padding is nonzero"
            )
        cursor = end
    if any(image[cursor:]):
        raise ProductionLayerDownstreamSimulationError(
            "HBM trailing padding is nonzero"
        )
    return image, direct, projections


def _records_by_id(
    records: list[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {record["id"]: record for record in records}


def _append_projection_commands(
    commands: list[ProductionCommand],
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


def _expected_commands(
    problem: Mapping[str, Any],
    sram_plan: Mapping[str, Any],
    direct: Mapping[str, Mapping[str, Any]],
    projections: Mapping[str, Mapping[str, Any]],
) -> tuple[ProductionCommand, ...]:
    sram = _records_by_id(sram_plan["regions"])
    definitions = {
        projection["id"]: projection for projection in problem["projections"]
    }
    commands: list[ProductionCommand] = []
    for role, kernel_index in (("hidden_0", 1), ("attention", 0)):
        commands.append(
            ProductionCommand(
                len(commands),
                Opcode.DMA_HBM_TO_SRAM,
                Engine.DMA,
                kernel_index=kernel_index,
                source0=direct[role]["address"],
                destination=sram[role]["address"],
                size0=direct[role]["size_bytes"],
            )
        )
    _append_projection_commands(
        commands,
        projections["attention_output"],
        definitions["attention_output"],
        sram,
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
        _append_projection_commands(
            commands,
            projections[role],
            definitions[role],
            sram,
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
    _append_projection_commands(
        commands,
        projections["down"],
        definitions["down"],
        sram,
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


def _plan(
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
    value = _load_canonical(root / PHYSICAL_PLAN_PATH, "physical plan")
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
    expected_operations = [f"node.{index:04d}" for index in range(10, 18)]
    if (
        value["schema"] != PHYSICAL_PLAN_SCHEMA
        or value["physical_plan_id"] != manifest["physical_plan_id"]
        or value["capability_id"] != capability.capability_id
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
        or value["numeric_contracts"] != NUMERIC_CONTRACTS
        or value["source_operation_ids"] != expected_operations
    ):
        raise ProductionLayerDownstreamSimulationError(
            "physical-plan identities differ"
        )
    problem = _problem(value["problem"], capability)
    _, sram_records = _sram(value["sram"], capability)
    image, direct, projections = _hbm(value["hbm"], root, capability, problem)
    program = value["program"]
    if not isinstance(program, dict):
        raise ProductionLayerDownstreamSimulationError("program record is malformed")
    exact_keys(
        program,
        {"command_count", "path", "sha256", "size_bytes"},
        set(),
        "program",
    )
    program_path = _safe_relative(program["path"], "program path")
    try:
        payload = (root / program_path).read_bytes()
        commands = decode(payload)
        observed_abi = command_abi(payload)
    except (OSError, ProductionCommandError) as exc:
        raise ProductionLayerDownstreamSimulationError(
            f"cannot decode command program: {exc}"
        ) from exc
    if (
        program_path != COMMAND_PATH
        or program["size_bytes"] != len(payload)
        or program["sha256"] != hashlib.sha256(payload).hexdigest()
        or program["command_count"] != len(commands)
        or observed_abi != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
        or observed_abi != (capability.command_abi_major, capability.command_abi_minor)
    ):
        raise ProductionLayerDownstreamSimulationError(
            "program identity or ABI differs"
        )
    expected_commands = _expected_commands(problem, value["sram"], direct, projections)
    if commands != expected_commands:
        raise ProductionLayerDownstreamSimulationError(
            "program differs from the artifact-derived legal schedule"
        )
    counters = value["expected_counters"]
    if not isinstance(counters, dict) or tuple(sorted(counters)) != tuple(
        sorted(COUNTER_NAMES)
    ):
        raise ProductionLayerDownstreamSimulationError(
            "counter expectation names differ"
        )
    for name in COUNTER_NAMES:
        _required_int(counters[name], f"expected counter {name}")
    if counters["command_count"] != len(commands):
        raise ProductionLayerDownstreamSimulationError(
            "counter and program command counts differ"
        )
    return (
        value,
        sram_records,
        image,
        direct,
        projections,
        commands,
    )


def _kernel_ir(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
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
    if (
        value["schema"] != KERNEL_SCHEMA
        or value["kernel_ir_id"] != manifest["kernel_ir_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
    ):
        raise ProductionLayerDownstreamSimulationError(
            "Tensor Kernel IR identities differ"
        )
    if (
        b"address" in canonical_json_bytes(value).lower()
        or b"sram" in canonical_json_bytes(value).lower()
    ):
        raise ProductionLayerDownstreamSimulationError(
            "Tensor Kernel IR contains physical placement"
        )
    kernels = value["kernels"]
    if not isinstance(kernels, list) or len(kernels) != 8:
        raise ProductionLayerDownstreamSimulationError(
            "Tensor Kernel IR coverage differs"
        )
    expected = (
        (
            "MATMUL",
            "bf16_bf16_fp32_sequential_rne_v1",
            {"reduction_width": HIDDEN_WIDTH, "rows": ROWS, "width": HIDDEN_WIDTH},
            {
                "accumulator_dtype": "fp32",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "reduction_order": "strictly_increasing_k",
                "transpose_weight": True,
            },
        ),
        (
            "ADD",
            "bf16_add_rne_v1",
            {"rows": ROWS, "width": HIDDEN_WIDTH},
            {
                "addition": "binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "zero_canonicalization": "positive",
            },
        ),
        (
            "RMS_NORM",
            "qwen3_rmsnorm_fp32_bf16_v1",
            {"rows": ROWS, "width": HIDDEN_WIDTH},
            {
                "epsilon_binary32_code": EPSILON_CODE,
                "final_weight_product": "bf16_multiply_then_bf16_rne",
                "normalized_boundary": "bf16_rne_before_weight",
                "reduction_order": "canonical_balanced_binary32_tree",
                "rsqrt": "correctly_rounded_binary32_rne",
            },
        ),
        (
            "MATMUL",
            "bf16_bf16_fp32_sequential_rne_v1",
            {
                "reduction_width": HIDDEN_WIDTH,
                "rows": ROWS,
                "width": INTERMEDIATE_WIDTH,
            },
            {
                "accumulator_dtype": "fp32",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "reduction_order": "strictly_increasing_k",
                "transpose_weight": True,
            },
        ),
        (
            "MATMUL",
            "bf16_bf16_fp32_sequential_rne_v1",
            {
                "reduction_width": HIDDEN_WIDTH,
                "rows": ROWS,
                "width": INTERMEDIATE_WIDTH,
            },
            {
                "accumulator_dtype": "fp32",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "reduction_order": "strictly_increasing_k",
                "transpose_weight": True,
            },
        ),
        (
            "SILU_MUL",
            "qwen3_silu_mul_bf16_v1",
            {"rows": ROWS, "width": INTERMEDIATE_WIDTH},
            {
                "activation_boundary": "bf16_rne_before_up_multiply",
                "exponential": "correctly_rounded_binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "sigmoid": "stable_sign_selected_binary32",
                "zero_canonicalization": "positive",
            },
        ),
        (
            "MATMUL",
            "bf16_bf16_fp32_sequential_rne_v1",
            {
                "reduction_width": INTERMEDIATE_WIDTH,
                "rows": ROWS,
                "width": HIDDEN_WIDTH,
            },
            {
                "accumulator_dtype": "fp32",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "reduction_order": "strictly_increasing_k",
                "transpose_weight": True,
            },
        ),
        (
            "ADD",
            "bf16_add_rne_v1",
            {"rows": ROWS, "width": HIDDEN_WIDTH},
            {
                "addition": "binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "zero_canonicalization": "positive",
            },
        ),
    )
    for index, (kernel, contract) in enumerate(zip(kernels, expected, strict=True)):
        if not isinstance(kernel, dict):
            raise ProductionLayerDownstreamSimulationError(
                f"Tensor Kernel IR record {index} is malformed"
            )
        exact_keys(
            kernel,
            {
                "attributes",
                "index",
                "inputs",
                "kind",
                "numeric_contract",
                "outputs",
                "shape",
                "source_operation_id",
            },
            set(),
            f"Tensor Kernel IR record {index}",
        )
        kind, numeric_contract, shape, attributes = contract
        if (
            kernel["index"] != index
            or kernel["kind"] != kind
            or kernel["numeric_contract"] != numeric_contract
            or kernel["shape"] != shape
            or kernel["attributes"] != attributes
            or kernel["source_operation_id"] != f"node.{index + 10:04d}"
            or not isinstance(kernel["inputs"], list)
            or not kernel["inputs"]
            or not isinstance(kernel["outputs"], list)
            or len(kernel["outputs"]) != 1
            or any(not isinstance(item, str) or not item for item in kernel["inputs"])
            or any(not isinstance(item, str) or not item for item in kernel["outputs"])
        ):
            raise ProductionLayerDownstreamSimulationError(
                f"Tensor Kernel IR record {index} differs"
            )
    return value


def _independent_check(
    root: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(root / "checks/independent_check.json", "independent check")
    exact_keys(
        value,
        {
            "capability_id",
            "check_id",
            "checks",
            "command_abi",
            "command_count",
            "expected_counters",
            "expected_intermediate_payload_sha256",
            "expected_output_payload_sha256",
            "expected_saturated_element_count",
            "graph_id",
            "hbm_image_sha256",
            "hbm_size_bytes",
            "kernel_ir_id",
            "physical_plan_id",
            "qualification_report_id",
            "schema",
            "source_lock_id",
            "status",
        },
        set(),
        "independent check",
    )
    _identity(value, "check_id", "independent check")
    if (
        value["schema"] != CHECK_SCHEMA
        or value["status"] != "pass"
        or value["check_id"] != manifest["independent_check_id"]
        or value["capability_id"] != manifest["capability_id"]
        or value["graph_id"] != manifest["graph_id"]
        or value["kernel_ir_id"] != kernel_ir["kernel_ir_id"]
        or value["physical_plan_id"] != plan["physical_plan_id"]
        or value["qualification_report_id"] != manifest["qualification_report_id"]
        or value["source_lock_id"] != manifest["source_lock_id"]
        or value["command_abi"] != {"major": ABI_MAJOR, "minor": ELEMENTWISE_ABI_MINOR}
        or value["command_count"] != plan["program"]["command_count"]
        or value["expected_counters"] != plan["expected_counters"]
        or value["hbm_image_sha256"] != plan["hbm"]["image"]["sha256"]
        or value["hbm_size_bytes"] != plan["hbm"]["image"]["size_bytes"]
    ):
        raise ProductionLayerDownstreamSimulationError(
            "independent-check identities differ"
        )
    if not isinstance(value["checks"], list) or len(value["checks"]) != 9:
        raise ProductionLayerDownstreamSimulationError(
            "independent-check coverage differs"
        )
    _validate_expectation_payloads(value)
    return value


def _validate_expectation_payloads(value: Mapping[str, Any]) -> None:
    intermediates = value.get("expected_intermediate_payload_sha256")
    outputs = value.get("expected_output_payload_sha256")
    saturation = value.get("expected_saturated_element_count")
    if (
        not isinstance(intermediates, dict)
        or tuple(intermediates) != INTERMEDIATE_ROLES
        or not isinstance(outputs, dict)
        or tuple(outputs) != ("hidden_1",)
        or not isinstance(saturation, dict)
        or set(saturation) != {"projection", "rmsnorm", "vector"}
        or set(saturation["projection"]) != {"attention_output", "down", "gate", "up"}
        or set(saturation["rmsnorm"]) != {"normalized", "output"}
        or set(saturation["vector"])
        != {
            "attention_residual",
            "final_residual",
            "silu_activation",
            "silu_output",
        }
    ):
        raise ProductionLayerDownstreamSimulationError(
            "output or saturation expectation coverage differs"
        )
    for role, digest in (*intermediates.items(), *outputs.items()):
        _required_sha(digest, f"expected {role} hash")
    for category in saturation.values():
        if not isinstance(category, dict):
            raise ProductionLayerDownstreamSimulationError(
                "saturation expectation category is malformed"
            )
        for role, count in category.items():
            _required_int(count, f"expected {role} saturation count")


def _expectations(
    root: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    check: Mapping[str, Any],
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
            "saturated_element_count",
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
        or value["intermediate_payload_sha256"]
        != check["expected_intermediate_payload_sha256"]
        or value["output_payload_sha256"] != check["expected_output_payload_sha256"]
        or value["saturated_element_count"] != check["expected_saturated_element_count"]
    ):
        raise ProductionLayerDownstreamSimulationError("execution expectations differ")
    _validate_expectation_payloads(
        {
            "expected_intermediate_payload_sha256": value[
                "intermediate_payload_sha256"
            ],
            "expected_output_payload_sha256": value["output_payload_sha256"],
            "expected_saturated_element_count": value["saturated_element_count"],
        }
    )
    return value


def _request(
    path: Path,
    plan: Mapping[str, Any],
    source_lock: Mapping[str, Any],
) -> dict[str, Any]:
    value = _load_canonical(path, "execution request")
    exact_keys(
        value,
        {
            "graph_id",
            "inputs",
            "request_id",
            "schema",
            "source_operation_ids",
        },
        set(),
        "execution request",
    )
    _identity(value, "request_id", "execution request")
    inputs = value["inputs"]
    if not isinstance(inputs, dict):
        raise ProductionLayerDownstreamSimulationError(
            "execution request inputs are malformed"
        )
    exact_keys(
        inputs,
        {"attention_execution_report_id", "token_id"},
        set(),
        "execution request inputs",
    )
    token_id = _required_int(inputs["token_id"], "request token ID")
    expected_token_id = plan["hbm"]["regions"][0]["source"]["row"]
    if (
        value["schema"] != REQUEST_SCHEMA
        or value["graph_id"] != plan["graph_id"]
        or value["source_operation_ids"] != plan["source_operation_ids"]
        or inputs["attention_execution_report_id"]
        != source_lock["attention_execution_report_id"]
        or token_id != expected_token_id
    ):
        raise ProductionLayerDownstreamSimulationError(
            "execution request differs from the fixed deployment inputs"
        )
    return value


def _region_for(
    regions: Mapping[str, _SRAMRegion],
    address: int,
    size: int,
) -> _SRAMRegion:
    matches = [region for region in regions.values() if region.contains(address, size)]
    if len(matches) != 1:
        raise ProductionLayerDownstreamSimulationError(
            "SRAM address resolves to zero or multiple regions"
        )
    return matches[0]


def _payload_codes(payload: bytes, shape: tuple[int, int]) -> np.ndarray:
    expected = shape[0] * shape[1] * 2
    if len(payload) != expected:
        raise ProductionLayerDownstreamSimulationError(
            "BF16 payload byte count differs"
        )
    return np.frombuffer(payload, dtype="<u2").reshape(shape)


def _u32_codes(payload: bytes, shape: tuple[int, int]) -> np.ndarray:
    expected = shape[0] * shape[1] * 4
    if len(payload) != expected:
        raise ProductionLayerDownstreamSimulationError(
            "binary32 payload byte count differs"
        )
    return np.frombuffer(payload, dtype="<u4").reshape(shape)


def _bf16_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _u32_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u4").tobytes(order="C")


class ProductionLayerDownstreamSimulator:
    """Immutable deployment whose ABI commands causally produce hidden-1."""

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
    ):
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
    def load(cls, root: Path) -> ProductionLayerDownstreamSimulator:
        deployment = Path(root).resolve()
        if not deployment.is_dir():
            raise ProductionLayerDownstreamSimulationError(
                f"deployment directory does not exist: {deployment}"
            )
        manifest = _manifest(deployment)
        source_lock = _source_lock(deployment, manifest)
        _required_sha(
            source_lock["attention_execution_report_id"],
            "source-lock attention report ID",
        )
        _required_sha(
            source_lock["checkpoint_lock_id"],
            "source-lock checkpoint lock ID",
        )
        try:
            capability = load_production_capability(deployment / "capability.json")
        except ProductionCapabilityError as exc:
            raise ProductionLayerDownstreamSimulationError(
                f"capability admission failed: {exc}"
            ) from exc
        if (
            capability.capability_id != manifest["capability_id"]
            or (capability.command_abi_major, capability.command_abi_minor)
            != (ABI_MAJOR, ELEMENTWISE_ABI_MINOR)
            or not set(NUMERIC_CONTRACTS) <= set(capability.qualified_numeric_contracts)
        ):
            raise ProductionLayerDownstreamSimulationError(
                "capability identity or numerical coverage differs"
            )
        kernel_ir = _kernel_ir(deployment, manifest)
        (
            plan,
            sram_records,
            image,
            direct,
            projections,
            commands,
        ) = _plan(deployment, manifest, capability)
        check = _independent_check(deployment, manifest, plan, kernel_ir)
        expectations = _expectations(deployment, manifest, plan, check)
        known_request = _request(
            deployment / REQUEST_PATH,
            plan,
            source_lock,
        )
        return cls(
            root=deployment,
            manifest=manifest,
            source_lock=source_lock,
            capability=capability,
            kernel_ir=kernel_ir,
            plan=plan,
            sram_records=sram_records,
            image=image,
            direct=direct,
            projections=projections,
            commands=commands,
            expectations=expectations,
            known_request=known_request,
        )

    def execute(self, request_path: Path | None = None) -> dict[str, Any]:
        """Execute the decoded program from fresh initialized-state tracking."""

        request = (
            self._known_request
            if request_path is None
            else _request(
                Path(request_path).resolve(),
                self._plan,
                self._source_lock,
            )
        )
        regions = {
            role: _SRAMRegion.create(record)
            for role, record in self._sram_records.items()
        }
        hbm_base = self._capability.hbm.base_address
        direct_by_address = {
            record["address"]: role for role, record in self._direct.items()
        }
        tile_by_address: dict[int, tuple[str, Mapping[str, Any]]] = {}
        for projection_id, projection in self._projections.items():
            for tile in projection["tiles"]:
                if tile["address"] in tile_by_address:
                    raise ProductionLayerDownstreamSimulationError(
                        "HBM tile address aliases another tile"
                    )
                tile_by_address[tile["address"]] = (projection_id, tile)
        projection_by_kernel = {
            projection["kernel_index"]: (projection_id, projection)
            for projection_id, projection in self._projections.items()
        }
        counters = {name: 0 for name in COUNTER_NAMES}
        intermediate_hashes: dict[str, str] = {}
        saturation = {
            "projection": {
                "attention_output": 0,
                "down": 0,
                "gate": 0,
                "up": 0,
            },
            "rmsnorm": {"normalized": 0, "output": 0},
            "vector": {
                "attention_residual": 0,
                "final_residual": 0,
                "silu_activation": 0,
                "silu_output": 0,
            },
        }
        projection_progress = {projection_id: 0 for projection_id in self._projections}
        trace: list[dict[str, Any]] = []
        fresh_weight_dma: tuple[str, Mapping[str, Any]] | None = None
        completed = False
        hidden_output: bytes | None = None
        rmsnorm_diagnostics: dict[str, str] | None = None

        def capture(role: str, payload: bytes) -> str:
            digest = hashlib.sha256(payload).hexdigest()
            if role in intermediate_hashes:
                raise ProductionLayerDownstreamSimulationError(
                    f"intermediate {role!r} was produced more than once"
                )
            intermediate_hashes[role] = digest
            return digest

        def hbm_read(address: int, size: int) -> bytes:
            offset = address - hbm_base
            if size < 0 or offset < 0 or offset + size > len(self._image):
                raise ProductionLayerDownstreamSimulationError(
                    "command HBM read escapes the deployment image"
                )
            return self._image[offset : offset + size]

        try:
            for command in self._commands:
                if completed:
                    raise ProductionLayerDownstreamSimulationError(
                        "command appears after COMPLETE"
                    )
                counters["command_count"] += 1
                event: dict[str, Any] = {
                    "engine": command.engine.name,
                    "index": command.index,
                    "kernel_index": command.kernel_index,
                    "opcode": command.opcode.name,
                }
                if command.opcode == Opcode.DMA_HBM_TO_SRAM:
                    payload = hbm_read(command.source0, command.size0)
                    destination = _region_for(
                        regions, command.destination, command.size0
                    )
                    destination.write(command.destination, payload)
                    counters["dma_command_count"] += 1
                    counters["dma_sram_bytes_written"] += command.size0
                    counters["hbm_transferred_bytes_read"] += command.size0
                    counters["hbm_useful_bytes_read"] += command.size0
                    tile_binding = tile_by_address.get(command.source0)
                    if destination.region_id == "weight_tile":
                        if (
                            tile_binding is None
                            or tile_binding[1]["size_bytes"] != command.size0
                            or tile_binding[0]
                            not in {
                                projection_id
                                for projection_id, projection in self._projections.items()
                                if projection["kernel_index"] == command.kernel_index
                            }
                        ):
                            raise ProductionLayerDownstreamSimulationError(
                                "weight DMA does not select the next legal tile"
                            )
                        fresh_weight_dma = tile_binding
                        event.update(
                            {
                                "k_start": tile_binding[1]["k_start"],
                                "n_start": tile_binding[1]["n_start"],
                                "projection": tile_binding[0],
                                "tile_index": tile_binding[1]["tile_index"],
                            }
                        )
                    else:
                        if tile_binding is not None:
                            raise ProductionLayerDownstreamSimulationError(
                                "projection tile DMA targets a non-weight region"
                            )
                        role = direct_by_address.get(command.source0)
                        if role is None or role != destination.region_id:
                            raise ProductionLayerDownstreamSimulationError(
                                "direct DMA source and SRAM role differ"
                            )
                        fresh_weight_dma = None
                        event["role"] = role

                elif command.opcode == Opcode.MATMUL_BF16_TILE:
                    binding = projection_by_kernel.get(command.kernel_index)
                    if binding is None or fresh_weight_dma is None:
                        raise ProductionLayerDownstreamSimulationError(
                            "matrix command lacks a fresh causal weight DMA"
                        )
                    projection_id, projection = binding
                    dma_projection, tile = fresh_weight_dma
                    expected_tile_index = projection_progress[projection_id]
                    if (
                        dma_projection != projection_id
                        or tile["tile_index"] != expected_tile_index
                        or projection["tiles"][expected_tile_index] != tile
                    ):
                        raise ProductionLayerDownstreamSimulationError(
                            "matrix tile order or projection identity differs"
                        )
                    input_region = regions[projection["input_region"]]
                    weight_region = regions["weight_tile"]
                    accumulator_region = regions["accumulator_tile"]
                    output_region = regions[projection["output_region"]]
                    input_payload = input_region.read(
                        command.source0, command.size0 * command.size2 * 2
                    )
                    weight_payload = weight_region.read(
                        command.source1,
                        command.size1 * command.size2 * 2,
                    )
                    input_codes = _payload_codes(
                        input_payload, (command.size0, command.size2)
                    )
                    weight_codes = _payload_codes(
                        weight_payload, (command.size1, command.size2)
                    )
                    initialized = bool(command.flags & MATMUL_INIT)
                    final = bool(command.flags & MATMUL_FINAL)
                    if initialized != (tile["k_start"] == 0) or final != (
                        tile["k_start"] + tile["k_count"]
                        == self._plan["problem"]["projections"][
                            tuple(self._projections).index(projection_id)
                        ]["k"]
                    ):
                        raise ProductionLayerDownstreamSimulationError(
                            "matrix reduction flags differ from tile position"
                        )
                    accumulator_codes = None
                    accumulator_bytes = command.size0 * command.size1 * 4
                    if not initialized:
                        accumulator_codes = _u32_codes(
                            accumulator_region.read(
                                command.destination, accumulator_bytes
                            ),
                            (command.size0, command.size1),
                        )
                        counters["accumulator_sram_bytes_read"] += accumulator_bytes
                    accumulated = accumulate_bf16_tile_fp32(
                        input_codes,
                        weight_codes,
                        accumulator_codes,
                    )
                    accumulator_region.write(
                        command.destination,
                        _u32_payload(accumulated.values),
                    )
                    counters["accumulator_sram_bytes_written"] += accumulator_bytes
                    scalar_operations = command.size0 * command.size1 * command.size2
                    counters["matmul_command_count"] += 1
                    counters["matrix_input_sram_bytes_read"] += len(input_payload)
                    counters["weight_sram_bytes_read"] += len(weight_payload)
                    counters["projection_multiplications"] += scalar_operations
                    counters["projection_accumulation_additions"] += scalar_operations
                    event.update(
                        {
                            "final": final,
                            "k_start": tile["k_start"],
                            "n_start": tile["n_start"],
                            "projection": projection_id,
                            "tile_index": tile["tile_index"],
                        }
                    )
                    if final:
                        finalized = finalize_bf16_accumulator(accumulated.values)
                        output_payload = _bf16_payload(finalized.values)
                        output_region.write(command.auxiliary, output_payload)
                        counters["matrix_output_sram_bytes_written"] += len(
                            output_payload
                        )
                        saturation["projection"][projection_id] += (
                            finalized.output_saturated_element_count
                        )
                        if tile["tile_index"] == len(projection["tiles"]) - 1:
                            entire_output = output_region.read(
                                output_region.address,
                                output_region.logical_bytes,
                            )
                            digest = capture(projection["output_region"], entire_output)
                            event["output_payload_sha256"] = digest
                    projection_progress[projection_id] += 1
                    fresh_weight_dma = None

                elif command.opcode == Opcode.ADD_BF16:
                    if fresh_weight_dma is not None:
                        raise ProductionLayerDownstreamSimulationError(
                            "vector add bypasses a pending weight DMA"
                        )
                    size = command.size0 * command.size1 * 2
                    left_region = _region_for(regions, command.source0, size)
                    right_region = _region_for(regions, command.source1, size)
                    output_region = _region_for(regions, command.destination, size)
                    left = _payload_codes(
                        left_region.read(command.source0, size),
                        (command.size0, command.size1),
                    )
                    right = _payload_codes(
                        right_region.read(command.source1, size),
                        (command.size0, command.size1),
                    )
                    result = bf16_add_rne(left, right)
                    payload = _bf16_payload(result.values)
                    output_region.write(command.destination, payload)
                    counters["add_command_count"] += 1
                    counters["add_input_sram_bytes_read"] += 2 * size
                    counters["add_output_sram_bytes_written"] += size
                    counters["residual_additions"] += command.size0 * command.size1
                    if command.kernel_index == 1:
                        role = "post_attention"
                        saturation_role = "attention_residual"
                    elif command.kernel_index == 7:
                        role = "hidden_1"
                        saturation_role = "final_residual"
                    else:
                        raise ProductionLayerDownstreamSimulationError(
                            "add kernel index differs"
                        )
                    saturation["vector"][saturation_role] = (
                        result.output_saturated_element_count
                    )
                    digest = hashlib.sha256(payload).hexdigest()
                    if role == "hidden_1":
                        if hidden_output is not None:
                            raise ProductionLayerDownstreamSimulationError(
                                "hidden-1 was produced more than once"
                            )
                        hidden_output = payload
                    else:
                        capture(role, payload)
                    event.update({"output": role, "output_payload_sha256": digest})

                elif command.opcode == Opcode.RMSNORM_BF16:
                    if fresh_weight_dma is not None:
                        raise ProductionLayerDownstreamSimulationError(
                            "RMSNorm bypasses a pending weight DMA"
                        )
                    input_bytes = command.size0 * command.size1 * 2
                    weight_bytes = command.size1 * 2
                    source = _region_for(regions, command.source0, input_bytes)
                    weight = _region_for(regions, command.source1, weight_bytes)
                    output = _region_for(regions, command.destination, input_bytes)
                    source_codes = _payload_codes(
                        source.read(command.source0, input_bytes),
                        (command.size0, command.size1),
                    )
                    weight_codes = np.frombuffer(
                        weight.read(command.source1, weight_bytes),
                        dtype="<u2",
                    )
                    result = rms_norm_bf16(
                        source_codes,
                        weight_codes,
                        epsilon_code=command.size2,
                    )
                    payload = _bf16_payload(result.values)
                    output.write(command.destination, payload)
                    counters["rmsnorm_command_count"] += 1
                    counters["rmsnorm_input_sram_bytes_read"] += input_bytes
                    counters["rmsnorm_weight_sram_bytes_read"] += weight_bytes
                    counters["rmsnorm_output_sram_bytes_written"] += input_bytes
                    elements = command.size0 * command.size1
                    counters["input_square_multiplications"] += elements
                    counters["reduction_additions"] += command.size0 * (
                        command.size1 - 1
                    )
                    counters["mean_divisions"] += command.size0
                    counters["epsilon_additions"] += command.size0
                    counters["reciprocal_square_roots"] += command.size0
                    counters["normalization_multiplications"] += elements
                    counters["final_weight_multiplications"] += elements
                    saturation["rmsnorm"]["normalized"] = (
                        result.normalized_saturated_element_count
                    )
                    saturation["rmsnorm"]["output"] = (
                        result.output_saturated_element_count
                    )
                    digest = capture("mlp_norm", payload)
                    rmsnorm_diagnostics = {
                        "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                            _u32_payload(result.inverse_rms_codes.reshape(ROWS, 1))
                        ).hexdigest(),
                        "mean_square_binary32_codes_sha256": hashlib.sha256(
                            _u32_payload(result.mean_square_codes.reshape(ROWS, 1))
                        ).hexdigest(),
                        "normalized_payload_sha256": hashlib.sha256(
                            _bf16_payload(result.normalized_values)
                        ).hexdigest(),
                    }
                    event.update(
                        {"output": "mlp_norm", "output_payload_sha256": digest}
                    )

                elif command.opcode == Opcode.SILU_MUL_BF16:
                    if fresh_weight_dma is not None:
                        raise ProductionLayerDownstreamSimulationError(
                            "SiLU multiply bypasses a pending weight DMA"
                        )
                    size = command.size0 * command.size1 * 2
                    gate_region = _region_for(regions, command.source0, size)
                    up_region = _region_for(regions, command.source1, size)
                    output_region = _region_for(regions, command.destination, size)
                    gate = _payload_codes(
                        gate_region.read(command.source0, size),
                        (command.size0, command.size1),
                    )
                    up = _payload_codes(
                        up_region.read(command.source1, size),
                        (command.size0, command.size1),
                    )
                    result = qwen3_silu_mul_bf16(gate, up)
                    activation_payload = _bf16_payload(result.activation_values)
                    output_payload = _bf16_payload(result.values)
                    output_region.write(command.destination, output_payload)
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
                    activation_digest = capture("silu_activation", activation_payload)
                    output_digest = capture("gated_mlp", output_payload)
                    event.update(
                        {
                            "activation_payload_sha256": activation_digest,
                            "output": "gated_mlp",
                            "output_payload_sha256": output_digest,
                        }
                    )

                elif command.opcode == Opcode.COMPLETE:
                    if (
                        fresh_weight_dma is not None
                        or command.index != len(self._commands) - 1
                    ):
                        raise ProductionLayerDownstreamSimulationError(
                            "COMPLETE occurs with unfinished work"
                        )
                    counters["complete_command_count"] += 1
                    completed = True

                else:
                    raise ProductionLayerDownstreamSimulationError(
                        f"unsupported downstream opcode {command.opcode.name}"
                    )
                trace.append(event)
        except (
            BF16KernelError,
            ElementwiseKernelError,
            RMSNormKernelError,
        ) as exc:
            raise ProductionLayerDownstreamSimulationError(
                f"target numerical execution failed: {exc}"
            ) from exc

        if (
            not completed
            or hidden_output is None
            or rmsnorm_diagnostics is None
            or projection_progress
            != {
                role: len(projection["tiles"])
                for role, projection in self._projections.items()
            }
            or set(intermediate_hashes) != set(INTERMEDIATE_ROLES)
        ):
            raise ProductionLayerDownstreamSimulationError(
                "program completed without every required downstream output"
            )
        output_hash = hashlib.sha256(hidden_output).hexdigest()
        if counters != self._expectations["counters"]:
            raise ProductionLayerDownstreamSimulationError(
                "observed counters differ from expectations"
            )
        if intermediate_hashes != self._expectations["intermediate_payload_sha256"]:
            raise ProductionLayerDownstreamSimulationError(
                "observed intermediate hashes differ from expectations"
            )
        if {"hidden_1": output_hash} != self._expectations["output_payload_sha256"]:
            raise ProductionLayerDownstreamSimulationError(
                "observed hidden-1 hash differs from expectations"
            )
        if saturation != self._expectations["saturated_element_count"]:
            raise ProductionLayerDownstreamSimulationError(
                "observed saturation counts differ from expectations"
            )
        output_codes = np.frombuffer(hidden_output, dtype="<u2")
        trace_sha256 = hashlib.sha256(canonical_json_bytes(trace)).hexdigest()
        body = {
            "build_id": self._manifest["build_id"],
            "command_abi": {
                "major": ABI_MAJOR,
                "minor": ELEMENTWISE_ABI_MINOR,
            },
            "command_count": len(self._commands),
            "counter_reconciliation": "exact",
            "counters": counters,
            "intermediate_payload_sha256": intermediate_hashes,
            "numeric_diagnostics": {"rmsnorm": rmsnorm_diagnostics},
            "output": {
                "hidden_1": {
                    "codes": [int(code) for code in output_codes],
                    "dtype": "bf16",
                    "payload_sha256": output_hash,
                    "shape": [ROWS, HIDDEN_WIDTH],
                    "size_bytes": len(hidden_output),
                }
            },
            "physical_plan_id": self._plan["physical_plan_id"],
            "qualification_report_id": self._manifest["qualification_report_id"],
            "request_id": request["request_id"],
            "saturated_element_count": saturation,
            "schema": EXECUTION_SCHEMA,
            "status": "pass",
            "timing": {
                "reason": "capability_uncharacterized",
                "status": "unavailable",
            },
            "trace": trace,
            "trace_sha256": trace_sha256,
        }
        return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def publish_layer_downstream_execution_report(
    report: Mapping[str, Any],
    output_path: Path,
) -> None:
    """Atomically retain one canonical report without overwriting evidence."""

    if not isinstance(report, Mapping):
        raise ProductionLayerDownstreamSimulationError(
            "execution report must be an object"
        )
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise ProductionLayerDownstreamSimulationError(
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
            raise ProductionLayerDownstreamSimulationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "EXECUTION_SCHEMA",
    "ProductionLayerDownstreamSimulationError",
    "ProductionLayerDownstreamSimulator",
    "publish_layer_downstream_execution_report",
]
