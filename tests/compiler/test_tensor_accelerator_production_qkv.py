from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from jsonschema import Draft202012Validator
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
from compiler.tensor_accelerator.production_qkv import (
    ProductionQKVBuildError,
    build_qkv_deployment,
)
from compiler.tensor_accelerator.production_qkv_checking import (
    ProductionQKVCheckError,
    check_qkv_candidate,
)
from runtime.tensor_accelerator.production_qkv_simulator import (
    ProductionQKVSimulationError,
    ProductionQKVSimulator,
    publish_qkv_execution_report,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = ROOT / "build/qwen3-8b/checkpoint.lock.json"
GRAPH = ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json"
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v3.json"
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"
HAS_REAL_SOURCES = (
    all(path.is_file() for path in (LOCK, GRAPH, CAPABILITY, QUALIFICATION))
    and SNAPSHOT.is_dir()
)
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES, reason="pinned Qwen sources unavailable"
)

BUILD_ID = "b84d8f049fd16d90bed1aeb67c7317919d80ca3096055688d3a2144a81c06b63"
PHYSICAL_PLAN_ID = "f38e45bcecf22d4b4f77829f88c65e3306fb41460056b372f36f3adbfac89f3d"
CHECK_ID = "249852ee5f014040de56712e2bbb2d35123d1ffe1025c11e2fcfa8c1ae912023"
KERNEL_IR_ID = "68f15201e9f49ca0f6ad358aef20322237c4907e6a9687cd57847d34820bb17f"
HBM_SHA256 = "6f228bc2ecc5d6370ceecd67e2190a9e97199cce54bb03e6a2890bee9535da4d"
REPORT_ID = "af4b5b5d3ea68689f073fdc22584699462ad64c44295120cea7a5e7873383730"
OUTPUT_SHA256 = {
    "k_rotary": "ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858",
    "q_rotary": "a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d",
    "v": "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
}


def _build(output: Path) -> dict[str, Any]:
    return build_qkv_deployment(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        output=output,
    )


