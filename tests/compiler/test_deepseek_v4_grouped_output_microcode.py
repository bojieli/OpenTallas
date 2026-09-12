from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import zlib

import pytest

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_grouped_output import (
    ABI_MAJOR,
    ABI_MINOR,
    CANONICAL_APPLICATION_ID,
    CANONICAL_ASSIGNMENTS,
    GLOBAL_GROUP_COUNT,
    GROUP_INPUT_FEATURES,
    HEAD_DIM,
    HEADER,
    HEADS_PER_GROUP,
    MAGIC,
    MAPPING_CONTENT_SHA256,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    NO_OPERAND,
    OUTPUT_RANK_PER_GROUP,
    RAW_LAYER0_WO_A_SCALE_SHA256,
    RAW_LAYER0_WO_A_WEIGHT_SHA256,
    RECORD,
    TENSOR_PARALLEL_WORLD_SIZES,
    DeepSeekV4GroupedOutputMicrocodeError,
    Instruction,
    Opcode,
    Register,
    Resource,
    assemble,
    build_program_contract,
    build_source_contract,
    canonical_assignment_contract,
    decode,
    disassemble,
    encode,
    resource_contract,
    tensor_contract,
    topology_mapping,
    topology_mappings,
    validate_token_count,
    validate_topology,
    verify,
    verify_canonical_assignment_contract,
    verify_program_contract,
    verify_resource_contract,
    verify_source_contract,
    verify_tensor_contract,
    verify_topology_mappings,
)


PROGRAM_SHA256 = {
    (1, 0): "e4722ad4e68661bb2e643cdc526c8e2572f4a319a11e0cdbdad3f3f63a1fcfb6",
    (2, 0): "2686bdf4c61d05f1cb1103bf6d6d0598a5b271c885660c5eb94991f2bbc598af",
    (2, 1): "e3dd05ba5c1f95e001ec4a296b45fbed4b7c425c7a5a083deaf51ed57ec9a2c0",
    (4, 0): "d6ea68b8e9542ac5d3d3991aa62678dd4ec6af854a357d307567b4cecc6dd3d3",
    (4, 1): "e60d60973f8de953455e13063018ee67b90c962629b3947e4785d07da770db52",
    (4, 2): "1a9ec644f1987e04eb6f5d2f5efb34290e082d96ef5080f8303680955ad6cc1d",
    (4, 3): "efecb94bf543b7ac0d6c6754777083814977b36b07980bb931ba4e4f62d35950",
    (8, 0): "e5064a83baa985a846d4a99e866f53ec59f11909dc81664af35ee6b606d33f5f",
    (8, 1): "0be49aaf5b83e2346c3e99e850845bda8ee59dff02eeda93ecbfb81fb08c97d6",
    (8, 2): "e38d32097a66bb23cb6c4215a7bd5fd2e31d301c5db57798b606e42636ca5b08",
    (8, 3): "613c3f2bbecc3988989844da5e5b3a4b5838e3d6b8bd02737c991e5263be9c49",
    (8, 4): "b889d0ae2d1374ac203aaabdb9cab4cde4c22048207c180907a9f44a5179b482",
    (8, 5): "7da745ed158322b0cfdecdf2824b9e05d45a462341675c2296a62623e5dcb7da",
    (8, 6): "69fb674fc5b192e946fcbae945c0bae2aadafb445e9e3ec71b463e43525bda88",
    (8, 7): "e2cb1394d2075866e0327ec43324899ff5ec30f5d35f87f45ddc1472fa7603a2",
}


def _keys() -> tuple[tuple[int, int], ...]:
    return tuple(
        (world_size, rank)
        for world_size in TENSOR_PARALLEL_WORLD_SIZES
        for rank in range(world_size)
    )


def _rewrite_header(payload: bytes, **updates: int | bytes) -> bytes:
    fields = list(HEADER.unpack_from(payload))
    names = ("magic", "major", "minor", "record_size", "count", "crc")
    for name, value in updates.items():
        fields[names.index(name)] = value
    return HEADER.pack(*fields) + payload[HEADER.size :]


def _rewrite_record(
    payload: bytes,
    index: int,
    field: int,
    value: int,
    *,
    refresh_crc: bool = True,
) -> bytes:
    body = bytearray(payload[HEADER.size :])
    record = list(RECORD.unpack_from(body, index * RECORD.size))
    record[field] = value
    RECORD.pack_into(body, index * RECORD.size, *record)
    result = payload[: HEADER.size] + bytes(body)
    if refresh_crc:
        result = _rewrite_header(result, crc=zlib.crc32(body) & 0xFFFFFFFF)
    return result


