"""OWNER 12.24b (2026-10-31 00:56): die STA gate numbers are NOMINAL by default.  --margin-policy nominal (the shared
default) ignores the spice clock factor, clock OCV/AOCV/droop, mesh U / pair unc and the data droop derate that callers
still pass; --margin-policy legacy reproduces the pre-12.24b numbers for A/B."""
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402
import die_sta_related as R  # noqa: E402
import test_ca_ocv as F  # noqa: E402  (fixture: two regions under h, one landed crossing A->B)

MARGIN_ARGS = ["--clock-cal", "spice_edge", "--clock-ocv", "table", "--clock-droop", "shared", "--data-droop", "class"]
ALL_NONE = ["--clock-cal", "none", "--clock-ocv", "none", "--data-droop", "none"]


@pytest.fixture(autouse=True)
def _restore_cppr_lca():
    old = R.CPPR_LCA
    yield
    R.CPPR_LCA = old


def _run(tmp_path, monkeypatch, name, extra):
    proof, _, _, _ = F._fold_proof(tmp_path)
    monkeypatch.setattr(R, "characterise", lambda *a, **k: dict(F.REG))
    d_lo, d_hi = 230.0, 360.0
    bind = {"sync_aperture_ps": 26.5, "ports": {"x": dict(src="A", dst="B", K=1, depth=8, tree=False,
                                                          L_lo_ps=F.T + d_lo, L_hi_ps=F.T + d_hi, d_lo_ps=d_lo,
                                                          d_hi_ps=d_hi, wander_ps=0.0)}, "regions": {}}
    (tmp_path / "bind.json").write_text(json.dumps(bind))
    R.main([str(proof), "--plan", str(tmp_path / "plan.json"), "--count-align", str(tmp_path / "bind.json"),
            "--period-ps", str(F.T), "--count-align-ss-scale", "0", "--out", str(tmp_path / name)] + extra)
    return json.loads((tmp_path / name / "die_sta_related.json").read_text())


def _numbers(r):
    """gate numbers of a record: per corner every class's slacks + the CA rows, and the summary gate verdicts"""
    cls = {c: {k: {f: v.get(f) for f in ("worst_setup_slack_ps", "worst_hold_slack_ps", "pairs")}
               for k, v in cr["classes"].items()} for c, cr in r["corners"].items()}
    ca = {c: [{k: x[k] for k in ("margin_lo_ps", "margin_hi_ps")} for x in v["rows"]]
          for c, v in r.get("count_aligned", {}).items()}
    summ = {k: v for k, v in r["summary"].items() if k not in ("margin_policy",)}
    summ["landed"] = {k: v for k, v in summ["landed"].items() if k != "bind"}
    return cls, ca, summ


def test_default_policy_is_nominal(tmp_path, monkeypatch):
    assert R.MARGIN_POLICY_DEFAULT == "nominal"
    r = _run(tmp_path, monkeypatch, "o", [])
    assert r["summary"]["margin_policy"] == dict(policy="nominal", rule="OWNER 12.24b", overridden={})
    assert "data_droop" not in r and "data_droop" not in r["summary"]          # no data droop term by default
    assert r["count_aligned"]["TT"]["clock_variation"] == "none"


def test_margin_flags_ignored_under_default_equal_all_none(tmp_path, monkeypatch, capsys):
    rm = _run(tmp_path, monkeypatch, "m", MARGIN_ARGS)
    out = capsys.readouterr().out
    assert "MARGIN POLICY nominal (OWNER 12.24b): ignored --clock-cal spice_edge, --clock-ocv table, " \
           "--clock-droop shared, --data-droop class" in out
    assert "WARNING --count-align" not in out                                   # no 12.14a warning under nominal
    rn = _run(tmp_path, monkeypatch, "n", ["--margin-policy", "legacy"] + ALL_NONE)
    assert _numbers(rm) == _numbers(rn)
    assert rm["summary"]["margin_policy"]["overridden"] == {"--clock-cal": "spice_edge", "--clock-ocv": "table",
                                                            "--clock-droop": "shared", "--data-droop": "class"}
    assert rm["count_aligned"]["TT"]["verdict"] == rn["count_aligned"]["TT"]["verdict"]


def test_legacy_reproduces_old_margins(tmp_path, monkeypatch):
    rn = _run(tmp_path, monkeypatch, "n", [])
    rl = _run(tmp_path, monkeypatch, "l", ["--margin-policy", "legacy", "--clock-ocv", "table", "--clock-droop",
                                           "shared"])
    assert rl["summary"]["margin_policy"]["policy"] == "legacy"
    assert rl["count_aligned"]["TT"]["clock_variation"] == "table"
    assert rl["data_droop"]["mode"] == "class"                                   # legacy default data droop kept
    x0, x1 = rn["count_aligned"]["TT"]["rows"][0], rl["count_aligned"]["TT"]["rows"][0]
    ps = F._hand("TT", (1200.0, 12), (1440.0, 14), 250.0)
    ph = F._hand("TT", (1500.0, 14), (1150.0, 12), 250.0)
    assert abs((x0["margin_lo_ps"] - x1["margin_lo_ps"]) - ps) < 0.11
    assert abs((x0["margin_hi_ps"] - x1["margin_hi_ps"]) - ph) < 0.11
    # legacy with the spice factor scales the arrivals; nominal never does
    rs = _run(tmp_path, monkeypatch, "s", ["--margin-policy", "legacy", "--clock-cal", "spice"])
    assert _numbers(rs) != _numbers(rn)
    assert _numbers(_run(tmp_path, monkeypatch, "s2", ["--clock-cal", "spice"])) == _numbers(rn)


