from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import struct
import zlib

import pytest

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    assemble as assemble_integrated,
    encode as encode_shared,
    resource_contract as integrated_resource_contract,
)
from compiler.microcode.deepseek_v4_hc_pre import (
    EVIDENCE_OBSERVABLES,
    EXPLICIT_NON_CLAIMS,
    HEADER,
    LIVE_AT_COMPLETE,
    PROGRAM_BINDING,
    RECORD,
    DeepSeekV4HCPreMicrocodeError,
    Opcode,
    Register,
    Resource,
    assemble,
    build_program_contract,
    decode,
    disassemble,
    encode,
    resource_contract,
    tensor_contract,
    validate_token_count,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_tensor_contract,
)


def _repair_crc(payload: bytearray) -> None:
    struct.pack_into(
        "<I",
        payload,
        12,
        zlib.crc32(payload[HEADER.size :]) & 0xFFFFFFFF,
    )


def test_hc_pre_fragment_is_exact_and_integrated_abi_compatible() -> None:
    instructions = assemble()
    payload = encode(instructions)
    assert len(payload) == HEADER.size + 2 * RECORD.size
    assert decode(payload) == instructions
    verify(decode(payload))
    assert [item.opcode for item in instructions] == [
        Opcode.HC_PRE,
        Opcode.COMPLETE,
    ]

    integrated = assemble_integrated()
    assert instructions[0] == integrated[2]
    assert instructions[1] == integrated[-1]
    assert PROGRAM_BINDING.instruction_index == 0
    assert PROGRAM_BINDING.input_register is Register.HC_HIDDEN
    assert PROGRAM_BINDING.base_resource is Resource.HC_ATTN_BASE
    assert PROGRAM_BINDING.projection_resource is Resource.HC_ATTN_PROJECTION
    assert PROGRAM_BINDING.scale_resource is Resource.HC_ATTN_SCALE

    text = disassemble(instructions)
    assert text.startswith(
        "# OpenTallas DeepSeek V4 HC_PRE fragment ABI 1.0\n0000 HC_PRE"
    )
    assert text.endswith("imm=[0x00000000,0x00000000,0x00000000,0x00000000]\n")


def test_hc_pre_fragment_binds_every_operand_and_numeric_immediate() -> None:
    instruction = assemble()[0]
    assert instruction.destination0 == Register.ATTENTION_INPUT
    assert instruction.destination1 == Register.ATTENTION_PRE
    assert instruction.destination2 == Register.ATTENTION_POST
    assert instruction.destination3 == Register.ATTENTION_COMBINATION
    assert instruction.destination4 == Register.ATTENTION_RESIDUAL
    assert instruction.source == Register.HC_HIDDEN
    assert instruction.resource0 == Resource.HC_ATTN_BASE
    assert instruction.resource1 == Resource.HC_ATTN_PROJECTION
    assert instruction.resource2 == Resource.HC_ATTN_SCALE
    assert instruction.resource3 == 0xFFFFFFFF
    assert (
        instruction.immediate0,
        instruction.immediate1,
        instruction.immediate2,
        instruction.immediate3,
    ) == (4, 20, 0x358637BD, 0x358637BD)


def test_hc_pre_fragment_typed_state_is_complete_and_bounded() -> None:
    specs = tensor_contract(3)
    by_register = {item.register: item for item in specs}
    assert tuple(by_register) == (
        Register.HC_HIDDEN,
        Register.ATTENTION_INPUT,
        Register.ATTENTION_PRE,
        Register.ATTENTION_POST,
        Register.ATTENTION_COMBINATION,
        Register.ATTENTION_RESIDUAL,
    )
    assert by_register[Register.HC_HIDDEN].shape == (3, 4, 4096)
    assert by_register[Register.ATTENTION_INPUT].shape == (3, 4096)
    assert by_register[Register.ATTENTION_PRE].shape == (3, 4)
    assert by_register[Register.ATTENTION_POST].shape == (3, 4)
    assert by_register[Register.ATTENTION_COMBINATION].shape == (3, 4, 4)
    assert by_register[Register.ATTENTION_RESIDUAL].shape == (3, 4, 4096)
    assert tuple(item.register for item in specs if item.live_at_complete) == (
        LIVE_AT_COMPLETE
    )
    assert tuple(item.register for item in specs if item.evidence_observable) == (
        EVIDENCE_OBSERVABLES
    )
    assert not by_register[Register.ATTENTION_PRE].live_at_complete
    assert by_register[Register.ATTENTION_PRE].evidence_observable
    verify_tensor_contract(specs, 3)

    changed = list(specs)
    changed[4] = replace(changed[4], shape=(3, 16))
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="typed HC_PRE state"):
        verify_tensor_contract(tuple(changed), 3)


