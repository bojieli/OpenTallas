from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from compiler.canonical.application import apply_canonical_plan_records
from compiler.checking.deepseek_v4_lookup_slice import (
    DeepSeekV4LookupCheckError,
    verify_deepseek_v4_lookup_roundtrip,
)
from compiler.checking.deepseek_v4_application import (
    DeepSeekV4ApplicationCheckError,
)
from compiler.checking.deepseek_v4_lookup_execution import (
    DeepSeekV4LookupDifferentialError,
    verify_deepseek_v4_lookup_execution,
)
from compiler.cli.main import main as compiler_main
from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from compiler.vertical_slice.deepseek_v4_lookup import (
    DeepSeekV4LookupBuildError,
    build_deepseek_v4_lookup_deployment,
)
from runtime.reference.lookup import bf16_token_embedding, hash_route_indices
from runtime.reference.structural import hc_expand_bf16
from runtime.service_engine.deepseek_v4_lookup import (
    DeepSeekV4LookupServiceEngine,
    DeepSeekV4LookupServiceEngineError,
    REQUEST_SCHEMA,
)
from runtime.service_engine.cli import main as service_engine_main


FIXTURE_REVISION = "0123456789abcdef0123456789abcdef01234567"
ROOT = Path(__file__).resolve().parents[2]
LOOKUP_SCHEMA_DIR = ROOT / "schemas/compiler/deepseek_v4_lookup"


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
    source_slice: dict[str, int] | None,
) -> dict[str, Any]:
    return {
        "logical_dtype": logical_dtype,
        "name": name,
        "payload_bytes": payload_bytes,
        "rank": rank,
        "scale_source": None,
        "scale_source_slice": None,
        "shape": shape,
        "source_slice": source_slice,
        "storage_dtype": dtype,
        "transform": "identity",
    }


def _plan() -> list[dict[str, Any]]:
    return [
        {
            "action": "tensor_parallel_slice_axis_0",
            "logical_dtype": "BF16",
            "name": "embed.weight",
            "outputs": [
                _output(
                    "embed.weight",
                    rank=rank,
                    shape=[4, 4],
                    dtype="BF16",
                    logical_dtype="BF16",
                    payload_bytes=32,
                    source_slice={
                        "axis": 0,
                        "start": rank * 4,
                        "stop": rank * 4 + 4,
                    },
                )
                for rank in range(2)
            ],
            "semantic_role": "model.token_embedding.weight",
            "shape": [8, 4],
            "size_bytes": 64,
            "storage_dtype": "BF16",
        },
        {
            "action": "replicate_identity",
            "logical_dtype": "INT64",
            "name": "layers.0.ffn.gate.tid2eid",
            "outputs": [
                _output(
                    "layers.0.ffn.gate.tid2eid",
                    rank=rank,
                    shape=[8, 2],
                    dtype="I64",
                    logical_dtype="INT64",
                    payload_bytes=128,
                    source_slice=None,
                )
                for rank in range(2)
            ],
            "semantic_role": "moe.hash_route.table",
            "shape": [8, 2],
            "size_bytes": 128,
            "storage_dtype": "I64",
        },
    ]


@pytest.fixture
def lookup_application(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]]:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    embedding_codes = tuple(
        (row << 8) | column for row in range(8) for column in range(4)
    )
    route_values = tuple(
        value for row in range(8) for value in (row % 5, (row + 2) % 5)
    )
    tensors = [
        (
            "embed.weight",
            "BF16",
            [8, 4],
            struct.pack("<32H", *embedding_codes),
        ),
        (
            "layers.0.ffn.gate.tid2eid",
            "I64",
            [8, 2],
            struct.pack("<16q", *route_values),
        ),
    ]
    shard = _safetensors(tensors)
    config = canonical_json_bytes({"architectures": ["LookupFixture"]})
    index = canonical_json_bytes(
        {
            "metadata": {"total_size": 192},
            "weight_map": {
                name: "model.safetensors" for name, _, _, _ in tensors
            },
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
            "repository": "OpenTallas/deepseek-v4-lookup-fixture",
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
        plan_schema="opentallas.deepseek_v4_lookup_fixture_plan.v1",
        plan_inputs=plan,
        output=application,
    )
    return snapshot, lock, application, embedding_codes, route_values


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_lookup_slice_builds_deterministically_from_verified_canonical_artifacts(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, embedding_codes, route_values = lookup_application
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = build_deepseek_v4_lookup_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=first,
        hc_multiplier=3,
        expert_count=5,
    )
    second_manifest = build_deepseek_v4_lookup_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=second,
        hc_multiplier=3,
        expert_count=5,
    )
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["status"] == (
        "development_fixture_lookup_slice_not_release_evidence"
    )
    assert first_manifest["source_application_id"] == load_strict_json(
        application / "canonical_application.json"
    )["application_id"]
    semantic = load_strict_json(first / "model.ir.json")
    assert semantic["dimensions"] == {
        "expert_count": 5,
        "hc_multiplier": 3,
        "hidden_size": 4,
        "model_parallel": 2,
        "route_top_k": 2,
        "vocabulary_size": 8,
    }
    assert (first / "rom/embed/rank-000.bin").read_bytes() == struct.pack(
        "<16H", *embedding_codes[:16]
    )
    assert (first / "rom/embed/rank-001.bin").read_bytes() == struct.pack(
        "<16H", *embedding_codes[16:]
    )
    assert (first / "rom/hash_route.bin").read_bytes() == struct.pack(
        "<16q", *route_values
    )
    assert verify_deepseek_v4_lookup_roundtrip(first, application) == load_strict_json(
        first / "roundtrip_report.json"
    )


