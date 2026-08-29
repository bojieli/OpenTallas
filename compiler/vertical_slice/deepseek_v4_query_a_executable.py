"""Build the official DeepSeek V4 weighted-RMS and Query-A package.

The builder accepts only an independently replayed partial official canonical
application selecting the exact layer-0 attention-normalization weight,
Query-A FP8 weight, and Query-A E8M0 scale.  It validates all four rank
replicas, copies one byte-identical resource instance, adds the exhaustive row
constant, program, contracts, schedule, and runtime interfaces, then invokes
the independent package checker before atomic create-once publication.

No activation, expected output, execution result, timing value, or physical
claim is accepted or emitted.
"""

from __future__ import annotations

from contextlib import ExitStack
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import stat
import struct
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME as APPLICATION_MANIFEST,
    VERIFICATION_FILENAME as APPLICATION_VERIFICATION,
    DeepSeekV4ApplicationCheckError,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_query_a_executable import (
    verify_deepseek_v4_query_a_executable_deployment,
)
from compiler.checking.deepseek_v4_query_a_schedule import (
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
    assemble,
    build_program_contract,
    disassemble,
    encode,
    exhaustive_row_payload,
    verify,
    verify_program_contract,
)
from compiler.scheduling.deepseek_v4_query_a import (
    build_deepseek_v4_query_a_logical_schedule,
)
from runtime.service_engine.query_a_numeric import query_a_functional_counters


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_query_a_executable.v1"
DEPLOYMENT_STATUS = "official_checkpoint_program_packaged_execution_not_evidenced"
EXECUTION_REQUEST_SCHEMA = "opentallas.deepseek_v4_query_a_execution_request.v1"
EXECUTION_RESULT_SCHEMA = "opentallas.deepseek_v4_query_a_execution_result.v1"
RESOURCE_MANIFEST_SCHEMA = "opentallas.deepseek_v4_query_a_resources.v1"
COUNTER_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_query_a_functional_counter_contract.v1"
)
EXECUTION_COVERAGE_SCHEMA = "opentallas.deepseek_v4_query_a_executable_coverage.v1"
COMPILER_NAME = "opentallas-deepseek-v4-query-a-executable-packager"
COMPILER_VERSION = "0.1.0"
MANIFEST_FILENAME = "deployment_manifest.json"
PROGRAM_BYTES = 196
PROGRAM_SHA256 = "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
PROGRAM_CONTRACT_ID = "0aa1969479c527d33fa893557f40dd05e3efbc9a3e1af7d959d4cb8496806903"
LOGICAL_SCHEDULE_ID = "2673d8ef4e62df0ec1441c1b14eeb6a207b246a70a987adadfe354a418711e13"
LOGICAL_CERTIFICATE_ID = (
    "d2a6e754abc7440dc341e00fac4bf7e48f9e53659f971fdfbb03c4782c47b546"
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

_ROLE_BY_PATH = {
    "execution_coverage.json": "execution_coverage",
    "interfaces/execution_request_v1.schema.json": "execution_request_schema",
    "interfaces/execution_result_v1.schema.json": "execution_result_schema",
    "interfaces/functional_counter_contract.json": "functional_counter_contract",
    "program/query_a.bin": "microcode_program",
    "program/query_a.disassembly.txt": "microcode_disassembly",
    "program/program_contract.json": "program_contract",
    "resources/attn_norm_weight.bf16le": "attention_norm_weight",
    ROWS_PATH: "exhaustive_output_rows",
    "resources/query_a_scale.e8m0": "query_a_scale",
    "resources/query_a_weight.f8e4m3fn": "query_a_weight",
    "resources/resource_manifest.json": "resource_manifest",
    "schedule/logical_schedule.json": "logical_schedule",
    "schedule/logical_schedule_certificate.json": "logical_schedule_certificate",
}
_READ_CHUNK_BYTES = 1024 * 1024
_MAX_SOURCE_JSON_BYTES = 256 * 1024
_MAX_GENERATED_ARTIFACT_BYTES = 512 * 1024
_MAX_COPY_BYTES = 8 * 1024 * 1024
_MAX_CLEANUP_ENTRIES = 32
_MAX_TREE_DEPTH = 4
_MINIMUM_FREE_BYTES = 32 * 1024 * 1024
_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_ID_ROOT = (
    "https://opentallas.org/schemas/compiler/deepseek_v4_query_a_executable"
)
_SHA256_PATTERN = "^[0-9a-f]{64}$"


class DeepSeekV4QueryAExecutableBuildError(RuntimeError):
    """Raised when the official Query-A package cannot be published."""


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
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or any(operation not in os.supports_dir_fd for operation in required_dir_fd)
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "platform lacks race-resistant bounded package operations"
        )


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} is not canonical POSIX")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not a lowercase SHA-256"
        )
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} fields differ")
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
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _verify_root_binding(root: Path, descriptor: int, label: str) -> None:
    held = os.fstat(descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"{label} was replaced while the package was built"
            )
    finally:
        os.close(current_descriptor)


