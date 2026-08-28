from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.canonical import (
    CanonicalApplicationError,
    apply_canonical_plan_records,
    apply_official_canonical_plan,
)
from compiler.checking import (
    DeepSeekV4ApplicationCheckError,
    verify_canonical_application,
)
from compiler.frontend.checkpoint import (
    CheckpointError,
    build_checkpoint_lock,
    validate_checkpoint_source,
)
from compiler.frontend.deepseek_v4 import DeepSeekV4AdapterError
from compiler.ir.model import canonical_json_bytes, load_strict_json


ROOT = Path(__file__).resolve().parents[2]
APPLICATION_SCHEMA = ROOT / "schemas/compiler/canonical_application_v1.schema.json"
CHECK_SCHEMA = (
    ROOT / "schemas/compiler/canonical_application_check_v1.schema.json"
)
FIXTURE_REVISION = "89abcdef0123456789abcdef0123456789abcdef"


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
    storage_dtype: str,
    logical_dtype: str,
    payload_bytes: int,
    transform: str = "identity",
    source_slice: dict[str, int] | None = None,
    scale_source: str | None = None,
    scale_source_slice: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "logical_dtype": logical_dtype,
        "name": name,
        "payload_bytes": payload_bytes,
        "rank": rank,
        "scale_source": scale_source,
        "scale_source_slice": scale_source_slice,
        "shape": shape,
        "source_slice": source_slice,
        "storage_dtype": storage_dtype,
        "transform": transform,
    }


def _input(
    name: str,
    *,
    action: str,
    storage_dtype: str,
    logical_dtype: str,
    shape: list[int],
    size_bytes: int,
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "action": action,
        "logical_dtype": logical_dtype,
        "name": name,
        "outputs": outputs,
        "semantic_role": f"fixture.{name}",
        "shape": shape,
        "size_bytes": size_bytes,
        "storage_dtype": storage_dtype,
    }


def _plan_inputs() -> list[dict[str, Any]]:
    return [
        _input(
            "axis0.weight",
            action="tensor_parallel_slice_axis_0",
            storage_dtype="U16",
            logical_dtype="U16",
            shape=[4, 2],
            size_bytes=16,
            outputs=[
                _output(
                    "axis0.weight",
                    rank=rank,
                    shape=[2, 2],
                    storage_dtype="U16",
                    logical_dtype="U16",
                    payload_bytes=8,
                    source_slice={"axis": 0, "start": rank * 2, "stop": rank * 2 + 2},
                )
                for rank in range(2)
            ],
        ),
        _input(
            "axis1.weight",
            action="tensor_parallel_slice_axis_1",
            storage_dtype="U8",
            logical_dtype="U8",
            shape=[2, 4],
            size_bytes=8,
            outputs=[
                _output(
                    "axis1.weight",
                    rank=rank,
                    shape=[2, 2],
                    storage_dtype="U8",
                    logical_dtype="U8",
                    payload_bytes=4,
                    source_slice={"axis": 1, "start": rank * 2, "stop": rank * 2 + 2},
                )
                for rank in range(2)
            ],
        ),
        _input(
            "native.scale",
            action="route_whole_tensor_to_expert_rank",
            storage_dtype="F8_E8M0",
            logical_dtype="UE8M0_SCALE",
            shape=[2, 1],
            size_bytes=2,
            outputs=[
                _output(
                    "native.scale",
                    rank=0,
                    shape=[2, 1],
                    storage_dtype="F8_E8M0",
                    logical_dtype="UE8M0_SCALE",
                    payload_bytes=2,
                )
            ],
        ),
        _input(
            "native.weight",
            action="route_and_reinterpret_native_mxfp4",
            storage_dtype="I8",
            logical_dtype="MXFP4_E2M1_X2",
            shape=[2, 16],
            size_bytes=32,
            outputs=[
                _output(
                    "native.weight",
                    rank=0,
                    shape=[2, 16],
                    storage_dtype="U8",
                    logical_dtype="MXFP4_E2M1_X2",
                    payload_bytes=32,
                    transform=(
                        "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
                    ),
                )
            ],
        ),
        _input(
            "replicate.weight",
            action="replicate_identity",
            storage_dtype="I8",
            logical_dtype="I8",
            shape=[4],
            size_bytes=4,
            outputs=[
                _output(
                    "replicate.weight",
                    rank=rank,
                    shape=[4],
                    storage_dtype="I8",
                    logical_dtype="I8",
                    payload_bytes=4,
                )
                for rank in range(2)
            ],
        ),
        _input(
            "wo_a.scale",
            action="consume_wo_a_scale",
            storage_dtype="F8_E8M0",
            logical_dtype="UE8M0_SCALE",
            shape=[2, 1],
            size_bytes=2,
            outputs=[],
        ),
        _input(
            "wo_a.weight",
            action="slice_then_dequantize_wo_a_to_bf16",
            storage_dtype="F8_E4M3",
            logical_dtype="FP8_E4M3FN",
            shape=[256, 128],
            size_bytes=32_768,
            outputs=[
                _output(
                    "wo_a.weight",
                    rank=rank,
                    shape=[128, 128],
                    storage_dtype="BF16",
                    logical_dtype="BF16",
                    payload_bytes=32_768,
                    transform="dequantize_fp8_e8m0_to_bf16_rne",
                    source_slice={
                        "axis": 0,
                        "start": rank * 128,
                        "stop": rank * 128 + 128,
                    },
                    scale_source="wo_a.scale",
                    scale_source_slice={
                        "axis": 0,
                        "start": rank,
                        "stop": rank + 1,
                    },
                )
                for rank in range(2)
            ],
        ),
    ]


