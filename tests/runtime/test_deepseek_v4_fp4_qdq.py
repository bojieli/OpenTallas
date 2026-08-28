from __future__ import annotations

from fractions import Fraction
import random

import pytest

from runtime.reference.formats import (
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_e2m1,
    encode_binary32_rne,
)
from runtime.reference.quantization import (
    FP4_AMAX_FLOOR,
    FP4_QDQ_BLOCK_SIZE,
    KERNEL_SOURCE_SHA256,
    QuantizationReferenceError,
    fp4_qdq_bf16,
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
    row: tuple[int, ...], block_size: int = FP4_QDQ_BLOCK_SIZE
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    magnitudes = (
        Fraction(0),
        Fraction(1, 2),
        Fraction(1),
        Fraction(3, 2),
        Fraction(2),
        Fraction(3),
        Fraction(4),
        Fraction(6),
    )
    scales: list[int] = []
    fp4: list[int] = []
    output: list[int] = []
    for start in range(0, len(row), block_size):
        values = tuple(
            decode_bf16(code).value for code in row[start : start + block_size]
        )
        assert all(value is not None for value in values)
        finite_values = tuple(value for value in values if value is not None)
        maximum = max(max(map(abs, finite_values)), FP4_AMAX_FLOOR)
        exponent = _ceil_log2(maximum / 6)
        scale = _power_of_two(exponent)
        scales.append(exponent + 127)
        for value in finite_values:
            normalized = max(Fraction(-6), min(Fraction(6), value / scale))
            magnitude = abs(normalized)
            selected = min(
                range(8),
                key=lambda code: (abs(magnitudes[code] - magnitude), code & 1),
            )
            code = selected | (0x8 if normalized < 0 and selected else 0)
            fp4.append(code)
            decoded = decode_e2m1(code)
            assert decoded.value is not None
            output.append(_bf16_code(decoded.value * scale))
    return tuple(scales), tuple(fp4), tuple(output)


def test_fp4_qdq_source_and_profile_are_pinned() -> None:
    assert KERNEL_SOURCE_SHA256 == (
        "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
    )
    assert FP4_QDQ_BLOCK_SIZE == 32
    assert FP4_AMAX_FLOOR == Fraction(6, 1 << 126)


def test_fp4_qdq_known_answer_covers_every_rne_interval_and_sign() -> None:
    positive = (
        0x0000,
        0x3E80,
        0x3F00,
        0x3F40,
        0x3F80,
        0x3FA0,
        0x3FC0,
        0x3FE0,
        0x4000,
        0x4020,
        0x4040,
        0x4060,
        0x4080,
        0x40A0,
        0x40C0,
        0x8000,
    )
    negative = (
        0x8000,
        0xBE80,
        0xBF00,
        0xBF40,
        0xBF80,
        0xBFA0,
        0xBFC0,
        0xBFE0,
        0xC000,
        0xC020,
        0xC040,
        0xC060,
        0xC080,
        0xC0A0,
        0xC0C0,
        0x0000,
    )
    result = fp4_qdq_bf16((positive + negative,))

    assert result.scale_codes == ((0x7F,),)
    assert result.e2m1_codes == (
        (
            0x0,
            0x0,
            0x1,
            0x2,
            0x2,
            0x2,
            0x3,
            0x4,
            0x4,
            0x4,
            0x5,
            0x6,
            0x6,
            0x6,
            0x7,
            0x0,
            0x0,
            0x0,
            0x9,
            0xA,
            0xA,
            0xA,
            0xB,
            0xC,
            0xC,
            0xC,
            0xD,
            0xE,
            0xE,
            0xE,
            0xF,
            0x0,
        ),
    )
    assert result.values == (
        (
            0x0000,
            0x0000,
            0x3F00,
            0x3F80,
            0x3F80,
            0x3F80,
            0x3FC0,
            0x4000,
            0x4000,
            0x4000,
            0x4040,
            0x4080,
            0x4080,
            0x4080,
            0x40C0,
            0x0000,
            0x0000,
            0x0000,
            0xBF00,
            0xBF80,
            0xBF80,
            0xBF80,
            0xBFC0,
            0xC000,
            0xC000,
            0xC000,
            0xC040,
            0xC080,
            0xC080,
            0xC080,
            0xC0C0,
            0x0000,
        ),
    )


def test_fp4_qdq_scale_floor_boundaries_and_independent_blocks() -> None:
    result = fp4_qdq_bf16(
        (
            (0x0000,) * 32,
            (0x01C0,) * 32,
            (0x01C1,) * 32,
            (0x40C0,) * 32,
            (0x40C1,) * 32,
            (0x7F40,) * 32,
            (0x7F41,) * 32,
        )
    )
    # Unlike ordinary all-zero MX blocks, the pinned indexer kernel's explicit
    # floor selects 2^-126 (E8M0 0x01), not scale one (0x7f).
    assert result.scale_codes == (
        (0x01,),
        (0x01,),
        (0x02,),
        (0x7F,),
        (0x80,),
        (0xFC,),
        (0xFD,),
    )
    assert tuple(row[0] for row in result.e2m1_codes) == (
        0x0,
        0x7,
        0x5,
        0x7,
        0x5,
        0x7,
        0x5,
    )
    assert tuple(row[0] for row in result.values) == (
        0x0000,
        0x01C0,
        0x01C0,
        0x40C0,
        0x40C0,
        0x7F40,
        0x7F40,
    )


def test_fp4_qdq_matches_independent_randomized_composition() -> None:
    generator = random.Random(0x4453_5634_4650_3451)
    rows = []
    for _ in range(64):
        row = []
        for _ in range(64):
            magnitude = generator.randrange(0x6000)
            sign = 0x8000 if generator.getrandbits(1) else 0
            row.append(sign | magnitude)
        rows.append(tuple(row))

    result = fp4_qdq_bf16(tuple(rows))
    expected = tuple(_independent_qdq_row(row) for row in rows)
    assert result.scale_codes == tuple(item[0] for item in expected)
    assert result.e2m1_codes == tuple(item[1] for item in expected)
    assert result.values == tuple(item[2] for item in expected)


def test_fp4_qdq_fails_closed_on_nonfinite_and_intermediate_overflow() -> None:
    with pytest.raises(QuantizationReferenceError, match="must be finite BF16"):
        fp4_qdq_bf16(((0x7F80,) * 32,))
    with pytest.raises(QuantizationReferenceError, match="must be finite BF16"):
        fp4_qdq_bf16(((0x7FC0,) * 32,))
    with pytest.raises(QuantizationReferenceError, match="binary32.*overflow"):
        fp4_qdq_bf16(((0x7F7F,) * 32,))


@pytest.mark.parametrize(
    ("input_codes", "block_size", "match"),
    [
        ((), 32, "at least one row"),
        (((),), 32, "at least one element"),
        (((0,) * 31,), 32, "divisible"),
        (((0,) * 32, (0,) * 64), 32, "rectangular"),
        (((0,) * 32,), 16, "qualified value 32"),
        (((0,) * 32,), True, "qualified value 32"),
        (((False,) * 32,), 32, "16-bit BF16"),
        (((1 << 16,) * 32,), 32, "16-bit BF16"),
    ],
)
def test_fp4_qdq_rejects_malformed_requests(
    input_codes: object, block_size: object, match: str
) -> None:
    with pytest.raises(QuantizationReferenceError, match=match):
        fp4_qdq_bf16(input_codes, block_size=block_size)  # type: ignore[arg-type]
