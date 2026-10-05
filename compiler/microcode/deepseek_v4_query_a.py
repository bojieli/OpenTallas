"""Exact weighted-normalization and query-A program for DeepSeek V4.

The fragment reuses the fixed-width embedding-to-query-A wire ABI.  Its only
external activation is ``ATTENTION_INPUT`` from a preceding, independently
verified HC_PRE transaction.  It executes weighted ``RMS_NORM``, all 1,024
rows of the layer-0 query-A ``FP8_LINEAR``, and terminal ``COMPLETE``.

The program carries no activation, expected output, callback, fallback
operator, timing value, or physical claim.  Checkpoint execution additionally
requires a verified artifact package, artifact-only interpreter, persisted
request/result, and independent locked-checkpoint differential.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    ABI_MAJOR,
    ABI_MINOR,
    DENSE_BLOCK_SIZE,
    HEADER,
    HIDDEN_SIZE,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    NO_OPERAND,
    QUERY_A_OUTPUT_FEATURES,
    RECORD,
    RMS_EPSILON_BINARY32_BITS,
    DeepSeekV4EmbeddingQueryAMicrocodeError,
    Instruction,
    Opcode,
    Register,
    Resource,
    ResourceSpec,
    TensorSpec,
    decode as _decode_program,
    encode as _encode_program,
    exhaustive_row_payload as _exhaustive_row_payload,
)


MODEL_ID = "deepseek-v4-flash-0731"
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_query_a_program.v1"
PROGRAM_STATUS = "exact_weighted_rms_complete_query_a_program_contract"

LIVE_AT_COMPLETE = (Register.QUERY_A,)
EVIDENCE_OBSERVABLES = (
    Register.ATTENTION_INPUT,
    Register.ATTENTION_NORMALIZED,
    Register.QUERY_A,
)
EXPLICIT_NON_CLAIMS = (
    "attention_completion",
    "checkpoint_execution",
    "cycle_accuracy",
    "full_model_execution",
    "hc_pre_execution",
    "nvidia_comparison",
    "physical_schedule",
    "ppa",
    "query_b",
    "rtl_execution",
    "transformer_block_completion",
)


class DeepSeekV4QueryAMicrocodeError(ValueError):
    """Raised when a query-A program differs from its exact ABI contract."""


@dataclass(frozen=True)
class QueryAProgramBinding:
    """Exact register and resource bindings for the standalone fragment."""

    rms_instruction_index: int
    linear_instruction_index: int
    input_register: Register
    normalized_register: Register
    output_register: Register
    norm_weight_resource: Resource
    query_weight_resource: Resource
    query_scale_resource: Resource
    exhaustive_rows_resource: Resource


PROGRAM_BINDING = QueryAProgramBinding(
    rms_instruction_index=0,
    linear_instruction_index=1,
    input_register=Register.ATTENTION_INPUT,
    normalized_register=Register.ATTENTION_NORMALIZED,
    output_register=Register.QUERY_A,
    norm_weight_resource=Resource.ATTN_NORM_WEIGHT,
    query_weight_resource=Resource.QUERY_A_WEIGHT,
    query_scale_resource=Resource.QUERY_A_SCALE,
    exhaustive_rows_resource=Resource.QUERY_A_EXHAUSTIVE_ROWS,
)


def _strict_contract_equal(value: object, expected: object) -> bool:
    """Compare public contracts without bool/int, enum/int, or float aliases."""

    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        if (
            value.keys() != expected.keys()
            or any(type(key) is not str for key in value)
            or any(type(key) is not str for key in expected)
        ):
            return False
        return all(
            _strict_contract_equal(value[key], expected_item)
            for key, expected_item in expected.items()
        )
    if isinstance(expected, (list, tuple)):
        return len(value) == len(expected) and all(
            _strict_contract_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(value, expected, strict=True)
        )
    if is_dataclass(expected) and not isinstance(expected, type):
        return all(
            _strict_contract_equal(
                getattr(value, field.name),
                getattr(expected, field.name),
            )
            for field in fields(expected)
        )
    return value == expected


def _expected_program() -> tuple[Instruction, ...]:
    return (
        Instruction(
            Opcode.RMS_NORM,
            destination0=PROGRAM_BINDING.normalized_register,
            source=PROGRAM_BINDING.input_register,
            resource0=PROGRAM_BINDING.norm_weight_resource,
            immediate0=HIDDEN_SIZE,
            immediate1=RMS_EPSILON_BINARY32_BITS,
        ),
        Instruction(
            Opcode.FP8_LINEAR,
            destination0=PROGRAM_BINDING.output_register,
            source=PROGRAM_BINDING.normalized_register,
            resource0=PROGRAM_BINDING.query_weight_resource,
            resource1=PROGRAM_BINDING.query_scale_resource,
            resource2=PROGRAM_BINDING.exhaustive_rows_resource,
            immediate0=QUERY_A_OUTPUT_FEATURES,
            immediate1=DENSE_BLOCK_SIZE,
        ),
        Instruction(Opcode.COMPLETE),
    )


def assemble() -> tuple[Instruction, ...]:
    """Assemble the sole legal weighted-RMS plus complete query-A program."""

    program = _expected_program()
    verify(program)
    return program


def verify(instructions: tuple[Instruction, ...]) -> None:
    """Require exact operands, ordering, and terminal completion."""

    if not _strict_contract_equal(instructions, _expected_program()):
        raise DeepSeekV4QueryAMicrocodeError(
            "program does not exactly lower RMS_NORM, complete FP8_LINEAR, "
            "and terminal COMPLETE"
        )


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    """Encode the exact fragment using the shared schedule ABI."""

    verify(instructions)
    try:
        return _encode_program(instructions)
    except DeepSeekV4EmbeddingQueryAMicrocodeError as exc:  # pragma: no cover
        raise DeepSeekV4QueryAMicrocodeError(
            f"cannot encode query-A program: {exc}"
        ) from exc


def _decoded_register(value: int) -> int:
    if value == NO_OPERAND:
        return value
    try:
        return Register(value)
    except ValueError:
        return value


def _decoded_resource(value: int) -> int:
    if value == NO_OPERAND:
        return value
    try:
        return Resource(value)
    except ValueError:
        return value


def _typed_decoded_instruction(instruction: Instruction) -> Instruction:
    return Instruction(
        instruction.opcode,
        destination0=_decoded_register(instruction.destination0),
        destination1=_decoded_register(instruction.destination1),
        destination2=_decoded_register(instruction.destination2),
        destination3=_decoded_register(instruction.destination3),
        destination4=_decoded_register(instruction.destination4),
        source=_decoded_register(instruction.source),
        resource0=_decoded_resource(instruction.resource0),
        resource1=_decoded_resource(instruction.resource1),
        resource2=_decoded_resource(instruction.resource2),
        resource3=_decoded_resource(instruction.resource3),
        immediate0=instruction.immediate0,
        immediate1=instruction.immediate1,
        immediate2=instruction.immediate2,
        immediate3=instruction.immediate3,
        flags=instruction.flags,
    )


def decode(payload: bytes) -> tuple[Instruction, ...]:
    """Decode structurally valid shared-ABI bytes; call :func:`verify` next."""

    if type(payload) is not bytes:
        raise DeepSeekV4QueryAMicrocodeError("microcode must be exact bytes")
    try:
        return tuple(
            _typed_decoded_instruction(instruction)
            for instruction in _decode_program(payload)
        )
    except DeepSeekV4EmbeddingQueryAMicrocodeError as exc:
        raise DeepSeekV4QueryAMicrocodeError(
            f"cannot decode query-A program: {exc}"
        ) from exc


def validate_token_count(token_count: int) -> None:
    if (
        type(token_count) is not int
        or not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT
    ):
        raise DeepSeekV4QueryAMicrocodeError(
            f"token_count must be an integer in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )


def tensor_contract(token_count: int) -> tuple[TensorSpec, ...]:
    """Return the complete typed state table for this bounded fragment."""

    validate_token_count(token_count)
    live = frozenset(LIVE_AT_COMPLETE)
    observable = frozenset(EVIDENCE_OBSERVABLES)
    return (
        TensorSpec(
            Register.ATTENTION_INPUT,
            "BF16",
            (token_count, HIDDEN_SIZE),
            Register.ATTENTION_INPUT in live,
            Register.ATTENTION_INPUT in observable,
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
    if not _strict_contract_equal(value, tensor_contract(token_count)):
        raise DeepSeekV4QueryAMicrocodeError(
            "typed query-A state differs from the exact program contract"
        )


def resource_contract() -> tuple[ResourceSpec, ...]:
    """Return the exact learned resources plus exhaustive row selector."""

    return (
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
            content_sha256=hashlib.sha256(_exhaustive_row_payload()).hexdigest(),
        ),
    )


def verify_resource_contract(value: object) -> None:
    if not _strict_contract_equal(value, resource_contract()):
        raise DeepSeekV4QueryAMicrocodeError(
            "query-A artifact resources differ from the exact program contract"
        )


def exhaustive_row_payload() -> bytes:
    """Return the only row-selection payload denoting complete query-A."""

    payload = _exhaustive_row_payload()
    if type(payload) is not bytes or len(payload) != QUERY_A_OUTPUT_FEATURES * 4:
        raise RuntimeError("shared exhaustive query-A payload invariant failed")
    return payload


def validate_exhaustive_row_payload(payload: bytes) -> None:
    if type(payload) is not bytes or payload != exhaustive_row_payload():
        raise DeepSeekV4QueryAMicrocodeError(
            "query-A row payload must be exact little-endian U32 0..1023"
        )


def build_program_contract() -> dict[str, object]:
    """Build the hash-bound and output-free executable program contract."""

    program = encode(assemble())
    body: dict[str, object] = {
        "abi": {
            "major": ABI_MAJOR,
            "magic_ascii": MAGIC.decode("ascii"),
            "minor": ABI_MINOR,
            "record_bytes": RECORD.size,
        },
        "claim_boundary": (
            "Exact executable weighted RMS_NORM, complete query-A FP8_LINEAR, "
            "and terminal COMPLETE program with typed resource/state bindings "
            "only; execution requires separately verified checkpoint artifacts, "
            "an artifact-only result, and an independent differential."
        ),
        "dimensions": {
            "dense_block_size": DENSE_BLOCK_SIZE,
            "hidden_size": HIDDEN_SIZE,
            "maximum_token_count": MAX_TOKEN_COUNT,
            "minimum_token_count": MIN_TOKEN_COUNT,
            "query_a_output_features": QUERY_A_OUTPUT_FEATURES,
        },
        "evidence_observables": [item.name for item in EVIDENCE_OBSERVABLES],
        "live_at_complete": [item.name for item in LIVE_AT_COMPLETE],
        "model_id": MODEL_ID,
        "numeric_bindings": {
            "dense_block_size": DENSE_BLOCK_SIZE,
            "rms_epsilon_binary32": f"0x{RMS_EPSILON_BINARY32_BITS:08x}",
        },
        "operator_sequence": [
            Opcode.RMS_NORM.name,
            Opcode.FP8_LINEAR.name,
            Opcode.COMPLETE.name,
        ],
        "program_bytes": len(program),
        "program_sha256": hashlib.sha256(program).hexdigest(),
        "required_nonclaims": list(EXPLICIT_NON_CLAIMS),
        "resource_ids": [int(item.resource) for item in resource_contract()],
        "schema": PROGRAM_CONTRACT_SCHEMA,
        "status": PROGRAM_STATUS,
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def verify_program_contract(value: object) -> None:
    if not _strict_contract_equal(value, build_program_contract()):
        raise DeepSeekV4QueryAMicrocodeError(
            "query-A program contract differs from its hash-bound definition"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    """Return the exact human-readable form after semantic verification."""

    verify(instructions)
    lines = [
        f"# OpenTallas DeepSeek V4 weighted-RMS/query-A fragment ABI "
        f"{ABI_MAJOR}.{ABI_MINOR}"
    ]
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
            f"res=[{resources}] "
            f"imm=[{instruction.immediate0:#010x},"
            f"{instruction.immediate1:#010x},"
            f"{instruction.immediate2:#010x},"
            f"{instruction.immediate3:#010x}]"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "EVIDENCE_OBSERVABLES",
    "EXPLICIT_NON_CLAIMS",
    "HEADER",
    "LIVE_AT_COMPLETE",
    "MAGIC",
    "MODEL_ID",
    "PROGRAM_BINDING",
    "PROGRAM_CONTRACT_SCHEMA",
    "PROGRAM_STATUS",
    "RECORD",
    "DeepSeekV4QueryAMicrocodeError",
    "Instruction",
    "Opcode",
    "QueryAProgramBinding",
    "Register",
    "Resource",
    "assemble",
    "build_program_contract",
    "decode",
    "disassemble",
    "encode",
    "exhaustive_row_payload",
    "resource_contract",
    "tensor_contract",
    "validate_exhaustive_row_payload",
    "validate_token_count",
    "verify",
    "verify_program_contract",
    "verify_resource_contract",
    "verify_tensor_contract",
]
