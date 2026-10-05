"""Deterministic compiler for a real Qwen embedding-to-RMSNorm slice."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
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
    Engine,
    Opcode,
    ProductionCommand,
    RMSNORM_ABI_MINOR,
    disassemble,
    encode,
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


COMPILER_VERSION = "tensor-accelerator-production-rmsnorm-0.1.0"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_physical_plan.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_request.v1"
SOURCE_LOCK_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_source_lock.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_expectations.v1"
MANIFEST_SCHEMA = "opentallas.tensor_accelerator.rmsnorm_deployment.v1"
HBM_IMAGE_PATH = "memory/hbm_embedding_rmsnorm.bin"
COMMAND_PATH = "program/commands.bin"
REQUEST_PATH = "request/execution_request.json"
PHYSICAL_PLAN_PATH = "physical/physical_plan.json"
LOOKUP_CONTRACT = "bf16_payload_lookup_v1"


class ProductionRMSNormBuildError(RuntimeError):
    """Raised when the embedding-to-RMSNorm deployment cannot be proven."""


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionRMSNormBuildError(f"unsafe compiler artifact path: {value!r}")
    return value


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _copy_canonical(source: Path, destination: Path) -> None:
    destination.write_bytes(Path(source).read_bytes())


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
    ):
        raise ProductionRMSNormBuildError(
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
        raise ProductionRMSNormBuildError(
            f"tensor {tensor_id!r} is not an identity checkpoint binding"
        )
    return binding.sources[0].shape, binding.sources[0].payload_sha256


def _source_operations(
    model: ProductionModelGraph,
    *,
    embedding_tensor: str,
    weight_tensor: str,
    width: int,
) -> tuple[str, str, str, str]:
    lookups = [
        operation
        for operation in model.operations
        if operation.kind == "EMBEDDING_LOOKUP"
        and operation.inputs == ("input.token_ids", embedding_tensor)
        and operation.numeric_contract == LOOKUP_CONTRACT
    ]
    if len(lookups) != 1 or len(lookups[0].outputs) != 1:
        raise ProductionRMSNormBuildError(
            "production graph must contain exactly one source embedding lookup"
        )
    lookup = lookups[0]
    norms = [
        operation
        for operation in model.operations
        if operation.kind == "RMS_NORM"
        and operation.inputs == (lookup.outputs[0], weight_tensor)
        and operation.numeric_contract == NUMERIC_CONTRACT
    ]
    if len(norms) != 1 or len(norms[0].outputs) != 1:
        raise ProductionRMSNormBuildError(
            "production graph must contain exactly one source RMSNorm"
        )
    norm = norms[0]
    if (
        norm.attributes.get("epsilon") != 1e-6
        or norm.attributes.get("normalization_width") != width
        or norm.attributes.get("layer") != 0
    ):
        raise ProductionRMSNormBuildError("source RMSNorm attributes differ")
    return (
        lookup.operation_id,
        norm.operation_id,
        lookup.outputs[0],
        norm.outputs[0],
    )


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
) -> tuple[bytes, bytes]:
    embedding_name = qualification["input"]["tensor"]
    token_id = qualification["input"]["token_id"]
    weight_name = qualification["weight"]["tensor"]
    try:
        with LockedCheckpointReader(snapshot, dict(lock)) as reader:
            embedding_record = reader.tensor_record(embedding_name)
            shape = tuple(embedding_record["shape"])
            if len(shape) != 2 or not 0 <= token_id < shape[0]:
                raise ProductionRMSNormBuildError(
                    "qualified token is outside the embedding tensor"
                )
            captured, consumer = _capture_row(shape, token_id)
            reader.consume_tensor_payload(embedding_name, consumer)
            weight_payload = bytearray()
            weight_record = reader.consume_tensor_payload(
                weight_name, weight_payload.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise ProductionRMSNormBuildError(
            f"locked checkpoint payload read failed: {exc}"
        ) from exc
    row_payload = bytes(captured)
    weight_bytes = bytes(weight_payload)
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
        raise ProductionRMSNormBuildError(
            "locked checkpoint payloads differ from qualification evidence"
        )
    return row_payload, weight_bytes


def _problem(
    qualification: Mapping[str, Any], capability: ProductionCapability
) -> dict[str, int]:
    output_shape = qualification["output"]["shape"]
    if len(output_shape) != 2 or output_shape[0] != 1:
        raise ProductionRMSNormBuildError("qualification output must be [1,width]")
    width = output_shape[1]
    if qualification["weight"]["shape"] != [width]:
        raise ProductionRMSNormBuildError("qualification RMSNorm width differs")
    if (
        capability.command_abi_minor != RMSNORM_ABI_MINOR
        or capability.vector_engine is None
        or capability.vector_engine.max_rows < 1
        or capability.vector_engine.max_width < width
        or NUMERIC_CONTRACT not in capability.qualified_numeric_contracts
        or "vector_fp32" not in capability.qualified_execution_modes
    ):
        raise ProductionRMSNormBuildError(
            "capability does not qualify the full-width RMSNorm operation"
        )
    return {
        "resident_embedding_base_token": qualification["input"]["token_id"],
        "resident_embedding_rows": 1,
        "row_bytes": width * 2,
        "rows": 1,
        "width": width,
    }


def _hbm_image(
    row_payload: bytes,
    weight_payload: bytes,
    *,
    qualification: Mapping[str, Any],
    capability: ProductionCapability,
) -> tuple[bytes, list[dict[str, Any]]]:
    image = bytearray()
    regions: list[dict[str, Any]] = []
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
                "source": source,
            }
        )
    if len(image) % capability.hbm.burst_bytes:
        image.extend(
            bytes(
                align_up(len(image), capability.hbm.burst_bytes) - len(image)
            )
        )
    return bytes(image), regions


def _sram_plan(
    problem: Mapping[str, int], capability: ProductionCapability
) -> dict[str, Any]:
    specs = (
        ("token_id", 0, "u32", [1], 4),
        ("embedding", 1, "bf16", [1, problem["width"]], problem["row_bytes"]),
        ("rmsnorm_weight", 2, "bf16", [problem["width"]], problem["row_bytes"]),
        ("output", 3, "bf16", [1, problem["width"]], problem["row_bytes"]),
    )
    regions: list[dict[str, Any]] = []
    for region_id, bank, dtype, shape, logical_bytes in specs:
        allocated = align_up(logical_bytes, capability.sram.word_bytes)
        if bank >= capability.sram.banks or allocated > capability.sram.bytes_per_bank:
            raise ProductionRMSNormBuildError(
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
    return {"addressing": "bank_base_plus_byte_offset", "regions": regions}


def _commands(
    *,
    hbm_regions: list[dict[str, Any]],
    sram: Mapping[str, Any],
    problem: Mapping[str, int],
) -> tuple[ProductionCommand, ...]:
    hbm = {region["id"]: region for region in hbm_regions}
    local = {region["id"]: region for region in sram["regions"]}
    return (
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
            size0=problem["rows"],
            size1=problem["width"],
            size2=EPSILON_CODE,
        ),
        ProductionCommand(
            index=3,
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        ),
    )


def _expected_counters(problem: Mapping[str, int]) -> dict[str, int]:
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


def _kernel_ir(
    *,
    model: ProductionModelGraph,
    qualification: Mapping[str, Any],
    lookup_operation_id: str,
    rmsnorm_operation_id: str,
    lookup_output: str,
    rmsnorm_output: str,
    problem: Mapping[str, int],
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
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
                "source_operation_id": lookup_operation_id,
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
                "source_operation_id": rmsnorm_operation_id,
            },
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
    source_operation_ids: tuple[str, str],
) -> dict[str, Any]:
    body = {
        "graph_id": model.graph_id,
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
    source_operation_ids: tuple[str, str],
    problem: Mapping[str, int],
    sram: Mapping[str, Any],
    hbm_regions: list[dict[str, Any]],
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
            "regions": hbm_regions,
        },
        "numeric_contracts": [LOOKUP_CONTRACT, NUMERIC_CONTRACT],
        "problem": dict(problem),
        "program": {
            "command_count": counters["command_count"],
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
            "one authenticated Qwen3-8B token embedding row through layer-0 input RMSNorm",
            "runtime-indexed HBM lookup, explicit banked SRAM placement, and causal vector execution",
            "uncharacterized functional evidence only",
            "not a complete Qwen layer, model, decode, timing, RTL, 130-nm, HBM PHY, performance, or energy result",
        ],
        "command_abi": {
            "major": capability.command_abi_major,
            "minor": capability.command_abi_minor,
        },
        "compiler": {
            "deterministic": True,
            "name": "OpenTallas tensor-accelerator RMSNorm compiler",
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
        qualification = load_rmsnorm_qualification(qualification_path)
    except (
        CheckpointError,
        ProductionModelGraphError,
        ProductionCapabilityError,
        RMSNormQualificationError,
    ) as exc:
        raise ProductionRMSNormBuildError(f"source admission failed: {exc}") from exc
    if qualification["checkpoint_lock_id"] != checkpoint_lock["lock_id"]:
        raise ProductionRMSNormBuildError(
            "qualification and checkpoint lock identities differ"
        )
    embedding_tensor = qualification["input"]["tensor"]
    weight_tensor = qualification["weight"]["tensor"]
    embedding_shape, embedding_hash = _identity_binding(
        model,
        embedding_tensor,
        checkpoint_lock_id=checkpoint_lock["lock_id"],
        rank=2,
    )
    weight_shape, weight_hash = _identity_binding(
        model,
        weight_tensor,
        checkpoint_lock_id=checkpoint_lock["lock_id"],
        rank=1,
    )
    if (
        list(embedding_shape) != qualification["input"]["source_shape"]
        or embedding_hash != qualification["input"]["source_payload_sha256"]
        or list(weight_shape) != qualification["weight"]["shape"]
        or weight_hash != qualification["weight"]["payload_sha256"]
    ):
        raise ProductionRMSNormBuildError(
            "qualification tensors differ from production graph bindings"
        )
    problem = _problem(qualification, capability)
    lookup_id, rmsnorm_id, lookup_output, rmsnorm_output = _source_operations(
        model,
        embedding_tensor=embedding_tensor,
        weight_tensor=weight_tensor,
        width=problem["width"],
    )
    row_payload, weight_payload = _read_locked_sources(
        snapshot, checkpoint_lock, qualification
    )
    if len(row_payload) != problem["row_bytes"] or len(weight_payload) != problem[
        "row_bytes"
    ]:
        raise ProductionRMSNormBuildError("source payload byte counts differ")
    image, hbm_regions = _hbm_image(
        row_payload,
        weight_payload,
        qualification=qualification,
        capability=capability,
    )
    sram = _sram_plan(problem, capability)
    commands = _commands(
        hbm_regions=hbm_regions,
        sram=sram,
        problem=problem,
    )
    if len(commands) > capability.limits["max_commands"]:
        raise ProductionRMSNormBuildError("command count exceeds capability")
    command_payload = encode(commands, abi_minor=capability.command_abi_minor)
    kernel_ir = _kernel_ir(
        model=model,
        qualification=qualification,
        lookup_operation_id=lookup_id,
        rmsnorm_operation_id=rmsnorm_id,
        lookup_output=lookup_output,
        rmsnorm_output=rmsnorm_output,
        problem=problem,
    )
    source_operation_ids = (lookup_id, rmsnorm_id)
    plan = _physical_plan(
        model=model,
        qualification=qualification,
        capability=capability,
        source_operation_ids=source_operation_ids,
        problem=problem,
        sram=sram,
        hbm_regions=hbm_regions,
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
        source_operation_ids=source_operation_ids,
    )
    for directory in ("checks", "ir", "memory", "physical", "program", "request", "source"):
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

    from .production_rmsnorm_checking import check_rmsnorm_candidate

    independent_check = check_rmsnorm_candidate(
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
        "normalized_payload_sha256": qualification["output"][
            "normalized_payload_sha256"
        ],
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


def build_rmsnorm_deployment(
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
        raise ProductionRMSNormBuildError(
            f"checkpoint snapshot does not exist: {snapshot}"
        )
    for label, path in (
        ("checkpoint lock", checkpoint_lock_path),
        ("model graph", model_graph_path),
        ("capability", capability_path),
        ("qualification report", qualification_path),
    ):
        if not path.is_file():
            raise ProductionRMSNormBuildError(f"{label} does not exist: {path}")
    if output.exists():
        raise ProductionRMSNormBuildError(f"output already exists: {output}")
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
    "KERNEL_SCHEMA",
    "MANIFEST_SCHEMA",
    "PHYSICAL_PLAN_PATH",
    "PHYSICAL_PLAN_SCHEMA",
    "ProductionRMSNormBuildError",
    "REQUEST_PATH",
    "REQUEST_SCHEMA",
    "SOURCE_LOCK_SCHEMA",
    "build_rmsnorm_deployment",
]
