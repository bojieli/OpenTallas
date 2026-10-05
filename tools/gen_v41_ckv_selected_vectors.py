"""Deterministic selected compressed-KV RTL vectors from the row reference."""
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.prefill.v41_main_kv_row import pack_main_row, parse_main_row
from runtime.reference.formats import decode_e4m3fn

FIX = ROOT / "tests/fixtures/v41_ckv_selected"


def generate() -> tuple[str, str, str]:
    rng = random.Random(0xC4C5E1)
    sectors = []
    expected = []
    expected_fp32 = []
    for row in range(2):
        codes = [rng.randrange(16) for _ in range(512)]
        scales = [rng.choice((0x00, 0x01, 0x08, 0x20, 0x38, 0x50,
                              0x7e, 0x80, 0x88, 0xb8, 0xfe)) for _ in range(32)]
        # All finite code/scale combinations, signed zero, subnormal and
        # saturation are present in the exhaustive generated decoder table.
        codes[:16] = list(range(16))
        scales[0] = 0x7e if row == 0 else 0x80
        packed = pack_main_row(codes, scales)
        parsed = parse_main_row(packed)
        assert parsed.saturation_count > 0 or row == 1
        for s in range(9):
            sectors.append(packed[s*32:(s+1)*32][::-1].hex())
        expected.extend(f"{code:02x}" for code in parsed.fp8_codes)
        for code in parsed.fp8_codes:
            d = decode_e4m3fn(code)
            bits = struct.unpack("<I", struct.pack("<f", float(d.value)))[0]
            expected_fp32.append(f"{bits if d.value else 0:08x}")
    return ("\n".join(sectors) + "\n", "\n".join(expected) + "\n",
            "\n".join(expected_fp32) + "\n")


if __name__ == "__main__":
    FIX.mkdir(parents=True, exist_ok=True)
    a, b, c = generate()
    (FIX / "sectors.hex").write_text(a)
    (FIX / "expected_fp8.hex").write_text(b)
    (FIX / "expected_fp32.hex").write_text(c)
