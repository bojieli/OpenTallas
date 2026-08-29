"""Reference-independent arithmetic for layer-0 attention preparation.

The implementation consumes raw architectural encodings and never imports the
compiler or ``runtime.reference``.  Dense FP8 projections use a vectorized
binary32 implementation whose block boundaries, increasing-K accumulation,
balanced block reduction, and BF16 conversion are identical to the scalar
service contract.  Vectorization changes host execution time only; it does not
define hardware lanes or cycles.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from .fp8_numeric import (
    FP8ServiceNumericError,
    _binary32_to_bf16,
    _encode_binary32,
    decode_e4m3fn_finite,
    decode_e8m0_finite,
    quantize_bf16_block,
)
from .head_rms_numeric import (
    HEAD_RMS_NORM_MAX_ROWS,
    HeadRMSServiceNumericError,
    execute_head_rms_norm,
)
from .rms_numeric import RMSServiceNumericError, execute_weighted_rms_norm


QUERY_A_WIDTH = 1_024
HIDDEN_WIDTH = 4_096
HEAD_COUNT = 64
HEAD_WIDTH = 512
QUERY_B_LOCAL_WIDTH = 8_192
WORLD_SIZE = 4
KV_WIDTH = 512
KV_QDQ_WIDTH = 448
ROPE_WIDTH = 64
DENSE_BLOCK = 128
QDQ_BLOCK = 64


class AttentionPrepareNumericError(ValueError):
    """Raised when the complete attention-preparation transaction poisons."""


@dataclass(frozen=True)
class AttentionPrepareNumericResult:
    query_rank_normalized_codes: tuple[int, ...]
    query_raw_codes: tuple[int, ...]
    query_prepared_codes: tuple[tuple[int, ...], ...]
    kv_raw_codes: tuple[int, ...]
    kv_normalized_codes: tuple[int, ...]
    kv_prepared_codes: tuple[int, ...]
    kv_qdq_value_codes: tuple[int, ...]
    kv_qdq_scale_codes: tuple[int, ...]
    query_rank_mean_code: int
    query_rank_inverse_code: int
    query_head_mean_codes: tuple[int, ...]
    query_head_inverse_codes: tuple[int, ...]
    kv_mean_code: int
    kv_inverse_code: int
    activation_saturated_block_count: int
    output_saturated_element_count: int
    normalization_saturated_element_count: int


def _finite_bf16_row(value: object, width: int, label: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AttentionPrepareNumericError(f"{label} must be a sequence")
    row = tuple(value)
    if len(row) != width:
        raise AttentionPrepareNumericError(
            f"{label} must contain exactly {width} BF16 values"
        )
    for index, code in enumerate(row):
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code < 1 << 16
            or code & 0x7F80 == 0x7F80
        ):
            raise AttentionPrepareNumericError(
                f"{label}[{index}] must be a finite 16-bit BF16 encoding"
            )
    return row  # type: ignore[return-value]


_E4M3_FLOAT64 = np.asarray(
    [
        np.nan if code in {0x7F, 0xFF} else float(decode_e4m3fn_finite(code))
        for code in range(256)
    ],
    dtype=np.float64,
)


def _binary32_add_vectors(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if left.dtype != np.float32 or right.dtype != np.float32 or left.shape != right.shape:
        raise AttentionPrepareNumericError("binary32 vector-add operands differ")
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        result = np.asarray(left.astype(np.float64) + right.astype(np.float64), dtype=np.float32)
    if not np.isfinite(result).all():
        raise AttentionPrepareNumericError("finite binary32 vector reduction overflowed")
    return result


def _bf16_codes_from_binary32(values: np.ndarray) -> tuple[tuple[int, ...], int]:
    if values.dtype != np.float32 or values.ndim != 1 or not np.isfinite(values).all():
        raise AttentionPrepareNumericError("dense projection result is not finite binary32")
    bits = values.view(np.uint32)
    upper = (bits >> np.uint32(16)).astype(np.uint32)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    upper = upper + increment.astype(np.uint32)
    saturated = (upper & np.uint32(0x7F80)) == np.uint32(0x7F80)
    upper = np.where(
        saturated,
        (upper & np.uint32(0x8000)) | np.uint32(0x7F7F),
        upper,
    )
    upper = np.where((upper & np.uint32(0x7FFF)) == 0, np.uint32(0), upper)
    return tuple(int(value) for value in upper), int(np.count_nonzero(saturated))


def execute_full_fp8_linear_vectorized(
    input_codes: Sequence[int],
    *,
    weight_payload: bytes,
    scale_payload: bytes,
    output_features: int,
    input_features: int,
) -> tuple[tuple[int, ...], int, int]:
    """Execute every dense output row with exact target rounding boundaries."""

    row = _finite_bf16_row(input_codes, input_features, "input_codes")
    if (
        isinstance(output_features, bool)
        or not isinstance(output_features, int)
        or output_features < 1
        or output_features % DENSE_BLOCK
        or input_features % DENSE_BLOCK
    ):
        raise AttentionPrepareNumericError("dense FP8 matrix dimensions are illegal")
    if type(weight_payload) is not bytes or len(weight_payload) != output_features * input_features:
        raise AttentionPrepareNumericError("dense FP8 weight payload extent differs")
    block_count = input_features // DENSE_BLOCK
    scale_rows = output_features // DENSE_BLOCK
    if type(scale_payload) is not bytes or len(scale_payload) != scale_rows * block_count:
        raise AttentionPrepareNumericError("dense FP8 scale payload extent differs")

    weights = np.frombuffer(weight_payload, dtype=np.uint8).reshape(
        output_features, input_features
    )
    scales = np.frombuffer(scale_payload, dtype=np.uint8).reshape(
        scale_rows, block_count
    )
    if np.any((weights == 0x7F) | (weights == 0xFF)):
        raise AttentionPrepareNumericError("dense FP8 weight payload contains E4M3FN NaN")
    if np.any(scales == 0xFF):
        raise AttentionPrepareNumericError("dense FP8 scale payload contains reserved E8M0")

    partials: list[np.ndarray] = []
    activation_saturations = 0
    for block_index in range(block_count):
        start = block_index * DENSE_BLOCK
        try:
            activation = quantize_bf16_block(row[start : start + DENSE_BLOCK])
        except FP8ServiceNumericError as exc:
            raise AttentionPrepareNumericError(
                f"activation block {block_index} failed: {exc}"
            ) from exc
        activation_saturations += int(activation.saturated)
        activation_scale = float(decode_e8m0_finite(activation.scale_code))
        activation_values = _E4M3_FLOAT64[
            np.asarray(activation.value_codes, dtype=np.uint8)
        ] * activation_scale
        scale_codes = np.repeat(scales[:, block_index], DENSE_BLOCK)
        scale_values = np.ldexp(
            np.ones(output_features, dtype=np.float64),
            scale_codes.astype(np.int16) - 127,
        )
        accumulator = np.zeros(output_features, dtype=np.float32)
        for offset in range(DENSE_BLOCK):
            weight_values = _E4M3_FLOAT64[weights[:, start + offset]]
            product = weight_values * scale_values * activation_values[offset]
            with np.errstate(over="ignore", invalid="ignore", under="ignore"):
                accumulator = np.asarray(
                    accumulator.astype(np.float64) + product,
                    dtype=np.float32,
                )
            if not np.isfinite(accumulator).all():
                raise AttentionPrepareNumericError(
                    f"dense FP8 block {block_index} accumulation overflowed"
                )
        partials.append(accumulator)

    level = partials
    while len(level) > 1:
        if len(level) & 1:
            level = [*level, np.zeros(output_features, dtype=np.float32)]
        level = [
            _binary32_add_vectors(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        ]
    output, output_saturations = _bf16_codes_from_binary32(level[0])
    return output, activation_saturations, output_saturations


def _head_normalize(
    query_raw: tuple[int, ...],
) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...], tuple[int, ...], int]:
    heads = tuple(
        query_raw[index * HEAD_WIDTH : (index + 1) * HEAD_WIDTH]
        for index in range(HEAD_COUNT)
    )
    outputs: list[tuple[int, ...]] = []
    means: list[int] = []
    inverses: list[int] = []
    saturation_count = 0
    for start in range(0, HEAD_COUNT, HEAD_RMS_NORM_MAX_ROWS):
        try:
            result = execute_head_rms_norm(
                heads[start : start + HEAD_RMS_NORM_MAX_ROWS]
            )
        except HeadRMSServiceNumericError as exc:
            raise AttentionPrepareNumericError(
                f"query head normalization failed at head {start}: {exc}"
            ) from exc
        outputs.extend(result.output_codes)
        means.extend(result.mean_square_codes)
        inverses.extend(result.inverse_rms_codes)
        saturation_count += result.output_saturation_count
    return tuple(outputs), tuple(means), tuple(inverses), saturation_count


def _position_zero_rope(
    rows: tuple[tuple[int, ...], ...], *, label: str
) -> tuple[tuple[int, ...], ...]:
    # At position zero every qualified frequency has cos=1 and sin=0.  The
    # target result is therefore a bit-preserving BF16 identity, including the
    # 448 non-RoPE values.  Restricting this first vertical slice to start_pos=0
    # removes no state transition from the following KV write.
    return tuple(_finite_bf16_row(row, HEAD_WIDTH, f"{label}[{index}]") for index, row in enumerate(rows))


def _fp8_qdq_kv(row: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    output: list[int] = []
    value_codes: list[int] = []
    scale_codes: list[int] = []
    for block_index in range(KV_QDQ_WIDTH // QDQ_BLOCK):
        start = block_index * QDQ_BLOCK
        # The dense helper has a fixed 128-value contract.  Duplicate each
        # 64-value KV block only for scale/code generation, then retain its
        # first half; max and encoding are identical because both halves match.
        block = row[start : start + QDQ_BLOCK]
        try:
            quantized = quantize_bf16_block(block + block)
        except FP8ServiceNumericError as exc:
            raise AttentionPrepareNumericError(
                f"KV FP8_QDQ block {block_index} failed: {exc}"
            ) from exc
        codes = quantized.value_codes[:QDQ_BLOCK]
        scale = decode_e8m0_finite(quantized.scale_code)
        scale_codes.append(quantized.scale_code)
        value_codes.extend(codes)
        for code in codes:
            exact = decode_e4m3fn_finite(code) * scale
            binary32 = _encode_binary32(exact)
            converted = _binary32_to_bf16(binary32)
            output.append(converted.code)
    output.extend(row[KV_QDQ_WIDTH:])
    return tuple(output), tuple(value_codes), tuple(scale_codes)


def attention_prepare_functional_counters() -> dict[str, int]:
    query_b_outputs = WORLD_SIZE * QUERY_B_LOCAL_WIDTH
    return dict(
        sorted(
            {
                "activation_blocks_quantized": WORLD_SIZE * (QUERY_A_WIDTH // DENSE_BLOCK)
                + HIDDEN_WIDTH // DENSE_BLOCK,
                "bf16_attention_normalized_values_read": HIDDEN_WIDTH,
                "bf16_kv_values_written": KV_WIDTH,
                "bf16_query_a_values_read": QUERY_A_WIDTH,
                "bf16_query_values_written": query_b_outputs,
                "binary32_fp8_product_accumulates": query_b_outputs * QUERY_A_WIDTH
                + KV_WIDTH * HIDDEN_WIDTH,
                "head_rms_rows": HEAD_COUNT,
                "kv_fp8_qdq_values": KV_QDQ_WIDTH,
                "logical_immutable_parameter_bytes_read": (
                    QUERY_A_WIDTH * 2
                    + query_b_outputs * QUERY_A_WIDTH
                    + (query_b_outputs // DENSE_BLOCK) * (QUERY_A_WIDTH // DENSE_BLOCK)
                    + KV_WIDTH * HIDDEN_WIDTH
                    + (KV_WIDTH // DENSE_BLOCK) * (HIDDEN_WIDTH // DENSE_BLOCK)
                    + KV_WIDTH * 2
                ),
                "micro_ops_executed": 9,
                "position_zero_rope_values": HEAD_COUNT * ROPE_WIDTH + ROPE_WIDTH,
                "semantic_operators_executed": 8,
            }.items()
        )
    )


def execute_attention_prepare(
    query_a_codes: Sequence[int],
    attention_normalized_codes: Sequence[int],
    resources: Mapping[str, bytes],
) -> AttentionPrepareNumericResult:
    expected = {
        "query_norm_weight",
        "query_b_weight_rank_0",
        "query_b_scale_rank_0",
        "query_b_weight_rank_1",
        "query_b_scale_rank_1",
        "query_b_weight_rank_2",
        "query_b_scale_rank_2",
        "query_b_weight_rank_3",
        "query_b_scale_rank_3",
        "kv_weight",
        "kv_scale",
        "kv_norm_weight",
    }
    if type(resources) is not dict or set(resources) != expected or any(
        type(value) is not bytes for value in resources.values()
    ):
        raise AttentionPrepareNumericError("attention-preparation resource closure differs")
    query_a = _finite_bf16_row(query_a_codes, QUERY_A_WIDTH, "query_a_codes")
    attention_normalized = _finite_bf16_row(
        attention_normalized_codes,
        HIDDEN_WIDTH,
        "attention_normalized_codes",
    )

    query_norm_weight = tuple(struct_value for struct_value in np.frombuffer(resources["query_norm_weight"], dtype="<u2"))
    kv_norm_weight = tuple(struct_value for struct_value in np.frombuffer(resources["kv_norm_weight"], dtype="<u2"))
    try:
        query_norm = execute_weighted_rms_norm((query_a,), query_norm_weight)
    except RMSServiceNumericError as exc:
        raise AttentionPrepareNumericError(f"Query-A RMS_NORM failed: {exc}") from exc

    query_shards: list[int] = []
    activation_saturations = 0
    output_saturations = 0
    for rank in range(WORLD_SIZE):
        output, activation_saturated, output_saturated = execute_full_fp8_linear_vectorized(
            query_norm.output_codes[0],
            weight_payload=resources[f"query_b_weight_rank_{rank}"],
            scale_payload=resources[f"query_b_scale_rank_{rank}"],
            output_features=QUERY_B_LOCAL_WIDTH,
            input_features=QUERY_A_WIDTH,
        )
        query_shards.extend(output)
        activation_saturations += activation_saturated
        output_saturations += output_saturated
    query_raw = tuple(query_shards)
    query_heads, head_means, head_inverses, head_saturations = _head_normalize(query_raw)
    query_prepared = _position_zero_rope(query_heads, label="query_heads")

    kv_raw, kv_activation_saturated, kv_output_saturated = execute_full_fp8_linear_vectorized(
        attention_normalized,
        weight_payload=resources["kv_weight"],
        scale_payload=resources["kv_scale"],
        output_features=KV_WIDTH,
        input_features=HIDDEN_WIDTH,
    )
    try:
        kv_norm = execute_weighted_rms_norm((kv_raw,), kv_norm_weight)
    except RMSServiceNumericError as exc:
        raise AttentionPrepareNumericError(f"KV RMS_NORM failed: {exc}") from exc
    kv_rotated = _position_zero_rope((kv_norm.output_codes[0],), label="kv")[0]
    kv_prepared, qdq_values, qdq_scales = _fp8_qdq_kv(kv_rotated)

    return AttentionPrepareNumericResult(
        query_rank_normalized_codes=query_norm.output_codes[0],
        query_raw_codes=query_raw,
        query_prepared_codes=query_prepared,
        kv_raw_codes=kv_raw,
        kv_normalized_codes=kv_norm.output_codes[0],
        kv_prepared_codes=kv_prepared,
        kv_qdq_value_codes=qdq_values,
        kv_qdq_scale_codes=qdq_scales,
        query_rank_mean_code=query_norm.mean_square_codes[0],
        query_rank_inverse_code=query_norm.inverse_rms_codes[0],
        query_head_mean_codes=head_means,
        query_head_inverse_codes=head_inverses,
        kv_mean_code=kv_norm.mean_square_codes[0],
        kv_inverse_code=kv_norm.inverse_rms_codes[0],
        activation_saturated_block_count=activation_saturations + kv_activation_saturated,
        output_saturated_element_count=output_saturations + kv_output_saturated,
        normalization_saturated_element_count=(
            query_norm.output_saturation_count
            + head_saturations
            + kv_norm.output_saturation_count
        ),
    )


__all__ = [
    "AttentionPrepareNumericError",
    "AttentionPrepareNumericResult",
    "attention_prepare_functional_counters",
    "execute_attention_prepare",
    "execute_full_fp8_linear_vectorized",
]
