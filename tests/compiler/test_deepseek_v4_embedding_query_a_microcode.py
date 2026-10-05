from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import struct
import zlib

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.microcode.deepseek_v4_embedding_query_a import (
    EVIDENCE_OBSERVABLES,
    EXHAUSTIVE_ROW_SHA256,
    EXPLICIT_NON_CLAIMS,
    HC_NORMALIZATION_EPSILON_BINARY32_BITS,
    HC_SINKHORN_EPSILON_BINARY32_BITS,
    HEADER,
    LIVE_AT_COMPLETE,
    RECORD,
    DeepSeekV4EmbeddingQueryAMicrocodeError,
    Opcode,
    Register,
    Resource,
    assemble,
    build_semantic_contract,
    decode,
    disassemble,
    encode,
    exhaustive_row_payload,
    resource_contract,
    tensor_contract,
    validate_token_count,
    validate_exhaustive_row_payload,
    verify,
    verify_resource_contract,
    verify_semantic_contract,
    verify_tensor_contract,
)


def _repair_crc(payload: bytearray) -> None:
    struct.pack_into("<I", payload, 12, zlib.crc32(payload[HEADER.size :]) & 0xFFFFFFFF)


def test_embedding_query_a_microcode_roundtrip_and_exact_order() -> None:
    instructions = assemble()
    payload = encode(instructions)
    assert len(payload) == HEADER.size + len(instructions) * RECORD.size
    assert decode(payload) == instructions
    verify(decode(payload))
    assert [instruction.opcode for instruction in instructions] == [
        Opcode.TOKEN_EMBED,
        Opcode.HC_EXPAND,
        Opcode.HC_PRE,
        Opcode.RMS_NORM,
        Opcode.FP8_LINEAR,
        Opcode.COMPLETE,
    ]
    assert disassemble(instructions).startswith(
        "# OpenTallas DeepSeek V4 embedding-query-A ABI 1.0\n0000 TOKEN_EMBED"
    )
    assert disassemble(instructions).endswith("imm=[0,0,0,0]\n")
    assert instructions[2].immediate2 == HC_NORMALIZATION_EPSILON_BINARY32_BITS
    assert instructions[2].immediate3 == HC_SINKHORN_EPSILON_BINARY32_BITS
    assert (
        HC_NORMALIZATION_EPSILON_BINARY32_BITS
        == HC_SINKHORN_EPSILON_BINARY32_BITS
        == 0x358637BD
    )


def test_embedding_query_a_typed_state_and_liveness_are_fixed() -> None:
    specs = tensor_contract(3)
    by_register = {spec.register: spec for spec in specs}
    assert by_register[Register.TOKEN_IDS].shape == (3,)
    assert by_register[Register.TOKEN_IDS].dtype == "I64"
    assert by_register[Register.HC_HIDDEN].shape == (3, 4, 4096)
    assert by_register[Register.ATTENTION_PRE].shape == (3, 4)
    assert by_register[Register.ATTENTION_POST].shape == (3, 4)
    assert by_register[Register.ATTENTION_COMBINATION].shape == (3, 4, 4)
    assert by_register[Register.ATTENTION_RESIDUAL].shape == (3, 4, 4096)
    assert by_register[Register.ATTENTION_NORMALIZED].shape == (3, 4096)
    assert by_register[Register.QUERY_A].shape == (3, 1024)
    assert (
        tuple(spec.register for spec in specs if spec.live_at_complete)
        == LIVE_AT_COMPLETE
    )
    assert (
        tuple(spec.register for spec in specs if spec.evidence_observable)
        == EVIDENCE_OBSERVABLES
    )
    assert Register.ATTENTION_PRE not in LIVE_AT_COMPLETE
    assert Register.ATTENTION_PRE in EVIDENCE_OBSERVABLES
    assert Register.ATTENTION_NORMALIZED in LIVE_AT_COMPLETE

    assert tensor_contract(1)[0].shape == (1,)
    assert tensor_contract(4)[-1].shape == (4, 1024)
    verify_tensor_contract(specs, 3)

    wrong_dtype = list(specs)
    wrong_dtype[4] = replace(wrong_dtype[4], dtype="BF16")
    wrong_shape = list(specs)
    wrong_shape[6] = replace(wrong_shape[6], shape=(3, 16))
    wrong_liveness = list(specs)
    wrong_liveness[8] = replace(wrong_liveness[8], live_at_complete=False)
    wrong_observability = list(specs)
    wrong_observability[4] = replace(wrong_observability[4], evidence_observable=False)
    for changed in (
        tuple(wrong_dtype),
        tuple(wrong_shape),
        tuple(wrong_liveness),
        tuple(wrong_observability),
    ):
        with pytest.raises(
            DeepSeekV4EmbeddingQueryAMicrocodeError, match="typed tensor state"
        ):
            verify_tensor_contract(changed, 3)


