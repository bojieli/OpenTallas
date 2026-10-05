from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator.hbm_shards import (
    HBMShardError,
    HBMShardReader,
    HBMShardWriter,
    hardlink_verified_shard_prefix,
)


def test_sparse_mmap_hbm_shards_preserve_one_logical_image(tmp_path: Path) -> None:
    prefix = b"OpenTallas-HBM"
    crossing = bytes(range(20))
    total_size = 9000
    expected = bytearray(total_size)
    expected[: len(prefix)] = prefix
    expected[4090 : 4090 + len(crossing)] = crossing

    with HBMShardWriter(
        tmp_path,
        total_size=total_size,
        shard_bytes=4096,
    ) as writer:
        writer.write(prefix)
        writer.advance_to(4090)
        writer.write(crossing)
        writer.advance_to(total_size)
        image = writer.finish()

    assert image["logical_sha256"] == hashlib.sha256(expected).hexdigest()
    assert image["size_bytes"] == total_size
    assert [record["size_bytes"] for record in image["shards"]] == [4096, 4096, 808]
    with HBMShardReader(tmp_path, image["shards"]) as reader:
        assert reader.total_size == total_size
        assert reader.read(0, len(prefix)) == prefix
        assert reader.read(4088, 24) == bytes(expected[4088:4112])
        assert reader.sha256(0, total_size) == image["logical_sha256"]
        reader.require_zero(32, 4000)


def test_hbm_shards_reject_incomplete_reuse_and_corruption(tmp_path: Path) -> None:
    first = HBMShardWriter(tmp_path, total_size=4096, shard_bytes=4096)
    with pytest.raises(HBMShardError, match="incomplete"):
        first.finish()
    first.abort()
    assert not (tmp_path / "memory/hbm").exists()

    with HBMShardWriter(tmp_path, total_size=4096, shard_bytes=4096) as writer:
        writer.skip_zeros(4096)
        image = writer.finish()
    with pytest.raises(HBMShardError, match="already exists"):
        HBMShardWriter(tmp_path, total_size=4096, shard_bytes=4096)

    shard = tmp_path / image["shards"][0]["path"]
    with shard.open("r+b") as handle:
        handle.seek(2048)
        handle.write(b"\x01")
    with pytest.raises(HBMShardError, match="hash differs"):
        HBMShardReader(tmp_path, image["shards"])


def test_hbm_shards_reject_out_of_range_access(tmp_path: Path) -> None:
    with HBMShardWriter(tmp_path, total_size=4096, shard_bytes=4096) as writer:
        with pytest.raises(HBMShardError, match="exceeds"):
            writer.write(bytes(4097))
        writer.skip_zeros(4096)
        image = writer.finish()
    with HBMShardReader(tmp_path, image["shards"]) as reader:
        with pytest.raises(HBMShardError, match="exceeds"):
            reader.read(4090, 16)
        with pytest.raises(HBMShardError, match="256 MiB"):
            reader.read(0, 256 * 1024 * 1024 + 1)


def _small_sharded_image(root: Path, payload: bytes) -> dict[str, object]:
    with HBMShardWriter(root, total_size=len(payload), shard_bytes=4096) as writer:
        writer.write(payload)
        return writer.finish()


def test_verified_hbm_prefix_reuse_hardlinks_only_admitted_shards(
    tmp_path: Path,
) -> None:
    payload = bytes(range(256)) * 36
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()
    source = _small_sharded_image(source_root, payload)
    target = _small_sharded_image(target_root, payload)
    source_paths = [source_root / record["path"] for record in source["shards"]]
    target_paths = [target_root / record["path"] for record in target["shards"]]
    before_suffix_inode = target_paths[2].stat().st_ino

    reused = hardlink_verified_shard_prefix(
        target_root,
        target["shards"],
        source_root=source_root,
        source_shards=source["shards"],
        shard_count=2,
    )
    assert reused == {"reused_bytes": 8192, "reused_shard_count": 2}
    for index in range(2):
        assert source_paths[index].stat().st_ino == target_paths[index].stat().st_ino
        assert source_paths[index].stat().st_nlink == 2
    assert target_paths[2].stat().st_ino == before_suffix_inode
    assert target_paths[2].stat().st_ino != source_paths[2].stat().st_ino
    with HBMShardReader(target_root, target["shards"]) as reader:
        assert reader.sha256(0, len(payload)) == hashlib.sha256(payload).hexdigest()


def test_verified_hbm_prefix_reuse_fails_closed_on_drift(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 32
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()
    source = _small_sharded_image(source_root, payload)
    target = _small_sharded_image(target_root, payload)
    source_path = source_root / source["shards"][0]["path"]
    target_path = target_root / target["shards"][0]["path"]
    target_inode = target_path.stat().st_ino
    with source_path.open("r+b") as handle:
        handle.seek(17)
        handle.write(b"\xff")
    with pytest.raises(HBMShardError, match="hash differs"):
        hardlink_verified_shard_prefix(
            target_root,
            target["shards"],
            source_root=source_root,
            source_shards=source["shards"],
            shard_count=1,
        )
    assert target_path.stat().st_ino == target_inode