def test_pair_unc_and_mesh_signoff_ignored_under_nominal(tmp_path, monkeypatch):
    r = _run(tmp_path, monkeypatch, "p", ["--pair-unc", str(tmp_path / "missing.json"), "--mesh-signoff", "TT=a,FF=b"])
    assert r["summary"]["margin_policy"]["overridden"] == {"--mesh-signoff": "TT=a,FF=b",
                                                           "--pair-unc": str(tmp_path / "missing.json")}
    assert _numbers(r) == _numbers(_run(tmp_path, monkeypatch, "q", []))


def test_library_intervals_nominal_by_default(tmp_path):
    proof, _, _, plan = F._fold_proof(tmp_path)
    base = R.sta_d_intervals(proof, plan, ("TT",), "none", False)["TT"]["A->B"]
    kw = dict(clock_ocv="table", clock_droop="shared")
    assert R.sta_d_intervals(proof, plan, ("TT",), "spice", False, **kw)["TT"]["A->B"] == base
    assert R.sta_d_intervals(proof, plan, ("TT",), "spice", False, margin_policy="legacy", **kw)["TT"]["A->B"] != base
    with pytest.raises(SystemExit):
        R.margin_policy("bogus")


def test_start_tree_needs_no_ocv_under_nominal():
    errs = []
    a = types.SimpleNamespace(start_tree="clock", sta_proof="p", sta_plan="q", sta_clock_ocv="none", tree_parent=None,
                              margin_policy="nominal")
    CAP.check_start_tree_args(a, errs.append)
    assert errs == []
    a.margin_policy = "legacy"
    CAP.check_start_tree_args(a, errs.append)
    assert len(errs) == 1 and "--sta-clock-ocv table" in errs[0]


def test_clock_contexts_nominal(tmp_path):
    proof, taps, _, plan = F._fold_proof(tmp_path)
    for c in ("TT", "FF"):
        f = tmp_path / f"tap_arrivals_{c}.json"
        d = json.loads(f.read_text())
        for t in d["taps"]:
            t["tree_path"] = ["h", t["cppr_node"]]
        f.write_text(json.dumps(d))
    ctx = CAP.clock_contexts(proof, tmp_path / "plan.json", ("TT",), clock_cal="spice", clock_ocv="table",
                             clock_droop="shared")
    assert ctx["TT"]["ocv"] is None and ctx["TT"]["taps"]["pa"]["late_ps"] == taps["pa"]["late_ps"]
    leg = CAP.clock_contexts(proof, tmp_path / "plan.json", ("TT",), clock_cal="spice", clock_ocv="table",
                             clock_droop="shared", margin_policy="legacy")
    assert leg["TT"]["ocv"] is not None and leg["TT"]["taps"]["pa"]["late_ps"] > taps["pa"]["late_ps"]
    with pytest.raises(ValueError, match="clock variation model"):
        CAP.clock_contexts(proof, tmp_path / "plan.json", ("TT",), clock_ocv="none", margin_policy="legacy")


def test_planner_cli_margin_flags_ignored(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake(proof, plan, cs, ports, pr, cal, lca, fall=False, **kw):
        seen.update(kw, cal=cal)
        return {"TT": dict(rise={}, fall={}, unbound=[])}
    monkeypatch.setattr(R, "sta_port_intervals", fake)
    rows = dict(corners={"TT_x": dict(all=[dict(port="p", src="a", dst="b", d_ps=100.0, p_up_ps=1.0, p_dn_ps=1.0,
                                                unshared_a_ps=0.0, unshared_b_ps=0.0, margin_ps=0.0)])})
    (tmp_path / "r.json").write_text(json.dumps(rows))
    try:
        CAP.main([str(tmp_path / "r.json"), "--corner", "TT_x", "--sta-proof", str(tmp_path), "--sta-plan", "p.json",
                  "--sta-clock-cal", "spice_edge", "--sta-clock-ocv", "table", "--sta-clock-droop", "shared",
                  "--sta-droop-regions", "dr.json", "--out", str(tmp_path / "o.json")])
    except SystemExit:
        pass
    assert seen["cal"] == "none" and seen["clock_ocv"] == "none" and seen["clock_droop"] is None
    assert seen["droop_regions_file"] is None and seen["margin_policy"] == "nominal"
    err = capsys.readouterr().err
    assert "MARGIN POLICY nominal (OWNER 12.24b): ignored --sta-clock-cal spice_edge, --sta-clock-ocv table" in err
    seen.clear()
    try:
        CAP.main([str(tmp_path / "r.json"), "--corner", "TT_x", "--sta-proof", str(tmp_path), "--sta-plan", "p.json",
                  "--margin-policy", "legacy", "--out", str(tmp_path / "o2.json")])
    except SystemExit:
        pass
    assert seen["cal"] == "spice"                                                # pre-12.24b planner default
