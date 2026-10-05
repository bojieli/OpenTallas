from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
import hashlib
import inspect
import struct
from typing import Any, Callable
import zlib

import pytest

import compiler.checking.deepseek_v4_rope as checker_module
import compiler.microcode.deepseek_v4_rope as microcode_module
import compiler.scheduling.deepseek_v4_rope as schedule_module
from compiler.checking.deepseek_v4_rope import (
    CERTIFICATE_CLAIM_BOUNDARY,
    DeepSeekV4RopeCheckError,
    build_verification_certificate,
    verify_compiled_deepseek_v4_rope,
    verify_deepseek_v4_rope_logical_schedule,
    verify_verification_certificate,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_rope import (
    ABI_MAJOR,
    ABI_MINOR,
    EXPLICIT_NON_CLAIMS,
    HEADER,
    MAGIC,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    NO_OPERAND,
    NUMERIC_PROFILE,
    NUMERIC_PROFILE_CODE,
    PHASOR_TABLE_BYTES,
    PHASOR_TABLE_SHAPE,
    PROGRAM_INSTRUCTION_COUNT,
    RECORD,
    ROPE_COMPLEX_PAIRS,
    ROPE_DIMENSION,
    SUPPORTED_RANK4_HEAD_COUNTS,
    DeepSeekV4RopeMicrocodeError,
    Instruction,
    Opcode,
    Phase,
    PositionPolicy,
    Register,
    Resource,
    RopeDescriptor,
    RopeProfile,
    ScalingMode,
    TensorRole,
    assemble,
    build_descriptor,
    build_program_contract,
    decode,
    descriptor_id,
    descriptor_record,
    disassemble,
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
from compiler.scheduling.deepseek_v4_rope import (
    CLAIM_BOUNDARY,
    LOGICAL_SCHEDULE_SCHEMA,
    LOGICAL_SCHEDULE_STATUS,
    ORDERING_POLICY,
    REQUIRED_NONCLAIMS,
    DeepSeekV4RopeScheduleError,
    build_deepseek_v4_rope_logical_schedule,
)
from runtime.reference.rope import (
    BASE_ROPE_THETA,
    COMPRESSED_ROPE_THETA,
    MAX_POSITION,
    MAX_SEQUENCE_LENGTH,
    YARN_BETA_FAST,
    YARN_BETA_SLOW,
    YARN_CORRECTION_HIGH,
    YARN_CORRECTION_LOW,
    YARN_FACTOR,
    YARN_ORIGINAL_SEQUENCE_LENGTH,
)


def _ordinary(
    *,
    opcode: Opcode = Opcode.ROPE_APPLY,
    role: TensorRole = TensorRole.QUERY,
    rank: int = 4,
    width: int = 512,
    heads: int = 64,
    profile: RopeProfile = RopeProfile.BASE,
    ratio: int = 0,
    phase: Phase = Phase.PREFILL,
    batch: int = 4,
    sequence: int = MAX_SEQUENCE_LENGTH,
    start: int = 0,
) -> RopeDescriptor:
    return build_descriptor(
        opcode=opcode,
        tensor_role=role,
        tensor_rank=rank,
        batch_count=batch,
        sequence_length=sequence,
        head_count=heads,
        head_width=width,
        profile=profile,
        phase=phase,
        position_policy=PositionPolicy.CONSECUTIVE,
        compression_ratio=ratio,
        request_start_position=start,
    )


def _compressor_prefill(
    ratio: int,
    *,
    source_length: int = MAX_SEQUENCE_LENGTH,
    batch: int = 4,
) -> RopeDescriptor:
    cutoff = source_length - source_length % ratio
    return build_descriptor(
        opcode=Opcode.ROPE_APPLY,
        tensor_role=TensorRole.COMPRESSOR_KV,
        tensor_rank=3,
        batch_count=batch,
        sequence_length=cutoff // ratio,
        head_count=1,
        head_width=512,
        profile=RopeProfile.COMPRESSED_YARN,
        phase=Phase.PREFILL,
        position_policy=PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE,
        compression_ratio=ratio,
        request_start_position=0,
        source_sequence_length=source_length,
    )


def _compressor_decode(
    ratio: int,
    *,
    request_start: int | None = None,
    batch: int = 4,
) -> RopeDescriptor:
    start = ratio - 1 if request_start is None else request_start
    return build_descriptor(
        opcode=Opcode.ROPE_APPLY,
        tensor_role=TensorRole.COMPRESSOR_KV,
        tensor_rank=3,
        batch_count=batch,
        sequence_length=1,
        head_count=1,
        head_width=512,
        profile=RopeProfile.COMPRESSED_YARN,
        phase=Phase.DECODE,
        position_policy=PositionPolicy.COMPRESSOR_DECODE_ADJUSTED,
        compression_ratio=ratio,
        request_start_position=start,
        source_sequence_length=1,
    )


def _forge(instance: object, **changes: object) -> object:
    forged = object.__new__(type(instance))
    for field in fields(instance):
        object.__setattr__(
            forged,
            field.name,
            changes.get(field.name, getattr(instance, field.name)),
        )
    return forged


def _rewrite_header(payload: bytes, **updates: int | bytes) -> bytes:
    values = list(HEADER.unpack_from(payload))
    names = ("magic", "major", "minor", "record_size", "count", "crc")
    for name, value in updates.items():
        values[names.index(name)] = value
    return HEADER.pack(*values) + payload[HEADER.size :]


def _rewrite_record(
    payload: bytes,
    record_index: int,
    field_index: int,
    value: int,
    *,
    refresh_crc: bool = True,
) -> bytes:
    body = bytearray(payload[HEADER.size :])
    values = list(RECORD.unpack_from(body, record_index * RECORD.size))
    values[field_index] = value
    RECORD.pack_into(body, record_index * RECORD.size, *values)
    result = payload[: HEADER.size] + bytes(body)
    if refresh_crc:
        result = _rewrite_header(result, crc=zlib.crc32(body) & 0xFFFFFFFF)
    return result


def _rehash_schedule(schedule: dict[str, Any]) -> None:
    body = dict(schedule)
    body.pop("schedule_id", None)
    schedule["schedule_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_official_release_and_frozen_v2_numeric_authority_are_explicit() -> None:
    assert MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert NUMERIC_PROFILE == "opentallas.deepseek_v4_rope_numeric.v2"
    assert NUMERIC_PROFILE_CODE == int.from_bytes(
        hashlib.sha256(NUMERIC_PROFILE.encode("ascii")).digest()[:4],
        "little",
    )
    assert PHASOR_TABLE_SHAPE == (65_536, 32, 2)
    assert PHASOR_TABLE_BYTES == 16_777_216
    assert SUPPORTED_RANK4_HEAD_COUNTS == frozenset({8, 16, 32, 64})


@pytest.mark.parametrize(
    ("descriptor", "shape", "last"),
    [
        (_ordinary(), (4, 65_536, 64, 512), 65_535),
        (
            _ordinary(role=TensorRole.KV, rank=3, heads=1),
            (4, 65_536, 512),
            65_535,
        ),
        (
            _ordinary(
                role=TensorRole.INDEX_QUERY,
                width=128,
                profile=RopeProfile.COMPRESSED_YARN,
                ratio=4,
            ),
            (4, 65_536, 64, 128),
            65_535,
        ),
        (
            _ordinary(
                opcode=Opcode.ROPE_INVERSE,
                role=TensorRole.ATTENTION_OUTPUT,
                profile=RopeProfile.COMPRESSED_YARN,
                ratio=128,
            ),
            (4, 65_536, 64, 512),
            65_535,
        ),
        (_compressor_prefill(4), (4, 16_384, 512), 65_532),
        (_compressor_prefill(128), (4, 512, 512), 65_408),
        (_compressor_decode(4, request_start=65_535), (4, 1, 512), 65_532),
        (_compressor_decode(128, request_start=65_535), (4, 1, 512), 65_408),
    ],
)
def test_complete_official_shapes_roundtrip_without_materializing_activations(
    descriptor: RopeDescriptor,
    shape: tuple[int, ...],
    last: int,
) -> None:
    program = assemble(descriptor)
    payload = encode(program)
    assert len(payload) == HEADER.size + 2 * RECORD.size == 256
    assert decode(payload) == program
    verify(decode(payload), descriptor)
    assert tensor_contract(descriptor)[0].shape == shape
    assert descriptor.last_table_position == last
    assert [instruction.opcode for instruction in program] == [
        descriptor.opcode,
        Opcode.COMPLETE,
    ]
    assert program[0].destination is Register.OUTPUT
    assert program[0].source is Register.INPUT
    assert program[0].destination is not program[0].source
    assert program[1] == Instruction(Opcode.COMPLETE)


def test_base_and_compressed_profiles_bind_all_scaling_constants_and_resources() -> (
    None
):
    base = _ordinary(sequence=2, batch=1, heads=8)
    compressed = _ordinary(
        profile=RopeProfile.COMPRESSED_YARN,
        ratio=4,
        sequence=2,
        batch=1,
        heads=8,
    )
    assert (
        base.profile,
        base.scaling_mode,
        base.theta,
        base.original_sequence_length,
        base.yarn_factor,
        base.beta_fast,
        base.beta_slow,
        base.correction_low,
        base.correction_high,
    ) == (RopeProfile.BASE, ScalingMode.NONE, BASE_ROPE_THETA, 0, 1, 0, 0, 0, 0)
    assert (
        compressed.profile,
        compressed.scaling_mode,
        compressed.theta,
        compressed.original_sequence_length,
        compressed.yarn_factor,
        compressed.beta_fast,
        compressed.beta_slow,
        compressed.correction_low,
        compressed.correction_high,
    ) == (
        RopeProfile.COMPRESSED_YARN,
        ScalingMode.YARN,
        COMPRESSED_ROPE_THETA,
        YARN_ORIGINAL_SEQUENCE_LENGTH,
        YARN_FACTOR,
        YARN_BETA_FAST,
        YARN_BETA_SLOW,
        YARN_CORRECTION_LOW,
        YARN_CORRECTION_HIGH,
    )
    assert assemble(base)[0].resource is Resource.BASE_PHASOR_TABLE
    assert assemble(compressed)[0].resource is Resource.COMPRESSED_YARN_PHASOR_TABLE


@pytest.mark.parametrize("ratio", [4, 128])
def test_compressor_prefill_encodes_ratio_stride_cutoff_and_remainder(
    ratio: int,
) -> None:
    source_length = 2 * ratio + 3
    descriptor = _compressor_prefill(ratio, source_length=source_length)
    assert descriptor.source_cutoff == 2 * ratio
    assert descriptor.sequence_length == 2
    assert descriptor.table_start_position == 0
    assert descriptor.position_stride == ratio
    assert descriptor.last_table_position == ratio
    contract = position_contract(descriptor)
    assert contract.policy is PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE
    assert contract.table_position_formula == (
        "table_start=0; table[i]=i*compression_ratio"
    )


@pytest.mark.parametrize("ratio", [4, 128])
@pytest.mark.parametrize("group", [1, 3, 16])
def test_compressor_decode_encodes_adjusted_absolute_table_position(
    ratio: int,
    group: int,
) -> None:
    request_start = group * ratio - 1
    descriptor = _compressor_decode(ratio, request_start=request_start)
    assert descriptor.request_start_position == request_start
    assert descriptor.table_start_position == request_start + 1 - ratio
    assert descriptor.last_table_position == descriptor.table_start_position
    assert descriptor.position_stride == 1
    assert descriptor.position_policy is PositionPolicy.COMPRESSOR_DECODE_ADJUSTED


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tensor_rank", True),
        ("batch_count", True),
        ("sequence_length", True),
        ("head_count", True),
        ("head_width", True),
        ("rope_dimension", True),
        ("theta", True),
        ("original_sequence_length", True),
        ("yarn_factor", True),
        ("beta_fast", True),
        ("beta_slow", True),
        ("correction_low", True),
        ("correction_high", True),
        ("compression_ratio", True),
        ("request_start_position", True),
        ("table_start_position", True),
        ("last_table_position", True),
        ("position_stride", True),
        ("source_sequence_length", True),
        ("source_cutoff", True),
    ],
)
def test_descriptor_constructor_rejects_bool_integer_aliases(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="exact integer"):
        replace(_ordinary(sequence=1), **{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    [
        ("opcode", int(Opcode.ROPE_APPLY), "opcode"),
        ("tensor_role", int(TensorRole.QUERY), "tensor_role"),
        ("profile", int(RopeProfile.BASE), "profile"),
        ("scaling_mode", int(ScalingMode.NONE), "scaling_mode"),
        ("phase", int(Phase.PREFILL), "phase"),
        ("position_policy", int(PositionPolicy.CONSECUTIVE), "position_policy"),
        ("numeric_profile", "opentallas.deepseek_v4_rope_numeric.v1", "numeric"),
        ("numeric_profile", True, "numeric"),
    ],
)
def test_descriptor_constructor_rejects_untyped_enums_and_profile_drift(
    field_name: str,
    value: object,
    match: str,
) -> None:
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match=match):
        replace(_ordinary(sequence=1), **{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("opcode", int(Opcode.ROPE_APPLY)),
        ("tensor_role", int(TensorRole.QUERY)),
        ("sequence_length", "1"),
        ("profile", int(RopeProfile.BASE)),
        ("position_policy", int(PositionPolicy.CONSECUTIVE)),
        ("compression_ratio", "0"),
        ("request_start_position", "0"),
        ("source_sequence_length", object()),
    ],
)
def test_descriptor_builder_rejects_untyped_values_before_derived_arithmetic(
    field_name: str,
    value: object,
) -> None:
    arguments: dict[str, object] = {
        "opcode": Opcode.ROPE_APPLY,
        "tensor_role": TensorRole.QUERY,
        "tensor_rank": 4,
        "batch_count": 1,
        "sequence_length": 1,
        "head_count": 8,
        "head_width": 512,
        "profile": RopeProfile.BASE,
        "phase": Phase.PREFILL,
        "position_policy": PositionPolicy.CONSECUTIVE,
        "compression_ratio": 0,
        "request_start_position": 0,
        "source_sequence_length": None,
    }
    arguments[field_name] = value
    with pytest.raises(DeepSeekV4RopeMicrocodeError):
        build_descriptor(**arguments)


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"profile": RopeProfile.COMPRESSED_YARN}, "profile"),
        ({"scaling_mode": ScalingMode.YARN}, "scaling"),
        ({"theta": COMPRESSED_ROPE_THETA}, "scaling"),
        ({"original_sequence_length": 65_536}, "scaling"),
        ({"yarn_factor": 16}, "scaling"),
        ({"beta_fast": 32}, "scaling"),
        ({"correction_high": 25}, "scaling"),
        ({"compression_ratio": 4}, "profile"),
    ],
)
def test_base_descriptor_rejects_every_ambiguous_or_partial_scaling_mode(
    updates: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match=match):
        replace(_ordinary(sequence=1), **updates)


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"profile": RopeProfile.BASE}, "profile"),
        ({"scaling_mode": ScalingMode.NONE}, "scaling"),
        ({"theta": BASE_ROPE_THETA}, "scaling"),
        ({"original_sequence_length": 0}, "scaling"),
        ({"yarn_factor": 1}, "scaling"),
        ({"beta_slow": 0}, "scaling"),
        ({"correction_low": 14}, "scaling"),
        ({"correction_high": 26}, "scaling"),
    ],
)
def test_compressed_descriptor_rejects_profile_or_yarn_constant_drift(
    updates: dict[str, object],
    match: str,
) -> None:
    descriptor = _ordinary(
        profile=RopeProfile.COMPRESSED_YARN,
        ratio=4,
        sequence=1,
        phase=Phase.DECODE,
        start=7,
    )
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match=match):
        replace(descriptor, **updates)


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"tensor_rank": 2}, "tensor_rank"),
        ({"tensor_rank": 5}, "tensor_rank"),
        ({"batch_count": 0}, "batch_count"),
        ({"batch_count": 5}, "batch_count"),
        ({"sequence_length": 0}, "sequence_length"),
        ({"sequence_length": 65_537}, "sequence_length"),
        ({"head_count": 1}, "head_count"),
        ({"head_count": 7}, "head_count"),
        ({"head_width": 256}, "head_width"),
        ({"rope_dimension": 32}, "rope_dimension"),
        ({"last_table_position": MAX_POSITION + 1}, "last_table_position"),
    ],
)
def test_descriptor_rejects_nonofficial_shapes_and_position_bounds(
    updates: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match=match):
        replace(_ordinary(sequence=1), **updates)


