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
from compiler.tensor_accelerator.production_connected_layer import (
    ProductionConnectedLayerBuildError,
    build_connected_layer_deployment,
)
from compiler.tensor_accelerator.production_connected_layer_checking import (
    ProductionConnectedLayerCheckError,
    check_connected_layer_candidate,
)
from runtime.tensor_accelerator.production_connected_layer_simulator import (
    ProductionConnectedLayerSimulationError,
    ProductionConnectedLayerSimulator,
    publish_connected_layer_execution_report,
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
QKV_QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"
QKV_EXECUTION = ROOT / "results/tensor_accelerator/qwen3_hbm_sram_qkv_execution.json"
ATTENTION_QUALIFICATION = (
    ROOT / "results/tensor_accelerator/qwen3_attention_qualification.json"
)
ATTENTION_EXECUTION = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_attention_execution.json"
)
DOWNSTREAM_QUALIFICATION = (
    ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
)
DOWNSTREAM_EXECUTION = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_layer_downstream_execution.json"
)
RETAINED_EXECUTION = (
    ROOT / "results/tensor_accelerator/qwen3_hbm_sram_connected_layer_execution.json"
)
SOURCE_PATHS = (
    CHECKPOINT_LOCK,
    GRAPH,
    CAPABILITY,
    QKV_QUALIFICATION,
    QKV_EXECUTION,
    ATTENTION_QUALIFICATION,
    ATTENTION_EXECUTION,
    DOWNSTREAM_QUALIFICATION,
    DOWNSTREAM_EXECUTION,
)
HAS_REAL_SOURCES = SNAPSHOT.is_dir() and all(path.is_file() for path in SOURCE_PATHS)
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES,
    reason="authentic connected Qwen-layer sources unavailable",
)

BUILD_ID = "80f3698dfedd2852ee2800be2d5cb1397dd2100d755c52fd30e0e6c2d17cd01e"
PHYSICAL_PLAN_ID = "4b58c336aa79b9d9d863b1470f498e1ae1a64620743e23e417b085106810379c"
CHECK_ID = "7304eb5b8777fe0631e567102549cc5f9a902b1feaa23d5fee382590ceb1ebfc"
KERNEL_IR_ID = "4c3723a04ec8ce213267f8c005b10d50bf6300c4c98321846b7082ea9f7dbef1"
SOURCE_LOCK_ID = "f1f6d7b3fc7d7e8cfa9bf2e925d7f3ae00460ca6e9bdcab51fe81edf43216ce6"
EXPECTATIONS_ID = "09fab39f148c8e1c01f654d24f342b15ba607394669ae0c3cc146a0e6c964a7c"
HBM_SHA256 = "b3ef0d7d81fc9b78122c56c57e2a6ec7499d83d742aec3960ee40eb2c09deb23"
PROGRAM_SHA256 = "ab2318259cfdc669d6050423cf8da9643baa5d012b50816ede06bb2cad28114a"
REPORT_ID = "86453b0822f2fd5f045da0fea67f51361e16999c263ded30b1ad497d7f50cca2"
FINAL_HIDDEN_SHA256 = "7c65791e13e3814af26b0114a5437a3ff44e91b5728ca5e1f23f1f2b7929bf7a"
STATE_SHA256 = "c446dd569837a2acf3f6a2333799794caaf0a7ae2919f42edecfcd6f7fd6bc56"


def _build(output: Path) -> dict[str, Any]:
    return build_connected_layer_deployment(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qkv_qualification_path=QKV_QUALIFICATION,
        qkv_execution_path=QKV_EXECUTION,
        attention_qualification_path=ATTENTION_QUALIFICATION,
        attention_execution_path=ATTENTION_EXECUTION,
        downstream_qualification_path=DOWNSTREAM_QUALIFICATION,
        downstream_execution_path=DOWNSTREAM_EXECUTION,
        output=output,
    )


def _check(root: Path) -> dict[str, Any]:
    return check_connected_layer_candidate(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=CHECKPOINT_LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qkv_qualification_path=QKV_QUALIFICATION,
        qkv_execution_path=QKV_EXECUTION,
        attention_qualification_path=ATTENTION_QUALIFICATION,
        attention_execution_path=ATTENTION_EXECUTION,
        downstream_qualification_path=DOWNSTREAM_QUALIFICATION,
        downstream_execution_path=DOWNSTREAM_EXECUTION,
        root=root,
    )


@pytest.fixture(scope="module")
def connected_builds(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path, dict[str, Any]]:
    if not HAS_REAL_SOURCES:
        pytest.skip("authentic connected Qwen-layer sources unavailable")
    root = tmp_path_factory.mktemp("production-connected-layer")
    first = root / "first"
    second = root / "second"
    _build(first)
    _build(second)
    report = ProductionConnectedLayerSimulator.load(first).execute()
    return first, second, report


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _tree_identity(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, _file_sha256(path))
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _hardlink_clone(source: Path, destination: Path) -> Path:
    return shutil.copytree(source, destination, copy_function=os.link)


