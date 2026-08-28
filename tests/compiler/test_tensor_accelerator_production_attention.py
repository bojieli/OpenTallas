from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import struct
from typing import Any

from jsonschema import Draft202012Validator
import pytest
from referencing import Registry, Resource

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.production_attention import (
    ProductionAttentionBuildError,
    build_attention_deployment,
)
from compiler.tensor_accelerator.production_attention_checking import (
    ProductionAttentionCheckError,
    check_attention_candidate,
)
from compiler.tensor_accelerator.production_command import (
    Opcode,
    command_abi,
    decode,
    disassemble,
    encode,
)
from runtime.tensor_accelerator.production_attention_simulator import (
    ProductionAttentionSimulationError,
    ProductionAttentionSimulator,
)


ROOT = Path(__file__).resolve().parents[2]
QKV_EXECUTION = ROOT / "results/tensor_accelerator/qwen3_hbm_sram_qkv_execution.json"
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v4.json"
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_attention_qualification.json"
RETAINED_EXECUTION = ROOT / "results/tensor_accelerator/qwen3_hbm_sram_attention_execution.json"
HAS_REAL_SOURCES = all(path.is_file() for path in (QKV_EXECUTION, GRAPH, CAPABILITY, QUALIFICATION))
REAL = pytest.mark.skipif(not HAS_REAL_SOURCES, reason="retained Qwen attention sources unavailable")

BUILD_ID = "df11a02f915722127788d21501609b693b388f0e6c02f8ca4a83dc8f878cac95"
PHYSICAL_PLAN_ID = "52bf4f067e77cf71d266a391fc6affae1e74ce817f08f43848d3650621dc3ff7"
CHECK_ID = "d6e971ed42ffa386ca22b7be53818bf5f84da478a25081107777934d28478b3d"
KERNEL_IR_ID = "04b2294e406ccc915bfd0c72cd5baf024221559941e31361fc8c85b03cc120a6"
HBM_SHA256 = "8aa8eee83b0f044614d9bdcc10ee6525a6b646c8d85f69acf77aa816755b9445"
REPORT_ID = "cf62189cc5d3e4e370b76e68767e6630e884077bb8dc39e3ba7c05646f43ef13"
STATE_SHA256 = "c446dd569837a2acf3f6a2333799794caaf0a7ae2919f42edecfcd6f7fd6bc56"
TRANSACTION_ID = 0x4154544E0002
OUTPUT_SHA256 = {
    "attention": "d53e8a3890eb01357fb60ec2607a716179cec0eb556e28629963af655cd3e1fb",
    "probabilities": "eb557e71a0d0110f467343eac7be5edd832c2ff79617b96c9bde777ad7a73685",
    "scaled_scores": "65c111d6a5026a86aaa86264d1cad5b97b10e8c871ba96e56e19f4b3f206fac3",
}


def _build(output: Path) -> dict[str, Any]:
    return build_attention_deployment(
        qkv_execution_path=QKV_EXECUTION,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        output=output,
    )


@pytest.fixture(scope="module")
def attention_builds(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    if not HAS_REAL_SOURCES:
        pytest.skip("retained Qwen attention sources unavailable")
    root = tmp_path_factory.mktemp("production-attention")
    first = root / "first"
    second = root / "second"
    _build(first)
    _build(second)
    return first, second


def _tree_identity(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _clone(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def _reidentify(path: Path, field: str) -> dict[str, Any]:
    value = load_strict_json(path)
    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()
    write_canonical_json(path, value)
    return value


def _refresh_manifest(root: Path) -> None:
    manifest_path = root / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    plan = load_strict_json(root / "physical/physical_plan.json")
    manifest["physical_plan_id"] = plan["physical_plan_id"]
    for artifact in manifest["artifacts"]:
        payload = (root / artifact["path"]).read_bytes()
        artifact["sha256"] = hashlib.sha256(payload).hexdigest()
        artifact["size_bytes"] = len(payload)
    manifest["build_id"] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in manifest.items() if key != "build_id"})
    ).hexdigest()
    write_canonical_json(manifest_path, manifest)


