from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    DENSE_REDUCTION_BLOCK,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_ordered_dot,
    decode_bf16,
    encode_bf16_rne,
    encode_binary32_rne,
    fp8_fp8_block_dot,
    quantize_bf16_activation_block,
)
from runtime.reference.matrix import (
    BF16_LINEAR_INPUT_FEATURES,
    BF16_LINEAR_OUTPUT_FEATURES,
    DENSE_OUTPUT_SCALE_BLOCK,
    MODEL_SOURCE_SHA256,
    BF16LinearResult,
    MatrixReferenceError,
    bf16_linear_bf16,
    dense_fp8_linear_bf16,
    dense_fp8_linear_selected_rows_bf16,
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


def _independent_bf16_linear(
    inputs: tuple[tuple[int, ...], ...],
    weights: tuple[tuple[int, ...], ...],
) -> BF16LinearResult:
    input_values = []
    for row in inputs:
        decoded_row = []
        for code in row:
            decoded = decode_bf16(code)
            assert decoded.value is not None
            decoded_row.append(decoded.value)
        input_values.append(tuple(decoded_row))
    weight_values = []
    for row in weights:
        decoded_row = []
        for code in row:
            decoded = decode_bf16(code)
            assert decoded.value is not None
            decoded_row.append(decoded.value)
        weight_values.append(tuple(decoded_row))

    saturation_count = 0
    output = []
    for input_row in input_values:
        output_row = []
        for weight_row in weight_values:
            converted = binary32_bits_to_bf16_rne(
                binary32_ordered_dot(input_row, weight_row)
            )
            saturation_count += int(converted.saturated)
            output_row.append(converted.code)
        output.append(tuple(output_row))
    return BF16LinearResult(saturation_count, tuple(output))


def test_dense_fp8_matrix_reference_is_bound_to_pinned_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert DENSE_OUTPUT_SCALE_BLOCK == DENSE_REDUCTION_BLOCK == 128
    assert BF16_LINEAR_INPUT_FEATURES == 4096
    assert BF16_LINEAR_OUTPUT_FEATURES == 64


def test_bf16_linear_known_answers_and_output_boundary() -> None:
    inputs = (
        (0x3F80, 0x4000, 0xBF80, 0x3F00),
        (0xBF80, 0xC000, 0x3F80, 0xBF00),
    )
    weights = (
        (0x3F80, 0x3F80, 0x3F80, 0x3F80),
        (0x3F80, 0xBF80, 0x3F80, 0xBF80),
        (0, 0, 0, 0),
    )

    result = bf16_linear_bf16(inputs, weights)

    assert result.values == (
        (0x4020, 0xC020, 0),
        (0xC020, 0x4020, 0),
    )
    assert result.output_saturated_element_count == 0


def test_bf16_linear_rounds_each_increasing_k_accumulation() -> None:
    # The second product is exactly half a binary32 ULP at 1.0. It ties back to
    # even before the final -1.0 arrives, so the ordered target returns zero;
    # one exact end-of-dot rounding would retain 2^-24 as BF16 0x3380.
    two_to_minus_twelve = 0x3980
    result = bf16_linear_bf16(
        ((0x3F80, two_to_minus_twelve, 0xBF80),),
        ((0x3F80, two_to_minus_twelve, 0x3F80),),
    )
    assert result.values == ((0,),)
    assert encode_bf16_rne(Fraction(1, 1 << 24)).code == 0x3380


def test_bf16_linear_covers_the_complete_graph_shape() -> None:
    inputs = ((0x3F80,) + (0,) * (BF16_LINEAR_INPUT_FEATURES - 1),)
    palette = (0, 0x3E80, 0xBE80, 0x3F00, 0xBF00, 0x3F80, 0xBF80, 0x4000)
    weights = tuple(
        (palette[row % len(palette)],)
        + (0,) * (BF16_LINEAR_INPUT_FEATURES - 1)
        for row in range(BF16_LINEAR_OUTPUT_FEATURES)
    )

    result = bf16_linear_bf16(inputs, weights)

    assert result.values == (
        tuple(palette[row % len(palette)] for row in range(64)),
    )
    assert result.output_saturated_element_count == 0


def test_bf16_linear_matches_independent_randomized_composition() -> None:
    generator = random.Random(0x4246_3136_4C49_4E45)
    palette = (
        0,
        0x0001,
        0x8001,
        0x3D80,
        0xBD80,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    for _ in range(12):
        reduction = generator.randint(1, 48)
        inputs = tuple(
            tuple(generator.choice(palette) for _ in range(reduction))
            for _ in range(generator.randint(1, 3))
        )
        weights = tuple(
            tuple(generator.choice(palette) for _ in range(reduction))
            for _ in range(generator.randint(1, 5))
        )
        assert bf16_linear_bf16(inputs, weights) == _independent_bf16_linear(
            inputs,
            weights,
        )


def test_bf16_linear_counts_output_saturation_and_poisons_accumulator_overflow() -> None:
    # max_finite + 2^119 is the midpoint above odd max-finite BF16. Binary32 can
    # represent it, but BF16 RNE selects infinity and the target saturates/counts.
    saturated = bf16_linear_bf16(
        ((0x7F7F, 0x7B00),),
        ((0x3F80, 0x3F80),),
    )
    assert saturated.values == ((0x7F7F,),)
    assert saturated.output_saturated_element_count == 1

    with pytest.raises(MatrixReferenceError, match="binary32 accumulation overflow"):
        bf16_linear_bf16(((0x7F7F,),), ((0x7F7F,),))


@pytest.mark.parametrize(
    ("inputs", "weights", "match"),
    [
        ((), ((0,),), "at least one row"),
        ("bad", ((0,),), "must be a sequence"),
        (((),), ((0,),), "at least one element"),
        (((0,), (0, 0)), ((0,),), "rectangular"),
        (((0,),), (), "at least one row"),
        (((0, 0),), ((0,),), "rectangular with width 2"),
        (((True,),), ((0,),), "must be in"),
        (((0,),), ((False,),), "must be in"),
        (((0x7F80,),), ((0,),), "finite BF16"),
        (((0,),), ((0x7FC0,),), "finite BF16"),
    ],
)
def test_bf16_linear_rejects_malformed_or_nonfinite_inputs(
    inputs: object,
    weights: object,
    match: str,
) -> None:
    with pytest.raises(MatrixReferenceError, match=match):
        bf16_linear_bf16(inputs, weights)  # type: ignore[arg-type]


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_bf16_linear_matches_bounded_native_pytorch_differential(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    generator = random.Random(0x4246_3136_4C49_4E45)
    reduction = BF16_LINEAR_INPUT_FEATURES
    input_rows = 16
    output_rows = 4
    palette = (
        0,
        0x0001,
        0x8001,
        0x3D80,
        0xBD80,
        0x3E80,
        0xBE80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
    )
    inputs = tuple(
        tuple(generator.choice(palette) for _ in range(reduction))
        for _ in range(input_rows)
    )
    weights = tuple(
        tuple(generator.choice(palette) for _ in range(reduction))
        for _ in range(output_rows)
    )
    expected = bf16_linear_bf16(inputs, weights)

    input_bits = torch.tensor(
        [code for row in inputs for code in row], dtype=torch.uint16
    ).reshape(input_rows, reduction)
    weight_bits = torch.tensor(
        [code for row in weights for code in row], dtype=torch.uint16
    ).reshape(output_rows, reduction)
    observed = torch.nn.functional.linear(
        input_bits.view(torch.bfloat16).to(device),
        weight_bits.view(torch.bfloat16).to(device),
    )
    assert observed.dtype == torch.bfloat16
    observed_codes = tuple(
        0 if int(code) & 0x7FFF == 0 else int(code)
        for code in observed.view(torch.uint16).reshape(-1).cpu().tolist()
    )
    expected_codes = tuple(code for row in expected.values for code in row)

    # Native CUDA tensor-core tiling is not the target's increasing-K order.
    # The governed audit records its exact difference count; this test bounds
    # backend drift without making native reduction order architectural.
    assert all(
        observed_code == expected_code
        or (
            observed_code >> 15 == expected_code >> 15
            and abs(observed_code - expected_code) <= 8
        )
        for observed_code, expected_code in zip(
            observed_codes,
            expected_codes,
            strict=True,
        )
    )


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


def test_selected_output_rows_are_an_exact_projection_of_complete_linear() -> None:
    inputs = (
        tuple(_bf16(Fraction((index % 11) - 5, 4)) for index in range(256)),
    )
    weights = tuple(
        tuple((row * 13 + column * 5) % 0x7F for column in range(256))
        for row in range(257)
    )
    scales = (
        (0x7D, 0x7E),
        (0x7F, 0x80),
        (0x81, 0x82),
    )
    complete = dense_fp8_linear_bf16(inputs, weights, scales)
    selected_rows = (0, 127, 128, 255, 256)
    selected = dense_fp8_linear_selected_rows_bf16(
        inputs,
        tuple(weights[index] for index in selected_rows),
        scales,
        output_row_indices=selected_rows,
        declared_output_count=257,
    )
    assert selected.values == (
        tuple(complete.values[0][index] for index in selected_rows),
    )
    assert selected.activation_saturated_block_count == (
        complete.activation_saturated_block_count
    )


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


@pytest.mark.parametrize(
    ("indices", "declared", "match"),
    [
        ((), 4, "non-empty"),
        ((1, 0), 4, "strictly increasing"),
        ((0, 0), 4, "strictly increasing"),
        ((4,), 4, "must be in"),
        ((0,), 0, "declared_output_count"),
    ],
)
def test_selected_dense_fp8_rows_reject_illegal_logical_indices(
    indices, declared: int, match: str
) -> None:
    with pytest.raises(MatrixReferenceError, match=match):
        dense_fp8_linear_selected_rows_bf16(
            ((0,) * 128,),
            tuple((0,) * 128 for _ in indices),
            ((0x7F,),),
            output_row_indices=indices,
            declared_output_count=declared,
        )
