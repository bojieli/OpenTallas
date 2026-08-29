from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil
from typing import Any

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.frontend.checkpoint import load_checkpoint_lock
from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.production_capability import (
    load_production_capability,
)
from compiler.tensor_accelerator.production_command import (
    ABI_MAJOR,
    SELECTION_ABI_MINOR,
    encode,
)
from compiler.tensor_accelerator.production_model import load_production_model_graph
from compiler.tensor_accelerator.qwen_full_model_physical import (
    CLAIM_BOUNDARY,
    COMPILER_VERSION,
    MANIFEST_SCHEMA,
    QwenFullModelPhysicalError,
    _capacity_certificate,
    _commands,
    _physical_layout,
    _physical_plan,
    _request,
    _source_lock,
    _sram_plan,
    build_qwen_full_model_physical_deployment,
)
from compiler.tensor_accelerator.qwen_full_model_physical_checking import (
    CHECKER_VERSION,
    CHECK_SCHEMA,
    COMMAND_PATH,
    QwenFullModelPhysicalCheckError,
    _derive_hbm,
    _derive_sram,
    _verify_command_program,
    check_qwen_full_model_physical_deployment,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v6.json"
SEMANTICS = ROOT / "results/tensor_accelerator/qwen3_full_model_semantics"
COVERAGE = SEMANTICS / "coverage.json"
KERNEL_IR = SEMANTICS / "tensor_kernel_ir.json"
SEMANTIC_CHECK = SEMANTICS / "independent_check.json"
CHECKPOINT_LOCK = Path("/home/ubuntu/OpenTallas/build/qwen3-8b/checkpoint.lock.json")
SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/"
    "snapshots/b968826d9c46dd6066d109eabc6255188de91218"
)
SCHEMAS = ROOT / "schemas/compiler/tensor_accelerator"
AUTHENTIC_ENV = "OPENTALLAS_RUN_QWEN_FULL_MODEL_PHYSICAL"

HAS_LAYOUT_SOURCES = all(
    path.is_file()
    for path in (
        GRAPH,
        CAPABILITY,
        COVERAGE,
        KERNEL_IR,
        SEMANTIC_CHECK,
        CHECKPOINT_LOCK,
    )
)
LAYOUT = pytest.mark.skipif(
    not HAS_LAYOUT_SOURCES,
    reason="authentic Qwen graph/checkpoint metadata are unavailable",
)
RUN_AUTHENTIC = os.environ.get(AUTHENTIC_ENV) == "1"
AUTHENTIC = pytest.mark.skipif(
    not RUN_AUTHENTIC or not HAS_LAYOUT_SOURCES or not SNAPSHOT.is_dir(),
    reason=f"set {AUTHENTIC_ENV}=1 with the pinned Qwen snapshot available",
)


def _source_paths() -> dict[str, Path]:
    return {
        "capability": CAPABILITY,
        "checkpoint_lock": CHECKPOINT_LOCK,
        "model_graph": GRAPH,
        "semantic_check": SEMANTIC_CHECK,
        "semantic_coverage": COVERAGE,
        "semantic_kernel_ir": KERNEL_IR,
    }