def test_lookup_slice_rejects_bad_expert_table_atomically(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = lookup_application
    route = application / "ranks/rank-000/layers.0.ffn.gate.tid2eid.bin"
    payload = bytearray(route.read_bytes())
    payload[:8] = struct.pack("<q", 5)
    route.write_bytes(payload)
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4ApplicationCheckError, match="differs"):
        build_deepseek_v4_lookup_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
            hc_multiplier=3,
            expert_count=5,
        )
    assert not output.exists()


def test_lookup_roundtrip_rejects_deployment_tampering(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = lookup_application
    output = tmp_path / "deployment"
    build_deepseek_v4_lookup_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
        hc_multiplier=3,
        expert_count=5,
    )
    path = output / "rom/embed/rank-001.bin"
    changed = bytearray(path.read_bytes())
    changed[-1] ^= 1
    path.write_bytes(changed)
    with pytest.raises(DeepSeekV4LookupCheckError, match="differs"):
        verify_deepseek_v4_lookup_roundtrip(output, application)


def test_lookup_slice_rejects_missing_required_canonical_tensor(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = lookup_application
    manifest_path = application / "canonical_application.json"
    manifest = load_strict_json(manifest_path)
    manifest["assignments"] = [
        record
        for record in manifest["assignments"]
        if record["name"] != "embed.weight"
    ]
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(DeepSeekV4ApplicationCheckError):
        build_deepseek_v4_lookup_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=tmp_path / "output",
            hc_multiplier=3,
            expert_count=5,
        )


def test_lookup_slice_refuses_existing_output(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = lookup_application
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(DeepSeekV4LookupBuildError, match="already exists"):
        build_deepseek_v4_lookup_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application,
            output=output,
            hc_multiplier=3,
            expert_count=5,
        )


def _build_lookup_fixture_deployment(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    output: Path,
) -> tuple[Path, tuple[int, ...], tuple[int, ...]]:
    snapshot, lock, application, embedding_codes, route_values = lookup_application
    build_deepseek_v4_lookup_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application,
        output=output,
        hc_multiplier=3,
        expert_count=5,
    )
    return output, embedding_codes, route_values


def _lookup_request(deployment: Path, path: Path, token_ids: list[list[int]]) -> Path:
    manifest = load_strict_json(deployment / "deployment_manifest.json")
    write_canonical_json(
        path,
        {
            "build_id": manifest["build_id"],
            "model_id": "deepseek-v4-flash-0731",
            "schema": REQUEST_SCHEMA,
            "token_ids": token_ids,
        },
    )
    return path


