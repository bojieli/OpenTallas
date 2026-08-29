from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Any

import pytest
from jsonschema import Draft202012Validator
import compiler.checking.deepseek_v4_fp8_linear_execution as fp8_checker_module
import compiler.vertical_slice.deepseek_v4_fp8_linear as fp8_build_module
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
from compiler.frontend.deepseek_v4 import (
    CONFIG_SHA256,
    INDEX_SHA256,
    REPOSITORY,
    REVISION,
    DeepSeekV4AdapterError,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from compiler.vertical_slice.deepseek_v4_fp8_linear import (
    DeepSeekV4FP8LinearBuildError,
    build_deepseek_v4_fp8_linear_deployment,
    build_deepseek_v4_fp8_linear_full_deployment,
)
from runtime.reference.matrix import (
    dense_fp8_linear_bf16,
    dense_fp8_linear_selected_rows_bf16,
)
from runtime.service_engine.deepseek_v4_fp8_linear import (
    FULL_RESULT_SCHEMA,
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
SELECTED_FIXTURE_BUILD_ID = (
    "1fb406682ea620112eeadd4d7cc7b128a605af5a177058f8ed530633dadfe579"
)
SELECTED_FIXTURE_TREE_SHA256 = (
    "b53ce05ebe23b8474f00f07b8730c0ae94e5ffa895573aa2ab7d4bd5d613cbd0"
)


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


def _materialize_fp8_linear_application(
    root: Path, *, weight: bytes, scale: bytes
) -> tuple[Path, dict[str, Any], Path, bytes, bytes]:
    if len(weight) != 257 * 256 or len(scale) != 6:
        raise ValueError("fixture weight or scale payload has the wrong extent")
    root.mkdir(parents=True, exist_ok=True)
    snapshot = root / "snapshot"
    snapshot.mkdir()
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
    application = root / "canonical"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=hashlib.sha256(canonical_json_bytes(plan)).hexdigest(),
        plan_schema="opentallas.deepseek_v4_fp8_linear_fixture_plan.v1",
        plan_inputs=plan,
        output=application,
    )
    return snapshot, lock, application, weight, scale


@pytest.fixture
def fp8_linear_application(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], Path, bytes, bytes]:
    return _materialize_fp8_linear_application(
        tmp_path,
        weight=bytes((index * 11 + 3) % 0x7F for index in range(257 * 256)),
        scale=bytes((0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82)),
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, payload in _tree(root).items():
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)
    return digest.hexdigest()


