"""Independent causal checker for a DeepSeek V4 ``HC_PRE`` request.

The request accepted by this checker is not an arbitrary activation fixture.  It
must be composed from a lookup result which is reproduced directly from the
locked checkpoint, and official evidence must additionally reproduce the exact
token IDs by running the pinned, locally verified tokenizer on caller-supplied
source text.  The source text itself is never persisted by this layer.

All ordinary evidence and output files are opened descriptor-relative with
``O_NOFOLLOW`` and ``O_NONBLOCK`` and retained until their stability has been
checked.  Hugging Face checkpoint snapshots are the deliberate exception:
their files are content-addressed symlinks, and the existing checkpoint and
tokenizer readers cryptographically verify the resolved bytes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
from typing import Any

from compiler.checking.deepseek_v4_hc_pre_executable import (
    verify_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.checking.deepseek_v4_lookup_execution import (
    verify_deepseek_v4_lookup_execution,
)
from compiler.frontend.checkpoint import validate_checkpoint_lock
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.frontend.deepseek_v4_tokenizer import (
    TOKENIZER_CONFIG_SHA256,
    TOKENIZER_CONFIG_SIZE_BYTES,
    TOKENIZER_SHA256,
    TOKENIZER_SIZE_BYTES,
    load_verified_deepseek_v4_tokenizer,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_lookup import (
    decode as decode_lookup_program,
    disassemble as disassemble_lookup_program,
    verify as verify_lookup_program,
)


COMPOSITION_SCHEMA = "opentallas.deepseek_v4_hc_pre_input_composition.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_request.v1"
LOOKUP_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_lookup_deployment.v1"
LOOKUP_REQUEST_SCHEMA = "opentallas.deepseek_v4_lookup_request.v1"
LOOKUP_RESULT_SCHEMA = "opentallas.deepseek_v4_lookup_result.v1"
LOOKUP_DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_lookup_differential.v1"
EXECUTABLE_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable.v1"
PROGRAM_SHA256 = "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"

REQUEST_MANIFEST = "request_manifest.json"
INPUT_RELATIVE = "input/hc_hidden.bf16le"
CLAIM_BOUNDARY = [
    "Composes one HC_PRE request only from a lookup result reproduced against the same locked checkpoint.",
    "Official evidence requires exact tokenization of caller-supplied source text by the pinned, locally verified DeepSeek V4 tokenizer.",
    "The report stores the source-text UTF-8 hash and length, never the source text itself.",
    "The request contains no expected HC_PRE output and establishes no HC_PRE execution, transformer-block, full-model, timing, PPA, manufacturability, or NVIDIA comparison claim.",
]

_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_SOURCE_TEXT_BYTES = 1024 * 1024
_MAX_LOOKUP_ARTIFACT_BYTES = 2 * 1024 * 1024 * 1024
_MAX_LOOKUP_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
_MAX_TREE_ENTRIES = 128
_MAX_TREE_DEPTH = 8
_MAX_TOKEN_COUNT = 4
_HIDDEN_SIZE = 4096
_HC_MULTIPLIER = 4
_SHA256_LENGTH = 64
_OFFICIAL_TOKENIZER_VALIDATION_ID = (
    "176e504a2a500bfccd88d6ef10b72c1d08853a90ff62d97d173faaa808dd5c23"
)


class DeepSeekV4HCPreInputCheckError(RuntimeError):
    """Raised when an HC_PRE request lacks a complete causal evidence chain."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


@dataclass(frozen=True)
class _StableRoot:
    descriptor: int
    fingerprint: tuple[int, ...]
    path: Path


@dataclass(frozen=True)
class _CompositionMaterial:
    input_payload: bytes
    request_manifest: dict[str, Any]
    report: dict[str, Any]


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _require_secure_file_operations() -> None:
    missing = [
        name
        for name in ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
        if not hasattr(os, name)
    ]
    if missing:
        raise DeepSeekV4HCPreInputCheckError(
            f"secure descriptor operations are unavailable: {', '.join(missing)}"
        )


def _specific_path(value: Path, label: str) -> Path:
    try:
        path = Path(value).absolute()
    except TypeError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} must be a filesystem path"
        ) from exc
    if not path.name or path.name in {".", ".."} or path == Path(path.anchor):
        raise DeepSeekV4HCPreInputCheckError(f"{label} must name a specific path")
    return path


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreInputCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreInputCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreInputCheckError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, path: Path, label: str) -> _StableRoot:
    _require_secure_file_operations()
    path = Path(path).absolute()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreInputCheckError(f"{label} is not a directory")
    return _StableRoot(descriptor, _fingerprint(metadata), path)


def _open_relative_descriptor(
    root_descriptor: int,
    relative: str,
    label: str,
    *,
    directory: bool,
) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    current = os.dup(root_descriptor)
    try:
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = directory_flags if directory or not final else file_flags
            next_descriptor = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = next_descriptor
        return current
    except OSError as exc:
        os.close(current)
        raise DeepSeekV4HCPreInputCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _safe_file(
    stack: ExitStack,
    root_descriptor: int,
    relative: object,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    safe = _safe_relative(relative, label)
    descriptor = _open_relative_descriptor(
        root_descriptor, safe, label, directory=False
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreInputCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor,
        _fingerprint(metadata),
        safe,
        root_descriptor,
        metadata.st_size,
    )


def _direct_file(
    stack: ExitStack,
    path: Path,
    label: str,
    *,
    maximum_size: int,
) -> tuple[_StableRoot, _StableFile]:
    specific = _specific_path(path, label)
    parent = _open_root(stack, specific.parent, f"{label} parent")
    source = _safe_file(
        stack,
        parent.descriptor,
        specific.name,
        label,
        maximum_size=maximum_size,
    )
    return parent, source


def _read_file(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreInputCheckError(f"{label} exceeds its read bound")
    chunks: list[bytes] = []
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(1024 * 1024, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreInputCheckError(f"cannot read {label}: {exc}") from exc
        if not chunk:
            raise DeepSeekV4HCPreInputCheckError(
                f"{label} ended before its stable size"
            )
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _hash_file(source: _StableFile, label: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(8 * 1024 * 1024, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreInputCheckError(f"cannot hash {label}: {exc}") from exc
        if not chunk:
            raise DeepSeekV4HCPreInputCheckError(
                f"{label} ended before its stable size"
            )
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest(), offset


def _verify_file_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreInputCheckError(f"{label} changed during verification")
    current = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
        directory=False,
    )
    try:
        metadata = os.fstat(current)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or _fingerprint(metadata) != source.fingerprint
        ):
            raise DeepSeekV4HCPreInputCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current)


def _verify_root_stable(root: _StableRoot, label: str) -> None:
    if _fingerprint(os.fstat(root.descriptor)) != root.fingerprint:
        raise DeepSeekV4HCPreInputCheckError(f"{label} changed during verification")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(root.path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"cannot re-open {label} without following symlinks: {exc}"
        ) from exc
    try:
        metadata = os.fstat(current)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or _fingerprint(metadata) != root.fingerprint
        ):
            raise DeepSeekV4HCPreInputCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current)


