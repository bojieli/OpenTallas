from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

import compiler.checking.deepseek_v4_markov as checker_module
from compiler.checking.deepseek_v4_markov import (
    DeepSeekV4MarkovCheckError,
    verify_deepseek_v4_markov_program,
)
from compiler.microcode.deepseek_v4_markov import (
    ABI_MAJOR,
    ABI_MINOR,
    BLOCK_SIZE,
    EXPLICIT_NONCLAIMS,
    HEADER,
    MAGIC,
    NO_OPERAND,
    NUMERIC_PROFILE,
    OUTPUT_TOKEN_COUNT,
    PROGRAM_BYTES,
    PROGRAM_INSTRUCTION_COUNT,
    PROGRAM_SHA256,
    RECORD,
    DeepSeekV4MarkovMicrocodeError,
    MarkovInstruction,
    MarkovOpcode,
    MarkovRegister,
    MarkovResource,
    assemble,
    build_program_contract,
    decode,
    disassemble,
    encode,
    verify,
    verify_program_contract,
)


def _rewrite_header(payload: bytes, **updates: int | bytes) -> bytes:
    values = list(HEADER.unpack_from(payload))
    names = ("magic", "major", "minor", "count", "record_size", "digest")
    for name, value in updates.items():
        values[names.index(name)] = value
    return HEADER.pack(*values) + payload[HEADER.size :]


def _rewrite_record(
    payload: bytes,
    index: int,
    field: int,
    value: int,
    *,
    refresh_digest: bool = True,
) -> bytes:
    body = bytearray(payload[HEADER.size :])
    record = list(RECORD.unpack_from(body, index * RECORD.size))
    record[field] = value
    RECORD.pack_into(body, index * RECORD.size, *record)
    digest = hashlib.sha256(body).digest()
    result = payload[: HEADER.size] + bytes(body)
    if refresh_digest:
        result = _rewrite_header(result, digest=digest)
    return result


def test_fixed_program_unrolls_all_five_causal_steps() -> None:
    program = assemble()
    assert len(program) == PROGRAM_INSTRUCTION_COUNT == 21
    assert BLOCK_SIZE == 5
    assert OUTPUT_TOKEN_COUNT == 6
    assert [instruction.opcode for instruction in program[:-1]] == [
        opcode
        for _ in range(BLOCK_SIZE)
        for opcode in (
            MarkovOpcode.TOKEN_LOOKUP,
            MarkovOpcode.VOCABULARY_PROJECT,
            MarkovOpcode.BINARY32_BIAS_ADD,
            MarkovOpcode.SAMPLE_AND_CARRY,
        )
    ]
    assert program[-1] == MarkovInstruction(
        opcode=MarkovOpcode.COMPLETE,
        step=5,
        destination=MarkovRegister.TOKENS,
        source0=MarkovRegister.ADJUSTED_LOGITS,
        source1=MarkovRegister.EMBEDDINGS,
        source2=MarkovRegister.ENTROPY_CONTINUATION,
    )
    for step in range(BLOCK_SIZE):
        lookup, project, addition, sample = program[step * 4 : step * 4 + 4]
        assert {item.step for item in (lookup, project, addition, sample)} == {step}
        assert lookup.source0 is (
            MarkovRegister.INITIAL_TOKENS
            if step == 0
            else MarkovRegister.TOKENS
        )
        assert lookup.resource is MarkovResource.W1_EMBEDDING
        assert project.source0 is MarkovRegister.EMBEDDINGS
        assert project.resource is MarkovResource.W2_VOCABULARY_HEAD
        assert addition.source0 is MarkovRegister.BASE_LOGITS
        assert addition.source1 is MarkovRegister.BIASES
        assert sample.source0 is MarkovRegister.ADJUSTED_LOGITS
        assert sample.source1 is MarkovRegister.TEMPERATURE
        assert sample.source2 is (
            MarkovRegister.ENTROPY_INPUT
            if step == 0
            else MarkovRegister.ENTROPY_CONTINUATION
        )


def test_wire_program_roundtrips_and_independent_checker_agrees() -> None:
    program = assemble()
    payload = encode(program)
    assert len(payload) == PROGRAM_BYTES == HEADER.size + 21 * RECORD.size
    assert hashlib.sha256(payload).hexdigest() == PROGRAM_SHA256
    assert decode(payload) == program
    verify(decode(payload))
    contract = build_program_contract(program_sha256=PROGRAM_SHA256)
    verify_program_contract(contract, program_sha256=PROGRAM_SHA256)
    report = verify_deepseek_v4_markov_program(payload, contract)
    assert report.program_sha256 == PROGRAM_SHA256
    assert report.instruction_count == 21
    assert (
        report.lookup_count,
        report.projection_count,
        report.bias_add_count,
        report.sampling_count,
        report.complete_count,
    ) == (5, 5, 5, 5, 1)