def _open_relative_descriptor(root_descriptor: int, relative: str, label: str) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_descriptor = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part, directory_flags, dir_fd=directory_descriptor
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        return os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)


def _stable_source_file(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    label: str,
    expected_size: int,
) -> tuple[int, tuple[int, ...]]:
    descriptor = _open_relative_descriptor(root_descriptor, relative, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != expected_size:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not a {expected_size}-byte regular file"
        )
    return descriptor, _fingerprint(metadata)


def _verify_source_stable(
    root_descriptor: int,
    relative: str,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} changed while read")
    reopened = _open_relative_descriptor(root_descriptor, relative, label)
    try:
        if _fingerprint(os.fstat(reopened)) != fingerprint:
            raise DeepSeekV4QueryAExecutableBuildError(f"{label} was replaced")
    finally:
        os.close(reopened)


def _descriptor_bytes(
    descriptor: int,
    size: int,
    label: str,
    maximum: int,
) -> bytes:
    if size > maximum:
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} exceeds its bound")
    payload = bytearray()
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(_READ_CHUNK_BYTES, size - offset), offset)
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != size:
        raise DeepSeekV4QueryAExecutableBuildError(f"{label} ended while read")
    return bytes(payload)


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4QueryAExecutableBuildError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> object:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} has non-finite JSON number {token!r}"
        )

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
            parse_float=lambda token: _finite_float(token, label),
        )
    except DeepSeekV4QueryAExecutableBuildError:
        raise
    except (UnicodeError, json.JSONDecodeError, OverflowError, ValueError) as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if type(value) is not dict or canonical_json_bytes(value) != payload:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not one canonical JSON object"
        )
    return value


def _finite_float(token: str, label: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} has non-finite JSON number {token!r}"
        )
    return value


def _load_source_json(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    label: str,
) -> tuple[dict[str, Any], str]:
    descriptor = _open_relative_descriptor(root_descriptor, relative, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    fingerprint = _fingerprint(metadata)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size < 2
        or metadata.st_size > _MAX_SOURCE_JSON_BYTES
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} is not a bounded regular file"
        )
    payload = _descriptor_bytes(
        descriptor, metadata.st_size, label, _MAX_SOURCE_JSON_BYTES
    )
    _verify_source_stable(root_descriptor, relative, descriptor, fingerprint, label)
    return _strict_json_payload(payload, label), hashlib.sha256(payload).hexdigest()