@pytest.fixture
def application_fixture(tmp_path: Path) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    config = canonical_json_bytes({"architectures": ["CanonicalFixture"]})
    axis0 = struct.pack("<8H", *range(8))
    axis1 = bytes(range(8))
    native_scale = b"\x7f\x80"
    native_weight = bytes(range(32))
    replicate = b"\x01\x02\xfe\x7f"
    wo_scale = b"\x78\x7f"
    wo_weight = bytes(
        ((index * 29) % 0x7F) | (0x80 if index & 1 else 0)
        for index in range(256 * 128)
    )
    tensors = [
        ("axis0.weight", "U16", [4, 2], axis0),
        ("axis1.weight", "U8", [2, 4], axis1),
        ("native.scale", "F8_E8M0", [2, 1], native_scale),
        ("native.weight", "I8", [2, 16], native_weight),
        ("replicate.weight", "I8", [4], replicate),
        ("wo_a.scale", "F8_E8M0", [2, 1], wo_scale),
        ("wo_a.weight", "F8_E4M3", [256, 128], wo_weight),
    ]
    shard = _safetensors(tensors)
    index = canonical_json_bytes(
        {
            "metadata": {"total_size": sum(len(record[3]) for record in tensors)},
            "weight_map": {
                record[0]: "model.safetensors" for record in tensors
            },
        }
    )
    (snapshot / "config.json").write_bytes(config)
    (snapshot / "model.safetensors").write_bytes(shard)
    (snapshot / "model.safetensors.index.json").write_bytes(index)
    expected_files = []
    for name, payload in [
        ("config.json", config),
        ("model.safetensors", shard),
        ("model.safetensors.index.json", index),
    ]:
        expected_files.append(
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    source = validate_checkpoint_source(
        {
            "checkpoint_index": "model.safetensors.index.json",
            "expected_files": expected_files,
            "remote_code_policy": "disabled",
            "repository": "OpenTallas/canonical-application-fixture",
            "required_files": ["config.json"],
            "revision": FIXTURE_REVISION,
            "schema": "opentallas.checkpoint_source.v1",
        }
    )
    lock = build_checkpoint_lock(snapshot, source)
    return snapshot, lock, _plan_inputs()


def _plan_id(inputs: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(inputs)).hexdigest()


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_locked_fixture_applies_all_transform_classes_deterministically(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_result = apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=_plan_id(inputs),
        plan_schema="opentallas.canonical_fixture_plan.v1",
        plan_inputs=inputs,
        output=first,
    )
    second_result = apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=_plan_id(inputs),
        plan_schema="opentallas.canonical_fixture_plan.v1",
        plan_inputs=inputs,
        output=second,
    )
    assert first_result == second_result
    assert _tree(first) == _tree(second)

    manifest = first_result["manifest"]
    verification = first_result["verification"]
    assert manifest["application_id"] == (
        "ea6d5225cf434bce31b12d4bb4f555bb00ca1eb66842881ac0fe01cc6be07e3d"
    )
    assert verification["verification_id"] == (
        "794096f0f55341458f80a2cdc7d075f2aa4dd036c0a8aa606e651fbe6b35cbb8"
    )
    assert manifest["coverage"] == {
        "consumed_input_count": 7,
        "consumed_input_payload_bytes": 32_832,
        "output_assignment_count": 10,
        "output_payload_bytes": 65_602,
    }
    assert manifest["selection"] == {
        "complete_plan": True,
        "dependency_input_names": [],
        "requested_input_names": [record["name"] for record in inputs],
    }
    assert manifest["status"] == (
        "development_fixture_application_not_release_evidence"
    )
    assert verification["coverage"] == {
        "checked_assignment_count": 10,
        "checked_input_count": 7,
        "checked_output_bytes": 65_602,
    }
    assert verification["status"] == "full_assignment_match"
    methods = [record["method"] for record in verification["checks"]]
    assert methods.count("streamed_identity_or_slice") == 7
    assert methods.count("native_mxfp4_pair_identity") == 1
    assert methods.count("independent_fp8_e8m0_bf16") == 2

    assert (first / "ranks/rank-000/axis0.weight.bin").read_bytes() == struct.pack(
        "<4H", 0, 1, 2, 3
    )
    assert (first / "ranks/rank-001/axis0.weight.bin").read_bytes() == struct.pack(
        "<4H", 4, 5, 6, 7
    )
    assert (first / "ranks/rank-000/axis1.weight.bin").read_bytes() == bytes(
        (0, 1, 4, 5)
    )
    assert (first / "ranks/rank-001/axis1.weight.bin").read_bytes() == bytes(
        (2, 3, 6, 7)
    )
    assert (first / "ranks/rank-000/native.weight.bin").read_bytes() == bytes(
        range(32)
    )
    assert len(first.joinpath("ranks/rank-000/wo_a.weight.bin").read_bytes()) == (
        32_768
    )

    application_schema = load_strict_json(APPLICATION_SCHEMA)
    check_schema = load_strict_json(CHECK_SCHEMA)
    Draft202012Validator.check_schema(application_schema)
    Draft202012Validator.check_schema(check_schema)
    Draft202012Validator(application_schema).validate(manifest)
    Draft202012Validator(check_schema).validate(verification)