@pytest.fixture(scope="module")
def qkv_builds(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    if not HAS_REAL_SOURCES:
        pytest.skip("pinned Qwen sources unavailable")
    root = tmp_path_factory.mktemp("production-qkv")
    first = root / "first"
    second = root / "second"
    _build(first)
    _build(second)
    return first, second


def _tree_identity(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            payload = path.read_bytes()
            result[path.relative_to(root).as_posix()] = (
                len(payload),
                hashlib.sha256(payload).hexdigest(),
            )
    return result


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
        canonical_json_bytes(
            {key: item for key, item in manifest.items() if key != "build_id"}
        )
    ).hexdigest()
    write_canonical_json(manifest_path, manifest)


def _replace_program(root: Path, commands: tuple[Any, ...]) -> None:
    reindexed = tuple(
        replace(command, index=index) for index, command in enumerate(commands)
    )
    payload = encode(reindexed, abi_minor=2)
    (root / "program/commands.bin").write_bytes(payload)
    (root / "program/commands.disasm").write_text(
        disassemble(reindexed, abi_minor=2), encoding="utf-8", newline="\n"
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


def _check(root: Path) -> dict[str, Any]:
    return check_qkv_candidate(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        root=root,
    )


def _external_request(root: Path, output: Path, *, token: int, position: int) -> Path:
    request = load_strict_json(root / "request/execution_request.json")
    request["token"]["token_id"] = token
    request["position"]["position_id"] = position
    request["request_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: item for key, item in request.items() if key != "request_id"}
        )
    ).hexdigest()
    write_canonical_json(output, request)
    return output


@REAL
def test_real_qkv_build_is_byte_deterministic_checked_and_causally_exact(
    qkv_builds: tuple[Path, Path],
) -> None:
    first, second = qkv_builds
    assert load_strict_json(first / "deployment_manifest.json") == load_strict_json(
        second / "deployment_manifest.json"
    )
    assert _tree_identity(first) == _tree_identity(second)

    manifest = load_strict_json(first / "deployment_manifest.json")
    plan = load_strict_json(first / "physical/physical_plan.json")
    check = load_strict_json(first / "checks/independent_check.json")
    kernel = load_strict_json(first / "ir/tensor_kernel_ir.json")
    assert manifest["build_id"] == BUILD_ID
    assert plan["physical_plan_id"] == PHYSICAL_PLAN_ID
    assert check["check_id"] == CHECK_ID
    assert kernel["kernel_ir_id"] == KERNEL_IR_ID
    assert plan["hbm"]["image"] == {
        "base_address": 0,
        "path": "memory/hbm_qkv.bin",
        "sha256": HBM_SHA256,
        "size_bytes": 54_444_544,
    }
    assert check["hbm_image_sha256"] == HBM_SHA256
    assert [region["bank"] for region in plan["sram"]["regions"]] == list(range(16))

    command_payload = (first / "program/commands.bin").read_bytes()
    commands = decode(command_payload)
    assert command_abi(command_payload) == (2, 2)
    assert len(commands) == 3_082
    assert Counter(command.opcode for command in commands) == {
        Opcode.DMA_HBM_INDEXED_TO_SRAM: 2,
        Opcode.DMA_HBM_TO_SRAM: 1_539,
        Opcode.MATMUL_BF16_TILE: 1_536,
        Opcode.RMSNORM_BF16: 3,
        Opcode.ROPE_BF16: 1,
        Opcode.COMPLETE: 1,
    }

    report = ProductionQKVSimulator.load(first).execute()
    assert report["report_id"] == REPORT_ID
    assert report["status"] == "pass"
    assert report["counter_reconciliation"] == "exact"
    assert report["counters"] == check["expected_counters"] == plan["expected_counters"]
    assert {
        role: record["payload_sha256"] for role, record in report["outputs"].items()
    } == OUTPUT_SHA256
    assert report["timing"] == {
        "reason": "capability_uncharacterized",
        "status": "unavailable",
    }


@REAL
def test_qkv_artifacts_validate_against_strict_schemas(
    qkv_builds: tuple[Path, Path],
) -> None:
    deployment = qkv_builds[0]
    report = ProductionQKVSimulator.load(deployment).execute()
    schema_root = ROOT / "schemas/compiler/tensor_accelerator"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in schema_root.glob("*.schema.json")
    }
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    instances: dict[str, Any] = {
        "qkv_qualification_v1.schema.json": load_strict_json(QUALIFICATION),
        "production_tensor_kernel_ir_v1.schema.json": load_strict_json(
            deployment / "ir/tensor_kernel_ir.json"
        ),
        "qkv_physical_plan_v1.schema.json": load_strict_json(
            deployment / "physical/physical_plan.json"
        ),
        "qkv_request_v1.schema.json": load_strict_json(
            deployment / "request/execution_request.json"
        ),
        "qkv_source_lock_v1.schema.json": load_strict_json(
            deployment / "source.lock.json"
        ),
        "qkv_independent_check_v1.schema.json": load_strict_json(
            deployment / "checks/independent_check.json"
        ),
        "qkv_expectations_v1.schema.json": load_strict_json(
            deployment / "execution_expectations.json"
        ),
        "qkv_deployment_v1.schema.json": load_strict_json(
            deployment / "deployment_manifest.json"
        ),
        "qkv_execution_v1.schema.json": report,
        "production_capability_v1.schema.json": load_strict_json(
            deployment / "capability.json"
        ),
    }
    assert len(instances) == 10
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)


