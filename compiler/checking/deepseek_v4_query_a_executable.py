"""Independent verifier for the official DeepSeek V4 Query-A package.

This checker deliberately does not import the executable-package builder.  It
replays the selected canonical application against the pinned checkpoint,
checks all four rank replicas, reconstructs every packaged contract, and
requires one closed regular-file tree.  Passing verification proves package
identity and compiler/runtime interface closure only.  It is not execution,
numeric-result, cycle, physical-schedule, PPA, or NVIDIA-comparison evidence.
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
import struct
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME as APPLICATION_MANIFEST,
    VERIFICATION_FILENAME as APPLICATION_VERIFICATION,
    DeepSeekV4ApplicationCheckError,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_query_a_schedule import (
    DeepSeekV4QueryAScheduleCheckError,
    verify_deepseek_v4_query_a_logical_schedule,
    verify_deepseek_v4_query_a_logical_schedule_certificate,
)
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_query_a import (
    DeepSeekV4QueryAMicrocodeError,
    assemble,
    build_program_contract,
    decode,
    disassemble,
    encode,
    exhaustive_row_payload,
    verify,
    verify_program_contract,
)
from runtime.service_engine.query_a_numeric import (
    QueryAServiceNumericError,
    query_a_functional_counters,
)


EXECUTABLE_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_query_a_executable.v1"
EXECUTABLE_STATUS = "official_checkpoint_program_packaged_execution_not_evidenced"
EXECUTION_REQUEST_SCHEMA = "opentallas.deepseek_v4_query_a_execution_request.v1"
EXECUTION_RESULT_SCHEMA = "opentallas.deepseek_v4_query_a_execution_result.v1"
RESOURCE_MANIFEST_SCHEMA = "opentallas.deepseek_v4_query_a_resources.v1"
COUNTER_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_query_a_functional_counter_contract.v1"
)
EXECUTION_COVERAGE_SCHEMA = "opentallas.deepseek_v4_query_a_executable_coverage.v1"
COMPILER_NAME = "opentallas-deepseek-v4-query-a-executable-packager"
COMPILER_VERSION = "0.1.0"
DEPLOYMENT_MANIFEST = "deployment_manifest.json"

PROGRAM_BYTES = 196
PROGRAM_SHA256 = "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
PROGRAM_CONTRACT_ID = "0aa1969479c527d33fa893557f40dd05e3efbc9a3e1af7d959d4cb8496806903"
PROGRAM_CONTRACT_SHA256 = (
    "a8f0d21f1b1daa01a5acfcac8f05a1b74e71988af195ecb58fd85e3a13127a02"
)
PROGRAM_DISASSEMBLY_SHA256 = (
    "8bb73c0d445e315ef76e94ba99f37e32b4185943463583c71c825c1ff79c7cb1"
)
LOGICAL_SCHEDULE_ID = "2673d8ef4e62df0ec1441c1b14eeb6a207b246a70a987adadfe354a418711e13"
LOGICAL_SCHEDULE_SHA256 = (
    "1f2237dfdb6ecb5766678ad960a34ff09d441676a1f20b39c3248e243d3b7c08"
)
LOGICAL_CERTIFICATE_ID = (
    "d2a6e754abc7440dc341e00fac4bf7e48f9e53659f971fdfbb03c4782c47b546"
)
LOGICAL_CERTIFICATE_SHA256 = (
    "a5ccf12b531fbad2a9ec86a81b63cb5f4898c2298503c42fe384f6bf47b30404"
)

NORM_NAME = "layers.0.attn_norm.weight"
WEIGHT_NAME = "layers.0.attn.wq_a.weight"
SCALE_NAME = "layers.0.attn.wq_a.scale"
OFFICIAL_RESOURCES: dict[str, dict[str, Any]] = {
    NORM_NAME: {
        "dtype": "BF16",
        "encoding": "bfloat16_little_endian",
        "logical_dtype": "BF16",
        "path": "resources/attn_norm_weight.bf16le",
        "resource_id": 7,
        "resource_name": "ATTN_NORM_WEIGHT",
        "role": "block.attention_norm.weight",
        "sha256": ("2628db36b6aa28c06121bb01f2d8e0f6acf9d240393af7a91ae5073b0acb5772"),
        "shape": [4096],
        "size_bytes": 8192,
    },
    WEIGHT_NAME: {
        "dtype": "F8_E4M3",
        "encoding": "float8_e4m3fn_bytes",
        "logical_dtype": "FP8_E4M3FN",
        "path": "resources/query_a_weight.f8e4m3fn",
        "resource_id": 8,
        "resource_name": "QUERY_A_WEIGHT",
        "role": "attention.query_a.weight",
        "sha256": ("d8646783efb3c0bda83bcd2c64b03cb25d1677d27b0c45ffe143a4175922932c"),
        "shape": [1024, 4096],
        "size_bytes": 4_194_304,
    },
    SCALE_NAME: {
        "dtype": "F8_E8M0",
        "encoding": "unsigned_e8m0_bytes",
        "logical_dtype": "UE8M0_SCALE",
        "path": "resources/query_a_scale.e8m0",
        "resource_id": 9,
        "resource_name": "QUERY_A_SCALE",
        "role": "attention.query_a.scale",
        "sha256": ("aea19c77d256ca30999de59a811b152a2dfc82673a43877d9cd67b80578bc5e2"),
        "shape": [8, 32],
        "size_bytes": 256,
    },
}
ROWS_PATH = "resources/query_a_exhaustive_rows.u32le"
ROWS_SHA256 = "c89db7222126863309183fc023c7091fb18392d16a397dac76a96a022cd62cef"

CLAIM_BOUNDARY = [
    (
        "Packages the exact weighted RMS_NORM, exhaustive 1,024-row Query-A "
        "FP8_LINEAR, and terminal COMPLETE program with all three official "
        "checkpoint resources and one generated exhaustive-row constant."
    ),
    "Program and artifact-only runtime interfaces packaged; execution not evidenced.",
    (
        "Contains no activation, expected output, embedded result, callback, "
        "fallback arithmetic, runtime execution, or execution-success claim."
    ),
    (
        "Logical counters are source-visible functional work, not cycles, "
        "latency, bandwidth, throughput, energy, area, density, routing, or PPA."
    ),
    (
        "No package field establishes full attention, a transformer block, "
        "complete-model execution, or superiority over NVIDIA hardware."
    ),
]

ENTRYPOINT = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "functional_counter_contract": "interfaces/functional_counter_contract.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "program": "program/query_a.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/query_a.disassembly.txt",
    "resource_manifest": "resources/resource_manifest.json",
}

_FIXED_PATH_BY_ROLE = {
    "attention_norm_weight": "resources/attn_norm_weight.bf16le",
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "exhaustive_output_rows": ROWS_PATH,
    "functional_counter_contract": "interfaces/functional_counter_contract.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "microcode_disassembly": "program/query_a.disassembly.txt",
    "microcode_program": "program/query_a.bin",
    "program_contract": "program/program_contract.json",
    "query_a_scale": "resources/query_a_scale.e8m0",
    "query_a_weight": "resources/query_a_weight.f8e4m3fn",
    "resource_manifest": "resources/resource_manifest.json",
}
_EXPECTED_ROLES = frozenset(_FIXED_PATH_BY_ROLE)
_EXACT_SIZE_BY_ROLE = {
    "attention_norm_weight": 8_192,
    "exhaustive_output_rows": 4_096,
    "microcode_disassembly": 639,
    "microcode_program": PROGRAM_BYTES,
    "program_contract": 1_318,
    "query_a_scale": 256,
    "query_a_weight": 4_194_304,
}
_MAX_JSON_BYTES = 512 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_TREE_ENTRIES = 32
_MAX_TREE_DEPTH = 4
_READ_CHUNK_BYTES = 1024 * 1024
_EXPECTED_DIRECTORIES = {"interfaces", "program", "resources", "schedule"}
_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_ID_ROOT = (
    "https://opentallas.org/schemas/compiler/deepseek_v4_query_a_executable"
)
_SHA256_PATTERN = "^[0-9a-f]{64}$"


class DeepSeekV4QueryAExecutableCheckError(RuntimeError):
    """Raised when an official Query-A executable package fails closed."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


