"""Package the exact DeepSeek V4 ``HC_PRE`` program without claiming execution.

This layer deliberately wraps the independently checked parameter-only HC_PRE
deployment.  It adds the committed shared-ABI program, deterministic
disassembly, typed program contract, logical schedule, and independent schedule
certificate.  It does not accept or emit activations, expected results, runtime
callbacks, fallback arithmetic, or execution evidence.

Publication is descriptor-anchored and create-once inside a caller-trusted
output parent.  Concurrent mutation by a process with the same filesystem
identity remains outside that trust boundary.  Namespace publication is
atomic; this package makes no crash-durability claim for an unflushed parent
directory.
"""

from __future__ import annotations

from contextlib import ExitStack
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import stat
from typing import Any

from compiler.checking.deepseek_v4_hc_pre_executable import (
    verify_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.checking.deepseek_v4_hc_pre_schedule import (
    verify_deepseek_v4_hc_pre_logical_schedule,
    verify_deepseek_v4_hc_pre_logical_schedule_certificate,
)
from compiler.checking.deepseek_v4_hc_pre_slice import (
    verify_deepseek_v4_hc_pre_deployment,
)
from compiler.frontend.deepseek_v4 import MODEL_ID
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_hc_pre import (
    assemble,
    build_program_contract,
    disassemble,
    encode,
    verify,
    verify_program_contract,
)
from compiler.scheduling.deepseek_v4_hc_pre import (
    build_deepseek_v4_hc_pre_logical_schedule,
)
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    build_deepseek_v4_hc_pre_deployment,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable.v1"
COMPILER_NAME = "opentallas-deepseek-v4-hc-pre-executable-packager"
COMPILER_VERSION = "0.1.0"
DEPLOYMENT_STATUS = "program_packaged_execution_not_yet_evidenced"
MANIFEST_FILENAME = "deployment_manifest.json"
PARAMETER_DIRECTORY = "parameters"
PROGRAM_BYTES = 136

CLAIM_BOUNDARY = [
    "Packages the exact HC_PRE plus COMPLETE program, deterministic disassembly, hash-bound program contract, independently checked logical schedule and certificate, and all three verified F32 parameter resources.",
    "Program packaged, execution not yet evidenced.",
    "Contains no activation, expected result, callback, fallback arithmetic, runtime execution, or execution-success claim.",
    "The logical schedule establishes instruction order, register causality, and resource identity only; it establishes no cycles, latency, bandwidth, throughput, energy, area, density, routing, or PPA result.",
    "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
]

ENTRYPOINT = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": ("schedule/logical_schedule_certificate.json"),
    "parameter_deployment": "parameters/deployment_manifest.json",
    "program": "program/hc_pre.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/hc_pre.disassembly.txt",
}

_PARAMETER_ROLES = {
    "counter_contract": "parameter_counter_contract",
    "hc_base_parameter": "hc_base_parameter",
    "hc_projection_parameter": "hc_projection_parameter",
    "hc_scale_parameter": "hc_scale_parameter",
    "numeric_profile": "parameter_numeric_profile",
    "operator_coverage": "parameter_operator_coverage",
    "roundtrip_report": "parameter_roundtrip_report",
    "semantic_ir": "parameter_semantic_ir",
    "tensor_manifest": "parameter_tensor_manifest",
}
_ADDITIONAL_ROLES = {
    "execution_coverage.json": "execution_coverage",
    "interfaces/execution_request_v1.schema.json": "execution_request_schema",
    "interfaces/execution_result_v1.schema.json": "execution_result_schema",
    "parameters/deployment_manifest.json": "parameter_deployment_manifest",
    "program/hc_pre.bin": "microcode_program",
    "program/hc_pre.disassembly.txt": "microcode_disassembly",
    "program/program_contract.json": "program_contract",
    "schedule/logical_schedule.json": "logical_schedule",
    "schedule/logical_schedule_certificate.json": "logical_schedule_certificate",
}
_EXPECTED_ROLES = frozenset(_PARAMETER_ROLES.values()) | frozenset(
    _ADDITIONAL_ROLES.values()
)
_READ_CHUNK_BYTES = 1024 * 1024
_MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
_MAX_CLEANUP_ENTRIES = 64
_MAX_TREE_DEPTH = 8
_MINIMUM_FREE_BYTES = 16 * 1024 * 1024
_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_ID_ROOT = (
    "https://opentallas.org/schemas/compiler/deepseek_v4_hc_pre_executable"
)
_SHA256_PATTERN = "^[0-9a-f]{64}$"
_PROGRAM_SHA256 = "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
EXECUTION_REQUEST_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_request.v1"
EXECUTION_RESULT_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_result.v1"
EXECUTION_COVERAGE_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable_coverage.v1"


