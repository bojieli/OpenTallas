"""Bit-exact directed and randomized gate for the O4 INT8 product/row scale.

The oracle is computed in binary64 from exact BF16 and FP32 operands, then
rounded once to binary32.  An INT8 x BF16 product is exact in binary32 for
the ordinary exponent range used here.  The scale corpus also covers FP32
subnormals and halfway rounding cases; the scale pipe handles those by RNE.
"""
from __future__ import annotations

import pathlib
import random
import struct
import subprocess
import tempfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
N = 1024


def as_float(bits: int) -> float:
    return struct.unpack(">f", bits.to_bytes(4, "big"))[0]


def to_bits(value: float) -> int:
    with np.errstate(all="ignore"):
        rounded = np.float32(value)
        bits = struct.unpack(">I", struct.pack(">f", rounded))[0]
        return bits & 0x7FFFFFFF if rounded == 0 else bits


def vectors():
    rng = random.Random(0x04_8B_2026)
    x_directed = [0x0000, 0x8000, 0x3F80, 0xBF80, 0x3F00, 0x4040,
                  0x3F81, 0xBF7F, 0x0080, 0x4F00]
    scales = [0x3F80, 0x3F81, 0x3E80, 0x4000, 0x0080, 0x0001]
    sums = [0x00000000, 0x80000000, 0x3F800001, 0xBF800001,
            0x00000001, 0x007FFFFF, 0x00800000, 0x4B7FFFFF]
    for i in range(N):
        code = i & 255 if i < 256 else rng.randrange(256)
        signed_code = code if code < 128 else code - 256
        x = x_directed[i % len(x_directed)] if i < 256 else ((rng.randrange(100, 151) << 7) | rng.randrange(128) | (rng.randrange(2) << 15))
        scale = scales[i % len(scales)] if i < 256 else ((rng.randrange(70, 160) << 7) | rng.randrange(128))
        sum_bits = sums[i % len(sums)] if i < 256 else ((rng.randrange(1, 200) << 23) | rng.getrandbits(23) | (rng.randrange(2) << 31))
        p = to_bits(signed_code * as_float(x << 16))
        s = to_bits(as_float(sum_bits) * as_float(scale << 16))
        packed = ((((((code << 16) | x) << 32 | p) << 32 | sum_bits) << 16 | scale) << 32 | s)
        yield f"{packed:034x}"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-int8-arith-") as scratch:
        tmp = pathlib.Path(scratch)
        (tmp / "vectors.mem").write_text("\n".join(vectors()) + "\n")
        exe = tmp / "sim"
        sources = [
            ROOT / "rtl/test/tb_hdc_qwen_int8_arith.sv",
            ROOT / "rtl/hdc/ot_hdc_qwen_int8_arith.sv",
            ROOT / "rtl/hdc/ot_hdc_fpu.sv",
            ROOT / "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
        ]
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_arith", "-o", str(exe), *map(str, sources)], check=True)
        completed = subprocess.run(["vvp", str(exe)], cwd=tmp, text=True, capture_output=True)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "QWEN_INT8 checked=1024 errors=0" in completed.stdout, completed.stdout
        assert "PASS" in completed.stdout, completed.stdout
        print(completed.stdout.strip())


if __name__ == "__main__":
    main()
