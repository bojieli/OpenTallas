"""Exact DeepSeek V4 compressor-pooling reference semantics.

This module is pinned to ``deepseek-ai/DeepSeek-V4-Flash-0731`` revision
``7872f01b1d1fe23eabc4c98b48bffcef5a386062``.  In
``inference/model.py:Compressor.forward`` the released model adds the learned
APE row to each binary32 gate-score row, optionally applies
``Compressor.overlap_transform``, and evaluates::

    kv = (kv * score.softmax(dim=2)).sum(dim=2)

The source fixes the tensor axes but does not make a CUDA reduction tree or
exponential approximation architectural.  The OpenTallas target adaptation
named below therefore freezes these otherwise backend-dependent boundaries:

* every score-plus-APE addition rounds once to IEEE binary32 RNE;
* softmax selects the first maximum finite lane, subtracts it with one
  binary32 RNE operation, and correctly rounds mathematical ``exp`` once to
  binary32;
* exponentials reduce in source-position order with the NUM-6.1 balanced
  binary32 tree, and each probability division rounds once to binary32;
* every KV/probability multiplication rounds once to binary32, then products
  reduce in source-position order with the same balanced tree.

Ratio four uses the released overlapping layout.  Projected rows have width
``2*D``.  Pool group zero receives four zero-KV/negative-infinity-score rows;
later groups concatenate the preceding group's first feature half with the
current group's second half.  Ratio 128 uses non-overlapping ``[128,D]``
groups.  Only the three released profiles are admitted: main ratio-four
``D=512``, index ratio-four ``D=128``, and main ratio-128 ``D=512``.

The direct API consumes immutable structural equivalents of the concurrent
compressor-state handoff, with axes ``[B,G,P,D]``.  The prefill and complete
decode-window adapters independently reproduce APE placement and overlap
assembly from raw projected tensors without importing or mutating compressor
state.  They are functional equivalence helpers; they do not implement RMS
normalization, RoPE, FP8/FP4 QDQ, compressed-KV writes, compiler lowering,
service execution, schedules, cycles, bandwidth, energy, area, or PPA.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_divide,
    binary32_multiply,
    decode_binary32,
)
from .transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
)


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
COMPRESS_POOL_NUMERIC_PROFILE = "opentallas.deepseek_v4_compress_pool_f32.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
PINNED_OVERLAP_RATIO = 4
PINNED_NONOVERLAP_RATIO = 128
PINNED_MAIN_HEAD_DIM = 512
PINNED_INDEX_HEAD_DIM = 128
PINNED_COMPRESSION_RATIOS = (
    PINNED_OVERLAP_RATIO,
    PINNED_NONOVERLAP_RATIO,
)
PINNED_RATIO4_HEAD_DIMS = (
    PINNED_INDEX_HEAD_DIM,
    PINNED_MAIN_HEAD_DIM,
)
PINNED_MAIN_RATIO4_SITE_COUNT = 21
PINNED_INDEX_RATIO4_SITE_COUNT = 21
PINNED_MAIN_RATIO128_SITE_COUNT = 20

F32_MAX_ENCODING = (1 << 32) - 1
F32_NEGATIVE_INFINITY = 0xFF800000
F32_BYTES = 4

EXCLUDED_DOWNSTREAM_OPERATIONS = (
    "compressor_state_mutation",
    "rms_normalization",
    "rotary_embedding",
    "activation_qdq",
    "compressed_cache_write",
    "compiler_lowering",
    "service_engine_execution",
    "schedule_cycles_ppa",
)


F32Vector: TypeAlias = tuple[int, ...]
F32Sequence: TypeAlias = tuple[F32Vector, ...]
F32Batch: TypeAlias = tuple[F32Sequence, ...]
F32PoolGroup: TypeAlias = tuple[F32Vector, ...]
F32PoolSequence: TypeAlias = tuple[F32PoolGroup, ...]
F32PoolBatch: TypeAlias = tuple[F32PoolSequence, ...]
F32DiagnosticSequence: TypeAlias = tuple[F32Vector, ...]
F32DiagnosticBatch: TypeAlias = tuple[F32DiagnosticSequence, ...]
PoolInputKind: TypeAlias = Literal["direct", "prefill", "decode_window"]
PoolShapeProfile: TypeAlias = Literal[
    "main_ratio4",
    "index_ratio4",
    "main_ratio128",
]


class CompressionPoolReferenceError(ValueError):
    """Raised when a compressor-pool transaction is malformed or poisoned."""


@dataclass(frozen=True)
class CompressionPoolCounters:
    """Exact logical work for one atomic compressor-pool transaction."""

    batch_count: int
    complete_group_count: int
    ratio: int
    overlap: bool
    pool_axis: int
    head_dim: int
    projected_width: int
    source_projected_rows: int
    source_projected_kv_f32_values: int
    source_projected_score_f32_values: int
    source_projected_kv_read_bytes: int
    source_projected_score_read_bytes: int
    logical_ape_f32_values_read: int
    logical_ape_read_bytes: int
    score_ape_additions: int
    pool_kv_f32_values: int
    pool_score_f32_values: int
    overlap_zero_fill_values: int
    overlap_negative_infinity_fill_values: int
    softmax_vectors: int
    softmax_max_comparisons: int
    softmax_finite_subtractions: int
    softmax_exp_evaluations: int
    softmax_negative_infinity_lanes: int
    softmax_reduction_additions: int
    softmax_probability_divisions: int
    weighted_multiplications: int
    weighted_reduction_additions: int
    pooled_output_f32_values: int
    pooled_output_write_bytes: int
    transaction_commits: int


@dataclass(frozen=True)
class CompressionPoolResult:
    """Pooled binary32 values and all visible deterministic intermediates."""

    input_kind: PoolInputKind
    shape_profile: PoolShapeProfile
    ratio: int
    overlap: bool
    head_dim: int
    projected_width: int
    source_sequence_length: int | None
    prefill_cutoff: int | None
    prefill_remainder: int | None
    previous_window_present: bool | None
    pool_kv_f32_codes: F32PoolBatch
    pool_score_f32_codes: F32PoolBatch
    softmax_max_f32_codes: F32DiagnosticBatch
    softmax_denominator_f32_codes: F32DiagnosticBatch
    softmax_probability_f32_codes: F32PoolBatch
    pooled_f32_codes: F32Batch
    counters: CompressionPoolCounters


@dataclass(frozen=True)
class _PoolMetadata:
    input_kind: PoolInputKind
    source_sequence_length: int | None
    prefill_cutoff: int | None
    prefill_remainder: int | None
    previous_window_present: bool | None
    source_projected_rows: int
    source_projected_values: int
    score_ape_additions: int


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise CompressionPoolReferenceError(f"{label} must be an exact list or tuple")
    return value


def _ratio(value: object) -> int:
    if type(value) is not int or value not in PINNED_COMPRESSION_RATIOS:
        raise CompressionPoolReferenceError(
            "ratio must be exactly 4 (overlap) or 128 (non-overlap)"
        )
    return value


def _f32_code(
    value: object,
    label: str,
    *,
    allow_negative_infinity: bool = False,
) -> int:
    if type(value) is not int or not 0 <= value <= F32_MAX_ENCODING:
        raise CompressionPoolReferenceError(
            f"{label} must be a 32-bit binary32 encoding"
        )
    decoded = decode_binary32(value)
    if decoded.finite:
        return value
    if allow_negative_infinity and value == F32_NEGATIVE_INFINITY:
        return value
    permitted = "finite binary32"
    if allow_negative_infinity:
        permitted += " or the negative-infinity overlap sentinel"
    raise CompressionPoolReferenceError(f"{label} must be {permitted}")


def _shape_profile(ratio: int, head_dim: int) -> PoolShapeProfile:
    if ratio == PINNED_OVERLAP_RATIO:
        if head_dim == PINNED_MAIN_HEAD_DIM:
            return "main_ratio4"
        if head_dim == PINNED_INDEX_HEAD_DIM:
            return "index_ratio4"
        raise CompressionPoolReferenceError(
            "ratio-4 head dimension must be exactly 128 (index) or 512 (main)"
        )
    if head_dim != PINNED_MAIN_HEAD_DIM:
        raise CompressionPoolReferenceError(
            "ratio-128 head dimension must be exactly 512"
        )
    return "main_ratio128"


def _freeze_tensor3(
    value: object,
    label: str,
    *,
    batch_count: int | None = None,
    sequence_length: int | None = None,
    width: int | None = None,
    maximum_sequence_length: int = PINNED_MAX_POSITION,
) -> tuple[F32Batch, int, int, int]:
    raw_batches = _sequence(value, label)
    if batch_count is None:
        if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
            raise CompressionPoolReferenceError(
                f"{label} batch extent must be in [1, {PINNED_MAX_BATCH_SIZE}]"
            )
        observed_batches = len(raw_batches)
    else:
        if len(raw_batches) != batch_count:
            raise CompressionPoolReferenceError(
                f"{label} must contain exactly {batch_count} batches"
            )
        observed_batches = batch_count

    observed_sequence = sequence_length
    observed_width = width
    batches: list[F32Sequence] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if observed_sequence is None:
            observed_sequence = len(sequence)
            if not 1 <= observed_sequence <= maximum_sequence_length:
                raise CompressionPoolReferenceError(
                    f"{label} sequence extent must be in [1, {maximum_sequence_length}]"
                )
        elif len(sequence) != observed_sequence:
            raise CompressionPoolReferenceError(
                f"{label} must be rectangular on the sequence axis"
            )

        rows: list[F32Vector] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(raw_row, f"{label}[{batch_index}][{position}]")
            if observed_width is None:
                observed_width = len(row)
                if observed_width < 1:
                    raise CompressionPoolReferenceError(
                        f"{label} rows must contain at least one value"
                    )
            elif len(row) != observed_width:
                raise CompressionPoolReferenceError(
                    f"{label} must be rectangular on the value axis"
                )
            rows.append(
                tuple(
                    _f32_code(
                        code,
                        f"{label}[{batch_index}][{position}][{column}]",
                    )
                    for column, code in enumerate(row)
                )
            )
        batches.append(tuple(rows))

    assert observed_sequence is not None
    assert observed_width is not None
    return tuple(batches), observed_batches, observed_sequence, observed_width


def _freeze_ape(
    value: object,
    *,
    ratio: int,
    width: int,
) -> tuple[F32Vector, ...]:
    rows = _sequence(value, "ape_f32_codes")
    if len(rows) != ratio:
        raise CompressionPoolReferenceError(
            f"ape_f32_codes must contain exactly {ratio} rows"
        )
    result: list[F32Vector] = []
    for position, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"ape_f32_codes[{position}]")
        if len(row) != width:
            raise CompressionPoolReferenceError(
                f"ape_f32_codes[{position}] must contain exactly {width} values"
            )
        result.append(
            tuple(
                _f32_code(
                    code,
                    f"ape_f32_codes[{position}][{column}]",
                )
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def _freeze_pool_tensor(
    value: object,
    label: str,
    *,
    ratio: int,
    batch_count: int | None = None,
    group_count: int | None = None,
    head_dim: int | None = None,
    allow_negative_infinity: bool = False,
) -> tuple[F32PoolBatch, int, int, int]:
    raw_batches = _sequence(value, label)
    if batch_count is None:
        if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
            raise CompressionPoolReferenceError(
                f"{label} batch extent must be in [1, {PINNED_MAX_BATCH_SIZE}]"
            )
        observed_batches = len(raw_batches)
    else:
        if len(raw_batches) != batch_count:
            raise CompressionPoolReferenceError(
                f"{label} must contain exactly {batch_count} batches"
            )
        observed_batches = batch_count

    maximum_groups = PINNED_MAX_POSITION // ratio
    observed_groups = group_count
    observed_head_dim = head_dim
    pool_axis = 2 * ratio if ratio == PINNED_OVERLAP_RATIO else ratio
    batches: list[F32PoolSequence] = []
    for batch_index, raw_groups in enumerate(raw_batches):
        groups = _sequence(raw_groups, f"{label}[{batch_index}]")
        if observed_groups is None:
            observed_groups = len(groups)
            if not 1 <= observed_groups <= maximum_groups:
                raise CompressionPoolReferenceError(
                    f"{label} group extent must be in [1, {maximum_groups}]"
                )
        elif len(groups) != observed_groups:
            raise CompressionPoolReferenceError(
                f"{label} must be rectangular on the group axis"
            )

        frozen_groups: list[F32PoolGroup] = []
        for group_index, raw_group in enumerate(groups):
            group = _sequence(
                raw_group,
                f"{label}[{batch_index}][{group_index}]",
            )
            if len(group) != pool_axis:
                raise CompressionPoolReferenceError(
                    f"{label}[{batch_index}][{group_index}] must contain "
                    f"exactly {pool_axis} pool positions"
                )
            frozen_rows: list[F32Vector] = []
            for pool_position, raw_row in enumerate(group):
                row = _sequence(
                    raw_row,
                    f"{label}[{batch_index}][{group_index}][{pool_position}]",
                )
                if observed_head_dim is None:
                    observed_head_dim = len(row)
                    if observed_head_dim < 1:
                        raise CompressionPoolReferenceError(
                            f"{label} rows must contain at least one value"
                        )
                elif len(row) != observed_head_dim:
                    raise CompressionPoolReferenceError(
                        f"{label} must be rectangular on the value axis"
                    )
                frozen_rows.append(
                    tuple(
                        _f32_code(
                            code,
                            f"{label}[{batch_index}][{group_index}]"
                            f"[{pool_position}][{column}]",
                            allow_negative_infinity=allow_negative_infinity,
                        )
                        for column, code in enumerate(row)
                    )
                )
            frozen_groups.append(tuple(frozen_rows))
        batches.append(tuple(frozen_groups))

    assert observed_groups is not None
    assert observed_head_dim is not None
    return (
        tuple(batches),
        observed_batches,
        observed_groups,
        observed_head_dim,
    )


def _validate_overlap_sentinels(
    kv: F32PoolBatch,
    scores: F32PoolBatch,
    *,
    ratio: int,
) -> int:
    if ratio != PINNED_OVERLAP_RATIO:
        return 0

    padding_values = 0
    group_count = len(kv[0])
    for group_index in range(group_count):
        group_padding: bool | None = None
        for batch_index in range(len(kv)):
            prefix_scores = scores[batch_index][group_index][:ratio]
            prefix_kv = kv[batch_index][group_index][:ratio]
            sentinel_count = sum(
                code == F32_NEGATIVE_INFINITY for row in prefix_scores for code in row
            )
            prefix_value_count = ratio * len(prefix_scores[0])
            if sentinel_count not in {0, prefix_value_count}:
                raise CompressionPoolReferenceError(
                    "ratio-4 overlap sentinel must fill every value in the "
                    "leading four pool rows"
                )
            padded = sentinel_count == prefix_value_count
            if group_padding is None:
                group_padding = padded
            elif group_padding != padded:
                raise CompressionPoolReferenceError(
                    "ratio-4 overlap padding state must match across batches"
                )
            if padded and any(code != 0 for row in prefix_kv for code in row):
                raise CompressionPoolReferenceError(
                    "negative-infinity overlap fill requires positive-zero KV"
                )

            suffix_scores = scores[batch_index][group_index][ratio:]
            if any(
                code == F32_NEGATIVE_INFINITY for row in suffix_scores for code in row
            ):
                raise CompressionPoolReferenceError(
                    "negative-infinity overlap fill is legal only in the "
                    "leading four pool rows"
                )
        if group_padding:
            if group_index != 0:
                raise CompressionPoolReferenceError(
                    "overlap padding is legal only in the first pool group"
                )
            padding_values += len(kv) * ratio * len(kv[0][0][0])
    return padding_values


def _add_ape(
    score: F32Vector,
    ape: F32Vector,
    *,
    batch_index: int,
    source_position: int,
    ape_position: int,
) -> F32Vector:
    output: list[int] = []
    for column, (score_code, ape_code) in enumerate(zip(score, ape, strict=True)):
        try:
            output.append(binary32_add(score_code, ape_code))
        except NumericReferenceError as exc:
            raise CompressionPoolReferenceError(
                "score + APE binary32 arithmetic failed at batch "
                f"{batch_index}, source position {source_position}, "
                f"APE position {ape_position}, column {column}: {exc}"
            ) from exc
    return tuple(output)


def _maximum_finite(codes: tuple[int, ...]) -> tuple[int, int]:
    maximum_code: int | None = None
    maximum_value: Fraction | None = None
    finite_count = 0
    for code in codes:
        if code == F32_NEGATIVE_INFINITY:
            continue
        decoded = decode_binary32(code)
        if not decoded.finite or decoded.value is None:  # pragma: no cover
            raise RuntimeError("validated pool score became nonfinite")
        finite_count += 1
        if maximum_value is None or decoded.value > maximum_value:
            maximum_code = code
            maximum_value = decoded.value
    if maximum_code is None:  # pragma: no cover - sentinel validation invariant
        raise RuntimeError("pool score vector contained no finite lane")
    return maximum_code, finite_count


def _pool_vector(
    kv_codes: tuple[int, ...],
    score_codes: tuple[int, ...],
    *,
    batch_index: int,
    group_index: int,
    column: int,
) -> tuple[int, int, tuple[int, ...], int, int]:
    maximum, finite_count = _maximum_finite(score_codes)
    negative_maximum = maximum ^ 0x80000000
    exponentials: list[int] = []
    try:
        for score in score_codes:
            if score == F32_NEGATIVE_INFINITY:
                exponentials.append(0)
                continue
            delta = binary32_add(score, negative_maximum)
            exponentials.append(binary32_exp_general_rne(delta))
        denominator = binary32_balanced_sum(exponentials)
        denominator_value = decode_binary32(denominator)
        if (
            not denominator_value.finite
            or denominator_value.value is None
            or denominator_value.value <= 0
        ):  # pragma: no cover - maximum contributes exp(0) == 1
            raise CompressionPoolReferenceError(
                "compressor-pool softmax denominator must be positive finite"
            )
        probabilities = tuple(
            binary32_divide(exponential, denominator) for exponential in exponentials
        )
        products = tuple(
            binary32_multiply(kv, probability)
            for kv, probability in zip(kv_codes, probabilities, strict=True)
        )
        pooled = binary32_balanced_sum(products)
    except (NumericReferenceError, TranscendentalReferenceError) as exc:
        raise CompressionPoolReferenceError(
            "compressor-pool arithmetic failed at batch "
            f"{batch_index}, group {group_index}, column {column}: {exc}"
        ) from exc
    return maximum, denominator, probabilities, pooled, finite_count


def _pool_validated(
    pool_kv: F32PoolBatch,
    pool_scores: F32PoolBatch,
    *,
    ratio: int,
    shape_profile: PoolShapeProfile,
    head_dim: int,
    metadata: _PoolMetadata,
    overlap_fill_values: int,
) -> CompressionPoolResult:
    batch_count = len(pool_kv)
    group_count = len(pool_kv[0])
    overlap = ratio == PINNED_OVERLAP_RATIO
    coefficient = 2 if overlap else 1
    pool_axis = coefficient * ratio
    projected_width = coefficient * head_dim

    maxima_batches: list[F32DiagnosticSequence] = []
    denominator_batches: list[F32DiagnosticSequence] = []
    probability_batches: list[F32PoolSequence] = []
    output_batches: list[F32Sequence] = []
    finite_lane_count = 0

    for batch_index in range(batch_count):
        batch_maxima: list[F32Vector] = []
        batch_denominators: list[F32Vector] = []
        batch_probabilities: list[F32PoolGroup] = []
        batch_outputs: list[F32Vector] = []
        for group_index in range(group_count):
            group_maxima: list[int] = []
            group_denominators: list[int] = []
            probability_rows: list[list[int]] = [[] for _ in range(pool_axis)]
            pooled_row: list[int] = []
            for column in range(head_dim):
                kv_vector = tuple(
                    pool_kv[batch_index][group_index][position][column]
                    for position in range(pool_axis)
                )
                score_vector = tuple(
                    pool_scores[batch_index][group_index][position][column]
                    for position in range(pool_axis)
                )
                (
                    maximum,
                    denominator,
                    probabilities,
                    pooled,
                    finite_count,
                ) = _pool_vector(
                    kv_vector,
                    score_vector,
                    batch_index=batch_index,
                    group_index=group_index,
                    column=column,
                )
                group_maxima.append(maximum)
                group_denominators.append(denominator)
                pooled_row.append(pooled)
                finite_lane_count += finite_count
                for position, probability in enumerate(probabilities):
                    probability_rows[position].append(probability)
            batch_maxima.append(tuple(group_maxima))
            batch_denominators.append(tuple(group_denominators))
            batch_probabilities.append(tuple(tuple(row) for row in probability_rows))
            batch_outputs.append(tuple(pooled_row))
        maxima_batches.append(tuple(batch_maxima))
        denominator_batches.append(tuple(batch_denominators))
        probability_batches.append(tuple(batch_probabilities))
        output_batches.append(tuple(batch_outputs))

    pool_values = batch_count * group_count * pool_axis * head_dim
    output_values = batch_count * group_count * head_dim
    negative_infinity_lanes = pool_values - finite_lane_count
    reduction_additions = output_values * (pool_axis - 1)
    counters = CompressionPoolCounters(
        batch_count=batch_count,
        complete_group_count=group_count,
        ratio=ratio,
        overlap=overlap,
        pool_axis=pool_axis,
        head_dim=head_dim,
        projected_width=projected_width,
        source_projected_rows=metadata.source_projected_rows,
        source_projected_kv_f32_values=metadata.source_projected_values,
        source_projected_score_f32_values=metadata.source_projected_values,
        source_projected_kv_read_bytes=(metadata.source_projected_values * F32_BYTES),
        source_projected_score_read_bytes=(
            metadata.source_projected_values * F32_BYTES
        ),
        logical_ape_f32_values_read=metadata.score_ape_additions,
        logical_ape_read_bytes=metadata.score_ape_additions * F32_BYTES,
        score_ape_additions=metadata.score_ape_additions,
        pool_kv_f32_values=pool_values,
        pool_score_f32_values=pool_values,
        overlap_zero_fill_values=overlap_fill_values,
        overlap_negative_infinity_fill_values=overlap_fill_values,
        softmax_vectors=output_values,
        softmax_max_comparisons=output_values * (pool_axis - 1),
        softmax_finite_subtractions=finite_lane_count,
        softmax_exp_evaluations=finite_lane_count,
        softmax_negative_infinity_lanes=negative_infinity_lanes,
        softmax_reduction_additions=reduction_additions,
        softmax_probability_divisions=pool_values,
        weighted_multiplications=pool_values,
        weighted_reduction_additions=reduction_additions,
        pooled_output_f32_values=output_values,
        pooled_output_write_bytes=output_values * F32_BYTES,
        transaction_commits=1,
    )
    return CompressionPoolResult(
        input_kind=metadata.input_kind,
        shape_profile=shape_profile,
        ratio=ratio,
        overlap=overlap,
        head_dim=head_dim,
        projected_width=projected_width,
        source_sequence_length=metadata.source_sequence_length,
        prefill_cutoff=metadata.prefill_cutoff,
        prefill_remainder=metadata.prefill_remainder,
        previous_window_present=metadata.previous_window_present,
        pool_kv_f32_codes=pool_kv,
        pool_score_f32_codes=pool_scores,
        softmax_max_f32_codes=tuple(maxima_batches),
        softmax_denominator_f32_codes=tuple(denominator_batches),
        softmax_probability_f32_codes=tuple(probability_batches),
        pooled_f32_codes=tuple(output_batches),
        counters=counters,
    )


def compress_pool_f32(
    pool_kv_f32_codes: object,
    pool_score_f32_codes: object,
    *,
    ratio: int,
) -> CompressionPoolResult:
    """Pool validated ``[B,G,P,D]`` state-handoff operands.

    ``P`` is eight for ratio four and 128 for ratio 128.  Ratio-four permits
    the exact leading zero/negative-infinity block produced by the official
    overlap transform; all other score lanes must be finite.  No caller-owned
    tensor is mutated.
    """

    ratio = _ratio(ratio)
    overlap = ratio == PINNED_OVERLAP_RATIO
    pool_kv, batch_count, group_count, head_dim = _freeze_pool_tensor(
        pool_kv_f32_codes,
        "pool_kv_f32_codes",
        ratio=ratio,
    )
    shape_profile = _shape_profile(ratio, head_dim)
    pool_scores, _, _, _ = _freeze_pool_tensor(
        pool_score_f32_codes,
        "pool_score_f32_codes",
        ratio=ratio,
        batch_count=batch_count,
        group_count=group_count,
        head_dim=head_dim,
        allow_negative_infinity=overlap,
    )
    overlap_fill_values = _validate_overlap_sentinels(
        pool_kv,
        pool_scores,
        ratio=ratio,
    )
    metadata = _PoolMetadata(
        input_kind="direct",
        source_sequence_length=None,
        prefill_cutoff=None,
        prefill_remainder=None,
        previous_window_present=None,
        source_projected_rows=0,
        source_projected_values=0,
        score_ape_additions=0,
    )
    return _pool_validated(
        pool_kv,
        pool_scores,
        ratio=ratio,
        shape_profile=shape_profile,
        head_dim=head_dim,
        metadata=metadata,
        overlap_fill_values=overlap_fill_values,
    )


def _freeze_projected_inputs(
    projected_kv_f32_codes: object,
    projected_score_f32_codes: object,
    ape_f32_codes: object,
    *,
    ratio: int,
    expected_sequence_length: int | None = None,
) -> tuple[
    F32Batch,
    F32Batch,
    tuple[F32Vector, ...],
    int,
    int,
    int,
    int,
    PoolShapeProfile,
]:
    maximum_sequence_length = (
        expected_sequence_length
        if expected_sequence_length is not None
        else PINNED_MAX_POSITION
    )
    kv, batch_count, sequence_length, projected_width = _freeze_tensor3(
        projected_kv_f32_codes,
        "projected_kv_f32_codes",
        sequence_length=expected_sequence_length,
        maximum_sequence_length=maximum_sequence_length,
    )
    overlap = ratio == PINNED_OVERLAP_RATIO
    coefficient = 2 if overlap else 1
    if projected_width % coefficient:
        raise CompressionPoolReferenceError(
            "ratio-4 projected width must be divisible into two feature halves"
        )
    head_dim = projected_width // coefficient
    shape_profile = _shape_profile(ratio, head_dim)
    scores, _, _, _ = _freeze_tensor3(
        projected_score_f32_codes,
        "projected_score_f32_codes",
        batch_count=batch_count,
        sequence_length=sequence_length,
        width=projected_width,
        maximum_sequence_length=maximum_sequence_length,
    )
    ape = _freeze_ape(
        ape_f32_codes,
        ratio=ratio,
        width=projected_width,
    )
    return (
        kv,
        scores,
        ape,
        batch_count,
        sequence_length,
        projected_width,
        head_dim,
        shape_profile,
    )


def _biased_scores(
    scores: F32Batch,
    ape: tuple[F32Vector, ...],
    *,
    source_rows: int,
    ratio: int,
) -> F32Batch:
    return tuple(
        tuple(
            _add_ape(
                sequence[position],
                ape[position % ratio],
                batch_index=batch_index,
                source_position=position,
                ape_position=position % ratio,
            )
            for position in range(source_rows)
        )
        for batch_index, sequence in enumerate(scores)
    )


def _assemble_prefill_groups(
    kv: F32Batch,
    biased_scores: F32Batch,
    *,
    ratio: int,
    cutoff: int,
    head_dim: int,
) -> tuple[F32PoolBatch, F32PoolBatch, int]:
    overlap = ratio == PINNED_OVERLAP_RATIO
    group_count = cutoff // ratio
    zero_row = (0,) * head_dim
    negative_infinity_row = (F32_NEGATIVE_INFINITY,) * head_dim
    kv_batches: list[F32PoolSequence] = []
    score_batches: list[F32PoolSequence] = []

    for batch_index in range(len(kv)):
        kv_groups: list[F32PoolGroup] = []
        score_groups: list[F32PoolGroup] = []
        for group_index in range(group_count):
            group_start = group_index * ratio
            if not overlap:
                kv_groups.append(
                    tuple(
                        kv[batch_index][group_start + phase] for phase in range(ratio)
                    )
                )
                score_groups.append(
                    tuple(
                        biased_scores[batch_index][group_start + phase]
                        for phase in range(ratio)
                    )
                )
                continue

            if group_index == 0:
                kv_rows: list[F32Vector] = [zero_row] * ratio
                score_rows: list[F32Vector] = [negative_infinity_row] * ratio
            else:
                previous_start = group_start - ratio
                kv_rows = [
                    kv[batch_index][previous_start + phase][:head_dim]
                    for phase in range(ratio)
                ]
                score_rows = [
                    biased_scores[batch_index][previous_start + phase][:head_dim]
                    for phase in range(ratio)
                ]
            kv_rows.extend(
                kv[batch_index][group_start + phase][head_dim:]
                for phase in range(ratio)
            )
            score_rows.extend(
                biased_scores[batch_index][group_start + phase][head_dim:]
                for phase in range(ratio)
            )
            kv_groups.append(tuple(kv_rows))
            score_groups.append(tuple(score_rows))
        kv_batches.append(tuple(kv_groups))
        score_batches.append(tuple(score_groups))

    overlap_fill_values = len(kv) * ratio * head_dim if overlap and group_count else 0
    return tuple(kv_batches), tuple(score_batches), overlap_fill_values


def compress_pool_prefill_f32(
    projected_kv_f32_codes: object,
    projected_score_f32_codes: object,
    ape_f32_codes: object,
    *,
    ratio: int,
) -> CompressionPoolResult | None:
    """Add APE, apply prefill overlap semantics, and pool complete groups.

    A trailing incomplete group is validated but remains a compressor-state
    responsibility.  When the sequence contains no complete group, the
    function returns ``None`` exactly like the source's no-compression branch.
    """

    ratio = _ratio(ratio)
    (
        kv,
        scores,
        ape,
        batch_count,
        sequence_length,
        projected_width,
        head_dim,
        shape_profile,
    ) = _freeze_projected_inputs(
        projected_kv_f32_codes,
        projected_score_f32_codes,
        ape_f32_codes,
        ratio=ratio,
    )
    remainder = sequence_length % ratio
    cutoff = sequence_length - remainder
    if cutoff == 0:
        return None

    biased_scores = _biased_scores(
        scores,
        ape,
        source_rows=cutoff,
        ratio=ratio,
    )
    pool_kv, pool_scores, overlap_fill_values = _assemble_prefill_groups(
        kv,
        biased_scores,
        ratio=ratio,
        cutoff=cutoff,
        head_dim=head_dim,
    )
    metadata = _PoolMetadata(
        input_kind="prefill",
        source_sequence_length=sequence_length,
        prefill_cutoff=cutoff,
        prefill_remainder=remainder,
        previous_window_present=None,
        source_projected_rows=batch_count * cutoff,
        source_projected_values=batch_count * cutoff * projected_width,
        score_ape_additions=batch_count * cutoff * projected_width,
    )
    return _pool_validated(
        pool_kv,
        pool_scores,
        ratio=ratio,
        shape_profile=shape_profile,
        head_dim=head_dim,
        metadata=metadata,
        overlap_fill_values=overlap_fill_values,
    )


def compress_pool_decode_window_f32(
    current_kv_f32_codes: object,
    current_score_f32_codes: object,
    ape_f32_codes: object,
    *,
    ratio: int,
    previous_kv_f32_codes: object | None = None,
    previous_score_f32_codes: object | None = None,
) -> CompressionPoolResult:
    """Pool one complete decode window without owning mutable state.

    Current inputs contain exactly ``ratio`` raw projected rows.  Ratio four
    optionally accepts the preceding raw projected group; when absent, the
    helper models the first completed window with official zero/-infinity
    overlap fill.  Ratio 128 rejects preceding-group inputs.  Scores supplied
    here are raw projection results, so this equivalence helper applies APE to
    every supplied row before selecting the feature halves used by pooling.
    """

    ratio = _ratio(ratio)
    overlap = ratio == PINNED_OVERLAP_RATIO
    previous_pair = (
        previous_kv_f32_codes is not None,
        previous_score_f32_codes is not None,
    )
    if previous_pair[0] != previous_pair[1]:
        raise CompressionPoolReferenceError(
            "previous KV and score decode windows must be supplied together"
        )
    if not overlap and previous_pair[0]:
        raise CompressionPoolReferenceError(
            "ratio-128 decode pooling does not accept a previous window"
        )

    (
        current_kv,
        current_scores,
        ape,
        batch_count,
        sequence_length,
        projected_width,
        head_dim,
        shape_profile,
    ) = _freeze_projected_inputs(
        current_kv_f32_codes,
        current_score_f32_codes,
        ape_f32_codes,
        ratio=ratio,
        expected_sequence_length=ratio,
    )
    previous_kv: F32Batch | None = None
    previous_scores: F32Batch | None = None
    if previous_pair[0]:
        previous_kv, previous_batches, previous_length, previous_width = (
            _freeze_tensor3(
                previous_kv_f32_codes,
                "previous_kv_f32_codes",
                batch_count=batch_count,
                sequence_length=ratio,
                width=projected_width,
                maximum_sequence_length=ratio,
            )
        )
        assert previous_batches == batch_count
        assert previous_length == ratio
        assert previous_width == projected_width
        previous_scores, _, _, _ = _freeze_tensor3(
            previous_score_f32_codes,
            "previous_score_f32_codes",
            batch_count=batch_count,
            sequence_length=ratio,
            width=projected_width,
            maximum_sequence_length=ratio,
        )
    # The whole transaction, including an optional preceding group, is frozen
    # before the first score-plus-APE arithmetic boundary executes.
    current_biased = _biased_scores(
        current_scores,
        ape,
        source_rows=ratio,
        ratio=ratio,
    )
    previous_biased: F32Batch | None = None
    if previous_scores is not None:
        previous_biased = _biased_scores(
            previous_scores,
            ape,
            source_rows=ratio,
            ratio=ratio,
        )

    zero_row = (0,) * head_dim
    negative_infinity_row = (F32_NEGATIVE_INFINITY,) * head_dim
    pool_kv_batches: list[F32PoolSequence] = []
    pool_score_batches: list[F32PoolSequence] = []
    for batch_index in range(batch_count):
        if overlap:
            if previous_kv is None:
                kv_rows: list[F32Vector] = [zero_row] * ratio
                score_rows: list[F32Vector] = [negative_infinity_row] * ratio
            else:
                assert previous_biased is not None
                kv_rows = [
                    previous_kv[batch_index][phase][:head_dim] for phase in range(ratio)
                ]
                score_rows = [
                    previous_biased[batch_index][phase][:head_dim]
                    for phase in range(ratio)
                ]
            kv_rows.extend(
                current_kv[batch_index][phase][head_dim:] for phase in range(ratio)
            )
            score_rows.extend(
                current_biased[batch_index][phase][head_dim:] for phase in range(ratio)
            )
        else:
            kv_rows = list(current_kv[batch_index])
            score_rows = list(current_biased[batch_index])
        pool_kv_batches.append((tuple(kv_rows),))
        pool_score_batches.append((tuple(score_rows),))

    supplied_group_count = 1 + int(previous_pair[0])
    source_values = batch_count * supplied_group_count * ratio * projected_width
    overlap_fill_values = (
        batch_count * ratio * head_dim if overlap and not previous_pair[0] else 0
    )
    metadata = _PoolMetadata(
        input_kind="decode_window",
        source_sequence_length=sequence_length,
        prefill_cutoff=None,
        prefill_remainder=None,
        previous_window_present=previous_pair[0],
        source_projected_rows=batch_count * supplied_group_count * ratio,
        source_projected_values=source_values,
        score_ape_additions=source_values,
    )
    return _pool_validated(
        tuple(pool_kv_batches),
        tuple(pool_score_batches),
        ratio=ratio,
        shape_profile=shape_profile,
        head_dim=head_dim,
        metadata=metadata,
        overlap_fill_values=overlap_fill_values,
    )


__all__ = [
    "COMPRESS_POOL_NUMERIC_PROFILE",
    "EXCLUDED_DOWNSTREAM_OPERATIONS",
    "F32_BYTES",
    "F32_MAX_ENCODING",
    "F32_NEGATIVE_INFINITY",
    "INFERENCE_CONFIG_SHA256",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "PINNED_COMPRESSION_RATIOS",
    "PINNED_INDEX_HEAD_DIM",
    "PINNED_INDEX_RATIO4_SITE_COUNT",
    "PINNED_MAIN_HEAD_DIM",
    "PINNED_MAIN_RATIO4_SITE_COUNT",
    "PINNED_MAIN_RATIO128_SITE_COUNT",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "PINNED_NONOVERLAP_RATIO",
    "PINNED_OVERLAP_RATIO",
    "PINNED_RATIO4_HEAD_DIMS",
    "CompressionPoolCounters",
    "CompressionPoolReferenceError",
    "CompressionPoolResult",
    "PoolInputKind",
    "PoolShapeProfile",
    "compress_pool_decode_window_f32",
    "compress_pool_f32",
    "compress_pool_prefill_f32",
]