class DeepSeekV4HCPreExecutableBuildError(RuntimeError):
    """Raised when an exact HC_PRE executable package cannot be published."""


def _shape_schema(*suffix: int) -> dict[str, Any]:
    return {
        "items": False,
        "maxItems": 2 + len(suffix),
        "minItems": 2 + len(suffix),
        "prefixItems": [
            {"maximum": 4, "minimum": 1, "type": "integer"},
            {"maximum": 4, "minimum": 1, "type": "integer"},
            *({"const": extent} for extent in suffix),
        ],
        "type": "array",
    }


def _artifact_descriptor_schema(
    *,
    identifier: str,
    dtype: str,
    encoding: str,
    suffix: tuple[int, ...],
    minimum_size: int,
    maximum_size: int,
    size_multiple: int,
    register: str | None,
    path: str,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "dtype": {"const": dtype},
        "encoding": {"const": encoding},
        "id": {"const": identifier},
        "path": {"const": path},
        "sha256": {"$ref": "#/$defs/sha256"},
        "shape": _shape_schema(*suffix),
        "size_bytes": {
            "maximum": maximum_size,
            "minimum": minimum_size,
            "multipleOf": size_multiple,
            "type": "integer",
        },
    }
    required = [
        "dtype",
        "encoding",
        "id",
        "path",
        "sha256",
        "shape",
        "size_bytes",
    ]
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
        "$defs": {
            "inputDescriptor": _artifact_descriptor_schema(
                identifier="hc_hidden",
                dtype="BF16",
                encoding="bfloat16_little_endian",
                suffix=(4, 4096),
                minimum_size=32_768,
                maximum_size=131_072,
                size_multiple=32_768,
                register="HC_HIDDEN",
                path="input/hc_hidden.bf16le",
            ),
            "sha256": {"pattern": _SHA256_PATTERN, "type": "string"},
        },
        "$id": f"{_SCHEMA_ID_ROOT}/execution_request_v1.schema.json",
        "$schema": _DRAFT_2020_12,
        "additionalProperties": False,
        "properties": {
            "batch_size": {"maximum": 4, "minimum": 1, "type": "integer"},
            "build_id": {"$ref": "#/$defs/sha256"},
            "input": {"$ref": "#/$defs/inputDescriptor"},
            "model_id": {"const": MODEL_ID},
            "program_sha256": {"const": _PROGRAM_SHA256},
            "schema": {"const": EXECUTION_REQUEST_SCHEMA},
            "sequence_length": {
                "maximum": 4,
                "minimum": 1,
                "type": "integer",
            },
            "token_count": {"maximum": 4, "minimum": 1, "type": "integer"},
        },
        "required": [
            "batch_size",
            "build_id",
            "input",
            "model_id",
            "program_sha256",
            "schema",
            "sequence_length",
            "token_count",
        ],
        "title": "OpenTallas DeepSeek V4 HC_PRE execution request v1",
        "type": "object",
    }


