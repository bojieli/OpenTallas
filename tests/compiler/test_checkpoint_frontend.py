from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from compiler.frontend.checkpoint import (
    CheckpointError,
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
    read_tensor_payload,
    validate_checkpoint_source,
    verify_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, write_canonical_json


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "testdata/compiler/checkpoint_fixture"
FIXTURE_SOURCE = FIXTURE / "source.json"
OFFICIAL_SOURCE = (
    ROOT
    / "compiler/models/deepseek-v4-flash-0731/checkpoint_source.json"
)


def _safetensors(
    tensors: list[tuple[str, str, list[int], bytes]],
    metadata: dict[str, str] | None = None,
) -> bytes:
    header: dict[str, Any] = {}
    if metadata is not None:
        header["__metadata__"] = metadata
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


def _raw_safetensors(raw_header: bytes, payload: bytes) -> bytes:
    raw_header += b" " * (-len(raw_header) % 8)
    return struct.pack("<Q", len(raw_header)) + raw_header + payload


def _write_fixture(snapshot: Path) -> None:
    snapshot.mkdir()
    (snapshot / "config.json").write_bytes(
        canonical_json_bytes({"architectures": ["FixtureModel"]})
    )
    (snapshot / "model-00001-of-00002.safetensors").write_bytes(
        _safetensors(
            [
                ("a.weight", "I8", [2, 2], b"\x01\x02\x03\x04"),
                ("b.scale", "F32", [1], struct.pack("<f", 1.5)),
            ],
            {"format": "pt"},
        )
    )
    (snapshot / "model-00002-of-00002.safetensors").write_bytes(
        _safetensors(
            [("c.bias", "I16", [3], struct.pack("<hhh", -1, 2, 7))]
        )
    )
    write_canonical_json(
        snapshot / "model.safetensors.index.json",
        {
            "metadata": {"total_size": 14},
            "weight_map": {
                "a.weight": "model-00001-of-00002.safetensors",
                "b.scale": "model-00001-of-00002.safetensors",
                "c.bias": "model-00002-of-00002.safetensors",
            },
        },
    )


@pytest.fixture
def checkpoint_snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "snapshot"
    _write_fixture(snapshot)
    return snapshot


def _source_with_current_hashes(snapshot: Path) -> dict[str, Any]:
    source = copy.deepcopy(load_checkpoint_source(FIXTURE_SOURCE))
    records: list[dict[str, Any]] = []
    for old_record in source["expected_files"]:
        path = snapshot / old_record["path"]
        payload = path.read_bytes()
        records.append(
            {
                "path": old_record["path"],
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    source["expected_files"] = records
    return validate_checkpoint_source(source)


def _relock_id(lock: dict[str, Any]) -> None:
    body = {key: value for key, value in lock.items() if key != "lock_id"}
    lock["lock_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_checkpoint_lock_is_deterministic_complete_and_host_free(
    checkpoint_snapshot: Path,
) -> None:
    source = load_checkpoint_source(FIXTURE_SOURCE)
    first = build_checkpoint_lock(checkpoint_snapshot, source)
    second = build_checkpoint_lock(checkpoint_snapshot, source)

    assert first == second
    assert first["checkpoint"] == {
        "payload_bytes": 14,
        "shard_count": 2,
        "tensor_content_sha256": (
            "2284bdccf9afb0eebbd10c3e5fe349ed2620f535586d04ede593642e71fa7635"
        ),
        "tensor_count": 3,
    }
    assert [shard["path"] for shard in first["shards"]] == [
        "model-00001-of-00002.safetensors",
        "model-00002-of-00002.safetensors",
    ]
    assert [
        tensor["name"]
        for shard in first["shards"]
        for tensor in shard["tensors"]
    ] == ["a.weight", "b.scale", "c.bias"]
    serialized = canonical_json_bytes(first).decode("ascii")
    assert str(checkpoint_snapshot) not in serialized
    assert "timestamp" not in serialized
    assert "created_at" not in serialized


def test_checkpoint_replay_and_individual_payload_access(
    checkpoint_snapshot: Path, tmp_path: Path
) -> None:
    lock = build_checkpoint_lock(
        checkpoint_snapshot, load_checkpoint_source(FIXTURE_SOURCE)
    )
    lock_path = tmp_path / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)
    loaded = load_checkpoint_lock(lock_path)

    assert verify_checkpoint_lock(checkpoint_snapshot, loaded) == lock
    assert read_tensor_payload(checkpoint_snapshot, loaded, "a.weight") == (
        b"\x01\x02\x03\x04"
    )
    assert read_tensor_payload(checkpoint_snapshot, loaded, "b.scale") == (
        struct.pack("<f", 1.5)
    )
    assert read_tensor_payload(checkpoint_snapshot, loaded, "c.bias") == (
        struct.pack("<hhh", -1, 2, 7)
    )
    with pytest.raises(CheckpointError, match="0 records"):
        read_tensor_payload(checkpoint_snapshot, loaded, "missing")


def test_source_identity_and_payload_tampering_fail_closed(
    checkpoint_snapshot: Path,
) -> None:
    source = load_checkpoint_source(FIXTURE_SOURCE)
    lock = build_checkpoint_lock(checkpoint_snapshot, source)
    shard_path = checkpoint_snapshot / "model-00001-of-00002.safetensors"
    tampered = bytearray(shard_path.read_bytes())
    tampered[-1] ^= 1
    shard_path.write_bytes(tampered)

    with pytest.raises(CheckpointError, match="immutable source expectation"):
        build_checkpoint_lock(checkpoint_snapshot, source)
    with pytest.raises(CheckpointError, match="payload differs"):
        read_tensor_payload(checkpoint_snapshot, lock, "b.scale")
    with pytest.raises(CheckpointError, match="immutable source expectation"):
        verify_checkpoint_lock(checkpoint_snapshot, lock)


def test_header_tampering_is_detected_by_targeted_payload_reader(
    checkpoint_snapshot: Path,
) -> None:
    lock = build_checkpoint_lock(
        checkpoint_snapshot, load_checkpoint_source(FIXTURE_SOURCE)
    )
    shard_path = checkpoint_snapshot / "model-00001-of-00002.safetensors"
    tampered = bytearray(shard_path.read_bytes())
    tampered[12] ^= 1
    shard_path.write_bytes(tampered)
    with pytest.raises(CheckpointError, match="different header"):
        read_tensor_payload(checkpoint_snapshot, lock, "a.weight")


def test_index_to_shard_mismatch_is_rejected(checkpoint_snapshot: Path) -> None:
    index_path = checkpoint_snapshot / "model.safetensors.index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["weight_map"]["b.scale"] = "model-00002-of-00002.safetensors"
    write_canonical_json(index_path, index)
    source = _source_with_current_hashes(checkpoint_snapshot)
    with pytest.raises(CheckpointError, match="coverage differs"):
        build_checkpoint_lock(checkpoint_snapshot, source)


@pytest.mark.parametrize("malformation", ["gap", "overlap", "trailing", "shape"])
def test_invalid_shard_layouts_are_rejected(
    checkpoint_snapshot: Path, malformation: str
) -> None:
    shard_path = checkpoint_snapshot / "model-00001-of-00002.safetensors"
    if malformation == "trailing":
        shard_path.write_bytes(shard_path.read_bytes() + b"!")
    else:
        second_offsets = [5, 9] if malformation == "gap" else [3, 7]
        first_shape = [5] if malformation == "shape" else [2, 2]
        if malformation == "shape":
            second_offsets = [4, 8]
        header = {
            "a.weight": {
                "data_offsets": [0, 4],
                "dtype": "I8",
                "shape": first_shape,
            },
            "b.scale": {
                "data_offsets": second_offsets,
                "dtype": "F32",
                "shape": [1],
            },
        }
        raw_header = json.dumps(
            header, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        payload_size = second_offsets[1]
        shard_path.write_bytes(_raw_safetensors(raw_header, bytes(payload_size)))
    source = _source_with_current_hashes(checkpoint_snapshot)
    match = {
        "gap": "data gap",
        "overlap": "data overlap",
        "trailing": "trailing payload bytes",
        "shape": "storage differs from shape/dtype",
    }[malformation]
    with pytest.raises(CheckpointError, match=match):
        build_checkpoint_lock(checkpoint_snapshot, source)


def test_duplicate_header_keys_are_rejected(checkpoint_snapshot: Path) -> None:
    duplicate_header = (
        b'{"a.weight":{"data_offsets":[0,4],"dtype":"I8","shape":[2,2]},'
        b'"a.weight":{"data_offsets":[0,4],"dtype":"I8","shape":[2,2]}}'
    )
    shard_path = checkpoint_snapshot / "model-00001-of-00002.safetensors"
    shard_path.write_bytes(_raw_safetensors(duplicate_header, bytes(4)))
    source = _source_with_current_hashes(checkpoint_snapshot)
    with pytest.raises(CheckpointError, match="duplicate JSON key"):
        build_checkpoint_lock(checkpoint_snapshot, source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("checkpoint_index", "../model.safetensors.index.json"),
        ("checkpoint_index", "/tmp/model.safetensors.index.json"),
        ("checkpoint_index", "nested\\index.json"),
    ],
)
def test_unsafe_source_paths_are_rejected(field: str, value: str) -> None:
    source = json.loads(FIXTURE_SOURCE.read_text(encoding="utf-8"))
    source[field] = value
    with pytest.raises(CheckpointError, match="relative path|canonical POSIX"):
        validate_checkpoint_source(source)


def test_malformed_lock_public_apis_raise_checkpoint_error(
    checkpoint_snapshot: Path,
) -> None:
    lock = build_checkpoint_lock(
        checkpoint_snapshot, load_checkpoint_source(FIXTURE_SOURCE)
    )
    bad_path = copy.deepcopy(lock)
    bad_path["shards"][0]["path"] = 3
    with pytest.raises(CheckpointError):
        read_tensor_payload(checkpoint_snapshot, bad_path, "a.weight")

    bad_header = copy.deepcopy(lock)
    bad_header["shards"][0]["header_length_bytes"] = "large"
    with pytest.raises(CheckpointError):
        read_tensor_payload(checkpoint_snapshot, bad_header, "a.weight")

    bad_summary = copy.deepcopy(lock)
    bad_summary["checkpoint"]["tensor_count"] = 99
    _relock_id(bad_summary)
    with pytest.raises(CheckpointError, match="summary differs"):
        verify_checkpoint_lock(checkpoint_snapshot, bad_summary)


def test_checkpoint_schemas_resolve_and_validate_generated_documents(
    checkpoint_snapshot: Path,
) -> None:
    schema_dir = ROOT / "schemas/compiler"
    source_schema = json.loads(
        (schema_dir / "checkpoint_source_v1.schema.json").read_text(encoding="utf-8")
    )
    lock_schema = json.loads(
        (schema_dir / "checkpoint_lock_v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(source_schema)
    Draft202012Validator.check_schema(lock_schema)
    registry = Registry().with_resources(
        [
            (source_schema["$id"], Resource.from_contents(source_schema)),
            (lock_schema["$id"], Resource.from_contents(lock_schema)),
        ]
    )
    source = load_checkpoint_source(FIXTURE_SOURCE)
    lock = build_checkpoint_lock(checkpoint_snapshot, source)
    Draft202012Validator(source_schema, registry=registry).validate(source)
    Draft202012Validator(lock_schema, registry=registry).validate(lock)


def test_official_deepseek_v4_flash_release_is_fully_content_pinned() -> None:
    source = load_checkpoint_source(OFFICIAL_SOURCE)
    inventory = json.loads(
        (ROOT / "data/inventory/deepseek-v4-flash-0731.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {record["path"]: record for record in source["expected_files"]}
    shards = [path for path in expected if path.endswith(".safetensors")]

    assert source["repository"] == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert source["revision"] == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert source["remote_code_policy"] == "disabled"
    assert len(expected) == 74
    assert len(shards) == inventory["shard_count"] == 48
    assert expected["config.json"]["sha256"] == inventory["config_sha256"]
    assert (
        expected["model.safetensors.index.json"]["sha256"]
        == inventory["index_sha256"]
    )
    assert sum(expected[path]["size_bytes"] for path in shards) > (
        inventory["checkpoint_bytes"]
    )
    assert "inference/model.py" in source["required_files"]
    assert "encoding/encoding_dsv4.py" in source["required_files"]
    assert "tokenizer.json" in source["required_files"]


def test_checkpoint_cli_locks_and_replays_snapshot(
    checkpoint_snapshot: Path, tmp_path: Path
) -> None:
    lock_path = tmp_path / "cli.lock.json"
    lock_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "lock-checkpoint",
            "--source",
            str(FIXTURE_SOURCE),
            "--snapshot",
            str(checkpoint_snapshot),
            "--output",
            str(lock_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert lock_result.returncode == 0, lock_result.stderr
    assert "locked 3 tensors in 2 shards" in lock_result.stdout
    verify_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "verify-checkpoint",
            "--lock",
            str(lock_path),
            "--snapshot",
            str(checkpoint_snapshot),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify_result.returncode == 0, verify_result.stderr
    assert "verified checkpoint lock" in verify_result.stdout
