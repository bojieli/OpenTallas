from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import random
import subprocess

import pytest

from runtime.reference.formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_divide,
    binary32_multiply,
    binary32_ordered_dot,
    binary32_product_add,
    binary32_rsqrt,
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_binary32,
    decode_e2m1,
    decode_e4m3fn,
    decode_e8m0,
    decode_mxfp4_block,
    decode_packed_e2m1,
    encode_binary32_rne,
    encode_e2m1_rne,
    encode_e4m3fn_rne,
    fp8_fp8_block_dot,
    mxfp4_fp8_block_dot,
    quantize_bf16_activation_block,
)


def test_e2m1_exhaustive_table_and_canonical_zero() -> None:
    positive = (
        Fraction(0),
        Fraction(1, 2),
        Fraction(1),
        Fraction(3, 2),
        Fraction(2),
        Fraction(3),
        Fraction(4),
        Fraction(6),
    )
    for code in range(16):
        decoded = decode_e2m1(code)
        magnitude = positive[code & 7]
        expected = -magnitude if code & 8 and magnitude else magnitude
        assert decoded.finite
        assert decoded.value == expected
        assert decoded.zero == (magnitude == 0)
        assert decoded.negative == (expected < 0)

    low, high = decode_packed_e2m1(0x91)
    assert low.value == Fraction(1, 2)
    assert high.value == Fraction(-1, 2)


def test_e2m1_rne_round_trip_ties_and_saturation() -> None:
    for code in range(16):
        decoded = decode_e2m1(code)
        assert decoded.value is not None
        canonical = 0 if decoded.zero else code
        result = encode_e2m1_rne(decoded.value)
        assert result.code == canonical
        assert not result.saturated

    # These are every positive midpoint. The retained significand/code LSB
    # chooses the even endpoint, matching native CUDA E2M1 conversion.
    midpoints = (
        (Fraction(1, 4), 0x0),
        (Fraction(3, 4), 0x2),
        (Fraction(5, 4), 0x2),
        (Fraction(7, 4), 0x4),
        (Fraction(5, 2), 0x4),
        (Fraction(7, 2), 0x6),
        (Fraction(5), 0x6),
    )
    for value, expected in midpoints:
        assert encode_e2m1_rne(value).code == expected
        negative = encode_e2m1_rne(-value)
        assert negative.code == (0 if expected == 0 else expected | 0x8)

    endpoint = encode_e2m1_rne(6)
    assert endpoint.code == 0x7 and not endpoint.saturated
    positive_overflow = encode_e2m1_rne(7)
    assert positive_overflow.code == 0x7 and positive_overflow.saturated
    negative_overflow = encode_e2m1_rne(-7)
    assert negative_overflow.code == 0xF and negative_overflow.saturated


def test_e8m0_all_encodings_are_exact_and_ff_is_reserved() -> None:
    for code in range(0xFF):
        decoded = decode_e8m0(code)
        expected = (
            Fraction(1 << (code - 127), 1)
            if code >= 127
            else Fraction(1, 1 << (127 - code))
        )
        assert decoded.finite
        assert decoded.value == expected
    assert decode_e8m0(0xFF).nan


def test_e4m3fn_exhaustive_classification_and_round_trip() -> None:
    nan_codes = set()
    finite_codes = set()
    for code in range(256):
        decoded = decode_e4m3fn(code)
        if decoded.nan:
            nan_codes.add(code)
            continue
        finite_codes.add(code)
        assert decoded.value is not None
        canonical = 0 if decoded.zero else code
        assert encode_e4m3fn_rne(decoded.value).code == canonical

    assert nan_codes == {0x7F, 0xFF}
    assert len(finite_codes) == 254
    assert decode_e4m3fn(0x7E).value == 448
    assert decode_e4m3fn(0xFE).value == -448
    assert decode_e4m3fn(0x80).zero
    assert not decode_e4m3fn(0x80).negative