def _execution_result_schema() -> dict[str, Any]:
    bf16 = "bfloat16_little_endian"
    f32 = "ieee754_binary32_little_endian"
    descriptor_arguments = {
        "attentionInput": (
            "attention_input",
            "BF16",
            bf16,
            (4096,),
            8_192,
            32_768,
            8_192,
            "ATTENTION_INPUT",
            "outputs/attention_input.bf16le",
        ),
        "attentionPre": (
            "attention_pre",
            "F32",
            f32,
            (4,),
            16,
            64,
            16,
            "ATTENTION_PRE",
            "outputs/attention_pre.f32le",
        ),
        "attentionPost": (
            "attention_post",
            "F32",
            f32,
            (4,),
            16,
            64,
            16,
            "ATTENTION_POST",
            "outputs/attention_post.f32le",
        ),
        "attentionCombination": (
            "attention_combination",
            "F32",
            f32,
            (4, 4),
            64,
            256,
            64,
            "ATTENTION_COMBINATION",
            "outputs/attention_combination.f32le",
        ),
        "attentionResidual": (
            "attention_residual",
            "BF16",
            bf16,
            (4, 4096),
            32_768,
            131_072,
            32_768,
            "ATTENTION_RESIDUAL",
            "outputs/attention_residual.bf16le",
        ),
        "rmsMeanCodes": (
            "rms_mean_codes",
            "F32",
            f32,
            (),
            4,
            16,
            4,
            None,
            "diagnostics/rms_mean.f32le",
        ),
        "rmsInverseCodes": (
            "rms_inverse_codes",
            "F32",
            f32,
            (),
            4,
            16,
            4,
            None,
            "diagnostics/rms_inverse.f32le",
        ),
        "projectionCodes": (
            "projection_codes",
            "F32",
            f32,
            (24,),
            96,
            384,
            96,
            None,
            "diagnostics/projection.f32le",
        ),
        "mixCodes": (
            "mix_codes",
            "F32",
            f32,
            (24,),
            96,
            384,
            96,
            None,
            "diagnostics/mix.f32le",
        ),
        "stableSoftmaxCodes": (
            "stable_softmax_codes",
            "F32",
            f32,
            (4, 4),
            64,
            256,
            64,
            None,
            "diagnostics/stable_softmax.f32le",
        ),
    }
    definitions: dict[str, Any] = {
        name: _artifact_descriptor_schema(
            identifier=arguments[0],
            dtype=arguments[1],
            encoding=arguments[2],
            suffix=arguments[3],
            minimum_size=arguments[4],
            maximum_size=arguments[5],
            size_multiple=arguments[6],
            register=arguments[7],
            path=arguments[8],
        )
        for name, arguments in descriptor_arguments.items()
    }
    counter_names = [
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
    ]
    definitions.update(
        {
            "diagnostics": {
                "additionalProperties": False,
                "properties": {
                    "mix_codes": {"$ref": "#/$defs/mixCodes"},
                    "projection_codes": {"$ref": "#/$defs/projectionCodes"},
                    "rms_inverse_codes": {"$ref": "#/$defs/rmsInverseCodes"},
                    "rms_mean_codes": {"$ref": "#/$defs/rmsMeanCodes"},
                    "stable_softmax_codes": {"$ref": "#/$defs/stableSoftmaxCodes"},
                },
                "required": [
                    "mix_codes",
                    "projection_codes",
                    "rms_inverse_codes",
                    "rms_mean_codes",
                    "stable_softmax_codes",
                ],
                "type": "object",
            },
            "numericStatus": {
                "additionalProperties": False,
                "properties": {
                    "branch_saturation_count": {
                        "maximum": 16_384,
                        "minimum": 0,
                        "type": "integer",
                    },
                    "poison": {"const": False},
                },
                "required": ["branch_saturation_count", "poison"],
                "type": "object",
            },
            "logicalCounters": {
                "additionalProperties": False,
                "properties": {
                    name: {"minimum": 0, "type": "integer"} for name in counter_names
                },
                "required": counter_names,
                "type": "object",
            },
            "sha256": {"pattern": _SHA256_PATTERN, "type": "string"},
        }
    )
    return {
        "$defs": definitions,
        "$id": f"{_SCHEMA_ID_ROOT}/execution_result_v1.schema.json",
        "$schema": _DRAFT_2020_12,
        "additionalProperties": False,
        "allOf": [
            {
                "else": {
                    "properties": {
                        "deployment_status": {
                            "const": "development_fixture_complete_hc_pre_parameters_not_release_evidence"
                        },
                        "source_application_status": {
                            "const": "development_fixture_application_not_release_evidence"
                        },
                    }
                },
                "if": {
                    "properties": {"evidence_scope": {"const": "official_checkpoint"}},
                    "required": ["evidence_scope"],
                },
                "then": {
                    "properties": {
                        "deployment_status": {
                            "const": "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
                        },
                        "source_application_status": {
                            "const": "partial_official_transform_application_not_release_evidence"
                        },
                    }
                },
            }
        ],
        "properties": {
            "batch_size": {"maximum": 4, "minimum": 1, "type": "integer"},
            "build_id": {"$ref": "#/$defs/sha256"},
            "counter_reconciliation": {"const": "exact"},
            "deployment_status": {
                "enum": [
                    "development_fixture_complete_hc_pre_parameters_not_release_evidence",
                    "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence",
                ]
            },
            "diagnostics": {"$ref": "#/$defs/diagnostics"},
            "evidence_scope": {"enum": ["development_fixture", "official_checkpoint"]},
            "execution_scope": {"const": "exact_hc_pre_site_only"},
            "model_id": {"const": MODEL_ID},
            "numeric_status": {"$ref": "#/$defs/numericStatus"},
            "outputs": {
                "items": False,
                "maxItems": 5,
                "minItems": 5,
                "prefixItems": [
                    {"$ref": "#/$defs/attentionInput"},
                    {"$ref": "#/$defs/attentionPre"},
                    {"$ref": "#/$defs/attentionPost"},
                    {"$ref": "#/$defs/attentionCombination"},
                    {"$ref": "#/$defs/attentionResidual"},
                ],
                "type": "array",
            },
            "program_sha256": {"const": _PROGRAM_SHA256},
            "request_sha256": {"$ref": "#/$defs/sha256"},
            "schema": {"const": EXECUTION_RESULT_SCHEMA},
            "logical_counters": {"$ref": "#/$defs/logicalCounters"},
            "sequence_length": {
                "maximum": 4,
                "minimum": 1,
                "type": "integer",
            },
            "source_application_status": {
                "enum": [
                    "development_fixture_application_not_release_evidence",
                    "partial_official_transform_application_not_release_evidence",
                ]
            },
            "status": {"const": "pass"},
            "token_count": {"maximum": 4, "minimum": 1, "type": "integer"},
        },
        "required": [
            "batch_size",
            "build_id",
            "counter_reconciliation",
            "deployment_status",
            "diagnostics",
            "evidence_scope",
            "execution_scope",
            "model_id",
            "numeric_status",
            "outputs",
            "program_sha256",
            "request_sha256",
            "schema",
            "logical_counters",
            "sequence_length",
            "source_application_status",
            "status",
            "token_count",
        ],
        "title": "OpenTallas DeepSeek V4 HC_PRE artifact-only execution result v1",
        "type": "object",
    }


