"""FLOW-HOLD-1 (OWNER 12.19, COORD 10-29 05:52): the shared die STA judges die hold on REAL SIGNED VIEWS only.

A related pair with an endpoint block that has no signed real view is UNMEASURED (reason: missing view <block>), never
a hold failure from the declared-register / tap-window model.  The gate is not loosened: hold PASS needs 0 unmeasured
pairs and every measured pair >= 0; unmeasured pairs -> BLOCKED(kits).  Setup is unchanged."""
import json

import die_sta_related as R
from test_die_sta_core_insertion import REG, CORE, PLAIN, OTHER, _plan, _run

KIT = {"corners": {c: dict(lat_min_ps=250.0, lat_max_ps=250.0, clkq_max_ps=68.0, clkq_min_ps=60.0, setup_ps=5.6,
                           hold_ps=22.2) for c in ("TT", "FF")}}


def _tap(port, part, late, early):
    return dict(port=port, part=part, late_ps=late, early_ps=early, slew_ps=20.0, cppr_node="h0", xy_um=[0.0, 0.0])


def _taps(skew=0.0):
    """two taps per partition; pfa's second tap lands `skew` ps late (a hold risk for pfa1 -> pfa2 ... pairs)"""
    return {"a1": _tap("a1", "pfa", 1000.0, 990.0), "a2": _tap("a2", "pfa", 1000.0 + skew, 990.0 + skew),
            "b1": _tap("b1", "pfb", 1000.0, 990.0), "b2": _tap("b2", "pfb", 1000.0, 990.0)}


def _cls(views, taps, plan):
    pairs = [(x, y, "t") for x in taps for y in taps if x != y]
    return R.time_class(pairs, taps, {"h0": 10.0}, REG, 20.0, 833.333, 60.0, 25.0, views=views,
                        hold_window=dict(ps=0.0, basis="t"), missing=R.missing_views(views, taps, plan))


def _views(taps, kit_types):
    b = R.budget_model(REG, 250.0)
    return {p: [R.kit_model(KIT, "FF", t["part"][1:])] if t["part"][1:] in kit_types else [b] for p, t in taps.items()}


def test_missing_view_pairs_are_unmeasured_not_tap_window_failures():
    plan, taps = _plan(early=False), _taps(skew=300.0)        # a2 300 ps late: declared-register hold < 0
    r = _cls(_views(taps, {"fb"}), taps, plan)                # only fb has a signed kit
    hm = r["hold_measured"]
    assert r["worst_hold_slack_ps"] < 0 and r["kit_contract_hold"]["verdict"] == "FAIL"   # diagnostics unchanged
    assert hm["pairs_measured"] == 2 and hm["pairs_unmeasured"] == 10                     # only b1<->b2 measured
    assert hm["missing_views"] == {"type:fa": 10}
    assert hm["neg_pairs"] == 0 and hm["hold_margin_ps"] >= 0 and hm["status"] == "BLOCKED(kits)"


def test_measured_failure_is_fail_and_full_coverage_pass():
    plan = _plan(early=False)
    bad = _cls(_views(_taps(300.0), {"fa", "fb"}), _taps(300.0), plan)["hold_measured"]
    assert bad["pairs_unmeasured"] == 0 and bad["neg_pairs"] > 0 and bad["status"] == "FAIL"
    assert bad["hold_margin_ps"] < 0 and bad["worst"]["capture"] == "a2"
    good = _cls(_views(_taps(), {"fa", "fb"}), _taps(), plan)
    assert good["hold_measured"]["status"] == "PASS" and good["hold_measured"]["pairs_measured"] == 12
    assert good["hold_measured"]["hold_margin_ps"] == good["worst_hold_slack_ps"]          # same number when measured


