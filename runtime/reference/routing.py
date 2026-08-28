"""Deterministic official-precision routed-weight normalization.

The pinned DeepSeek V4 gate gathers original unbiased FP32 scores at selected
expert indices, sums the selected slot axis, divides each slot by that sum, and
then applies the configured route scale. PyTorch does not freeze one reduction
tree across backends, so OpenTallas uses the existing NUM-6.1 canonical balanced
tree while preserving source slot order. Every add, divide, and multiply rounds
once to IEEE binary32 under round-to-nearest-ties-to-even.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_balanced_sum,
    binary32_divide,
    binary32_multiply,
    decode_binary32,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)

Binary32Row: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Row, ...]
IndexRow: TypeAlias = tuple[int, ...]
IndexMatrix: TypeAlias = tuple[IndexRow, ...]


class RoutingReferenceError(ValueError):
    """Raised when routed-weight inputs violate the target contract."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RoutingReferenceError(f"{label} must be a sequence")
    return value


def _nonnegative_binary32(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RoutingReferenceError(f"{label} must be a binary32 encoding")
    try:
        decoded = decode_binary32(value)
    except ValueError as exc:
        raise RoutingReferenceError(f"{label} must be a binary32 encoding") from exc
    if not decoded.finite or decoded.value is None:
        raise RoutingReferenceError(f"{label} must be finite binary32")
    if decoded.value < 0:
        raise RoutingReferenceError(f"{label} must be nonnegative")
    return value


def _score_matrix(value: object) -> Binary32Matrix:
    raw_rows = _sequence(value, "original_score_codes")
    if not raw_rows:
        raise RoutingReferenceError(
            "original_score_codes must contain at least one token row"
        )
    result: list[Binary32Row] = []
    expert_count: int | None = None
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"original_score_codes[{row_index}]")
        if expert_count is None:
            expert_count = len(row)
            if expert_count == 0:
                raise RoutingReferenceError(
                    "original_score_codes must contain at least one expert"
                )
        elif len(row) != expert_count:
            raise RoutingReferenceError(
                "original_score_codes must be a rectangular rank-2 matrix"
            )
        result.append(
            tuple(
                _nonnegative_binary32(
                    code, f"original_score_codes[{row_index}][{expert_index}]"
                )
                for expert_index, code in enumerate(row)
            )
        )
    return tuple(result)


def _index_matrix(
    value: object, *, token_count: int, expert_count: int
) -> IndexMatrix:
    raw_rows = _sequence(value, "expert_indices")
    if len(raw_rows) != token_count:
        raise RoutingReferenceError(
            "expert_indices token count must match original_score_codes"
        )
    result: list[IndexRow] = []
    selected_count: int | None = None
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"expert_indices[{row_index}]")
        if selected_count is None:
            selected_count = len(row)
            if selected_count == 0:
                raise RoutingReferenceError(
                    "expert_indices must select at least one expert"
                )
        elif len(row) != selected_count:
            raise RoutingReferenceError(
                "expert_indices must be a rectangular rank-2 matrix"
            )
        output_row: list[int] = []
        for slot, expert_index in enumerate(row):
            if (
                isinstance(expert_index, bool)
                or not isinstance(expert_index, int)
                or not 0 <= expert_index < expert_count
            ):
                raise RoutingReferenceError(
                    f"expert_indices[{row_index}][{slot}] must be in "
                    f"[0, {expert_count})"
                )
            output_row.append(expert_index)
        result.append(tuple(output_row))
    return tuple(result)


def normalize_routed_weight_codes(
    original_score_codes: Sequence[Sequence[int]],
    expert_indices: Sequence[Sequence[int]],
    *,
    route_scale_code: int,
) -> Binary32Matrix:
    """Gather unbiased scores, normalize by selected-slot sum, and scale.

    Duplicate expert IDs intentionally remain duplicate logical slots here,
    matching ``Gate.forward``. The later dispatch/reduction path is responsible
    for any execution coalescing without changing their combined contribution.
    """

    scores = _score_matrix(original_score_codes)
    indices = _index_matrix(
        expert_indices,
        token_count=len(scores),
        expert_count=len(scores[0]),
    )
    route_scale_code = _nonnegative_binary32(
        route_scale_code, "route_scale_code"
    )
    scale = decode_binary32(route_scale_code).value
    assert scale is not None
    if scale == 0:
        raise RoutingReferenceError("route_scale_code must be greater than zero")

    output: list[Binary32Row] = []
    for row_index, (score_row, index_row) in enumerate(
        zip(scores, indices, strict=True)
    ):
        selected = tuple(score_row[index] for index in index_row)
        try:
            denominator = binary32_balanced_sum(selected)
            denominator_value = decode_binary32(denominator).value
            assert denominator_value is not None
            if denominator_value == 0:
                raise RoutingReferenceError(
                    f"selected score sum is zero for token row {row_index}"
                )
            output.append(
                tuple(
                    binary32_multiply(
                        binary32_divide(score_code, denominator),
                        route_scale_code,
                    )
                    for score_code in selected
                )
            )
        except NumericReferenceError as exc:
            raise RoutingReferenceError(
                f"routed-weight arithmetic failed for token row {row_index}: {exc}"
            ) from exc
    return tuple(output)


__all__ = [
    "MODEL_SOURCE_SHA256",
    "Binary32Matrix",
    "Binary32Row",
    "IndexMatrix",
    "IndexRow",
    "RoutingReferenceError",
    "normalize_routed_weight_codes",
]
