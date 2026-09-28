"""Bit-exact tests for the prefill KV binary32/BF16 to E4M3FN converter."""

import math
import random
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

import pytest


RTL = Path(__file__).resolve().parents[1] / "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv"


def _positive_e4m3():
    values = []
    for code in range(0x7F):  # 0x7F is NaN, 0x7E is maximum finite
        exp, frac = (code >> 3) & 15, code & 7
        value = frac * 2.0**-9 if exp == 0 else (1 + frac / 8) * 2.0 ** (exp - 7)
        values.append((value, code))
    return values


E4 = _positive_e4m3()


def _reference(bits):
    """Choose the nearest finite E4M3 value; ties use the even mantissa bit."""
    sign = bits >> 31
    value = struct.unpack("<f", struct.pack("<I", bits))[0]
    if math.isnan(value) or math.isinf(value):
        return (sign << 7) | 0x7E
    magnitude = abs(value)
    if magnitude >= 448:
        return (sign << 7) | 0x7E
    _, code = min(E4, key=lambda pair: (abs(pair[0] - magnitude), pair[1] & 1))
    return 0 if code == 0 else (sign << 7) | code


@pytest.mark.skipif(not shutil.which("iverilog") or not shutil.which("vvp"), reason="Icarus Verilog unavailable")
def test_fp8q_exhaustive_bf16_and_fp32_boundaries():
    random_bits = random.Random(0xE4A3)
    vectors = [n << 16 for n in range(65536)]  # every BF16 encoding, including NaNs
    vectors += [random_bits.getrandbits(32) for _ in range(4096)]
    # Binary32 neighbours of every representable E4M3 midpoint exercise RNE.
    for (lo, _), (hi, _) in zip(E4, E4[1:]):
        midpoint = (lo + hi) / 2
        mid_bits = struct.unpack("<I", struct.pack("<f", midpoint))[0]
        for bits in (mid_bits - 1, mid_bits, mid_bits + 1):
            vectors.extend((bits, bits | 0x80000000))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        (path / "vectors.hex").write_text("".join(f"{bits:08x}\n" for bits in vectors))
        (path / "tb.sv").write_text(
            "module tb;\n"
            f"  reg [31:0] vec [0:{len(vectors)-1}];\n"
            "  reg [31:0] f; wire [7:0] q; integer i;\n"
            "  ot_hdc_ingest_fp8q dut(.f(f), .q(q));\n"
            "  initial begin\n"
            "    $readmemh(\"vectors.hex\", vec);\n"
            f"    for (i=0; i<{len(vectors)}; i=i+1) begin\n"
            "      f=vec[i]; #1; $display(\"%02x\", q);\n"
            "    end\n"
            "    $finish;\n"
            "  end\n"
            "endmodule\n"
        )
        subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", "sim", str(RTL), "tb.sv"], cwd=path, check=True)
        output = subprocess.run(["vvp", "sim"], cwd=path, check=True, capture_output=True, text=True).stdout
    codes = [int(line, 16) for line in output.splitlines()]
    assert len(codes) == len(vectors)
    for index, (bits, got) in enumerate(zip(vectors, codes)):
        expected = _reference(bits)
        assert got == expected, f"vector {index}: binary32 0x{bits:08x}, got 0x{got:02x}, expected 0x{expected:02x}"