def _validate_encoding(descriptor: int, size: int, dtype: str, label: str) -> str:
    digest = hashlib.sha256()
    offset = 0
    carry = b""
    while offset < size:
        chunk = os.pread(descriptor, min(_READ_CHUNK_BYTES, size - offset), offset)
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
        if dtype == "BF16":
            combined = carry + chunk
            even = len(combined) & ~1
            for item_offset in range(0, even, 2):
                code = combined[item_offset] | (combined[item_offset + 1] << 8)
                if code & 0x7F80 == 0x7F80:
                    raise DeepSeekV4QueryAExecutableBuildError(
                        f"{label} contains non-finite BF16 code 0x{code:04x}"
                    )
            carry = combined[even:]
        elif dtype == "F8_E4M3":
            if any(code in {0x7F, 0xFF} for code in chunk):
                raise DeepSeekV4QueryAExecutableBuildError(
                    f"{label} contains a reserved FP8 E4M3 code"
                )
        elif dtype == "F8_E8M0":
            if 0xFF in chunk:
                raise DeepSeekV4QueryAExecutableBuildError(
                    f"{label} contains a reserved E8M0 code"
                )
        else:  # pragma: no cover - closed caller set
            raise DeepSeekV4QueryAExecutableBuildError(
                f"unsupported resource dtype {dtype!r}"
            )
    if offset != size or carry:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"{label} ended during encoding validation"
        )
    return digest.hexdigest()


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
        raise DeepSeekV4QueryAExecutableBuildError(
            "retained canonical verification differs from independent replay"
        )
    if (
        application.get("schema") != "opentallas.canonical_application.v1"
        or application.get("evidence_scope") != "official_checkpoint"
        or application.get("status")
        != "partial_official_transform_application_not_release_evidence"
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A application is not partial official evidence"
        )
    lock_id = _digest(lock.get("lock_id"), "checkpoint lock_id")
    if application.get("source") != {
        "checkpoint_lock_id": lock_id,
        "repository": REPOSITORY,
        "revision": REVISION,
    }:
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A application is not the pinned official release"
        )
    requested = sorted(OFFICIAL_RESOURCES)
    if not _canonical_equal(
        application.get("selection"),
        {
            "complete_plan": False,
            "dependency_input_names": [],
            "requested_input_names": requested,
        },
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A application does not select exactly three tensors"
        )
    inputs = application.get("inputs")
    if type(inputs) is not list or len(inputs) != 3:
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A application must declare three inputs"
        )
    observed_names: list[str] = []
    for raw in inputs:
        if type(raw) is not dict:
            raise DeepSeekV4QueryAExecutableBuildError("Query-A input is not an object")
        name = raw.get("name")
        if type(name) is not str or name not in OFFICIAL_RESOURCES:
            raise DeepSeekV4QueryAExecutableBuildError("Query-A input name differs")
        spec = OFFICIAL_RESOURCES[name]
        if not _canonical_equal(
            raw,
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
            raise DeepSeekV4QueryAExecutableBuildError(
                f"Query-A input {name!r} differs from official bytes"
            )
        observed_names.append(name)
    if observed_names != requested:
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A inputs are not canonical and unique"
        )

    assignments = application.get("assignments")
    if type(assignments) is not list or len(assignments) != 12:
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A application must contain twelve assignments"
        )
    by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in requested}
    for index, raw in enumerate(assignments):
        if type(raw) is not dict:
            raise DeepSeekV4QueryAExecutableBuildError(
                f"Query-A assignment {index} is not an object"
            )
        name = raw.get("name")
        rank = raw.get("rank")
        if (
            type(name) is not str
            or name not in OFFICIAL_RESOURCES
            or type(rank) is not int
            or not 0 <= rank < 4
        ):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"Query-A assignment {index} identity differs"
            )
        spec = OFFICIAL_RESOURCES[name]
        expected = {
            "logical_dtype": spec["logical_dtype"],
            "name": name,
            "path": f"ranks/rank-{rank:03d}/{name}.bin",
            "payload_bytes": spec["size_bytes"],
            "rank": rank,
            "scale_source": None,
            "sha256": spec["sha256"],
            "shape": spec["shape"],
            "source": {
                "name": name,
                "payload_sha256": spec["sha256"],
                "shape": spec["shape"],
                "slice": None,
                "storage_dtype": spec["dtype"],
            },
            "storage_dtype": spec["dtype"],
            "transform": "identity",
        }
        if not _canonical_equal(raw, expected):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"Query-A assignment {index} is not an exact identity replica"
            )
        by_name[name].append(raw)
    for name, records in by_name.items():
        if [record["rank"] for record in records] != [0, 1, 2, 3] or [
            record["path"] for record in records
        ] != _assignment_paths(name):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"Query-A resource {name!r} lacks four ordered replicas"
            )
    application_id = _digest(application.get("application_id"), "application_id")
    verification_id = _digest(replay.get("verification_id"), "verification_id")
    expected_coverage = {
        "checked_assignment_count": 12,
        "checked_input_count": 3,
        "checked_output_bytes": 4
        * sum(spec["size_bytes"] for spec in OFFICIAL_RESOURCES.values()),
    }
    if (
        replay.get("application_id") != application_id
        or replay.get("checkpoint_lock_id") != lock_id
        or replay.get("schema") != "opentallas.canonical_application_check.v1"
        or replay.get("status") != "full_assignment_match"
        or not _canonical_equal(replay.get("coverage"), expected_coverage)
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A canonical replay identity or coverage differs"
        )
    return application_id, verification_id, by_name