def test_no_real_views_all_unmeasured_and_unsigned_view_is_missing():
    plan, taps = _plan(early=False), _taps()
    r = _cls(None, taps, plan)["hold_measured"]
    assert r["pairs_measured"] == 0 and r["hold_margin_ps"] is None and r["status"] == "BLOCKED(kits)"
    assert r["missing_views"] == {"type:fa": 10, "type:fb": 10}
    v = _views(taps, {"fa", "fb"})
    v["b1"] = [dict(v["b1"][0], meta=dict(verdict="FAIL (signoff.py)"))]
    m = R.missing_views(v, taps, plan)
    assert m["b1"] == ["kit:fb (view not SIGNED)"] and m["a1"] == []
    v["b1"] = [dict(v["b1"][0], meta=dict(verdict="SIGNED (signoff.py verdict SIGNED; routed LEC EQUIVALENT)"))]
    assert R.missing_views(v, taps, plan)["b1"] == []


def test_early_core_tap_without_view_is_missing_core():
    plan = _plan()
    taps = {CORE: _tap(CORE, "pfa", 820.0, 810.0), PLAIN: _tap(PLAIN, "pfa", 1000.0, 990.0)}
    ecm = R.early_core_map(plan, taps)
    v, _ = R.core_tap_views(_views(taps, {"fa"}), ecm, "FF", REG, {}, "view")
    assert R.missing_views(v, taps, plan, ecm) == {CORE: ["core:cmod"], PLAIN: []}


def test_main_summary_gate(tmp_path, monkeypatch):
    kit = tmp_path / "kit.json"
    kit.write_text(json.dumps(KIT))
    plan = _plan(early=False)
    half = _run(tmp_path, monkeypatch, plan, "--kit", f"fb={kit}")
    g = half["summary"]["intra"]
    assert g["hold_status"] == "BLOCKED(kits)" and g["verdict"] == "BLOCKED(kits)" and g["missing_views"] == ["type:fa"]
    assert g["hold_pairs_unmeasured"] > 0 and "ff_hold_all_pairs_diag_ps" in g and "ff_hold_ps" not in g
    full = _run(tmp_path, monkeypatch, plan, "--kit", f"fa={kit}", "--kit", f"fb={kit}")
    f = full["summary"]["intra"]
    assert f["hold_pairs_unmeasured"] == 0 and f["missing_views"] == []
    assert f["hold_status"] == ("PASS" if f["ff_hold_margin_ps"] >= 0 else "FAIL")
    assert f["verdict"] == ("PASS" if f["tt_setup_ps"] >= 0 and f["hold_status"] == "PASS" else "FAIL")
    # setup reporting unchanged by the view split
    assert full["corners"]["TT"]["classes"]["intra"]["worst_setup_slack_ps"] == f["tt_setup_ps"]


def test_die_infra_freeze_reads_measured_hold(tmp_path):
    import hashlib
    import die_infra as DI
    pf = tmp_path / "plan.json"
    pf.write_text("{}")
    sha = hashlib.sha256(pf.read_bytes()).hexdigest()
    pre = dict(plan_sha256=sha, plan=str(pf))

    def rec(hm):
        tt = dict(pairs=4, worst_setup_slack_ps=50.0, setup_neg_pairs=0, worst_hold_slack_ps=-300.0, hold_neg_pairs=4)
        ff = dict(tt, worst_setup_slack_ps=60.0, hold_measured=hm)
        empty = dict(pairs=0)
        cls = lambda x: dict(intra=x, intra_cross_region=empty, seam=empty, landed=empty)
        f = tmp_path / "sta.json"
        f.write_text(json.dumps(dict(plan_sha256=sha, period_ps=833, unc_setup_ps=60, unc_hold_ps=25,
                                     coverage=dict(uncovered_bits={}),
                                     corners=dict(TT=dict(basis="routed RC", classes=cls(tt)),
                                                  FF=dict(basis="routed RC", classes=cls(ff))))))
        return DI.related_sta_state(f, pre)
    hm = dict(pairs_measured=1, pairs_unmeasured=3, hold_margin_ps=12.0, neg_pairs=0, missing_views={"type:fa": 3})
    b = rec(hm)
    assert b["verdict"] == "BLOCKED(kits)" and b["checks"]["intra"]["missing_views"] == ["type:fa"]
    assert rec(dict(hm, pairs_measured=4, pairs_unmeasured=0, missing_views={}))["verdict"] == "PASS"
    assert rec(dict(hm, neg_pairs=1, hold_margin_ps=-1.0))["verdict"] == "FAIL"


