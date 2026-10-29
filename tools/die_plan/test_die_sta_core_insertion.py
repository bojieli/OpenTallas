"""FLOW-ONEMODEL-3 (COORD 10-28 11:54, S81-14 + QC-15): an early core tap (clock.core_taps 'early') is delivered
core_tap_early_ps before the plain taps on purpose; its endpoint must carry the core's OWN insertion, not the common
latency on both sides.  Gate = signed core view (fail closed without one); --core-insertion declared = plan per-tap
insertion, labelled, never a gate PASS; the kit contract measures arrival + declared earliness (late core pin)."""
import json

import pytest

import die_sta_related as R
from test_corelat import pair_with_core

REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=60.0, setup_ps=5.6, hold_ps=22.2)
CORE, PLAIN, OTHER = "t_pfa__clk_c0", "t_pfa__clk", "t_pfb__clk"


def _plan(early=True):
    raw = pair_with_core(430.0, 350.0)          # core tap clk_c0: insertion TT 430 / FF 350 -> early 180 / 147.5
    if not early:
        raw["partition_types"]["fa"]["clock"].pop("core_taps")
    raw["partition_types"]["fa"]["hard_cores"] = [{"inst": "u_c", "module": "cmod", "origin_um": [200.0, 800.0],
                                                   "outline_um": [200.0, 200.0]}]
    return raw


def _taps(corner="TT", core_early=None):
    """plain taps at 1000/990 TT (800/792 FF); the core tap delivered `core_early` (default: as planned) earlier"""
    pl, pe = (1000.0, 990.0) if corner == "TT" else (800.0, 792.0)
    e = core_early if core_early is not None else (180.0 if corner == "TT" else 147.5)
    t = lambda port, part, l, ee: dict(port=port, part=part, late_ps=l, early_ps=ee, slew_ps=20.0, cppr_node="h0",
                                       xy_um=[300.0, 900.0])
    return {CORE: t(CORE, "pfa", pl - e, pe - e), PLAIN: t(PLAIN, "pfa", pl, pe), OTHER: t(OTHER, "pfb", pl, pe)}


def test_early_core_map_reads_plan_insertion():
    m = R.early_core_map(_plan(), _taps())
    assert list(m) == [CORE]
    r = m[CORE][0]
    assert (r["part"], r["inst"], r["module"]) == ("pfa", "u_c", "cmod")
    assert r["ins_ps"] == {"TT": 430.0, "FF": 350.0}
    assert r["early_ps"]["TT"] == 180.0 and r["early_ps"]["FF"] == pytest.approx(147.5)
    assert R.early_core_map(_plan(early=False), _taps()) == {}


def _intra(views=None, kit_offset=None, corner="TT", core_early=None):
    taps = _taps(corner, core_early)
    pairs = [(a, b, "pfa") for a, b in ((CORE, PLAIN), (PLAIN, CORE))]
    return R.time_class(pairs, taps, {"h0": 10.0}, REG, 20.0, 833.333, 60.0, 25.0, views=views,
                        hold_window=dict(ps=0.0, basis="t"), kit_offset=kit_offset)


def test_early_tap_fixture_declared_insertion_removes_planned_earliness():
    ecm = R.early_core_map(_plan(), _taps())
    old = _intra()                                           # pre-fix: common latency both sides
    # core launches 180 early: hold = (810 + 60) - (1000 + 22.2) - 25 + 10
    assert old["worst_hold_slack_ps"] == round(810 + 60 - 1000 - 22.2 - 25 + 10, 2)
    v = {p: [R.budget_model(REG, 250.0)] for p in _taps()}
    v, rec = R.core_tap_views(v, ecm, "TT", REG, {}, "declared")
    assert rec["source"] == dict(view=0, declared=1, missing=0) and v[CORE][0]["name"] == "declared:cmod"
    new = _intra(views=v)
    # own insertion: core pin 810 + 430 = plain pin 990 + 250 -> the pair is timed as an aligned pair
    assert new["worst_hold_slack_ps"] == round(810 + 430 + 60 - (1000 + 250) - 22.2 - 25 + 10, 2)
    assert new["worst_hold_slack_ps"] > 0 > old["worst_hold_slack_ps"]
    assert R.core_insertion_verdict("PASS", [rec]) == "DECLARED"          # never a gate PASS
    assert R.core_insertion_verdict("FAIL", [rec]) == "FAIL"


