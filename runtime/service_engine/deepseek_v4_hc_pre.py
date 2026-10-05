"""Fail-closed artifact service boundary for DeepSeek V4 ``HC_PRE``.

The currently emitted ``opentallas.deepseek_v4_hc_pre_deployment.v1`` package is
an exact learned-parameter and numeric-contract package.  Its closed manifest
contains no microcode artifact, and its coverage ledger explicitly declares
``execution_coverage`` to be ``"none"``.  This module therefore verifies and
immutably snapshots that package, but it does not turn the package into an
execution claim by silently assembling host-side microcode.

The committed HC_PRE program fragment is used only to state the exact missing
integration identity.  Execution remains fail-closed until a new, versioned
deployment contract packages those bytes, binds them into its build identity,
defines canonical request/result schemas, and changes the coverage claim.

All deployment reads are descriptor-relative, bounded, nonblocking, and
``O_NOFOLLOW``.  Every byte is hash checked and every file/root fingerprint is
rechecked before an immutable deployment snapshot is returned.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, NoReturn

from compiler.microcode.deepseek_v4_hc_pre import (
    ABI_MAJOR,
    ABI_MINOR,
    PROGRAM_CONTRACT_SCHEMA,
    assemble as assemble_hc_pre_program,
    build_program_contract,
    decode as decode_hc_pre_program,
    encode as encode_hc_pre_program,
    verify as verify_hc_pre_program,
)
from runtime.service_engine.hc_pre_numeric import (
    HC_PRE_FLATTENED_WIDTH,
    HC_PRE_HC_MULT,
    HC_PRE_MIX_FIELDS,
    HC_PRE_NORM_EPSILON_BINARY32,
    HC_PRE_SINKHORN_EPSILON_BINARY32,
    HC_PRE_SINKHORN_ITERATIONS,
    HC_PRE_WIDTH,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_hc_pre_semantic.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_hc_pre_tensors.v1"
NUMERIC_PROFILE_SCHEMA = "opentallas.deepseek_v4_hc_pre_numeric_profile.v1"
COUNTER_CONTRACT_SCHEMA = "opentallas.deepseek_v4_hc_pre_counter_contract.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_hc_pre_coverage.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_hc_pre_roundtrip.v1"
NUMERIC_PROFILE_ID = "opentallas.deepseek_v4_hc_pre_numeric.v1"

MODEL_ID = "deepseek-v4-flash-0731"
OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
OFFICIAL_CHECKPOINT_LOCK_ID = (
    "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
)
OFFICIAL_APPLICATION_STATUS = (
    "partial_official_transform_application_not_release_evidence"
)
OFFICIAL_EVIDENCE_SCOPE = "official_checkpoint"
OFFICIAL_DEPLOYMENT_STATUS = (
    "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
)

BASE_NAME = "layers.0.hc_attn_base"
PROJECTION_NAME = "layers.0.hc_attn_fn"
SCALE_NAME = "layers.0.hc_attn_scale"
MODEL_PARALLEL = 4
BASE_SHAPE = (HC_PRE_MIX_FIELDS,)
PROJECTION_SHAPE = (HC_PRE_MIX_FIELDS, HC_PRE_FLATTENED_WIDTH)
SCALE_SHAPE = (3,)
BASE_BYTES = HC_PRE_MIX_FIELDS * 4
PROJECTION_BYTES = HC_PRE_MIX_FIELDS * HC_PRE_FLATTENED_WIDTH * 4
SCALE_BYTES = 3 * 4
TOTAL_PARAMETER_BYTES = BASE_BYTES + PROJECTION_BYTES + SCALE_BYTES

MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)

_MAX_JSON_BYTES = 1024 * 1024
_READ_CHUNK_BYTES = 1024 * 1024
_MAX_TREE_DEPTH = 8
_MAX_TREE_ENTRIES = 64
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SITE = {"branch": "attention", "layer": 0, "scope": "main"}
_ENTRYPOINT = {
    "counter_contract": "counter_contract.json",
    "numeric_profile": "numeric_profile.json",
    "semantic_ir": "model.ir.json",
    "tensor_manifest": "tensor_manifest.json",
}
_CLAIM_BOUNDARY = [
    "Packages all learned parameters and the frozen numeric contract for one complete HC_PRE site.",
    "Contains no input activation or expected result and establishes no execution, transformer, model-completion, or CUDA-equivalence claim.",
    "Semantic counter coefficients are contract metadata only and establish no cycles, throughput, energy, area, or PPA result.",
    "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
]
_COMPILER = {
    "name": "opentallas-deepseek-v4-hc-pre-artifact-compiler",
    "version": "0.1.0",
}
_ARTIFACT_ROLES = frozenset(
    {
        "counter_contract",
        "hc_base_parameter",
        "hc_projection_parameter",
        "hc_scale_parameter",
        "numeric_profile",
        "operator_coverage",
        "roundtrip_report",
        "semantic_ir",
        "tensor_manifest",
    }
)
_JSON_ROLES = frozenset(
    {
        "counter_contract",
        "numeric_profile",
        "operator_coverage",
        "roundtrip_report",
        "semantic_ir",
        "tensor_manifest",
    }
)
_FIXED_JSON_PATHS = {
    "counter_contract": "counter_contract.json",
    "numeric_profile": "numeric_profile.json",
    "operator_coverage": "operator_coverage.json",
    "roundtrip_report": "roundtrip_report.json",
    "semantic_ir": "model.ir.json",
    "tensor_manifest": "tensor_manifest.json",
}


class DeepSeekV4HCPreServiceError(RuntimeError):
    """Raised when HC_PRE artifacts or their execution boundary are unsafe."""


@dataclass(frozen=True)
class HCPreArtifactRecord:
    """One immutable, verified deployment artifact identity."""

    relative_path: str
    role: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class HCPreParameterResource:
    """One immutable official F32 tensor identity and decoded payload."""

    name: str
    role: str
    shape: tuple[int, ...]
    relative_path: str
    sha256: str
    size_bytes: int
    codes: tuple[int, ...] | tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class DeepSeekV4HCPreArtifactDeployment:
    """Verified v1 parameter package; deliberately not executable."""

    root: Path
    build_id: str
    application_id: str
    verification_id: str
    artifacts: tuple[HCPreArtifactRecord, ...]
    base: HCPreParameterResource
    projection: HCPreParameterResource
    scale: HCPreParameterResource
    counter_coefficients: tuple[tuple[str, int], ...]
    required_microcode_sha256: str
    required_microcode_size_bytes: int
    required_program_contract_id: str
    integration_requirements: tuple[str, ...]

    @property
    def executable(self) -> bool:
        """The v1 artifact schema explicitly carries no execution authority."""

        return False


_EXPECTED_PROGRAM_BYTES = encode_hc_pre_program(assemble_hc_pre_program())
_EXPECTED_PROGRAM = decode_hc_pre_program(_EXPECTED_PROGRAM_BYTES)
verify_hc_pre_program(_EXPECTED_PROGRAM)
_EXPECTED_PROGRAM_SHA256 = hashlib.sha256(_EXPECTED_PROGRAM_BYTES).hexdigest()
_PROGRAM_CONTRACT = build_program_contract()
_PROGRAM_CONTRACT_ID = _PROGRAM_CONTRACT["contract_id"]
if (
    _PROGRAM_CONTRACT.get("schema") != PROGRAM_CONTRACT_SCHEMA
    or _PROGRAM_CONTRACT.get("program_sha256") != _EXPECTED_PROGRAM_SHA256
    or not isinstance(_PROGRAM_CONTRACT_ID, str)
    or _SHA256.fullmatch(_PROGRAM_CONTRACT_ID) is None
):  # pragma: no cover - committed-module invariant
    raise RuntimeError("committed HC_PRE program contract is internally inconsistent")

EXECUTABLE_INTEGRATION_REQUIREMENTS = (
    "a new closed, versioned HC_PRE executable deployment schema",
    f"a packaged microcode artifact with SHA-256 {_EXPECTED_PROGRAM_SHA256}",
    f"a packaged {PROGRAM_CONTRACT_SCHEMA} contract bound by build_id",
    f"microcode ABI {ABI_MAJOR}.{ABI_MINOR} decode and exact semantic verification",
    "canonical versioned execution-request and execution-result schemas",
    "an execution coverage ledger that no longer declares execution_coverage=none",
)


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreServiceError(
            f"value is not canonical JSON: {exc}"
        ) from exc
    return (encoded + "\n").encode("ascii")


def _json_equal(left: Any, right: Any) -> bool:
    """Compare strict JSON without Python's bool/integer equivalence."""

    return _canonical_json_bytes(left) == _canonical_json_bytes(right)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreServiceError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4HCPreServiceError(
                    f"{label} contains non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4HCPreServiceError(f"cannot decode {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise DeepSeekV4HCPreServiceError(f"{label} is not a JSON object")
    if _canonical_json_bytes(value) != payload:
        raise DeepSeekV4HCPreServiceError(f"{label} is not canonical JSON")
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4HCPreServiceError(f"{label} is not an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreServiceError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4HCPreServiceError(f"{label} is not a lowercase SHA-256")
    return value


def _integer(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise DeepSeekV4HCPreServiceError(f"{label} is outside its integer bound")
    return value


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
    ):
        raise DeepSeekV4HCPreServiceError(
            "platform lacks descriptor-relative, no-follow bounded file operations"
        )


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreServiceError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreServiceError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreServiceError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, root: Path, label: str) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreServiceError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):  # pragma: no cover - O_DIRECTORY guard
        raise DeepSeekV4HCPreServiceError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _open_relative_descriptor(root_descriptor: int, relative: str, label: str) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_descriptor = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        return os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreServiceError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)