@REAL
def test_independent_checker_rejects_rehashed_hbm_and_sram_corruption(
    qkv_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    corrupted = _clone(qkv_builds[0], tmp_path / "corrupted-hbm")
    image_path = corrupted / "memory/hbm_qkv.bin"
    image = bytearray(image_path.read_bytes())
    image[0] ^= 1
    image_path.write_bytes(image)
    plan_path = corrupted / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["hbm"]["image"]["sha256"] = hashlib.sha256(image).hexdigest()
    embedding = plan["hbm"]["regions"][0]
    assert embedding["id"] == "embedding_rows"
    start = embedding["offset_bytes"]
    end = start + embedding["size_bytes"]
    embedding["payload_sha256"] = hashlib.sha256(image[start:end]).hexdigest()
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    with pytest.raises(ProductionQKVCheckError, match="locked source"):
        _check(corrupted)

    misplaced = _clone(qkv_builds[0], tmp_path / "misplaced-sram")
    misplaced_plan_path = misplaced / "physical/physical_plan.json"
    misplaced_plan = load_strict_json(misplaced_plan_path)
    misplaced_plan["sram"]["regions"][1]["address"] += 16
    write_canonical_json(misplaced_plan_path, misplaced_plan)
    _reidentify(misplaced_plan_path, "physical_plan_id")
    with pytest.raises(ProductionQKVCheckError, match="SRAM region allocation"):
        _check(misplaced)


@REAL
def test_checker_rejects_missing_and_reordered_commands(
    qkv_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    missing = _clone(qkv_builds[0], tmp_path / "missing")
    commands = decode((missing / "program/commands.bin").read_bytes())
    _replace_program(missing, commands[1:])
    with pytest.raises(ProductionQKVCheckError, match="legal Q/K/V schedule"):
        _check(missing)

    reordered = _clone(qkv_builds[0], tmp_path / "reordered")
    commands = decode((reordered / "program/commands.bin").read_bytes())
    _replace_program(reordered, (commands[1], commands[0], *commands[2:]))
    with pytest.raises(ProductionQKVCheckError, match="legal Q/K/V schedule"):
        _check(reordered)


@REAL
@pytest.mark.parametrize(
    ("remove_index", "message"),
    [
        (2, "uninitialized"),
        (3, "matching fresh causally preceding DMA"),
        (4, "unconsumed weight tile"),
        (-2, "unfinished or duplicate"),
    ],
)
def test_simulator_rejects_causally_missing_operation_families(
    qkv_builds: tuple[Path, Path],
    tmp_path: Path,
    remove_index: int,
    message: str,
) -> None:
    deployment = _clone(qkv_builds[0], tmp_path / f"missing-{remove_index}")
    commands = list(decode((deployment / "program/commands.bin").read_bytes()))
    del commands[remove_index]
    _replace_program(deployment, tuple(commands))
    with pytest.raises(ProductionQKVSimulationError, match=message):
        ProductionQKVSimulator.load(deployment).execute()


@REAL
@pytest.mark.parametrize(
    ("token", "position"),
    [(1, 7_999), (0, 8_000)],
)
def test_simulator_rejects_runtime_token_and_position_outside_resident_ranges(
    qkv_builds: tuple[Path, Path],
    tmp_path: Path,
    token: int,
    position: int,
) -> None:
    request = _external_request(
        qkv_builds[0],
        tmp_path / f"request-{token}-{position}.json",
        token=token,
        position=position,
    )
    with pytest.raises(ProductionQKVSimulationError, match="index or stride"):
        ProductionQKVSimulator.load(qkv_builds[0]).execute(request)


@REAL
def test_simulator_rejects_forged_values_and_counters(
    qkv_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    forged_values = _clone(qkv_builds[0], tmp_path / "forged-values")
    expectations_path = forged_values / "execution_expectations.json"
    expectations = load_strict_json(expectations_path)
    expectations["output_payload_sha256"]["q_rotary"] = "0" * 64
    write_canonical_json(expectations_path, expectations)
    _reidentify(expectations_path, "expectations_id")
    _refresh_manifest(forged_values)
    with pytest.raises(ProductionQKVSimulationError, match="causal Q/K/V values"):
        ProductionQKVSimulator.load(forged_values).execute()

    forged_counters = _clone(qkv_builds[0], tmp_path / "forged-counters")
    plan_path = forged_counters / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["expected_counters"]["scalar_multiplications"] += 1
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    expectations_path = forged_counters / "execution_expectations.json"
    expectations = load_strict_json(expectations_path)
    expectations["counters"]["scalar_multiplications"] += 1
    write_canonical_json(expectations_path, expectations)
    _reidentify(expectations_path, "expectations_id")
    _refresh_manifest(forged_counters)
    with pytest.raises(ProductionQKVSimulationError, match="observed counters"):
        ProductionQKVSimulator.load(forged_counters).execute()


def test_qkv_simulator_has_no_compiler_checker_framework_or_reference_imports() -> None:
    module = __import__(
        "runtime.tensor_accelerator.production_qkv_simulator", fromlist=["unused"]
    )
    source = Path(module.__file__).read_text(encoding="utf-8").lower()
    assert "import torch" not in source
    assert "transformers" not in source
    assert "production_qkv import" not in source
    assert "production_qkv_checking" not in source
    assert "runtime.reference" not in source
    assert "import qwen" not in source
    assert "compiler.qwen" not in source


@REAL
def test_qkv_build_and_report_publication_never_overwrite(
    qkv_builds: tuple[Path, Path], tmp_path: Path
) -> None:
    deployment = qkv_builds[0]
    before = _tree_identity(deployment)
    with pytest.raises(ProductionQKVBuildError, match="already exists"):
        _build(deployment)
    assert _tree_identity(deployment) == before

    report = ProductionQKVSimulator.load(deployment).execute()
    output = tmp_path / "report.json"
    publish_qkv_execution_report(report, output)
    first = output.read_bytes()
    with pytest.raises(ProductionQKVSimulationError, match="will not be overwritten"):
        publish_qkv_execution_report(report, output)
    assert output.read_bytes() == first