def _assert_recursive_object_schema_strict(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        raw_type = value.get("type")
        object_typed = raw_type == "object" or (
            isinstance(raw_type, list) and "object" in raw_type
        )
        if object_typed:
            assert value.get("additionalProperties") is False, (
                f"object schema at {path} is not closed"
            )
        for key, child in value.items():
            _assert_recursive_object_schema_strict(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_recursive_object_schema_strict(child, f"{path}[{index}]")


def test_fp8_linear_slice_builds_deterministically_from_canonical_tensors(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, weight, scale = fp8_linear_application
    rows = (0, 127, 128, 256)
    first = tmp_path / "first"
    complete = tmp_path / "complete"
    second = tmp_path / "second"
    first_manifest = build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=first,
        output_rows=rows,
    )
    build_deepseek_v4_fp8_linear_full_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=complete,
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
    assert first_manifest["build_id"] == SELECTED_FIXTURE_BUILD_ID
    assert _tree_sha256(first) == SELECTED_FIXTURE_TREE_SHA256
    assert _tree_sha256(second) == SELECTED_FIXTURE_TREE_SHA256
    assert _tree(complete) != _tree(first)
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


def test_fp8_linear_full_build_is_deterministic_and_selects_every_output(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, weight, scale = fp8_linear_application
    first = tmp_path / "full-first"
    second = tmp_path / "full-second"
    first_manifest = build_deepseek_v4_fp8_linear_full_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=first,
    )
    second_manifest = build_deepseek_v4_fp8_linear_full_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
    )

    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["schema"] == (
        "opentallas.deepseek_v4_fp8_linear_full_deployment.v1"
    )
    assert first_manifest["status"] == (
        "development_fixture_complete_fp8_linear_operator_not_release_evidence"
    )
    assert first_manifest["compiler"]["name"] == (
        "opentallas-deepseek-v4-fp8-linear-compiler"
    )
    assert (first / "rom/query_a.weight.bin").read_bytes() == weight
    assert (first / "rom/query_a.scale.bin").read_bytes() == scale
    all_rows = tuple(range(257))
    selection = (first / "rom/output_rows.bin").read_bytes()
    assert len(selection) == 257 * 4
    assert struct.unpack("<257I", selection) == all_rows

    tensors = load_strict_json(first / "tensor_manifest.json")
    assert tensors["schema"] == (
        "opentallas.deepseek_v4_fp8_linear_full_tensors.v1"
    )
    assert tensors["output_selection"]["rows"] == list(all_rows)
    semantic = load_strict_json(first / "model.ir.json")
    assert semantic["schema"] == "opentallas.deepseek_v4_fp8_linear_full.v1"
    assert semantic["dimensions"] == {
        "block_size": 128,
        "input_features": 256,
        "output_features": 257,
    }
    assert semantic["operation"]["kind"] == "FP8_LINEAR"
    assert semantic["numeric_profile"] == "deepseek_v4_dense_fp8_full_v1"
    assert load_strict_json(first / "operator_coverage.json") == {
        "implemented_operator_kind": "FP8_LINEAR",
        "model_id": "deepseek-v4-flash-0731",
        "schema": "opentallas.deepseek_v4_fp8_linear_full_coverage.v1",
        "status": "complete_operator_arithmetic_only",
        "underlying_graph_operator_kind": "FP8_LINEAR",
    }
    assert verify_deepseek_v4_fp8_linear_roundtrip(first, application) == (
        load_strict_json(first / "roundtrip_report.json")
    )


def test_fp8_full_build_enforces_explicit_memory_and_work_budgets(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    monkeypatch.setattr(fp8_build_module, "MAX_WEIGHT_PAYLOAD_BYTES", 1024)
    with pytest.raises(DeepSeekV4FP8LinearBuildError, match="memory budget"):
        build_deepseek_v4_fp8_linear_full_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=tmp_path / "memory-budget-rejection",
        )
    monkeypatch.setattr(fp8_build_module, "MAX_WEIGHT_PAYLOAD_BYTES", 1024 * 1024)
    monkeypatch.setattr(fp8_build_module, "MAX_FULL_PRODUCTS_PER_INPUT_ROW", 1024)
    with pytest.raises(DeepSeekV4FP8LinearBuildError, match="work budget"):
        build_deepseek_v4_fp8_linear_full_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=tmp_path / "work-budget-rejection",
        )


def test_official_checkpoint_validation_rejects_self_consistent_fake_content(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
) -> None:
    _, lock, _, _, _ = fp8_linear_application
    forged = json.loads(json.dumps(lock))
    forged["source"]["repository"] = REPOSITORY
    forged["source"]["revision"] = REVISION
    expected = {
        record["path"]: record for record in forged["source"]["expected_files"]
    }
    expected["config.json"]["sha256"] = CONFIG_SHA256
    expected["model.safetensors.index.json"]["sha256"] = INDEX_SHA256
    files = {record["path"]: record for record in forged["files"]}
    files["config.json"]["sha256"] = CONFIG_SHA256
    files["model.safetensors.index.json"]["sha256"] = INDEX_SHA256
    body = {key: value for key, value in forged.items() if key != "lock_id"}
    forged["lock_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()

    with pytest.raises(DeepSeekV4AdapterError, match="content is not the pinned"):
        validate_official_checkpoint_lock(forged, load_official_config())


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


def _build_fp8_full_fixture_deployment(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    output: Path,
) -> tuple[Path, bytes, bytes]:
    snapshot, lock, application, weight, scale = fp8_linear_application
    build_deepseek_v4_fp8_linear_full_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
    )
    return output, weight, scale


def _fixture_weight_rows(weight: bytes) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(weight[start : start + 256])
        for start in range(0, len(weight), 256)
    )


def _fixture_scale_rows(scale: bytes) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(scale[start : start + 2]) for start in range(0, len(scale), 2))


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


