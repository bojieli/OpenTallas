from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any

import pytest
from jsonschema import Draft202012Validator
import runtime.service_engine.deepseek_v4_fp8_linear as fp8_service_module

from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_application import (
    DeepSeekV4ApplicationCheckError,
)
from compiler.checking.deepseek_v4_fp8_linear_slice import (
    DeepSeekV4FP8LinearCheckError,
    verify_deepseek_v4_fp8_linear_roundtrip,
)
from compiler.checking.deepseek_v4_fp8_linear_execution import (
    DeepSeekV4FP8LinearDifferentialError,
    verify_deepseek_v4_fp8_linear_execution,
)
from compiler.cli.main import main as compiler_main
from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from compiler.vertical_slice.deepseek_v4_fp8_linear import (
    DeepSeekV4FP8LinearBuildError,
    build_deepseek_v4_fp8_linear_deployment,
)
from runtime.reference.matrix import dense_fp8_linear_selected_rows_bf16
from runtime.service_engine.deepseek_v4_fp8_linear import (
    REQUEST_SCHEMA,
    DeepSeekV4FP8LinearServiceEngine,
    DeepSeekV4FP8LinearServiceEngineError,
)
from runtime.service_engine.cli import main as service_engine_main


FIXTURE_REVISION = "1234567890abcdef1234567890abcdef12345678"
WEIGHT_NAME = "layers.0.attn.wq_a.weight"
SCALE_NAME = "layers.0.attn.wq_a.scale"
ROOT = Path(__file__).resolve().parents[2]
FP8_SCHEMA_DIR = ROOT / "schemas/compiler/deepseek_v4_fp8_linear"


def _safetensors(tensors: list[tuple[str, str, list[int], bytes]]) -> bytes:
    header: dict[str, Any] = {}
    payload = bytearray()
    for name, dtype, shape, tensor_payload in tensors:
        start = len(payload)
        payload.extend(tensor_payload)
        header[name] = {
            "data_offsets": [start, len(payload)],
            "dtype": dtype,
            "shape": shape,
        }
    raw_header = json.dumps(
        header, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    raw_header += b" " * (-len(raw_header) % 8)
    return struct.pack("<Q", len(raw_header)) + raw_header + bytes(payload)


def _output(
    name: str,
    *,
    rank: int,
    shape: list[int],
    dtype: str,
    logical_dtype: str,
    payload_bytes: int,
) -> dict[str, Any]:
    return {
        "logical_dtype": logical_dtype,
        "name": name,
        "payload_bytes": payload_bytes,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": shape,
        "source_slice": None,
        "storage_dtype": dtype,
        "transform": "identity",
    }


def _plan() -> list[dict[str, Any]]:
    return [
        {
            "action": "replicate_identity",
            "logical_dtype": "UE8M0_SCALE",
            "name": SCALE_NAME,
            "outputs": [
                _output(
                    SCALE_NAME,
                    rank=rank,
                    shape=[3, 2],
                    dtype="F8_E8M0",
                    logical_dtype="UE8M0_SCALE",
                    payload_bytes=6,
                )
                for rank in range(2)
            ],
            "semantic_role": "attention.query_a.scale",
            "shape": [3, 2],
            "size_bytes": 6,
            "storage_dtype": "F8_E8M0",
        },
        {
            "action": "replicate_identity",
            "logical_dtype": "FP8_E4M3FN",
            "name": WEIGHT_NAME,
            "outputs": [
                _output(
                    WEIGHT_NAME,
                    rank=rank,
                    shape=[257, 256],
                    dtype="F8_E4M3",
                    logical_dtype="FP8_E4M3FN",
                    payload_bytes=257 * 256,
                )
                for rank in range(2)
            ],
            "semantic_role": "attention.query_a.weight",
            "shape": [257, 256],
            "size_bytes": 257 * 256,
            "storage_dtype": "F8_E4M3",
        },
    ]


@pytest.fixture
def fp8_linear_application(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], Path, bytes, bytes]:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    weight = bytes((index * 11 + 3) % 0x7F for index in range(257 * 256))
    scale = bytes((0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82))
    tensors = [
        (SCALE_NAME, "F8_E8M0", [3, 2], scale),
        (WEIGHT_NAME, "F8_E4M3", [257, 256], weight),
    ]
    shard = _safetensors(tensors)
    config = canonical_json_bytes({"architectures": ["FP8LinearFixture"]})
    index = canonical_json_bytes(
        {
            "metadata": {"total_size": len(weight) + len(scale)},
            "weight_map": {name: "model.safetensors" for name, _, _, _ in tensors},
        }
    )
    payloads = {
        "config.json": config,
        "model.safetensors": shard,
        "model.safetensors.index.json": index,
    }
    for name, payload in payloads.items():
        (snapshot / name).write_bytes(payload)
    source = validate_checkpoint_source(
        {
            "checkpoint_index": "model.safetensors.index.json",
            "expected_files": [
                {
                    "path": name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
                for name, payload in sorted(payloads.items())
            ],
            "remote_code_policy": "disabled",
            "repository": "OpenTallas/deepseek-v4-fp8-linear-fixture",
            "required_files": ["config.json"],
            "revision": FIXTURE_REVISION,
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    plan = _plan()
    application = tmp_path / "canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_fp8_linear_fixture_plan.v1",
        plan_inputs=plan,
        output=application,
    )
    return snapshot, lock, application, weight, scale


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_fp8_linear_slice_builds_deterministically_from_canonical_tensors(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, weight, scale = fp8_linear_application
    rows = (0, 127, 128, 256)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=first,
        output_rows=rows,
    )
    second_manifest = build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
        output_rows=rows,
    )
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["status"] == (
        "development_fixture_selected_fp8_linear_rows_not_release_evidence"
    )
    assert (first / "rom/query_a.weight.bin").read_bytes() == weight
    assert (first / "rom/query_a.scale.bin").read_bytes() == scale
    assert (first / "rom/output_rows.bin").read_bytes() == struct.pack(
        "<4I", *rows
    )
    semantic = load_strict_json(first / "model.ir.json")
    assert semantic["dimensions"] == {
        "block_size": 128,
        "input_features": 256,
        "output_features": 257,
        "selected_output_rows": list(rows),
    }
    assert verify_deepseek_v4_fp8_linear_roundtrip(first, application) == (
        load_strict_json(first / "roundtrip_report.json")
    )


def test_fp8_linear_slice_rejects_reserved_weight_code_atomically(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    weight_path = application / f"ranks/rank-000/{WEIGHT_NAME}.bin"
    changed = bytearray(weight_path.read_bytes())
    changed[0] = 0x7F
    weight_path.write_bytes(changed)
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4ApplicationCheckError, match="differs"):
        build_deepseek_v4_fp8_linear_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
            output_rows=(0,),
        )
    assert not output.exists()


