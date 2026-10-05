"""Typed schedule microcode for the first causal DeepSeek V4 chain.

The program begins with token ids and ends after the complete layer-0 query-A
projection.  It deliberately keeps the hyper-connection state live so a later
HC_POST implementation can consume the same architectural values.  This ABI
does not by itself establish executable HC_PRE semantics, the remainder of
attention, or a transformer block.  Those claims require independently frozen
numeric references, an artifact-only interpreter, and checkpoint evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import struct
import zlib

from compiler.ir.model import canonical_json_bytes


MAGIC = b"OTEQ"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBH14I")
NO_OPERAND = 0xFFFFFFFF

MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
VOCABULARY_SIZE = 129_280
HIDDEN_SIZE = 4_096
HC_MULTIPLIER = 4
HC_PARAMETER_COUNT = 24
QUERY_A_OUTPUT_FEATURES = 1_024
DENSE_BLOCK_SIZE = 128
SINKHORN_ITERATIONS = 20
HC_NORMALIZATION_EPSILON_BINARY32_BITS = 0x358637BD
HC_SINKHORN_EPSILON_BINARY32_BITS = 0x358637BD
RMS_EPSILON_BINARY32_BITS = 0x358637BD  # binary32 round-to-nearest of 1e-6


class Register(IntEnum):
    """Typed state slots in the embedding-to-query-A interpreter."""

    TOKEN_IDS = 0
    EMBEDDING = 1
    HC_HIDDEN = 2
    ATTENTION_INPUT = 3
    ATTENTION_PRE = 4
    ATTENTION_POST = 5
    ATTENTION_COMBINATION = 6
    ATTENTION_RESIDUAL = 7
    ATTENTION_NORMALIZED = 8
    QUERY_A = 9


class Resource(IntEnum):
    """Artifact-table slots bound by a deployment manifest."""

    EMBEDDING_SHARD_0 = 0
    EMBEDDING_SHARD_1 = 1
    EMBEDDING_SHARD_2 = 2
    EMBEDDING_SHARD_3 = 3
    HC_ATTN_BASE = 4
    HC_ATTN_PROJECTION = 5
    HC_ATTN_SCALE = 6
    ATTN_NORM_WEIGHT = 7
    QUERY_A_WEIGHT = 8
    QUERY_A_SCALE = 9
    QUERY_A_EXHAUSTIVE_ROWS = 10


class Opcode(IntEnum):
    TOKEN_EMBED = 0x10
    HC_EXPAND = 0x11
    HC_PRE = 0x13
    RMS_NORM = 0x14
    FP8_LINEAR = 0x20
    COMPLETE = 0xFF


class DeepSeekV4EmbeddingQueryAMicrocodeError(ValueError):
    """Raised when this microcode is malformed or semantically different."""


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    destination0: int = NO_OPERAND
    destination1: int = NO_OPERAND
    destination2: int = NO_OPERAND
    destination3: int = NO_OPERAND
    destination4: int = NO_OPERAND
    source: int = NO_OPERAND
    resource0: int = NO_OPERAND
    resource1: int = NO_OPERAND
    resource2: int = NO_OPERAND
    resource3: int = NO_OPERAND
    immediate0: int = 0
    immediate1: int = 0
    immediate2: int = 0
    immediate3: int = 0
    flags: int = 0


@dataclass(frozen=True)
class TensorSpec:
    register: Register
    dtype: str
    shape: tuple[int, ...]
    live_at_complete: bool
    evidence_observable: bool


@dataclass(frozen=True)
class ResourceSpec:
    resource: Resource
    role: str
    dtype: str
    shape: tuple[int, ...]
    size_bytes: int
    checkpoint_derived: bool
    rank: int | None = None
    row_start: int | None = None
    row_stop: int | None = None
    content_sha256: str | None = None


SCHEDULED_OPERATOR_KINDS = (
    "TOKEN_EMBED",
    "HC_EXPAND",
    "HC_PRE",
    "RMS_NORM",
    "FP8_LINEAR",
)

EXPLICIT_NON_CLAIMS = (
    "attention_completion",
    "query_b",
    "kv_path",
    "transformer_block_completion",
    "logits",
    "decode",
    "cycle_accuracy",
    "ppa",
    "nvidia_comparison",
)

SEMANTIC_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_embedding_query_a_schedule_semantic.v1"
)
SEMANTIC_CONTRACT_STATUS = "schedule_only_hc_pre_numeric_reference_pending"

LIVE_AT_COMPLETE = (
    Register.ATTENTION_POST,
    Register.ATTENTION_COMBINATION,
    Register.ATTENTION_RESIDUAL,
    Register.ATTENTION_NORMALIZED,
    Register.QUERY_A,
)

EVIDENCE_OBSERVABLES = (
    Register.EMBEDDING,
    Register.ATTENTION_INPUT,
    Register.ATTENTION_PRE,
    Register.ATTENTION_POST,
    Register.ATTENTION_COMBINATION,
    Register.ATTENTION_RESIDUAL,
    Register.ATTENTION_NORMALIZED,
    Register.QUERY_A,
)

_EXHAUSTIVE_ROW_PAYLOAD = struct.pack(
    f"<{QUERY_A_OUTPUT_FEATURES}I", *range(QUERY_A_OUTPUT_FEATURES)
)
EXHAUSTIVE_ROW_SHA256 = hashlib.sha256(_EXHAUSTIVE_ROW_PAYLOAD).hexdigest()


def _expected_program() -> tuple[Instruction, ...]:
    return (
        Instruction(
            Opcode.TOKEN_EMBED,
            destination0=Register.EMBEDDING,
            source=Register.TOKEN_IDS,
            resource0=Resource.EMBEDDING_SHARD_0,
            resource1=Resource.EMBEDDING_SHARD_1,
            resource2=Resource.EMBEDDING_SHARD_2,
            resource3=Resource.EMBEDDING_SHARD_3,
            immediate0=VOCABULARY_SIZE,
            immediate1=HIDDEN_SIZE,
        ),
        Instruction(
            Opcode.HC_EXPAND,
            destination0=Register.HC_HIDDEN,
            source=Register.EMBEDDING,
            immediate0=HC_MULTIPLIER,
            immediate1=MAX_TOKEN_COUNT,
        ),
        Instruction(
            Opcode.HC_PRE,
            destination0=Register.ATTENTION_INPUT,
            destination1=Register.ATTENTION_PRE,
            destination2=Register.ATTENTION_POST,
            destination3=Register.ATTENTION_COMBINATION,
            destination4=Register.ATTENTION_RESIDUAL,
            source=Register.HC_HIDDEN,
            resource0=Resource.HC_ATTN_BASE,
            resource1=Resource.HC_ATTN_PROJECTION,
            resource2=Resource.HC_ATTN_SCALE,
            immediate0=HC_MULTIPLIER,
            immediate1=SINKHORN_ITERATIONS,
            immediate2=HC_NORMALIZATION_EPSILON_BINARY32_BITS,
            immediate3=HC_SINKHORN_EPSILON_BINARY32_BITS,
        ),
        Instruction(
            Opcode.RMS_NORM,
            destination0=Register.ATTENTION_NORMALIZED,
            source=Register.ATTENTION_INPUT,
            resource0=Resource.ATTN_NORM_WEIGHT,
            immediate0=HIDDEN_SIZE,
            immediate1=RMS_EPSILON_BINARY32_BITS,
        ),
        Instruction(
            Opcode.FP8_LINEAR,
            destination0=Register.QUERY_A,
            source=Register.ATTENTION_NORMALIZED,
            resource0=Resource.QUERY_A_WEIGHT,
            resource1=Resource.QUERY_A_SCALE,
            resource2=Resource.QUERY_A_EXHAUSTIVE_ROWS,
            immediate0=QUERY_A_OUTPUT_FEATURES,
            immediate1=DENSE_BLOCK_SIZE,
        ),
        Instruction(Opcode.COMPLETE),
    )


def assemble() -> tuple[Instruction, ...]:
    """Assemble the one legal v1 causal schedule."""

    result = _expected_program()
    verify(result)
    return result


def _instruction_operands(instruction: Instruction) -> tuple[int, ...]:
    return (
        instruction.destination0,
        instruction.destination1,
        instruction.destination2,
        instruction.destination3,
        instruction.destination4,
        instruction.source,
        instruction.resource0,
        instruction.resource1,
        instruction.resource2,
        instruction.resource3,
        instruction.immediate0,
        instruction.immediate1,
        instruction.immediate2,
        instruction.immediate3,
    )


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    if not instructions:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError("microcode program is empty")
    records: list[bytes] = []
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, Instruction) or not isinstance(
            instruction.opcode, Opcode
        ):
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has an invalid opcode"
            )
        if instruction.flags != 0:
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        operands = _instruction_operands(instruction)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 0xFFFFFFFF
            for value in operands
        ):
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has an operand outside uint32"
            )
        records.append(
            RECORD.pack(int(instruction.opcode), instruction.flags, 0, *operands)
        )
    body = b"".join(records)
    return (
        HEADER.pack(
            MAGIC,
            ABI_MAJOR,
            ABI_MINOR,
            RECORD.size,
            len(instructions),
            zlib.crc32(body) & 0xFFFFFFFF,
        )
        + body
    )


def decode(payload: bytes) -> tuple[Instruction, ...]:
    if not isinstance(payload, bytes):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError("microcode must be bytes")
    if len(payload) < HEADER.size:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "microcode is shorter than its header"
        )
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            f"unsupported embedding-query-A ABI {major}.{minor}; expected "
            f"{ABI_MAJOR}.{ABI_MINOR}"
        )
    if record_size != RECORD.size:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            f"unsupported instruction size {record_size}"
        )
    if count == 0 or count > 64:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "microcode instruction count is outside the ABI bound"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "microcode body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError("microcode CRC32 mismatch")

    result: list[Instruction] = []
    for index in range(count):
        unpacked = RECORD.unpack_from(body, index * RECORD.size)
        opcode_raw, flags, reserved = unpacked[:3]
        if reserved != 0:
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has nonzero reserved bits"
            )
        if flags != 0:
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise DeepSeekV4EmbeddingQueryAMicrocodeError(
                f"instruction {index} has unknown opcode 0x{opcode_raw:02x}"
            ) from exc
        result.append(Instruction(opcode, *unpacked[3:], flags=flags))
    return tuple(result)


def verify(instructions: tuple[Instruction, ...]) -> None:
    """Require the exact ordered lowering, operands, and terminal boundary."""

    if instructions != _expected_program():
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "program does not exactly lower TOKEN_EMBED, HC_EXPAND, HC_PRE, "
            "RMS_NORM, complete FP8_LINEAR, and terminal COMPLETE"
        )


def validate_token_count(token_count: int) -> None:
    if (
        isinstance(token_count, bool)
        or not isinstance(token_count, int)
        or not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT
    ):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            f"token_count must be an integer in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )


def tensor_contract(token_count: int) -> tuple[TensorSpec, ...]:
    """Return the concrete typed state table for a flattened request."""

    validate_token_count(token_count)
    live = frozenset(LIVE_AT_COMPLETE)
    observable = frozenset(EVIDENCE_OBSERVABLES)
    return (
        TensorSpec(Register.TOKEN_IDS, "I64", (token_count,), False, False),
        TensorSpec(
            Register.EMBEDDING,
            "BF16",
            (token_count, HIDDEN_SIZE),
            False,
            Register.EMBEDDING in observable,
        ),
        TensorSpec(
            Register.HC_HIDDEN,
            "BF16",
            (token_count, HC_MULTIPLIER, HIDDEN_SIZE),
            False,
            False,
        ),
        TensorSpec(
            Register.ATTENTION_INPUT,
            "BF16",
            (token_count, HIDDEN_SIZE),
            False,
            Register.ATTENTION_INPUT in observable,
        ),
        TensorSpec(
            Register.ATTENTION_PRE,
            "F32",
            (token_count, HC_MULTIPLIER),
            Register.ATTENTION_PRE in live,
            Register.ATTENTION_PRE in observable,
        ),
        TensorSpec(
            Register.ATTENTION_POST,
            "F32",
            (token_count, HC_MULTIPLIER),
            Register.ATTENTION_POST in live,
            Register.ATTENTION_POST in observable,
        ),
        TensorSpec(
            Register.ATTENTION_COMBINATION,
            "F32",
            (token_count, HC_MULTIPLIER, HC_MULTIPLIER),
            Register.ATTENTION_COMBINATION in live,
            Register.ATTENTION_COMBINATION in observable,
        ),
        TensorSpec(
            Register.ATTENTION_RESIDUAL,
            "BF16",
            (token_count, HC_MULTIPLIER, HIDDEN_SIZE),
            Register.ATTENTION_RESIDUAL in live,
            Register.ATTENTION_RESIDUAL in observable,
        ),
        TensorSpec(
            Register.ATTENTION_NORMALIZED,
            "BF16",
            (token_count, HIDDEN_SIZE),
            Register.ATTENTION_NORMALIZED in live,
            Register.ATTENTION_NORMALIZED in observable,
        ),
        TensorSpec(
            Register.QUERY_A,
            "BF16",
            (token_count, QUERY_A_OUTPUT_FEATURES),
            Register.QUERY_A in live,
            Register.QUERY_A in observable,
        ),
    )


def verify_tensor_contract(value: object, token_count: int) -> None:
    """Require every tensor type, shape, liveness, and evidence attribute."""

    if value != tensor_contract(token_count):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "typed tensor state differs from the v1 schedule contract"
        )


def resource_contract() -> tuple[ResourceSpec, ...]:
    """Return the exact artifact table expected by the v1 program."""

    embedding_rows = VOCABULARY_SIZE // 4
    embedding_bytes = embedding_rows * HIDDEN_SIZE * 2
    embedding_specs = tuple(
        ResourceSpec(
            Resource(rank),
            "model.token_embedding.weight",
            "BF16",
            (embedding_rows, HIDDEN_SIZE),
            embedding_bytes,
            True,
            rank=rank,
            row_start=rank * embedding_rows,
            row_stop=(rank + 1) * embedding_rows,
        )
        for rank in range(4)
    )
    if tuple(
        (spec.rank, spec.row_start, spec.row_stop) for spec in embedding_specs
    ) != tuple(
        (rank, rank * embedding_rows, (rank + 1) * embedding_rows) for rank in range(4)
    ):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "embedding shard ranges do not exactly partition the vocabulary"
        )
    return (
        *embedding_specs,
        ResourceSpec(
            Resource.HC_ATTN_BASE,
            "hyper_connection.attn.base",
            "F32",
            (HC_PARAMETER_COUNT,),
            HC_PARAMETER_COUNT * 4,
            True,
        ),
        ResourceSpec(
            Resource.HC_ATTN_PROJECTION,
            "hyper_connection.attn.projection",
            "F32",
            (HC_PARAMETER_COUNT, HC_MULTIPLIER * HIDDEN_SIZE),
            HC_PARAMETER_COUNT * HC_MULTIPLIER * HIDDEN_SIZE * 4,
            True,
        ),
        ResourceSpec(
            Resource.HC_ATTN_SCALE,
            "hyper_connection.attn.scale",
            "F32",
            (3,),
            3 * 4,
            True,
        ),
        ResourceSpec(
            Resource.ATTN_NORM_WEIGHT,
            "block.attention_norm.weight",
            "BF16",
            (HIDDEN_SIZE,),
            HIDDEN_SIZE * 2,
            True,
        ),
        ResourceSpec(
            Resource.QUERY_A_WEIGHT,
            "attention.query_a.weight",
            "F8_E4M3",
            (QUERY_A_OUTPUT_FEATURES, HIDDEN_SIZE),
            QUERY_A_OUTPUT_FEATURES * HIDDEN_SIZE,
            True,
        ),
        ResourceSpec(
            Resource.QUERY_A_SCALE,
            "attention.query_a.scale",
            "F8_E8M0",
            (
                QUERY_A_OUTPUT_FEATURES // DENSE_BLOCK_SIZE,
                HIDDEN_SIZE // DENSE_BLOCK_SIZE,
            ),
            (QUERY_A_OUTPUT_FEATURES // DENSE_BLOCK_SIZE)
            * (HIDDEN_SIZE // DENSE_BLOCK_SIZE),
            True,
        ),
        ResourceSpec(
            Resource.QUERY_A_EXHAUSTIVE_ROWS,
            "attention.query_a.exhaustive_output_rows",
            "U32",
            (QUERY_A_OUTPUT_FEATURES,),
            QUERY_A_OUTPUT_FEATURES * 4,
            False,
            content_sha256=EXHAUSTIVE_ROW_SHA256,
        ),
    )


def verify_resource_contract(value: object) -> None:
    """Require the exact ordered resource identities and shard ranges."""

    if value != resource_contract():
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "artifact resource table differs from the v1 schedule contract"
        )


def exhaustive_row_payload() -> bytes:
    """Return the only row-selection payload that denotes complete query-A."""

    return _EXHAUSTIVE_ROW_PAYLOAD


def validate_exhaustive_row_payload(payload: bytes) -> None:
    if not isinstance(payload, bytes):
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "exhaustive row payload must be bytes"
        )
    if payload != _EXHAUSTIVE_ROW_PAYLOAD:
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "query-A row payload must be exact little-endian U32 0..1023"
        )


def build_semantic_contract() -> dict[str, object]:
    """Build the hash-addressed, schema-governed schedule claim boundary."""

    body: dict[str, object] = {
        "architectural_live_at_complete": [value.name for value in LIVE_AT_COMPLETE],
        "claim_boundary": (
            "Typed causal schedule from token IDs through complete layer-0 "
            "query-A outputs; HC_PRE numeric reference, integrated execution, "
            "attention completion, transformer completion, and performance are "
            "not established."
        ),
        "dimensions": {
            "dense_block_size": DENSE_BLOCK_SIZE,
            "hc_multiplier": HC_MULTIPLIER,
            "hidden_size": HIDDEN_SIZE,
            "maximum_token_count": MAX_TOKEN_COUNT,
            "minimum_token_count": MIN_TOKEN_COUNT,
            "query_a_output_features": QUERY_A_OUTPUT_FEATURES,
            "vocabulary_size": VOCABULARY_SIZE,
        },
        "evidence_observables": [value.name for value in EVIDENCE_OBSERVABLES],
        "exhaustive_row_sha256": EXHAUSTIVE_ROW_SHA256,
        "hc_pre_execution_status": "numeric_reference_pending",
        "model_id": "deepseek-v4-flash-0731",
        "numeric_bindings": {
            "hc_normalization_epsilon_binary32": (
                f"0x{HC_NORMALIZATION_EPSILON_BINARY32_BITS:08x}"
            ),
            "hc_sinkhorn_epsilon_binary32": (
                f"0x{HC_SINKHORN_EPSILON_BINARY32_BITS:08x}"
            ),
            "rms_epsilon_binary32": f"0x{RMS_EPSILON_BINARY32_BITS:08x}",
            "sinkhorn_iterations": SINKHORN_ITERATIONS,
        },
        "operator_sequence": [*SCHEDULED_OPERATOR_KINDS, "COMPLETE"],
        "required_nonclaims": list(EXPLICIT_NON_CLAIMS),
        "schema": SEMANTIC_CONTRACT_SCHEMA,
        "status": SEMANTIC_CONTRACT_STATUS,
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def verify_semantic_contract(value: object) -> None:
    """Reject semantic drift, including a self-consistent-looking stale hash."""

    if value != build_semantic_contract():
        raise DeepSeekV4EmbeddingQueryAMicrocodeError(
            "semantic schedule contract differs from the hash-bound v1 contract"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    lines = [f"# OpenTallas DeepSeek V4 embedding-query-A ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for pc, instruction in enumerate(instructions):
        destinations = ",".join(
            f"{value:#010x}"
            for value in (
                instruction.destination0,
                instruction.destination1,
                instruction.destination2,
                instruction.destination3,
                instruction.destination4,
            )
        )
        resources = ",".join(
            f"{value:#010x}"
            for value in (
                instruction.resource0,
                instruction.resource1,
                instruction.resource2,
                instruction.resource3,
            )
        )
        lines.append(
            f"{pc:04d} {instruction.opcode.name:<10} "
            f"dst=[{destinations}] src={instruction.source:#010x} "
            f"resources=[{resources}] "
            f"imm=[{instruction.immediate0},{instruction.immediate1},"
            f"{instruction.immediate2},{instruction.immediate3}]"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "DENSE_BLOCK_SIZE",
    "DeepSeekV4EmbeddingQueryAMicrocodeError",
    "EVIDENCE_OBSERVABLES",
    "EXHAUSTIVE_ROW_SHA256",
    "EXPLICIT_NON_CLAIMS",
    "HEADER",
    "HC_MULTIPLIER",
    "HC_NORMALIZATION_EPSILON_BINARY32_BITS",
    "HC_SINKHORN_EPSILON_BINARY32_BITS",
    "Instruction",
    "LIVE_AT_COMPLETE",
    "MAX_TOKEN_COUNT",
    "MIN_TOKEN_COUNT",
    "Opcode",
    "QUERY_A_OUTPUT_FEATURES",
    "RECORD",
    "Register",
    "Resource",
    "ResourceSpec",
    "SCHEDULED_OPERATOR_KINDS",
    "SEMANTIC_CONTRACT_SCHEMA",
    "SEMANTIC_CONTRACT_STATUS",
    "TensorSpec",
    "assemble",
    "build_semantic_contract",
    "decode",
    "disassemble",
    "encode",
    "exhaustive_row_payload",
    "resource_contract",
    "tensor_contract",
    "validate_token_count",
    "validate_exhaustive_row_payload",
    "verify",
    "verify_resource_contract",
    "verify_semantic_contract",
    "verify_tensor_contract",
]
