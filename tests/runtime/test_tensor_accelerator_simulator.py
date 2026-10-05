from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator import build_deployment
from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from runtime.reference.tensor_accelerator import (
    evaluate_tensor_accelerator_reference,
)
from runtime.tensor_accelerator import SimulationError, TensorAcceleratorSimulator


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "testdata/compiler/tensor_accelerator_fixture"
MODEL = FIXTURE / "model_graph.json"
CAPABILITY = FIXTURE / "capability.json"
REQUEST = FIXTURE / "execution_request.json"
KNOWN = FIXTURE / "known_answers.json"


@pytest.fixture
def deployment(tmp_path: Path) -> Path:
    output = tmp_path / "deployment"
    build_deployment(MODEL, CAPABILITY, output)
    return output


def test_artifact_only_data_bearing_timing_matches_independent_reference(
    deployment: Path,
) -> None:
    simulator = TensorAcceleratorSimulator.load(deployment)
    timed = simulator.execute(REQUEST, mode="data_bearing_timing")
    functional = simulator.execute(REQUEST, mode="functional")
    reference = evaluate_tensor_accelerator_reference(MODEL, REQUEST)
    known = load_strict_json(KNOWN)
    assert timed["status"] == functional["status"] == reference["status"] == "pass"
    assert timed["outputs"] == functional["outputs"] == reference["outputs"]
    assert timed["outputs"] == known["outputs"]
    assert timed["request_sha256"] == reference["request_sha256"] == known[
        "request_sha256"
    ]
    assert timed["semantic_sha256"] == reference["semantic_sha256"] == known[
        "semantic_sha256"
    ]
    assert timed["counter_reconciliation"] == "exact"
    assert timed["timing"] == {
        "clock_hz": 100000000,
        "cycles": 69,
        "seconds": 6.9e-07,
    }
    assert [record["opcode"] for record in timed["trace"]] == [
        "DMA_HBM_TO_SRAM",
        "MATMUL_I8_I8_I32",
        "DMA_HBM_TO_SRAM",
        "ADD_I32",
        "COMPLETE",
    ]


def test_simulator_rejects_manifested_artifact_tamper(deployment: Path) -> None:
    image = deployment / "memory/hbm_weights.bin"
    payload = bytearray(image.read_bytes())
    payload[0] ^= 1
    image.write_bytes(payload)
    with pytest.raises(SimulationError, match="SHA-256 mismatch"):
        TensorAcceleratorSimulator.load(deployment)


def test_simulator_rejects_forged_counter_expectations(deployment: Path) -> None:
    expectations_path = deployment / "execution_expectations.json"
    expectations = load_strict_json(expectations_path)
    expectations["counters"]["cycles"] += 1
    write_canonical_json(expectations_path, expectations)

    manifest_path = deployment / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    for artifact in manifest["artifacts"]:
        if artifact["role"] == "execution_expectations":
            payload = expectations_path.read_bytes()
            artifact["sha256"] = hashlib.sha256(payload).hexdigest()
            artifact["size_bytes"] = len(payload)
    body = {key: value for key, value in manifest.items() if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    write_canonical_json(manifest_path, manifest)
    with pytest.raises(SimulationError, match="expectations are incomplete"):
        TensorAcceleratorSimulator.load(deployment)


def test_request_identity_and_value_bounds_fail_closed(
    deployment: Path,
    tmp_path: Path,
) -> None:
    missing = load_strict_json(REQUEST)
    missing["tensors"] = []
    missing_path = tmp_path / "missing.json"
    write_canonical_json(missing_path, missing)
    with pytest.raises(SimulationError, match="lacks required input"):
        TensorAcceleratorSimulator.load(deployment).execute(missing_path)

    out_of_range = load_strict_json(REQUEST)
    out_of_range["tensors"][0]["values"][0] = 128
    out_of_range_path = tmp_path / "out-of-range.json"
    write_canonical_json(out_of_range_path, out_of_range)
    with pytest.raises(SimulationError, match="outside i8"):
        TensorAcceleratorSimulator.load(deployment).execute(out_of_range_path)


def test_reference_oracle_has_no_compiler_or_simulator_dependency() -> None:
    module = __import__(
        "runtime.reference.tensor_accelerator",
        fromlist=["unused"],
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert evaluate_tensor_accelerator_reference(MODEL, REQUEST)["outputs"] == (
        load_strict_json(KNOWN)["outputs"]
    )
