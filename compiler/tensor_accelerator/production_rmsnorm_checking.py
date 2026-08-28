"""Independent inverse checker for embedding-to-RMSNorm deployments.

This module does not import the compiler generator.  It reconstructs source
payloads, neutral kernels, storage, commands, and counter expectations from the
locked inputs and emitted candidate artifacts.
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
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE,
    NUMERIC_CONTRACT,
)

from .common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
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
    ABI_MINOR,
    Engine,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi,
    decode,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    load_production_model_graph,
)
from .rmsnorm_qualification import (
    RMSNormQualificationError,
    load_rmsnorm_qualification,
)


CHECK_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_independent_check.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_source_lock.v1"
HBM_IMAGE_PATH = "memory/hbm_embedding_rmsnorm.bin"
COMMAND_PATH = "program/commands.bin"
LOOKUP_CONTRACT = "bf16_payload_lookup_v1"
COMPILER_VERSION = "tensor-accelerator-production-rmsnorm-0.1.0"


class ProductionRMSNormCheckError(RuntimeError):
    """Raised when a candidate cannot be independently proven legal."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise ProductionRMSNormCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise ProductionRMSNormCheckError(f"{label} is not canonical JSON")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProductionRMSNormCheckError(f"{label} must be a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionRMSNormCheckError(f"{label} must be a safe relative path")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise ProductionRMSNormCheckError(f"{label} {field} differs from content")


def _binding(
    model: ProductionModelGraph,
    tensor_id: str,
    *,
    lock_id: str,
    rank: int,
) -> tuple[tuple[int, ...], str]:
    tensor = model.tensor_by_id.get(tensor_id)
    if tensor is None or tensor.dtype != "bf16" or tensor.binding is None:
        raise ProductionRMSNormCheckError(f"graph tensor {tensor_id!r} is unbound")
    binding = tensor.binding
    if (
        len(tensor.shape) != rank
        or binding.checkpoint_lock_id != lock_id
        or len(binding.sources) != 1
        or binding.sources[0].tensor_name != tensor_id
        or binding.sources[0].dtype != "bf16"
        or binding.sources[0].shape != tuple(tensor.shape)
        or binding.transform != {"kind": "identity"}
        or binding.payload_sha256 != binding.sources[0].payload_sha256
    ):
        raise ProductionRMSNormCheckError(
            f"graph tensor {tensor_id!r} binding differs"
        )
    return binding.sources[0].shape, binding.sources[0].payload_sha256


def _graph(
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    lock_id: str,
) -> tuple[str, str, str, str]:
    embedding = qualification["input"]["tensor"]
    weight = qualification["weight"]["tensor"]
    embedding_shape, embedding_hash = _binding(
        model, embedding, lock_id=lock_id, rank=2
    )
    weight_shape, weight_hash = _binding(model, weight, lock_id=lock_id, rank=1)
    if (
        list(embedding_shape) != qualification["input"]["source_shape"]
        or embedding_hash != qualification["input"]["source_payload_sha256"]
        or list(weight_shape) != qualification["weight"]["shape"]
        or weight_hash != qualification["weight"]["payload_sha256"]
    ):
        raise ProductionRMSNormCheckError("graph bindings differ from qualification")
    lookups = [
        operation
        for operation in model.operations
        if operation.kind == "EMBEDDING_LOOKUP"
        and operation.inputs == ("input.token_ids", embedding)
        and operation.numeric_contract == LOOKUP_CONTRACT
    ]
    if len(lookups) != 1 or len(lookups[0].outputs) != 1:
        raise ProductionRMSNormCheckError("graph embedding operation differs")
    lookup = lookups[0]
    norms = [
        operation
        for operation in model.operations
        if operation.kind == "RMS_NORM"
        and operation.inputs == (lookup.outputs[0], weight)
        and operation.numeric_contract == NUMERIC_CONTRACT
    ]
    width = qualification["output"]["shape"][1]
    if (
        len(norms) != 1
        or len(norms[0].outputs) != 1
        or norms[0].attributes.get("epsilon") != 1e-6
        or norms[0].attributes.get("normalization_width") != width
        or norms[0].attributes.get("layer") != 0
    ):
        raise ProductionRMSNormCheckError("graph RMSNorm operation differs")
    return (
        lookup.operation_id,
        norms[0].operation_id,
        lookup.outputs[0],
        norms[0].outputs[0],
    )


