"""Production artifact-only execution of the frozen Query-A fragment.

The service accepts exactly one official DeepSeek-V4-Flash-0731 executable
package and a separately composed HC_PRE-derived request.  Every artifact is
opened beneath a held directory descriptor, bounded, hashed, and kept open for
the complete transaction.  Results are published as one create-once tree.

The returned logical counters describe functional work only.  This module
does not claim cycles, bandwidth, latency, physical scheduling, PPA,
full-model execution, or a comparison with NVIDIA hardware.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
from types import MappingProxyType
from typing import Any, NoReturn
import zlib

from .query_a_numeric import (
    HIDDEN_SIZE,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    QUERY_A_BLOCK_COUNT,
    QUERY_A_OUTPUT_FEATURES,
    QueryAServiceNumericError,
    QueryAServiceNumericResult,
    execute_complete_query_a,
    query_a_functional_counters,
)
from .secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    SecureFile,
    canonical_json_bytes,
    parse_canonical_json,
    publish_payload_tree,
)


MODEL_ID = "deepseek-v4-flash-0731"
EXECUTABLE_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_query_a_executable.v1"
EXECUTABLE_STATUS = "official_checkpoint_program_packaged_execution_not_evidenced"
EXECUTION_REQUEST_SCHEMA = "opentallas.deepseek_v4_query_a_execution_request.v1"
EXECUTION_RESULT_SCHEMA = "opentallas.deepseek_v4_query_a_execution_result.v1"
RESOURCE_MANIFEST_SCHEMA = "opentallas.deepseek_v4_query_a_resources.v1"
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_query_a_program.v1"
LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_query_a_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_query_a_logical_schedule_certificate.v1"
)
COUNTER_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_query_a_functional_counter_contract.v1"
)
EXECUTION_COVERAGE_SCHEMA = "opentallas.deepseek_v4_query_a_executable_coverage.v1"

EXECUTABLE_BUILD_ID = "0ad1cad42f0b5f4b002f824db8cc9d52ab9becbff04b6488dfe44dc7992d4a58"
PROGRAM_SHA256 = "91f43d7e0b28cdf1b825aaeb005ef3d45f01d862622067b693e56f8669593710"
PROGRAM_CONTRACT_ID = "0aa1969479c527d33fa893557f40dd05e3efbc9a3e1af7d959d4cb8496806903"
RESOURCE_MANIFEST_ID = (
    "5c271d4a348e907ae97f6bbc33848248dffdb16c70d8636ed834685acc2c7d8c"
)
SCHEDULE_ID = "2673d8ef4e62df0ec1441c1b14eeb6a207b246a70a987adadfe354a418711e13"
SCHEDULE_CERTIFICATE_ID = (
    "d2a6e754abc7440dc341e00fac4bf7e48f9e53659f971fdfbb03c4782c47b546"
)
FUNCTIONAL_COUNTER_CONTRACT_ID = (
    "a50495f14025022af0313830b920db0a71d9815f267e91057efd114afb74a1fa"
)
HC_PRE_EXECUTABLE_BUILD_ID = (
    "7c2adb319710357ec2faeb941d74c8fed3cfa815ec8986d29e6c190b30ff00ea"
)

PROGRAM_BYTES = 196
_MAX_JSON_BYTES = 512 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_TREE_ENTRIES = 32
_MAX_TREE_DEPTH = 4
_MAX_REQUEST_BYTES = MAX_TOKEN_COUNT * HIDDEN_SIZE * 2
_EXPECTED_PACKAGE_DIRECTORIES = {"interfaces", "program", "resources", "schedule"}
_EXPECTED_REQUEST_DIRECTORIES = {"input"}
_EXPECTED_RESULT_DIRECTORIES = {"diagnostics", "outputs"}

_PROGRAM_HEADER = struct.Struct("<4sBBHII")
_PROGRAM_RECORD = struct.Struct("<BBH14I")
_PROGRAM_MAGIC = b"OTEQ"
_PROGRAM_ABI = (1, 0)
_UNUSED = 0xFFFFFFFF
_OPCODE_RMS_NORM = 20
_OPCODE_FP8_LINEAR = 32
_OPCODE_COMPLETE = 255

_ENTRYPOINT = {
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

_CLAIM_BOUNDARY_SHA256 = (
    "8374f017d91d242040b06b953609a7c21287b690d3aea0ef600cf5b254547d48"
)

_REQUIRED_NONCLAIMS = {
    "attention_completion",
    "checkpoint_execution",
    "cycle_accuracy",
    "full_model_execution",
    "hc_pre_execution",
    "nvidia_comparison",
    "physical_schedule",
    "ppa",
    "query_b",
    "rtl_execution",
    "transformer_block_completion",
}


@dataclass(frozen=True)
class _RoleSpec:
    path: str
    size_bytes: int
    sha256: str


_ROLE_SPECS: Mapping[str, _RoleSpec] = MappingProxyType(
    {
        "attention_norm_weight": _RoleSpec(
            "resources/attn_norm_weight.bf16le",
            8192,
            "2628db36b6aa28c06121bb01f2d8e0f6acf9d240393af7a91ae5073b0acb5772",
        ),
        "execution_coverage": _RoleSpec(
            "execution_coverage.json",
            803,
            "a793e1e9b3bdd96b14eed3ae3e19723df00af409d2fc06d7a96de2f1a9b3a5e1",
        ),
        "execution_request_schema": _RoleSpec(
            "interfaces/execution_request_v1.schema.json",
            2479,
            "866d6c3c7b8b6c7f50c970870043d9a152974eb996a6adad258805cfb83dd12c",
        ),
        "execution_result_schema": _RoleSpec(
            "interfaces/execution_result_v1.schema.json",
            6659,
            "eef58f08b8f1ee4bb6773bed394306a2edbd720ce676d9d9b3b1324d5ca6d6d7",
        ),
        "exhaustive_output_rows": _RoleSpec(
            "resources/query_a_exhaustive_rows.u32le",
            4096,
            "c89db7222126863309183fc023c7091fb18392d16a397dac76a96a022cd62cef",
        ),
        "functional_counter_contract": _RoleSpec(
            "interfaces/functional_counter_contract.json",
            1509,
            "1eb4605f10b898d4ac3d1379934c3246a2813a11c82370d53ad76c7c0825a383",
        ),
        "logical_schedule": _RoleSpec(
            "schedule/logical_schedule.json",
            4805,
            "1f2237dfdb6ecb5766678ad960a34ff09d441676a1f20b39c3248e243d3b7c08",
        ),
        "logical_schedule_certificate": _RoleSpec(
            "schedule/logical_schedule_certificate.json",
            1797,
            "a5ccf12b531fbad2a9ec86a81b63cb5f4898c2298503c42fe384f6bf47b30404",
        ),
        "microcode_disassembly": _RoleSpec(
            "program/query_a.disassembly.txt",
            639,
            "8bb73c0d445e315ef76e94ba99f37e32b4185943463583c71c825c1ff79c7cb1",
        ),
        "microcode_program": _RoleSpec(
            "program/query_a.bin",
            PROGRAM_BYTES,
            PROGRAM_SHA256,
        ),
        "program_contract": _RoleSpec(
            "program/program_contract.json",
            1318,
            "a8f0d21f1b1daa01a5acfcac8f05a1b74e71988af195ecb58fd85e3a13127a02",
        ),
        "query_a_scale": _RoleSpec(
            "resources/query_a_scale.e8m0",
            256,
            "aea19c77d256ca30999de59a811b152a2dfc82673a43877d9cd67b80578bc5e2",
        ),
        "query_a_weight": _RoleSpec(
            "resources/query_a_weight.f8e4m3fn",
            4_194_304,
            "d8646783efb3c0bda83bcd2c64b03cb25d1677d27b0c45ffe143a4175922932c",
        ),
        "resource_manifest": _RoleSpec(
            "resources/resource_manifest.json",
            3516,
            "3d9acf04b60e116823d9abef2426a529b37d10bfe706444fc2dbd5d97c9321a4",
        ),
    }
)


class DeepSeekV4QueryAExecutableServiceError(RuntimeError):
    """Raised when a Query-A service transaction must fail closed."""


@dataclass(frozen=True)
class QueryAExecutableArtifactRecord:
    relative_path: str
    role: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class QueryAInstruction:
    opcode: int
    destinations: tuple[int, ...]
    source: int
    resources: tuple[int, ...]
    immediates: tuple[int, ...]

    @property
    def opcode_name(self) -> str:
        return {
            _OPCODE_RMS_NORM: "RMS_NORM",
            _OPCODE_FP8_LINEAR: "FP8_LINEAR",
            _OPCODE_COMPLETE: "COMPLETE",
        }[self.opcode]


def _expected_program_instructions() -> tuple[QueryAInstruction, ...]:
    return (
        QueryAInstruction(
            _OPCODE_RMS_NORM,
            (8, _UNUSED, _UNUSED, _UNUSED, _UNUSED),
            3,
            (7, _UNUSED, _UNUSED, _UNUSED),
            (HIDDEN_SIZE, 0x358637BD, 0, 0),
        ),
        QueryAInstruction(
            _OPCODE_FP8_LINEAR,
            (9, _UNUSED, _UNUSED, _UNUSED, _UNUSED),
            8,
            (8, 9, 10, _UNUSED),
            (QUERY_A_OUTPUT_FEATURES, 128, 0, 0),
        ),
        QueryAInstruction(
            _OPCODE_COMPLETE,
            (_UNUSED, _UNUSED, _UNUSED, _UNUSED, _UNUSED),
            _UNUSED,
            (_UNUSED, _UNUSED, _UNUSED, _UNUSED),
            (0, 0, 0, 0),
        ),
    )


def _poison(message: str, cause: BaseException | None = None) -> NoReturn:
    if cause is None:
        raise DeepSeekV4QueryAExecutableServiceError(message)
    raise DeepSeekV4QueryAExecutableServiceError(message) from cause


def _exact_object(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _poison(f"{label} must be an exact object")
    observed = set(value)
    if observed != fields:
        _poison(
            f"{label} fields differ: missing={sorted(fields - observed)}, "
            f"unknown={sorted(observed - fields)}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _poison(f"{label} is not a lowercase SHA-256")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _poison(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _parse_object(
    payload: bytes, label: str, maximum_bytes: int = _MAX_JSON_BYTES
) -> dict[str, Any]:
    value = parse_canonical_json(payload, label=label, maximum_bytes=maximum_bytes)
    if type(value) is not dict:
        _poison(f"{label} must be an object")
    return value


def _derived_identity(value: Mapping[str, Any], field: str, label: str) -> str:
    identity = _digest(value.get(field), f"{label}.{field}")
    body = {key: value[key] for key in value if key != field}
    if hashlib.sha256(canonical_json_bytes(body)).hexdigest() != identity:
        _poison(f"{label} {field} does not bind its complete body")
    return identity


def _require_nonclaims(value: object, label: str) -> None:
    if type(value) is not list or any(type(item) is not str for item in value):
        _poison(f"{label} must be a string list")
    if not _REQUIRED_NONCLAIMS <= set(value):
        _poison(f"{label} omits a required claim boundary")


def _decode_exact_program(payload: bytes) -> tuple[QueryAInstruction, ...]:
    if type(payload) is not bytes or len(payload) != PROGRAM_BYTES:
        _poison("Query-A program must be the exact 196-byte ABI payload")
    if hashlib.sha256(payload).hexdigest() != PROGRAM_SHA256:
        _poison("Query-A program SHA-256 differs")
    magic, major, minor, record_bytes, count, body_crc = _PROGRAM_HEADER.unpack_from(
        payload
    )
    if (
        magic != _PROGRAM_MAGIC
        or (major, minor) != _PROGRAM_ABI
        or record_bytes != _PROGRAM_RECORD.size
        or count != 3
    ):
        _poison("Query-A program ABI header differs")
    body = payload[_PROGRAM_HEADER.size :]
    if len(body) != count * _PROGRAM_RECORD.size:
        _poison("Query-A program body length differs")
    if zlib.crc32(body) & 0xFFFFFFFF != body_crc:
        _poison("Query-A program body CRC32 differs")

    decoded: list[QueryAInstruction] = []
    for index in range(count):
        raw = _PROGRAM_RECORD.unpack_from(body, index * _PROGRAM_RECORD.size)
        opcode, flags, reserved = raw[:3]
        if flags != 0 or reserved != 0:
            _poison(f"Query-A instruction {index} has unsupported control bits")
        operands = raw[3:]
        decoded.append(
            QueryAInstruction(
                opcode=opcode,
                destinations=tuple(operands[:5]),
                source=operands[5],
                resources=tuple(operands[6:10]),
                immediates=tuple(operands[10:14]),
            )
        )

    expected = _expected_program_instructions()
    if tuple(decoded) != expected:
        _poison("Query-A program is not exact RMS_NORM, FP8_LINEAR, COMPLETE")
    return expected


def _verify_interface_schema(
    value: Mapping[str, Any],
    *,
    instance_schema: str,
    filename: str,
    label: str,
) -> None:
    properties = value.get("properties")
    if (
        value.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or value.get("$id")
        != (
            "https://opentallas.org/schemas/compiler/"
            f"deepseek_v4_query_a_executable/{filename}"
        )
        or value.get("type") != "object"
        or value.get("additionalProperties") is not False
        or type(properties) is not dict
        or properties.get("schema") != {"const": instance_schema}
    ):
        _poison(f"{label} outer identity differs")


def _verify_counter_contract(value: Mapping[str, Any]) -> None:
    if _derived_identity(value, "contract_id", "functional counter contract") != (
        FUNCTIONAL_COUNTER_CONTRACT_ID
    ):
        _poison("functional counter contract identity differs")
    coefficients = value.get("per_token_coefficients")
    fixed = value.get("fixed_counters")
    if (
        value.get("schema") != COUNTER_CONTRACT_SCHEMA
        or value.get("model_id") != MODEL_ID
        or value.get("token_count_minimum") != MIN_TOKEN_COUNT
        or value.get("token_count_maximum") != MAX_TOKEN_COUNT
        or type(coefficients) is not dict
        or type(fixed) is not dict
    ):
        _poison("functional counter contract metadata differs")
    for token_count in range(MIN_TOKEN_COUNT, MAX_TOKEN_COUNT + 1):
        packaged = {
            name: coefficient * token_count
            for name, coefficient in coefficients.items()
            if type(name) is str and type(coefficient) is int
        }
        packaged.update(fixed)
        if packaged != query_a_functional_counters(token_count):
            _poison("functional counter contract differs from service arithmetic")


def _verify_resource_manifest(value: Mapping[str, Any]) -> None:
    if _derived_identity(value, "manifest_id", "resource manifest") != (
        RESOURCE_MANIFEST_ID
    ):
        _poison("resource manifest identity differs")
    resources = value.get("resources")
    tensor_contract = value.get("tensor_contract")
    if (
        value.get("schema") != RESOURCE_MANIFEST_SCHEMA
        or value.get("model_id") != MODEL_ID
        or type(resources) is not list
        or len(resources) != 4
        or type(tensor_contract) is not dict
    ):
        _poison("resource manifest outer contract differs")

    expected_resources = (
        (7, "ATTN_NORM_WEIGHT", "BF16", [4096], 8192, "attention_norm_weight"),
        (
            8,
            "QUERY_A_WEIGHT",
            "F8_E4M3",
            [1024, 4096],
            4_194_304,
            "query_a_weight",
        ),
        (9, "QUERY_A_SCALE", "F8_E8M0", [8, 32], 256, "query_a_scale"),
        (
            10,
            "QUERY_A_EXHAUSTIVE_ROWS",
            "U32",
            [1024],
            4096,
            "exhaustive_output_rows",
        ),
    )
    for index, expected in enumerate(expected_resources):
        resource = resources[index]
        if type(resource) is not dict:
            _poison(f"resource manifest entry {index} is not an object")
        resource_id, name, dtype, shape, size, role = expected
        spec = _ROLE_SPECS[role]
        observed = (
            resource.get("resource_id"),
            resource.get("resource_name"),
            resource.get("dtype"),
            resource.get("shape"),
            resource.get("size_bytes"),
            resource.get("path"),
            resource.get("sha256"),
        )
        if observed != (resource_id, name, dtype, shape, size, spec.path, spec.sha256):
            _poison(f"resource manifest entry {index} identity differs")
    registers = tensor_contract.get("registers")
    if (
        tensor_contract.get("minimum_token_count") != MIN_TOKEN_COUNT
        or tensor_contract.get("maximum_token_count") != MAX_TOKEN_COUNT
        or type(registers) is not list
        or [
            (entry.get("register_id"), entry.get("register_name"), entry.get("shape"))
            for entry in registers
            if type(entry) is dict
        ]
        != [
            (3, "ATTENTION_INPUT", ["token_count", 4096]),
            (8, "ATTENTION_NORMALIZED", ["token_count", 4096]),
            (9, "QUERY_A", ["token_count", 1024]),
        ]
    ):
        _poison("resource tensor/register contract differs")


def _verify_schedule(value: Mapping[str, Any]) -> None:
    if _derived_identity(value, "schedule_id", "logical schedule") != SCHEDULE_ID:
        _poison("logical schedule identity differs")
    identity = value.get("identity")
    slots = value.get("slots")
    if (
        value.get("schema") != LOGICAL_SCHEDULE_SCHEMA
        or type(identity) is not dict
        or identity.get("program_sha256") != PROGRAM_SHA256
        or identity.get("program_contract_id") != PROGRAM_CONTRACT_ID
        or type(slots) is not list
        or len(slots) != 3
    ):
        _poison("logical schedule program binding differs")
    observed_slots = [
        (
            slot.get("slot"),
            slot.get("instruction_index"),
            slot.get("opcode"),
            slot.get("opcode_code"),
            slot.get("terminal"),
        )
        for slot in slots
        if type(slot) is dict
    ]
    if observed_slots != [
        (0, 0, "RMS_NORM", _OPCODE_RMS_NORM, False),
        (1, 1, "FP8_LINEAR", _OPCODE_FP8_LINEAR, False),
        (2, 2, "COMPLETE", _OPCODE_COMPLETE, True),
    ]:
        _poison("logical schedule slot order differs")
    _require_nonclaims(value.get("required_nonclaims"), "schedule nonclaims")


def _verify_certificate(value: Mapping[str, Any]) -> None:
    if _derived_identity(value, "certificate_id", "schedule certificate") != (
        SCHEDULE_CERTIFICATE_ID
    ):
        _poison("logical schedule certificate identity differs")
    checks = value.get("checks")
    if (
        value.get("schema") != LOGICAL_CERTIFICATE_SCHEMA
        or value.get("schedule_id") != SCHEDULE_ID
        or value.get("program_contract_id") != PROGRAM_CONTRACT_ID
        or value.get("program_sha256") != PROGRAM_SHA256
        or value.get("status") != "pass"
        or type(checks) is not dict
        or not checks
        or any(check is not True for check in checks.values())
    ):
        _poison("logical schedule certificate contract differs")
    _require_nonclaims(value.get("required_nonclaims"), "certificate nonclaims")


def _verify_packaged_contracts(payloads: Mapping[str, bytes]) -> None:
    program_contract = _parse_object(payloads["program_contract"], "program contract")
    if (
        _derived_identity(program_contract, "contract_id", "program contract")
        != PROGRAM_CONTRACT_ID
        or program_contract.get("schema") != PROGRAM_CONTRACT_SCHEMA
        or program_contract.get("model_id") != MODEL_ID
        or program_contract.get("program_sha256") != PROGRAM_SHA256
        or program_contract.get("program_bytes") != PROGRAM_BYTES
        or program_contract.get("operator_sequence")
        != ["RMS_NORM", "FP8_LINEAR", "COMPLETE"]
        or program_contract.get("resource_ids") != [7, 8, 9, 10]
    ):
        _poison("program contract differs")
    _require_nonclaims(
        program_contract.get("required_nonclaims"), "program contract nonclaims"
    )

    coverage = _parse_object(payloads["execution_coverage"], "execution coverage")
    if (
        coverage.get("schema") != EXECUTION_COVERAGE_SCHEMA
        or coverage.get("model_id") != MODEL_ID
        or coverage.get("request_schema") != EXECUTION_REQUEST_SCHEMA
        or coverage.get("result_schema") != EXECUTION_RESULT_SCHEMA
        or coverage.get("execution_evidence") != "none"
        or coverage.get("physical_schedule_evidence") != "none"
        or coverage.get("ppa_evidence") != "none"
        or coverage.get("program_execution_authority") != "complete"
    ):
        _poison("execution coverage boundary differs")

    request_schema = _parse_object(
        payloads["execution_request_schema"], "execution request schema"
    )
    _verify_interface_schema(
        request_schema,
        instance_schema=EXECUTION_REQUEST_SCHEMA,
        filename="execution_request_v1.schema.json",
        label="execution request schema",
    )
    result_schema = _parse_object(
        payloads["execution_result_schema"], "execution result schema"
    )
    _verify_interface_schema(
        result_schema,
        instance_schema=EXECUTION_RESULT_SCHEMA,
        filename="execution_result_v1.schema.json",
        label="execution result schema",
    )

    _verify_counter_contract(
        _parse_object(
            payloads["functional_counter_contract"],
            "functional counter contract",
        )
    )
    _verify_resource_manifest(
        _parse_object(payloads["resource_manifest"], "resource manifest")
    )
    _verify_schedule(_parse_object(payloads["logical_schedule"], "logical schedule"))
    _verify_certificate(
        _parse_object(
            payloads["logical_schedule_certificate"],
            "logical schedule certificate",
        )
    )


def _decode_bf16(payload: bytes, *, label: str) -> tuple[int, ...]:
    if len(payload) % 2:
        _poison(f"{label} has a partial BF16 element")
    result = tuple(code for (code,) in struct.iter_unpack("<H", payload))
    for index, code in enumerate(result):
        if code & 0x7F80 == 0x7F80:
            _poison(f"{label} contains nonfinite BF16 at element {index}")
    return result


def _validate_resource_codes(
    norm_codes: Sequence[int],
    weight_payload: bytes,
    scale_payload: bytes,
    rows_payload: bytes,
) -> tuple[tuple[int, ...], tuple[int, ...], bytes, tuple[int, ...]]:
    if len(norm_codes) != HIDDEN_SIZE:
        _poison("attention norm resource shape differs")
    poison_weight = next(
        (index for index, code in enumerate(weight_payload) if code & 0x7F == 0x7F),
        None,
    )
    if poison_weight is not None:
        _poison(f"Query-A weight contains E4M3FN NaN at element {poison_weight}")
    poison_scale = scale_payload.find(b"\xff")
    if poison_scale >= 0:
        _poison(f"Query-A scale contains reserved E8M0 at element {poison_scale}")
    rows = tuple(code for (code,) in struct.iter_unpack("<I", rows_payload))
    if rows != tuple(range(QUERY_A_OUTPUT_FEATURES)):
        _poison("Query-A exhaustive-row resource is not exact 0 through 1023")
    return tuple(norm_codes), tuple(scale_payload), weight_payload, rows


class DeepSeekV4QueryAExecutableDeployment:
    """Held, verified package snapshot and immutable numeric resources."""

    def __init__(
        self,
        *,
        root: Path,
        artifacts: tuple[QueryAExecutableArtifactRecord, ...],
        instructions: tuple[QueryAInstruction, ...],
        norm_weight_codes: tuple[int, ...],
        weight_payload: bytes,
        scale_codes: tuple[int, ...],
        exhaustive_rows: tuple[int, ...],
        tree: SecureDirectory,
    ) -> None:
        self.root = root
        self.build_id = EXECUTABLE_BUILD_ID
        self.model_id = MODEL_ID
        self.program_sha256 = PROGRAM_SHA256
        self.program_contract_id = PROGRAM_CONTRACT_ID
        self.resource_manifest_id = RESOURCE_MANIFEST_ID
        self.schedule_id = SCHEDULE_ID
        self.schedule_certificate_id = SCHEDULE_CERTIFICATE_ID
        self.functional_counter_contract_id = FUNCTIONAL_COUNTER_CONTRACT_ID
        self.artifacts = artifacts
        self.instructions = instructions
        self.norm_weight_codes = norm_weight_codes
        self.weight_payload = weight_payload
        self.scale_codes = scale_codes
        self.exhaustive_rows = exhaustive_rows
        self._tree = tree
        self._closed = False

    def verify(self) -> None:
        if type(self._closed) is not bool or self._closed:
            _poison("Query-A executable deployment is closed")
        if type(self._tree) is not SecureDirectory or self._tree.root != self.root:
            _poison("Query-A executable deployment root snapshot differs")
        expected_metadata = (
            EXECUTABLE_BUILD_ID,
            MODEL_ID,
            PROGRAM_SHA256,
            PROGRAM_CONTRACT_ID,
            RESOURCE_MANIFEST_ID,
            SCHEDULE_ID,
            SCHEDULE_CERTIFICATE_ID,
            FUNCTIONAL_COUNTER_CONTRACT_ID,
        )
        observed_metadata = (
            self.build_id,
            self.model_id,
            self.program_sha256,
            self.program_contract_id,
            self.resource_manifest_id,
            self.schedule_id,
            self.schedule_certificate_id,
            self.functional_counter_contract_id,
        )
        if observed_metadata != expected_metadata:
            _poison("Query-A executable deployment metadata snapshot differs")
        expected_artifacts = tuple(
            QueryAExecutableArtifactRecord(
                spec.path,
                role,
                spec.sha256,
                spec.size_bytes,
            )
            for role, spec in sorted(_ROLE_SPECS.items(), key=lambda item: item[1].path)
        )
        if self.artifacts != expected_artifacts:
            _poison("Query-A executable deployment artifact snapshot differs")
        if self.instructions != _expected_program_instructions():
            _poison("Query-A executable deployment instruction snapshot differs")

        if (
            type(self.norm_weight_codes) is not tuple
            or len(self.norm_weight_codes) != HIDDEN_SIZE
            or any(
                type(code) is not int or not 0 <= code < 1 << 16
                for code in self.norm_weight_codes
            )
        ):
            _poison("Query-A executable norm-weight memory snapshot differs")
        if (
            type(self.weight_payload) is not bytes
            or len(self.weight_payload) != _ROLE_SPECS["query_a_weight"].size_bytes
            or hashlib.sha256(self.weight_payload).hexdigest()
            != _ROLE_SPECS["query_a_weight"].sha256
        ):
            _poison("Query-A executable weight memory snapshot differs")
        if (
            type(self.scale_codes) is not tuple
            or len(self.scale_codes) != _ROLE_SPECS["query_a_scale"].size_bytes
            or any(
                type(code) is not int or not 0 <= code < 1 << 8
                for code in self.scale_codes
            )
        ):
            _poison("Query-A executable scale memory snapshot differs")
        if (
            type(self.exhaustive_rows) is not tuple
            or len(self.exhaustive_rows) != QUERY_A_OUTPUT_FEATURES
            or any(
                type(code) is not int or not 0 <= code < 1 << 32
                for code in self.exhaustive_rows
            )
        ):
            _poison("Query-A executable row-selection memory snapshot differs")
        try:
            norm_payload = struct.pack(f"<{HIDDEN_SIZE}H", *self.norm_weight_codes)
            scale_payload = bytes(self.scale_codes)
            rows_payload = struct.pack(
                f"<{QUERY_A_OUTPUT_FEATURES}I", *self.exhaustive_rows
            )
        except (OverflowError, TypeError, ValueError, struct.error) as exc:
            _poison("Query-A executable memory snapshot cannot be encoded", exc)
        for role, payload in (
            ("attention_norm_weight", norm_payload),
            ("query_a_scale", scale_payload),
            ("exhaustive_output_rows", rows_payload),
        ):
            if hashlib.sha256(payload).hexdigest() != _ROLE_SPECS[role].sha256:
                _poison(f"Query-A executable {role} memory snapshot differs")
        self._tree.verify()

    def weight_row(self, row: int) -> bytes:
        if type(row) is not int or not 0 <= row < QUERY_A_OUTPUT_FEATURES:
            _poison("Query-A weight row is outside the packaged range")
        start = row * HIDDEN_SIZE
        return self.weight_payload[start : start + HIDDEN_SIZE]

    def scale_code(self, row: int, block: int) -> int:
        if (
            type(row) is not int
            or type(block) is not int
            or not 0 <= row < QUERY_A_OUTPUT_FEATURES
            or not 0 <= block < QUERY_A_BLOCK_COUNT
        ):
            _poison("Query-A scale coordinate is outside the packaged range")
        return self.scale_codes[(row // 128) * QUERY_A_BLOCK_COUNT + block]

    def close(self) -> None:
        if self._closed:
            return
        self._tree.close()
        self._closed = True

    def __enter__(self) -> DeepSeekV4QueryAExecutableDeployment:
        self.verify()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()


def _load_deployment(deployment_dir: Path) -> DeepSeekV4QueryAExecutableDeployment:
    root = Path(deployment_dir).absolute()
    tree = SecureDirectory(root, label="Query-A executable deployment")
    keep_tree = False
    try:
        manifest_file = tree.open_file(
            "deployment_manifest.json",
            label="Query-A deployment manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        manifest_payload = manifest_file.read_bytes(
            label="Query-A deployment manifest",
            maximum_bytes=_MAX_MANIFEST_BYTES,
        )
        manifest = _parse_object(
            manifest_payload,
            "Query-A deployment manifest",
            _MAX_MANIFEST_BYTES,
        )
        _exact_object(
            manifest,
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
            "Query-A deployment manifest",
        )
        build_id = _derived_identity(manifest, "build_id", "deployment manifest")
        if build_id != EXECUTABLE_BUILD_ID:
            _poison("Query-A executable is not the frozen official package build")
        claim_boundary = manifest.get("claim_boundary")
        if (
            type(claim_boundary) is not list
            or any(type(item) is not str for item in claim_boundary)
            or hashlib.sha256(canonical_json_bytes(claim_boundary)).hexdigest()
            != _CLAIM_BOUNDARY_SHA256
        ):
            _poison("Query-A deployment claim boundary differs")
        expected_metadata = {
            "compiler": {
                "name": "opentallas-deepseek-v4-query-a-executable-packager",
                "version": "0.1.0",
            },
            "entrypoint": _ENTRYPOINT,
            "functional_counter_contract_id": FUNCTIONAL_COUNTER_CONTRACT_ID,
            "model_id": MODEL_ID,
            "program_contract_id": PROGRAM_CONTRACT_ID,
            "program_sha256": PROGRAM_SHA256,
            "resource_manifest_id": RESOURCE_MANIFEST_ID,
            "schedule_certificate_id": SCHEDULE_CERTIFICATE_ID,
            "schedule_id": SCHEDULE_ID,
            "schema": EXECUTABLE_DEPLOYMENT_SCHEMA,
            "site": {"branch": "attention", "layer": 0, "scope": "main"},
            "status": EXECUTABLE_STATUS,
        }
        if any(manifest.get(key) != value for key, value in expected_metadata.items()):
            _poison("Query-A deployment identity or claim boundary differs")
        source = manifest.get("source")
        if type(source) is not dict or (
            source.get("repository") != "deepseek-ai/DeepSeek-V4-Flash-0731"
            or source.get("revision") != "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
            or source.get("evidence_scope") != "official_checkpoint"
            or source.get("rank_replica_count") != 4
        ):
            _poison("Query-A deployment official source identity differs")
        for field in (
            "application_id",
            "application_manifest_sha256",
            "checkpoint_lock_id",
            "verification_id",
            "verification_manifest_sha256",
        ):
            _digest(source.get(field), f"deployment source.{field}")

        raw_artifacts = manifest.get("artifacts")
        if type(raw_artifacts) is not list or len(raw_artifacts) != len(_ROLE_SPECS):
            _poison("Query-A deployment artifact count differs")
        records: list[QueryAExecutableArtifactRecord] = []
        sources: dict[str, SecureFile] = {}
        observed_paths: set[str] = set()
        previous_path: str | None = None
        for index, raw_record in enumerate(raw_artifacts):
            record = _exact_object(
                raw_record,
                {"path", "role", "sha256", "size_bytes"},
                f"artifacts[{index}]",
            )
            role = record.get("role")
            if type(role) is not str or role not in _ROLE_SPECS or role in sources:
                _poison(f"artifacts[{index}] role is outside the closed role set")
            spec = _ROLE_SPECS[role]
            if record != {
                "path": spec.path,
                "role": role,
                "sha256": spec.sha256,
                "size_bytes": spec.size_bytes,
            }:
                _poison(f"artifact role {role!r} differs from its frozen contract")
            if previous_path is not None and spec.path <= previous_path:
                _poison("Query-A artifact table is not strictly path sorted")
            previous_path = spec.path
            observed_paths.add(spec.path)
            artifact = tree.open_file(
                spec.path,
                label=f"Query-A artifact {spec.path!r}",
                maximum_size=spec.size_bytes,
                exact_size=spec.size_bytes,
            )
            if artifact.guarded_sha256 != spec.sha256:
                _poison(f"Query-A artifact {spec.path!r} differs from its SHA-256")
            sources[role] = artifact
            records.append(
                QueryAExecutableArtifactRecord(
                    spec.path,
                    role,
                    spec.sha256,
                    spec.size_bytes,
                )
            )
        if set(sources) != set(_ROLE_SPECS):
            _poison("Query-A deployment role closure differs")

        files, directories = tree.enumerate_tree(
            maximum_depth=_MAX_TREE_DEPTH,
            maximum_entries=_MAX_TREE_ENTRIES,
        )
        if files != observed_paths | {"deployment_manifest.json"}:
            _poison("Query-A deployment contains an unlisted or missing file")
        if directories != _EXPECTED_PACKAGE_DIRECTORIES:
            _poison("Query-A deployment directory closure differs")

        payloads: dict[str, bytes] = {}
        for role, artifact in sources.items():
            payloads[role] = artifact.read_bytes(
                label=f"Query-A artifact {artifact.relative_path!r}",
                maximum_bytes=_ROLE_SPECS[role].size_bytes,
            )
        _verify_packaged_contracts(payloads)
        instructions = _decode_exact_program(payloads["microcode_program"])
        norm_codes = _decode_bf16(
            payloads["attention_norm_weight"],
            label="attention norm resource",
        )
        norm_codes, scale_codes, weight_payload, rows = _validate_resource_codes(
            norm_codes,
            payloads["query_a_weight"],
            payloads["query_a_scale"],
            payloads["exhaustive_output_rows"],
        )
        tree.verify()
        result = DeepSeekV4QueryAExecutableDeployment(
            root=root,
            artifacts=tuple(records),
            instructions=instructions,
            norm_weight_codes=norm_codes,
            weight_payload=weight_payload,
            scale_codes=scale_codes,
            exhaustive_rows=rows,
            tree=tree,
        )
        keep_tree = True
        return result
    finally:
        if not keep_tree:
            tree.close()


def load_deepseek_v4_query_a_executable_deployment(
    deployment_dir: Path,
) -> DeepSeekV4QueryAExecutableDeployment:
    """Load and hold the sole frozen official Query-A package."""

    try:
        return _load_deployment(deployment_dir)
    except DeepSeekV4QueryAExecutableServiceError:
        raise
    except (OSError, SecureArtifactError, ValueError, struct.error) as exc:
        _poison("Query-A executable deployment verification failed", exc)


class _ExecutionRequest:
    def __init__(
        self,
        *,
        root: Path,
        tree: SecureDirectory,
        request_sha256: str,
        token_count: int,
        input_codes: tuple[tuple[int, ...], ...],
    ) -> None:
        self.root = root
        self._tree = tree
        self.request_sha256 = request_sha256
        self.token_count = token_count
        self.input_codes = input_codes
        self._closed = False

    def verify(self) -> None:
        if self._closed:
            _poison("Query-A execution request is closed")
        self._tree.verify()

    def close(self) -> None:
        if self._closed:
            return
        self._tree.close()
        self._closed = True


def _load_request(
    deployment: DeepSeekV4QueryAExecutableDeployment,
    request_manifest: Path,
) -> _ExecutionRequest:
    path = Path(request_manifest).absolute()
    if path.name != "request_manifest.json":
        _poison("Query-A request must be named request_manifest.json")
    root = path.parent
    tree = SecureDirectory(root, label="Query-A execution request")
    keep_tree = False
    try:
        manifest_file = tree.open_file(
            "request_manifest.json",
            label="Query-A request manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        manifest_payload = manifest_file.read_bytes(
            label="Query-A request manifest",
            maximum_bytes=_MAX_MANIFEST_BYTES,
        )
        request = _parse_object(
            manifest_payload,
            "Query-A request manifest",
            _MAX_MANIFEST_BYTES,
        )
        _exact_object(
            request,
            {
                "build_id",
                "input",
                "model_id",
                "program_sha256",
                "provenance",
                "schema",
                "token_count",
            },
            "Query-A request manifest",
        )
        if {
            "build_id": request.get("build_id"),
            "model_id": request.get("model_id"),
            "program_sha256": request.get("program_sha256"),
            "schema": request.get("schema"),
        } != {
            "build_id": deployment.build_id,
            "model_id": MODEL_ID,
            "program_sha256": PROGRAM_SHA256,
            "schema": EXECUTION_REQUEST_SCHEMA,
        }:
            _poison("Query-A request identity differs from its deployment")
        token_count = _integer(
            request.get("token_count"),
            "request.token_count",
            minimum=MIN_TOKEN_COUNT,
            maximum=MAX_TOKEN_COUNT,
        )

        descriptor = _exact_object(
            request.get("input"),
            {
                "dtype",
                "encoding",
                "id",
                "path",
                "register",
                "sha256",
                "shape",
                "size_bytes",
            },
            "Query-A request input descriptor",
        )
        input_sha256 = _digest(descriptor.get("sha256"), "request.input.sha256")
        size_bytes = token_count * HIDDEN_SIZE * 2
        if descriptor != {
            "dtype": "BF16",
            "encoding": "bfloat16_little_endian",
            "id": "attention_input",
            "path": "input/attention_input.bf16le",
            "register": "ATTENTION_INPUT",
            "sha256": input_sha256,
            "shape": [token_count, HIDDEN_SIZE],
            "size_bytes": size_bytes,
        }:
            _poison("Query-A request input descriptor differs")

        provenance = _exact_object(
            request.get("provenance"),
            {
                "kind",
                "source_batch_size",
                "source_build_id",
                "source_output_path",
                "source_output_sha256",
                "source_request_sha256",
                "source_result_manifest_sha256",
                "source_schema",
                "source_sequence_length",
            },
            "Query-A request provenance",
        )
        batch = _integer(
            provenance.get("source_batch_size"),
            "request.provenance.source_batch_size",
            minimum=1,
            maximum=4,
        )
        sequence = _integer(
            provenance.get("source_sequence_length"),
            "request.provenance.source_sequence_length",
            minimum=1,
            maximum=4,
        )
        for field in (
            "source_output_sha256",
            "source_request_sha256",
            "source_result_manifest_sha256",
        ):
            _digest(provenance.get(field), f"request.provenance.{field}")
        if (
            batch * sequence != token_count
            or provenance.get("kind") != "verified_hc_pre_execution_result"
            or provenance.get("source_build_id") != HC_PRE_EXECUTABLE_BUILD_ID
            or provenance.get("source_schema")
            != "opentallas.deepseek_v4_hc_pre_execution_result.v1"
            or provenance.get("source_output_path") != "outputs/attention_input.bf16le"
            or provenance.get("source_output_sha256") != input_sha256
        ):
            _poison("Query-A request HC_PRE provenance differs")

        input_file = tree.open_file(
            "input/attention_input.bf16le",
            label="Query-A request BF16 input",
            maximum_size=_MAX_REQUEST_BYTES,
            exact_size=size_bytes,
        )
        input_payload = input_file.read_bytes(
            label="Query-A request BF16 input",
            maximum_bytes=_MAX_REQUEST_BYTES,
        )
        if hashlib.sha256(input_payload).hexdigest() != input_sha256:
            _poison("Query-A request BF16 input differs from its SHA-256")
        flat = _decode_bf16(input_payload, label="Query-A request BF16 input")
        input_codes = tuple(
            tuple(flat[offset : offset + HIDDEN_SIZE])
            for offset in range(0, len(flat), HIDDEN_SIZE)
        )
        if len(input_codes) != token_count:
            _poison("Query-A request token decoding differs")

        files, directories = tree.enumerate_tree(
            maximum_depth=2,
            maximum_entries=4,
        )
        if (
            files
            != {
                "request_manifest.json",
                "input/attention_input.bf16le",
            }
            or directories != _EXPECTED_REQUEST_DIRECTORIES
        ):
            _poison("Query-A request tree closure differs")
        tree.verify()
        result = _ExecutionRequest(
            root=root,
            tree=tree,
            request_sha256=hashlib.sha256(manifest_payload).hexdigest(),
            token_count=token_count,
            input_codes=input_codes,
        )
        keep_tree = True
        return result
    finally:
        if not keep_tree:
            tree.close()


@dataclass(frozen=True)
class QueryAExecutableResult:
    build_id: str
    model_id: str
    program_sha256: str
    request_sha256: str
    token_count: int
    execution_scope: str
    status: str
    counter_reconciliation: str
    attention_normalized_codes: tuple[tuple[int, ...], ...]
    query_a_codes: tuple[tuple[int, ...], ...]
    rms_mean_codes: tuple[int, ...]
    rms_inverse_codes: tuple[int, ...]
    logical_counters: Mapping[str, int]
    numeric_status: Mapping[str, object]
    manifest: Mapping[str, object]


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(child) for key, child in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json(child) for child in value)
    return value


def _encode_u16_matrix(value: Sequence[Sequence[int]], *, label: str) -> bytes:
    flattened: list[int] = []
    for row_index, row in enumerate(value):
        for column_index, code in enumerate(row):
            if type(code) is not int or not 0 <= code < 1 << 16:
                _poison(f"{label}[{row_index}][{column_index}] is not unsigned 16-bit")
            flattened.append(code)
    return struct.pack(f"<{len(flattened)}H", *flattened)


def _encode_u32(value: Sequence[int], *, label: str) -> bytes:
    codes = tuple(value)
    if any(type(code) is not int or not 0 <= code < 1 << 32 for code in codes):
        _poison(f"{label} contains a non-U32 code")
    return struct.pack(f"<{len(codes)}I", *codes)


def _descriptor(
    *,
    identifier: str,
    path: str,
    dtype: str,
    encoding: str,
    shape: list[int],
    payload: bytes,
    register: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dtype": dtype,
        "encoding": encoding,
        "id": identifier,
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "shape": shape,
        "size_bytes": len(payload),
    }
    if register is not None:
        result["register"] = register
    return result


def _build_result(
    deployment: DeepSeekV4QueryAExecutableDeployment,
    request: _ExecutionRequest,
    numeric: QueryAServiceNumericResult,
) -> tuple[QueryAExecutableResult, dict[str, bytes], dict[str, Any]]:
    token_count = request.token_count
    if (
        len(numeric.normalized_codes) != token_count
        or any(len(row) != HIDDEN_SIZE for row in numeric.normalized_codes)
        or len(numeric.query_a_codes) != token_count
        or any(len(row) != QUERY_A_OUTPUT_FEATURES for row in numeric.query_a_codes)
        or len(numeric.mean_square_codes) != token_count
        or len(numeric.inverse_rms_codes) != token_count
    ):
        _poison("Query-A numeric result shape differs")

    payloads = {
        "diagnostics/rms_inverse.f32le": _encode_u32(
            numeric.inverse_rms_codes,
            label="rms inverse diagnostics",
        ),
        "diagnostics/rms_mean.f32le": _encode_u32(
            numeric.mean_square_codes,
            label="rms mean diagnostics",
        ),
        "outputs/attention_normalized.bf16le": _encode_u16_matrix(
            numeric.normalized_codes,
            label="attention normalized output",
        ),
        "outputs/query_a.bf16le": _encode_u16_matrix(
            numeric.query_a_codes,
            label="Query-A output",
        ),
    }
    normalized_descriptor = _descriptor(
        identifier="attention_normalized",
        path="outputs/attention_normalized.bf16le",
        dtype="BF16",
        encoding="bfloat16_little_endian",
        shape=[token_count, HIDDEN_SIZE],
        payload=payloads["outputs/attention_normalized.bf16le"],
        register="ATTENTION_NORMALIZED",
    )
    query_descriptor = _descriptor(
        identifier="query_a",
        path="outputs/query_a.bf16le",
        dtype="BF16",
        encoding="bfloat16_little_endian",
        shape=[token_count, QUERY_A_OUTPUT_FEATURES],
        payload=payloads["outputs/query_a.bf16le"],
        register="QUERY_A",
    )
    mean_descriptor = _descriptor(
        identifier="rms_mean",
        path="diagnostics/rms_mean.f32le",
        dtype="F32",
        encoding="ieee754_binary32_little_endian",
        shape=[token_count],
        payload=payloads["diagnostics/rms_mean.f32le"],
    )
    inverse_descriptor = _descriptor(
        identifier="rms_inverse",
        path="diagnostics/rms_inverse.f32le",
        dtype="F32",
        encoding="ieee754_binary32_little_endian",
        shape=[token_count],
        payload=payloads["diagnostics/rms_inverse.f32le"],
    )
    counters = query_a_functional_counters(token_count)
    numeric_status: dict[str, object] = {
        "activation_saturated_block_count": numeric.activation_saturated_block_count,
        "poison": False,
        "query_output_saturated_element_count": (
            numeric.query_output_saturated_element_count
        ),
        "rms_output_saturation_count": numeric.rms_output_saturation_count,
    }
    if (
        not 0 <= numeric.rms_output_saturation_count <= token_count * HIDDEN_SIZE
        or not 0
        <= numeric.activation_saturated_block_count
        <= token_count * QUERY_A_BLOCK_COUNT
        or not 0
        <= numeric.query_output_saturated_element_count
        <= token_count * QUERY_A_OUTPUT_FEATURES
    ):
        _poison("Query-A numeric saturation accounting differs")
    manifest: dict[str, Any] = {
        "build_id": deployment.build_id,
        "counter_reconciliation": "exact",
        "diagnostics": {
            "rms_inverse": inverse_descriptor,
            "rms_mean": mean_descriptor,
        },
        "execution_scope": "exact_complete_query_a_fragment",
        "logical_counters": counters,
        "model_id": MODEL_ID,
        "numeric_status": numeric_status,
        "outputs": [normalized_descriptor, query_descriptor],
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": request.request_sha256,
        "schema": EXECUTION_RESULT_SCHEMA,
        "status": "pass",
        "token_count": token_count,
    }
    result = QueryAExecutableResult(
        build_id=deployment.build_id,
        model_id=MODEL_ID,
        program_sha256=PROGRAM_SHA256,
        request_sha256=request.request_sha256,
        token_count=token_count,
        execution_scope="exact_complete_query_a_fragment",
        status="pass",
        counter_reconciliation="exact",
        attention_normalized_codes=numeric.normalized_codes,
        query_a_codes=numeric.query_a_codes,
        rms_mean_codes=numeric.mean_square_codes,
        rms_inverse_codes=numeric.inverse_rms_codes,
        logical_counters=MappingProxyType(counters),
        numeric_status=MappingProxyType(numeric_status),
        manifest=_freeze_json(manifest),
    )
    return result, payloads, manifest


def _execute_program(
    deployment: DeepSeekV4QueryAExecutableDeployment,
    request: _ExecutionRequest,
) -> QueryAServiceNumericResult:
    state: set[int] = {3}
    completed = False
    for program_counter, instruction in enumerate(deployment.instructions):
        if instruction.opcode == _OPCODE_RMS_NORM:
            if program_counter != 0 or instruction.source not in state or 8 in state:
                _poison("Query-A program has illegal RMS_NORM control flow")
            state.add(8)
            continue
        if instruction.opcode == _OPCODE_FP8_LINEAR:
            if program_counter != 1 or instruction.source not in state or 9 in state:
                _poison("Query-A program has illegal FP8_LINEAR control flow")
            state.add(9)
            continue
        if instruction.opcode == _OPCODE_COMPLETE:
            if (
                program_counter != len(deployment.instructions) - 1
                or 9 not in state
                or completed
            ):
                _poison("Query-A program has illegal COMPLETE control flow")
            completed = True
            continue
        _poison(f"Query-A program contains unsupported opcode {instruction.opcode}")
    if not completed:
        _poison("Query-A program did not commit COMPLETE")
    if deployment.exhaustive_rows != tuple(range(QUERY_A_OUTPUT_FEATURES)):
        _poison("Query-A program row-selection resource changed after loading")

    # The service arithmetic owns this fixed two-operator numeric boundary.
    # The controller first proves that the packaged flow produces both state
    # registers and reaches its sole COMPLETE commit point.
    try:
        return execute_complete_query_a(
            request.input_codes,
            deployment.norm_weight_codes,
            weight_row=deployment.weight_row,
            scale_code=deployment.scale_code,
        )
    except QueryAServiceNumericError as exc:
        _poison("Query-A packaged arithmetic poisoned", exc)


def _verify_published_result(
    output: Path,
    payloads: Mapping[str, bytes],
    manifest: Mapping[str, Any],
) -> None:
    expected = dict(payloads)
    expected["result_manifest.json"] = canonical_json_bytes(manifest)
    with SecureDirectory(output, label="published Query-A result") as tree:
        files, directories = tree.enumerate_tree(maximum_depth=2, maximum_entries=8)
        if files != set(expected) or directories != _EXPECTED_RESULT_DIRECTORIES:
            _poison("published Query-A result tree closure differs")
        for relative, expected_payload in sorted(expected.items()):
            source = tree.open_file(
                relative,
                label=f"published Query-A result {relative!r}",
                minimum_size=0,
                maximum_size=len(expected_payload),
                exact_size=len(expected_payload),
            )
            observed = source.read_bytes(
                label=f"published Query-A result {relative!r}",
                maximum_bytes=max(1, len(expected_payload)),
            )
            if observed != expected_payload:
                _poison(f"published Query-A result {relative!r} differs")
        tree.verify()


def _preflight_output(output: Path) -> None:
    if not output.name or output.name in {".", ".."} or output == Path(output.anchor):
        _poison("Query-A result must name one non-root directory")
    try:
        os.lstat(output)
    except FileNotFoundError:
        return
    except OSError as exc:
        _poison("cannot inspect Query-A result output", exc)
    _poison(f"Query-A result output already exists: {output}")


class DeepSeekV4QueryAExecutableServiceEngine:
    """Interpreter for the held official Query-A executable package."""

    def __init__(self, deployment: DeepSeekV4QueryAExecutableDeployment):
        if type(deployment) is not DeepSeekV4QueryAExecutableDeployment:
            _poison("Query-A executable deployment snapshot is invalid")
        self.deployment = deployment
        self._closed = False

    @classmethod
    def load(cls, deployment_dir: Path) -> DeepSeekV4QueryAExecutableServiceEngine:
        return cls(load_deepseek_v4_query_a_executable_deployment(deployment_dir))

    def execute(
        self,
        request_manifest: Path,
        result_dir: Path,
    ) -> QueryAExecutableResult:
        """Execute one composed request and atomically publish all observables."""

        if self._closed:
            _poison("Query-A executable service engine is closed")
        output = Path(result_dir).absolute()
        _preflight_output(output)
        request: _ExecutionRequest | None = None
        try:
            self.deployment.verify()
            request = _load_request(self.deployment, request_manifest)
            request.verify()
            numeric = _execute_program(self.deployment, request)
            self.deployment.verify()
            request.verify()
            result, payloads, manifest = _build_result(
                self.deployment,
                request,
                numeric,
            )
            _preflight_output(output)
            publish_payload_tree(
                output,
                payloads={
                    **payloads,
                    "result_manifest.json": canonical_json_bytes(manifest),
                },
                directories=("diagnostics", "outputs"),
                label="Query-A execution result",
                maximum_depth=2,
                maximum_entries=8,
            )
            _verify_published_result(output, payloads, manifest)
            self.deployment.verify()
            request.verify()
            return result
        except DeepSeekV4QueryAExecutableServiceError:
            raise
        except (OSError, SecureArtifactError, ValueError, struct.error) as exc:
            _poison("Query-A execution transaction failed", exc)
        finally:
            if request is not None:
                request.close()

    def close(self) -> None:
        if self._closed:
            return
        self.deployment.close()
        self._closed = True

    def __enter__(self) -> DeepSeekV4QueryAExecutableServiceEngine:
        if self._closed:
            _poison("Query-A executable service engine is closed")
        self.deployment.verify()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()


def execute_deepseek_v4_query_a_executable_deployment(
    deployment_dir: Path,
    request_manifest: Path,
    result_dir: Path,
) -> QueryAExecutableResult:
    """Load, execute, publish, and close one official Query-A transaction."""

    with DeepSeekV4QueryAExecutableServiceEngine.load(deployment_dir) as engine:
        return engine.execute(request_manifest, result_dir)


__all__ = [
    "EXECUTABLE_BUILD_ID",
    "EXECUTABLE_DEPLOYMENT_SCHEMA",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "FUNCTIONAL_COUNTER_CONTRACT_ID",
    "HC_PRE_EXECUTABLE_BUILD_ID",
    "MODEL_ID",
    "PROGRAM_CONTRACT_ID",
    "PROGRAM_SHA256",
    "RESOURCE_MANIFEST_ID",
    "SCHEDULE_CERTIFICATE_ID",
    "SCHEDULE_ID",
    "DeepSeekV4QueryAExecutableDeployment",
    "DeepSeekV4QueryAExecutableServiceEngine",
    "DeepSeekV4QueryAExecutableServiceError",
    "QueryAExecutableArtifactRecord",
    "QueryAExecutableResult",
    "QueryAInstruction",
    "execute_deepseek_v4_query_a_executable_deployment",
    "load_deepseek_v4_query_a_executable_deployment",
]