@dataclass(frozen=True)
class _StableDirectory:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int


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
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            "platform lacks race-resistant bounded checker file operations"
        )


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not canonical POSIX")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} is not a lowercase SHA-256"
        )
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _canonical_equal(left: object, right: object) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (RecursionError, TypeError, ValueError):
        return False


def _open_root(
    stack: ExitStack,
    root: Path,
    label: str,
) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


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
    current_descriptor = os.dup(root_descriptor)
    try:
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = directory_flags if not final or directory else file_flags
            next_descriptor = os.open(part, flags, dir_fd=current_descriptor)
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        return current_descriptor
    except OSError as exc:
        os.close(current_descriptor)
        raise DeepSeekV4QueryAExecutableCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _safe_file(
    stack: ExitStack,
    root_descriptor: int,
    value: object,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    relative = _safe_relative(value, label)
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        label,
        directory=False,
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor=descriptor,
        fingerprint=_fingerprint(metadata),
        relative_path=relative,
        root_descriptor=root_descriptor,
        size_bytes=metadata.st_size,
    )


def _safe_directory(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    label: str,
) -> _StableDirectory:
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        label,
        directory=True,
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not a directory")
    return _StableDirectory(
        descriptor=descriptor,
        fingerprint=_fingerprint(metadata),
        relative_path=relative,
        root_descriptor=root_descriptor,
    )


def _verify_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} changed while the checker read it"
        )
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
        directory=False,
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"{label} was replaced while the checker read it"
            )
    finally:
        os.close(current_descriptor)


def _verify_directory_stable(source: _StableDirectory, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} changed during verification"
        )
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
        directory=True,
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISDIR(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _verify_root_stable(
    root: Path,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} changed during verification"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _descriptor_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} exceeds its {maximum}-byte bound"
        )
    payload = bytearray()
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"cannot read {label}: {exc}"
            ) from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} ended while it was read")
    _verify_stable(source, label)
    return bytes(payload)


def _sha256_file(source: _StableFile, label: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"cannot hash {label}: {exc}"
            ) from exc
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
    if offset != source.size_bytes:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} ended while it was hashed")
    _verify_stable(source, label)
    return digest.hexdigest(), offset


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> object:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} has non-finite JSON number {token!r}"
        )

    def bounded_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"{label} has non-finite JSON number {token!r}"
            )
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_float=bounded_float,
        )
    except DeepSeekV4QueryAExecutableCheckError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        ValueError,
    ) as exc:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if type(value) is not dict:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not a JSON object")
    try:
        canonical = canonical_json_bytes(value)
    except (RecursionError, TypeError, ValueError) as exc:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"cannot canonicalize {label}: {exc}"
        ) from exc
    if canonical != payload:
        raise DeepSeekV4QueryAExecutableCheckError(f"{label} is not canonical JSON")
    return value


def _json_from_file(
    source: _StableFile,
    label: str,
    *,
    maximum: int = _MAX_JSON_BYTES,
) -> dict[str, Any]:
    return _strict_json_payload(_descriptor_bytes(source, label, maximum), label)


def _artifact_record(path: str, role: str, source: _StableFile) -> dict[str, Any]:
    digest, size = _sha256_file(source, f"Query-A artifact {path!r}")
    return {"path": path, "role": role, "sha256": digest, "size_bytes": size}


def _validate_encoding(source: _StableFile, dtype: str, label: str) -> None:
    offset = 0
    carry = b""
    while offset < source.size_bytes:
        chunk = os.pread(
            source.descriptor,
            min(_READ_CHUNK_BYTES, source.size_bytes - offset),
            offset,
        )
        if not chunk:
            break
        offset += len(chunk)
        if dtype == "BF16":
            combined = carry + chunk
            even = len(combined) & ~1
            for element_offset in range(0, even, 2):
                code = combined[element_offset] | (combined[element_offset + 1] << 8)
                if code & 0x7F80 == 0x7F80:
                    raise DeepSeekV4QueryAExecutableCheckError(
                        f"{label} contains non-finite BF16 code 0x{code:04x}"
                    )
            carry = combined[even:]
        elif dtype == "F8_E4M3":
            if any(code in {0x7F, 0xFF} for code in chunk):
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"{label} contains a reserved FP8 E4M3 code"
                )
        elif dtype == "F8_E8M0":
            if 0xFF in chunk:
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"{label} contains a reserved E8M0 code"
                )
        else:  # pragma: no cover - closed caller set
            raise DeepSeekV4QueryAExecutableCheckError(
                f"{label} has unsupported validation dtype {dtype!r}"
            )
    if offset != source.size_bytes or carry:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"{label} ended during encoding validation"
        )
    _verify_stable(source, label)


