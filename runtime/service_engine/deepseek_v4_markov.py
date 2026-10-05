"""Reference-independent service execution for DeepSeek V4 Markov microcode.

The service accepts the fixed 21-record program plus caller-supplied BF16 W1/W2
shards, finite binary32 base logits, an initial token per batch, and an explicit
sampling boundary.  It decodes and independently verifies every wire
record, then dispatches lookup, projection, separate bias-add, sampling/carry,
and completion operations in program order.

This module imports no compiler, checkpoint reader, safetensors code, runtime
reference, expected output, or implicit RNG.  It reuses only service-lane scalar
binary32 primitives.  Records and counters are semantic, not timing slots or
physical traffic.  Checkpoint authentication, checkpoint-derived base logits,
complete official-vocabulary execution, collectives, speculative acceptance,
RTL, full-model execution, cycles, bandwidth, PPA, and performance comparison
remain outside this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import struct
from types import MappingProxyType
from typing import TypeAlias

from .hc_pre_numeric import (
    HCPreServiceNumericError,
    cr32_exp,
    rn32_add,
    rn32_balanced_sum,
    rn32_divide,
    rn32_fused_product_add,
)


SERVICE_NUMERIC_PROFILE = "opentallas.deepseek_v4_markov_microprogram_service.v1"
MARKOV_NUMERIC_PROFILE = "opentallas.deepseek_v4_markov_loop_binary32.v1"
GREEDY_NUMERIC_PROFILE = "finite_binary32_first_index_argmax_v1"
TARGET_STOCHASTIC_NUMERIC_PROFILE = (
    "cr32_exp_balanced_softmax_explicit_binary32_exponential_race_v1"
)
PYTORCH_STOCHASTIC_EQUIVALENCE = (
    "unresolved_unpinned_torch_cuda_rng_exponential_softmax_backend"
)
PROGRAM_SHA256 = "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MARKOV_RANK = 256
OFFICIAL_MAX_BATCH_SIZE = 4
OFFICIAL_BLOCK_SIZE = 5
OFFICIAL_WORLD_SIZES = (1, 2, 4, 8)
BINARY32_MINIMUM_TEMPERATURE = 0x3727C5AC
BINARY32_ONE = 0x3F800000

_MAGIC = b"OTMKV1\0\0"
_HEADER = struct.Struct("<8sHHII32s")
_RECORD = struct.Struct("<HHHHHHHH")
_NO = 0xFFFF
_INSTRUCTION_COUNT = 21
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Batch5: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Batch5: TypeAlias = tuple[tuple[Binary32Vector, ...], ...]
TokenRows: TypeAlias = tuple[tuple[int, ...], ...]

EXCLUDED_CLAIMS = (
    "checkpoint_or_artifact_authentication",
    "checkpoint_derived_base_logits",
    "complete_official_vocabulary_execution",
    "exact_nonzero_temperature_pytorch_cuda_replay",
    "confidence_target_verification_or_speculative_acceptance",
    "physical_collective_or_memory_traffic",
    "physical_schedule_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
    "rtl_or_full_model_execution",
)


class DeepSeekV4MarkovServiceError(ValueError):
    """Raised when a complete Markov service command must poison atomically."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be an exact list or tuple"
        )
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be a deeply immutable exact tuple"
        )
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    if value & 0x7F80 == 0x7F80:
        raise DeepSeekV4MarkovServiceError(f"{label} must be finite BF16")
    return value


def _finite_binary32(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 32:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be an exact binary32 encoding"
        )
    if value & 0x7F800000 == 0x7F800000:
        raise DeepSeekV4MarkovServiceError(f"{label} must be finite binary32")
    return value


def _positive_binary32(value: object, label: str) -> int:
    code = _finite_binary32(value, label)
    if code == 0 or code & 0x80000000:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must be positive finite binary32"
        )
    return code


def _order_key(code: int) -> int:
    """Map canonical finite binary32 codes to monotonic unsigned keys."""

    if code & 0x7FFFFFFF == 0:
        code = 0
    return (~code & 0xFFFFFFFF) if code & 0x80000000 else code | 0x80000000


def _first_argmax(row: Binary32Vector) -> int:
    best_index = 0
    best_key = _order_key(row[0])
    for index, code in enumerate(row[1:], 1):
        key = _order_key(code)
        if key > best_key:
            best_index = index
            best_key = key
    return best_index


def _negate(code: int) -> int:
    return 0 if code == 0 else code ^ 0x80000000