@pytest.mark.parametrize("token_count", [0, 5, -1, True, 1.0])
def test_embedding_query_a_rejects_out_of_contract_token_count(
    token_count: object,
) -> None:
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="token_count"):
        validate_token_count(token_count)  # type: ignore[arg-type]
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="token_count"):
        tensor_contract(token_count)  # type: ignore[arg-type]


def test_embedding_query_a_resource_table_is_complete_and_typed() -> None:
    resources = resource_contract()
    assert [resource.resource for resource in resources] == list(Resource)
    assert len(resources) == 11
    assert sum(resource.checkpoint_derived for resource in resources) == 10
    assert resources[0].shape == (32320, 4096)
    assert resources[0].size_bytes == 264_765_440
    assert {
        (resource.rank, resource.row_start, resource.row_stop)
        for resource in resources[:4]
    } == {
        (0, 0, 32320),
        (1, 32320, 64640),
        (2, 64640, 96960),
        (3, 96960, 129280),
    }
    assert {resource.role for resource in resources[:4]} == {
        "model.token_embedding.weight"
    }
    assert resources[4].shape == (24,)
    assert resources[4].size_bytes == 96
    assert resources[5].shape == (24, 16384)
    assert resources[5].size_bytes == 1_572_864
    assert resources[8].shape == (1024, 4096)
    assert resources[8].size_bytes == 4_194_304
    assert resources[9].shape == (8, 32)
    assert resources[9].size_bytes == 256
    assert resources[10].dtype == "U32"
    assert resources[10].shape == (1024,)
    assert resources[10].size_bytes == 4_096
    assert resources[10].content_sha256 == EXHAUSTIVE_ROW_SHA256
    assert [
        (resource.resource, resource.rank, resource.row_start, resource.row_stop)
        for resource in resources[:4]
    ] == [
        (Resource.EMBEDDING_SHARD_0, 0, 0, 32320),
        (Resource.EMBEDDING_SHARD_1, 1, 32320, 64640),
        (Resource.EMBEDDING_SHARD_2, 2, 64640, 96960),
        (Resource.EMBEDDING_SHARD_3, 3, 96960, 129280),
    ]
    verify_resource_contract(resources)

    swapped = (resources[1], resources[0], *resources[2:])
    wrong_range = list(resources)
    wrong_range[1] = replace(wrong_range[1], row_start=32321)
    wrong_role = list(resources)
    wrong_role[0] = replace(wrong_role[0], role="invented.rank0")
    wrong_content = list(resources)
    wrong_content[10] = replace(wrong_content[10], content_sha256="0" * 64)
    for changed in (
        swapped,
        tuple(wrong_range),
        tuple(wrong_role),
        tuple(wrong_content),
    ):
        with pytest.raises(
            DeepSeekV4EmbeddingQueryAMicrocodeError, match="resource table"
        ):
            verify_resource_contract(changed)


def test_embedding_query_a_complete_rows_are_content_bound() -> None:
    payload = exhaustive_row_payload()
    assert len(payload) == 4096
    assert struct.unpack("<1024I", payload) == tuple(range(1024))
    validate_exhaustive_row_payload(payload)

    mutations = []
    swapped = bytearray(payload)
    swapped[:8] = swapped[4:8] + swapped[:4]
    mutations.append(bytes(swapped))
    duplicate = bytearray(payload)
    duplicate[4:8] = duplicate[:4]
    mutations.append(bytes(duplicate))
    out_of_range = bytearray(payload)
    struct.pack_into("<I", out_of_range, 0, 1024)
    mutations.append(bytes(out_of_range))
    bit_drift = bytearray(payload)
    bit_drift[-1] ^= 1
    mutations.extend((bytes(bit_drift), payload[:-4]))
    for mutation in mutations:
        with pytest.raises(
            DeepSeekV4EmbeddingQueryAMicrocodeError, match="exact little-endian"
        ):
            validate_exhaustive_row_payload(mutation)
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="must be bytes"):
        validate_exhaustive_row_payload(bytearray(payload))  # type: ignore[arg-type]


