"""Stage / layer rebalancing levers for the V4.1 index-scan imbalance (tools/v41_stage_rebalance.py): the scenarios
are priced on the design point, the adoption rule is applied as recorded, and the split mutation and the per-die
workloads conserve the scan's work while moving it to the helper stages."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/arch/v41_stage_rebalance.json"
LANES = ROOT / "results/arch/v41_lanes.json"
CTX = ("1048576", "200000")


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_the_design_point_scenario_is_the_lanes_headline(rec):
    """The scenario the design point runs (the adopted plan, or the baseline before adoption) reproduces the lanes
    record's headline batch-1 rates."""
    import v41_stage_rebalance as SR
    dp_name = rec["adopted"] or "baseline"
    assert rec["adopted"] == SR.ADOPTED
    head = json.loads(LANES.read_text())["design_point"]
    for c in CTX:
        for k in ("ar", "mtp"):
            assert rec["scenarios"][dp_name]["batch1"][c][k] == pytest.approx(head[c][k], rel=1e-9), (c, k)


def test_imbalance_is_the_layer20_scan(rec):
    b = rec["scenarios"]["baseline"]["points"]["1048576"]
    for k in ("b1", "fill28", "sat1024"):
        assert b[k]["busiest_stage"] == "14" and b[k]["busiest_over_mean"] > 3
    # the 28-user fill at 1M is stage-bound (below the batch-1 rate) on the design point without a split
    assert b["fill28"]["tokens_s_per_user"] < 0.8 * b["b1"]["tokens_s_per_user"]


def test_recommendation_meets_the_rule(rec):
    r = rec["recommendation"]
    assert r["meets_rule"] and r["scenario"] in r["passing"]
    sc, base = rec["scenarios"][r["scenario"]], rec["scenarios"]["baseline"]
    for c in sc["batch1_sweep"]:
        assert sc["batch1_sweep"][c]["ar"] >= base["batch1_sweep"][c]["ar"] * (1 - 1e-9), c
        # MTP verify passes past 900K engage the ratio-2 helpers the liquid limit needs: a bounded cost
        assert sc["batch1_sweep"][c]["mtp"] >= base["batch1_sweep"][c]["mtp"] * 0.995, c
    # the liquid limit (the V4.1 baseline cooling) holds at every point of the context sweep; the baseline breaks it
    v = sc["verdict"]
    assert v["liquid_at_every_point"] and not v["over_liquid"]
    assert not base["verdict"]["liquid_at_every_point"]
    assert all(r_["liquid"] for rows in sc["cooling_sweep"].values() for r_ in rows.values())
    assert {"200000", "1048576"} <= set(sc["cooling_sweep"])
    # layer 20 alone never slows batch 1 but leaves the ratio-2 homes over liquid with MTP
    l20 = rec["scenarios"]["split_L20_S13_S12"]["verdict"]
    assert l20["batch1_not_slower"] and not l20["liquid_at_every_point"]
    p, q = sc["points"]["1048576"], base["points"]["1048576"]
    # the fill runs at the batch-1 rate again, and the saturated aggregates rise
    assert p["fill28"]["tokens_s_per_user"] == pytest.approx(p["b1"]["tokens_s_per_user"], rel=1e-6)
    for k in ("fill28", "fill28_mtp", "sat1024", "sat1024_mtp"):
        assert p[k]["aggregate_tokens_s"] > 1.3 * q[k]["aggregate_tokens_s"], k
    # the hottest die cools at every 1M point, and the points that exceeded liquid without MTP now fit it
    pw, pb = sc["power"]["1048576"], base["power"]["1048576"]
    for k in pw:
        assert pw[k]["hottest_die_w"] <= pb[k]["hottest_die_w"] + 1e-6, k
    assert pb["saturated_batch1024"]["cooling"] == "exceeds liquid" and pw["saturated_batch1024"]["cooling"] == "liquid"
    # 200K: the helper range starts above it, nothing changes
    for k in ("b1", "fill28", "sat1024"):
        assert sc["points"]["200000"][k]["aggregate_tokens_s"] == pytest.approx(
            base["points"]["200000"][k]["aggregate_tokens_s"], rel=1e-9)


