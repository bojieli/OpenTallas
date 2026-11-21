"""R-REACH-5 (S81-STRIP 11-17): half-cycle (mixed-edge) hops reach HALF_REACH_UM; START raw resets name same-edge
leaf taps when the plan has no START broadcast."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reach_rules as RR  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
from test_reach_rules import _start_plan, _P  # noqa: E402


def _neg(p):
    p = copy.deepcopy(p)
    p["reset"]["release"] = "wavefront"
    p["reset"]["relay_lockup"] = dict(form="negedge", types=["mid"])
    return p


def _stages(t):
    return [st for _k, _b, _i, st in RR._start_stages(t)]


TREE = dict(relays=[dict(name="u_rrl_5", d="rst_root_n", q="rst_rl_5", xy=[100.0, 100.0], tap=None)])


def test_half_cycle_raw_hop_limit_and_same_edge_tap(monkeypatch):
    p = _neg(_start_plan())                  # negedge lockup excludes the START broadcast (reset_tree.relay_lockup)
    P = _P(p)
    t = P.types["mid"]
    monkeypatch.setattr(RT, "consumer_taps", lambda P_, tn: [("t0", 100.0, 100.0), ("t1", 900.0, 900.0)])
    monkeypatch.setattr(RT, "for_type", lambda P_, tn, reach=None: copy.deepcopy(TREE))
    t["clock"]["landing_reader_start"] = dict(depth=1, branches=dict(
        f0=dict(stages=[dict(xy_um=[100.0, 300.0], raw_reset="rst_rl_5")]),        # 200 um, falling relay -> posedge
        f1=dict(stages=[dict(xy_um=[100.0, 250.0], raw_reset="rst_n_t0")])))       # 150 um, plain leaf tap
    t["clock"]["landing_local_resets"] = [dict(name="fstart_face_q", raw="rst_rl_5", xy_um=[260.0, 100.0],
                                               consumers=["u_cland_fstart_q"])]   # 160 um half cycle: passes
    assert RR.negedge_type(P, "mid")
    hops = {h[0]: h for h in RR.raw_hops(P, t, "mid")}
    assert hops["reader_start:f0:0"][2:] == ("half", 200.0, RR.HALF_REACH_UM)
    assert hops["reader_start:f1:0"][2:] == ("same", 150.0, RR.REACH_UM)
    assert hops["local_reset:fstart_face_q"][2:] == ("half", 160.0, RR.HALF_REACH_UM)
    row, fs = RR.edge_findings(P, t, "mid")
    assert [f["kind"] for f in fs] == ["edge_reach"] and fs[0]["value"] == 200.0 and fs[0]["limit"] == 180.0
    assert row["raw_half"] == 2 and row["raw_over"] == 1
    # the same hop at 170 um passes; without the negedge lockup the 200 um hop is a full-cycle hop and passes too
    t["clock"]["landing_reader_start"]["branches"]["f0"]["stages"][0]["xy_um"] = [100.0, 270.0]
    assert RR.edge_findings(P, t, "mid")[1] == []
    t["clock"]["landing_reader_start"]["branches"]["f0"]["stages"][0]["xy_um"] = [100.0, 300.0]
    p2 = copy.deepcopy(P.raw)
    p2["reset"].pop("relay_lockup")
    P2 = _P(p2)
    assert not RR.negedge_type(P2, "mid") and RR.edge_findings(P2, P2.types["mid"], "mid")[1] == []
    # fix: the half-cycle stage is re-pointed to the nearest same-edge leaf tap (rst_n_t0, 200 um, full cycle)
    rep = RR._fix_raw_edges(P, t, "mid", dict(changed=[]))
    assert rep["raw_repoints"] == 1 and t["clock"]["landing_reader_start"]["branches"]["f0"]["stages"][0]["raw_reset"] \
        == "rst_n_t0" and RR.edge_findings(P, t, "mid")[1] == []


def test_rr_t_without_broadcast_is_missing_and_fix_repoints_to_leaf_taps(monkeypatch):
    p = _neg(_start_plan())                                     # S81 form: wavefront, no START broadcast
    t = p["partition_types"]["mid"]
    P = _P(p)
    taps = [(f"t{i}", 100.0 + 200.0 * (i % 5), 100.0 + 200.0 * (i // 5)) for i in range(25)]    # 200 um grid
    monkeypatch.setattr(RT, "consumer_taps", lambda P_, tn: list(taps))
    rep = RR.fix_start(P, t, "mid")
    assert "landing_reader_start" in rep["changed"]
    raws = {st["raw_reset"] for st in _stages(t)}
    assert raws and all(r.startswith("rst_n_t") for r in raws)   # fixed plans name existing same-edge leaf taps
    assert RR.edge_findings(P, t, "mid")[1] == []
    # a plan made by the old tool (rr_t names) is repaired by a second fix run, and that run is idempotent
    for st in _stages(t):
        st["raw_reset"] = "rr_t" + st["raw_reset"][len("rst_n_t"):]
    kinds = [f["kind"] for f in RR.edge_findings(P, t, "mid")[1]]
    assert kinds == ["start_raw_net"]
    rep2 = RR.fix_start(P, t, "mid")
    assert rep2["changed"] == ["raw_reset"] and rep2["raw_repoints"] == len(_stages(t))
    assert RR.edge_findings(P, t, "mid")[1] == []
    assert RR.fix_start(P, t, "mid")["changed"] == []
    assert schema.validate(p) == []


def test_raw_hop_the_nearest_tap_cannot_close_is_not_fixed(monkeypatch):
    p = _neg(_start_plan())
    t = p["partition_types"]["mid"]
    P = _P(p)
    monkeypatch.setattr(RT, "consumer_taps", lambda P_, tn: [("t0", 100.0, 100.0)])
    t["clock"]["landing_reader_start"] = dict(depth=1, branches=dict(
        f0=dict(stages=[dict(xy_um=[100.0, 600.0], raw_reset="rr_t0")])))
    monkeypatch.setattr(RR, "start_findings", lambda t_, tn, reach=RR.REACH_UM: ({}, []))
    with pytest.raises(ValueError, match="stay over their edge reach"):
        RR.fix_start(P, t, "mid")


def test_tree_half_hops_counts_falling_edge_launches():
    T = dict(relay_lockup="negedge", relays=[
        dict(name="u_rrl_0", d="rst_root_n", q="rst_rl_0", xy=[0.0, 0.0], tap=None),
        dict(name="u_rrl_1", d="rst_rl_0", q="rst_rl_1", xy=[300.0, 0.0], tap=None),     # nl -> nl, 300 um
        dict(name="u_rrl_2", d="rst_rl_1", q="rst_n_t0", xy=[400.0, 0.0], tap=0)],       # nl -> leaf, 100 um
        taps=[(0, 400.0, 0.0)])
    hops = RR.tree_half_hops(None, "mid", T)
    assert hops == [(300.0, "u_rrl_0", "u_rrl_1"), (100.0, "u_rrl_1", "u_rrl_2")]
    T["relay_lockup"] = None
    assert RR.tree_half_hops(None, "mid", T) == []


@pytest.mark.parametrize("lowered", [False, True])
def test_kit_relay_phase_controls_start_and_tree_reach(monkeypatch, lowered):
    raw = _neg(_start_plan())
    t = raw["partition_types"]["mid"]
    if lowered:
        t["reset_relay_full"] = True
    P = _P(raw)
    tree = dict(relay_lockup="negedge", taps=[(0, 200.0, 0.0)], relays=[
        dict(name="u_rrl_5", d="rst_root_n", q="rst_rl_5", xy=[0.0, 0.0], tap=None),
        dict(name="u_rrl_6", d="rst_rl_5", q="rst_n_t0", xy=[200.0, 0.0], tap=0)])
    monkeypatch.setattr(RT, "for_type", lambda *_: tree)
    t["clock"]["landing_reader_start"] = dict(branches=dict(f0=dict(stages=[
        dict(raw_reset="rst_rl_5", xy_um=[200.0, 0.0]),
        dict(raw_reset="rst_rl_5", xy_um=[RR.REACH_UM + 1.0, 0.0]),
        dict(raw_reset="rst_rl_99", xy_um=[0.0, 0.0])])))
    row, findings = RR.edge_findings(P, t, "mid", tree_hops=True)
    assert row["negedge"] is (not lowered)
    assert row["raw_missing"] == 1
    assert row["raw_half"] == (0 if lowered else 2)
    assert row["raw_over"] == (1 if lowered else 2)
    assert RR.tree_half_hops(P, "mid", tree) == ([] if lowered else [(200.0, "u_rrl_5", "u_rrl_6")])
    assert {f["kind"]: f["limit"] for f in findings} == (
        {"start_raw_net": 0, "edge_reach": RR.REACH_UM} if lowered else
        {"start_raw_net": 0, "edge_reach": RR.HALF_REACH_UM, "reset_half_cycle": RR.HALF_REACH_UM})


def test_start_export_reset_uses_emitted_site_beyond_consumer_taps(monkeypatch):
    raw = _neg(_start_plan())
    raw["reset"].pop("relay_lockup")
    raw["reset"]["start"] = "broadcast"
    plan = _P(raw)
    t = plan.types["mid"]
    tree = dict(
        n_reset_consumers=1, outs=[[100.0, 200.0]], start=True,
        relays=[
            dict(name="u_rrl_0", d="rst_root_n", q="rst_n_t0", xy=[0.0, 0.0], kind="tap", depth=1),
            dict(name="u_rrl_1", d="rst_root_n", q="rst_n_t1", xy=[100.0, 200.0], kind="tap", depth=1),
        ],
    )
    monkeypatch.setattr(RT, "consumer_taps", lambda *_: [("t0", 0.0, 0.0)])
    t["clock"]["landing_reader_start"] = dict(branches=dict(f0=dict(stages=[
        dict(raw_reset="rr_t1", xy_um=[100.0, 250.0]),
        dict(raw_reset="rr_t2", xy_um=[100.0, 250.0]),
    ])))
    assert RR.raw_hops(plan, t, "mid", tree) == [
        ("reader_start:f0:0", "rr_t1", "same", 50.0, RR.REACH_UM),
        ("reader_start:f0:1", "rr_t2", "missing", None, 0.0),
    ]
