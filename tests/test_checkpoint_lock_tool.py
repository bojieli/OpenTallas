"""``tools/build_checkpoint_lock.py`` binds a checkpoint or refuses to.

The lock is the join between a released checkpoint and every artifact the
compiler derives from it: a kernel-IR ``CheckpointBinding`` quotes the
per-tensor digest recorded here, and a ROM image's inverse proof reconstructs
the checkpoint from those same bytes.  So the properties worth pinning are the
refusals.  A synthetic two-shard snapshot exercises them in milliseconds; the
whole-checkpoint evidence is separate and is stated in the tool's docstring --
run against the released DeepSeek-V4-Flash-0731 snapshot the tool rebuilds
``~/.cache/opentallas/deepseek-v4-flash-0731/checkpoint.lock.json`` with
``lock_id`` 30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760,
identical in every field, hashing 166,878,536,440 payload bytes in 185 s.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

from tools.build_checkpoint_lock import main

REVISION = "0" * 39 + "1"
REPOSITORY = "example-org/example-model"
INDEX = "model.safetensors.index.json"


def _shard_bytes(tensors: dict[str, tuple[str, list[int], bytes]]) -> bytes:
    """One safetensors shard: 8-byte header length, header JSON, payload."""

    header: dict[str, object] = {}
    payload = b""
    for name, (dtype, shape, data) in tensors.items():
        header[name] = {
            "dtype": dtype,
            "shape": shape,
            "data_offsets": [len(payload), len(payload) + len(data)],
        }
        payload += data
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    return struct.pack("<Q", len(raw)) + raw + payload


def _write_snapshot(root: Path) -> dict[str, bytes]:
    """A two-shard snapshot with an index and one required auxiliary file."""

    first = _shard_bytes(
        {
            "embed.weight": ("BF16", [4, 2], bytes(range(16))),
            "layers.0.mlp.weight": ("F8_E4M3", [3, 3], bytes(range(9))),
        }
    )
    second = _shard_bytes({"head.weight": ("F32", [2, 2], bytes(range(16)))})
    files = {
        "model-00001-of-00002.safetensors": first,
        "model-00002-of-00002.safetensors": second,
        "config.json": b'{"model_type":"example"}',
        INDEX: json.dumps(
            {
                "metadata": {"total_size": 16 + 9 + 16},
                "weight_map": {
                    "embed.weight": "model-00001-of-00002.safetensors",
                    "layers.0.mlp.weight": "model-00001-of-00002.safetensors",
                    "head.weight": "model-00002-of-00002.safetensors",
                },
            },
            sort_keys=True,
        ).encode(),
    }
    for name, payload in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return files


def _source(files: dict[str, bytes]) -> dict[str, object]:
    return {
        "checkpoint_index": INDEX,
        "expected_files": sorted(
            (
                {
                    "path": name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
                for name, payload in files.items()
            ),
            key=lambda item: item["path"],
        ),
        "remote_code_policy": "disabled",
        "repository": REPOSITORY,
        "required_files": ["config.json"],
        "revision": REVISION,
        "schema": "opentallas.checkpoint_source.v1",
    }


@pytest.fixture()
def snapshot(tmp_path: Path):
    root = tmp_path / "snapshot"
    root.mkdir()
    files = _write_snapshot(root)
    source_path = tmp_path / "checkpoint_source.json"
    source_path.write_text(json.dumps(_source(files), indent=2, sort_keys=True))
    return root, source_path, files


def _run(source: Path, snapshot_root: Path, output: Path, *extra: str) -> int:
    return main(
        [
            "--source",
            str(source),
            "--snapshot",
            str(snapshot_root),
            "--output",
            str(output),
            *extra,
        ]
    )


def test_a_clean_snapshot_binds_every_tensor(snapshot, tmp_path):
    root, source, files = snapshot
    output = tmp_path / "checkpoint.lock.json"
    assert _run(source, root, output) == 0
    lock = json.loads(output.read_text())
    assert lock["schema"] == "opentallas.checkpoint_lock.v1"
    assert lock["checkpoint"]["shard_count"] == 2
    assert lock["checkpoint"]["tensor_count"] == 3
    assert lock["checkpoint"]["payload_bytes"] == 16 + 9 + 16
    # The per-tensor digest is the digest of that tensor's payload bytes alone,
    # which is the value a kernel-IR binding quotes.
    tensors = {
        tensor["name"]: tensor
        for shard in lock["shards"]
        for tensor in shard["tensors"]
    }
    assert tensors["embed.weight"]["payload_sha256"] == hashlib.sha256(
        bytes(range(16))
    ).hexdigest()
    assert tensors["layers.0.mlp.weight"]["payload_sha256"] == hashlib.sha256(
        bytes(range(9))
    ).hexdigest()
    assert tensors["embed.weight"]["shape"] == [4, 2]
    assert tensors["layers.0.mlp.weight"]["dtype"] == "F8_E4M3"
    # The lock embeds the expectation it was checked against.
    assert lock["source"]["revision"] == REVISION
    assert lock["source"]["expected_files"] == _source(files)["expected_files"]


def test_two_builds_of_one_snapshot_agree(snapshot, tmp_path):
    root, source, _files = snapshot
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert _run(source, root, first) == 0
    assert _run(source, root, second) == 0
    assert first.read_bytes() == second.read_bytes()


def test_a_flipped_payload_byte_is_refused(snapshot, tmp_path, capsys):
    root, source, _files = snapshot
    shard = root / "model-00001-of-00002.safetensors"
    payload = bytearray(shard.read_bytes())
    payload[-1] ^= 0x01
    shard.write_bytes(bytes(payload))
    assert _run(source, root, tmp_path / "lock.json") == 3
    assert "differs from its immutable source" in capsys.readouterr().err


def test_a_declared_digest_that_does_not_match_is_refused(
    snapshot, tmp_path, capsys
):
    root, source, files = snapshot
    body = _source(files)
    for entry in body["expected_files"]:
        if entry["path"] == "config.json":
            entry["sha256"] = "f" * 64
    source.write_text(json.dumps(body, indent=2, sort_keys=True))
    assert _run(source, root, tmp_path / "lock.json") == 3
    assert "differs from its immutable source" in capsys.readouterr().err


def test_an_index_payload_total_that_disagrees_is_refused(
    snapshot, tmp_path, capsys
):
    root, source, files = snapshot
    index = json.loads((root / INDEX).read_text())
    index["metadata"]["total_size"] = 1
    raw = json.dumps(index, sort_keys=True).encode()
    (root / INDEX).write_bytes(raw)
    body = _source({**files, INDEX: raw})
    source.write_text(json.dumps(body, indent=2, sort_keys=True))
    assert _run(source, root, tmp_path / "lock.json") == 3
    assert "index declares" in capsys.readouterr().err


def test_a_tensor_the_index_does_not_name_is_refused(snapshot, tmp_path, capsys):
    root, source, files = snapshot
    index = json.loads((root / INDEX).read_text())
    del index["weight_map"]["head.weight"]
    index["metadata"]["total_size"] = 16 + 9
    raw = json.dumps(index, sort_keys=True).encode()
    (root / INDEX).write_bytes(raw)
    body = _source({**files, INDEX: raw})
    source.write_text(json.dumps(body, indent=2, sort_keys=True))
    assert _run(source, root, tmp_path / "lock.json") == 3
    error = capsys.readouterr().err
    assert "coverage differs" in error or "extra=" in error


def test_a_missing_required_file_is_refused(snapshot, tmp_path, capsys):
    root, source, _files = snapshot
    (root / "config.json").unlink()
    assert _run(source, root, tmp_path / "lock.json") == 3
    assert "config.json" in capsys.readouterr().err


def test_an_existing_lock_is_not_overwritten_without_force(snapshot, tmp_path):
    root, source, _files = snapshot
    output = tmp_path / "lock.json"
    output.write_text("{}")
    assert _run(source, root, output) == 4
    assert output.read_text() == "{}"
    assert _run(source, root, output, "--force") == 0
    assert json.loads(output.read_text())["checkpoint"]["shard_count"] == 2


def test_an_unreadable_source_is_reported_not_raised(tmp_path, capsys):
    assert (
        _run(tmp_path / "absent.json", tmp_path, tmp_path / "lock.json") == 2
    )
    assert "cannot read checkpoint source" in capsys.readouterr().err