def _break_link(path: Path) -> None:
    payload = path.read_bytes()
    path.unlink()
    path.write_bytes(payload)


def _break_large_link(path: Path) -> None:
    temporary = path.with_name(f".{path.name}.copy")
    shutil.copyfile(path, temporary)
    path.unlink()
    os.replace(temporary, path)


def _reidentify(path: Path, field: str) -> dict[str, Any]:
    value = load_strict_json(path)
    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()
    write_canonical_json(path, value)
    return value


def _refresh_manifest(root: Path) -> dict[str, Any]:
    path = root / "deployment_manifest.json"
    _break_link(path)
    value = load_strict_json(path)
    value["physical_plan_id"] = load_strict_json(root / "physical/physical_plan.json")[
        "physical_plan_id"
    ]
    value["independent_check_id"] = load_strict_json(
        root / "checks/independent_check.json"
    )["check_id"]
    value["kernel_ir_id"] = load_strict_json(root / "ir/tensor_kernel_ir.json")[
        "kernel_ir_id"
    ]
    value["source_lock_id"] = load_strict_json(root / "source.lock.json")[
        "source_lock_id"
    ]
    for record in value["artifacts"]:
        artifact = root / record["path"]
        record["size_bytes"] = artifact.stat().st_size
        record["sha256"] = _file_sha256(artifact)
    write_canonical_json(path, value)
    return _reidentify(path, "build_id")


def _replace_commands(root: Path, commands: tuple[Any, ...]) -> None:
    parsed = tuple(
        replace(command, index=index) for index, command in enumerate(commands)
    )
    binary = root / "program/commands.bin"
    assembly = root / "program/commands.disasm"
    _break_link(binary)
    _break_link(assembly)
    payload = encode(parsed, abi_minor=4)
    binary.write_bytes(payload)
    assembly.write_text(
        disassemble(parsed, abi_minor=4), encoding="utf-8", newline="\n"
    )
    plan_path = root / "physical/physical_plan.json"
    _break_link(plan_path)
    plan = load_strict_json(plan_path)
    plan["program"] = {
        "command_count": len(parsed),
        "path": "program/commands.bin",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(root)


def _all_counts(value: object) -> list[int]:
    if isinstance(value, dict):
        result: list[int] = []
        for child in value.values():
            result.extend(_all_counts(child))
        return result
    return [int(value)]


@REAL
def test_connected_build_is_deterministic_independent_and_causally_exact(
    connected_builds: tuple[Path, Path, dict[str, Any]],
) -> None:
    first, second, report = connected_builds
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
        "path": "memory/hbm_connected_layer.bin",
        "sha256": HBM_SHA256,
        "size_bytes": 422_765_184,
    }
    assert plan["program"]["sha256"] == PROGRAM_SHA256
    assert check == _check(first)
    assert len(kernel["kernels"]) == 19
    assert [record["source_operation_id"] for record in kernel["kernels"]] == [
        *(f"node.{index:04d}" for index in range(18)),
        "state.commit",
    ]
    serialized_kernel = json.dumps(kernel).lower()
    assert "address" not in serialized_kernel
    assert "sram" not in serialized_kernel
    assert "opcode" not in serialized_kernel

    commands = decode((first / "program/commands.bin").read_bytes())
    assert command_abi((first / "program/commands.bin").read_bytes()) == (2, 4)
    assert Counter(command.opcode for command in commands) == {
        Opcode.DMA_HBM_TO_SRAM: 11_780,
        Opcode.DMA_HBM_INDEXED_TO_SRAM: 2,
        Opcode.MATMUL_BF16_TILE: 11_776,
        Opcode.RMSNORM_BF16: 4,
        Opcode.ROPE_BF16: 1,
        Opcode.KV_PREPARE_BF16: 1,
        Opcode.GQA_ATTENTION_BF16: 1,
        Opcode.ADD_BF16: 2,
        Opcode.SILU_MUL_BF16: 1,
        Opcode.STATE_COMMIT: 1,
        Opcode.COMPLETE: 1,
    }
    assert len(commands) == 23_570

    assert report["report_id"] == REPORT_ID
    assert report["counter_reconciliation"] == "exact"
    assert report["counters"] == check["expected_counters"]
    assert report["output"]["hidden_1"]["payload_sha256"] == FINAL_HIDDEN_SHA256
    assert report["state"]["state_sha256"] == STATE_SHA256
    assert len(report["output"]["hidden_1"]["codes"]) == 4096
    assert len(report["trace"]) == 23_570
    assert all(count == 0 for count in _all_counts(report["saturated_element_count"]))
    assert report["timing"] == {
        "reason": "capability_uncharacterized",
        "status": "unavailable",
    }
    assert ProductionConnectedLayerSimulator.load(second).execute() == report
    if RETAINED_EXECUTION.is_file():
        assert load_strict_json(RETAINED_EXECUTION) == report