def _fake_image(total_size: int) -> dict[str, Any]:
    shard_bytes = 1 << 30
    remaining = total_size
    offset = 0
    records: list[dict[str, Any]] = []
    for index in range((total_size + shard_bytes - 1) // shard_bytes):
        size = min(shard_bytes, remaining)
        digest = f"{index:064x}"
        records.append(
            {
                "index": index,
                "logical_offset": offset,
                "path": f"memory/hbm/hbm.{index:05d}.{digest}.bin",
                "sha256": digest,
                "size_bytes": size,
            }
        )
        remaining -= size
        offset += size
    return {
        "logical_sha256": "f" * 64,
        "shard_bytes": shard_bytes,
        "shards": records,
        "size_bytes": total_size,
    }


def _physical_check_fixture(
    *,
    capability_id: str,
    capacity_id: str,
    graph_id: str,
    physical_plan_id: str,
    source_lock_id: str,
) -> dict[str, Any]:
    body = {
        "capability_id": capability_id,
        "capacity_certificate_id": capacity_id,
        "checker_version": CHECKER_VERSION,
        "checks": {
            "canonical_and_exact_file_set": True,
            "capacity_and_no_host_paging": True,
            "checkpoint_payload_reconstruction": True,
            "command_and_kernel_range_derivation": True,
            "complete_graph_and_semantic_binding": True,
            "hbm_region_and_shard_integrity": True,
            "independent_inverse_reconstruction": True,
            "rope_and_state_table_payloads": True,
            "source_lock_and_immutable_copies": True,
            "sram_bank_capacity_and_liveness": True,
            "terminal_36_resource_atomic_commit": True,
            "zero_initialized_transactional_state": True,
        },
        "command_count": 924386,
        "graph_id": graph_id,
        "hbm_logical_sha256": "f" * 64,
        "operation_count": 617,
        "physical_plan_id": physical_plan_id,
        "schema": CHECK_SCHEMA,
        "source_lock_id": source_lock_id,
        "state_resource_count": 36,
        "status": "pass",
        "tensor_count": 1053,
        "weight_count": 399,
    }
    return {**body, "check_id": sha256_bytes(canonical_json_bytes(body))}


@pytest.fixture(scope="module")
def physical_fixture() -> dict[str, Any]:
    if not HAS_LAYOUT_SOURCES:
        pytest.skip("authentic Qwen graph/checkpoint metadata are unavailable")
    model = load_production_model_graph(GRAPH)
    capability = load_production_capability(CAPABILITY)
    checkpoint_lock = load_checkpoint_lock(CHECKPOINT_LOCK)
    coverage = load_strict_json(COVERAGE)
    kernel_ir = load_strict_json(KERNEL_IR)
    semantic_check = load_strict_json(SEMANTIC_CHECK)

    forward_hbm = _physical_layout(model, capability, checkpoint_lock)
    inverse_hbm = _derive_hbm(model, capability, checkpoint_lock)
    assert forward_hbm == inverse_hbm
    for weight in forward_hbm["weights"]:
        weight["deployed_payload_sha256"] = "0" * 64
    forward_hbm["metadata_table"]["payload_sha256"] = "1" * 64
    forward_hbm["descriptor_table"]["payload_sha256"] = "2" * 64
    forward_hbm["image"] = _fake_image(forward_hbm["total_size_bytes"])

    forward_sram = _sram_plan(model, capability)
    inverse_sram = _derive_sram(model, capability)
    assert forward_sram == inverse_sram
    commands, ranges, counts = _commands(
        model=model, hbm=forward_hbm, sram=forward_sram
    )
    command_payload = encode(commands, abi_minor=SELECTION_ABI_MINOR)
    command_program = {
        "abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
        "command_count": len(commands),
        "kernel_command_ranges": ranges,
        "opcode_counts": counts,
        "path": COMMAND_PATH,
        "sha256": hashlib.sha256(command_payload).hexdigest(),
        "size_bytes": len(command_payload),
    }
    _verify_command_program(
        model=model,
        hbm=forward_hbm,
        sram=forward_sram,
        payload=command_payload,
        candidate_program=command_program,
    )

    source_lock = _source_lock(
        model=model,
        capability=capability,
        checkpoint_lock=checkpoint_lock,
        coverage=coverage,
        kernel_ir=kernel_ir,
        semantic_check=semantic_check,
        source_paths=_source_paths(),
    )
    capacity = _capacity_certificate(
        capability=capability,
        hbm=forward_hbm,
        sram=forward_sram,
        command_count=len(commands),
    )
    physical_plan = _physical_plan(
        model=model,
        capability=capability,
        source_lock=source_lock,
        semantic_kernel_ir=kernel_ir,
        hbm=forward_hbm,
        sram=forward_sram,
        command_payload=command_payload,
        command_ranges=ranges,
        opcode_counts=counts,
        capacity=capacity,
    )
    check = _physical_check_fixture(
        capability_id=capability.capability_id,
        capacity_id=capacity["capacity_certificate_id"],
        graph_id=model.graph_id,
        physical_plan_id=physical_plan["physical_plan_id"],
        source_lock_id=source_lock["source_lock_id"],
    )
    roles = [
        "capability",
        "capacity_certificate",
        "command_program",
        "execution_request",
        "independent_check",
        "physical_plan",
        "source_lock",
        "tensor_kernel_ir",
        *[f"source_{role}" for role in sorted(_source_paths())],
        *(["hbm_shard"] * 17),
    ]
    artifacts = [
        {
            "path": f"artifact/{index:02d}.bin",
            "role": role,
            "sha256": f"{index:064x}",
            "size_bytes": 1,
        }
        for index, role in enumerate(roles)
    ]
    manifest_body = {
        "artifacts": artifacts,
        "build_class": "independently_reconstructed_physical_deployment",
        "capability_id": capability.capability_id,
        "capacity_certificate_id": capacity["capacity_certificate_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "command_abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
        "compiler_version": COMPILER_VERSION,
        "graph_id": model.graph_id,
        "independent_check_id": check["check_id"],
        "kernel_ir_id": kernel_ir["kernel_ir_id"],
        "physical_plan_id": physical_plan["physical_plan_id"],
        "schema": MANIFEST_SCHEMA,
        "source_lock_id": source_lock["source_lock_id"],
    }
    manifest = {
        **manifest_body,
        "build_id": sha256_bytes(canonical_json_bytes(manifest_body)),
    }
    samples = {
        "first": commands[0].to_dict(),
        "last": commands[-1].to_dict(),
        "state_commit": commands[-2].to_dict(),
    }
    return {
        "capacity": capacity,
        "check": check,
        "commands": commands,
        "command_payload": command_payload,
        "command_program": command_program,
        "hbm": forward_hbm,
        "manifest": manifest,
        "physical_plan": physical_plan,
        "request": _request(model),
        "samples": samples,
        "source_lock": source_lock,
        "sram": forward_sram,
    }


@LAYOUT
def test_complete_physical_layout_is_exact_and_within_capacity(
    physical_fixture: dict[str, Any],
) -> None:
    hbm = physical_fixture["hbm"]
    sram = physical_fixture["sram"]
    capacity = physical_fixture["capacity"]
    assert len(hbm["weights"]) == 399
    assert len(hbm["states"]) == 36
    assert hbm["immutable_weight_bytes"] == 16_381_470_720
    assert hbm["mutable_kv_bytes"] == 1_179_648_000
    assert hbm["total_size_bytes"] == 17_573_089_792
    assert len(hbm["image"]["shards"]) == 17
    assert len(sram["slots"]) == 18
    assert len(sram["tensor_assignments"]) == 617
    assert len(sram["state_handle_assignments"]) == 36
    assert len(sram["staged_weight_assignments"]) == 145
    assert len(sram["workspace_assignments"]) == 542
    assert capacity["no_host_paging"] is True
    assert capacity["hbm_capacity"]["margin_bytes"] == 257_304_817_152
    assert capacity["command_capacity"]["margin"] == 15_852_830
    assert capacity["sram_capacity"]["max_bank_allocated_bytes"] == 303_872

    for weight in hbm["weights"]:
        unit = weight["access_unit_bytes"]
        assert weight["offset_bytes"] % unit == 0
        assert weight["size_bytes"] % unit == 0
        assert (1 << 30) % unit == 0


@LAYOUT
def test_complete_command_program_is_independently_derived_and_bound(
    physical_fixture: dict[str, Any],
) -> None:
    program = physical_fixture["command_program"]
    assert program["command_count"] == 924_386
    assert program["size_bytes"] == 59_160_736
    assert len(program["kernel_command_ranges"]) == 617
    assert program["opcode_counts"] == {
        "ADD_BF16": 72,
        "COMPLETE": 1,
        "DMA_HBM_INDEXED_TO_SRAM": 37,
        "DMA_HBM_TO_SRAM": 462_065,
        "DMA_SRAM_INDEXED_TO_SRAM": 1,
        "GQA_ATTENTION_BF16": 36,
        "KV_PREPARE_BF16": 36,
        "MATMUL_BF16_TILE": 461_920,
        "RMSNORM_BF16": 145,
        "ROPE_BF16": 36,
        "SILU_MUL_BF16": 36,
        "STATE_COMMIT": 1,
    }
    assert physical_fixture["samples"]["first"]["opcode"] == ("DMA_HBM_INDEXED_TO_SRAM")
    assert physical_fixture["samples"]["state_commit"]["opcode"] == "STATE_COMMIT"
    assert physical_fixture["samples"]["state_commit"]["size1"] == 36
    assert physical_fixture["samples"]["last"]["opcode"] == "COMPLETE"

    corrupted = bytearray(physical_fixture["command_payload"])
    corrupted[-1] ^= 1
    with pytest.raises(QwenFullModelPhysicalCheckError, match="command program"):
        model = load_production_model_graph(GRAPH)
        _verify_command_program(
            model=model,
            hbm=physical_fixture["hbm"],
            sram=physical_fixture["sram"],
            payload=bytes(corrupted),
            candidate_program=program,
        )

    commands = physical_fixture["commands"]
    add_position = program["kernel_command_ranges"][11]["command_start"]
    reordered = list(commands)
    reordered[add_position] = replace(commands[-2], index=add_position)
    reordered[-2] = replace(commands[add_position], index=len(commands) - 2)
    reordered_payload = encode(reordered, abi_minor=SELECTION_ABI_MINOR)
    reordered_program = copy.deepcopy(program)
    reordered_program["sha256"] = hashlib.sha256(reordered_payload).hexdigest()
    with pytest.raises(
        QwenFullModelPhysicalCheckError, match=f"command {add_position}"
    ):
        _verify_command_program(
            model=load_production_model_graph(GRAPH),
            hbm=physical_fixture["hbm"],
            sram=physical_fixture["sram"],
            payload=reordered_payload,
            candidate_program=reordered_program,
        )


@LAYOUT
def test_complete_physical_artifacts_validate_strict_schemas(
    physical_fixture: dict[str, Any],
) -> None:
    cases = {
        "qwen_full_model_capacity_v1.schema.json": physical_fixture["capacity"],
        "qwen_full_model_deployment_v1.schema.json": physical_fixture["manifest"],
        "qwen_full_model_physical_check_v1.schema.json": physical_fixture["check"],
        "qwen_full_model_physical_plan_v1.schema.json": physical_fixture[
            "physical_plan"
        ],
        "qwen_full_model_request_v1.schema.json": physical_fixture["request"],
        "qwen_full_model_source_lock_v1.schema.json": physical_fixture["source_lock"],
    }
    for name, value in cases.items():
        schema = load_strict_json(SCHEMAS / name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)

    forged = copy.deepcopy(physical_fixture["physical_plan"])
    forged["claim_boundary"]["full_model_execution"] = True
    schema = load_strict_json(SCHEMAS / "qwen_full_model_physical_plan_v1.schema.json")
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(forged)

    stale_request = copy.deepcopy(physical_fixture["request"])
    stale_request["expected_generations"][0] = 1
    request_schema = load_strict_json(
        SCHEMAS / "qwen_full_model_request_v1.schema.json"
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(request_schema).validate(stale_request)


def test_full_model_physical_checker_does_not_import_the_generator() -> None:
    source = (
        ROOT / "compiler/tensor_accelerator/qwen_full_model_physical_checking.py"
    ).read_text(encoding="utf-8")
    assert "from .qwen_full_model_physical import" not in source
    assert "import qwen_full_model_physical" not in source


@LAYOUT
def test_complete_physical_builder_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(QwenFullModelPhysicalError, match="already exists"):
        build_qwen_full_model_physical_deployment(
            snapshot=SNAPSHOT if SNAPSHOT.is_dir() else ROOT,
            checkpoint_lock_path=CHECKPOINT_LOCK,
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            semantic_coverage_path=COVERAGE,
            semantic_kernel_ir_path=KERNEL_IR,
            semantic_check_path=SEMANTIC_CHECK,
            output=output,
        )


def _deployment_fingerprint(
    root: Path,
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    ordinary = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "memory/hbm/" not in path.relative_to(root).as_posix()
    }
    plan = load_strict_json(root / "physical/physical_plan.json")
    return ordinary, plan["hbm"]["image"]["shards"]


@AUTHENTIC
def test_two_authentic_complete_physical_builds_are_byte_identical(
    tmp_path: Path,
) -> None:
    arguments = {
        "snapshot": SNAPSHOT,
        "checkpoint_lock_path": CHECKPOINT_LOCK,
        "model_graph_path": GRAPH,
        "capability_path": CAPABILITY,
        "semantic_coverage_path": COVERAGE,
        "semantic_kernel_ir_path": KERNEL_IR,
        "semantic_check_path": SEMANTIC_CHECK,
    }
    first = tmp_path / "first"
    first_manifest = build_qwen_full_model_physical_deployment(
        output=first, **arguments
    )
    first_files, first_shards = _deployment_fingerprint(first)
    shutil.rmtree(first)

    second = tmp_path / "second"
    second_manifest = build_qwen_full_model_physical_deployment(
        output=second, **arguments
    )
    second_files, second_shards = _deployment_fingerprint(second)
    assert first_manifest == second_manifest
    assert first_files == second_files
    assert first_shards == second_shards
    assert second_manifest["claim_boundary"]["full_model_execution"] is False
    assert load_strict_json(second / "checks/independent_check.json")["status"] == (
        "pass"
    )
    rechecked = check_qwen_full_model_physical_deployment(
        root=second,
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        semantic_coverage_path=COVERAGE,
        semantic_kernel_ir_path=KERNEL_IR,
        semantic_check_path=SEMANTIC_CHECK,
    )
    assert rechecked == load_strict_json(second / "checks/independent_check.json")
