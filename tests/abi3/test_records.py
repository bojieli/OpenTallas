"""Round-trip and fail-closed tests for the four fixed ABI 3.0 records.

Section 1 of the wire format says unknown major versions, nonzero reserved
values, invalid lengths and invalid CRCs "fail before work is issued".  These
tests take a *valid* record, make exactly one thing wrong, restore the integrity
fields so nothing else can object, and require the decoder to reject it anyway.
Restoring the CRC matters: a test that corrupts a field and leaves the CRC stale
proves only that the CRC works.
"""

from __future__ import annotations


import pytest

from runtime.abi3.constants import (
    ABI_MINOR,
    COMPLETION_BYTES,
    INSTRUCTION_BYTES,
    NO_ID,
    PROGRAM_HEADER_BYTES,
    SUBMISSION_BYTES,
    SUBOPCODES,
    CompletionFlag,
    CompletionStatus,
    Control,
    HostOpcode,
    InstructionFlag,
    Major,
    SubmissionFlag,
    Tensor,
    TrapClass,
)
from runtime.abi3.crc import record_crc, sha256
from runtime.abi3.layout import Layout, RecordError
from runtime.abi3.records import (
    COMPLETION,
    INSTRUCTION,
    PROGRAM_HEADER,
    SUBMISSION,
    Completion,
    EosReason,
    Instruction,
    ProgramHeader,
    Submission,
    build_program,
    decode_body,
    encode_body,
    split_program,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def reseal(record: bytes, layout: Layout) -> bytes:
    """Re-stamp ``record``'s own CRC field after an edit."""
    offset = layout.crc_offset()
    edited = bytearray(record)
    edited[offset : offset + 4] = b"\x00\x00\x00\x00"
    edited[offset : offset + 4] = record_crc(bytes(edited), offset).to_bytes(
        4, "little"
    )
    return bytes(edited)


def poke(record: bytes, layout: Layout, field: str, value: int) -> bytes:
    """Overwrite one field and restore the record CRC."""
    spec = layout.field(field)
    edited = bytearray(record)
    edited[spec.offset : spec.end] = int(value).to_bytes(spec.size, "little")
    return reseal(bytes(edited), layout)


def sample_header(**overrides: object) -> ProgramHeader:
    fields: dict[str, object] = {
        "instruction_count": 3,
        "entrypoint_count": 1,
        "required_features": bytes(range(32)),
        "deployment_digest": bytes([1]) * 32,
        "descriptor_table_digest": bytes([2]) * 32,
        "topology_digest": bytes([3]) * 32,
        "body_digest": bytes([4]) * 32,
        "max_retired_work": 4096,
        "watchdog_class": 1,
        "entrypoint_table_descriptor": 7,
        "signature_metadata_descriptor": NO_ID,
    }
    fields.update(overrides)
    return ProgramHeader(**fields)  # type: ignore[arg-type]


def sample_submission(**overrides: object) -> Submission:
    fields: dict[str, object] = {
        "host_opcode": int(HostOpcode.GENERATE),
        "deployment_id": 1,
        "deployment_generation": 2,
        "session_id": 3,
        "session_generation": 4,
        "request_descriptor_id": 5,
        "transaction_id": (1 << 64) - 1,
        "idempotency_key": bytes(range(16)),
        "input_window_id": 6,
        "output_window_id": 7,
        "input_offset": 1 << 40,
        "input_bytes": 4096,
        "output_offset": 1 << 41,
        "output_capacity_bytes": 8192,
        "entrypoint_id": 0,
        "generation_policy_id": 9,
        "watchdog_class": 2,
        "deadline_cycles": 1 << 33,
        "flags": int(SubmissionFlag.DECODE_PHASE | SubmissionFlag.TRACE_ENABLE),
    }
    fields.update(overrides)
    return Submission(**fields)  # type: ignore[arg-type]


def sample_completion(**overrides: object) -> Completion:
    fields: dict[str, object] = {
        "status": int(CompletionStatus.SUCCESS),
        "transaction_id": (1 << 64) - 1,
        "deployment_id": 1,
        "deployment_generation": 2,
        "session_id": 3,
        "session_generation": 4,
        "trap_class": int(TrapClass.NONE),
        "engine_fault_class": 0,
        "committed_token_position": 11,
        "produced_token_count": 5,
        "committed_state_generation": 1 << 40,
        "output_bytes_written": 20,
        "first_fault_instruction": NO_ID,
        "fault_descriptor_id": NO_ID,
        "counter_snapshot_id": 3,
        "trace_id": NO_ID,
        "completion_timestamp": 1 << 50,
        "idempotency_key": bytes(range(16)),
        "final_token_id": 12,
        "eos_reason": EosReason.OFFICIAL_EOS,
        "retired_work": 4095,
        "flags": int(CompletionFlag.EOS_STOP | CompletionFlag.STATE_COMMITTED),
    }
    fields.update(overrides)
    return Completion(**fields)  # type: ignore[arg-type]


ALL_OPCODES = [
    (int(major), int(sub))
    for major, enum in SUBOPCODES.items()
    for sub in enum
]


# ---------------------------------------------------------------------------
# program header
# ---------------------------------------------------------------------------
def test_program_header_round_trips() -> None:
    header = sample_header()
    record = header.encode()
    assert len(record) == PROGRAM_HEADER_BYTES
    assert ProgramHeader.decode(record) == header


def test_program_header_crc_covers_every_preceding_byte() -> None:
    record = sample_header().encode()
    crc_offset = PROGRAM_HEADER.crc_offset()
    assert crc_offset == 252
    for index in range(crc_offset):
        edited = bytearray(record)
        edited[index] ^= 0xFF
        with pytest.raises(RecordError):
            ProgramHeader.decode(bytes(edited))


def test_program_header_rejects_bad_magic() -> None:
    edited = bytearray(sample_header().encode())
    edited[0:8] = b"OTTA3PGX"
    with pytest.raises(RecordError, match="magic"):
        ProgramHeader.decode(reseal(bytes(edited), PROGRAM_HEADER))


def test_program_header_rejects_a_foreign_abi_major() -> None:
    record = sample_header().encode()
    for major in (0, 2, 4, 255):
        with pytest.raises(RecordError, match="ABI major"):
            ProgramHeader.decode(poke(record, PROGRAM_HEADER, "abi_major", major))


def test_program_header_rejects_a_newer_abi_minor() -> None:
    record = sample_header().encode()
    for minor in (ABI_MINOR + 1, 255):
        with pytest.raises(RecordError, match="ABI minor"):
            ProgramHeader.decode(poke(record, PROGRAM_HEADER, "abi_minor", minor))


@pytest.mark.parametrize("index", range(204, 252))
def test_program_header_rejects_nonzero_reserved_bytes(index: int) -> None:
    edited = bytearray(sample_header().encode())
    edited[index] = 0x01
    with pytest.raises(RecordError, match="reserved"):
        ProgramHeader.decode(reseal(bytes(edited), PROGRAM_HEADER))


def test_program_header_rejects_wrong_record_geometry() -> None:
    record = sample_header().encode()
    with pytest.raises(RecordError, match="header_bytes"):
        ProgramHeader.decode(poke(record, PROGRAM_HEADER, "header_bytes", 512))
    with pytest.raises(RecordError, match="instruction_bytes"):
        ProgramHeader.decode(poke(record, PROGRAM_HEADER, "instruction_bytes", 16))
    with pytest.raises(RecordError):
        ProgramHeader.decode(record[:-1])
    with pytest.raises(RecordError):
        ProgramHeader.decode(record + b"\x00")


def test_program_header_rejects_reserved_flag_bits() -> None:
    record = sample_header().encode()
    for flags in (1, 0x8000, 0xFFFF):
        with pytest.raises(RecordError, match="flag"):
            ProgramHeader.decode(poke(record, PROGRAM_HEADER, "flags", flags))


def test_program_header_rejects_empty_programs() -> None:
    record = sample_header().encode()
    with pytest.raises(RecordError, match="instruction_count"):
        ProgramHeader.decode(poke(record, PROGRAM_HEADER, "instruction_count", 0))
    with pytest.raises(RecordError, match="entrypoint_count"):
        ProgramHeader.decode(poke(record, PROGRAM_HEADER, "entrypoint_count", 0))


def test_program_header_rejects_out_of_range_values_at_encode_time() -> None:
    with pytest.raises(RecordError):
        sample_header(watchdog_class=1 << 32).encode()
    with pytest.raises(RecordError):
        sample_header(max_retired_work=1 << 64).encode()
    with pytest.raises(RecordError):
        sample_header(instruction_count=-1).encode()
    with pytest.raises(RecordError):
        sample_header(body_digest=bytes(31)).encode()
    with pytest.raises(RecordError):
        sample_header(required_features=bytes(33)).encode()


def test_program_header_accepts_the_full_range_of_its_widths() -> None:
    header = sample_header(
        max_retired_work=(1 << 64) - 1,
        watchdog_class=0xFFFFFFFF,
        instruction_count=0xFFFFFFFF,
        entrypoint_count=0xFFFFFFFF,
        entrypoint_table_descriptor=NO_ID,
    )
    assert ProgramHeader.decode(header.encode()) == header


# ---------------------------------------------------------------------------
# instruction
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("major,sub", ALL_OPCODES)
def test_every_frozen_opcode_pair_round_trips(major: int, sub: int) -> None:
    instruction = Instruction(
        major=major,
        sub=sub,
        descriptor_id=1,
        wait_set_id=2,
        signal_event_id=3,
        control_id=4,
        source_operation_id=5,
    )
    record = instruction.encode()
    assert len(record) == INSTRUCTION_BYTES
    assert Instruction.decode(record) == instruction


def test_instruction_rejects_unknown_major_opcodes() -> None:
    known = {int(major) for major in Major}
    for major in (0x01, 0x0F, 0x11, 0xC0, 0xFF):
        assert major not in known
        with pytest.raises(RecordError, match="unknown major opcode"):
            Instruction(major=major, sub=0).encode()


@pytest.mark.parametrize("major", sorted(int(m) for m in SUBOPCODES))
def test_instruction_rejects_subopcodes_outside_their_family(major: int) -> None:
    legal = {int(sub) for sub in SUBOPCODES[Major(major)]}
    illegal = [value for value in range(256) if value not in legal][:4]
    for sub in illegal:
        with pytest.raises(RecordError, match="not legal for"):
            Instruction(major=major, sub=sub).encode()


def test_instruction_rejects_reserved_flag_bits() -> None:
    for bit in range(8, 16):
        with pytest.raises(RecordError, match="reserved bits"):
            Instruction(major=int(Major.CONTROL), sub=int(Control.NOP), flags=1 << bit).encode()


def test_instruction_rejects_illegal_predicate_flag_combinations() -> None:
    nop = dict(major=int(Major.CONTROL), sub=int(Control.NOP))
    with pytest.raises(RecordError, match="PREDICATE_INVERT"):
        Instruction(**nop, flags=int(InstructionFlag.PREDICATE_INVERT), predicate_id=1).encode()
    with pytest.raises(RecordError, match="predicate ID is NO_ID"):
        Instruction(**nop, flags=int(InstructionFlag.PREDICATED)).encode()
    with pytest.raises(RecordError, match="without the PREDICATED flag"):
        Instruction(**nop, predicate_id=4).encode()
    legal = Instruction(
        **nop,
        flags=int(InstructionFlag.PREDICATED | InstructionFlag.PREDICATE_INVERT),
        predicate_id=4,
    )
    assert Instruction.decode(legal.encode()) == legal


def test_instruction_flags_do_not_fit_outside_two_bytes() -> None:
    with pytest.raises(RecordError):
        INSTRUCTION.encode(
            {
                "major": 0,
                "sub": 0,
                "flags": 1 << 16,
                "predicate_id": NO_ID,
                "descriptor_id": NO_ID,
                "wait_set_id": NO_ID,
                "signal_event_id": NO_ID,
                "control_id": NO_ID,
                "source_operation_id": NO_ID,
                "instruction_crc": 0,
            }
        )


def test_instruction_crc_covers_every_preceding_byte() -> None:
    record = Instruction(major=int(Major.TENSOR), sub=int(Tensor.MATMUL)).encode()
    for index in range(INSTRUCTION.crc_offset()):
        edited = bytearray(record)
        edited[index] ^= 0xFF
        with pytest.raises(RecordError):
            Instruction.decode(bytes(edited))


def test_instruction_decode_rejects_a_stale_crc() -> None:
    record = bytearray(Instruction(major=0, sub=0).encode())
    record[28] ^= 0x01
    with pytest.raises(RecordError, match="CRC32C mismatch"):
        Instruction.decode(bytes(record))


def test_body_round_trips_and_rejects_ragged_lengths() -> None:
    program = [
        Instruction(major=int(Major.CONTROL), sub=int(Control.NOP)),
        Instruction(major=int(Major.TENSOR), sub=int(Tensor.MATMUL), descriptor_id=2),
        Instruction(major=int(Major.CONTROL), sub=int(Control.COMPLETE)),
    ]
    body = encode_body(program)
    assert len(body) == 3 * INSTRUCTION_BYTES
    assert decode_body(body) == program
    with pytest.raises(RecordError, match="not a multiple"):
        decode_body(body + b"\x00")


# ---------------------------------------------------------------------------
# program image
# ---------------------------------------------------------------------------
def program_image() -> bytes:
    return build_program(
        [
            Instruction(major=int(Major.CONTROL), sub=int(Control.NOP)),
            Instruction(major=int(Major.CONTROL), sub=int(Control.COMPLETE)),
        ],
        entrypoint_count=1,
        required_features=bytes(32),
        deployment_digest=bytes(32),
        descriptor_table_digest=bytes(32),
        topology_digest=bytes(32),
        max_retired_work=2,
        watchdog_class=1,
        entrypoint_table_descriptor=0,
    )


def test_program_image_round_trips() -> None:
    image = program_image()
    header, body = split_program(image)
    assert header.instruction_count == 2
    assert header.body_digest == sha256(body)
    assert len(image) == PROGRAM_HEADER_BYTES + 2 * INSTRUCTION_BYTES


def test_program_image_rejects_a_body_that_does_not_match_the_header() -> None:
    image = program_image()
    with pytest.raises(RecordError, match="SHA-256"):
        split_program(image[:PROGRAM_HEADER_BYTES] + bytes(2 * INSTRUCTION_BYTES))
    truncated = image[: PROGRAM_HEADER_BYTES + INSTRUCTION_BYTES]
    with pytest.raises(RecordError, match="header declares"):
        split_program(truncated)
    with pytest.raises(RecordError, match="shorter than its header"):
        split_program(image[:100])


def test_program_image_rejects_an_instruction_count_lie() -> None:
    image = program_image()
    header = poke(image[:PROGRAM_HEADER_BYTES], PROGRAM_HEADER, "instruction_count", 3)
    with pytest.raises(RecordError, match="header declares"):
        split_program(header + image[PROGRAM_HEADER_BYTES:])


# ---------------------------------------------------------------------------
# submission
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("opcode", sorted(int(o) for o in HostOpcode))
def test_every_host_opcode_round_trips(opcode: int) -> None:
    submission = sample_submission(host_opcode=opcode)
    record = submission.encode()
    assert len(record) == SUBMISSION_BYTES
    assert Submission.decode(record) == submission


def test_submission_rejects_unknown_host_opcodes() -> None:
    known = {int(o) for o in HostOpcode}
    record = sample_submission().encode()
    for opcode in (0x05, 0x0F, 0x15, 0x24, 0xFF):
        assert opcode not in known
        with pytest.raises(ValueError):
            sample_submission(host_opcode=opcode).encode()
        with pytest.raises(ValueError):
            Submission.decode(poke(record, SUBMISSION, "host_opcode", opcode))


def test_submission_rejects_bad_magic_version_and_size() -> None:
    record = sample_submission().encode()
    edited = bytearray(record)
    edited[0:4] = b"TA3X"
    with pytest.raises(RecordError, match="magic"):
        Submission.decode(reseal(bytes(edited), SUBMISSION))
    with pytest.raises(RecordError, match="major"):
        Submission.decode(poke(record, SUBMISSION, "abi_major", 4))
    with pytest.raises(RecordError, match="minor"):
        Submission.decode(poke(record, SUBMISSION, "abi_minor", ABI_MINOR + 1))
    with pytest.raises(RecordError, match="record_bytes"):
        Submission.decode(poke(record, SUBMISSION, "record_bytes", 256))
    with pytest.raises(RecordError):
        Submission.decode(record[:-1])


@pytest.mark.parametrize("index", [10, 11, 108, 109, 110, 111, 120, 121, 122, 123])
def test_submission_rejects_nonzero_reserved_bytes(index: int) -> None:
    edited = bytearray(sample_submission().encode())
    edited[index] = 0xFF
    with pytest.raises(RecordError, match="reserved"):
        Submission.decode(reseal(bytes(edited), SUBMISSION))


def test_submission_crc_covers_every_preceding_byte() -> None:
    record = sample_submission().encode()
    for index in range(SUBMISSION.crc_offset()):
        if index in {10, 11, 108, 109, 110, 111, 120, 121, 122, 123}:
            continue  # reserved spans are rejected before the CRC is consulted
        edited = bytearray(record)
        edited[index] ^= 0xFF
        with pytest.raises(ValueError):
            Submission.decode(bytes(edited))


def test_submission_rejects_a_short_idempotency_key() -> None:
    with pytest.raises(RecordError, match="16 bytes"):
        sample_submission(idempotency_key=b"\x00" * 15).encode()
    with pytest.raises(RecordError, match="16 bytes"):
        sample_submission(idempotency_key=b"\x00" * 17).encode()


def test_submission_rejects_out_of_range_field_values() -> None:
    with pytest.raises(RecordError):
        sample_submission(input_bytes=1 << 64).encode()
    with pytest.raises(RecordError):
        sample_submission(deployment_id=1 << 32).encode()
    with pytest.raises(RecordError):
        sample_submission(flags=1 << 8).encode()


# ---------------------------------------------------------------------------
# completion
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status", sorted(int(s) for s in CompletionStatus))
def test_every_completion_status_round_trips(status: int) -> None:
    trap = TrapClass.NONE if status == CompletionStatus.SUCCESS else TrapClass.ENGINE
    completion = sample_completion(status=status, trap_class=int(trap))
    record = completion.encode()
    assert len(record) == COMPLETION_BYTES
    assert Completion.decode(record) == completion


def test_completion_amendment_fields_round_trip() -> None:
    """A1 and A2 assigned bytes 104..119; a decoder must see them."""
    completion = sample_completion(
        final_token_id=0xDEADBEEF,
        eos_reason=EosReason.MAX_NEW_TOKENS,
        retired_work=(1 << 64) - 1,
    )
    decoded = Completion.decode(completion.encode())
    assert decoded.final_token_id == 0xDEADBEEF
    assert decoded.eos_reason == EosReason.MAX_NEW_TOKENS
    assert decoded.retired_work == (1 << 64) - 1
    raw = completion.encode()
    assert int.from_bytes(raw[104:108], "little") == 0xDEADBEEF
    assert raw[108] == EosReason.MAX_NEW_TOKENS
    assert raw[109:112] == b"\x00\x00\x00"
    assert int.from_bytes(raw[112:120], "little") == (1 << 64) - 1


def test_completion_rejects_success_with_a_trap_class() -> None:
    with pytest.raises(RecordError, match="SUCCESS"):
        sample_completion(
            status=int(CompletionStatus.SUCCESS), trap_class=int(TrapClass.ENGINE)
        ).encode()


def test_completion_rejects_unknown_status_and_trap_class() -> None:
    record = sample_completion().encode()
    for status in (4, 200, 255):
        with pytest.raises(ValueError):
            sample_completion(status=status).encode()
        with pytest.raises(ValueError):
            Completion.decode(poke(record, COMPLETION, "status", status))
    for trap in (14, 0xFFFF):
        with pytest.raises(ValueError):
            sample_completion(
                status=int(CompletionStatus.FAILED), trap_class=trap
            ).encode()
        with pytest.raises(ValueError):
            Completion.decode(poke(record, COMPLETION, "trap_class", trap))


def test_completion_rejects_bad_magic_major_and_size() -> None:
    record = sample_completion().encode()
    edited = bytearray(record)
    edited[0:4] = b"TA3S"
    with pytest.raises(RecordError, match="magic"):
        Completion.decode(reseal(bytes(edited), COMPLETION))
    with pytest.raises(RecordError, match="major"):
        Completion.decode(poke(record, COMPLETION, "abi_major", 4))
    with pytest.raises(RecordError, match="record_bytes"):
        Completion.decode(poke(record, COMPLETION, "record_bytes", 64))


def test_completion_rejects_a_newer_abi_minor() -> None:
    record = sample_completion().encode()
    with pytest.raises(RecordError):
        Completion.decode(poke(record, COMPLETION, "abi_minor", ABI_MINOR + 1))


@pytest.mark.parametrize("index", [30, 31, 109, 110, 111, 120, 121, 122, 123])
def test_completion_rejects_nonzero_reserved_bytes(index: int) -> None:
    edited = bytearray(sample_completion().encode())
    edited[index] = 0x80
    with pytest.raises(RecordError, match="reserved"):
        Completion.decode(reseal(bytes(edited), COMPLETION))


def test_completion_crc_covers_every_preceding_byte() -> None:
    record = sample_completion(
        status=int(CompletionStatus.FAILED), trap_class=int(TrapClass.ENGINE)
    ).encode()
    reserved = {30, 31, 109, 110, 111, 120, 121, 122, 123}
    for index in range(COMPLETION.crc_offset()):
        if index in reserved:
            continue
        edited = bytearray(record)
        edited[index] ^= 0xFF
        with pytest.raises(ValueError):
            Completion.decode(bytes(edited))


def test_completion_rejects_a_short_idempotency_key() -> None:
    with pytest.raises(RecordError, match="16 bytes"):
        sample_completion(idempotency_key=bytes(15)).encode()


def test_completion_rejects_out_of_range_field_values() -> None:
    with pytest.raises(RecordError):
        sample_completion(retired_work=1 << 64).encode()
    with pytest.raises(RecordError):
        sample_completion(produced_token_count=1 << 32).encode()
    with pytest.raises(RecordError):
        sample_completion(eos_reason=256).encode()
    with pytest.raises(RecordError):
        sample_completion(engine_fault_class=1 << 16).encode()


def test_record_crc_helper_refuses_a_field_outside_the_record() -> None:
    with pytest.raises(ValueError, match="outside the record"):
        record_crc(bytes(16), 14)
    with pytest.raises(ValueError, match="outside the record"):
        record_crc(bytes(16), -1)