def _verify_root_binding(root: _StableRoot, label: str) -> None:
    held = os.fstat(root.descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root.path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"cannot re-open {label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
            held.st_dev,
            held.st_ino,
        ):
            raise DeepSeekV4HCPreInputCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreInputCheckError(
                    f"{label} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} contains non-finite JSON number {token!r}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4HCPreInputCheckError(f"cannot parse {label}: {exc}") from exc
    if type(value) is not dict:
        raise DeepSeekV4HCPreInputCheckError(f"{label} must be a JSON object")
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} is not canonical JSON: {exc}"
        ) from exc
    if payload != canonical:
        raise DeepSeekV4HCPreInputCheckError(f"{label} bytes are not canonical JSON")
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4HCPreInputCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreInputCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


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
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">= {minimum}"
        raise DeepSeekV4HCPreInputCheckError(f"{label} must be an integer in {bound}")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4HCPreInputCheckError(f"{label} must be a lowercase SHA-256")
    return value


def _sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited = 0

    def walk(descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreInputCheckError(
                "artifact tree exceeds its depth bound"
            )
        try:
            names = sorted(os.listdir(descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreInputCheckError(
                f"cannot enumerate artifact tree: {exc}"
            ) from exc
        for name in names:
            visited += 1
            if visited > _MAX_TREE_ENTRIES:
                raise DeepSeekV4HCPreInputCheckError(
                    "artifact tree exceeds its entry bound"
                )
            if not name or name in {".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreInputCheckError(
                    "artifact tree contains an unsafe name"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except OSError as exc:
                raise DeepSeekV4HCPreInputCheckError(
                    f"cannot inspect artifact tree entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                child = _open_relative_descriptor(
                    descriptor, name, f"artifact directory {relative!r}", directory=True
                )
                try:
                    walk(child, relative, depth + 1)
                finally:
                    os.close(child)
            else:
                raise DeepSeekV4HCPreInputCheckError(
                    f"artifact tree entry {relative!r} is not a regular file or directory"
                )

    walk(root_descriptor, "", 0)
    return files, directories


def _expected_directories(paths: set[str]) -> set[str]:
    result: set[str] = set()
    for relative in paths:
        parts = Path(relative).parts
        for count in range(1, len(parts)):
            result.add(Path(*parts[:count]).as_posix())
    return result


def _verify_lookup_auxiliary_contracts(
    *,
    by_role: Mapping[str, _StableFile],
    dimensions: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    tensor_manifest = _strict_json(
        _read_file(
            by_role["tensor_manifest"], "lookup tensor manifest", _MAX_JSON_BYTES
        ),
        "lookup tensor manifest",
    )
    _exact_keys(
        tensor_manifest,
        {"embedding", "hash_route", "schema"},
        "lookup tensor manifest",
    )
    if tensor_manifest["schema"] != "opentallas.deepseek_v4_lookup_tensors.v1":
        raise DeepSeekV4HCPreInputCheckError("lookup tensor manifest schema differs")
    embedding = _exact_keys(
        tensor_manifest["embedding"],
        {"dtype", "hidden_size", "ranks", "vocabulary_size"},
        "lookup embedding manifest",
    )
    if (
        embedding["dtype"] != "BF16"
        or embedding["hidden_size"] != dimensions["hidden_size"]
        or embedding["vocabulary_size"] != dimensions["vocabulary_size"]
        or type(embedding["ranks"]) is not list
        or len(embedding["ranks"]) != dimensions["model_parallel"]
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup embedding manifest differs")
    expected_start = 0
    expected_roundtrip: list[dict[str, Any]] = []
    payload_bytes = 0
    for rank, raw in enumerate(embedding["ranks"]):
        record = _exact_keys(
            raw,
            {
                "path",
                "rank",
                "row_start",
                "row_stop",
                "sha256",
                "size_bytes",
                "source_assignment_path",
            },
            f"lookup embedding rank {rank}",
        )
        stop = _integer(
            record["row_stop"], f"lookup embedding rank {rank}.row_stop", minimum=1
        )
        size = (stop - expected_start) * dimensions["hidden_size"] * 2
        role = f"embedding_rank_{rank:03d}"
        artifact = by_role[role]
        digest, artifact_size = _hash_file(artifact, f"lookup {role}")
        source_assignment = _safe_relative(
            record["source_assignment_path"],
            f"lookup embedding rank {rank}.source_assignment_path",
        )
        expected_path = f"rom/embed/rank-{rank:03d}.bin"
        expected_source_assignment = f"ranks/rank-{rank:03d}/embed.weight.bin"
        if (
            not _canonical_equal(
                record,
                {
                    "path": expected_path,
                    "rank": rank,
                    "row_start": expected_start,
                    "row_stop": stop,
                    "sha256": digest,
                    "size_bytes": size,
                    "source_assignment_path": expected_source_assignment,
                },
            )
            or artifact_size != size
            or source_assignment != expected_source_assignment
        ):
            raise DeepSeekV4HCPreInputCheckError(
                f"lookup embedding rank {rank} metadata differs"
            )
        expected_roundtrip.append(
            {
                "deployment_path": expected_path,
                "rank": rank,
                "sha256": digest,
                "size_bytes": size,
                "source_assignment_path": expected_source_assignment,
                "tensor_name": "embed.weight",
            }
        )
        expected_start = stop
        payload_bytes += size
    if expected_start != dimensions["vocabulary_size"]:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup embedding ranks do not cover the vocabulary"
        )

    route = _exact_keys(
        tensor_manifest["hash_route"],
        {
            "dtype",
            "expert_count",
            "path",
            "route_top_k",
            "sha256",
            "size_bytes",
            "source_assignment_path",
            "source_rank",
            "verified_replica_ranks",
            "vocabulary_size",
        },
        "lookup hash-route manifest",
    )
    route_artifact = by_role["hash_route_table"]
    route_sha256, route_artifact_bytes = _hash_file(
        route_artifact, "lookup hash-route table"
    )
    route_size = dimensions["vocabulary_size"] * dimensions["route_top_k"] * 8
    source_assignment = _safe_relative(
        route["source_assignment_path"],
        "lookup hash-route source_assignment_path",
    )
    source_rank = _integer(
        route["source_rank"],
        "lookup hash-route source_rank",
        maximum=dimensions["model_parallel"] - 1,
    )
    expected_source_assignment = (
        f"ranks/rank-{source_rank:03d}/layers.0.ffn.gate.tid2eid.bin"
    )
    expected_route = {
        "dtype": "I64",
        "expert_count": dimensions["expert_count"],
        "path": "rom/hash_route.bin",
        "route_top_k": dimensions["route_top_k"],
        "sha256": route_sha256,
        "size_bytes": route_size,
        "source_assignment_path": expected_source_assignment,
        "source_rank": source_rank,
        "verified_replica_ranks": list(range(dimensions["model_parallel"])),
        "vocabulary_size": dimensions["vocabulary_size"],
    }
    if (
        not _canonical_equal(route, expected_route)
        or route_artifact_bytes != route_size
        or source_assignment != expected_source_assignment
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup hash-route metadata differs")
    expected_roundtrip.append(
        {
            "deployment_path": "rom/hash_route.bin",
            "rank": None,
            "sha256": route_sha256,
            "size_bytes": route_size,
            "source_assignment_path": expected_source_assignment,
            "tensor_name": "layers.0.ffn.gate.tid2eid",
        }
    )
    payload_bytes += route_size

    hidden = dimensions["hidden_size"]
    multiplier = dimensions["hc_multiplier"]
    route_top_k = dimensions["route_top_k"]
    expected_expectations = {
        "counter_coefficients_per_token": {
            "bf16_codes_copied": multiplier * hidden,
            "logical_activation_bytes_read": hidden * 2,
            "logical_activation_bytes_written": (
                hidden * 2 + multiplier * hidden * 2 + route_top_k * 8
            ),
            "logical_input_bytes_read": 16,
            "logical_rom_bytes_read": hidden * 2 + route_top_k * 8,
            "rom_lookup_rows": 2,
        },
        "fixed_counters": {
            "completion_events": 1,
            "micro_ops_executed": 4,
            "semantic_operations_executed": 3,
        },
        "hardware_accounting": {
            "cycles": None,
            "hbm_transactions": None,
            "stalls": None,
            "status": "not modeled by the functional lookup slice",
        },
        "schema": "opentallas.deepseek_v4_lookup_expectations.v1",
    }
    expectations = _strict_json(
        _read_file(
            by_role["execution_expectations"],
            "lookup execution expectations",
            _MAX_JSON_BYTES,
        ),
        "lookup execution expectations",
    )
    if not _canonical_equal(expectations, expected_expectations):
        raise DeepSeekV4HCPreInputCheckError("lookup execution expectations differ")
    expected_coverage = {
        "implemented_operator_kinds": ["HASH_ROUTE", "HC_EXPAND", "TOKEN_EMBED"],
        "model_id": MODEL_ID,
        "schema": "opentallas.deepseek_v4_lookup_coverage.v1",
        "status": "three_operator_real_payload_slice_only",
        "unimplemented_graph_operator_kind_count": 40,
    }
    coverage = _strict_json(
        _read_file(
            by_role["operator_coverage"],
            "lookup operator coverage",
            _MAX_JSON_BYTES,
        ),
        "lookup operator coverage",
    )
    if not _canonical_equal(coverage, expected_coverage):
        raise DeepSeekV4HCPreInputCheckError("lookup operator coverage differs")

    roundtrip = _strict_json(
        _read_file(
            by_role["roundtrip_report"],
            "lookup roundtrip report",
            _MAX_JSON_BYTES,
        ),
        "lookup roundtrip report",
    )
    expected_roundtrip_body = {
        "application_id": manifest["source_application_id"],
        "checked_artifact_count": len(expected_roundtrip),
        "checked_payload_bytes": payload_bytes,
        "model_id": MODEL_ID,
        "reconstructed": expected_roundtrip,
        "schema": "opentallas.deepseek_v4_lookup_roundtrip.v1",
        "status": "full_selected_payload_match",
    }
    expected_roundtrip_report = {
        **expected_roundtrip_body,
        "roundtrip_id": _sha256_json(expected_roundtrip_body),
    }
    if not _canonical_equal(roundtrip, expected_roundtrip_report):
        raise DeepSeekV4HCPreInputCheckError("lookup roundtrip report differs")


def _canonical_equal(left: object, right: object) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _inspect_lookup_deployment(
    stack: ExitStack,
    root: Path,
    lock: Mapping[str, Any],
) -> tuple[
    dict[str, Any], bytes, dict[str, Any], bytes, _StableRoot, list[_StableFile]
]:
    deployment_root = _open_root(stack, root, "lookup deployment root")
    manifest_file = _safe_file(
        stack,
        deployment_root.descriptor,
        "deployment_manifest.json",
        "lookup deployment manifest",
        maximum_size=_MAX_MANIFEST_BYTES,
    )
    manifest_bytes = _read_file(
        manifest_file, "lookup deployment manifest", _MAX_MANIFEST_BYTES
    )
    manifest = _strict_json(manifest_bytes, "lookup deployment manifest")
    _exact_keys(
        manifest,
        {
            "artifacts",
            "build_id",
            "claim_boundary",
            "compiler",
            "entrypoint",
            "microcode_abi",
            "model_id",
            "schema",
            "source_application_id",
            "status",
        },
        "lookup deployment manifest",
    )
    if (
        manifest["schema"] != LOOKUP_DEPLOYMENT_SCHEMA
        or manifest["model_id"] != MODEL_ID
        or manifest["compiler"]
        != {
            "name": "opentallas-deepseek-v4-lookup-slice-compiler",
            "version": "0.1.0",
        }
        or manifest["microcode_abi"]
        != {"major": 1, "minor": 0, "name": "deepseek_v4_lookup"}
        or manifest["claim_boundary"]
        != [
            "Executes TOKEN_EMBED, HC_EXPAND, and HASH_ROUTE only.",
            "Does not execute a transformer block, attention, MoE arithmetic, logits, or decode state.",
            "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
        ]
        or manifest["entrypoint"]
        != {
            "execution_expectations": "execution_expectations.json",
            "microcode": "microcode.bin",
            "semantic_ir": "model.ir.json",
            "tensor_manifest": "tensor_manifest.json",
        }
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup deployment identity differs")
    _digest(manifest["source_application_id"], "lookup source_application_id")
    artifacts = manifest["artifacts"]
    if type(artifacts) is not list or not 1 <= len(artifacts) <= 64:
        raise DeepSeekV4HCPreInputCheckError("lookup artifact table size differs")
    records: list[dict[str, Any]] = []
    files_by_path: dict[str, _StableFile] = {}
    roles: set[str] = set()
    total_bytes = 0
    guarded = [manifest_file]
    for index, raw in enumerate(artifacts):
        record = _exact_keys(
            raw,
            {"path", "role", "sha256", "size_bytes"},
            f"lookup artifacts[{index}]",
        )
        relative = _safe_relative(record["path"], f"lookup artifacts[{index}].path")
        role = record["role"]
        if (
            type(role) is not str
            or not role
            or role in roles
            or relative in files_by_path
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "lookup artifact path or role is duplicated"
            )
        expected_sha256 = _digest(record["sha256"], f"lookup artifacts[{index}].sha256")
        size = _integer(
            record["size_bytes"],
            f"lookup artifacts[{index}].size_bytes",
            maximum=_MAX_LOOKUP_ARTIFACT_BYTES,
        )
        total_bytes += size
        if total_bytes > _MAX_LOOKUP_TOTAL_BYTES:
            raise DeepSeekV4HCPreInputCheckError(
                "lookup deployment exceeds its byte bound"
            )
        source = _safe_file(
            stack,
            deployment_root.descriptor,
            relative,
            f"lookup artifact {relative!r}",
            exact_size=size,
        )
        observed_sha256, observed_size = _hash_file(
            source, f"lookup artifact {relative!r}"
        )
        if (observed_sha256, observed_size) != (expected_sha256, size):
            raise DeepSeekV4HCPreInputCheckError(
                f"lookup artifact {relative!r} differs from its manifest"
            )
        roles.add(role)
        files_by_path[relative] = source
        guarded.append(source)
        records.append(
            {
                "path": relative,
                "role": role,
                "sha256": expected_sha256,
                "size_bytes": size,
            }
        )
    if records != sorted(records, key=lambda record: record["path"]):
        raise DeepSeekV4HCPreInputCheckError("lookup artifacts are not path-sorted")
    required_roles = {
        "execution_expectations",
        "microcode",
        "microcode_disassembly",
        "operator_coverage",
        "roundtrip_report",
        "semantic_ir",
        "tensor_manifest",
        "hash_route_table",
    }
    if not required_roles.issubset(roles) or not any(
        role.startswith("embedding_rank_") for role in roles
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup deployment roles are incomplete")
    by_role = {record["role"]: files_by_path[record["path"]] for record in records}
    semantic_file = by_role["semantic_ir"]
    semantic_bytes = _read_file(semantic_file, "lookup semantic IR", _MAX_JSON_BYTES)
    semantic = _strict_json(semantic_bytes, "lookup semantic IR")
    _exact_keys(
        semantic,
        {
            "claim_boundary",
            "dimensions",
            "model_id",
            "numeric_profile",
            "operations",
            "outputs",
            "schema",
            "source",
        },
        "lookup semantic IR",
    )
    source = semantic.get("source")
    dimensions = semantic.get("dimensions")
    if type(source) is dict:
        _exact_keys(
            source,
            {
                "application_id",
                "application_status",
                "checkpoint_lock_id",
                "evidence_scope",
                "repository",
                "revision",
                "verification_id",
            },
            "lookup semantic source",
        )
        _digest(source["application_id"], "lookup semantic application_id")
        _digest(source["verification_id"], "lookup semantic verification_id")
    if type(dimensions) is dict:
        _exact_keys(
            dimensions,
            {
                "expert_count",
                "hc_multiplier",
                "hidden_size",
                "model_parallel",
                "route_top_k",
                "vocabulary_size",
            },
            "lookup semantic dimensions",
        )
        for name, value in dimensions.items():
            _integer(value, f"lookup dimensions.{name}", minimum=1)
    if (
        semantic.get("schema") != "opentallas.deepseek_v4_lookup_slice.v1"
        or semantic.get("model_id") != MODEL_ID
        or type(source) is not dict
        or source.get("checkpoint_lock_id") != lock["lock_id"]
        or source.get("application_id") != manifest["source_application_id"]
        or type(dimensions) is not dict
        or dimensions.get("hc_multiplier") != _HC_MULTIPLIER
        or dimensions.get("hidden_size") != _HIDDEN_SIZE
        or semantic.get("claim_boundary")
        != "Three real-payload pure operators only; not a transformer block, complete decode, hardware timing, or full-model execution."
        or semantic.get("numeric_profile") != "deepseek_v4_flash_lookup_bits_v1"
        or semantic.get("operations")
        != [
            {
                "id": "token_embed",
                "input": "token_ids",
                "kind": "TOKEN_EMBED",
                "output": "embedding_bf16_codes",
                "resource": "embed.weight",
            },
            {
                "id": "hc_expand",
                "input": "embedding_bf16_codes",
                "kind": "HC_EXPAND",
                "output": "hc_hidden_bf16_codes",
                "resource": None,
            },
            {
                "id": "hash_route",
                "input": "token_ids",
                "kind": "HASH_ROUTE",
                "output": "expert_ids",
                "resource": "layers.0.ffn.gate.tid2eid",
            },
        ]
        or semantic.get("outputs")
        != ["embedding_bf16_codes", "hc_hidden_bf16_codes", "expert_ids"]
    ):
        raise DeepSeekV4HCPreInputCheckError(
            "lookup semantic source or HC_PRE interface dimensions differ"
        )
    expected_status = (
        "real_checkpoint_lookup_slice_not_full_model"
        if source.get("evidence_scope") == "official_checkpoint"
        else "development_fixture_lookup_slice_not_release_evidence"
    )
    if manifest["status"] != expected_status:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup status differs from its evidence scope"
        )
    expected_application_status = (
        "partial_official_transform_application_not_release_evidence"
        if source.get("evidence_scope") == "official_checkpoint"
        else "development_fixture_application_not_release_evidence"
    )
    if source.get("application_status") != expected_application_status:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup application status differs from its evidence scope"
        )
    expected_role_paths = {
        "execution_expectations": "execution_expectations.json",
        "hash_route_table": "rom/hash_route.bin",
        "microcode": "microcode.bin",
        "microcode_disassembly": "microcode.disasm",
        "operator_coverage": "operator_coverage.json",
        "roundtrip_report": "roundtrip_report.json",
        "semantic_ir": "model.ir.json",
        "tensor_manifest": "tensor_manifest.json",
    }
    for rank in range(dimensions["model_parallel"]):
        expected_role_paths[f"embedding_rank_{rank:03d}"] = (
            f"rom/embed/rank-{rank:03d}.bin"
        )
    observed_role_paths = {record["role"]: record["path"] for record in records}
    if observed_role_paths != expected_role_paths:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup artifact path-to-role closure differs"
        )
    _verify_lookup_auxiliary_contracts(
        by_role=by_role,
        dimensions=dimensions,
        manifest=manifest,
    )
    identity = {
        "artifacts": records,
        "compiler_version": "0.1.0",
        "microcode_abi": manifest["microcode_abi"],
        "model_id": MODEL_ID,
        "source_application_id": manifest["source_application_id"],
    }
    build_id = _digest(manifest["build_id"], "lookup build_id")
    if _sha256_json(identity) != build_id:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup build_id does not bind its artifacts"
        )
    microcode = _read_file(by_role["microcode"], "lookup microcode", 1024 * 1024)
    try:
        instructions = decode_lookup_program(microcode)
        verify_lookup_program(instructions, _HC_MULTIPLIER)
    except ValueError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"lookup microcode differs: {exc}"
        ) from exc
    disassembly = _read_file(
        by_role["microcode_disassembly"], "lookup microcode disassembly", 1024 * 1024
    )
    if disassembly != disassemble_lookup_program(instructions).encode("ascii"):
        raise DeepSeekV4HCPreInputCheckError("lookup microcode disassembly differs")
    actual_files, actual_directories = _enumerate_tree(deployment_root.descriptor)
    expected_files = set(files_by_path) | {"deployment_manifest.json"}
    if actual_files != expected_files or actual_directories != _expected_directories(
        expected_files
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup deployment tree closure differs")
    return (
        manifest,
        manifest_bytes,
        semantic,
        semantic_bytes,
        deployment_root,
        guarded,
    )


def _parse_tokens(
    request: Mapping[str, Any], build_id: str
) -> tuple[tuple[int, ...], ...]:
    _exact_keys(
        request,
        {"build_id", "model_id", "schema", "token_ids"},
        "lookup request",
    )
    if (
        request["schema"] != LOOKUP_REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != build_id
    ):
        raise DeepSeekV4HCPreInputCheckError("lookup request identity differs")
    raw_batches = request["token_ids"]
    if type(raw_batches) is not list or not raw_batches:
        raise DeepSeekV4HCPreInputCheckError(
            "lookup token IDs must be a non-empty rank-2 array"
        )
    batches: list[tuple[int, ...]] = []
    sequence_length: int | None = None
    for batch_index, raw_batch in enumerate(raw_batches):
        if type(raw_batch) is not list or not raw_batch:
            raise DeepSeekV4HCPreInputCheckError(
                f"lookup token_ids[{batch_index}] must be a non-empty array"
            )
        if sequence_length is None:
            sequence_length = len(raw_batch)
        elif len(raw_batch) != sequence_length:
            raise DeepSeekV4HCPreInputCheckError("lookup token IDs must be rectangular")
        batches.append(
            tuple(
                _integer(
                    token,
                    f"lookup token_ids[{batch_index}][{position}]",
                    maximum=129_279,
                )
                for position, token in enumerate(raw_batch)
            )
        )
    token_count = len(batches) * len(batches[0])
    if token_count > _MAX_TOKEN_COUNT:
        raise DeepSeekV4HCPreInputCheckError(
            f"HC_PRE accepts at most {_MAX_TOKEN_COUNT} lookup tokens"
        )
    return tuple(batches)


def _extract_hc_payload(
    result: Mapping[str, Any],
    *,
    tokens: tuple[tuple[int, ...], ...],
    build_id: str,
    request_sha256: str,
    evidence_scope: str,
    deployment_status: str,
    source_application_status: str,
) -> tuple[bytes, str]:
    _exact_keys(
        result,
        {
            "build_id",
            "counter_reconciliation",
            "counters",
            "deployment_status",
            "evidence_scope",
            "execution_scope",
            "model_id",
            "outputs",
            "request_sha256",
            "schema",
            "source_application_status",
            "status",
        },
        "lookup result",
    )
    if (
        result["schema"] != LOOKUP_RESULT_SCHEMA
        or result["model_id"] != MODEL_ID
        or result["build_id"] != build_id
        or result["request_sha256"] != request_sha256
        or result["status"] != "pass"
        or result["counter_reconciliation"] != "exact"
        or result["execution_scope"] != "three_operator_real_payload_slice_only"
        or result["evidence_scope"] != evidence_scope
        or result["deployment_status"] != deployment_status
        or result["source_application_status"] != source_application_status
    ):
        raise DeepSeekV4HCPreInputCheckError(
            "lookup result identity or pass status differs"
        )
    outputs = result["outputs"]
    if type(outputs) is not list or len(outputs) != 3:
        raise DeepSeekV4HCPreInputCheckError("lookup result outputs differ")
    expected_ids = ["embedding_bf16_codes", "hc_hidden_bf16_codes", "expert_ids"]
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(outputs):
        record = _exact_keys(
            raw, {"dtype", "id", "shape", "values"}, f"lookup output {index}"
        )
        if record["id"] != expected_ids[index]:
            raise DeepSeekV4HCPreInputCheckError("lookup output ordering differs")
        by_id[record["id"]] = record
    hc = by_id["hc_hidden_bf16_codes"]
    batch_size = len(tokens)
    sequence_length = len(tokens[0])
    shape = [batch_size, sequence_length, _HC_MULTIPLIER, _HIDDEN_SIZE]
    if hc["dtype"] != "BF16_BITS" or hc["shape"] != shape:
        raise DeepSeekV4HCPreInputCheckError("lookup HC-hidden metadata differs")
    raw_batches = hc["values"]
    if type(raw_batches) is not list or len(raw_batches) != batch_size:
        raise DeepSeekV4HCPreInputCheckError("lookup HC-hidden batch extent differs")
    payload = bytearray(
        batch_size * sequence_length * _HC_MULTIPLIER * _HIDDEN_SIZE * 2
    )
    offset = 0
    for batch_index, raw_batch in enumerate(raw_batches):
        if type(raw_batch) is not list or len(raw_batch) != sequence_length:
            raise DeepSeekV4HCPreInputCheckError(
                f"lookup HC-hidden batch {batch_index} sequence extent differs"
            )
        for position, raw_copies in enumerate(raw_batch):
            if type(raw_copies) is not list or len(raw_copies) != _HC_MULTIPLIER:
                raise DeepSeekV4HCPreInputCheckError(
                    f"lookup HC-hidden [{batch_index}][{position}] HC extent differs"
                )
            for copy_index, raw_vector in enumerate(raw_copies):
                if type(raw_vector) is not list or len(raw_vector) != _HIDDEN_SIZE:
                    raise DeepSeekV4HCPreInputCheckError(
                        f"lookup HC-hidden [{batch_index}][{position}][{copy_index}] width differs"
                    )
                for column, raw_code in enumerate(raw_vector):
                    code = _integer(
                        raw_code,
                        (
                            f"lookup HC-hidden [{batch_index}][{position}]"
                            f"[{copy_index}][{column}]"
                        ),
                        maximum=(1 << 16) - 1,
                    )
                    if code & 0x7F80 == 0x7F80:
                        raise DeepSeekV4HCPreInputCheckError(
                            "lookup HC-hidden contains non-finite BF16"
                        )
                    struct.pack_into("<H", payload, offset, code)
                    offset += 2
    return bytes(payload), _sha256_json(raw_batches)


def _write_replay_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise DeepSeekV4HCPreInputCheckError(
                    "cannot materialize lookup replay evidence"
                )
            view = view[written:]
    finally:
        os.close(descriptor)


def _replay_lookup_differential(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    manifest_bytes: bytes,
    semantic_bytes: bytes,
    request_bytes: bytes,
    result_bytes: bytes,
) -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory(
            prefix=".opentallas-hc-pre-input-replay-"
        ) as raw:
            root = Path(raw)
            deployment = root / "deployment"
            deployment.mkdir(mode=0o700)
            _write_replay_file(deployment / "deployment_manifest.json", manifest_bytes)
            _write_replay_file(deployment / "model.ir.json", semantic_bytes)
            request = root / "request.json"
            result = root / "result.json"
            _write_replay_file(request, request_bytes)
            _write_replay_file(result, result_bytes)
            return verify_deepseek_v4_lookup_execution(
                snapshot=Path(snapshot),
                lock=lock,
                deployment_root=deployment,
                request_path=request,
                result_path=result,
            )
    except DeepSeekV4HCPreInputCheckError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"independent lookup differential replay failed: {exc}"
        ) from exc


def _tokenizer_provenance(
    *,
    snapshot: Path,
    lock: Mapping[str, Any],
    source_texts: Sequence[str],
    tokens: tuple[tuple[int, ...], ...],
    evidence_scope: str,
) -> dict[str, Any]:
    if type(source_texts) not in {list, tuple}:
        raise DeepSeekV4HCPreInputCheckError(
            "source_texts must be an exact list or tuple, not a scalar string"
        )
    if len(source_texts) != len(tokens):
        raise DeepSeekV4HCPreInputCheckError(
            "source_texts must contain exactly one text for each lookup batch row"
        )
    source_rows: list[dict[str, Any]] = []
    source_payloads: list[bytes] = []
    for batch_index, (source_text, token_row) in enumerate(
        zip(source_texts, tokens, strict=True)
    ):
        if type(source_text) is not str:
            raise DeepSeekV4HCPreInputCheckError(
                f"source_texts[{batch_index}] must be an exact string"
            )
        try:
            source_bytes = source_text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise DeepSeekV4HCPreInputCheckError(
                f"source_texts[{batch_index}] is not valid UTF-8"
            ) from exc
        if len(source_bytes) > _MAX_SOURCE_TEXT_BYTES:
            raise DeepSeekV4HCPreInputCheckError(
                f"source_texts[{batch_index}] exceeds its UTF-8 byte bound"
            )
        source_payloads.append(source_bytes)
        source_rows.append(
            {
                "batch_index": batch_index,
                "encoded_token_ids_sha256": _sha256_json(token_row),
                "encode_status": "not_available_development_fixture",
                "utf8_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "utf8_size_bytes": len(source_bytes),
            }
        )
    token_lists = [list(batch) for batch in tokens]
    common = {
        "batch_size": len(tokens),
        "encode_equivalence": "not_available_development_fixture",
        "source_text_rows": source_rows,
        "token_ids": token_lists,
        "token_ids_sha256": _sha256_json(tokens),
        "tokenizer_config_sha256": None,
        "tokenizer_config_size_bytes": None,
        "tokenizer_sha256": None,
        "tokenizer_size_bytes": None,
        "tokenizer_validation_id": None,
    }
    if evidence_scope != "official_checkpoint":
        return common
    expected_files = {
        record.get("path"): record
        for record in lock["source"].get("expected_files", [])
        if type(record) is dict
    }
    if expected_files.get("tokenizer.json") != {
        "path": "tokenizer.json",
        "sha256": TOKENIZER_SHA256,
        "size_bytes": TOKENIZER_SIZE_BYTES,
    } or expected_files.get("tokenizer_config.json") != {
        "path": "tokenizer_config.json",
        "sha256": TOKENIZER_CONFIG_SHA256,
        "size_bytes": TOKENIZER_CONFIG_SIZE_BYTES,
    }:
        raise DeepSeekV4HCPreInputCheckError(
            "official checkpoint lock does not bind the pinned tokenizer artifacts"
        )
    try:
        tokenizer = load_verified_deepseek_v4_tokenizer(Path(snapshot))
        encoded_rows = [tokenizer.encode(source_text) for source_text in source_texts]
        validation = tokenizer.validation_report
    except RuntimeError as exc:
        raise DeepSeekV4HCPreInputCheckError(
            f"official tokenizer verification or encoding failed: {exc}"
        ) from exc
    validation_id = _digest(validation.get("validation_id"), "tokenizer validation_id")
    if validation_id != _OFFICIAL_TOKENIZER_VALIDATION_ID:
        raise DeepSeekV4HCPreInputCheckError(
            "official tokenizer validation identity differs from its frozen contract"
        )
    for batch_index, (encoded, expected) in enumerate(
        zip(encoded_rows, tokens, strict=True)
    ):
        if encoded != list(expected):
            raise DeepSeekV4HCPreInputCheckError(
                "official tokenizer output differs from lookup request token IDs "
                f"at batch row {batch_index}"
            )
        source_rows[batch_index]["encode_status"] = (
            "exact_official_tokenizer_encode_equivalence"
        )
    return {
        **common,
        "encode_equivalence": "exact_official_tokenizer_encode_equivalence",
        "tokenizer_config_sha256": TOKENIZER_CONFIG_SHA256,
        "tokenizer_config_size_bytes": TOKENIZER_CONFIG_SIZE_BYTES,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_size_bytes": TOKENIZER_SIZE_BYTES,
        "tokenizer_validation_id": validation_id,
    }


def _derive_material(
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
) -> _CompositionMaterial:
    """Reopen all causal evidence and derive the only acceptable request bytes."""

    _require_secure_file_operations()
    if type(source_texts) not in {list, tuple}:
        raise DeepSeekV4HCPreInputCheckError(
            "source_texts must be an exact list or tuple, not a scalar string"
        )
    frozen_source_texts = tuple(source_texts)
    try:
        validate_checkpoint_lock(lock)
    except (RuntimeError, ValueError) as exc:
        raise DeepSeekV4HCPreInputCheckError(f"checkpoint lock differs: {exc}") from exc
    with ExitStack() as stack:
        (
            lookup_manifest,
            lookup_manifest_bytes,
            lookup_semantic,
            lookup_semantic_bytes,
            lookup_root,
            lookup_guarded,
        ) = _inspect_lookup_deployment(stack, lookup_deployment_root, lock)
        request_parent, request_file = _direct_file(
            stack,
            lookup_request_path,
            "lookup request",
            maximum_size=_MAX_JSON_BYTES,
        )
        result_parent, result_file = _direct_file(
            stack,
            lookup_result_path,
            "lookup result",
            maximum_size=_MAX_JSON_BYTES,
        )
        differential_parent, differential_file = _direct_file(
            stack,
            lookup_differential_path,
            "lookup differential",
            maximum_size=_MAX_JSON_BYTES,
        )
        request_bytes = _read_file(request_file, "lookup request", _MAX_JSON_BYTES)
        result_bytes = _read_file(result_file, "lookup result", _MAX_JSON_BYTES)
        differential_bytes = _read_file(
            differential_file, "lookup differential", _MAX_JSON_BYTES
        )
        request = _strict_json(request_bytes, "lookup request")
        result = _strict_json(result_bytes, "lookup result")
        retained_differential = _strict_json(differential_bytes, "lookup differential")
        lookup_build_id = _digest(lookup_manifest["build_id"], "lookup build_id")
        tokens = _parse_tokens(request, lookup_build_id)
        request_sha256 = hashlib.sha256(request_bytes).hexdigest()
        lookup_source = lookup_semantic["source"]
        evidence_scope = lookup_source.get("evidence_scope")
        if evidence_scope not in {"official_checkpoint", "development_fixture"}:
            raise DeepSeekV4HCPreInputCheckError("lookup evidence scope differs")
        input_payload, hc_values_sha256 = _extract_hc_payload(
            result,
            tokens=tokens,
            build_id=lookup_build_id,
            request_sha256=request_sha256,
            evidence_scope=evidence_scope,
            deployment_status=lookup_manifest["status"],
            source_application_status=lookup_source.get("application_status"),
        )
        replayed_differential = _replay_lookup_differential(
            snapshot=Path(snapshot),
            lock=lock,
            manifest_bytes=lookup_manifest_bytes,
            semantic_bytes=lookup_semantic_bytes,
            request_bytes=request_bytes,
            result_bytes=result_bytes,
        )
        if canonical_json_bytes(retained_differential) != canonical_json_bytes(
            replayed_differential
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "retained lookup differential differs from independent replay"
            )
        _exact_keys(
            retained_differential,
            {
                "build_id",
                "checkpoint_lock_id",
                "claim_boundary",
                "comparisons",
                "counters",
                "differential_id",
                "model_id",
                "request_sha256",
                "schema",
                "source_tensors",
                "status",
                "token_count",
                "token_ids_sha256",
            },
            "lookup differential",
        )
        token_count = len(tokens) * len(tokens[0])
        if (
            retained_differential["schema"] != LOOKUP_DIFFERENTIAL_SCHEMA
            or retained_differential["model_id"] != MODEL_ID
            or retained_differential["status"] != "exact_locked_checkpoint_differential"
            or retained_differential["build_id"] != lookup_build_id
            or retained_differential["checkpoint_lock_id"] != lock["lock_id"]
            or retained_differential["request_sha256"] != request_sha256
            or retained_differential["token_count"] != token_count
            or retained_differential["token_ids_sha256"] != _sha256_json(tokens)
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "lookup differential identity or exact status differs"
            )
        differential_id = _digest(
            retained_differential["differential_id"], "lookup differential_id"
        )
        identity = dict(retained_differential)
        identity.pop("differential_id")
        if _sha256_json(identity) != differential_id:
            raise DeepSeekV4HCPreInputCheckError(
                "lookup differential_id does not bind its body"
            )

        executable_root = _open_root(
            stack, executable_deployment_root, "HC_PRE executable deployment root"
        )
        executable_manifest_file = _safe_file(
            stack,
            executable_root.descriptor,
            "deployment_manifest.json",
            "HC_PRE executable deployment manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        executable_manifest_bytes = _read_file(
            executable_manifest_file,
            "HC_PRE executable deployment manifest",
            _MAX_MANIFEST_BYTES,
        )
        executable_manifest = _strict_json(
            executable_manifest_bytes, "HC_PRE executable deployment manifest"
        )
        try:
            executable_check = verify_deepseek_v4_hc_pre_executable_deployment(
                Path(executable_deployment_root), Path(executable_application_root)
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeepSeekV4HCPreInputCheckError(
                f"HC_PRE executable deployment verification failed: {exc}"
            ) from exc
        executable_source = executable_manifest.get("source")
        if (
            executable_manifest.get("schema") != EXECUTABLE_SCHEMA
            or executable_manifest.get("model_id") != MODEL_ID
            or executable_manifest.get("program_sha256") != PROGRAM_SHA256
            or executable_manifest.get("build_id") != executable_check.get("build_id")
            or type(executable_source) is not dict
            or executable_source.get("checkpoint_lock_id") != lock["lock_id"]
            or executable_source.get("evidence_scope") != evidence_scope
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "HC_PRE executable identity or source differs from lookup evidence"
            )
        if evidence_scope == "official_checkpoint" and (
            lookup_source.get("repository"),
            lookup_source.get("revision"),
            executable_source.get("repository"),
            executable_source.get("revision"),
            lock["source"].get("repository"),
            lock["source"].get("revision"),
        ) != (REPOSITORY, REVISION, REPOSITORY, REVISION, REPOSITORY, REVISION):
            raise DeepSeekV4HCPreInputCheckError(
                "official evidence does not bind the pinned repository revision"
            )
        if evidence_scope == "official_checkpoint":
            try:
                validate_official_checkpoint_lock(lock, load_official_config())
            except (OSError, RuntimeError, ValueError) as exc:
                raise DeepSeekV4HCPreInputCheckError(
                    f"official checkpoint lock differs from the frozen release: {exc}"
                ) from exc
        tokenizer = _tokenizer_provenance(
            snapshot=Path(snapshot),
            lock=lock,
            source_texts=frozen_source_texts,
            tokens=tokens,
            evidence_scope=evidence_scope,
        )

        batch_size = len(tokens)
        sequence_length = len(tokens[0])
        input_sha256 = hashlib.sha256(input_payload).hexdigest()
        request_manifest = {
            "batch_size": batch_size,
            "build_id": executable_manifest["build_id"],
            "input": {
                "dtype": "BF16",
                "encoding": "bfloat16_little_endian",
                "id": "hc_hidden",
                "path": INPUT_RELATIVE,
                "register": "HC_HIDDEN",
                "sha256": input_sha256,
                "shape": [batch_size, sequence_length, _HC_MULTIPLIER, _HIDDEN_SIZE],
                "size_bytes": len(input_payload),
            },
            "model_id": MODEL_ID,
            "program_sha256": PROGRAM_SHA256,
            "schema": REQUEST_SCHEMA,
            "sequence_length": sequence_length,
            "token_count": token_count,
        }
        request_manifest_bytes = canonical_json_bytes(request_manifest)
        composed_request_sha256 = hashlib.sha256(request_manifest_bytes).hexdigest()
        request_files = [
            {
                "path": INPUT_RELATIVE,
                "sha256": input_sha256,
                "size_bytes": len(input_payload),
            },
            {
                "path": REQUEST_MANIFEST,
                "sha256": composed_request_sha256,
                "size_bytes": len(request_manifest_bytes),
            },
        ]
        status = (
            "official_tokenizer_lookup_differential_composition_verified"
            if evidence_scope == "official_checkpoint"
            else "development_fixture_lookup_differential_composition_not_release_evidence"
        )
        report_body: dict[str, Any] = {
            "checkpoint": {
                "evidence_scope": evidence_scope,
                "lock_id": lock["lock_id"],
                "repository": lock["source"]["repository"],
                "revision": lock["source"]["revision"],
            },
            "claim_boundary": list(CLAIM_BOUNDARY),
            "executable": {
                "application_id": executable_source.get("application_id"),
                "build_id": executable_manifest["build_id"],
                "deployment_manifest_sha256": hashlib.sha256(
                    executable_manifest_bytes
                ).hexdigest(),
                "parameter_build_id": executable_manifest.get("parameter_build_id"),
                "program_sha256": PROGRAM_SHA256,
                "schedule_certificate_id": executable_manifest.get(
                    "schedule_certificate_id"
                ),
                "schedule_id": executable_manifest.get("schedule_id"),
            },
            "lookup": {
                "build_id": lookup_build_id,
                "deployment_manifest_sha256": hashlib.sha256(
                    lookup_manifest_bytes
                ).hexdigest(),
                "differential_id": differential_id,
                "differential_sha256": hashlib.sha256(differential_bytes).hexdigest(),
                "differential_status": retained_differential["status"],
                "hc_hidden_values_sha256": hc_values_sha256,
                "request_sha256": request_sha256,
                "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
                "result_status": result["status"],
                "source_application_id": lookup_manifest["source_application_id"],
            },
            "model_id": MODEL_ID,
            "request": {
                "files": request_files,
                "input_sha256": input_sha256,
                "request_sha256": composed_request_sha256,
                "shape": [batch_size, sequence_length, _HC_MULTIPLIER, _HIDDEN_SIZE],
                "tree_sha256": _sha256_json(request_files),
            },
            "schema": COMPOSITION_SCHEMA,
            "status": status,
            "tokenizer": tokenizer,
        }
        report = {
            **report_body,
            "composition_id": _sha256_json(report_body),
        }

        for guarded in [
            *lookup_guarded,
            request_file,
            result_file,
            differential_file,
            executable_manifest_file,
        ]:
            _verify_file_stable(guarded, f"guarded evidence {guarded.relative_path!r}")
        for parent, label in (
            (request_parent, "lookup request parent"),
            (result_parent, "lookup result parent"),
            (differential_parent, "lookup differential parent"),
        ):
            _verify_root_binding(parent, label)
        _verify_root_stable(lookup_root, "lookup deployment root")
        _verify_root_stable(executable_root, "HC_PRE executable deployment root")
        return _CompositionMaterial(input_payload, request_manifest, report)


def verify_deepseek_v4_hc_pre_input_composition(
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
    request_root: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Recompute the full causal chain and verify a closed two-file request tree."""

    material = _derive_material(
        snapshot=snapshot,
        lock=lock,
        lookup_deployment_root=lookup_deployment_root,
        lookup_request_path=lookup_request_path,
        lookup_result_path=lookup_result_path,
        lookup_differential_path=lookup_differential_path,
        executable_deployment_root=executable_deployment_root,
        executable_application_root=executable_application_root,
        source_texts=source_texts,
    )
    with ExitStack() as stack:
        root = _open_root(stack, request_root, "HC_PRE request root")
        manifest_file = _safe_file(
            stack,
            root.descriptor,
            REQUEST_MANIFEST,
            "HC_PRE request manifest",
            exact_size=len(canonical_json_bytes(material.request_manifest)),
        )
        input_file = _safe_file(
            stack,
            root.descriptor,
            INPUT_RELATIVE,
            "HC_PRE request input",
            exact_size=len(material.input_payload),
        )
        report_parent, report_file = _direct_file(
            stack,
            report_path,
            "HC_PRE composition report",
            maximum_size=_MAX_JSON_BYTES,
        )
        manifest_bytes = _read_file(
            manifest_file, "HC_PRE request manifest", _MAX_MANIFEST_BYTES
        )
        input_payload = _read_file(
            input_file, "HC_PRE request input", len(material.input_payload)
        )
        report_bytes = _read_file(
            report_file, "HC_PRE composition report", _MAX_JSON_BYTES
        )
        observed_manifest = _strict_json(manifest_bytes, "HC_PRE request manifest")
        observed_report = _strict_json(report_bytes, "HC_PRE composition report")
        if canonical_json_bytes(observed_manifest) != canonical_json_bytes(
            material.request_manifest
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "HC_PRE request manifest differs from causal composition"
            )
        if input_payload != material.input_payload:
            raise DeepSeekV4HCPreInputCheckError(
                "HC_PRE input payload differs from the verified lookup result"
            )
        if canonical_json_bytes(observed_report) != canonical_json_bytes(
            material.report
        ):
            raise DeepSeekV4HCPreInputCheckError(
                "HC_PRE composition report differs from causal composition"
            )
        actual_files, actual_directories = _enumerate_tree(root.descriptor)
        expected_files = {REQUEST_MANIFEST, INPUT_RELATIVE}
        if actual_files != expected_files or actual_directories != {"input"}:
            raise DeepSeekV4HCPreInputCheckError(
                "HC_PRE request must be a closed two-file tree"
            )
        for guarded, label in (
            (manifest_file, "HC_PRE request manifest"),
            (input_file, "HC_PRE request input"),
            (report_file, "HC_PRE composition report"),
        ):
            _verify_file_stable(guarded, label)
        _verify_root_stable(root, "HC_PRE request root")
        _verify_root_binding(report_parent, "HC_PRE composition report parent")
        return {
            "composition_id": material.report["composition_id"],
            "input_sha256": material.report["request"]["input_sha256"],
            "request_sha256": material.report["request"]["request_sha256"],
            "status": material.report["status"],
            "token_count": material.request_manifest["token_count"],
        }


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPOSITION_SCHEMA",
    "INPUT_RELATIVE",
    "PROGRAM_SHA256",
    "REQUEST_MANIFEST",
    "REQUEST_SCHEMA",
    "DeepSeekV4HCPreInputCheckError",
    "verify_deepseek_v4_hc_pre_input_composition",
]
