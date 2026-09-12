from __future__ import annotations

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
    encode,
)
from compiler.tensor_accelerator.production_rmsnorm import (
    ProductionRMSNormBuildError,
    build_rmsnorm_deployment,
)
from compiler.tensor_accelerator.production_rmsnorm_checking import (
    ProductionRMSNormCheckError,
    check_rmsnorm_candidate,
)
from runtime.tensor_accelerator.production_rmsnorm_simulator import (
    ProductionRMSNormSimulationError,
    ProductionRMSNormSimulator,
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
CAPABILITY = ROOT / "configs/hardware/tensor_accelerator_development_v2.json"
QUALIFICATION = ROOT / "results/tensor_accelerator/qwen3_rmsnorm_qualification.json"
HAS_REAL_SOURCES = all(
    path.is_file() for path in (LOCK, GRAPH, CAPABILITY, QUALIFICATION)
) and SNAPSHOT.is_dir()
REAL = pytest.mark.skipif(not HAS_REAL_SOURCES, reason="pinned Qwen sources unavailable")


def _build(output: Path) -> dict[str, Any]:
    return build_rmsnorm_deployment(
        snapshot=SNAPSHOT,
        checkpoint_lock_path=LOCK,
        model_graph_path=GRAPH,
        capability_path=CAPABILITY,
        qualification_path=QUALIFICATION,
        output=output,
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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
    payload = encode(commands, abi_minor=1)
    command_path = root / "program/commands.bin"
    command_path.write_bytes(payload)
    plan_path = root / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["program"].update(
        {
            "command_count": len(commands),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    )
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    _refresh_manifest(root)


@REAL
def test_real_rmsnorm_build_is_deterministic_checked_and_causally_exact(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = _build(first)
    second_manifest = _build(second)
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["build_id"] == (
        "4cdd371c63dda8db64f0fe101777de1f0de0043ca8c01474f4b554cfefe65ba6"
    )
    commands_payload = (first / "program/commands.bin").read_bytes()
    assert command_abi(commands_payload) == (2, 1)
    assert [command.opcode for command in decode(commands_payload)] == [
        Opcode.DMA_HBM_INDEXED_TO_SRAM,
        Opcode.DMA_HBM_TO_SRAM,
        Opcode.RMSNORM_BF16,
        Opcode.COMPLETE,
    ]
    check = load_strict_json(first / "checks/independent_check.json")
    assert check["status"] == "pass"
    assert [item["role"] for item in check["reconstructed_sources"]] == [
        "embedding_row",
        "rmsnorm_weight",
    ]
    report = ProductionRMSNormSimulator.load(first).execute()
    assert report["report_id"] == (
        "ef9143adedbf06a57340539b212dc9d76648323e1c2b72269ae2e748d8a1c28f"
    )
    assert report["output"]["payload_sha256"] == (
        "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
    )
    assert report["output"]["normalized_payload_sha256"] == (
        "bf4b81b7e711157b4e8c91bde7294d3be647844dbd7336d462201a246a1da28d"
    )
    assert report["output"]["mean_square_binary32_code"] == 0x3A5BF2CA
    assert report["output"]["inverse_rms_binary32_code"] == 0x420A0297
    selected = load_strict_json(QUALIFICATION)["selected_reference"]
    assert [report["output"]["codes"][index] for index in selected["element_indices"]] == selected["output_codes"]
    assert report["counters"] == check["expected_counters"]
    assert report["timing"] == {
        "reason": "capability_uncharacterized",
        "status": "unavailable",
    }


@REAL
def test_independent_checker_rejects_rehashed_hbm_and_sram_corruption(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deployment"
    _build(deployment)
    image_path = deployment / "memory/hbm_embedding_rmsnorm.bin"
    image = bytearray(image_path.read_bytes())
    image[0] ^= 1
    image_path.write_bytes(image)
    plan_path = deployment / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["hbm"]["image"]["sha256"] = hashlib.sha256(image).hexdigest()
    plan["hbm"]["regions"][0]["payload_sha256"] = hashlib.sha256(
        image[:8192]
    ).hexdigest()
    write_canonical_json(plan_path, plan)
    _reidentify(plan_path, "physical_plan_id")
    with pytest.raises(ProductionRMSNormCheckError, match="locked source"):
        check_rmsnorm_candidate(
            snapshot=SNAPSHOT,
            checkpoint_lock_path=LOCK,
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            qualification_path=QUALIFICATION,
            root=deployment,
        )

    clean = tmp_path / "clean"
    _build(clean)
    clean_plan_path = clean / "physical/physical_plan.json"
    clean_plan = load_strict_json(clean_plan_path)
    clean_plan["sram"]["regions"][1]["address"] += 16
    write_canonical_json(clean_plan_path, clean_plan)
    _reidentify(clean_plan_path, "physical_plan_id")
    with pytest.raises(ProductionRMSNormCheckError, match="SRAM region allocation"):
        check_rmsnorm_candidate(
            snapshot=SNAPSHOT,
            checkpoint_lock_path=LOCK,
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            qualification_path=QUALIFICATION,
            root=clean,
        )


@REAL
def test_checker_rejects_missing_and_reordered_commands(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    _build(missing_root)
    original = decode((missing_root / "program/commands.bin").read_bytes())
    missing = tuple(
        replace(command, index=index)
        for index, command in enumerate(original[1:])
    )
    _replace_program(missing_root, missing)
    with pytest.raises(ProductionRMSNormCheckError, match="legal schedule"):
        check_rmsnorm_candidate(
            snapshot=SNAPSHOT,
            checkpoint_lock_path=LOCK,
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            qualification_path=QUALIFICATION,
            root=missing_root,
        )

    reordered_root = tmp_path / "reordered"
    _build(reordered_root)
    original = decode((reordered_root / "program/commands.bin").read_bytes())
    reordered = tuple(
        replace(command, index=index)
        for index, command in enumerate((original[1], original[0], *original[2:]))
    )
    _replace_program(reordered_root, reordered)
    with pytest.raises(ProductionRMSNormCheckError, match="legal schedule"):
        check_rmsnorm_candidate(
            snapshot=SNAPSHOT,
            checkpoint_lock_path=LOCK,
            model_graph_path=GRAPH,
            capability_path=CAPABILITY,
            qualification_path=QUALIFICATION,
            root=reordered_root,
        )


@REAL
def test_simulator_is_causal_but_allows_legally_independent_dma_order(
    tmp_path: Path,
) -> None:
    clean = tmp_path / "clean"
    _build(clean)
    expected = ProductionRMSNormSimulator.load(clean).execute()["output"][
        "payload_sha256"
    ]

    reordered = tmp_path / "reordered"
    shutil.copytree(clean, reordered)
    commands = decode((reordered / "program/commands.bin").read_bytes())
    swapped = tuple(
        replace(command, index=index)
        for index, command in enumerate((commands[1], commands[0], *commands[2:]))
    )
    _replace_program(reordered, swapped)
    assert ProductionRMSNormSimulator.load(reordered).execute()["output"][
        "payload_sha256"
    ] == expected

    missing = tmp_path / "missing"
    shutil.copytree(clean, missing)
    commands = decode((missing / "program/commands.bin").read_bytes())
    removed = tuple(
        replace(command, index=index)
        for index, command in enumerate(commands[1:])
    )
    _replace_program(missing, removed)
    with pytest.raises(ProductionRMSNormSimulationError, match="uninitialized"):
        ProductionRMSNormSimulator.load(missing).execute()


@REAL
def test_simulator_rejects_runtime_index_and_forged_expectation(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deployment"
    _build(deployment)
    request = load_strict_json(deployment / "request/execution_request.json")
    request["token"]["token_id"] = 1
    request["request_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: item for key, item in request.items() if key != "request_id"}
        )
    ).hexdigest()
    request_path = tmp_path / "bad_request.json"
    write_canonical_json(request_path, request)
    with pytest.raises(ProductionRMSNormSimulationError, match="index or stride"):
        ProductionRMSNormSimulator.load(deployment).execute(request_path)

    forged = tmp_path / "forged"
    shutil.copytree(deployment, forged)
    expectations_path = forged / "execution_expectations.json"
    expectations = load_strict_json(expectations_path)
    expectations["output_payload_sha256"] = "0" * 64
    expectations["expectations_id"] = hashlib.sha256(
        canonical_json_bytes(
            {
                key: item
                for key, item in expectations.items()
                if key != "expectations_id"
            }
        )
    ).hexdigest()
    write_canonical_json(expectations_path, expectations)
    _refresh_manifest(forged)
    with pytest.raises(ProductionRMSNormSimulationError, match="causal output"):
        ProductionRMSNormSimulator.load(forged).execute()


@REAL
def test_rmsnorm_artifacts_validate_against_strict_schemas(tmp_path: Path) -> None:
    deployment = tmp_path / "deployment"
    _build(deployment)
    report = ProductionRMSNormSimulator.load(deployment).execute()
    schema_root = ROOT / "schemas/compiler/tensor_accelerator"
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in schema_root.glob("*.schema.json")
    }
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    instances: dict[str, Any] = {
        "rmsnorm_qualification_v1.schema.json": load_strict_json(QUALIFICATION),
        "production_tensor_kernel_ir_v1.schema.json": load_strict_json(
            deployment / "ir/tensor_kernel_ir.json"
        ),
        "rmsnorm_physical_plan_v1.schema.json": load_strict_json(
            deployment / "physical/physical_plan.json"
        ),
        "rmsnorm_request_v1.schema.json": load_strict_json(
            deployment / "request/execution_request.json"
        ),
        "rmsnorm_source_lock_v1.schema.json": load_strict_json(
            deployment / "source.lock.json"
        ),
        "rmsnorm_independent_check_v1.schema.json": load_strict_json(
            deployment / "checks/independent_check.json"
        ),
        "rmsnorm_expectations_v1.schema.json": load_strict_json(
            deployment / "execution_expectations.json"
        ),
        "rmsnorm_deployment_v1.schema.json": load_strict_json(
            deployment / "deployment_manifest.json"
        ),
        "rmsnorm_execution_v1.schema.json": report,
        "production_capability_v1.schema.json": load_strict_json(
            deployment / "capability.json"
        ),
    }
    for name, instance in instances.items():
        Draft202012Validator(schemas[name], registry=registry).validate(instance)


def test_rmsnorm_simulator_has_no_model_framework_planner_checker_or_oracle() -> None:
    module = __import__(
        "runtime.tensor_accelerator.production_rmsnorm_simulator",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8").lower()
    assert "import torch" not in source
    assert "transformers" not in source
    assert "production_rmsnorm import" not in source
    assert "production_rmsnorm_checking" not in source
    assert "runtime.reference" not in source
    assert "import qwen" not in source
    assert "compiler.qwen" not in source


@REAL
def test_build_never_overwrites_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "deployment"
    _build(output)
    before = _tree(output)
    with pytest.raises(ProductionRMSNormBuildError, match="already exists"):
        _build(output)
    assert _tree(output) == before