def test_e4m3fn_reference_matches_rtl_for_every_encoding(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    bench = tmp_path / "tb_format_decode.sv"
    bench.write_text(
        """`timescale 1ns/1ps
module tb_format_decode;
  reg [3:0] mode = 4'd0;
  reg [15:0] code = 16'b0;
  wire finite, zero, nan, infinity, negative;
  wire signed [31:0] value_q16;
  wire signed [15:0] mantissa;
  wire signed [8:0] exponent;
  integer i;
  ot_format_decode dut(
    .mode(mode), .code(code), .finite(finite), .zero(zero), .nan(nan),
    .infinity(infinity), .negative(negative), .value_q16(value_q16),
    .mantissa(mantissa), .exponent(exponent));
  initial begin
    code = 16'hffff; #1;
    mode = 4'd2;
    for (i = 0; i < 256; i = i + 1) begin
      code = i[15:0]; #1;
      $display("%0d %0d %0d %0d %0d %0d %0d %0d", i, finite, zero,
               nan, infinity, negative, mantissa, exponent);
    end
    $finish;
  end
endmodule
""",
        encoding="ascii",
    )
    executable = tmp_path / "tb_format_decode.vvp"
    compile_result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-Wall",
            "-s",
            "tb_format_decode",
            "-o",
            str(executable),
            str(root / "rtl/ot_format_decode.sv"),
            str(bench),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    run_result = subprocess.run(
        ["vvp", str(executable)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stderr
    rows = [tuple(map(int, line.split())) for line in run_result.stdout.splitlines()]
    assert len(rows) == 256
    for code, finite, zero, nan, infinity, negative, mantissa, exponent in rows:
        expected = decode_e4m3fn(code)
        assert (finite, zero, nan, infinity, negative) == (
            int(expected.finite),
            int(expected.zero),
            int(expected.nan),
            int(expected.infinity),
            int(expected.negative),
        )
        if expected.nan or expected.zero:
            assert (mantissa, exponent) == (0, 0)
        else:
            raw_exponent = (code >> 3) & 0xF
            raw_fraction = code & 0x7
            expected_mantissa = raw_fraction if raw_exponent == 0 else 8 + raw_fraction
            if code & 0x80:
                expected_mantissa = -expected_mantissa
            expected_exponent = -9 if raw_exponent == 0 else raw_exponent - 10
            assert (mantissa, exponent) == (expected_mantissa, expected_exponent)


def test_e4m3fn_round_to_nearest_ties_even_and_saturation() -> None:
    assert encode_e4m3fn_rne(Fraction(1, 1024)).code == 0x00
    assert encode_e4m3fn_rne(Fraction(3, 1024)).code == 0x02
    assert encode_e4m3fn_rne(Fraction(-3, 1024)).code == 0x82
    endpoint = encode_e4m3fn_rne(448)
    assert endpoint.code == 0x7E and not endpoint.saturated
    overflow = encode_e4m3fn_rne(449)
    assert overflow.code == 0x7E and overflow.saturated
    negative_overflow = encode_e4m3fn_rne(-449)
    assert negative_overflow.code == 0xFE and negative_overflow.saturated


def test_bf16_exhaustive_classification() -> None:
    counts = {"zero": 0, "finite": 0, "infinity": 0, "nan": 0}
    for code in range(1 << 16):
        value = decode_bf16(code)
        counts[value.classification] += 1
        if value.zero:
            assert value.value == 0
            assert not value.negative
    assert counts == {
        "zero": 2,
        "finite": 65_278,
        "infinity": 2,
        "nan": 254,
    }
    assert decode_bf16(0x0001).value == Fraction(1, 1 << 133)
    assert decode_bf16(0x3F80).value == 1


def test_binary32_to_bf16_uses_rne_and_saturates_finite_overflow() -> None:
    assert binary32_bits_to_bf16_rne(0x3F800000).code == 0x3F80
    assert binary32_bits_to_bf16_rne(0x3F808000).code == 0x3F80
    assert binary32_bits_to_bf16_rne(0x3F818000).code == 0x3F82
    assert binary32_bits_to_bf16_rne(0x80000000).code == 0x0000
    maximum = binary32_bits_to_bf16_rne(0x7F7FFFFF)
    assert maximum.code == 0x7F7F and maximum.saturated
    with pytest.raises(NumericReferenceError, match="infinity"):
        binary32_bits_to_bf16_rne(0x7F800000)
    with pytest.raises(NumericReferenceError, match="NaN"):
        binary32_bits_to_bf16_rne(0x7FC00000)


def test_binary32_exact_decode_encode_round_trip_and_classification() -> None:
    cases = (
        0x00000000,
        0x80000000,
        0x00000001,
        0x007FFFFF,
        0x00800000,
        0x3F800000,
        0x3F800001,
        0x7F7FFFFF,
        0x80800000,
        0xFF7FFFFF,
    )
    for code in cases:
        decoded = decode_binary32(code)
        assert decoded.finite and decoded.value is not None
        canonical = 0 if decoded.zero else code
        assert encode_binary32_rne(decoded.value) == canonical
    assert decode_binary32(0x7F800000).infinity
    assert decode_binary32(0xFF800000).infinity
    assert decode_binary32(0x7FC00000).nan

    generator = random.Random(0x4F_54_46_33_32)
    checked = 0
    while checked < 20_000:
        code = generator.getrandbits(32)
        decoded = decode_binary32(code)
        if not decoded.finite or decoded.value is None:
            continue
        canonical = 0 if decoded.zero else code
        assert encode_binary32_rne(decoded.value) == canonical
        checked += 1


def test_binary32_rne_covers_subnormal_normal_ties_and_overflow() -> None:
    minimum_subnormal = Fraction(1, 1 << 149)
    assert encode_binary32_rne(minimum_subnormal / 2) == 0
    assert encode_binary32_rne(3 * minimum_subnormal / 2) == 0x00000002
    halfway_above_one = Fraction(1) + Fraction(1, 1 << 24)
    halfway_above_next = Fraction(1) + Fraction(3, 1 << 24)
    assert encode_binary32_rne(halfway_above_one) == 0x3F800000
    assert encode_binary32_rne(halfway_above_next) == 0x3F800002
    maximum = decode_binary32(0x7F7FFFFF).value
    assert maximum is not None
    with pytest.raises(NumericReferenceError, match="overflow"):
        encode_binary32_rne(maximum * 2)


def test_binary32_product_add_rounds_after_each_logical_add() -> None:
    one = Fraction(1)
    half_ulp = Fraction(1, 1 << 24)
    assert binary32_product_add(0x3F800000, half_ulp, one) == 0x3F800000
    assert binary32_product_add(0x3F800001, half_ulp, one) == 0x3F800002
    # Ordered accumulation is intentionally not an exact dot followed by one
    # final rounding: +2^-24 is lost at 1.0 before the later -1.0 arrives.
    result = binary32_ordered_dot(
        (one, half_ulp, -one),
        (one, one, one),
    )
    assert result == 0
    assert decode_binary32(result).value == 0


def test_binary32_scalar_arithmetic_rounds_each_declared_operation() -> None:
    one = encode_binary32_rne(1)
    three = encode_binary32_rne(3)
    one_third = binary32_divide(one, three)
    assert one_third == 0x3EAAAAAB
    assert binary32_multiply(one_third, three) == one
    assert binary32_add(one, one_third) == 0x3FAAAAAB


def test_binary32_rsqrt_is_correctly_rounded_and_fails_closed() -> None:
    assert binary32_rsqrt(0x3F800000) == 0x3F800000
    assert binary32_rsqrt(0x40800000) == 0x3F000000
    assert binary32_rsqrt(0x40000000) == 0x3F3504F3
    assert binary32_rsqrt(0x358637BD) == 0x447A0000
    assert binary32_rsqrt(0x00000001) == 0x64B504F3
    assert binary32_rsqrt(0x7F7FFFFF) == 0x1F800000

    generator = random.Random(0x5253_5152_5433_32)
    previous_input = 0
    previous_result = 0x7F800000
    for _ in range(2_000):
        input_code = generator.randrange(1, 0x7F800000)
        result = binary32_rsqrt(input_code)
        source = decode_binary32(input_code).value
        rounded = decode_binary32(result).value
        assert source is not None and rounded is not None
        assert rounded > 0

        product = source * rounded * rounded
        if product == 1:
            # The target happens to be exactly representable.
            pass
        elif product < 1:
            lower_code = result
            upper_code = result + 1
            lower = rounded
            upper = decode_binary32(upper_code).value
            assert upper is not None
            assert source * upper * upper > 1
            midpoint_product = source * ((lower + upper) / 2) ** 2
            if midpoint_product < 1:
                assert result == upper_code
            elif midpoint_product == 1:
                assert result == (lower_code if lower_code & 1 == 0 else upper_code)
            else:
                assert result == lower_code
        else:
            upper_code = result
            lower_code = result - 1
            upper = rounded
            lower = decode_binary32(lower_code).value
            assert lower is not None
            assert source * lower * lower < 1
            midpoint_product = source * ((lower + upper) / 2) ** 2
            if midpoint_product < 1:
                assert result == upper_code
            elif midpoint_product == 1:
                assert result == (lower_code if lower_code & 1 == 0 else upper_code)
            else:
                assert result == lower_code

        if input_code > previous_input:
            assert result <= previous_result
        previous_input = input_code
        previous_result = result

    for code in (0, 0x80000000, 0xBF800000):
        with pytest.raises(NumericReferenceError, match="must be positive"):
            binary32_rsqrt(code)
    for code in (0x7F800000, 0x7FC00000):
        with pytest.raises(NumericReferenceError, match="NaN or infinity"):
            binary32_rsqrt(code)


def test_binary32_balanced_sum_uses_canonical_tree_not_linear_accumulation() -> None:
    values = (
        0x3F015F4A,
        0x3F3B3BC5,
        0x3E4B0FA0,
        0x3F410971,
        0x3F21E97E,
        0x3F30590C,
    )
    assert binary32_balanced_sum(values) == 0x4060AABC
    linear = values[0]
    for code in values[1:]:
        linear = binary32_add(linear, code)
    assert linear == 0x4060AABD
    assert binary32_balanced_sum((0x80000000,)) == 0x80000000


@pytest.mark.parametrize(
    ("function", "arguments", "match"),
    [
        (binary32_add, (0x7F800000, 0), "NaN or infinity"),
        (binary32_multiply, (0, 0x7FC00000), "NaN or infinity"),
        (binary32_divide, (0x3F800000, 0), "denominator is zero"),
        (binary32_balanced_sum, ((),), "must not be empty"),
        (binary32_balanced_sum, ((0xFF800000,),), "NaN or infinity"),
    ],
)
def test_binary32_scalar_arithmetic_fails_closed(
    function, arguments: tuple, match: str
) -> None:
    with pytest.raises(NumericReferenceError, match=match):
        function(*arguments)


def test_official_routed_mxfp4_fp8_block_dot() -> None:
    # 0x22 expands to two +1 E2M1 values; 0x3f is FP8 +1.875.
    packed_weights = [0x22] * 16
    activations = [0x3F] * 32
    result = mxfp4_fp8_block_dot(
        packed_weights,
        0x7F,
        activations,
        0x7F,
    )
    assert decode_binary32(result).value == 60

    with pytest.raises(NumericReferenceError, match="32 weights"):
        mxfp4_fp8_block_dot([0x22], 0x7F, activations, 0x7F)
    with pytest.raises(NumericReferenceError, match="E4M3FN NaN"):
        mxfp4_fp8_block_dot(packed_weights, 0x7F, [0x7F] * 32, 0x7F)


def test_official_dense_fp8_fp8_block_dot() -> None:
    # Scale weights by 2 and activations by 1/2. Each logical product remains 1.
    ones = [0x38] * 128
    result = fp8_fp8_block_dot(ones, 0x80, ones, 0x7E)
    assert decode_binary32(result).value == 128

    with pytest.raises(NumericReferenceError, match="128 weights"):
        fp8_fp8_block_dot(ones[:-1], 0x7F, ones, 0x7F)
    with pytest.raises(NumericReferenceError, match="reserved E8M0"):
        fp8_fp8_block_dot(ones, 0xFF, ones, 0x7F)


def test_mxfp4_packing_and_scale_follow_official_conversion_order() -> None:
    # Official conversion expands the low nibble first, then the high nibble.
    assert decode_mxfp4_block([0x91], 0x80) == (Fraction(1), Fraction(-1))
    with pytest.raises(NumericReferenceError, match="reserved E8M0"):
        decode_mxfp4_block([0x00], 0xFF)


def test_activation_microscaling_selects_the_smallest_legal_power_of_two() -> None:
    zeros = quantize_bf16_activation_block([0x0000, 0x8000])
    assert zeros.scale_code == 0x7F
    assert zeros.value_codes == (0, 0)
    assert not zeros.saturated

    endpoint = quantize_bf16_activation_block([0x43E0])  # exact BF16 448
    assert endpoint.scale_code == 0x7F
    assert endpoint.value_codes == (0x7E,)

    unit = quantize_bf16_activation_block([0x3F80, 0xBF80])
    assert unit.scale_code == 0x77  # 2^-8; 2^-9 would require magnitude 512
    assert unit.value_codes == (0x78, 0xF8)
    scale = decode_e8m0(unit.scale_code).value
    assert scale is not None
    assert tuple(decode_e4m3fn(code).value * scale for code in unit.value_codes) == (
        Fraction(1),
        Fraction(-1),
    )

    with pytest.raises(NumericReferenceError, match="at least one"):
        quantize_bf16_activation_block([])
    with pytest.raises(NumericReferenceError, match="NaN or infinity"):
        quantize_bf16_activation_block([0x7F80])


@pytest.mark.parametrize(
    ("function", "value"),
    [
        (decode_e2m1, 16),
        (decode_e8m0, 256),
        (decode_e4m3fn, -1),
        (decode_bf16, 1 << 16),
    ],
)
def test_decoders_reject_out_of_range_codes(function, value: int) -> None:
    with pytest.raises(NumericReferenceError):
        function(value)
