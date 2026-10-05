"""Released-width V4.1 main-KV row acceptance and exact decode checks."""

import random

import pytest

from runtime.prefill import v41_main_kv_row as R
from runtime.reference import fp4_kv as F


def test_row_low_nibble_order_and_exact_reference_expansion():
    rng = random.Random(0xD541)
    codes = [rng.randrange(16) for _ in range(R.ELEMENTS)]
    scales = [rng.choice((0x08, 0x20, 0x38, 0x50, 0x7E, 0x88, 0xB8)) for _ in range(R.SCALE_BYTES)]
    packed = R.pack_main_row(codes, scales)
    assert len(packed) == 288 and packed[0] == codes[0] | codes[1] << 4
    assert packed[256:] == bytes(scales)
    row = R.parse_main_row(packed)
    assert row.e2m1_codes == tuple(codes)
    assert row.scale_codes == tuple(scales)
    ref = F.dequantize_to_fp8(codes, scales, group=16)
    assert row.fp8_codes == bytes(ref.fp8_codes)
    assert row.saturation_count == ref.saturation_count
    assert R.pack_main_row(row.e2m1_codes, row.scale_codes) == packed


def test_invalid_rows_fail_closed():
    base = R.pack_main_row([0] * 512, [0x38] * 32)
    with pytest.raises(ValueError, match="288"):
        R.parse_main_row(base[:-1])
    with pytest.raises(ValueError, match="nonfinite"):
        R.parse_main_row(base[:256] + bytes([0x7F]) + base[257:])
    with pytest.raises(ValueError, match="512"):
        R.pack_main_row([0] * 511, [0x38] * 32)
    with pytest.raises(ValueError, match="4-bit"):
        R.pack_main_row([16] + [0] * 511, [0x38] * 32)
    with pytest.raises(ValueError, match="nonfinite"):
        R.pack_main_row([0] * 512, [0xFF] + [0x38] * 31)
