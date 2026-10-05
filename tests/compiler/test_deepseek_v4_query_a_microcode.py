from __future__ import annotations

from dataclasses import replace
import hashlib
import struct

import pytest

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    DENSE_BLOCK_SIZE,
    HIDDEN_SIZE,
    NO_OPERAND,
    QUERY_A_OUTPUT_FEATURES,
    RMS_EPSILON_BINARY32_BITS,
)
from compiler.microcode.deepseek_v4_query_a import (
    EVIDENCE_OBSERVABLES,
    EXPLICIT_NON_CLAIMS,
    HEADER,
    LIVE_AT_COMPLETE,
    PROGRAM_BINDING,
    RECORD,
    DeepSeekV4QueryAMicrocodeError,
    Instruction,
    Opcode,
    Register,
    Resource,
    assemble,
    build_program_contract,
    decode,
    disassemble,
    encode,
    exhaustive_row_payload,
    resource_contract,
    tensor_contract,
    validate_exhaustive_row_payload,
    validate_token_count,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_tensor_contract,
)


def test_query_a_program_has_exact_causal_operator_sequence_and_bindings() -> None:
    program = assemble()

    assert [instruction.opcode for instruction in program] == [
        Opcode.RMS_NORM,
        Opcode.FP8_LINEAR,
        Opcode.COMPLETE,
    ]
    rms, linear, complete = program
    assert rms == Instruction(
        Opcode.RMS_NORM,
        destination0=Register.ATTENTION_NORMALIZED,
        source=Register.ATTENTION_INPUT,
        resource0=Resource.ATTN_NORM_WEIGHT,
        immediate0=HIDDEN_SIZE,
        immediate1=RMS_EPSILON_BINARY32_BITS,
    )
    assert linear == Instruction(
        Opcode.FP8_LINEAR,
        destination0=Register.QUERY_A,
        source=Register.ATTENTION_NORMALIZED,
        resource0=Resource.QUERY_A_WEIGHT,
        resource1=Resource.QUERY_A_SCALE,
        resource2=Resource.QUERY_A_EXHAUSTIVE_ROWS,
        immediate0=QUERY_A_OUTPUT_FEATURES,
        immediate1=DENSE_BLOCK_SIZE,
    )
    assert complete == Instruction(Opcode.COMPLETE)
    assert PROGRAM_BINDING.rms_instruction_index == 0
    assert PROGRAM_BINDING.linear_instruction_index == 1
    verify(program)


def test_query_a_program_roundtrips_shared_wire_abi_and_disassembles() -> None:
    program = assemble()
    payload = encode(program)

    assert len(payload) == HEADER.size + 3 * RECORD.size == 196
    assert decode(payload) == program
    verify(decode(payload))
    text = disassemble(program)
    assert text.startswith(
        "# OpenTallas DeepSeek V4 weighted-RMS/query-A fragment ABI 1.0\n"
    )
    assert [line.split()[1] for line in text.splitlines()[1:]] == [
        "RMS_NORM",
        "FP8_LINEAR",
        "COMPLETE",
    ]


@pytest.mark.parametrize(
    "mutated",
    [
        assemble()[:-1],
        tuple(reversed(assemble())),
        (replace(assemble()[0], destination0=Register.QUERY_A), *assemble()[1:]),
        (replace(assemble()[0], resource0=Resource.QUERY_A_WEIGHT), *assemble()[1:]),
        (replace(assemble()[0], immediate0=HIDDEN_SIZE - 1), *assemble()[1:]),
        (
            assemble()[0],
            replace(assemble()[1], source=Register.ATTENTION_INPUT),
            assemble()[2],
        ),
        (
            assemble()[0],
            replace(assemble()[1], resource2=NO_OPERAND),
            assemble()[2],
        ),
        (
            assemble()[0],
            replace(assemble()[1], immediate0=QUERY_A_OUTPUT_FEATURES - 1),
            assemble()[2],
        ),
        (*assemble()[:-1], replace(assemble()[-1], flags=1)),
    ],
)
def test_query_a_program_rejects_every_semantic_schedule_drift(
    mutated: tuple[Instruction, ...],
) -> None:
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="exactly lower"):
        verify(mutated)
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="exactly lower"):
        encode(mutated)


def test_query_a_decoder_rejects_corrupt_header_body_crc_and_types() -> None:
    payload = encode(assemble())
    cases = [
        payload[: HEADER.size - 1],
        b"BAD!" + payload[4:],
        payload[:-1],
        payload + b"\x00",
        payload[: HEADER.size + 7]
        + bytes([payload[HEADER.size + 7] ^ 1])
        + payload[HEADER.size + 8 :],
    ]
    for candidate in cases:
        with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="cannot decode"):
            decode(candidate)
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="exact bytes"):
        decode(bytearray(payload))  # type: ignore[arg-type]


