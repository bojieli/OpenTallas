#!/usr/bin/env python3
"""Bit-exact directed gate for the INT8 embedding code × BF16 row scale."""
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv"
TB = ROOT / "rtl/test/tb_hdc_qwen_int8_embed_decode.sv"


def bits32(value):
    return struct.unpack("<I", struct.pack("<f", float(value)))[0]


def vector(code, scale):
    exp = (scale >> 7) & 255
    sc = np.float32(struct.unpack("<f", struct.pack("<I", scale << 16))[0])
    with np.errstate(over="ignore"):
        result = np.float32(np.asarray(code, dtype=np.uint8).view(np.int8).item()) * sc
    fault = int(exp in (0, 255) or (code != 0 and not np.isfinite(result)))
    value = 0 if code == 0 or fault else bits32(result)
    return (fault << 56) | (value << 24) | (code << 16) | scale


def main():
    # Every code at several real, normal scales, plus the fail-closed inputs.
    scales = (0x3f00, 0x3f80, 0x3f90, 0x3b80, 0x4300, 0x0080, 0x7f00)
    cases = [(code, scale) for scale in scales for code in range(256)]
    cases += [(0, 0), (1, 0), (127, 0x7f7f), (255, 0x7f80)]
    with tempfile.TemporaryDirectory(prefix="qwen_embed_decode_") as dirname:
        tmp = Path(dirname)
        vec = tmp / "vectors.hex"
        vec.write_text("".join(f"{vector(c, s):015x}\n" for c, s in cases))
        binary = tmp / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_embed_decode",
                        "-o", str(binary), str(RTL), str(TB)], check=True)
        run = subprocess.run(["vvp", str(binary), f"+VEC={vec}", f"+N={len(cases)}"],
                             capture_output=True, text=True)
        print(run.stdout.strip())
        if run.returncode:
            raise RuntimeError(run.stderr.strip() or "embedding decode RTL failed")


if __name__ == "__main__":
    main()
