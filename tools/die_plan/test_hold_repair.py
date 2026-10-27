"""HOLD-REPAIR (METHODOLOGY 12.4a a1, OWNER 10-26): opt-in clock.io_hold = plan_demand -> the receiving kit's min input
delay = sender guarantee - plan-declared seam hold demand; structural gate keeps the option A values; HB4 + buffer cap
GRT hook only in plan_demand kits; legacy / sender_min output unchanged; hold_demand.py estimate + plan fragment."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import hold_demand as H  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _plan(io_hold=None, demand=None):
    raw = copy.deepcopy(PAIR)
    if io_hold:
        raw.setdefault("clock", {})["io_hold"] = io_hold
    if demand is not None:
        raw.setdefault("clock", {})["hold_demand"] = demand
    return schema.Plan(raw)


def test_sender_min_unchanged_by_hold_repair(monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    P = _plan("sender_min")
    tcl = gen_phys.io_hold_tcl(P, "fb")
    assert "OT_IO_HOLD sender_min ports 2" in tcl and "ot_io_hold_apply_demand" not in tcl
    assert "HOLD-REPAIR" not in gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    assert gen_phys.input_hold_min(P, "fb", structural=True) == gen_phys.input_hold_min(P, "fb")


def test_plan_demand_per_port():
    P = _plan("plan_demand", dict(source="plan", pairs={"pfa|pfb": 70.0}))
    fb = gen_phys.input_hold_min(P, "fb")
    assert set(fb) == {"z_i", "x_i"} and all(d["in_min_ps"] == 12.5 - 70.0 for d in fb.values())
    assert "plan hold demand 70" in fb["x_i"]["basis"]
    st = gen_phys.input_hold_min(P, "fb", structural=True)
    assert all(d["in_min_ps"] == 12.5 for d in st.values())
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    assert "HOLD-REPAIR plan_demand" in s and f"set_input_delay -min {-57.5:.4f} -clock vclk" in s
    ctx = sdc_lint.kit_context(P, "fb")
    assert ctx["hold_in_min_ports_ps"] == {"x_i": -57.5, "z_i": -57.5}
    assert sdc_lint.lint(s, **ctx) == []
    tcl = gen_phys.io_hold_tcl(P, "fb")
    st, dm = tcl.split("proc ot_io_hold_apply_demand {vclk}")
    assert "proc ot_io_hold_apply {vclk}" in st and f"set_input_delay -min {12.5:.4f}" in st and "-57.5" not in st
    assert f"set_input_delay -min {-57.5:.4f}" in dm


def test_directed_key_landed_and_errors():
    P = _plan("plan_demand", dict(source="plan", pairs={"pfa>pfb": 90.0, "pfa|pfb": 70.0}))
    assert gen_phys.hold_demand_ps(P, "pfa", "pfb") == 90.0 and gen_phys.hold_demand_ps(P, "pfb", "pfa") == 70.0
    P = _plan("plan_demand", dict(source="plan", landed=["pfa|pfb"]))
    assert gen_phys.input_hold_min(P, "fb") == {} and gen_phys.input_hold_min(P, "fa") == {}
    with pytest.raises(ValueError):                       # measured / unknown source refused
        gen_phys.input_hold_min(_plan("plan_demand", dict(source="plan", pairs={})), "fb")
    raw = copy.deepcopy(PAIR)
    raw.setdefault("clock", {}).update(io_hold="plan_demand", hold_demand=dict(source="plan"))
    raw["clock"]["hold_demand"]["source"] = "measured"
    with pytest.raises(Exception):
        gen_phys.input_hold_min(schema.Plan(raw), "fb")
    with pytest.raises(ValueError):
        gen_phys.input_hold_min(_plan("plan_demand"), "fb")   # no hold_demand block


def test_hold_gate_calls_structural_proc():
    t = (HERE / "hold_gate.tcl").read_text()          # unchanged: its ot_io_hold_apply is the structural view
    assert "ot_io_hold_apply [lindex $vclks 0]" in t
    hook = (HERE / "hold_repair_pre.tcl").read_text()
    assert "grt_pre.tcl" in hook and "hold_pad_hb4.tcl" in hook and "-max_buffer_percent" in hook
    assert gen_phys.HOLD_PAD_HB4.is_file()


def _sl():
    B = dict(setup_tt_ps=631.81, hold_ff_ps=10.88)
    seams = [dict(a="p0", b="p1", cls="region_node", bits_ab=10, bits_ba=6, nc_tt_ps=300.0, nc_ff_ps=250.0),
             dict(a="p1", b="p2", cls="die_root", bits_ab=4, bits_ba=0, nc_tt_ps=6000.0, nc_ff_ps=4900.0)]
    for s in seams:
        s["setup_pess_tt_ps"] = H.pessimism("flat", s["cls"], s["nc_tt_ps"], "TT")
        s["hold_pess_ff_ps"] = H.pessimism("flat", s["cls"], s["nc_ff_ps"], "FF")
    return dict(budgets=B, seams=seams)


def test_hold_demand_estimate_and_fragment(tmp_path):
    p = tmp_path / "sl.json"
    p.write_text(json.dumps(_sl()))
    out = tmp_path / "o"
    assert H.main(["--seam-landing", str(p), "--entry-window-ff", "15", "--entry-window-tt", "4",
                   "--out", str(out)]) == 0
    rec = json.loads((out / "hold_demand.json").read_text())
    r0, r1 = rec["seams"]
    # region_node: D = flat pessimism + 15 + 20 core window; contract pad = 12.28 + 12.5 - (12.5 - D)
    D = H.pessimism("flat", "region_node", 250.0, "FF") + 35.0
    assert abs(r0["demand_ff_ps"] - D) < 0.01 and abs(r0["contract_pad_ps"] - (12.28 + D)) < 0.01
    d_ff = H.HOLD_CELLS["HB4xp67"]["ff_min_ps"] * 0.95
    import math
    assert r0["cells_per_bit"] == math.ceil((12.28 + D) / d_ff) and r0["action"] == "pad"
    assert r1["action"] == "land"                          # die-root seam: hold delay cannot keep TT setup
    s = rec["summary"]["DIE"]
    assert s["hold_cells"] == 16 * r0["cells_per_bit"] and s["bits_land"] == 4
    frag = json.loads((out / "plan_hold_demand.json").read_text())
    assert frag["source"] == "plan" and frag["landed"] == ["p1|p2"] and set(frag["pairs"]) == {"p0|p1"}
    assert frag["pairs"]["p0|p1"] >= r0["demand_ff_ps"]
    # the fragment is a valid plan clock.hold_demand
    raw = copy.deepcopy(PAIR)
    raw.setdefault("clock", {}).update(io_hold="plan_demand", hold_demand=frag)
    schema.Plan(raw)
    # draft AOCV and mesh what-if run and lower the deep-tree demand
    assert H.main(["--seam-landing", str(p), "--entry-window-ff", "15", "--entry-window-tt", "4",
                   "--derate", "aocv_draft", "--out", str(tmp_path / "a")]) == 0
    a1 = json.loads((tmp_path / "a" / "hold_demand.json").read_text())["seams"][1]
    assert a1["demand_ff_ps"] < r1["demand_ff_ps"]
    assert H.main(["--seam-landing", str(p), "--entry-window-ff", "15", "--entry-window-tt", "4",
                   "--mesh-skew-ps", "20", "--out", str(tmp_path / "m")]) == 0
    m = json.loads((tmp_path / "m" / "hold_demand.json").read_text())["seams"]
    assert m[0]["demand_ff_ps"] == m[1]["demand_ff_ps"] and m[1]["action"] == "pad"


def test_census(tmp_path):
    (tmp_path / "k1").mkdir()
    (tmp_path / "k1" / "5_1_grt.log").write_text("OT_HB4PAD: after hold repair the design holds 120 HB4xp67 cells\n")
    c = H.hold_cell_census([tmp_path / "k1"])
    assert c["cells"] == 120 and abs(c["area_um2"] - 12.3) < 0.1