def test_fp8_linear_roundtrip_rejects_deployment_tampering(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    output = tmp_path / "deployment"
    build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
        output_rows=(0, 128, 256),
    )
    path = output / "rom/query_a.weight.bin"
    changed = bytearray(path.read_bytes())
    changed[-1] ^= 1
    path.write_bytes(changed)
    with pytest.raises(DeepSeekV4FP8LinearCheckError, match="differs"):
        verify_deepseek_v4_fp8_linear_roundtrip(output, application)


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ((), "non-empty"),
        ((128, 127), "strictly increasing"),
        ((0, 0), "strictly increasing"),
        ((257,), "must be in"),
    ],
)
def test_fp8_linear_slice_rejects_illegal_output_selection(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    rows,
    match: str,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    with pytest.raises(DeepSeekV4FP8LinearBuildError, match=match):
        build_deepseek_v4_fp8_linear_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=tmp_path / f"output-{len(rows)}",
            output_rows=rows,
        )


def test_fp8_linear_slice_refuses_existing_output(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(DeepSeekV4FP8LinearBuildError, match="already exists"):
        build_deepseek_v4_fp8_linear_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
            output_rows=(0,),
        )


def _build_fp8_fixture_deployment(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    output: Path,
    *,
    rows: tuple[int, ...] = (0, 127, 128, 256),
) -> tuple[Path, bytes, bytes]:
    snapshot, lock, application, weight, scale = fp8_linear_application
    build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
        output_rows=rows,
    )
    return output, weight, scale


def _fp8_request(
    deployment: Path, path: Path, inputs: tuple[tuple[int, ...], ...]
) -> Path:
    manifest = load_strict_json(deployment / "deployment_manifest.json")
    write_canonical_json(
        path,
        {
            "build_id": manifest["build_id"],
            "input_bf16_codes": [list(row) for row in inputs],
            "model_id": "deepseek-v4-flash-0731",
            "schema": REQUEST_SCHEMA,
        },
    )
    return path


def _finite_inputs() -> tuple[tuple[int, ...], ...]:
    return (
        tuple(0x3E80 + index % 0x100 for index in range(256)),
        tuple(0xBE80 + (index * 7) % 0x100 for index in range(256)),
    )


