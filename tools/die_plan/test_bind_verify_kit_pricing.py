"""VERIFY-PRICING-1 11-12: bind verify credits the source-kit stations a kit_source_station_pricing bind priced in the
lane but left to the source kit (S81 out_r12bA_dst: 3966 sinks short by exactly that count), from the same station
source as the as-built lane check (lane_asbuilt_latency, LATCHECK-1).  A real depth error must still fail."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_verify as V  # noqa: E402
import lane_asbuilt_latency as LAL  # noqa: E402
from bind import Graph, Rules  # noqa: E402
from test_lane_asbuilt_latency import dst_rtl, module, plan, src_rtl  # noqa: E402

LEAF = "p.u_leaf.y[0]"


def _st(path, d, q):
    return N(path=path, module="ot_dp_st", kind="leaf", params={},
             ports={"clk": [90], "rst_n": [91], "d": [d], "ea": [92], "q": [q], "eq": [93]},
             dirs={"clk": "input", "rst_n": "input", "d": "input", "ea": "input", "q": "output", "eq": "output"})


def _leaf(path, port, net, d):
    return N(path=path, module="lf", kind="leaf", params={}, ports={port: [net]}, dirs={port: d})


def _graph():
    """p.u_leaf.y -> p.u_bout_o -> q.u_bin_i -> q.u_sink (lane L0, bus o -> i)
                  -> p.u_bout_x -> q.u_bin_x -> q.u_sink2 (unpriced bus x)
       q.u_bin_i -> q.u_bout_f -> r.u_bin_f -> r.u_sink3 (forwarded on lane L1, bus f)"""
    cells = [_leaf("p.u_leaf", "y", 1, "output"), _st("p.u_bout_o", 1, 2), _st("q.u_bin_i", 2, 3),
             _leaf("q.u_sink", "a", 3, "input"), _st("p.u_bout_x", 1, 5), _st("q.u_bin_x", 5, 6),
             _leaf("q.u_sink2", "a", 6, "input"), _st("q.u_bout_f", 3, 7), _st("r.u_bin_f", 7, 8),
             _leaf("r.u_sink3", "a", 8, "input")]
    errs = []
    G = Graph(N(cells=cells, const_drivers={}, top_ports={}), Rules(V.VERIFY_RULES), errs)
    assert not errs
    return G


def _cmp(G, kit, net, want_stages):
    """the verify sink compare (cmd_verify): gdesc of the traced pin + kit credit, then want[:3] == got[:3]"""
    s = G.source(net)
    assert s[0] == "pin" and G.F.cells[s[1]].path == "p.u_leaf"
    got = ["pin", LEAF, s[4], False]
    got, kc, raw, lanes = kit.adjust(s, got, net)
    want = ["pin", LEAF, want_stages, False]
    return want[:3] == got[:3], kc, raw, lanes


def test_switch_on_credits_the_priced_source_stations():
    G = _graph()
    kit = V.KitSourceCredit(G, {("p", "o"): (2, "L0")})
    assert kit.unmatched == []
    # bind_sinks wants the full lane (2 boundary + 2 kit source stations); the bound RTL has the 2 boundary flops
    ok, kc, raw, lanes = _cmp(G, kit, 3, 4)
    assert (ok, kc, raw[2], lanes) == (True, 2, 2, ("L0",))


def test_switch_on_unpriced_bus_is_unchanged():
    G = _graph()
    kit = V.KitSourceCredit(G, {("p", "o"): (2, "L0")})
    assert _cmp(G, kit, 6, 2)[:2] == (True, 0)
    assert _cmp(G, kit, 6, 4)[0] is False         # a short unpriced lane still fails


def test_switch_off_credits_nothing():
    G = _graph()
    kit = V.KitSourceCredit(G, {})
    assert kit.cells == {}
    assert _cmp(G, kit, 3, 2)[:2] == (True, 0)    # OFF: the receiver pad holds the stations, bound == want
    assert _cmp(G, kit, 3, 4)[0] is False         # OFF with the stations missing: still a mismatch (old behaviour)


def test_planted_real_mismatch_still_fails():
    G = _graph()
    kit = V.KitSourceCredit(G, {("p", "o"): (2, "L0")})
    ok, kc, raw, _ = _cmp(G, kit, 3, 5)            # bound short by 3, only 2 are kit source stations
    assert (ok, kc, raw[2]) == (False, 2, 2)
    ok, kc, _, _ = _cmp(G, kit, 3, 2)              # bound already holds the stations: the credit exposes the double count
    assert (ok, kc) == (False, 2)


def test_forwarded_chain_sums_both_faces_and_unmatched_face_is_reported():
    G = _graph()
    kit = V.KitSourceCredit(G, {("p", "o"): (2, "L0"), ("q", "f"): (1, "L1"), ("z", "w"): (3, "L9")})
    assert kit.unmatched == ["z.u_bout_w"]
    ok, kc, _, lanes = _cmp(G, kit, 8, 7)          # 4 boundary flops + 2 + 1
    assert (ok, kc, lanes) == (True, 3, ("L0", "L1"))


# ---- the station source: lane_asbuilt_latency.source_cuts == check()'s pricing cut ----------------------------------
def _rows(P):
    return [dict(lane="L0", src="p", dst="q", bus_out="o", bus_in="i", plan_cycles=P["latency"]["lanes"]["L0"]["cycles"])]


def test_source_cuts_match_latcheck_pricing_cut():
    P = plan()
    mods = {"p": LAL.ModuleIndex(src_rtl()), "q": LAL.ModuleIndex(dst_rtl(D=7)), "f": LAL.ModuleIndex("")}
    pt = {p["name"]: p["type"] for p in P["partitions"]}
    cuts = LAL.source_cuts(P, _rows(P), mods.get, pt.get, P["partition_types"], True)
    assert cuts == {("p", "o"): (2, "L0")}
    recs, errs = LAL.check(P, _rows(P), mods.get, pt.get, P["partition_types"], {"L0": 4}.get, pricing="off")
    assert recs[0]["pricing_cut"] == 2               # the two tools agree on the station count
    assert LAL.source_cuts(P, _rows(P), mods.get, pt.get, P["partition_types"], False) == {}
    assert LAL.source_cuts(P, _rows(P), mods.get, pt.get, P["partition_types"], ["R"]) == {}
    assert LAL.source_cuts(P, _rows(P), mods.get, pt.get, P["partition_types"], ["S"]) == {("p", "o"): (2, "L0")}
    mods["p"] = LAL.ModuleIndex(src_rtl(native=2))   # native source stations: in the bound RTL, nothing to credit
    assert LAL.source_cuts(P, _rows(P), mods.get, pt.get, P["partition_types"], True) == {}
    P2 = plan(fixed=1)                               # stations not priced in fixed_cycles: no pad cut, no credit
    assert LAL.source_cuts(P2, _rows(P2), mods.get, pt.get, P2["partition_types"], True) == {}


def test_kit_source_cuts_reads_a_bind_dir(tmp_path):
    P = plan()
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "S.sv").write_text(module("S", "S", src_rtl()))
    (rtl / "R.sv").write_text(module("R", "R", dst_rtl(D=7)))
    (rtl / "t_bound_top.sv").write_text("module t_bound_top (input clk);\n    S p (.clk(clk));\n    R q (.clk(clk));\nendmodule\n")
    (tmp_path / "bind_latency.json").write_text(json.dumps(dict(buses=_rows(P))))
    assert V.kit_source_cuts(tmp_path, dict(P, asbuilt=dict(kit_source_station_pricing=True))) == {("p", "o"): (2, "L0")}
    assert V.kit_source_cuts(tmp_path, dict(P, asbuilt=dict())) == {}
    assert V.kit_source_cuts(tmp_path, dict(P, asbuilt=dict(kit_source_station_pricing=False))) == {}
