"""Independent payload roundtrip for a DeepSeek V4 FP8 linear deployment."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

from compiler.checking.deepseek_v4_application import MANIFEST_FILENAME
from compiler.ir.model import canonical_json_bytes, load_strict_json


ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_fp8_linear_roundtrip.v1"
SELECTED_SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_slice.v1"
SELECTED_TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_tensors.v1"
FULL_SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full.v1"
FULL_TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_tensors.v1"


class DeepSeekV4FP8LinearCheckError(RuntimeError):
    """Raised when an FP8 linear deployment does not invert to its source."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearCheckError(
            f"cannot hash FP8 linear artifact {path.name!r}: {exc}"
        ) from exc
    return digest.hexdigest(), size


def _safe_file(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4FP8LinearCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4FP8LinearCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4FP8LinearCheckError(f"{label} is not canonical POSIX")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4FP8LinearCheckError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4FP8LinearCheckError(f"{label} escapes its root") from exc
    if not current.is_file():
        raise DeepSeekV4FP8LinearCheckError(f"{label} is not a regular file")
    return current


def _source_assignment(
    application: Mapping[str, Any], name: str, rank: int
) -> Mapping[str, Any]:
    assignments = application.get("assignments")
    if not isinstance(assignments, list):
        raise DeepSeekV4FP8LinearCheckError("canonical assignments are absent")
    matches = [
        record
        for record in assignments
        if isinstance(record, Mapping)
        and record.get("name") == name
        and record.get("rank") == rank
    ]
    if len(matches) != 1:
        raise DeepSeekV4FP8LinearCheckError(
            f"canonical source has {len(matches)} assignments for rank {rank} {name!r}"
        )
    return matches[0]


def verify_deepseek_v4_fp8_linear_roundtrip(
    deployment_root: Path, application_root: Path
) -> dict[str, Any]:
    """Match emitted weight/scale bytes to canonical rank-zero assignments."""

    deployment_root = Path(deployment_root)
    application_root = Path(application_root)
    try:
        tensors = load_strict_json(deployment_root / "tensor_manifest.json")
        semantic = load_strict_json(deployment_root / "model.ir.json")
        application = load_strict_json(application_root / MANIFEST_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4FP8LinearCheckError(
            f"cannot load FP8 linear roundtrip inputs: {exc}"
        ) from exc
    schema_pair = (semantic.get("schema"), tensors.get("schema"))
    if schema_pair not in {
        (SELECTED_SEMANTIC_SCHEMA, SELECTED_TENSOR_SCHEMA),
        (FULL_SEMANTIC_SCHEMA, FULL_TENSOR_SCHEMA),
    }:
        raise DeepSeekV4FP8LinearCheckError(
            "FP8 linear semantic/tensor schema profile differs"
        )
    if semantic.get("source", {}).get("application_id") != application.get(
        "application_id"
    ):
        raise DeepSeekV4FP8LinearCheckError("FP8 linear application identity differs")
    assignments = application.get("assignments")
    if not isinstance(assignments, list) or any(
        not isinstance(record, Mapping) for record in assignments
    ):
        raise DeepSeekV4FP8LinearCheckError(
            "canonical assignments are malformed"
        )
    if {record.get("name") for record in assignments} != {
        "layers.0.attn.wq_a.scale",
        "layers.0.attn.wq_a.weight",
    }:
        raise DeepSeekV4FP8LinearCheckError(
            "FP8 linear application contains tensors outside query-A weight and scale"
        )
    checked = []
    for resource, tensor_name in (
        ("weight", "layers.0.attn.wq_a.weight"),
        ("scale", "layers.0.attn.wq_a.scale"),
    ):
        record = tensors.get(resource)
        if not isinstance(record, Mapping):
            raise DeepSeekV4FP8LinearCheckError(
                f"FP8 linear {resource} resource is absent"
            )
        source = _source_assignment(application, tensor_name, 0)
        replicas = sorted(
            (
                assignment
                for assignment in assignments
                if assignment.get("name") == tensor_name
            ),
            key=lambda assignment: assignment.get("rank", -1),
        )
        if not replicas or [record.get("rank") for record in replicas] != list(
            range(len(replicas))
        ):
            raise DeepSeekV4FP8LinearCheckError(
                f"canonical {tensor_name!r} replicas do not cover contiguous ranks"
            )
        replica_identity = {
            key: source.get(key)
            for key in (
                "logical_dtype",
                "payload_bytes",
                "sha256",
                "shape",
                "storage_dtype",
                "transform",
            )
        }
        for replica in replicas:
            if (
                {key: replica.get(key) for key in replica_identity}
                != replica_identity
                or replica.get("source") != source.get("source")
                or replica.get("scale_source") is not None
            ):
                raise DeepSeekV4FP8LinearCheckError(
                    f"canonical {tensor_name!r} replicas are not byte-identical identities"
                )
        if record.get("source_assignment_path") != source.get("path"):
            raise DeepSeekV4FP8LinearCheckError(
                f"FP8 linear {resource} source path differs"
            )
        path = _safe_file(
            deployment_root, record.get("path"), f"FP8 linear {resource}.path"
        )
        digest, size = _sha256_file(path)
        if (
            digest != record.get("sha256")
            or size != record.get("size_bytes")
            or digest != source.get("sha256")
            or size != source.get("payload_bytes")
        ):
            raise DeepSeekV4FP8LinearCheckError(
                f"FP8 linear {resource} differs from its canonical source"
            )
        checked.append(
            {
                "deployment_path": record["path"],
                "sha256": digest,
                "size_bytes": size,
                "source_assignment_path": source["path"],
                "tensor_name": tensor_name,
            }
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
    "DeepSeekV4FP8LinearCheckError",
    "ROUNDTRIP_SCHEMA",
    "verify_deepseek_v4_fp8_linear_roundtrip",
]
