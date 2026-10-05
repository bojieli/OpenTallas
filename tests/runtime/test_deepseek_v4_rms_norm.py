from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    bf16_rsqrt,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    binary32_rsqrt,
    decode_bf16,
    encode_bf16_rne,
    encode_binary32_rne,
)
from runtime.reference.normalization import (
    HEAD_RMS_NORM_EPSILON_BF16,
    HEAD_RMS_NORM_WIDTH,
    MODEL_SOURCE_SHA256,
    RMS_NORM_EPSILON_BINARY32,
    RMS_NORM_WIDTHS,
    HeadRMSNormResult,
    NormalizationReferenceError,
    RMSNormResult,
    head_rms_norm_bf16,
    rms_norm_bf16,
)


def _widen_bf16(code: int) -> int:
    decoded = decode_bf16(code)
    assert decoded.finite and decoded.value is not None
    return encode_binary32_rne(decoded.value)


def _independent_balanced_sum(codes: tuple[int, ...]) -> int:
    if len(codes) == 1:
        return codes[0]
    midpoint = len(codes) // 2
    return binary32_add(
        _independent_balanced_sum(codes[:midpoint]),
        _independent_balanced_sum(codes[midpoint:]),
    )


def _independent_rms_norm(
    rows: tuple[tuple[int, ...], ...],
    weights: tuple[int, ...],
) -> RMSNormResult:
    width_code = encode_binary32_rne(len(weights))
    widened_weights = tuple(_widen_bf16(code) for code in weights)
    mean_codes = []
    inverse_codes = []
    output_rows = []
    saturation_count = 0
    for row in rows:
        widened = tuple(_widen_bf16(code) for code in row)
        squares = tuple(binary32_multiply(value, value) for value in widened)
        mean = binary32_divide(_independent_balanced_sum(squares), width_code)
        inverse = binary32_rsqrt(binary32_add(mean, RMS_NORM_EPSILON_BINARY32))
        output = []
        for value, weight in zip(widened, widened_weights, strict=True):
            normalized = binary32_multiply(value, inverse)
            converted = binary32_bits_to_bf16_rne(binary32_multiply(weight, normalized))
            saturation_count += int(converted.saturated)
            output.append(converted.code)
        mean_codes.append(mean)
        inverse_codes.append(inverse)
        output_rows.append(tuple(output))
    return RMSNormResult(
        inverse_rms_codes=tuple(inverse_codes),
        mean_square_codes=tuple(mean_codes),
        output_codes=tuple(output_rows),
        output_saturation_count=saturation_count,
    )


def _independent_head_rms_norm(
    rows: tuple[tuple[int, ...], ...],
) -> HeadRMSNormResult:
    width_code = encode_binary32_rne(HEAD_RMS_NORM_WIDTH)
    epsilon = decode_bf16(HEAD_RMS_NORM_EPSILON_BF16).value
    assert epsilon is not None
    mean_codes = []
    inverse_codes = []
    output_rows = []
    saturation_count = 0
    for row in rows:
        values = tuple(decode_bf16(code).value for code in row)
        assert all(value is not None for value in values)
        squares = tuple(encode_bf16_rne(value * value) for value in values)  # type: ignore[operator]
        assert not any(square.saturated for square in squares)
        widened_squares = tuple(_widen_bf16(square.code) for square in squares)
        mean_binary32 = binary32_divide(
            _independent_balanced_sum(widened_squares),
            width_code,
        )
        mean = binary32_bits_to_bf16_rne(mean_binary32)
        assert not mean.saturated
        mean_value = decode_bf16(mean.code).value
        assert mean_value is not None
        biased = encode_bf16_rne(mean_value + epsilon)
        assert not biased.saturated
        inverse = bf16_rsqrt(biased.code)
        inverse_value = decode_bf16(inverse).value
        assert inverse_value is not None
        output = []
        for value in values:
            assert value is not None
            converted = encode_bf16_rne(value * inverse_value)
            saturation_count += int(converted.saturated)
            output.append(converted.code)
        mean_codes.append(mean.code)
        inverse_codes.append(inverse)
        output_rows.append(tuple(output))
    return HeadRMSNormResult(
        inverse_rms_codes=tuple(inverse_codes),
        mean_square_codes=tuple(mean_codes),
        output_codes=tuple(output_rows),
        output_saturation_count=saturation_count,
    )