def test_source_contract_is_pinned_to_official_release_and_transform() -> None:
    contract = build_source_contract()
    assert contract["repository"] == MODEL_REPOSITORY
    assert contract["revision"] == MODEL_REVISION
    assert contract["source_contract_id"] == (
        "f0220c70a30456e76276add36821ca7fff12c3944b2d202c2b0118ffdcd29bd9"
    )
    assert contract["checkpoint"]["raw_weight_sha256"] == (
        RAW_LAYER0_WO_A_WEIGHT_SHA256
    )
    assert contract["checkpoint"]["raw_scale_sha256"] == (RAW_LAYER0_WO_A_SCALE_SHA256)
    assert contract["canonical_application"]["application_id"] == (
        CANONICAL_APPLICATION_ID
    )
    assert contract["transform"] == "dequantize_fp8_e8m0_to_bf16_rne"
    assert contract["source_operations"] == [
        "attention_group_view",
        "weight_group_view",
        "grouped_einsum_bsgd_grd_to_bsgr",
        "group_major_flatten_alias",
    ]
    verify_source_contract(contract)


def test_four_canonical_assignments_exactly_partition_global_rows_and_scale() -> None:
    assignments = canonical_assignment_contract()
    assert assignments == CANONICAL_ASSIGNMENTS
    assert len(assignments) == 4
    assert tuple(
        (item.raw_row_start, item.raw_row_stop) for item in assignments
    ) == tuple((rank * 2_048, (rank + 1) * 2_048) for rank in range(4))
    assert tuple(
        (item.scale_row_start, item.scale_row_stop) for item in assignments
    ) == tuple((rank * 16, (rank + 1) * 16) for rank in range(4))
    assert all(item.shape == (2_048, 4_096) for item in assignments)
    assert all(item.size_bytes == 16_777_216 for item in assignments)
    verify_canonical_assignment_contract(assignments)


def test_all_fifteen_topology_mappings_are_contiguous_and_hash_bound() -> None:
    mappings = topology_mappings()
    assert tuple((item.world_size, item.rank) for item in mappings) == _keys()
    assert len(mappings) == 15
    for mapping in mappings:
        local_groups = GLOBAL_GROUP_COUNT // mapping.world_size
        assert mapping.local_group_count == local_groups
        assert mapping.global_group_start == mapping.rank * local_groups
        assert mapping.global_group_stop == (mapping.rank + 1) * local_groups
        assert mapping.global_row_start == (
            mapping.global_group_start * OUTPUT_RANK_PER_GROUP
        )
        assert mapping.global_row_stop == (
            mapping.global_group_stop * OUTPUT_RANK_PER_GROUP
        )
        assert mapping.shape == (
            local_groups * OUTPUT_RANK_PER_GROUP,
            GROUP_INPUT_FEATURES,
        )
        assert mapping.size_bytes == mapping.shape[0] * mapping.shape[1] * 2
        assert (
            mapping.content_sha256
            == MAPPING_CONTENT_SHA256[(mapping.world_size, mapping.rank)]
        )
        assert mapping.segments[0].global_row_start == mapping.global_row_start
        assert mapping.segments[-1].global_row_stop == mapping.global_row_stop
        assert sum(item.size_bytes for item in mapping.segments) == (mapping.size_bytes)
        assert all(
            left.global_row_stop == right.global_row_start
            for left, right in zip(
                mapping.segments,
                mapping.segments[1:],
            )
        )
    verify_topology_mappings(mappings)


