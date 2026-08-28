"""Production command ABI v2 for tiled HBM/SRAM execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib
from typing import Iterable


ABI_MAJOR = 2
ABI_MINOR = 0
MAGIC = b"OTTAISA2"
HEADER = struct.Struct("<8sHHII12s")
COMMAND_WITH_CRC = struct.Struct("<BBHIIQQQQIIIII")
COMMAND_PREFIX = struct.Struct("<BBHIIQQQQIIII")
NO_KERNEL = 0xFFFFFFFF
MATMUL_INIT = 1 << 0
MATMUL_FINAL = 1 << 1

if HEADER.size != 32 or COMMAND_WITH_CRC.size != 64 or COMMAND_PREFIX.size != 60:
    raise RuntimeError("tensor-accelerator production ABI widths differ")


class ProductionCommandError(ValueError):
    """Raised when a v2 command stream is malformed or inconsistent."""


class Opcode(IntEnum):
    DMA_HBM_TO_SRAM = 0x01
    MATMUL_BF16_TILE = 0x10
    COMPLETE = 0xFF


class Engine(IntEnum):
    CONTROL = 0
    DMA = 1
    TENSOR = 2


EXPECTED_ENGINE = {
    Opcode.DMA_HBM_TO_SRAM: Engine.DMA,
    Opcode.MATMUL_BF16_TILE: Engine.TENSOR,
    Opcode.COMPLETE: Engine.CONTROL,
}


@dataclass(frozen=True)
class ProductionCommand:
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


def _all_zero(command: ProductionCommand) -> bool:
    return all(
        value == 0
        for value in (
            command.flags,
            command.source0,
            command.source1,
            command.destination,
            command.auxiliary,
            command.size0,
            command.size1,
            command.size2,
            command.size3,
        )
    )


def _validate_command(command: ProductionCommand, expected_index: int) -> None:
    if not isinstance(command, ProductionCommand):
        raise ProductionCommandError("command stream contains a non-command value")
    if not isinstance(command.opcode, Opcode) or not isinstance(command.engine, Engine):
        raise ProductionCommandError(
            f"command {expected_index} opcode and engine must use ABI enums"
        )
    if command.index != expected_index:
        raise ProductionCommandError("command indices must be contiguous and ordered")
    if command.engine != EXPECTED_ENGINE.get(command.opcode):
        raise ProductionCommandError(
            f"command {command.index} engine differs from {command.opcode.name}"
        )
    named_fields = (
        ("flags", command.flags, 0xFFFF),
        ("index", command.index, 0xFFFFFFFF),
        ("kernel_index", command.kernel_index, 0xFFFFFFFF),
        ("source0", command.source0, 0xFFFFFFFFFFFFFFFF),
        ("source1", command.source1, 0xFFFFFFFFFFFFFFFF),
        ("destination", command.destination, 0xFFFFFFFFFFFFFFFF),
        ("auxiliary", command.auxiliary, 0xFFFFFFFFFFFFFFFF),
        ("size0", command.size0, 0xFFFFFFFF),
        ("size1", command.size1, 0xFFFFFFFF),
        ("size2", command.size2, 0xFFFFFFFF),
        ("size3", command.size3, 0xFFFFFFFF),
    )
    for name, value, limit in named_fields:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > limit
        ):
            raise ProductionCommandError(
                f"command {command.index} field {name} is outside its ABI width"
            )
    if command.opcode == Opcode.DMA_HBM_TO_SRAM:
        if (
            command.flags
            or command.kernel_index == NO_KERNEL
            or not command.size0
            or command.source1
            or command.auxiliary
            or command.size1
            or command.size2
            or command.size3
        ):
            raise ProductionCommandError(
                f"command {command.index} has illegal DMA fields"
            )
    elif command.opcode == Opcode.MATMUL_BF16_TILE:
        if (
            command.flags & ~(MATMUL_INIT | MATMUL_FINAL)
            or command.kernel_index == NO_KERNEL
            or not command.size0
            or not command.size1
            or not command.size2
            or command.size3
        ):
            raise ProductionCommandError(
                f"command {command.index} has illegal BF16 MATMUL fields"
            )
    elif command.opcode == Opcode.COMPLETE:
        if command.kernel_index != NO_KERNEL or not _all_zero(command):
            raise ProductionCommandError(
                f"command {command.index} has illegal COMPLETE fields"
            )


def _validate_stream(commands: tuple[ProductionCommand, ...]) -> None:
    if not commands:
        raise ProductionCommandError("command stream must be nonempty")
    if len(commands) > 0xFFFFFFFF:
        raise ProductionCommandError("command stream exceeds the ABI count field")
    for expected_index, command in enumerate(commands):
        _validate_command(command, expected_index)
    if commands[-1].opcode != Opcode.COMPLETE or any(
        command.opcode == Opcode.COMPLETE for command in commands[:-1]
    ):
        raise ProductionCommandError("COMPLETE must appear exactly once at the end")


def encode(commands: Iterable[ProductionCommand]) -> bytes:
    parsed = tuple(commands)
    _validate_stream(parsed)
    records: list[bytes] = []
    for command in parsed:
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
        records.append(prefix + struct.pack("<I", zlib.crc32(prefix) & 0xFFFFFFFF))
    body = b"".join(records)
    return HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        len(parsed),
        zlib.crc32(body) & 0xFFFFFFFF,
        bytes(12),
    ) + body


def decode(payload: bytes) -> tuple[ProductionCommand, ...]:
    if not isinstance(payload, bytes):
        raise ProductionCommandError("command stream must be immutable bytes")
    if len(payload) < HEADER.size:
        raise ProductionCommandError("command stream is shorter than its header")
    magic, major, minor, count, expected_crc, reserved = HEADER.unpack_from(payload)
    if magic != MAGIC or (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise ProductionCommandError("command stream magic or ABI differs")
    if reserved != bytes(12) or not count:
        raise ProductionCommandError("command header reserved bits/count differ")
    expected_size = HEADER.size + count * COMMAND_WITH_CRC.size
    if len(payload) != expected_size:
        raise ProductionCommandError("command stream size differs from its header")
    body = payload[HEADER.size :]
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise ProductionCommandError("command stream payload CRC32 differs")
    result: list[ProductionCommand] = []
    for index in range(count):
        offset = HEADER.size + index * COMMAND_WITH_CRC.size
        raw = payload[offset : offset + COMMAND_WITH_CRC.size]
        fields = COMMAND_WITH_CRC.unpack(raw)
        if zlib.crc32(raw[:-4]) & 0xFFFFFFFF != fields[-1]:
            raise ProductionCommandError(f"command {index} CRC32 differs")
        try:
            opcode = Opcode(fields[0])
            engine = Engine(fields[1])
        except ValueError as exc:
            raise ProductionCommandError(
                f"command {index} has an unknown opcode or engine"
            ) from exc
        command = ProductionCommand(
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
    parsed = tuple(result)
    _validate_stream(parsed)
    return parsed


def disassemble(commands: Iterable[ProductionCommand]) -> str:
    lines = [
        f"OTTA-ISA {ABI_MAJOR}.{ABI_MINOR}",
        "# index opcode engine flags kernel src0 src1 dst aux size0 size1 size2 size3",
    ]
    for command in commands:
        lines.append(
            f"{command.index:05d} {command.opcode.name} {command.engine.name} "
            f"0x{command.flags:04x} {command.kernel_index} "
            f"0x{command.source0:016x} 0x{command.source1:016x} "
            f"0x{command.destination:016x} 0x{command.auxiliary:016x} "
            f"{command.size0} {command.size1} {command.size2} {command.size3}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "Engine",
    "MATMUL_FINAL",
    "MATMUL_INIT",
    "NO_KERNEL",
    "Opcode",
    "ProductionCommand",
    "ProductionCommandError",
    "decode",
    "disassemble",
    "encode",
]
