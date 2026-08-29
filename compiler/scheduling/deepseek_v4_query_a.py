"""Canonical logical schedule for the exact DeepSeek V4 Query-A fragment.

The schedule binds the already frozen ``RMS_NORM; FP8_LINEAR; COMPLETE``
microprogram to its typed registers and bounded resources.  A logical slot is
only a semantic program ordinal.  It is not a cycle, pipeline stage, physical
placement, bandwidth allocation, or execution observation.
"""

from __future__ import annotations

import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    ABI_MAJOR,
    ABI_MINOR,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    NO_OPERAND,
    RECORD,
    Instruction,
    Opcode,
    Register,
)
from compiler.microcode.deepseek_v4_query_a import (
    MODEL_ID,
    DeepSeekV4QueryAMicrocodeError,
    assemble,
    build_program_contract,
    decode,
    encode,
    resource_contract,
    tensor_contract,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_query_a_logical_schedule.v1"
LOGICAL_SCHEDULE_STATUS = "logical_schedule_only"
CLAIM_BOUNDARY = (
    "Deterministic logical instruction, register, and resource ordering for the "
    "exact weighted-RMS and complete Query-A fragment only; this is not "
    "execution, timing, bandwidth, physical scheduling, numeric-correctness, "
    "or PPA evidence."
)
REQUIRED_NONCLAIMS = (
    "attention_completion",
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "execution_evidence",
    "full_model_execution",
    "hc_pre_execution",
    "nvidia_comparison",
    "numeric_correctness",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "query_b",
    "rtl_execution",
    "transformer_block_completion",
)
ORDERING_POLICY = {
    "completion_rule": "terminal COMPLETE depends on every preceding logical slot",
    "dependency_rule": (
        "every consumed register is external or produced by a lower-numbered slot"
    ),
    "resource_rule": (
        "resource IDs resolve exactly through the committed Query-A resource contract"
    ),
    "slot_rule": "one microinstruction per monotonically increasing logical slot",
}


class DeepSeekV4QueryAScheduleError(ValueError):
    """Raised when the exact Query-A fragment cannot form its logical schedule."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


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


def _destination_ids(instruction: Instruction) -> list[int]:
    return [
        int(value)
        for value in (
            instruction.destination0,
            instruction.destination1,
            instruction.destination2,
            instruction.destination3,
            instruction.destination4,
        )
        if value != NO_OPERAND
    ]


def _source_ids(instruction: Instruction) -> list[int]:
    return [] if instruction.source == NO_OPERAND else [int(instruction.source)]


def _resource_ids(instruction: Instruction) -> list[int]:
    return [
        int(value)
        for value in (
            instruction.resource0,
            instruction.resource1,
            instruction.resource2,
            instruction.resource3,
        )
        if value != NO_OPERAND
    ]


def _resource_table() -> list[dict[str, Any]]:
    resources = resource_contract()
    verify_resource_contract(resources)
    return [
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
        for spec in resources
    ]


def _register_table(
    instructions: tuple[Instruction, ...],
) -> list[dict[str, Any]]:
    minimum_specs = tensor_contract(MIN_TOKEN_COUNT)
    maximum_specs = tensor_contract(MAX_TOKEN_COUNT)
    verify_tensor_contract(minimum_specs, MIN_TOKEN_COUNT)
    verify_tensor_contract(maximum_specs, MAX_TOKEN_COUNT)
    if len(minimum_specs) != len(maximum_specs):  # pragma: no cover - frozen contract
        raise DeepSeekV4QueryAScheduleError(
            "Query-A tensor bounds have different register counts"
        )

    producers: dict[int, int] = {}
    consumers: dict[int, list[int]] = {}
    for slot, instruction in enumerate(instructions):
        for register_id in _source_ids(instruction):
            consumers.setdefault(register_id, []).append(slot)
        for register_id in _destination_ids(instruction):
            if register_id in producers:  # pragma: no cover - frozen contract
                raise DeepSeekV4QueryAScheduleError(
                    f"register {register_id} has more than one producer"
                )
            producers[register_id] = slot

    records: list[dict[str, Any]] = []
    for lower, upper in zip(minimum_specs, maximum_specs, strict=True):
        if (
            lower.register != upper.register
            or lower.dtype != upper.dtype
            or lower.live_at_complete != upper.live_at_complete
            or lower.evidence_observable != upper.evidence_observable
            or lower.shape[1:] != upper.shape[1:]
            or lower.shape[0] != MIN_TOKEN_COUNT
            or upper.shape[0] != MAX_TOKEN_COUNT
        ):  # pragma: no cover - frozen contract
            raise DeepSeekV4QueryAScheduleError(
                f"register {lower.register.name} has an inconsistent bounded shape"
            )
        register_id = int(lower.register)
        records.append(
            {
                "consumer_slots": consumers.get(register_id, []),
                "dtype": lower.dtype,
                "evidence_observable": lower.evidence_observable,
                "live_at_complete": lower.live_at_complete,
                "producer_kind": "slot" if register_id in producers else "external",
                "producer_slot": producers.get(register_id),
                "register_id": register_id,
                "register_name": lower.register.name,
                "token_major_shape_suffix": list(lower.shape[1:]),
            }
        )
    return records


def _slots(
    instructions: tuple[Instruction, ...],
    register_ids: set[int],
    resource_ids: set[int],
) -> list[dict[str, Any]]:
    producers: dict[int, int | None] = {
        int(Register.ATTENTION_INPUT): None,
    }
    slots: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        sources = _source_ids(instruction)
        destinations = _destination_ids(instruction)
        resources = _resource_ids(instruction)
        if any(value not in register_ids for value in (*sources, *destinations)):
            raise DeepSeekV4QueryAScheduleError(
                f"instruction {index} references a register outside the tensor contract"
            )
        if any(value not in resource_ids for value in resources):
            raise DeepSeekV4QueryAScheduleError(
                f"instruction {index} references a resource outside the resource contract"
            )
        missing = [value for value in sources if value not in producers]
        if missing:
            raise DeepSeekV4QueryAScheduleError(
                f"instruction {index} reads registers without producers: {missing}"
            )
        dependencies = sorted(
            {
                producer
                for value in sources
                if (producer := producers[value]) is not None
            }
        )
        external = sorted(value for value in sources if producers[value] is None)
        terminal = instruction.opcode == Opcode.COMPLETE
        if terminal:
            dependencies = list(range(index))
        slots.append(
            {
                "dependency_slots": dependencies,
                "destination_register_ids": destinations,
                "external_input_register_ids": external,
                "flags": instruction.flags,
                "immediates": [
                    instruction.immediate0,
                    instruction.immediate1,
                    instruction.immediate2,
                    instruction.immediate3,
                ],
                "instruction_index": index,
                "instruction_sha256": _sha256(_instruction_identity(instruction)),
                "opcode": instruction.opcode.name,
                "opcode_code": int(instruction.opcode),
                "resource_ids": resources,
                "slot": index,
                "source_register_ids": sources,
                "terminal": terminal,
            }
        )
        for register_id in destinations:
            if register_id in producers:
                raise DeepSeekV4QueryAScheduleError(
                    f"instruction {index} overwrites register {register_id}"
                )
            producers[register_id] = index
    return slots


def build_deepseek_v4_query_a_logical_schedule(
    instructions: tuple[Instruction, ...] | None = None,
) -> dict[str, Any]:
    """Build the sole canonical logical schedule for the exact Query-A fragment."""

    program = assemble() if instructions is None else instructions
    try:
        verify(program)
        program_bytes = encode(program)
        decoded = decode(program_bytes)
        verify(decoded)
    except DeepSeekV4QueryAMicrocodeError as exc:
        raise DeepSeekV4QueryAScheduleError(
            f"Query-A logical schedule requires the exact microcode fragment: {exc}"
        ) from exc
    if decoded != program:  # pragma: no cover - exact codec invariant
        raise DeepSeekV4QueryAScheduleError(
            "Query-A microcode changes identity after wire-ABI roundtrip"
        )

    program_contract = build_program_contract()
    verify_program_contract(program_contract)
    resources = _resource_table()
    registers = _register_table(program)
    slots = _slots(
        program,
        {record["register_id"] for record in registers},
        {record["resource_id"] for record in resources},
    )
    summary = {
        "checkpoint_parameter_bytes": sum(
            record["size_bytes"] for record in resources if record["checkpoint_derived"]
        ),
        "complete_count": sum(slot["opcode"] == "COMPLETE" for slot in slots),
        "dependency_edge_count": sum(len(slot["dependency_slots"]) for slot in slots),
        "evidence_observable_register_count": sum(
            record["evidence_observable"] for record in registers
        ),
        "external_input_register_count": sum(
            record["producer_kind"] == "external" for record in registers
        ),
        "fp8_linear_count": sum(slot["opcode"] == "FP8_LINEAR" for slot in slots),
        "generated_constant_bytes": sum(
            record["size_bytes"]
            for record in resources
            if not record["checkpoint_derived"]
        ),
        "instruction_count": len(program),
        "live_at_complete_register_count": sum(
            record["live_at_complete"] for record in registers
        ),
        "produced_register_count": sum(
            record["producer_kind"] == "slot" for record in registers
        ),
        "register_count": len(registers),
        "resource_count": len(resources),
        "resource_read_count": sum(len(slot["resource_ids"]) for slot in slots),
        "rms_norm_count": sum(slot["opcode"] == "RMS_NORM" for slot in slots),
        "slot_count": len(slots),
    }
    body = {
        "claim_boundary": CLAIM_BOUNDARY,
        "identity": {
            "abi_magic_ascii": MAGIC.decode("ascii"),
            "abi_major": ABI_MAJOR,
            "abi_minor": ABI_MINOR,
            "instruction_record_bytes": RECORD.size,
            "model_id": MODEL_ID,
            "program_bytes": len(program_bytes),
            "program_contract_id": program_contract["contract_id"],
            "program_sha256": hashlib.sha256(program_bytes).hexdigest(),
            "register_table_sha256": _sha256(registers),
            "resource_table_sha256": _sha256(resources),
            "token_count_maximum": MAX_TOKEN_COUNT,
            "token_count_minimum": MIN_TOKEN_COUNT,
        },
        "ordering_policy": dict(ORDERING_POLICY),
        "registers": registers,
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "resources": resources,
        "schema": LOGICAL_SCHEDULE_SCHEMA,
        "slots": slots,
        "status": LOGICAL_SCHEDULE_STATUS,
        "summary": summary,
    }
    return {
        **body,
        "schedule_id": _sha256(body),
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "LOGICAL_SCHEDULE_SCHEMA",
    "LOGICAL_SCHEDULE_STATUS",
    "ORDERING_POLICY",
    "REQUIRED_NONCLAIMS",
    "DeepSeekV4QueryAScheduleError",
    "build_deepseek_v4_query_a_logical_schedule",
]
