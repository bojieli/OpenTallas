"""Fixed-width microcode for the first real DeepSeek V4 lookup slice.

This ABI is deliberately separate from the exact-integer fixture ABI.  It
encodes only the three operator-complete primitives in the initial real-payload
slice and fails closed on every other instruction or operand arrangement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib


MAGIC = b"OTV4"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBHIIII")
NO_OPERAND = 0xFFFFFFFF

TOKENS = 0
EMBEDDING = 1
HC_HIDDEN = 2
HASH_ROUTES = 3
EMBEDDING_RESOURCE = 0
HASH_ROUTE_RESOURCE = 1


class DeepSeekV4LookupMicrocodeError(ValueError):
    """Raised when lookup-slice microcode is malformed or semantically wrong."""


class Opcode(IntEnum):
    TOKEN_EMBED = 0x10
    HC_EXPAND = 0x11
    HASH_ROUTE = 0x12
    COMPLETE = 0xFF


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    destination: int
    source: int
    resource: int
    immediate: int = 0
    flags: int = 0


def assemble(hc_multiplier: int) -> tuple[Instruction, ...]:
    """Assemble the one legal lookup-slice program."""

    if (
        isinstance(hc_multiplier, bool)
        or not isinstance(hc_multiplier, int)
        or not 1 <= hc_multiplier <= 0xFFFFFFFF
    ):
        raise DeepSeekV4LookupMicrocodeError(
            "hc_multiplier must be an integer in [1, 2^32-1]"
        )
    result = (
        Instruction(
            Opcode.TOKEN_EMBED,
            EMBEDDING,
            TOKENS,
            EMBEDDING_RESOURCE,
        ),
        Instruction(
            Opcode.HC_EXPAND,
            HC_HIDDEN,
            EMBEDDING,
            NO_OPERAND,
            hc_multiplier,
        ),
        Instruction(
            Opcode.HASH_ROUTE,
            HASH_ROUTES,
            TOKENS,
            HASH_ROUTE_RESOURCE,
        ),
        Instruction(
            Opcode.COMPLETE,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
        ),
    )
    verify(result, hc_multiplier)
    return result


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    if not instructions:
        raise DeepSeekV4LookupMicrocodeError("microcode program is empty")
    records: list[bytes] = []
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction.opcode, Opcode):
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has an invalid opcode"
            )
        if instruction.flags != 0:
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        operands = (
            instruction.destination,
            instruction.source,
            instruction.resource,
            instruction.immediate,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 0xFFFFFFFF
            for value in operands
        ):
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has an operand outside uint32"
            )
        records.append(
            RECORD.pack(
                int(instruction.opcode),
                instruction.flags,
                0,
                *operands,
            )
        )
    body = b"".join(records)
    return HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        RECORD.size,
        len(instructions),
        zlib.crc32(body) & 0xFFFFFFFF,
    ) + body


def decode(payload: bytes) -> tuple[Instruction, ...]:
    if len(payload) < HEADER.size:
        raise DeepSeekV4LookupMicrocodeError("microcode is shorter than its header")
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(
        payload
    )
    if magic != MAGIC:
        raise DeepSeekV4LookupMicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4LookupMicrocodeError(
            f"unsupported lookup ABI {major}.{minor}; expected "
            f"{ABI_MAJOR}.{ABI_MINOR}"
        )
    if record_size != RECORD.size:
        raise DeepSeekV4LookupMicrocodeError(
            f"unsupported instruction size {record_size}"
        )
    if count == 0 or count > 1024:
        raise DeepSeekV4LookupMicrocodeError(
            "microcode instruction count is outside the lookup ABI bound"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4LookupMicrocodeError(
            "microcode body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4LookupMicrocodeError("microcode CRC32 mismatch")
    result: list[Instruction] = []
    for index in range(count):
        (
            opcode_raw,
            flags,
            reserved,
            destination,
            source,
            resource,
            immediate,
        ) = RECORD.unpack_from(body, index * RECORD.size)
        if reserved != 0:
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has nonzero reserved bits"
            )
        if flags != 0:
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise DeepSeekV4LookupMicrocodeError(
                f"instruction {index} has unknown opcode 0x{opcode_raw:02x}"
            ) from exc
        result.append(
            Instruction(opcode, destination, source, resource, immediate, flags)
        )
    return tuple(result)


def verify(instructions: tuple[Instruction, ...], hc_multiplier: int) -> None:
    """Require the exact, ordered semantic lowering for this slice."""

    expected = assemble(hc_multiplier) if not instructions else (
        Instruction(
            Opcode.TOKEN_EMBED,
            EMBEDDING,
            TOKENS,
            EMBEDDING_RESOURCE,
        ),
        Instruction(
            Opcode.HC_EXPAND,
            HC_HIDDEN,
            EMBEDDING,
            NO_OPERAND,
            hc_multiplier,
        ),
        Instruction(
            Opcode.HASH_ROUTE,
            HASH_ROUTES,
            TOKENS,
            HASH_ROUTE_RESOURCE,
        ),
        Instruction(
            Opcode.COMPLETE,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
        ),
    )
    if instructions != expected:
        raise DeepSeekV4LookupMicrocodeError(
            "program does not exactly lower TOKEN_EMBED, HC_EXPAND, HASH_ROUTE, "
            "and terminal COMPLETE"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    lines = [f"# OpenTallas DeepSeek V4 lookup ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for pc, instruction in enumerate(instructions):
        lines.append(
            f"{pc:04d} {instruction.opcode.name:<11} "
            f"dst={instruction.destination:#010x} "
            f"src={instruction.source:#010x} "
            f"resource={instruction.resource:#010x} "
            f"imm={instruction.immediate}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "DeepSeekV4LookupMicrocodeError",
    "Instruction",
    "Opcode",
    "assemble",
    "decode",
    "disassemble",
    "encode",
    "verify",
]