def _capture_row(shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = shape[1] * 2
    row_start = row * row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        start = max(cursor, row_start)
        stop = min(end, row_start + row_bytes)
        if start < stop:
            captured.extend(chunk[start - cursor : stop - cursor])
        cursor = end

    return captured, consume


def _read_sources(
    snapshot: Path,
    lock: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> tuple[bytes, bytes]:
    token_id = qualification["input"]["token_id"]
    try:
        with LockedCheckpointReader(snapshot, dict(lock)) as reader:
            embedding_record = reader.tensor_record(qualification["input"]["tensor"])
            shape = tuple(embedding_record["shape"])
            if len(shape) != 2 or not 0 <= token_id < shape[0]:
                raise ProductionRMSNormCheckError("source token row is illegal")
            captured, consumer = _capture_row(shape, token_id)
            reader.consume_tensor_payload(embedding_record["name"], consumer)
            weight_payload = bytearray()
            weight_record = reader.consume_tensor_payload(
                qualification["weight"]["tensor"], weight_payload.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionRMSNormCheckError(
            f"independent locked source read failed: {exc}"
        ) from exc
    row_payload = bytes(captured)
    weights = bytes(weight_payload)
    if (
        embedding_record["payload_sha256"]
        != qualification["input"]["source_payload_sha256"]
        or embedding_record["shape"] != qualification["input"]["source_shape"]
        or hashlib.sha256(row_payload).hexdigest()
        != qualification["input"]["row_payload_sha256"]
        or weight_record["payload_sha256"]
        != qualification["weight"]["payload_sha256"]
        or weight_record["shape"] != qualification["weight"]["shape"]
    ):
        raise ProductionRMSNormCheckError("locked sources differ from qualification")
    return row_payload, weights


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
    copies = (
        ("source/model_graph.v2.json", model_graph_path),
        ("source/checkpoint.lock.json", checkpoint_lock_path),
        ("capability.json", capability_path),
        ("source/qualification.json", qualification_path),
    )
    for relative, source in copies:
        if (root / relative).read_bytes() != source.read_bytes():
            raise ProductionRMSNormCheckError(
                f"candidate source copy {relative!r} differs"
            )
    source_lock = _load_canonical(root / "source.lock.json", "source lock")
    exact_keys(
        source_lock,
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
    _identity(source_lock, "source_lock_id", "source lock")
    expected_sources: list[dict[str, Any]] = []
    for role, path in (
        ("model_graph", model_graph_path),
        ("checkpoint_lock", checkpoint_lock_path),
        ("hardware_capability", capability_path),
        ("qualification_report", qualification_path),
    ):
        digest, size = sha256_file(path)
        expected_sources.append({"role": role, "sha256": digest, "size_bytes": size})
    if source_lock != {
        "capability_id": capability_id,
        "checkpoint_lock_id": lock_id,
        "compiler_version": COMPILER_VERSION,
        "graph_id": graph_id,
        "qualification_report_id": qualification_id,
        "schema": SOURCE_LOCK_SCHEMA,
        "source_lock_id": source_lock["source_lock_id"],
        "sources": expected_sources,
    }:
        raise ProductionRMSNormCheckError("source lock differs from inputs")
    return source_lock["source_lock_id"]


def _problem(
    raw: Any,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormCheckError("problem must be an object")
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
    width = qualification["output"]["shape"][1]
    expected = {
        "resident_embedding_base_token": qualification["input"]["token_id"],
        "resident_embedding_rows": 1,
        "row_bytes": width * 2,
        "rows": 1,
        "width": width,
    }
    if raw != expected:
        raise ProductionRMSNormCheckError("problem differs from qualification")
    if (
        capability.command_abi_minor != ABI_MINOR
        or capability.vector_engine is None
        or capability.vector_engine.max_rows < 1
        or capability.vector_engine.max_width < width
        or NUMERIC_CONTRACT not in capability.qualified_numeric_contracts
    ):
        raise ProductionRMSNormCheckError("problem exceeds qualified capability")
    return expected


def _counters(problem: Mapping[str, int]) -> dict[str, int]:
    width = problem["width"]
    row_bytes = problem["row_bytes"]
    return {
        "command_count": 4,
        "complete_command_count": 1,
        "direct_dma_command_count": 1,
        "dma_command_count": 2,
        "dma_sram_bytes_written": 2 * row_bytes,
        "epsilon_additions": 1,
        "final_weight_multiplications": width,
        "hbm_transferred_bytes_read": 2 * row_bytes,
        "hbm_useful_bytes_read": 2 * row_bytes,
        "indexed_dma_command_count": 1,
        "input_square_multiplications": width,
        "input_sram_bytes_read": row_bytes,
        "mean_divisions": 1,
        "normalization_multiplications": width,
        "output_sram_bytes_written": row_bytes,
        "reciprocal_square_roots": 1,
        "reduction_additions": width - 1,
        "rmsnorm_command_count": 1,
        "runtime_request_sram_bytes_written": 4,
        "weight_sram_bytes_read": row_bytes,
    }


def _kernel(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    source: tuple[str, str, str, str],
    problem: Mapping[str, int],
) -> str:
    value = _load_canonical(root / "ir/tensor_kernel_ir.json", "kernel IR")
    _identity(value, "kernel_ir_id", "kernel IR")
    lookup_id, rmsnorm_id, lookup_output, rmsnorm_output = source
    expected = {
        "graph_id": model.graph_id,
        "kernel_ir_id": value["kernel_ir_id"],
        "kernels": [
            {
                "attributes": {
                    "index_dtype": "u32",
                    "output_dtype": "bf16",
                    "source_index_max_exclusive": qualification["input"][
                        "source_shape"
                    ][0],
                    "source_index_min": 0,
                },
                "index": 0,
                "inputs": ["input.token_ids", qualification["input"]["tensor"]],
                "kind": "EMBEDDING_LOOKUP",
                "numeric_contract": LOOKUP_CONTRACT,
                "outputs": [lookup_output],
                "shape": {"rows": 1, "width": problem["width"]},
                "source_operation_id": lookup_id,
            },
            {
                "attributes": {
                    "epsilon_binary32_code": EPSILON_CODE,
                    "final_weight_product": "bf16_multiply_then_bf16_rne",
                    "normalized_boundary": "bf16_rne_before_weight",
                    "reduction_order": "canonical_balanced_binary32_tree",
                    "rsqrt": "correctly_rounded_binary32_rne",
                },
                "index": 1,
                "inputs": [lookup_output, qualification["weight"]["tensor"]],
                "kind": "RMS_NORM",
                "numeric_contract": NUMERIC_CONTRACT,
                "outputs": [rmsnorm_output],
                "shape": {"rows": 1, "width": problem["width"]},
                "source_operation_id": rmsnorm_id,
            },
        ],
        "qualification_report_id": qualification["report_id"],
        "schema": KERNEL_SCHEMA,
    }
    if value != expected:
        raise ProductionRMSNormCheckError("kernel IR differs from graph semantics")
    return value["kernel_ir_id"]


def _sram(
    raw: Any,
    *,
    problem: Mapping[str, int],
    capability: ProductionCapability,
) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormCheckError("SRAM plan must be an object")
    exact_keys(raw, {"addressing", "regions"}, set(), "SRAM plan")
    if raw["addressing"] != "bank_base_plus_byte_offset":
        raise ProductionRMSNormCheckError("SRAM addressing differs")
    specs = (
        ("token_id", 0, "u32", [1], 4),
        ("embedding", 1, "bf16", [1, problem["width"]], problem["row_bytes"]),
        ("rmsnorm_weight", 2, "bf16", [problem["width"]], problem["row_bytes"]),
        ("output", 3, "bf16", [1, problem["width"]], problem["row_bytes"]),
    )
    expected: list[dict[str, Any]] = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        expected.append(
            {
                "address": capability.sram.bank_base(bank),
                "allocated_bytes": align_up(logical_bytes, capability.sram.word_bytes),
                "bank": bank,
                "dtype": dtype,
                "id": region_id,
                "logical_bytes": logical_bytes,
                "shape": shape,
            }
        )
    if raw["regions"] != expected:
        raise ProductionRMSNormCheckError("SRAM region allocation differs")
    return {region["id"]: region for region in expected}


def _hbm(
    raw: Any,
    root: Path,
    *,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
    row_payload: bytes,
    weight_payload: bytes,
) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ProductionRMSNormCheckError("HBM plan must be an object")
    exact_keys(raw, {"image", "regions"}, set(), "HBM plan")
    image_record = raw["image"]
    if not isinstance(image_record, dict):
        raise ProductionRMSNormCheckError("HBM image record is malformed")
    exact_keys(
        image_record,
        {"base_address", "path", "sha256", "size_bytes"},
        set(),
        "HBM image",
    )
    path = _safe_relative(image_record["path"], "HBM image path")
    if path != HBM_IMAGE_PATH:
        raise ProductionRMSNormCheckError("HBM image path differs")
    image = (root / path).read_bytes()
    if (
        image_record["base_address"] != capability.hbm.base_address
        or image_record["size_bytes"] != len(image)
        or image_record["sha256"] != hashlib.sha256(image).hexdigest()
        or len(image) % capability.hbm.burst_bytes
    ):
        raise ProductionRMSNormCheckError("HBM image identity or alignment differs")
    expected: list[dict[str, Any]] = []
    cursor = 0
    for region_id, payload, source in (
        (
            "embedding_rows",
            row_payload,
            {
                "dtype": "bf16",
                "row_count": 1,
                "row_stride_bytes": len(row_payload),
                "source_payload_sha256": qualification["input"][
                    "source_payload_sha256"
                ],
                "source_row_base": qualification["input"]["token_id"],
                "source_shape": qualification["input"]["source_shape"],
                "tensor_name": qualification["input"]["tensor"],
            },
        ),
        (
            "rmsnorm_weight",
            weight_payload,
            {
                "dtype": "bf16",
                "payload_sha256": qualification["weight"]["payload_sha256"],
                "shape": qualification["weight"]["shape"],
                "tensor_name": qualification["weight"]["tensor"],
            },
        ),
    ):
        offset = align_up(cursor, capability.hbm.burst_bytes)
        if any(image[cursor:offset]):
            raise ProductionRMSNormCheckError("HBM alignment padding is nonzero")
        if image[offset : offset + len(payload)] != payload:
            raise ProductionRMSNormCheckError(
                f"HBM region {region_id!r} differs from locked source"
            )
        expected.append(
            {
                "address": capability.hbm.base_address + offset,
                "id": region_id,
                "offset_bytes": offset,
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "source": source,
            }
        )
        cursor = offset + len(payload)
    padded_end = align_up(cursor, capability.hbm.burst_bytes)
    if padded_end != len(image) or any(image[cursor:padded_end]):
        raise ProductionRMSNormCheckError("HBM image coverage or padding differs")
    if raw["regions"] != expected:
        raise ProductionRMSNormCheckError("HBM region metadata differs")
    return expected


def _program(
    raw: Any,
    root: Path,
    *,
    capability: ProductionCapability,
    problem: Mapping[str, int],
    hbm_regions: list[dict[str, Any]],
    sram_regions: Mapping[str, Mapping[str, Any]],
) -> int:
    if not isinstance(raw, dict):
        raise ProductionRMSNormCheckError("program must be an object")
    exact_keys(raw, {"command_count", "path", "sha256", "size_bytes"}, set(), "program")
    path = _safe_relative(raw["path"], "program.path")
    if path != COMMAND_PATH:
        raise ProductionRMSNormCheckError("program path differs")
    payload = (root / path).read_bytes()
    if (
        raw["size_bytes"] != len(payload)
        or raw["sha256"] != hashlib.sha256(payload).hexdigest()
    ):
        raise ProductionRMSNormCheckError("program identity differs")
    try:
        commands = decode(payload)
        observed_abi = command_abi(payload)
    except ProductionCommandError as exc:
        raise ProductionRMSNormCheckError(f"program is malformed: {exc}") from exc
    if observed_abi != (
        capability.command_abi_major,
        capability.command_abi_minor,
    ):
        raise ProductionRMSNormCheckError("program ABI differs from capability")
    hbm = {region["id"]: region for region in hbm_regions}
    local = sram_regions
    expected = (
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=0,
            source0=hbm["embedding_rows"]["address"],
            source1=local["token_id"]["address"],
            destination=local["embedding"]["address"],
            auxiliary=problem["resident_embedding_base_token"],
            size0=problem["row_bytes"],
            size1=problem["row_bytes"],
            size2=problem["resident_embedding_rows"],
            size3=4,
        ),
        ProductionCommand(
            index=1,
            opcode=Opcode.DMA_HBM_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=1,
            source0=hbm["rmsnorm_weight"]["address"],
            destination=local["rmsnorm_weight"]["address"],
            size0=problem["row_bytes"],
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
            kernel_index=1,
            source0=local["embedding"]["address"],
            source1=local["rmsnorm_weight"]["address"],
            destination=local["output"]["address"],
            size0=1,
            size1=problem["width"],
            size2=EPSILON_CODE,
        ),
        ProductionCommand(index=3, opcode=Opcode.COMPLETE, engine=Engine.CONTROL),
    )
    if commands != expected or raw["command_count"] != len(expected):
        raise ProductionRMSNormCheckError("command program differs from legal schedule")
    return len(commands)


def _request(
    root: Path,
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    source_operation_ids: tuple[str, str],
) -> str:
    value = _load_canonical(root / "request/execution_request.json", "request")
    _identity(value, "request_id", "request")
    expected = {
        "graph_id": model.graph_id,
        "request_id": value["request_id"],
        "schema": REQUEST_SCHEMA,
        "source_operation_ids": list(source_operation_ids),
        "token": {"dtype": "u32", "token_id": qualification["input"]["token_id"]},
    }
    if value != expected:
        raise ProductionRMSNormCheckError("request differs from qualified token")
    return value["request_id"]


def check_rmsnorm_candidate(
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
        qualification = load_rmsnorm_qualification(Path(qualification_path))
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        RMSNormQualificationError,
    ) as exc:
        raise ProductionRMSNormCheckError(
            f"independent source admission failed: {exc}"
        ) from exc
    root = Path(root)
    if qualification["checkpoint_lock_id"] != lock["lock_id"]:
        raise ProductionRMSNormCheckError("qualification checkpoint identity differs")
    source = _graph(model, qualification, lock["lock_id"])
    row_payload, weight_payload = _read_sources(Path(snapshot), lock, qualification)
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
        or plan["numeric_contracts"] != [LOOKUP_CONTRACT, NUMERIC_CONTRACT]
        or plan["qualification_report_id"] != qualification["report_id"]
        or plan["source_operation_ids"] != list(source[:2])
    ):
        raise ProductionRMSNormCheckError("physical-plan identities differ")
    problem = _problem(plan["problem"], qualification, capability)
    kernel_ir_id = _kernel(
        root,
        model=model,
        qualification=qualification,
        source=source,
        problem=problem,
    )
    sram_regions = _sram(plan["sram"], problem=problem, capability=capability)
    hbm_regions = _hbm(
        plan["hbm"],
        root,
        qualification=qualification,
        capability=capability,
        row_payload=row_payload,
        weight_payload=weight_payload,
    )
    command_count = _program(
        plan["program"],
        root,
        capability=capability,
        problem=problem,
        hbm_regions=hbm_regions,
        sram_regions=sram_regions,
    )
    request_id = _request(
        root,
        model=model,
        qualification=qualification,
        source_operation_ids=source[:2],
    )
    counters = _counters(problem)
    if plan["expected_counters"] != counters:
        raise ProductionRMSNormCheckError(
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
        "reconstructed_sources": [
            {
                "payload_sha256": hashlib.sha256(row_payload).hexdigest(),
                "role": "embedding_row",
                "size_bytes": len(row_payload),
                "source_tensor": qualification["input"]["tensor"],
            },
            {
                "payload_sha256": hashlib.sha256(weight_payload).hexdigest(),
                "role": "rmsnorm_weight",
                "size_bytes": len(weight_payload),
                "source_tensor": qualification["weight"]["tensor"],
            },
        ],
        "request_id": request_id,
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock_id,
        "status": "pass",
    }
    return {**body, "check_id": sha256_bytes(canonical_json_bytes(body))}


__all__ = [
    "CHECK_SCHEMA",
    "ProductionRMSNormCheckError",
    "check_rmsnorm_candidate",
]