@pytest.mark.parametrize(
    "descriptor",
    [
        _ordinary(),
        _ordinary(role=TensorRole.KV, rank=3, heads=1),
        _ordinary(
            role=TensorRole.INDEX_QUERY,
            width=128,
            profile=RopeProfile.COMPRESSED_YARN,
            ratio=4,
        ),
        _ordinary(
            opcode=Opcode.ROPE_INVERSE,
            role=TensorRole.ATTENTION_OUTPUT,
        ),
    ],
)
def test_direction_rank_width_and_role_are_jointly_authoritative(
    descriptor: RopeDescriptor,
) -> None:
    for field_name, value in (
        (
            "opcode",
            Opcode.ROPE_INVERSE
            if descriptor.opcode is Opcode.ROPE_APPLY
            else Opcode.ROPE_APPLY,
        ),
        ("tensor_rank", 3 if descriptor.tensor_rank == 4 else 4),
        ("head_width", 128 if descriptor.head_width == 512 else 512),
    ):
        with pytest.raises(DeepSeekV4RopeMicrocodeError, match="role|rank|width"):
            replace(descriptor, **{field_name: value})


def test_index_query_exists_only_on_the_official_ratio_four_path() -> None:
    descriptor = _ordinary(
        role=TensorRole.INDEX_QUERY,
        width=128,
        profile=RopeProfile.COMPRESSED_YARN,
        ratio=4,
    )
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="ratio 4"):
        replace(descriptor, compression_ratio=128)


