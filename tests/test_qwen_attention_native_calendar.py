"""Per-context compiler calendar of the static native Qwen TP8 attention service (Q-VMWB 2026-10-15)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("attn_calendar", ROOT / "tools/qwen_attention_native/attn_calendar.py")
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)


def test_measured_lmax_points():
    # minimal exact LMAX measured on the production binary (fix_r3 RL21/HXK8)
    for T, L in [(1, 151), (1024, 182), (2048, 214), (4096, 278), (8192, 406)]:
        assert cal.lmax_min(T) == L


def test_lmax_is_qk_pass_not_t_over_32():
    # ns > 1024 rows/stack scan the 2048-slot ECTL order: 6144 is not 150 + 6144/32
    assert cal.lmax_min(6144) == 374
    assert cal.lmax_min(5000) == 358


def test_pairs_and_empty_pair():
    assert cal.pair_rows(1) == [1, 0]
    assert cal.pair_rows(8192) == [4096, 4096]
    c = cal.calendar(100)
    assert c["P1"] == cal.EMPTY_PAIR_OUT and c["P0"] == cal.PAIR_OUT + 100 and c["R"] == c["P0"]


def test_r3_8192_capture_slots():
    c = cal.calendar(8192)
    assert c["R"] == c["P0"] == c["P1"] == cal.R3_8192["R"]


@pytest.mark.parametrize("T", [1, 127, 128, 129, 511, 512, 513, 3000, 6145, 8191, 8192])
def test_every_context_passes_leaf_rules(T):
    c = cal.calendar(T)
    cal.check(c)
    assert len(cal.hexcal(c)) == 44


def test_rules_refuse():
    c = cal.calendar(1000)
    with pytest.raises(ValueError):
        cal.check(dict(c, Z=c["LMAX"] + 3))
    with pytest.raises(ValueError):
        cal.check(dict(c, EXP=32))
    with pytest.raises(ValueError):
        cal.calendar(0)
    with pytest.raises(ValueError):
        cal.calendar(8193)
