"""V4.1 released-width index and window profile checks."""

from fractions import Fraction
import random

import pytest

from runtime.prefill import v41_aux_kv_rows as R


def test_index_row_roundtrip_and_group_arithmetic():
    rng = random.Random(0x6810)
    codes = [rng.randrange(16) for _ in range(128)]
    scales = [126, 127, 128, 129]  # 1/2, 1, 2, 4
    packed = R.pack_index_row(codes, scales)
    row = R.parse_index_row(packed)
    assert len(packed) == 68 and row.codes == tuple(codes) and row.scales == tuple(scales)
    assert packed[0] == codes[0] | (codes[1] << 4)
    base = (Fraction(0), Fraction(1, 2), Fraction(1), Fraction(3, 2),
            Fraction(2), Fraction(3), Fraction(4), Fraction(6))
    for i, code in enumerate(codes):
        magnitude = base[code & 7]
        expected = (-magnitude if code & 8 else magnitude) * (Fraction(1, 2), 1, 2, 4)[i // 32]
        assert row.exact_values[i] == expected
    assert R.pack_index_row(row.codes, row.scales) == packed


def test_window_row_roundtrip_and_exact_scaled_values():
    rng = random.Random(0x5280)
    finite_codes = [c for c in range(256) if (c & 0x7F) != 0x7F]
    codes = [rng.choice(finite_codes) for _ in range(512)]
    scales = [127 + (i % 5) for i in range(16)]
    packed = R.pack_window_row(codes, scales)
    row = R.parse_window_row(packed)
    assert len(packed) == 528 and row.codes == tuple(codes) and row.scales == tuple(scales)
    assert packed[:512] == bytes(codes) and packed[512:] == bytes(scales)
    # E4M3 0x38 = 1, 0x3c = 1.5, 0x7e = 448; E8M0 0x7f = 1.
    fixed = R.pack_window_row([0x38, 0x3C, 0x7E] + [0] * 509, [0x7F] * 16)
    assert R.parse_window_row(fixed).exact_values[:3] == (1, Fraction(3, 2), 448)
    for i, code in enumerate(codes):
        sign = -1 if code & 0x80 else 1
        exponent, mantissa = (code >> 3) & 15, code & 7
        if exponent == 0:
            magnitude = Fraction(mantissa, 512)
        else:
            power = exponent - 7
            magnitude = Fraction(8 + mantissa, 8) * (
                Fraction(2**power) if power >= 0 else Fraction(1, 2**-power))
        assert row.exact_values[i] == sign * magnitude * 2 ** (scales[i // 32] - 127)
    assert R.pack_window_row(row.codes, row.scales) == packed


def test_invalid_codes_scales_and_lengths_fail_closed():
    index = R.pack_index_row([0] * 128, [127] * 4)
    window = R.pack_window_row([0] * 512, [127] * 16)
    with pytest.raises(ValueError, match="68"):
        R.parse_index_row(index[:-1])
    with pytest.raises(ValueError, match="528"):
        R.parse_window_row(window[:-1])
    with pytest.raises(ValueError, match="reserved"):
        R.parse_index_row(index[:64] + b"\xff" + index[65:])
    with pytest.raises(ValueError, match="reserved"):
        R.parse_window_row(window[:512] + b"\xff" + window[513:])
    with pytest.raises(ValueError, match="nonfinite"):
        R.parse_window_row(b"\x7f" + window[1:])
    with pytest.raises(ValueError, match="128"):
        R.pack_index_row([0] * 127, [127] * 4)
    with pytest.raises(ValueError, match="nonfinite"):
        R.pack_window_row([0xFF] + [0] * 511, [127] * 16)