@pytest.mark.parametrize("ratio", [4, 128])
def test_compressor_prefill_policy_rejects_stride_cutoff_and_mode_drift(
    ratio: int,
) -> None:
    descriptor = _compressor_prefill(ratio, source_length=3 * ratio + 1)
    cases = (
        {"position_stride": 1},
        {"position_stride": 4 if ratio == 128 else 128},
        {"source_cutoff": descriptor.source_cutoff - 1},
        {"sequence_length": descriptor.sequence_length - 1},
        {"request_start_position": 1},
        {"table_start_position": 1},
        {"last_table_position": descriptor.last_table_position + 1},
        {"phase": Phase.DECODE},
        {"position_policy": PositionPolicy.CONSECUTIVE},
        {"opcode": Opcode.ROPE_INVERSE},
    )
    for updates in cases:
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            replace(descriptor, **updates)


@pytest.mark.parametrize("ratio", [4, 128])
def test_compressor_decode_policy_rejects_unadjusted_or_nonboundary_position(
    ratio: int,
) -> None:
    descriptor = _compressor_decode(ratio, request_start=3 * ratio - 1)
    cases = (
        {"table_start_position": descriptor.request_start_position},
        {"table_start_position": descriptor.table_start_position + 1},
        {"request_start_position": descriptor.request_start_position - 1},
        {"sequence_length": 2},
        {"source_sequence_length": 2},
        {"source_cutoff": 2},
        {"position_stride": ratio},
        {"phase": Phase.PREFILL},
        {"position_policy": PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE},
        {"opcode": Opcode.ROPE_INVERSE},
    )
    for updates in cases:
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            replace(descriptor, **updates)