@pytest.mark.parametrize("token_count", [0, 5, -1, True, 1.0, "1"])
def test_hc_pre_fragment_rejects_out_of_bounds_token_count(
    token_count: object,
) -> None:
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="token_count"):
        validate_token_count(token_count)  # type: ignore[arg-type]
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="token_count"):
        tensor_contract(token_count)  # type: ignore[arg-type]


def test_hc_pre_fragment_resource_table_is_exact_integrated_subset() -> None:
    resources = resource_contract()
    assert [item.resource for item in resources] == [
        Resource.HC_ATTN_BASE,
        Resource.HC_ATTN_PROJECTION,
        Resource.HC_ATTN_SCALE,
    ]
    assert [item.role for item in resources] == [
        "hyper_connection.attn.base",
        "hyper_connection.attn.projection",
        "hyper_connection.attn.scale",
    ]
    assert [item.shape for item in resources] == [(24,), (24, 16384), (3,)]
    assert [item.size_bytes for item in resources] == [96, 1_572_864, 12]
    assert all(item.dtype == "F32" for item in resources)
    assert all(item.checkpoint_derived for item in resources)
    assert resources == integrated_resource_contract()[4:7]
    verify_resource_contract(resources)

    changed = list(resources)
    changed[1] = replace(changed[1], size_bytes=1_572_860)
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="artifact resources"):
        verify_resource_contract(tuple(changed))


def test_hc_pre_fragment_rejects_every_semantic_operand_drift() -> None:
    instructions = assemble()
    first, complete = instructions
    mutations = (
        instructions[:-1],
        (complete, first),
        (replace(first, destination0=Register.ATTENTION_PRE), complete),
        (replace(first, source=Register.EMBEDDING), complete),
        (replace(first, resource0=Resource.HC_ATTN_SCALE), complete),
        (replace(first, resource1=Resource.HC_ATTN_BASE), complete),
        (replace(first, resource2=Resource.HC_ATTN_PROJECTION), complete),
        (replace(first, immediate0=3), complete),
        (replace(first, immediate1=19), complete),
        (replace(first, immediate2=0x358637BC), complete),
        (replace(first, immediate3=0x358637BC), complete),
        (first, replace(complete, source=Register.HC_HIDDEN)),
    )
    for changed in mutations:
        with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="does not exactly"):
            verify(changed)
        with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="does not exactly"):
            encode(changed)

    # A valid shared-ABI CRC cannot make a semantically different fragment legal.
    structurally_valid = encode_shared(mutations[2])
    decoded = decode(structurally_valid)
    assert decoded == mutations[2]
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="does not exactly"):
        verify(decoded)


def test_hc_pre_fragment_decode_rejects_corruption_and_malformed_records() -> None:
    payload = encode(assemble())
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="body length"):
        decode(payload[:-1])
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="body length"):
        decode(payload + b"\x00")

    corrupt = bytearray(payload)
    corrupt[-1] ^= 1
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="CRC32"):
        decode(bytes(corrupt))

    unknown = bytearray(payload)
    unknown[HEADER.size] = 0x42
    _repair_crc(unknown)
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="unknown opcode"):
        decode(bytes(unknown))

    flagged = bytearray(payload)
    flagged[HEADER.size + 1] = 1
    _repair_crc(flagged)
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="unsupported flags"):
        decode(bytes(flagged))

    reserved = bytearray(payload)
    reserved[HEADER.size + 2] = 1
    _repair_crc(reserved)
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="reserved bits"):
        decode(bytes(reserved))


def test_hc_pre_program_contract_is_hash_bound_and_contains_no_expectations() -> None:
    contract = build_program_contract()
    body = copy.deepcopy(contract)
    contract_id = body.pop("contract_id")
    assert hashlib.sha256(canonical_json_bytes(body)).hexdigest() == contract_id
    assert contract["program_sha256"] == hashlib.sha256(encode(assemble())).hexdigest()
    assert contract["program_bytes"] == HEADER.size + 2 * RECORD.size
    assert contract["operator_sequence"] == ["HC_PRE", "COMPLETE"]
    assert contract["required_nonclaims"] == list(EXPLICIT_NON_CLAIMS)
    assert "expected_outputs" not in contract
    assert "expected_values" not in contract
    verify_program_contract(contract)

    changed = copy.deepcopy(contract)
    changed["dimensions"]["sinkhorn_iterations"] = 19
    changed_body = copy.deepcopy(changed)
    changed_body.pop("contract_id")
    changed["contract_id"] = hashlib.sha256(
        canonical_json_bytes(changed_body)
    ).hexdigest()
    with pytest.raises(DeepSeekV4HCPreMicrocodeError, match="hash-bound"):
        verify_program_contract(changed)