def _safe_file(
    stack: ExitStack,
    root_descriptor: int,
    value: Any,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    relative = _safe_relative(value, label)
    descriptor = _open_relative_descriptor(root_descriptor, relative, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreServiceError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreServiceError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreServiceError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor,
        _fingerprint(metadata),
        relative,
        root_descriptor,
        metadata.st_size,
    )


def _verify_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreServiceError(f"{label} changed while it was read")
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor, source.relative_path, label
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreServiceError(f"{label} was replaced while it was read")
    finally:
        os.close(current_descriptor)


def _read_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreServiceError(f"{label} exceeds its bounded size")
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
            raise DeepSeekV4HCPreServiceError(f"cannot read {label}: {exc}") from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreServiceError(f"{label} ended while it was read")
    _verify_stable(source, label)
    return bytes(payload)


def _verify_root_stable(
    root: Path,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4HCPreServiceError(f"{label} changed during verification")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreServiceError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4HCPreServiceError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited_entries = 0

    def visit(directory_descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited_entries
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment directory depth exceeds its bound"
            )
        before = _fingerprint(os.fstat(directory_descriptor))
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreServiceError(
                f"cannot enumerate deployment directory {prefix or '.'!r}: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > _MAX_TREE_ENTRIES:
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment entry count exceeds its bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreServiceError(
                    "HC_PRE deployment contains an unsafe directory entry"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(
                    name, dir_fd=directory_descriptor, follow_symlinks=False
                )
            except OSError as exc:
                raise DeepSeekV4HCPreServiceError(
                    f"cannot inspect deployment entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
                continue
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    child = os.open(name, flags, dir_fd=directory_descriptor)
                except OSError as exc:
                    raise DeepSeekV4HCPreServiceError(
                        f"cannot open deployment directory {relative!r}: {exc}"
                    ) from exc
                try:
                    visit(child, relative, depth + 1)
                finally:
                    os.close(child)
                continue
            raise DeepSeekV4HCPreServiceError(
                f"deployment entry {relative!r} is not a regular file or directory"
            )
        if _fingerprint(os.fstat(directory_descriptor)) != before:
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment changed during directory enumeration"
            )

    visit(root_descriptor, "", 0)
    return files, directories


def _expected_semantic(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "architectural_outputs": {
            "branch": {"dtype": "BF16", "shape": "[batch,sequence,4096]"},
            "comb": {"dtype": "F32", "shape": "[batch,sequence,4,4]"},
            "post": {"dtype": "F32", "shape": "[batch,sequence,4]"},
            "residual": {
                "dtype": "BF16",
                "shape": "[batch,sequence,4,4096]",
            },
        },
        "claim_boundary": (
            "Complete learned-parameter and numeric-contract package for one "
            "layer-0 attention HC_PRE site; contains no activation, result, or "
            "execution evidence."
        ),
        "model_id": MODEL_ID,
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "operation": {
            "base_resource": BASE_NAME,
            "input": "x_bf16[batch,sequence,4,4096]",
            "kind": "HC_PRE",
            "projection_resource": PROJECTION_NAME,
            "scale_resource": SCALE_NAME,
        },
        "schema": SEMANTIC_SCHEMA,
        "site": dict(_SITE),
        "source": dict(source),
    }


def _expected_numeric_profile() -> dict[str, Any]:
    return {
        "arithmetic_order": {
            "branch_reduction": "balanced_(p0_plus_p1)_plus_(p2_plus_p3)",
            "field_affine": "separate_binary32_multiply_then_add",
            "nonlinear": "correctly_rounded_binary32_sigmoid_and_exp",
            "projection": "increasing_k_exact_product_single_rne_product_add",
            "rms_reduction": "balanced_14_level_binary32_rne",
            "sinkhorn": "stable_softmax_column_then_19_row_column_pairs",
        },
        "constants": {
            "hc_epsilon_binary32": HC_PRE_SINKHORN_EPSILON_BINARY32,
            "norm_epsilon_binary32": HC_PRE_NORM_EPSILON_BINARY32,
        },
        "dimensions": {
            "combination_destinations": HC_PRE_HC_MULT,
            "combination_sources": HC_PRE_HC_MULT,
            "flattened_width": HC_PRE_FLATTENED_WIDTH,
            "hc_multiplier": HC_PRE_HC_MULT,
            "hidden_size": HC_PRE_WIDTH,
            "mix_fields": HC_PRE_MIX_FIELDS,
            "post_fields": HC_PRE_HC_MULT,
            "pre_fields": HC_PRE_HC_MULT,
            "sinkhorn_iterations": HC_PRE_SINKHORN_ITERATIONS,
        },
        "encodings": {
            "branch_and_residual": "BF16",
            "byte_order": "little",
            "coefficients_and_parameters": "F32",
            "input": "BF16",
        },
        "exception_policy": {
            "command_commit": "atomic_across_all_batch_times_sequence_tokens",
            "finite_branch_saturation": "final_bf16_conversion_only_and_counted",
            "nonfinite_or_boundary_overflow": "poison_without_partial_commit",
            "subnormals": "preserved_no_ftz_or_daz",
        },
        "profile_id": NUMERIC_PROFILE_ID,
        "runtime_axes": {
            "batch": "positive_dynamic",
            "sequence": "positive_dynamic",
            "token_count": "batch_times_sequence",
        },
        "schema": NUMERIC_PROFILE_SCHEMA,
        "source_boundary": {
            "backend_bit_equivalence": "not_claimed",
            "kernel_source_sha256": KERNEL_SOURCE_SHA256,
            "model_source_sha256": MODEL_SOURCE_SHA256,
        },
        "specification": {
            "document": "SPEC-NUM",
            "requirement": "NUM-6.10",
            "version": "1.1",
        },
    }


def _expected_counter_contract() -> dict[str, Any]:
    return {
        "command_scaling": {
            "fixed_counters": "per_token_coefficient_times_batch_times_sequence",
            "poisoned_command": "no_success_counter_commit",
            "saturation_counter": "exact_observed_final_bf16_clamp_count",
        },
        "data_dependent": {
            "hc_pre_branch_bf16_saturations": {
                "maximum_per_token": HC_PRE_WIDTH,
                "minimum_per_token": 0,
            }
        },
        "evidence_boundary": (
            "Semantic reconciliation coefficients only; not instruction, traffic, "
            "cycle, throughput, energy, area, or PPA evidence."
        ),
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "per_successfully_committed_token": {
            "hc_pre_branch_bf16_conversions": 4096,
            "hc_pre_branch_coefficient_multiplies": 16384,
            "hc_pre_branch_reduction_adds": 12288,
            "hc_pre_coefficient_epsilon_adds": 4,
            "hc_pre_exp_evaluations": 16,
            "hc_pre_field_affine_adds": 24,
            "hc_pre_field_affine_multiplies": 24,
            "hc_pre_input_bf16_values": 16384,
            "hc_pre_post_factor_multiplies": 4,
            "hc_pre_projection_product_accumulates": 393216,
            "hc_pre_projection_rms_multiplies": 24,
            "hc_pre_residual_bf16_values_preserved": 16384,
            "hc_pre_rms_divides": 1,
            "hc_pre_rms_epsilon_adds": 1,
            "hc_pre_rms_reduction_adds": 16383,
            "hc_pre_rms_square_multiplies": 16384,
            "hc_pre_rsqrt_evaluations": 1,
            "hc_pre_sigmoid_evaluations": 8,
            "hc_pre_sinkhorn_column_reduction_adds": 240,
            "hc_pre_sinkhorn_column_stages": 20,
            "hc_pre_sinkhorn_divides": 640,
            "hc_pre_sinkhorn_epsilon_adds": 172,
            "hc_pre_sinkhorn_row_reduction_adds": 240,
            "hc_pre_sinkhorn_row_stages": 20,
            "hc_pre_softmax_max_comparisons": 12,
            "hc_pre_softmax_subtracts": 16,
        },
        "schema": COUNTER_CONTRACT_SCHEMA,
        "specification": "SPEC-NUM 1.1 NUM-6.10.6",
    }


def _expected_coverage() -> dict[str, Any]:
    return {
        "execution_coverage": "none",
        "model_id": MODEL_ID,
        "numeric_contract_coverage": "SPEC-NUM 1.1 NUM-6.10",
        "packaged_operator_kind": "HC_PRE",
        "parameter_coverage": "all_three_learned_resources_for_one_site",
        "schema": COVERAGE_SCHEMA,
        "site": dict(_SITE),
        "status": "complete_operator_artifact_contract_not_execution_evidence",
    }


def _source_identity(value: Any) -> dict[str, Any]:
    source = _exact_keys(
        value,
        {
            "application_id",
            "application_status",
            "checkpoint_lock_id",
            "evidence_scope",
            "repository",
            "revision",
            "verification_id",
        },
        "HC_PRE deployment source",
    )
    result = dict(source)
    _digest(result["application_id"], "source.application_id")
    _digest(result["verification_id"], "source.verification_id")
    expected = {
        "application_id": result["application_id"],
        "application_status": OFFICIAL_APPLICATION_STATUS,
        "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
        "evidence_scope": OFFICIAL_EVIDENCE_SCOPE,
        "repository": OFFICIAL_REPOSITORY,
        "revision": OFFICIAL_REVISION,
        "verification_id": result["verification_id"],
    }
    if not _json_equal(result, expected):
        raise DeepSeekV4HCPreServiceError(
            "HC_PRE deployment is not the pinned official checkpoint identity"
        )
    return result


def _artifact_size_bound(role: str) -> tuple[int | None, int]:
    exact = {
        "hc_base_parameter": BASE_BYTES,
        "hc_projection_parameter": PROJECTION_BYTES,
        "hc_scale_parameter": SCALE_BYTES,
    }.get(role)
    return exact, exact if exact is not None else _MAX_JSON_BYTES


def _f32_codes(payload: bytes, expected_count: int, label: str) -> tuple[int, ...]:
    if len(payload) != expected_count * 4:
        raise DeepSeekV4HCPreServiceError(
            f"{label} has {len(payload)} bytes, expected {expected_count * 4}"
        )
    result: list[int] = []
    for index, (code,) in enumerate(struct.iter_unpack("<I", payload)):
        if code & 0x7F800000 == 0x7F800000:
            raise DeepSeekV4HCPreServiceError(
                f"{label} contains nonfinite binary32 at element {index}"
            )
        # The artifact snapshot preserves the official payload bits.  The
        # numeric core canonicalizes signed zero only when arithmetic consumes
        # the value.
        result.append(code)
    return tuple(result)


def _resource_record(
    value: Any,
    *,
    resource: str,
    name: str,
    shape: tuple[int, ...],
    size_bytes: int,
    role: str,
    artifact: HCPreArtifactRecord,
) -> Mapping[str, Any]:
    record = _exact_keys(
        value,
        {
            "content_address",
            "dtype",
            "encoding",
            "layout",
            "memory_map",
            "name",
            "path",
            "replicated_ranks",
            "sha256",
            "shape",
            "size_bytes",
            "source_assignment_paths",
        },
        f"tensor_manifest.{resource}",
    )
    digest = _digest(record["sha256"], f"tensor_manifest.{resource}.sha256")
    expected_path = f"payloads/sha256/{digest}.f32le"
    source_paths = [f"ranks/rank-{rank:03d}/{name}.bin" for rank in range(4)]
    expected = {
        "content_address": f"sha256:{digest}",
        "dtype": "F32",
        "encoding": "ieee754_binary32_little_endian",
        "layout": "c_contiguous_row_major",
        "memory_map": {"length_bytes": size_bytes, "offset_bytes": 0},
        "name": name,
        "path": expected_path,
        "replicated_ranks": [0, 1, 2, 3],
        "sha256": digest,
        "shape": list(shape),
        "size_bytes": size_bytes,
        "source_assignment_paths": source_paths,
    }
    if not _json_equal(record, expected):
        raise DeepSeekV4HCPreServiceError(
            f"tensor_manifest.{resource} differs from its official F32 identity"
        )
    if (
        artifact.role != role
        or artifact.relative_path != expected_path
        or artifact.sha256 != digest
        or artifact.size_bytes != size_bytes
    ):
        raise DeepSeekV4HCPreServiceError(
            f"tensor_manifest.{resource} differs from its artifact record"
        )
    return record


def _expected_roundtrip(
    source: Mapping[str, Any], resources: tuple[HCPreParameterResource, ...]
) -> dict[str, Any]:
    reconstructed = []
    for resource in resources:
        reconstructed.append(
            {
                "deployment_path": resource.relative_path,
                "dtype": "F32",
                "replicated_ranks": [0, 1, 2, 3],
                "sha256": resource.sha256,
                "shape": list(resource.shape),
                "size_bytes": resource.size_bytes,
                "source_assignment_paths": [
                    f"ranks/rank-{rank:03d}/{resource.name}.bin" for rank in range(4)
                ],
                "tensor_name": resource.name,
            }
        )
    body: dict[str, Any] = {
        "application_id": source["application_id"],
        "checked_artifact_count": 3,
        "checked_payload_bytes": TOTAL_PARAMETER_BYTES,
        "checked_replica_count": 12,
        "checked_replica_payload_bytes": TOTAL_PARAMETER_BYTES * MODEL_PARALLEL,
        "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
        "model_id": MODEL_ID,
        "reconstructed": reconstructed,
        "schema": ROUNDTRIP_SCHEMA,
        "status": "byte_exact_full_parameter_roundtrip",
    }
    body["roundtrip_id"] = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
    return body


def load_deepseek_v4_hc_pre_artifact_deployment(
    deployment_dir: Path,
) -> DeepSeekV4HCPreArtifactDeployment:
    """Verify and snapshot the current non-executable official v1 package."""

    root = Path(deployment_dir).absolute()
    with ExitStack() as stack:
        root_descriptor, root_fingerprint = _open_root(
            stack, root, "HC_PRE deployment root"
        )
        manifest_file = _safe_file(
            stack,
            root_descriptor,
            "deployment_manifest.json",
            "HC_PRE deployment manifest",
            maximum_size=_MAX_JSON_BYTES,
        )
        manifest_payload = _read_bytes(
            manifest_file, "HC_PRE deployment manifest", _MAX_JSON_BYTES
        )
        manifest = _strict_json(manifest_payload, "HC_PRE deployment manifest")
        _exact_keys(
            manifest,
            {
                "artifacts",
                "build_id",
                "claim_boundary",
                "compiler",
                "entrypoint",
                "model_id",
                "numeric_profile_id",
                "schema",
                "site",
                "source",
                "status",
            },
            "HC_PRE deployment manifest",
        )
        source = _source_identity(manifest["source"])
        expected_manifest_metadata = {
            "claim_boundary": _CLAIM_BOUNDARY,
            "compiler": _COMPILER,
            "entrypoint": _ENTRYPOINT,
            "model_id": MODEL_ID,
            "numeric_profile_id": NUMERIC_PROFILE_ID,
            "schema": DEPLOYMENT_SCHEMA,
            "site": _SITE,
            "status": OFFICIAL_DEPLOYMENT_STATUS,
        }
        observed_manifest_metadata = {
            key: manifest[key] for key in expected_manifest_metadata
        }
        if not _json_equal(observed_manifest_metadata, expected_manifest_metadata):
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment metadata or non-execution claim boundary differs"
            )

        raw_artifacts = manifest["artifacts"]
        if not isinstance(raw_artifacts, list) or len(raw_artifacts) != 9:
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment must enumerate exactly nine v1 artifacts"
            )
        observed_records: list[dict[str, Any]] = []
        records: list[HCPreArtifactRecord] = []
        files_by_role: dict[str, _StableFile] = {}
        payloads_by_role: dict[str, bytes] = {}
        paths: set[str] = set()
        previous_path: str | None = None
        for index, raw_record in enumerate(raw_artifacts):
            record = _exact_keys(
                raw_record,
                {"path", "role", "sha256", "size_bytes"},
                f"artifacts[{index}]",
            )
            relative = _safe_relative(record["path"], f"artifacts[{index}].path")
            role = record["role"]
            if not isinstance(role, str) or role not in _ARTIFACT_ROLES:
                raise DeepSeekV4HCPreServiceError(
                    f"artifacts[{index}].role is not in the closed v1 role set"
                )
            if role in files_by_role or relative in paths:
                raise DeepSeekV4HCPreServiceError(
                    "HC_PRE artifact roles and paths must be unique"
                )
            if previous_path is not None and relative <= previous_path:
                raise DeepSeekV4HCPreServiceError(
                    "HC_PRE artifact table is not strictly path-sorted"
                )
            previous_path = relative
            paths.add(relative)
            digest = _digest(record["sha256"], f"artifacts[{index}].sha256")
            exact_size, maximum_size = _artifact_size_bound(role)
            size = _integer(
                record["size_bytes"],
                f"artifacts[{index}].size_bytes",
                minimum=1,
                maximum=maximum_size,
            )
            if exact_size is not None and size != exact_size:
                raise DeepSeekV4HCPreServiceError(
                    f"artifact role {role!r} has {size} bytes, expected {exact_size}"
                )
            source_file = _safe_file(
                stack,
                root_descriptor,
                relative,
                f"artifact {relative!r}",
                exact_size=size,
                maximum_size=maximum_size,
            )
            payload = _read_bytes(source_file, f"artifact {relative!r}", maximum_size)
            if hashlib.sha256(payload).hexdigest() != digest:
                raise DeepSeekV4HCPreServiceError(
                    f"artifact {relative!r} differs from its deployment hash"
                )
            immutable = HCPreArtifactRecord(relative, role, digest, size)
            records.append(immutable)
            files_by_role[role] = source_file
            payloads_by_role[role] = payload
            observed_records.append(dict(record))
        if set(files_by_role) != _ARTIFACT_ROLES:
            raise DeepSeekV4HCPreServiceError("HC_PRE artifact role closure differs")
        for role, expected_path in _FIXED_JSON_PATHS.items():
            if (
                next(item.relative_path for item in records if item.role == role)
                != expected_path
            ):
                raise DeepSeekV4HCPreServiceError(
                    f"HC_PRE artifact role {role!r} has a noncanonical path"
                )

        identity = {
            "artifacts": observed_records,
            "compiler": _COMPILER,
            "model_id": MODEL_ID,
            "numeric_profile_id": NUMERIC_PROFILE_ID,
            "site": _SITE,
            "source": source,
        }
        build_id = _digest(manifest["build_id"], "deployment.build_id")
        if hashlib.sha256(_canonical_json_bytes(identity)).hexdigest() != build_id:
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment build_id does not bind its artifacts"
            )

        json_by_role = {
            role: _strict_json(payloads_by_role[role], f"HC_PRE {role}")
            for role in _JSON_ROLES
        }
        if not _json_equal(json_by_role["semantic_ir"], _expected_semantic(source)):
            raise DeepSeekV4HCPreServiceError("HC_PRE semantic IR differs")
        if not _json_equal(
            json_by_role["numeric_profile"], _expected_numeric_profile()
        ):
            raise DeepSeekV4HCPreServiceError("HC_PRE numeric profile differs")
        counter_contract = _expected_counter_contract()
        if not _json_equal(json_by_role["counter_contract"], counter_contract):
            raise DeepSeekV4HCPreServiceError("HC_PRE counter contract differs")
        if not _json_equal(json_by_role["operator_coverage"], _expected_coverage()):
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE coverage must retain its explicit non-execution boundary"
            )

        tensor_manifest = json_by_role["tensor_manifest"]
        _exact_keys(
            tensor_manifest,
            {
                "base",
                "model_parallel",
                "projection",
                "scale",
                "schema",
                "total_unique_payload_bytes",
            },
            "HC_PRE tensor manifest",
        )
        tensor_header = {
            "model_parallel": tensor_manifest["model_parallel"],
            "schema": tensor_manifest["schema"],
            "total_unique_payload_bytes": tensor_manifest["total_unique_payload_bytes"],
        }
        expected_tensor_header = {
            "model_parallel": MODEL_PARALLEL,
            "schema": TENSOR_SCHEMA,
            "total_unique_payload_bytes": TOTAL_PARAMETER_BYTES,
        }
        if not _json_equal(tensor_header, expected_tensor_header):
            raise DeepSeekV4HCPreServiceError("HC_PRE tensor manifest header differs")
        artifact_by_role = {item.role: item for item in records}
        _resource_record(
            tensor_manifest["base"],
            resource="base",
            name=BASE_NAME,
            shape=BASE_SHAPE,
            size_bytes=BASE_BYTES,
            role="hc_base_parameter",
            artifact=artifact_by_role["hc_base_parameter"],
        )
        _resource_record(
            tensor_manifest["projection"],
            resource="projection",
            name=PROJECTION_NAME,
            shape=PROJECTION_SHAPE,
            size_bytes=PROJECTION_BYTES,
            role="hc_projection_parameter",
            artifact=artifact_by_role["hc_projection_parameter"],
        )
        _resource_record(
            tensor_manifest["scale"],
            resource="scale",
            name=SCALE_NAME,
            shape=SCALE_SHAPE,
            size_bytes=SCALE_BYTES,
            role="hc_scale_parameter",
            artifact=artifact_by_role["hc_scale_parameter"],
        )

        base_codes = _f32_codes(
            payloads_by_role["hc_base_parameter"], HC_PRE_MIX_FIELDS, "HC_PRE base"
        )
        projection_flat = _f32_codes(
            payloads_by_role["hc_projection_parameter"],
            HC_PRE_MIX_FIELDS * HC_PRE_FLATTENED_WIDTH,
            "HC_PRE projection",
        )
        projection_codes = tuple(
            projection_flat[
                row * HC_PRE_FLATTENED_WIDTH : (row + 1) * HC_PRE_FLATTENED_WIDTH
            ]
            for row in range(HC_PRE_MIX_FIELDS)
        )
        scale_codes = _f32_codes(
            payloads_by_role["hc_scale_parameter"], 3, "HC_PRE scale"
        )
        base = HCPreParameterResource(
            BASE_NAME,
            "hc_base_parameter",
            BASE_SHAPE,
            artifact_by_role["hc_base_parameter"].relative_path,
            artifact_by_role["hc_base_parameter"].sha256,
            BASE_BYTES,
            base_codes,
        )
        projection = HCPreParameterResource(
            PROJECTION_NAME,
            "hc_projection_parameter",
            PROJECTION_SHAPE,
            artifact_by_role["hc_projection_parameter"].relative_path,
            artifact_by_role["hc_projection_parameter"].sha256,
            PROJECTION_BYTES,
            projection_codes,
        )
        scale = HCPreParameterResource(
            SCALE_NAME,
            "hc_scale_parameter",
            SCALE_SHAPE,
            artifact_by_role["hc_scale_parameter"].relative_path,
            artifact_by_role["hc_scale_parameter"].sha256,
            SCALE_BYTES,
            scale_codes,
        )
        if not _json_equal(
            json_by_role["roundtrip_report"],
            _expected_roundtrip(source, (base, projection, scale)),
        ):
            raise DeepSeekV4HCPreServiceError("HC_PRE roundtrip report differs")

        actual_files, actual_directories = _enumerate_tree(root_descriptor)
        expected_directories = {"payloads", "payloads/sha256"}
        if actual_files != paths | {"deployment_manifest.json"} or (
            actual_directories != expected_directories
        ):
            raise DeepSeekV4HCPreServiceError(
                "HC_PRE deployment contains an unlisted, missing, or nonregular entry"
            )
        for source_file in (manifest_file, *files_by_role.values()):
            _verify_stable(source_file, f"guarded file {source_file.relative_path!r}")
        _verify_root_stable(
            root,
            root_descriptor,
            root_fingerprint,
            "HC_PRE deployment root",
        )

        coefficients = counter_contract["per_successfully_committed_token"]
        return DeepSeekV4HCPreArtifactDeployment(
            root=root,
            build_id=build_id,
            application_id=source["application_id"],
            verification_id=source["verification_id"],
            artifacts=tuple(records),
            base=base,
            projection=projection,
            scale=scale,
            counter_coefficients=tuple(sorted(coefficients.items())),
            required_microcode_sha256=_EXPECTED_PROGRAM_SHA256,
            required_microcode_size_bytes=len(_EXPECTED_PROGRAM_BYTES),
            required_program_contract_id=_PROGRAM_CONTRACT_ID,
            integration_requirements=EXECUTABLE_INTEGRATION_REQUIREMENTS,
        )