def test_build_descriptor_fails_before_position_underflow_or_overflow_can_wrap() -> (
    None
):
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="last_table_position"):
        _ordinary(sequence=2, phase=Phase.DECODE, start=MAX_POSITION)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="table_start_position"):
        _compressor_decode(128, request_start=0)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="sequence_length|cutoff"):
        _compressor_prefill(128, source_length=127)


def test_instruction_constructor_and_verifier_reject_aliases_and_forgery() -> None:
    descriptor = _ordinary(sequence=1)
    program = assemble(descriptor)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="destination"):
        Instruction(
            Opcode.ROPE_APPLY,
            destination=Register.INPUT,
            source=Register.INPUT,
            resource=Resource.BASE_PHASOR_TABLE,
            descriptor=descriptor,
        )
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="typed OUTPUT"):
        Instruction(
            Opcode.ROPE_APPLY,
            destination=int(Register.OUTPUT),
            source=Register.INPUT,
            resource=Resource.BASE_PHASOR_TABLE,
            descriptor=descriptor,
        )

    forged_first = _forge(program[0], destination=Register.INPUT)
    forged_complete = _forge(program[1], flags=1)
    for forged_program in (
        (forged_first, program[1]),
        (program[0], forged_complete),
        tuple(reversed(program)),
        program[:1],
        (*program, program[1]),
    ):
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            verify(forged_program)
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            encode(forged_program)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="exact two"):
        verify(list(program))


def test_forged_descriptor_cannot_bypass_public_verification_or_schedule_build() -> (
    None
):
    descriptor = _ordinary(sequence=1)
    forged = _forge(descriptor, numeric_profile="forged")
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="numeric"):
        verify_descriptor(forged)
    forged_instruction = _forge(assemble(descriptor)[0], descriptor=forged)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="numeric"):
        verify((forged_instruction, Instruction(Opcode.COMPLETE)))
    with pytest.raises(DeepSeekV4RopeScheduleError, match="typed RoPE|numeric"):
        build_deepseek_v4_rope_logical_schedule(forged)


def test_wire_decoder_rejects_header_crc_length_and_type_corruption() -> None:
    payload = encode(assemble(_ordinary(sequence=1)))
    cases = (
        payload[: HEADER.size - 1],
        b"BAD!" + payload[4:],
        _rewrite_header(payload, major=ABI_MAJOR + 1),
        _rewrite_header(payload, minor=ABI_MINOR + 1),
        _rewrite_header(payload, record_size=RECORD.size - 4),
        _rewrite_header(payload, count=1),
        payload[:-1],
        payload + b"\x00",
        _rewrite_record(payload, 0, 3, 0, refresh_crc=False),
    )
    for candidate in cases:
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            decode(candidate)
    for alias in (bytearray(payload), memoryview(payload), "payload"):
        with pytest.raises(DeepSeekV4RopeMicrocodeError, match="exact bytes"):
            decode(alias)