def test_fp8_full_service_executes_all_rows_and_matches_dense_reference(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    deployment, weight, scale = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    inputs = _finite_inputs()
    request = _fp8_request(deployment, tmp_path / "full-request.json", inputs)
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    expected = dense_fp8_linear_bf16(
        inputs,
        _fixture_weight_rows(weight),
        _fixture_scale_rows(scale),
    )
    all_rows = list(range(257))

    assert result["schema"] == FULL_RESULT_SCHEMA
    assert result["execution_scope"] == "complete_fp8_linear_operator"
    assert result["outputs"] == [
        {
            "dtype": "BF16_BITS",
            "id": "output_bf16_codes",
            "logical_output_rows": all_rows,
            "shape": [2, 257],
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
        "bf16_outputs_written": 514,
        "binary32_block_reduction_adds": 514,
        "binary32_product_accumulates": 131584,
        "completion_events": 1,
        "logical_input_bytes_read": 1024,
        "logical_output_bytes_written": 1028,
        "logical_rom_bytes_read": 132612,
        "matrix_block_dots": 1028,
        "micro_ops_executed": 2,
        "semantic_operations_executed": 1,
    }
    assert result["counter_reconciliation"] == "exact"
    assert result["status"] == "pass"


def test_fp8_full_counters_scale_per_input_and_report_finite_saturation(
    tmp_path: Path,
) -> None:
    weight = bytearray(257 * 256)
    weight[:7] = bytes((0x30, 0x28, 0x20, 0x18, 0x10, 0x08, 0x07))
    application = _materialize_fp8_linear_application(
        tmp_path / "saturation-source",
        weight=bytes(weight),
        scale=bytes((0x7F,) * 6),
    )
    deployment, retained_weight, retained_scale = _build_fp8_full_fixture_deployment(
        application, tmp_path / "saturation-deployment"
    )
    saturating = tuple((0x7F7F if index < 7 else 0) for index in range(256))
    inputs = (saturating, (0,) * 256, (0,) * 256)
    request = _fp8_request(
        deployment, tmp_path / "saturation-request.json", inputs
    )
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    expected = dense_fp8_linear_bf16(
        inputs,
        _fixture_weight_rows(retained_weight),
        _fixture_scale_rows(retained_scale),
    )

    assert expected.activation_saturated_block_count == 0
    assert expected.output_saturated_element_count == 1
    assert expected.values[0][0] == 0x7F7F
    assert result["numeric_status"] == {
        "activation_saturated_block_count": 0,
        "output_saturated_element_count": 1,
        "poison": False,
    }
    assert result["outputs"][0]["values"] == [
        list(row) for row in expected.values
    ]
    assert result["counters"] == {
        "activation_blocks_quantized": 6,
        "activation_values_quantized": 768,
        "bf16_outputs_written": 771,
        "binary32_block_reduction_adds": 771,
        "binary32_product_accumulates": 197376,
        "completion_events": 1,
        "logical_input_bytes_read": 1536,
        "logical_output_bytes_written": 1542,
        "logical_rom_bytes_read": 198918,
        "matrix_block_dots": 1542,
        "micro_ops_executed": 2,
        "semantic_operations_executed": 1,
    }


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


def test_fp8_runtime_and_checker_bound_untrusted_json_before_parsing(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * (128 * 1024) + b"}")
    engine = DeepSeekV4FP8LinearServiceEngine.load(deployment)
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError, match="exceeds its .*runtime bound"
    ):
        engine.execute(oversized)

    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError,
        match="execution result exceeds its .*checker bound",
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request,
            result_path=oversized,
        )


