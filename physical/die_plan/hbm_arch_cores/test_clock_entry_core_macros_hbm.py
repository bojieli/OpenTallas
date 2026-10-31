"""AUTOBUILD-PIPE-2 10-31 (KIT-WAVE-3 00:46: every d44f core_kit kit failed kit preflight): opt-in --clock-pin-entry
(clock-class M5 plan pins at their plan point / face, 0.048 x 0.48, centre on the M5 track) and --core-macros auto
(plan core_macros.json KNOWN rects -> static macro placement; none -> PLAN_CORE_MACROS)."""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_centry", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))

W, H = 345.6, 518.4
M5 = (0.024, 0.048)
PINS = [dict(name="clk", layer="M5", x=172.776, y=259.2),           # hnx_fused_lane interior centre entry (12.8a)
        dict(name="ck_n", layer="M5", x=630.6 - 400, y=518.4),      # N face, unsized
        dict(name="clk_w", layer="M5", x=0.0, y=51.84),             # W face, unsized (svc_vmdel_lane_n form)
        dict(name="clk_e", layer="M5", x=W, y=90.72),               # E face
        dict(name="d[0]", layer="M4", x=0.0, y=2.424)]
CE = dict(names={"clk", "ck_n", "clk_w", "clk_e"}, m5=M5)


def _io(io):
    out = {}
    for m in re.finditer(r"place_pin -pin_name \{([^}]*)\} -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}", io):
        out[m.group(1)] = (m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)))
    return out


def on_track(x):
    k = (x - M5[0]) / M5[1]
    return abs(k - round(k)) < 1e-6


def test_off_is_byte_identical():
    assert coregen.io_tcl(PINS, W, H, "t") == coregen.io_tcl(PINS, W, H, "t", clock_entry=None)
    io, _ = coregen.io_tcl(PINS, W, H, "t")
    assert _io(io)["clk"][1:3] == (0.096, 259.2)        # the old nearest-face projection (the preflight FAIL)


def test_every_clock_pin_passes_geometry_and_stays_at_its_plan_point():
    io, rows = coregen.io_tcl(PINS, W, H, "t", clock_entry=CE)
    p = _io(io)
    for n in CE["names"]:
        layer, x, y, sx, sy = p[n]
        assert layer == "M5" and sx >= 0.048 - 1e-9 and sy >= 0.48 - 1e-9 and on_track(x), (n, p[n])
        assert x - sx / 2 >= -1e-9 and x + sx / 2 <= W + 1e-9 and y - sy / 2 >= -1e-9 and y + sy / 2 <= H + 1e-9
    assert p["clk"][1:3] == (172.776, 259.2)                       # interior entry kept (already on track)
    assert p["ck_n"][2] == round(H - 0.24, 4)                      # N face, touching it
    assert abs(p["clk_w"][1] - p["clk_w"][3] / 2) < 1e-9           # W face, touching x = 0
    assert abs(p["clk_e"][1] + p["clk_e"][3] / 2 - W) < 1e-9       # E face, touching x = W
    assert p["d[0]"] == _io(coregen.io_tcl(PINS, W, H, "t")[0])["d[0]"]   # non-clock pins unchanged


def test_plan_pin_records_equal_io_centres():
    io, rows = coregen.io_tcl(PINS, W, H, "t", clock_entry=CE)
    recs, cen = coregen.plan_pin_records(rows), _io(io)
    for n, r in recs.items():
        assert abs(r["x"] - cen[n][1]) < 1e-4 and abs(r["y"] - cen[n][2]) < 1e-4, (n, r, cen[n])
    assert next(r for r in rows if r["bus"] == "clk")["face"] == "I"


def test_off_track_plan_x_snaps_to_nearest_track():
    cx, cy, size, f = coregen.clock_entry_pin(dict(x=100.03, y=50.0), 200.0, 100.0, M5)
    assert f is None and on_track(cx) and abs(cx - 100.03) <= 0.024 + 1e-9 and cy == 50.0


def _cm(tmp_path, entry):
    p = tmp_path / "core_macros.json"
    p.write_text(json.dumps(dict(cores={"mod": entry})))
    return p


def test_core_macros_known_rects_become_the_placement(tmp_path):
    p = _cm(tmp_path, dict(status="KNOWN", macros=[
        dict(name="u_fcore.g_t[0].u_m", master="sram", rect_um=[21.6, 170.46, 116.424, 211.524]),
        dict(name="pc[1].u_payload", rect_um=[30.24, 58.572, 125.064, 99.6])]))
    rows, src = coregen.core_macros_placement(p, "mod", ["sram"])
    assert rows == [dict(inst="g_t[0].u_m", xy_um=[21.6, 170.46], orient="R0", macro="sram"),
                    dict(inst="pc[1].u_payload", xy_um=[30.24, 58.572], orient="R0", macro="sram")]
    assert src["status"] == "KNOWN" and src["module"] == "mod"