@pytest.mark.parametrize(
    ("record_index", "field_index", "value"),
    [
        (0, 0, 0x62),
        (0, 1, 1),
        (0, 2, 1),
        (0, 3, int(Register.INPUT)),
        (0, 4, int(Register.OUTPUT)),
        (0, 5, int(Resource.COMPRESSED_YARN_PHASOR_TABLE)),
        (0, 6, 255),
        (0, 7, 3),
        (0, 8, 5),
        (0, 11, 256),
        (0, 12, 32),
        (0, 13, NUMERIC_PROFILE_CODE ^ 1),
        (0, 14, int(RopeProfile.COMPRESSED_YARN)),
        (0, 15, int(ScalingMode.YARN)),
        (0, 16, COMPRESSED_ROPE_THETA),
        (0, 23, int(Phase.DECODE)),
        (0, 24, int(PositionPolicy.COMPRESSOR_DECODE_ADJUSTED)),
        (0, 25, 4),
        (0, 27, 1),
        (0, 28, 1),
        (0, 29, 4),
        (1, 1, 1),
        (1, 2, 1),
        (1, 3, 0),
    ],
)
def test_crc_refreshed_wire_forgery_still_fails_semantic_verification(
    record_index: int,
    field_index: int,
    value: int,
) -> None:
    descriptor = _ordinary(sequence=1)
    payload = encode(assemble(descriptor))
    forged = _rewrite_record(payload, record_index, field_index, value)
    with pytest.raises(DeepSeekV4RopeMicrocodeError):
        verify(decode(forged), descriptor)


def test_tensor_resource_position_and_state_contracts_are_typed_and_immutable() -> None:
    descriptor = _compressor_prefill(128, source_length=513)
    tensors = tensor_contract(descriptor)
    resources = resource_contract(descriptor)
    position = position_contract(descriptor)
    state = state_contract(descriptor)
    assert tensors[0].shape == tensors[1].shape == (4, 4, 512)
    assert tensors[0].access == "read_only"
    assert tensors[1].access == "write_only"
    assert tensors[0].alias_of is tensors[1].alias_of is None
    assert tensors[0].preserved_prefix_width == 448
    assert tensors[0].rotary_suffix_width == ROPE_DIMENSION
    assert tensors[0].channel_semantics.endswith("adjacent_complex_pairs")
    assert resources[0].resource is Resource.COMPRESSED_YARN_PHASOR_TABLE
    assert resources[0].checkpoint_derived is False
    assert resources[0].rope_dimension == ROPE_DIMENSION
    assert resources[0].complex_pair_count == ROPE_COMPLEX_PAIRS
    assert position.position_stride == 128
    assert state.mutable_state_reads == state.mutable_state_writes == ()
    assert state.alias_policy == "distinct_input_output_registers_no_in_place_alias"
    assert state.preserved_prefix_policy.endswith("bit_exact")
    assert state.rotary_suffix_width == ROPE_DIMENSION
    verify_tensor_contract(tensors, descriptor)
    verify_resource_contract(resources, descriptor)
    verify_position_contract(position, descriptor)
    verify_state_contract(state, descriptor)
    for value in (*tensors, *resources, position, state):
        with pytest.raises((AttributeError, TypeError)):
            value.__dict__[next(iter(value.__dict__))] = object()


def test_contract_constructors_and_verifiers_reject_mutable_aliases_and_forgery() -> (
    None
):
    descriptor = _ordinary(sequence=2, batch=1, heads=8)
    tensors = tensor_contract(descriptor)
    resources = resource_contract(descriptor)
    position = position_contract(descriptor)
    state = state_contract(descriptor)

    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="immutable"):
        replace(tensors[0], shape=list(tensors[0].shape))
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="alias"):
        replace(tensors[1], alias_of=Register.INPUT)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="preserved-prefix"):
        replace(tensors[0], preserved_prefix_width=0)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="complex-pair"):
        replace(resources[0], complex_pair_count=16)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="profile constants"):
        replace(resources[0], theta=COMPRESSED_ROPE_THETA)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="position range"):
        replace(position, last_table_position=2)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="mutable state"):
        replace(state, mutable_state_writes=("state.cache",))
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="request input"):
        replace(state, request_inputs=["request.start_pos"])
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="rotary suffix"):
        replace(state, rotary_suffix_width=32)

    forged_tensor = _forge(tensors[0], shape=(1, 2, 128))
    forged_resource = _forge(resources[0], semantic_sha256="0" * 64)
    forged_position = _forge(position, position_stride=4)
    forged_state = _forge(state, mutable_state_reads=("state.cache",))
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="tensor contract"):
        verify_tensor_contract((forged_tensor, tensors[1]), descriptor)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="resource contract"):
        verify_resource_contract((forged_resource,), descriptor)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="position contract"):
        verify_position_contract(forged_position, descriptor)
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="state/commit"):
        verify_state_contract(forged_state, descriptor)
    for alias, verifier in (
        (list(tensors), lambda value: verify_tensor_contract(value, descriptor)),
        (list(resources), lambda value: verify_resource_contract(value, descriptor)),
        (
            {field.name: getattr(position, field.name) for field in fields(position)},
            lambda value: verify_position_contract(value, descriptor),
        ),
        (
            {field.name: getattr(state, field.name) for field in fields(state)},
            lambda value: verify_state_contract(value, descriptor),
        ),
    ):
        with pytest.raises(DeepSeekV4RopeMicrocodeError):
            verifier(alias)


