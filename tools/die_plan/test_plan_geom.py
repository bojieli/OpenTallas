"""plan_geom.py: the existing AUTO-GEOM rules at PLAN time in G0C (OWNER 12.23 (A), AUTOBUILD-GATE-1)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import check  # noqa: E402
import geom_rules as GR  # noqa: E402
import plan_geom as PG  # noqa: E402
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _metrics(**kw):
    m = dict(type="t", outline=[100.0, 100.0], aspect=1.0, clock_reach_max=10.0, clock_reach_far="x", grid_taps=2,
             grid_tap_sinks_max=10.0, grid_tap_sinks_worst="clk", pin_reg_p90=2.0, pin_reg_max=2.0,
             pin_reg_worst=["2.0 a[0]"], r2r_max=10.0, r2r_worst="ft", r2r_gt405=0, partial_faces=0,
             partial_face_detail=[])
    m.update(kw)
    return m


def _status(rules, rule):
    return next(r["status"] for r in rules if r["rule"] == rule)


def test_limits_are_the_auto_geom_limits():
    # no new limit: every number comes from geom_rules
    assert PG.CLK_REACH == round(GR.CLK_REACH_MAX * GR.CLK_REACH_TOL, 1) == 220.0
    R = PG.judge(_metrics(clock_reach_max=220.0, grid_tap_sinks_max=GR.TAP_SINKS_MAX, pin_reg_p90=GR.PINREG_P90,
                          pin_reg_max=GR.PINREG_HARD, r2r_max=GR.R2R_MAX, aspect=GR.ASPECT_MAX))
    assert all(r["status"] == "PASS" for r in R), R
    R = PG.judge(_metrics(clock_reach_max=220.01, grid_tap_sinks_max=GR.TAP_SINKS_MAX + 1, pin_reg_p90=30.01,
                          pin_reg_max=150.01, r2r_max=405.01, aspect=2.001, partial_faces=1))
    assert {r["rule"] for r in R if r["status"] == "FAIL"} == {
        "clock_reach", "clock_tap_sinks", "pin_reg_p90", "pin_reg_max", "r2r", "aspect", "partial_face"}


def test_tap_load_rule_needs_two_grid_taps():
    # AUTO-GEOM: < 2 grid taps -> the tap rule is INFO (not evaluated)
    R = PG.judge(_metrics(grid_taps=1, grid_tap_sinks_max=9999))
    assert "clock_tap_sinks" not in {r["rule"] for r in R}


def test_granted_exception_kept():
    # COORD RULING 10-30 22:24 (a): S81 stform2 stations keep partial_face as a granted exception, nothing else
    m = _metrics(type="slice_station__t7__clx", partial_faces=2, clock_reach_max=366.0)
    R = PG.judge(m, "s81")
    assert _status(R, "partial_face") == "EXCEPTION" and _status(R, "clock_reach") == "FAIL"
    assert _status(PG.judge(m, "qwen_kvsys"), "partial_face") == "FAIL"
    assert _status(PG.judge(_metrics(type="eng__t1", partial_faces=1), "s81"), "partial_face") == "FAIL"
    # COORD RULING 18:54: QC slice lattice aspect
    assert _status(PG.judge(_metrics(type="sle_stm_v3", aspect=2.18), "qwen_compute"), "aspect") == "EXCEPTION"
    assert _status(PG.judge(_metrics(type="tt_ctlm", aspect=2.18), "qwen_compute"), "aspect") == "FAIL"


def test_reset_leaf_estimate_never_gates():
    R = PG.judge(_metrics(reset_leaf_max=500.0, reset_leaf_worst="reset leaf u_rrl_1->sink"))
    assert _status(R, "r2r_reset_leaf") == "WARN" and not [r for r in R if r["status"] == "FAIL"]


def test_tiny_plan_reach_from_plan_alone():
    # tiny_plan: 864-um types on the 400-um R4 grid -> 3x3 taps at 144/432/720; a face register at the corner window
    # (2, 600.5) is 142 + 119.5 = 261.5 um from tap (144, 720): the clock_reach rule fails before any kit exists
    P = schema.Plan(copy.deepcopy(EX))
    m = PG.type_metrics(P, "mid")
    assert m["clock_reach_max"] > PG.CLK_REACH and m["grid_taps"] == 9
    assert _status(PG.judge(m, P.name), "clock_reach") == "FAIL"
    # a 280-um grid brings every planned sink within reach (same rule, the plan fixed)
    p = copy.deepcopy(EX)
    p.setdefault("budgets", {})["tap_pitch_um"] = 280.0
    m2 = PG.type_metrics(schema.Plan(p), "mid")
    assert m2["clock_reach_max"] <= PG.CLK_REACH, m2["clock_reach_far"]


def test_g0c_cli_runs_plan_geom_and_g0_does_not(tmp_path):
    plan = tmp_path / "die_plan.json"
    plan.write_text(json.dumps(EX))
    check.main([str(plan), "--completeness", "--quiet", "--out", str(tmp_path / "g0c")])
    rep = json.loads((tmp_path / "g0c" / "g0_report.json").read_text())
    geo = [i for i in rep["findings"] if i["check"] in PG.CHECKS]
    # default mode = report: WARN "[G0C-GEOM]" (COORD flips DEFAULT_MODE to enforce after measured validation)
    assert PG.DEFAULT_MODE == "report"
    assert geo and all(i["level"] == "WARN" and i["msg"].startswith("[G0C-GEOM]") and i.get("type") for i in geo)
    assert rep["summary"]["plan_geom"]["by_rule"].get("clock_reach") == 3
    check.main([str(plan), "--completeness", "--plan-geom", "enforce", "--quiet", "--out", str(tmp_path / "enf")])
    rep = json.loads((tmp_path / "enf" / "g0_report.json").read_text())
    geo = [i for i in rep["findings"] if i["check"] in PG.CHECKS]
    assert geo and all(i["level"] == "ERROR" for i in geo) and rep["verdict"] == "FAIL"
    # plain G0 and library callers of check.run are unchanged (no plan-time GEOM unless G0C asks for it)
    check.main([str(plan), "--quiet", "--out", str(tmp_path / "g0")])
    rep0 = json.loads((tmp_path / "g0" / "g0_report.json").read_text())
    assert not [i for i in rep0["findings"] if i["check"] in PG.CHECKS] and "plan_geom" not in rep0["summary"]
    R, summ = check.run(copy.deepcopy(EX), completeness=True)
    assert "plan_geom" not in summ
    # diagnostics opt-out
    check.main([str(plan), "--completeness", "--plan-geom", "off", "--quiet", "--out", str(tmp_path / "ng")])
    rep2 = json.loads((tmp_path / "ng" / "g0_report.json").read_text())
    assert not [i for i in rep2["findings"] if i["check"] in PG.CHECKS]


def test_plan_geom_checks_are_g0c_checks():
    assert set(PG.CHECKS) <= set(check.G0C_CHECKS)