def _bf16_to_binary32(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code << 16


def _hash_bf16_rows(rows: BF16Matrix) -> str:
    digest = hashlib.sha256()
    for row in rows:
        for code in row:
            digest.update(code.to_bytes(2, "little"))
    return digest.hexdigest()


def _hash_tensor3(
    value: tuple[tuple[tuple[int, ...], ...], ...],
    *,
    bytes_per_value: int,
    domain: bytes,
) -> str:
    digest = hashlib.sha256()
    digest.update(domain)
    dimensions = (
        len(value),
        len(value[0]) if value else 0,
        len(value[0][0]) if value and value[0] else 0,
    )
    for dimension in dimensions:
        digest.update(dimension.to_bytes(8, "little"))
    for batch in value:
        for row in batch:
            for code in row:
                digest.update(code.to_bytes(bytes_per_value, "little"))
    return digest.hexdigest()


def _hash_tokens(value: TokenRows) -> str:
    digest = hashlib.sha256()
    digest.update(b"opentallas.deepseek_v4_markov_output_tokens.v1\x00")
    digest.update(len(value).to_bytes(8, "little"))
    digest.update((len(value[0]) if value else 0).to_bytes(8, "little"))
    for row in value:
        for token in row:
            digest.update(token.to_bytes(4, "little"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class MarkovServiceEntropy:
    """Immutable service-lane stream of post-exponential binary32 draws."""

    binary32_codes: tuple[int, ...]
    offset: int = 0

    def __post_init__(self) -> None:
        if type(self.binary32_codes) is not tuple:
            raise DeepSeekV4MarkovServiceError(
                "entropy binary32_codes must be an immutable tuple"
            )
        for index, code in enumerate(self.binary32_codes):
            _positive_binary32(code, f"entropy binary32_codes[{index}]")
        _integer(
            self.offset,
            "entropy offset",
            minimum=0,
            maximum=len(self.binary32_codes),
        )

    @classmethod
    def from_codes(cls, value: object) -> MarkovServiceEntropy:
        raw = _sequence(value, "entropy binary32_codes")
        return cls(tuple(raw))

    @property
    def remaining(self) -> int:
        return len(self.binary32_codes) - self.offset

    @property
    def stream_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(b"opentallas.explicit_exponential_entropy.v1\x00")
        digest.update((1).to_bytes(8, "little"))
        digest.update(len(self.binary32_codes).to_bytes(8, "little"))
        for code in self.binary32_codes:
            digest.update(code.to_bytes(4, "little"))
        return digest.hexdigest()

    def take(self, count: int) -> tuple[tuple[int, ...], MarkovServiceEntropy]:
        count = _integer(
            count,
            "entropy draw count",
            minimum=0,
            maximum=(1 << 63) - 1,
        )
        stop = self.offset + count
        if stop > len(self.binary32_codes):
            raise DeepSeekV4MarkovServiceError(
                f"explicit exponential entropy exhausted: need {count}, "
                f"have {self.remaining}"
            )
        return self.binary32_codes[self.offset : stop], replace(self, offset=stop)


def _expected_program_records() -> tuple[tuple[int, ...], ...]:
    records: list[tuple[int, ...]] = []
    for step in range(OFFICIAL_BLOCK_SIZE):
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


def _decode_program(payload: object) -> tuple[tuple[int, ...], ...]:
    if type(payload) is not bytes or len(payload) < _HEADER.size:
        raise DeepSeekV4MarkovServiceError("microcode is truncated")
    magic, major, minor, count, record_size, body_digest = _HEADER.unpack_from(payload)
    if magic != _MAGIC or (major, minor) != (1, 0):
        raise DeepSeekV4MarkovServiceError("microcode ABI identity differs")
    if count != _INSTRUCTION_COUNT or record_size != _RECORD.size:
        raise DeepSeekV4MarkovServiceError("microcode record contract differs")
    body = payload[_HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4MarkovServiceError("microcode body extent differs")
    if hashlib.sha256(body).digest() != body_digest:
        raise DeepSeekV4MarkovServiceError("microcode body digest differs")
    records = tuple(
        _RECORD.unpack_from(body, offset)
        for offset in range(0, len(body), _RECORD.size)
    )
    for index, (record, expected) in enumerate(
        zip(records, _expected_program_records(), strict=True)
    ):
        if record != expected:
            raise DeepSeekV4MarkovServiceError(
                f"microcode instruction {index} differs from the causal contract"
            )
    if _sha256(payload) != PROGRAM_SHA256:
        raise DeepSeekV4MarkovServiceError("microcode complete identity differs")
    return records


def _freeze_weight_shards(
    value: object,
    *,
    label: str,
    world_size: int,
    expected_rows: int | None = None,
    expected_rank: int | None = None,
) -> tuple[BF16Matrix, int, int]:
    raw_shards = _sequence(value, label)
    if len(raw_shards) != world_size:
        raise DeepSeekV4MarkovServiceError(
            f"{label} must contain one shard per tensor-parallel rank"
        )
    rows_per_rank = expected_rows
    rank_width = expected_rank
    frozen: list[BF16Vector] = []
    for shard_index, raw_shard in enumerate(raw_shards):
        shard = _sequence(raw_shard, f"{label}[{shard_index}]")
        if rows_per_rank is None:
            rows_per_rank = len(shard)
            if rows_per_rank < 1:
                raise DeepSeekV4MarkovServiceError(
                    f"{label} shards must contain rows"
                )
        elif len(shard) != rows_per_rank:
            raise DeepSeekV4MarkovServiceError(
                f"{label} shards must have equal row counts"
            )
        for local_row, raw_row in enumerate(shard):
            row = _sequence(raw_row, f"{label}[{shard_index}][{local_row}]")
            if rank_width is None:
                rank_width = len(row)
                if not 1 <= rank_width <= OFFICIAL_MARKOV_RANK:
                    raise DeepSeekV4MarkovServiceError(
                        f"{label} Markov rank is outside the official bound"
                    )
            elif len(row) != rank_width:
                raise DeepSeekV4MarkovServiceError(
                    f"{label} rows must have equal width"
                )
            frozen.append(
                tuple(
                    _finite_bf16(
                        code,
                        f"{label}[{shard_index}][{local_row}][{column}]",
                    )
                    for column, code in enumerate(row)
                )
            )
    assert rows_per_rank is not None and rank_width is not None
    if rows_per_rank * world_size > OFFICIAL_VOCABULARY_SIZE:
        raise DeepSeekV4MarkovServiceError(
            f"{label} vocabulary exceeds the official bound"
        )
    return tuple(frozen), rows_per_rank, rank_width


def _freeze_logits(value: object, vocabulary_size: int) -> Binary32Batch5:
    raw_batches = _sequence(value, "base_logits_binary32_codes")
    if not 1 <= len(raw_batches) <= OFFICIAL_MAX_BATCH_SIZE:
        raise DeepSeekV4MarkovServiceError(
            "base-logit batch extent is outside the official bound"
        )
    batches: list[tuple[Binary32Vector, ...]] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(
            raw_sequence, f"base_logits_binary32_codes[{batch_index}]"
        )
        if len(sequence) != OFFICIAL_BLOCK_SIZE:
            raise DeepSeekV4MarkovServiceError(
                f"base logits batch {batch_index} must contain five rows"
            )
        rows: list[Binary32Vector] = []
        for step, raw_row in enumerate(sequence):
            row = _sequence(
                raw_row, f"base_logits_binary32_codes[{batch_index}][{step}]"
            )
            if len(row) != vocabulary_size:
                raise DeepSeekV4MarkovServiceError(
                    f"base logits [{batch_index}][{step}] vocabulary width differs"
                )
            rows.append(
                tuple(
                    _finite_binary32(
                        code,
                        f"base_logits_binary32_codes[{batch_index}]"
                        f"[{step}][{column}]",
                    )
                    for column, code in enumerate(row)
                )
            )
        batches.append(tuple(rows))
    return tuple(batches)


def _freeze_tokens(
    value: object,
    *,
    batch_count: int,
    vocabulary_size: int,
) -> tuple[int, ...]:
    raw = _sequence(value, "input_token_ids")
    if len(raw) != batch_count:
        raise DeepSeekV4MarkovServiceError(
            "input-token count must equal the base-logit batch extent"
        )
    return tuple(
        _integer(
            token,
            f"input_token_ids[{batch}]",
            minimum=0,
            maximum=vocabulary_size - 1,
        )
        for batch, token in enumerate(raw)
    )


def _project(
    embeddings: tuple[BF16Vector, ...],
    head_weights: BF16Matrix,
) -> tuple[Binary32Vector, ...]:
    output: list[Binary32Vector] = []
    for batch, embedding in enumerate(embeddings):
        row: list[int] = []
        for vocabulary_index, weight in enumerate(head_weights):
            accumulator = 0
            try:
                for embedding_code, weight_code in zip(
                    embedding, weight, strict=True
                ):
                    accumulator = rn32_fused_product_add(
                        accumulator,
                        _bf16_to_binary32(embedding_code),
                        _bf16_to_binary32(weight_code),
                    )
            except HCPreServiceNumericError as exc:
                raise DeepSeekV4MarkovServiceError(
                    f"projection failed at batch {batch}, vocabulary row "
                    f"{vocabulary_index}: {exc}"
                ) from exc
            row.append(accumulator)
        output.append(tuple(row))
    return tuple(output)


def _add_bias(
    base_rows: tuple[Binary32Vector, ...],
    bias_rows: tuple[Binary32Vector, ...],
) -> tuple[Binary32Vector, ...]:
    output: list[Binary32Vector] = []
    for batch, (base, bias) in enumerate(zip(base_rows, bias_rows, strict=True)):
        try:
            output.append(
                tuple(
                    rn32_add(base_code, bias_code)
                    for base_code, bias_code in zip(base, bias, strict=True)
                )
            )
        except HCPreServiceNumericError as exc:
            raise DeepSeekV4MarkovServiceError(
                f"separate bias addition failed at batch {batch}: {exc}"
            ) from exc
    return tuple(output)


def _sample_stochastic_row(
    row: Binary32Vector,
    draws: tuple[int, ...],
    effective_temperature: int,
    row_index: int,
) -> int:
    try:
        scaled = tuple(
            rn32_divide(code, effective_temperature) for code in row
        )
        maximum = max(scaled, key=_order_key)
        shifted = tuple(rn32_add(code, _negate(maximum)) for code in scaled)
        exponentials = tuple(cr32_exp(code) for code in shifted)
        denominator = rn32_balanced_sum(exponentials)
        probabilities = tuple(
            rn32_divide(code, denominator) for code in exponentials
        )
        race_scores = tuple(
            rn32_divide(probability, draw)
            for probability, draw in zip(probabilities, draws, strict=True)
        )
    except HCPreServiceNumericError as exc:
        raise DeepSeekV4MarkovServiceError(
            f"target sampling arithmetic failed at batch row {row_index}: {exc}"
        ) from exc
    return _first_argmax(race_scores)


def _sample(
    rows: tuple[Binary32Vector, ...],
    *,
    temperature: int,
    entropy: MarkovServiceEntropy | None,
    require_pytorch_cuda_equivalence: bool,
) -> tuple[tuple[int, ...], MarkovServiceEntropy | None, int, str, str]:
    if temperature & 0x7FFFFFFF == 0:
        return (
            tuple(_first_argmax(row) for row in rows),
            entropy,
            0,
            "greedy_argmax",
            "bit_exact_for_validated_finite_binary32_inputs",
        )
    if require_pytorch_cuda_equivalence:
        raise DeepSeekV4MarkovServiceError(
            "exact nonzero-temperature PyTorch/CUDA replay is unresolved"
        )
    if type(entropy) is not MarkovServiceEntropy:
        raise DeepSeekV4MarkovServiceError(
            "nonzero-temperature target sampling requires explicit entropy"
        )
    value_count = len(rows) * len(rows[0])
    draws, next_entropy = entropy.take(value_count)
    effective_temperature = (
        BINARY32_MINIMUM_TEMPERATURE
        if _order_key(temperature) < _order_key(BINARY32_MINIMUM_TEMPERATURE)
        else temperature
    )
    tokens: list[int] = []
    width = len(rows[0])
    for row_index, row in enumerate(rows):
        start = row_index * width
        tokens.append(
            _sample_stochastic_row(
                row,
                draws[start : start + width],
                effective_temperature,
                row_index,
            )
        )
    return (
        tuple(tokens),
        next_entropy,
        value_count,
        "explicit_exponential_race_target_adaptation",
        PYTORCH_STOCHASTIC_EQUIVALENCE,
    )


def _counter_values(
    *,
    batch_count: int,
    vocabulary_size: int,
    markov_rank: int,
    world_size: int,
    entropy_draws: int,
) -> dict[str, int]:
    token_steps = batch_count * OFFICIAL_BLOCK_SIZE
    logit_values = token_steps * vocabulary_size
    products = logit_values * markov_rank
    return {
        "batch_count": batch_count,
        "block_size": OFFICIAL_BLOCK_SIZE,
        "vocabulary_size": vocabulary_size,
        "markov_rank": markov_rank,
        "tensor_parallel_world_size": world_size,
        "partition_vocabulary_rows": vocabulary_size // world_size,
        "loop_iterations": OFFICIAL_BLOCK_SIZE,
        "micro_ops_executed": _INSTRUCTION_COUNT,
        "lookup_micro_ops": OFFICIAL_BLOCK_SIZE,
        "projection_micro_ops": OFFICIAL_BLOCK_SIZE,
        "bias_add_micro_ops": OFFICIAL_BLOCK_SIZE,
        "sampling_micro_ops": OFFICIAL_BLOCK_SIZE,
        "complete_micro_ops": 1,
        "initial_token_values_read": batch_count,
        "initial_token_values_written": batch_count,
        "causal_token_values_read": token_steps,
        "base_logit_binary32_values_validated": logit_values,
        "base_logit_binary32_values_read": logit_values,
        "embedding_weight_bf16_values_validated": vocabulary_size * markov_rank,
        "head_weight_bf16_values_validated": vocabulary_size * markov_rank,
        "embedding_row_lookups": token_steps,
        "embedding_bf16_values_read": token_steps * markov_rank,
        "embedding_bf16_values_written": token_steps * markov_rank,
        "embedding_binary32_widens": token_steps * markov_rank,
        "head_weight_binary32_widens": vocabulary_size * markov_rank,
        "exact_product_accumulates": products,
        "binary32_accumulation_roundings": products,
        "markov_bias_binary32_values_written": logit_values,
        "binary32_bias_additions": logit_values,
        "adjusted_logit_binary32_values_written": logit_values,
        "sampling_calls": OFFICIAL_BLOCK_SIZE,
        "sampling_logit_binary32_values_read": logit_values,
        "sampling_argmax_comparisons": token_steps * (vocabulary_size - 1),
        "sampling_entropy_draws_consumed": entropy_draws,
        "sampled_token_values_written": token_steps,
        "output_token_values_written": batch_count * (OFFICIAL_BLOCK_SIZE + 1),
        "transaction_commits": 1,
    }


@dataclass(frozen=True, slots=True)
class MarkovServiceResult:
    """Immutable microprogram outputs, identities, and semantic counters."""

    service_numeric_profile: str
    markov_numeric_profile: str
    sampling_numeric_profile: str
    sampling_mode: str
    source_equivalence: str
    program_sha256: str
    temperature_binary32: int
    require_pytorch_cuda_equivalence: bool
    tensor_parallel_world_size: int
    vocabulary_size: int
    markov_rank: int
    input_token_ids: tuple[int, ...]
    output_token_ids: TokenRows
    base_logits_binary32_codes: Binary32Batch5
    markov_bias_binary32_codes: Binary32Batch5
    adjusted_logits_binary32_codes: Binary32Batch5
    markov_embeddings_bf16_codes: BF16Batch5
    embedding_weight_bf16_sha256: str
    head_weight_bf16_sha256: str
    base_logits_binary32_sha256: str
    markov_bias_binary32_sha256: str
    adjusted_logits_binary32_sha256: str
    markov_embeddings_bf16_sha256: str
    output_token_ids_sha256: str
    entropy_stream_sha256: str | None
    entropy_offset_before: int | None
    entropy_offset_after: int | None
    next_entropy: MarkovServiceEntropy | None
    logical_counters: MappingProxyType
    excluded_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_result(self)

    @property
    def semantic_counters(self) -> MappingProxyType:
        return self.logical_counters


def _validate_result(value: object) -> MarkovServiceResult:
    if type(value) is not MarkovServiceResult:
        raise DeepSeekV4MarkovServiceError(
            "result must be an exact MarkovServiceResult"
        )
    if (
        value.service_numeric_profile != SERVICE_NUMERIC_PROFILE
        or value.markov_numeric_profile != MARKOV_NUMERIC_PROFILE
        or value.program_sha256 != PROGRAM_SHA256
        or value.excluded_claims != EXCLUDED_CLAIMS
        or type(value.require_pytorch_cuda_equivalence) is not bool
    ):
        raise DeepSeekV4MarkovServiceError("result authority metadata differs")
    temperature = _finite_binary32(
        value.temperature_binary32, "result.temperature_binary32"
    )
    if type(value.logical_counters) is not _MAPPING_PROXY_TYPE:
        raise DeepSeekV4MarkovServiceError("result counters must be a mapping proxy")
    counters = dict(value.logical_counters)
    required = set(
        _counter_values(
            batch_count=1,
            vocabulary_size=1,
            markov_rank=1,
            world_size=1,
            entropy_draws=0,
        )
    )
    if set(counters) != required or any(
        type(item) is not int for item in counters.values()
    ):
        raise DeepSeekV4MarkovServiceError("result counter schema differs")
    batch_count = _integer(
        counters["batch_count"],
        "result counter batch_count",
        minimum=1,
        maximum=OFFICIAL_MAX_BATCH_SIZE,
    )
    vocabulary_size = _integer(
        counters["vocabulary_size"],
        "result counter vocabulary_size",
        minimum=1,
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    markov_rank = _integer(
        counters["markov_rank"],
        "result counter markov_rank",
        minimum=1,
        maximum=OFFICIAL_MARKOV_RANK,
    )
    world_size = counters["tensor_parallel_world_size"]
    if world_size not in OFFICIAL_WORLD_SIZES or vocabulary_size % world_size:
        raise DeepSeekV4MarkovServiceError("result tensor-parallel topology differs")
    entropy_draws = counters["sampling_entropy_draws_consumed"]
    maximum_draws = batch_count * OFFICIAL_BLOCK_SIZE * vocabulary_size
    if entropy_draws not in {0, maximum_draws}:
        raise DeepSeekV4MarkovServiceError("result entropy count differs")
    if counters != _counter_values(
        batch_count=batch_count,
        vocabulary_size=vocabulary_size,
        markov_rank=markov_rank,
        world_size=world_size,
        entropy_draws=entropy_draws,
    ):
        raise DeepSeekV4MarkovServiceError("result counters do not reconcile")
    if (
        value.tensor_parallel_world_size != world_size
        or value.vocabulary_size != vocabulary_size
        or value.markov_rank != markov_rank
    ):
        raise DeepSeekV4MarkovServiceError("result dimensions differ from counters")
    inputs = _exact_tuple(value.input_token_ids, "result.input_token_ids")
    outputs = _exact_tuple(value.output_token_ids, "result.output_token_ids")
    if len(inputs) != batch_count or len(outputs) != batch_count:
        raise DeepSeekV4MarkovServiceError("result token batch extent differs")
    for batch, (input_token, raw_output) in enumerate(
        zip(inputs, outputs, strict=True)
    ):
        token = _integer(
            input_token,
            f"result.input_token_ids[{batch}]",
            minimum=0,
            maximum=vocabulary_size - 1,
        )
        row = _exact_tuple(raw_output, f"result.output_token_ids[{batch}]")
        if len(row) != OFFICIAL_BLOCK_SIZE + 1 or row[0] != token:
            raise DeepSeekV4MarkovServiceError(
                "result output tokens do not retain the initial column"
            )
        for step, item in enumerate(row):
            _integer(
                item,
                f"result.output_token_ids[{batch}][{step}]",
                minimum=0,
                maximum=vocabulary_size - 1,
            )

    def tensor3(raw: object, label: str, width: int, bf16: bool) -> tuple:
        batches = _exact_tuple(raw, label)
        if len(batches) != batch_count:
            raise DeepSeekV4MarkovServiceError(f"{label} batch extent differs")
        output_batches: list[tuple] = []
        for batch, raw_sequence in enumerate(batches):
            sequence = _exact_tuple(raw_sequence, f"{label}[{batch}]")
            if len(sequence) != OFFICIAL_BLOCK_SIZE:
                raise DeepSeekV4MarkovServiceError(f"{label} step extent differs")
            output_rows: list[tuple[int, ...]] = []
            for step, raw_row in enumerate(sequence):
                row = _exact_tuple(raw_row, f"{label}[{batch}][{step}]")
                if len(row) != width:
                    raise DeepSeekV4MarkovServiceError(f"{label} width differs")
                output_rows.append(
                    tuple(
                        (
                            _finite_bf16(
                                code, f"{label}[{batch}][{step}][{column}]"
                            )
                            if bf16
                            else _finite_binary32(
                                code, f"{label}[{batch}][{step}][{column}]"
                            )
                        )
                        for column, code in enumerate(row)
                    )
                )
            output_batches.append(tuple(output_rows))
        return tuple(output_batches)

    base = tensor3(
        value.base_logits_binary32_codes,
        "result.base_logits_binary32_codes",
        vocabulary_size,
        False,
    )
    bias = tensor3(
        value.markov_bias_binary32_codes,
        "result.markov_bias_binary32_codes",
        vocabulary_size,
        False,
    )
    adjusted = tensor3(
        value.adjusted_logits_binary32_codes,
        "result.adjusted_logits_binary32_codes",
        vocabulary_size,
        False,
    )
    embeddings = tensor3(
        value.markov_embeddings_bf16_codes,
        "result.markov_embeddings_bf16_codes",
        markov_rank,
        True,
    )
    for batch in range(batch_count):
        for step in range(OFFICIAL_BLOCK_SIZE):
            for column in range(vocabulary_size):
                try:
                    expected = rn32_add(
                        base[batch][step][column], bias[batch][step][column]
                    )
                except HCPreServiceNumericError as exc:  # pragma: no cover
                    raise DeepSeekV4MarkovServiceError(
                        "result bias reconciliation failed"
                    ) from exc
                if adjusted[batch][step][column] != expected:
                    raise DeepSeekV4MarkovServiceError(
                        "result adjusted logits differ from base plus bias"
                    )
    hashes = {
        "base_logits_binary32_sha256": _hash_tensor3(
            base,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_base_logits.v1\x00",
        ),
        "markov_bias_binary32_sha256": _hash_tensor3(
            bias,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_bias.v1\x00",
        ),
        "adjusted_logits_binary32_sha256": _hash_tensor3(
            adjusted,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_adjusted_logits.v1\x00",
        ),
        "markov_embeddings_bf16_sha256": _hash_tensor3(
            embeddings,
            bytes_per_value=2,
            domain=b"opentallas.deepseek_v4_markov_embeddings.v1\x00",
        ),
        "output_token_ids_sha256": _hash_tokens(outputs),
    }
    for name, expected in hashes.items():
        if getattr(value, name) != expected:
            raise DeepSeekV4MarkovServiceError(f"result {name} differs")
    for name in ("embedding_weight_bf16_sha256", "head_weight_bf16_sha256"):
        digest = getattr(value, name)
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise DeepSeekV4MarkovServiceError(f"result {name} differs")
    if temperature & 0x7FFFFFFF == 0:
        if (
            value.sampling_mode != "greedy_argmax"
            or value.sampling_numeric_profile != GREEDY_NUMERIC_PROFILE
            or value.source_equivalence
            != "bit_exact_for_validated_finite_binary32_inputs"
            or entropy_draws != 0
        ):
            raise DeepSeekV4MarkovServiceError("result greedy metadata differs")
    elif (
        value.sampling_mode != "explicit_exponential_race_target_adaptation"
        or value.sampling_numeric_profile != TARGET_STOCHASTIC_NUMERIC_PROFILE
        or value.source_equivalence != PYTORCH_STOCHASTIC_EQUIVALENCE
        or value.require_pytorch_cuda_equivalence
        or entropy_draws != maximum_draws
    ):
        raise DeepSeekV4MarkovServiceError("result stochastic metadata differs")
    if value.next_entropy is None:
        if any(
            item is not None
            for item in (
                value.entropy_stream_sha256,
                value.entropy_offset_before,
                value.entropy_offset_after,
            )
        ):
            raise DeepSeekV4MarkovServiceError("result entropy metadata differs")
    else:
        if type(value.next_entropy) is not MarkovServiceEntropy:
            raise DeepSeekV4MarkovServiceError("result entropy type differs")
        if (
            value.entropy_stream_sha256 != value.next_entropy.stream_sha256
            or value.entropy_offset_after != value.next_entropy.offset
            or type(value.entropy_offset_before) is not int
            or value.entropy_offset_after
            != value.entropy_offset_before + entropy_draws
        ):
            raise DeepSeekV4MarkovServiceError("result entropy continuation differs")

    replay_entropy = (
        None
        if value.next_entropy is None
        else MarkovServiceEntropy(
            value.next_entropy.binary32_codes,
            value.entropy_offset_before,
        )
    )
    replay_mode: str | None = None
    replay_equivalence: str | None = None
    for step in range(OFFICIAL_BLOCK_SIZE):
        rows = tuple(adjusted[batch][step] for batch in range(batch_count))
        (
            sampled,
            replay_entropy,
            _,
            step_mode,
            step_equivalence,
        ) = _sample(
            rows,
            temperature=temperature,
            entropy=replay_entropy,
            require_pytorch_cuda_equivalence=(
                value.require_pytorch_cuda_equivalence
            ),
        )
        expected_tokens = tuple(
            outputs[batch][step + 1] for batch in range(batch_count)
        )
        if sampled != expected_tokens:
            raise DeepSeekV4MarkovServiceError(
                f"result causal sampling differs at step {step}"
            )
        if replay_mode is None:
            replay_mode = step_mode
            replay_equivalence = step_equivalence
        elif (
            replay_mode != step_mode
            or replay_equivalence != step_equivalence
        ):  # pragma: no cover - one immutable transaction profile
            raise DeepSeekV4MarkovServiceError(
                "result causal sampling profile changed"
            )
    if (
        replay_entropy != value.next_entropy
        or replay_mode != value.sampling_mode
        or replay_equivalence != value.source_equivalence
    ):
        raise DeepSeekV4MarkovServiceError(
            "result causal sampling continuation differs"
        )
    return value


def execute_deepseek_v4_markov_program(
    program_payload: object,
    base_logits_binary32_codes: object,
    input_token_ids: object,
    embedding_weight_shards_bf16_codes: object,
    head_weight_shards_bf16_codes: object,
    *,
    temperature_binary32: int = BINARY32_ONE,
    entropy: MarkovServiceEntropy | None = None,
    tensor_parallel_world_size: int = 4,
    require_pytorch_cuda_equivalence: bool = True,
) -> MarkovServiceResult:
    """Execute one exact fixed-program five-step Markov transaction."""

    records = _decode_program(program_payload)
    if (
        type(tensor_parallel_world_size) is not int
        or tensor_parallel_world_size not in OFFICIAL_WORLD_SIZES
    ):
        raise DeepSeekV4MarkovServiceError(
            "tensor_parallel_world_size must be exactly 1, 2, 4, or 8"
        )
    if type(require_pytorch_cuda_equivalence) is not bool:
        raise DeepSeekV4MarkovServiceError(
            "require_pytorch_cuda_equivalence must be an exact bool"
        )
    temperature = _finite_binary32(temperature_binary32, "temperature_binary32")
    if entropy is not None and type(entropy) is not MarkovServiceEntropy:
        raise DeepSeekV4MarkovServiceError(
            "entropy must be an exact MarkovServiceEntropy or None"
        )
    embedding_weights, rows_per_rank, rank_width = _freeze_weight_shards(
        embedding_weight_shards_bf16_codes,
        label="embedding_weight_shards_bf16_codes",
        world_size=tensor_parallel_world_size,
    )
    head_weights, head_rows, head_rank = _freeze_weight_shards(
        head_weight_shards_bf16_codes,
        label="head_weight_shards_bf16_codes",
        world_size=tensor_parallel_world_size,
        expected_rows=rows_per_rank,
        expected_rank=rank_width,
    )
    if head_rows != rows_per_rank or head_rank != rank_width:
        raise DeepSeekV4MarkovServiceError("W1 and W2 topology differs")
    vocabulary_size = rows_per_rank * tensor_parallel_world_size
    base_logits = _freeze_logits(base_logits_binary32_codes, vocabulary_size)
    initial_tokens = _freeze_tokens(
        input_token_ids,
        batch_count=len(base_logits),
        vocabulary_size=vocabulary_size,
    )

    output_tokens: list[list[int]] = [[token] for token in initial_tokens]
    embeddings_by_batch: list[list[BF16Vector]] = [
        [] for _ in initial_tokens
    ]
    bias_by_batch: list[list[Binary32Vector]] = [[] for _ in initial_tokens]
    adjusted_by_batch: list[list[Binary32Vector]] = [
        [] for _ in initial_tokens
    ]
    next_entropy = entropy
    entropy_draws = 0
    current_embeddings: tuple[BF16Vector, ...] | None = None
    current_biases: tuple[Binary32Vector, ...] | None = None
    current_adjusted: tuple[Binary32Vector, ...] | None = None
    sampling_mode: str | None = None
    source_equivalence: str | None = None
    committed = False

    for program_counter, record in enumerate(records):
        opcode, step = record[:2]
        if opcode == 1:
            current_embeddings = tuple(
                embedding_weights[output_tokens[batch][step]]
                for batch in range(len(initial_tokens))
            )
        elif opcode == 2:
            if current_embeddings is None:
                raise DeepSeekV4MarkovServiceError(
                    f"projection at pc {program_counter} lacks its lookup"
                )
            current_biases = _project(current_embeddings, head_weights)
        elif opcode == 3:
            if current_biases is None:
                raise DeepSeekV4MarkovServiceError(
                    f"bias add at pc {program_counter} lacks its projection"
                )
            current_adjusted = _add_bias(
                tuple(base_logits[batch][step] for batch in range(len(initial_tokens))),
                current_biases,
            )
        elif opcode == 4:
            if (
                current_embeddings is None
                or current_biases is None
                or current_adjusted is None
            ):
                raise DeepSeekV4MarkovServiceError(
                    f"sample at pc {program_counter} lacks causal inputs"
                )
            (
                sampled,
                next_entropy,
                consumed,
                step_mode,
                step_equivalence,
            ) = _sample(
                current_adjusted,
                temperature=temperature,
                entropy=next_entropy,
                require_pytorch_cuda_equivalence=require_pytorch_cuda_equivalence,
            )
            if sampling_mode is None:
                sampling_mode = step_mode
                source_equivalence = step_equivalence
            elif (
                sampling_mode != step_mode
                or source_equivalence != step_equivalence
            ):
                raise DeepSeekV4MarkovServiceError(
                    "sampling mode changed inside one transaction"
                )
            for batch, token in enumerate(sampled):
                embeddings_by_batch[batch].append(current_embeddings[batch])
                bias_by_batch[batch].append(current_biases[batch])
                adjusted_by_batch[batch].append(current_adjusted[batch])
                output_tokens[batch].append(token)
            entropy_draws += consumed
            current_embeddings = None
            current_biases = None
            current_adjusted = None
        elif opcode == 0xFFFF:
            if program_counter != len(records) - 1 or any(
                len(row) != OFFICIAL_BLOCK_SIZE + 1 for row in output_tokens
            ):
                raise DeepSeekV4MarkovServiceError(
                    "COMPLETE occurred before all causal outputs were available"
                )
            committed = True
        else:  # pragma: no cover - decoder proves the finite opcode set
            raise DeepSeekV4MarkovServiceError("decoded unsupported opcode")
    if not committed or sampling_mode is None or source_equivalence is None:
        raise DeepSeekV4MarkovServiceError("program ended without one valid COMPLETE")

    frozen_tokens = tuple(tuple(row) for row in output_tokens)
    frozen_embeddings = tuple(tuple(rows) for rows in embeddings_by_batch)
    frozen_bias = tuple(tuple(rows) for rows in bias_by_batch)
    frozen_adjusted = tuple(tuple(rows) for rows in adjusted_by_batch)
    counters = MappingProxyType(
        _counter_values(
            batch_count=len(initial_tokens),
            vocabulary_size=vocabulary_size,
            markov_rank=rank_width,
            world_size=tensor_parallel_world_size,
            entropy_draws=entropy_draws,
        )
    )
    entropy_stream_sha256 = entropy.stream_sha256 if entropy is not None else None
    entropy_before = entropy.offset if entropy is not None else None
    entropy_after = next_entropy.offset if next_entropy is not None else None
    sampling_profile = (
        GREEDY_NUMERIC_PROFILE
        if sampling_mode == "greedy_argmax"
        else TARGET_STOCHASTIC_NUMERIC_PROFILE
    )
    return MarkovServiceResult(
        service_numeric_profile=SERVICE_NUMERIC_PROFILE,
        markov_numeric_profile=MARKOV_NUMERIC_PROFILE,
        sampling_numeric_profile=sampling_profile,
        sampling_mode=sampling_mode,
        source_equivalence=source_equivalence,
        program_sha256=PROGRAM_SHA256,
        temperature_binary32=temperature,
        require_pytorch_cuda_equivalence=require_pytorch_cuda_equivalence,
        tensor_parallel_world_size=tensor_parallel_world_size,
        vocabulary_size=vocabulary_size,
        markov_rank=rank_width,
        input_token_ids=initial_tokens,
        output_token_ids=frozen_tokens,
        base_logits_binary32_codes=base_logits,
        markov_bias_binary32_codes=frozen_bias,
        adjusted_logits_binary32_codes=frozen_adjusted,
        markov_embeddings_bf16_codes=frozen_embeddings,
        embedding_weight_bf16_sha256=_hash_bf16_rows(embedding_weights),
        head_weight_bf16_sha256=_hash_bf16_rows(head_weights),
        base_logits_binary32_sha256=_hash_tensor3(
            base_logits,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_base_logits.v1\x00",
        ),
        markov_bias_binary32_sha256=_hash_tensor3(
            frozen_bias,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_bias.v1\x00",
        ),
        adjusted_logits_binary32_sha256=_hash_tensor3(
            frozen_adjusted,
            bytes_per_value=4,
            domain=b"opentallas.deepseek_v4_markov_adjusted_logits.v1\x00",
        ),
        markov_embeddings_bf16_sha256=_hash_tensor3(
            frozen_embeddings,
            bytes_per_value=2,
            domain=b"opentallas.deepseek_v4_markov_embeddings.v1\x00",
        ),
        output_token_ids_sha256=_hash_tokens(frozen_tokens),
        entropy_stream_sha256=entropy_stream_sha256,
        entropy_offset_before=entropy_before,
        entropy_offset_after=entropy_after,
        next_entropy=next_entropy,
        logical_counters=counters,
        excluded_claims=EXCLUDED_CLAIMS,
    )


__all__ = [
    "BINARY32_MINIMUM_TEMPERATURE",
    "BINARY32_ONE",
    "DeepSeekV4MarkovServiceError",
    "EXCLUDED_CLAIMS",
    "GREEDY_NUMERIC_PROFILE",
    "MARKOV_NUMERIC_PROFILE",
    "MarkovServiceEntropy",
    "MarkovServiceResult",
    "OFFICIAL_BLOCK_SIZE",
    "OFFICIAL_MARKOV_RANK",
    "OFFICIAL_VOCABULARY_SIZE",
    "PROGRAM_SHA256",
    "PYTORCH_STOCHASTIC_EQUIVALENCE",
    "SERVICE_NUMERIC_PROFILE",
    "TARGET_STOCHASTIC_NUMERIC_PROFILE",
    "execute_deepseek_v4_markov_program",
]
