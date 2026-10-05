"""Independent causal checker for a DeepSeek V4 Query-A request.

The only accepted input payload is the persisted ``ATTENTION_INPUT`` output of
an official, passing ``HC_PRE`` execution result.  The source output has shape
``[B,S,4096]`` and the Query-A ABI consumes ``[T,4096]`` where ``T=B*S``.
Both layouts are contiguous in the same token-major order, so composition is
strict byte identity: this module never decodes, computes, or re-encodes BF16.

Hostile artifact trees are opened descriptor-relative with ``O_NOFOLLOW`` and
``O_NONBLOCK``.  JSON must be canonical and type-exact, every HC result payload
is hash/size/shape checked, tree closure is exact, and retained inode identities
are rechecked after derivation.  The Query-A deployment is also reopened and
bound to the independent executable-package verifier.

Passing this checker proves only causal, byte-preserving request composition.
It performs no HC_PRE or Query-A arithmetic, execution, expected-output
generation, reference fallback, scheduling, timing, physical, PPA,
manufacturability, or accelerator-comparison work.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from typing import Any

from compiler.frontend.deepseek_v4 import MODEL_ID
from compiler.ir.model import canonical_json_bytes


COMPOSITION_SCHEMA = "opentallas.deepseek_v4_query_a_input_composition.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_query_a_execution_request.v1"
HC_RESULT_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_result.v1"
QUERY_A_EXECUTABLE_SCHEMA = "opentallas.deepseek_v4_query_a_executable.v1"
HC_PRE_PROGRAM_SHA256 = (
    "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
)
QUERY_A_PROGRAM_SHA256 = (
    "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
)

RESULT_MANIFEST = "result_manifest.json"
DEPLOYMENT_MANIFEST = "deployment_manifest.json"
REQUEST_MANIFEST = "request_manifest.json"
INPUT_RELATIVE = "input/attention_input.bf16le"

CLAIM_BOUNDARY = [
    "Composes Query-A ATTENTION_INPUT only from one persisted official passing HC_PRE execution result.",
    "Flattens contiguous [B,S,4096] to [B*S,4096] by exact byte identity without BF16 decode, arithmetic, or re-encoding.",
    "Binds the request to an independently verified Query-A executable build and program identity.",
    "Stores no source text and no expected Query-A output.",
    "Establishes no Query-A execution, attention completion, transformer-block, full-model, timing, bandwidth, physical, PPA, manufacturability, or accelerator-comparison claim.",
]

_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_TOKEN_COUNT = 4
_HIDDEN_SIZE = 4096
_BF16_BYTES = 2
_MAX_INPUT_BYTES = _MAX_TOKEN_COUNT * _HIDDEN_SIZE * _BF16_BYTES
_MAX_RESULT_FILE_BYTES = _MAX_TOKEN_COUNT * 4 * _HIDDEN_SIZE * _BF16_BYTES
_MAX_TREE_ENTRIES = 32
_MAX_TREE_DEPTH = 4
_SHA256_LENGTH = 64

_HC_COUNTERS = frozenset(
    {
        "hc_pre_branch_bf16_conversions",
        "hc_pre_branch_bf16_saturations",
        "hc_pre_branch_coefficient_multiplies",
        "hc_pre_branch_reduction_adds",
        "hc_pre_coefficient_epsilon_adds",
        "hc_pre_exp_evaluations",
        "hc_pre_field_affine_adds",
        "hc_pre_field_affine_multiplies",
        "hc_pre_input_bf16_values",
        "hc_pre_post_factor_multiplies",
        "hc_pre_projection_product_accumulates",
        "hc_pre_projection_rms_multiplies",
        "hc_pre_residual_bf16_values_preserved",
        "hc_pre_rms_divides",
        "hc_pre_rms_epsilon_adds",
        "hc_pre_rms_reduction_adds",
        "hc_pre_rms_square_multiplies",
        "hc_pre_rsqrt_evaluations",
        "hc_pre_sigmoid_evaluations",
        "hc_pre_sinkhorn_column_reduction_adds",
        "hc_pre_sinkhorn_column_stages",
        "hc_pre_sinkhorn_divides",
        "hc_pre_sinkhorn_epsilon_adds",
        "hc_pre_sinkhorn_row_reduction_adds",
        "hc_pre_sinkhorn_row_stages",
        "hc_pre_softmax_max_comparisons",
        "hc_pre_softmax_subtracts",
    }
)


class DeepSeekV4QueryAInputCheckError(RuntimeError):
    """Raised when Query-A input lacks an exact verified HC_PRE provenance."""


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
class _PayloadSpec:
    identifier: str
    path: str
    dtype: str
    encoding: str
    shape_suffix: tuple[int, ...]
    bytes_per_token: int
    register: str | None


@dataclass(frozen=True)
class _HCResult:
    root: _StableRoot
    manifest_file: _StableFile
    guarded_files: tuple[_StableFile, ...]
    manifest_sha256: str
    build_id: str
    request_sha256: str
    batch_size: int
    sequence_length: int
    token_count: int
    input_payload: bytes
    input_sha256: str
    input_path: str
    tree_sha256: str


@dataclass(frozen=True)
class _QueryADeployment:
    root: _StableRoot
    manifest_file: _StableFile
    manifest_sha256: str
    application_id: str
    build_id: str
    checkpoint_lock_id: str
    program_sha256: str
    repository: str
    revision: str
    verification_id: str
    verifier_status: str


@dataclass(frozen=True)
class _CompositionMaterial:
    input_payload: bytes
    request_manifest: dict[str, Any]
    report: dict[str, Any]


_OUTPUT_SPECS = (
    _PayloadSpec(
        "attention_input",
        "outputs/attention_input.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (_HIDDEN_SIZE,),
        _HIDDEN_SIZE * _BF16_BYTES,
        "ATTENTION_INPUT",
    ),
    _PayloadSpec(
        "attention_pre",
        "outputs/attention_pre.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        4 * 4,
        "ATTENTION_PRE",
    ),
    _PayloadSpec(
        "attention_post",
        "outputs/attention_post.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        4 * 4,
        "ATTENTION_POST",
    ),
    _PayloadSpec(
        "attention_combination",
        "outputs/attention_combination.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        4 * 4 * 4,
        "ATTENTION_COMBINATION",
    ),
    _PayloadSpec(
        "attention_residual",
        "outputs/attention_residual.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (4, _HIDDEN_SIZE),
        4 * _HIDDEN_SIZE * _BF16_BYTES,
        "ATTENTION_RESIDUAL",
    ),
)

_DIAGNOSTIC_SPECS = (
    _PayloadSpec(
        "rms_mean_codes",
        "diagnostics/rms_mean.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        None,
    ),
    _PayloadSpec(
        "rms_inverse_codes",
        "diagnostics/rms_inverse.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        None,
    ),
    _PayloadSpec(
        "projection_codes",
        "diagnostics/projection.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        24 * 4,
        None,
    ),
    _PayloadSpec(
        "mix_codes",
        "diagnostics/mix.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        24 * 4,
        None,
    ),
    _PayloadSpec(
        "stable_softmax_codes",
        "diagnostics/stable_softmax.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        4 * 4 * 4,
        None,
    ),
)


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
    if (
        missing
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.listdir not in os.supports_fd
    ):
        raise DeepSeekV4QueryAInputCheckError(
            "secure descriptor operations are unavailable"
            + (f": {', '.join(missing)}" if missing else "")
        )


def _specific_path(value: Path, label: str) -> Path:
    try:
        path = Path(value).absolute()
    except TypeError as exc:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} must be a filesystem path"
        ) from exc
    if not path.name or path.name in {".", ".."} or path == Path(path.anchor):
        raise DeepSeekV4QueryAInputCheckError(f"{label} must name a specific path")
    return path


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4QueryAInputCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4QueryAInputCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4QueryAInputCheckError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, path: Path, label: str) -> _StableRoot:
    _require_secure_file_operations()
    path = _specific_path(path, label)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAInputCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4QueryAInputCheckError(f"{label} is not a directory")
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
        raise DeepSeekV4QueryAInputCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _safe_file(
    stack: ExitStack,
    root: _StableRoot,
    relative: object,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    safe = _safe_relative(relative, label)
    descriptor = _open_relative_descriptor(
        root.descriptor, safe, label, directory=False
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4QueryAInputCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor,
        _fingerprint(metadata),
        safe,
        root.descriptor,
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
        parent,
        specific.name,
        label,
        maximum_size=maximum_size,
    )
    return parent, source


def _read_file(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4QueryAInputCheckError(f"{label} exceeds its read bound")
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
            raise DeepSeekV4QueryAInputCheckError(
                f"cannot read {label}: {exc}"
            ) from exc
        if not chunk:
            raise DeepSeekV4QueryAInputCheckError(
                f"{label} ended before its stable size"
            )
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _verify_file_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4QueryAInputCheckError(f"{label} changed during verification")
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
            raise DeepSeekV4QueryAInputCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current)


def _verify_root_stable(root: _StableRoot, label: str) -> None:
    if _fingerprint(os.fstat(root.descriptor)) != root.fingerprint:
        raise DeepSeekV4QueryAInputCheckError(f"{label} changed during verification")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(root.path, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAInputCheckError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        metadata = os.fstat(current)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or _fingerprint(metadata) != root.fingerprint
        ):
            raise DeepSeekV4QueryAInputCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4QueryAInputCheckError(
                    f"{label} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} contains non-finite JSON number {token!r}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4QueryAInputCheckError(f"cannot parse {label}: {exc}") from exc
    if type(value) is not dict:
        raise DeepSeekV4QueryAInputCheckError(f"{label} must be a JSON object")
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} is not canonical JSON: {exc}"
        ) from exc
    if payload != canonical:
        raise DeepSeekV4QueryAInputCheckError(f"{label} bytes are not canonical JSON")
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4QueryAInputCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _strict_equal(value: object, expected: object) -> bool:
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return value.keys() == expected.keys() and all(  # type: ignore[union-attr]
            type(key) is str and _strict_equal(value[key], expected[key])  # type: ignore[index]
            for key in expected  # type: ignore[union-attr]
        )
    if type(expected) in {list, tuple}:
        return len(value) == len(expected) and all(  # type: ignore[arg-type]
            _strict_equal(left, right)
            for left, right in zip(value, expected, strict=True)  # type: ignore[arg-type]
        )
    return value == expected


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
        raise DeepSeekV4QueryAInputCheckError(f"{label} must be an integer in {bound}")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4QueryAInputCheckError(f"{label} must be a lowercase SHA-256")
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
            raise DeepSeekV4QueryAInputCheckError(
                "artifact tree exceeds its depth bound"
            )
        before = _fingerprint(os.fstat(descriptor))
        try:
            names = sorted(os.listdir(descriptor))
        except OSError as exc:
            raise DeepSeekV4QueryAInputCheckError(
                f"cannot enumerate artifact tree: {exc}"
            ) from exc
        for name in names:
            visited += 1
            if visited > _MAX_TREE_ENTRIES:
                raise DeepSeekV4QueryAInputCheckError(
                    "artifact tree exceeds its entry bound"
                )
            if not name or name in {".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4QueryAInputCheckError(
                    "artifact tree contains an unsafe name"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except OSError as exc:
                raise DeepSeekV4QueryAInputCheckError(
                    f"cannot inspect artifact tree entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                child = _open_relative_descriptor(
                    descriptor,
                    name,
                    f"artifact directory {relative!r}",
                    directory=True,
                )
                try:
                    walk(child, relative, depth + 1)
                finally:
                    os.close(child)
            else:
                raise DeepSeekV4QueryAInputCheckError(
                    f"artifact tree entry {relative!r} is not a regular file or directory"
                )
        if _fingerprint(os.fstat(descriptor)) != before:
            raise DeepSeekV4QueryAInputCheckError(
                "artifact tree changed during directory enumeration"
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


def _payload_descriptor(
    value: object,
    spec: _PayloadSpec,
    *,
    batch_size: int,
    sequence_length: int,
    label: str,
) -> tuple[dict[str, Any], str, int]:
    keys = {"dtype", "encoding", "id", "path", "sha256", "shape", "size_bytes"}
    if spec.register is not None:
        keys.add("register")
    descriptor = _exact_keys(value, keys, label)
    digest = _digest(descriptor["sha256"], f"{label}.sha256")
    size_bytes = batch_size * sequence_length * spec.bytes_per_token
    expected: dict[str, Any] = {
        "dtype": spec.dtype,
        "encoding": spec.encoding,
        "id": spec.identifier,
        "path": spec.path,
        "sha256": digest,
        "shape": [batch_size, sequence_length, *spec.shape_suffix],
        "size_bytes": size_bytes,
    }
    if spec.register is not None:
        expected["register"] = spec.register
    if not _strict_equal(descriptor, expected):
        raise DeepSeekV4QueryAInputCheckError(f"{label} metadata differs")
    if math.prod(expected["shape"]) * (2 if spec.dtype == "BF16" else 4) != size_bytes:
        raise DeepSeekV4QueryAInputCheckError(
            f"{label} shape and byte count do not reconcile"
        )
    return descriptor, digest, size_bytes


def _load_hc_result(stack: ExitStack, result_root: Path) -> _HCResult:
    root = _open_root(stack, result_root, "HC_PRE result root")
    manifest_file = _safe_file(
        stack,
        root,
        RESULT_MANIFEST,
        "HC_PRE result manifest",
        maximum_size=_MAX_MANIFEST_BYTES,
    )
    manifest_payload = _read_file(
        manifest_file, "HC_PRE result manifest", _MAX_MANIFEST_BYTES
    )
    result = _strict_json(manifest_payload, "HC_PRE result manifest")
    _exact_keys(
        result,
        {
            "batch_size",
            "build_id",
            "counter_reconciliation",
            "deployment_status",
            "diagnostics",
            "evidence_scope",
            "execution_scope",
            "logical_counters",
            "model_id",
            "numeric_status",
            "outputs",
            "program_sha256",
            "request_sha256",
            "schema",
            "sequence_length",
            "source_application_status",
            "status",
            "token_count",
        },
        "HC_PRE result manifest",
    )
    batch_size = _integer(
        result["batch_size"], "HC_PRE result batch_size", minimum=1, maximum=4
    )
    sequence_length = _integer(
        result["sequence_length"],
        "HC_PRE result sequence_length",
        minimum=1,
        maximum=4,
    )
    token_count = _integer(
        result["token_count"],
        "HC_PRE result token_count",
        minimum=1,
        maximum=_MAX_TOKEN_COUNT,
    )
    build_id = _digest(result["build_id"], "HC_PRE result build_id")
    request_sha256 = _digest(result["request_sha256"], "HC_PRE result request_sha256")
    program_sha256 = _digest(result["program_sha256"], "HC_PRE result program_sha256")
    expected_identity = {
        "counter_reconciliation": "exact",
        "deployment_status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
        ),
        "evidence_scope": "official_checkpoint",
        "execution_scope": "exact_hc_pre_site_only",
        "model_id": MODEL_ID,
        "program_sha256": HC_PRE_PROGRAM_SHA256,
        "schema": HC_RESULT_SCHEMA,
        "source_application_status": (
            "partial_official_transform_application_not_release_evidence"
        ),
        "status": "pass",
    }
    if not _strict_equal(
        {key: result[key] for key in expected_identity}, expected_identity
    ):
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE result schema, status, evidence, or execution scope differs"
        )
    if program_sha256 != HC_PRE_PROGRAM_SHA256:
        raise DeepSeekV4QueryAInputCheckError("HC_PRE result program identity differs")
    if batch_size * sequence_length != token_count:
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE result token_count must equal batch_size * sequence_length"
        )

    numeric = _exact_keys(
        result["numeric_status"],
        {"branch_saturation_count", "poison"},
        "HC_PRE result numeric_status",
    )
    _integer(
        numeric["branch_saturation_count"],
        "HC_PRE result branch_saturation_count",
        maximum=token_count * _HIDDEN_SIZE,
    )
    if type(numeric["poison"]) is not bool or numeric["poison"] is not False:
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE result numeric poison must be exactly false"
        )
    counters = _exact_keys(
        result["logical_counters"], set(_HC_COUNTERS), "HC_PRE logical counters"
    )
    for name in _HC_COUNTERS:
        _integer(counters[name], f"HC_PRE logical counter {name}")

    outputs = result["outputs"]
    if type(outputs) is not list or len(outputs) != len(_OUTPUT_SPECS):
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE result must contain exactly five ordered outputs"
        )
    diagnostics = _exact_keys(
        result["diagnostics"],
        {spec.identifier for spec in _DIAGNOSTIC_SPECS},
        "HC_PRE result diagnostics",
    )
    descriptor_values = list(zip(_OUTPUT_SPECS, outputs, strict=True))
    descriptor_values.extend(
        (spec, diagnostics[spec.identifier]) for spec in _DIAGNOSTIC_SPECS
    )
    guarded: list[_StableFile] = []
    records: list[dict[str, Any]] = []
    selected_payload: bytes | None = None
    selected_sha256 = ""
    selected_path = ""
    for spec, raw_descriptor in descriptor_values:
        descriptor, digest, size_bytes = _payload_descriptor(
            raw_descriptor,
            spec,
            batch_size=batch_size,
            sequence_length=sequence_length,
            label=f"HC_PRE result payload {spec.identifier!r}",
        )
        source = _safe_file(
            stack,
            root,
            descriptor["path"],
            f"HC_PRE result payload {spec.identifier!r}",
            exact_size=size_bytes,
            maximum_size=_MAX_RESULT_FILE_BYTES,
        )
        payload = _read_file(
            source,
            f"HC_PRE result payload {spec.identifier!r}",
            _MAX_RESULT_FILE_BYTES,
        )
        if hashlib.sha256(payload).hexdigest() != digest:
            raise DeepSeekV4QueryAInputCheckError(
                f"HC_PRE result payload {spec.identifier!r} differs from its hash"
            )
        guarded.append(source)
        records.append({"path": spec.path, "sha256": digest, "size_bytes": size_bytes})
        if spec.identifier == "attention_input":
            selected_payload = payload
            selected_sha256 = digest
            selected_path = spec.path
    if (
        selected_payload is None
        or len(selected_payload) != token_count * _HIDDEN_SIZE * 2
    ):
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE ATTENTION_INPUT payload extent differs"
        )

    expected_files = {RESULT_MANIFEST, *(record["path"] for record in records)}
    actual_files, actual_directories = _enumerate_tree(root.descriptor)
    if actual_files != expected_files or actual_directories != _expected_directories(
        expected_files
    ):
        raise DeepSeekV4QueryAInputCheckError(
            "HC_PRE result tree role/path closure differs"
        )
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    records.append(
        {
            "path": RESULT_MANIFEST,
            "sha256": manifest_sha256,
            "size_bytes": len(manifest_payload),
        }
    )
    records.sort(key=lambda record: record["path"])
    return _HCResult(
        root=root,
        manifest_file=manifest_file,
        guarded_files=tuple(guarded),
        manifest_sha256=manifest_sha256,
        build_id=build_id,
        request_sha256=request_sha256,
        batch_size=batch_size,
        sequence_length=sequence_length,
        token_count=token_count,
        input_payload=selected_payload,
        input_sha256=selected_sha256,
        input_path=selected_path,
        tree_sha256=_sha256_json(records),
    )


def _verify_query_a_executable(
    deployment_root: Path,
    application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> dict[str, Any]:
    """Call the independent package verifier without accepting a fallback."""

    try:
        from compiler.checking.deepseek_v4_query_a_executable import (
            verify_deepseek_v4_query_a_executable_deployment,
        )
    except ImportError as exc:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A executable verifier is unavailable"
        ) from exc
    try:
        checked = verify_deepseek_v4_query_a_executable_deployment(
            Path(deployment_root),
            Path(application_root),
            Path(snapshot),
            lock,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeepSeekV4QueryAInputCheckError(
            f"Query-A executable deployment verification failed: {exc}"
        ) from exc
    if type(checked) is not dict:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A executable verifier returned a malformed contract"
        )
    return checked


def _load_query_a_deployment(
    stack: ExitStack,
    deployment_root: Path,
    application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> _QueryADeployment:
    root = _open_root(stack, deployment_root, "Query-A executable deployment root")
    manifest_file = _safe_file(
        stack,
        root,
        DEPLOYMENT_MANIFEST,
        "Query-A executable deployment manifest",
        maximum_size=_MAX_MANIFEST_BYTES,
    )
    manifest_payload = _read_file(
        manifest_file,
        "Query-A executable deployment manifest",
        _MAX_MANIFEST_BYTES,
    )
    manifest = _strict_json(manifest_payload, "Query-A executable deployment manifest")
    checked = _verify_query_a_executable(
        root.path,
        application_root,
        snapshot,
        lock,
    )
    build_id = _digest(manifest.get("build_id"), "Query-A deployment build_id")
    program_sha256 = _digest(
        manifest.get("program_sha256"), "Query-A deployment program_sha256"
    )
    checked_build_id = _digest(
        checked.get("build_id"), "verified Query-A deployment build_id"
    )
    checked_program_sha256 = _digest(
        checked.get("program_sha256"),
        "verified Query-A deployment program_sha256",
    )
    application_id = _digest(
        checked.get("application_id"),
        "verified Query-A canonical application_id",
    )
    verification_id = _digest(
        checked.get("verification_id"),
        "verified Query-A canonical application verification_id",
    )
    if type(lock) is not dict:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A checkpoint lock must be an exact object"
        )
    checkpoint_lock_id = _digest(
        lock.get("lock_id"), "verified Query-A checkpoint lock_id"
    )
    lock_source = lock.get("source")
    if type(lock_source) is not dict:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A checkpoint lock source must be an exact object"
        )
    repository = lock_source.get("repository")
    revision = lock_source.get("revision")
    if type(repository) is not str or not repository:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A checkpoint repository identity is malformed"
        )
    if type(revision) is not str or not revision:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A checkpoint revision identity is malformed"
        )
    verifier_status = checked.get("status")
    if type(verifier_status) is not str or not verifier_status:
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A executable verifier status is malformed"
        )
    if (
        manifest.get("schema") != QUERY_A_EXECUTABLE_SCHEMA
        or manifest.get("model_id") != MODEL_ID
        or build_id != checked_build_id
        or program_sha256 != QUERY_A_PROGRAM_SHA256
        or program_sha256 != checked_program_sha256
    ):
        raise DeepSeekV4QueryAInputCheckError(
            "Query-A executable schema, model, build, or program identity differs"
        )
    return _QueryADeployment(
        root=root,
        manifest_file=manifest_file,
        manifest_sha256=hashlib.sha256(manifest_payload).hexdigest(),
        application_id=application_id,
        build_id=build_id,
        checkpoint_lock_id=checkpoint_lock_id,
        program_sha256=program_sha256,
        repository=repository,
        revision=revision,
        verification_id=verification_id,
        verifier_status=verifier_status,
    )


def _derive_material(
    *,
    hc_result_root: Path,
    executable_deployment_root: Path,
    executable_application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> _CompositionMaterial:
    """Reopen both causal inputs and derive the only acceptable request bytes."""

    _require_secure_file_operations()
    with ExitStack() as stack:
        result = _load_hc_result(stack, hc_result_root)
        executable = _load_query_a_deployment(
            stack,
            executable_deployment_root,
            executable_application_root,
            snapshot,
            lock,
        )

        input_payload = result.input_payload
        input_sha256 = hashlib.sha256(input_payload).hexdigest()
        if input_sha256 != result.input_sha256:
            raise DeepSeekV4QueryAInputCheckError(
                "byte-preserving flatten changed the HC_PRE output hash"
            )
        request_manifest: dict[str, Any] = {
            "build_id": executable.build_id,
            "input": {
                "dtype": "BF16",
                "encoding": "bfloat16_little_endian",
                "id": "attention_input",
                "path": INPUT_RELATIVE,
                "register": "ATTENTION_INPUT",
                "sha256": input_sha256,
                "shape": [result.token_count, _HIDDEN_SIZE],
                "size_bytes": len(input_payload),
            },
            "model_id": MODEL_ID,
            "program_sha256": executable.program_sha256,
            "provenance": {
                "kind": "verified_hc_pre_execution_result",
                "source_batch_size": result.batch_size,
                "source_build_id": result.build_id,
                "source_output_path": result.input_path,
                "source_output_sha256": result.input_sha256,
                "source_request_sha256": result.request_sha256,
                "source_result_manifest_sha256": result.manifest_sha256,
                "source_schema": HC_RESULT_SCHEMA,
                "source_sequence_length": result.sequence_length,
            },
            "schema": REQUEST_SCHEMA,
            "token_count": result.token_count,
        }
        request_payload = canonical_json_bytes(request_manifest)
        request_sha256 = hashlib.sha256(request_payload).hexdigest()
        request_files = [
            {
                "path": INPUT_RELATIVE,
                "sha256": input_sha256,
                "size_bytes": len(input_payload),
            },
            {
                "path": REQUEST_MANIFEST,
                "sha256": request_sha256,
                "size_bytes": len(request_payload),
            },
        ]
        report_body: dict[str, Any] = {
            "claim_boundary": list(CLAIM_BOUNDARY),
            "executable": {
                "application_id": executable.application_id,
                "build_id": executable.build_id,
                "deployment_manifest_sha256": executable.manifest_sha256,
                "program_sha256": executable.program_sha256,
                "schema": QUERY_A_EXECUTABLE_SCHEMA,
                "verification_id": executable.verification_id,
                "verifier_status": executable.verifier_status,
            },
            "flatten": {
                "destination_shape": [result.token_count, _HIDDEN_SIZE],
                "destination_sha256": input_sha256,
                "destination_size_bytes": len(input_payload),
                "operation": "contiguous_token_major_byte_identity",
                "source_sha256": result.input_sha256,
                "source_shape": [
                    result.batch_size,
                    result.sequence_length,
                    _HIDDEN_SIZE,
                ],
                "source_size_bytes": len(input_payload),
                "status": "exact_byte_identity",
            },
            "model_id": MODEL_ID,
            "request": {
                "build_id": executable.build_id,
                "files": request_files,
                "input_sha256": input_sha256,
                "program_sha256": executable.program_sha256,
                "request_sha256": request_sha256,
                "schema": REQUEST_SCHEMA,
                "token_count": result.token_count,
                "tree_sha256": _sha256_json(request_files),
            },
            "schema": COMPOSITION_SCHEMA,
            "source_result": {
                "batch_size": result.batch_size,
                "build_id": result.build_id,
                "evidence_scope": "official_checkpoint",
                "execution_scope": "exact_hc_pre_site_only",
                "output_path": result.input_path,
                "output_sha256": result.input_sha256,
                "program_sha256": HC_PRE_PROGRAM_SHA256,
                "request_sha256": result.request_sha256,
                "result_manifest_sha256": result.manifest_sha256,
                "schema": HC_RESULT_SCHEMA,
                "sequence_length": result.sequence_length,
                "status": "pass",
                "token_count": result.token_count,
                "tree_sha256": result.tree_sha256,
            },
            "status": "verified_hc_pre_attention_input_byte_preserving_composition",
            "verification_dependencies": {
                "application_id": executable.application_id,
                "checkpoint_lock_id": executable.checkpoint_lock_id,
                "dependency_policy": "identity_only_no_checkpoint_payload_copied",
                "repository": executable.repository,
                "revision": executable.revision,
                "verification_id": executable.verification_id,
            },
        }
        report = {**report_body, "composition_id": _sha256_json(report_body)}

        for guarded in (
            result.manifest_file,
            *result.guarded_files,
            executable.manifest_file,
        ):
            _verify_file_stable(
                guarded, f"guarded causal artifact {guarded.relative_path!r}"
            )
        expected_result_files = {
            RESULT_MANIFEST,
            *(spec.path for spec in (*_OUTPUT_SPECS, *_DIAGNOSTIC_SPECS)),
        }
        actual_result_files, actual_result_directories = _enumerate_tree(
            result.root.descriptor
        )
        if (
            actual_result_files != expected_result_files
            or actual_result_directories != _expected_directories(expected_result_files)
        ):
            raise DeepSeekV4QueryAInputCheckError(
                "HC_PRE result tree changed after causal verification"
            )
        _verify_root_stable(result.root, "HC_PRE result root")
        _verify_root_stable(executable.root, "Query-A executable deployment root")
        return _CompositionMaterial(input_payload, request_manifest, report)


def verify_deepseek_v4_query_a_input_composition(
    *,
    hc_result_root: Path,
    executable_deployment_root: Path,
    executable_application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
    request_root: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Recompute provenance and verify a closed two-file Query-A request."""

    material = _derive_material(
        hc_result_root=hc_result_root,
        executable_deployment_root=executable_deployment_root,
        executable_application_root=executable_application_root,
        snapshot=snapshot,
        lock=lock,
    )
    with ExitStack() as stack:
        root = _open_root(stack, request_root, "Query-A request root")
        manifest_payload = canonical_json_bytes(material.request_manifest)
        manifest_file = _safe_file(
            stack,
            root,
            REQUEST_MANIFEST,
            "Query-A request manifest",
            exact_size=len(manifest_payload),
        )
        input_file = _safe_file(
            stack,
            root,
            INPUT_RELATIVE,
            "Query-A request input",
            exact_size=len(material.input_payload),
        )
        report_parent, report_file = _direct_file(
            stack,
            report_path,
            "Query-A composition report",
            maximum_size=_MAX_JSON_BYTES,
        )
        observed_manifest_payload = _read_file(
            manifest_file, "Query-A request manifest", _MAX_MANIFEST_BYTES
        )
        observed_input = _read_file(
            input_file, "Query-A request input", _MAX_INPUT_BYTES
        )
        observed_report_payload = _read_file(
            report_file, "Query-A composition report", _MAX_JSON_BYTES
        )
        observed_manifest = _strict_json(
            observed_manifest_payload, "Query-A request manifest"
        )
        observed_report = _strict_json(
            observed_report_payload, "Query-A composition report"
        )
        if not _strict_equal(observed_manifest, material.request_manifest):
            raise DeepSeekV4QueryAInputCheckError(
                "Query-A request manifest differs from causal composition"
            )
        if observed_input != material.input_payload:
            raise DeepSeekV4QueryAInputCheckError(
                "Query-A input differs from the verified HC_PRE ATTENTION_INPUT bytes"
            )
        if not _strict_equal(observed_report, material.report):
            raise DeepSeekV4QueryAInputCheckError(
                "Query-A composition report differs from causal composition"
            )
        actual_files, actual_directories = _enumerate_tree(root.descriptor)
        expected_files = {REQUEST_MANIFEST, INPUT_RELATIVE}
        if actual_files != expected_files or actual_directories != {"input"}:
            raise DeepSeekV4QueryAInputCheckError(
                "Query-A request must be a closed two-file tree"
            )
        for guarded, label in (
            (manifest_file, "Query-A request manifest"),
            (input_file, "Query-A request input"),
            (report_file, "Query-A composition report"),
        ):
            _verify_file_stable(guarded, label)
        _verify_root_stable(root, "Query-A request root")
        _verify_root_stable(report_parent, "Query-A composition report parent")
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
    "DEPLOYMENT_MANIFEST",
    "HC_PRE_PROGRAM_SHA256",
    "HC_RESULT_SCHEMA",
    "INPUT_RELATIVE",
    "QUERY_A_EXECUTABLE_SCHEMA",
    "QUERY_A_PROGRAM_SHA256",
    "REQUEST_MANIFEST",
    "REQUEST_SCHEMA",
    "RESULT_MANIFEST",
    "DeepSeekV4QueryAInputCheckError",
    "verify_deepseek_v4_query_a_input_composition",
]
