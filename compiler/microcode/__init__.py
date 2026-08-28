"""OpenTallas fixture micro-op encoding, decoding, and static verification."""

from .isa import (
    ABI_MAJOR,
    ABI_MINOR,
    Instruction,
    MicrocodeError,
    Opcode,
    assemble,
    decode,
    disassemble,
    encode,
    verify,
)

__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "Instruction",
    "MicrocodeError",
    "Opcode",
    "assemble",
    "decode",
    "disassemble",
    "encode",
    "verify",
]
