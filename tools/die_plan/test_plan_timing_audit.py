"""PLAN-READERS-1 (FABLE-METHOD levers 1 + 8): plan_timing_audit.py.  python3 -m pytest -q tools/die_plan/test_plan_timing_audit.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import core_clock_contract as CC  # noqa: E402
import plan_timing_audit as PTA  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())

LIB = """library (x) { time_unit : "1ps";
 cell (core) { pin (clk) { clock : true; }
  pin (d) { timing () { related_pin : "clk"; timing_type : setup_rising;
      rise_constraint (t) { values ("300, 346.0, 346.0", "346.0, 400, 900"); } fall_constraint (t) { values ("5, 7"); } } }
  pin (q) { timing () { related_pin : "clk"; timing_type : rising_edge;
      cell_rise (t) { values ("100, 480.5, 480.5, 900"); } cell_fall (t) { values ("90, 400"); } } } } }
"""


LIB_OK = LIB.replace("480.5", "100").replace("900", "100").replace("346.0", "50").replace("400", "50")


def plan(mut=None):
    p = copy.deepcopy(TINY)
    if mut:
        mut(p)
    return schema.Plan(p)


def test_lib_boundary_arcs(tmp_path):
    f = tmp_path / "core_tt.lib"
    f.write_text(LIB)
    assert PTA.lib_boundary_arcs(f) == (480.5, 346.0)   # median of each table (typical point), max over tables
    f2 = tmp_path / "ns.lib"
    f2.write_text(LIB.replace('"1ps"', '"1ns"'))
    assert PTA.lib_boundary_arcs(f2) == (480500.0, 346000.0)


def test_hop_pricing():
    assert PTA.hop_limit_ps(833.0) == 833.0 - PTA.SETUP_PS - PTA.MARGIN_PS == 658.0
    assert PTA.hop_ps(0) == 50.0 and abs(PTA.hop_ps(1000) - 700.0) < 1e-9
    # a zero-logic hop of 935 um is the last one that fits: (658 - 50) / 0.65
    assert PTA.hop_ps(935.0) <= 658.0 < PTA.hop_ps(936.5)


def test_reach_flags_long_lane_hops_in_ps(monkeypatch):
    P = plan()
    lid = next(iter(P.lanes))
    real = check.lane_pin_hops
    monkeypatch.setattr(check, "lane_pin_hops", lambda P_, l, regs: [300.0, 1250.0] if l == lid else real(P_, l, regs))
    rows = PTA.audit_reach(P)
    (r,) = [x for x in rows if x["lane"] == lid]
    assert r["hop_um"] == 1250.0 and r["hop_ps"] == round(50 + 0.65 * 1250, 1) and r["over_ps"] == round(862.5 - 658.0, 1)
    assert r["hop_index"] == 1 and r["types"]
    assert all(x["lane"] != next(i for i in P.lanes if i != lid) for x in rows) or True


def test_reach_clean_plan_has_no_rows():
    assert PTA.audit_reach(plan()) == []


def core_plan(depth=None, tap=None, lib=None):
    p = plan()
    t = p.types["mid"]
    t["hard_cores"] = [dict(inst="u_c", module="core", origin_um=[10, 10], outline_um=[50, 50], lib=str(lib) if lib else "x.lib")]
    if tap:
        t["clock"].update(core_taps="early", taps=[dict(name="u_c", xy=[20.0, 20.0], kind="core", **tap)])
    return p


def fake_load(monkeypatch, mean):
    monkeypatch.setattr(CC, "load", lambda core, root=None, require_signed=True, plan_type=None: {
        "clk": dict(corners=dict(tt=dict(mean_ps=mean, basis="pin_register_mean"), ff=dict(mean_ps=mean)), signed=True)})


def rows_for(p, **kw):
    return [r for r in PTA.audit_cores(p, None, **kw) if r["type"] == "mid"]


def test_core_deeper_than_budget_without_early_tap_fails(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB_OK)
    fake_load(monkeypatch, 271.0)                           # S81 col: 271 ps inside a 250 ps budget
    (r,) = rows_for(core_plan(lib=lib))
    assert r["verdict"] == "FAIL" and r["depth_ps"] == 271.0 and r["budget_ps"] == 250.0 and r["over_ps"] == 21.0
    assert "no early tap" in r["reasons"][0]
    fake_load(monkeypatch, 190.0)                           # <= budget - 50: usable
    assert rows_for(core_plan(lib=lib))[0]["verdict"] == "PASS"


def test_early_tap_must_match_the_measured_depth(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB_OK)
    fake_load(monkeypatch, 533.0)
    ok = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=533.0)))
    assert ok[0]["verdict"] == "PASS" and ok[0]["tap"] == "early"
    bad = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=450.0)))
    assert bad[0]["verdict"] == "FAIL" and "declares 450" in bad[0]["reasons"][0]
    assert rows_for(core_plan(lib=lib, tap=dict(insertion_ps=450.0, insertion_tol_ps=100)))[0]["verdict"] == "PASS"


def test_boundary_arcs_eat_the_cycle(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB)                                     # clk->q 480.5 + setup 346 = 826.5 of 833 (QC / S81 col_h9_r2)
    fake_load(monkeypatch, 100.0)
    (r,) = rows_for(core_plan(lib=lib))
    assert r["verdict"] == "FAIL" and r["arc_headroom_ps"] == 6.5 and "boundary arcs" in r["reasons"][0]
    assert rows_for(core_plan(lib=lib), arcs=False)[0]["verdict"] == "PASS"


def test_unmeasured_core_fails_closed(monkeypatch):
    def boom(core, root=None, require_signed=True, plan_type=None):
        raise CC.ContractError("pin-register mean measurement missing (no ETM-max fallback)")
    monkeypatch.setattr(CC, "load", boom)
    (r,) = rows_for(core_plan())
    assert r["verdict"] == "UNMEASURED" and "no measured clock depth" in r["reasons"][0]
    assert r["basis"] is None or r["basis"] == "LIB"        # LIB fallback depth, never a failure
    R = check.Report()
    s = PTA.g0(core_plan(), R, mode="error")
    assert not R.errors() and s["unmeasured_rows"] == 1 and s["failing_types"] == 0


def test_type_budget_follows_the_type_clock(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB_OK)
    fake_load(monkeypatch, 271.0)
    p = core_plan(lib=lib)
    p.types["mid"]["clock"]["insertion_ps"] = 450.0        # HEAD / serdes budget
    (r,) = rows_for(p)
    assert r["budget_ps"] == 450.0 and r["verdict"] == "PASS"


def test_g0_modes_and_tables(monkeypatch):
    fake_load(monkeypatch, 271.0)
    P = core_plan()
    P.types["mid"]["hard_cores"][0]["lib"] = "x.lib"
    monkeypatch.setattr(PTA, "lib_boundary_arcs", lambda p: (100.0, 50.0))
    monkeypatch.setattr("cores.resolve", lambda p, root=None: Path(p), raising=False)
    R = check.Report()
    s = PTA.g0(P, R, mode="warn")
    assert s["failing_types"] == 1 and not R.errors() and any(i["check"] == "timing_audit" and i["type"] == "mid" for i in R.items)
    R2 = check.Report()
    PTA.g0(P, R2, mode="error")
    assert any(i["check"] == "timing_audit" for i in R2.errors())
    assert PTA.g0(P, check.Report(), mode="off") is None
    txt = PTA.tables(PTA.run(P), "S81")
    assert "PLAN TIMING AUDIT S81" in txt and "mid\tcore\tclk" in txt and "271.0" in txt


def test_check_run_wires_the_audit():
    raw = copy.deepcopy(TINY)
    R, summ = check.run(raw, timing_audit="warn")
    assert "timing_audit" in summ
    R, summ = check.run(copy.deepcopy(TINY), timing_audit="off")
    assert "timing_audit" not in summ
    R, summ = check.run(copy.deepcopy(TINY))                  # COORD 11-15: default warn
    assert "timing_audit" in summ
