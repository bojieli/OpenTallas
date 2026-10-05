"""Independent inverse checker for the DeepSeek V4 lookup-slice deployment."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

from compiler.checking.deepseek_v4_application import MANIFEST_FILENAME
from compiler.ir.model import canonical_json_bytes, load_strict_json


ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_lookup_roundtrip.v1"


class DeepSeekV4LookupCheckError(RuntimeError):
    """Raised when a lookup deployment does not invert to its application."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise DeepSeekV4LookupCheckError(
            f"cannot hash lookup artifact {path.name!r}: {exc}"
        ) from exc
    return digest.hexdigest(), size


def _safe_file(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4LookupCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4LookupCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4LookupCheckError(f"{label} is not canonical POSIX")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4LookupCheckError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4LookupCheckError(f"{label} escapes its root") from exc
    if not current.is_file():
        raise DeepSeekV4LookupCheckError(f"{label} is not a regular file")
    return current


def _assignments_by_key(
    application: Mapping[str, Any],
) -> dict[tuple[int, str], Mapping[str, Any]]:
    raw = application.get("assignments")
    if not isinstance(raw, list):
        raise DeepSeekV4LookupCheckError("application assignments are absent")
    result: dict[tuple[int, str], Mapping[str, Any]] = {}
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4LookupCheckError(
                f"application assignment {index} is not an object"
            )
        key = (record.get("rank"), record.get("name"))
        if (
            isinstance(key[0], bool)
            or not isinstance(key[0], int)
            or not isinstance(key[1], str)
            or key in result
        ):
            raise DeepSeekV4LookupCheckError(
                f"application assignment {index} has an invalid identity"
            )
        result[key] = record
    return result


def _check_copy(
    deployment_root: Path,
    record: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    path = _safe_file(deployment_root, record.get("path"), f"{label}.path")
    digest, size = _sha256_file(path)
    if digest != record.get("sha256") or size != record.get("size_bytes"):
        raise DeepSeekV4LookupCheckError(
            f"{label} differs from its deployment manifest"
        )
    if digest != source.get("sha256") or size != source.get("payload_bytes"):
        raise DeepSeekV4LookupCheckError(
            f"{label} differs from its canonical source assignment"
        )
    return {
        "deployment_path": record["path"],
        "rank": record.get("rank"),
        "sha256": digest,
        "size_bytes": size,
        "source_assignment_path": source.get("path"),
        "tensor_name": source.get("name"),
    }


def verify_deepseek_v4_lookup_roundtrip(
    deployment_root: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Hash every emitted ROM payload and match its canonical assignment."""

    deployment_root = Path(deployment_root)
    application_root = Path(application_root)
    try:
        semantic = load_strict_json(deployment_root / "model.ir.json")
        tensors = load_strict_json(deployment_root / "tensor_manifest.json")
        application = load_strict_json(application_root / MANIFEST_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4LookupCheckError(
            f"cannot load lookup roundtrip inputs: {exc}"
        ) from exc
    if semantic.get("schema") != "opentallas.deepseek_v4_lookup_slice.v1":
        raise DeepSeekV4LookupCheckError("lookup semantic schema differs")
    if tensors.get("schema") != "opentallas.deepseek_v4_lookup_tensors.v1":
        raise DeepSeekV4LookupCheckError("lookup tensor schema differs")
    if semantic.get("source", {}).get("application_id") != application.get(
        "application_id"
    ):
        raise DeepSeekV4LookupCheckError("lookup application identity differs")
    by_key = _assignments_by_key(application)
    embedding = tensors.get("embedding")
    route = tensors.get("hash_route")
    if not isinstance(embedding, Mapping) or not isinstance(route, Mapping):
        raise DeepSeekV4LookupCheckError("lookup tensor resources are incomplete")
    ranks = embedding.get("ranks")
    if not isinstance(ranks, list) or not ranks:
        raise DeepSeekV4LookupCheckError("embedding rank records are absent")
    checked: list[dict[str, Any]] = []
    for index, record in enumerate(ranks):
        if not isinstance(record, Mapping):
            raise DeepSeekV4LookupCheckError(
                f"embedding rank record {index} is malformed"
            )
        rank = record.get("rank")
        source = by_key.get((rank, "embed.weight"))
        if source is None or record.get("source_assignment_path") != source.get(
            "path"
        ):
            raise DeepSeekV4LookupCheckError(
                f"embedding rank {rank!r} lacks its canonical source"
            )
        checked.append(
            _check_copy(
                deployment_root,
                record,
                source,
                label=f"embedding rank {rank}",
            )
        )
    route_rank = route.get("source_rank")
    route_source = by_key.get((route_rank, "layers.0.ffn.gate.tid2eid"))
    if route_source is None or route.get(
        "source_assignment_path"
    ) != route_source.get("path"):
        raise DeepSeekV4LookupCheckError("hash route lacks its canonical source")
    checked.append(
        _check_copy(
            deployment_root,
            route,
            route_source,
            label="hash route",
        )
    )
    body: dict[str, Any] = {
        "application_id": application["application_id"],
        "checked_artifact_count": len(checked),
        "checked_payload_bytes": sum(record["size_bytes"] for record in checked),
        "model_id": semantic.get("model_id"),
        "reconstructed": checked,
        "schema": ROUNDTRIP_SCHEMA,
        "status": "full_selected_payload_match",
    }
    body["roundtrip_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


__all__ = [
    "DeepSeekV4LookupCheckError",
    "ROUNDTRIP_SCHEMA",
    "verify_deepseek_v4_lookup_roundtrip",
]
