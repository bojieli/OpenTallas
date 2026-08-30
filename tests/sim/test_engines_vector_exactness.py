"""The data-bearing vector kernels equal their scalar reference, code for code.

Two ``VECTOR`` contracts are specified by ``fractions.Fraction`` evaluation per
element -- the unweighted BF16 head RMSNorm and the NUM-3.3 block activation
quantiser -- and neither is affordable that way: one DeepSeek prefill evaluates
them a hundred million times.  The engine therefore implements both over whole
tensors, and this file is the reason that is allowed to count as the same
function: not "close", not "within tolerance", but the identical encoding for
every input, including the awkward ones.

The generators deliberately reach for the awkward ones.  BF16 has only 65,536
encodings, so the interesting inputs -- subnormals, the boundary of the E4M3FN
range, exact rounding ties, blocks that are all zero -- can be enumerated
rather than hoped for.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.reference.formats import (
    NumericReferenceError,
    quantize_bf16_activation_block,
)
from runtime.reference.normalization import (
    HEAD_RMS_NORM_EPSILON_BF16,
    HEAD_RMS_NORM_WIDTH,
    head_rms_norm_bf16,
)
from runtime.sim.engines.vector import (
    _head_rms_norm_rows,
    _quantize_activation_blocks,
)

#: BF16 encodings that are finite: everything but the NaN and infinity band.
def _finite_bf16_codes(count: int, rng: np.random.Generator) -> np.ndarray:
    codes = np.empty(count, dtype=np.uint16)
    filled = 0
    while filled < count:
        draw = rng.integers(0, 1 << 16, size=count - filled, dtype=np.uint16)
        keep = draw[(draw & np.uint16(0x7F80)) != np.uint16(0x7F80)]
        codes[filled : filled + keep.size] = keep
        filled += keep.size
    return codes


def _moderate_bf16_codes(count: int, rng: np.random.Generator) -> np.ndarray:
    """Codes whose magnitudes sit where a real activation sits.

    The head RMSNorm squares its input, so a code near the top of the BF16
    range overflows the *contract* -- the reference raises there too.  This
    generator stays inside the exponent band a normalised activation occupies
    so that the comparison is about the arithmetic rather than about which side
    raises first.
    """
    exponent = rng.integers(110, 134, size=count, dtype=np.uint16)
    mantissa = rng.integers(0, 128, size=count, dtype=np.uint16)
    sign = rng.integers(0, 2, size=count, dtype=np.uint16)
    return (sign << np.uint16(15)) | (exponent << np.uint16(7)) | mantissa


class TestHeadRmsNormExactness:
    def test_matches_the_reference_on_random_rows(self) -> None:
        rng = np.random.default_rng(20260830)
        codes = _moderate_bf16_codes(16 * HEAD_RMS_NORM_WIDTH, rng).reshape(
            16, HEAD_RMS_NORM_WIDTH
        )
        expected = head_rms_norm_bf16(
            [tuple(int(code) for code in row) for row in codes],
            epsilon_bf16=HEAD_RMS_NORM_EPSILON_BF16,
        )
        produced = _head_rms_norm_rows(codes, HEAD_RMS_NORM_EPSILON_BF16)
        assert produced.tolist() == [list(row) for row in expected.output_codes]

    def test_matches_the_reference_on_an_all_zero_row(self) -> None:
        codes = np.zeros((1, HEAD_RMS_NORM_WIDTH), dtype=np.uint16)
        expected = head_rms_norm_bf16(
            [tuple(int(code) for code in codes[0])],
            epsilon_bf16=HEAD_RMS_NORM_EPSILON_BF16,
        )
        produced = _head_rms_norm_rows(codes, HEAD_RMS_NORM_EPSILON_BF16)
        assert produced.tolist() == [list(expected.output_codes[0])]

    def test_matches_the_reference_on_tiny_rows(self) -> None:
        """A row whose squares stay normal in binary32 is still exact."""
        rng = np.random.default_rng(7)
        exponent = rng.integers(64, 72, size=HEAD_RMS_NORM_WIDTH, dtype=np.uint16)
        mantissa = rng.integers(0, 128, size=HEAD_RMS_NORM_WIDTH, dtype=np.uint16)
        codes = ((exponent << np.uint16(7)) | mantissa).reshape(
            1, HEAD_RMS_NORM_WIDTH
        )
        expected = head_rms_norm_bf16(
            [tuple(int(code) for code in codes[0])],
            epsilon_bf16=HEAD_RMS_NORM_EPSILON_BF16,
        )
        produced = _head_rms_norm_rows(codes, HEAD_RMS_NORM_EPSILON_BF16)
        assert produced.tolist() == [list(expected.output_codes[0])]

    def test_refuses_a_subnormal_square_rather_than_rounding_twice(self) -> None:
        """Below the binary32 normal range the fast path fails closed.

        This is the guard the implementation's docstring claims: a product the
        contract rounds once, and binary32 would round twice, is refused rather
        than approximated.
        """
        codes = np.full((1, HEAD_RMS_NORM_WIDTH), 0x0001, dtype=np.uint16)
        with pytest.raises(NumericReferenceError):
            _head_rms_norm_rows(codes, HEAD_RMS_NORM_EPSILON_BF16)


class TestActivationQuantiserExactness:
    @pytest.mark.parametrize("width", [32, 64, 128])
    def test_matches_the_reference_on_random_blocks(self, width: int) -> None:
        rng = np.random.default_rng(31337 + width)
        codes = _finite_bf16_codes(64 * width, rng).reshape(64, width)
        produced_codes, produced_scales, saturations = _quantize_activation_blocks(
            codes
        )
        assert saturations == 0
        for row in range(codes.shape[0]):
            expected = quantize_bf16_activation_block(
                int(code) for code in codes[row]
            )
            assert int(produced_scales[row]) == expected.scale_code
            assert produced_codes[row].tolist() == list(expected.value_codes)

    def test_matches_the_reference_on_a_zero_block(self) -> None:
        codes = np.zeros((1, 32), dtype=np.uint16)
        produced_codes, produced_scales, saturations = _quantize_activation_blocks(
            codes
        )
        expected = quantize_bf16_activation_block(int(c) for c in codes[0])
        assert int(produced_scales[0]) == expected.scale_code == 0x7F
        assert produced_codes[0].tolist() == list(expected.value_codes)
        assert saturations == 0

    def test_matches_the_reference_at_the_extremes_of_the_range(self) -> None:
        """The largest and smallest finite BF16 magnitudes, and the ties.

        A block's scale is chosen from its maximum, so a block holding both the
        largest and the smallest finite magnitude exercises the widest possible
        scaled range in one call -- and the values midway between two E4M3FN
        encodings exercise the tie rule that the encoding LSB resolves.
        """
        extremes = [0x0001, 0x0080, 0x7F7F, 0xFF7F, 0x0000, 0x8000]
        ties = [0x3F40, 0x3FC0, 0x4020, 0xBF40]
        codes = np.array([extremes + ties + [0x3F80] * 6], dtype=np.uint16)
        produced_codes, produced_scales, _ = _quantize_activation_blocks(codes)
        expected = quantize_bf16_activation_block(int(c) for c in codes[0])
        assert int(produced_scales[0]) == expected.scale_code
        assert produced_codes[0].tolist() == list(expected.value_codes)

    def test_matches_the_reference_across_every_block_scale(self) -> None:
        """One block per attainable E8M0 scale, driven by its own maximum."""
        rng = np.random.default_rng(99)
        rows = []
        for exponent in range(1, 255, 7):
            mantissa = rng.integers(0, 128, size=16, dtype=np.uint16)
            rows.append(((np.uint16(exponent) << np.uint16(7)) | mantissa))
        codes = np.asarray(rows, dtype=np.uint16)
        produced_codes, produced_scales, _ = _quantize_activation_blocks(codes)
        for row in range(codes.shape[0]):
            expected = quantize_bf16_activation_block(
                int(code) for code in codes[row]
            )
            assert int(produced_scales[row]) == expected.scale_code
            assert produced_codes[row].tolist() == list(expected.value_codes)