def _execution_coverage() -> dict[str, Any]:
    return {
        "execution_evidence": "none",
        "model_id": MODEL_ID,
        "parameter_coverage": "all_three_verified_f32_resources",
        "program_execution_authority": "complete",
        "program_scope": "exact_hc_pre_plus_complete_for_one_layer_0_attention_site",
        "request_schema": EXECUTION_REQUEST_SCHEMA,
        "result_schema": EXECUTION_RESULT_SCHEMA,
        "schedule_coverage": (
            "exact_two_slot_logical_schedule_with_independent_certificate"
        ),
        "schema": EXECUTION_COVERAGE_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "status": "program_authority_complete_execution_evidence_none",
    }


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
        raise DeepSeekV4HCPreExecutableBuildError(
            "platform lacks race-resistant bounded executable-package operations"
        )


def _safe_relative(value: Any, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreExecutableBuildError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreExecutableBuildError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, root: Path, label: str) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableBuildError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _verify_root_binding(root: Path, descriptor: int, label: str) -> None:
    held = os.fstat(descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
            raise DeepSeekV4HCPreExecutableBuildError(
                f"{label} was replaced while the package was built"
            )
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
        name = f".hc-pre-executable.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"cannot create private executable-package directory: {exc}"
            ) from exc
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise DeepSeekV4HCPreExecutableBuildError(
                f"cannot open private executable-package directory: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise DeepSeekV4HCPreExecutableBuildError(
                "private executable-package path is not a directory"
            )
        return parent / name, name, descriptor
    raise DeepSeekV4HCPreExecutableBuildError(
        "cannot reserve a collision-free executable-package directory"
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
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot safely reopen temporary executable package for cleanup: {exc}"
        ) from exc
    current = os.fstat(current_descriptor)
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
        held.st_dev,
        held.st_ino,
    ):
        os.close(current_descriptor)
        raise DeepSeekV4HCPreExecutableBuildError(
            "refusing to clean a replaced temporary executable package"
        )

    visited = 0

    def remove_contents(directory_descriptor: int, depth: int) -> None:
        nonlocal visited
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreExecutableBuildError(
                "temporary executable-package cleanup exceeds its depth bound"
            )
        try:
            names = os.listdir(directory_descriptor)
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"cannot enumerate temporary executable package: {exc}"
            ) from exc
        visited += len(names)
        if visited > _MAX_CLEANUP_ENTRIES:
            raise DeepSeekV4HCPreExecutableBuildError(
                "temporary executable-package cleanup exceeds its entry bound"
            )
        for child_name in names:
            if (
                child_name in {"", ".", ".."}
                or "/" in child_name
                or "\x00" in child_name
            ):
                raise DeepSeekV4HCPreExecutableBuildError(
                    "temporary executable package contains an unsafe entry"
                )
            try:
                metadata = os.stat(
                    child_name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
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
            except OSError as exc:
                raise DeepSeekV4HCPreExecutableBuildError(
                    f"cannot remove temporary entry {child_name!r}: {exc}"
                ) from exc

    try:
        remove_contents(current_descriptor, 0)
    finally:
        os.close(current_descriptor)
    try:
        os.rmdir(name, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot remove temporary executable package: {exc}"
        ) from exc


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
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)