@REAL
def test_connected_artifacts_validate_against_strict_schemas(
    connected_builds: tuple[Path, Path, dict[str, Any]],
) -> None:
    deployment, _, report = connected_builds
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
        "connected_layer_source_lock_v1.schema.json": load_strict_json(
            deployment / "source.lock.json"
        ),
        "connected_layer_physical_plan_v1.schema.json": load_strict_json(
            deployment / "physical/physical_plan.json"
        ),
        "connected_layer_request_v1.schema.json": load_strict_json(
            deployment / "request/execution_request.json"
        ),
        "connected_layer_expectations_v1.schema.json": load_strict_json(
            deployment / "execution_expectations.json"
        ),
        "connected_layer_independent_check_v1.schema.json": load_strict_json(
            deployment / "checks/independent_check.json"
        ),
        "connected_layer_deployment_v1.schema.json": load_strict_json(
            deployment / "deployment_manifest.json"
        ),
        "connected_layer_execution_v1.schema.json": report,
    }
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)

    forged = json.loads(json.dumps(report))
    forged["output"]["hidden_1"]["host_fallback"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(
            schemas["connected_layer_execution_v1.schema.json"], registry=registry
        ).validate(forged)


@REAL
def test_connected_layer_has_no_retained_activation_handoff(
    connected_builds: tuple[Path, Path, dict[str, Any]],
) -> None:
    deployment = connected_builds[0]
    plan = load_strict_json(deployment / "physical/physical_plan.json")
    check = load_strict_json(deployment / "checks/independent_check.json")
    region_ids = {record["id"] for record in plan["hbm"]["regions"]}
    retained_activation_roles = {
        "attention",
        "attention_norm",
        "hidden_0_retained",
        "k_rotary",
        "q_rotary",
        "v_retained",
    }
    assert not region_ids & retained_activation_roles
    assert check["no_retained_activation_regions"] is True
    assert plan["source_operation_ids"] == [
        *(f"node.{index:04d}" for index in range(18)),
        "state.commit",
    ]


@REAL
@pytest.mark.parametrize(
    "opcode",
    [
        Opcode.KV_PREPARE_BF16,
        Opcode.GQA_ATTENTION_BF16,
        Opcode.ADD_BF16,
        Opcode.SILU_MUL_BF16,
        Opcode.STATE_COMMIT,
    ],
)
def test_connected_checker_and_simulator_reject_missing_stage_work(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
    opcode: Opcode,
) -> None:
    candidate = _hardlink_clone(connected_builds[0], tmp_path / opcode.name.lower())
    commands = list(decode((candidate / "program/commands.bin").read_bytes()))
    del commands[
        next(
            index for index, command in enumerate(commands) if command.opcode == opcode
        )
    ]
    _replace_commands(candidate, tuple(commands))
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(candidate)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        ProductionConnectedLayerSimulator.load(candidate)


@REAL
def test_connected_checker_and_simulator_reject_reordered_boundaries_and_early_commit(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    source = connected_builds[0]
    reordered = _hardlink_clone(source, tmp_path / "reordered")
    commands = list(decode((reordered / "program/commands.bin").read_bytes()))
    prepare = next(
        index
        for index, command in enumerate(commands)
        if command.opcode == Opcode.KV_PREPARE_BF16
    )
    commands[prepare - 1], commands[prepare] = commands[prepare], commands[prepare - 1]
    _replace_commands(reordered, tuple(commands))
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(reordered)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        ProductionConnectedLayerSimulator.load(reordered)

    early = _hardlink_clone(source, tmp_path / "early-commit")
    commands = list(decode((early / "program/commands.bin").read_bytes()))
    commit = next(
        index
        for index, command in enumerate(commands)
        if command.opcode == Opcode.STATE_COMMIT
    )
    hidden = commit - 1
    commands[hidden], commands[commit] = commands[commit], commands[hidden]
    _replace_commands(early, tuple(commands))
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(early)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        ProductionConnectedLayerSimulator.load(early)


@REAL
def test_connected_simulator_rejects_missing_complete(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    candidate = _hardlink_clone(connected_builds[0], tmp_path / "missing-complete")
    command_path = candidate / "program/commands.bin"
    _break_link(command_path)
    command_path.write_bytes(command_path.read_bytes()[:-64])
    _refresh_manifest(candidate)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        ProductionConnectedLayerSimulator.load(candidate)


@REAL
def test_connected_rejects_rehashed_hbm_and_sram_corruption(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    source = connected_builds[0]
    hbm_candidate = _hardlink_clone(source, tmp_path / "hbm-corrupt")
    hbm_path = hbm_candidate / "memory/hbm_connected_layer.bin"
    _break_large_link(hbm_path)
    plan_path = hbm_candidate / "physical/physical_plan.json"
    _break_link(plan_path)
    plan = load_strict_json(plan_path)
    tile = plan["hbm"]["projections"][0]["tiles"][0]
    with hbm_path.open("r+b") as handle:
        handle.seek(tile["offset_bytes"])
        handle.write(b"\x80\x7f")
    tile_start = tile["offset_bytes"]
    with hbm_path.open("rb") as handle:
        handle.seek(tile_start)
        tile["payload_sha256"] = hashlib.sha256(
            handle.read(tile["size_bytes"])
        ).hexdigest()
    plan["hbm"]["image"]["sha256"] = _file_sha256(hbm_path)
    write_canonical_json(plan_path, plan)
    plan = _reidentify(plan_path, "physical_plan_id")

    check_path = hbm_candidate / "checks/independent_check.json"
    _break_link(check_path)
    check = load_strict_json(check_path)
    check["hbm_image_sha256"] = plan["hbm"]["image"]["sha256"]
    check["physical_plan_id"] = plan["physical_plan_id"]
    write_canonical_json(check_path, check)
    check = _reidentify(check_path, "check_id")
    expectations_path = hbm_candidate / "execution_expectations.json"
    _break_link(expectations_path)
    expectations = load_strict_json(expectations_path)
    expectations["check_id"] = check["check_id"]
    write_canonical_json(expectations_path, expectations)
    _reidentify(expectations_path, "expectations_id")
    _refresh_manifest(hbm_candidate)

    with pytest.raises(ProductionConnectedLayerCheckError, match="HBM image differs"):
        _check(hbm_candidate)
    simulator = ProductionConnectedLayerSimulator.load(hbm_candidate)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        simulator.execute()

    sram_candidate = _hardlink_clone(source, tmp_path / "sram-corrupt")
    plan_path = sram_candidate / "physical/physical_plan.json"
    _break_link(plan_path)
    plan = load_strict_json(plan_path)
    plan["sram"]["regions"][17]["address"] += 16
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(sram_candidate)
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(sram_candidate)
    with pytest.raises(ProductionConnectedLayerSimulationError):
        ProductionConnectedLayerSimulator.load(sram_candidate)


@REAL
def test_connected_rejects_kernel_physical_leak_and_source_corruption(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    source = connected_builds[0]
    kernel_candidate = _hardlink_clone(source, tmp_path / "kernel-leak")
    kernel_path = kernel_candidate / "ir/tensor_kernel_ir.json"
    _break_link(kernel_path)
    kernel = load_strict_json(kernel_path)
    kernel["kernels"][0]["attributes"]["address"] = 0
    write_canonical_json(kernel_path, kernel)
    _reidentify(kernel_path, "kernel_ir_id")
    _refresh_manifest(kernel_candidate)
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(kernel_candidate)
    with pytest.raises(
        ProductionConnectedLayerSimulationError,
        match="physical execution fields",
    ):
        ProductionConnectedLayerSimulator.load(kernel_candidate)

    source_candidate = _hardlink_clone(source, tmp_path / "source-corrupt")
    qualification_path = source_candidate / "source/qkv_qualification.json"
    _break_link(qualification_path)
    qualification_path.write_bytes(qualification_path.read_bytes() + b"\n")
    with pytest.raises(ProductionConnectedLayerCheckError):
        _check(source_candidate)
    with pytest.raises(
        ProductionConnectedLayerSimulationError, match="artifact identity"
    ):
        ProductionConnectedLayerSimulator.load(source_candidate)


@REAL
def test_connected_dependencies_are_independent_and_publication_is_atomic(
    connected_builds: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    deployment, _, report = connected_builds
    import compiler.tensor_accelerator.production_connected_layer_checking as checker
    import runtime.tensor_accelerator.production_connected_layer_simulator as simulator

    checker_source = inspect.getsource(checker)
    simulator_source = inspect.getsource(simulator)
    assert "from .production_connected_layer import" not in checker_source
    assert "production_connected_layer_checking" not in simulator_source
    assert "qualification" not in "\n".join(
        line
        for line in simulator_source.splitlines()
        if line.startswith(("from ", "import "))
    )
    assert "runtime.reference" not in simulator_source
    assert "transformers" not in simulator_source
    assert "torch" not in simulator_source

    with pytest.raises(ProductionConnectedLayerBuildError, match="already exists"):
        _build(deployment)
    output = tmp_path / "execution.json"
    publish_connected_layer_execution_report(report, output)
    assert load_strict_json(output) == report
    with pytest.raises(ProductionConnectedLayerSimulationError, match="already exists"):
        publish_connected_layer_execution_report(report, output)
