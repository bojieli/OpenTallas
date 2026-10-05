"""Independent inverse checker for bounded DeepSeek V4 Markov deployments.

The checker does not import the deployment builder, assembler, or service
engine.  It reconstructs selected rows from the verified canonical application,
rehashes every complete source assignment that contributes, compares every
emitted byte, and invokes the separately implemented Markov wire checker.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any

from compiler.checking.deepseek_v4_application import MANIFEST_FILENAME
from compiler.checking.deepseek_v4_markov import (
    DeepSeekV4MarkovCheckError,
    verify_deepseek_v4_markov_program,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json


MODEL_ID = "deepseek-v4-flash-0731"
RESOURCE_SCHEMA = "opentallas.deepseek_v4_markov_resources.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_markov_executable_slice.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_markov_executable_roundtrip.v1"
W1_NAME = "mtp.2.markov_head.markov_w1.weight"
W2_NAME = "mtp.2.markov_head.markov_w2.weight"
_PROGRAM_SHA256 = (
    "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
)
_SHA256 = frozenset("0123456789abcdef")


class DeepSeekV4MarkovExecutableCheckError(RuntimeError):
    """Raised when selected Markov artifacts do not invert to their sources."""


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"cannot load {label}: {exc}"
        ) from exc


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _integer(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        type(value) is not int
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">={minimum}"
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} must be an exact integer in {bound}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _SHA256 for character in value)
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _safe_file(root: Path, value: object, label: str) -> Path:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4MarkovExecutableCheckError(
                f"{label} traverses a symlink"
            )
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} escapes its root"
        ) from exc
    if not current.is_file():
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} is not a regular file"
        )
    return current


def _read_and_hash(path: Path, label: str) -> tuple[bytes, str]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"cannot read {label}: {exc}"
        ) from exc
    return payload, hashlib.sha256(payload).hexdigest()


def _selected_ids(value: object, label: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DeepSeekV4MarkovExecutableCheckError(f"{label} must be an array")
    result = tuple(
        _integer(item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    if not result or any(left >= right for left, right in zip(result, result[1:])):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"{label} must be nonempty and strictly increasing"
        )
    return result


def _assignment_table(
    application: Mapping[str, Any],
) -> dict[tuple[str, int], Mapping[str, Any]]:
    raw = application.get("assignments")
    if not isinstance(raw, list):
        raise DeepSeekV4MarkovExecutableCheckError(
            "canonical application assignments are absent"
        )
    result: dict[tuple[str, int], Mapping[str, Any]] = {}
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4MarkovExecutableCheckError(
                f"canonical assignment {index} is not an object"
            )
        name = record.get("name")
        rank = record.get("rank")
        if type(name) is not str or type(rank) is not int or rank < 0:
            raise DeepSeekV4MarkovExecutableCheckError(
                f"canonical assignment {index} has invalid identity"
            )
        key = (name, rank)
        if key in result:
            raise DeepSeekV4MarkovExecutableCheckError(
                f"canonical assignment {index} duplicates {key!r}"
            )
        result[key] = record
    return result


def _source_descriptor(
    record: Mapping[str, Any],
    *,
    tensor_name: str,
    rank: int,
    markov_rank: int,
) -> tuple[int, int, int, str, str]:
    source = record.get("source")
    descriptor = source.get("slice") if isinstance(source, Mapping) else None
    shape = record.get("shape")
    if (
        record.get("name") != tensor_name
        or record.get("rank") != rank
        or record.get("transform") != "identity"
        or record.get("storage_dtype") != "BF16"
        or record.get("logical_dtype") != "BF16"
        or not isinstance(source, Mapping)
        or source.get("name") != tensor_name
        or source.get("storage_dtype") != "BF16"
        or not isinstance(source.get("shape"), list)
        or source["shape"][-1:] != [markov_rank]
        or not isinstance(descriptor, Mapping)
        or set(descriptor) != {"axis", "start", "stop"}
        or descriptor.get("axis") != 0
        or type(descriptor.get("start")) is not int
        or type(descriptor.get("stop")) is not int
        or descriptor["start"] < 0
        or descriptor["stop"] <= descriptor["start"]
        or shape != [descriptor["stop"] - descriptor["start"], markov_rank]
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"canonical {tensor_name} rank {rank} metadata differs"
        )
    row_bytes = markov_rank * 2
    expected_size = (descriptor["stop"] - descriptor["start"]) * row_bytes
    if record.get("payload_bytes") != expected_size:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"canonical {tensor_name} rank {rank} byte extent differs"
        )
    return (
        descriptor["start"],
        descriptor["stop"],
        expected_size,
        _digest(record.get("sha256"), f"canonical {tensor_name} rank {rank} SHA"),
        str(record.get("path")),
    )


def _verify_selected_payload(
    *,
    deployment_root: Path,
    application_root: Path,
    application_record: Mapping[str, Any],
    deployed_record: Mapping[str, Any],
    tensor_name: str,
    rank: int,
    global_ids: tuple[int, ...],
    markov_rank: int,
) -> dict[str, Any]:
    _exact_keys(
        deployed_record,
        {
            "path",
            "sha256",
            "size_bytes",
            "source_assignment_path",
            "source_assignment_sha256",
            "source_assignment_size_bytes",
        },
        f"deployed {tensor_name} rank {rank}",
    )
    start, stop, source_size, source_sha, source_relative = _source_descriptor(
        application_record,
        tensor_name=tensor_name,
        rank=rank,
        markov_rank=markov_rank,
    )
    if any(token < start or token >= stop for token in global_ids):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"selected {tensor_name} rank {rank} IDs escape source interval"
        )
    if (
        deployed_record["source_assignment_path"] != source_relative
        or deployed_record["source_assignment_sha256"] != source_sha
        or deployed_record["source_assignment_size_bytes"] != source_size
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"deployed {tensor_name} rank {rank} source authority differs"
        )
    source_path = _safe_file(
        application_root,
        source_relative,
        f"canonical {tensor_name} rank {rank} path",
    )
    source_payload, observed_source_sha = _read_and_hash(
        source_path, f"canonical {tensor_name} rank {rank}"
    )
    if len(source_payload) != source_size or observed_source_sha != source_sha:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"canonical {tensor_name} rank {rank} changed during inverse checking"
        )
    row_bytes = markov_rank * 2
    expected = b"".join(
        source_payload[(token - start) * row_bytes : (token - start + 1) * row_bytes]
        for token in global_ids
    )
    deployed_path = _safe_file(
        deployment_root,
        deployed_record["path"],
        f"deployed {tensor_name} rank {rank} path",
    )
    deployed_payload, observed_deployed_sha = _read_and_hash(
        deployed_path, f"deployed {tensor_name} rank {rank}"
    )
    declared_deployed_sha = _digest(
        deployed_record["sha256"], f"deployed {tensor_name} rank {rank} SHA"
    )
    expected_deployed_size = len(global_ids) * row_bytes
    if (
        deployed_record["size_bytes"] != expected_deployed_size
        or len(deployed_payload) != expected_deployed_size
        or observed_deployed_sha != declared_deployed_sha
        or deployed_payload != expected
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            f"deployed {tensor_name} rank {rank} differs from selected canonical rows"
        )
    return {
        "deployment_path": deployed_record["path"],
        "global_token_ids": list(global_ids),
        "rank": rank,
        "selected_payload_sha256": observed_deployed_sha,
        "selected_payload_size_bytes": len(deployed_payload),
        "source_assignment_path": source_relative,
        "source_assignment_sha256": observed_source_sha,
        "source_assignment_size_bytes": len(source_payload),
        "tensor_name": tensor_name,
    }


def verify_deepseek_v4_markov_executable_roundtrip(
    deployment_root: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Reconstruct every bounded deployment row from canonical assignments."""

    deployment_root = Path(deployment_root).resolve()
    application_root = Path(application_root).resolve()
    resources = _load(deployment_root / "resource_manifest.json", "resource manifest")
    semantic = _load(deployment_root / "model.ir.json", "semantic IR")
    contract = _load(deployment_root / "program_contract.json", "program contract")
    application = _load(
        application_root / MANIFEST_FILENAME, "canonical application manifest"
    )
    _exact_keys(
        resources,
        {
            "application_id",
            "full_vocabulary_size",
            "markov_rank",
            "model_parallel",
            "ranks",
            "schema",
            "selected_global_token_ids",
            "selected_vocabulary_size",
            "source_tensor_payload_sha256",
        },
        "resource manifest",
    )
    if resources["schema"] != RESOURCE_SCHEMA:
        raise DeepSeekV4MarkovExecutableCheckError("resource schema differs")
    if semantic.get("schema") != SEMANTIC_SCHEMA or semantic.get("model_id") != MODEL_ID:
        raise DeepSeekV4MarkovExecutableCheckError("semantic identity differs")
    application_id = _digest(application.get("application_id"), "application ID")
    if (
        resources["application_id"] != application_id
        or semantic.get("source", {}).get("application_id") != application_id
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            "deployment canonical application identity differs"
        )
    selected = _selected_ids(
        resources["selected_global_token_ids"], "selected_global_token_ids"
    )
    selected_size = _integer(
        resources["selected_vocabulary_size"],
        "selected_vocabulary_size",
        minimum=1,
    )
    full_vocabulary = _integer(
        resources["full_vocabulary_size"], "full_vocabulary_size", minimum=1
    )
    markov_rank = _integer(resources["markov_rank"], "markov_rank", minimum=1)
    model_parallel = _integer(
        resources["model_parallel"], "model_parallel", minimum=1
    )
    if (
        len(selected) != selected_size
        or selected[-1] >= full_vocabulary
        or semantic.get("dimensions")
        != {
            "block_size": 5,
            "full_vocabulary_size": full_vocabulary,
            "markov_rank": markov_rank,
            "model_parallel": model_parallel,
            "selected_rows_per_rank": selected_size // model_parallel,
            "selected_vocabulary_size": selected_size,
        }
    ):
        raise DeepSeekV4MarkovExecutableCheckError(
            "deployment dimensions or selected vocabulary differ"
        )
    if selected_size % model_parallel:
        raise DeepSeekV4MarkovExecutableCheckError(
            "selected vocabulary is not balanced across ranks"
        )
    source_hashes = resources["source_tensor_payload_sha256"]
    if not isinstance(source_hashes, Mapping) or set(source_hashes) != {W1_NAME, W2_NAME}:
        raise DeepSeekV4MarkovExecutableCheckError(
            "source tensor payload authority differs"
        )
    for name, value in source_hashes.items():
        _digest(value, f"source tensor {name} SHA")
    ranks = resources["ranks"]
    if not isinstance(ranks, list) or len(ranks) != model_parallel:
        raise DeepSeekV4MarkovExecutableCheckError("resource rank table differs")
    assignments = _assignment_table(application)
    reconstructed: list[dict[str, Any]] = []
    observed_global_ids: list[int] = []
    expected_rows_per_rank = selected_size // model_parallel
    for expected_rank, raw_rank in enumerate(ranks):
        if not isinstance(raw_rank, Mapping):
            raise DeepSeekV4MarkovExecutableCheckError(
                f"resource rank {expected_rank} is not an object"
            )
        _exact_keys(
            raw_rank,
            {"global_token_ids", "rank", "row_start", "row_stop", "w1", "w2"},
            f"resource rank {expected_rank}",
        )
        if raw_rank["rank"] != expected_rank:
            raise DeepSeekV4MarkovExecutableCheckError("resource ranks are not contiguous")
        rank_ids = _selected_ids(
            raw_rank["global_token_ids"], f"resource rank {expected_rank} IDs"
        )
        if len(rank_ids) != expected_rows_per_rank:
            raise DeepSeekV4MarkovExecutableCheckError(
                f"resource rank {expected_rank} selected-row count differs"
            )
        row_start = _integer(raw_rank["row_start"], "rank row_start")
        row_stop = _integer(raw_rank["row_stop"], "rank row_stop", minimum=1)
        if row_start >= row_stop or any(
            token < row_start or token >= row_stop for token in rank_ids
        ):
            raise DeepSeekV4MarkovExecutableCheckError(
                f"resource rank {expected_rank} selected interval differs"
            )
        observed_global_ids.extend(rank_ids)
        for key, tensor_name in (("w1", W1_NAME), ("w2", W2_NAME)):
            deployed = raw_rank[key]
            if not isinstance(deployed, Mapping):
                raise DeepSeekV4MarkovExecutableCheckError(
                    f"resource rank {expected_rank} {key} is not an object"
                )
            source = assignments.get((tensor_name, expected_rank))
            if source is None:
                raise DeepSeekV4MarkovExecutableCheckError(
                    f"canonical {tensor_name} rank {expected_rank} is absent"
                )
            source_meta = source.get("source")
            if (
                not isinstance(source_meta, Mapping)
                or source_meta.get("payload_sha256") != source_hashes[tensor_name]
            ):
                raise DeepSeekV4MarkovExecutableCheckError(
                    f"canonical {tensor_name} full payload authority differs"
                )
            reconstructed.append(
                _verify_selected_payload(
                    deployment_root=deployment_root,
                    application_root=application_root,
                    application_record=source,
                    deployed_record=deployed,
                    tensor_name=tensor_name,
                    rank=expected_rank,
                    global_ids=rank_ids,
                    markov_rank=markov_rank,
                )
            )
    if tuple(observed_global_ids) != selected:
        raise DeepSeekV4MarkovExecutableCheckError(
            "rank-local selected IDs do not reconstruct the global mapping"
        )
    program_path = _safe_file(deployment_root, "microcode.bin", "microcode path")
    program, program_sha = _read_and_hash(program_path, "microcode")
    if program_sha != _PROGRAM_SHA256:
        raise DeepSeekV4MarkovExecutableCheckError("microcode identity differs")
    try:
        report = verify_deepseek_v4_markov_program(program, contract)
    except DeepSeekV4MarkovCheckError as exc:
        raise DeepSeekV4MarkovExecutableCheckError(
            f"microcode or program contract differs: {exc}"
        ) from exc
    body: dict[str, Any] = {
        "application_id": application_id,
        "checked_deployment_payload_bytes": sum(
            record["selected_payload_size_bytes"] for record in reconstructed
        ),
        "checked_deployment_payload_count": len(reconstructed),
        "checked_source_assignment_bytes": sum(
            record["source_assignment_size_bytes"] for record in reconstructed
        ),
        "checked_source_assignment_count": len(reconstructed),
        "model_id": MODEL_ID,
        "program_sha256": report.program_sha256,
        "reconstructed": reconstructed,
        "schema": ROUNDTRIP_SCHEMA,
        "selected_global_token_ids": list(selected),
        "status": "all_selected_rows_match_verified_canonical_assignments",
    }
    body["roundtrip_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


__all__ = [
    "DeepSeekV4MarkovExecutableCheckError",
    "ROUNDTRIP_SCHEMA",
    "verify_deepseek_v4_markov_executable_roundtrip",
]
