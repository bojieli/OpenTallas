"""Deterministic logical schedule for typed DeepSeek V4 RoPE microcode.

Logical slots record semantic ordering, complete tensor/register identity,
phasor-resource selection, and the explicit request-to-table position mapping.
A slot is an ordinal, not a cycle, pipeline stage, physical placement, or
bandwidth allocation.
"""

from __future__ import annotations

import hashlib
from typing import Any

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_rope import (
    ABI_MAJOR,
    ABI_MINOR,
    EXPLICIT_NON_CLAIMS,
    MAGIC,
    MODEL_ID,
    NUMERIC_PROFILE,
    RECORD,
    DeepSeekV4RopeMicrocodeError,
    Instruction,
    Opcode,
    RopeDescriptor,
    assemble,
    build_program_contract,
    descriptor_id,
    descriptor_record,
    encode,
    position_contract,
    resource_contract,
    state_contract,
    tensor_contract,
    verify,
    verify_descriptor,
    verify_position_contract,
    verify_program_contract,
    verify_resource_contract,
    verify_state_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_rope_logical_schedule.v1"
LOGICAL_SCHEDULE_STATUS = "deterministic_logical_schedule_only"
CLAIM_BOUNDARY = (
    "Deterministic instruction, register, generated-phasor-resource, and "
    "request-to-table position ordering for one typed ROPE_APPLY or "
    "ROPE_INVERSE transaction only; no execution, timing, bandwidth, "
    "physical scheduling, RTL, full-model, or PPA claim."
)
ORDERING_POLICY = {
    "alias_rule": "input and output are distinct logical registers",
    "completion_rule": "terminal COMPLETE depends on the entire RoPE transaction",
    "dependency_rule": "every input is external or produced by a lower logical slot",
    "position_rule": "all sampled table positions are descriptor-derived and bounded",
    "resource_rule": "the phasor resource exactly matches the explicit profile",
    "slot_rule": "one instruction per monotonically increasing logical slot",
}
REQUIRED_NONCLAIMS = tuple(
    sorted(
        {
            *EXPLICIT_NON_CLAIMS,
            "bandwidth_allocation",
            "numeric_reexecution",
            "physical_topology",
        }
    )
)


class DeepSeekV4RopeScheduleError(ValueError):
    """Raised when typed RoPE microcode cannot form its canonical schedule."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _tensor_table(descriptor: RopeDescriptor) -> list[dict[str, Any]]:
    specs = tensor_contract(descriptor)
    verify_tensor_contract(specs, descriptor)
    return [
        {
            "access": spec.access,
            "alias_of_register_id": (
                None if spec.alias_of is None else int(spec.alias_of)
            ),
            "dtype": spec.dtype,
            "live_at_complete": spec.live_at_complete,
            "preserved_prefix_width": spec.preserved_prefix_width,
            "register_id": int(spec.register),
            "register_name": spec.register.name,
            "rotary_suffix_width": spec.rotary_suffix_width,
            "shape": list(spec.shape),
            "channel_semantics": spec.channel_semantics,
        }
        for spec in specs
    ]


def _resource_table(descriptor: RopeDescriptor) -> list[dict[str, Any]]:
    specs = resource_contract(descriptor)
    verify_resource_contract(specs, descriptor)
    return [
        {
            "beta_fast": spec.beta_fast,
            "beta_slow": spec.beta_slow,
            "checkpoint_derived": spec.checkpoint_derived,
            "correction_high": spec.correction_high,
            "correction_low": spec.correction_low,
            "complex_pair_count": spec.complex_pair_count,
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
        for spec in specs
    ]


def _position_record(descriptor: RopeDescriptor) -> dict[str, Any]:
    contract = position_contract(descriptor)
    verify_position_contract(contract, descriptor)
    return {
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


def _state_record(descriptor: RopeDescriptor) -> dict[str, Any]:
    contract = state_contract(descriptor)
    verify_state_contract(contract, descriptor)
    return {
        "alias_policy": contract.alias_policy,
        "mutable_state_reads": list(contract.mutable_state_reads),
        "mutable_state_writes": list(contract.mutable_state_writes),
        "output_commit": contract.output_commit,
        "phasor_resource_id": int(contract.phasor_resource),
        "phasor_resource_name": contract.phasor_resource.name,
        "preserved_prefix_policy": contract.preserved_prefix_policy,
        "request_inputs": list(contract.request_inputs),
        "rotary_suffix_width": contract.rotary_suffix_width,
    }


def _slots(
    instructions: tuple[Instruction, ...],
    descriptor: RopeDescriptor,
) -> list[dict[str, Any]]:
    first, complete = instructions
    if first.descriptor != descriptor or complete.opcode is not Opcode.COMPLETE:
        raise DeepSeekV4RopeScheduleError(
            "verified program unexpectedly differs from its schedule descriptor"
        )
    first_identity = {
        "descriptor_id": descriptor_id(descriptor),
        "destination_register_id": int(first.destination),
        "flags": first.flags,
        "opcode": first.opcode.name,
        "opcode_code": int(first.opcode),
        "resource_id": int(first.resource),
        "source_register_id": int(first.source),
    }
    complete_identity = {
        "flags": complete.flags,
        "opcode": complete.opcode.name,
        "opcode_code": int(complete.opcode),
    }
    return [
        {
            "dependency_slots": [],
            "destination_register_ids": [int(first.destination)],
            "external_input_register_ids": [int(first.source)],
            "instruction_index": 0,
            "instruction_sha256": _sha256(first_identity),
            "logical_table_position_count": descriptor.sequence_length,
            "opcode": first.opcode.name,
            "opcode_code": int(first.opcode),
            "position_stride": descriptor.position_stride,
            "resource_ids": [int(first.resource)],
            "source_register_ids": [int(first.source)],
            "slot": 0,
            "table_position_first": descriptor.table_start_position,
            "table_position_last": descriptor.last_table_position,
            "terminal": False,
        },
        {
            "dependency_slots": [0],
            "destination_register_ids": [],
            "external_input_register_ids": [],
            "instruction_index": 1,
            "instruction_sha256": _sha256(complete_identity),
            "logical_table_position_count": 0,
            "opcode": complete.opcode.name,
            "opcode_code": int(complete.opcode),
            "position_stride": 0,
            "resource_ids": [],
            "source_register_ids": [],
            "slot": 1,
            "table_position_first": None,
            "table_position_last": None,
            "terminal": True,
        },
    ]


def build_deepseek_v4_rope_logical_schedule(
    descriptor: RopeDescriptor,
    instructions: tuple[Instruction, ...] | None = None,
) -> dict[str, Any]:
    """Build the one canonical logical schedule for a complete RoPE command."""

    try:
        verify_descriptor(descriptor)
        program = assemble(descriptor) if instructions is None else instructions
        verify(program, descriptor)
        program_bytes = encode(program)
        program_contract = build_program_contract(descriptor)
        verify_program_contract(program_contract, descriptor)
    except DeepSeekV4RopeMicrocodeError as exc:
        raise DeepSeekV4RopeScheduleError(
            f"logical scheduling requires exact typed RoPE microcode: {exc}"
        ) from exc

    tensors = _tensor_table(descriptor)
    resources = _resource_table(descriptor)
    position = _position_record(descriptor)
    state = _state_record(descriptor)
    slots = _slots(program, descriptor)
    summary = {
        "complete_count": 1,
        "dependency_edge_count": 1,
        "external_input_register_count": 1,
        "generated_phasor_resource_bytes": sum(
            resource["size_bytes"] for resource in resources
        ),
        "instruction_count": len(program),
        "logical_table_position_count": descriptor.sequence_length,
        "mutable_state_read_count": len(state["mutable_state_reads"]),
        "mutable_state_write_count": len(state["mutable_state_writes"]),
        "register_count": len(tensors),
        "resource_count": len(resources),
        "slot_count": len(slots),
    }
    body = {
        "claim_boundary": CLAIM_BOUNDARY,
        "descriptor": descriptor_record(descriptor),
        "identity": {
            "abi_magic_ascii": MAGIC.decode("ascii"),
            "abi_major": ABI_MAJOR,
            "abi_minor": ABI_MINOR,
            "descriptor_id": descriptor_id(descriptor),
            "instruction_record_bytes": RECORD.size,
            "model_id": MODEL_ID,
            "numeric_profile": NUMERIC_PROFILE,
            "program_bytes": len(program_bytes),
            "program_contract_id": program_contract["contract_id"],
            "program_sha256": hashlib.sha256(program_bytes).hexdigest(),
            "register_table_sha256": _sha256(tensors),
            "resource_table_sha256": _sha256(resources),
        },
        "ordering_policy": dict(ORDERING_POLICY),
        "position_contract": position,
        "registers": tensors,
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "resources": resources,
        "schema": LOGICAL_SCHEDULE_SCHEMA,
        "slots": slots,
        "state_contract": state,
        "status": LOGICAL_SCHEDULE_STATUS,
        "summary": summary,
    }
    return {**body, "schedule_id": _sha256(body)}


__all__ = [
    "CLAIM_BOUNDARY",
    "LOGICAL_SCHEDULE_SCHEMA",
    "LOGICAL_SCHEDULE_STATUS",
    "ORDERING_POLICY",
    "REQUIRED_NONCLAIMS",
    "DeepSeekV4RopeScheduleError",
    "build_deepseek_v4_rope_logical_schedule",
]