def test_fp8_runtime_and_checker_reject_symlink_and_fifo_json_inputs(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    engine = DeepSeekV4FP8LinearServiceEngine.load(deployment)
    result = engine.execute(request)
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)

    request_symlink = tmp_path / "request-symlink.json"
    request_symlink.symlink_to(request.name)
    with pytest.raises(
        DeepSeekV4FP8LinearServiceEngineError,
        match="without following symlinks",
    ):
        engine.execute(request_symlink)

    result_symlink = tmp_path / "result-symlink.json"
    result_symlink.symlink_to(result_path.name)
    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError,
        match="without following symlinks",
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request,
            result_path=result_symlink,
        )

    fifo = tmp_path / "untrusted.json.fifo"
    os.mkfifo(fifo)
    original_read_bytes = Path.read_bytes
    original_open = os.open
    fifo_descriptor = original_open(
        fifo,
        os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW,
    )

    def forbid_potentially_blocking_path_read(path: Path) -> bytes:
        if path == fifo:
            raise AssertionError("attempted blocking Path.read_bytes() on a FIFO")
        return original_read_bytes(path)

    def controlled_open(
        path: Any,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if dir_fd is None and Path(path) == fifo:
            assert flags & os.O_NONBLOCK
            assert flags & os.O_NOFOLLOW
            return os.dup(fifo_descriptor)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    try:
        with monkeypatch.context() as context:
            context.setattr(Path, "read_bytes", forbid_potentially_blocking_path_read)
            context.setattr(fp8_service_module.os, "open", controlled_open)
            os.supports_dir_fd.add(controlled_open)
            try:
                with pytest.raises(
                    DeepSeekV4FP8LinearServiceEngineError,
                    match="not a regular file",
                ):
                    engine.execute(fifo)
                with pytest.raises(
                    DeepSeekV4FP8LinearDifferentialError,
                    match="not a regular file",
                ):
                    verify_deepseek_v4_fp8_linear_execution(
                        snapshot=snapshot,
                        lock=lock,
                        deployment_root=deployment,
                        request_path=request,
                        result_path=fifo,
                    )
            finally:
                os.supports_dir_fd.discard(controlled_open)
    finally:
        os.close(fifo_descriptor)


def test_fp8_runtime_and_checker_reject_atomic_json_replacement_during_read(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    request = _fp8_request(
        deployment, tmp_path / "request.json", (_finite_inputs()[0],)
    )
    engine = DeepSeekV4FP8LinearServiceEngine.load(deployment)
    result = engine.execute(request)
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)

    request_payload = request.read_bytes()
    request_stat = request.stat()
    request_identity = (request_stat.st_dev, request_stat.st_ino)
    runtime_replaced = False
    runtime_pread = fp8_service_module.os.pread

    def replace_request_after_read(
        descriptor: int, length: int, offset: int
    ) -> bytes:
        nonlocal runtime_replaced
        chunk = runtime_pread(descriptor, length, offset)
        metadata = os.fstat(descriptor)
        if not runtime_replaced and (metadata.st_dev, metadata.st_ino) == request_identity:
            replacement = tmp_path / "request.replacement"
            replacement.write_bytes(request_payload)
            os.replace(replacement, request)
            runtime_replaced = True
        return chunk

    with monkeypatch.context() as context:
        context.setattr(fp8_service_module.os, "pread", replace_request_after_read)
        with pytest.raises(
            DeepSeekV4FP8LinearServiceEngineError,
            match="changed while the runtime read it|was replaced while the runtime read it",
        ):
            engine.execute(request)
    assert runtime_replaced

    result_payload = result_path.read_bytes()
    result_stat = result_path.stat()
    result_identity = (result_stat.st_dev, result_stat.st_ino)
    checker_replaced = False
    checker_pread = fp8_checker_module.os.pread

    def replace_result_after_read(
        descriptor: int, length: int, offset: int
    ) -> bytes:
        nonlocal checker_replaced
        chunk = checker_pread(descriptor, length, offset)
        metadata = os.fstat(descriptor)
        if not checker_replaced and (metadata.st_dev, metadata.st_ino) == result_identity:
            replacement = tmp_path / "result.replacement"
            replacement.write_bytes(result_payload)
            os.replace(replacement, result_path)
            checker_replaced = True
        return chunk

    with monkeypatch.context() as context:
        context.setattr(fp8_checker_module.os, "pread", replace_result_after_read)
        with pytest.raises(
            DeepSeekV4FP8LinearDifferentialError,
            match="changed while the checker read it|was replaced while the checker read it",
        ):
            verify_deepseek_v4_fp8_linear_execution(
                snapshot=snapshot,
                lock=lock,
                deployment_root=deployment,
                request_path=request,
                result_path=result_path,
            )
    assert checker_replaced


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


def test_fp8_full_execution_checker_uses_complete_dense_semantics_and_rejects_drift(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    request = _fp8_request(
        deployment, tmp_path / "full-request.json", (_finite_inputs()[0],)
    )
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    result_path = tmp_path / "full-result.json"
    write_canonical_json(result_path, result)

    dense_calls = 0
    original_dense = fp8_checker_module.dense_fp8_linear_bf16

    def tracked_dense(*args: Any, **kwargs: Any) -> Any:
        nonlocal dense_calls
        dense_calls += 1
        return original_dense(*args, **kwargs)

    def forbidden_selected(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("full checker used the selected-row reference")

    monkeypatch.setattr(
        fp8_checker_module, "dense_fp8_linear_bf16", tracked_dense
    )
    monkeypatch.setattr(
        fp8_checker_module,
        "dense_fp8_linear_selected_rows_bf16",
        forbidden_selected,
    )
    report = verify_deepseek_v4_fp8_linear_execution(
        snapshot=snapshot,
        lock=lock,
        deployment_root=deployment,
        request_path=request,
        result_path=result_path,
    )
    assert dense_calls == 1
    assert report["schema"] == (
        "opentallas.deepseek_v4_fp8_linear_full_differential.v1"
    )
    assert report["status"] == (
        "exact_locked_checkpoint_complete_fp8_linear_differential"
    )
    assert report["output_row_count"] == 257
    assert "selected_output_rows" not in report
    assert report["comparison"]["status"] == "exact"
    assert report["comparison"]["expected_sha256"] == (
        report["comparison"]["observed_sha256"]
    )
    assert all(
        record["deployment_sha256"] == record["payload_sha256"]
        for record in report["source_tensors"]
    )

    result["outputs"][0]["values"][0][256] ^= 1
    write_canonical_json(tmp_path / "tampered-full-result.json", result)
    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError,
        match="differs from locked checkpoint semantics",
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request,
            result_path=tmp_path / "tampered-full-result.json",
        )


def test_fp8_checker_rejects_byte_identical_artifact_replacement(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    request = _fp8_request(
        deployment, tmp_path / "full-request.json", (_finite_inputs()[0],)
    )
    result = DeepSeekV4FP8LinearServiceEngine.load(deployment).execute(request)
    result_path = tmp_path / "full-result.json"
    write_canonical_json(result_path, result)
    original_dense = fp8_checker_module.dense_fp8_linear_bf16
    target = deployment / "operator_coverage.json"

    def replace_artifact(*args: Any, **kwargs: Any) -> Any:
        replacement = deployment / "operator_coverage.replacement"
        replacement.write_bytes(target.read_bytes())
        os.replace(replacement, target)
        return original_dense(*args, **kwargs)

    monkeypatch.setattr(
        fp8_checker_module, "dense_fp8_linear_bf16", replace_artifact
    )
    with pytest.raises(
        DeepSeekV4FP8LinearDifferentialError,
        match="descriptor identity changed|deployment root changed|was replaced",
    ):
        verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request,
            result_path=result_path,
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


def test_fp8_full_checker_rejects_self_consistent_transformer_coverage_claim(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, _, _, _ = fp8_linear_application
    deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    request_path = _fp8_request(
        deployment, tmp_path / "full-request.json", (_finite_inputs()[0],)
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
    manifest["build_id"] = hashlib.sha256(
        canonical_json_bytes(identity)
    ).hexdigest()
    write_canonical_json(manifest_path, manifest)
    request = load_strict_json(request_path)
    request["build_id"] = manifest["build_id"]
    write_canonical_json(request_path, request)
    result["build_id"] = manifest["build_id"]
    result["request_sha256"] = hashlib.sha256(
        canonical_json_bytes(request)
    ).hexdigest()
    result_path = tmp_path / "forged-full-result.json"
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


def test_fp8_full_compiler_service_and_checker_cli_dispatch_end_to_end(
    fp8_linear_application: tuple[Path, dict[str, Any], Path, bytes, bytes],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = fp8_linear_application
    lock_path = tmp_path / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)
    deployment = tmp_path / "full-deployment"
    assert (
        compiler_main(
            [
                "compile-deepseek-v4-fp8-linear",
                "--snapshot",
                str(snapshot),
                "--lock",
                str(lock_path),
                "--application",
                str(application),
                "--output",
                str(deployment),
            ]
        )
        == 0
    )
    manifest = load_strict_json(deployment / "deployment_manifest.json")
    assert manifest["schema"] == (
        "opentallas.deepseek_v4_fp8_linear_full_deployment.v1"
    )
    request = _fp8_request(
        deployment, tmp_path / "full-request.json", (_finite_inputs()[0],)
    )
    result_path = tmp_path / "full-result.json"
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
    result = load_strict_json(result_path)
    assert result["schema"] == FULL_RESULT_SCHEMA
    assert result["execution_scope"] == "complete_fp8_linear_operator"
    assert result["outputs"][0]["shape"] == [1, 257]

    differential_path = tmp_path / "full-differential.json"
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
    differential = load_strict_json(differential_path)
    assert differential["schema"] == (
        "opentallas.deepseek_v4_fp8_linear_full_differential.v1"
    )
    assert differential["status"] == (
        "exact_locked_checkpoint_complete_fp8_linear_differential"
    )
    assert differential["output_row_count"] == 257
    assert "selected_output_rows" not in differential


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
        "full_deployment_v1.schema.json",
        "full_differential_v1.schema.json",
        "full_execution_result_v1.schema.json",
        "full_operator_coverage_v1.schema.json",
        "full_semantic_v1.schema.json",
        "full_tensor_manifest_v1.schema.json",
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
        _assert_recursive_object_schema_strict(schema)
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

    full_deployment, _, _ = _build_fp8_full_fixture_deployment(
        fp8_linear_application, tmp_path / "full-deployment"
    )
    full_documents = {
        "full_deployment_v1.schema.json": "deployment_manifest.json",
        "execution_expectations_v1.schema.json": "execution_expectations.json",
        "full_operator_coverage_v1.schema.json": "operator_coverage.json",
        "roundtrip_v1.schema.json": "roundtrip_report.json",
        "full_semantic_v1.schema.json": "model.ir.json",
        "full_tensor_manifest_v1.schema.json": "tensor_manifest.json",
    }
    for schema_name, document_name in full_documents.items():
        schemas[schema_name].validate(
            load_strict_json(full_deployment / document_name)
        )
    full_request = _fp8_request(
        full_deployment,
        tmp_path / "full-request.json",
        (_finite_inputs()[0],),
    )
    schemas["execution_request_v1.schema.json"].validate(
        load_strict_json(full_request)
    )
    full_result = DeepSeekV4FP8LinearServiceEngine.load(
        full_deployment
    ).execute(full_request)
    schemas["full_execution_result_v1.schema.json"].validate(full_result)
    full_result_path = tmp_path / "full-result.json"
    write_canonical_json(full_result_path, full_result)
    full_differential = verify_deepseek_v4_fp8_linear_execution(
        snapshot=snapshot,
        lock=lock,
        deployment_root=full_deployment,
        request_path=full_request,
        result_path=full_result_path,
    )
    schemas["full_differential_v1.schema.json"].validate(full_differential)

    for schema_name, validator in schemas.items():
        candidate: dict[str, Any]
        if schema_name == "full_deployment_v1.schema.json":
            candidate = load_strict_json(full_deployment / "deployment_manifest.json")
        elif schema_name == "full_differential_v1.schema.json":
            candidate = dict(full_differential)
        elif schema_name == "full_execution_result_v1.schema.json":
            candidate = dict(full_result)
        elif schema_name == "full_operator_coverage_v1.schema.json":
            candidate = load_strict_json(full_deployment / "operator_coverage.json")
        elif schema_name == "full_semantic_v1.schema.json":
            candidate = load_strict_json(full_deployment / "model.ir.json")
        elif schema_name == "full_tensor_manifest_v1.schema.json":
            candidate = load_strict_json(full_deployment / "tensor_manifest.json")
        else:
            continue
        candidate["unexpected"] = None
        assert list(validator.iter_errors(candidate)), (
            f"{schema_name} accepted an unknown top-level field"
        )