def test_lookup_service_engine_executes_artifacts_and_matches_independent_references(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    deployment, embedding_codes, route_values = _build_lookup_fixture_deployment(
        lookup_application, tmp_path / "deployment"
    )
    tokens = [[0, 3, 4], [7, 4, 0]]
    request = _lookup_request(deployment, tmp_path / "request.json", tokens)
    result = DeepSeekV4LookupServiceEngine.load(deployment).execute(request)

    embedding_weight = tuple(
        tuple(embedding_codes[row * 4 : row * 4 + 4]) for row in range(8)
    )
    route_table = tuple(
        tuple(route_values[row * 2 : row * 2 + 2]) for row in range(8)
    )
    expected_embedding = bf16_token_embedding(tokens, embedding_weight)
    expected_hc = hc_expand_bf16(expected_embedding, 3)
    expected_routes_flat = hash_route_indices(
        tuple(token for batch in tokens for token in batch),
        route_table,
        expert_count=5,
    )
    expected_routes = (
        expected_routes_flat[:3],
        expected_routes_flat[3:],
    )
    outputs = {record["id"]: record for record in result["outputs"]}
    assert outputs["embedding_bf16_codes"]["values"] == [
        [list(vector) for vector in batch] for batch in expected_embedding
    ]
    assert outputs["hc_hidden_bf16_codes"]["values"] == [
        [[list(vector) for vector in copies] for copies in batch]
        for batch in expected_hc
    ]
    assert outputs["expert_ids"]["values"] == [
        [list(vector) for vector in batch] for batch in expected_routes
    ]
    assert result["status"] == "pass"
    assert result["evidence_scope"] == "development_fixture"
    assert result["execution_scope"] == "three_operator_real_payload_slice_only"
    assert result["counter_reconciliation"] == "exact"
    assert result["counters"] == {
        "bf16_codes_copied": 72,
        "completion_events": 1,
        "logical_activation_bytes_read": 48,
        "logical_activation_bytes_written": 288,
        "logical_input_bytes_read": 96,
        "logical_rom_bytes_read": 144,
        "micro_ops_executed": 4,
        "rom_lookup_rows": 12,
        "semantic_operations_executed": 3,
    }


def test_lookup_service_engine_memory_maps_payloads_instead_of_reading_them(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment, _, _ = _build_lookup_fixture_deployment(
        lookup_application, tmp_path / "deployment"
    )
    request = _lookup_request(deployment, tmp_path / "request.json", [[0, 4, 7]])
    original = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path.name == "hash_route.bin" or path.parent.name == "embed":
            raise AssertionError(f"ROM payload was materialized through read_bytes: {path}")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    assert DeepSeekV4LookupServiceEngine.load(deployment).execute(request)[
        "status"
    ] == "pass"


def test_lookup_service_engine_rejects_payload_and_request_tampering(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    deployment, _, _ = _build_lookup_fixture_deployment(
        lookup_application, tmp_path / "deployment"
    )
    request = _lookup_request(deployment, tmp_path / "request.json", [[0]])
    malformed = load_strict_json(request)
    malformed["token_ids"] = [[8]]
    write_canonical_json(tmp_path / "bad-request.json", malformed)
    engine = DeepSeekV4LookupServiceEngine.load(deployment)
    with pytest.raises(DeepSeekV4LookupServiceEngineError, match="outside vocabulary"):
        engine.execute(tmp_path / "bad-request.json")

    payload_path = deployment / "rom/embed/rank-001.bin"
    payload = bytearray(payload_path.read_bytes())
    payload[0] ^= 1
    payload_path.write_bytes(payload)
    with pytest.raises(
        DeepSeekV4LookupServiceEngineError,
        match="differs from its deployment manifest",
    ):
        DeepSeekV4LookupServiceEngine.load(deployment)


def test_lookup_compiler_and_service_engine_cli_dispatch_end_to_end(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, application, _, _ = lookup_application
    lock_path = tmp_path / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)
    deployment = tmp_path / "deployment"
    assert (
        compiler_main(
            [
                "compile-deepseek-v4-lookup-slice",
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
    request = _lookup_request(deployment, tmp_path / "request.json", [[0, 4, 7]])
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
    result = load_strict_json(result_path)
    assert result["status"] == "pass"
    assert result["counter_reconciliation"] == "exact"
    assert result["execution_scope"] == "three_operator_real_payload_slice_only"
    differential_path = tmp_path / "differential.json"
    assert (
        compiler_main(
            [
                "verify-deepseek-v4-lookup-execution",
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
        "exact_locked_checkpoint_differential"
    )


def test_lookup_schema_set_is_strict_and_validates_every_json_boundary(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
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
    paths = sorted(LOOKUP_SCHEMA_DIR.glob("*.schema.json"))
    assert {path.name for path in paths} == expected
    schemas = {}
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        schemas[path.name] = Draft202012Validator(schema)

    deployment, _, _ = _build_lookup_fixture_deployment(
        lookup_application, tmp_path / "deployment"
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
    request_path = _lookup_request(deployment, tmp_path / "request.json", [[0, 4, 7]])
    schemas["execution_request_v1.schema.json"].validate(
        load_strict_json(request_path)
    )
    result = DeepSeekV4LookupServiceEngine.load(deployment).execute(request_path)
    schemas["execution_result_v1.schema.json"].validate(result)


def test_lookup_execution_checker_streams_locked_checkpoint_and_rejects_drift(
    lookup_application: tuple[
        Path, dict[str, Any], Path, tuple[int, ...], tuple[int, ...]
    ],
    tmp_path: Path,
) -> None:
    snapshot, lock, _, _, _ = lookup_application
    deployment, _, _ = _build_lookup_fixture_deployment(
        lookup_application, tmp_path / "deployment"
    )
    request_path = _lookup_request(
        deployment, tmp_path / "request.json", [[0, 3, 4, 7]]
    )
    result = DeepSeekV4LookupServiceEngine.load(deployment).execute(request_path)
    result_path = tmp_path / "result.json"
    write_canonical_json(result_path, result)
    report = verify_deepseek_v4_lookup_execution(
        snapshot=snapshot,
        lock=lock,
        deployment_root=deployment,
        request_path=request_path,
        result_path=result_path,
    )
    assert report["status"] == "exact_locked_checkpoint_differential"
    assert report["token_count"] == 4
    assert [record["status"] for record in report["comparisons"]] == [
        "exact",
        "exact",
        "exact",
    ]
    assert all(
        record["expected_sha256"] == record["observed_sha256"]
        for record in report["comparisons"]
    )
    differential_schema = json.loads(
        (LOOKUP_SCHEMA_DIR / "differential_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(differential_schema).validate(report)

    result["outputs"][0]["values"][0][0][0] ^= 1
    write_canonical_json(tmp_path / "tampered-result.json", result)
    with pytest.raises(
        DeepSeekV4LookupDifferentialError,
        match="differs from locked checkpoint semantics",
    ):
        verify_deepseek_v4_lookup_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment,
            request_path=request_path,
            result_path=tmp_path / "tampered-result.json",
        )
