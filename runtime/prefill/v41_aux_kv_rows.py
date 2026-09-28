"""OpenTallas released-width V4.1 index-key and window-row profiles.

The code/scale concatenation and index nibble order are versioned OpenTallas
choices, not vendor DMA-layout claims. Decoding returns exact rational products
without assuming a destination rounding mode or HBM address.
"""

from dataclasses import dataclass
from fractions import Fraction

from runtime.reference.formats import decode_e2m1, decode_e4m3fn, decode_e8m0


INDEX_PROFILE = "opentallas.deepseek_v41.index_fp4_e2m1_s32_e8m0.row.v1"
WINDOW_PROFILE = "opentallas.deepseek_v41.window_fp8_e4m3_s32_e8m0.row.v1"
INDEX_ELEMENTS, WINDOW_ELEMENTS, GROUP = 128, 512, 32
INDEX_CODE_BYTES, INDEX_SCALE_BYTES, INDEX_ROW_BYTES = 64, 4, 68
WINDOW_CODE_BYTES, WINDOW_SCALE_BYTES, WINDOW_ROW_BYTES = 512, 16, 528


@dataclass(frozen=True)
class ScaledRow:
    packed: bytes
    codes: tuple[int, ...]
    scales: tuple[int, ...]
    exact_values: tuple[Fraction, ...]


def _validate_codes(codes, width, bits, name):
    if len(codes) != width or any(isinstance(c, bool) or not isinstance(c, int)
                                  or not 0 <= c < (1 << bits) for c in codes):
        raise ValueError(f"{name} requires {width} unsigned {bits}-bit codes")


def _validate_scales(scales, width):
    if len(scales) != width or any(isinstance(s, bool) or not isinstance(s, int)
                                   or not 0 <= s < 255 for s in scales):
        raise ValueError(f"row requires {width} finite E8M0 scales; 0xff is reserved")


def pack_index_row(codes, scales):
    _validate_codes(codes, INDEX_ELEMENTS, 4, "index row")
    _validate_scales(scales, INDEX_SCALE_BYTES)
    return bytes(codes[2 * i] | (codes[2 * i + 1] << 4) for i in range(INDEX_CODE_BYTES)) + bytes(scales)


def parse_index_row(data):
    if not isinstance(data, bytes) or len(data) != INDEX_ROW_BYTES:
        raise ValueError("index row must be exactly 68 bytes")
    codes = tuple(n for byte in data[:INDEX_CODE_BYTES] for n in (byte & 15, byte >> 4))
    scales = tuple(data[INDEX_CODE_BYTES:])
    _validate_scales(scales, INDEX_SCALE_BYTES)
    values = tuple(decode_e2m1(c).value * decode_e8m0(scales[i // GROUP]).value
                   for i, c in enumerate(codes))
    return ScaledRow(data, codes, scales, values)


def pack_window_row(codes, scales):
    _validate_codes(codes, WINDOW_ELEMENTS, 8, "window row")
    if any((c & 0x7F) == 0x7F for c in codes):
        raise ValueError("window E4M3 code is nonfinite")
    _validate_scales(scales, WINDOW_SCALE_BYTES)
    return bytes(codes) + bytes(scales)


def parse_window_row(data):
    if not isinstance(data, bytes) or len(data) != WINDOW_ROW_BYTES:
        raise ValueError("window row must be exactly 528 bytes")
    codes = tuple(data[:WINDOW_CODE_BYTES])
    if any((c & 0x7F) == 0x7F for c in codes):
        raise ValueError("window E4M3 code is nonfinite")
    scales = tuple(data[WINDOW_CODE_BYTES:])
    _validate_scales(scales, WINDOW_SCALE_BYTES)
    values = tuple(decode_e4m3fn(c).value * decode_e8m0(scales[i // GROUP]).value
                   for i, c in enumerate(codes))
    return ScaledRow(data, codes, scales, values)
