"""P-STALE-TABLE (QC-INT-R2-TOOLS 11-26): stale_tables equality checks (tap tables, or_groups, tap legality, relay vs bit sites)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stale_tables as ST  # noqa: E402


def _raw():
    ports = {f"clk_t{i}": (float(i), 0.0) for i in range(1, 20)}
    ports["clk"] = (0.0, 0.0)
    t = {"internal_stations": [{"conn": "bus:io_collective__fault", "regs_um": [[121.662, 626.454], [121.662, 973.62]],
                                "or_groups": [{"name": "south", "regs_um": [[121.662, 624.645], [121.662, 973.62]]},
                                              {"name": "north", "regs_um": [[1, 2], [3, 4]]}]}],
         "clock": {}}
    raw = {"die": {"name": "d"}, "partition_types": {"cA4": t},
           "clock": {"tap_window": {"per_port_ps": {"cA4": {p: 60.0 for p in list(ports)[:9]}}}}}
    return raw, {"cA4": (ports, set(), None)}


def test_tap_window_lists_9_of_20():
    raw, ts = _raw()
    lines = ST.findings(raw, ts)
    tl = [x for x in lines if "STALETABLE-TAPTABLE" in x]
    assert len(tl) == 1 and "lists 9 of the type's 20 tap ports" in tl[0] and "11 missing" in tl[0] and tl[0].startswith("WARN")


def test_stale_and_core_ports():
    raw, ts = _raw()
    raw["clock"]["tap_window"]["per_port_ps"]["cA4"] = {**{p: 1.0 for p in ts["cA4"][0]}, "clk_t99": 1.0, "clk_c0": 1.0}
    ts = {"cA4": (ts["cA4"][0], {"clk_c0"}, None)}
    tl = [x for x in ST.findings(raw, ts) if "STALETABLE-TAPTABLE" in x]
    assert len(tl) == 1 and "0 missing" in tl[0] and "1 stale (clk_t99)" in tl[0]       # core tap rows are neither missing nor stale


def test_or_group_regs_and_fix():
    raw, ts = _raw()
    og = [x for x in ST.findings(raw, ts) if "STALETABLE-ORGROUP" in x]
    assert len(og) == 1 and "624.645" in og[0] and "626.454" in og[0]
    assert ST.fix_orgroups(raw) == 1
    assert raw["partition_types"]["cA4"]["internal_stations"][0]["or_groups"][0]["regs_um"] == [[121.662, 626.454], [121.662, 973.62]]
    assert not [x for x in ST.findings(raw, ts) if "STALETABLE-ORGROUP" in x]
    assert raw["partition_types"]["cA4"]["internal_stations"][0]["or_groups"][1]["regs_um"] == [[1, 2], [3, 4]]   # other groups untouched


def test_tap_legality_callback():
    raw, ts = _raw()
    raw["partition_types"]["cA4"]["clock"]["added_taps"] = [{"name": "clk_t41", "xy": [512.992, 415.776]}, {"name": "clk_t42", "xy": [1, 1]}]
    lines = ST.findings(raw, ts, legal=lambda tn, x, y, n: n != "clk_t41")
    tl = [x for x in lines if "STALETABLE-TAPLEGAL" in x]
    assert len(tl) == 1 and "clk_t41=[512.992, 415.776]" in tl[0] and "clk_t42" not in tl[0]


def test_unsolved_grid_reasons():
    raw, _ = _raw()
    l1 = ST.findings(raw, {"cA4": ({}, set(), "ValueError: added tap spacing")})
    assert any(x.startswith("WARN STALETABLE-TAPLEGAL cA4") for x in l1)
    l2 = ST.findings(raw, {"cA4": ({}, set(), "FileNotFoundError: sink bins")})
    assert any("STALETABLE-UNCHECKED" in x for x in l2) and not any("STALETABLE-TAPLEGAL" in x for x in l2)


def test_relay_sites_vs_bit_sites():
    t = {"internal_stations": [{"conn": "bus:b", "bit_sites_um": [[[10.0, 10.0], [11.0, 10.0]], [[500.0, 10.0]]]}],
         "relay_sites": {"u_ist_b_0.q[0]": [10.0, 10.0], "u_ist_b_0.q[1]": [11.0, 10.0], "u_ist_b_1.q[0]": [200.0, 10.0]}}
    rows = ST.relay_bit_rows(t)
    assert len(rows) == 1 and rows[0][0] == "u_ist_b_1.q[0]" and rows[0][3] == 300.0


def test_block_env_and_list_line(monkeypatch):
    raw, ts = _raw()
    lines = ST.findings(raw, ts)
    assert lines[-1].startswith("LIST STALETABLE die d TAPTABLE 1 ORGROUP 1") and "advisory" in lines[-1]
    monkeypatch.setenv("OT_PRE_STALETABLE_BLOCK", "1")
    assert any(x.startswith("FAIL STALETABLE-ORGROUP") for x in ST.findings(copy.deepcopy(raw), ts))


def test_tap_legal_in_macro_halo():
    # Coll_s: macro box y 449.29..530.29 grown by the 8.64 clearance; old C9 clk_t41 inside a moved macro's halo, new seat clean
    boxes = [(319.68, 440.65, 515.59, 538.93)]
    assert not ST.tap_legal_in((786.24, 803.52), 8.64, boxes, 512.992, 445.0)
    assert ST.tap_legal_in((786.24, 803.52), 8.64, boxes, 512.992, 415.776)
    assert ST.tap_legal_in((786.24, 803.52), 8.64, boxes, 504.288, 424.48)          # badd78bdf36b seat
    assert ST.tap_legal_in((786.24, 803.52), 8.64, boxes, 515.59, 480.0)            # on the halo face: legal
    assert not ST.tap_legal_in((786.24, 803.52), 8.64, boxes, 3.0, 100.0)           # outside the clearance ring


def test_legality_covers_solver_taps_not_only_rows():
    raw, ts = _raw()
    ports = dict(ts["cA4"][0], clk_t50=(5.0, 5.0))
    ts = {"cA4": (ports, set(), None)}
    lines = ST.findings(raw, ts, legal=lambda tn, x, y, n: n != "clk_t50")
    tl = [x for x in lines if "STALETABLE-TAPLEGAL" in x]
    assert len(tl) == 1 and "clk_t50=[5.0, 5.0]" in tl[0] and "C-MACRO-TAP-LEGAL" in tl[0]