@pytest.mark.parametrize(("world_size", "rank"), _keys())
def test_program_is_exact_typed_and_roundtrips(world_size: int, rank: int) -> None:
    mapping = topology_mapping(world_size, rank)
    program = assemble(world_size, rank)
    assert program == (
        Instruction(
            Opcode.GROUPED_OUTPUT_PROJECT,
            destination0=Register.GROUPED_OUTPUT,
            destination1=Register.FLATTENED_OUTPUT,
            source=Register.GROUPED_ATTENTION_INPUT,
            resource0=Resource.LAYER0_WO_A_LOCAL_BF16,
            immediate0=world_size,
            immediate1=rank,
            immediate2=mapping.local_group_count,
            immediate3=OUTPUT_RANK_PER_GROUP,
        ),
        Instruction(Opcode.COMPLETE),
    )
    verify(program, world_size, rank)
    payload = encode(program, world_size, rank)
    assert len(payload) == HEADER.size + 2 * RECORD.size == 88
    assert hashlib.sha256(payload).hexdigest() == PROGRAM_SHA256[(world_size, rank)]
    assert decode(payload) == program
    assert (
        disassemble(program, world_size, rank)
        .splitlines()[1]
        .startswith("0000 GROUPED_OUTPUT_PROJECT")
    )


@pytest.mark.parametrize(("world_size", "rank"), _keys())
def test_resource_contract_is_one_real_local_bf16_mapping(
    world_size: int,
    rank: int,
) -> None:
    mapping = topology_mapping(world_size, rank)
    resources = resource_contract(world_size, rank)
    assert len(resources) == 1
    resource = resources[0]
    assert resource.resource is Resource.LAYER0_WO_A_LOCAL_BF16
    assert resource.dtype == "BF16"
    assert resource.shape == mapping.shape
    assert resource.size_bytes == mapping.size_bytes
    assert resource.content_sha256 == mapping.content_sha256
    assert resource.segments == mapping.segments
    assert resource.canonical_application_id == CANONICAL_APPLICATION_ID
    verify_resource_contract(resources, world_size, rank)


@pytest.mark.parametrize(("world_size", "rank"), _keys())
@pytest.mark.parametrize("token_count", range(MIN_TOKEN_COUNT, MAX_TOKEN_COUNT + 1))
def test_tensor_contract_covers_all_tokens_topologies_and_flatten_alias(
    world_size: int,
    rank: int,
    token_count: int,
) -> None:
    mapping = topology_mapping(world_size, rank)
    tensors = tensor_contract(token_count, world_size, rank)
    assert tensors[0].shape == (
        token_count,
        mapping.local_group_count * HEADS_PER_GROUP,
        HEAD_DIM,
    )
    assert tensors[1].shape == (
        token_count,
        mapping.local_group_count,
        OUTPUT_RANK_PER_GROUP,
    )
    assert tensors[2].shape == (
        token_count,
        mapping.local_group_count * OUTPUT_RANK_PER_GROUP,
    )
    assert tensors[2].alias_of is Register.GROUPED_OUTPUT
    assert tensors[1].live_at_complete and tensors[2].live_at_complete
    assert all(item.evidence_observable for item in tensors)
    verify_tensor_contract(tensors, token_count, world_size, rank)


@pytest.mark.parametrize("value", [True, False, 0, 5, 1.0, "1", None])
def test_token_count_rejects_python_type_aliases_and_out_of_range(
    value: object,
) -> None:
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        validate_token_count(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("world_size", "rank"),
    [
        (True, 0),
        (False, 0),
        (0, 0),
        (3, 0),
        (16, 0),
        (1.0, 0),
        (1, True),
        (1, -1),
        (1, 1),
        (4, 4),
    ],
)
def test_topology_rejects_invalid_values(world_size: object, rank: object) -> None:
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        validate_topology(world_size, rank)  # type: ignore[arg-type]


def test_exact_program_verifier_rejects_every_operand_and_type_mutation() -> None:
    program = assemble(4, 2)
    project = program[0]
    mutations = (
        replace(project, opcode=Opcode.COMPLETE),
        replace(project, destination0=Register.FLATTENED_OUTPUT),
        replace(project, destination1=Register.GROUPED_OUTPUT),
        replace(project, source=Register.GROUPED_OUTPUT),
        replace(project, resource0=NO_OPERAND),
        replace(project, immediate0=8),
        replace(project, immediate1=1),
        replace(project, immediate2=1),
        replace(project, immediate3=OUTPUT_RANK_PER_GROUP - 1),
        replace(project, flags=1),
        replace(project, immediate0=True),
        replace(project, destination0=int(Register.GROUPED_OUTPUT)),
    )
    for mutation in mutations:
        with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
            verify((mutation, program[1]), 4, 2)
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify((program[0],), 4, 2)
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify((program[1], program[0]), 4, 2)


@pytest.mark.parametrize("payload", [bytearray(), memoryview(b""), "", None])
def test_decoder_requires_exact_bytes(payload: object) -> None:
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        decode(payload)  # type: ignore[arg-type]