def test_fp8_service_engine_executes_artifacts_and_matches_independent_reference(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    selected_rows = (0, 127, 128, 256)
    deployment, weight, scale = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment", rows=selected_rows
    )
    inputs = _finite_inputs()
    request = _fp8_request(deployment, tmp_path / "request.json", inputs)
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)

    expected = dense_fp8_linear_selected_rows_bf16(
        inputs,
        tuple(
            tuple(weight[row * 256 : (row + 1) * 256]) for row in selected_rows
        ),
        tuple(tuple(scale[start : start + 2]) for start in range(0, len(scale), 2)),
        output_row_indices=selected_rows,
        declared_output_count=257,
    )
    assert result["outputs"] == [
        {
            "dtype": "BF16_BITS",
            "id": "output_bf16_codes",
            "logical_output_rows": list(selected_rows),
            "shape": [2, 4],
            "values": [list(row) for row in expected.values],
        }
    ]
    assert result["numeric_status"] == {
        "activation_saturated_block_count": (
            expected.activation_saturated_block_count
        ),
        "output_saturated_element_count": expected.output_saturated_element_count,
        "poison": False,
    }
    assert result["counters"] == {
        "activation_blocks_quantized": 4,
        "activation_values_quantized": 512,
        "bf16_outputs_written": 8,
        "binary32_block_reduction_adds": 8,
        "binary32_product_accumulates": 2048,
        "completion_events": 1,
        "logical_input_bytes_read": 1024,
        "logical_output_bytes_written": 16,
        "logical_rom_bytes_read": 2064,
        "matrix_block_dots": 16,
        "micro_ops_executed": 2,
        "semantic_operations_executed": 1,
    }
    assert result["counter_reconciliation"] == "exact"
    assert result["execution_scope"] == "selected_output_rows_arithmetic_slice_only"
    assert result["status"] == "pass"


def test_fp8_service_engine_memory_maps_payloads_instead_of_materializing_them(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment"
    )
    request = _fp8_request(deployment, tmp_path / "request.json", (_finite_inputs()[0],))
    original = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path.name in {"query_a.weight.bin", "query_a.scale.bin"}:
            raise AssertionError(f"ROM payload was materialized through read_bytes: {path}")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    assert DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)[
        "status"
    ] == "pass"


def test_fp8_service_engine_rejects_request_numeric_and_artifact_tampering(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment"
    )
    inputs = _finite_inputs()
    request = _fp8_request(deployment, tmp_path / "request.json", (inputs[0],))
    malformed = load_strict_json(request)
    malformed["unexpected"] = 1
    write_canonical_json(tmp_path / "bad-request.json", malformed)
    engine = DeepSeekV4FP8LinearServiceEngine.load(deployment)
    with pytest.raises(DeepSeekV4FP8LinearServiceEngineError, match="fields differ"):
        engine.execute(tmp_path / "bad-request.json")

    poisoned = list(inputs[0])
    poisoned[17] = 0x7F80
    poison_request = _fp8_request(
        deployment, tmp_path / "poison-request.json", (tuple(poisoned),)
    )
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError, match="numeric poison.*NaN or infinity"
    ):
        engine.execute(poison_request)

    payload_path = deployment / "rom/query_a.scale.bin"
    payload = bytearray(payload_path.read_bytes())
    payload[0] ^= 1
    payload_path.write_bytes(payload)
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError,
        match="runtime artifact.*differs from deployment",
    ):
        engine.execute(request)
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError,
        match="differs from deployment manifest",
    ):
        DeepSeekV4FP8LinearServiceEngine.load(deployment)


def test_fp8_service_engine_rejects_atomic_artifact_replacement_during_execution(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment"
    )
    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    engine = DeepSeekV4FP8LinearServiceEngine.load(deployment)
    weight_path = deployment / "rom/query_a.weight.bin"
    original_execute = fp8_service_module.execute_selected_rows

    def execute_and_replace(*args, **kwargs):
        result = original_execute(*args, **kwargs)
        replacement = weight_path.with_name("replacement.bin")
        replacement.write_bytes(weight_path.read_bytes())
        replacement.replace(weight_path)
        return result

    monkeypatch.setattr(
        fp8_service_module, "execute_selected_rows", execute_and_replace
    )
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError,
        match="runtime artifact.*changed during execution",
    ):
        engine.execute(request)


def test_fp8_execution_checker_streams_locked_checkpoint_and_rejects_drift(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    selected_rows = (0, 127, 128, 256)
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment", rows=selected_rows
    )
    request = _fp8_request(deployment, tmp_path / "request.json", _finite_inputs())
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)
    report = verify_deepseek_v4_fp8_linear_execution(
        snapshot=snapshot,
        lock=lock,
        deployment_root=deployment,
        request_path=request,
        result_path=result_path,
    )
    assert report["status"] == (
        "exact_locked_checkpoint_selected_row_differential"
    )
    assert report["selected_output_rows"] == list(selected_rows)
    assert report["comparison"]["status"] == "exact"
    assert report["comparison"]["expected_sha256"] == (
        report["comparison"]["observed_sha256"]
    )
    assert all(
        record["deployment_sha256"] == record["payload_sha256"]
        for record in report["source_tensors"]
    )

    result["outputs"][0]["values"][0][0] ^= 1
    write_canonical_json(tmp_path / "tampered-result.json", result)
    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError,
        match="differs from locked checkpoint semantics",
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request,
            result_path=tmp_path / "tampered-result.json",
        )