def test_early_tap_view_model_and_missing_view_fail_closed():
    ecm = R.early_core_map(_plan(), _taps())
    core = dict(name="core:cmod", real=True, lat_late=0.0, lat_early=0.0, clkq_max=498.0, clkq_min=490.0,
                setup=-424.4, hold=452.2, meta={})                  # ETM arcs hold the core's 430 insertion
    base = {p: [R.budget_model(REG, 250.0)] for p in _taps()}
    v, rec = R.core_tap_views(dict(base), ecm, "TT", REG, {"cmod": core}, "view")
    assert v[CORE] == [core] and rec["source"] == dict(view=1, declared=0, missing=0)
    r = _intra(views=v)
    assert r["worst_hold_slack_ps"] == round(810 + 490 - (1000 + 250) - 22.2 - 25 + 10, 2) > 0
    assert R.core_insertion_verdict("PASS", [rec]) == "PASS"
    # no view for the core: the tap keeps the common latency, listed missing, verdict BLOCKED(kits) (OWNER 12.19;
    # never PASS, a FAIL stays FAIL)
    v2, rec2 = R.core_tap_views(dict(base), ecm, "TT", REG, {}, "view")
    assert v2[CORE] == base[CORE] and rec2["source"]["missing"] == 1 and rec2["missing_taps"] == [CORE]
    assert R.core_insertion_verdict("PASS", [rec2]) == "BLOCKED(kits)"
    assert R.core_insertion_verdict("FAIL", [rec2]) == "FAIL"
    # declared mode never hides a missing declared insertion (0 ps = not declared)
    ecm0 = {CORE: [dict(ecm[CORE][0], ins_ps=dict(TT=0.0, FF=0.0))]}
    assert R.core_tap_views(dict(base), ecm0, "TT", REG, {}, "declared")[1]["source"]["missing"] == 1
    with pytest.raises(ValueError):
        R.core_tap_views(dict(base), ecm, "TT", REG, {}, "nominal")


def test_kit_contract_charges_late_core_tap_not_planned_earliness():
    off = {CORE: 180.0}
    planned = _intra(kit_offset=off)["kit_contract_hold"]
    assert planned["window_needed_ps"] == 0.0 and planned["verdict"] == "PASS"
    assert planned["core_tap_offset"]["taps"] == 1
    assert _intra()["kit_contract_hold"]["window_needed_ps"] == 180.0      # pre-fix: planned earliness = damage
    late = _intra(kit_offset=off, core_early=0.0)["kit_contract_hold"]       # no early delivery: core pin 180 late
    assert late["window_needed_ps"] == 180.0 and late["verdict"] == "FAIL"



def test_skew_diag_is_arrival_minus_planned_target():
    """DIE-S81-18 (COORD 10-28 rule 2): the skew report subtracts the planned target (early core tap earliness);
    the raw tap-arrival number stays as skew_raw_max_ps.  Without early core taps both are identical."""
    off = {CORE: 180.0}
    raw = _intra()
    assert raw["skew_raw_max_ps"] == raw["skew_diag_max_ps"]              # no offsets: raw == target-relative
    assert raw["skew_diag_max_ps"] >= 180.0                               # planned earliness counted as skew
    planned = _intra(kit_offset=off)
    assert planned["skew_raw_max_ps"] == raw["skew_raw_max_ps"]
    assert planned["skew_diag_max_ps"] == round(raw["skew_diag_max_ps"] - 180.0, 2)   # only the late/early spread
    assert planned["skew_diag_over_80"] == 0 and "planned target" in planned["skew_diag_basis"]
    late = _intra(kit_offset=off, core_early=60.0)                       # delivered 120 ps less early than planned
    assert late["skew_diag_max_ps"] == round(planned["skew_diag_max_ps"] + 120.0, 2)
    assert late["worst_skew"][0][0] == late["skew_diag_max_ps"]

