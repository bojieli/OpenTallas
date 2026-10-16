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
    c = cal.calendar(100, pv="w1")
    assert c["P1"] == cal.EMPTY_PAIR_OUT and c["P0"] == cal.PAIR_OUT + 100 and c["R"] == c["P0"]


def test_r3_8192_capture_slots():
    c = cal.calendar(8192, pv="w1")
    assert c["R"] == c["P0"] == c["P1"] == cal.R3_8192["R"]


def test_minimal_laws_8192():
    c = cal.calendar(8192, pv="w1")
    assert (c["LMAX"], c["EXP"], c["Z"], c["PV_START"]) == (406, 421, 911, 627)
    assert c["PV_START"] + c["R"] < cal.R3_8192["PV_START"] + cal.R3_8192["R"]   # earlier than the generous r3 calendar


def test_zwalk_block0():
    assert cal.zwalk(1) == 0 and cal.zwalk(8192) == 240 and cal.zwalk(3000) == 90


def test_pv_binds_reciprocal_for_tiny_context():
    c = cal.calendar(1, pv="w1")
    assert c["PV_START"] + c["R"] >= c["HUB_PUB"] + cal.RZ_MARGIN
    with pytest.raises(ValueError):
        cal.check(dict(c, PV_START=c["HUB_PUB"] + cal.RZ_MARGIN - c["R"] - 1))


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


def test_w16_measured_service_cycles():
    # Q-ATTN-RATE: measured on the w16 production binary (results/arch/qwen_attention_rate_1015/receipt.json)
    for T, cyc in [(1, 882), (1000, 943), (4096, 1129), (8192, 1561)]:
        assert cal.service_cycles(cal.calendar(T, pv="w16")) == cyc


def test_w16_pair_out_and_pv_law():
    assert cal.w16_pair_out(8192, 0) == cal.w16_pair_out(8192, 1) == 665
    assert cal.w16_pair_out(100, 1) == 137          # empty pair: tree of the 16 zero-initialised leaves + join
    c = cal.calendar(8192, pv="w16")
    assert c["PV_START"] - c["EXP"] - cal.zwalk(8192) == cal.W16_PV_AFTER_EXP


def test_production_default_is_w16():
    assert cal.calendar(8192) == cal.calendar(8192, pv="w16")
    assert cal.calendar(8192)["P0"] == cal.w16_pair_out(8192, 0)
    assert cal.main(["--ctx", "8192"]) is None
