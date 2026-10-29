"""HEAD-START-4 V1 tests: opt-in per-start-port MEASURED data delay (launch CLK -> capture D) in count_align_plan
(--start-data-delay) and die_sta_related (--count-align-start-data-delay).  The clock-only START model samples
d = capture clock - launch clock; the start bit reaches the capture D dd later, so the sync samples d - dd
(HEAD-START-3 root cause: dd 141-601 ps TT, all 513 as-built fails had dd > the plan's skew limit)."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_count_align_starttree as ST  # noqa: E402
import count_align_bind as CAB  # noqa: E402
import die_sta_related as DSR  # noqa: E402

cap = ST.cap
T, AP = ST.T, ST.AP
KEEP = ("port", "src", "dst", "launch", "capture", "retime", "clean_ok", "d_ps", "p_dn_ps", "p_up_ps", "lo", "hi")


ZERO = dict(lo_ps=(0.0, 0.0), hi_ps=(0.0, 0.0))     # candidate ports of the contraction / retime search: dd 0
HOP = 1e6                                            # geometry on, no reach limit (the hop model needs hop_um)


def plan_with(dd=None, hop=HOP):
    rows = ST.chain_rows()
    ctx = ST.ctx_chain()
    root, edges, info = cap.clock_start_edges(rows, ctx, max_hop_um=hop, data_delay=dd)
    s, out, regs = cap.plan(rows, T, AP, 0.05, start_edges=edges, start_root=root)
    return rows, ctx, root, edges, info, s, out, regs


def bind_of(s, out, regs, edges):
    doc = dict(summary=dict(s, period_ps=T, pad=0), regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    return CAB.bind(doc)


def gate(b, ctx, dd=None):
    k = ctx["TT"]
    taps = {q: t for q, t in k["taps"].items() if not q.startswith("__st__")}
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    try:
        kw = {} if dd is None else dict(data_delay=dd)
        return {r["port"]: r for r in DSR.count_align_start_ports(b, taps, k["meta"], T, {}, k["ocv"], **kw)}
    finally:
        DSR.CPPR_LCA = old


def test_default_none_is_unchanged():
    a = plan_with(None, None)
    rows = ST.chain_rows()
    root, edges, info = cap.clock_start_edges(rows, ST.ctx_chain())
    assert a[2] == root and a[4] == info
    assert json.dumps(a[3], sort_keys=True, default=str) == json.dumps(edges, sort_keys=True, default=str)
    assert all("data_delay_ps" not in e for e in edges) and "data_delay" not in info


def test_zero_delay_keeps_every_choice():
    _, _, root0, e0, _, s0, _, regs0 = plan_with(None)
    ports = {e["port"]: (0.0, 0.0) for e in e0}
    _, _, root1, e1, info1, s1, _, regs1 = plan_with(dict(ports=ports, model=ZERO))
    assert root0 == root1
    assert [{k: e[k] for k in KEEP} for e in e0] == [{k: e[k] for k in KEEP} for e in e1]
    assert [g["start_from"] for g in regs0 if g["start_from"]] == \
        [{k: v for k, v in g["start_from"].items() if k not in ("clock_interval_ps", "data_delay_ps", "data_delay_source")}
         for g in regs1 if g["start_from"]]
    assert info1["data_delay"]["measured"] == len(e1) and info1["data_delay"]["modelled"] == 0


def test_interval_shifts_by_measured_delay():
    rows = ST.chain_rows()
    root, e0, _ = cap.clock_start_edges(rows, ST.ctx_chain())
    r = dict(e0[0], hop_um=123.0)
    q = cap.shift_data_delay(r, 150.0, 400.0, "measured")
    assert q["d_ps"] - q["p_dn_ps"] == pytest.approx(r["d_ps"] - r["p_dn_ps"] - 400.0)
    assert q["d_ps"] + q["p_up_ps"] == pytest.approx(r["d_ps"] + r["p_up_ps"] - 150.0)
    if r.get("fall_lo") is not None:
        assert q["fall_lo"] == pytest.approx(r["fall_lo"] - 400.0) and q["fall_hi"] == pytest.approx(r["fall_hi"] - 150.0)
    assert q["data_delay_ps"] == [150.0, 400.0] and q["data_delay_source"] == "measured"
    lo, hi, src = cap.data_delay_of(dict(ports={}, model=dict(lo_ps=(10.0, 0.5), hi_ps=(20.0, 1.0))), "x", r)
    assert (lo, hi, src) == (10.0 + 61.5, 20.0 + 123.0, "model")
    assert cap.data_delay_of(dict(ports={}, model=None), "x", r) is None


def test_clock_only_plan_fails_gate_with_measured_delay_v1_plan_passes():
    """the HEAD-START-3 root cause in miniature: a clock-only plan's edges fail the gate once the real data delay is
    timed; the V1 plan (same dd) picks edges/J on d - dd and passes the same gate"""
    _, ctx, _, e0, _, s0, out0, regs0 = plan_with(None)
    b0 = bind_of(s0, out0, regs0, e0)
    assert all(r["ok"] for r in gate(b0, ctx).values())                 # clock-only gate: PASS (blind to dd)
    # dd that moves each port's sampled phase onto its clock-only sampling boundary
    dd = {}
    for e in e0:
        g = next(g for g in regs0 if g["start_from"] and g["start_from"]["port"] == e["port"])
        off = T / 2 if g["start_from"]["edge"] == "fall" else 0.0
        sh = (e["d_ps"] - off) % T                                     # d - sh = off (mod T)
        dd[e["port"]] = (sh - 20.0, sh + 20.0)
    g0 = gate(b0, ctx, dd)
    assert sum(not r["ok"] for r in g0.values()) == len(e0)           # mutant (no data path in the plan): all FAIL
    assert all(r["skew_source"] == "measured-data-delay" for r in g0.values())
    _, _, _, e1, info1, s1, out1, regs1 = plan_with(dict(ports=dd, model=ZERO))
    assert {e["port"] for e in e1} == set(dd)
    assert s1["start_tree"]["start_fail"] == 0
    b1 = bind_of(s1, out1, regs1, e1)
    g1 = gate(b1, ctx, dd)
    assert all(r["ok"] for r in g1.values())
    flips = sum(1 for a, b in zip(regs0, regs1) if a["start_from"] and a["start_from"]["edge"] != b["start_from"]["edge"])
    assert flips >= 1


def test_gate_fails_closed_without_measured_row():
    _, ctx, _, e0, _, s0, out0, regs0 = plan_with(None)
    b0 = bind_of(s0, out0, regs0, e0)
    dd = {e["port"]: (0.0, 0.0) for e in e0[1:]}
    g = gate(b0, ctx, dd)
    assert g[e0[0]["port"]]["ok"] is False and "no measured START data delay" in g[e0[0]["port"]]["reason"]
    assert all(g[e["port"]]["ok"] for e in e0[1:])


def test_planner_fails_closed_without_row_or_model(tmp_path):
    rows = ST.chain_rows()
    root, e, info = cap.clock_start_edges(copy.deepcopy(rows), ST.ctx_chain(), data_delay=dict(ports={}, model=None))
    s, _, _ = cap.plan(copy.deepcopy(rows), T, AP, 0.05, start_edges=e, start_root=root)
    assert info["data_delay"]["missing"] == len(e) and not any(x["clean_ok"] for x in e)
    assert s["start_tree"]["start_fail"] == len(e)              # unmeasured START ports FAIL the plan (fail closed)
    with pytest.raises(ValueError):              # hop model needs the hop geometry (--start-max-hop-um)
        cap.clock_start_edges(rows, ST.ctx_chain(), data_delay=dict(ports={}, model=dict(lo_ps=(0, 0), hi_ps=(0, 0))))
    root, e, info = cap.clock_start_edges(rows, ST.ctx_chain(), max_hop_um=1e6,
                                          data_delay=dict(ports={}, model=dict(lo_ps=(0.0, 0.0), hi_ps=(0.0, 0.0))))
    assert info["data_delay"]["modelled"] == len(e)
    f = tmp_path / "dd.json"
    f.write_text(json.dumps(dict(ports={"p": [3, 1]})))
    with pytest.raises(ValueError):
        cap.load_start_data_delay(str(f))


def test_cli_needs_clock_tree(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(dict(corners={"TT_x": dict(all=ST.chain_rows())})))
    d = tmp_path / "dd.json"
    d.write_text(json.dumps(dict(ports={})))
    with pytest.raises(SystemExit):
        cap.main([str(f), "--corner", "TT_x", "--start-data-delay", str(d)])


def test_same_corner_subtraction_excludes_impossible_combinations():
    r = dict(d_ps=300., p_dn_ps=200., p_up_ps=200., fall_lo=200., fall_hi=600.)
    corners = dict(TT=(400., 500., 500., 600.), FF=(100., 200., 200., 300.))
    dd = dict(TT=(300., 350.), FF=(0., 50.))
    q = cap.shift_corner_data_delay(r, corners, dd)
    assert q["d_ps"]-q["p_dn_ps"] == pytest.approx(50.)
    assert q["d_ps"]+q["p_up_ps"] == pytest.approx(200.)
    assert (q["fall_lo"], q["fall_hi"]) == (150., 300.)
    # The old cross-corner hull would invent [-250,500] and lose clean edges.
    mutant = cap.shift_data_delay(r, 0., 350., "measured")
    assert mutant["d_ps"]-mutant["p_dn_ps"] == -250.
    assert mutant["d_ps"]+mutant["p_up_ps"] == 500.


def test_corner_document_validation_and_missing_corner_fail_closed(tmp_path):
    f = tmp_path / "dd.json"
    f.write_text(json.dumps(dict(ports={"x": [1., 10.]}, corners={"TT": {"x": [4., 10.]}})))
    doc = cap.load_start_data_delay(f)
    assert cap.start_data_delay_for_corner(doc, "TT") == {"x": (4., 10.)}
    assert cap.start_data_delay_for_corner(doc, "FF") == {}
    assert cap.start_data_delay_for_corner(dict(ports={"x": (1., 10.)}), "FF") == {"x": (1., 10.)}
    f.write_text(json.dumps(dict(corners={"TT": {"x": [10., 4.]}})))
    with pytest.raises(ValueError):
        cap.load_start_data_delay(f)


def test_clock_start_plan_missing_one_corner_fails_closed():
    _, _, _, e0, _, _, _, _ = plan_with(None)
    ports = {e["port"]: (0., 0.) for e in e0}
    rows = ST.chain_rows()
    ctx = ST.ctx_chain()
    # The only context corner is TT; a document measured at FF cannot reuse its
    # union interval or candidate model for already-measured ports.
    _, edges, info = cap.clock_start_edges(rows, ctx, max_hop_um=HOP,
        data_delay=dict(ports=ports, model=None, corners=dict(FF=ports)))
    assert info["data_delay"]["missing"] > 0
    assert not any(e["clean_ok"] for e in edges)


def test_corner_model_predicts_candidates_but_does_not_qualify_the_gate():
    _, _, _, _, _, s0, _, _ = plan_with(None)
    ctx = ST.ctx_chain()
    doc = dict(ports={}, model=None, corners={}, corner_models={c: ZERO for c in ctx})
    root, edges, info = cap.clock_start_edges(ST.chain_rows(), ctx, max_hop_um=HOP, data_delay=doc)
    s, out, regs = cap.plan(ST.chain_rows(), T, AP, .05, start_edges=edges, start_root=root)
    assert info["data_delay"]["modelled"] == len(edges)
    assert s["start_tree"]["start_fail"] == s0["start_tree"]["start_fail"] == 0
    assert all(not r["ok"] for r in gate(bind_of(s, out, regs, edges), ctx, {}).values())
