from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_e4m3fn,
    encode_binary32_rne,
)
from runtime.reference.quantization import (
    FP8_QDQ_AMAX_FLOOR,
    FP8_QDQ_BLOCK_SIZE,
    FP8_QDQ_MAXIMUM,
    KERNEL_SOURCE_SHA256,
    QuantizationReferenceError,
    fp8_qdq_bf16,
)


def _power_of_two(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _ceil_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _power_of_two(exponent):
        exponent -= 1
    return exponent if value == _power_of_two(exponent) else exponent + 1


def _bf16_code(value: Fraction) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _independent_qdq_row(
    row: tuple[int, ...], block_size: int = FP8_QDQ_BLOCK_SIZE
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    positive = tuple(decode_e4m3fn(code).value for code in range(0x7F))
    assert all(value is not None for value in positive)
    magnitudes = tuple(value for value in positive if value is not None)
    scales: list[int] = []
    fp8: list[int] = []
    output: list[int] = []
    for start in range(0, len(row), block_size):
        values = tuple(
            decode_bf16(code).value for code in row[start : start + block_size]
        )
        assert all(value is not None for value in values)
        finite_values = tuple(value for value in values if value is not None)
        maximum = max(max(map(abs, finite_values)), FP8_QDQ_AMAX_FLOOR)
        exponent = _ceil_log2(maximum / 448)
        scale = _power_of_two(exponent)
        scales.append(exponent + 127)
        for value in finite_values:
            normalized = max(Fraction(-448), min(Fraction(448), value / scale))
            magnitude = abs(normalized)
            selected = min(
                range(0x7F),
                key=lambda code: (abs(magnitudes[code] - magnitude), code & 1),
            )
            code = selected | (0x80 if normalized < 0 and selected else 0)
            fp8.append(code)
            decoded = decode_e4m3fn(code)
            assert decoded.value is not None
            output.append(_bf16_code(decoded.value * scale))
    return tuple(scales), tuple(fp8), tuple(output)


def test_fp8_qdq_source_and_profile_are_pinned() -> None:
    assert KERNEL_SOURCE_SHA256 == (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    )
    assert FP8_QDQ_BLOCK_SIZE == 64
    assert FP8_QDQ_MAXIMUM == 448
    assert encode_binary32_rne(FP8_QDQ_AMAX_FLOOR) == 0x38D1B717
    assert encode_binary32_rne(Fraction(1, 448)) == 0x3B124925


def test_fp8_qdq_known_answer_covers_subnormal_normal_ties_and_sign() -> None:
    exact_codes = (
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x38,
        0x39,
        0x3A,
        0x40,
        0x48,
        0x50,
        0x58,
        0x60,
        0x68,
        0x70,
        0x7E,
    )
    midpoint_pairs = (
        (0x00, 0x01),
        (0x01, 0x02),
        (0x02, 0x03),
        (0x03, 0x04),
        (0x38, 0x39),
        (0x39, 0x3A),
        (0x3A, 0x3B),
        (0x3B, 0x3C),
        (0x40, 0x41),
        (0x41, 0x42),
        (0x50, 0x51),
        (0x51, 0x52),
        (0x60, 0x61),
        (0x61, 0x62),
        (0x70, 0x71),
    )
    positive_values = []
    positive_expected = []
    for code in exact_codes:
        decoded = decode_e4m3fn(code)
        assert decoded.value is not None
        positive_values.append(decoded.value)
        positive_expected.append(code)
    for lower, upper in midpoint_pairs:
        lower_value = decode_e4m3fn(lower).value
        upper_value = decode_e4m3fn(upper).value
        assert lower_value is not None and upper_value is not None
        positive_values.append((lower_value + upper_value) / 2)
        positive_expected.append(lower if lower & 1 == 0 else upper)
    positive_values.append(Fraction(0))
    positive_expected.append(0)

    values = tuple(positive_values + [-value for value in positive_values])
    expected = tuple(
        positive_expected
        + [0 if code == 0 else code | 0x80 for code in positive_expected]
    )
    result = fp8_qdq_bf16((tuple(_bf16_code(value) for value in values),))

    assert result.scale_codes == ((0x7F,),)
    assert result.e4m3fn_codes == (expected,)
    assert result.values == (
        tuple(
            _bf16_code(decode_e4m3fn(code).value)  # type: ignore[arg-type]
            for code in expected
        ),
    )


def test_fp8_qdq_scale_floor_boundaries_and_independent_blocks() -> None:
    result = fp8_qdq_bf16(
        (
            (0x0000,) * 64,
            (0x38E0,) * 64,
            (0x38E1,) * 64,
            (0x43E0,) * 64,
            (0x43E1,) * 64,
            (0x7F60,) * 64,
            (0x7F61,) * 64,
        )
    )
    # The in-place kernel's binary32 1e-4 floor selects 2^-22 for zeros.
    assert result.scale_codes == (
        (0x69,),
        (0x69,),
        (0x6A,),
        (0x7F,),
        (0x80,),
        (0xF6,),
        (0xF7,),
    )
    assert tuple(row[0] for row in result.e4m3fn_codes) == (
        0x00,
        0x7E,
        0x76,
        0x7E,
        0x76,
        0x7E,
        0x76,
    )
    assert tuple(row[0] for row in result.values) == (
        0x0000,
        0x38E0,
        0x38E0,
        0x43E0,
        0x43E0,
        0x7F60,
        0x7F60,
    )


def test_fp8_qdq_matches_independent_randomized_multiblock_composition() -> None:
    generator = random.Random(0x4453_5634_4650_3851)
    rows = []
    for _ in range(32):
        row = []
        for _ in range(128):
            magnitude = generator.randrange(0x6000)
            sign = 0x8000 if generator.getrandbits(1) else 0
            row.append(sign | magnitude)
        rows.append(tuple(row))

    result = fp8_qdq_bf16(tuple(rows))
    expected = tuple(_independent_qdq_row(row) for row in rows)
    assert result.scale_codes == tuple(item[0] for item in expected)
    assert result.e4m3fn_codes == tuple(item[1] for item in expected)
    assert result.values == tuple(item[2] for item in expected)


def test_fp8_qdq_fails_closed_on_nonfinite_and_intermediate_overflow() -> None:
    with pytest.raises(QuantizationReferenceError, match="must be finite BF16"):
        fp8_qdq_bf16(((0x7F80,) * 64,))
    with pytest.raises(QuantizationReferenceError, match="must be finite BF16"):
        fp8_qdq_bf16(((0x7FC0,) * 64,))
    with pytest.raises(QuantizationReferenceError, match="binary32.*overflow"):
        fp8_qdq_bf16(((0x7F7F,) * 64,))


@pytest.mark.parametrize(
    ("input_codes", "block_size", "match"),
    [
        ((), 64, "at least one row"),
        (((),), 64, "at least one element"),
        (((0,) * 63,), 64, "divisible"),
        (((0,) * 64, (0,) * 128), 64, "rectangular"),
        (((0,) * 64,), 32, "qualified value 64"),
        (((0,) * 64,), True, "qualified value 64"),
        (((False,) * 64,), 64, "16-bit BF16"),
        (((1 << 16,) * 64,), 64, "16-bit BF16"),
    ],
)
def test_fp8_qdq_rejects_malformed_requests(
    input_codes: object, block_size: object, match: str
) -> None:
    with pytest.raises(QuantizationReferenceError, match=match):
        fp8_qdq_bf16(input_codes, block_size=block_size)  # type: ignore[arg-type]