def _run(tmp_path, monkeypatch, plan, *extra, core_view_model=None):
    monkeypatch.setattr(R, "characterise", lambda *a, **k: dict(REG))
    if core_view_model is not None:
        monkeypatch.setattr(R, "core_view_model", core_view_model)
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    proof = tmp_path / "proof"
    proof.mkdir(exist_ok=True)
    for c in ("TT", "FF"):
        (proof / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(taps=list(_taps(c).values()),
                                                                      cppr_node_range_ps={"h0": 10.0, "h": 10.0},
                                                                      clock_cell="buf")))
    out = tmp_path / ("o" + "_".join(x.strip("-") for x in extra))
    assert R.main([str(proof), "--plan", str(pf), "--out", str(out), "--corner", "TT", "--corner", "FF",
                   "--data-droop", "none", *extra]) == 0
    return json.loads((out / "die_sta_related.json").read_text())


def test_main_fail_closed_declared_and_view(tmp_path, monkeypatch):
    r = _run(tmp_path, monkeypatch, _plan())                               # gate default: view, none given
    g = r["summary"]
    assert g["core_insertion"]["verdict"] == "BLOCKED(kits)" and g["intra"]["verdict"] == "BLOCKED(kits)"
    assert g["intra"]["hold_status"] == "BLOCKED(kits)" and "core:cmod" in g["intra"]["missing_views"]
    assert g["core_insertion"]["source"]["FF"] == dict(view=0, declared=0, missing=1)
    assert "missing 1" in r["corners"]["FF"]["classes"]["intra"]["label"]
    d = _run(tmp_path, monkeypatch, _plan(), "--core-insertion", "declared")
    assert d["summary"]["core_insertion"]["verdict"] == "DECLARED"
    # a declared pass is not a gate PASS; with no signed view at all the hold is BLOCKED(kits) (OWNER 12.19)
    assert d["summary"]["intra"]["verdict"] == "BLOCKED(kits)"
    assert d["summary"]["intra"]["hold_pairs_measured"] == 0
    assert d["corners"]["FF"]["classes"]["intra"]["worst_hold_slack_ps"] > 0
    assert d["corners"]["FF"]["classes"]["intra"]["kit_contract_hold"]["verdict"] == "PASS"
    assert "declared 1" in d["corners"]["TT"]["classes"]["intra"]["label"]

    def cvm(module, vd, corner, load_ff, pdel):
        ins = 430.0 if corner == "TT" else 350.0
        return dict(name=f"core:{module}", real=True, lat_late=pdel, lat_early=pdel, clkq_max=ins + 68.0,
                    clkq_min=ins + 60.0, setup=5.6 - ins, hold=22.2 + ins, meta={}, etm={})
    v = _run(tmp_path, monkeypatch, _plan(), "--core-view", "cmod=/nonexistent", "--no-core-view-match-pins",
             core_view_model=cvm)
    assert v["summary"]["core_insertion"]["verdict"] == "PASS"
    assert v["summary"]["core_insertion"]["source"]["TT"] == dict(view=1, declared=0, missing=0)
    assert v["corners"]["FF"]["classes"]["intra"]["worst_hold_slack_ps"] > 0
    assert v["corners"]["TT"]["real_view_coverage"]["early_core_tap_instances"] == 1


def test_main_plan_without_early_core_taps_unchanged(tmp_path, monkeypatch):
    r = _run(tmp_path, monkeypatch, _plan(early=False))
    assert "core_insertion" not in r["summary"] and "core_insertion" not in r["corners"]["TT"]
    assert r["corners"]["TT"]["classes"]["intra"]["label"] == "declared-budget"
    assert "real_view" not in r["corners"]["TT"]["classes"]["intra"]


def test_early_core_map_minimal_plan_skips_schema_parse():
    # CA-OCV-style minimal plan (no 'die'): no early core taps -> {} without a schema.Plan parse (RM188 hold)
    assert R.early_core_map(dict(partition_types={"fa": {"clock": {}}}, partitions=[], ports=[]), _taps()) == {}
    assert R.early_core_map(dict(partitions=[], ports=[]), _taps()) == {}