def _assignment_paths(name: str) -> list[str]:
    return [f"ranks/rank-{rank:03d}/{name}.bin" for rank in range(4)]


def _validate_application(
    application: dict[str, Any],
    retained: dict[str, Any],
    replay: dict[str, Any],
    lock: dict[str, Any],
) -> tuple[str, str, dict[str, list[dict[str, Any]]]]:
    _exact_keys(
        application,
        {
            "application_id",
            "assignments",
            "coverage",
            "evidence_scope",
            "inputs",
            "plan",
            "schema",
            "selection",
            "source",
            "status",
        },
        "canonical Query-A application",
    )
    if not _canonical_equal(retained, replay):
        raise DeepSeekV4QueryAExecutableCheckError(
            "retained canonical verification differs from independent replay"
        )
    if (
        application.get("schema") != "opentallas.canonical_application.v1"
        or application.get("evidence_scope") != "official_checkpoint"
        or application.get("status")
        != "partial_official_transform_application_not_release_evidence"
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A application is not a partial official application"
        )
    source = _exact_keys(
        application.get("source"),
        {"checkpoint_lock_id", "repository", "revision"},
        "canonical Query-A source",
    )
    lock_id = _digest(lock.get("lock_id"), "checkpoint lock_id")
    if source != {
        "checkpoint_lock_id": lock_id,
        "repository": REPOSITORY,
        "revision": REVISION,
    }:
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A source is not the pinned official release"
        )
    requested = sorted(OFFICIAL_RESOURCES)
    selection = _exact_keys(
        application.get("selection"),
        {"complete_plan", "dependency_input_names", "requested_input_names"},
        "canonical Query-A selection",
    )
    if not _canonical_equal(
        selection,
        {
            "complete_plan": False,
            "dependency_input_names": [],
            "requested_input_names": requested,
        },
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A selection differs from the exact three tensors"
        )

    inputs = application.get("inputs")
    if type(inputs) is not list or len(inputs) != 3:
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A application must declare exactly three inputs"
        )
    by_input: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(inputs):
        record = _exact_keys(
            raw,
            {
                "action",
                "logical_dtype",
                "name",
                "payload_sha256",
                "shape",
                "size_bytes",
                "storage_dtype",
            },
            f"canonical Query-A inputs[{index}]",
        )
        name = record.get("name")
        if type(name) is not str or name in by_input or name not in OFFICIAL_RESOURCES:
            raise DeepSeekV4QueryAExecutableCheckError(
                "canonical Query-A input identity differs"
            )
        spec = OFFICIAL_RESOURCES[name]
        if not _canonical_equal(
            record,
            {
                "action": "replicate_identity",
                "logical_dtype": spec["logical_dtype"],
                "name": name,
                "payload_sha256": spec["sha256"],
                "shape": spec["shape"],
                "size_bytes": spec["size_bytes"],
                "storage_dtype": spec["dtype"],
            },
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"canonical Query-A input {name!r} differs from official bytes"
            )
        by_input[name] = record
    if list(by_input) != requested:
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A inputs are not in exact canonical order"
        )

    assignments = application.get("assignments")
    if type(assignments) is not list or len(assignments) != 12:
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A application must contain twelve rank assignments"
        )
    by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in requested}
    for index, raw in enumerate(assignments):
        record = _exact_keys(
            raw,
            {
                "logical_dtype",
                "name",
                "path",
                "payload_bytes",
                "rank",
                "scale_source",
                "sha256",
                "shape",
                "source",
                "storage_dtype",
                "transform",
            },
            f"canonical Query-A assignments[{index}]",
        )
        name = record.get("name")
        if type(name) is not str or name not in OFFICIAL_RESOURCES:
            raise DeepSeekV4QueryAExecutableCheckError(
                "canonical Query-A assignment has an unknown tensor"
            )
        spec = OFFICIAL_RESOURCES[name]
        rank = _integer(record.get("rank"), "canonical assignment rank")
        expected_path = f"ranks/rank-{rank:03d}/{name}.bin"
        expected_source = {
            "name": name,
            "payload_sha256": spec["sha256"],
            "shape": spec["shape"],
            "slice": None,
            "storage_dtype": spec["dtype"],
        }
        expected_record = {
            "logical_dtype": spec["logical_dtype"],
            "name": name,
            "path": expected_path,
            "payload_bytes": spec["size_bytes"],
            "rank": rank,
            "scale_source": None,
            "sha256": spec["sha256"],
            "shape": spec["shape"],
            "source": expected_source,
            "storage_dtype": spec["dtype"],
            "transform": "identity",
        }
        if not _canonical_equal(record, expected_record):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"canonical Query-A assignment {index} is not an exact replica"
            )
        by_name[name].append(record)
    for name in requested:
        records = by_name[name]
        if [record["rank"] for record in records] != [0, 1, 2, 3] or [
            record["path"] for record in records
        ] != _assignment_paths(name):
            raise DeepSeekV4QueryAExecutableCheckError(
                f"canonical Query-A tensor {name!r} lacks four ordered replicas"
            )

    application_id = _digest(application.get("application_id"), "application_id")
    verification_id = _digest(replay.get("verification_id"), "verification_id")
    if (
        replay.get("application_id") != application_id
        or replay.get("checkpoint_lock_id") != lock_id
        or replay.get("status") != "full_assignment_match"
        or replay.get("schema") != "opentallas.canonical_application_check.v1"
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A replay identity or status differs"
        )
    coverage = replay.get("coverage")
    if type(coverage) is not dict or not _canonical_equal(
        coverage,
        {
            "checked_assignment_count": 12,
            "checked_input_count": 3,
            "checked_output_bytes": 4
            * sum(spec["size_bytes"] for spec in OFFICIAL_RESOURCES.values()),
        },
    ):
        raise DeepSeekV4QueryAExecutableCheckError(
            "canonical Query-A replay coverage differs"
        )
    return application_id, verification_id, by_name


