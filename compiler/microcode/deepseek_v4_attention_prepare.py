"""Fixed layer-0 Query-A-to-attention-input microprogram.

This is the first contiguous extension of the executable
``TOKEN_EMBED -> HC_PRE -> RMS_NORM -> QUERY_A`` chain.  It consumes the two
architectural outputs of that chain and prepares the complete 64-head query
and the one 512-value KV row used by a fresh layer-0 attention transaction.

The program is semantic microcode.  Its records are not cycles, physical
slots, messages, flits, memory transactions, or a certified schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import struct
import zlib

from compiler.ir.model import canonical_json_bytes


MAGIC = b"OTAP"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBH12I")
NO_OPERAND = 0xFFFFFFFF

MODEL_ID = "deepseek-v4-flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
LAYER = 0
TOKEN_COUNT = 1
START_POSITION = 0
MODEL_PARALLEL_WORLD_SIZE = 4
QUERY_A_WIDTH = 1_024
HIDDEN_WIDTH = 4_096
HEAD_COUNT = 64
HEAD_WIDTH = 512
ROPE_WIDTH = 64
QUERY_B_LOCAL_WIDTH = 8_192
KV_WIDTH = 512
KV_QDQ_WIDTH = 448
DENSE_BLOCK = 128
KV_QDQ_BLOCK = 64
RMS_EPSILON_BINARY32 = 0x358637BD
HEAD_RMS_EPSILON_BF16 = 0x3586


class Register(IntEnum):
    QUERY_A = 0
    ATTENTION_NORMALIZED = 1
    QUERY_RANK_NORMALIZED = 2
    QUERY_RAW = 3
    QUERY_HEAD_NORMALIZED = 4
    QUERY_PREPARED = 5
    KV_RAW = 6
    KV_NORMALIZED = 7
    KV_ROTATED = 8
    KV_PREPARED = 9


class Resource(IntEnum):
    QUERY_NORM_WEIGHT = 0
    QUERY_B_WEIGHT_RANK_0 = 1
    QUERY_B_SCALE_RANK_0 = 2
    QUERY_B_WEIGHT_RANK_1 = 3
    QUERY_B_SCALE_RANK_1 = 4
    QUERY_B_WEIGHT_RANK_2 = 5
    QUERY_B_SCALE_RANK_2 = 6
    QUERY_B_WEIGHT_RANK_3 = 7
    QUERY_B_SCALE_RANK_3 = 8
    KV_WEIGHT = 9
    KV_SCALE = 10
    KV_NORM_WEIGHT = 11


class Opcode(IntEnum):
    RMS_NORM = 0x14
    FP8_LINEAR = 0x20
    TP_FP8_LINEAR = 0x21
    HEAD_RMS_NORM = 0x30
    ROPE_APPLY = 0x60
    FP8_QDQ = 0x70
    COMPLETE = 0xFF


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    destination: int = NO_OPERAND
    source: int = NO_OPERAND
    resource0: int = NO_OPERAND
    resource1: int = NO_OPERAND
    immediate0: int = 0
    immediate1: int = 0
    immediate2: int = 0
    immediate3: int = 0
    immediate4: int = 0
    immediate5: int = 0
    immediate6: int = 0
    immediate7: int = 0
    flags: int = 0


class DeepSeekV4AttentionPrepareMicrocodeError(ValueError):
    """Raised when attention-preparation microcode differs from its contract."""


def _expected_program() -> tuple[Instruction, ...]:
    return (
        Instruction(
            Opcode.RMS_NORM,
            destination=Register.QUERY_RANK_NORMALIZED,
            source=Register.QUERY_A,
            resource0=Resource.QUERY_NORM_WEIGHT,
            immediate0=QUERY_A_WIDTH,
            immediate1=RMS_EPSILON_BINARY32,
        ),
        Instruction(
            Opcode.TP_FP8_LINEAR,
            destination=Register.QUERY_RAW,
            source=Register.QUERY_RANK_NORMALIZED,
            resource0=Resource.QUERY_B_WEIGHT_RANK_0,
            resource1=Resource.QUERY_B_SCALE_RANK_0,
            immediate0=MODEL_PARALLEL_WORLD_SIZE,
            immediate1=QUERY_B_LOCAL_WIDTH,
            immediate2=QUERY_A_WIDTH,
            immediate3=DENSE_BLOCK,
            immediate4=HEAD_COUNT,
            immediate5=HEAD_WIDTH,
        ),
        Instruction(
            Opcode.HEAD_RMS_NORM,
            destination=Register.QUERY_HEAD_NORMALIZED,
            source=Register.QUERY_RAW,
            immediate0=HEAD_COUNT,
            immediate1=HEAD_WIDTH,
            immediate2=HEAD_RMS_EPSILON_BF16,
        ),
        Instruction(
            Opcode.ROPE_APPLY,
            destination=Register.QUERY_PREPARED,
            source=Register.QUERY_HEAD_NORMALIZED,
            immediate0=HEAD_COUNT,
            immediate1=HEAD_WIDTH,
            immediate2=ROPE_WIDTH,
            immediate3=START_POSITION,
        ),
        Instruction(
            Opcode.FP8_LINEAR,
            destination=Register.KV_RAW,
            source=Register.ATTENTION_NORMALIZED,
            resource0=Resource.KV_WEIGHT,
            resource1=Resource.KV_SCALE,
            immediate0=KV_WIDTH,
            immediate1=HIDDEN_WIDTH,
            immediate2=DENSE_BLOCK,
        ),
        Instruction(
            Opcode.RMS_NORM,
            destination=Register.KV_NORMALIZED,
            source=Register.KV_RAW,
            resource0=Resource.KV_NORM_WEIGHT,
            immediate0=KV_WIDTH,
            immediate1=RMS_EPSILON_BINARY32,
        ),
        Instruction(
            Opcode.ROPE_APPLY,
            destination=Register.KV_ROTATED,
            source=Register.KV_NORMALIZED,
            immediate0=1,
            immediate1=KV_WIDTH,
            immediate2=ROPE_WIDTH,
            immediate3=START_POSITION,
        ),
        Instruction(
            Opcode.FP8_QDQ,
            destination=Register.KV_PREPARED,
            source=Register.KV_ROTATED,
            immediate0=KV_QDQ_WIDTH,
            immediate1=KV_QDQ_BLOCK,
            immediate2=ROPE_WIDTH,
        ),
        Instruction(
            Opcode.COMPLETE,
            destination=Register.QUERY_PREPARED,
            source=Register.KV_PREPARED,
        ),
    )


def assemble() -> tuple[Instruction, ...]:
    result = _expected_program()
    verify(result)
    return result


def _operands(instruction: Instruction) -> tuple[int, ...]:
    return (
        instruction.destination,
        instruction.source,
        instruction.resource0,
        instruction.resource1,
        instruction.immediate0,
        instruction.immediate1,
        instruction.immediate2,
        instruction.immediate3,
        instruction.immediate4,
        instruction.immediate5,
        instruction.immediate6,
        instruction.immediate7,
    )


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    verify(instructions)
    body = b"".join(
        RECORD.pack(int(instruction.opcode), instruction.flags, 0, *_operands(instruction))
        for instruction in instructions
    )
    return HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        RECORD.size,
        len(instructions),
        zlib.crc32(body) & 0xFFFFFFFF,
    ) + body


def decode(payload: bytes) -> tuple[Instruction, ...]:
    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise DeepSeekV4AttentionPrepareMicrocodeError(
            "attention-preparation microcode is not complete bytes"
        )
    magic, major, minor, record_size, count, checksum = HEADER.unpack_from(payload)
    if (magic, major, minor, record_size, count) != (
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        RECORD.size,
        len(_expected_program()),
    ):
        raise DeepSeekV4AttentionPrepareMicrocodeError(
            "attention-preparation microcode header differs"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4AttentionPrepareMicrocodeError(
            "attention-preparation microcode body length differs"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != checksum:
        raise DeepSeekV4AttentionPrepareMicrocodeError(
            "attention-preparation microcode checksum differs"
        )
    result: list[Instruction] = []
    for index in range(count):
        raw = RECORD.unpack_from(body, index * RECORD.size)
        opcode, flags, reserved = raw[:3]
        if flags != 0 or reserved != 0:
            raise DeepSeekV4AttentionPrepareMicrocodeError(
                f"instruction {index} has unsupported control bits"
            )
        try:
            decoded_opcode = Opcode(opcode)
        except ValueError as exc:
            raise DeepSeekV4AttentionPrepareMicrocodeError(
                f"instruction {index} has an unknown opcode"
            ) from exc
        operands = raw[3:]
        result.append(Instruction(decoded_opcode, *operands, flags=flags))
    decoded = tuple(result)
    verify(decoded)
    return decoded


def verify(instructions: tuple[Instruction, ...]) -> None:
    if type(instructions) is not tuple or instructions != _expected_program():
        raise DeepSeekV4AttentionPrepareMicrocodeError(
            "program is not the exact Query-A-to-attention-preparation transaction"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    verify(instructions)
    lines = [f"# OpenTallas DeepSeek V4 attention-prepare ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for index, instruction in enumerate(instructions):
        lines.append(
            f"{index:04d} {instruction.opcode.name} "
            f"dst={instruction.destination} src={instruction.source} "
            f"res=[{instruction.resource0},{instruction.resource1}] "
            "imm=[" + ",".join(str(value) for value in _operands(instruction)[4:]) + "]"
        )
    return "\n".join(lines) + "\n"


def build_program_contract() -> dict[str, object]:
    program = encode(assemble())
    body: dict[str, object] = {
        "abi": {"major": ABI_MAJOR, "minor": ABI_MINOR, "record_bytes": RECORD.size},
        "fixed_request": {
            "layer": LAYER,
            "model_parallel_world_size": MODEL_PARALLEL_WORLD_SIZE,
            "start_position": START_POSITION,
            "token_count": TOKEN_COUNT,
        },
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "operator_sequence": [instruction.opcode.name for instruction in assemble()],
        "program_bytes": len(program),
        "program_sha256": hashlib.sha256(program).hexdigest(),
        "required_nonclaims": [
            "attention_execution",
            "certified_physical_schedule",
            "cycles_or_bandwidth",
            "full_transformer_block",
            "gpu_speedup",
            "ppa_or_target_node_closure",
        ],
        "schema": "opentallas.deepseek_v4_attention_prepare_program.v1",
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


PROGRAM = encode(assemble())
PROGRAM_SHA256 = hashlib.sha256(PROGRAM).hexdigest()
PROGRAM_CONTRACT = build_program_contract()
PROGRAM_CONTRACT_ID = str(PROGRAM_CONTRACT["contract_id"])


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "DENSE_BLOCK",
    "DeepSeekV4AttentionPrepareMicrocodeError",
    "HEAD_COUNT",
    "HEAD_WIDTH",
    "HIDDEN_WIDTH",
    "Instruction",
    "KV_QDQ_BLOCK",
    "KV_QDQ_WIDTH",
    "KV_WIDTH",
    "MODEL_ID",
    "MODEL_PARALLEL_WORLD_SIZE",
    "MODEL_REVISION",
    "Opcode",
    "PROGRAM",
    "PROGRAM_CONTRACT",
    "PROGRAM_CONTRACT_ID",
    "PROGRAM_SHA256",
    "QUERY_A_WIDTH",
    "QUERY_B_LOCAL_WIDTH",
    "RECORD",
    "Register",
    "Resource",
    "ROPE_WIDTH",
    "START_POSITION",
    "TOKEN_COUNT",
    "assemble",
    "build_program_contract",
    "decode",
    "disassemble",
    "encode",
    "verify",
]
