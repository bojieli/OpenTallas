from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
from typing import Any

from jsonschema import Draft202012Validator, ValidationError
import pytest
from referencing import Registry, Resource

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.production_command import (
    Opcode,
    command_abi,
    decode,
    disassemble,
    encode,
)
from compiler.tensor_accelerator.production_layer_downstream import (
    ProductionLayerDownstreamBuildError,
    build_layer_downstream_deployment,
)
from compiler.tensor_accelerator.production_layer_downstream_checking import (
    ProductionLayerDownstreamCheckError,
    check_layer_downstream_candidate,
)
from runtime.tensor_accelerator.production_layer_downstream_simulator import (
    ProductionLayerDownstreamSimulationError,
    ProductionLayerDownstreamSimulator,
    publish_layer_downstream_execution_report,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
CHECKPOINT_LOCK = ROOT / "build/qwen3-8b/checkpoint.lock.json"
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v5.json"
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
ATTENTION_EXECUTION = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_attention_execution.json"
)
RETAINED_EXECUTION = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_layer_downstream_execution.json"
)
HAS_REAL_SOURCES = SNAPSHOT.is_dir() and all(
    path.is_file()
    for path in (
        CHECKPOINT_LOCK,
        GRAPH,
        CAPABILITY,
        QUALIFICATION,
        ATTENTION_EXECUTION,
    )
)
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES,
    reason="authentic Qwen downstream sources unavailable",
)

BUILD_ID = "9609e03551b2b4e9509fcd1c6be08dd546dc20aac97289958e70b1d4325ec3a2"
PHYSICAL_PLAN_ID = "4c7ffe6e22945f4fdbf1b0027994886c26b1567eca53aef149a25d607030f853"
CHECK_ID = "357a7df565fa86809215f30cee278145e285103db426c10868980d231107ad27"
KERNEL_IR_ID = "ff09706b8e1540c020c2fa6e4f0b9b6741e89f5ca6f9e3eb71f6b60307909175"
SOURCE_LOCK_ID = "f6c29008c5949850ac0f7420fa3b41458e79f2185ae04903f27aa69787b7479d"
EXPECTATIONS_ID = "89bd42c35507cd6b24a9bee3335757a76a421db77d7d14dc9ef6d75bf13887f7"
HBM_SHA256 = "e42c0dc596d99bdcf9b5fc569a39bdfe8f3eaa7ebc396a43eef9792bbd236081"
PROGRAM_SHA256 = "e41732d89ec5a767a79a4e40cf61e9a97b45ac80336dfcc1fbdaa84edd33ebb2"
REPORT_ID = "783c48f0fd81d174c54ab82ddf3945a7b518d55e33c84707cb02a0337e879db7"
FINAL_HIDDEN_SHA256 = "7c65791e13e3814af26b0114a5437a3ff44e91b5728ca5e1f23f1f2b7929bf7a"


def _build(output: Path) -> dict[str, Any]:
    return build_layer_downstream_deployment(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        attention_execution_path=ATTENTION_EXECUTION,
        output=output,
    )


def _check(root: Path) -> dict[str, Any]:
    return check_layer_downstream_candidate(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        attention_execution_path=ATTENTION_EXECUTION,
        root=root,
    )


@pytest.fixture(scope="module")
def downstream_builds(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path, dict[str, Any]]:
    if not HAS_REAL_SOURCES:
        pytest.skip("authentic Qwen downstream sources unavailable")
    root = tmp_path_factory.mktemp("production-layer-downstream")
    first = root / "first"
    second = root / "second"
    _build(first)
    _build(second)
    report = ProductionLayerDownstreamSimulator.load(first).execute()
    return first, second, report


