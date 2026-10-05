"""Independent legality checker for DeepSeek V4 Markov microcode.

This module deliberately does not import the Markov assembler or decoder.  It
reconstructs the wire ABI, exact 21-slot causal sequence, and public program
contract from separately stated constants, then compares every byte/field.
Arithmetic execution and artifact/resource authentication are separate gates.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Any

from compiler.ir.model import canonical_json_bytes


_MAGIC = b"OTMKV1\0\0"
_HEADER = struct.Struct("<8sHHII32s")
_RECORD = struct.Struct("<HHHHHHHH")
_ABI = (1, 0)
_NO = 0xFFFF
_BLOCK_SIZE = 5
_INSTRUCTION_COUNT = 21
_MODEL_ID = "deepseek-v4-flash-0731"
_MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
_MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
_MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
_NUMERIC_PROFILE = "opentallas.deepseek_v4_markov_loop_binary32.v1"
_PROGRAM_SCHEMA = "opentallas.deepseek_v4_markov_program.v1"
_REGISTER_NAMES = (
    "BASE_LOGITS",
    "INITIAL_TOKENS",
    "TEMPERATURE",
    "ENTROPY_INPUT",
    "TOKENS",
    "EMBEDDINGS",
    "BIASES",
    "ADJUSTED_LOGITS",
    "ENTROPY_CONTINUATION",
)
_OPCODE_NAMES = {
    1: "TOKEN_LOOKUP",
    2: "VOCABULARY_PROJECT",
    3: "BINARY32_BIAS_ADD",
    4: "SAMPLE_AND_CARRY",
    0xFFFF: "COMPLETE",
}
_NONCLAIMS = (
    "checkpoint_or_artifact_authentication",
    "checkpoint_derived_base_logits",
    "complete_official_vocabulary_execution",
    "exact_nonzero_temperature_pytorch_cuda_replay",
    "confidence_target_verification_or_speculative_acceptance",
    "physical_collective_or_memory_traffic",
    "physical_schedule_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
    "rtl_or_full_model_execution",
)


class DeepSeekV4MarkovCheckError(ValueError):
    """Raised when program bytes or their declared contract differ."""


@dataclass(frozen=True, slots=True)
class MarkovProgramVerificationReport:
    """Small immutable result of independent structural verification."""

    program_sha256: str
    instruction_count: int
    block_size: int
    lookup_count: int
    projection_count: int
    bias_add_count: int
    sampling_count: int
    complete_count: int
    status: str

    def __post_init__(self) -> None:
        if (
            type(self.program_sha256) is not str
            or len(self.program_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.program_sha256)
        ):
            raise DeepSeekV4MarkovCheckError("report program SHA-256 differs")
        if (
            self.instruction_count != _INSTRUCTION_COUNT
            or self.block_size != _BLOCK_SIZE
            or self.lookup_count != _BLOCK_SIZE
            or self.projection_count != _BLOCK_SIZE
            or self.bias_add_count != _BLOCK_SIZE
            or self.sampling_count != _BLOCK_SIZE
            or self.complete_count != 1
            or self.status != "independent_program_and_contract_verified_no_execution_claim"
        ):
            raise DeepSeekV4MarkovCheckError("report counts or status differ")


def _expected_records() -> tuple[tuple[int, ...], ...]:
    # Register IDs: BASE=0, INITIAL=1, TEMP=2, ENTROPY_IN=3, TOKENS=4,
    # EMBEDDINGS=5, BIASES=6, ADJUSTED=7, ENTROPY_OUT=8.
    records: list[tuple[int, ...]] = []
    for step in range(_BLOCK_SIZE):
        token_source = 1 if step == 0 else 4
        entropy_source = 3 if step == 0 else 8
        records.extend(
            (
                (1, step, 5, token_source, _NO, _NO, 0, 0),
                (2, step, 6, 5, _NO, _NO, 1, 0),
                (3, step, 7, 0, 6, _NO, _NO, 0),
                (4, step, 4, 7, 2, entropy_source, _NO, 0),
            )
        )
    records.append((0xFFFF, 5, 4, 7, 5, 8, _NO, 0))
    return tuple(records)


def _expected_contract(program_sha256: str) -> dict[str, Any]:
    micro_ops = [
        {"opcode": _OPCODE_NAMES[record[0]], "step": record[1]}
        for record in _expected_records()
    ]
    return {
        "abi": {"major": 1, "minor": 0},
        "causal_contract": {
            "block_size": 5,
            "entropy_order": "step_then_batch_then_vocabulary",
            "greedy_policy": "finite_binary32_first_index_argmax_exact",
            "initial_token_output_column": 0,
            "sampled_token_carry": (
                "sample_at_step_i_writes_token_column_i_plus_1_consumed_at_next_step"
            ),
            "stochastic_source_replay": (
                "fail_closed_unpinned_torch_cuda_rng_exponential_softmax_backend"
            ),
            "target_adaptation": "explicit_positive_binary32_post_exponential_draws",
        },
        "instruction_count": 21,
        "micro_ops": micro_ops,
        "model_id": _MODEL_ID,
        "numeric_contract": {
            "bias_add": "separate_binary32_rne",
            "embedding_storage": "BF16",
            "head_accumulator": "binary32",
            "head_reduction": "increasing_markov_rank_rne_fused_product_add",
            "head_storage": "BF16",
            "subnormals": "preserve",
        },
        "numeric_profile": _NUMERIC_PROFILE,
        "outputs": {
            "adjusted_logits": "binary32[B,5,V]",
            "embeddings": "BF16[B,5,R]",
            "entropy_continuation": "immutable_explicit_stream_continuation",
            "tokens": "u32[B,6]",
        },
        "program_sha256": program_sha256,
        "registers": [
            {"id": index, "name": name}
            for index, name in enumerate(_REGISTER_NAMES)
        ],
        "resources": [
            {
                "dtype": "BF16",
                "id": 0,
                "name": "mtp.2.markov_head.markov_w1.weight",
                "official_shape": [129_280, 256],
                "partition": "equal_contiguous_vocabulary_rows",
            },
            {
                "dtype": "BF16",
                "id": 1,
                "name": "mtp.2.markov_head.markov_w2.weight",
                "official_shape": [129_280, 256],
                "partition": "equal_contiguous_vocabulary_rows",
            },
        ],
        "schema": _PROGRAM_SCHEMA,
        "source": {
            "model_repository": _MODEL_REPOSITORY,
            "model_revision": _MODEL_REVISION,
            "model_source_sha256": _MODEL_SOURCE_SHA256,
        },
        "status": "compiler_contract_verified_execution_separately_required",
        "timing_claim": None,
        "unsupported_claims": list(_NONCLAIMS),
    }


def verify_deepseek_v4_markov_program(
    payload: object,
    contract: object,
) -> MarkovProgramVerificationReport:
    """Independently verify exact wire records and the causal contract."""

    if type(payload) is not bytes or len(payload) < _HEADER.size:
        raise DeepSeekV4MarkovCheckError("program payload is truncated")
    magic, major, minor, count, record_size, body_digest = _HEADER.unpack_from(payload)
    if magic != _MAGIC or (major, minor) != _ABI:
        raise DeepSeekV4MarkovCheckError("program ABI identity differs")
    if count != _INSTRUCTION_COUNT or record_size != _RECORD.size:
        raise DeepSeekV4MarkovCheckError("program record contract differs")
    body = payload[_HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4MarkovCheckError("program body extent differs")
    if hashlib.sha256(body).digest() != body_digest:
        raise DeepSeekV4MarkovCheckError("program body digest differs")
    records = tuple(
        _RECORD.unpack_from(body, offset)
        for offset in range(0, len(body), _RECORD.size)
    )
    expected_records = _expected_records()
    for index, (record, expected) in enumerate(
        zip(records, expected_records, strict=True)
    ):
        if record != expected:
            raise DeepSeekV4MarkovCheckError(
                f"program record {index} differs from the causal authority"
            )
    program_sha256 = hashlib.sha256(payload).hexdigest()
    expected_contract = _expected_contract(program_sha256)
    if type(contract) is not dict:
        raise DeepSeekV4MarkovCheckError("program contract must be an exact object")
    try:
        equal = canonical_json_bytes(contract) == canonical_json_bytes(
            expected_contract
        )
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4MarkovCheckError(
            "program contract is not canonical JSON"
        ) from exc
    if not equal:
        raise DeepSeekV4MarkovCheckError("program contract differs")
    return MarkovProgramVerificationReport(
        program_sha256=program_sha256,
        instruction_count=count,
        block_size=_BLOCK_SIZE,
        lookup_count=_BLOCK_SIZE,
        projection_count=_BLOCK_SIZE,
        bias_add_count=_BLOCK_SIZE,
        sampling_count=_BLOCK_SIZE,
        complete_count=1,
        status="independent_program_and_contract_verified_no_execution_claim",
    )


__all__ = [
    "DeepSeekV4MarkovCheckError",
    "MarkovProgramVerificationReport",
    "verify_deepseek_v4_markov_program",
]
