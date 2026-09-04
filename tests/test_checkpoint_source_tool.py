"""``tools/build_checkpoint_source.py`` derives a checkpoint expectation or refuses to.

The source is the expectation half of the checkpoint identity: everything the
compiler derives from a checkpoint is bound to the digests recorded here, and
``build_checkpoint_lock`` re-reads every byte against them.  Deriving the
expectation from the local bytes alone would be circular, so the tool confronts
each local digest with the model registry's own per-file record at the pinned
revision.  The properties worth pinning are therefore the refusals -- what
happens when the local bytes and that independent witness disagree -- and the
reporting boundary between files the registry defines as the checkpoint and
files that merely sit beside them in a working copy.

A synthetic two-shard snapshot exercises all of that in milliseconds.  The
whole-checkpoint evidence is separate: run against the released
DeepSeek-V4-Flash-0731 snapshot and that repository's registry listing at
revision 7872f01b1d1fe23eabc4c98b48bffcef5a386062, the tool rederives the
committed ``compiler/models/deepseek-v4-flash-0731/checkpoint_source.json`` --
74 files, 48 of them shards, 25 required, with 48 files witnessed by registry
digest and size and 26 by size alone, and 7 local files the registry does not
list at that revision left unbound.  The rederived document equals the committed
one field for field and canonically byte for byte; the committed file's
indented on-disk formatting is not what this tool writes.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import pytest

from compiler.frontend.checkpoint import validate_checkpoint_source
from tools.build_checkpoint_source import main

REVISION = "7" * 40
OTHER_REVISION = "a" * 40
REPOSITORY = "example-org/example-model"
INDEX = "model.safetensors.index.json"
FIRST_SHARD = "model-00001-of-00002.safetensors"
SECOND_SHARD = "model-00002-of-00002.safetensors"


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
    """Two shards, an index, and two auxiliary files, one of them nested."""

    first = _shard_bytes(
        {
            "embed.weight": ("BF16", [4, 2], bytes(range(16))),
            "layers.0.mlp.weight": ("F8_E4M3", [3, 3], bytes(range(9))),
        }
    )
    second = _shard_bytes({"head.weight": ("F32", [2, 2], bytes(range(16)))})
    files = {
        FIRST_SHARD: first,
        SECOND_SHARD: second,
        "config.json": b'{"model_type":"example"}',
        "inference/model.py": b"# released reference implementation\n",
        INDEX: json.dumps(
            {
                "metadata": {"total_size": 16 + 9 + 16},
                "weight_map": {
                    "embed.weight": FIRST_SHARD,
                    "layers.0.mlp.weight": FIRST_SHARD,
                    "head.weight": SECOND_SHARD,
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


def _listing(
    files: dict[str, bytes],
    *,
    revision: str = REVISION,
    blobs: bool = True,
) -> dict[str, Any]:
    """A registry listing over exactly ``files``.

    The registry publishes a content digest only for files it stores in LFS --
    the shards here, as in the released repositories -- and records the rest by
    size alone.  ``blobs=False`` is the shape returned when the model endpoint
    is fetched without ``?blobs=true``: names, and no witness at all.
    """

    siblings: list[dict[str, Any]] = []
    for name, payload in sorted(files.items()):
        entry: dict[str, Any] = {"rfilename": name}
        if blobs:
            entry["size"] = len(payload)
            if name.endswith(".safetensors"):
                entry["lfs"] = {
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                }
        siblings.append(entry)
    return {"sha": revision, "siblings": siblings}


@pytest.fixture()
def snapshot(tmp_path: Path):
    root = tmp_path / "snapshot"
    root.mkdir()
    files = _write_snapshot(root)
    return root, files


def _run(
    snapshot_root: Path,
    listing: dict[str, Any],
    output: Path,
    *extra: str,
) -> int:
    listing_path = output.parent / f"{output.stem}.listing.json"
    listing_path.write_text(json.dumps(listing, indent=2, sort_keys=True))
    return main(
        [
            "--repository",
            REPOSITORY,
            "--revision",
            REVISION,
            "--snapshot",
            str(snapshot_root),
            "--registry-listing",
            str(listing_path),
            "--output",
            str(output),
            *extra,
        ]
    )


def test_a_clean_snapshot_derives_the_registry_file_set(snapshot, tmp_path, capsys):
    root, files = snapshot
    output = tmp_path / "checkpoint_source.json"
    assert _run(root, _listing(files), output) == 0
    source = json.loads(output.read_text())

    assert source["schema"] == "opentallas.checkpoint_source.v1"
    assert source["repository"] == REPOSITORY
    assert source["revision"] == REVISION
    assert source["remote_code_policy"] == "disabled"
    assert source["checkpoint_index"] == INDEX
    # Required files are the non-shard files other than the index, which is
    # implicit; the shards are expected but reached through the index.
    assert source["required_files"] == ["config.json", "inference/model.py"]
    # Every declared digest is the digest of that file's bytes alone.
    expected = {record["path"]: record for record in source["expected_files"]}
    assert set(expected) == set(files)
    for name, payload in files.items():
        assert expected[name]["sha256"] == hashlib.sha256(payload).hexdigest()
        assert expected[name]["size_bytes"] == len(payload)

    report = capsys.readouterr().out
    assert "files 5 (shards 2, required 2)" in report
    assert f"shard payload bytes {len(files[FIRST_SHARD]) + len(files[SECOND_SHARD])}" in report
    # The registry stores the shards in LFS and the rest by size only.
    assert "2 files agree on digest and size, 3 on size alone" in report


def test_the_derived_source_validates_through_the_frontend(snapshot, tmp_path):
    root, files = snapshot
    output = tmp_path / "checkpoint_source.json"
    assert _run(root, _listing(files), output) == 0
    source = json.loads(output.read_text())
    # The front end is what every consumer loads the file through, and it
    # normalizes: an accepted document must survive it unchanged.
    assert validate_checkpoint_source(source) == source


def test_two_derivations_of_one_snapshot_agree(snapshot, tmp_path):
    root, files = snapshot
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert _run(root, _listing(files), first) == 0
    assert _run(root, _listing(files), second) == 0
    assert first.read_bytes() == second.read_bytes()


def test_a_local_digest_the_registry_contradicts_is_refused(
    snapshot, tmp_path, capsys
):
    root, files = snapshot
    listing = _listing(files)
    shard = root / FIRST_SHARD
    payload = bytearray(shard.read_bytes())
    payload[-1] ^= 0x01
    shard.write_bytes(bytes(payload))

    output = tmp_path / "checkpoint_source.json"
    assert _run(root, listing, output) == 3
    error = capsys.readouterr().err
    assert "snapshot and registry witness disagree" in error
    assert f"{FIRST_SHARD}: local sha256" in error
    assert "differs from the registry's" in error
    assert not output.exists()


def test_a_local_size_the_registry_contradicts_is_refused(
    snapshot, tmp_path, capsys
):
    root, files = snapshot
    listing = _listing(files)
    (root / "config.json").write_bytes(files["config.json"] + b"\n")

    output = tmp_path / "checkpoint_source.json"
    assert _run(root, listing, output) == 3
    error = capsys.readouterr().err
    assert (
        f"config.json: local size {len(files['config.json']) + 1} differs from "
        f"the registry's {len(files['config.json'])}" in error
    )
    assert not output.exists()


def test_a_file_the_registry_lists_but_the_snapshot_lacks_is_refused(
    snapshot, tmp_path, capsys
):
    root, files = snapshot
    listing = _listing(files)
    (root / "inference/model.py").unlink()

    output = tmp_path / "checkpoint_source.json"
    assert _run(root, listing, output) == 3
    error = capsys.readouterr().err
    assert "snapshot is missing 1 file(s) the registry lists" in error
    assert "inference/model.py" in error
    assert not output.exists()


def test_local_files_the_registry_does_not_list_are_reported_not_bound(
    snapshot, tmp_path, capsys
):
    root, files = snapshot
    listing = _listing(files)
    # A working copy accumulates things that are not part of the checkpoint: a
    # published deployment written beside the weights, and interpreter caches.
    (root / "deployment.json").write_bytes(b'{"deployment":"local"}')
    cache = root / "inference/__pycache__"
    cache.mkdir()
    (cache / "model.cpython-310.pyc").write_bytes(b"\x00cached")

    output = tmp_path / "checkpoint_source.json"
    assert _run(root, listing, output) == 0
    source = json.loads(output.read_text())
    bound = {record["path"] for record in source["expected_files"]}
    assert bound == set(files)
    assert "deployment.json" not in bound
    report = capsys.readouterr().out
    assert "2 local file(s) the registry does not list" in report
    assert "deployment.json" in report


def test_a_listing_for_another_revision_is_refused(snapshot, tmp_path, capsys):
    root, files = snapshot
    output = tmp_path / "checkpoint_source.json"
    assert _run(root, _listing(files, revision=OTHER_REVISION), output) == 3
    error = capsys.readouterr().err
    assert f"registry listing is for revision {OTHER_REVISION!r}" in error
    assert f"not the pinned {REVISION!r}" in error
    assert not output.exists()


def test_a_listing_without_blob_sizes_witnesses_nothing_and_is_refused(
    snapshot, tmp_path, capsys
):
    root, files = snapshot
    output = tmp_path / "checkpoint_source.json"
    # Fetched without ?blobs=true the listing carries names only. Binding files
    # against it would record digests no independent record ever confirmed.
    assert _run(root, _listing(files, blobs=False), output) == 3
    error = capsys.readouterr().err
    assert "records neither a digest nor a size" in error
    assert "?blobs=true" in error
    assert not output.exists()