def test_program_contract_is_content_bound_and_rejects_self_rehashed_forgery() -> None:
    descriptor = _compressor_decode(128, request_start=65_535)
    contract = build_program_contract(descriptor)
    body = dict(contract)
    contract_id = body.pop("contract_id")
    assert contract_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert contract["descriptor_id"] == descriptor_id(descriptor)
    assert contract["operator_sequence"] == ["ROPE_APPLY", "COMPLETE"]
    assert contract["required_nonclaims"] == list(EXPLICIT_NON_CLAIMS)
    verify_program_contract(contract, descriptor)

    forged = deepcopy(contract)
    forged["program_bytes"] = True
    forged_body = dict(forged)
    forged_body.pop("contract_id")
    forged["contract_id"] = hashlib.sha256(
        canonical_json_bytes(forged_body)
    ).hexdigest()
    with pytest.raises(DeepSeekV4RopeMicrocodeError, match="program contract"):
        verify_program_contract(forged, descriptor)


FROZEN_IDENTITIES = {
    "base_max_prefill": (
        "99e9894546ce96a6b8cdd79253094a57f015b6e46d4956d4e92aa04af39b654a",
        "95f46965178373c965cbf1f776b11c0b959829524569e97b4d64d952843dd99f",
    ),
    "ratio128_max_prefill": (
        "1b4f835fb6b0fedb2e0ec9e687c11994430acd27c420c3e404649ae0cfef0900",
        "5b8e387a198bbc3985bc1f6aaa136775c9cb348ab46b1aadefb2a8559036e416",
    ),
    "ratio128_max_decode": (
        "58a44ee86443b71de9f67a8b576756871db1600fb8b2b10dee1a3dd4247078b4",
        "79be31907fc3fac3e2852a9631dc1dd7d33049d21b987e9d4f61578caf382ba6",
    ),
    "compressed_max_inverse": (
        "1c6cf116762a7614fcd4fe7a8a8e8eb6f6dd78a438eef9cc1c98d4fdf61ee0a9",
        "724aa55ba55909a2a1f817f83c01146eb9902baf79868de379ed6aab0df15fa5",
    ),
}


@pytest.mark.parametrize(
    ("name", "descriptor"),
    [
        ("base_max_prefill", _ordinary()),
        ("ratio128_max_prefill", _compressor_prefill(128)),
        ("ratio128_max_decode", _compressor_decode(128, request_start=65_535)),
        (
            "compressed_max_inverse",
            _ordinary(
                opcode=Opcode.ROPE_INVERSE,
                role=TensorRole.ATTENTION_OUTPUT,
                profile=RopeProfile.COMPRESSED_YARN,
                ratio=4,
                phase=Phase.DECODE,
                sequence=1,
                start=65_535,
            ),
        ),
    ],
)
def test_program_and_schedule_identity_is_frozen_and_deterministic(
    name: str,
    descriptor: RopeDescriptor,
) -> None:
    first_program = encode(assemble(descriptor))
    second_program = encode(assemble(descriptor))
    first = build_deepseek_v4_rope_logical_schedule(descriptor)
    second = build_deepseek_v4_rope_logical_schedule(descriptor)
    assert first_program == second_program
    assert first == second
    assert (
        hashlib.sha256(first_program).hexdigest(),
        first["schedule_id"],
    ) == FROZEN_IDENTITIES[name]
    assert (
        verify_deepseek_v4_rope_logical_schedule(first, descriptor)
        == first["schedule_id"]
    )


def test_logical_schedule_carries_complete_register_resource_position_and_state_tables() -> (
    None
):
    descriptor = _compressor_prefill(4, source_length=15)
    schedule = build_deepseek_v4_rope_logical_schedule(descriptor)
    assert schedule["schema"] == LOGICAL_SCHEDULE_SCHEMA
    assert schedule["status"] == LOGICAL_SCHEDULE_STATUS
    assert schedule["claim_boundary"] == CLAIM_BOUNDARY
    assert schedule["ordering_policy"] == ORDERING_POLICY
    assert schedule["required_nonclaims"] == list(REQUIRED_NONCLAIMS)
    assert schedule["descriptor"] == descriptor_record(descriptor)
    assert [record["register_name"] for record in schedule["registers"]] == [
        "INPUT",
        "OUTPUT",
    ]
    assert schedule["registers"][0]["shape"] == [4, 3, 512]
    assert schedule["registers"][0]["preserved_prefix_width"] == 448
    assert schedule["registers"][0]["rotary_suffix_width"] == ROPE_DIMENSION
    assert schedule["resources"][0]["profile"] == "COMPRESSED_YARN"
    assert schedule["resources"][0]["complex_pair_count"] == ROPE_COMPLEX_PAIRS
    assert schedule["position_contract"]["position_stride"] == 4
    assert schedule["state_contract"]["mutable_state_reads"] == []
    assert schedule["state_contract"]["mutable_state_writes"] == []
    assert schedule["state_contract"]["rotary_suffix_width"] == ROPE_DIMENSION
    assert [slot["opcode"] for slot in schedule["slots"]] == [
        "ROPE_APPLY",
        "COMPLETE",
    ]
    assert schedule["slots"][1]["dependency_slots"] == [0]
    assert schedule["slots"][1]["terminal"] is True
    assert schedule["summary"]["logical_table_position_count"] == 3
    assert schedule["summary"]["generated_phasor_resource_bytes"] == (
        PHASOR_TABLE_BYTES
    )