def _write_exclusive_bytes(
    root_descriptor: int,
    relative: str,
    payload: bytes,
) -> None:
    if type(payload) is not bytes:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"artifact {relative!r} payload is not exact bytes"
        )
    parts = Path(_safe_relative(relative, "generated artifact path")).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_descriptor = os.dup(root_descriptor)
    descriptor: int | None = None
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                directory_flags,
                dir_fd=directory_descriptor,
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
                raise DeepSeekV4HCPreExecutableBuildError(
                    f"generated artifact {relative!r} ended while being written"
                )
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            raise DeepSeekV4HCPreExecutableBuildError(
                f"generated artifact {relative!r} is not a complete regular file"
            )
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot write generated artifact {relative!r}: {exc}"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_descriptor)


def _artifact_record(
    root_descriptor: int,
    relative: str,
    role: str,
) -> dict[str, Any]:
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        f"executable artifact {relative!r}",
    )
    try:
        metadata = os.fstat(descriptor)
        fingerprint = _fingerprint(metadata)
        if not stat.S_ISREG(metadata.st_mode):
            raise DeepSeekV4HCPreExecutableBuildError(
                f"executable artifact {relative!r} is not a regular file"
            )
        if not 1 <= metadata.st_size <= _MAX_ARTIFACT_BYTES:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"executable artifact {relative!r} exceeds its bounded size"
            )
        digest = hashlib.sha256()
        offset = 0
        while offset < metadata.st_size:
            try:
                chunk = os.pread(
                    descriptor,
                    min(_READ_CHUNK_BYTES, metadata.st_size - offset),
                    offset,
                )
            except OSError as exc:
                raise DeepSeekV4HCPreExecutableBuildError(
                    f"cannot hash executable artifact {relative!r}: {exc}"
                ) from exc
            if not chunk:
                break
            digest.update(chunk)
            offset += len(chunk)
        if (
            offset != metadata.st_size
            or _fingerprint(os.fstat(descriptor)) != fingerprint
        ):
            raise DeepSeekV4HCPreExecutableBuildError(
                f"executable artifact {relative!r} changed while it was hashed"
            )
    finally:
        os.close(descriptor)

    current_descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        f"executable artifact {relative!r}",
    )
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"executable artifact {relative!r} was replaced while it was hashed"
            )
    finally:
        os.close(current_descriptor)
    return {
        "path": relative,
        "role": role,
        "sha256": digest.hexdigest(),
        "size_bytes": metadata.st_size,
    }