def _shape_schema(width: int | None) -> dict[str, Any]:
    suffix = [] if width is None else [{"const": width}]
    return {
        "items": False,
        "maxItems": 1 + len(suffix),
        "minItems": 1 + len(suffix),
        "prefixItems": [
            {"maximum": 4, "minimum": 1, "type": "integer"},
            *suffix,
        ],
        "type": "array",
    }


def _descriptor_schema(
    *,
    identifier: str,
    register: str | None,
    dtype: str,
    encoding: str,
    width: int | None,
    path: str,
    element_bytes: int,
) -> dict[str, Any]:
    elements_per_token = 1 if width is None else width
    properties: dict[str, Any] = {
        "dtype": {"const": dtype},
        "encoding": {"const": encoding},
        "id": {"const": identifier},
        "path": {"const": path},
        "sha256": {"$ref": "#/$defs/sha256"},
        "shape": _shape_schema(width),
        "size_bytes": {
            "maximum": 4 * elements_per_token * element_bytes,
            "minimum": elements_per_token * element_bytes,
            "multipleOf": elements_per_token * element_bytes,
            "type": "integer",
        },
    }
    required = ["dtype", "encoding", "id", "path", "sha256", "shape", "size_bytes"]
    if register is not None:
        properties["register"] = {"const": register}
        required.insert(4, "register")
    return {
        "additionalProperties": False,
        "properties": properties,
        "required": required,
        "type": "object",
    }


def _expected_request_schema() -> dict[str, Any]:
    return {
        "$comment": (
            "Runtime validation additionally requires input.shape[0] == token_count, "
            "input.size_bytes == token_count*8192, source_batch_size*"
            "source_sequence_length == token_count, and source_output_sha256 == "
            "input.sha256."
        ),
        "$defs": {
            "inputDescriptor": _descriptor_schema(
                identifier="attention_input",
                register="ATTENTION_INPUT",
                dtype="BF16",
                encoding="bfloat16_little_endian",
                width=4096,
                path="input/attention_input.bf16le",
                element_bytes=2,
            ),
            "provenance": {
                "additionalProperties": False,
                "properties": {
                    "kind": {"const": "verified_hc_pre_execution_result"},
                    "source_batch_size": {
                        "maximum": 4,
                        "minimum": 1,
                        "type": "integer",
                    },
                    "source_build_id": {"$ref": "#/$defs/sha256"},
                    "source_output_path": {"const": "outputs/attention_input.bf16le"},
                    "source_output_sha256": {"$ref": "#/$defs/sha256"},
                    "source_request_sha256": {"$ref": "#/$defs/sha256"},
                    "source_result_manifest_sha256": {"$ref": "#/$defs/sha256"},
                    "source_schema": {
                        "const": "opentallas.deepseek_v4_hc_pre_execution_result.v1"
                    },
                    "source_sequence_length": {
                        "maximum": 4,
                        "minimum": 1,
                        "type": "integer",
                    },
                },
                "required": [
                    "kind",
                    "source_batch_size",
                    "source_build_id",
                    "source_output_path",
                    "source_output_sha256",
                    "source_request_sha256",
                    "source_result_manifest_sha256",
                    "source_schema",
                    "source_sequence_length",
                ],
                "type": "object",
            },
            "sha256": {"pattern": _SHA256_PATTERN, "type": "string"},
        },
        "$id": f"{_SCHEMA_ID_ROOT}/execution_request_v1.schema.json",
        "$schema": _DRAFT_2020_12,
        "additionalProperties": False,
        "properties": {
            "build_id": {"$ref": "#/$defs/sha256"},
            "input": {"$ref": "#/$defs/inputDescriptor"},
            "model_id": {"const": MODEL_ID},
            "program_sha256": {"const": PROGRAM_SHA256},
            "provenance": {"$ref": "#/$defs/provenance"},
            "schema": {"const": EXECUTION_REQUEST_SCHEMA},
            "token_count": {"maximum": 4, "minimum": 1, "type": "integer"},
        },
        "required": [
            "build_id",
            "input",
            "model_id",
            "program_sha256",
            "provenance",
            "schema",
            "token_count",
        ],
        "title": "OpenTallas DeepSeek V4 Query-A execution request v1",
        "type": "object",
    }


_PER_TOKEN_COUNTERS = {
    "activation_blocks_quantized": 32,
    "activation_values_quantized": 4096,
    "bf16_attention_input_values_read": 4096,
    "bf16_normalized_values_written": 4096,
    "bf16_query_a_values_written": 1024,
    "binary32_epsilon_adds": 1,
    "binary32_fp8_block_reduction_adds": 31_744,
    "binary32_fp8_product_accumulates": 4_194_304,
    "binary32_rms_divides": 1,
    "binary32_rms_normalization_multiplies": 4096,
    "binary32_rms_reduction_adds": 4095,
    "binary32_rms_square_multiplies": 4096,
    "binary32_rms_weight_multiplies": 4096,
    "binary32_rsqrt_evaluations": 1,
    "logical_attention_input_bytes_read": 8192,
    "logical_normalized_bytes_written": 8192,
    "logical_query_a_bytes_written": 2048,
    "logical_query_parameter_bytes_read": 4_227_072,
    "logical_rms_weight_bytes_read": 8192,
    "matrix_block_dots": 32_768,
}
_FIXED_COUNTERS = {
    "complete_events": 1,
    "micro_ops_executed": 3,
    "semantic_operators_executed": 2,
}


