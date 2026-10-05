from __future__ import annotations

from pathlib import Path

import pytest

from compiler.build import build_deployment
from compiler.ir.model import load_strict_json, write_canonical_json
from runtime.reference import ReferenceError, evaluate_reference
from runtime.service_engine import ServiceEngine, ServiceEngineError


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "testdata/compiler/linear_fixture"
MODEL = FIXTURE / "model.ir.json"
REQUEST = FIXTURE / "execution_input.json"
KNOWN = FIXTURE / "known_answers.json"


@pytest.fixture
def deployment(tmp_path: Path) -> Path:
    output = tmp_path / "deployment"
    build_deployment(MODEL, output)
    return output


def test_artifact_only_service_engine_matches_independent_reference_and_known_answer(
    deployment: Path,
) -> None:
    # The deployment contains neither source ROM values nor the known answer.
    assert not (deployment / "known_answers.json").exists()
    service = ServiceEngine.load(deployment).execute(REQUEST)
    reference = evaluate_reference(MODEL, REQUEST)
    known = load_strict_json(KNOWN)
    assert service["status"] == "pass"
    assert service["outputs"] == reference["outputs"] == known["outputs"]
    assert service["request_sha256"] == reference["request_sha256"] == known[
        "request_sha256"
    ]
    assert service["semantic_sha256"] == reference["semantic_sha256"] == known[
        "semantic_sha256"
    ]
    assert service["counter_reconciliation"] == "exact"
    assert service["counters"] == {
        "activation_tensor_reads": 2,
        "completion_events": 1,
        "elementwise_add_operations": 3,
        "logical_activation_bytes_read": 16,
        "logical_activation_bytes_written": 24,
        "logical_rom_bytes_read": 24,
        "micro_ops_executed": 3,
        "rom_tensor_reads": 2,
        "scalar_accumulate_add_operations": 12,
        "scalar_multiply_operations": 12,
        "semantic_operations_executed": 2,
    }


def test_service_engine_rejects_any_manifested_artifact_tamper(
    deployment: Path,
) -> None:
    image_path = deployment / "rom_stage00_image.bin"
    image = bytearray(image_path.read_bytes())
    image[0] ^= 1
    image_path.write_bytes(image)
    with pytest.raises(ServiceEngineError, match="SHA-256 mismatch"):
        ServiceEngine.load(deployment)


def test_service_engine_rejects_counter_contract_tamper(deployment: Path) -> None:
    expectations = deployment / "execution_expectations.json"
    value = load_strict_json(expectations)
    value["counters"]["logical_rom_bytes_read"] += 1
    write_canonical_json(expectations, value)
    with pytest.raises(ServiceEngineError, match="SHA-256 mismatch"):
        ServiceEngine.load(deployment)


def test_service_engine_rejects_entrypoint_role_drift(deployment: Path) -> None:
    manifest_path = deployment / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["entrypoint"]["semantic_ir"] = "operator_coverage.json"
    write_canonical_json(manifest_path, manifest)
    with pytest.raises(ServiceEngineError, match="entrypoint differs"):
        ServiceEngine.load(deployment)


def test_service_engine_rejects_missing_and_out_of_range_inputs(
    deployment: Path, tmp_path: Path
) -> None:
    missing = load_strict_json(REQUEST)
    missing["tensors"] = []
    missing_path = tmp_path / "missing.json"
    write_canonical_json(missing_path, missing)
    with pytest.raises(ServiceEngineError, match="lacks inputs"):
        ServiceEngine.load(deployment).execute(missing_path)

    out_of_range = load_strict_json(REQUEST)
    out_of_range["tensors"][0]["values"][0] = 128
    out_of_range_path = tmp_path / "out-of-range.json"
    write_canonical_json(out_of_range_path, out_of_range)
    with pytest.raises(ServiceEngineError, match="outside i8"):
        ServiceEngine.load(deployment).execute(out_of_range_path)
    with pytest.raises(ReferenceError, match="outside i8"):
        evaluate_reference(MODEL, out_of_range_path)


def test_reference_path_does_not_import_service_or_lowering_modules() -> None:
    module = __import__("runtime.reference.evaluator", fromlist=["unused"])
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "runtime.service_engine" not in source
    assert "compiler.microcode" not in source
    assert "compiler.image" not in source
    assert evaluate_reference(MODEL, REQUEST)["outputs"] == load_strict_json(KNOWN)[
        "outputs"
    ]