def test_no_macros_no_placement(tmp_path):
    assert coregen.core_macros_placement(tmp_path / "absent.json", "mod", []) is None


@pytest.mark.parametrize("entry", [dict(status="UNKNOWN", macros=[]), None])
def test_macro_core_without_known_rects_is_plan(tmp_path, entry):
    p = _cm(tmp_path, entry) if entry else tmp_path / "absent.json"
    with pytest.raises(SystemExit, match="PLAN_CORE_MACROS mod"):
        coregen.core_macros_placement(p, "mod", ["sram"])


def test_hard_child_rects_are_not_kit_macros(tmp_path):
    p = _cm(tmp_path, dict(status="KNOWN", macros=[
        dict(name="u_lane0", master="hnx_lane_x", rect_um=[0, 0, 50, 50]),
        dict(name="u_lf0.g_xm\\[3\\].u_x", master="sram", rect_um=[60, 0, 100, 40])]))
    rows, src = coregen.core_macros_placement(p, "mod", ["sram"])
    assert [r["inst"] for r in rows] == ["u_lf0.g_xm\\[3\\].u_x"] and src["not_kit_macros"] == ["u_lane0:hnx_lane_x"]
    p = _cm(tmp_path, dict(status="KNOWN", macros=[dict(name="u_lane0", master="hnx_lane_x", rect_um=[0, 0, 5, 5])]))
    with pytest.raises(SystemExit, match="PLAN_CORE_MACROS mod: plan core_macros.json KNOWN rects name no kit macro"):
        coregen.core_macros_placement(p, "mod", ["sram"])


# DIE-HBM-48 10-31: the plan clock entry (clock_entries.json) is the clock pin location (12.8a)
def _ce(tmp_path, entries):
    p = tmp_path / "clock_entries.json"
    p.write_text(json.dumps(entries))
    return p


def test_plan_entry_moves_face_clock_to_centre(tmp_path):
    p = _ce(tmp_path, {"q_hub_nw": {"u_dec": dict(module="mod", xy_um=[129.6, 129.6], port="clk", merged_clock_ports=[])},
                       "q_hub_ne": {"u_dec": dict(module="mod", xy_um=[129.6, 129.6], port="clk", merged_clock_ports=[])},
                       "x": {"u_o": dict(module="other", xy_um=[5.0, 5.0], port="clk")}})
    moved, rec = coregen.plan_clock_entries(p, "mod", ["clk"], 260.0, 260.0, M5)
    assert moved == {"clk": (129.624, 129.6)} and on_track(moved["clk"][0]) and rec["pins"] == 1
    pins = [dict(name="clk", layer="M5", x=69.336, y=0.24, w=0.048, h=0.48)]
    pins = [dict(q, x=moved[q["name"]][0], y=moved[q["name"]][1]) for q in pins]
    io, rows = coregen.io_tcl(pins, 260.0, 260.0, "t", clock_entry=dict(names={"clk"}, m5=M5))
    assert _io(io)["clk"][1:3] == (129.624, 129.6) and rows[0]["face"] == "I"


def test_plan_entry_merged_ports_spread_on_every_second_track(tmp_path):
    names = ["writer_clk_bank0", "writer_clk_body", "vmasm_clk[0]", "vmasm_clk[1]", "vmasm_clk[2]"]
    p = _ce(tmp_path, {"h": {"u_vm": dict(module="vm", xy_um=[462.24, 254.88], port=None,
                                           merged_clock_ports=["vmasm_clk", "writer_clk_bank0", "writer_clk_body"])}})
    moved, rec = coregen.plan_clock_entries(p, "vm", names + ["other_clk"], 924.48, 509.76, M5)
    assert sorted(moved) == sorted(names) and rec["pins"] == 5
    xs = sorted(x for x, _ in moved.values())
    assert all(abs((b - a) - 0.096) < 1e-6 for a, b in zip(xs, xs[1:])) and all(on_track(x) for x in xs)
    assert min(xs) <= 462.24 <= max(xs) and {y for _, y in moved.values()} == {254.88}


def test_plan_entry_absent_or_conflicting(tmp_path):
    assert coregen.plan_clock_entries(tmp_path / "none.json", "mod", ["clk"], 100.0, 100.0, M5) == ({}, None)
    p = _ce(tmp_path, {"a": {"u0": dict(module="other", xy_um=[50.0, 50.0], port="clk")}})
    assert coregen.plan_clock_entries(p, "mod", ["clk"], 100.0, 100.0, M5) == ({}, None)
    p = _ce(tmp_path, {"a": {"u0": dict(module="mod", xy_um=[50.0, 50.0], port="clk")},
                       "b": {"u1": dict(module="mod", xy_um=[40.0, 50.0], port="clk")}})
    with pytest.raises(SystemExit, match="CLOCK_ENTRY_CONFLICT"):
        coregen.plan_clock_entries(p, "mod", ["clk"], 100.0, 100.0, M5)