def _expected_counter_contract() -> dict[str, Any]:
    body = {
        "claim_boundary": (
            "Exact shape-derived functional work for RMS_NORM, exhaustive Query-A "
            "FP8_LINEAR, and COMPLETE; these counters are not hardware cycles, "
            "transactions, latency, throughput, energy, area, routing, or PPA."
        ),
        "fixed_counters": dict(_FIXED_COUNTERS),
        "implementation": (
            "runtime.service_engine.query_a_numeric.query_a_functional_counters"
        ),
        "model_id": MODEL_ID,
        "per_token_coefficients": dict(_PER_TOKEN_COUNTERS),
        "reconciliation": (
            "per-token counters equal coefficient*token_count; fixed counters equal "
            "their literal values"
        ),
        "schema": COUNTER_CONTRACT_SCHEMA,
        "token_count_maximum": 4,
        "token_count_minimum": 1,
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def _expected_result_schema() -> dict[str, Any]:
    counter_names = sorted({*_PER_TOKEN_COUNTERS, *_FIXED_COUNTERS})
    definitions: dict[str, Any] = {
        "attentionNormalized": _descriptor_schema(
            identifier="attention_normalized",
            register="ATTENTION_NORMALIZED",
            dtype="BF16",
            encoding="bfloat16_little_endian",
            width=4096,
            path="outputs/attention_normalized.bf16le",
            element_bytes=2,
        ),
        "inverseRms": _descriptor_schema(
            identifier="rms_inverse",
            register=None,
            dtype="F32",
            encoding="ieee754_binary32_little_endian",
            width=None,
            path="diagnostics/rms_inverse.f32le",
            element_bytes=4,
        ),
        "logicalCounters": {
            "additionalProperties": False,
            "properties": {
                name: {"minimum": 0, "type": "integer"} for name in counter_names
            },
            "required": counter_names,
            "type": "object",
        },
        "meanSquare": _descriptor_schema(
            identifier="rms_mean",
            register=None,
            dtype="F32",
            encoding="ieee754_binary32_little_endian",
            width=None,
            path="diagnostics/rms_mean.f32le",
            element_bytes=4,
        ),
        "numericStatus": {
            "additionalProperties": False,
            "properties": {
                "activation_saturated_block_count": {
                    "maximum": 128,
                    "minimum": 0,
                    "type": "integer",
                },
                "poison": {"const": False},
                "query_output_saturated_element_count": {
                    "maximum": 4096,
                    "minimum": 0,
                    "type": "integer",
                },
                "rms_output_saturation_count": {
                    "maximum": 16_384,
                    "minimum": 0,
                    "type": "integer",
                },
            },
            "required": [
                "activation_saturated_block_count",
                "poison",
                "query_output_saturated_element_count",
                "rms_output_saturation_count",
            ],
            "type": "object",
        },
        "queryA": _descriptor_schema(
            identifier="query_a",
            register="QUERY_A",
            dtype="BF16",
            encoding="bfloat16_little_endian",
            width=1024,
            path="outputs/query_a.bf16le",
            element_bytes=2,
        ),
        "sha256": {"pattern": _SHA256_PATTERN, "type": "string"},
    }
    return {
        "$comment": (
            "Runtime validation additionally requires every descriptor token axis "
            "to equal token_count, exact size/shape multiplication, and logical "
            "counters to equal the packaged functional-counter contract."
        ),
        "$defs": definitions,
        "$id": f"{_SCHEMA_ID_ROOT}/execution_result_v1.schema.json",
        "$schema": _DRAFT_2020_12,
        "additionalProperties": False,
        "properties": {
            "build_id": {"$ref": "#/$defs/sha256"},
            "counter_reconciliation": {"const": "exact"},
            "diagnostics": {
                "additionalProperties": False,
                "properties": {
                    "rms_inverse": {"$ref": "#/$defs/inverseRms"},
                    "rms_mean": {"$ref": "#/$defs/meanSquare"},
                },
                "required": ["rms_inverse", "rms_mean"],
                "type": "object",
            },
            "execution_scope": {"const": "exact_complete_query_a_fragment"},
            "logical_counters": {"$ref": "#/$defs/logicalCounters"},
            "model_id": {"const": MODEL_ID},
            "numeric_status": {"$ref": "#/$defs/numericStatus"},
            "outputs": {
                "items": False,
                "maxItems": 2,
                "minItems": 2,
                "prefixItems": [
                    {"$ref": "#/$defs/attentionNormalized"},
                    {"$ref": "#/$defs/queryA"},
                ],
                "type": "array",
            },
            "program_sha256": {"const": PROGRAM_SHA256},
            "request_sha256": {"$ref": "#/$defs/sha256"},
            "schema": {"const": EXECUTION_RESULT_SCHEMA},
            "status": {"const": "pass"},
            "token_count": {"maximum": 4, "minimum": 1, "type": "integer"},
        },
        "required": [
            "build_id",
            "counter_reconciliation",
            "diagnostics",
            "execution_scope",
            "logical_counters",
            "model_id",
            "numeric_status",
            "outputs",
            "program_sha256",
            "request_sha256",
            "schema",
            "status",
            "token_count",
        ],
        "title": "OpenTallas DeepSeek V4 Query-A execution result v1",
        "type": "object",
    }


def _expected_execution_coverage() -> dict[str, Any]:
    return {
        "execution_evidence": "none",
        "functional_counter_contract": COUNTER_CONTRACT_SCHEMA,
        "model_id": MODEL_ID,
        "parameter_coverage": "three_exact_official_resources_plus_generated_rows",
        "physical_schedule_evidence": "none",
        "ppa_evidence": "none",
        "program_execution_authority": "complete",
        "program_scope": "weighted_rms_norm_exhaustive_query_a_fp8_linear_complete",
        "request_schema": EXECUTION_REQUEST_SCHEMA,
        "result_schema": EXECUTION_RESULT_SCHEMA,
        "schedule_coverage": "exact_three_slot_logical_schedule_with_certificate",
        "schema": EXECUTION_COVERAGE_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "status": "program_authority_complete_execution_evidence_none",
    }


def _expected_resource_manifest(
    *,
    application_id: str,
    verification_id: str,
    checkpoint_lock_id: str,
) -> dict[str, Any]:
    resources: list[dict[str, Any]] = []
    for name in (NORM_NAME, WEIGHT_NAME, SCALE_NAME):
        spec = OFFICIAL_RESOURCES[name]
        resources.append(
            {
                "checkpoint_derived": True,
                "dtype": spec["dtype"],
                "encoding": spec["encoding"],
                "path": spec["path"],
                "replicated_ranks": [0, 1, 2, 3],
                "resource_id": spec["resource_id"],
                "resource_name": spec["resource_name"],
                "role": spec["role"],
                "sha256": spec["sha256"],
                "shape": spec["shape"],
                "size_bytes": spec["size_bytes"],
                "source_assignment_paths": _assignment_paths(name),
                "source_tensor_name": name,
            }
        )
    resources.append(
        {
            "checkpoint_derived": False,
            "dtype": "U32",
            "encoding": "unsigned_integer32_little_endian",
            "generator": {
                "kind": "contiguous_u32_range",
                "start_inclusive": 0,
                "stop_exclusive": 1024,
            },
            "path": ROWS_PATH,
            "replicated_ranks": [],
            "resource_id": 10,
            "resource_name": "QUERY_A_EXHAUSTIVE_ROWS",
            "role": "attention.query_a.exhaustive_output_rows",
            "sha256": ROWS_SHA256,
            "shape": [1024],
            "size_bytes": 4096,
            "source_assignment_paths": [],
            "source_tensor_name": None,
        }
    )
    body = {
        "checkpoint_lock_id": checkpoint_lock_id,
        "model_id": MODEL_ID,
        "resources": resources,
        "schema": RESOURCE_MANIFEST_SCHEMA,
        "source_application_id": application_id,
        "source_verification_id": verification_id,
        "tensor_contract": {
            "maximum_token_count": 4,
            "minimum_token_count": 1,
            "registers": [
                {
                    "dtype": "BF16",
                    "encoding": "bfloat16_little_endian",
                    "evidence_observable": True,
                    "live_at_complete": False,
                    "register_id": 3,
                    "register_name": "ATTENTION_INPUT",
                    "shape": ["token_count", 4096],
                    "storage": "request_input",
                },
                {
                    "dtype": "BF16",
                    "encoding": "bfloat16_little_endian",
                    "evidence_observable": True,
                    "live_at_complete": False,
                    "register_id": 8,
                    "register_name": "ATTENTION_NORMALIZED",
                    "shape": ["token_count", 4096],
                    "storage": "persisted_result",
                },
                {
                    "dtype": "BF16",
                    "encoding": "bfloat16_little_endian",
                    "evidence_observable": True,
                    "live_at_complete": True,
                    "register_id": 9,
                    "register_name": "QUERY_A",
                    "shape": ["token_count", 1024],
                    "storage": "persisted_result",
                },
            ],
        },
    }
    return {
        **body,
        "manifest_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited_entries = 0

    def walk(directory_descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited_entries
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A executable directory depth exceeds its bound"
            )
        before = _fingerprint(os.fstat(directory_descriptor))
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"cannot enumerate Query-A executable package: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > _MAX_TREE_ENTRIES:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A executable entry count exceeds its bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4QueryAExecutableCheckError(
                    "Query-A executable contains an unsafe directory entry"
                )
            relative = f"{prefix}/{name}" if prefix else name
            metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory_descriptor,
                )
                try:
                    walk(child, relative, depth + 1)
                finally:
                    os.close(child)
            else:
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"Query-A executable entry {relative!r} is not regular"
                )
        if _fingerprint(os.fstat(directory_descriptor)) != before:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A executable changed during directory enumeration"
            )

    walk(root_descriptor, "", 0)
    return files, directories