def _create_private_directory(
    stack: ExitStack,
    *,
    parent: Path,
    parent_descriptor: int,
) -> tuple[Path, str, int]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    for _ in range(128):
        name = f".query-a-executable.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4QueryAExecutableBuildError(
                f"cannot create private package directory: {exc}"
            ) from exc
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise DeepSeekV4QueryAExecutableBuildError(
                f"cannot open private package directory: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        return parent / name, name, descriptor
    raise DeepSeekV4QueryAExecutableBuildError(
        "cannot reserve a collision-free package directory"
    )


def _cleanup_private_directory(
    *,
    parent_descriptor: int,
    name: str,
    descriptor: int,
) -> None:
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    held = os.fstat(descriptor)
    try:
        current_descriptor = os.open(name, directory_flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot safely reopen temporary package for cleanup: {exc}"
        ) from exc
    current = os.fstat(current_descriptor)
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
        held.st_dev,
        held.st_ino,
    ):
        os.close(current_descriptor)
        raise DeepSeekV4QueryAExecutableBuildError(
            "refusing to clean a replaced temporary package"
        )
    visited = 0

    def remove_contents(directory_descriptor: int, depth: int) -> None:
        nonlocal visited
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4QueryAExecutableBuildError(
                "temporary package cleanup exceeds its depth bound"
            )
        names = os.listdir(directory_descriptor)
        visited += len(names)
        if visited > _MAX_CLEANUP_ENTRIES:
            raise DeepSeekV4QueryAExecutableBuildError(
                "temporary package cleanup exceeds its entry bound"
            )
        for child_name in names:
            metadata = os.stat(
                child_name, dir_fd=directory_descriptor, follow_symlinks=False
            )
            if stat.S_ISDIR(metadata.st_mode):
                child_descriptor = os.open(
                    child_name,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                try:
                    remove_contents(child_descriptor, depth + 1)
                finally:
                    os.close(child_descriptor)
                os.rmdir(child_name, dir_fd=directory_descriptor)
            else:
                os.unlink(child_name, dir_fd=directory_descriptor)

    try:
        remove_contents(current_descriptor, 0)
    finally:
        os.close(current_descriptor)
    os.rmdir(name, dir_fd=parent_descriptor)


def _write_exclusive_bytes(root_descriptor: int, relative: str, payload: bytes) -> None:
    if type(payload) is not bytes or len(payload) > max(
        _MAX_COPY_BYTES, _MAX_GENERATED_ARTIFACT_BYTES
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"generated artifact {relative!r} payload is invalid"
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
                raise DeepSeekV4QueryAExecutableBuildError(
                    f"generated artifact {relative!r} ended while written"
                )
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"generated artifact {relative!r} is incomplete"
            )
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot write generated artifact {relative!r}: {exc}"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_descriptor)


def _copy_source_to_package(
    *,
    source_descriptor: int,
    expected_size: int,
    expected_sha256: str,
    destination_root_descriptor: int,
    destination_relative: str,
) -> None:
    if expected_size > _MAX_COPY_BYTES:
        raise DeepSeekV4QueryAExecutableBuildError("resource exceeds copy bound")
    parts = Path(_safe_relative(destination_relative, "resource path")).parts
    directory_descriptor = os.dup(destination_root_descriptor)
    output_descriptor: int | None = None
    digest = hashlib.sha256()
    copied = 0
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        output_descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
        while copied < expected_size:
            chunk = os.pread(
                source_descriptor,
                min(_READ_CHUNK_BYTES, expected_size - copied),
                copied,
            )
            if not chunk:
                break
            digest.update(chunk)
            written_offset = 0
            while written_offset < len(chunk):
                written = os.write(output_descriptor, chunk[written_offset:])
                if written <= 0:
                    raise DeepSeekV4QueryAExecutableBuildError(
                        "copied resource ended while written"
                    )
                written_offset += written
            copied += len(chunk)
        os.fsync(output_descriptor)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot copy official Query-A resource: {exc}"
        ) from exc
    finally:
        if output_descriptor is not None:
            os.close(output_descriptor)
        os.close(directory_descriptor)
    if copied != expected_size or digest.hexdigest() != expected_sha256:
        raise DeepSeekV4QueryAExecutableBuildError(
            "official Query-A resource changed while copied"
        )