def _replace_program(root: Path, commands: tuple[Any, ...]) -> None:
    reindexed = tuple(replace(command, index=index) for index, command in enumerate(commands))
    payload = encode(reindexed, abi_minor=3)
    (root / "program/commands.bin").write_bytes(payload)
    (root / "program/commands.disasm").write_text(
        disassemble(reindexed, abi_minor=3), encoding="utf-8", newline="\n"
    )
    plan_path = root / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["program"].update(
        {
            "command_count": len(reindexed),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    )
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(root)


def _rehash_hbm(root: Path, region_id: str) -> None:
    plan_path = root / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    image_path = root / "memory/hbm_attention.bin"
    image = image_path.read_bytes()
    for region in plan["hbm"]["regions"]:
        if region["id"] == region_id:
            start = region["offset_bytes"]
            end = start + region["allocated_size_bytes"]
            region["payload_sha256"] = hashlib.sha256(image[start:end]).hexdigest()
            break
    else:
        raise AssertionError(f"missing HBM region {region_id}")
    plan["hbm"]["image"].update(
        {
            "sha256": hashlib.sha256(image).hexdigest(),
            "size_bytes": len(image),
        }
    )
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(root)


def _check(root: Path) -> dict[str, Any]:
    return check_attention_candidate(
        qkv_execution_path=QKV_EXECUTION,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        root=root,
    )


@REAL
def test_attention_build_is_deterministic_checked_and_causally_exact(
    attention_builds: tuple[Path, Path],
) -> None:
    first, second = attention_builds
    assert _tree_identity(first) == _tree_identity(second)
    manifest = load_strict_json(first / "deployment_manifest.json")
    plan = load_strict_json(first / "physical/physical_plan.json")
    check = load_strict_json(first / "checks/independent_check.json")
    kernel = load_strict_json(first / "ir/tensor_kernel_ir.json")
    assert manifest["build_id"] == BUILD_ID
    assert plan["physical_plan_id"] == PHYSICAL_PLAN_ID
    assert check["check_id"] == CHECK_ID
    assert kernel["kernel_ir_id"] == KERNEL_IR_ID
    assert plan["hbm"]["image"]["sha256"] == HBM_SHA256
    assert plan["hbm"]["image"]["size_bytes"] == 32_784_512
    assert check == _check(first)
    assert [kernel_record["kind"] for kernel_record in kernel["kernels"]] == [
        "KV_PREPARE",
        "ATTENTION",
        "STATE_COMMIT",
    ]
    assert all(
        "address" not in json.dumps(kernel_record)
        and "sram" not in json.dumps(kernel_record).lower()
        for kernel_record in kernel["kernels"]
    )

    payload = (first / "program/commands.bin").read_bytes()
    commands = decode(payload)
    assert command_abi(payload) == (2, 3)
    assert Counter(command.opcode for command in commands) == {
        Opcode.DMA_HBM_TO_SRAM: 3,
        Opcode.KV_PREPARE_BF16: 1,
        Opcode.GQA_ATTENTION_BF16: 1,
        Opcode.STATE_COMMIT: 1,
        Opcode.COMPLETE: 1,
    }

    report = ProductionAttentionSimulator.load(first).execute()
    assert report["report_id"] == REPORT_ID
    assert report["status"] == "pass"
    assert report["counter_reconciliation"] == "exact"
    assert report["counters"] == check["expected_counters"] == plan["expected_counters"]
    assert {role: record["payload_sha256"] for role, record in report["outputs"].items()} == OUTPUT_SHA256
    assert report["state"]["state_sha256"] == STATE_SHA256
    assert report["state"]["generation"] == 5
    assert report["state"]["length"] == 4
    assert [record["state_generation"] for record in report["trace"]] == [4, 4, 4, 4, 4, 5, 5]
    assert report["timing"] == {"reason": "capability_uncharacterized", "status": "unavailable"}
    if RETAINED_EXECUTION.is_file():
        assert load_strict_json(RETAINED_EXECUTION) == report


@REAL
def test_attention_artifacts_validate_against_strict_schemas(
    attention_builds: tuple[Path, Path],
) -> None:
    deployment = attention_builds[0]
    report = ProductionAttentionSimulator.load(deployment).execute()
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
        "attention_qualification_v1.schema.json": load_strict_json(QUALIFICATION),
        "production_tensor_kernel_ir_v1.schema.json": load_strict_json(deployment / "ir/tensor_kernel_ir.json"),
        "attention_physical_plan_v1.schema.json": load_strict_json(deployment / "physical/physical_plan.json"),
        "attention_request_v1.schema.json": load_strict_json(deployment / "request/execution_request.json"),
        "attention_source_lock_v1.schema.json": load_strict_json(deployment / "source.lock.json"),
        "attention_independent_check_v1.schema.json": load_strict_json(deployment / "checks/independent_check.json"),
        "attention_expectations_v1.schema.json": load_strict_json(deployment / "execution_expectations.json"),
        "attention_deployment_v1.schema.json": load_strict_json(deployment / "deployment_manifest.json"),
        "attention_execution_v1.schema.json": report,
        "production_capability_v1.schema.json": load_strict_json(deployment / "capability.json"),
    }
    assert len(instances) == 10
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)


