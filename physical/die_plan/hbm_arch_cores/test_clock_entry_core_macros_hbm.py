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
