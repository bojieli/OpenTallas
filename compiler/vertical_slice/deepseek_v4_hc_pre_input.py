"""Create-once composer for checkpoint-derived DeepSeek V4 ``HC_PRE`` input.

The independent checker owns all semantic derivation.  This module only
materializes the checker's exact BF16 payload, canonical request manifest, and
external provenance report into private objects, rechecks them, and publishes
them without replacement.  The request directory is the publication commit
point; the report is published first and is removed by inode identity if the
directory publication loses a race.

Namespace publication is atomic within each caller-trusted parent.  As with the
other compiler packages, this layer makes no claim of surviving a system crash
without an explicitly fsynced parent-directory transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import ExitStack
import ctypes
import errno
import os
from pathlib import Path
import secrets
import shutil
import stat
from typing import Any

from compiler.checking.deepseek_v4_hc_pre_input import (
    INPUT_RELATIVE,
    REQUEST_MANIFEST,
    _derive_material,
    verify_deepseek_v4_hc_pre_input_composition,
)
from compiler.ir.model import canonical_json_bytes


_MINIMUM_FREE_BYTES = 4 * 1024 * 1024
_MAX_CLEANUP_ENTRIES = 8
_MAX_TREE_DEPTH = 3


class DeepSeekV4HCPreInputBuildError(RuntimeError):
    """Raised when a causally verified HC_PRE request cannot be published."""


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _require_secure_file_operations() -> None:
    required_dir_fd = (os.open, os.mkdir, os.rmdir, os.stat, os.unlink)
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or any(operation not in os.supports_dir_fd for operation in required_dir_fd)
    ):
        raise DeepSeekV4HCPreInputBuildError(
            "platform lacks race-resistant HC_PRE input publication operations"
        )
    if getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None) is None:
        raise DeepSeekV4HCPreInputBuildError(
            "platform lacks atomic rename-without-replacement support"
        )


def _specific_path(value: Path, label: str) -> Path:
    try:
        path = Path(value).absolute()
    except TypeError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"{label} must be a filesystem path"
        ) from exc
    if not path.name or path.name in {".", ".."} or path == Path(path.anchor):
        raise DeepSeekV4HCPreInputBuildError(f"{label} must name a specific path")
    return path


def _safe_relative(value: str, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreInputBuildError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreInputBuildError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreInputBuildError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, root: Path, label: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        raise DeepSeekV4HCPreInputBuildError(f"{label} is not a directory")
    return descriptor


def _verify_root_binding(root: Path, descriptor: int, label: str) -> None:
    held = os.fstat(descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
            held.st_dev,
            held.st_ino,
        ):
            raise DeepSeekV4HCPreInputBuildError(f"{label} was replaced")
    finally:
        os.close(current_descriptor)


def _create_private_directory(
    stack: ExitStack,
    *,
    parent: Path,
    parent_descriptor: int,
) -> tuple[Path, str, int]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    for _ in range(128):
        name = f".hc-pre-input.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4HCPreInputBuildError(
                f"cannot create private HC_PRE request directory: {exc}"
            ) from exc
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise DeepSeekV4HCPreInputBuildError(
                f"cannot open private HC_PRE request directory: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise DeepSeekV4HCPreInputBuildError(
                "private HC_PRE request path is not a directory"
            )
        return parent / name, name, descriptor
    raise DeepSeekV4HCPreInputBuildError(
        "cannot reserve a collision-free HC_PRE request directory"
    )


def _write_exclusive_bytes(
    root_descriptor: int,
    relative: str,
    payload: bytes,
) -> None:
    if type(payload) is not bytes:
        raise DeepSeekV4HCPreInputBuildError(
            f"generated artifact {relative!r} is not exact bytes"
        )
    parts = Path(_safe_relative(relative, "generated artifact path")).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_descriptor = os.dup(root_descriptor)
    descriptor: int | None = None
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part, directory_flags, dir_fd=directory_descriptor
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise DeepSeekV4HCPreInputBuildError(
                    f"generated artifact {relative!r} ended while being written"
                )
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            raise DeepSeekV4HCPreInputBuildError(
                f"generated artifact {relative!r} size differs after write"
            )
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot write generated artifact {relative!r}: {exc}"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_descriptor)


def _create_private_report(
    stack: ExitStack,
    *,
    parent: Path,
    parent_descriptor: int,
    payload: bytes,
) -> tuple[Path, str, int, tuple[int, ...]]:
    for _ in range(128):
        name = f".hc-pre-input-report.tmp-{secrets.token_hex(16)}"
        try:
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_descriptor,
            )
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4HCPreInputBuildError(
                f"cannot create private HC_PRE composition report: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise DeepSeekV4HCPreInputBuildError(
                        "private HC_PRE composition report ended while being written"
                    )
                offset += written
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
                raise DeepSeekV4HCPreInputBuildError(
                    "private HC_PRE composition report size differs"
                )
        except Exception as exc:
            try:
                held = os.fstat(descriptor)
                current = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
                    raise DeepSeekV4HCPreInputBuildError(
                        "refusing to clean a replaced private composition report"
                    )
                os.unlink(name, dir_fd=parent_descriptor)
            except OSError as cleanup_exc:
                raise DeepSeekV4HCPreInputBuildError(
                    "cannot clean a failed private HC_PRE composition report: "
                    f"{cleanup_exc}"
                ) from exc
            if isinstance(exc, DeepSeekV4HCPreInputBuildError):
                raise
            raise DeepSeekV4HCPreInputBuildError(
                f"cannot write private HC_PRE composition report: {exc}"
            ) from exc
        return parent / name, name, descriptor, _fingerprint(metadata)
    raise DeepSeekV4HCPreInputBuildError(
        "cannot reserve a collision-free HC_PRE composition report"
    )


def _cleanup_private_directory(
    *,
    parent_descriptor: int,
    name: str,
    descriptor: int,
) -> None:
    held = os.fstat(descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot reopen temporary HC_PRE request for cleanup: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
            held.st_dev,
            held.st_ino,
        ):
            raise DeepSeekV4HCPreInputBuildError(
                "refusing to clean a replaced temporary HC_PRE request"
            )
        visited = 0

        def remove_contents(directory_descriptor: int, depth: int) -> None:
            nonlocal visited
            if depth > _MAX_TREE_DEPTH:
                raise DeepSeekV4HCPreInputBuildError(
                    "temporary HC_PRE request cleanup exceeds its depth bound"
                )
            for child_name in os.listdir(directory_descriptor):
                visited += 1
                if visited > _MAX_CLEANUP_ENTRIES:
                    raise DeepSeekV4HCPreInputBuildError(
                        "temporary HC_PRE request cleanup exceeds its entry bound"
                    )
                metadata = os.stat(
                    child_name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISDIR(metadata.st_mode):
                    child_descriptor = os.open(
                        child_name, flags, dir_fd=directory_descriptor
                    )
                    try:
                        remove_contents(child_descriptor, depth + 1)
                    finally:
                        os.close(child_descriptor)
                    os.rmdir(child_name, dir_fd=directory_descriptor)
                else:
                    os.unlink(child_name, dir_fd=directory_descriptor)

        remove_contents(current_descriptor, 0)
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot clean temporary HC_PRE request: {exc}"
        ) from exc
    finally:
        os.close(current_descriptor)
    os.rmdir(name, dir_fd=parent_descriptor)


def _unlink_if_held(
    *,
    parent_descriptor: int,
    name: str,
    descriptor: int,
    fingerprint: tuple[int, ...],
) -> None:
    try:
        current = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    held = os.fstat(descriptor)
    if (
        not stat.S_ISREG(current.st_mode)
        or not stat.S_ISREG(held.st_mode)
        or (held.st_dev, held.st_ino) != (fingerprint[0], fingerprint[1])
        or (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino)
    ):
        raise DeepSeekV4HCPreInputBuildError(
            "refusing to remove a replaced HC_PRE composition report"
        )
    os.unlink(name, dir_fd=parent_descriptor)


def _publish_create_once(
    *,
    source_parent_descriptor: int,
    source_name: str,
    destination_parent_descriptor: int,
    destination_name: str,
    destination: Path,
) -> None:
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is None:  # pragma: no cover - checked before creating temporary data
        raise DeepSeekV4HCPreInputBuildError(
            "platform lacks atomic rename-without-replacement support"
        )
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        source_parent_descriptor,
        os.fsencode(source_name),
        destination_parent_descriptor,
        os.fsencode(destination_name),
        1,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise DeepSeekV4HCPreInputBuildError(f"output already exists: {destination}")
    raise DeepSeekV4HCPreInputBuildError(
        f"cannot publish HC_PRE input atomically: {os.strerror(error)}"
    )


def build_deepseek_v4_hc_pre_input_request(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    lookup_deployment_root: Path,
    lookup_request_path: Path,
    lookup_result_path: Path,
    lookup_differential_path: Path,
    executable_deployment_root: Path,
    executable_application_root: Path,
    source_texts: Sequence[str],
    output: Path,
    report_output: Path,
) -> dict[str, Any]:
    """Derive, independently recheck, and create-once publish one HC_PRE request."""

    _require_secure_file_operations()
    if type(source_texts) not in {list, tuple}:
        raise DeepSeekV4HCPreInputBuildError(
            "source_texts must be an exact list or tuple, not a scalar string"
        )
    frozen_source_texts = tuple(source_texts)
    output = _specific_path(output, "HC_PRE request output")
    report_output = _specific_path(report_output, "HC_PRE composition report output")
    try:
        report_output.relative_to(output)
    except ValueError:
        pass
    else:
        raise DeepSeekV4HCPreInputBuildError(
            "composition report must be outside the closed request root"
        )
    if os.path.lexists(output):
        raise DeepSeekV4HCPreInputBuildError(f"output already exists: {output}")
    if os.path.lexists(report_output):
        raise DeepSeekV4HCPreInputBuildError(
            f"report output already exists: {report_output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < _MINIMUM_FREE_BYTES:
        raise DeepSeekV4HCPreInputBuildError(
            "HC_PRE request output lacks its bounded free-space reserve"
        )
    if shutil.disk_usage(report_output.parent).free < _MINIMUM_FREE_BYTES:
        raise DeepSeekV4HCPreInputBuildError(
            "HC_PRE report output lacks its bounded free-space reserve"
        )
    try:
        material = _derive_material(
            snapshot=snapshot,
            lock=lock,
            lookup_deployment_root=lookup_deployment_root,
            lookup_request_path=lookup_request_path,
            lookup_result_path=lookup_result_path,
            lookup_differential_path=lookup_differential_path,
            executable_deployment_root=executable_deployment_root,
            executable_application_root=executable_application_root,
            source_texts=frozen_source_texts,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot derive a verified HC_PRE input request: {exc}"
        ) from exc

    with ExitStack() as stack:
        output_parent_descriptor = _open_root(
            stack, output.parent, "HC_PRE request output parent"
        )
        report_parent_descriptor = _open_root(
            stack, report_output.parent, "HC_PRE report output parent"
        )
        _verify_root_binding(
            output.parent, output_parent_descriptor, "HC_PRE request output parent"
        )
        _verify_root_binding(
            report_output.parent,
            report_parent_descriptor,
            "HC_PRE report output parent",
        )
        temporary, temporary_name, temporary_descriptor = _create_private_directory(
            stack,
            parent=output.parent,
            parent_descriptor=output_parent_descriptor,
        )
        report_published = False
        request_published = False
        report_temporary_name = ""
        report_descriptor = -1
        report_fingerprint: tuple[int, ...] = ()
        try:
            os.mkdir("input", 0o700, dir_fd=temporary_descriptor)
            _write_exclusive_bytes(
                temporary_descriptor, INPUT_RELATIVE, material.input_payload
            )
            _write_exclusive_bytes(
                temporary_descriptor,
                REQUEST_MANIFEST,
                canonical_json_bytes(material.request_manifest),
            )
            (
                temporary_report,
                report_temporary_name,
                report_descriptor,
                report_fingerprint,
            ) = _create_private_report(
                stack,
                parent=report_output.parent,
                parent_descriptor=report_parent_descriptor,
                payload=canonical_json_bytes(material.report),
            )
            try:
                integrity = verify_deepseek_v4_hc_pre_input_composition(
                    snapshot=snapshot,
                    lock=lock,
                    lookup_deployment_root=lookup_deployment_root,
                    lookup_request_path=lookup_request_path,
                    lookup_result_path=lookup_result_path,
                    lookup_differential_path=lookup_differential_path,
                    executable_deployment_root=executable_deployment_root,
                    executable_application_root=executable_application_root,
                    source_texts=frozen_source_texts,
                    request_root=temporary,
                    report_path=temporary_report,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                raise DeepSeekV4HCPreInputBuildError(
                    f"independent HC_PRE input verification failed: {exc}"
                ) from exc
            if integrity.get("composition_id") != material.report["composition_id"]:
                raise DeepSeekV4HCPreInputBuildError(
                    "composer and independent checker composition identities differ"
                )
            _verify_root_binding(
                temporary, temporary_descriptor, "temporary HC_PRE request"
            )
            _verify_root_binding(
                output.parent,
                output_parent_descriptor,
                "HC_PRE request output parent",
            )
            _verify_root_binding(
                report_output.parent,
                report_parent_descriptor,
                "HC_PRE report output parent",
            )
            _publish_create_once(
                source_parent_descriptor=report_parent_descriptor,
                source_name=report_temporary_name,
                destination_parent_descriptor=report_parent_descriptor,
                destination_name=report_output.name,
                destination=report_output,
            )
            report_published = True
            _publish_create_once(
                source_parent_descriptor=output_parent_descriptor,
                source_name=temporary_name,
                destination_parent_descriptor=output_parent_descriptor,
                destination_name=output.name,
                destination=output,
            )
            request_published = True
            _verify_root_binding(
                output, temporary_descriptor, "published HC_PRE request"
            )
            held_report = os.fstat(report_descriptor)
            current_report = os.stat(
                report_output.name,
                dir_fd=report_parent_descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(current_report.st_mode) or (
                held_report.st_dev,
                held_report.st_ino,
            ) != (current_report.st_dev, current_report.st_ino):
                raise DeepSeekV4HCPreInputBuildError(
                    "published HC_PRE composition report was replaced"
                )
            return material.report
        except Exception:
            if report_published and not request_published:
                _unlink_if_held(
                    parent_descriptor=report_parent_descriptor,
                    name=report_output.name,
                    descriptor=report_descriptor,
                    fingerprint=report_fingerprint,
                )
            elif not report_published and report_temporary_name:
                _unlink_if_held(
                    parent_descriptor=report_parent_descriptor,
                    name=report_temporary_name,
                    descriptor=report_descriptor,
                    fingerprint=report_fingerprint,
                )
            if not request_published:
                _cleanup_private_directory(
                    parent_descriptor=output_parent_descriptor,
                    name=temporary_name,
                    descriptor=temporary_descriptor,
                )
            raise


__all__ = [
    "DeepSeekV4HCPreInputBuildError",
    "build_deepseek_v4_hc_pre_input_request",
]
