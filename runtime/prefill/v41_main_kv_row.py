"""OpenTallas released-width DeepSeek V4.1 main-KV row boundary.

This versioned image places 512 low-nibble-first E2M1 codes before 32 E4M3FN
scale bytes. The constituent tensors and nibble order are pinned; concatenation
is this profile's choice, not a claim about a vendor interconnect. This module
accepts already-quantized rows and never infers a forward quantizer from the
vendor's reconstructed BF16 cache values.
"""

from dataclasses import dataclass

from runtime.reference.fp4_kv import dequantize_to_fp8, scale_code_is_nonfinite


PROFILE = "opentallas.deepseek_v41.main_fp4_e2m1_s16_e4m3.row.v1"
ELEMENTS = 512
GROUP = 16
CODE_BYTES = ELEMENTS // 2
SCALE_BYTES = ELEMENTS // GROUP
ROW_BYTES = CODE_BYTES + SCALE_BYTES


@dataclass(frozen=True)
class MainKVRow:
    packed: bytes
    e2m1_codes: tuple[int, ...]
    scale_codes: tuple[int, ...]
    fp8_codes: bytes
    saturation_count: int


def pack_main_row(codes, scales):
    """Pack explicit already-quantized codes; low nibble is the earlier element."""
    if len(codes) != ELEMENTS or len(scales) != SCALE_BYTES:
        raise ValueError("main KV row requires 512 codes and 32 scales")
    if any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < 16 for c in codes):
        raise ValueError("E2M1 code is not a 4-bit integer")
    if any(isinstance(s, bool) or not isinstance(s, int) or not 0 <= s < 256
           or scale_code_is_nonfinite(s) for s in scales):
        raise ValueError("E4M3 scale is invalid or nonfinite")
    packed = bytes(codes[2 * i] | (codes[2 * i + 1] << 4) for i in range(CODE_BYTES))
    return packed + bytes(scales)


def parse_main_row(data):
    """Validate the released-width row, then decode each element to FP8."""
    if not isinstance(data, bytes) or len(data) != ROW_BYTES:
        raise ValueError("main KV row must be exactly 288 bytes")
    codes = tuple(v for byte in data[:CODE_BYTES] for v in (byte & 15, byte >> 4))
    scales = tuple(data[CODE_BYTES:])
    if any(scale_code_is_nonfinite(s) for s in scales):
        raise ValueError("main KV row contains a nonfinite E4M3 scale")
    decoded = dequantize_to_fp8(codes, scales, group=GROUP)
    return MainKVRow(data, codes, scales, bytes(decoded.fp8_codes), decoded.saturation_count)
