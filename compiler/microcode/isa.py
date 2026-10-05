"""Fixed-width, fail-closed microcode for the executable compiler fixture."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib

from compiler.ir.model import Model


MAGIC = b"OTMC"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBHIII")
NO_TENSOR = 0xFFFFFFFF


class MicrocodeError(ValueError):
    """Raised when microcode is malformed or differs from semantic IR."""


class Opcode(IntEnum):
    ROM_MATMUL = 0x10
    VECTOR_ADD = 0x20
    COMPLETE = 0xFF


OPCODE_FOR_KIND = {
    "ROM_MATMUL": Opcode.ROM_MATMUL,
    "VECTOR_ADD": Opcode.VECTOR_ADD,
}


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    destination: int
    source0: int
    source1: int
    flags: int = 0


def assemble(model: Model) -> tuple[Instruction, ...]:
    indices = {tensor.tensor_id: tensor.index for tensor in model.tensors}
    instructions = [
        Instruction(
            opcode=OPCODE_FOR_KIND[operation.kind],
            destination=indices[operation.output],
            source0=indices[operation.inputs[0]],
            source1=indices[operation.inputs[1]],
        )
        for operation in model.operations
    ]
    instructions.append(
        Instruction(
            opcode=Opcode.COMPLETE,
            destination=indices[model.outputs[0]],
            source0=NO_TENSOR,
            source1=NO_TENSOR,
        )
    )
    result = tuple(instructions)
    verify(result, model)
    return result


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    if not instructions:
        raise MicrocodeError("microcode program is empty")
    records: list[bytes] = []
    for index, instruction in enumerate(instructions):
        if instruction.flags != 0:
            raise MicrocodeError(f"instruction {index} has unsupported flags")
        for label, value in (
            ("destination", instruction.destination),
            ("source0", instruction.source0),
            ("source1", instruction.source1),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
                raise MicrocodeError(f"instruction {index} {label} is outside uint32")
        records.append(
            RECORD.pack(
                int(instruction.opcode),
                instruction.flags,
                0,
                instruction.destination,
                instruction.source0,
                instruction.source1,
            )
        )
    body = b"".join(records)
    header = HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        RECORD.size,
        len(instructions),
        zlib.crc32(body) & 0xFFFFFFFF,
    )
    return header + body


def decode(payload: bytes) -> tuple[Instruction, ...]:
    if len(payload) < HEADER.size:
        raise MicrocodeError("microcode is shorter than its header")
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise MicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise MicrocodeError(
            f"unsupported microcode ABI {major}.{minor}; expected {ABI_MAJOR}.{ABI_MINOR}"
        )
    if record_size != RECORD.size:
        raise MicrocodeError(f"unsupported instruction size {record_size}")
    if count == 0 or count > 1_000_000:
        raise MicrocodeError("microcode instruction count is outside the v1 bound")
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise MicrocodeError("microcode body length differs from its header")
    actual_crc = zlib.crc32(body) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        raise MicrocodeError("microcode CRC32 mismatch")
    instructions: list[Instruction] = []
    for index in range(count):
        opcode_raw, flags, reserved, destination, source0, source1 = RECORD.unpack_from(
            body, index * RECORD.size
        )
        if reserved != 0:
            raise MicrocodeError(f"instruction {index} has nonzero reserved bits")
        if flags != 0:
            raise MicrocodeError(f"instruction {index} has unsupported flags")
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise MicrocodeError(
                f"instruction {index} has unknown opcode 0x{opcode_raw:02x}"
            ) from exc
        instructions.append(Instruction(opcode, destination, source0, source1, flags))
    return tuple(instructions)


def verify(instructions: tuple[Instruction, ...], model: Model) -> None:
    if len(instructions) != len(model.operations) + 1:
        raise MicrocodeError("program length does not match semantic operation coverage")
    indices = {tensor.tensor_id: tensor.index for tensor in model.tensors}
    for index, operation in enumerate(model.operations):
        instruction = instructions[index]
        expected = (
            OPCODE_FOR_KIND[operation.kind],
            indices[operation.output],
            indices[operation.inputs[0]],
            indices[operation.inputs[1]],
        )
        actual = (
            instruction.opcode,
            instruction.destination,
            instruction.source0,
            instruction.source1,
        )
        if actual != expected or instruction.flags != 0:
            raise MicrocodeError(
                f"instruction {index} does not exactly lower operation {operation.operation_id!r}"
            )
    complete = instructions[-1]
    if complete != Instruction(
        Opcode.COMPLETE,
        indices[model.outputs[0]],
        NO_TENSOR,
        NO_TENSOR,
    ):
        raise MicrocodeError("program lacks one exact terminal COMPLETE instruction")
    if any(instruction.opcode == Opcode.COMPLETE for instruction in instructions[:-1]):
        raise MicrocodeError("COMPLETE may appear only as the terminal instruction")


def disassemble(instructions: tuple[Instruction, ...], model: Model) -> str:
    names = {tensor.index: tensor.tensor_id for tensor in model.tensors}

    def operand(value: int) -> str:
        if value == NO_TENSOR:
            return "-"
        return f"{value}:{names.get(value, '?')}"

    lines = [f"# OpenTallas microcode ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for pc, instruction in enumerate(instructions):
        lines.append(
            f"{pc:04d} {instruction.opcode.name:<11} "
            f"dst={operand(instruction.destination)} "
            f"src0={operand(instruction.source0)} "
            f"src1={operand(instruction.source1)}"
        )
    return "\n".join(lines) + "\n"