def test_embedding_query_a_rejects_semantic_schedule_drift() -> None:
    instructions = assemble()
    for changed in (
        instructions[:-1],
        (instructions[1], instructions[0], *instructions[2:]),
        (
            *instructions[:2],
            replace(instructions[2], resource1=Resource.HC_ATTN_SCALE),
            *instructions[3:],
        ),
        (
            *instructions[:2],
            replace(instructions[2], immediate2=0x358637BC),
            *instructions[3:],
        ),
        (
            *instructions[:2],
            replace(instructions[2], immediate3=0x358637BC),
            *instructions[3:],
        ),
        (
            *instructions[:4],
            replace(instructions[4], immediate0=1023),
            *instructions[5:],
        ),
    ):
        with pytest.raises(
            DeepSeekV4EmbeddingQueryAMicrocodeError, match="does not exactly"
        ):
            verify(changed)


def test_embedding_query_a_decode_rejects_trailing_and_unknown_opcode() -> None:
    payload = encode(assemble())
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="body length"):
        decode(payload + b"\x00")
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="body length"):
        decode(payload[:-1])

    unknown = bytearray(payload)
    unknown[HEADER.size] = 0x42
    _repair_crc(unknown)
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="unknown opcode"):
        decode(bytes(unknown))


def test_embedding_query_a_decode_rejects_header_and_record_drift() -> None:
    payload = encode(assemble())
    with pytest.raises(
        DeepSeekV4EmbeddingQueryAMicrocodeError, match="shorter than its header"
    ):
        decode(payload[: HEADER.size - 1])
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="must be bytes"):
        decode(bytearray(payload))  # type: ignore[arg-type]

    cases = []
    bad_magic = bytearray(payload)
    bad_magic[0] ^= 1
    cases.append((bad_magic, "magic"))
    bad_version = bytearray(payload)
    bad_version[4] += 1
    cases.append((bad_version, "unsupported embedding-query-A ABI"))
    bad_record_size = bytearray(payload)
    struct.pack_into("<H", bad_record_size, 6, RECORD.size - 4)
    cases.append((bad_record_size, "instruction size"))
    zero_count = bytearray(payload)
    struct.pack_into("<I", zero_count, 8, 0)
    cases.append((zero_count, "instruction count"))
    excessive_count = bytearray(payload)
    struct.pack_into("<I", excessive_count, 8, 65)
    cases.append((excessive_count, "instruction count"))
    for changed, match in cases:
        with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match=match):
            decode(bytes(changed))

    reserved = bytearray(payload)
    reserved[HEADER.size + 2] = 1
    _repair_crc(reserved)
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="reserved bits"):
        decode(bytes(reserved))

    flags = bytearray(payload)
    flags[HEADER.size + 1] = 1
    _repair_crc(flags)
    with pytest.raises(
        DeepSeekV4EmbeddingQueryAMicrocodeError, match="unsupported flags"
    ):
        decode(bytes(flags))


def test_embedding_query_a_integrity_and_encoding_fail_closed() -> None:
    corrupted = bytearray(encode(assemble()))
    corrupted[-1] ^= 1
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="CRC32"):
        decode(bytes(corrupted))

    instructions = assemble()
    with pytest.raises(
        DeepSeekV4EmbeddingQueryAMicrocodeError, match="unsupported flags"
    ):
        encode((replace(instructions[0], flags=1), *instructions[1:]))
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="outside uint32"):
        encode((replace(instructions[0], immediate0=True), *instructions[1:]))
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="invalid opcode"):
        encode((replace(instructions[0], opcode=0x42), *instructions[1:]))  # type: ignore[arg-type]
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="invalid opcode"):
        encode((object(), *instructions[1:]))  # type: ignore[arg-type]


def test_embedding_query_a_nonclaims_are_schema_required_and_hash_bound() -> None:
    assert set(EXPLICIT_NON_CLAIMS) == {
        "attention_completion",
        "query_b",
        "kv_path",
        "transformer_block_completion",
        "logits",
        "decode",
        "cycle_accuracy",
        "ppa",
        "nvidia_comparison",
    }
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (
            root
            / "schemas/compiler/deepseek_v4_embedding_query_a/semantic_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    contract = build_semantic_contract()
    validator.validate(contract)
    verify_semantic_contract(contract)

    missing = dict(contract)
    del missing["required_nonclaims"]
    with pytest.raises(ValidationError):
        validator.validate(missing)

    overstated = dict(contract)
    overstated["required_nonclaims"] = list(EXPLICIT_NON_CLAIMS[:-1])
    with pytest.raises(ValidationError):
        validator.validate(overstated)
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="hash-bound"):
        verify_semantic_contract(overstated)

    self_consistent_looking = dict(overstated)
    self_consistent_looking["contract_id"] = contract["contract_id"]
    with pytest.raises(DeepSeekV4EmbeddingQueryAMicrocodeError, match="hash-bound"):
        verify_semantic_contract(self_consistent_looking)
