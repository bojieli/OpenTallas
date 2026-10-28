"""MESO-START-1 (COORD 02:42): feed-edge start tree, start-only relays, hop relays (count_align_plan / _bind /
die_sta_related, all opt-in; the default byte path is unchanged)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import die_sta_related as DSR  # noqa: E402

T = 833.0
AP = T / 8


def row(port, s, d, dd, up=40, dn=40, unsh=1000.0, sp=None, dp=None):
    r = dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
             margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))
    if sp:
        r.update(src_part=sp, dst_part=dp)
    return r


def doc(rows, **kw):
    s, out, regs = CAP.plan([dict(r) for r in rows], T, AP, 0.0, 26.5, 0, **kw)
    s.update(period_ps=T, aperture_ps=AP, sync_aperture_ps=26.5, pad=0)
    return CB.plan_doc(s, out, regs)


# a -> b -> c is the clock feed; the cheapest start tree without the feed rule is a -> c directly (clean) and
# a -> b; with --feed the edge b -> c must be used even though a -> c is cleaner
FEED = {"a": None, "b": "a", "c": "b"}
ROWS = [row("ab", "a", "b", 300, 40, 40), row("bc", "b", "c", 300, 60, 60), row("ac", "a", "c", 200, 20, 20),
        row("ca", "c", "a", -200, 20, 20)]


def test_default_path_unchanged_without_feed():
    s0, out0, r0 = CAP.plan([dict(r) for r in ROWS], T, AP, 0.0)
    s1, out1, r1 = CAP.plan([dict(r) for r in ROWS], T, AP, 0.0, feed=None, start_relay=False, hop_relay=False)
    assert (s0, out0, r0) == (s1, out1, r1) and "start_tree" not in s0


def test_feed_tree_uses_only_feed_edges():
    s, out, regs = CAP.plan([dict(r) for r in ROWS], T, AP, 0.0, feed=FEED)
    par = {g["region"]: g["start_from"]["parent"] for g in regs if g["start_from"]}
    assert par == {"b": "a", "c": "b"} and s["start_tree"] == "feed" and s["tree_root"] == "a"
    assert CAP.feed_edges_ok(regs, CAP.contract_feed(FEED, "abc")) == []
    assert s["fail"] == 0 and CAP.mc_check([dict(r, lo=r["d_ps"] - r["p_dn_ps"], hi=r["d_ps"] + r["p_up_ps"])
                                            for r in ROWS], out, regs, T, 300)[1] == 0


def test_mutant_off_feed_start_edge_is_rejected():
    """MUTANT (COORD 02:42 (3)): a plan whose start tree takes an off-feed edge (c from a) must be refused by the bind"""
    p = doc(ROWS, feed=FEED)
    CB.bind(p)                                            # the feed plan binds
    g = next(g for g in p["regions"] if g["region"] == "c")
    g["start_from"] = dict(g["start_from"], parent="a", port="ac")
    with pytest.raises(CB.BindError, match="not feed edges"):
        CB.bind(p)
    assert CAP.feed_edges_ok(p["regions"], p["summary"]["feed_parent"]) == [("c", "a")]


def test_feed_contraction_skips_non_region_nodes_and_needs_one_root():
    f = {"a": None, "j": "a", "b": "j", "c": "b", "leaf": "c"}
    assert CAP.contract_feed(f, ["a", "b", "c"]) == {"a": None, "b": "a", "c": "b"}
    with pytest.raises(ValueError):
        CAP.contract_feed({"a": None, "b": None}, ["a", "b"])
    with pytest.raises(ValueError):
        CAP.contract_feed({"a": None}, ["a", "b"])


REV = [row("ab", "a", "b", 300, 40, 40, sp="pa", dp="pb"), row("cb", "c", "b", -310, 30, 50, sp="pc", dp="pb2"),
       row("ac", "a", "c", 600, 40, 40, sp="pa", dp="pc")]


def test_feed_edge_without_forward_crossing_fails_closed_or_gets_start_relay():
    s, out, regs = CAP.plan([dict(r) for r in REV], T, AP, 0.0, feed=FEED)
    assert s["regions_reached"] == 2 and "c" in s["unreached_regions"] and s["fail"] >= 1
    s, out, regs = CAP.plan([dict(r) for r in REV], T, AP, 0.0, feed=FEED, start_relay=True)
    assert s["regions_reached"] == 3 and s["fail"] == 0 and s["start_relays"] == 1
    rel = next(o for o in out if o["kind"] == "start_relay")
    assert (rel["src"], rel["dst"], rel["reverse_of"]) == ("b", "c", "cb")
    assert rel["d_ps"] == 310 and rel["p_up_ps"] == 50 and rel["p_dn_ps"] == 30 and rel["rtl"] is None
    assert (rel["src_part"], rel["dst_part"]) == ("pb2", "pc")
    assert {g["region"]: g["start_from"]["port"] for g in regs if g["start_from"]}["c"] == rel["port"]
    rows = [dict(r, lo=r["d_ps"] - r["p_dn_ps"], hi=r["d_ps"] + r["p_up_ps"]) for r in REV]
    assert CAP.mc_check(rows, out, regs, T, 600)[1] == 0


def test_start_relay_binds_without_a_ring_and_simulates_clean():
    p = doc(REV, feed=FEED, start_relay=True)
    for parts in (None, {r["port"]: (r["src_part"], r["dst_part"]) for r in REV}):
        b = CB.bind(p, parts=parts)
        rel = [k for k, c in b["ports"].items() if c.get("start_only")]
        assert len(rel) == 1 and b["ports"][rel[0]]["tree"] and b["ports"][rel[0]]["K"] == -1
        v = CB.verify(b, 400)
        assert v["identity_and_loop_errors"] == [] and v["sim_window_violations"] == 0
        rep = CB.report(b, v)
        assert rep["start_relays"] == 1 and rep["depth_hist"] == {"4": 3, "8": 0}


def test_hop_relay_splits_a_failing_far_crossing():
    """u -> v fails on its own (derated interval wider than the D8 window); u -> x and x -> v are short existing pairs:
    two hops via x pass, the MC chip check of the emitted legs is clean, a leg one count early is caught"""
    rows = [row("ux", "u", "x", 300, 40, 40), row("xv", "x", "v", 300, 40, 40),
            row("uw", "u", "w", 0, 500, 500), row("wv", "w", "v", 0, 500, 500),
            row("uv", "u", "v", 600, 3000, 3000)]
    s0, out0, _ = CAP.plan([dict(r) for r in rows], T, AP, 0.05)
    assert s0["fail"] >= 1
    rr = [dict(r) for r in rows]
    s, out, regs = CAP.plan(rr, T, AP, 0.05, hop_relay=True)
    o = {x["port"]: x for x in out}
    assert s["hop_relayed"] >= 1 and s["fail"] == 0
    assert o["uv"]["kind"] == "hop_relayed" and o["uv"]["hop_via"] == "x" and o["uv"]["rtl"] is None
    legs = [o[k] for k in o["uv"]["hop_legs"]]
    assert [(l["src"], l["dst"]) for l in legs] == [("u", "x"), ("x", "v")] and all(l["depth"] for l in legs)
    assert o["uv"]["hop_lat_cycles"] == legs[0]["lat_cycles"] + legs[1]["lat_cycles"] + 1
    assert CAP.mc_check(rr, out, regs, T, 600)[1] == 0
    p = CB.plan_doc(dict(s, period_ps=T, aperture_ps=AP, sync_aperture_ps=26.5, pad=0), out, regs)
    b = CB.bind(p)
    assert "uv" not in b["ports"] and "uv#hop1" in b["ports"]
    v = CB.verify(b, 400)
    assert v["identity_and_loop_errors"] == [] and v["sim_window_violations"] == 0
    legs[0]["K"] -= 1                                   # mutant: leg one count early
    assert CAP.mc_check(rr, out, regs, T, 600)[1] > 0


def test_sta_start_row_for_start_relay_uses_reverse_pair(monkeypatch):
    p = doc(REV, feed=FEED, start_relay=True)
    b = CB.bind(p)
    # STA intervals per region pair (bind ports are region-level here): the reverse pair c->b gives the relay's phase
    dsta = {"a->b": (260.0, 340.0), "c->b": (-360.0, -280.0), "a->c": (560.0, 640.0)}
    monkeypatch.setattr(DSR, "count_align_d_intervals", lambda landed, taps, cppr_range=None: dsta)
    r = DSR.count_align_landed([], {}, b, T)
    assert r["no_taps"] == 0 and r["crossings"] == 3            # no lag row for the start-only relay
    srow = {s["port"]: s for s in r["start_skew"]["rows"]}
    rel = next(k for k, c in b["ports"].items() if c.get("start_only"))
    assert rel in srow and r["start_skew"]["tree_ports"] == 2
    if srow[rel]["sync_values"] == 1:
        off = T / 2 if srow[rel]["edge"] == "fall" else 0.0
        lo, hi = 280.0, 360.0                                   # negated reverse interval, skew 0
        k = (lo - off) // T
        assert abs(srow[rel]["sta_sync_dist_ps"] - min(lo - (off + k * T), off + (k + 1) * T - hi)) < 0.05
