"""Deterministic DeepSeek V4 DSpark Markov-loop semantics.

The pinned ``DSparkBlock.forward_head`` performs five causally ordered steps.
At step ``i`` it looks up the current token in the BF16 ``markov_w1`` table,
projects that embedding through the BF16 ``markov_w2`` vocabulary head into
binary32, adds the result to draft-logit row ``i`` with one binary32 RNE add,
and samples the adjusted row.  The sampled token becomes the lookup index for
the next step.  The returned token tensor includes the input token followed by
the five samples; adjusted logits and the five BF16 Markov embeddings are also
returned.

The vocabulary tables are supplied as equal, contiguous tensor-parallel
shards in rank order.  BF16 operands widen exactly, every Markov-head dot uses
an increasing-rank exact product followed by one binary32 RNE product-add, and
the logit-bias addition is a separate binary32 RNE boundary.

Sampling delegates to the qualified ``deepseek_v4_sample_binary32`` boundary.
Zero temperature is exact first-index argmax.  The official source default is
one, but its PyTorch/CUDA RNG, exponential transform, and softmax backend are
not pinned, so exact nonzero-temperature replay fails closed.  A caller may
explicitly select the separately named deterministic target adaptation and
provide an immutable stream of post-exponential binary32 draws.  Entropy is
threaded through all five steps without mutating caller state.

This is a functional numeric/control reference.  It does not authenticate
checkpoint bytes, establish draft-logit provenance, execute confidence or
speculative acceptance, model a physical collective or memory, or claim
cycles, latency, bandwidth, throughput, energy, area, routing, or PPA.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from fractions import Fraction
import hashlib
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_ordered_dot,
    decode_bf16,
    decode_binary32,
)
from .sampling import (
    BINARY32_ONE,
    GREEDY_NUMERIC_PROFILE,
    PYTORCH_STOCHASTIC_EQUIVALENCE,
    TARGET_STOCHASTIC_NUMERIC_PROFILE,
    ExplicitExponentialEntropy,
    SamplingReferenceError,
    SamplingResult,
    deepseek_v4_sample_binary32,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
CHECKPOINT_INDEX_SHA256 = (
    "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
)
CHECKPOINT_LOCK_ID = "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
CHECKPOINT_SHARD = "model-00048-of-00048.safetensors"
MARKOV_LOOP_NUMERIC_PROFILE = "opentallas.deepseek_v4_markov_loop_binary32.v1"

OFFICIAL_VOCABULARY_SIZE = 129_280
OFFICIAL_MARKOV_RANK = 256
OFFICIAL_BLOCK_SIZE = 5
OFFICIAL_OUTPUT_TOKEN_COUNT = OFFICIAL_BLOCK_SIZE + 1
OFFICIAL_MAX_BATCH_SIZE = 4
OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES = (1, 2, 4, 8)
OFFICIAL_MP4_PARTITION_ROWS = OFFICIAL_VOCABULARY_SIZE // 4
OFFICIAL_DEFAULT_TEMPERATURE_BINARY32 = BINARY32_ONE
OFFICIAL_W1_TENSOR_NAME = "mtp.2.markov_head.markov_w1.weight"
OFFICIAL_W2_TENSOR_NAME = "mtp.2.markov_head.markov_w2.weight"
OFFICIAL_WEIGHT_SHAPE = (OFFICIAL_VOCABULARY_SIZE, OFFICIAL_MARKOV_RANK)
OFFICIAL_WEIGHT_BYTES = OFFICIAL_VOCABULARY_SIZE * OFFICIAL_MARKOV_RANK * 2
OFFICIAL_W1_SHA256 = (
    "966bd0507046347754d0f4bf3addd6df6c179ff16243d63998258b3987e4b2f5"
)
OFFICIAL_W2_SHA256 = (
    "40ac7e99651c5c6aab8d2555ff65d247931f318414cf94baedc6da2d3bf7c175"
)
OFFICIAL_W1_MP4_SHA256 = (
    "ceea71f22c755c8517e3698004280d64712c93c5a4115c008edb23b2512917f6",
    "1ee7e87fb6ef425705393a68c9fc55328e1463e7bc18aad65c343c0177bdc423",
    "35170e3fbb7284731f9c83262fd9cd2fdaf24bf8d89956a56b5851de66864ba5",
    "c923b8cd3bcea770a62f5cc655ba9dbe00deed5036493dbbf1642fe471534fef",
)
OFFICIAL_W2_MP4_SHA256 = (
    "4e7fb04d60fc0c4fc40020ef9749193607994a35a5c19ab7a6771074a9750f6a",
    "ea4a7b2122d411f0635ae2e1a21ecfb08687b66721e5442d7ad5e56acaeb46c8",
    "c9b30d6e6433fda98a3601b91c7bd3fdc30ffe6208fffc6447aab6de561745ca",
    "d80ce53194fbed4a6a6f1d34da993cdf7e915d316f94ec331c27be000f0a16dc",
)
OFFICIAL_SELECTED_TOKEN_IDS = (
    0,
    32_319,
    32_320,
    64_639,
    64_640,
    96_959,
    96_960,
    129_279,
)
OFFICIAL_W1_SELECTED_ROW_SHA256 = (
    "979c832be5220914389a01ff08cd3434d07bad2aa9a788d5a4b8c93013821ac2",
    "dba9f400089dd2f656923f17ba5bc1b09d4458a922357e9617dd73bbcf408f76",
    "63f259e5af563c74f3df4816938f5b0264f592e662df4a2b13837786645a7caa",
    "94d236d2169f39459852f048c52e45423198488cb7ba4a28773c5a8a031b10c2",
    "709c02da312adb97bbbe1aeab3d916817a430fc292f76f230b18cf2a37d4489f",
    "7dacd1f0abfa621920918860f42aec66d4d1574a71426438ebcf49b44d9f0cc4",
    "e752a71f90e06b26d339e92a3d52d8541189e24c3a0c3c1e742c9e951844216d",
    "05a13c5c2eb47b7888754a21e0b8111b80c3d8be293b212ff2edf28b348343a4",
)
OFFICIAL_W2_SELECTED_ROW_SHA256 = (
    "06077a0e4376e1df9de0bf320a55958435c3b3bb3f8e6c1bf74d6e0e6d8b47d9",
    "f878546dd2dd2f06634dbc71bafbc44bbac86847c1e53eb7e5a93bf8bf481b37",
    "2270161d089a149404620271668ff43e85de17c048aa362f5d302b80a8149ab8",
    "957dbd1a0191099b880451a3bd2eb44e5c991f5d8f3700c1ecea6b96906b1613",
    "f68e7381e7920b896b169c60c44cb5ca73c0f09bbbc1f11103a51f0b1fc26102",
    "629b94e002bc1ed6035d817c335b597d04b3a8d8a0dff70d8f110bc7697c7342",
    "93446109bf486af3ac9e379033d37c3bfd297e4ff2b5879e3d7d4ad2b0aff76c",
    "a6d244fbbc27d6b52bf6a5b8dee21e285c5f83ce1b3106a23f3558d61961adf5",
)
OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_BINARY32 = (
    0xC0581E4C,
    0xBEA8489F,
    0xBF051136,
    0xBF89F37E,
    0xBF3EFBFF,
    0xBFA3E9F0,
    0xC0155C56,
    0xC09B71D2,
)
OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_SHA256 = (
    "cd2d68aff994647705aee41fd16a5f13f8219fe61ee824eae6f054d43127470d"
)

SOURCE_EXPRESSIONS = (
    "temperature: float = 1",
    "self.markov_w1 = ParallelEmbedding(vocab_size, dspark_markov_rank)",
    "self.markov_w2 = ParallelHead(vocab_size, dspark_markov_rank)",
    "self.temperature = args.temperature",
    "embed = self.markov_w1(token_ids)",
    "logits = self.markov_w2(embed, full_logits=True)",
    "output_ids[:, 0] = input_ids",
    "for i in range(self.block_size):",
    "logits_bias, markov_embed = self.markov_head(output_ids[:, i])",
    "logits[:, i].add_(logits_bias)",
    "output_ids[:, i + 1] = sample(logits[:, i], self.temperature)",
    "markov_embed = torch.stack(markov_embeds, dim=1)",
    "return output_ids, logits, confidence",
)
SOURCE_EQUIVALENCE_BOUNDARY = (
    "The five lookup/project/add/control dependencies match the pinned DSparkBlock.forward_head source order.",
    "BF16 lookup rows and Markov-head weights widen exactly; increasing-rank exact products use one binary32 RNE product-add each, followed by one separate binary32 RNE logit addition.",
    "Zero-temperature sampling is source-exact finite-binary32 first-index argmax at every step.",
    "The official default temperature is binary32 one, but exact nonzero-temperature PyTorch/CUDA replay remains blocked by the unpinned RNG, exponential transform, and softmax backend.",
    "The deterministic target adaptation consumes immutable caller-supplied post-exponential binary32 draws in step-major, then batch-major, then vocabulary-major order.",
)
EXCLUDED_CLAIMS = (
    "checkpoint_or_artifact_authentication",
    "draft_hidden_or_base_logit_provenance",
    "pytorch_cuda_gemm_bit_equivalence",
    "pytorch_cuda_nonzero_temperature_stochastic_replay",
    "confidence_projection_target_verification_or_speculative_acceptance",
    "physical_tensor_parallel_collective_or_memory_execution",
    "compiler_service_or_rtl_execution",
    "physical_rom_sram_hbm_cycles_latency_bandwidth_throughput_energy_area_routing_ppa",
    "end_to_end_model_or_task_quality_evidence",
)


BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Batch5: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Batch5: TypeAlias = tuple[tuple[Binary32Vector, ...], ...]
TokenRows: TypeAlias = tuple[tuple[int, ...], ...]


class MarkovLoopReferenceError(ValueError):
    """Raised when a Markov-loop transaction must poison without commit."""


@dataclass(frozen=True, slots=True)
class MarkovLoopCounters:
    """Exact logical topology and arithmetic counts; never physical timing."""

    batch_count: int
    block_size: int
    vocabulary_size: int
    markov_rank: int
    tensor_parallel_world_size: int
    partition_vocabulary_rows: int
    loop_iterations: int
    initial_token_values_read: int
    initial_token_values_written: int
    causal_token_values_read: int
    base_logit_binary32_values_validated: int
    base_logit_binary32_values_read: int
    embedding_weight_bf16_values_validated: int
    head_weight_bf16_values_validated: int
    embedding_row_lookups: int
    embedding_bf16_values_read: int
    embedding_bf16_values_written: int
    embedding_binary32_widens: int
    head_weight_binary32_widens: int
    exact_product_accumulates: int
    binary32_accumulation_roundings: int
    markov_bias_binary32_values_written: int
    binary32_bias_additions: int
    adjusted_logit_binary32_values_written: int
    sampling_calls: int
    sampling_logit_binary32_values_read: int
    sampling_argmax_comparisons: int
    sampling_entropy_draws_consumed: int
    sampled_token_values_written: int
    output_token_values_written: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class MarkovLoopResult:
    """Immutable causal outputs, intermediates, provenance hashes, and work."""

    numeric_profile: str
    sampling_numeric_profile: str
    sampling_mode: str
    source_equivalence: str
    temperature_binary32: int
    require_pytorch_cuda_equivalence: bool
    tensor_parallel_world_size: int
    vocabulary_size: int
    markov_rank: int
    official_shape_profile: bool
    input_token_ids: tuple[int, ...]
    output_token_ids: TokenRows
    base_logits_binary32_codes: Binary32Batch5
    markov_bias_binary32_codes: Binary32Batch5
    adjusted_logits_binary32_codes: Binary32Batch5
    markov_embeddings_bf16_codes: BF16Batch5
    sampling_results: tuple[SamplingResult, ...]
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
    next_entropy: ExplicitExponentialEntropy | None
    counters: MarkovLoopCounters
    source_equivalence_boundary: tuple[str, ...]
    excluded_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_result(self)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise MarkovLoopReferenceError(f"{label} must be an exact list or tuple")
    return value


def _exact_tuple(value: object, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise MarkovLoopReferenceError(f"{label} must be a deeply immutable tuple")
    return value


def _integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise MarkovLoopReferenceError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _world_size(value: object) -> int:
    if type(value) is not int or value not in OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES:
        raise MarkovLoopReferenceError(
            "tensor_parallel_world_size must be exactly 1, 2, 4, or 8"
        )
    return value


def _finite_bf16(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int or not 0 <= value < 1 << 16:
        raise MarkovLoopReferenceError(f"{label} must be an exact BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise MarkovLoopReferenceError(f"{label} must be finite BF16")
    return value, decoded.value


def _finite_binary32(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value < 1 << 32:
        raise MarkovLoopReferenceError(
            f"{label} must be an exact binary32 encoding"
        )
    decoded = decode_binary32(value)
    if not decoded.finite or decoded.value is None:
        raise MarkovLoopReferenceError(f"{label} must be finite binary32")
    return value


def _sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MarkovLoopReferenceError(f"{label} must be a lowercase SHA-256")
    return value


def _freeze_weight_shards(
    value: object,
    *,
    label: str,
    world_size: int,
    expected_partition_rows: int | None = None,
    expected_rank: int | None = None,
) -> tuple[BF16Matrix, tuple[tuple[Fraction, ...], ...], int, int]:
    raw_shards = _sequence(value, label)
    if len(raw_shards) != world_size:
        raise MarkovLoopReferenceError(
            f"{label} must contain one shard per tensor-parallel rank"
        )
    partition_rows = expected_partition_rows
    rank_width = expected_rank
    frozen_rows: list[BF16Vector] = []
    value_rows: list[tuple[Fraction, ...]] = []
    for shard_index, raw_shard in enumerate(raw_shards):
        shard = _sequence(raw_shard, f"{label}[{shard_index}]")
        if partition_rows is None:
            partition_rows = len(shard)
            if partition_rows < 1:
                raise MarkovLoopReferenceError(f"{label} shards must contain rows")
        elif len(shard) != partition_rows:
            raise MarkovLoopReferenceError(f"{label} shards must have equal row counts")
        for local_row, raw_row in enumerate(shard):
            row = _sequence(raw_row, f"{label}[{shard_index}][{local_row}]")
            if rank_width is None:
                rank_width = len(row)
                if not 1 <= rank_width <= OFFICIAL_MARKOV_RANK:
                    raise MarkovLoopReferenceError(
                        f"{label} Markov rank must be in [1, {OFFICIAL_MARKOV_RANK}]"
                    )
            elif len(row) != rank_width:
                raise MarkovLoopReferenceError(f"{label} rows must have equal width")
            frozen_row: list[int] = []
            decoded_row: list[Fraction] = []
            for column, code in enumerate(row):
                frozen, decoded = _finite_bf16(
                    code,
                    f"{label}[{shard_index}][{local_row}][{column}]",
                )
                frozen_row.append(frozen)
                decoded_row.append(decoded)
            frozen_rows.append(tuple(frozen_row))
            value_rows.append(tuple(decoded_row))
    assert partition_rows is not None and rank_width is not None
    vocabulary_size = partition_rows * world_size
    if vocabulary_size > OFFICIAL_VOCABULARY_SIZE:
        raise MarkovLoopReferenceError(f"{label} exceeds the official vocabulary")
    return tuple(frozen_rows), tuple(value_rows), partition_rows, rank_width


def _freeze_logits(value: object, *, vocabulary_size: int) -> Binary32Batch5:
    raw_batches = _sequence(value, "base_logits_binary32_codes")
    if not 1 <= len(raw_batches) <= OFFICIAL_MAX_BATCH_SIZE:
        raise MarkovLoopReferenceError(
            "base logits batch extent must be in "
            f"[1, {OFFICIAL_MAX_BATCH_SIZE}]"
        )
    batches: list[tuple[Binary32Vector, ...]] = []
    for batch, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"base_logits_binary32_codes[{batch}]")
        if len(sequence) != OFFICIAL_BLOCK_SIZE:
            raise MarkovLoopReferenceError(
                f"base_logits_binary32_codes[{batch}] must contain exactly "
                f"{OFFICIAL_BLOCK_SIZE} draft rows"
            )
        rows: list[Binary32Vector] = []
        for step, raw_row in enumerate(sequence):
            row = _sequence(
                raw_row,
                f"base_logits_binary32_codes[{batch}][{step}]",
            )
            if len(row) != vocabulary_size:
                raise MarkovLoopReferenceError(
                    f"base_logits_binary32_codes[{batch}][{step}] must have "
                    f"vocabulary width {vocabulary_size}"
                )
            rows.append(
                tuple(
                    _finite_binary32(
                        code,
                        "base_logits_binary32_codes"
                        f"[{batch}][{step}][{column}]",
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
        raise MarkovLoopReferenceError(
            "input_token_ids length must equal the base-logit batch extent"
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


def _sampling_logits_hash(rows: tuple[Binary32Vector, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"opentallas.deepseek_v4_sample_logits.v1\x00")
    digest.update(len(rows).to_bytes(8, "little"))
    digest.update(len(rows[0]).to_bytes(8, "little"))
    for row in rows:
        for code in row:
            digest.update(code.to_bytes(4, "little"))
    return digest.hexdigest()


def _counter_values(
    *,
    batch_count: int,
    vocabulary_size: int,
    markov_rank: int,
    world_size: int,
    entropy_draws: int,
) -> dict[str, int]:
    steps = OFFICIAL_BLOCK_SIZE
    token_steps = batch_count * steps
    logit_values = token_steps * vocabulary_size
    products = logit_values * markov_rank
    return {
        "batch_count": batch_count,
        "block_size": steps,
        "vocabulary_size": vocabulary_size,
        "markov_rank": markov_rank,
        "tensor_parallel_world_size": world_size,
        "partition_vocabulary_rows": vocabulary_size // world_size,
        "loop_iterations": steps,
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
        "sampling_calls": steps,
        "sampling_logit_binary32_values_read": logit_values,
        "sampling_argmax_comparisons": token_steps * (vocabulary_size - 1),
        "sampling_entropy_draws_consumed": entropy_draws,
        "sampled_token_values_written": token_steps,
        "output_token_values_written": batch_count * (steps + 1),
        "transaction_commits": 1,
    }


def _validate_counters(value: object) -> MarkovLoopCounters:
    if type(value) is not MarkovLoopCounters:
        raise MarkovLoopReferenceError(
            "counters must be an exact MarkovLoopCounters record"
        )
    batch_count = _integer(
        value.batch_count,
        "counters.batch_count",
        minimum=1,
        maximum=OFFICIAL_MAX_BATCH_SIZE,
    )
    vocabulary_size = _integer(
        value.vocabulary_size,
        "counters.vocabulary_size",
        minimum=1,
        maximum=OFFICIAL_VOCABULARY_SIZE,
    )
    markov_rank = _integer(
        value.markov_rank,
        "counters.markov_rank",
        minimum=1,
        maximum=OFFICIAL_MARKOV_RANK,
    )
    world_size = _world_size(value.tensor_parallel_world_size)
    if vocabulary_size % world_size:
        raise MarkovLoopReferenceError(
            "counter vocabulary must divide across tensor-parallel ranks"
        )
    maximum_draws = batch_count * OFFICIAL_BLOCK_SIZE * vocabulary_size
    entropy_draws = value.sampling_entropy_draws_consumed
    if type(entropy_draws) is not int or entropy_draws not in {0, maximum_draws}:
        raise MarkovLoopReferenceError(
            "counter entropy draws must describe greedy or all five target steps"
        )
    expected = _counter_values(
        batch_count=batch_count,
        vocabulary_size=vocabulary_size,
        markov_rank=markov_rank,
        world_size=world_size,
        entropy_draws=entropy_draws,
    )
    for field in fields(value):
        observed = getattr(value, field.name)
        expected_value = expected[field.name]
        if type(observed) is not int or observed != expected_value:
            raise MarkovLoopReferenceError(
                f"counters.{field.name} does not reconcile to the Markov loop"
            )
    return value


def _validate_result(value: object) -> MarkovLoopResult:
    if type(value) is not MarkovLoopResult:
        raise MarkovLoopReferenceError(
            "result must be an exact MarkovLoopResult record"
        )
    if value.numeric_profile != MARKOV_LOOP_NUMERIC_PROFILE:
        raise MarkovLoopReferenceError("result numeric profile differs")
    temperature = _finite_binary32(
        value.temperature_binary32,
        "result.temperature_binary32",
    )
    temperature_value = decode_binary32(temperature).value
    assert temperature_value is not None
    if type(value.require_pytorch_cuda_equivalence) is not bool:
        raise MarkovLoopReferenceError(
            "result.require_pytorch_cuda_equivalence must be an exact bool"
        )
    counters = _validate_counters(value.counters)
    if value.tensor_parallel_world_size != counters.tensor_parallel_world_size:
        raise MarkovLoopReferenceError("result tensor-parallel world size differs")
    if value.vocabulary_size != counters.vocabulary_size:
        raise MarkovLoopReferenceError("result vocabulary size differs")
    if value.markov_rank != counters.markov_rank:
        raise MarkovLoopReferenceError("result Markov rank differs")
    expected_official = (
        counters.vocabulary_size == OFFICIAL_VOCABULARY_SIZE
        and counters.markov_rank == OFFICIAL_MARKOV_RANK
        and counters.block_size == OFFICIAL_BLOCK_SIZE
    )
    if (
        type(value.official_shape_profile) is not bool
        or value.official_shape_profile != expected_official
    ):
        raise MarkovLoopReferenceError("result official-shape status differs")
    if value.source_equivalence_boundary != SOURCE_EQUIVALENCE_BOUNDARY:
        raise MarkovLoopReferenceError("result source-equivalence boundary differs")
    if value.excluded_claims != EXCLUDED_CLAIMS:
        raise MarkovLoopReferenceError("result excluded claims differ")
    for name in (
        "embedding_weight_bf16_sha256",
        "head_weight_bf16_sha256",
        "base_logits_binary32_sha256",
        "markov_bias_binary32_sha256",
        "adjusted_logits_binary32_sha256",
        "markov_embeddings_bf16_sha256",
        "output_token_ids_sha256",
    ):
        _sha256(getattr(value, name), f"result.{name}")

    inputs = _exact_tuple(value.input_token_ids, "result.input_token_ids")
    if len(inputs) != counters.batch_count:
        raise MarkovLoopReferenceError("result input-token batch extent differs")
    for batch, token in enumerate(inputs):
        _integer(
            token,
            f"result.input_token_ids[{batch}]",
            minimum=0,
            maximum=counters.vocabulary_size - 1,
        )
    output_tokens = _exact_tuple(value.output_token_ids, "result.output_token_ids")
    if len(output_tokens) != counters.batch_count:
        raise MarkovLoopReferenceError("result output-token batch extent differs")
    for batch, raw_row in enumerate(output_tokens):
        row = _exact_tuple(raw_row, f"result.output_token_ids[{batch}]")
        if len(row) != OFFICIAL_OUTPUT_TOKEN_COUNT or row[0] != inputs[batch]:
            raise MarkovLoopReferenceError(
                "result output tokens do not preserve the initial-token column"
            )
        for step, token in enumerate(row):
            _integer(
                token,
                f"result.output_token_ids[{batch}][{step}]",
                minimum=0,
                maximum=counters.vocabulary_size - 1,
            )

    def validate_tensor3(
        raw_value: object,
        *,
        label: str,
        width: int,
        bf16: bool,
    ) -> tuple[tuple[tuple[int, ...], ...], ...]:
        raw_batches = _exact_tuple(raw_value, label)
        if len(raw_batches) != counters.batch_count:
            raise MarkovLoopReferenceError(f"{label} batch extent differs")
        batches: list[tuple[tuple[int, ...], ...]] = []
        for batch, raw_sequence in enumerate(raw_batches):
            sequence = _exact_tuple(raw_sequence, f"{label}[{batch}]")
            if len(sequence) != OFFICIAL_BLOCK_SIZE:
                raise MarkovLoopReferenceError(f"{label} block extent differs")
            rows: list[tuple[int, ...]] = []
            for step, raw_row in enumerate(sequence):
                row = _exact_tuple(raw_row, f"{label}[{batch}][{step}]")
                if len(row) != width:
                    raise MarkovLoopReferenceError(f"{label} row width differs")
                rows.append(
                    tuple(
                        (
                            _finite_bf16(code, f"{label}[{batch}][{step}][{column}]")[0]
                            if bf16
                            else _finite_binary32(
                                code,
                                f"{label}[{batch}][{step}][{column}]",
                            )
                        )
                        for column, code in enumerate(row)
                    )
                )
            batches.append(tuple(rows))
        return tuple(batches)

    base = validate_tensor3(
        value.base_logits_binary32_codes,
        label="result.base_logits_binary32_codes",
        width=counters.vocabulary_size,
        bf16=False,
    )
    bias = validate_tensor3(
        value.markov_bias_binary32_codes,
        label="result.markov_bias_binary32_codes",
        width=counters.vocabulary_size,
        bf16=False,
    )
    adjusted = validate_tensor3(
        value.adjusted_logits_binary32_codes,
        label="result.adjusted_logits_binary32_codes",
        width=counters.vocabulary_size,
        bf16=False,
    )
    embeddings = validate_tensor3(
        value.markov_embeddings_bf16_codes,
        label="result.markov_embeddings_bf16_codes",
        width=counters.markov_rank,
        bf16=True,
    )
    for batch in range(counters.batch_count):
        for step in range(OFFICIAL_BLOCK_SIZE):
            for column in range(counters.vocabulary_size):
                try:
                    expected_adjusted = binary32_add(
                        base[batch][step][column],
                        bias[batch][step][column],
                    )
                except NumericReferenceError as exc:  # pragma: no cover - finite invariant
                    raise MarkovLoopReferenceError(
                        "result base/bias addition became invalid"
                    ) from exc
                if adjusted[batch][step][column] != expected_adjusted:
                    raise MarkovLoopReferenceError(
                        "result adjusted logits do not reconcile to base plus bias"
                    )

    if _hash_tensor3(
        base,
        bytes_per_value=4,
        domain=b"opentallas.deepseek_v4_markov_base_logits.v1\x00",
    ) != value.base_logits_binary32_sha256:
        raise MarkovLoopReferenceError("result base-logit hash does not reconcile")
    if _hash_tensor3(
        bias,
        bytes_per_value=4,
        domain=b"opentallas.deepseek_v4_markov_bias.v1\x00",
    ) != value.markov_bias_binary32_sha256:
        raise MarkovLoopReferenceError("result Markov-bias hash does not reconcile")
    if _hash_tensor3(
        adjusted,
        bytes_per_value=4,
        domain=b"opentallas.deepseek_v4_markov_adjusted_logits.v1\x00",
    ) != value.adjusted_logits_binary32_sha256:
        raise MarkovLoopReferenceError(
            "result adjusted-logit hash does not reconcile"
        )
    if _hash_tensor3(
        embeddings,
        bytes_per_value=2,
        domain=b"opentallas.deepseek_v4_markov_embeddings.v1\x00",
    ) != value.markov_embeddings_bf16_sha256:
        raise MarkovLoopReferenceError("result embedding hash does not reconcile")
    if _hash_tokens(output_tokens) != value.output_token_ids_sha256:
        raise MarkovLoopReferenceError("result output-token hash does not reconcile")

    samples = _exact_tuple(value.sampling_results, "result.sampling_results")
    if len(samples) != OFFICIAL_BLOCK_SIZE:
        raise MarkovLoopReferenceError("result must retain exactly five sampling records")
    entropy_draws = 0
    previous_after: int | None = value.entropy_offset_before
    for step, sample in enumerate(samples):
        if type(sample) is not SamplingResult:
            raise MarkovLoopReferenceError(
                "result sampling records must be exact SamplingResult values"
            )
        rows = tuple(
            adjusted[batch][step] for batch in range(counters.batch_count)
        )
        expected_tokens = tuple(
            output_tokens[batch][step + 1] for batch in range(counters.batch_count)
        )
        if (
            sample.batch_size != counters.batch_count
            or sample.vocabulary_size != counters.vocabulary_size
            or sample.temperature_binary32 != temperature
            or sample.logits_sha256 != _sampling_logits_hash(rows)
            or sample.token_ids != expected_tokens
            or sample.entropy_offset_before != previous_after
        ):
            raise MarkovLoopReferenceError(
                f"result sampling record {step} does not reconcile causally"
            )
        entropy_draws += sample.counters.exponential_draws_consumed
        previous_after = sample.entropy_offset_after
    if entropy_draws != counters.sampling_entropy_draws_consumed:
        raise MarkovLoopReferenceError("result entropy work differs from sampling")
    if previous_after != value.entropy_offset_after:
        raise MarkovLoopReferenceError("result final entropy offset differs")
    last_entropy = samples[-1].next_entropy
    if value.next_entropy != last_entropy:
        raise MarkovLoopReferenceError("result entropy continuation differs")

    if temperature_value == 0:
        if (
            value.sampling_mode != "greedy_argmax"
            or value.sampling_numeric_profile != GREEDY_NUMERIC_PROFILE
            or value.source_equivalence
            != "bit_exact_for_validated_finite_binary32_inputs"
            or entropy_draws != 0
        ):
            raise MarkovLoopReferenceError("result greedy sampling metadata differs")
    else:
        if (
            value.require_pytorch_cuda_equivalence
            or value.sampling_mode
            != "explicit_exponential_race_target_adaptation"
            or value.sampling_numeric_profile != TARGET_STOCHASTIC_NUMERIC_PROFILE
            or value.source_equivalence != PYTORCH_STOCHASTIC_EQUIVALENCE
            or entropy_draws
            != counters.batch_count * OFFICIAL_BLOCK_SIZE * counters.vocabulary_size
        ):
            raise MarkovLoopReferenceError(
                "result stochastic target-adaptation metadata differs"
            )

    if value.next_entropy is None:
        if any(
            item is not None
            for item in (
                value.entropy_stream_sha256,
                value.entropy_offset_before,
                value.entropy_offset_after,
            )
        ):
            raise MarkovLoopReferenceError(
                "result entropy metadata exists without a continuation"
            )
    else:
        if type(value.next_entropy) is not ExplicitExponentialEntropy:
            raise MarkovLoopReferenceError("result entropy continuation type differs")
        if (
            _sha256(value.entropy_stream_sha256, "result.entropy_stream_sha256")
            != value.next_entropy.stream_sha256
            or value.next_entropy.offset != value.entropy_offset_after
        ):
            raise MarkovLoopReferenceError(
                "result entropy stream and continuation do not reconcile"
            )
    return value


def markov_autoregressive_loop_bf16(
    base_logits_binary32_codes: object,
    input_token_ids: object,
    embedding_weight_shards_bf16_codes: object,
    head_weight_shards_bf16_codes: object,
    *,
    temperature_binary32: int = OFFICIAL_DEFAULT_TEMPERATURE_BINARY32,
    entropy: ExplicitExponentialEntropy | None = None,
    tensor_parallel_world_size: int = 4,
    require_pytorch_cuda_equivalence: bool = True,
) -> MarkovLoopResult:
    """Execute the complete five-step DSpark Markov transaction.

    Base logits have shape ``[B,5,V]`` and are copied before adjustment.
    Inputs contain one token per batch.  Both BF16 weight arguments contain
    exactly ``world_size`` equal contiguous vocabulary shards in rank order;
    their common shape is ``[V,R]``.  The result shapes are tokens ``[B,6]``,
    adjusted logits ``[B,5,V]``, and embeddings ``[B,5,R]``.

    With the official default nonzero temperature, the default equivalence
    request fails closed.  Set ``require_pytorch_cuda_equivalence=False`` and
    provide explicit post-exponential entropy to select the deterministic
    target adaptation.  Temperature zero consumes no entropy.
    """

    world_size = _world_size(tensor_parallel_world_size)
    if type(require_pytorch_cuda_equivalence) is not bool:
        raise MarkovLoopReferenceError(
            "require_pytorch_cuda_equivalence must be an exact bool"
        )
    temperature = _finite_binary32(temperature_binary32, "temperature_binary32")
    if entropy is not None and type(entropy) is not ExplicitExponentialEntropy:
        raise MarkovLoopReferenceError(
            "entropy must be an exact ExplicitExponentialEntropy stream or None"
        )
    (
        embedding_weights,
        _,
        partition_rows,
        markov_rank,
    ) = _freeze_weight_shards(
        embedding_weight_shards_bf16_codes,
        label="embedding_weight_shards_bf16_codes",
        world_size=world_size,
    )
    (
        head_weights,
        head_weight_values,
        head_partition_rows,
        head_rank,
    ) = _freeze_weight_shards(
        head_weight_shards_bf16_codes,
        label="head_weight_shards_bf16_codes",
        world_size=world_size,
        expected_partition_rows=partition_rows,
        expected_rank=markov_rank,
    )
    if head_partition_rows != partition_rows or head_rank != markov_rank:
        raise MarkovLoopReferenceError("Markov W1 and W2 topology differs")
    vocabulary_size = partition_rows * world_size
    base_logits = _freeze_logits(
        base_logits_binary32_codes,
        vocabulary_size=vocabulary_size,
    )
    batch_count = len(base_logits)
    initial_tokens = _freeze_tokens(
        input_token_ids,
        batch_count=batch_count,
        vocabulary_size=vocabulary_size,
    )

    output_tokens: list[list[int]] = [[token] for token in initial_tokens]
    embeddings_by_batch: list[list[BF16Vector]] = [
        [] for _ in range(batch_count)
    ]
    bias_by_batch: list[list[Binary32Vector]] = [[] for _ in range(batch_count)]
    adjusted_by_batch: list[list[Binary32Vector]] = [
        [] for _ in range(batch_count)
    ]
    sampling_results: list[SamplingResult] = []
    next_entropy = entropy

    for step in range(OFFICIAL_BLOCK_SIZE):
        step_embeddings = tuple(
            embedding_weights[output_tokens[batch][step]]
            for batch in range(batch_count)
        )
        step_biases: list[Binary32Vector] = []
        step_adjusted: list[Binary32Vector] = []
        for batch, embedding_codes in enumerate(step_embeddings):
            embedding_values = tuple(
                decode_bf16(code).value for code in embedding_codes
            )
            if any(item is None for item in embedding_values):  # pragma: no cover
                raise RuntimeError("validated Markov embedding became nonfinite")
            try:
                bias_row = tuple(
                    binary32_ordered_dot(embedding_values, weight_row)
                    for weight_row in head_weight_values
                )
                adjusted_row = tuple(
                    binary32_add(base, bias)
                    for base, bias in zip(
                        base_logits[batch][step],
                        bias_row,
                        strict=True,
                    )
                )
            except NumericReferenceError as exc:
                raise MarkovLoopReferenceError(
                    f"Markov arithmetic failed at step {step}, batch {batch}: {exc}"
                ) from exc
            step_biases.append(bias_row)
            step_adjusted.append(adjusted_row)
        try:
            sample = deepseek_v4_sample_binary32(
                tuple(step_adjusted),
                temperature,
                entropy=next_entropy,
                vocabulary_size=vocabulary_size,
                require_pytorch_cuda_equivalence=require_pytorch_cuda_equivalence,
            )
        except SamplingReferenceError as exc:
            raise MarkovLoopReferenceError(
                f"Markov sampling failed at causal step {step}: {exc}"
            ) from exc
        for batch in range(batch_count):
            embeddings_by_batch[batch].append(step_embeddings[batch])
            bias_by_batch[batch].append(step_biases[batch])
            adjusted_by_batch[batch].append(step_adjusted[batch])
            output_tokens[batch].append(sample.token_ids[batch])
        sampling_results.append(sample)
        next_entropy = sample.next_entropy

    frozen_tokens: TokenRows = tuple(tuple(row) for row in output_tokens)
    frozen_embeddings: BF16Batch5 = tuple(
        tuple(sequence) for sequence in embeddings_by_batch
    )
    frozen_bias: Binary32Batch5 = tuple(tuple(sequence) for sequence in bias_by_batch)
    frozen_adjusted: Binary32Batch5 = tuple(
        tuple(sequence) for sequence in adjusted_by_batch
    )
    entropy_draws = sum(
        sample.counters.exponential_draws_consumed for sample in sampling_results
    )
    counters = MarkovLoopCounters(
        **_counter_values(
            batch_count=batch_count,
            vocabulary_size=vocabulary_size,
            markov_rank=markov_rank,
            world_size=world_size,
            entropy_draws=entropy_draws,
        )
    )
    first_sample = sampling_results[0]
    entropy_stream_sha256 = entropy.stream_sha256 if entropy is not None else None
    entropy_before = entropy.offset if entropy is not None else None
    entropy_after = next_entropy.offset if next_entropy is not None else None
    return MarkovLoopResult(
        numeric_profile=MARKOV_LOOP_NUMERIC_PROFILE,
        sampling_numeric_profile=first_sample.numeric_profile,
        sampling_mode=first_sample.mode,
        source_equivalence=first_sample.source_equivalence,
        temperature_binary32=temperature,
        require_pytorch_cuda_equivalence=require_pytorch_cuda_equivalence,
        tensor_parallel_world_size=world_size,
        vocabulary_size=vocabulary_size,
        markov_rank=markov_rank,
        official_shape_profile=(
            vocabulary_size == OFFICIAL_VOCABULARY_SIZE
            and markov_rank == OFFICIAL_MARKOV_RANK
        ),
        input_token_ids=initial_tokens,
        output_token_ids=frozen_tokens,
        base_logits_binary32_codes=base_logits,
        markov_bias_binary32_codes=frozen_bias,
        adjusted_logits_binary32_codes=frozen_adjusted,
        markov_embeddings_bf16_codes=frozen_embeddings,
        sampling_results=tuple(sampling_results),
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
        counters=counters,
        source_equivalence_boundary=SOURCE_EQUIVALENCE_BOUNDARY,
        excluded_claims=EXCLUDED_CLAIMS,
    )


__all__ = [
    "CHECKPOINT_INDEX_SHA256",
    "CHECKPOINT_LOCK_ID",
    "CHECKPOINT_SHARD",
    "EXCLUDED_CLAIMS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "MARKOV_LOOP_NUMERIC_PROFILE",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_BLOCK_SIZE",
    "OFFICIAL_DEFAULT_TEMPERATURE_BINARY32",
    "OFFICIAL_MARKOV_RANK",
    "OFFICIAL_MAX_BATCH_SIZE",
    "OFFICIAL_MP4_PARTITION_ROWS",
    "OFFICIAL_OUTPUT_TOKEN_COUNT",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_SELECTED_TOKEN_IDS",
    "OFFICIAL_TENSOR_PARALLEL_WORLD_SIZES",
    "OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_BINARY32",
    "OFFICIAL_TOKEN0_SELECTED_W2_LOGITS_SHA256",
    "OFFICIAL_VOCABULARY_SIZE",
    "OFFICIAL_W1_MP4_SHA256",
    "OFFICIAL_W1_SELECTED_ROW_SHA256",
    "OFFICIAL_W1_SHA256",
    "OFFICIAL_W1_TENSOR_NAME",
    "OFFICIAL_W2_MP4_SHA256",
    "OFFICIAL_W2_SELECTED_ROW_SHA256",
    "OFFICIAL_W2_SHA256",
    "OFFICIAL_W2_TENSOR_NAME",
    "OFFICIAL_WEIGHT_BYTES",
    "OFFICIAL_WEIGHT_SHAPE",
    "SOURCE_EQUIVALENCE_BOUNDARY",
    "SOURCE_EXPRESSIONS",
    "MarkovLoopCounters",
    "MarkovLoopReferenceError",
    "MarkovLoopResult",
    "markov_autoregressive_loop_bf16",
]