class DeepSeekV4HCPreServiceEngine:
    """Fail-closed service facade for the current parameter-only deployment."""

    def __init__(self, deployment: DeepSeekV4HCPreArtifactDeployment):
        if not isinstance(deployment, DeepSeekV4HCPreArtifactDeployment):
            raise DeepSeekV4HCPreServiceError("HC_PRE deployment snapshot is invalid")
        self.deployment = deployment

    @classmethod
    def load(cls, deployment_dir: Path) -> DeepSeekV4HCPreServiceEngine:
        return cls(load_deepseek_v4_hc_pre_artifact_deployment(deployment_dir))

    def execute(self, request_path: Path) -> NoReturn:
        """Reject before reading a request because v1 has no request authority."""

        del request_path
        requirements = "; ".join(self.deployment.integration_requirements)
        raise DeepSeekV4HCPreServiceError(
            "HC_PRE deployment v1 is parameter-only and declares "
            "execution_coverage=none; execution requires " + requirements
        )


def execute_deepseek_v4_hc_pre_deployment(
    deployment_dir: Path, request_path: Path
) -> NoReturn:
    """Verify v1 completely, then fail closed at its non-execution boundary."""

    return DeepSeekV4HCPreServiceEngine.load(deployment_dir).execute(request_path)


__all__ = [
    "BASE_BYTES",
    "BASE_NAME",
    "BASE_SHAPE",
    "COVERAGE_SCHEMA",
    "COUNTER_CONTRACT_SCHEMA",
    "DEPLOYMENT_SCHEMA",
    "EXECUTABLE_INTEGRATION_REQUIREMENTS",
    "HCPreArtifactRecord",
    "HCPreParameterResource",
    "MODEL_ID",
    "NUMERIC_PROFILE_ID",
    "NUMERIC_PROFILE_SCHEMA",
    "OFFICIAL_CHECKPOINT_LOCK_ID",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "PROJECTION_BYTES",
    "PROJECTION_NAME",
    "PROJECTION_SHAPE",
    "ROUNDTRIP_SCHEMA",
    "SCALE_BYTES",
    "SCALE_NAME",
    "SCALE_SHAPE",
    "SEMANTIC_SCHEMA",
    "TENSOR_SCHEMA",
    "DeepSeekV4HCPreArtifactDeployment",
    "DeepSeekV4HCPreServiceEngine",
    "DeepSeekV4HCPreServiceError",
    "execute_deepseek_v4_hc_pre_deployment",
    "load_deepseek_v4_hc_pre_artifact_deployment",
]
