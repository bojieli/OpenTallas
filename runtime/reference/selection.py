"""Deterministic official-precision selection for DeepSeek V4 top-k paths.

The pinned source calls ``torch.topk`` for sparse-index and expert selection,
but its declared ``torch>=2.10.0`` dependency does not freeze a backend and the
official PyTorch 2.10 documentation says tied indices are not stable. OpenTallas
therefore makes the otherwise missing target rule explicit: larger values win
and exact ties select the smaller logical index first.

Router inputs are raw IEEE binary32 encodings. Learned indexer inputs are raw
BF16 encodings: the pinned BF16 Q/K einsum, BF16 head weighting, and BF16 sum
feed ``torch.topk`` without a float conversion. Comparisons decode to exact
rational values, so the reference does not inherit host floating-point ordering.
NaNs fail closed. The shared primitives permit infinities for masking tests; the
model operators require finite source scores and introduce BF16 negative infinity
only as the official causal-mask sentinel.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    DecodedValue,
    NumericReferenceError,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
REQUIREMENTS_SOURCE_SHA256 = (
    "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
)
TIE_POLICY = "score_descending_then_logical_index_ascending"
NEGATIVE_INFINITY_BINARY32 = 0xFF800000
NEGATIVE_INFINITY_BF16 = 0xFF80
INT64_MAX = (1 << 63) - 1

BF16Row: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Row, ...]
BF16Tensor: TypeAlias = tuple[BF16Matrix, ...]
Binary32Row: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Row, ...]
IndexMatrix: TypeAlias = tuple[tuple[int, ...], ...]
IndexTensor: TypeAlias = tuple[IndexMatrix, ...]


class SelectionReferenceError(ValueError):
    """Raised when top-k inputs violate the deterministic target contract."""


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SelectionReferenceError(f"{label} must be an integer >= {minimum}")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SelectionReferenceError(f"{label} must be a sequence")
    return value


def _binary32_code(value: object, label: str, *, finite: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SelectionReferenceError(f"{label} must be a binary32 encoding")
    try:
        decoded = decode_binary32(value)
    except ValueError as exc:
        raise SelectionReferenceError(f"{label} must be a binary32 encoding") from exc
    if decoded.nan:
        raise SelectionReferenceError(f"{label} is binary32 NaN")
    if finite and not decoded.finite:
        raise SelectionReferenceError(f"{label} must be finite binary32")
    return value


def _bf16_code(value: object, label: str, *, finite: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SelectionReferenceError(f"{label} must be a BF16 encoding")
    try:
        decoded = decode_bf16(value)
    except ValueError as exc:
        raise SelectionReferenceError(f"{label} must be a BF16 encoding") from exc
    if decoded.nan:
        raise SelectionReferenceError(f"{label} is BF16 NaN")
    if finite and not decoded.finite:
        raise SelectionReferenceError(f"{label} must be finite BF16")
    return value


def _score_key(decoded: DecodedValue) -> tuple[int, Fraction]:
    if decoded.nan:
        raise SelectionReferenceError("top-k score is NaN")
    if decoded.infinity:
        return (0 if decoded.negative else 2, Fraction(0))
    assert decoded.value is not None
    return (1, decoded.value)


def stable_topk_binary32(score_codes: Sequence[int], k: int) -> tuple[int, ...]:
    """Return deterministic top-k logical indices for one binary32 score row."""

    raw_scores = _sequence(score_codes, "score_codes")
    scores = tuple(
        _binary32_code(score, f"score_codes[{index}]", finite=False)
        for index, score in enumerate(raw_scores)
    )
    k = _integer(k, "k")
    if k > len(scores):
        raise SelectionReferenceError(f"k={k} exceeds score count {len(scores)}")
    # ``reverse=True`` makes higher rank/value win. ``-index`` makes a smaller
    # logical index the larger final key and therefore resolves exact ties.
    ordered = sorted(
        range(len(scores)),
        key=lambda index: (*_score_key(decode_binary32(scores[index])), -index),
        reverse=True,
    )
    return tuple(ordered[:k])


def stable_topk_bf16(score_codes: Sequence[int], k: int) -> tuple[int, ...]:
    """Return deterministic top-k logical indices for one BF16 score row."""

    raw_scores = _sequence(score_codes, "score_codes")
    scores = tuple(
        _bf16_code(score, f"score_codes[{index}]", finite=False)
        for index, score in enumerate(raw_scores)
    )
    k = _integer(k, "k")
    if k > len(scores):
        raise SelectionReferenceError(f"k={k} exceeds score count {len(scores)}")
    ordered = sorted(
        range(len(scores)),
        key=lambda index: (*_score_key(decode_bf16(scores[index])), -index),
        reverse=True,
    )
    return tuple(ordered[:k])


def _finite_row(value: object, label: str) -> Binary32Row:
    row = _sequence(value, label)
    return tuple(
        _binary32_code(code, f"{label}[{index}]", finite=True)
        for index, code in enumerate(row)
    )


def biased_topk_route_indices(
    original_score_codes: Sequence[Sequence[int]],
    selection_bias_codes: Sequence[int],
    *,
    top_k: int,
) -> IndexMatrix:
    """Apply FP32 selection-only bias and deterministic expert top-k.

    This reproduces the ``Gate.forward`` selection branch. It returns indices
    only; routing weights continue to gather the unbiased scores in their
    separate graph operator.
    """

    raw_rows = _sequence(original_score_codes, "original_score_codes")
    if not raw_rows:
        raise SelectionReferenceError(
            "original_score_codes must contain at least one token row"
        )
    bias = _finite_row(selection_bias_codes, "selection_bias_codes")
    if not bias:
        raise SelectionReferenceError(
            "selection_bias_codes must contain at least one expert"
        )
    top_k = _integer(top_k, "top_k", minimum=1)
    if top_k > len(bias):
        raise SelectionReferenceError(
            f"top_k={top_k} exceeds expert count {len(bias)}"
        )

    bias_values = tuple(decode_binary32(code).value for code in bias)
    if any(value is None for value in bias_values):  # pragma: no cover
        raise RuntimeError("finite bias decode invariant failed")
    result: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _finite_row(raw_row, f"original_score_codes[{row_index}]")
        if len(row) != len(bias):
            raise SelectionReferenceError(
                "router score rows must match the selection-bias expert count"
            )
        biased: list[int] = []
        for expert_index, (score_code, bias_value) in enumerate(
            zip(row, bias_values, strict=True)
        ):
            score_value = decode_binary32(score_code).value
            assert score_value is not None and bias_value is not None
            try:
                biased.append(encode_binary32_rne(score_value + bias_value))
            except NumericReferenceError as exc:
                raise SelectionReferenceError(
                    f"biased router score overflows at token {row_index}, "
                    f"expert {expert_index}"
                ) from exc
        result.append(stable_topk_binary32(biased, top_k))
    return tuple(result)


def _finite_bf16_row(value: object, label: str) -> BF16Row:
    row = _sequence(value, label)
    return tuple(
        _bf16_code(code, f"{label}[{index}]", finite=True)
        for index, code in enumerate(row)
    )


def _finite_score_tensor(value: object) -> BF16Tensor:
    raw_batches = _sequence(value, "index_score_bf16_codes")
    if not raw_batches:
        raise SelectionReferenceError(
            "index_score_bf16_codes must contain at least one batch"
        )
    result: list[BF16Matrix] = []
    sequence_length: int | None = None
    candidate_count: int | None = None
    for batch_index, raw_matrix in enumerate(raw_batches):
        matrix = _sequence(raw_matrix, f"index_score_bf16_codes[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(matrix)
            if sequence_length == 0:
                raise SelectionReferenceError(
                    "index_score_bf16_codes must contain at least one query"
                )
        elif len(matrix) != sequence_length:
            raise SelectionReferenceError(
                "index_score_bf16_codes must be a rectangular rank-3 tensor"
            )
        rows: list[BF16Row] = []
        for query_index, raw_row in enumerate(matrix):
            row = _finite_bf16_row(
                raw_row,
                f"index_score_bf16_codes[{batch_index}][{query_index}]",
            )
            if candidate_count is None:
                candidate_count = len(row)
            elif len(row) != candidate_count:
                raise SelectionReferenceError(
                    "index_score_bf16_codes must be a rectangular rank-3 tensor"
                )
            rows.append(row)
        result.append(tuple(rows))
    return tuple(result)


def index_topk_indices(
    index_score_bf16_codes: Sequence[Sequence[Sequence[int]]],
    *,
    top_k: int,
    compression_ratio: int,
    start_position: int,
    offset: int,
) -> IndexTensor:
    """Apply official causal compressed-position mask, top-k, and offset.

    Prefill (``start_position == 0``) exposes only compression groups complete
    at each query and maps selected masked slots to ``-1``. Decode exposes every
    cached group. Equal finite scores follow :data:`TIE_POLICY`.
    """

    scores = _finite_score_tensor(index_score_bf16_codes)
    top_k = _integer(top_k, "top_k", minimum=1)
    compression_ratio = _integer(
        compression_ratio, "compression_ratio", minimum=1
    )
    start_position = _integer(start_position, "start_position")
    offset = _integer(offset, "offset")
    sequence_length = len(scores[0])
    candidate_count = len(scores[0][0])
    expected_candidates = (start_position + sequence_length) // compression_ratio
    if candidate_count != expected_candidates:
        raise SelectionReferenceError(
            f"index score candidate count is {candidate_count}, expected "
            f"{expected_candidates} from start/sequence/ratio"
        )
    selected_count = min(top_k, candidate_count)
    if selected_count and offset + candidate_count - 1 > INT64_MAX:
        raise SelectionReferenceError("offset compressed index exceeds signed int64")

    output_batches: list[IndexMatrix] = []
    for matrix in scores:
        output_rows: list[tuple[int, ...]] = []
        for query_index, row in enumerate(matrix):
            valid_count = (
                (query_index + 1) // compression_ratio
                if start_position == 0
                else candidate_count
            )
            masked = row[:valid_count] + (NEGATIVE_INFINITY_BF16,) * (
                candidate_count - valid_count
            )
            selected = stable_topk_bf16(masked, selected_count)
            output_rows.append(
                tuple(
                    selected_index + offset
                    if selected_index < valid_count
                    else -1
                    for selected_index in selected
                )
            )
        output_batches.append(tuple(output_rows))
    return tuple(output_batches)


__all__ = [
    "INT64_MAX",
    "MODEL_SOURCE_SHA256",
    "NEGATIVE_INFINITY_BF16",
    "NEGATIVE_INFINITY_BINARY32",
    "REQUIREMENTS_SOURCE_SHA256",
    "TIE_POLICY",
    "BF16Matrix",
    "BF16Row",
    "BF16Tensor",
    "Binary32Matrix",
    "Binary32Row",
    "IndexMatrix",
    "IndexTensor",
    "SelectionReferenceError",
    "biased_topk_route_indices",
    "index_topk_indices",
    "shared_index_view",
    "stable_topk_bf16",
    "stable_topk_binary32",
]


# ---------------------------------------------------------------------------
# SHARED_INDEX_REUSE, a Reindex layer's selection reused by the layers after it.
# Numeric contract `selection_shared_index_view_v1`.
#
# DeepSeek-V4.1-Flash scores the index on eight layers only --
# `index_source_layer_ids` [2, 8, 14, 20, 24, 28, 32, 36] of
# SRC-DSV41-FLASH-CONFIG.  Every other layer attends with the selection the most
# recent of those published; the exported kernel says so in its own attributes,
# `published_by_layer` and `selection_lifetime: until_the_next_index_source`.
#
# The read is a `STATE_READ`, so its contract is identity over a lifetime rather
# than arithmetic on values: the indices a reusing layer attends with must be
# bit-for-bit the ones its publisher selected, and the publisher must still be
# the current one.  Both are preconditions a plain copy cannot check, and both
# are real failure modes -- a layer that reused a stale selection would attend to
# a set of compressed rows that a later `INDEX_TOPK` has already replaced, and
# nothing downstream could tell, because a wrong selection is still a
# well-formed one.
#
# NOT ESTABLISHED: which indices the publisher chose (that is
# `index_topk_indices` above), the window/compressed join that follows the read
# (whose contract `selection_shared_index_view_window_then_compressed_v1` is
# attribute-for-attribute the join `index_topk_indices` already publishes), and
# anything about the attention that consumes the joined indices.
# ---------------------------------------------------------------------------


def shared_index_view(
    published_selection: IndexTensor,
    *,
    published_by_layer: int,
    reading_layer: int,
    index_source_layers: Sequence[int],
    padding_index: int = -1,
) -> IndexTensor:
    """Read a Reindex layer's published selection -- ``selection_shared_index_view_v1``.

    Returns the published tensor itself, unchanged, so that a caller comparing
    the view with the publication compares identity rather than a
    re-derivation.  What this function contributes is the set of reads it
    REFUSES:

    * a reading layer that is itself an index source.  Such a layer selects its
      own indices; if it read a view instead, the selection the hardware
      computed for it would be discarded silently.
    * a publisher that is not an index source at all.
    * a publisher that is not the *most recent* index source at or before the
      reading layer.  This is ``selection_lifetime:
      until_the_next_index_source`` stated as a rule: layer 3 may read layer 2's
      selection, and once layer 8 has published, layer 9 may not.
    * a reading layer at or before its publisher.
    * a ragged selection, a non-integer index, or a negative index that is not
      the declared ``padding_index``.  ``-1`` is the exported padding index; any
      other negative value is a fault, not a slot that selected nothing.
    """

    def _layer(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SelectionReferenceError(f"{label} must be a non-negative integer")
        return int(value)

    published_by_layer = _layer(published_by_layer, "published_by_layer")
    reading_layer = _layer(reading_layer, "reading_layer")
    sources = sorted(
        {
            _layer(layer, f"index_source_layers[{position}]")
            for position, layer in enumerate(_sequence(
                index_source_layers, "index_source_layers"
            ))
        }
    )
    if not sources:
        raise SelectionReferenceError(
            "index_source_layers must name at least one index source"
        )
    if published_by_layer not in sources:
        raise SelectionReferenceError(
            f"layer {published_by_layer} is not an index source, so it publishes "
            "no selection to view"
        )
    if reading_layer in sources:
        raise SelectionReferenceError(
            f"layer {reading_layer} is an index source and selects its own "
            "indices; it must not read a shared view"
        )
    if reading_layer <= published_by_layer:
        raise SelectionReferenceError(
            f"layer {reading_layer} reads a selection published by layer "
            f"{published_by_layer}, which is not ahead of it"
        )
    current = max(layer for layer in sources if layer < reading_layer)
    if current != published_by_layer:
        raise SelectionReferenceError(
            f"layer {reading_layer} reads layer {published_by_layer}'s selection, "
            f"but layer {current} has published since: the selection lifetime "
            "ends at the next index source"
        )

    batches = _sequence(published_selection, "published_selection")
    if not batches:
        raise SelectionReferenceError("published_selection must contain a batch")
    width: int | None = None
    for batch_index, raw_matrix in enumerate(batches):
        rows = _sequence(raw_matrix, f"published_selection[{batch_index}]")
        if not rows:
            raise SelectionReferenceError(
                f"published_selection[{batch_index}] must contain a row"
            )
        for row_index, raw_row in enumerate(rows):
            row = _sequence(
                raw_row, f"published_selection[{batch_index}][{row_index}]"
            )
            if width is None:
                width = len(row)
                if width == 0:
                    raise SelectionReferenceError(
                        "published_selection rows must not be empty"
                    )
            elif len(row) != width:
                raise SelectionReferenceError(
                    "published_selection must be a rectangular rank-3 tensor"
                )
            for slot, value in enumerate(row):
                label = (
                    f"published_selection[{batch_index}][{row_index}][{slot}]"
                )
                if isinstance(value, bool) or not isinstance(value, int):
                    raise SelectionReferenceError(f"{label} must be an integer")
                if value < 0 and value != padding_index:
                    raise SelectionReferenceError(
                        f"{label} is {value}, which is neither an index nor the "
                        f"declared padding index {padding_index}"
                    )
    return published_selection
