"""Deterministic logical schedule for DeepSeek V4 grouped output.

The schedule binds the exact ``GROUPED_OUTPUT_PROJECT; COMPLETE`` program to
its typed registers and one authenticated local ``wo_a`` resource.  A logical
slot is only an instruction ordinal.  It is not a cycle, pipeline stage,
bandwidth allocation, physical placement, or execution observation.
"""

from __future__ import annotations

import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_grouped_output import (
    ABI_MAJOR,
    ABI_MINOR,
    CANONICAL_APPLICATION_ID,
    CANONICAL_VERIFICATION_ID,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    MODEL_ID,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    NO_OPERAND,
    RECORD,
    DeepSeekV4GroupedOutputMicrocodeError,
    Instruction,
    Opcode,
    Register,
    assemble,
    build_program_contract,
    build_source_contract,
    decode,
    encode,
    resource_contract,
    tensor_contract,
    topology_mapping,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_source_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_grouped_output_logical_schedule.v1"
LOGICAL_SCHEDULE_STATUS = "logical_schedule_only"
CLAIM_BOUNDARY = (
    "Deterministic logical instruction, register, alias-view, topology, and "
    "canonical-resource ordering for grouped output only; this is not "
    "execution, numerical agreement, timing, bandwidth, physical scheduling, "
    "or PPA evidence."
)
REQUIRED_NONCLAIMS = (
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "end_to_end_model_execution",
    "execution_evidence",
    "full_attention_execution",
    "full_transformer_block_execution",
    "nvidia_comparison",
    "numeric_correctness",
    "output_b_projection",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "rtl_execution",
    "tensor_parallel_collective",
)
ORDERING_POLICY = {
    "alias_rule": (
        "FLATTENED_OUTPUT is a view of GROUPED_OUTPUT produced by the same semantic slot"
    ),
    "completion_rule": "terminal COMPLETE depends on every preceding logical slot",
    "dependency_rule": (
        "every consumed register is external or produced by a lower-numbered slot"
    ),
    "resource_rule": (
        "the resource resolves exactly through the topology-specific canonical wo_a contract"
    ),
    "slot_rule": "one microinstruction per monotonically increasing logical slot",
}


class DeepSeekV4GroupedOutputScheduleError(ValueError):
    """Raised when an exact grouped-output logical schedule cannot be formed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _instruction_identity(instruction: Instruction) -> dict[str, int]:
    return {
        "destination0": int(instruction.destination0),
        "destination1": int(instruction.destination1),
        "flags": instruction.flags,
        "immediate0": instruction.immediate0,
        "immediate1": instruction.immediate1,
        "immediate2": instruction.immediate2,
        "immediate3": instruction.immediate3,
        "opcode": int(instruction.opcode),
        "resource0": int(instruction.resource0),
        "source": int(instruction.source),
    }


def _destination_ids(instruction: Instruction) -> list[int]:
    return [
        int(value)
        for value in (instruction.destination0, instruction.destination1)
        if value != NO_OPERAND
    ]


def _source_ids(instruction: Instruction) -> list[int]:
    return [] if instruction.source == NO_OPERAND else [int(instruction.source)]


def _resource_ids(instruction: Instruction) -> list[int]:
    return [] if instruction.resource0 == NO_OPERAND else [int(instruction.resource0)]


def _resource_table(world_size: int, rank: int) -> list[dict[str, Any]]:
    resources = resource_contract(world_size, rank)
    verify_resource_contract(resources, world_size, rank)
    return [
        {
            "canonical_application_id": spec.canonical_application_id,
            "checkpoint_derived": spec.checkpoint_derived,
            "content_sha256": spec.content_sha256,
            "dtype": spec.dtype,
            "global_group_range": [
                spec.global_group_start,
                spec.global_group_stop,
            ],
            "global_row_range": [spec.global_row_start, spec.global_row_stop],
            "rank": spec.rank,
            "resource_id": int(spec.resource),
            "resource_name": spec.resource.name,
            "role": spec.role,
            "segments": [
                {
                    "assignment_rank": segment.assignment_rank,
                    "byte_offset": segment.byte_offset,
                    "content_sha256": segment.content_sha256,
                    "global_row_range": [
                        segment.global_row_start,
                        segment.global_row_stop,
                    ],
                    "path": segment.path,
                    "size_bytes": segment.size_bytes,
                }
                for segment in spec.segments
            ],
            "shape": list(spec.shape),
            "size_bytes": spec.size_bytes,
            "world_size": spec.world_size,
        }
        for spec in resources
    ]


def _register_table(
    instructions: tuple[Instruction, ...],
    world_size: int,
    rank: int,
) -> list[dict[str, Any]]:
    minimum_specs = tensor_contract(MIN_TOKEN_COUNT, world_size, rank)
    maximum_specs = tensor_contract(MAX_TOKEN_COUNT, world_size, rank)
    verify_tensor_contract(minimum_specs, MIN_TOKEN_COUNT, world_size, rank)
    verify_tensor_contract(maximum_specs, MAX_TOKEN_COUNT, world_size, rank)

    producers: dict[int, int] = {}
    consumers: dict[int, list[int]] = {}
    for slot, instruction in enumerate(instructions):
        for register_id in _source_ids(instruction):
            consumers.setdefault(register_id, []).append(slot)
        for register_id in _destination_ids(instruction):
            if register_id in producers:  # pragma: no cover - frozen program
                raise DeepSeekV4GroupedOutputScheduleError(
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
            or lower.alias_of != upper.alias_of
            or lower.shape[1:] != upper.shape[1:]
            or lower.shape[0] != MIN_TOKEN_COUNT
            or upper.shape[0] != MAX_TOKEN_COUNT
        ):  # pragma: no cover - frozen typed contract
            raise DeepSeekV4GroupedOutputScheduleError(
                f"register {lower.register.name} has inconsistent bounded shapes"
            )
        register_id = int(lower.register)
        records.append(
            {
                "alias_of_register_id": (
                    None if lower.alias_of is None else int(lower.alias_of)
                ),
                "alias_of_register_name": (
                    None if lower.alias_of is None else lower.alias_of.name
                ),
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
        int(Register.GROUPED_ATTENTION_INPUT): None,
    }
    slots: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        sources = _source_ids(instruction)
        destinations = _destination_ids(instruction)
        resources = _resource_ids(instruction)
        if any(value not in register_ids for value in (*sources, *destinations)):
            raise DeepSeekV4GroupedOutputScheduleError(
                f"instruction {index} references a register outside the tensor contract"
            )
        if any(value not in resource_ids for value in resources):
            raise DeepSeekV4GroupedOutputScheduleError(
                f"instruction {index} references a resource outside the resource contract"
            )
        missing = [value for value in sources if value not in producers]
        if missing:
            raise DeepSeekV4GroupedOutputScheduleError(
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
                "opcode": Opcode(instruction.opcode).name,
                "opcode_code": int(instruction.opcode),
                "resource_ids": resources,
                "slot": index,
                "source_register_ids": sources,
                "terminal": terminal,
            }
        )
        for register_id in destinations:
            if register_id in producers:  # pragma: no cover - frozen program
                raise DeepSeekV4GroupedOutputScheduleError(
                    f"instruction {index} overwrites register {register_id}"
                )
            producers[register_id] = index
    return slots


def build_deepseek_v4_grouped_output_logical_schedule(
    world_size: int,
    rank: int,
    instructions: tuple[Instruction, ...] | None = None,
) -> dict[str, Any]:
    """Build the canonical logical schedule for one legal local-rank mapping."""

    program = assemble(world_size, rank) if instructions is None else instructions
    try:
        verify(program, world_size, rank)
        program_bytes = encode(program, world_size, rank)
        decoded = decode(program_bytes)
        verify(decoded, world_size, rank)
    except DeepSeekV4GroupedOutputMicrocodeError as exc:
        raise DeepSeekV4GroupedOutputScheduleError(
            f"grouped-output schedule requires exact microcode: {exc}"
        ) from exc
    if decoded != program:  # pragma: no cover - codec invariant
        raise DeepSeekV4GroupedOutputScheduleError(
            "grouped-output program changes identity after ABI roundtrip"
        )

    source = build_source_contract()
    verify_source_contract(source)
    program_contract = build_program_contract(world_size, rank)
    verify_program_contract(program_contract, world_size, rank)
    mapping = topology_mapping(world_size, rank)
    resources = _resource_table(world_size, rank)
    registers = _register_table(program, world_size, rank)
    slots = _slots(
        program,
        {record["register_id"] for record in registers},
        {record["resource_id"] for record in resources},
    )
    summary = {
        "alias_register_count": sum(
            record["alias_of_register_id"] is not None for record in registers
        ),
        "canonical_resource_bytes": sum(record["size_bytes"] for record in resources),
        "complete_count": sum(slot["opcode"] == "COMPLETE" for slot in slots),
        "dependency_edge_count": sum(len(slot["dependency_slots"]) for slot in slots),
        "evidence_observable_register_count": sum(
            record["evidence_observable"] for record in registers
        ),
        "external_input_register_count": sum(
            record["producer_kind"] == "external" for record in registers
        ),
        "grouped_output_project_count": sum(
            slot["opcode"] == "GROUPED_OUTPUT_PROJECT" for slot in slots
        ),
        "instruction_count": len(program),
        "live_at_complete_register_count": sum(
            record["live_at_complete"] for record in registers
        ),
        "local_group_count": mapping.local_group_count,
        "produced_register_count": sum(
            record["producer_kind"] == "slot" for record in registers
        ),
        "register_count": len(registers),
        "resource_count": len(resources),
        "resource_read_count": sum(len(slot["resource_ids"]) for slot in slots),
        "slot_count": len(slots),
    }
    body = {
        "claim_boundary": CLAIM_BOUNDARY,
        "identity": {
            "abi_magic_ascii": MAGIC.decode("ascii"),
            "abi_major": ABI_MAJOR,
            "abi_minor": ABI_MINOR,
            "canonical_application_id": CANONICAL_APPLICATION_ID,
            "canonical_verification_id": CANONICAL_VERIFICATION_ID,
            "instruction_record_bytes": RECORD.size,
            "model_id": MODEL_ID,
            "program_bytes": len(program_bytes),
            "program_contract_id": program_contract["contract_id"],
            "program_sha256": hashlib.sha256(program_bytes).hexdigest(),
            "register_table_sha256": _sha256(registers),
            "repository": MODEL_REPOSITORY,
            "resource_table_sha256": _sha256(resources),
            "revision": MODEL_REVISION,
            "source_contract_id": source["source_contract_id"],
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
        "topology": {
            "global_group_range": [
                mapping.global_group_start,
                mapping.global_group_stop,
            ],
            "global_row_range": [mapping.global_row_start, mapping.global_row_stop],
            "local_group_count": mapping.local_group_count,
            "rank": rank,
            "world_size": world_size,
        },
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
    "DeepSeekV4GroupedOutputScheduleError",
    "build_deepseek_v4_grouped_output_logical_schedule",
]