def test_schedule_builder_does_not_share_mutable_identity_between_results() -> None:
    descriptor = _ordinary(sequence=2, batch=1, heads=8)
    first = build_deepseek_v4_rope_logical_schedule(descriptor)
    second = build_deepseek_v4_rope_logical_schedule(descriptor)
    expected_id = second["schedule_id"]
    first["registers"][0]["shape"][0] = 99
    first["required_nonclaims"].clear()
    assert second["registers"][0]["shape"] == [1, 2, 8, 512]
    assert second["required_nonclaims"] == list(REQUIRED_NONCLAIMS)
    assert second["schedule_id"] == expected_id
    assert verify_deepseek_v4_rope_logical_schedule(second, descriptor) == expected_id


def test_schedule_verifier_rejects_rehashed_nested_forgery_and_ordering_drift() -> None:
    descriptor = _compressor_decode(4, request_start=15)
    canonical = build_deepseek_v4_rope_logical_schedule(descriptor)
    mutators: tuple[Callable[[dict[str, Any]], None], ...] = (
        lambda item: item["descriptor"].__setitem__("profile", "BASE"),
        lambda item: item["identity"].__setitem__("numeric_profile", "v1"),
        lambda item: item["identity"].__setitem__("program_sha256", "0" * 64),
        lambda item: item["ordering_policy"].__setitem__("slot_rule", "forged"),
        lambda item: item["position_contract"].__setitem__("position_stride", 4),
        lambda item: item["position_contract"].__setitem__("table_start_position", 15),
        lambda item: item["registers"][1].__setitem__("register_id", 0),
        lambda item: item["registers"][0].__setitem__("shape", [4, 1, 128]),
        lambda item: item["resources"][0].__setitem__("theta", BASE_ROPE_THETA),
        lambda item: item["state_contract"]["mutable_state_writes"].append(
            "state.cache"
        ),
        lambda item: item["slots"].reverse(),
        lambda item: item["slots"][1].__setitem__("dependency_slots", []),
        lambda item: item["slots"][0].__setitem__("slot", True),
        lambda item: item["summary"].__setitem__("complete_count", True),
        lambda item: item["required_nonclaims"].pop(),
        lambda item: item.__setitem__("extra", None),
    )
    for mutate in mutators:
        forged = deepcopy(canonical)
        mutate(forged)
        _rehash_schedule(forged)
        with pytest.raises(DeepSeekV4RopeCheckError):
            verify_deepseek_v4_rope_logical_schedule(forged, descriptor)


def test_schedule_verifier_rejects_mapping_list_and_scalar_type_aliases() -> None:
    descriptor = _ordinary(sequence=1, batch=1, heads=8)
    schedule = build_deepseek_v4_rope_logical_schedule(descriptor)
    for alias in (list(schedule.items()), tuple(schedule.items()), "schedule", None):
        with pytest.raises(DeepSeekV4RopeCheckError, match="exact.*object"):
            verify_deepseek_v4_rope_logical_schedule(alias, descriptor)
    forged = deepcopy(schedule)
    forged["registers"] = tuple(forged["registers"])
    _rehash_schedule(forged)
    with pytest.raises(DeepSeekV4RopeCheckError, match="exact array|non-canonical"):
        verify_deepseek_v4_rope_logical_schedule(forged, descriptor)


def test_compiled_verifier_cross_binds_program_schedule_and_descriptor() -> None:
    base = _ordinary(sequence=1, batch=1, heads=8)
    compressed = _ordinary(
        sequence=1,
        batch=1,
        heads=8,
        profile=RopeProfile.COMPRESSED_YARN,
        ratio=4,
    )
    base_payload = encode(assemble(base))
    base_schedule = build_deepseek_v4_rope_logical_schedule(base)
    report = verify_compiled_deepseek_v4_rope(base_payload, base_schedule, base)
    assert report.tensor_shape == (1, 1, 8, 512)
    assert report.opcode == "ROPE_APPLY"
    assert report.numeric_profile == NUMERIC_PROFILE
    assert report.mutable_state_read_count == report.mutable_state_write_count == 0

    with pytest.raises(DeepSeekV4RopeCheckError):
        verify_compiled_deepseek_v4_rope(base_payload, base_schedule, compressed)
    with pytest.raises(DeepSeekV4RopeCheckError):
        verify_compiled_deepseek_v4_rope(
            encode(assemble(compressed)),
            base_schedule,
            compressed,
        )
    with pytest.raises(DeepSeekV4RopeCheckError, match="exact bytes"):
        verify_compiled_deepseek_v4_rope(bytearray(base_payload), base_schedule, base)


def test_verification_report_and_certificate_are_authoritative_and_hash_bound() -> None:
    descriptor = _ordinary(
        opcode=Opcode.ROPE_INVERSE,
        role=TensorRole.ATTENTION_OUTPUT,
        profile=RopeProfile.COMPRESSED_YARN,
        ratio=128,
        phase=Phase.DECODE,
        sequence=1,
        start=65_535,
    )
    payload = encode(assemble(descriptor))
    schedule = build_deepseek_v4_rope_logical_schedule(descriptor)
    report = verify_compiled_deepseek_v4_rope(payload, schedule, descriptor)
    certificate = build_verification_certificate(report)
    body = dict(certificate)
    certificate_id = body.pop("certificate_id")
    assert certificate["claim_boundary"] == CERTIFICATE_CLAIM_BOUNDARY
    assert certificate["required_nonclaims"] == list(REQUIRED_NONCLAIMS)
    assert certificate_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    verify_verification_certificate(certificate, report)

    with pytest.raises(DeepSeekV4RopeCheckError, match="numeric profile"):
        replace(report, numeric_profile="v1")
    with pytest.raises(
        DeepSeekV4RopeCheckError,
        match="positions|last_table_position",
    ):
        replace(report, last_table_position=report.last_table_position + 1)
    with pytest.raises(DeepSeekV4RopeCheckError, match="mutable state"):
        replace(report, mutable_state_write_count=1)
    forged_report = _forge(report, program_sha256="forged")
    with pytest.raises(DeepSeekV4RopeCheckError, match="program_sha256"):
        build_verification_certificate(forged_report)
    report_mapping = {
        field.name: getattr(report, field.name) for field in fields(report)
    }
    with pytest.raises(DeepSeekV4RopeCheckError, match="exact RopeVerificationReport"):
        build_verification_certificate(report_mapping)

    forged = deepcopy(certificate)
    forged["status"] = "executed"
    forged_body = dict(forged)
    forged_body.pop("certificate_id")
    forged["certificate_id"] = hashlib.sha256(
        canonical_json_bytes(forged_body)
    ).hexdigest()
    with pytest.raises(DeepSeekV4RopeCheckError, match="certificate differs"):
        verify_verification_certificate(forged, report)


