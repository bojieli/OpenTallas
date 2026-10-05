"""Fail-closed verification for DeepSeek V4 RoPE microcode and schedules.

The checker validates canonical wire bytes, descriptor authority, complete
register/resource/state/position contracts, logical causality, and deterministic
schedule identity.  It does not execute arithmetic and makes no physical or
full-model claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_rope import (
    EXPLICIT_NON_CLAIMS,
    MAX_BATCH_SIZE,
    MAX_POSITION,
    MAX_SEQUENCE_LENGTH,
    NUMERIC_PROFILE,
    SUPPORTED_HEAD_WIDTHS,
    SUPPORTED_RANK4_HEAD_COUNTS,
    DeepSeekV4RopeMicrocodeError,
    Opcode,
    RopeDescriptor,
    decode,
    descriptor_id,
    descriptor_record,
    encode,
    position_contract,
    resource_contract,
    state_contract,
    tensor_contract,
    verify,
    verify_descriptor,
)
from compiler.scheduling.deepseek_v4_rope import (
    CLAIM_BOUNDARY,
    LOGICAL_SCHEDULE_SCHEMA,
    LOGICAL_SCHEDULE_STATUS,
    ORDERING_POLICY,
    REQUIRED_NONCLAIMS,
    DeepSeekV4RopeScheduleError,
    build_deepseek_v4_rope_logical_schedule,
)


CERTIFICATE_SCHEMA = "opentallas.deepseek_v4_rope_verification.v1"
CERTIFICATE_STATUS = "compiler_contract_verified_no_execution_claim"
CERTIFICATE_CLAIM_BOUNDARY = (
    "Canonical DeepSeek V4 RoPE microcode and logical-schedule conformance "
    "only; arithmetic execution, target kernels, cycles, bandwidth, RTL, "
    "full-model execution, and PPA remain outside this certificate."
)


class DeepSeekV4RopeCheckError(ValueError):
    """Raised when any compiler artifact fails canonical RoPE authority."""


@dataclass(frozen=True, slots=True)
class RopeVerificationReport:
    descriptor_id: str
    opcode: str
    numeric_profile: str
    program_sha256: str
    schedule_id: str
    tensor_shape: tuple[int, ...]
    table_start_position: int
    last_table_position: int
    position_stride: int
    mutable_state_read_count: int
    mutable_state_write_count: int

    def __post_init__(self) -> None:
        _validate_report(self)


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4RopeCheckError(f"{label} must be a lowercase SHA-256")
    return value


def _exact_dict(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or not all(type(key) is str for key in value):
        raise DeepSeekV4RopeCheckError(f"{label} must be an exact string-keyed object")
    observed = set(value)
    if observed != keys:
        raise DeepSeekV4RopeCheckError(
            f"{label} fields differ; missing={sorted(keys - observed)}, "
            f"extra={sorted(observed - keys)}"
        )
    return value


def _array(value: object, label: str) -> list[Any]:
    if type(value) is not list:
        raise DeepSeekV4RopeCheckError(f"{label} must be an exact array")
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
        raise DeepSeekV4RopeCheckError(f"{label} must be an exact integer {bound}")
    return value


def _validate_report(report: RopeVerificationReport) -> None:
    if type(report) is not RopeVerificationReport:
        raise DeepSeekV4RopeCheckError("report must be exact")
    _digest(report.descriptor_id, "report.descriptor_id")
    _digest(report.program_sha256, "report.program_sha256")
    _digest(report.schedule_id, "report.schedule_id")
    if type(report.opcode) is not str or report.opcode not in {
        Opcode.ROPE_APPLY.name,
        Opcode.ROPE_INVERSE.name,
    }:
        raise DeepSeekV4RopeCheckError("report opcode differs")
    if (
        type(report.numeric_profile) is not str
        or report.numeric_profile != NUMERIC_PROFILE
    ):
        raise DeepSeekV4RopeCheckError("report numeric profile differs")
    if (
        type(report.tensor_shape) is not tuple
        or len(report.tensor_shape) not in {3, 4}
        or not all(type(value) is int and value > 0 for value in report.tensor_shape)
    ):
        raise DeepSeekV4RopeCheckError("report tensor shape differs")
    if (
        not 1 <= report.tensor_shape[0] <= MAX_BATCH_SIZE
        or not 1 <= report.tensor_shape[1] <= MAX_SEQUENCE_LENGTH
        or report.tensor_shape[-1] not in SUPPORTED_HEAD_WIDTHS
        or (
            len(report.tensor_shape) == 4
            and report.tensor_shape[2] not in SUPPORTED_RANK4_HEAD_COUNTS
        )
    ):
        raise DeepSeekV4RopeCheckError("report tensor shape is outside official bounds")
    start = _integer(
        report.table_start_position,
        "report.table_start_position",
        maximum=MAX_POSITION,
    )
    last = _integer(
        report.last_table_position,
        "report.last_table_position",
        maximum=MAX_POSITION,
    )
    stride = _integer(report.position_stride, "report.position_stride", minimum=1)
    if last != start + (report.tensor_shape[1] - 1) * stride:
        raise DeepSeekV4RopeCheckError("report table positions do not reconcile")
    if (
        type(report.mutable_state_read_count) is not int
        or report.mutable_state_read_count != 0
        or type(report.mutable_state_write_count) is not int
        or report.mutable_state_write_count != 0
    ):
        raise DeepSeekV4RopeCheckError("RoPE report must not claim mutable state")


def _validate_json_tree(
    value: object,
    label: str,
    *,
    _depth: int = 0,
    _budget: list[int] | None = None,
) -> None:
    budget = [0] if _budget is None else _budget
    budget[0] += 1
    if _depth > 16 or budget[0] > 4096:
        raise DeepSeekV4RopeCheckError(
            f"{label} exceeds the bounded canonical JSON structure"
        )
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise DeepSeekV4RopeCheckError(f"{label} has a non-string key")
        for key, child in value.items():
            _validate_json_tree(
                child,
                f"{label}.{key}",
                _depth=_depth + 1,
                _budget=budget,
            )
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _validate_json_tree(
                child,
                f"{label}[{index}]",
                _depth=_depth + 1,
                _budget=budget,
            )
        return
    if type(value) not in {str, int, bool, type(None)}:
        raise DeepSeekV4RopeCheckError(
            f"{label} contains a non-canonical JSON type {type(value).__name__}"
        )


def _canonical_equal(value: object, expected: object) -> bool:
    try:
        return canonical_json_bytes(value) == canonical_json_bytes(expected)
    except (TypeError, ValueError):
        return False


def _verify_registers(schedule: dict[str, Any], descriptor: RopeDescriptor) -> None:
    records = _array(schedule["registers"], "schedule.registers")
    specs = tensor_contract(descriptor)
    if len(records) != 2 or len(specs) != 2:
        raise DeepSeekV4RopeCheckError(
            "RoPE schedule must contain exactly two registers"
        )
    expected_shape = list(specs[0].shape)
    ids: list[int] = []
    for index, (record_value, spec) in enumerate(zip(records, specs, strict=True)):
        record = _exact_dict(
            record_value,
            {
                "access",
                "alias_of_register_id",
                "channel_semantics",
                "dtype",
                "live_at_complete",
                "preserved_prefix_width",
                "register_id",
                "register_name",
                "rotary_suffix_width",
                "shape",
            },
            f"schedule.registers[{index}]",
        )
        register_id = _integer(record["register_id"], "register_id")
        ids.append(register_id)
        if (
            register_id != int(spec.register)
            or record["register_name"] != spec.register.name
            or record["dtype"] != "BF16"
            or record["shape"] != expected_shape
            or record["access"] != spec.access
            or record["channel_semantics"] != spec.channel_semantics
            or type(record["live_at_complete"]) is not bool
            or record["live_at_complete"] is not spec.live_at_complete
            or record["alias_of_register_id"] is not None
            or record["preserved_prefix_width"] != spec.preserved_prefix_width
            or record["rotary_suffix_width"] != spec.rotary_suffix_width
        ):
            raise DeepSeekV4RopeCheckError(
                "register contract differs from typed authority"
            )
    if len(set(ids)) != 2:
        raise DeepSeekV4RopeCheckError("input and output registers alias")


def _verify_resources(schedule: dict[str, Any], descriptor: RopeDescriptor) -> None:
    records = _array(schedule["resources"], "schedule.resources")
    specs = resource_contract(descriptor)
    if len(records) != 1 or len(specs) != 1:
        raise DeepSeekV4RopeCheckError(
            "RoPE schedule must bind exactly one phasor table"
        )
    record = _exact_dict(
        records[0],
        {
            "beta_fast",
            "beta_slow",
            "checkpoint_derived",
            "complex_pair_count",
            "correction_high",
            "correction_low",
            "dtype",
            "numeric_profile",
            "original_sequence_length",
            "profile",
            "rope_dimension",
            "resource_id",
            "resource_name",
            "scaling_mode",
            "semantic_sha256",
            "shape",
            "size_bytes",
            "theta",
            "yarn_factor",
        },
        "schedule.resources[0]",
    )
    spec = specs[0]
    _digest(record["semantic_sha256"], "resource semantic_sha256")
    expected = {
        "beta_fast": spec.beta_fast,
        "beta_slow": spec.beta_slow,
        "checkpoint_derived": False,
        "complex_pair_count": spec.complex_pair_count,
        "correction_high": spec.correction_high,
        "correction_low": spec.correction_low,
        "dtype": spec.dtype,
        "numeric_profile": spec.numeric_profile,
        "original_sequence_length": spec.original_sequence_length,
        "profile": spec.profile.name,
        "rope_dimension": spec.rope_dimension,
        "resource_id": int(spec.resource),
        "resource_name": spec.resource.name,
        "scaling_mode": spec.scaling_mode.name,
        "semantic_sha256": spec.semantic_sha256,
        "shape": list(spec.shape),
        "size_bytes": spec.size_bytes,
        "theta": spec.theta,
        "yarn_factor": spec.yarn_factor,
    }
    if not _canonical_equal(record, expected):
        raise DeepSeekV4RopeCheckError("phasor resource/profile constants differ")


def _verify_position(schedule: dict[str, Any], descriptor: RopeDescriptor) -> None:
    record = _exact_dict(
        schedule["position_contract"],
        {
            "compression_ratio",
            "last_table_position",
            "output_sequence_length",
            "phase",
            "policy",
            "position_stride",
            "request_start_position",
            "source_cutoff",
            "source_sequence_length",
            "table_position_formula",
            "table_start_position",
        },
        "schedule.position_contract",
    )
    contract = position_contract(descriptor)
    table_start = _integer(
        record["table_start_position"],
        "position table_start_position",
        maximum=MAX_POSITION,
    )
    output_length = _integer(
        record["output_sequence_length"],
        "position output_sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    stride = _integer(
        record["position_stride"],
        "position position_stride",
        minimum=1,
    )
    table_last = _integer(
        record["last_table_position"],
        "position last_table_position",
        maximum=MAX_POSITION,
    )
    expected_last = table_start + (output_length - 1) * stride
    if expected_last != table_last:
        raise DeepSeekV4RopeCheckError("position range does not reconcile")
    expected = {
        "compression_ratio": contract.compression_ratio,
        "last_table_position": contract.last_table_position,
        "output_sequence_length": contract.output_sequence_length,
        "phase": contract.phase.name,
        "policy": contract.policy.name,
        "position_stride": contract.position_stride,
        "request_start_position": contract.request_start_position,
        "source_cutoff": contract.source_cutoff,
        "source_sequence_length": contract.source_sequence_length,
        "table_position_formula": contract.table_position_formula,
        "table_start_position": contract.table_start_position,
    }
    if not _canonical_equal(record, expected):
        raise DeepSeekV4RopeCheckError(
            "position policy differs from descriptor authority"
        )


def _verify_state(schedule: dict[str, Any], descriptor: RopeDescriptor) -> None:
    record = _exact_dict(
        schedule["state_contract"],
        {
            "alias_policy",
            "mutable_state_reads",
            "mutable_state_writes",
            "output_commit",
            "phasor_resource_id",
            "phasor_resource_name",
            "preserved_prefix_policy",
            "request_inputs",
            "rotary_suffix_width",
        },
        "schedule.state_contract",
    )
    contract = state_contract(descriptor)
    if (
        _array(record["mutable_state_reads"], "mutable_state_reads") != []
        or _array(record["mutable_state_writes"], "mutable_state_writes") != []
        or record["request_inputs"] != list(contract.request_inputs)
        or record["phasor_resource_id"] != int(contract.phasor_resource)
        or record["phasor_resource_name"] != contract.phasor_resource.name
        or record["output_commit"] != contract.output_commit
        or record["alias_policy"] != contract.alias_policy
        or record["preserved_prefix_policy"] != contract.preserved_prefix_policy
        or record["rotary_suffix_width"] != contract.rotary_suffix_width
    ):
        raise DeepSeekV4RopeCheckError("state, commit, or alias contract differs")


def _verify_slots(schedule: dict[str, Any], descriptor: RopeDescriptor) -> None:
    slots = _array(schedule["slots"], "schedule.slots")
    if len(slots) != 2:
        raise DeepSeekV4RopeCheckError(
            "schedule must contain exactly two logical slots"
        )
    required = {
        "dependency_slots",
        "destination_register_ids",
        "external_input_register_ids",
        "instruction_index",
        "instruction_sha256",
        "logical_table_position_count",
        "opcode",
        "opcode_code",
        "position_stride",
        "resource_ids",
        "slot",
        "source_register_ids",
        "table_position_first",
        "table_position_last",
        "terminal",
    }
    first = _exact_dict(slots[0], required, "schedule.slots[0]")
    complete = _exact_dict(slots[1], required, "schedule.slots[1]")
    _digest(first["instruction_sha256"], "slot 0 instruction_sha256")
    _digest(complete["instruction_sha256"], "slot 1 instruction_sha256")
    if (
        first["slot"] != 0
        or first["instruction_index"] != 0
        or first["opcode"] != descriptor.opcode.name
        or first["opcode_code"] != int(descriptor.opcode)
        or first["dependency_slots"] != []
        or first["source_register_ids"] != [0]
        or first["external_input_register_ids"] != [0]
        or first["destination_register_ids"] != [1]
        or first["logical_table_position_count"] != descriptor.sequence_length
        or first["table_position_first"] != descriptor.table_start_position
        or first["table_position_last"] != descriptor.last_table_position
        or first["position_stride"] != descriptor.position_stride
        or type(first["terminal"]) is not bool
        or first["terminal"]
    ):
        raise DeepSeekV4RopeCheckError("semantic RoPE slot ordering or binding differs")
    if (
        complete["slot"] != 1
        or complete["instruction_index"] != 1
        or complete["opcode"] != Opcode.COMPLETE.name
        or complete["opcode_code"] != int(Opcode.COMPLETE)
        or complete["dependency_slots"] != [0]
        or complete["source_register_ids"] != []
        or complete["destination_register_ids"] != []
        or complete["resource_ids"] != []
        or complete["logical_table_position_count"] != 0
        or complete["position_stride"] != 0
        or complete["table_position_first"] is not None
        or complete["table_position_last"] is not None
        or type(complete["terminal"]) is not bool
        or not complete["terminal"]
    ):
        raise DeepSeekV4RopeCheckError("terminal COMPLETE causality differs")


def verify_deepseek_v4_rope_logical_schedule(
    schedule: object,
    descriptor: RopeDescriptor,
) -> str:
    """Verify and return the canonical schedule ID for one descriptor."""

    try:
        verify_descriptor(descriptor)
    except DeepSeekV4RopeMicrocodeError as exc:
        raise DeepSeekV4RopeCheckError(f"descriptor authority failed: {exc}") from exc
    top = _exact_dict(
        schedule,
        {
            "claim_boundary",
            "descriptor",
            "identity",
            "ordering_policy",
            "position_contract",
            "registers",
            "required_nonclaims",
            "resources",
            "schedule_id",
            "schema",
            "slots",
            "state_contract",
            "status",
            "summary",
        },
        "schedule",
    )
    _validate_json_tree(top, "schedule")
    if (
        top["schema"] != LOGICAL_SCHEDULE_SCHEMA
        or top["status"] != LOGICAL_SCHEDULE_STATUS
        or top["claim_boundary"] != CLAIM_BOUNDARY
        or top["ordering_policy"] != ORDERING_POLICY
        or top["required_nonclaims"] != list(REQUIRED_NONCLAIMS)
        or not set(EXPLICIT_NON_CLAIMS).issubset(top["required_nonclaims"])
        or top["descriptor"] != descriptor_record(descriptor)
    ):
        raise DeepSeekV4RopeCheckError("schedule identity, policy, or nonclaims differ")
    schedule_id = _digest(top["schedule_id"], "schedule.schedule_id")
    body = dict(top)
    del body["schedule_id"]
    if schedule_id != _sha256(body):
        raise DeepSeekV4RopeCheckError(
            "schedule_id does not bind the complete schedule"
        )

    _verify_registers(top, descriptor)
    _verify_resources(top, descriptor)
    _verify_position(top, descriptor)
    _verify_state(top, descriptor)
    _verify_slots(top, descriptor)

    expected = build_deepseek_v4_rope_logical_schedule(descriptor)
    if not _canonical_equal(top, expected):
        raise DeepSeekV4RopeCheckError(
            "schedule differs from independently reconstructed canonical authority"
        )
    return schedule_id


def verify_compiled_deepseek_v4_rope(
    program_payload: object,
    schedule: object,
    descriptor: RopeDescriptor,
) -> RopeVerificationReport:
    """Verify canonical program bytes and their matching logical schedule."""

    if type(program_payload) is not bytes:
        raise DeepSeekV4RopeCheckError("program payload must be exact bytes")
    try:
        program = decode(program_payload)
        verify(program, descriptor)
        if encode(program) != program_payload:
            raise DeepSeekV4RopeCheckError("program bytes are not canonical")
    except DeepSeekV4RopeMicrocodeError as exc:
        raise DeepSeekV4RopeCheckError(f"microcode verification failed: {exc}") from exc
    try:
        schedule_id = verify_deepseek_v4_rope_logical_schedule(schedule, descriptor)
    except (
        DeepSeekV4RopeScheduleError
    ) as exc:  # pragma: no cover - reconstruction guard
        raise DeepSeekV4RopeCheckError(
            f"schedule reconstruction failed: {exc}"
        ) from exc
    program_sha256 = hashlib.sha256(program_payload).hexdigest()
    identity = schedule["identity"]
    if identity["program_sha256"] != program_sha256:
        raise DeepSeekV4RopeCheckError("schedule program hash differs from payload")
    shape = tensor_contract(descriptor)[0].shape
    return RopeVerificationReport(
        descriptor_id=descriptor_id(descriptor),
        opcode=descriptor.opcode.name,
        numeric_profile=NUMERIC_PROFILE,
        program_sha256=program_sha256,
        schedule_id=schedule_id,
        tensor_shape=shape,
        table_start_position=descriptor.table_start_position,
        last_table_position=descriptor.last_table_position,
        position_stride=descriptor.position_stride,
        mutable_state_read_count=0,
        mutable_state_write_count=0,
    )


def build_verification_certificate(report: RopeVerificationReport) -> dict[str, Any]:
    if type(report) is not RopeVerificationReport:
        raise DeepSeekV4RopeCheckError("report must be an exact RopeVerificationReport")
    _validate_report(report)
    body = {
        "claim_boundary": CERTIFICATE_CLAIM_BOUNDARY,
        "descriptor_id": report.descriptor_id,
        "last_table_position": report.last_table_position,
        "mutable_state_read_count": report.mutable_state_read_count,
        "mutable_state_write_count": report.mutable_state_write_count,
        "numeric_profile": report.numeric_profile,
        "opcode": report.opcode,
        "position_stride": report.position_stride,
        "program_sha256": report.program_sha256,
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "schedule_id": report.schedule_id,
        "schema": CERTIFICATE_SCHEMA,
        "status": CERTIFICATE_STATUS,
        "table_start_position": report.table_start_position,
        "tensor_shape": list(report.tensor_shape),
    }
    return {**body, "certificate_id": _sha256(body)}


def verify_verification_certificate(
    certificate: object,
    report: RopeVerificationReport,
) -> None:
    expected = build_verification_certificate(report)
    if type(certificate) is not dict:
        raise DeepSeekV4RopeCheckError("certificate must be an exact object")
    _validate_json_tree(certificate, "certificate")
    if not _canonical_equal(certificate, expected):
        raise DeepSeekV4RopeCheckError("verification certificate differs")


__all__ = [
    "CERTIFICATE_CLAIM_BOUNDARY",
    "CERTIFICATE_SCHEMA",
    "CERTIFICATE_STATUS",
    "DeepSeekV4RopeCheckError",
    "RopeVerificationReport",
    "build_verification_certificate",
    "verify_compiled_deepseek_v4_rope",
    "verify_deepseek_v4_rope_logical_schedule",
    "verify_verification_certificate",
]