def test_rejected_levers_fail_for_their_stated_reason(rec):
    s = rec["scenarios"]
    assert not s["remap_scan_S13"]["verdict"]["batch1_not_slower"]          # (i): the round trip, no parallel gain
    assert not s["split_all_scans"]["verdict"]["batch1_not_slower"]         # ratio-2 scans shorter than the trip
    assert not s["split_L20_S13_S12_no_engage"]["verdict"]["batch1_not_slower"]   # a helper with too small a share
    assert not s["split_L20_S13_S15"]["verdict"]["batch1_not_slower"]       # switched return with MTP
    assert s["split_L20_S13_local"]["verdict"]["needs"] and s["split_L20_S13_local"]["rom_feasibility"]
    assert s["wide_select_128"]["verdict"]["needs"]


def test_switch_ports_have_room(rec):
    for n, sc in rec["scenarios"].items():
        for c, rows in sc["switch_lane_utilisation"].items():
            for k, v in rows.items():
                assert v["utilisation"] < 0.9, (n, c, k)
    r = rec["scenarios"][rec["recommendation"]["scenario"]]["switch_lane_utilisation"]
    assert max(v["utilisation"] for rows in r.values() for v in rows.values()) < 0.1


def test_fractions_by_position_range():
    import v41_stage_rebalance as SR
    hs = [SR.H(13, 600000, None, "up")]
    assert SR.fractions(hs, 200000) == (1.0, [0.0])
    f0, fr = SR.fractions(hs, 1000000)
    assert f0 == pytest.approx(0.6) and fr == [pytest.approx(0.4)]
    f0, fr = SR.fractions([SR.H(13, 0, None, "local", 0.5)], 1000)
    assert f0 == pytest.approx(0.5)


def test_split_mutation_conserves_the_scan_and_moves_it():
    import v41_stage_rebalance as SR
    import arch_lanes_v41 as AL
    U, A, LX = AL.U, AL.A, AL.LX
    dp = SR._dp()
    plan = SR.PLANS["split_L20_S13_S12"]
    hz = dp["hz"]
    with LX.clock(hz[0]), U.params(**hz[1]):
        r0 = U.solve(dp["sp"], 1048576, batch=1, levers=U.CHAIN_L3, muts=SR.plan_muts(dp, {}))
        r1 = U.solve(dp["sp"], 1048576, batch=1, levers=U.CHAIN_L3, muts=SR.plan_muts(dp, plan))
    g0, g1 = r0["_built"].g, r1["_built"].g
    sc = "L20.attn.idx.score"
    moved = g1.nodes["L20.attn.idx.h13.score"]["issue"] + g1.nodes["L20.attn.idx.h12.score"]["issue"]
    assert g1.nodes[sc]["issue"] + moved == pytest.approx(g0.nodes[sc]["issue"])
    assert g1.nodes["L20.attn.idx.h13.score"]["exec_stage"] == 13
    names = list(g1.nodes)
    for n, nd in g1.nodes.items():                       # insertion order stays topological
        assert all(names.index(d) < names.index(n) for d in nd["deps"]), n
    o0, o1 = A.stage_occupancy(g0), A.stage_occupancy(g1)
    t = lambda o, s: sum(o[s].values())  # noqa: E731
    assert t(o1, 14) < t(o0, 14) and t(o1, 13) > t(o0, 13)
    assert r1["T_s"] <= r0["T_s"]


def test_die_workloads_move_the_scan_ops():
    import v41_stage_rebalance as SR
    import power_scenarios as PS
    import arch_budget_v41 as A
    c = A._env()["c"]
    with SR.using({}):
        o0, _ = PS.v41_die_workloads(A, c, 1048576)
    with SR.using(SR.PLANS["split_L20_S13_S12"]):
        o1, c1 = PS.v41_die_workloads(A, c, 1048576)

    def w(ops, s):
        return sum(x for o, x in ops[s] if o["name"] == "attn.idx.score" and o.get("_layer") == 20)
    assert w(o0, 14) == pytest.approx(1.0) and w(o0, 13) == 0
    assert w(o1, 14) + w(o1, 13) + w(o1, 12) == pytest.approx(1.0) and w(o1, 13) > 0.3 and w(o1, 12) > 0.2
