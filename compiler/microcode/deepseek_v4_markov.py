"""Fixed causal microcode for the DeepSeek V4 DSpark Markov loop.

The program unrolls the released five-step control dependency.  Each step
performs one token-indexed BF16 embedding lookup, one BF16-storage/binary32-
runtime vocabulary projection, one separate binary32 bias addition, and one
sample that produces the token consumed by the next step.  The terminal record
exposes the six-token sequence, five adjusted-logit rows, five embeddings, and
the entropy continuation.

Records are semantic micro-operations, not cycles or physical pipeline slots.
The program contains no weight or activation payload, address placement,
schedule, collective implementation, RTL, performance, or full-model claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import struct
from typing import Any

from compiler.ir.model import canonical_json_bytes


MODEL_ID = "deepseek-v4-flash-0731"
MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
NUMERIC_PROFILE = "opentallas.deepseek_v4_markov_loop_binary32.v1"
PROGRAM_SCHEMA = "opentallas.deepseek_v4_markov_program.v1"
ABI_MAJOR = 1
ABI_MINOR = 0
MAGIC = b"OTMKV1\0\0"
HEADER = struct.Struct("<8sHHII32s")
RECORD = struct.Struct("<HHHHHHHH")
NO_OPERAND = 0xFFFF
BLOCK_SIZE = 5
OUTPUT_TOKEN_COUNT = BLOCK_SIZE + 1
PROGRAM_INSTRUCTION_COUNT = BLOCK_SIZE * 4 + 1
OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MARKOV_RANK = 256


class MarkovOpcode(IntEnum):
    """Exact semantic operations admitted by the standalone program."""

    TOKEN_LOOKUP = 1
    VOCABULARY_PROJECT = 2
    BINARY32_BIAS_ADD = 3
    SAMPLE_AND_CARRY = 4
    COMPLETE = 0xFFFF


class MarkovRegister(IntEnum):
    """Logical tensor/control registers visible to the service interpreter."""

    BASE_LOGITS = 0
    INITIAL_TOKENS = 1
    TEMPERATURE = 2
    ENTROPY_INPUT = 3
    TOKENS = 4
    EMBEDDINGS = 5
    BIASES = 6
    ADJUSTED_LOGITS = 7
    ENTROPY_CONTINUATION = 8


class MarkovResource(IntEnum):
    """Immutable resources selected by Markov instructions."""

    W1_EMBEDDING = 0
    W2_VOCABULARY_HEAD = 1


@dataclass(frozen=True, slots=True)
class MarkovInstruction:
    """One fixed-width Markov semantic microinstruction."""

    opcode: MarkovOpcode
    step: int
    destination: MarkovRegister | int
    source0: MarkovRegister | int = NO_OPERAND
    source1: MarkovRegister | int = NO_OPERAND
    source2: MarkovRegister | int = NO_OPERAND
    resource: MarkovResource | int = NO_OPERAND
    flags: int = 0


class DeepSeekV4MarkovMicrocodeError(ValueError):
    """Raised when Markov microcode differs from its frozen causal contract."""


def _expected_program() -> tuple[MarkovInstruction, ...]:
    instructions: list[MarkovInstruction] = []
    for step in range(BLOCK_SIZE):
        token_source = (
            MarkovRegister.INITIAL_TOKENS
            if step == 0
            else MarkovRegister.TOKENS
        )
        entropy_source = (
            MarkovRegister.ENTROPY_INPUT
            if step == 0
            else MarkovRegister.ENTROPY_CONTINUATION
        )
        instructions.extend(
            (
                MarkovInstruction(
                    opcode=MarkovOpcode.TOKEN_LOOKUP,
                    step=step,
                    destination=MarkovRegister.EMBEDDINGS,
                    source0=token_source,
                    resource=MarkovResource.W1_EMBEDDING,
                ),
                MarkovInstruction(
                    opcode=MarkovOpcode.VOCABULARY_PROJECT,
                    step=step,
                    destination=MarkovRegister.BIASES,
                    source0=MarkovRegister.EMBEDDINGS,
                    resource=MarkovResource.W2_VOCABULARY_HEAD,
                ),
                MarkovInstruction(
                    opcode=MarkovOpcode.BINARY32_BIAS_ADD,
                    step=step,
                    destination=MarkovRegister.ADJUSTED_LOGITS,
                    source0=MarkovRegister.BASE_LOGITS,
                    source1=MarkovRegister.BIASES,
                ),
                MarkovInstruction(
                    opcode=MarkovOpcode.SAMPLE_AND_CARRY,
                    step=step,
                    destination=MarkovRegister.TOKENS,
                    source0=MarkovRegister.ADJUSTED_LOGITS,
                    source1=MarkovRegister.TEMPERATURE,
                    source2=entropy_source,
                ),
            )
        )
    instructions.append(
        MarkovInstruction(
            opcode=MarkovOpcode.COMPLETE,
            step=BLOCK_SIZE,
            destination=MarkovRegister.TOKENS,
            source0=MarkovRegister.ADJUSTED_LOGITS,
            source1=MarkovRegister.EMBEDDINGS,
            source2=MarkovRegister.ENTROPY_CONTINUATION,
        )
    )
    return tuple(instructions)


def assemble() -> tuple[MarkovInstruction, ...]:
    """Return the only legal unrolled five-step Markov program."""

    program = _expected_program()
    verify(program)
    return program


def verify(instructions: object) -> None:
    """Require exact causal records, operands, resources, and terminal order."""

    if type(instructions) is not tuple:
        raise DeepSeekV4MarkovMicrocodeError("program must be an exact tuple")
    expected = _expected_program()
    if len(instructions) != PROGRAM_INSTRUCTION_COUNT:
        raise DeepSeekV4MarkovMicrocodeError(
            f"program must contain exactly {PROGRAM_INSTRUCTION_COUNT} instructions"
        )
    for index, (instruction, required) in enumerate(
        zip(instructions, expected, strict=True)
    ):
        if type(instruction) is not MarkovInstruction:
            raise DeepSeekV4MarkovMicrocodeError(
                f"instruction {index} must be an exact MarkovInstruction"
            )
        if instruction != required:
            raise DeepSeekV4MarkovMicrocodeError(
                f"instruction {index} differs from the fixed causal slot"
            )


def _record_bytes(instruction: MarkovInstruction) -> bytes:
    return RECORD.pack(
        int(instruction.opcode),
        instruction.step,
        int(instruction.destination),
        int(instruction.source0),
        int(instruction.source1),
        int(instruction.source2),
        int(instruction.resource),
        instruction.flags,
    )


def encode(instructions: tuple[MarkovInstruction, ...]) -> bytes:
    """Encode the exact program with a SHA-256 body commitment."""

    verify(instructions)
    body = b"".join(_record_bytes(instruction) for instruction in instructions)
    return HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        len(instructions),
        RECORD.size,
        hashlib.sha256(body).digest(),
    ) + body


def decode(payload: bytes) -> tuple[MarkovInstruction, ...]:
    """Decode structural bytes; callers must separately invoke :func:`verify`."""

    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise DeepSeekV4MarkovMicrocodeError("microcode is truncated")
    magic, major, minor, count, record_size, body_digest = HEADER.unpack_from(payload)
    if magic != MAGIC or (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4MarkovMicrocodeError("microcode header identity differs")
    if record_size != RECORD.size or count != PROGRAM_INSTRUCTION_COUNT:
        raise DeepSeekV4MarkovMicrocodeError("microcode record contract differs")
    body = payload[HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4MarkovMicrocodeError("microcode body size differs")
    if hashlib.sha256(body).digest() != body_digest:
        raise DeepSeekV4MarkovMicrocodeError("microcode body digest differs")
    instructions: list[MarkovInstruction] = []

    def register(raw: int, label: str) -> MarkovRegister | int:
        if raw == NO_OPERAND:
            return raw
        try:
            return MarkovRegister(raw)
        except ValueError as exc:
            raise DeepSeekV4MarkovMicrocodeError(
                f"{label} contains unknown register {raw}"
            ) from exc

    def resource_value(raw: int, label: str) -> MarkovResource | int:
        if raw == NO_OPERAND:
            return raw
        try:
            return MarkovResource(raw)
        except ValueError as exc:
            raise DeepSeekV4MarkovMicrocodeError(
                f"{label} contains unknown resource {raw}"
            ) from exc

    for index, offset in enumerate(range(0, len(body), RECORD.size)):
        (
            raw_opcode,
            step,
            destination,
            source0,
            source1,
            source2,
            resource_id,
            flags,
        ) = RECORD.unpack_from(body, offset)
        try:
            opcode = MarkovOpcode(raw_opcode)
        except ValueError as exc:
            raise DeepSeekV4MarkovMicrocodeError(
                f"instruction {index} contains unknown opcode {raw_opcode}"
            ) from exc
        instructions.append(
            MarkovInstruction(
                opcode=opcode,
                step=step,
                destination=register(destination, f"instruction {index} destination"),
                source0=register(source0, f"instruction {index} source0"),
                source1=register(source1, f"instruction {index} source1"),
                source2=register(source2, f"instruction {index} source2"),
                resource=resource_value(
                    resource_id, f"instruction {index} resource"
                ),
                flags=flags,
            )
        )
    return tuple(instructions)


def _operand(value: MarkovRegister | MarkovResource | int) -> str:
    if int(value) == NO_OPERAND:
        return "-"
    if isinstance(value, (MarkovRegister, MarkovResource)):
        return f"{int(value)}:{value.name}"
    return str(value)


def disassemble(instructions: tuple[MarkovInstruction, ...]) -> str:
    """Return deterministic human-readable causal slots."""

    verify(instructions)
    lines = [f"# OpenTallas DeepSeek V4 Markov ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for index, instruction in enumerate(instructions):
        lines.append(
            f"{index:04d} {instruction.opcode.name:<20} step={instruction.step} "
            f"dst={_operand(instruction.destination)} "
            f"src0={_operand(instruction.source0)} "
            f"src1={_operand(instruction.source1)} "
            f"src2={_operand(instruction.source2)} "
            f"resource={_operand(instruction.resource)} flags=0"
        )
    return "\n".join(lines) + "\n"


EXPLICIT_NONCLAIMS = (
    "checkpoint_or_artifact_authentication",
    "checkpoint_derived_base_logits",
    "complete_official_vocabulary_execution",
    "exact_nonzero_temperature_pytorch_cuda_replay",
    "confidence_target_verification_or_speculative_acceptance",
    "physical_collective_or_memory_traffic",
    "physical_schedule_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
    "rtl_or_full_model_execution",
)


def build_program_contract(*, program_sha256: str) -> dict[str, Any]:
    """Build the typed causal/register/resource contract for independent checks."""

    program = assemble()
    return {
        "abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "causal_contract": {
            "block_size": BLOCK_SIZE,
            "entropy_order": "step_then_batch_then_vocabulary",
            "greedy_policy": "finite_binary32_first_index_argmax_exact",
            "initial_token_output_column": 0,
            "sampled_token_carry": (
                "sample_at_step_i_writes_token_column_i_plus_1_consumed_at_next_step"
            ),
            "stochastic_source_replay": (
                "fail_closed_unpinned_torch_cuda_rng_exponential_softmax_backend"
            ),
            "target_adaptation": (
                "explicit_positive_binary32_post_exponential_draws"
            ),
        },
        "instruction_count": len(program),
        "micro_ops": [
            {"opcode": instruction.opcode.name, "step": instruction.step}
            for instruction in program
        ],
        "model_id": MODEL_ID,
        "numeric_contract": {
            "bias_add": "separate_binary32_rne",
            "embedding_storage": "BF16",
            "head_accumulator": "binary32",
            "head_reduction": "increasing_markov_rank_rne_fused_product_add",
            "head_storage": "BF16",
            "subnormals": "preserve",
        },
        "numeric_profile": NUMERIC_PROFILE,
        "outputs": {
            "adjusted_logits": "binary32[B,5,V]",
            "embeddings": "BF16[B,5,R]",
            "entropy_continuation": "immutable_explicit_stream_continuation",
            "tokens": "u32[B,6]",
        },
        "program_sha256": program_sha256,
        "registers": [
            {"id": int(register), "name": register.name}
            for register in MarkovRegister
        ],
        "resources": [
            {
                "dtype": "BF16",
                "id": int(MarkovResource.W1_EMBEDDING),
                "name": "mtp.2.markov_head.markov_w1.weight",
                "official_shape": [OFFICIAL_VOCABULARY_SIZE, OFFICIAL_MARKOV_RANK],
                "partition": "equal_contiguous_vocabulary_rows",
            },
            {
                "dtype": "BF16",
                "id": int(MarkovResource.W2_VOCABULARY_HEAD),
                "name": "mtp.2.markov_head.markov_w2.weight",
                "official_shape": [OFFICIAL_VOCABULARY_SIZE, OFFICIAL_MARKOV_RANK],
                "partition": "equal_contiguous_vocabulary_rows",
            },
        ],
        "schema": PROGRAM_SCHEMA,
        "source": {
            "model_repository": MODEL_REPOSITORY,
            "model_revision": MODEL_REVISION,
            "model_source_sha256": MODEL_SOURCE_SHA256,
        },
        "status": "compiler_contract_verified_execution_separately_required",
        "timing_claim": None,
        "unsupported_claims": list(EXPLICIT_NONCLAIMS),
    }


def verify_program_contract(value: object, *, program_sha256: str) -> None:
    """Require canonical equality with the reconstructable program contract."""

    expected = build_program_contract(program_sha256=program_sha256)
    if type(value) is not dict or canonical_json_bytes(value) != canonical_json_bytes(
        expected
    ):
        raise DeepSeekV4MarkovMicrocodeError("program contract differs")


PROGRAM_BYTES = len(encode(assemble()))
PROGRAM_SHA256 = hashlib.sha256(encode(assemble())).hexdigest()


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "BLOCK_SIZE",
    "DeepSeekV4MarkovMicrocodeError",
    "EXPLICIT_NONCLAIMS",
    "HEADER",
    "MAGIC",
    "MarkovInstruction",
    "MarkovOpcode",
    "MarkovRegister",
    "MarkovResource",
    "NO_OPERAND",
    "NUMERIC_PROFILE",
    "OFFICIAL_MARKOV_RANK",
    "OFFICIAL_VOCABULARY_SIZE",
    "OUTPUT_TOKEN_COUNT",
    "PROGRAM_BYTES",
    "PROGRAM_INSTRUCTION_COUNT",
    "PROGRAM_SCHEMA",
    "PROGRAM_SHA256",
    "RECORD",
    "assemble",
    "build_program_contract",
    "decode",
    "disassemble",
    "encode",
    "verify",
    "verify_program_contract",
]