@pytest.mark.parametrize("token_count", [1, 2, 3, 4])
def test_query_a_typed_state_preserves_bounded_token_axis(token_count: int) -> None:
    contract = tensor_contract(token_count)
    by_register = {spec.register: spec for spec in contract}

    assert tuple(by_register) == (
        Register.ATTENTION_INPUT,
        Register.ATTENTION_NORMALIZED,
        Register.QUERY_A,
    )
    assert by_register[Register.ATTENTION_INPUT].shape == (token_count, 4096)
    assert by_register[Register.ATTENTION_NORMALIZED].shape == (token_count, 4096)
    assert by_register[Register.QUERY_A].shape == (token_count, 1024)
    assert LIVE_AT_COMPLETE == (Register.QUERY_A,)
    assert EVIDENCE_OBSERVABLES == (
        Register.ATTENTION_INPUT,
        Register.ATTENTION_NORMALIZED,
        Register.QUERY_A,
    )
    assert by_register[Register.QUERY_A].live_at_complete is True
    assert by_register[Register.ATTENTION_NORMALIZED].live_at_complete is False
    assert all(spec.evidence_observable for spec in contract)
    verify_tensor_contract(contract, token_count)


@pytest.mark.parametrize("token_count", [True, False, 0, 5, 1.0, "1", None])
def test_query_a_token_count_is_type_sensitive_and_bounded(token_count: object) -> None:
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="token_count"):
        validate_token_count(token_count)  # type: ignore[arg-type]
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="token_count"):
        tensor_contract(token_count)  # type: ignore[arg-type]


def test_query_a_resource_table_is_exact_and_complete() -> None:
    resources = resource_contract()
    assert [spec.resource for spec in resources] == [
        Resource.ATTN_NORM_WEIGHT,
        Resource.QUERY_A_WEIGHT,
        Resource.QUERY_A_SCALE,
        Resource.QUERY_A_EXHAUSTIVE_ROWS,
    ]
    assert [(spec.dtype, spec.shape, spec.size_bytes) for spec in resources] == [
        ("BF16", (4096,), 8192),
        ("F8_E4M3", (1024, 4096), 4_194_304),
        ("F8_E8M0", (8, 32), 256),
        ("U32", (1024,), 4096),
    ]
    assert [spec.checkpoint_derived for spec in resources] == [True, True, True, False]
    assert (
        resources[-1].content_sha256
        == hashlib.sha256(exhaustive_row_payload()).hexdigest()
    )
    verify_resource_contract(resources)


def test_query_a_exhaustive_row_payload_binds_all_rows_in_order() -> None:
    payload = exhaustive_row_payload()
    assert len(payload) == 4096
    assert struct.unpack("<1024I", payload) == tuple(range(1024))
    validate_exhaustive_row_payload(payload)

    for candidate in (
        payload[:-4],
        payload + struct.pack("<I", 1024),
        struct.pack("<I", 1) + payload[4:],
    ):
        with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="0..1023"):
            validate_exhaustive_row_payload(candidate)
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="0..1023"):
        validate_exhaustive_row_payload(bytearray(payload))  # type: ignore[arg-type]


def test_query_a_program_contract_is_hash_bound_and_has_strict_nonclaims() -> None:
    contract = build_program_contract()
    body = dict(contract)
    contract_id = body.pop("contract_id")

    assert contract_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert contract["program_sha256"] == hashlib.sha256(encode(assemble())).hexdigest()
    assert contract["program_bytes"] == 196
    assert contract["operator_sequence"] == ["RMS_NORM", "FP8_LINEAR", "COMPLETE"]
    assert contract["required_nonclaims"] == list(EXPLICIT_NON_CLAIMS)
    assert {
        "attention_completion",
        "checkpoint_execution",
        "hc_pre_execution",
        "physical_schedule",
        "rtl_execution",
        "ppa",
        "nvidia_comparison",
    }.issubset(contract["required_nonclaims"])
    verify_program_contract(contract)


def test_query_a_contract_verifiers_reject_type_aliases_and_self_rehashing() -> None:
    tensor_alias = list(tensor_contract(1))
    tensor_alias[0] = replace(tensor_alias[0], register=int(Register.ATTENTION_INPUT))
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="typed query-A"):
        verify_tensor_contract(tuple(tensor_alias), 1)

    resources = list(resource_contract())
    resources[0] = replace(resources[0], resource=int(Resource.ATTN_NORM_WEIGHT))
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="artifact resources"):
        verify_resource_contract(tuple(resources))

    contract = build_program_contract()
    contract["program_bytes"] = True
    body = dict(contract)
    body.pop("contract_id")
    contract["contract_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    with pytest.raises(DeepSeekV4QueryAMicrocodeError, match="program contract"):
        verify_program_contract(contract)


def test_query_a_program_contains_no_activation_or_expected_output() -> None:
    payload = encode(assemble())
    contract_payload = canonical_json_bytes(build_program_contract())

    assert b"expected" not in payload.lower()
    assert b"output_bf16_codes" not in contract_payload
    assert b"activation" not in contract_payload
    assert len(payload) == 196