def test_rms_norm_source_epsilon_and_qualified_widths_are_pinned() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert RMS_NORM_EPSILON_BINARY32 == 0x358637BD
    assert RMS_NORM_WIDTHS == frozenset({128, 512, 1024, 4096})
    assert HEAD_RMS_NORM_EPSILON_BF16 == 0x3586
    assert HEAD_RMS_NORM_WIDTH == 512


def test_head_rms_norm_known_answers_expose_every_bf16_intermediate() -> None:
    width = HEAD_RMS_NORM_WIDTH
    zeros = (0,) * width
    ones = (0x3F80,) * width
    one_hot = (0x3F80,) + (0,) * (width - 1)
    rounded_square = (0x3F81,) * width

    result = head_rms_norm_bf16((zeros, ones, one_hot, rounded_square))

    assert result.mean_square_codes == (0, 0x3F80, 0x3B00, 0x3F82)
    assert result.inverse_rms_codes == (0x447A, 0x3F80, 0x41B5, 0x3F7E)
    assert result.output_codes == (
        zeros,
        ones,
        (0x41B5,) + (0,) * (width - 1),
        ones,
    )
    assert result.output_saturation_count == 0


def test_head_rms_norm_preserves_signs_subnormals_and_canonicalizes_zero() -> None:
    width = HEAD_RMS_NORM_WIDTH
    alternating = tuple(0xBF80 if index & 1 else 0x3F80 for index in range(width))
    result = head_rms_norm_bf16(
        (
            alternating,
            (0x8000,) * width,
            (0x0001,) * width,
            (0x8001,) * width,
        )
    )

    assert result.mean_square_codes == (0x3F80, 0, 0, 0)
    assert result.inverse_rms_codes == (0x3F80, 0x447A, 0x447A, 0x447A)
    assert result.output_codes == (
        alternating,
        (0,) * width,
        (0x01FA,) * width,
        (0x81FA,) * width,
    )


def test_head_rms_norm_matches_independent_randomized_bf16_composition() -> None:
    generator = random.Random(0x4845_4144_524D_534E)
    palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x3586,
        0xB586,
        0x3D80,
        0xBD80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
        0x4100,
        0xC100,
    )
    rows = tuple(
        tuple(generator.choice(palette) for _ in range(HEAD_RMS_NORM_WIDTH))
        for _ in range(4)
    )
    assert head_rms_norm_bf16(rows) == _independent_head_rms_norm(rows)


