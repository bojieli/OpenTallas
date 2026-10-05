"""Fixed-width microcode for the DeepSeek V4 selected-row FP8 linear slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib


MAGIC = b"OTF8"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBHIIIIII")
NO_OPERAND = 0xFFFFFFFF

INPUT_BF16 = 0
OUTPUT_BF16 = 1
WEIGHT_RESOURCE = 0
SCALE_RESOURCE = 1
ROW_SELECTION_RESOURCE = 2
DENSE_BLOCK_SIZE = 128


class DeepSeekV4FP8LinearMicrocodeError(ValueError):
    """Raised when selected-row FP8 linear microcode is malformed."""


class Opcode(IntEnum):
    FP8_LINEAR_SELECTED_ROWS = 0x20
    COMPLETE = 0xFF


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    destination: int
    source: int
    weight_resource: int
    scale_resource: int
    selection_resource: int
    block_size: int
    flags: int = 0


def assemble() -> tuple[Instruction, ...]:
    result = (
        Instruction(
            Opcode.FP8_LINEAR_SELECTED_ROWS,
            OUTPUT_BF16,
            INPUT_BF16,
            WEIGHT_RESOURCE,
            SCALE_RESOURCE,
            ROW_SELECTION_RESOURCE,
            DENSE_BLOCK_SIZE,
        ),
        Instruction(
            Opcode.COMPLETE,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            0,
        ),
    )
    verify(result)
    return result


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    if not instructions:
        raise DeepSeekV4FP8LinearMicrocodeError("microcode program is empty")
    records = []
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction.opcode, Opcode):
            raise DeepSeekV4FP8LinearMicrocodeError(
                f"instruction {index} has an invalid opcode"
            )
        if instruction.flags != 0:
            raise DeepSeekV4FP8LinearMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        operands = (
            instruction.destination,
            instruction.source,
            instruction.weight_resource,
            instruction.scale_resource,
            instruction.selection_resource,
            instruction.block_size,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 0xFFFFFFFF
            for value in operands
        ):
            raise DeepSeekV4FP8LinearMicrocodeError(
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
        raise DeepSeekV4FP8LinearMicrocodeError(
            "microcode is shorter than its header"
        )
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise DeepSeekV4FP8LinearMicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4FP8LinearMicrocodeError(
            f"unsupported FP8 linear ABI {major}.{minor}; expected "
            f"{ABI_MAJOR}.{ABI_MINOR}"
        )
    if record_size != RECORD.size:
        raise DeepSeekV4FP8LinearMicrocodeError(
            f"unsupported instruction size {record_size}"
        )
    if count == 0 or count > 1024:
        raise DeepSeekV4FP8LinearMicrocodeError(
            "microcode instruction count is outside the FP8 linear ABI bound"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4FP8LinearMicrocodeError(
            "microcode body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4FP8LinearMicrocodeError("microcode CRC32 mismatch")
    result = []
    for index in range(count):
        (
            opcode_raw,
            flags,
            reserved,
            destination,
            source,
            weight_resource,
            scale_resource,
            selection_resource,
            block_size,
        ) = RECORD.unpack_from(body, index * RECORD.size)
        if reserved != 0:
            raise DeepSeekV4FP8LinearMicrocodeError(
                f"instruction {index} has nonzero reserved bits"
            )
        if flags != 0:
            raise DeepSeekV4FP8LinearMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise DeepSeekV4FP8LinearMicrocodeError(
                f"instruction {index} has unknown opcode 0x{opcode_raw:02x}"
            ) from exc
        result.append(
            Instruction(
                opcode,
                destination,
                source,
                weight_resource,
                scale_resource,
                selection_resource,
                block_size,
                flags,
            )
        )
    return tuple(result)


def verify(instructions: tuple[Instruction, ...]) -> None:
    expected = (
        Instruction(
            Opcode.FP8_LINEAR_SELECTED_ROWS,
            OUTPUT_BF16,
            INPUT_BF16,
            WEIGHT_RESOURCE,
            SCALE_RESOURCE,
            ROW_SELECTION_RESOURCE,
            DENSE_BLOCK_SIZE,
        ),
        Instruction(
            Opcode.COMPLETE,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            NO_OPERAND,
            0,
        ),
    )
    if instructions != expected:
        raise DeepSeekV4FP8LinearMicrocodeError(
            "program does not exactly lower selected-row FP8_LINEAR and terminal COMPLETE"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    lines = [f"# OpenTallas DeepSeek V4 FP8 linear ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for pc, instruction in enumerate(instructions):
        lines.append(
            f"{pc:04d} {instruction.opcode.name:<24} "
            f"dst={instruction.destination:#010x} "
            f"src={instruction.source:#010x} "
            f"weight={instruction.weight_resource:#010x} "
            f"scale={instruction.scale_resource:#010x} "
            f"selection={instruction.selection_resource:#010x} "
            f"block={instruction.block_size}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "DENSE_BLOCK_SIZE",
    "DeepSeekV4FP8LinearMicrocodeError",
    "Instruction",
    "Opcode",
    "assemble",
    "decode",
    "disassemble",
    "encode",
    "verify",
]
