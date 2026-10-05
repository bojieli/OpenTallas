"""Independent checker for the DeepSeek V4 HC_PRE logical schedule.

The checker reconstructs the two-slot schedule from the committed microcode and
typed contracts without importing the schedule builder.  A passing certificate
proves only canonical logical ordering and identity reconciliation; it does not
assert execution, timing, bandwidth, topology, numerical results, or PPA.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    ABI_MAJOR,
    ABI_MINOR,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    RECORD,
    Instruction,
    Opcode,
    Register,
)
from compiler.microcode.deepseek_v4_hc_pre import (
    MODEL_ID,
    assemble,
    build_program_contract,
    encode,
    resource_contract,
    tensor_contract,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_hc_pre_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_hc_pre_logical_schedule_certificate.v1"
)
LOGICAL_SCHEDULE_STATUS = "logical_schedule_only"
CERTIFICATE_STATUS = "pass"
CLAIM_BOUNDARY = (
    "Deterministic logical instruction, register, and resource ordering for the "
    "exact HC_PRE fragment only; this is not execution, timing, bandwidth, "
    "physical-topology, numeric-correctness, or PPA evidence."
)
CERTIFICATE_CLAIM_BOUNDARY = (
    "Independent logical-schedule conformance certificate only; no execution, "
    "cycle, bandwidth, physical-topology, numeric-correctness, or PPA claim."
)
REQUIRED_NONCLAIMS = [
    "attention_completion",
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "execution_evidence",
    "full_model_execution",
    "nvidia_comparison",
    "numeric_correctness",
    "physical_topology",
    "ppa",
    "query_projection",
    "transformer_block_completion",
    "weighted_rms_norm",
]
ORDERING_POLICY = {
    "completion_rule": "terminal COMPLETE depends on every preceding logical slot",
    "dependency_rule": (
        "every consumed register is external or produced by a lower-numbered slot"
    ),
    "resource_rule": (
        "resource IDs resolve exactly through the committed HC_PRE resource contract"
    ),
    "slot_rule": "one microinstruction per monotonically increasing logical slot",
}
EXPECTED_COUNTS = {
    "checkpoint_parameter_bytes": 1_572_972,
    "complete_count": 1,
    "dependency_edge_count": 1,
    "evidence_observable_register_count": 5,
    "external_input_register_count": 1,
    "hc_pre_count": 1,
    "instruction_count": 2,
    "live_at_complete_register_count": 4,
    "produced_register_count": 5,
    "register_count": 6,
    "resource_count": 3,
    "resource_read_count": 3,
    "slot_count": 2,
}


class DeepSeekV4HCPreScheduleCheckError(ValueError):
    """Raised when a schedule or certificate fails closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/int equality aliasing."""

    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4HCPreScheduleCheckError(f"{label} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise DeepSeekV4HCPreScheduleCheckError(f"{label} keys must be strings")
    return value


def _exact(
    value: object,
    keys: set[str],
    label: str,
) -> Mapping[str, Any]:
    record = _mapping(value, label)
    observed = set(record)
    if observed != keys:
        missing = sorted(keys - observed)
        extra = sorted(observed - keys)
        raise DeepSeekV4HCPreScheduleCheckError(
            f"{label} fields differ; missing={missing}, extra={extra}"
        )
    return record


def _array(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, list):
        raise DeepSeekV4HCPreScheduleCheckError(f"{label} must be an array")
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DeepSeekV4HCPreScheduleCheckError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4HCPreScheduleCheckError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _instruction_identity(instruction: Instruction) -> dict[str, int]:
    return {
        "destination0": int(instruction.destination0),
        "destination1": int(instruction.destination1),
        "destination2": int(instruction.destination2),
        "destination3": int(instruction.destination3),
        "destination4": int(instruction.destination4),
        "flags": instruction.flags,
        "immediate0": instruction.immediate0,
        "immediate1": instruction.immediate1,
        "immediate2": instruction.immediate2,
        "immediate3": instruction.immediate3,
        "opcode": int(instruction.opcode),
        "resource0": int(instruction.resource0),
        "resource1": int(instruction.resource1),
        "resource2": int(instruction.resource2),
        "resource3": int(instruction.resource3),
        "source": int(instruction.source),
    }


def _expected_resources() -> list[dict[str, Any]]:
    specs = resource_contract()
    verify_resource_contract(specs)
    result = []
    for spec in specs:
        result.append(
            {
                "checkpoint_derived": spec.checkpoint_derived,
                "content_sha256": spec.content_sha256,
                "dtype": spec.dtype,
                "rank": spec.rank,
                "resource_id": int(spec.resource),
                "resource_name": spec.resource.name,
                "role": spec.role,
                "row_start": spec.row_start,
                "row_stop": spec.row_stop,
                "shape": list(spec.shape),
                "size_bytes": spec.size_bytes,
            }
        )
    return result


def _expected_registers() -> list[dict[str, Any]]:
    lower = tensor_contract(MIN_TOKEN_COUNT)
    upper = tensor_contract(MAX_TOKEN_COUNT)
    verify_tensor_contract(lower, MIN_TOKEN_COUNT)
    verify_tensor_contract(upper, MAX_TOKEN_COUNT)
    producer_slots = {
        Register.ATTENTION_INPUT: 0,
        Register.ATTENTION_PRE: 0,
        Register.ATTENTION_POST: 0,
        Register.ATTENTION_COMBINATION: 0,
        Register.ATTENTION_RESIDUAL: 0,
    }
    consumers = {Register.HC_HIDDEN: [0]}
    records: list[dict[str, Any]] = []
    for minimum_spec, maximum_spec in zip(lower, upper):
        if (
            minimum_spec.register != maximum_spec.register
            or minimum_spec.dtype != maximum_spec.dtype
            or minimum_spec.live_at_complete != maximum_spec.live_at_complete
            or minimum_spec.evidence_observable != maximum_spec.evidence_observable
            or minimum_spec.shape[0] != MIN_TOKEN_COUNT
            or maximum_spec.shape[0] != MAX_TOKEN_COUNT
            or minimum_spec.shape[1:] != maximum_spec.shape[1:]
        ):
            raise DeepSeekV4HCPreScheduleCheckError(
                "committed HC_PRE tensor bounds are internally inconsistent"
            )
        register = minimum_spec.register
        records.append(
            {
                "consumer_slots": consumers.get(register, []),
                "dtype": minimum_spec.dtype,
                "evidence_observable": minimum_spec.evidence_observable,
                "live_at_complete": minimum_spec.live_at_complete,
                "producer_kind": "slot" if register in producer_slots else "external",
                "producer_slot": producer_slots.get(register),
                "register_id": int(register),
                "register_name": register.name,
                "token_major_shape_suffix": list(minimum_spec.shape[1:]),
            }
        )
    return records


def _expected_slots(program: tuple[Instruction, ...]) -> list[dict[str, Any]]:
    hc_pre, complete = program
    if hc_pre.opcode != Opcode.HC_PRE or complete.opcode != Opcode.COMPLETE:
        raise DeepSeekV4HCPreScheduleCheckError(
            "committed program is not exact HC_PRE followed by COMPLETE"
        )
    return [
        {
            "dependency_slots": [],
            "destination_register_ids": [
                int(hc_pre.destination0),
                int(hc_pre.destination1),
                int(hc_pre.destination2),
                int(hc_pre.destination3),
                int(hc_pre.destination4),
            ],
            "external_input_register_ids": [int(hc_pre.source)],
            "flags": hc_pre.flags,
            "immediates": [
                hc_pre.immediate0,
                hc_pre.immediate1,
                hc_pre.immediate2,
                hc_pre.immediate3,
            ],
            "instruction_index": 0,
            "instruction_sha256": _sha256(_instruction_identity(hc_pre)),
            "opcode": "HC_PRE",
            "opcode_code": int(Opcode.HC_PRE),
            "resource_ids": [
                int(hc_pre.resource0),
                int(hc_pre.resource1),
                int(hc_pre.resource2),
            ],
            "slot": 0,
            "source_register_ids": [int(hc_pre.source)],
            "terminal": False,
        },
        {
            "dependency_slots": [0],
            "destination_register_ids": [],
            "external_input_register_ids": [],
            "flags": complete.flags,
            "immediates": [
                complete.immediate0,
                complete.immediate1,
                complete.immediate2,
                complete.immediate3,
            ],
            "instruction_index": 1,
            "instruction_sha256": _sha256(_instruction_identity(complete)),
            "opcode": "COMPLETE",
            "opcode_code": int(Opcode.COMPLETE),
            "resource_ids": [],
            "slot": 1,
            "source_register_ids": [],
            "terminal": True,
        },
    ]


def _reconcile_counts(
    slots: Sequence[Mapping[str, Any]],
    registers: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    return {
        "checkpoint_parameter_bytes": sum(
            _integer(record.get("size_bytes"), "resource size_bytes")
            for record in resources
        ),
        "complete_count": sum(record.get("opcode") == "COMPLETE" for record in slots),
        "dependency_edge_count": sum(
            len(_array(record.get("dependency_slots"), "slot dependency_slots"))
            for record in slots
        ),
        "evidence_observable_register_count": sum(
            record.get("evidence_observable") is True for record in registers
        ),
        "external_input_register_count": sum(
            record.get("producer_kind") == "external" for record in registers
        ),
        "hc_pre_count": sum(record.get("opcode") == "HC_PRE" for record in slots),
        "instruction_count": len(slots),
        "live_at_complete_register_count": sum(
            record.get("live_at_complete") is True for record in registers
        ),
        "produced_register_count": sum(
            record.get("producer_kind") == "slot" for record in registers
        ),
        "register_count": len(registers),
        "resource_count": len(resources),
        "resource_read_count": sum(
            len(_array(record.get("resource_ids"), "slot resource_ids"))
            for record in slots
        ),
        "slot_count": len(slots),
    }


def _verify_causality(
    slots: Sequence[Mapping[str, Any]],
    registers: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> None:
    register_by_id = {
        _integer(record.get("register_id"), "register_id"): record
        for record in registers
    }
    resource_ids = {
        _integer(record.get("resource_id"), "resource_id") for record in resources
    }
    if len(register_by_id) != len(registers) or len(resource_ids) != len(resources):
        raise DeepSeekV4HCPreScheduleCheckError(
            "register or resource identity is duplicated"
        )
    terminal_count = 0
    for index, slot in enumerate(slots):
        if slot.get("slot") != index or slot.get("instruction_index") != index:
            raise DeepSeekV4HCPreScheduleCheckError(
                f"logical slot {index} is not monotonically ordered"
            )
        dependencies = _array(slot.get("dependency_slots"), "dependency_slots")
        if any(
            _integer(dependency, "dependency slot") >= index
            for dependency in dependencies
        ):
            raise DeepSeekV4HCPreScheduleCheckError(
                f"logical slot {index} has a non-preceding dependency"
            )
        external = set(
            _array(slot.get("external_input_register_ids"), "external register IDs")
        )
        for raw_register_id in _array(
            slot.get("source_register_ids"), "source register IDs"
        ):
            register_id = _integer(raw_register_id, "source register ID")
            try:
                register = register_by_id[register_id]
            except KeyError as exc:
                raise DeepSeekV4HCPreScheduleCheckError(
                    f"logical slot {index} reads unknown register {register_id}"
                ) from exc
            producer = register.get("producer_slot")
            if register.get("producer_kind") == "external":
                if producer is not None or register_id not in external:
                    raise DeepSeekV4HCPreScheduleCheckError(
                        f"logical slot {index} has incorrect external causality"
                    )
            elif (
                not isinstance(producer, int)
                or isinstance(producer, bool)
                or producer >= index
                or producer not in dependencies
                or register_id in external
            ):
                raise DeepSeekV4HCPreScheduleCheckError(
                    f"logical slot {index} consumes a non-preceding producer"
                )
        for raw_register_id in _array(
            slot.get("destination_register_ids"), "destination register IDs"
        ):
            register_id = _integer(raw_register_id, "destination register ID")
            if (
                register_id not in register_by_id
                or register_by_id[register_id].get("producer_slot") != index
            ):
                raise DeepSeekV4HCPreScheduleCheckError(
                    f"logical slot {index} has an incorrect destination producer"
                )
        used_resources = {
            _integer(value, "used resource ID")
            for value in _array(slot.get("resource_ids"), "resource IDs")
        }
        if not used_resources <= resource_ids:
            raise DeepSeekV4HCPreScheduleCheckError(
                f"logical slot {index} uses an unknown resource"
            )
        if slot.get("terminal") is True:
            terminal_count += 1
            if index != len(slots) - 1 or dependencies != list(range(index)):
                raise DeepSeekV4HCPreScheduleCheckError(
                    "terminal COMPLETE is not the final all-predecessor barrier"
                )
    if terminal_count != 1 or slots[-1].get("opcode") != "COMPLETE":
        raise DeepSeekV4HCPreScheduleCheckError(
            "logical schedule lacks one exact terminal COMPLETE"
        )


def verify_deepseek_v4_hc_pre_logical_schedule(
    value: object,
) -> dict[str, Any]:
    """Verify the canonical schedule and return a hash-bound logical certificate."""

    schedule = _exact(
        value,
        {
            "claim_boundary",
            "identity",
            "ordering_policy",
            "registers",
            "required_nonclaims",
            "resources",
            "schedule_id",
            "schema",
            "slots",
            "status",
            "summary",
        },
        "HC_PRE logical schedule",
    )
    if schedule["schema"] != LOGICAL_SCHEDULE_SCHEMA:
        raise DeepSeekV4HCPreScheduleCheckError("unsupported HC_PRE schedule schema")
    if schedule["status"] != LOGICAL_SCHEDULE_STATUS:
        raise DeepSeekV4HCPreScheduleCheckError("HC_PRE schedule status differs")
    body = {key: schedule[key] for key in schedule if key != "schedule_id"}
    if _digest(schedule["schedule_id"], "schedule_id") != _sha256(body):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule_id does not bind canonical schedule serialization"
        )
    if schedule["claim_boundary"] != CLAIM_BOUNDARY:
        raise DeepSeekV4HCPreScheduleCheckError("schedule claim boundary differs")
    if not _canonical_equal(schedule["ordering_policy"], ORDERING_POLICY):
        raise DeepSeekV4HCPreScheduleCheckError("schedule ordering policy differs")
    if not _canonical_equal(schedule["required_nonclaims"], REQUIRED_NONCLAIMS):
        raise DeepSeekV4HCPreScheduleCheckError("schedule nonclaims differ")

    program = assemble()
    verify(program)
    program_payload = encode(program)
    program_contract = build_program_contract()
    verify_program_contract(program_contract)
    expected_resources = _expected_resources()
    expected_registers = _expected_registers()
    expected_slots = _expected_slots(program)
    expected_identity = {
        "abi_magic_ascii": MAGIC.decode("ascii"),
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "instruction_record_bytes": RECORD.size,
        "model_id": MODEL_ID,
        "program_bytes": len(program_payload),
        "program_contract_id": program_contract["contract_id"],
        "program_sha256": hashlib.sha256(program_payload).hexdigest(),
        "register_table_sha256": _sha256(expected_registers),
        "resource_table_sha256": _sha256(expected_resources),
        "token_count_maximum": MAX_TOKEN_COUNT,
        "token_count_minimum": MIN_TOKEN_COUNT,
    }
    if not _canonical_equal(schedule["identity"], expected_identity):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule program or table identity differs"
        )

    resources = _array(schedule["resources"], "schedule resources")
    registers = _array(schedule["registers"], "schedule registers")
    slots = _array(schedule["slots"], "schedule slots")
    if not _canonical_equal(resources, expected_resources):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule resource identities or bounds differ"
        )
    if not _canonical_equal(registers, expected_registers):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule register identities or causality differ"
        )
    if not _canonical_equal(slots, expected_slots):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule instruction identity or ordering differs"
        )
    _verify_causality(slots, registers, resources)
    reconciled = _reconcile_counts(slots, registers, resources)
    if not _canonical_equal(reconciled, EXPECTED_COUNTS) or not _canonical_equal(
        schedule["summary"], EXPECTED_COUNTS
    ):
        raise DeepSeekV4HCPreScheduleCheckError(
            "schedule exact count reconciliation differs"
        )

    certificate_body = {
        "checks": {
            "canonical_serialization_hash": True,
            "exact_count_reconciliation": True,
            "instruction_identity": True,
            "producer_before_consumer": True,
            "register_contract": True,
            "resource_identity_and_bounds": True,
            "terminal_complete": True,
        },
        "claim_boundary": CERTIFICATE_CLAIM_BOUNDARY,
        "counts": dict(EXPECTED_COUNTS),
        "program_contract_id": expected_identity["program_contract_id"],
        "program_sha256": expected_identity["program_sha256"],
        "register_table_sha256": expected_identity["register_table_sha256"],
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "resource_table_sha256": expected_identity["resource_table_sha256"],
        "schedule_id": schedule["schedule_id"],
        "schema": LOGICAL_CERTIFICATE_SCHEMA,
        "status": CERTIFICATE_STATUS,
    }
    return {
        **certificate_body,
        "certificate_id": _sha256(certificate_body),
    }


def verify_deepseek_v4_hc_pre_logical_schedule_certificate(
    value: object,
    schedule: object,
) -> None:
    """Require a certificate to equal an independent fresh schedule check."""

    expected = verify_deepseek_v4_hc_pre_logical_schedule(schedule)
    certificate = _exact(
        value,
        set(expected),
        "HC_PRE logical schedule certificate",
    )
    if not _canonical_equal(dict(certificate), expected):
        raise DeepSeekV4HCPreScheduleCheckError(
            "logical schedule certificate differs from independent verification"
        )


__all__ = [
    "CERTIFICATE_CLAIM_BOUNDARY",
    "CERTIFICATE_STATUS",
    "EXPECTED_COUNTS",
    "LOGICAL_CERTIFICATE_SCHEMA",
    "LOGICAL_SCHEDULE_SCHEMA",
    "DeepSeekV4HCPreScheduleCheckError",
    "verify_deepseek_v4_hc_pre_logical_schedule",
    "verify_deepseek_v4_hc_pre_logical_schedule_certificate",
]