def _artifact_record(root_descriptor: int, relative: str, role: str) -> dict[str, Any]:
    descriptor = _open_relative_descriptor(
        root_descriptor, relative, f"package artifact {relative!r}"
    )
    try:
        metadata = os.fstat(descriptor)
        fingerprint = _fingerprint(metadata)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not 1 <= metadata.st_size <= _MAX_COPY_BYTES
        ):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"package artifact {relative!r} is not bounded regular data"
            )
        digest = hashlib.sha256()
        offset = 0
        while offset < metadata.st_size:
            chunk = os.pread(
                descriptor,
                min(_READ_CHUNK_BYTES, metadata.st_size - offset),
                offset,
            )
            if not chunk:
                break
            digest.update(chunk)
            offset += len(chunk)
        if (
            offset != metadata.st_size
            or _fingerprint(os.fstat(descriptor)) != fingerprint
        ):
            raise DeepSeekV4QueryAExecutableBuildError(
                f"package artifact {relative!r} changed while hashed"
            )
    finally:
        os.close(descriptor)
    reopened = _open_relative_descriptor(
        root_descriptor, relative, f"package artifact {relative!r}"
    )
    try:
        if _fingerprint(os.fstat(reopened)) != fingerprint:
            raise DeepSeekV4QueryAExecutableBuildError(
                f"package artifact {relative!r} was replaced"
            )
    finally:
        os.close(reopened)
    return {
        "path": relative,
        "role": role,
        "sha256": digest.hexdigest(),
        "size_bytes": metadata.st_size,
    }


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


def _execution_request_schema() -> dict[str, Any]:
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


