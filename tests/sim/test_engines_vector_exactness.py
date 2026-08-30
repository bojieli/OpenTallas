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
from runtime.reference.quantization import (
    FP4_AMAX_FLOOR,
    FP4_MAXIMUM,
    _BINARY32_RECIPROCAL_SIX,
    _ceil_log2,
    _finite_bf16_matrix,
    _power_of_two,
)
from runtime.reference import formats as exact_formats
from runtime.sim.engines.vector import (
    _head_rms_norm_rows,
    _quantize_activation_blocks,
    _quantize_fp4_qdq_blocks,
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


def _fp4_quantise_block(values: tuple) -> tuple[int, tuple[int, ...]]:
    """``runtime.reference.quantization._block_qdq``, quantise half only.

    The reference performs the *dequantise* half in the same function and fails
    closed when the reconstruction overflows binary32 -- which it does for a
    block of BF16 maxima.  ``VECTOR.CONVERT`` splits the two: ``QUANTIZE``
    produces codes and scales and ``DEQUANTIZE`` reconstructs, so the overflow
    belongs to the other operator.  This is the reference's own arithmetic with
    the second half left where it belongs, and nothing here shares code with the
    engine.
    """
    maximum = max(max(abs(value) for value in values), FP4_AMAX_FLOOR)
    maximum_code = exact_formats.encode_binary32_rne(maximum)
    ratio_code = exact_formats.binary32_multiply(
        maximum_code, _BINARY32_RECIPROCAL_SIX
    )
    ratio = exact_formats.decode_binary32(ratio_code)
    exponent = _ceil_log2(ratio.value)
    scale_code = exponent + 127
    assert 1 <= scale_code <= 253
    scale_binary32 = exact_formats.encode_binary32_rne(_power_of_two(exponent))
    codes = []
    for value in values:
        quotient = exact_formats.decode_binary32(
            exact_formats.binary32_divide(
                exact_formats.encode_binary32_rne(value), scale_binary32
            )
        )
        clamped = max(-FP4_MAXIMUM, min(FP4_MAXIMUM, quotient.value))
        codes.append(exact_formats.encode_e2m1_rne(clamped).code)
    return scale_code, tuple(codes)


class TestFP4ActivationQuantiserExactness:
    """``quantization_fp4_qdq_bf16_quantize_v1``, code for code.

    This is a *different rule* from the block activation quantiser above, not a
    variant of it: the scale is derived by one binary32 multiply and a
    ceil(log2) rather than searched for, the amax has a floor, and the quotient
    is clamped by contract instead of raising.  The engine lacked it entirely,
    which is why a DeepSeek indexer quantisation refused with "QUANTIZE code
    view stores MXFP4_E2M1; expected FP8_E4M3FN" while the graph, the numeric
    profile, the view and the backend descriptor all agreed on MXFP4.
    """

    def _check(self, codes: np.ndarray) -> None:
        produced, scales, clamps = _quantize_fp4_qdq_blocks(codes)
        rows = _finite_bf16_matrix(tuple(tuple(int(c) for c in row) for row in codes))
        for index, row in enumerate(rows):
            scale_code, expected = _fp4_quantise_block(row)
            assert int(scales[index]) == scale_code, index
            assert produced[index].tolist() == list(expected), index
        # The scale is derived *from* the amax, so no quotient can exceed six:
        # the clamp in the contract is a guard, and this says it stays one.
        assert clamps == 0

    @pytest.mark.parametrize("blocks", [1, 8, 64])
    def test_matches_the_reference_on_random_blocks(self, blocks: int) -> None:
        rng = np.random.default_rng(4004 + blocks)
        self._check(_finite_bf16_codes(blocks * 32, rng).reshape(blocks, 32))

    def test_matches_the_reference_on_the_awkward_blocks(self) -> None:
        """Zero, the extremes, the ties, and one whole exponent sweep.

        A block of all zeros takes the ``6 * 2**-126`` amax floor rather than a
        searched scale, which is the branch a random draw never reaches.
        """
        extremes = [0x0001, 0x0080, 0x7F7F, 0xFF7F, 0x0000, 0x8000]
        ties = [0x3F40, 0x3FC0, 0x4020, 0xBF40]
        rows = [
            [0] * 32,
            list(range(0x3F00, 0x3F20)),
            [0x8000 | code for code in range(0x3F00, 0x3F20)],
            extremes + ties + [0x3F80] * 22,
        ]
        self._check(np.array(rows, dtype=np.uint16))

    def test_matches_the_reference_across_every_binary32_scale(self) -> None:
        """One block per attainable BF16 exponent, driven by its own maximum."""
        rows = []
        for exponent in range(0, 255):
            if exponent == 0xFF:
                continue
            rows.append([((exponent << 7) | ((i * 7) % 128)) for i in range(32)])
            rows.append(
                [0x8000 | ((exponent << 7) | ((i * 13) % 128)) for i in range(32)]
            )
        self._check(np.array(rows, dtype=np.uint16))

    def test_refuses_a_nonfinite_activation_rather_than_scaling_it(self) -> None:
        with pytest.raises(NumericReferenceError):
            _quantize_fp4_qdq_blocks(np.full((1, 32), 0x7F80, dtype=np.uint16))
        with pytest.raises(NumericReferenceError):
            _quantize_fp4_qdq_blocks(np.full((1, 32), 0x7FC0, dtype=np.uint16))
