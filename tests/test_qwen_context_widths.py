"""The Qwen O4 layer program's encoded fields fit the ISA at the product windows (8K and 32K).

The instruction's count fields are 16 bits (hdc_isa N = 16); the core's NW = 18 is its token / position / row
width, not an instruction field (me_row0's high bits ride the fullshape overlay).  At 32K every count and every
24-bit address still encodes (hdc_isa.encode fails closed on an overflow); 128K overflows the 24-bit address.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


@pytest.mark.parametrize("tmax", [8192, 32768])
def test_tp4_layer_program_encodes(tmax, monkeypatch):
    monkeypatch.setenv("QWEN_O4_TP", "4")
    import hdc_qwen_fullshape_program as FP
    monkeypatch.setattr(FP, "TMAX", tmax)
    r = FP.profile(0)
    assert r["kv_window_elems"] <= 1 << 24 and r["vm_elems"] <= 1 << 24


def test_128k_needs_a_wider_address(monkeypatch):
    import hdc_qwen_fullshape_program as FP
    monkeypatch.setattr(FP, "TMAX", 131072)
    with pytest.raises((AssertionError, ValueError)):
        FP.profile(0)
