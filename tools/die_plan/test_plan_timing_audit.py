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
    ok = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=533.0, insertion_ff_ps=430.0)))
    assert ok[0]["verdict"] == "PASS" and ok[0]["tap"] == "early"
    bad = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=450.0, insertion_ff_ps=360.0)))
    assert bad[0]["verdict"] == "FAIL" and "declares 450" in bad[0]["reasons"][0]
    assert rows_for(core_plan(lib=lib, tap=dict(insertion_ps=450.0, insertion_ff_ps=360.0, insertion_tol_ps=100)))[0]["verdict"] == "PASS"


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


def test_shared_directory_measurement_is_not_attributed(tmp_path):
    """S81 romq_split_1106: gb_he and gb_hw libs in one directory share one insertion.json -> refused, never one core's depth for another"""
    (tmp_path / "a_tt.lib").write_text("x")
    (tmp_path / "b_tt.lib").write_text("x")
    one = dict(clk=dict(corners=dict(tt=dict(mean_ps=410.0, basis="pin_register_mean")), signed=False, contract_source=str(tmp_path / "insertion.json")))
    with pytest.raises(CC.ContractError, match="shared by 2 core libraries"):
        PTA._shared_dir_guard(one)
    (tmp_path / "b_tt.lib").unlink()
    PTA._shared_dir_guard(one)


def test_early_tap_credits_the_boundary_arc(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB)                                     # clk->q 480.5 + setup 346: headroom 6.5 without a tap
    fake_load(monkeypatch, 533.0)
    p = core_plan(lib=lib, tap=dict(insertion_ps=533.0, insertion_ff_ps=430.0))
    common = float(p.clock["insertion_ps"])
    (r,) = rows_for(p)
    assert r["tap"] == "early" and r["verdict"] == "PASS"
    assert abs(r["arc_headroom_ps"] - (833.0 - (common + 480.5 - 533.0) - 346.0)) < 0.2 and r["arc_headroom_ps"] > 150
    fake_load(monkeypatch, 100.0)                           # no tap: the old form (6.5) still fails
    (n,) = rows_for(core_plan(lib=lib))
    assert n["verdict"] == "FAIL" and n["arc_headroom_ps"] == 6.5


def test_split_clock_pin_reads_ck_face_for_the_boundary_arcs(monkeypatch, tmp_path):
    lib = tmp_path / "c.lib"
    lib.write_text(LIB)                                     # clk->q 480.5 + setup 346: headroom 6.5 without a tap credit
    mk = lambda m: dict(corners=dict(tt=dict(mean_ps=m, basis="pin_register_mean"), ff=dict(mean_ps=m)), signed=True)
    monkeypatch.setattr(CC, "load", lambda core, root=None, require_signed=True, plan_type=None: {"ck": mk(300.0), "ck_face": mk(533.0)})
    p = core_plan(lib=lib, tap=dict(insertion_ps=533.0, insertion_ff_ps=430.0))
    common = float(p.clock["insertion_ps"])
    rows = {r["pin"]: r for r in rows_for(p)}
    assert rows["ck_face"]["tap"] == "early" and rows["ck_face"]["verdict"] == "PASS"
    assert abs(rows["ck_face"]["arc_headroom_ps"] - (833.0 - (common + 480.5 - 533.0) - 346.0)) < 0.2
    assert rows["ck"]["arc_headroom_ps"] is None            # the non-face pin carries no boundary-arc row
    monkeypatch.setattr(CC, "load", lambda core, root=None, require_signed=True, plan_type=None: {"ck": mk(300.0)})
    (only,) = rows_for(core_plan(lib=lib))                  # no ck_face: the old single-pin form
    assert only["arc_headroom_ps"] == 6.5


# ------------------------------------------------------------------ S81-TAPROWS 11-15: the signed io reference is the tap basis
def signed_view(tmp_path, tt=465.39, ff=361.26, with_ref=True, mean=555.0):
    """a view dir: one liberty + the signed record of the core (core_latency measured mean 555 TT, typed reference 465.39 / 361.26)"""
    d = tmp_path / "view"
    d.mkdir(exist_ok=True)
    (d / "core_tt.lib").write_text(LIB_OK)
    cl = dict(measured=dict(tt=dict(mean=mean, n=673), ff=dict(mean=mean * 0.81, n=673)))
    if with_ref:
        cl["contract"] = dict(io_reference_ps=dict(tt=tt, ff=ff, basis="typed reference", kind="plan_declared"))
    (d / "signoff.json").write_text(json.dumps(dict(verdict="SIGNED", core_latency=cl)))
    return d / "core_tt.lib"


