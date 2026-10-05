"""Fixed-width, CRC-protected tensor-accelerator command ABI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib
from typing import Iterable


ABI_MAJOR = 1
ABI_MINOR = 0
MAGIC = b"OTTAISA1"
HEADER = struct.Struct("<8sHHII12s")
COMMAND_WITH_CRC = struct.Struct("<BBHIIQQQQIIIII")
COMMAND_PREFIX = struct.Struct("<BBHIIQQQQIIII")
NO_KERNEL = 0xFFFFFFFF

if HEADER.size != 32 or COMMAND_WITH_CRC.size != 64 or COMMAND_PREFIX.size != 60:
    raise RuntimeError("tensor-accelerator ABI structs do not have frozen widths")


class CommandError(ValueError):
    """Raised when a command stream is malformed or fails integrity checks."""


class Opcode(IntEnum):
    DMA_HBM_TO_SRAM = 1
    MATMUL_I8_I8_I32 = 2
    ADD_I32 = 3
    COMPLETE = 255


class Engine(IntEnum):
    CONTROL = 0
    DMA = 1
    TENSOR = 2
    VECTOR = 3


EXPECTED_ENGINE = {
    Opcode.DMA_HBM_TO_SRAM: Engine.DMA,
    Opcode.MATMUL_I8_I8_I32: Engine.TENSOR,
    Opcode.ADD_I32: Engine.VECTOR,
    Opcode.COMPLETE: Engine.CONTROL,
}


@dataclass(frozen=True)
class Command:
    index: int
    opcode: Opcode
    engine: Engine
    flags: int = 0
    kernel_index: int = NO_KERNEL
    source0: int = 0
    source1: int = 0
    destination: int = 0
    auxiliary: int = 0
    size0: int = 0
    size1: int = 0
    size2: int = 0
    size3: int = 0

    def to_dict(self) -> dict[str, int | str]:
        return {
            "auxiliary": self.auxiliary,
            "destination": self.destination,
            "engine": self.engine.name,
            "flags": self.flags,
            "index": self.index,
            "kernel_index": self.kernel_index,
            "opcode": self.opcode.name,
            "size0": self.size0,
            "size1": self.size1,
            "size2": self.size2,
            "size3": self.size3,
            "source0": self.source0,
            "source1": self.source1,
        }


def _validate_command(command: Command, expected_index: int) -> None:
    if command.index != expected_index:
        raise CommandError("command indices must be contiguous and ordered")
    if command.engine != EXPECTED_ENGINE[command.opcode]:
        raise CommandError(
            f"command {command.index} engine does not match {command.opcode.name}"
        )
    if command.flags != 0:
        raise CommandError(f"command {command.index} has unsupported flags")
    fields = (
        command.index,
        command.kernel_index,
        command.source0,
        command.source1,
        command.destination,
        command.auxiliary,
        command.size0,
        command.size1,
        command.size2,
        command.size3,
    )
    limits = (
        0xFFFFFFFF,
        0xFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
        0xFFFFFFFFFFFFFFFF,
        0xFFFFFFFF,
        0xFFFFFFFF,
        0xFFFFFFFF,
        0xFFFFFFFF,
    )
    if any(value < 0 or value > limit for value, limit in zip(fields, limits, strict=True)):
        raise CommandError(f"command {command.index} has an out-of-range field")


def encode(commands: Iterable[Command]) -> bytes:
    parsed = tuple(commands)
    if not parsed:
        raise CommandError("command stream must be non-empty")
    payload_parts: list[bytes] = []
    for expected_index, command in enumerate(parsed):
        _validate_command(command, expected_index)
        prefix = COMMAND_PREFIX.pack(
            int(command.opcode),
            int(command.engine),
            command.flags,
            command.index,
            command.kernel_index,
            command.source0,
            command.source1,
            command.destination,
            command.auxiliary,
            command.size0,
            command.size1,
            command.size2,
            command.size3,
        )
        crc = zlib.crc32(prefix) & 0xFFFFFFFF
        payload_parts.append(prefix + struct.pack("<I", crc))
    payload = b"".join(payload_parts)
    header = HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        len(parsed),
        zlib.crc32(payload) & 0xFFFFFFFF,
        bytes(12),
    )
    return header + payload


def decode(payload: bytes) -> tuple[Command, ...]:
    if len(payload) < HEADER.size:
        raise CommandError("command stream is shorter than the header")
    magic, major, minor, count, expected_crc, reserved = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise CommandError("command stream magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise CommandError("unsupported command ABI")
    if reserved != bytes(12):
        raise CommandError("command header reserved bits are nonzero")
    expected_size = HEADER.size + count * COMMAND_WITH_CRC.size
    if len(payload) != expected_size:
        raise CommandError("command stream size differs from header count")
    command_payload = payload[HEADER.size:]
    if zlib.crc32(command_payload) & 0xFFFFFFFF != expected_crc:
        raise CommandError("command stream payload CRC32 mismatch")
    result: list[Command] = []
    for index in range(count):
        offset = HEADER.size + index * COMMAND_WITH_CRC.size
        fields = COMMAND_WITH_CRC.unpack_from(payload, offset)
        prefix = payload[offset : offset + COMMAND_PREFIX.size]
        if zlib.crc32(prefix) & 0xFFFFFFFF != fields[-1]:
            raise CommandError(f"command {index} CRC32 mismatch")
        try:
            opcode = Opcode(fields[0])
            engine = Engine(fields[1])
        except ValueError as exc:
            raise CommandError(f"command {index} has an unknown opcode or engine") from exc
        command = Command(
            index=fields[3],
            opcode=opcode,
            engine=engine,
            flags=fields[2],
            kernel_index=fields[4],
            source0=fields[5],
            source1=fields[6],
            destination=fields[7],
            auxiliary=fields[8],
            size0=fields[9],
            size1=fields[10],
            size2=fields[11],
            size3=fields[12],
        )
        _validate_command(command, index)
        result.append(command)
    if result[-1].opcode != Opcode.COMPLETE:
        raise CommandError("command stream lacks a terminal COMPLETE")
    if any(command.opcode == Opcode.COMPLETE for command in result[:-1]):
        raise CommandError("COMPLETE may appear only at the end")
    return tuple(result)


def disassemble(commands: Iterable[Command]) -> str:
    lines = [
        f"OTTA-ISA {ABI_MAJOR}.{ABI_MINOR}",
        "# index opcode engine kernel src0 src1 dst aux size0 size1 size2 size3",
    ]
    for command in commands:
        lines.append(
            f"{command.index:04d} {command.opcode.name} {command.engine.name} "
            f"{command.kernel_index} 0x{command.source0:016x} "
            f"0x{command.source1:016x} 0x{command.destination:016x} "
            f"0x{command.auxiliary:016x} {command.size0} {command.size1} "
            f"{command.size2} {command.size3}"
        )
    return "\n".join(lines) + "\n"
