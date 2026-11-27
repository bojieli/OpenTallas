"""pytest: adv_placed_est on fixtures from the real HEAD W12f misses (R3-RECALL 11-27).
hd_spn_wshim_tx: 8 taps, the seat-reach model read 292 um, OT_TAP_SPAN placed 916 (6 of 8 taps over 300)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_placed_est as A  # noqa: E402

WSHIM_TX = [699.84, 1036.8]
WSHIM_TAPS = [("clk", 241.56, 523.81), ("clk_t1", 17.28, 523.8), ("clk_t2", 520.03, 523.81), ("clk_t3", 351.0, 632.72),
              ("clk_t4", 682.56, 783.0), ("clk_t5", 17.28, 858.6), ("clk_t6", 351.0, 858.6), ("clk_t7", 682.56, 934.2)]
ST_M = [1442.88, 129.6]
ST_M_TAPS = [("clk", 584.35, 96.67), ("clk_t1", 17.28, 38.76), ("clk_t2", 1082.16, 39.53), ("clk_t3", 858.36, 51.36),
             ("clk_t4", 300.0, 70.0), ("clk_t5", 1150.7, 78.75), ("clk_t6", 1425.6, 80.76)]


def raw(name, outline, extra=None):
    t = {"outline_um": outline, "hard": False, "clock": {"tap_mode": "explicit"}}
    t.update(extra or {})
    return {"die": {"name": "s81_head"}, "partition_types": {name: t}}


def test_wshim_tx_span_flagged_where_seat_reach_read_292():
    sp = A.tap_span_est(WSHIM_TX, WSHIM_TAPS)
    assert max(sp.values()) > 300                       # placed 916
    assert sum(1 for v in sp.values() if v > 300) >= 6  # placed 6 of 8
    r = raw("hd_spn_wshim_tx", WSHIM_TX)
    lines = A.findings_by_check["TAP-SPAN-EST"](r, None, taps_of=lambda n, t: WSHIM_TAPS)
    assert lines[0].startswith("WARN ADV-TAP-SPAN-EST") and "hd_spn_wshim_tx" in lines[0]
    assert "summary 1 of 1" in lines[-1]


def test_st_m_flagged_placed_387():
    assert max(A.tap_span_est(ST_M, ST_M_TAPS).values()) > 300


def test_small_tile_dense_taps_not_flagged():
    taps = [(f"clk_t{4 * i + j}", 50.0 + 100 * i, 50.0 + 100 * j) for i in range(4) for j in range(4)]
    r = raw("t", [400.0, 400.0])
    lines = A.findings_by_check["TAP-SPAN-EST"](r, None, taps_of=lambda n, t: taps)
    assert len(lines) == 1 and "summary 0 of 1" in lines[0]


def test_aspect_exact():
    r = {"partition_types": {"a": {"outline_um": [95.04, 1036.8]}, "b": {"outline_um": [1442.88, 475.2]}, "c": {"outline_um": [622.08, 1339.2]}, "d": {"outline_um": [587.52, 518.4]}}}
    lines = A.findings_by_check["ASPECT-EST"](r, None)
    names = [x for x in lines if "summary" not in x]
    assert len(names) == 3 and not any(" d " in x for x in names) and "3 of 4" in lines[-1]   # c is 2.153


def test_origin_pin_leg_wshim_rx():
    t = {"outline_um": [699.84, 1036.8], "clock": {"landing_contract": {"pins": [
        {"name": "cland_fstart_in_link_i", "xy_um": [2.144, 867.232]}, {"name": "cland_tstart_in", "xy_um": [358.048, 858.528]}]}}}
    assert A.origin_pin_legs(t)[0][1] == 364.6
    lines = A.findings_by_check["LEG405-EST"]({"partition_types": {"hd_spn_wshim_rx": t}}, None)
    assert "hd_spn_wshim_rx" in lines[0] and "summary 1 types" in lines[-1]


def test_origin_pin_leg_silent_when_reader_start_staged():
    t = {"outline_um": [700.0, 1000.0], "clock": {"landing_reader_start": {"branches": {}}, "landing_contract": {"pins": [
        {"name": "cland_fstart_in_a", "xy_um": [2.0, 867.0]}, {"name": "cland_tstart_in", "xy_um": [358.0, 858.0]}]}}}
    assert A.origin_pin_legs(t) == []