def test_decoder_rejects_header_length_crc_and_control_mutations() -> None:
    payload = encode(assemble(4, 0), 4, 0)
    malformed = (
        b"",
        payload[: HEADER.size - 1],
        _rewrite_header(payload, magic=b"BAD!"),
        _rewrite_header(payload, major=ABI_MAJOR + 1),
        _rewrite_header(payload, minor=ABI_MINOR + 1),
        _rewrite_header(payload, record_size=RECORD.size + 4),
        _rewrite_header(payload, count=0),
        _rewrite_header(payload, count=9),
        _rewrite_header(payload, count=3),
        payload + b"\x00",
        _rewrite_record(payload, 0, 3, 99, refresh_crc=False),
        _rewrite_record(payload, 0, 2, 1),
        _rewrite_record(payload, 0, 1, 1),
        _rewrite_record(payload, 0, 0, 0x31),
    )
    for mutation in malformed:
        with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
            decode(mutation)


def test_structurally_valid_operand_mutations_decode_but_fail_semantics() -> None:
    payload = encode(assemble(4, 0), 4, 0)
    # RECORD fields: opcode, flags, reserved, destination0, destination1,
    # source, resource0, immediate0..3.
    for field, value in (
        (3, 2),
        (4, 1),
        (5, 1),
        (6, NO_OPERAND),
        (7, 8),
        (8, 1),
        (9, 1),
        (10, 1_023),
    ):
        mutation = _rewrite_record(payload, 0, field, value)
        decoded = decode(mutation)
        with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
            verify(decoded, 4, 0)


def test_program_and_source_contracts_fail_closed_on_self_consistent_mutations() -> (
    None
):
    source = build_source_contract()
    source["status"] = "pass"
    source_without_id = {
        key: value for key, value in source.items() if key != "source_contract_id"
    }
    source["source_contract_id"] = hashlib.sha256(
        canonical_json_bytes(source_without_id)
    ).hexdigest()
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify_source_contract(source)

    program = build_program_contract(8, 7)
    program["topology"]["rank"] = 6
    program_without_id = {
        key: value for key, value in program.items() if key != "contract_id"
    }
    program["contract_id"] = hashlib.sha256(
        canonical_json_bytes(program_without_id)
    ).hexdigest()
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify_program_contract(program, 8, 7)


def test_typed_contract_verifiers_reject_bool_int_and_list_tuple_aliases() -> None:
    tensors = list(tensor_contract(1, 4, 0))
    tensors[0] = replace(tensors[0], live_at_complete=0)  # type: ignore[arg-type]
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify_tensor_contract(tuple(tensors), 1, 4, 0)

    resources = list(resource_contract(4, 0))
    resources[0] = replace(resources[0], world_size=True)
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify_resource_contract(tuple(resources), 4, 0)

    assignments = list(canonical_assignment_contract())
    with pytest.raises(DeepSeekV4GroupedOutputMicrocodeError):
        verify_canonical_assignment_contract(assignments)


def test_real_cached_assignment_bytes_match_when_available() -> None:
    root = Path.home() / ".cache/opentallas/deepseek-v4-flash-0731/canonical-mp4"
    if not all((root / item.path).is_file() for item in CANONICAL_ASSIGNMENTS):
        pytest.skip("canonical DeepSeek V4 MP4 assignments are unavailable")
    for assignment in CANONICAL_ASSIGNMENTS:
        payload = (root / assignment.path).read_bytes()
        assert len(payload) == assignment.size_bytes
        assert hashlib.sha256(payload).hexdigest() == assignment.content_sha256


def test_abi_is_standalone_and_has_no_runtime_or_physical_payload() -> None:
    path = Path("compiler/microcode/deepseek_v4_grouped_output.py")
    source = path.read_text(encoding="utf-8")
    assert MAGIC == b"OTGO"
    assert (RECORD.format, RECORD.size) == (struct.Struct("<BBH8I").format, 36)
    assert "runtime." not in source
    assert "expected_output" not in source
    assert "callback=" not in source
    contract = build_program_contract(4, 0)
    assert {
        "cycle_accuracy",
        "nvidia_comparison",
        "output_b_projection",
        "physical_schedule",
        "ppa",
    } <= set(contract["required_nonclaims"])