def test_fp8_execution_checker_rejects_self_consistent_coverage_overstatement(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment"
    )
    request_path = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request_path)

    coverage_path = deployment / "operator_coverage.json"
    coverage = load_strict_json(coverage_path)
    coverage["status"] = "complete_transformer_block"
    write_canonical_json(coverage_path, coverage)
    manifest_path = deployment / "deployment_manifest.json"
    manifest = load_strict_json(manifest_path)
    for record in manifest["artifacts"]:
        if record["role"] == "operator_coverage":
            payload = coverage_path.read_bytes()
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["size_bytes"] = len(payload)
            break
    identity = {
        "artifacts": manifest["artifacts"],
        "compiler_version": manifest["compiler"]["version"],
        "microcode_abi": manifest["microcode_abi"],
        "model_id": manifest["model_id"],
        "source_application_id": manifest["source_application_id"],
    }
    manifest["build_id"] = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    write_canonical_json(manifest_path, manifest)
    request = load_strict_json(request_path)
    request["build_id"] = manifest["build_id"]
    write_canonical_json(request_path, request)
    result["build_id"] = manifest["build_id"]
    result["request_sha256"] = hashlib.sha256(
        canonical_json_bytes(request)
    ).hexdigest()
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)

    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError, match="coverage ledger differs"
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request_path,
            result_path=result_path,
        )


def test_fp8_compiler_service_and_checker_cli_dispatch_end_to_end(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    lock_path = tmp_path / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)
    deployment = tmp_path / "deployment"
    command = [
        "compile-deepseek-v4-fp8-linear-slice",
        "--snapshot",
        str(snapshot),
        "--lock",
        str(lock_path),
        "--application",
        str(application),
        "--output",
        str(deployment),
    ]
    for row in (0, 127, 128, 256):
        command.extend(("--output-row", str(row)))
    assert compiler_main(command) == 0
    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    result_path = tmp_path / "result.json"
    assert (
        service_engine_main(
            [
                "--deployment",
                str(deployment),
                "--inputs",
                str(request),
                "--output",
                str(result_path),
            ]
        )
        == 0
    )
    assert load_strict_json(result_path)["execution_scope"] == (
        "selected_output_rows_arithmetic_slice_only"
    )
    differential_path = tmp_path / "differential.json"
    assert (
        compiler_main(
            [
                "verify-deepseek-v4-fp8-linear-execution",
                "--snapshot",
                str(snapshot),
                "--lock",
                str(lock_path),
                "--deployment",
                str(deployment),
                "--request",
                str(request),
                "--result",
                str(result_path),
                "--output",
                str(differential_path),
            ]
        )
        == 0
    )
    assert load_strict_json(differential_path)["status"] == (
        "exact_locked_checkpoint_selected_row_differential"
    )


def test_fp8_schema_set_is_strict_and_validates_every_json_boundary(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    expected = {
        "deployment_v1.schema.json",
        "differential_v1.schema.json",
        "execution_expectations_v1.schema.json",
        "execution_request_v1.schema.json",
        "execution_result_v1.schema.json",
        "operator_coverage_v1.schema.json",
        "roundtrip_v1.schema.json",
        "semantic_slice_v1.schema.json",
        "tensor_manifest_v1.schema.json",
    }
    paths = sorted(FP8_SCHEMA_DIR.glob("*.schema.json"))
    assert {path.name for path in paths} == expected
    schemas = {}
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        schemas[path.name] = Draft202012Validator(schema)

    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_fixture_deployment(
        fp8_linear_application, tmp_path / "deployment"
    )
    documents = {
        "deployment_v1.schema.json": "deployment_manifest.json",
        "execution_expectations_v1.schema.json": "execution_expectations.json",
        "operator_coverage_v1.schema.json": "operator_coverage.json",
        "roundtrip_v1.schema.json": "roundtrip_report.json",
        "semantic_slice_v1.schema.json": "model.ir.json",
        "tensor_manifest_v1.schema.json": "tensor_manifest.json",
    }
    for schema_name, document_name in documents.items():
        schemas[schema_name].validate(load_strict_json(deployment / document_name))
    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    schemas["execution_request_v1.schema.json"].validate(load_strict_json(request))
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    schemas["execution_result_v1.schema.json"].validate(result)
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)
    differential = verify_deepseek_v4_fp8_linear_execution(
        snapshot=snapshot,
        lock=lock,
        deployment_root=deployment,
        request_path=request,
        result_path=result_path,
    )
    schemas["differential_v1.schema.json"].validate(differential)
