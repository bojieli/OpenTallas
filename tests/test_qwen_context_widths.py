"""The Qwen O4 layer program's encoded fields fit the ISA at the product windows.

The instruction's count fields are 16 bits (hdc_isa N = 16); the core's NW = 18 is its token / position / row
width, not an instruction field (me_row0's high bits ride the fullshape overlay).  The 24-bit address holds the
layer's KV window 2 * (8 / TP) * T * 128 elements: at TP-4 (the product) up to 32K, at TP-2 up to 16K.
hdc_isa.encode fails closed on an overflow.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


@pytest.mark.parametrize("tmax", [8192, 32768, 131072])
def test_layer_program_encodes_iff_the_kv_window_fits_24_bits(tmax, monkeypatch):
    import hdc_qwen_fullshape_program_w12 as FP
    monkeypatch.setattr(FP, "TMAX", tmax)
    fits = 2 * (8 // FP.TP) * tmax * 128 <= 1 << 24
    if fits:
        r = FP.profile(0)
        assert r["kv_window_elems"] <= 1 << 24 and r["vm_elems"] <= 1 << 24
    else:
        with pytest.raises((AssertionError, ValueError)):
            FP.profile(0)
