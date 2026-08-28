from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess

import pytest

from runtime.reference.formats import (
    NumericReferenceError,
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_e2m1,
    decode_e4m3fn,
    decode_e8m0,
    decode_mxfp4_block,
    decode_packed_e2m1,
    encode_e4m3fn_rne,
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
