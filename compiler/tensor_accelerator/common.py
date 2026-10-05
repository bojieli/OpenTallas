"""Strict, deterministic artifact helpers for tensor-accelerator releases."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, NoReturn


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ArtifactError(ValueError):
    """Raised when a canonical tensor-accelerator artifact is malformed."""


def _raise_nonfinite(token: str) -> NoReturn:
    raise ArtifactError(f"non-finite JSON number {token!r}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> dict[str, Any]:
    """Load one JSON object, rejecting duplicate keys and non-finite values."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_raise_nonfinite,
        )
    except ArtifactError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"expected a JSON object in {path}")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic ASCII JSON with no host or wall-clock state."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactError(f"value is not canonical JSON: {exc}") from exc
    return (encoded + "\n").encode("ascii")


def write_canonical_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def publish_bytes_atomic_no_replace(path: Path, payload: bytes) -> None:
    """Durably publish bytes without exposing or replacing a partial artifact."""

    destination = Path(path)
    if not isinstance(payload, bytes):
        raise TypeError("atomic publication payload must be bytes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.tmp-", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination, follow_symlinks=False)
        _fsync_directory(destination.parent)
        temporary.unlink()
        _fsync_directory(destination.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        else:
            _fsync_directory(destination.parent)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, *, chunk_bytes: int = 8 * 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def exact_keys(
    value: dict[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if not missing and not unknown:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing {missing}")
    if unknown:
        details.append(f"unknown {unknown}")
    raise ArtifactError(f"{label} has " + "; ".join(details))


def require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ArtifactError(f"{label} must be a stable identifier")
    return value


def require_int(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ArtifactError(f"{label} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ArtifactError(f"{label} must be <= {maximum}")
    return value


def require_power_of_two(
    value: Any,
    label: str,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    parsed = require_int(value, label, minimum=minimum, maximum=maximum)
    if parsed & (parsed - 1):
        raise ArtifactError(f"{label} must be a power of two")
    return parsed


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ArtifactError(f"{label} must be a lowercase SHA-256")
    return value


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & -alignment