# ---- (2) kit hold repair defaults (new builds only) ----

def test_stage_applies_measured_hold_by_default_on_rebind_kits(tmp_path):
    import kit_modes
    import sdc_lint
    from test_kit_modes import kit
    kd = kit(tmp_path)                                         # sdc_lint insertion_ff_ps -> 'rebind'
    r = kit_modes.stage(kd)
    assert r["measured_hold"] is True and r["measured_hold_ref"] == "rebind"
    assert kit_modes.MEASURED_FLAG in (kd / "config.mk").read_text()
    assert (kd / "vclk_measured_hold.tcl").is_file() and (kd / "vclk_ref.py").is_file()
    assert sdc_lint.measured_frame_errors(kd) == []            # the staged kit passes the existing preflight
    again = kit_modes.stage(kd)                                # an already staged kit is not changed
    assert again["already"] and "measured_hold" not in again


def test_stage_opt_out_and_non_rebind_kits(tmp_path):
    import kit_modes
    from test_kit_modes import kit
    (tmp_path / "a").mkdir()
    kd = kit(tmp_path / "a")
    r = kit_modes.stage(kd, measured_hold=False)
    assert r["measured_hold"] is False and kit_modes.MEASURED_FLAG not in (kd / "config.mk").read_text()
    def hard_core_kit(d):                                       # typed hard-core latency contract -> 'bound-ff'
        d.mkdir()
        kd = kit(d)
        (kd / "core.json").write_text(json.dumps(dict(clock_contract=dict(kind="hard_core_latency"))))
        (kd / "boundary_guard_context.json").write_text(json.dumps(dict(source_core_json="core.json")))
        return kd
    kd = hard_core_kit(tmp_path / "b")
    r = kit_modes.stage(kd)
    assert r["measured_hold"] is False and r["measured_hold_ref"] == "bound-ff" and "rebind" in r["measured_hold_reason"]
    assert kit_modes.MEASURED_FLAG not in (kd / "config.mk").read_text()
    kd = hard_core_kit(tmp_path / "c")
    assert kit_modes.main(["stage", str(kd), "--measured-hold"]) == 2          # explicit request still fails closed
    (tmp_path / "d").mkdir()
    kd = kit(tmp_path / "d")
    assert kit_modes.main(["stage", str(kd), "--no-measured-hold"]) == 0
    assert kit_modes.MEASURED_FLAG not in (kd / "config.mk").read_text()


def test_hold_ff_margin_default_is_10_everywhere(tmp_path):
    import core_flow
    import gen_phys
    from pathlib import Path
    assert core_flow.HOLD_FF_MARGIN_DEFAULT == gen_phys.HOLD_FF_MARGIN_DEFAULT == 10.0
    b = core_flow.binding(250.0, 202.5)
    cfg = core_flow.apply(tmp_path, b, "x", rc_cal=False)
    assert "export OT_HOLD_FF_MARGIN = 10" in cfg
    assert "export OT_HOLD_FF_MARGIN = 15" in core_flow.apply(tmp_path, b, "x", rc_cal=False, hold_ff_margin=15.0)
    root = Path(core_flow.__file__).resolve().parents[2] / "physical" / "die_plan"
    for f, needle in (("qwen_compute/cores/legacy/gen_core_kit_qc.py", 'rec.get("hold_ff_margin", core_flow.HOLD_FF_MARGIN_DEFAULT)'),
                      ("s81/cores/legacy/gen_core_kit_legacy.py", 'rec.get("hold_ff_margin", core_flow.HOLD_FF_MARGIN_DEFAULT)'),
                      ("qwen_kvsys/cores/harden/gen_core_kit_kv.py", "else core_flow.HOLD_FF_MARGIN_DEFAULT"),
                      ("hbm_arch_cores/gen_core_kit_hbm.py", "max(a.hold_margin, core_flow.HOLD_FF_MARGIN_DEFAULT)")):
        p = root / f
        if p.is_file():                                         # sparse checkouts may omit a die
            assert needle in p.read_text(), f