def test_partial_application_closes_native_weight_scale_dependency(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    output = tmp_path / "native-only"
    result = apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=_plan_id(inputs),
        plan_schema="opentallas.canonical_fixture_plan.v1",
        plan_inputs=inputs,
        requested_names=["native.weight"],
        output=output,
    )
    manifest = result["manifest"]
    assert [record["name"] for record in manifest["inputs"]] == [
        "native.scale",
        "native.weight",
    ]
    assert manifest["selection"] == {
        "complete_plan": False,
        "dependency_input_names": ["native.scale"],
        "requested_input_names": ["native.weight"],
    }
    assert manifest["coverage"]["output_assignment_count"] == 2
    assert result["verification"]["coverage"]["checked_input_count"] == 2


def test_independent_replay_rejects_output_tampering(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    output = tmp_path / "application"
    apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=_plan_id(inputs),
        plan_schema="opentallas.canonical_fixture_plan.v1",
        plan_inputs=inputs,
        output=output,
    )
    artifact = output / "ranks/rank-001/axis1.weight.bin"
    changed = bytearray(artifact.read_bytes())
    changed[2] ^= 1
    artifact.write_bytes(changed)
    with pytest.raises(DeepSeekV4ApplicationCheckError, match="differs"):
        verify_canonical_application(output, snapshot, lock)


def test_payload_tamper_fails_atomically_without_final_or_temporary_output(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    shard_path = snapshot / "model.safetensors"
    changed = bytearray(shard_path.read_bytes())
    changed[-1] ^= 1
    shard_path.write_bytes(changed)
    output = tmp_path / "must-not-exist"
    with pytest.raises(CheckpointError, match="payload differs"):
        apply_canonical_plan_records(
            snapshot=snapshot,
            lock=lock,
            plan_id=_plan_id(inputs),
            plan_schema="opentallas.canonical_fixture_plan.v1",
            plan_inputs=inputs,
            output=output,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".must-not-exist.tmp-*"))


def test_fixture_lock_cannot_enter_official_application_scope(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, _ = application_fixture
    output = tmp_path / "must-not-exist"
    with pytest.raises(DeepSeekV4AdapterError, match="not the pinned V4 Flash"):
        apply_official_canonical_plan(
            snapshot=snapshot,
            lock=lock,
            plan={},
            output=output,
        )
    assert not output.exists()


def test_malformed_plan_fails_before_creating_output(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    changed = copy.deepcopy(inputs)
    changed[0]["outputs"][0]["shape"] = [3, 2]
    output = tmp_path / "must-not-exist"
    with pytest.raises(CanonicalApplicationError, match="shape differs"):
        apply_canonical_plan_records(
            snapshot=snapshot,
            lock=lock,
            plan_id=_plan_id(changed),
            plan_schema="opentallas.canonical_fixture_plan.v1",
            plan_inputs=changed,
            output=output,
        )
    assert not output.exists()


def test_independent_verification_cli_matches_retained_report(
    application_fixture: tuple[Path, dict[str, Any], list[dict[str, Any]]],
    tmp_path: Path,
) -> None:
    snapshot, lock, inputs = application_fixture
    application = tmp_path / "application"
    result = apply_canonical_plan_records(
        snapshot=snapshot,
        lock=lock,
        plan_id=_plan_id(inputs),
        plan_schema="opentallas.canonical_fixture_plan.v1",
        plan_inputs=inputs,
        output=application,
    )
    lock_path = tmp_path / "checkpoint.lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock))
    report_path = tmp_path / "replayed-verification.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "verify-canonical-application",
            "--snapshot",
            str(snapshot),
            "--lock",
            str(lock_path),
            "--application",
            str(application),
            "--output",
            str(report_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert load_strict_json(report_path) == result["verification"]
    assert "verified 10 canonical assignments from 7 locked inputs" in (
        completed.stdout
    )