def _parameter_artifact_roles(parameter_manifest: dict[str, Any]) -> dict[str, str]:
    artifacts = parameter_manifest.get("artifacts")
    if type(artifacts) is not list or len(artifacts) != len(_PARAMETER_ROLES):
        raise DeepSeekV4HCPreExecutableBuildError(
            "verified parameter deployment does not enumerate exactly nine artifacts"
        )
    roles: dict[str, str] = {
        "parameters/deployment_manifest.json": "parameter_deployment_manifest"
    }
    observed_parameter_roles: set[str] = set()
    for index, raw_record in enumerate(artifacts):
        if type(raw_record) is not dict or set(raw_record) != {
            "path",
            "role",
            "sha256",
            "size_bytes",
        }:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"verified parameter artifact {index} has a moving interface"
            )
        raw_path = _safe_relative(
            raw_record["path"], f"verified parameter artifact {index}.path"
        )
        raw_role = raw_record["role"]
        if type(raw_role) is not str or raw_role not in _PARAMETER_ROLES:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"verified parameter artifact {index} has an unknown role"
            )
        observed_parameter_roles.add(raw_role)
        prefixed = f"parameters/{raw_path}"
        if prefixed in roles:
            raise DeepSeekV4HCPreExecutableBuildError(
                "verified parameter deployment repeats an artifact path"
            )
        roles[prefixed] = _PARAMETER_ROLES[raw_role]
    if observed_parameter_roles != set(_PARAMETER_ROLES):
        raise DeepSeekV4HCPreExecutableBuildError(
            "verified parameter deployment role closure differs"
        )
    roles.update(
        {
            path: role
            for path, role in _ADDITIONAL_ROLES.items()
            if path != "parameters/deployment_manifest.json"
        }
    )
    if len(roles) != 18 or set(roles.values()) != _EXPECTED_ROLES:
        raise DeepSeekV4HCPreExecutableBuildError(
            "executable artifact path or role closure differs"
        )
    return roles


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
            raise DeepSeekV4HCPreExecutableBuildError(
                f"output already exists: {output}"
            )
        if error not in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
            raise DeepSeekV4HCPreExecutableBuildError(
                f"cannot publish executable package atomically: {os.strerror(error)}"
            )
    raise DeepSeekV4HCPreExecutableBuildError(
        "platform lacks atomic rename-without-replacement support"
    )


