"""Exact HC_PRE program fragment for the DeepSeek V4 execution ABI.

The fragment reuses the fixed-width embedding-to-query-A ABI so the same
instruction can be composed into the real initial model schedule.  It binds
one ``HC_PRE`` instruction to the layer-0 attention resources and terminates
with ``COMPLETE``.  The program contains no activation, expected output, host
callback, or implicit arithmetic fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib

from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_embedding_query_a import (
    ABI_MAJOR,
    ABI_MINOR,
    HC_MULTIPLIER,
    HC_NORMALIZATION_EPSILON_BINARY32_BITS,
    HC_PARAMETER_COUNT,
    HC_SINKHORN_EPSILON_BINARY32_BITS,
    HEADER,
    HIDDEN_SIZE,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    NO_OPERAND,
    RECORD,
    SINKHORN_ITERATIONS,
    DeepSeekV4EmbeddingQueryAMicrocodeError,
    Instruction,
    Opcode,
    Register,
    Resource,
    ResourceSpec,
    TensorSpec,
    decode as _decode_program,
    encode as _encode_program,
)


MODEL_ID = "deepseek-v4-flash-0731"
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_hc_pre_program.v1"
PROGRAM_STATUS = "exact_hc_pre_program_contract"

LIVE_AT_COMPLETE = (
    Register.ATTENTION_INPUT,
    Register.ATTENTION_POST,
    Register.ATTENTION_COMBINATION,
    Register.ATTENTION_RESIDUAL,
)
EVIDENCE_OBSERVABLES = (
    Register.ATTENTION_INPUT,
    Register.ATTENTION_PRE,
    Register.ATTENTION_POST,
    Register.ATTENTION_COMBINATION,
    Register.ATTENTION_RESIDUAL,
)
EXPLICIT_NON_CLAIMS = (
    "checkpoint_execution",
    "weighted_rms_norm",
    "query_projection",
    "attention_completion",
    "transformer_block_completion",
    "full_model_execution",
    "cycle_accuracy",
    "ppa",
    "nvidia_comparison",
)


class DeepSeekV4HCPreMicrocodeError(ValueError):
    """Raised when an HC_PRE program differs from its exact ABI contract."""


@dataclass(frozen=True)
class HCPreProgramBinding:
    """One exact register/resource binding used by the standalone fragment."""

    instruction_index: int
    input_register: Register
    branch_register: Register
    pre_register: Register
    post_register: Register
    combination_register: Register
    residual_register: Register
    base_resource: Resource
    projection_resource: Resource
    scale_resource: Resource


PROGRAM_BINDING = HCPreProgramBinding(
    instruction_index=0,
    input_register=Register.HC_HIDDEN,
    branch_register=Register.ATTENTION_INPUT,
    pre_register=Register.ATTENTION_PRE,
    post_register=Register.ATTENTION_POST,
    combination_register=Register.ATTENTION_COMBINATION,
    residual_register=Register.ATTENTION_RESIDUAL,
    base_resource=Resource.HC_ATTN_BASE,
    projection_resource=Resource.HC_ATTN_PROJECTION,
    scale_resource=Resource.HC_ATTN_SCALE,
)


def _strict_contract_equal(value: object, expected: object) -> bool:
    """Compare public contract values without Python's cross-type aliases.

    Python considers ``True == 1``, raw integers equal to ``IntEnum`` members,
    and integral floats equal to integers.  None of those substitutions are
    legal at a typed microcode or JSON-contract boundary.
    """

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
            for actual_item, expected_item in zip(value, expected)
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
            Opcode.HC_PRE,
            destination0=PROGRAM_BINDING.branch_register,
            destination1=PROGRAM_BINDING.pre_register,
            destination2=PROGRAM_BINDING.post_register,
            destination3=PROGRAM_BINDING.combination_register,
            destination4=PROGRAM_BINDING.residual_register,
            source=PROGRAM_BINDING.input_register,
            resource0=PROGRAM_BINDING.base_resource,
            resource1=PROGRAM_BINDING.projection_resource,
            resource2=PROGRAM_BINDING.scale_resource,
            immediate0=HC_MULTIPLIER,
            immediate1=SINKHORN_ITERATIONS,
            immediate2=HC_NORMALIZATION_EPSILON_BINARY32_BITS,
            immediate3=HC_SINKHORN_EPSILON_BINARY32_BITS,
        ),
        Instruction(Opcode.COMPLETE),
    )


def assemble() -> tuple[Instruction, ...]:
    """Assemble the only legal standalone HC_PRE program."""

    program = _expected_program()
    verify(program)
    return program


def verify(instructions: tuple[Instruction, ...]) -> None:
    """Require one exact HC_PRE instruction followed by terminal COMPLETE."""

    if not _strict_contract_equal(instructions, _expected_program()):
        raise DeepSeekV4HCPreMicrocodeError(
            "program does not exactly lower HC_PRE and terminal COMPLETE"
        )


def encode(instructions: tuple[Instruction, ...]) -> bytes:
    """Encode an exact HC_PRE fragment using the shared schedule ABI."""

    verify(instructions)
    try:
        return _encode_program(instructions)
    except DeepSeekV4EmbeddingQueryAMicrocodeError as exc:  # pragma: no cover
        raise DeepSeekV4HCPreMicrocodeError(
            f"cannot encode HC_PRE program: {exc}"
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
    """Restore enum operand types erased by the shared uint32 wire decoder."""

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
        raise DeepSeekV4HCPreMicrocodeError("microcode must be exact bytes")
    try:
        return tuple(
            _typed_decoded_instruction(instruction)
            for instruction in _decode_program(payload)
        )
    except DeepSeekV4EmbeddingQueryAMicrocodeError as exc:
        raise DeepSeekV4HCPreMicrocodeError(
            f"cannot decode HC_PRE program: {exc}"
        ) from exc


def validate_token_count(token_count: int) -> None:
    if (
        type(token_count) is not int
        or not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT
    ):
        raise DeepSeekV4HCPreMicrocodeError(
            f"token_count must be an integer in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )


def tensor_contract(token_count: int) -> tuple[TensorSpec, ...]:
    """Return the complete typed state table for this bounded command."""

    validate_token_count(token_count)
    live = frozenset(LIVE_AT_COMPLETE)
    observable = frozenset(EVIDENCE_OBSERVABLES)
    return (
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
            Register.ATTENTION_INPUT in live,
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
    )


def verify_tensor_contract(value: object, token_count: int) -> None:
    if not _strict_contract_equal(value, tensor_contract(token_count)):
        raise DeepSeekV4HCPreMicrocodeError(
            "typed HC_PRE state differs from the exact program contract"
        )


def resource_contract() -> tuple[ResourceSpec, ...]:
    """Return the exact three checkpoint-derived resources used by HC_PRE."""

    return (
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
    )


def verify_resource_contract(value: object) -> None:
    if not _strict_contract_equal(value, resource_contract()):
        raise DeepSeekV4HCPreMicrocodeError(
            "HC_PRE artifact resources differ from the exact program contract"
        )


def build_program_contract() -> dict[str, object]:
    """Build the hash-bound, output-free program contract."""

    program = encode(assemble())
    body: dict[str, object] = {
        "abi": {
            "major": ABI_MAJOR,
            "magic_ascii": MAGIC.decode("ascii"),
            "minor": ABI_MINOR,
            "record_bytes": RECORD.size,
        },
        "claim_boundary": (
            "Exact executable HC_PRE plus COMPLETE program and typed resource/state "
            "bindings only; checkpoint execution requires a separately verified "
            "deployment, request, artifact-only result, and independent differential."
        ),
        "dimensions": {
            "flattened_width": HC_MULTIPLIER * HIDDEN_SIZE,
            "hc_multiplier": HC_MULTIPLIER,
            "hidden_size": HIDDEN_SIZE,
            "maximum_token_count": MAX_TOKEN_COUNT,
            "minimum_token_count": MIN_TOKEN_COUNT,
            "mix_fields": HC_PARAMETER_COUNT,
            "sinkhorn_iterations": SINKHORN_ITERATIONS,
        },
        "evidence_observables": [item.name for item in EVIDENCE_OBSERVABLES],
        "live_at_complete": [item.name for item in LIVE_AT_COMPLETE],
        "model_id": MODEL_ID,
        "numeric_bindings": {
            "hc_epsilon_binary32": (f"0x{HC_SINKHORN_EPSILON_BINARY32_BITS:08x}"),
            "norm_epsilon_binary32": (
                f"0x{HC_NORMALIZATION_EPSILON_BINARY32_BITS:08x}"
            ),
        },
        "operator_sequence": [Opcode.HC_PRE.name, Opcode.COMPLETE.name],
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
        raise DeepSeekV4HCPreMicrocodeError(
            "HC_PRE program contract differs from its hash-bound definition"
        )


def disassemble(instructions: tuple[Instruction, ...]) -> str:
    """Return the exact human-readable form after semantic verification."""

    verify(instructions)
    lines = [f"# OpenTallas DeepSeek V4 HC_PRE fragment ABI {ABI_MAJOR}.{ABI_MINOR}"]
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
            f"{pc:04d} {instruction.opcode.name:<8} "
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
    "PROGRAM_BINDING",
    "PROGRAM_CONTRACT_SCHEMA",
    "PROGRAM_STATUS",
    "RECORD",
    "DeepSeekV4HCPreMicrocodeError",
    "HCPreProgramBinding",
    "Instruction",
    "Opcode",
    "Register",
    "Resource",
    "assemble",
    "build_program_contract",
    "decode",
    "disassemble",
    "encode",
    "resource_contract",
    "tensor_contract",
    "validate_token_count",
    "verify",
    "verify_program_contract",
    "verify_resource_contract",
    "verify_tensor_contract",
]