@pytest.mark.parametrize(
    ("inputs", "epsilon", "match"),
    [
        ((), HEAD_RMS_NORM_EPSILON_BF16, "at least one row"),
        ("bad", HEAD_RMS_NORM_EPSILON_BF16, "must be a sequence"),
        ((0,) * 512, HEAD_RMS_NORM_EPSILON_BF16, "must be a sequence"),
        (((0,) * 511,), HEAD_RMS_NORM_EPSILON_BF16, "exactly 512"),
        (((0,) * 513,), HEAD_RMS_NORM_EPSILON_BF16, "exactly 512"),
        (((False,) * 512,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        (((1 << 16,) * 512,), HEAD_RMS_NORM_EPSILON_BF16, "16-bit BF16"),
        (((0x7F80,) * 512,), HEAD_RMS_NORM_EPSILON_BF16, "finite BF16"),
        (((0,) * 512,), 0x3585, "must equal"),
        (((0,) * 512,), True, "must equal"),
        (((0,) * 512,), 1e-6, "must equal"),
    ],
)
def test_head_rms_norm_rejects_malformed_or_nonfinite_requests(
    inputs: object,
    epsilon: object,
    match: str,
) -> None:
    with pytest.raises(NormalizationReferenceError, match=match):
        head_rms_norm_bf16(  # type: ignore[arg-type]
            inputs,
            epsilon_bf16=epsilon,
        )


def test_head_rms_norm_poisons_bf16_intermediate_overflow() -> None:
    with pytest.raises(NormalizationReferenceError, match="BF16 square overflow"):
        head_rms_norm_bf16(((0x7F7F,) * HEAD_RMS_NORM_WIDTH,))


def test_head_rms_norm_epsilon_code_is_direct_bf16_rounding_of_source_literal() -> None:
    assert encode_bf16_rne(Fraction(1, 1_000_000)).code == 0x3586


@pytest.mark.parametrize(
    ("width", "one_hot_mean", "one_hot_inverse", "one_hot_output"),
    [
        (128, 0x3C000000, 0x413501FC, 0x4135),
        (512, 0x3B000000, 0x41B4F917, 0x41B5),
        (1024, 0x3A800000, 0x41FFDE79, 0x4200),
        (4096, 0x39800000, 0x427F7A31, 0x427F),
    ],
)
def test_rms_norm_known_answers_cover_every_graph_width(
    width: int,
    one_hot_mean: int,
    one_hot_inverse: int,
    one_hot_output: int,
) -> None:
    weights = (0x3F80,) * width
    zeros = (0,) * width
    ones = (0x3F80,) * width
    one_hot = (0x3F80,) + (0,) * (width - 1)

    result = rms_norm_bf16((zeros, ones, one_hot), weights)

    assert result.mean_square_codes == (0, 0x3F800000, one_hot_mean)
    assert result.inverse_rms_codes == (
        0x447A0000,
        0x3F7FFFF8,
        one_hot_inverse,
    )
    assert result.output_codes[0] == zeros
    assert result.output_codes[1] == ones
    assert result.output_codes[2] == (one_hot_output,) + (0,) * (width - 1)
    assert result.output_saturation_count == 0


def test_rms_norm_preserves_signs_and_applies_nonuniform_checkpoint_weights() -> None:
    width = 128
    row = tuple(0xBF80 if index & 1 else 0x3F80 for index in range(width))
    weight_pattern = (0x3F80, 0x4000, 0x3F00, 0xBF80)
    weights = tuple(weight_pattern[index % 4] for index in range(width))

    result = rms_norm_bf16((row,), weights)

    assert result.mean_square_codes == (0x3F800000,)
    assert result.inverse_rms_codes == (0x3F7FFFF8,)
    assert result.output_codes == (
        tuple(
            code for _ in range(width // 4) for code in (0x3F80, 0xC000, 0x3F00, 0x3F80)
        ),
    )


def test_rms_norm_matches_independent_randomized_composition_at_all_widths() -> None:
    generator = random.Random(0x524D_534E_4F52_4D)
    input_palette = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x3D80,
        0xBD80,
        0x3F00,
        0xBF00,
        0x3F80,
        0xBF80,
        0x4000,
        0xC000,
        0x4100,
        0xC100,
    )
    weight_palette = (0x3E80, 0xBE80, 0x3F00, 0xBF00, 0x3F80, 0xBF80, 0x4000)
    for width in sorted(RMS_NORM_WIDTHS):
        rows = (tuple(generator.choice(input_palette) for _ in range(width)),)
        weights = tuple(generator.choice(weight_palette) for _ in range(width))
        assert rms_norm_bf16(rows, weights) == _independent_rms_norm(rows, weights)


def test_rms_norm_canonicalizes_signed_zero_and_preserves_subnormal_paths() -> None:
    width = 128
    weights = (0x3F80,) * width
    result = rms_norm_bf16(
        (
            (0x8000,) * width,
            (0x0001,) * width,
            (0x8001,) * width,
        ),
        weights,
    )

    assert result.mean_square_codes == (0, 0, 0)
    assert result.inverse_rms_codes == (0x447A0000,) * 3
    assert result.output_codes == (
        (0,) * width,
        (0x01FA,) * width,
        (0x81FA,) * width,
    )


def test_rms_norm_counts_finite_bf16_saturation_and_rejects_f32_overflow() -> None:
    width = 128
    saturating_row = (0x3F81,) + (0x3F80,) * (width - 1)
    saturating_weights = (0x7F7E,) + (0x3F80,) * (width - 1)
    result = rms_norm_bf16((saturating_row,), saturating_weights)
    assert result.output_codes[0][0] == 0x7F7F
    assert result.output_saturation_count == 1

    with pytest.raises(NormalizationReferenceError, match="binary32.*overflow"):
        rms_norm_bf16(((0x7F7F,) * width,), (0x3F80,) * width)
    with pytest.raises(NormalizationReferenceError, match="binary32.*overflow"):
        rms_norm_bf16((saturating_row,), (0x7F7F,) + (0x3F80,) * (width - 1))


@pytest.mark.parametrize(
    ("inputs", "weights", "epsilon", "match"),
    [
        ((), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "at least one row"),
        ("bad", (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "must be a sequence"),
        ((0,) * 128, (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "must be a sequence"),
        (((0,) * 127,), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "exactly 128"),
        (((0,) * 129,), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "exactly 128"),
        (((False,) * 128,), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "16-bit BF16"),
        (
            ((1 << 16,) * 128,),
            (0x3F80,) * 128,
            RMS_NORM_EPSILON_BINARY32,
            "16-bit BF16",
        ),
        (((0x7F80,) * 128,), (0x3F80,) * 128, RMS_NORM_EPSILON_BINARY32, "finite BF16"),
        (((0,) * 128,), (), RMS_NORM_EPSILON_BINARY32, "at least one value"),
        (
            ((0,) * 128,),
            (0x3F80,) * 127,
            RMS_NORM_EPSILON_BINARY32,
            "outside qualified widths",
        ),
        (((0,) * 128,), (False,) * 128, RMS_NORM_EPSILON_BINARY32, "16-bit BF16"),
        (((0,) * 128,), (0x7FC0,) * 128, RMS_NORM_EPSILON_BINARY32, "finite BF16"),
        (((0,) * 128,), (0x3F80,) * 128, 0x358637BC, "must equal"),
        (((0,) * 128,), (0x3F80,) * 128, True, "must equal"),
        (((0,) * 128,), (0x3F80,) * 128, 1e-6, "must equal"),
    ],
)
def test_rms_norm_rejects_malformed_or_nonfinite_requests(
    inputs: object,
    weights: object,
    epsilon: object,
    match: str,
) -> None:
    with pytest.raises(NormalizationReferenceError, match=match):
        rms_norm_bf16(  # type: ignore[arg-type]
            inputs,
            weights,
            epsilon_binary32=epsilon,
        )


def test_rms_norm_epsilon_code_is_the_binary32_rounding_of_source_literal() -> None:
    assert encode_binary32_rne(Fraction(1, 1_000_000)) == 0x358637BD


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_rms_norm_matches_bounded_native_pytorch_differential(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    generator = random.Random(0x524D_534E_4155_4449)
    for width in sorted(RMS_NORM_WIDTHS):
        weights = tuple(
            (generator.randrange(2) << 15)
            | (generator.randrange(117, 134) << 7)
            | generator.randrange(128)
            for _ in range(width)
        )
        rows = (
            (0,) * width,
            (0x3F80,) * width,
            (0x3F80,) + (0,) * (width - 1),
            (0x0001,) * width,
            *(
                tuple(
                    (generator.randrange(2) << 15)
                    | (generator.randrange(100, 151) << 7)
                    | generator.randrange(128)
                    for _ in range(width)
                )
                for _ in range(12)
            ),
        )
        expected = rms_norm_bf16(rows, weights)

        input_bits = torch.tensor(
            [code for row in rows for code in row], dtype=torch.uint16
        ).reshape(len(rows), width)
        widened = input_bits.view(torch.bfloat16).to(device).to(torch.float32)
        weight_bits = torch.tensor(weights, dtype=torch.uint16)
        widened_weights = weight_bits.view(torch.bfloat16).to(device).to(torch.float32)

        source_mean = widened.square().mean(dim=-1)
        source_inverse = torch.rsqrt(source_mean + 1e-6)
        source_output = (widened_weights * (widened * source_inverse.unsqueeze(-1))).to(
            torch.bfloat16
        )

        level = widened.square()
        while level.shape[-1] > 1:
            level = level[..., 0::2] + level[..., 1::2]
        canonical_mean = level[:, 0] / torch.tensor(
            float(width), dtype=torch.float32, device=device
        )
        canonical_inverse = torch.rsqrt(
            canonical_mean + torch.tensor(1e-6, dtype=torch.float32, device=device)
        )

        canonical_mean_codes = tuple(
            int(code) & 0xFFFFFFFF
            for code in canonical_mean.view(torch.int32).cpu().tolist()
        )
        canonical_inverse_codes = tuple(
            int(code) & 0xFFFFFFFF
            for code in canonical_inverse.view(torch.int32).cpu().tolist()
        )
        source_output_codes = tuple(
            0 if int(code) & 0x7FFF == 0 else int(code)
            for code in source_output.view(torch.uint16).reshape(-1).cpu().tolist()
        )
        expected_output_codes = tuple(
            code for row in expected.output_codes for code in row
        )

        assert canonical_mean_codes == expected.mean_square_codes
        # The installed native CPU and CUDA rsqrt paths may select an adjacent
        # binary32 code; the target independently fixes correct RNE.
        assert all(
            abs(observed - target) <= 1
            for observed, target in zip(
                canonical_inverse_codes,
                expected.inverse_rms_codes,
                strict=True,
            )
        )
        # The source path is a backend cross-check, not the target rule. Every
        # observed difference on this governed corpus must remain an adjacent
        # same-sign BF16 code after positive-zero canonicalization. NUM-6.8
        # records the exact counts from the pinned development CPU and SM120.
        assert all(
            observed == target
            or (observed >> 15 == target >> 15 and abs(observed - target) == 1)
            for observed, target in zip(
                source_output_codes,
                expected_output_codes,
                strict=True,
            )
        )


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_head_rms_norm_matches_bounded_native_bf16_differential(device: str) -> None:
    torch = pytest.importorskip("torch", reason="optional PyTorch differential")
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA is unavailable")

    generator = random.Random(0x4845_4144_524D_534E)
    width = HEAD_RMS_NORM_WIDTH
    rows = (
        (0,) * width,
        (0x3F80,) * width,
        (0x3F80,) + (0,) * (width - 1),
        (0x0001,) * width,
        *(
            tuple(
                (generator.randrange(2) << 15)
                | (generator.randrange(100, 152) << 7)
                | generator.randrange(128)
                for _ in range(width)
            )
            for _ in range(12)
        ),
    )
    expected = head_rms_norm_bf16(rows)
    input_bits = torch.tensor(
        [code for row in rows for code in row], dtype=torch.uint16
    ).reshape(len(rows), width)
    query = input_bits.view(torch.bfloat16).to(device)

    source_squares = query.square()
    source_mean = source_squares.mean(dim=-1)
    source_inverse = torch.rsqrt(source_mean + 1e-6)
    source_output = query * source_inverse.unsqueeze(-1)
    assert source_squares.dtype == torch.bfloat16
    assert source_mean.dtype == torch.bfloat16
    assert source_inverse.dtype == torch.bfloat16
    assert source_output.dtype == torch.bfloat16

    level = source_squares.to(torch.float32)
    while level.shape[-1] > 1:
        level = level[..., 0::2] + level[..., 1::2]
    canonical_mean = (level[:, 0] / float(width)).to(torch.bfloat16)
    canonical_inverse = torch.rsqrt(
        canonical_mean + torch.tensor(1e-6, dtype=torch.bfloat16, device=device)
    )
    canonical_output = query * canonical_inverse.unsqueeze(-1)

    def codes(tensor) -> tuple[int, ...]:
        return tuple(
            0 if int(code) & 0x7FFF == 0 else int(code)
            for code in tensor.view(torch.uint16).reshape(-1).cpu().tolist()
        )

    expected_outputs = tuple(
        code for row in expected.output_codes for code in row
    )
    assert codes(canonical_mean) == expected.mean_square_codes
    assert all(
        abs(observed - target) <= 1
        for observed, target in zip(
            codes(source_mean),
            expected.mean_square_codes,
            strict=True,
        )
    )
    assert all(
        abs(observed - target) <= 1
        for observed, target in zip(
            codes(canonical_inverse),
            expected.inverse_rms_codes,
            strict=True,
        )
    )
    for observed_codes in (codes(canonical_output), codes(source_output)):
        assert all(
            observed == target
            or (observed >> 15 == target >> 15 and abs(observed - target) == 1)
            for observed, target in zip(
                observed_codes,
                expected_outputs,
                strict=True,
            )
        )