def _tree_identity(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _hardlink_clone(source: Path, destination: Path) -> Path:
    return shutil.copytree(source, destination, copy_function=os.link)


def _break_link(path: Path) -> None:
    payload = path.read_bytes()
    path.unlink()
    path.write_bytes(payload)


def _reidentify(path: Path, field: str) -> dict[str, Any]:
    value = load_strict_json(path)
    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()
    write_canonical_json(path, value)
    return value


def _replace_commands(root: Path, commands: tuple[Any, ...]) -> None:
    reindexed = tuple(
        replace(command, index=index) for index, command in enumerate(commands)
    )
    binary = root / "program/commands.bin"
    assembly = root / "program/commands.disasm"
    _break_link(binary)
    _break_link(assembly)
    binary.write_bytes(encode(reindexed, abi_minor=4))
    assembly.write_text(
        disassemble(reindexed, abi_minor=4),
        encoding="utf-8",
        newline="\n",
    )


@REAL
def test_downstream_build_is_deterministic_checked_and_causally_exact(
    downstream_builds: tuple[Path, Path, dict[str, Any]],
) -> None:
    first, second, report = downstream_builds
    assert _tree_identity(first) == _tree_identity(second)
    manifest = load_strict_json(first / "deployment_manifest.json")
    plan = load_strict_json(first / "physical/physical_plan.json")
    check = load_strict_json(first / "checks/independent_check.json")
    kernel = load_strict_json(first / "ir/tensor_kernel_ir.json")
    source_lock = load_strict_json(first / "source.lock.json")
    expectations = load_strict_json(first / "execution_expectations.json")

    assert manifest["build_id"] == BUILD_ID
    assert plan["physical_plan_id"] == PHYSICAL_PLAN_ID
    assert check["check_id"] == CHECK_ID
    assert kernel["kernel_ir_id"] == KERNEL_IR_ID
    assert source_lock["source_lock_id"] == SOURCE_LOCK_ID
    assert expectations["expectations_id"] == EXPECTATIONS_ID
    assert plan["hbm"]["image"] == {
        "base_address": 0,
        "path": "memory/hbm_layer_downstream.bin",
        "sha256": HBM_SHA256,
        "size_bytes": 335_568_896,
    }
    assert plan["program"]["sha256"] == PROGRAM_SHA256
    assert check == _check(first)
    assert [record["kind"] for record in kernel["kernels"]] == [
        "MATMUL",
        "ADD",
        "RMS_NORM",
        "MATMUL",
        "MATMUL",
        "SILU_MUL",
        "MATMUL",
        "ADD",
    ]
    serialized_kernel = json.dumps(kernel).lower()
    assert "address" not in serialized_kernel
    assert "sram" not in serialized_kernel

    commands = decode((first / "program/commands.bin").read_bytes())
    assert command_abi((first / "program/commands.bin").read_bytes()) == (2, 4)
    assert Counter(command.opcode for command in commands) == {
        Opcode.DMA_HBM_TO_SRAM: 10_243,
        Opcode.MATMUL_BF16_TILE: 10_240,
        Opcode.ADD_BF16: 2,
        Opcode.RMSNORM_BF16: 1,
        Opcode.SILU_MUL_BF16: 1,
        Opcode.COMPLETE: 1,
    }
    assert len(commands) == 20_488

    assert report["report_id"] == REPORT_ID
    assert report["status"] == "pass"
    assert report["counter_reconciliation"] == "exact"
    assert report["counters"] == check["expected_counters"]
    assert report["output"]["hidden_1"]["payload_sha256"] == FINAL_HIDDEN_SHA256
    assert len(report["output"]["hidden_1"]["codes"]) == 4096
    assert len(report["trace"]) == 20_488
    assert all(
        count == 0
        for category in report["saturated_element_count"].values()
        for count in category.values()
    )
    assert report["timing"] == {
        "reason": "capability_uncharacterized",
        "status": "unavailable",
    }
    assert ProductionLayerDownstreamSimulator.load(second).execute() == report
    if RETAINED_EXECUTION.is_file():
        assert load_strict_json(RETAINED_EXECUTION) == report


@REAL
def test_downstream_real_artifacts_validate_against_strict_schemas(
    downstream_builds: tuple[Path, Path, dict[str, Any]],
) -> None:
    deployment, _, report = downstream_builds
    schema_root = ROOT / "schemas/compiler/tensor_accelerator"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in schema_root.glob("*.schema.json")
    }
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    instances = {
        "layer_downstream_source_lock_v1.schema.json": load_strict_json(
            deployment / "source.lock.json"
        ),
        "layer_downstream_physical_plan_v1.schema.json": load_strict_json(
            deployment / "physical/physical_plan.json"
        ),
        "layer_downstream_request_v1.schema.json": load_strict_json(
            deployment / "request/execution_request.json"
        ),
        "layer_downstream_expectations_v1.schema.json": load_strict_json(
            deployment / "execution_expectations.json"
        ),
        "layer_downstream_independent_check_v1.schema.json": load_strict_json(
            deployment / "checks/independent_check.json"
        ),
        "layer_downstream_deployment_v1.schema.json": load_strict_json(
            deployment / "deployment_manifest.json"
        ),
        "layer_downstream_execution_v1.schema.json": report,
    }
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)

    forged = json.loads(
        json.dumps(instances["layer_downstream_execution_v1.schema.json"])
    )
    forged["output"]["hidden_1"]["host_fallback"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(
            schemas["layer_downstream_execution_v1.schema.json"],
            registry=registry,
        ).validate(forged)


@REAL
@pytest.mark.parametrize("mutation", ["missing_vector", "reordered_tile"])
def test_inverse_checker_rejects_missing_or_reordered_commands(
    downstream_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
    mutation: str,
) -> None:
    source = downstream_builds[0]
    candidate = _hardlink_clone(source, tmp_path / mutation)
    commands = list(decode((candidate / "program/commands.bin").read_bytes()))
    if mutation == "missing_vector":
        del commands[
            next(
                index
                for index, command in enumerate(commands)
                if command.opcode == Opcode.ADD_BF16
            )
        ]
    else:
        first_matrix = next(
            index
            for index, command in enumerate(commands)
            if command.opcode == Opcode.MATMUL_BF16_TILE
        )
        commands[first_matrix - 1], commands[first_matrix] = (
            commands[first_matrix],
            commands[first_matrix - 1],
        )
    _replace_commands(candidate, tuple(commands))
    with pytest.raises(
        ProductionLayerDownstreamCheckError,
        match="command program differs",
    ):
        _check(candidate)
    with pytest.raises(ProductionLayerDownstreamSimulationError):
        ProductionLayerDownstreamSimulator.load(candidate)


@REAL
def test_inverse_checker_rejects_rehashed_hbm_and_sram_corruption(
    downstream_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    source = downstream_builds[0]
    hbm_candidate = _hardlink_clone(source, tmp_path / "hbm-corrupt")
    hbm_path = hbm_candidate / "memory/hbm_layer_downstream.bin"
    hbm_path.unlink()
    shutil.copy2(source / "memory/hbm_layer_downstream.bin", hbm_path)
    plan_path = hbm_candidate / "physical/physical_plan.json"
    _break_link(plan_path)
    plan = load_strict_json(plan_path)
    tile = plan["hbm"]["projections"][0]["tiles"][0]
    with hbm_path.open("r+b") as handle:
        handle.seek(tile["offset_bytes"])
        original = handle.read(1)
        handle.seek(tile["offset_bytes"])
        handle.write(bytes([original[0] ^ 1]))
    image = hbm_path.read_bytes()
    start = tile["offset_bytes"]
    end = start + tile["size_bytes"]
    tile["payload_sha256"] = hashlib.sha256(image[start:end]).hexdigest()
    plan["hbm"]["image"]["sha256"] = hashlib.sha256(image).hexdigest()
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    with pytest.raises(
        ProductionLayerDownstreamCheckError,
        match="HBM image differs",
    ):
        _check(hbm_candidate)

    sram_candidate = _hardlink_clone(source, tmp_path / "sram-corrupt")
    sram_plan_path = sram_candidate / "physical/physical_plan.json"
    _break_link(sram_plan_path)
    sram_plan = load_strict_json(sram_plan_path)
    sram_plan["sram"]["regions"][12]["address"] += 16
    write_canonical_json(sram_plan_path, sram_plan)
    _reidentify(sram_plan_path, "physical_plan_id")
    with pytest.raises(
        ProductionLayerDownstreamCheckError,
        match="physical plan differs",
    ):
        _check(sram_candidate)


@REAL
def test_downstream_dependencies_are_independent_and_publication_is_atomic(
    downstream_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    deployment, _, report = downstream_builds
    import compiler.tensor_accelerator.production_layer_downstream_checking as checker
    import runtime.tensor_accelerator.production_layer_downstream_simulator as simulator

    checker_source = inspect.getsource(checker)
    simulator_source = inspect.getsource(simulator)
    assert "from .production_layer_downstream import" not in checker_source
    assert "production_layer_downstream_checking" not in simulator_source
    assert "layer_qualification" not in simulator_source
    assert "runtime.reference" not in simulator_source
    assert "transformers" not in simulator_source
    assert "torch" not in simulator_source

    with pytest.raises(ProductionLayerDownstreamBuildError, match="already exists"):
        _build(deployment)
    output = tmp_path / "execution.json"
    publish_layer_downstream_execution_report(report, output)
    assert load_strict_json(output) == report
    with pytest.raises(
        ProductionLayerDownstreamSimulationError,
        match="already exists",
    ):
        publish_layer_downstream_execution_report(report, output)
