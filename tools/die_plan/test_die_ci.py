"""tests for die_ci.py (lane DIE-CI): margins policy guard, liberty numbers, derate injection, sub-top filter, seams and
stand-in budgets, latency consistency, and an end-to-end run (G0/G0C/census/latency, deltas, G2 carry) on the tiny plan.
No docker / OpenSTA needed."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import die_ci as C  # noqa: E402
import gen  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

TINY = HERE / "examples" / "tiny_plan.json"

MINI_LIB = """
library (x) {
 cell (DFFHQNx1_ASAP7_75t_R) {
  pin (D) {
   direction : input;
   capacitance : 0.5;
   timing () {
    related_pin : "CLK";
    timing_type : hold_rising;
    rise_constraint (c2) { index_1 ("10, 30"); index_2 ("10, 30"); values ( "4, 6", "8, 10" ); }
    fall_constraint (c2) { index_1 ("10, 30"); index_2 ("10, 30"); values ( "2, 2", "2, 2" ); }
   }
   timing () {
    related_pin : "CLK";
    timing_type : setup_rising;
    rise_constraint (c2) { index_1 ("10, 30"); index_2 ("10, 30"); values ( "20, 20", "20, 20" ); }
    fall_constraint (c2) { index_1 ("10, 30"); index_2 ("10, 30"); values ( "10, 10", "10, 10" ); }
   }
  }
  pin (QN) {
   direction : output;
   timing () {
    related_pin : "CLK";
    timing_type : rising_edge;
    cell_rise (d2) { index_1 ("10, 30"); index_2 ("5.76, 11.52"); values ( "100, 160", "110, 170" ); }
    cell_fall (d2) { index_1 ("10, 30"); index_2 ("5.76, 11.52"); values ( "90, 120", "100, 130" ); }
   }
  }
 }
}
"""


def test_flop_numbers_from_liberty():
    f = C.flop_numbers(MINI_LIB, slew=20.0, load_ff=5.76)
    assert f["clk_q_max_ps"] == pytest.approx(105.0)          # rise at slew 20 (between rows), load 5.76
    assert f["clk_q_min_ps"] == pytest.approx(95.0)
    assert f["r_eff_ps_per_ff"] == pytest.approx(60 / 5.76, abs=1e-3)
    assert f["setup_ps"] == pytest.approx(20.0)
    assert f["hold_ps"] == pytest.approx(7.0)
    assert f["d_cap_ff"] == 0.5


def test_margins_file_is_valid_and_pessimistic():
    m = C.load_margins(HERE / "die_ci_margins.json")
    d = C.derates(m)
    assert d["cell_late"] > 1.0 and d["cell_early"] < 1.0 and d["net_late"] >= 1.0 and d["net_early"] <= 1.0
    assert d["ir_factor"] > 1.0
    x = C.xtalk_ps(m, 30.0)
    assert x["setup_ps"] > 0 and x["hold_ps"] > 0 and x["seam_len_um"] == 60.0


@pytest.mark.parametrize("path,val", [(("ocv", "cell_late"), 0.98), (("ocv", "cell_early"), 1.02),
                                      (("xtalk", "mcf_setup"), 0.5), (("xtalk", "mcf_hold"), 1.5),
                                      (("ir", "vdd_drop_frac"), -0.01)])
def test_margins_never_relax_policy(path, val):
    m = json.loads(json.dumps(C.DEFAULT_MARGINS))
    m[path[0]][path[1]] = val
    with pytest.raises(SystemExit):
        C.check_margins(m)


def test_margins_reject_relaxed_policy_block():
    m = json.loads(json.dumps(C.DEFAULT_MARGINS))
    m["policy"] = dict(unc_setup_ps=40.0)
    with pytest.raises(SystemExit):
        C.check_margins(m)
    m["policy"] = dict(period_ps=900.0)
    with pytest.raises(SystemExit):
        C.check_margins(m)


def test_ir_pdnsim_replaces_stated_drop():
    m = json.loads(json.dumps(C.DEFAULT_MARGINS))
    f0, sens, drop = C.ir_factor(m)
    assert drop == 0.05 and f0 == pytest.approx(1 + 0.05 * sens, abs=1e-4)
    m["ir"]["pdnsim"] = dict(worst_drop_mv=12.6)
    f1, _, drop1 = C.ir_factor(m)
    assert drop1 == pytest.approx(0.02) and f1 < f0


def test_inject_derate_keeps_policy_lines():
    tcl = ("create_clock -name clk -period 833.3330 [get_ports clk]\nset_propagated_clock [all_clocks]\n"
           "set_clock_uncertainty 60.0000 -setup [all_clocks]\nset_clock_uncertainty 25.0000 -hold [all_clocks]\n"
           "set fh [open out.txt w]\n")
    out = C.inject_derate(tcl, C.DEFAULT_MARGINS)
    assert "set_clock_uncertainty 60.0000 -setup" in out and "set_clock_uncertainty 25.0000 -hold" in out
    assert out.index("set_timing_derate -late -cell_delay") < out.index("set fh [open")
    assert out.index("set_clock_uncertainty 25.0000") < out.index("set_timing_derate")
    with pytest.raises(SystemExit):
        C.inject_derate("read_liberty x\n", C.DEFAULT_MARGINS)


def test_filter_top_keeps_view_modules():
    import gen_rtl
    P = S.Plan(json.loads(TINY.read_text()))
    top = gen_rtl.die_top(P, gen_rtl.bus_epochs(P))
    mods = {P.types[p["type"]]["module"] for p in P.parts.values()}
    keep = sorted(mods)[:1]
    sub, kept = C.filter_top(top, set(keep))
    want = sorted(gen_rtl.sv_id(n) for n, p in P.parts.items() if P.types[p["type"]]["module"] in keep)
    assert sorted(kept) == want and kept
    for m in mods - set(keep):
        assert f"    {m} " not in sub
    assert "endmodule" in sub and "input  wire clk" in sub


def test_seams_and_standin_budgets():
    P = S.Plan(json.loads(TINY.read_text()))
    seams = C.plan_seams(P)
    inter = [p for p in P.ports.values() if "@die" not in (p["src"]["part"], p["dst"]["part"])]
    assert len(seams) == len(inter) > 0
    assert {s["cls"] for s in seams} <= {"ft", "ft_in", "ft_out", "bus"}
    m = C.load_margins(HERE / "die_ci_margins.json")
    kb = C.kit_budget(gen_phys)
    ft = C.standin("ft", P, m, kb)
    assert ft["basis"].startswith("contract") and ft["setup_policy_ps"] == pytest.approx(0.0, abs=0.1)
    assert ft["hold_policy_ps"] == pytest.approx(float(P.clock["insertion_tol_ps"]))
    assert ft["setup_ps"] < ft["setup_policy_ps"] and ft["hold_ps"] < ft["hold_policy_ps"]   # margins only subtract
    bus = C.standin("bus", P, m, kb)
    assert bus["basis"].startswith("R2")
    T = min(P.die["period_ps"], C.POLICY["period_ps"])
    assert bus["setup_policy_ps"] < T - C.POLICY["unc_setup_ps"]


def _plan_dir(tmp_path, with_latency=True, stale=False):
    d = tmp_path / "plan"
    d.mkdir()
    raw = json.loads(TINY.read_text())
    (d / "die_plan.json").write_text(json.dumps(raw))
    if with_latency:
        gen.write_latency(raw, d / "lat")
        if stale:
            f = next((d / "lat").glob("*_latency.json"))
            j = json.loads(f.read_text())
            j["plan_digest"] = "0" * 16
            f.write_text(json.dumps(j))
    return d / "die_plan.json"


def test_latency_gate(tmp_path):
    p = _plan_dir(tmp_path)
    r = C.gate_latency(REPO, p, None)
    assert r["status"] == "PASS" and r["record"].endswith("_latency.json")


def test_latency_gate_stale_and_missing(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    r = C.gate_latency(REPO, _plan_dir(a, stale=True), None)
    assert r["status"] == "FAIL" and "stale" in r["reason"]
    b = tmp_path / "b"
    b.mkdir()
    r = C.gate_latency(REPO, _plan_dir(b, with_latency=False), None)
    assert r["status"] == "FAIL" and "no <die>_latency.json" in r["reason"]


def test_latency_gate_lane_mismatch(tmp_path):
    p = _plan_dir(tmp_path)
    f = next((p.parent / "lat").glob("*_latency.json"))
    j = json.loads(f.read_text())
    lid = sorted(j["lanes"])[0]
    j["lanes"][lid]["cycles"] += 1
    f.write_text(json.dumps(j))
    r = C.gate_latency(REPO, p, None)
    assert r["status"] == "FAIL" and r["files"][0]["mismatched_lanes"] == 1


def _run(tmp_path, plan, out, *extra):
    argv = ["run", "--repo", str(REPO), "--sha", "a" * 40, "--date", "2026-10-24", "--out", str(out),
            "--plan", f"tiny={plan}", "--g2", "none", "--views", str(tmp_path / "noviews.json")] + list(extra)
    assert C.main(argv) == 0
    return json.loads((out / f"2026-10-24_{'a' * 12}" / "die_ci.json").read_text())


def test_run_end_to_end(tmp_path):
    plan = _plan_dir(tmp_path)
    out = tmp_path / "out"
    run = _run(tmp_path, plan, out, "--prev", "none")
    rd = out / f"2026-10-24_{'a' * 12}"
    for f in ("die_ci.json", "tiny.json", "tiny.md", "SUMMARY.md"):
        assert (rd / f).is_file()
    d = run["dies"]["tiny"]
    g = d["gates"]
    assert g["g0"]["status"] == "PASS" and g["g0c"]["status"] == "PASS"
    assert g["latency"]["status"] == "PASS"
    assert g["g2"]["status"].startswith("NOT RUN")
    assert g["sta"]["status"].startswith("NOT RUN") and g["sta"]["standin_ports"] == g["sta"]["seams"] > 0
    assert d["verdict"] == "INCOMPLETE" and d["delta"] is None
    assert "| tiny |" in (rd / "SUMMARY.md").read_text()
    assert "stand-in worst" in (rd / "tiny.md").read_text()


def test_run_deltas_and_g2_carry(tmp_path):
    plan = _plan_dir(tmp_path)
    out = tmp_path / "out"
    prev = _run(tmp_path, plan, out, "--prev", "none")
    # previous run: G2 PASS on the same plan + tools, one more G0C error than now
    pd = prev["dies"]["tiny"]
    pd["gates"]["g2"] = dict(status="PASS", probes=2, overflow=0, no_access=0)
    pd["gates"]["g0c"]["errors"] = 3
    pd["gates"]["g0c"]["status"] = "FAIL"
    pd["sha"] = prev["sha"] = "b" * 40
    pf = tmp_path / "prev.json"
    pf.write_text(json.dumps(prev))
    shutil.rmtree(out)
    run = _run(tmp_path, plan, out, "--prev", str(pf), "--g2", "auto")
    d = run["dies"]["tiny"]
    assert d["gates"]["g2"]["status"].startswith("PASS (CARRIED from " + "b" * 40)
    assert d["delta"]["metrics"]["g0c.errors"] == -3
    assert d["delta"]["status_changes"]["g0c"] == "FAIL -> PASS"
    assert "Delta vs bbbbbbbbbb" in (out / f"2026-10-24_{'a' * 12}" / "tiny.md").read_text()
    # a plan change voids the carry
    raw = json.loads(plan.read_text())
    raw["note"] = "changed"
    plan.write_text(json.dumps(raw))
    shutil.rmtree(out)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(C, "gate_g2", lambda *a, **k: dict(status="NOT RUN (stub)"))
        run = _run(tmp_path, plan, out, "--prev", str(pf), "--g2", "auto")
    assert run["dies"]["tiny"]["gates"]["g2"]["status"] == "NOT RUN (stub)"


def test_overall_verdicts():
    assert C.overall({"a": {"status": "PASS"}, "b": {"status": "N/A (x)"}}) == "PASS"
    assert C.overall({"a": {"status": "PASS"}, "b": {"status": "NOT RUN (x)"}}) == "INCOMPLETE"
    assert C.overall({"a": {"status": "PARTIAL (x)"}}) == "INCOMPLETE"
    assert C.overall({"a": {"status": "FAIL"}, "b": {"status": "NOT RUN"}}) == "FAIL"
