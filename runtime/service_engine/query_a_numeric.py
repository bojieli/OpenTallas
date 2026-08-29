"""Artifact-neutral service arithmetic for the complete Query-A fragment.

This module composes the already independent service implementations of the
weighted 4,096-wide RMS normalization and the exhaustive 1,024-row dense FP8
projection.  It deliberately knows nothing about compiler manifests,
checkpoint readers, reference-model helpers, expected outputs, or filesystem
layout.  The executable service engine supplies read-only, hash-verified
resource accessors after it has locked an artifact tree.

The returned counters describe source-visible functional work.  They are not
cycles, transactions, latency, throughput, energy, area, density, routing, or
PPA evidence.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .fp8_numeric import FP8ServiceNumericError, execute_selected_rows
from .rms_numeric import RMSServiceNumericError, execute_weighted_rms_norm


HIDDEN_SIZE = 4096
QUERY_A_OUTPUT_FEATURES = 1024
DENSE_BLOCK_SIZE = 128
QUERY_A_BLOCK_COUNT = HIDDEN_SIZE // DENSE_BLOCK_SIZE
MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
EXHAUSTIVE_QUERY_A_ROWS = tuple(range(QUERY_A_OUTPUT_FEATURES))

BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class QueryAServiceNumericError(ValueError):
    """Raised when the complete Query-A numeric transaction must poison."""


@dataclass(frozen=True)
class QueryAServiceNumericResult:
    """All architectural outputs and independently checkable diagnostics."""

    normalized_codes: BF16Matrix
    query_a_codes: BF16Matrix
    mean_square_codes: tuple[int, ...]
    inverse_rms_codes: tuple[int, ...]
    rms_output_saturation_count: int
    activation_saturated_block_count: int
    query_output_saturated_element_count: int


def _materialize_attention_input(value: object) -> BF16Matrix:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise QueryAServiceNumericError("attention_input_codes must be a sequence")
    rows = tuple(value)
    if not MIN_TOKEN_COUNT <= len(rows) <= MAX_TOKEN_COUNT:
        raise QueryAServiceNumericError(
            "attention_input_codes must contain between "
            f"{MIN_TOKEN_COUNT} and {MAX_TOKEN_COUNT} token rows"
        )
    materialized: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(rows):
        if isinstance(raw_row, (str, bytes, bytearray)) or not isinstance(
            raw_row, Sequence
        ):
            raise QueryAServiceNumericError(
                f"attention_input_codes[{row_index}] must be a sequence"
            )
        row = tuple(raw_row)
        if len(row) != HIDDEN_SIZE:
            raise QueryAServiceNumericError(
                f"attention_input_codes[{row_index}] must contain exactly "
                f"{HIDDEN_SIZE} BF16 values"
            )
        # Exact encoding and finiteness validation remains independently owned
        # by the RMS service implementation.  Materialization here prevents a
        # caller from changing a mutable sequence between the two operators.
        materialized.append(row)  # type: ignore[arg-type]
    return tuple(materialized)


def query_a_functional_counters(token_count: int) -> dict[str, int]:
    """Return the exact shape-derived functional accounting contract."""

    if (
        isinstance(token_count, bool)
        or not isinstance(token_count, int)
        or not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT
    ):
        raise QueryAServiceNumericError(
            f"token_count must be an integer in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )

    rms_reduction_adds = HIDDEN_SIZE - 1
    fp8_block_reduction_adds = QUERY_A_OUTPUT_FEATURES * (QUERY_A_BLOCK_COUNT - 1)
    per_token = {
        "activation_blocks_quantized": QUERY_A_BLOCK_COUNT,
        "activation_values_quantized": HIDDEN_SIZE,
        "bf16_attention_input_values_read": HIDDEN_SIZE,
        "bf16_normalized_values_written": HIDDEN_SIZE,
        "bf16_query_a_values_written": QUERY_A_OUTPUT_FEATURES,
        "binary32_epsilon_adds": 1,
        "binary32_fp8_block_reduction_adds": fp8_block_reduction_adds,
        "binary32_fp8_product_accumulates": (QUERY_A_OUTPUT_FEATURES * HIDDEN_SIZE),
        "binary32_rms_divides": 1,
        "binary32_rms_normalization_multiplies": HIDDEN_SIZE,
        "binary32_rms_reduction_adds": rms_reduction_adds,
        "binary32_rms_square_multiplies": HIDDEN_SIZE,
        "binary32_rms_weight_multiplies": HIDDEN_SIZE,
        "binary32_rsqrt_evaluations": 1,
        "logical_attention_input_bytes_read": HIDDEN_SIZE * 2,
        "logical_normalized_bytes_written": HIDDEN_SIZE * 2,
        "logical_query_a_bytes_written": QUERY_A_OUTPUT_FEATURES * 2,
        "logical_query_parameter_bytes_read": (
            QUERY_A_OUTPUT_FEATURES * (HIDDEN_SIZE + QUERY_A_BLOCK_COUNT)
        ),
        "logical_rms_weight_bytes_read": HIDDEN_SIZE * 2,
        "matrix_block_dots": QUERY_A_OUTPUT_FEATURES * QUERY_A_BLOCK_COUNT,
    }
    counters = {key: value * token_count for key, value in per_token.items()}
    counters.update(
        {
            "complete_events": 1,
            "micro_ops_executed": 3,
            "semantic_operators_executed": 2,
        }
    )
    return dict(sorted(counters.items()))


def execute_complete_query_a(
    attention_input_codes: Sequence[Sequence[int]],
    norm_weight_codes: Sequence[int],
    *,
    weight_row: Callable[[int], bytes],
    scale_code: Callable[[int, int], int],
) -> QueryAServiceNumericResult:
    """Execute weighted RMS normalization followed by every Query-A row.

    ``weight_row`` and ``scale_code`` must be side-effect-free accessors over a
    verified, immutably held artifact tree.  Output-row selection is not a
    caller option: the production fragment always executes rows 0 through
    1,023 in order.
    """

    if not callable(weight_row) or not callable(scale_code):
        raise QueryAServiceNumericError(
            "weight_row and scale_code must be resource accessors"
        )
    inputs = _materialize_attention_input(attention_input_codes)
    try:
        normalized = execute_weighted_rms_norm(inputs, norm_weight_codes)
    except RMSServiceNumericError as exc:
        raise QueryAServiceNumericError(f"RMS_NORM numeric poison: {exc}") from exc

    try:
        query_a, activation_saturations, output_saturations = execute_selected_rows(
            normalized.output_codes,
            selected_rows=EXHAUSTIVE_QUERY_A_ROWS,
            input_features=HIDDEN_SIZE,
            weight_row=weight_row,
            scale_code=scale_code,
        )
    except FP8ServiceNumericError as exc:
        raise QueryAServiceNumericError(f"FP8_LINEAR numeric poison: {exc}") from exc

    if len(query_a) != len(inputs) or any(
        len(row) != QUERY_A_OUTPUT_FEATURES for row in query_a
    ):
        raise QueryAServiceNumericError(
            "FP8_LINEAR returned an out-of-contract Query-A shape"
        )
    return QueryAServiceNumericResult(
        normalized_codes=normalized.output_codes,
        query_a_codes=query_a,
        mean_square_codes=normalized.mean_square_codes,
        inverse_rms_codes=normalized.inverse_rms_codes,
        rms_output_saturation_count=normalized.output_saturation_count,
        activation_saturated_block_count=activation_saturations,
        query_output_saturated_element_count=output_saturations,
    )


__all__ = [
    "DENSE_BLOCK_SIZE",
    "EXHAUSTIVE_QUERY_A_ROWS",
    "HIDDEN_SIZE",
    "MAX_TOKEN_COUNT",
    "MIN_TOKEN_COUNT",
    "QUERY_A_BLOCK_COUNT",
    "QUERY_A_OUTPUT_FEATURES",
    "QueryAServiceNumericError",
    "QueryAServiceNumericResult",
    "execute_complete_query_a",
    "query_a_functional_counters",
]
