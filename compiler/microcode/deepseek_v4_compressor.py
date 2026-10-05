"""Fixed microcode for the bounded DeepSeek V4 ratio-four compressor slice.

The fragment begins after the learned ``wkv`` and ``wgate`` projections.  Its
only checkpoint resource is the full-size layer-2 main-compressor APE tensor.
Slots are semantic operations, not cycles or physical pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import struct
from typing import Any

from compiler.ir.model import canonical_json_bytes


MODEL_ID = "deepseek-v4-flash-0731"
PROGRAM_SCHEMA = "opentallas.deepseek_v4_compressor_program.v1"
ABI_MAJOR = 1
ABI_MINOR = 0
MAGIC = b"OTCMPV1\0"
HEADER = struct.Struct("<8sHHII32s")
RECORD = struct.Struct("<HHIII")
RATIO = 4
HEAD_DIM = 512
PROJECTED_WIDTH = 1024
APE_SHAPE = (4, 1024)
APE_BYTES = 16_384


class CompressorOpcode(IntEnum):
    """Exact semantic operators admitted by this standalone program."""

    RAW_STATE_PREPARE = 1
    POOL_IF_READY = 2
    F32_TO_BF16_IF_READY = 3
    COMPRESSED_KV_COMMIT = 4
    VALID_PREFIX_VIEW = 5
    COMPLETE = 0xFFFF


@dataclass(frozen=True)
class CompressorInstruction:
    """One fixed-width semantic microinstruction."""

    opcode: CompressorOpcode
    flags: int = 0
    source: int = 0
    destination: int = 0
    immediate: int = 0


class DeepSeekV4CompressorMicrocodeError(ValueError):
    """Raised when compressor microcode differs from its frozen contract."""


def assemble() -> tuple[CompressorInstruction, ...]:
    """Return the only legal standalone ratio-four compressor program."""

    program = (
        CompressorInstruction(CompressorOpcode.RAW_STATE_PREPARE),
        CompressorInstruction(CompressorOpcode.POOL_IF_READY),
        CompressorInstruction(CompressorOpcode.F32_TO_BF16_IF_READY),
        CompressorInstruction(CompressorOpcode.COMPRESSED_KV_COMMIT),
        CompressorInstruction(CompressorOpcode.VALID_PREFIX_VIEW),
        CompressorInstruction(CompressorOpcode.COMPLETE),
    )
    verify(program)
    return program


def verify(instructions: object) -> None:
    """Require the exact six-slot causal program with no hidden operands."""

    if type(instructions) is not tuple:
        raise DeepSeekV4CompressorMicrocodeError("program must be an exact tuple")
    expected_opcodes = (
        CompressorOpcode.RAW_STATE_PREPARE,
        CompressorOpcode.POOL_IF_READY,
        CompressorOpcode.F32_TO_BF16_IF_READY,
        CompressorOpcode.COMPRESSED_KV_COMMIT,
        CompressorOpcode.VALID_PREFIX_VIEW,
        CompressorOpcode.COMPLETE,
    )
    if len(instructions) != len(expected_opcodes):
        raise DeepSeekV4CompressorMicrocodeError(
            "program must contain exactly six compressor instructions"
        )
    for index, (instruction, opcode) in enumerate(
        zip(instructions, expected_opcodes, strict=True)
    ):
        if type(instruction) is not CompressorInstruction:
            raise DeepSeekV4CompressorMicrocodeError(
                f"instruction {index} must be an exact CompressorInstruction"
            )
        if instruction != CompressorInstruction(opcode):
            raise DeepSeekV4CompressorMicrocodeError(
                f"instruction {index} differs from the fixed {opcode.name} slot"
            )


def _record_bytes(instruction: CompressorInstruction) -> bytes:
    return RECORD.pack(
        int(instruction.opcode),
        instruction.flags,
        instruction.source,
        instruction.destination,
        instruction.immediate,
    )


def encode(instructions: tuple[CompressorInstruction, ...]) -> bytes:
    """Encode the exact program with an internal body digest."""

    verify(instructions)
    body = b"".join(_record_bytes(instruction) for instruction in instructions)
    return (
        HEADER.pack(
            MAGIC,
            ABI_MAJOR,
            ABI_MINOR,
            len(instructions),
            RECORD.size,
            hashlib.sha256(body).digest(),
        )
        + body
    )


def decode(payload: bytes) -> tuple[CompressorInstruction, ...]:
    """Decode structurally valid bytes; callers must also invoke :func:`verify`."""

    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise DeepSeekV4CompressorMicrocodeError("microcode is truncated")
    magic, major, minor, count, record_size, body_digest = HEADER.unpack_from(payload)
    if magic != MAGIC or (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4CompressorMicrocodeError("microcode header identity differs")
    if record_size != RECORD.size or count != 6:
        raise DeepSeekV4CompressorMicrocodeError("microcode record contract differs")
    body = payload[HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4CompressorMicrocodeError("microcode body size differs")
    if hashlib.sha256(body).digest() != body_digest:
        raise DeepSeekV4CompressorMicrocodeError("microcode body digest differs")
    decoded: list[CompressorInstruction] = []
    for offset in range(0, len(body), RECORD.size):
        raw_opcode, flags, source, destination, immediate = RECORD.unpack_from(
            body, offset
        )
        try:
            opcode = CompressorOpcode(raw_opcode)
        except ValueError as exc:
            raise DeepSeekV4CompressorMicrocodeError(
                f"microcode contains unknown opcode {raw_opcode}"
            ) from exc
        decoded.append(
            CompressorInstruction(opcode, flags, source, destination, immediate)
        )
    return tuple(decoded)


def disassemble(instructions: tuple[CompressorInstruction, ...]) -> str:
    """Return deterministic human-readable semantic slots."""

    verify(instructions)
    lines = [
        f"{index:04d} {instruction.opcode.name} flags=0 source=0 destination=0 immediate=0"
        for index, instruction in enumerate(instructions)
    ]
    return "\n".join(lines) + "\n"


def build_program_contract(
    *,
    program_sha256: str,
    ape_sha256: str,
) -> dict[str, Any]:
    """Build the typed program/resource contract consumed by the checker."""

    program = assemble()
    return {
        "abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "boundary": {
            "input": "finite projected FP32 KV and gate-score codes after wkv/wgate",
            "output": (
                "transactional raw state, optional direct post-pool BF16 harness "
                "payload, compressed-cache state, and valid-prefix view"
            ),
            "omitted_before": ["wkv_projection", "wgate_projection"],
            "omitted_between_conversion_and_attention_cache": [
                "rms_normalization",
                "rotary_embedding",
                "activation_qdq",
            ],
        },
        "dimensions": {
            "ape_shape": list(APE_SHAPE),
            "head_dim": HEAD_DIM,
            "projected_width": PROJECTED_WIDTH,
            "ratio": RATIO,
        },
        "instruction_count": len(program),
        "micro_ops": [instruction.opcode.name for instruction in program],
        "model_id": MODEL_ID,
        "program_sha256": program_sha256,
        "resource": {
            "dtype": "F32",
            "name": "layers.2.attn.compressor.ape",
            "sha256": ape_sha256,
            "shape": list(APE_SHAPE),
            "size_bytes": APE_BYTES,
        },
        "schema": PROGRAM_SCHEMA,
        "timing_claim": None,
    }


def verify_program_contract(
    value: object,
    *,
    program_sha256: str,
    ape_sha256: str,
) -> None:
    """Require canonical equality with the independently reconstructable contract."""

    expected = build_program_contract(
        program_sha256=program_sha256,
        ape_sha256=ape_sha256,
    )
    if type(value) is not dict or canonical_json_bytes(value) != canonical_json_bytes(
        expected
    ):
        raise DeepSeekV4CompressorMicrocodeError("program contract differs")


PROGRAM_BYTES = len(encode(assemble()))
PROGRAM_SHA256 = hashlib.sha256(encode(assemble())).hexdigest()


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "APE_BYTES",
    "APE_SHAPE",
    "CompressorInstruction",
    "CompressorOpcode",
    "DeepSeekV4CompressorMicrocodeError",
    "HEAD_DIM",
    "MAGIC",
    "MODEL_ID",
    "PROGRAM_BYTES",
    "PROGRAM_SCHEMA",
    "PROGRAM_SHA256",
    "PROJECTED_WIDTH",
    "RATIO",
    "assemble",
    "build_program_contract",
    "decode",
    "disassemble",
    "encode",
    "verify",
    "verify_program_contract",
]
