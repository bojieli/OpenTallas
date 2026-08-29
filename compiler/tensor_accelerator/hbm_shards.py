"""Streaming sparse HBM shard construction and verified logical access.

Large production deployments must not materialize one logical HBM image as a
Python ``bytes`` object.  This module provides a monotonic mmap-backed writer
and an independent logical reader over fixed-size, content-bound shard files.
The layout policy remains the caller's responsibility; this module only owns
byte-exact storage, sparse-zero semantics, and range-safe access.
"""

from __future__ import annotations

import hashlib
import mmap
import os
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable, Mapping, Sequence

from .common import ArtifactError, sha256_file


DEFAULT_SHARD_BYTES = 1 << 30
HASH_CHUNK_BYTES = 8 * 1024 * 1024
_ZERO_CHUNK = bytes(HASH_CHUNK_BYTES)


class HBMShardError(ArtifactError):
    """Raised when an HBM shard set is incomplete, corrupt, or unsafe."""


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise HBMShardError(f"{label} must be an integer >= {minimum}")
    return value


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise HBMShardError(f"{label} must be a safe relative POSIX path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise HBMShardError(f"{label} must be a safe relative POSIX path")
    if parsed.as_posix() != value:
        raise HBMShardError(f"{label} is not in canonical POSIX form")
    return value


def _update_zeros(digest: object, size: int) -> None:
    remaining = size
    while remaining:
        count = min(remaining, len(_ZERO_CHUNK))
        digest.update(memoryview(_ZERO_CHUNK)[:count])
        remaining -= count


class HBMShardWriter:
    """Write one pre-sized logical image monotonically into sparse mmap shards."""

    def __init__(
        self,
        root: Path,
        *,
        total_size: int,
        shard_bytes: int = DEFAULT_SHARD_BYTES,
        relative_directory: str = "memory/hbm",
    ) -> None:
        self._root = Path(root)
        self._total_size = _integer(total_size, "total_size", minimum=1)
        self._shard_bytes = _integer(shard_bytes, "shard_bytes", minimum=4096)
        if self._shard_bytes & (self._shard_bytes - 1):
            raise HBMShardError("shard_bytes must be a power of two")
        self._relative_directory = _safe_relative(
            relative_directory, "relative_directory"
        )
        self._directory = self._root / self._relative_directory
        if self._directory.exists():
            raise HBMShardError(
                f"HBM shard directory already exists: {self._directory}"
            )
        self._directory.mkdir(parents=True)
        self._shard_sizes = tuple(
            min(self._shard_bytes, self._total_size - offset)
            for offset in range(0, self._total_size, self._shard_bytes)
        )
        self._staging_paths: list[Path] = []
        self._published_paths: list[Path] = []
        self._cursor = 0
        self._overall_digest = hashlib.sha256()
        self._shard_digests = [hashlib.sha256() for _ in self._shard_sizes]
        self._active_index: int | None = None
        self._active_handle: BinaryIO | None = None
        self._active_map: mmap.mmap | None = None
        self._finished = False
        try:
            for index, size in enumerate(self._shard_sizes):
                path = self._directory / f"hbm.{index:05d}.staging.bin"
                with path.open("xb") as handle:
                    handle.truncate(size)
                    handle.flush()
                    os.fsync(handle.fileno())
                self._staging_paths.append(path)
        except Exception:
            self.abort()
            raise

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def total_size(self) -> int:
        return self._total_size

    @property
    def shard_bytes(self) -> int:
        return self._shard_bytes

    def _require_writable(self) -> None:
        if self._finished:
            raise HBMShardError("HBM shard writer is already finished")

    def _close_active(self) -> None:
        if self._active_map is not None:
            self._active_map.flush()
            self._active_map.close()
            self._active_map = None
        if self._active_handle is not None:
            self._active_handle.flush()
            os.fsync(self._active_handle.fileno())
            self._active_handle.close()
            self._active_handle = None
        self._active_index = None

    def _mapping(self, index: int) -> mmap.mmap:
        if self._active_index == index and self._active_map is not None:
            return self._active_map
        if self._active_index is not None and index < self._active_index:
            raise HBMShardError("HBM shard writes must be monotonically addressed")
        self._close_active()
        try:
            handle = self._staging_paths[index].open("r+b")
            mapping = mmap.mmap(handle.fileno(), self._shard_sizes[index])
        except OSError as exc:
            if "handle" in locals():
                handle.close()
            raise HBMShardError(f"cannot mmap HBM shard {index}: {exc}") from exc
        self._active_index = index
        self._active_handle = handle
        self._active_map = mapping
        return mapping

    def advance_to(self, offset: int) -> None:
        target = _integer(offset, "HBM target offset")
        if target < self._cursor or target > self._total_size:
            raise HBMShardError("HBM target offset is outside the monotonic image")
        self.skip_zeros(target - self._cursor)

    def skip_zeros(self, size: int) -> None:
        self._require_writable()
        remaining = _integer(size, "zero extent size")
        if self._cursor + remaining > self._total_size:
            raise HBMShardError("zero extent exceeds the logical HBM image")
        while remaining:
            shard_index = self._cursor // self._shard_bytes
            within = self._cursor % self._shard_bytes
            count = min(remaining, self._shard_sizes[shard_index] - within)
            _update_zeros(self._overall_digest, count)
            _update_zeros(self._shard_digests[shard_index], count)
            self._cursor += count
            remaining -= count

    def write(self, payload: bytes | bytearray | memoryview) -> None:
        self._require_writable()
        try:
            view = memoryview(payload).cast("B")
        except (TypeError, ValueError) as exc:
            raise HBMShardError("HBM payload must be a contiguous byte buffer") from exc
        if self._cursor + len(view) > self._total_size:
            raise HBMShardError("HBM payload exceeds the logical image")
        consumed = 0
        while consumed < len(view):
            shard_index = self._cursor // self._shard_bytes
            within = self._cursor % self._shard_bytes
            count = min(
                len(view) - consumed,
                self._shard_sizes[shard_index] - within,
            )
            piece = view[consumed : consumed + count]
            mapping = self._mapping(shard_index)
            mapping[within : within + count] = piece
            self._overall_digest.update(piece)
            self._shard_digests[shard_index].update(piece)
            self._cursor += count
            consumed += count

    def finish(self) -> dict[str, object]:
        self._require_writable()
        if self._cursor != self._total_size:
            raise HBMShardError(
                f"logical HBM image is incomplete: {self._cursor} != {self._total_size}"
            )
        self._close_active()
        expected_shards = [digest.hexdigest() for digest in self._shard_digests]
        records: list[dict[str, object]] = []
        try:
            for index, (path, size, expected) in enumerate(
                zip(
                    self._staging_paths,
                    self._shard_sizes,
                    expected_shards,
                    strict=True,
                )
            ):
                observed, observed_size = sha256_file(path)
                if observed != expected or observed_size != size:
                    raise HBMShardError(
                        f"HBM shard {index} differs after mmap publication"
                    )
                name = f"hbm.{index:05d}.{observed}.bin"
                final_path = path.with_name(name)
                os.replace(path, final_path)
                self._published_paths.append(final_path)
                records.append(
                    {
                        "index": index,
                        "logical_offset": index * self._shard_bytes,
                        "path": (
                            PurePosixPath(self._relative_directory) / name
                        ).as_posix(),
                        "sha256": observed,
                        "size_bytes": size,
                    }
                )
        except Exception:
            self.abort()
            raise
        self._finished = True
        self._staging_paths.clear()
        self._published_paths.clear()
        return {
            "logical_sha256": self._overall_digest.hexdigest(),
            "shard_bytes": self._shard_bytes,
            "shards": records,
            "size_bytes": self._total_size,
        }

    def abort(self) -> None:
        self._close_active()
        for path in self._staging_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self._staging_paths.clear()
        for path in self._published_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self._published_paths.clear()
        if getattr(self, "_directory", None) is not None:
            try:
                self._directory.rmdir()
            except (FileNotFoundError, OSError):
                pass
        self._finished = True

    def __enter__(self) -> HBMShardWriter:
        self._require_writable()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is not None or not self._finished:
            self.abort()


class HBMShardReader:
    """Range-safe logical reader over a content-bound HBM shard table."""

    def __init__(
        self,
        root: Path,
        shards: Sequence[Mapping[str, object]],
        *,
        verify_hashes: bool = True,
    ) -> None:
        self._root = Path(root)
        if not isinstance(shards, Sequence) or not shards:
            raise HBMShardError("HBM shard table must be nonempty")
        parsed: list[dict[str, object]] = []
        cursor = 0
        for expected_index, raw in enumerate(shards):
            if not isinstance(raw, Mapping) or set(raw) != {
                "index",
                "logical_offset",
                "path",
                "sha256",
                "size_bytes",
            }:
                raise HBMShardError(f"HBM shard {expected_index} keys differ")
            index = _integer(raw["index"], f"HBM shard {expected_index}.index")
            offset = _integer(
                raw["logical_offset"],
                f"HBM shard {expected_index}.logical_offset",
            )
            size = _integer(
                raw["size_bytes"], f"HBM shard {expected_index}.size_bytes", minimum=1
            )
            path = _safe_relative(raw["path"], f"HBM shard {expected_index}.path")
            digest = raw["sha256"]
            if (
                index != expected_index
                or offset != cursor
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise HBMShardError(f"HBM shard {expected_index} identity differs")
            full_path = self._root / path
            try:
                observed_size = full_path.stat().st_size
            except OSError as exc:
                raise HBMShardError(f"cannot stat HBM shard {path}: {exc}") from exc
            if observed_size != size:
                raise HBMShardError(f"HBM shard {expected_index} size differs")
            if verify_hashes:
                observed, hashed_size = sha256_file(full_path)
                if observed != digest or hashed_size != size:
                    raise HBMShardError(f"HBM shard {expected_index} hash differs")
            parsed.append(
                {
                    "index": index,
                    "logical_offset": offset,
                    "path": path,
                    "sha256": digest,
                    "size_bytes": size,
                }
            )
            cursor += size
        self._shards = tuple(parsed)
        self._starts = tuple(int(item["logical_offset"]) for item in parsed)
        self._total_size = cursor
        self._handles: dict[int, BinaryIO] = {}

    @property
    def total_size(self) -> int:
        return self._total_size

    def _handle(self, index: int) -> BinaryIO:
        handle = self._handles.get(index)
        if handle is None:
            try:
                handle = (self._root / str(self._shards[index]["path"])).open("rb")
            except OSError as exc:
                raise HBMShardError(f"cannot open HBM shard {index}: {exc}") from exc
            self._handles[index] = handle
        return handle

    def consume(
        self,
        offset: int,
        size: int,
        consumer: Callable[[bytes], None],
        *,
        chunk_bytes: int = HASH_CHUNK_BYTES,
    ) -> None:
        start = _integer(offset, "HBM read offset")
        remaining = _integer(size, "HBM read size")
        chunk_bytes = _integer(chunk_bytes, "HBM read chunk", minimum=1)
        if start + remaining > self._total_size:
            raise HBMShardError("HBM logical read exceeds the shard set")
        cursor = start
        while remaining:
            shard_index = next(
                index
                for index, record in enumerate(self._shards)
                if int(record["logical_offset"])
                <= cursor
                < int(record["logical_offset"]) + int(record["size_bytes"])
            )
            record = self._shards[shard_index]
            within = cursor - int(record["logical_offset"])
            count = min(
                remaining,
                chunk_bytes,
                int(record["size_bytes"]) - within,
            )
            handle = self._handle(shard_index)
            try:
                handle.seek(within)
                payload = handle.read(count)
            except OSError as exc:
                raise HBMShardError(
                    f"cannot read HBM shard {shard_index}: {exc}"
                ) from exc
            if len(payload) != count:
                raise HBMShardError(f"short read from HBM shard {shard_index}")
            consumer(payload)
            cursor += count
            remaining -= count

    def read(self, offset: int, size: int) -> bytes:
        if size > 256 * 1024 * 1024:
            raise HBMShardError("one materialized HBM read exceeds 256 MiB")
        chunks: list[bytes] = []
        self.consume(offset, size, chunks.append)
        return b"".join(chunks)

    def sha256(self, offset: int, size: int) -> str:
        digest = hashlib.sha256()
        self.consume(offset, size, digest.update)
        return digest.hexdigest()

    def require_zero(self, offset: int, size: int) -> None:
        def check(chunk: bytes) -> None:
            if any(chunk):
                raise HBMShardError("HBM zero extent contains nonzero data")

        self.consume(offset, size, check)

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    def __enter__(self) -> HBMShardReader:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


__all__ = [
    "DEFAULT_SHARD_BYTES",
    "HASH_CHUNK_BYTES",
    "HBMShardError",
    "HBMShardReader",
    "HBMShardWriter",
]
