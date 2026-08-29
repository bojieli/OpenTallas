"""Deterministic DeepSeek V4 sparse-attention reference semantics.

The pinned TileLang kernel gathers selected mutable BF16 KV rows in blocks of
64, forms BF16 QK products into binary32 accumulators, performs an online
softmax with one learned binary32 attention-sink logit, converts probabilities
to BF16, and accumulates BF16 probability-times-KV products into binary32.

TileLang leaves GEMM association, reduction trees, exponential approximation,
FMA contraction, and exceptional behavior backend-dependent.  This independent
reference freezes those boundaries for OpenTallas while retaining the exact
source block order.  It also distinguishes valid selected KV traffic from
explicit ``-1`` and implicit tail padding: only valid occurrences read mutable
KV bytes, while duplicates remain separate reads and contributions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    binary32_ordered_dot,
    binary32_product_add,
    decode_bf16,
    decode_binary32,
)
from .transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)
SPARSE_ATTENTION_NUMERIC_PROFILE = (
    "opentallas.deepseek_v4_sparse_attention_numeric.v1"
)
SPARSE_ATTENTION_SITE_COUNT = 46
SPARSE_ATTENTION_HEADS = 64
SPARSE_ATTENTION_HEAD_DIM = 512
SPARSE_ATTENTION_BLOCK_SIZE = 64
SPARSE_ATTENTION_SCALE_BINARY32 = 0x3D3504F3
SPARSE_ATTENTION_KV_BYTES_PER_SELECTED_ROW = 1_024
BF16_MAX_ENCODING = (1 << 16) - 1
INT32_MAX = (1 << 31) - 1


BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Matrix, ...]
BF16Query: TypeAlias = tuple[tuple[tuple[BF16Vector, ...], ...], ...]
BF16Output: TypeAlias = BF16Query
BF16ValueVector: TypeAlias = tuple[Fraction, ...]
BF16ValueMatrix: TypeAlias = tuple[BF16ValueVector, ...]
BF16ValueBatch: TypeAlias = tuple[BF16ValueMatrix, ...]
BF16QueryValues: TypeAlias = tuple[
    tuple[tuple[BF16ValueVector, ...], ...], ...
]
IndexTensor: TypeAlias = tuple[tuple[tuple[int, ...], ...], ...]
Binary32HeadTensor: TypeAlias = tuple[tuple[tuple[int, ...], ...], ...]


class SparseAttentionReferenceError(ValueError):
    """Raised when a sparse-attention transaction is malformed or poisoned."""


@dataclass(frozen=True)
class SparseAttentionCounters:
    """Exact logical source work and mutable-KV traffic for one command."""

    output_rows: int
    source_blocks: int
    query_bf16_values: int
    query_bf16_read_bytes: int
    attention_sink_binary32_reads: int
    attention_sink_binary32_read_bytes: int
    logical_index_slots: int
    selected_index_int32_reads: int
    selected_index_read_bytes: int
    explicit_padding_slots: int
    implicit_tail_padding_lanes: int
    block_compute_lanes: int
    valid_selected_rows: int
    unique_selected_rows: int
    duplicate_selected_rows: int
    selected_kv_bf16_values: int
    selected_kv_read_bytes: int
    qk_valid_product_accumulates: int
    qk_padding_product_lanes: int
    score_scale_multiplies: int
    online_rescale_exp_evaluations: int
    score_exp_evaluations: int
    score_reduction_adds: int
    online_denominator_multiplies: int
    online_denominator_adds: int
    probability_bf16_conversions: int
    output_rescale_multiplies: int
    av_product_accumulates: int
    sink_exp_evaluations: int
    sink_denominator_adds: int
    final_binary32_divides: int
    output_bf16_conversions: int
    output_bf16_write_bytes: int


@dataclass(frozen=True)
class SparseAttentionResult:
    """BF16 output, final online-softmax observables, and exact counters."""

    values: BF16Output
    final_max_binary32_codes: Binary32HeadTensor
    sink_exp_binary32_codes: Binary32HeadTensor
    final_denominator_binary32_codes: Binary32HeadTensor
    output_saturated_element_count: int
    counters: SparseAttentionCounters


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SparseAttentionReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16(code: object, label: str) -> Fraction:
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or not 0 <= code <= BF16_MAX_ENCODING
    ):
        raise SparseAttentionReferenceError(
            f"{label} must be a 16-bit BF16 encoding"
        )
    decoded = decode_bf16(code)
    if not decoded.finite or decoded.value is None:
        raise SparseAttentionReferenceError(f"{label} must be finite BF16")
    return decoded.value


def _finite_binary32(code: object, label: str) -> tuple[int, Fraction]:
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or not 0 <= code < 1 << 32
    ):
        raise SparseAttentionReferenceError(
            f"{label} must be a 32-bit binary32 encoding"
        )
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None:
        raise SparseAttentionReferenceError(f"{label} must be finite binary32")
    return code, decoded.value


def _finite_query(
    value: object,
) -> tuple[BF16QueryValues, int, int, int, int]:
    raw_batches = _sequence(value, "query_bf16_codes")
    if not raw_batches:
        raise SparseAttentionReferenceError(
            "query_bf16_codes must contain at least one batch"
        )

    result: list[tuple[tuple[BF16ValueVector, ...], ...]] = []
    sequence_length: int | None = None
    head_count: int | None = None
    head_dim: int | None = None
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"query_bf16_codes[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise SparseAttentionReferenceError(
                    "query_bf16_codes must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise SparseAttentionReferenceError(
                "query_bf16_codes must be a rectangular rank-4 tensor"
            )

        positions: list[tuple[BF16ValueVector, ...]] = []
        for position, raw_heads in enumerate(sequence):
            heads = _sequence(
                raw_heads,
                f"query_bf16_codes[{batch_index}][{position}]",
            )
            if head_count is None:
                head_count = len(heads)
                if head_count == 0:
                    raise SparseAttentionReferenceError(
                        "query_bf16_codes must contain at least one head"
                    )
            elif len(heads) != head_count:
                raise SparseAttentionReferenceError(
                    "query_bf16_codes must be a rectangular rank-4 tensor"
                )

            head_values: list[BF16ValueVector] = []
            for head, raw_row in enumerate(heads):
                row = _sequence(
                    raw_row,
                    f"query_bf16_codes[{batch_index}][{position}][{head}]",
                )
                if head_dim is None:
                    head_dim = len(row)
                    if head_dim == 0:
                        raise SparseAttentionReferenceError(
                            "query_bf16_codes heads must contain at least one value"
                        )
                elif len(row) != head_dim:
                    raise SparseAttentionReferenceError(
                        "query_bf16_codes must be a rectangular rank-4 tensor"
                    )
                head_values.append(
                    tuple(
                        _finite_bf16(
                            code,
                            "query_bf16_codes"
                            f"[{batch_index}][{position}][{head}][{column}]",
                        )
                        for column, code in enumerate(row)
                    )
                )
            positions.append(tuple(head_values))
        result.append(tuple(positions))

    assert sequence_length is not None
    assert head_count is not None
    assert head_dim is not None
    return (
        tuple(result),
        len(raw_batches),
        sequence_length,
        head_count,
        head_dim,
    )


def _finite_kv(
    value: object,
    *,
    batch_size: int,
    head_dim: int,
) -> tuple[BF16ValueBatch, int]:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if len(raw_batches) != batch_size:
        raise SparseAttentionReferenceError(
            "kv_bf16_codes batch count must match query_bf16_codes"
        )

    result: list[BF16ValueMatrix] = []
    row_count: int | None = None
    for batch_index, raw_rows in enumerate(raw_batches):
        rows = _sequence(raw_rows, f"kv_bf16_codes[{batch_index}]")
        if row_count is None:
            row_count = len(rows)
            if row_count == 0:
                raise SparseAttentionReferenceError(
                    "kv_bf16_codes must contain at least one row per batch"
                )
        elif len(rows) != row_count:
            raise SparseAttentionReferenceError(
                "kv_bf16_codes must be rectangular on the row axis"
            )

        row_values: list[BF16ValueVector] = []
        for row_index, raw_row in enumerate(rows):
            row = _sequence(
                raw_row,
                f"kv_bf16_codes[{batch_index}][{row_index}]",
            )
            if len(row) != head_dim:
                raise SparseAttentionReferenceError(
                    f"kv_bf16_codes[{batch_index}][{row_index}] must have "
                    f"head dimension {head_dim}"
                )
            row_values.append(
                tuple(
                    _finite_bf16(
                        code,
                        f"kv_bf16_codes[{batch_index}]"
                        f"[{row_index}][{column}]",
                    )
                    for column, code in enumerate(row)
                )
            )
        result.append(tuple(row_values))

    assert row_count is not None
    return tuple(result), row_count


def _finite_sinks(value: object, *, head_count: int) -> tuple[int, ...]:
    raw = _sequence(value, "attention_sink_binary32_codes")
    if len(raw) != head_count:
        raise SparseAttentionReferenceError(
            "attention_sink_binary32_codes length must match query heads"
        )
    return tuple(
        _finite_binary32(code, f"attention_sink_binary32_codes[{head}]")[0]
        for head, code in enumerate(raw)
    )


def _indices(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    kv_row_count: int,
) -> tuple[IndexTensor, int, int, int, int]:
    raw_batches = _sequence(value, "selected_indices")
    if len(raw_batches) != batch_size:
        raise SparseAttentionReferenceError(
            "selected_indices batch count must match query_bf16_codes"
        )

    result: list[tuple[tuple[int, ...], ...]] = []
    topk: int | None = None
    explicit_padding = 0
    valid_selected = 0
    unique_selected = 0
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"selected_indices[{batch_index}]")
        if len(sequence) != sequence_length:
            raise SparseAttentionReferenceError(
                "selected_indices sequence length must match query_bf16_codes"
            )

        rows: list[tuple[int, ...]] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(
                raw_row,
                f"selected_indices[{batch_index}][{position}]",
            )
            if topk is None:
                topk = len(row)
                if topk == 0:
                    raise SparseAttentionReferenceError(
                        "selected_indices must contain at least one slot"
                    )
            elif len(row) != topk:
                raise SparseAttentionReferenceError(
                    "selected_indices must be a rectangular rank-3 tensor"
                )

            checked: list[int] = []
            valid_row: list[int] = []
            for slot, index in enumerate(row):
                if (
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or index < -1
                    or index > INT32_MAX
                ):
                    raise SparseAttentionReferenceError(
                        f"selected_indices[{batch_index}][{position}]"
                        f"[{slot}] must be -1 or a nonnegative INT32 index"
                    )
                if index >= kv_row_count:
                    raise SparseAttentionReferenceError(
                        f"selected_indices[{batch_index}][{position}]"
                        f"[{slot}] is outside {kv_row_count} KV rows"
                    )
                checked.append(index)
                if index == -1:
                    explicit_padding += 1
                else:
                    valid_row.append(index)
                    valid_selected += 1

            # The official kernel starts scores_max at -infinity.  An all-pad
            # first source block makes its first rescale expression -inf - -inf
            # and is therefore not a legal finite target transaction.  Official
            # window-index construction always supplies an early valid entry.
            if not any(index != -1 for index in checked[:SPARSE_ATTENTION_BLOCK_SIZE]):
                raise SparseAttentionReferenceError(
                    f"selected_indices[{batch_index}][{position}] first "
                    "64-slot source block must contain a valid KV row"
                )
            unique_selected += len(set(valid_row))
            rows.append(tuple(checked))
        result.append(tuple(rows))

    assert topk is not None
    return (
        tuple(result),
        topk,
        explicit_padding,
        valid_selected,
        unique_selected,
    )


def _subtract(left_code: int, right_code: int) -> int:
    return binary32_add(left_code, right_code ^ 0x80000000)


def _maximum(codes: Sequence[int]) -> int:
    if not codes:
        raise RuntimeError("maximum input must not be empty")
    maximum_code = codes[0]
    maximum = decode_binary32(maximum_code).value
    if maximum is None:  # pragma: no cover - computation invariant
        raise RuntimeError("score maximum received a nonfinite value")
    for code in codes[1:]:
        value = decode_binary32(code).value
        if value is None:  # pragma: no cover - computation invariant
            raise RuntimeError("score maximum received a nonfinite value")
        if value > maximum:
            maximum_code = code
            maximum = value
    return maximum_code


def _positive(code: int, label: str) -> None:
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None or decoded.value <= 0:
        raise SparseAttentionReferenceError(f"{label} must be positive finite binary32")


def sparse_attention_bf16(
    query_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    kv_bf16_codes: Sequence[Sequence[Sequence[int]]],
    attention_sink_binary32_codes: Sequence[int],
    selected_indices: Sequence[Sequence[Sequence[int]]],
    *,
    scale_binary32: int = SPARSE_ATTENTION_SCALE_BINARY32,
) -> SparseAttentionResult:
    """Execute the governed block-64 sparse-attention transaction.

    Arbitrary positive head counts and dimensions are accepted for bounded unit
    cases.  The graph-qualified profile fixes 64 heads, dimension 512, scale
    ``0x3d3504f3``, and 46 operator sites.  All inputs validate before numeric
    execution, and every output is assembled before the immutable result is
    returned; any intermediate binary32 overflow poisons the whole command.
    """

    query, batch_size, sequence_length, head_count, head_dim = _finite_query(
        query_bf16_codes
    )
    kv, kv_row_count = _finite_kv(
        kv_bf16_codes,
        batch_size=batch_size,
        head_dim=head_dim,
    )
    sinks = _finite_sinks(
        attention_sink_binary32_codes,
        head_count=head_count,
    )
    scale_code, scale_value = _finite_binary32(
        scale_binary32,
        "scale_binary32",
    )
    if scale_value <= 0:
        raise SparseAttentionReferenceError(
            "scale_binary32 must be greater than zero"
        )
    (
        indices,
        topk,
        explicit_padding,
        valid_selected,
        unique_selected,
    ) = _indices(
        selected_indices,
        batch_size=batch_size,
        sequence_length=sequence_length,
        kv_row_count=kv_row_count,
    )

    block_count = (topk + SPARSE_ATTENTION_BLOCK_SIZE - 1) // SPARSE_ATTENTION_BLOCK_SIZE
    output_rows = batch_size * sequence_length
    block_compute_lanes = output_rows * block_count * SPARSE_ATTENTION_BLOCK_SIZE
    implicit_tail = output_rows * (
        block_count * SPARSE_ATTENTION_BLOCK_SIZE - topk
    )
    padded_lanes = explicit_padding + implicit_tail

    outputs: list[tuple[tuple[BF16Vector, ...], ...]] = []
    all_maxima: list[tuple[tuple[int, ...], ...]] = []
    all_sink_exps: list[tuple[tuple[int, ...], ...]] = []
    all_denominators: list[tuple[tuple[int, ...], ...]] = []
    saturation_count = 0

    try:
        for batch_index in range(batch_size):
            batch_outputs: list[tuple[BF16Vector, ...]] = []
            batch_maxima: list[tuple[int, ...]] = []
            batch_sink_exps: list[tuple[int, ...]] = []
            batch_denominators: list[tuple[int, ...]] = []
            for position in range(sequence_length):
                row_indices = indices[batch_index][position]
                maxima: list[int | None] = [None] * head_count
                sums = [0] * head_count
                accumulators = [[0] * head_dim for _ in range(head_count)]

                for block_index in range(block_count):
                    start = block_index * SPARSE_ATTENTION_BLOCK_SIZE
                    block_indices = list(
                        row_indices[start : start + SPARSE_ATTENTION_BLOCK_SIZE]
                    )
                    block_indices.extend(
                        [-1]
                        * (SPARSE_ATTENTION_BLOCK_SIZE - len(block_indices))
                    )

                    for head in range(head_count):
                        score_codes: list[int | None] = []
                        for index in block_indices:
                            if index == -1:
                                score_codes.append(None)
                                continue
                            qk = binary32_ordered_dot(
                                query[batch_index][position][head],
                                kv[batch_index][index],
                            )
                            score_codes.append(binary32_multiply(qk, scale_code))

                        finite_scores = [
                            code for code in score_codes if code is not None
                        ]
                        previous_maximum = maxima[head]
                        if previous_maximum is None:
                            if not finite_scores:  # pragma: no cover - prevalidated
                                raise RuntimeError(
                                    "first sparse-attention block had no finite score"
                                )
                            new_maximum = _maximum(finite_scores)
                            scores_scale = 0
                        elif finite_scores:
                            new_maximum = _maximum(
                                (previous_maximum, *finite_scores)
                            )
                            scores_scale = binary32_exp_general_rne(
                                _subtract(previous_maximum, new_maximum)
                            )
                        else:
                            new_maximum = previous_maximum
                            scores_scale = 0x3F800000

                        probability_codes = tuple(
                            0
                            if score is None
                            else binary32_exp_general_rne(
                                _subtract(score, new_maximum)
                            )
                            for score in score_codes
                        )
                        block_sum = binary32_balanced_sum(probability_codes)
                        sums[head] = binary32_add(
                            binary32_multiply(sums[head], scores_scale),
                            block_sum,
                        )
                        probability_bf16 = tuple(
                            binary32_bits_to_bf16_rne(code).code
                            for code in probability_codes
                        )
                        probability_values = tuple(
                            decode_bf16(code).value for code in probability_bf16
                        )
                        if any(value is None for value in probability_values):
                            raise RuntimeError(
                                "finite probability conversion became nonfinite"
                            )

                        for column in range(head_dim):
                            accumulator = binary32_multiply(
                                accumulators[head][column],
                                scores_scale,
                            )
                            for lane, index in enumerate(block_indices):
                                kv_value = (
                                    Fraction(0)
                                    if index == -1
                                    else kv[batch_index][index][column]
                                )
                                probability = probability_values[lane]
                                assert probability is not None
                                accumulator = binary32_product_add(
                                    accumulator,
                                    probability,
                                    kv_value,
                                )
                            accumulators[head][column] = accumulator
                        maxima[head] = new_maximum

                output_heads: list[BF16Vector] = []
                sink_exps: list[int] = []
                denominators: list[int] = []
                committed_maxima: list[int] = []
                for head in range(head_count):
                    maximum = maxima[head]
                    if maximum is None:  # pragma: no cover - prevalidated
                        raise RuntimeError("sparse-attention maximum was not initialized")
                    sink_exp = binary32_exp_general_rne(
                        _subtract(sinks[head], maximum)
                    )
                    denominator = binary32_add(sums[head], sink_exp)
                    _positive(denominator, "final sparse-attention denominator")

                    output_row: list[int] = []
                    for accumulator in accumulators[head]:
                        value = binary32_divide(accumulator, denominator)
                        converted = binary32_bits_to_bf16_rne(value)
                        saturation_count += int(converted.saturated)
                        output_row.append(converted.code)
                    output_heads.append(tuple(output_row))
                    sink_exps.append(sink_exp)
                    denominators.append(denominator)
                    committed_maxima.append(maximum)

                batch_outputs.append(tuple(output_heads))
                batch_maxima.append(tuple(committed_maxima))
                batch_sink_exps.append(tuple(sink_exps))
                batch_denominators.append(tuple(denominators))
            outputs.append(tuple(batch_outputs))
            all_maxima.append(tuple(batch_maxima))
            all_sink_exps.append(tuple(batch_sink_exps))
            all_denominators.append(tuple(batch_denominators))
    except (NumericReferenceError, TranscendentalReferenceError) as exc:
        raise SparseAttentionReferenceError(
            f"sparse-attention numeric poison: {exc}"
        ) from exc

    counters = SparseAttentionCounters(
        output_rows=output_rows,
        source_blocks=output_rows * block_count,
        query_bf16_values=output_rows * head_count * head_dim,
        query_bf16_read_bytes=output_rows * head_count * head_dim * 2,
        attention_sink_binary32_reads=output_rows * head_count,
        attention_sink_binary32_read_bytes=output_rows * head_count * 4,
        logical_index_slots=output_rows * topk,
        selected_index_int32_reads=output_rows * topk,
        selected_index_read_bytes=output_rows * topk * 4,
        explicit_padding_slots=explicit_padding,
        implicit_tail_padding_lanes=implicit_tail,
        block_compute_lanes=block_compute_lanes,
        valid_selected_rows=valid_selected,
        unique_selected_rows=unique_selected,
        duplicate_selected_rows=valid_selected - unique_selected,
        selected_kv_bf16_values=valid_selected * head_dim,
        selected_kv_read_bytes=valid_selected * head_dim * 2,
        qk_valid_product_accumulates=valid_selected * head_count * head_dim,
        qk_padding_product_lanes=padded_lanes * head_count * head_dim,
        score_scale_multiplies=block_compute_lanes * head_count,
        online_rescale_exp_evaluations=output_rows * block_count * head_count,
        score_exp_evaluations=block_compute_lanes * head_count,
        score_reduction_adds=(
            output_rows
            * block_count
            * head_count
            * (SPARSE_ATTENTION_BLOCK_SIZE - 1)
        ),
        online_denominator_multiplies=output_rows * block_count * head_count,
        online_denominator_adds=output_rows * block_count * head_count,
        probability_bf16_conversions=block_compute_lanes * head_count,
        output_rescale_multiplies=(
            output_rows * block_count * head_count * head_dim
        ),
        av_product_accumulates=block_compute_lanes * head_count * head_dim,
        sink_exp_evaluations=output_rows * head_count,
        sink_denominator_adds=output_rows * head_count,
        final_binary32_divides=output_rows * head_count * head_dim,
        output_bf16_conversions=output_rows * head_count * head_dim,
        output_bf16_write_bytes=output_rows * head_count * head_dim * 2,
    )
    return SparseAttentionResult(
        values=tuple(outputs),
        final_max_binary32_codes=tuple(all_maxima),
        sink_exp_binary32_codes=tuple(all_sink_exps),
        final_denominator_binary32_codes=tuple(all_denominators),
        output_saturated_element_count=saturation_count,
        counters=counters,
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "INT32_MAX",
    "KERNEL_SOURCE_SHA256",
    "MODEL_SOURCE_SHA256",
    "SPARSE_ATTENTION_BLOCK_SIZE",
    "SPARSE_ATTENTION_HEAD_DIM",
    "SPARSE_ATTENTION_HEADS",
    "SPARSE_ATTENTION_KV_BYTES_PER_SELECTED_ROW",
    "SPARSE_ATTENTION_NUMERIC_PROFILE",
    "SPARSE_ATTENTION_SCALE_BINARY32",
    "SPARSE_ATTENTION_SITE_COUNT",
    "SparseAttentionCounters",
    "SparseAttentionReferenceError",
    "SparseAttentionResult",
    "sparse_attention_bf16",
]
