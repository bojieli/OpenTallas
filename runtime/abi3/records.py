"""ABI 3.0 fixed-record codecs: program header, instruction, host queues.

Layouts are transcribed directly from ``TA-ABI3-WIRE-1`` sections 2, 3, 6 and 7.
Two amendments made when the contract was frozen at ``TA-A3-ARCH-0`` are marked
``AMENDMENT`` below; both assign previously reserved bytes so that ADR-003
section 6.3 requirements have a wire representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Final, Iterator, Sequence

from .constants import (
    ABI_MAJOR,
    ABI_MINOR,
    COMPLETION_BYTES,
    COMPLETION_MAGIC,
    INSTRUCTION_BYTES,
    INSTRUCTION_FLAG_MASK,
    NO_ID,
    PROGRAM_HEADER_BYTES,
    PROGRAM_MAGIC,
    SUBMISSION_BYTES,
    SUBMISSION_MAGIC,
    SUBOPCODES,
    CompletionStatus,
    HostOpcode,
    InstructionFlag,
    Major,
    TrapClass,
)
from .crc import crc32c, record_crc, sha256
from .layout import Field, Layout, RecordError

# ---------------------------------------------------------------------------
# Section 2 -- device program header (256 bytes)
# ---------------------------------------------------------------------------
PROGRAM_HEADER = Layout(
    "program_header",
    PROGRAM_HEADER_BYTES,
    [
        Field("magic", 0, 8, "magic", PROGRAM_MAGIC),
        Field("abi_major", 8, 1),
        Field("abi_minor", 9, 1),
        Field("header_bytes", 10, 2),
        Field("instruction_bytes", 12, 2),
        Field("flags", 14, 2),
        Field("instruction_count", 16, 4),
        Field("entrypoint_count", 20, 4),
        Field("required_features", 24, 32, "bytes"),
        Field("deployment_digest", 56, 32, "bytes"),
        Field("descriptor_table_digest", 88, 32, "bytes"),
        Field("topology_digest", 120, 32, "bytes"),
        Field("body_digest", 152, 32, "bytes"),
        Field("max_retired_work", 184, 8),
        Field("watchdog_class", 192, 4),
        Field("entrypoint_table_descriptor", 196, 4),
        Field("signature_metadata_descriptor", 200, 4),
        Field("reserved", 204, 48, "reserved"),
        Field("header_crc", 252, 4),
    ],
    crc_field="header_crc",
)

# ---------------------------------------------------------------------------
# Section 3 -- device instruction (32 bytes)
# ---------------------------------------------------------------------------
INSTRUCTION = Layout(
    "instruction",
    INSTRUCTION_BYTES,
    [
        Field("major", 0, 1),
        Field("sub", 1, 1),
        Field("flags", 2, 2),
        Field("predicate_id", 4, 4),
        Field("descriptor_id", 8, 4),
        Field("wait_set_id", 12, 4),
        Field("signal_event_id", 16, 4),
        Field("control_id", 20, 4),
        Field("source_operation_id", 24, 4),
        Field("instruction_crc", 28, 4),
    ],
    crc_field="instruction_crc",
)

# ---------------------------------------------------------------------------
# Section 6 -- host submission record (128 bytes)
# ---------------------------------------------------------------------------
SUBMISSION = Layout(
    "submission",
    SUBMISSION_BYTES,
    [
        Field("magic", 0, 4, "magic", SUBMISSION_MAGIC),
        Field("abi_major", 4, 1),
        Field("abi_minor", 5, 1),
        Field("host_opcode", 6, 1),
        Field("flags", 7, 1),
        Field("record_bytes", 8, 2),
        Field("reserved_0", 10, 2, "reserved"),
        Field("deployment_id", 12, 4),
        Field("deployment_generation", 16, 4),
        Field("session_id", 20, 4),
        Field("session_generation", 24, 4),
        Field("request_descriptor_id", 28, 4),
        Field("transaction_id", 32, 8),
        Field("idempotency_key", 40, 16, "bytes"),
        Field("input_window_id", 56, 4),
        Field("output_window_id", 60, 4),
        Field("input_offset", 64, 8),
        Field("input_bytes", 72, 8),
        Field("output_offset", 80, 8),
        Field("output_capacity_bytes", 88, 8),
        Field("entrypoint_id", 96, 4),
        Field("generation_policy_id", 100, 4),
        Field("watchdog_class", 104, 4),
        Field("reserved_1", 108, 4, "reserved"),
        Field("deadline_cycles", 112, 8),
        Field("reserved_2", 120, 4, "reserved"),
        Field("record_crc", 124, 4),
    ],
    crc_field="record_crc",
)

# ---------------------------------------------------------------------------
# Section 7 -- host completion record (128 bytes)
# ---------------------------------------------------------------------------
# AMENDMENT TA-A3-ARCH-0-A1: bytes 104..111 of the former 20-byte reserved span
# carry the final selected token and the EOS reason required by ADR-003 6.3.
# AMENDMENT TA-A3-ARCH-0-A2: bytes 112..119 carry retired work so that a
# completion can be checked against the header's proved work bound.
COMPLETION = Layout(
    "completion",
    COMPLETION_BYTES,
    [
        Field("magic", 0, 4, "magic", COMPLETION_MAGIC),
        Field("abi_major", 4, 1),
        Field("abi_minor", 5, 1),
        Field("status", 6, 1),
        Field("flags", 7, 1),
        Field("record_bytes", 8, 2),
        Field("trap_class", 10, 2),
        Field("deployment_id", 12, 4),
        Field("deployment_generation", 16, 4),
        Field("session_id", 20, 4),
        Field("session_generation", 24, 4),
        Field("engine_fault_class", 28, 2),
        Field("reserved_0", 30, 2, "reserved"),
        Field("transaction_id", 32, 8),
        Field("committed_token_position", 40, 4),
        Field("produced_token_count", 44, 4),
        Field("committed_state_generation", 48, 8),
        Field("output_bytes_written", 56, 8),
        Field("first_fault_instruction", 64, 4),
        Field("fault_descriptor_id", 68, 4),
        Field("counter_snapshot_id", 72, 4),
        Field("trace_id", 76, 4),
        Field("completion_timestamp", 80, 8),
        Field("idempotency_key", 88, 16, "bytes"),
        Field("final_token_id", 104, 4),
        Field("eos_reason", 108, 1),
        Field("reserved_1", 109, 3, "reserved"),
        Field("retired_work", 112, 8),
        Field("reserved_2", 120, 4, "reserved"),
        Field("record_crc", 124, 4),
    ],
    crc_field="record_crc",
)


class EosReason:
    """Values for the amended completion ``eos_reason`` byte."""

    NONE: Final = 0
    OFFICIAL_EOS: Final = 1
    MAX_NEW_TOKENS: Final = 2
    TERMINATED_BY_TRAP: Final = 3
    HOST_BOUND: Final = 4


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------
def _seal(layout: Layout, values: dict[str, Any]) -> bytes:
    """Encode ``values`` and stamp the record CRC in place."""
    values = dict(values)
    values[layout.crc_field] = 0  # type: ignore[index]
    record = layout.encode(values)
    crc = record_crc(bytes(record), layout.crc_offset())
    offset = layout.crc_offset()
    record[offset : offset + 4] = crc.to_bytes(4, "little")
    return bytes(record)


def _open(layout: Layout, record: bytes) -> dict[str, Any]:
    """Decode ``record`` after verifying its CRC, failing closed on mismatch."""
    values = layout.decode(record)
    expected = record_crc(record, layout.crc_offset())
    actual = values[layout.crc_field]  # type: ignore[index]
    if actual != expected:
        raise RecordError(
            f"{layout.name}: CRC32C mismatch (record {actual:#010x}, "
            f"computed {expected:#010x})"
        )
    return values


@dataclass(slots=True)
class Instruction:
    """One decoded 32-byte device instruction."""

    major: int
    sub: int
    flags: int = 0
    predicate_id: int = NO_ID
    descriptor_id: int = NO_ID
    wait_set_id: int = NO_ID
    signal_event_id: int = NO_ID
    control_id: int = NO_ID
    source_operation_id: int = NO_ID

    def validate(self) -> None:
        """Structural legality independent of any deployment context."""
        try:
            family = Major(self.major)
        except ValueError:
            raise RecordError(f"unknown major opcode {self.major:#04x}") from None
        try:
            SUBOPCODES[family](self.sub)
        except ValueError:
            raise RecordError(
                f"subopcode {self.sub:#04x} is not legal for {family.name}"
            ) from None
        if self.flags & ~INSTRUCTION_FLAG_MASK:
            raise RecordError(
                f"instruction flags {self.flags:#06x} set reserved bits 8..15"
            )
        invert = bool(self.flags & InstructionFlag.PREDICATE_INVERT)
        predicated = bool(self.flags & InstructionFlag.PREDICATED)
        if invert and not predicated:
            raise RecordError("PREDICATE_INVERT set without PREDICATED")
        if predicated and self.predicate_id == NO_ID:
            raise RecordError("PREDICATED set but predicate ID is NO_ID")
        if not predicated and self.predicate_id != NO_ID:
            raise RecordError("predicate ID supplied without the PREDICATED flag")

    @property
    def mnemonic(self) -> str:
        family = Major(self.major)
        return f"{family.name}.{SUBOPCODES[family](self.sub).name}"

    def encode(self) -> bytes:
        self.validate()
        return _seal(
            INSTRUCTION,
            {
                "major": self.major,
                "sub": self.sub,
                "flags": self.flags,
                "predicate_id": self.predicate_id,
                "descriptor_id": self.descriptor_id,
                "wait_set_id": self.wait_set_id,
                "signal_event_id": self.signal_event_id,
                "control_id": self.control_id,
                "source_operation_id": self.source_operation_id,
            },
        )

    @classmethod
    def decode(cls, record: bytes) -> "Instruction":
        values = _open(INSTRUCTION, record)
        values.pop("instruction_crc")
        instruction = cls(**values)
        instruction.validate()
        return instruction

    def __str__(self) -> str:  # pragma: no cover - diagnostics only
        parts = [self.mnemonic]
        for name in ("descriptor_id", "control_id", "wait_set_id", "signal_event_id"):
            value = getattr(self, name)
            if value != NO_ID:
                parts.append(f"{name}={value}")
        if self.flags:
            parts.append(f"flags={InstructionFlag(self.flags)!r}")
        return " ".join(parts)


def encode_body(instructions: Sequence[Instruction]) -> bytes:
    """Encode an instruction sequence into the authenticated program body."""
    return b"".join(instruction.encode() for instruction in instructions)


def decode_body(body: bytes) -> list[Instruction]:
    """Decode a program body, failing closed on length or CRC errors."""
    if len(body) % INSTRUCTION_BYTES:
        raise RecordError(
            f"program body is {len(body)} bytes, not a multiple of "
            f"{INSTRUCTION_BYTES}"
        )
    return [
        Instruction.decode(body[offset : offset + INSTRUCTION_BYTES])
        for offset in range(0, len(body), INSTRUCTION_BYTES)
    ]


def iter_body(body: bytes) -> Iterator[bytes]:
    for offset in range(0, len(body), INSTRUCTION_BYTES):
        yield body[offset : offset + INSTRUCTION_BYTES]


@dataclass(slots=True)
class ProgramHeader:
    """The 256-byte authenticated device-program header."""

    instruction_count: int
    entrypoint_count: int
    required_features: bytes
    deployment_digest: bytes
    descriptor_table_digest: bytes
    topology_digest: bytes
    body_digest: bytes
    max_retired_work: int
    watchdog_class: int
    entrypoint_table_descriptor: int
    signature_metadata_descriptor: int = NO_ID
    flags: int = 0
    abi_major: int = ABI_MAJOR
    abi_minor: int = ABI_MINOR

    def encode(self) -> bytes:
        return _seal(
            PROGRAM_HEADER,
            {
                "abi_major": self.abi_major,
                "abi_minor": self.abi_minor,
                "header_bytes": PROGRAM_HEADER_BYTES,
                "instruction_bytes": INSTRUCTION_BYTES,
                "flags": self.flags,
                "instruction_count": self.instruction_count,
                "entrypoint_count": self.entrypoint_count,
                "required_features": self.required_features,
                "deployment_digest": self.deployment_digest,
                "descriptor_table_digest": self.descriptor_table_digest,
                "topology_digest": self.topology_digest,
                "body_digest": self.body_digest,
                "max_retired_work": self.max_retired_work,
                "watchdog_class": self.watchdog_class,
                "entrypoint_table_descriptor": self.entrypoint_table_descriptor,
                "signature_metadata_descriptor": self.signature_metadata_descriptor,
            },
        )

    @classmethod
    def decode(cls, record: bytes) -> "ProgramHeader":
        values = _open(PROGRAM_HEADER, record)
        if values["abi_major"] != ABI_MAJOR:
            raise RecordError(
                f"unsupported ABI major version {values['abi_major']}"
            )
        if values["abi_minor"] > ABI_MINOR:
            raise RecordError(
                f"program requires ABI minor {values['abi_minor']}, "
                f"implementation provides {ABI_MINOR}"
            )
        if values["header_bytes"] != PROGRAM_HEADER_BYTES:
            raise RecordError("header_bytes is not 256")
        if values["instruction_bytes"] != INSTRUCTION_BYTES:
            raise RecordError("instruction_bytes is not 32")
        if values["flags"]:
            raise RecordError("all version-3.0 header flag bits are reserved")
        if values["instruction_count"] == 0:
            raise RecordError("instruction_count must be nonzero")
        if values["entrypoint_count"] == 0:
            raise RecordError("entrypoint_count must be nonzero")
        for drop in ("header_bytes", "instruction_bytes", "header_crc"):
            values.pop(drop)
        return cls(**values)


def build_program(
    instructions: Sequence[Instruction],
    *,
    entrypoint_count: int,
    required_features: bytes,
    deployment_digest: bytes,
    descriptor_table_digest: bytes,
    topology_digest: bytes,
    max_retired_work: int,
    watchdog_class: int,
    entrypoint_table_descriptor: int,
    signature_metadata_descriptor: int = NO_ID,
) -> bytes:
    """Assemble a complete 256-byte-aligned device program image."""
    body = encode_body(instructions)
    header = ProgramHeader(
        instruction_count=len(instructions),
        entrypoint_count=entrypoint_count,
        required_features=required_features,
        deployment_digest=deployment_digest,
        descriptor_table_digest=descriptor_table_digest,
        topology_digest=topology_digest,
        body_digest=sha256(body),
        max_retired_work=max_retired_work,
        watchdog_class=watchdog_class,
        entrypoint_table_descriptor=entrypoint_table_descriptor,
        signature_metadata_descriptor=signature_metadata_descriptor,
    )
    return header.encode() + body


def split_program(image: bytes) -> tuple[ProgramHeader, bytes]:
    """Split a program image, verifying header CRC, length and body digest."""
    if len(image) < PROGRAM_HEADER_BYTES:
        raise RecordError("program image is shorter than its header")
    header = ProgramHeader.decode(image[:PROGRAM_HEADER_BYTES])
    body = image[PROGRAM_HEADER_BYTES:]
    expected = header.instruction_count * INSTRUCTION_BYTES
    if len(body) != expected:
        raise RecordError(
            f"program body is {len(body)} bytes, header declares {expected}"
        )
    if sha256(body) != header.body_digest:
        raise RecordError("program body SHA-256 does not match the header")
    return header, body


@dataclass(slots=True)
class Submission:
    """A 128-byte host submission-ring record."""

    host_opcode: int
    deployment_id: int = NO_ID
    deployment_generation: int = 0
    session_id: int = NO_ID
    session_generation: int = 0
    request_descriptor_id: int = NO_ID
    transaction_id: int = 0
    idempotency_key: bytes = b"\x00" * 16
    input_window_id: int = NO_ID
    output_window_id: int = NO_ID
    input_offset: int = 0
    input_bytes: int = 0
    output_offset: int = 0
    output_capacity_bytes: int = 0
    entrypoint_id: int = NO_ID
    generation_policy_id: int = NO_ID
    watchdog_class: int = 0
    deadline_cycles: int = 0
    flags: int = 0

    def encode(self) -> bytes:
        HostOpcode(self.host_opcode)  # fail closed on an unknown host opcode
        if len(self.idempotency_key) != 16:
            raise RecordError("idempotency key must be 16 bytes")
        return _seal(
            SUBMISSION,
            {
                "abi_major": ABI_MAJOR,
                "abi_minor": ABI_MINOR,
                "host_opcode": self.host_opcode,
                "flags": self.flags,
                "record_bytes": SUBMISSION_BYTES,
                "deployment_id": self.deployment_id,
                "deployment_generation": self.deployment_generation,
                "session_id": self.session_id,
                "session_generation": self.session_generation,
                "request_descriptor_id": self.request_descriptor_id,
                "transaction_id": self.transaction_id,
                "idempotency_key": self.idempotency_key,
                "input_window_id": self.input_window_id,
                "output_window_id": self.output_window_id,
                "input_offset": self.input_offset,
                "input_bytes": self.input_bytes,
                "output_offset": self.output_offset,
                "output_capacity_bytes": self.output_capacity_bytes,
                "entrypoint_id": self.entrypoint_id,
                "generation_policy_id": self.generation_policy_id,
                "watchdog_class": self.watchdog_class,
                "deadline_cycles": self.deadline_cycles,
            },
        )

    @classmethod
    def decode(cls, record: bytes) -> "Submission":
        values = _open(SUBMISSION, record)
        if values["abi_major"] != ABI_MAJOR:
            raise RecordError("unsupported submission ABI major version")
        if values["abi_minor"] > ABI_MINOR:
            raise RecordError("unsupported submission ABI minor version")
        if values["record_bytes"] != SUBMISSION_BYTES:
            raise RecordError("submission record_bytes is not 128")
        HostOpcode(values["host_opcode"])
        for drop in ("abi_major", "abi_minor", "record_bytes", "record_crc"):
            values.pop(drop)
        return cls(**values)


@dataclass(slots=True)
class Completion:
    """A 128-byte host completion-ring record."""

    status: int
    transaction_id: int
    deployment_id: int = NO_ID
    deployment_generation: int = 0
    session_id: int = NO_ID
    session_generation: int = 0
    trap_class: int = TrapClass.NONE
    engine_fault_class: int = 0
    committed_token_position: int = 0
    produced_token_count: int = 0
    committed_state_generation: int = 0
    output_bytes_written: int = 0
    first_fault_instruction: int = NO_ID
    fault_descriptor_id: int = NO_ID
    counter_snapshot_id: int = NO_ID
    trace_id: int = NO_ID
    completion_timestamp: int = 0
    idempotency_key: bytes = b"\x00" * 16
    final_token_id: int = NO_ID
    eos_reason: int = EosReason.NONE
    retired_work: int = 0
    flags: int = 0

    def encode(self) -> bytes:
        CompletionStatus(self.status)
        TrapClass(self.trap_class)
        if len(self.idempotency_key) != 16:
            raise RecordError("idempotency key must be 16 bytes")
        if self.status == CompletionStatus.SUCCESS and self.trap_class != TrapClass.NONE:
            raise RecordError("SUCCESS completion cannot carry a trap class")
        return _seal(
            COMPLETION,
            {
                "abi_major": ABI_MAJOR,
                "abi_minor": ABI_MINOR,
                "status": self.status,
                "flags": self.flags,
                "record_bytes": COMPLETION_BYTES,
                "trap_class": self.trap_class,
                "deployment_id": self.deployment_id,
                "deployment_generation": self.deployment_generation,
                "session_id": self.session_id,
                "session_generation": self.session_generation,
                "engine_fault_class": self.engine_fault_class,
                "transaction_id": self.transaction_id,
                "committed_token_position": self.committed_token_position,
                "produced_token_count": self.produced_token_count,
                "committed_state_generation": self.committed_state_generation,
                "output_bytes_written": self.output_bytes_written,
                "first_fault_instruction": self.first_fault_instruction,
                "fault_descriptor_id": self.fault_descriptor_id,
                "counter_snapshot_id": self.counter_snapshot_id,
                "trace_id": self.trace_id,
                "completion_timestamp": self.completion_timestamp,
                "idempotency_key": self.idempotency_key,
                "final_token_id": self.final_token_id,
                "eos_reason": self.eos_reason,
                "retired_work": self.retired_work,
            },
        )

    @classmethod
    def decode(cls, record: bytes) -> "Completion":
        values = _open(COMPLETION, record)
        if values["abi_major"] != ABI_MAJOR:
            raise RecordError("unsupported completion ABI major version")
        if values["record_bytes"] != COMPLETION_BYTES:
            raise RecordError("completion record_bytes is not 128")
        CompletionStatus(values["status"])
        TrapClass(values["trap_class"])
        for drop in ("abi_major", "abi_minor", "record_bytes", "record_crc"):
            values.pop(drop)
        return cls(**values)
