from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator import build_deployment
from compiler.tensor_accelerator.build import TensorAcceleratorBuildError
from compiler.tensor_accelerator.checking import (
    IndependentCheckError,
    check_candidate,
)
from compiler.tensor_accelerator.command import CommandError, decode
from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.model import ModelGraphError
from compiler.tensor_accelerator.physical import PhysicalPlanError


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "testdata/compiler/tensor_accelerator_fixture"
MODEL = FIXTURE / "model_graph.json"
CAPABILITY = FIXTURE / "capability.json"


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _rehash_capability(value: dict[str, object]) -> None:
    body = dict(value)
    body.pop("capability_id", None)
    value["capability_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_hbm_sram_compiler_is_byte_deterministic_and_payload_free_at_runtime(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = build_deployment(MODEL, CAPABILITY, first)
    second_manifest = build_deployment(MODEL, CAPABILITY, second)
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["build_id"] == (
        "911973425e81802135e884fe66255564fc43a1cbca9e86bf674107d59f2b1b6f"
    )
    runtime_graph = load_strict_json(first / "ir/model_graph.json")
    assert all("values" not in tensor for tensor in runtime_graph["tensors"])
    assert not (first / "known_answers.json").exists()
    assert set(record["role"] for record in first_manifest["artifacts"]) == {
        "command_disassembly",
        "command_program",
        "execution_expectations",
        "hardware_capability",
        "hbm_image",
        "independent_check",
        "model_graph",
        "operator_coverage",
        "physical_plan",
        "source_lock",
        "tensor_kernel_ir",
    }


def test_independent_checker_reconstructs_every_hbm_payload_and_schedule(
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    build_deployment(MODEL, CAPABILITY, output)
    observed = check_candidate(
        source_model=MODEL,
        source_capability=CAPABILITY,
        root=output,
    )
    assert observed == load_strict_json(output / "checks/independent_check.json")
    assert observed["status"] == "pass"
    assert observed["command_count"] == 5
    assert observed["expected_counters"]["cycles"] == 69
    assert observed["expected_counters"]["hbm_useful_bytes_read"] == 36
    assert [record["tensor_id"] for record in observed["reconstructed_tensors"]] == [
        "projection_weight",
        "projection_bias",
    ]


def test_command_stream_and_hbm_padding_corruption_fail_closed(
    tmp_path: Path,
) -> None:
    output = tmp_path / "deployment"
    build_deployment(MODEL, CAPABILITY, output)
    commands = bytearray((output / "program/commands.bin").read_bytes())
    commands[-1] ^= 1
    with pytest.raises(CommandError, match="CRC32"):
        decode(bytes(commands))

    image = bytearray((output / "memory/hbm_weights.bin").read_bytes())
    image[-1] = 1
    (output / "memory/hbm_weights.bin").write_bytes(image)
    plan_path = output / "physical/physical_plan.json"
    plan = load_strict_json(plan_path)
    plan["hbm"]["image"]["sha256"] = hashlib.sha256(image).hexdigest()
    plan["physical_plan_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in plan.items() if key != "physical_plan_id"}
        )
    ).hexdigest()
    write_canonical_json(plan_path, plan)
    with pytest.raises(IndependentCheckError, match="padding is nonzero"):
        check_candidate(
            source_model=MODEL,
            source_capability=CAPABILITY,
            root=output,
        )


def test_unsupported_operation_and_sram_topology_fail_closed(tmp_path: Path) -> None:
    source = load_strict_json(MODEL)
    unsupported = copy.deepcopy(source)
    unsupported["operations"][1]["kind"] = "RMS_NORM"
    unsupported_path = tmp_path / "unsupported.json"
    write_canonical_json(unsupported_path, unsupported)
    with pytest.raises(TensorAcceleratorBuildError, match="unsupported operations"):
        build_deployment(
            unsupported_path,
            CAPABILITY,
            tmp_path / "unsupported-output",
        )

    capability = load_strict_json(CAPABILITY)
    capability["sram"]["banks"] = 1
    _rehash_capability(capability)
    capability_path = tmp_path / "small-capability.json"
    write_canonical_json(capability_path, capability)
    with pytest.raises(PhysicalPlanError, match="at least two SRAM banks"):
        build_deployment(
            MODEL,
            capability_path,
            tmp_path / "small-output",
        )


def test_backend_neutral_graph_rejects_rom_semantics_and_implicit_broadcast(
    tmp_path: Path,
) -> None:
    source = load_strict_json(MODEL)
    rom_kind = copy.deepcopy(source)
    rom_kind["operations"][0]["kind"] = "ROM_MATMUL"
    rom_path = tmp_path / "rom-kind.json"
    write_canonical_json(rom_path, rom_kind)
    with pytest.raises(ModelGraphError, match="unknown kind"):
        build_deployment(rom_path, CAPABILITY, tmp_path / "rom-kind-output")

    broadcast = copy.deepcopy(source)
    broadcast["tensors"][3]["shape"] = [3]
    broadcast["tensors"][3]["values"] = [1, 2, 3]
    broadcast_path = tmp_path / "broadcast.json"
    write_canonical_json(broadcast_path, broadcast)
    with pytest.raises(ModelGraphError, match="implicit broadcasting"):
        build_deployment(
            broadcast_path,
            CAPABILITY,
            tmp_path / "broadcast-output",
        )


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "deployment"
    output.mkdir()
    marker = output / "owner"
    marker.write_text("user\n", encoding="utf-8")
    with pytest.raises(TensorAcceleratorBuildError, match="already exists"):
        build_deployment(MODEL, CAPABILITY, output)
    assert marker.read_text(encoding="utf-8") == "user\n"