def test_schedule_checker_bounds_nested_external_json_before_canonicalization() -> None:
    descriptor = _ordinary(sequence=1, batch=1, heads=8)
    schedule = build_deepseek_v4_rope_logical_schedule(descriptor)
    nested: object = "claim"
    for _ in range(20):
        nested = [nested]
    schedule["required_nonclaims"] = nested
    with pytest.raises(DeepSeekV4RopeCheckError, match="bounded canonical JSON"):
        verify_deepseek_v4_rope_logical_schedule(schedule, descriptor)


def test_disassembly_exposes_profile_position_policy_and_complete_shape() -> None:
    descriptor = _compressor_decode(128, request_start=65_535)
    text = disassemble(assemble(descriptor))
    assert text.startswith("# OpenTallas DeepSeek V4 RoPE ABI 1.0\n")
    assert "ROPE_APPLY" in text
    assert "resource=COMPRESSED_YARN_PHASOR_TABLE" in text
    assert "profile=COMPRESSED_YARN" in text
    assert "phase=DECODE" in text
    assert "policy=COMPRESSOR_DECODE_ADJUSTED" in text
    assert "shape=(4, 1, 512)" in text
    assert "request_start=65535 table_start=65408 stride=1" in text
    assert text.endswith("0001 COMPLETE\n")


def test_compiler_artifacts_contain_no_activation_execution_or_physical_claims() -> (
    None
):
    descriptor = _ordinary(sequence=1, batch=1, heads=8)
    payload = encode(assemble(descriptor))
    schedule = build_deepseek_v4_rope_logical_schedule(descriptor)
    contract = build_program_contract(descriptor)
    combined = b"\n".join(
        (payload, canonical_json_bytes(schedule), canonical_json_bytes(contract))
    ).lower()
    assert b"output_bf16_codes" not in combined
    assert b"activation_payload" not in combined
    assert b"expected_output" not in combined
    assert set(EXPLICIT_NON_CLAIMS).issubset(schedule["required_nonclaims"])
    for claim in (
        "cycle_accuracy",
        "cycle_latency",
        "full_model_execution",
        "physical_schedule",
        "ppa",
        "rtl_execution",
        "target_kernel_execution",
    ):
        assert claim in schedule["required_nonclaims"]


def test_compiler_lane_has_no_torch_numpy_checkpoint_or_runtime_execution_dependency() -> (
    None
):
    sources = "\n".join(
        inspect.getsource(module)
        for module in (microcode_module, schedule_module, checker_module)
    )
    assert "import torch" not in sources
    assert "import numpy" not in sources
    assert "safetensors" not in sources
    assert "apply_rotary_bf16" not in sources
    assert "rope_apply_bf16" not in sources
    assert "rope_inverse_bf16" not in sources
    assert "open(" not in sources
    assert "Path(" not in sources
    assert "subprocess" not in sources
    assert "import time" not in sources
    assert "time.time" not in sources


def test_descriptor_record_has_no_implicit_profile_or_position_defaults() -> None:
    descriptor = _compressor_prefill(128, source_length=513)
    record = descriptor_record(descriptor)
    assert set(record) == {field.name for field in fields(RopeDescriptor)}
    assert record["numeric_profile"] == NUMERIC_PROFILE
    assert record["profile"] == "COMPRESSED_YARN"
    assert record["scaling_mode"] == "YARN"
    assert record["theta"] == COMPRESSED_ROPE_THETA
    assert record["phase"] == "PREFILL"
    assert record["position_policy"] == "COMPRESSOR_PREFILL_RATIO_STRIDE"
    assert record["compression_ratio"] == 128
    assert record["position_stride"] == 128
    assert record["source_sequence_length"] == 513
    assert record["source_cutoff"] == 512


def test_wire_layout_is_fixed_width_and_has_no_host_padding() -> None:
    assert MAGIC == b"OTRP"
    assert (ABI_MAJOR, ABI_MINOR) == (1, 0)
    assert HEADER.size == 16
    assert RECORD.size == 120
    assert PROGRAM_INSTRUCTION_COUNT == 2
    payload = encode(assemble(_ordinary(sequence=1)))
    magic, major, minor, size, count, crc = HEADER.unpack_from(payload)
    assert (magic, major, minor, size, count) == (b"OTRP", 1, 0, 120, 2)
    assert crc == zlib.crc32(payload[HEADER.size :]) & 0xFFFFFFFF
    complete = RECORD.unpack_from(payload, HEADER.size + RECORD.size)
    assert complete[:3] == (int(Opcode.COMPLETE), 0, 0)
    assert complete[3:6] == (NO_OPERAND, NO_OPERAND, NO_OPERAND)
    assert complete[6:] == (0,) * 26
    assert struct.calcsize("<BBH" + "I" * 29) == RECORD.size
