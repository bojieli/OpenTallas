"""Exhaustive exact-rational truth vectors for the factored CKV decoder."""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.reference.formats import decode_e4m3fn
from runtime.reference.fp4_kv import dequantize_element_to_fp8, scale_code_is_nonfinite

OUTPUT = ROOT / "tests/fixtures/v41_ckv_selected/decode_pairs.hex"


def generate() -> str:
    lines = []
    for scale in range(256):
        for code in range(16):
            fp8 = 0 if scale_code_is_nonfinite(scale) else dequantize_element_to_fp8(code, scale)[0]
            decoded = decode_e4m3fn(fp8)
            bits = struct.unpack("<I", struct.pack("<f", float(decoded.value)))[0]
            # Both E2M1 and E4M3 signed zero canonicalize to positive zero.
            lines.append(f"{bits if decoded.value else 0:08x}{fp8:02x}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generate())
