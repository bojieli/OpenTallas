from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.matrix import dense_fp8_linear_selected_rows_bf16
from runtime.service_engine.fp8_numeric import (
    FP8ServiceNumericError,
    execute_selected_rows,
)


def _bf16(value: Fraction | int) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _execute(
    inputs: tuple[tuple[int, ...], ...],
    weights: tuple[tuple[int, ...], ...],
    scales: tuple[tuple[int, ...], ...],
    selected: tuple[int, ...],
):
    return execute_selected_rows(
        inputs,
        selected_rows=selected,
        input_features=len(inputs[0]),
        weight_row=lambda row: bytes(weights[row]),
        scale_code=lambda row, block: scales[row // 128][block],
    )


def test_service_numeric_matches_independent_reference_across_scale_tiles() -> None:
    inputs = (
        tuple(_bf16(Fraction((index % 19) - 9, 8)) for index in range(256)),
        tuple(_bf16(Fraction((index * 5) % 31 - 15, 16)) for index in range(256)),
    )
    weights = tuple(
        tuple((row * 17 + column * 3) % 0x7F for column in range(256))
        for row in range(257)
    )
    scales = (
        (0x7D, 0x7E),
        (0x7F, 0x80),
        (0x81, 0x82),
    )
    selected = (0, 127, 128, 255, 256)
    observed, activation_saturations, output_saturations = _execute(
        inputs, weights, scales, selected
    )
    expected = dense_fp8_linear_selected_rows_bf16(
        inputs,
        tuple(weights[row] for row in selected),
        scales,
        output_row_indices=selected,
        declared_output_count=257,
    )
    assert observed == expected.values
    assert activation_saturations == expected.activation_saturated_block_count
    assert output_saturations == expected.output_saturated_element_count


def test_service_numeric_matches_reference_randomly_without_shared_algorithm() -> None:
    rng = random.Random(0x5E8_1CE)
    finite_weights = (0x00, 0x28, 0x30, 0x38, 0x3C, 0xA8, 0xB0, 0xB8)
    for _ in range(24):
        blocks = rng.randint(1, 3)
        reduction = blocks * 128
        output_count = rng.randint(129, 260)
        inputs = tuple(
            tuple(
                _bf16(Fraction(rng.randint(-64, 64), 16))
                for _ in range(reduction)
            )
            for _ in range(rng.randint(1, 3))
        )
        weights = tuple(
            tuple(rng.choice(finite_weights) for _ in range(reduction))
            for _ in range(output_count)
        )
        scales = tuple(
            tuple(rng.randrange(0x7C, 0x81) for _ in range(blocks))
            for _ in range((output_count + 127) // 128)
        )
        selected = tuple(sorted({0, 127, 128, output_count - 1}))
        observed, activation_saturations, output_saturations = _execute(
            inputs, weights, scales, selected
        )
        expected = dense_fp8_linear_selected_rows_bf16(
            inputs,
            tuple(weights[row] for row in selected),
            scales,
            output_row_indices=selected,
            declared_output_count=output_count,
        )
        assert observed == expected.values
        assert activation_saturations == expected.activation_saturated_block_count
        assert output_saturations == expected.output_saturated_element_count


def test_service_numeric_rejects_nonfinite_activation_and_reserved_scale() -> None:
    inputs = ((0,) * 127 + (0x7F80,),)
    weights = ((0x38,) * 128,)
    with pytest.raises(FP8ServiceNumericError, match="BF16 NaN or infinity"):
        _execute(inputs, weights, ((0x7F,),), (0,))
    with pytest.raises(FP8ServiceNumericError, match="reserved E8M0"):
        _execute(((0,) * 128,), weights, ((0xFF,),), (0,))