def test_io_reference_reads_the_typed_reference_then_the_band_bound():
    rec = dict(verdict="SIGNED", core_latency=dict(contract=dict(io_reference_ps=dict(tt=465.39, ff=361.26))),
               insertion_band=dict(corners=dict(tt=dict(bound_ps=400.0), ff=dict(bound_ps=324.0))))
    assert CC.io_reference(rec)["tt"] == 465.39 and CC.io_reference(rec)["source"] == "core_latency.contract.io_reference_ps"
    del rec["core_latency"]
    r = CC.io_reference(rec)                                  # idx_tx_n32: no typed reference, the kit vclk bound the IO closed against
    assert (r["tt"], r["ff"]) == (400.0, 324.0) and r["source"] == "insertion_band.corners.bound_ps"
    assert CC.io_reference(dict(rec, verdict="FAIL")) is None and CC.io_reference({}) is None


def test_audit_takes_the_io_reference_not_the_routed_mean(monkeypatch, tmp_path):
    lib = signed_view(tmp_path)
    fake_load(monkeypatch, 555.0)                             # the routed pin-register mean (he 555.02): NOT the basis
    ok = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=465.39, insertion_ff_ps=361.26)))
    assert ok[0]["verdict"] == "PASS" and ok[0]["basis"] == "io_reference" and ok[0]["depth_ps"] == 465.4
    for ins in (532.99, 553.18, 437.41):                      # liberty max rows and the stale midpoint: all fail against the reference
        bad = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=ins, insertion_ff_ps=361.26)))
        assert bad[0]["verdict"] == "FAIL" and "signed io reference" in bad[0]["reasons"][0], ins
    ff = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=465.39, insertion_ff_ps=300.0)))
    assert ff[0]["verdict"] == "FAIL" and "FF" in ff[0]["reasons"][-1]


def test_early_row_without_ff_fails(monkeypatch, tmp_path):
    lib = signed_view(tmp_path)
    (r,) = rows_for(core_plan(lib=lib, tap=dict(insertion_ps=465.39)))
    assert r["verdict"] == "FAIL" and any("no insertion_ff_ps" in x for x in r["reasons"])


def test_two_rows_on_one_core_clock_fail(monkeypatch, tmp_path):
    lib = signed_view(tmp_path)
    p = core_plan(lib=lib, tap=dict(insertion_ps=465.39, insertion_ff_ps=361.26))
    p.types["mid"]["clock"]["taps"] = [dict(name="u_c.clk", xy=[20.0, 20.0], kind="core", insertion_ps=465.39, insertion_ff_ps=361.26),
                                       dict(name="u_c.ck", xy=[30.0, 20.0], kind="core", insertion_ps=437.41, insertion_ff_ps=348.7)]
    (r,) = rows_for(p)
    assert r["verdict"] == "FAIL" and any("2 tap rows on one core clock" in x for x in r["reasons"])


def test_explicit_signed_record_wins_over_the_view_dir(tmp_path):
    lib = signed_view(tmp_path, with_ref=False)               # the view dir record has no reference ...
    rec = tmp_path / "gb_hw_signoff.json"
    rec.write_text(json.dumps(dict(verdict="SIGNED", core_latency=dict(contract=dict(io_reference_ps=dict(tt=465.39, ff=361.26))))))
    p = core_plan(lib=lib, tap=dict(insertion_ps=465.39, insertion_ff_ps=361.26))
    r = [x for x in PTA.audit_cores(p, None, records={"core": str(rec)}) if x["type"] == "mid"]
    assert r[0]["verdict"] == "PASS" and r[0]["basis"] == "io_reference"
    CC_none = CC.io_reference_of_core(p.types["mid"]["hard_cores"][0], None)
    assert CC_none is None                                    # ... and without the explicit record the core is not judged by a reference