def _counter_contract() -> dict[str, Any]:
    one = query_a_functional_counters(1)
    fixed_names = {
        "complete_events",
        "micro_ops_executed",
        "semantic_operators_executed",
    }
    fixed = {name: one[name] for name in sorted(fixed_names)}
    per_token = {name: value for name, value in one.items() if name not in fixed_names}
    for token_count in range(2, 5):
        observed = query_a_functional_counters(token_count)
        expected = {
            name: coefficient * token_count for name, coefficient in per_token.items()
        }
        expected.update(fixed)
        if not _canonical_equal(observed, dict(sorted(expected.items()))):
            raise DeepSeekV4QueryAExecutableBuildError(
                "Query-A runtime counters do not have the frozen affine contract"
            )
    body = {
        "claim_boundary": (
            "Exact shape-derived functional work for RMS_NORM, exhaustive Query-A "
            "FP8_LINEAR, and COMPLETE; these counters are not hardware cycles, "
            "transactions, latency, throughput, energy, area, routing, or PPA."
        ),
        "fixed_counters": fixed,
        "implementation": (
            "runtime.service_engine.query_a_numeric.query_a_functional_counters"
        ),
        "model_id": MODEL_ID,
        "per_token_coefficients": per_token,
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


def _execution_result_schema(counter_names: list[str]) -> dict[str, Any]:
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


def _execution_coverage() -> dict[str, Any]:
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


def _resource_manifest(
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


def _publish_create_once(
    *,
    parent_descriptor: int,
    temporary_name: str,
    output_name: str,
    output: Path,
) -> None:
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is not None:
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
            os.fsencode(temporary_name),
            parent_descriptor,
            os.fsencode(output_name),
            1,
        )
        if result == 0:
            return
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise DeepSeekV4QueryAExecutableBuildError(
                f"output already exists: {output}"
            )
        if error not in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
            raise DeepSeekV4QueryAExecutableBuildError(
                f"cannot publish package atomically: {os.strerror(error)}"
            )
    raise DeepSeekV4QueryAExecutableBuildError(
        "platform lacks atomic rename-without-replacement support"
    )


def _build_into(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    application_descriptor: int,
    application: dict[str, Any],
    retained: dict[str, Any],
    application_manifest_sha256: str,
    application_verification_sha256: str,
    root: Path,
    root_descriptor: int,
) -> dict[str, Any]:
    try:
        replay = verify_canonical_application(application_root, snapshot, lock)
    except DeepSeekV4ApplicationCheckError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"independent canonical application replay failed: {exc}"
        ) from exc
    application_id, verification_id, assignments = _validate_application(
        application, retained, replay, lock
    )

    try:
        for directory in ("interfaces", "program", "resources", "schedule"):
            os.mkdir(directory, 0o700, dir_fd=root_descriptor)
    except OSError as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"cannot create package directories: {exc}"
        ) from exc

    with ExitStack() as source_stack:
        for name in sorted(OFFICIAL_RESOURCES):
            spec = OFFICIAL_RESOURCES[name]
            rank_zero_descriptor: int | None = None
            rank_zero_fingerprint: tuple[int, ...] | None = None
            rank_zero_path: str | None = None
            for record in assignments[name]:
                label = f"canonical resource {name!r} rank {record['rank']}"
                descriptor, fingerprint = _stable_source_file(
                    source_stack,
                    application_descriptor,
                    record["path"],
                    label,
                    spec["size_bytes"],
                )
                digest = _validate_encoding(
                    descriptor, spec["size_bytes"], spec["dtype"], label
                )
                if digest != spec["sha256"]:
                    raise DeepSeekV4QueryAExecutableBuildError(
                        f"{label} differs from official bytes"
                    )
                _verify_source_stable(
                    application_descriptor,
                    record["path"],
                    descriptor,
                    fingerprint,
                    label,
                )
                if record["rank"] == 0:
                    rank_zero_descriptor = descriptor
                    rank_zero_fingerprint = fingerprint
                    rank_zero_path = record["path"]
            if (
                rank_zero_descriptor is None
                or rank_zero_fingerprint is None
                or rank_zero_path is None
            ):  # pragma: no cover - validation already closes ranks
                raise DeepSeekV4QueryAExecutableBuildError(
                    f"canonical resource {name!r} lacks rank zero"
                )
            _copy_source_to_package(
                source_descriptor=rank_zero_descriptor,
                expected_size=spec["size_bytes"],
                expected_sha256=spec["sha256"],
                destination_root_descriptor=root_descriptor,
                destination_relative=spec["path"],
            )
            _verify_source_stable(
                application_descriptor,
                rank_zero_path,
                rank_zero_descriptor,
                rank_zero_fingerprint,
                f"canonical resource {name!r} rank zero",
            )

    rows = exhaustive_row_payload()
    if (
        rows != struct.pack("<1024I", *range(1024))
        or hashlib.sha256(rows).hexdigest() != ROWS_SHA256
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "generated exhaustive Query-A rows differ"
        )
    _write_exclusive_bytes(root_descriptor, ROWS_PATH, rows)

    instructions = assemble()
    verify(instructions)
    program = encode(instructions)
    if (
        len(program) != PROGRAM_BYTES
        or hashlib.sha256(program).hexdigest() != PROGRAM_SHA256
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "committed Query-A program identity differs"
        )
    program_contract = build_program_contract()
    verify_program_contract(program_contract)
    if program_contract.get("contract_id") != PROGRAM_CONTRACT_ID:
        raise DeepSeekV4QueryAExecutableBuildError(
            "committed Query-A program contract identity differs"
        )
    schedule = build_deepseek_v4_query_a_logical_schedule()
    certificate = verify_deepseek_v4_query_a_logical_schedule(schedule)
    verify_deepseek_v4_query_a_logical_schedule_certificate(certificate, schedule)
    if (
        schedule.get("schedule_id") != LOGICAL_SCHEDULE_ID
        or certificate.get("certificate_id") != LOGICAL_CERTIFICATE_ID
    ):
        raise DeepSeekV4QueryAExecutableBuildError(
            "committed Query-A logical schedule identity differs"
        )

    checkpoint_lock_id = _digest(lock.get("lock_id"), "checkpoint lock_id")
    resource_manifest = _resource_manifest(
        application_id=application_id,
        verification_id=verification_id,
        checkpoint_lock_id=checkpoint_lock_id,
    )
    counter_contract = _counter_contract()
    counter_names = sorted(
        {
            *counter_contract["per_token_coefficients"],
            *counter_contract["fixed_counters"],
        }
    )
    generated = {
        "execution_coverage.json": canonical_json_bytes(_execution_coverage()),
        "interfaces/execution_request_v1.schema.json": canonical_json_bytes(
            _execution_request_schema()
        ),
        "interfaces/execution_result_v1.schema.json": canonical_json_bytes(
            _execution_result_schema(counter_names)
        ),
        "interfaces/functional_counter_contract.json": canonical_json_bytes(
            counter_contract
        ),
        "program/query_a.bin": program,
        "program/query_a.disassembly.txt": disassemble(instructions).encode("ascii"),
        "program/program_contract.json": canonical_json_bytes(program_contract),
        "resources/resource_manifest.json": canonical_json_bytes(resource_manifest),
        "schedule/logical_schedule.json": canonical_json_bytes(schedule),
        "schedule/logical_schedule_certificate.json": canonical_json_bytes(certificate),
    }
    for relative, payload in generated.items():
        _write_exclusive_bytes(root_descriptor, relative, payload)

    artifacts = [
        _artifact_record(root_descriptor, relative, _ROLE_BY_PATH[relative])
        for relative in sorted(_ROLE_BY_PATH)
    ]
    source = {
        "application_id": application_id,
        "application_manifest_sha256": application_manifest_sha256,
        "application_status": application["status"],
        "checkpoint_lock_id": checkpoint_lock_id,
        "evidence_scope": "official_checkpoint",
        "rank_replica_count": 4,
        "repository": REPOSITORY,
        "revision": REVISION,
        "verification_id": verification_id,
        "verification_manifest_sha256": application_verification_sha256,
    }
    body = {
        "artifacts": artifacts,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
        "entrypoint": dict(ENTRYPOINT),
        "functional_counter_contract_id": counter_contract["contract_id"],
        "model_id": MODEL_ID,
        "program_contract_id": PROGRAM_CONTRACT_ID,
        "program_sha256": PROGRAM_SHA256,
        "resource_manifest_id": resource_manifest["manifest_id"],
        "schedule_certificate_id": LOGICAL_CERTIFICATE_ID,
        "schedule_id": LOGICAL_SCHEDULE_ID,
        "schema": DEPLOYMENT_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "source": source,
        "status": DEPLOYMENT_STATUS,
    }
    deployment = {
        **body,
        "build_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }
    _write_exclusive_bytes(
        root_descriptor, MANIFEST_FILENAME, canonical_json_bytes(deployment)
    )
    try:
        integrity = verify_deepseek_v4_query_a_executable_deployment(
            root, application_root, snapshot, lock
        )
    except (RuntimeError, ValueError, OSError) as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"independent Query-A package verification failed: {exc}"
        ) from exc
    if integrity.get("build_id") != deployment["build_id"]:
        raise DeepSeekV4QueryAExecutableBuildError(
            "builder and independent checker identities differ"
        )
    return deployment