def _build_into(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    root: Path,
    root_descriptor: int,
) -> dict[str, Any]:
    try:
        parameter_manifest = build_deepseek_v4_hc_pre_deployment(
            snapshot=snapshot,
            lock=lock,
            application_root=application_root,
            output=root / PARAMETER_DIRECTORY,
        )
        parameter_integrity = verify_deepseek_v4_hc_pre_deployment(
            root / PARAMETER_DIRECTORY,
            application_root,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot build and independently verify parameter deployment: {exc}"
        ) from exc

    parameter_build_id = parameter_manifest.get("build_id")
    if (
        type(parameter_build_id) is not str
        or parameter_integrity.get("build_id") != parameter_build_id
        or type(parameter_integrity.get("checked_artifact_count")) is not int
        or parameter_integrity["checked_artifact_count"] != 9
    ):
        raise DeepSeekV4HCPreExecutableBuildError(
            "parameter builder and independent checker identities differ"
        )

    try:
        os.mkdir("program", 0o700, dir_fd=root_descriptor)
        os.mkdir("schedule", 0o700, dir_fd=root_descriptor)
        os.mkdir("interfaces", 0o700, dir_fd=root_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"cannot create executable artifact directories: {exc}"
        ) from exc

    instructions = assemble()
    verify(instructions)
    program = encode(instructions)
    if type(program) is not bytes or len(program) != PROGRAM_BYTES:
        raise DeepSeekV4HCPreExecutableBuildError(
            "committed HC_PRE program does not have its exact 136-byte identity"
        )
    program_contract = build_program_contract()
    verify_program_contract(program_contract)
    program_disassembly = disassemble(instructions).encode("ascii")

    schedule = build_deepseek_v4_hc_pre_logical_schedule()
    certificate = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
    verify_deepseek_v4_hc_pre_logical_schedule_certificate(certificate, schedule)

    request_schema = _execution_request_schema()
    result_schema = _execution_result_schema()
    generated = {
        "execution_coverage.json": canonical_json_bytes(_execution_coverage()),
        "interfaces/execution_request_v1.schema.json": canonical_json_bytes(
            request_schema
        ),
        "interfaces/execution_result_v1.schema.json": canonical_json_bytes(
            result_schema
        ),
        "program/hc_pre.bin": program,
        "program/hc_pre.disassembly.txt": program_disassembly,
        "program/program_contract.json": canonical_json_bytes(program_contract),
        "schedule/logical_schedule.json": canonical_json_bytes(schedule),
        "schedule/logical_schedule_certificate.json": canonical_json_bytes(certificate),
    }
    for relative, payload in generated.items():
        _write_exclusive_bytes(root_descriptor, relative, payload)

    roles_by_path = _parameter_artifact_roles(parameter_manifest)
    artifacts = [
        _artifact_record(root_descriptor, relative, roles_by_path[relative])
        for relative in sorted(roles_by_path)
    ]
    source = parameter_manifest.get("source")
    site = parameter_manifest.get("site")
    if type(source) is not dict or type(site) is not dict:
        raise DeepSeekV4HCPreExecutableBuildError(
            "verified parameter deployment source or site interface differs"
        )
    body = {
        "artifacts": artifacts,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
        "entrypoint": dict(ENTRYPOINT),
        "model_id": MODEL_ID,
        "parameter_build_id": parameter_build_id,
        "program_contract_id": program_contract["contract_id"],
        "program_sha256": hashlib.sha256(program).hexdigest(),
        "schedule_certificate_id": certificate["certificate_id"],
        "schedule_id": schedule["schedule_id"],
        "schema": DEPLOYMENT_SCHEMA,
        "site": dict(site),
        "source": dict(source),
        "status": DEPLOYMENT_STATUS,
    }
    deployment = {
        **body,
        "build_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }
    _write_exclusive_bytes(
        root_descriptor,
        MANIFEST_FILENAME,
        canonical_json_bytes(deployment),
    )
    try:
        integrity = verify_deepseek_v4_hc_pre_executable_deployment(
            root,
            application_root,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        raise DeepSeekV4HCPreExecutableBuildError(
            f"independent executable-package verification failed: {exc}"
        ) from exc
    if integrity.get("build_id") != deployment["build_id"]:
        raise DeepSeekV4HCPreExecutableBuildError(
            "executable builder and independent checker identities differ"
        )
    return deployment


def build_deepseek_v4_hc_pre_executable_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
) -> dict[str, Any]:
    """Build, independently verify, and create-once publish the HC_PRE program."""

    _require_secure_file_operations()
    snapshot = Path(snapshot)
    application_root = Path(application_root).absolute()
    raw_output = Path(output)
    if not raw_output.name or raw_output.name in {".", ".."}:
        raise DeepSeekV4HCPreExecutableBuildError(
            "output must name a specific directory"
        )
    if os.path.lexists(raw_output):
        raise DeepSeekV4HCPreExecutableBuildError(
            f"output already exists: {raw_output}"
        )
    output = raw_output.resolve()
    if output == Path(output.anchor):
        raise DeepSeekV4HCPreExecutableBuildError(
            "output must not be a filesystem root"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < _MINIMUM_FREE_BYTES:
        raise DeepSeekV4HCPreExecutableBuildError(
            "HC_PRE executable package lacks its bounded free-space reserve"
        )

    with ExitStack() as stack:
        parent_descriptor, _ = _open_root(
            stack,
            output.parent,
            "HC_PRE executable output parent",
        )
        _verify_root_binding(
            output.parent,
            parent_descriptor,
            "HC_PRE executable output parent",
        )
        temporary, temporary_name, temporary_descriptor = _create_private_directory(
            stack,
            parent=output.parent,
            parent_descriptor=parent_descriptor,
        )
        published = False
        try:
            _verify_root_binding(
                temporary,
                temporary_descriptor,
                "HC_PRE temporary executable deployment",
            )
            deployment = _build_into(
                snapshot=snapshot,
                lock=lock,
                application_root=application_root,
                root=temporary,
                root_descriptor=temporary_descriptor,
            )
            _verify_root_binding(
                temporary,
                temporary_descriptor,
                "HC_PRE temporary executable deployment",
            )
            _verify_root_binding(
                output.parent,
                parent_descriptor,
                "HC_PRE executable output parent",
            )
            _publish_create_once(
                parent_descriptor=parent_descriptor,
                temporary_name=temporary_name,
                output_name=output.name,
                output=output,
            )
            published = True
            _verify_root_binding(
                output.parent,
                parent_descriptor,
                "HC_PRE executable output parent",
            )
            _verify_root_binding(
                output,
                temporary_descriptor,
                "published HC_PRE executable deployment",
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
    "MANIFEST_FILENAME",
    "PROGRAM_BYTES",
    "DeepSeekV4HCPreExecutableBuildError",
    "build_deepseek_v4_hc_pre_executable_deployment",
]