def test_program_contract_pins_numeric_entropy_resource_and_nonclaim_boundaries() -> (
    None
):
    contract = build_program_contract(program_sha256=PROGRAM_SHA256)
    assert contract["numeric_profile"] == NUMERIC_PROFILE
    assert contract["numeric_contract"] == {
        "bias_add": "separate_binary32_rne",
        "embedding_storage": "BF16",
        "head_accumulator": "binary32",
        "head_reduction": "increasing_markov_rank_rne_fused_product_add",
        "head_storage": "BF16",
        "subnormals": "preserve",
    }
    assert contract["causal_contract"]["entropy_order"] == (
        "step_then_batch_then_vocabulary"
    )
    assert contract["causal_contract"]["initial_token_output_column"] == 0
    assert contract["outputs"] == {
        "adjusted_logits": "binary32[B,5,V]",
        "embeddings": "BF16[B,5,R]",
        "entropy_continuation": "immutable_explicit_stream_continuation",
        "tokens": "u32[B,6]",
    }
    assert [resource["name"] for resource in contract["resources"]] == [
        "mtp.2.markov_head.markov_w1.weight",
        "mtp.2.markov_head.markov_w2.weight",
    ]
    assert contract["timing_claim"] is None
    assert tuple(contract["unsupported_claims"]) == EXPLICIT_NONCLAIMS


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (b"", "truncated"),
        (_rewrite_header(encode(assemble()), magic=b"BADMAGIC"), "identity"),
        (_rewrite_header(encode(assemble()), major=ABI_MAJOR + 1), "identity"),
        (_rewrite_header(encode(assemble()), minor=ABI_MINOR + 1), "identity"),
        (_rewrite_header(encode(assemble()), count=20), "record contract"),
        (_rewrite_header(encode(assemble()), record_size=RECORD.size + 2), "record contract"),
        (_rewrite_record(encode(assemble()), 0, 1, 1, refresh_digest=False), "digest"),
        (encode(assemble())[:-1], "body size"),
    ],
)
def test_decoder_rejects_wire_corruption(payload: bytes, match: str) -> None:
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match=match):
        decode(payload)


@pytest.mark.parametrize(
    ("record_index", "field", "value", "decode_match", "verify_match"),
    [
        (0, 0, 99, "unknown opcode", None),
        (0, 2, 99, "unknown register", None),
        (0, 6, 99, "unknown resource", None),
        (0, 1, 1, None, "instruction 0"),
        (4, 3, int(MarkovRegister.INITIAL_TOKENS), None, "instruction 4"),
        (7, 5, int(MarkovRegister.ENTROPY_INPUT), None, "instruction 7"),
        (20, 0, int(MarkovOpcode.SAMPLE_AND_CARRY), None, "instruction 20"),
        (20, 7, 1, None, "instruction 20"),
    ],
)
def test_decoder_or_typed_verifier_rejects_semantic_forgery(
    record_index: int,
    field: int,
    value: int,
    decode_match: str | None,
    verify_match: str | None,
) -> None:
    forged = _rewrite_record(encode(assemble()), record_index, field, value)
    if decode_match is not None:
        with pytest.raises(DeepSeekV4MarkovMicrocodeError, match=decode_match):
            decode(forged)
        return
    decoded = decode(forged)
    assert verify_match is not None
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match=verify_match):
        verify(decoded)


def test_independent_checker_rejects_rehashed_semantic_and_contract_forgery() -> None:
    payload = encode(assemble())
    contract = build_program_contract(program_sha256=PROGRAM_SHA256)
    forged_payload = _rewrite_record(payload, 4, 3, 1)
    with pytest.raises(DeepSeekV4MarkovCheckError, match="record 4"):
        verify_deepseek_v4_markov_program(forged_payload, contract)

    forged_contract = {**contract, "timing_claim": 1}
    with pytest.raises(DeepSeekV4MarkovCheckError, match="contract differs"):
        verify_deepseek_v4_markov_program(payload, forged_contract)
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match="contract differs"):
        verify_program_contract(forged_contract, program_sha256=PROGRAM_SHA256)


def test_verifier_rejects_nonexact_program_values() -> None:
    program = assemble()
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match="exact tuple"):
        verify(list(program))
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match="exactly 21"):
        verify(program[:-1])
    with pytest.raises(DeepSeekV4MarkovMicrocodeError, match="instruction 0"):
        verify((replace(program[0], flags=1),) + program[1:])


def test_disassembly_is_deterministic_and_names_every_causal_boundary() -> None:
    text = disassemble(assemble())
    assert text.startswith("# OpenTallas DeepSeek V4 Markov ABI 1.0\n")
    assert text.count("TOKEN_LOOKUP") == 5
    assert text.count("VOCABULARY_PROJECT") == 5
    assert text.count("BINARY32_BIAS_ADD") == 5
    assert text.count("SAMPLE_AND_CARRY") == 5
    assert text.count("COMPLETE") == 1
    assert "src2=3:ENTROPY_INPUT" in text
    assert "src2=8:ENTROPY_CONTINUATION" in text
    assert "resource=0:W1_EMBEDDING" in text
    assert "resource=1:W2_VOCABULARY_HEAD" in text
    assert f"resource={NO_OPERAND}" not in text


def test_independent_checker_has_no_markov_assembler_dependency() -> None:
    source = Path(checker_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "compiler.microcode.deepseek_v4_markov" not in imported_modules
    assert "runtime.reference.markov_loop" not in imported_modules
    assert "runtime.service_engine.markov_loop" not in imported_modules


def test_frozen_program_identity_is_explicit() -> None:
    assert MAGIC == b"OTMKV1\0\0"
    assert (ABI_MAJOR, ABI_MINOR) == (1, 0)
    assert PROGRAM_BYTES == 388
    assert PROGRAM_SHA256 == (
        "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
    )
