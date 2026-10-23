"""FT-KV2 10-23: OT_KV_AHUB_MEASURE -- natural post-station hub ages -> AP_OFS / FR_OFS (kv_static_die.ahub_ages formulas),
off by default and never active together with the fixed-offset pad flow (OT_KV_AHUB_PAD=1)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kv_bundle_eq as KBE   # noqa: E402
import kv_fwd_lanes as FL    # noqa: E402


def test_offsets_match_ahub_check(monkeypatch):
    # gen_r1200 try3 final netlist ages (fail_logs_r1200/fwd_lanes.log)
    ages = dict(ks_ahs=41, ks_ahfr=0, ks_pvfst=35, ap_WS=3, ap_WN=3, ap_ES=4, ap_EN=8)
    o = FL.ahub_measure_offsets(ages)
    assert o['AP_OFS'] == [-36, -36, -35, -31] and o['FR_OFS'] == -7
    assert KBE.ahub_check(ages, o) == []               # a hub hardened at these offsets needs no pad on this table
    assert o['AP_OFS_hex'] == "{16'hffe1, 16'hffdd, 16'hffdc, 16'hffdc}"


def test_measure_knob(monkeypatch):
    monkeypatch.delenv('OT_KV_AHUB_MEASURE', raising=False)
    monkeypatch.delenv('OT_KV_AHUB_PAD', raising=False)
    assert not FL.ahub_measure_on()
    monkeypatch.setenv('OT_KV_AHUB_MEASURE', '1')
    assert FL.ahub_measure_on()
    monkeypatch.setenv('OT_KV_AHUB_PAD', '1')
    assert not FL.ahub_measure_on()                     # the pad flow owns the hub ages then