def build_deepseek_v4_query_a_executable_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
) -> dict[str, Any]:
    """Build, verify, and create-once publish the official Query-A package."""

    _require_secure_file_operations()
    snapshot = Path(snapshot).absolute()
    application_root = Path(application_root).absolute()
    raw_output = Path(output)
    if not raw_output.name or raw_output.name in {".", ".."}:
        raise DeepSeekV4QueryAExecutableBuildError(
            "output must name a specific directory"
        )
    if os.path.lexists(raw_output):
        raise DeepSeekV4QueryAExecutableBuildError(
            f"output already exists: {raw_output}"
        )
    output = raw_output.resolve()
    if output == Path(output.anchor):
        raise DeepSeekV4QueryAExecutableBuildError(
            "output must not be a filesystem root"
        )
    try:
        validate_official_checkpoint_lock(lock, load_official_config())
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeepSeekV4QueryAExecutableBuildError(
            f"checkpoint lock is not the pinned official release: {exc}"
        ) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < _MINIMUM_FREE_BYTES:
        raise DeepSeekV4QueryAExecutableBuildError(
            "Query-A package lacks its bounded free-space reserve"
        )

    with ExitStack() as stack:
        parent_descriptor, _ = _open_root(stack, output.parent, "Query-A output parent")
        application_descriptor, _ = _open_root(
            stack, application_root, "canonical Query-A application root"
        )
        snapshot_descriptor, _ = _open_root(
            stack, snapshot, "official checkpoint snapshot root"
        )
        application, application_manifest_sha256 = _load_source_json(
            stack,
            application_descriptor,
            APPLICATION_MANIFEST,
            "canonical Query-A application manifest",
        )
        retained, application_verification_sha256 = _load_source_json(
            stack,
            application_descriptor,
            APPLICATION_VERIFICATION,
            "canonical Query-A retained verification",
        )
        temporary, temporary_name, temporary_descriptor = _create_private_directory(
            stack,
            parent=output.parent,
            parent_descriptor=parent_descriptor,
        )
        published = False
        try:
            for path, descriptor, label in (
                (output.parent, parent_descriptor, "Query-A output parent"),
                (
                    application_root,
                    application_descriptor,
                    "canonical Query-A application root",
                ),
                (snapshot, snapshot_descriptor, "official checkpoint snapshot root"),
                (temporary, temporary_descriptor, "temporary Query-A package"),
            ):
                _verify_root_binding(path, descriptor, label)
            deployment = _build_into(
                snapshot=snapshot,
                lock=lock,
                application_root=application_root,
                application_descriptor=application_descriptor,
                application=application,
                retained=retained,
                application_manifest_sha256=application_manifest_sha256,
                application_verification_sha256=application_verification_sha256,
                root=temporary,
                root_descriptor=temporary_descriptor,
            )
            for path, descriptor, label in (
                (output.parent, parent_descriptor, "Query-A output parent"),
                (
                    application_root,
                    application_descriptor,
                    "canonical Query-A application root",
                ),
                (snapshot, snapshot_descriptor, "official checkpoint snapshot root"),
                (temporary, temporary_descriptor, "temporary Query-A package"),
            ):
                _verify_root_binding(path, descriptor, label)
            _publish_create_once(
                parent_descriptor=parent_descriptor,
                temporary_name=temporary_name,
                output_name=output.name,
                output=output,
            )
            published = True
            _verify_root_binding(
                output, temporary_descriptor, "published Query-A package"
            )
            _verify_root_binding(
                output.parent, parent_descriptor, "Query-A output parent"
            )
            return deployment
        except Exception:
            if not published:
                _cleanup_private_directory(
                    parent_descriptor=parent_descriptor,
                    name=temporary_name,
                    descriptor=temporary_descriptor,
                )
            raise


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPILER_NAME",
    "COMPILER_VERSION",
    "DEPLOYMENT_SCHEMA",
    "DEPLOYMENT_STATUS",
    "ENTRYPOINT",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "MANIFEST_FILENAME",
    "PROGRAM_BYTES",
    "DeepSeekV4QueryAExecutableBuildError",
    "build_deepseek_v4_query_a_executable_deployment",
]
