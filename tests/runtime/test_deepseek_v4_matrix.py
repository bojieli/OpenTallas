from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    DENSE_REDUCTION_BLOCK,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
    fp8_fp8_block_dot,
    quantize_bf16_activation_block,
)
from runtime.reference.matrix import (
    DENSE_OUTPUT_SCALE_BLOCK,
    MODEL_SOURCE_SHA256,
    MatrixReferenceError,
    dense_fp8_linear_bf16,
)


def _bf16(value: Fraction | int) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _independent_row(
    inputs: tuple[int, ...],
    weights: tuple[int, ...],
    scales: tuple[int, ...],
) -> int:
    partials = []
    for block_index, scale in enumerate(scales):
        start = block_index * DENSE_REDUCTION_BLOCK
        activation = quantize_bf16_activation_block(
            inputs[start : start + DENSE_REDUCTION_BLOCK]
        )
        partials.append(
            fp8_fp8_block_dot(
                weights[start : start + DENSE_REDUCTION_BLOCK],
                scale,
                activation.value_codes,
                activation.scale_code,
            )
        )
    return binary32_bits_to_bf16_rne(binary32_balanced_sum(partials)).code


def test_dense_fp8_matrix_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert DENSE_OUTPUT_SCALE_BLOCK == DENSE_REDUCTION_BLOCK == 128


def test_dense_fp8_linear_composes_blocks_tree_and_bf16_boundary_exactly() -> None:
    inputs = (
        tuple(
            _bf16(Fraction((index % 17) - 8, 8))
            for index in range(256)
        ),
        tuple(
            _bf16(Fraction((index * 3) % 23 - 11, 16))
            for index in range(256)
        ),
    )
    weights = tuple(
        tuple((row * 29 + column * 7) % 0x7F for column in range(256))
        for row in range(3)
    )
    scales = ((0x7E, 0x7F),)
    observed = dense_fp8_linear_bf16(inputs, weights, scales)
    expected = tuple(
        tuple(_independent_row(input_row, weight_row, scales[0]) for weight_row in weights)
        for input_row in inputs
    )
    assert observed.values == expected
    assert observed.activation_saturated_block_count == 0
    assert observed.output_saturated_element_count == 0


def test_dense_fp8_weight_scale_orientation_crosses_output_tile_boundary() -> None:
    one = _bf16(1)
    inputs = ((one,) * 128,)
    # E4M3FN code 0x38 is 1.0. Rows are identical so only scale orientation can
    # distinguish output row 127 from output row 128.
    weights = tuple((0x38,) * 128 for _ in range(129))
    scales = ((0x7F,), (0x80,))
    result = dense_fp8_linear_bf16(inputs, weights, scales)
    assert result.values[0][0] == result.values[0][127]
    assert result.values[0][128] != result.values[0][127]


def test_dense_fp8_linear_matches_independent_composition_randomly() -> None:
    rng = random.Random(0xF8_11)
    for _ in range(24):
        reduction_blocks = rng.randint(1, 3)
        reduction = reduction_blocks * 128
        input_rows = rng.randint(1, 3)
        output_rows = rng.randint(1, 5)
        inputs = tuple(
            tuple(
                _bf16(Fraction(rng.randint(-64, 64), 16))
                for _ in range(reduction)
            )
            for _ in range(input_rows)
        )
        finite_weight_codes = (0x00, 0x28, 0x30, 0x38, 0x3C, 0xA8, 0xB0, 0xB8)
        weights = tuple(
            tuple(rng.choice(finite_weight_codes) for _ in range(reduction))
            for _ in range(output_rows)
        )
        scales = (tuple(rng.randrange(0x7C, 0x81) for _ in range(reduction_blocks)),)
        observed = dense_fp8_linear_bf16(inputs, weights, scales)
        assert observed.values == tuple(
            tuple(
                _independent_row(input_row, weight_row, scales[0])
                for weight_row in weights
            )
            for input_row in inputs
        )


@pytest.mark.parametrize(
    ("inputs", "weights", "scales", "match"),
    [
        ((), ((0,) * 128,), ((0x7F,),), "at least one row"),
        (((0,) * 127,), ((0,) * 127,), ((0x7F,),), "divisible by 128"),
        (((0,) * 128,), (), ((0x7F,),), "at least one row"),
        (((0,) * 128,), ((0,) * 127,), ((0x7F,),), "rectangular"),
        (((0,) * 128,), ((0,) * 128,), (), "at least one row"),
        (((0,) * 128,), ((0,) * 128,), ((0x7F, 0x7F),), "width 1"),
        (
            ((0,) * 128,),
            tuple((0,) * 128 for _ in range(129)),
            ((0x7F,),),
            "ceil",
        ),
        (((True,) * 128,), ((0,) * 128,), ((0x7F,),), "must be in"),
        (((0,) * 128,), ((0x7F,) * 128,), ((0xFF,),), "poisons"),
    ],
)
def test_dense_fp8_linear_rejects_malformed_or_poisoned_inputs(
    inputs, weights, scales, match: str
) -> None:
    with pytest.raises(MatrixReferenceError, match=match):
        dense_fp8_linear_bf16(inputs, weights, scales)
