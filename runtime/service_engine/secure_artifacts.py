"""Race-resistant artifact-tree I/O for production service engines.

Compiler output, execution requests, and result directories are untrusted
filesystem namespaces.  This module centralizes the mechanics required to
consume and publish them without following symlinks or silently accepting a
replacement between validation and use:

* every path component is opened relative to a held directory descriptor;
* regular files use ``O_NOFOLLOW`` and ``O_NONBLOCK`` and remain open;
* reads are bounded and use ``pread`` from a stable inode;
* root and file fingerprints are rechecked against both held descriptors and
  freshly reopened namespace entries;
* JSON must already be in the canonical byte representation accepted here;
* result publication is create-once via Linux ``renameat2(RENAME_NOREPLACE)``;
* failed publication cleanup is inode-bound and entry/depth bounded.

The caller still chooses a trusted parent directory and defines the exact
schema, role/path closure, byte bounds, and content hashes.  Same-identity
processes that can mutate an already opened regular file remain outside the
filesystem permission boundary, but such mutation is detected before
authority is returned.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
from typing import Any, NoReturn


READ_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_TREE_DEPTH = 12
DEFAULT_MAX_TREE_ENTRIES = 256
_RENAME_NOREPLACE = 1


class SecureArtifactError(RuntimeError):
    """Raised when an artifact tree cannot be consumed or published safely."""


def _poison(message: str, cause: BaseException | None = None) -> NoReturn:
    if cause is None:
        raise SecureArtifactError(message)
    raise SecureArtifactError(message) from cause


def require_secure_platform() -> None:
    """Fail closed unless descriptor-relative race-resistant operations exist."""

    required_dir_fd = (os.open, os.mkdir, os.rmdir, os.stat, os.unlink)
    if (
        not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "pread")
        or any(operation not in os.supports_dir_fd for operation in required_dir_fd)
    ):
        _poison("platform lacks descriptor-relative secure artifact operations")
    if getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None) is None:
        _poison("platform lacks atomic rename-without-replacement support")


def fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    """Return the complete metadata identity guarded during one transaction."""

    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def canonical_json_bytes(value: object) -> bytes:
    """Serialize one JSON value with the service-engine canonical profile."""

    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError, UnicodeError) as exc:
        _poison(f"value is not canonical JSON: {exc}", exc)


def _reject_constant(value: str) -> NoReturn:
    _poison(f"non-finite JSON constant {value!r} is forbidden")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            _poison("JSON object contains a non-string key")
        if key in result:
            _poison(f"JSON object repeats key {key!r}")
        result[key] = value
    return result


def parse_canonical_json(
    payload: bytes,
    *,
    label: str,
    maximum_bytes: int,
) -> Any:
    """Parse exact canonical JSON with duplicate/nonfinite rejection."""

    if type(payload) is not bytes:
        _poison(f"{label} payload must be exact bytes")
    if (
        type(maximum_bytes) is not int
        or maximum_bytes < 1
        or not 1 <= len(payload) <= maximum_bytes
    ):
        _poison(f"{label} exceeds its bounded JSON size")
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (RecursionError, ValueError, UnicodeError) as exc:
        _poison(f"{label} is not valid UTF-8 JSON: {exc}", exc)
    if canonical_json_bytes(value) != payload:
        _poison(f"{label} is not canonical JSON")
    return value


def safe_relative_path(value: object, *, label: str) -> str:
    """Validate a canonical nonempty POSIX path beneath a held root."""

    if (
        type(value) is not str
        or value in {"", ".", ".."}
        or "\\" in value
        or "\x00" in value
    ):
        _poison(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        _poison(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        _poison(f"{label} is not canonical POSIX")
    return value


def _open_relative(
    root_descriptor: int,
    relative: str,
    *,
    label: str,
    directory: bool,
) -> int:
    parts = Path(safe_relative_path(relative, label=label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    current = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        flags = directory_flags if directory else file_flags
        return os.open(parts[-1], flags, dir_fd=current)
    except OSError as exc:
        _poison(f"cannot open {label} without following symlinks: {exc}", exc)
    finally:
        os.close(current)


@dataclass(frozen=True)
class SecureFile:
    """One held regular file and the fingerprint observed when it was opened."""

    relative_path: str
    descriptor: int
    guarded_fingerprint: tuple[int, ...]
    size_bytes: int
    guarded_sha256: str

    def read_bytes(self, *, label: str, maximum_bytes: int) -> bytes:
        if (
            type(maximum_bytes) is not int
            or maximum_bytes < 1
            or self.size_bytes > maximum_bytes
        ):
            _poison(f"{label} exceeds its read bound")
        before = fingerprint(os.fstat(self.descriptor))
        if before != self.guarded_fingerprint:
            _poison(f"{label} changed before it was read")
        chunks: list[bytes] = []
        offset = 0
        while offset < self.size_bytes:
            try:
                chunk = os.pread(
                    self.descriptor,
                    min(READ_CHUNK_BYTES, self.size_bytes - offset),
                    offset,
                )
            except OSError as exc:
                _poison(f"cannot read {label}: {exc}", exc)
            if not chunk:
                _poison(f"{label} ended before its declared size")
            chunks.append(chunk)
            offset += len(chunk)
        if fingerprint(os.fstat(self.descriptor)) != before:
            _poison(f"{label} changed while it was read")
        payload = b"".join(chunks)
        if hashlib.sha256(payload).hexdigest() != self.guarded_sha256:
            _poison(f"{label} content changed after it was opened")
        return payload

    def sha256(self, *, label: str) -> str:
        before = fingerprint(os.fstat(self.descriptor))
        if before != self.guarded_fingerprint:
            _poison(f"{label} changed before it was hashed")
        digest = hashlib.sha256()
        offset = 0
        while offset < self.size_bytes:
            try:
                chunk = os.pread(
                    self.descriptor,
                    min(READ_CHUNK_BYTES, self.size_bytes - offset),
                    offset,
                )
            except OSError as exc:
                _poison(f"cannot hash {label}: {exc}", exc)
            if not chunk:
                _poison(f"{label} ended before its declared size")
            digest.update(chunk)
            offset += len(chunk)
        if fingerprint(os.fstat(self.descriptor)) != before:
            _poison(f"{label} changed while it was hashed")
        observed = digest.hexdigest()
        if observed != self.guarded_sha256:
            _poison(f"{label} content changed after it was opened")
        return observed


class SecureDirectory:
    """Held artifact root whose opened files can be reverified as one snapshot."""

    def __init__(self, root: Path, *, label: str):
        require_secure_platform()
        self.root = Path(root).absolute()
        self.label = label
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            self.descriptor = os.open(self.root, flags)
        except OSError as exc:
            _poison(f"cannot open {label} without following symlinks: {exc}", exc)
        metadata = os.fstat(self.descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            os.close(self.descriptor)
            _poison(f"{label} is not a directory")
        self.guarded_fingerprint = fingerprint(metadata)
        self._files: list[SecureFile] = []
        self._closed = False

    def __enter__(self) -> SecureDirectory:
        if self._closed:
            _poison(f"{self.label} snapshot is closed")
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        for source in reversed(self._files):
            try:
                os.close(source.descriptor)
            except OSError:
                pass
        self._files.clear()
        os.close(self.descriptor)
        self._closed = True

    def open_file(
        self,
        relative: str,
        *,
        label: str,
        minimum_size: int = 1,
        maximum_size: int,
        exact_size: int | None = None,
    ) -> SecureFile:
        if self._closed:
            _poison(f"{self.label} snapshot is closed")
        if (
            type(minimum_size) is not int
            or type(maximum_size) is not int
            or minimum_size < 0
            or maximum_size < minimum_size
            or (exact_size is not None and type(exact_size) is not int)
        ):
            _poison(f"{label} has invalid file-size bounds")
        descriptor = _open_relative(
            self.descriptor,
            relative,
            label=label,
            directory=False,
        )
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _poison(f"{label} is not a regular file")
            if exact_size is not None and metadata.st_size != exact_size:
                _poison(f"{label} has {metadata.st_size} bytes, expected {exact_size}")
            if not minimum_size <= metadata.st_size <= maximum_size:
                _poison(f"{label} exceeds its bounded size")
            guarded_fingerprint = fingerprint(metadata)
            digest = hashlib.sha256()
            offset = 0
            try:
                while offset < metadata.st_size:
                    chunk = os.pread(
                        descriptor,
                        min(READ_CHUNK_BYTES, metadata.st_size - offset),
                        offset,
                    )
                    if not chunk:
                        _poison(f"{label} ended while its opening digest was computed")
                    digest.update(chunk)
                    offset += len(chunk)
            except OSError as exc:
                _poison(f"cannot hash {label} while opening it: {exc}", exc)
            if fingerprint(os.fstat(descriptor)) != guarded_fingerprint:
                _poison(f"{label} changed while it was opened")
            source = SecureFile(
                relative_path=safe_relative_path(relative, label=label),
                descriptor=descriptor,
                guarded_fingerprint=guarded_fingerprint,
                size_bytes=metadata.st_size,
                guarded_sha256=digest.hexdigest(),
            )
        except Exception:
            os.close(descriptor)
            raise
        self._files.append(source)
        return source

    def enumerate_tree(
        self,
        *,
        maximum_depth: int = DEFAULT_MAX_TREE_DEPTH,
        maximum_entries: int = DEFAULT_MAX_TREE_ENTRIES,
    ) -> tuple[set[str], set[str]]:
        """Return exact regular-file and directory paths beneath the held root."""

        if self._closed:
            _poison(f"{self.label} snapshot is closed")
        if (
            type(maximum_depth) is not int
            or type(maximum_entries) is not int
            or maximum_depth < 0
            or maximum_entries < 1
        ):
            _poison("tree enumeration bounds are invalid")
        files: set[str] = set()
        directories: set[str] = set()
        visited = 0
        directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW

        def visit(descriptor: int, prefix: str, depth: int) -> None:
            nonlocal visited
            if depth > maximum_depth:
                _poison(f"{self.label} exceeds its tree-depth bound")
            try:
                names = os.listdir(descriptor)
            except OSError as exc:
                _poison(f"cannot enumerate {self.label}: {exc}", exc)
            visited += len(names)
            if visited > maximum_entries:
                _poison(f"{self.label} exceeds its tree-entry bound")
            for name in names:
                if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                    _poison(f"{self.label} contains an unsafe entry name")
                relative = f"{prefix}/{name}" if prefix else name
                try:
                    metadata = os.stat(
                        name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                except OSError as exc:
                    _poison(f"cannot inspect {relative!r}: {exc}", exc)
                if stat.S_ISDIR(metadata.st_mode):
                    directories.add(relative)
                    try:
                        child = os.open(name, directory_flags, dir_fd=descriptor)
                    except OSError as exc:
                        _poison(
                            f"cannot open artifact directory {relative!r}: {exc}",
                            exc,
                        )
                    try:
                        visit(child, relative, depth + 1)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(metadata.st_mode):
                    files.add(relative)
                else:
                    _poison(f"{self.label} contains non-regular entry {relative!r}")

        visit(self.descriptor, "", 0)
        return files, directories

    def verify(self) -> None:
        """Recheck held inodes and freshly reopened namespace bindings."""

        if self._closed:
            _poison(f"{self.label} snapshot is closed")
        if fingerprint(os.fstat(self.descriptor)) != self.guarded_fingerprint:
            _poison(f"{self.label} root changed while held")
        self.verify_identity()

        for source in self._files:
            if fingerprint(os.fstat(source.descriptor)) != source.guarded_fingerprint:
                _poison(f"artifact {source.relative_path!r} changed while held")
            source.sha256(label=f"artifact {source.relative_path!r}")
            current_descriptor = _open_relative(
                self.descriptor,
                source.relative_path,
                label=f"artifact {source.relative_path!r}",
                directory=False,
            )
            try:
                if (
                    fingerprint(os.fstat(current_descriptor))
                    != source.guarded_fingerprint
                ):
                    _poison(f"artifact {source.relative_path!r} was replaced")
            finally:
                os.close(current_descriptor)

    def verify_identity(self) -> None:
        """Recheck only the held root's namespace identity.

        Publication necessarily changes its parent directory metadata.  The
        parent is therefore guarded by inode identity while the staged or
        consumed artifact root itself uses :meth:`verify`'s full fingerprint.
        """

        if self._closed:
            _poison(f"{self.label} snapshot is closed")
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            current_root = os.open(self.root, flags)
        except OSError as exc:
            _poison(f"cannot reopen {self.label}: {exc}", exc)
        try:
            current = os.fstat(current_root)
            held = os.fstat(self.descriptor)
            if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
                _poison(f"{self.label} root was replaced")
        finally:
            os.close(current_root)


def _write_exclusive_bytes(
    root_descriptor: int,
    relative: str,
    payload: bytes,
) -> None:
    if type(payload) is not bytes:
        _poison(f"published artifact {relative!r} is not exact bytes")
    parts = Path(safe_relative_path(relative, label="published artifact path")).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.dup(root_descriptor)
    descriptor: int | None = None
    try:
        for part in parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=current,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                _poison(f"published artifact {relative!r} ended while writing")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            _poison(f"published artifact {relative!r} is incomplete")
    except OSError as exc:
        _poison(f"cannot write published artifact {relative!r}: {exc}", exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _rename_no_replace(
    *,
    parent_descriptor: int,
    source_name: str,
    destination_name: str,
    label: str,
) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(library, "renameat2", None)
    if renameat2 is None:  # pragma: no cover - platform checked first
        _poison("platform lacks atomic rename-without-replacement support")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_descriptor,
        os.fsencode(source_name),
        parent_descriptor,
        os.fsencode(destination_name),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        _poison(f"{label} already exists")
    _poison(f"cannot atomically publish {label}: {os.strerror(error)}")


def _same_directory_entry(
    *,
    parent_descriptor: int,
    name: str,
    held_descriptor: int,
) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError:
        return False
    try:
        observed = os.fstat(current)
        held = os.fstat(held_descriptor)
        return (observed.st_dev, observed.st_ino) == (held.st_dev, held.st_ino)
    finally:
        os.close(current)


def _cleanup_held_tree(
    *,
    parent_descriptor: int,
    name: str,
    held_descriptor: int,
    maximum_depth: int,
    maximum_entries: int,
) -> None:
    if not _same_directory_entry(
        parent_descriptor=parent_descriptor,
        name=name,
        held_descriptor=held_descriptor,
    ):
        _poison("refusing to clean a replaced temporary artifact tree")
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    visited = 0

    def remove_contents(descriptor: int, depth: int) -> None:
        nonlocal visited
        if depth > maximum_depth:
            _poison("temporary artifact cleanup exceeds its depth bound")
        names = os.listdir(descriptor)
        visited += len(names)
        if visited > maximum_entries:
            _poison("temporary artifact cleanup exceeds its entry bound")
        for child_name in names:
            if (
                child_name in {"", ".", ".."}
                or "/" in child_name
                or "\x00" in child_name
            ):
                _poison("temporary artifact tree contains an unsafe entry")
            metadata = os.stat(
                child_name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(child_name, directory_flags, dir_fd=descriptor)
                try:
                    remove_contents(child, depth + 1)
                finally:
                    os.close(child)
                os.rmdir(child_name, dir_fd=descriptor)
            else:
                os.unlink(child_name, dir_fd=descriptor)

    remove_contents(held_descriptor, 0)
    os.rmdir(name, dir_fd=parent_descriptor)


def publish_payload_tree(
    output: Path,
    *,
    payloads: Mapping[str, bytes],
    directories: Sequence[str],
    label: str,
    maximum_depth: int = DEFAULT_MAX_TREE_DEPTH,
    maximum_entries: int = DEFAULT_MAX_TREE_ENTRIES,
) -> None:
    """Atomically create one exact artifact tree without replacing a target."""

    require_secure_platform()
    raw_output = Path(output)
    if not raw_output.name or raw_output.name in {".", ".."}:
        _poison(f"{label} output must name one directory")
    output = raw_output.absolute()
    if output == Path(output.anchor):
        _poison(f"{label} output must not be a filesystem root")
    if type(payloads) is not dict or not payloads:
        _poison(f"{label} payload closure must be a nonempty exact dictionary")
    if type(directories) not in {list, tuple}:
        _poison(f"{label} directories must be an exact list or tuple")
    payload_paths = {
        safe_relative_path(path, label=f"{label} payload path") for path in payloads
    }
    if len(payload_paths) != len(payloads) or any(
        type(payload) is not bytes for payload in payloads.values()
    ):
        _poison(f"{label} payload closure is invalid")
    directory_paths = tuple(
        safe_relative_path(path, label=f"{label} directory path")
        for path in directories
    )
    if len(set(directory_paths)) != len(directory_paths):
        _poison(f"{label} repeats a directory path")
    required_parents = {
        parent.as_posix()
        for path in payload_paths
        for parent in Path(path).parents
        if parent != Path(".")
    }
    if required_parents != set(directory_paths):
        _poison(f"{label} directory closure differs from payload parents")
    if len(payload_paths) + len(directory_paths) > maximum_entries:
        _poison(f"{label} exceeds its tree-entry bound")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        parent = SecureDirectory(output.parent, label=f"{label} parent")
        stack.callback(parent.close)
        try:
            os.stat(output.name, dir_fd=parent.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as exc:
            _poison(f"cannot inspect {label} output: {exc}", exc)
        else:
            _poison(f"{label} already exists")

        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
        temporary_name = ""
        temporary_descriptor: int | None = None
        for _ in range(128):
            candidate = f".{output.name}.tmp-{secrets.token_hex(16)}"
            try:
                os.mkdir(candidate, 0o700, dir_fd=parent.descriptor)
            except FileExistsError:
                continue
            except OSError as exc:
                _poison(f"cannot create private {label} directory: {exc}", exc)
            temporary_name = candidate
            try:
                temporary_descriptor = os.open(
                    candidate,
                    flags,
                    dir_fd=parent.descriptor,
                )
            except OSError as exc:
                try:
                    os.rmdir(candidate, dir_fd=parent.descriptor)
                except OSError:
                    pass
                _poison(f"cannot open private {label} directory: {exc}", exc)
            break
        if temporary_descriptor is None:
            _poison(f"cannot reserve a collision-free private {label} directory")
        stack.callback(os.close, temporary_descriptor)

        published = False
        namespace_committed = False
        try:
            for relative in sorted(
                directory_paths,
                key=lambda path: (len(Path(path).parts), path),
            ):
                parts = Path(relative).parts
                current = os.dup(temporary_descriptor)
                try:
                    for part in parts[:-1]:
                        following = os.open(part, flags, dir_fd=current)
                        os.close(current)
                        current = following
                    os.mkdir(parts[-1], 0o700, dir_fd=current)
                finally:
                    os.close(current)
            for relative in sorted(payload_paths):
                _write_exclusive_bytes(
                    temporary_descriptor,
                    relative,
                    payloads[relative],
                )
            for relative in sorted(
                directory_paths,
                key=lambda path: (-len(Path(path).parts), path),
            ):
                descriptor = _open_relative(
                    temporary_descriptor,
                    relative,
                    label=f"{label} staged directory {relative!r}",
                    directory=True,
                )
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            os.fsync(temporary_descriptor)

            temporary_root = output.parent / temporary_name
            with SecureDirectory(temporary_root, label=f"staged {label}") as staged:
                files, observed_directories = staged.enumerate_tree(
                    maximum_depth=maximum_depth,
                    maximum_entries=maximum_entries,
                )
                if files != payload_paths or observed_directories != set(
                    directory_paths
                ):
                    _poison(f"staged {label} tree closure differs")
                for relative in sorted(payload_paths):
                    source = staged.open_file(
                        relative,
                        label=f"staged {label} artifact {relative!r}",
                        minimum_size=0,
                        maximum_size=len(payloads[relative]),
                        exact_size=len(payloads[relative]),
                    )
                    observed = source.read_bytes(
                        label=f"staged {label} artifact {relative!r}",
                        maximum_bytes=max(1, len(payloads[relative])),
                    )
                    if observed != payloads[relative]:
                        _poison(f"staged {label} artifact {relative!r} differs")
                staged.verify()
            parent.verify_identity()
            _rename_no_replace(
                parent_descriptor=parent.descriptor,
                source_name=temporary_name,
                destination_name=output.name,
                label=label,
            )
            namespace_committed = True
            if not _same_directory_entry(
                parent_descriptor=parent.descriptor,
                name=output.name,
                held_descriptor=temporary_descriptor,
            ):
                _poison(f"published {label} root was replaced")
            os.fsync(parent.descriptor)
            parent.verify_identity()
            if not _same_directory_entry(
                parent_descriptor=parent.descriptor,
                name=output.name,
                held_descriptor=temporary_descriptor,
            ):
                _poison(f"published {label} root was replaced after sync")
            published = True
        finally:
            if not published:
                cleanup_name = temporary_name
                if namespace_committed:
                    try:
                        _rename_no_replace(
                            parent_descriptor=parent.descriptor,
                            source_name=output.name,
                            destination_name=temporary_name,
                            label=f"failed {label} rollback",
                        )
                    except SecureArtifactError:
                        cleanup_name = ""
                if cleanup_name:
                    _cleanup_held_tree(
                        parent_descriptor=parent.descriptor,
                        name=cleanup_name,
                        held_descriptor=temporary_descriptor,
                        maximum_depth=maximum_depth,
                        maximum_entries=maximum_entries,
                    )


__all__ = [
    "DEFAULT_MAX_TREE_DEPTH",
    "DEFAULT_MAX_TREE_ENTRIES",
    "READ_CHUNK_BYTES",
    "SecureArtifactError",
    "SecureDirectory",
    "SecureFile",
    "canonical_json_bytes",
    "fingerprint",
    "parse_canonical_json",
    "publish_payload_tree",
    "require_secure_platform",
    "safe_relative_path",
]