def verify_deepseek_v4_query_a_executable_deployment(
    deployment_root: Path,
    application_root: Path,
    snapshot: Path,
    lock: dict[str, Any],
) -> dict[str, Any]:
    """Verify a closed official Query-A package without an execution claim."""

    deployment_root = Path(deployment_root).absolute()
    application_root = Path(application_root).absolute()
    snapshot = Path(snapshot).absolute()
    try:
        validate_official_checkpoint_lock(lock, load_official_config())
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeepSeekV4QueryAExecutableCheckError(
            f"checkpoint lock is not the pinned official release: {exc}"
        ) from exc

    with ExitStack() as stack:
        root_descriptor, root_fingerprint = _open_root(
            stack, deployment_root, "Query-A executable deployment root"
        )
        app_descriptor, app_fingerprint = _open_root(
            stack, application_root, "canonical Query-A application root"
        )
        snapshot_descriptor, snapshot_fingerprint = _open_root(
            stack, snapshot, "official checkpoint snapshot root"
        )

        app_manifest_file = _safe_file(
            stack,
            app_descriptor,
            APPLICATION_MANIFEST,
            "canonical Query-A application manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        app_verification_file = _safe_file(
            stack,
            app_descriptor,
            APPLICATION_VERIFICATION,
            "canonical Query-A retained verification",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        application = _json_from_file(
            app_manifest_file,
            "canonical Query-A application manifest",
            maximum=_MAX_MANIFEST_BYTES,
        )
        retained = _json_from_file(
            app_verification_file,
            "canonical Query-A retained verification",
            maximum=_MAX_MANIFEST_BYTES,
        )
        try:
            replay = verify_canonical_application(application_root, snapshot, lock)
        except DeepSeekV4ApplicationCheckError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"independent canonical application replay failed: {exc}"
            ) from exc
        application_id, verification_id, assignments = _validate_application(
            application, retained, replay, lock
        )
        app_manifest_sha256, _ = _sha256_file(
            app_manifest_file, "canonical Query-A application manifest"
        )
        app_verification_sha256, _ = _sha256_file(
            app_verification_file, "canonical Query-A retained verification"
        )

        for name in sorted(OFFICIAL_RESOURCES):
            spec = OFFICIAL_RESOURCES[name]
            for record in assignments[name]:
                source_file = _safe_file(
                    stack,
                    app_descriptor,
                    record["path"],
                    f"canonical Query-A rank {record['rank']} resource {name!r}",
                    exact_size=spec["size_bytes"],
                )
                digest, size = _sha256_file(source_file, f"canonical resource {name!r}")
                if (digest, size) != (spec["sha256"], spec["size_bytes"]):
                    raise DeepSeekV4QueryAExecutableCheckError(
                        f"canonical resource {name!r} rank {record['rank']} differs"
                    )
                _validate_encoding(
                    source_file, spec["dtype"], f"canonical resource {name!r}"
                )

        manifest_file = _safe_file(
            stack,
            root_descriptor,
            DEPLOYMENT_MANIFEST,
            "Query-A executable deployment manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        deployment = _json_from_file(
            manifest_file,
            "Query-A executable deployment manifest",
            maximum=_MAX_MANIFEST_BYTES,
        )
        _exact_keys(
            deployment,
            {
                "artifacts",
                "build_id",
                "claim_boundary",
                "compiler",
                "entrypoint",
                "functional_counter_contract_id",
                "model_id",
                "program_contract_id",
                "program_sha256",
                "resource_manifest_id",
                "schedule_certificate_id",
                "schedule_id",
                "schema",
                "site",
                "source",
                "status",
            },
            "Query-A executable deployment manifest",
        )
        artifacts = deployment.get("artifacts")
        if type(artifacts) is not list or len(artifacts) != 14:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A executable must enumerate exactly fourteen artifacts"
            )
        paths: set[str] = set()
        roles: set[str] = set()
        ordered_paths: list[str] = []
        files_by_path: dict[str, _StableFile] = {}
        observed_records: list[dict[str, Any]] = []
        guarded_files = [manifest_file, app_manifest_file, app_verification_file]
        artifact_bytes = 0
        for index, raw in enumerate(artifacts):
            record = _exact_keys(
                raw,
                {"path", "role", "sha256", "size_bytes"},
                f"Query-A artifacts[{index}]",
            )
            path = _safe_relative(
                record.get("path"), f"Query-A artifacts[{index}].path"
            )
            role = record.get("role")
            size = record.get("size_bytes")
            if (
                path in paths
                or type(role) is not str
                or role in roles
                or role not in _EXPECTED_ROLES
                or type(size) is not int
                or size < 1
                or path != _FIXED_PATH_BY_ROLE[role]
            ):
                raise DeepSeekV4QueryAExecutableCheckError(
                    "Query-A artifact path, role, or size closure differs"
                )
            exact_size = _EXACT_SIZE_BY_ROLE.get(role)
            maximum_size = None if exact_size is not None else _MAX_JSON_BYTES
            artifact_file = _safe_file(
                stack,
                root_descriptor,
                path,
                f"Query-A artifact {path!r}",
                exact_size=size,
                maximum_size=maximum_size,
            )
            if exact_size is not None and size != exact_size:
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"Query-A role {role!r} has an invalid exact size"
                )
            digest, observed_size = _sha256_file(
                artifact_file, f"Query-A artifact {path!r}"
            )
            if digest != _digest(
                record.get("sha256"), f"Query-A artifacts[{index}].sha256"
            ):
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"Query-A artifact {path!r} differs from its manifest"
                )
            paths.add(path)
            roles.add(role)
            ordered_paths.append(path)
            files_by_path[path] = artifact_file
            observed_records.append(dict(record))
            guarded_files.append(artifact_file)
            artifact_bytes += observed_size
        if roles != _EXPECTED_ROLES or ordered_paths != sorted(ordered_paths):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A artifact roles or canonical ordering differs"
            )

        program_payload = _descriptor_bytes(
            files_by_path[ENTRYPOINT["program"]], "Query-A program", PROGRAM_BYTES
        )
        if hashlib.sha256(program_payload).hexdigest() != PROGRAM_SHA256:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A program differs from the frozen 196-byte identity"
            )
        try:
            decoded = decode(program_payload)
            verify(decoded)
            expected_program = encode(assemble())
        except DeepSeekV4QueryAMicrocodeError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"Query-A program fails semantic verification: {exc}"
            ) from exc
        if program_payload != expected_program:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A program differs from independent assembly"
            )

        disassembly_payload = _descriptor_bytes(
            files_by_path[ENTRYPOINT["program_disassembly"]],
            "Query-A disassembly",
            _EXACT_SIZE_BY_ROLE["microcode_disassembly"],
        )
        if (
            hashlib.sha256(disassembly_payload).hexdigest()
            != PROGRAM_DISASSEMBLY_SHA256
            or disassembly_payload != disassemble(decoded).encode("ascii")
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A deterministic disassembly differs"
            )
        program_contract = _json_from_file(
            files_by_path[ENTRYPOINT["program_contract"]], "Query-A program contract"
        )
        try:
            verify_program_contract(program_contract)
        except DeepSeekV4QueryAMicrocodeError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"Query-A program contract differs: {exc}"
            ) from exc
        contract_payload = canonical_json_bytes(program_contract)
        if (
            program_contract.get("contract_id") != PROGRAM_CONTRACT_ID
            or program_contract.get("program_sha256") != PROGRAM_SHA256
            or hashlib.sha256(contract_payload).hexdigest() != PROGRAM_CONTRACT_SHA256
            or not _canonical_equal(program_contract, build_program_contract())
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A program contract is not its frozen exact document"
            )

        schedule = _json_from_file(
            files_by_path[ENTRYPOINT["logical_schedule"]], "Query-A logical schedule"
        )
        certificate = _json_from_file(
            files_by_path[ENTRYPOINT["logical_schedule_certificate"]],
            "Query-A logical schedule certificate",
        )
        try:
            expected_certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
            verify_deepseek_v4_query_a_logical_schedule_certificate(
                certificate, schedule
            )
        except DeepSeekV4QueryAScheduleCheckError as exc:
            raise DeepSeekV4QueryAExecutableCheckError(
                f"Query-A logical schedule differs: {exc}"
            ) from exc
        if (
            schedule.get("schedule_id") != LOGICAL_SCHEDULE_ID
            or certificate.get("certificate_id") != LOGICAL_CERTIFICATE_ID
            or hashlib.sha256(canonical_json_bytes(schedule)).hexdigest()
            != LOGICAL_SCHEDULE_SHA256
            or hashlib.sha256(canonical_json_bytes(certificate)).hexdigest()
            != LOGICAL_CERTIFICATE_SHA256
            or not _canonical_equal(certificate, expected_certificate)
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A schedule or certificate frozen identity differs"
            )

        for name, role in (
            (NORM_NAME, "attention_norm_weight"),
            (WEIGHT_NAME, "query_a_weight"),
            (SCALE_NAME, "query_a_scale"),
        ):
            spec = OFFICIAL_RESOURCES[name]
            packaged = files_by_path[spec["path"]]
            digest, size = _sha256_file(packaged, f"packaged resource {name!r}")
            if (digest, size) != (spec["sha256"], spec["size_bytes"]):
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"packaged resource {name!r} differs from official bytes"
                )
            _validate_encoding(packaged, spec["dtype"], f"packaged resource {name!r}")
            if _FIXED_PATH_BY_ROLE[role] != spec["path"]:
                raise DeepSeekV4QueryAExecutableCheckError(
                    f"packaged resource {name!r} role binding differs"
                )
        row_payload = _descriptor_bytes(
            files_by_path[ROWS_PATH], "exhaustive Query-A rows", 4096
        )
        if (
            row_payload != struct.pack("<1024I", *range(1024))
            or row_payload != exhaustive_row_payload()
            or hashlib.sha256(row_payload).hexdigest() != ROWS_SHA256
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                "generated exhaustive Query-A row resource differs"
            )

        checkpoint_lock_id = _digest(lock.get("lock_id"), "checkpoint lock_id")
        resource_manifest = _json_from_file(
            files_by_path[ENTRYPOINT["resource_manifest"]], "Query-A resource manifest"
        )
        expected_resource_manifest = _expected_resource_manifest(
            application_id=application_id,
            verification_id=verification_id,
            checkpoint_lock_id=checkpoint_lock_id,
        )
        if not _canonical_equal(resource_manifest, expected_resource_manifest):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A resource and tensor contract differs"
            )

        counter_contract = _json_from_file(
            files_by_path[ENTRYPOINT["functional_counter_contract"]],
            "Query-A functional counter contract",
        )
        expected_counter_contract = _expected_counter_contract()
        if not _canonical_equal(counter_contract, expected_counter_contract):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A functional counter contract differs"
            )
        try:
            for token_count in range(1, 5):
                expected_counters = {
                    name: coefficient * token_count
                    for name, coefficient in _PER_TOKEN_COUNTERS.items()
                }
                expected_counters.update(_FIXED_COUNTERS)
                expected_counters = dict(sorted(expected_counters.items()))
                if not _canonical_equal(
                    query_a_functional_counters(token_count), expected_counters
                ):
                    raise DeepSeekV4QueryAExecutableCheckError(
                        "runtime Query-A functional counters differ from the package"
                    )
        except QueryAServiceNumericError as exc:  # pragma: no cover - frozen range
            raise DeepSeekV4QueryAExecutableCheckError(
                f"runtime Query-A counter contract failed: {exc}"
            ) from exc

        for path, label, expected in (
            (
                ENTRYPOINT["execution_request_schema"],
                "Query-A execution request schema",
                _expected_request_schema(),
            ),
            (
                ENTRYPOINT["execution_result_schema"],
                "Query-A execution result schema",
                _expected_result_schema(),
            ),
            (
                ENTRYPOINT["execution_coverage"],
                "Query-A execution coverage",
                _expected_execution_coverage(),
            ),
        ):
            observed = _json_from_file(files_by_path[path], label)
            if not _canonical_equal(observed, expected):
                raise DeepSeekV4QueryAExecutableCheckError(f"{label} differs")

        expected_source = {
            "application_id": application_id,
            "application_manifest_sha256": app_manifest_sha256,
            "application_status": application["status"],
            "checkpoint_lock_id": checkpoint_lock_id,
            "evidence_scope": "official_checkpoint",
            "rank_replica_count": 4,
            "repository": REPOSITORY,
            "revision": REVISION,
            "verification_id": verification_id,
            "verification_manifest_sha256": app_verification_sha256,
        }
        expected_metadata = {
            "claim_boundary": CLAIM_BOUNDARY,
            "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
            "entrypoint": ENTRYPOINT,
            "functional_counter_contract_id": expected_counter_contract["contract_id"],
            "model_id": MODEL_ID,
            "program_contract_id": PROGRAM_CONTRACT_ID,
            "program_sha256": PROGRAM_SHA256,
            "resource_manifest_id": expected_resource_manifest["manifest_id"],
            "schedule_certificate_id": LOGICAL_CERTIFICATE_ID,
            "schedule_id": LOGICAL_SCHEDULE_ID,
            "schema": EXECUTABLE_DEPLOYMENT_SCHEMA,
            "site": {"branch": "attention", "layer": 0, "scope": "main"},
            "source": expected_source,
            "status": EXECUTABLE_STATUS,
        }
        if not _canonical_equal(
            {key: deployment.get(key) for key in expected_metadata}, expected_metadata
        ):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A deployment metadata or claim boundary differs"
            )

        expected_records = [
            _artifact_record(path, role, files_by_path[path])
            for role, path in _FIXED_PATH_BY_ROLE.items()
        ]
        expected_records.sort(key=lambda record: record["path"])
        if not _canonical_equal(observed_records, expected_records):
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A artifact path-to-role or hash closure differs"
            )

        build_id = _digest(deployment.get("build_id"), "deployment build_id")
        identity_body = {
            key: deployment[key] for key in deployment if key != "build_id"
        }
        if hashlib.sha256(canonical_json_bytes(identity_body)).hexdigest() != build_id:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A deployment full-body build identity differs"
            )
        actual_files, actual_directories = _enumerate_tree(root_descriptor)
        if actual_files != paths | {DEPLOYMENT_MANIFEST}:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A package contains an unlisted or missing file"
            )
        if actual_directories != _EXPECTED_DIRECTORIES:
            raise DeepSeekV4QueryAExecutableCheckError(
                "Query-A package directory closure differs"
            )

        for relative in sorted(_EXPECTED_DIRECTORIES):
            directory = _safe_directory(
                stack, root_descriptor, relative, f"Query-A directory {relative!r}"
            )
            _verify_directory_stable(directory, f"Query-A directory {relative!r}")
        for guarded in guarded_files:
            _verify_stable(guarded, f"guarded file {guarded.relative_path!r}")
        _verify_root_stable(
            deployment_root,
            root_descriptor,
            root_fingerprint,
            "Query-A executable deployment root",
        )
        _verify_root_stable(
            application_root,
            app_descriptor,
            app_fingerprint,
            "canonical Query-A application root",
        )
        _verify_root_stable(
            snapshot,
            snapshot_descriptor,
            snapshot_fingerprint,
            "official checkpoint snapshot root",
        )
        return {
            "application_id": application_id,
            "artifact_bytes": artifact_bytes,
            "build_id": build_id,
            "checked_artifact_count": len(artifacts),
            "checked_rank_replica_count": 12,
            "functional_counter_contract_id": expected_counter_contract["contract_id"],
            "program_contract_id": PROGRAM_CONTRACT_ID,
            "program_sha256": PROGRAM_SHA256,
            "resource_manifest_id": expected_resource_manifest["manifest_id"],
            "schedule_certificate_id": LOGICAL_CERTIFICATE_ID,
            "schedule_id": LOGICAL_SCHEDULE_ID,
            "status": "package_identity_verified_execution_not_evidenced",
            "verification_id": verification_id,
        }


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPILER_NAME",
    "COMPILER_VERSION",
    "DEPLOYMENT_MANIFEST",
    "ENTRYPOINT",
    "EXECUTABLE_DEPLOYMENT_SCHEMA",
    "EXECUTABLE_STATUS",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "DeepSeekV4QueryAExecutableCheckError",
    "verify_deepseek_v4_query_a_executable_deployment",
]