@REAL
def test_independent_checker_rejects_rehashed_hbm_and_sram_corruption(
    attention_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    source = attention_builds[0]
    corrupted_hbm = _clone(source, tmp_path / "hbm")
    image_path = corrupted_hbm / "memory/hbm_attention.bin"
    payload = bytearray(image_path.read_bytes())
    payload[4096] ^= 1
    image_path.write_bytes(bytes(payload))
    _rehash_hbm(corrupted_hbm, "query")
    with pytest.raises(ProductionAttentionCheckError, match="HBM image differs"):
        _check(corrupted_hbm)

    corrupted_sram = _clone(source, tmp_path / "sram")
    plan_path = corrupted_sram / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["sram"]["regions"][0]["bank"] = 4
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(corrupted_sram)
    with pytest.raises(ProductionAttentionCheckError, match="physical plan differs"):
        _check(corrupted_sram)


@REAL
@pytest.mark.parametrize(
    ("name", "transform", "match"),
    [
        (
            "missing_query_dma",
            lambda commands: commands[1:],
            "lacks prepared causal inputs",
        ),
        (
            "dma_after_prepare",
            lambda commands: commands[:2] + commands[3:4] + commands[2:3] + commands[4:],
            "lacks causal DMA",
        ),
        (
            "missing_attention",
            lambda commands: commands[:4] + commands[5:],
            "lacks successful attention",
        ),
        (
            "missing_commit",
            lambda commands: commands[:5] + commands[6:],
            "before attention and commit",
        ),
    ],
)
def test_simulator_rejects_missing_or_reordered_causal_work_without_publication(
    attention_builds: tuple[Path, Path],
    tmp_path: Path,
    name: str,
    transform: Any,
    match: str,
) -> None:
    candidate = _clone(attention_builds[0], tmp_path / name)
    before = hashlib.sha256((candidate / "memory/hbm_attention.bin").read_bytes()).hexdigest()
    commands = decode((candidate / "program/commands.bin").read_bytes())
    _replace_program(candidate, tuple(transform(commands)))
    with pytest.raises(ProductionAttentionSimulationError, match=match):
        ProductionAttentionSimulator.load(candidate).execute()
    after = hashlib.sha256((candidate / "memory/hbm_attention.bin").read_bytes()).hexdigest()
    assert after == before == HBM_SHA256


@REAL
def test_simulator_rejects_corrupt_state_mixed_transaction_and_forged_expectations(
    attention_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    source = attention_builds[0]

    corrupt_state = _clone(source, tmp_path / "corrupt-state")
    image_path = corrupt_state / "memory/hbm_attention.bin"
    image = bytearray(image_path.read_bytes())
    plan = load_strict_json(corrupt_state / "physical/physical_plan.json")
    key_state = next(region for region in plan["hbm"]["regions"] if region["id"] == "key_state")
    image[key_state["offset_bytes"]] ^= 1
    image_path.write_bytes(bytes(image))
    _rehash_hbm(corrupt_state, "key_state")
    with pytest.raises(ProductionAttentionSimulationError, match="differs from qualification"):
        ProductionAttentionSimulator.load(corrupt_state).execute()

    mixed = _clone(source, tmp_path / "mixed-transaction")
    image_path = mixed / "memory/hbm_attention.bin"
    image = bytearray(image_path.read_bytes())
    plan = load_strict_json(mixed / "physical/physical_plan.json")
    descriptor = next(region for region in plan["hbm"]["regions"] if region["id"] == "transaction_descriptor")
    struct.pack_into("<Q", image, descriptor["offset_bytes"] + 8, TRANSACTION_ID + 1)
    image_path.write_bytes(bytes(image))
    _rehash_hbm(mixed, "transaction_descriptor")
    with pytest.raises(ProductionAttentionSimulationError, match="descriptor differs"):
        ProductionAttentionSimulator.load(mixed).execute()

    forged = _clone(source, tmp_path / "forged")
    expectations_path = forged / "execution_expectations.json"
    expectations = load_strict_json(expectations_path)
    expectations["counters"]["score_multiplications"] += 1
    expectations["output_payload_sha256"]["attention"] = "0" * 64
    write_canonical_json(expectations_path, expectations)
    _reidentify(expectations_path, "expectations_id")
    _refresh_manifest(forged)
    with pytest.raises(ProductionAttentionSimulationError, match="expectations differ"):
        ProductionAttentionSimulator.load(forged)


@REAL
def test_stale_generation_request_and_implementation_coupling_are_rejected(
    attention_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    source = attention_builds[0]
    request = load_strict_json(source / "request/execution_request.json")
    request["expected_generation"] = 3
    request["request_id"] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in request.items() if key != "request_id"})
    ).hexdigest()
    request_path = tmp_path / "stale.json"
    write_canonical_json(request_path, request)
    with pytest.raises(ProductionAttentionSimulationError, match="expected_generation differs"):
        ProductionAttentionSimulator.load(source).execute(request_path)

    checker_source = (ROOT / "compiler/tensor_accelerator/production_attention_checking.py").read_text(encoding="utf-8")
    simulator_source = (ROOT / "runtime/tensor_accelerator/production_attention_simulator.py").read_text(encoding="utf-8")
    assert "from .production_attention import" not in checker_source
    assert "runtime.reference" not in simulator_source
    assert "production_attention import" not in simulator_source


def test_attention_build_rejects_missing_sources_and_existing_output(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(ProductionAttentionBuildError, match="does not exist"):
        build_attention_deployment(
            qkv_execution_path=missing,
            model_graph_path=missing,
            capability_path=missing,
            qualification_path=missing,
            output=tmp_path / "output",
        )
    existing = tmp_path / "existing"
    existing.mkdir()
    if HAS_REAL_SOURCES:
        with pytest.raises(ProductionAttentionBuildError, match="already exists"):
            _build(existing)
