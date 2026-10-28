"""Tests for tools/die_plan/count_align_plan.py (MESO-COUNT-1/-2)."""
import importlib.util
import math
from pathlib import Path

spec = importlib.util.spec_from_file_location("cap", Path(__file__).with_name("count_align_plan.py"))
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
T = 833.0
AP = T / 8


def row(port, s, d, dd, up, dn, margin=None, unsh=1000.0):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
                margin_ps=(T / 2 - max(abs(dd + up), abs(dd - dn))) if margin is None else margin)


def by_port(out):
    return {o["port"]: o for o in out}


def test_clean_triangle_depth4_latency2():
    rows = [row("ab", "a", "b", 0, 50, 50), row("bc", "b", "c", 10, 50, 50), row("ca", "c", "a", -10, 60, 60)]
    s, out, regs = cap.plan(rows, T, AP, 0.05)
    assert s["regions_reached"] == 3 and s["tree_edges"] == 2 and s["tree_edges_clean"] == 2
    nt = [o for o in out if o["kind"] == "nontree"]
    assert len(nt) == 1 and nt[0]["path_ambiguous_cycles"] == 0 and nt[0]["depth"] == 4 and nt[0]["lat_cycles"] == 2
    assert s["fail"] == 0 and s["old_ring_not_cycle_fixed"] == 0


def test_clean_tree_crossing_K_from_derated_lag_not_pinned():
    # MESO-COUNT-2 fix (1): a clean tree crossing's K comes from its derated lag like any other crossing; the low end is
    # NOT pinned to 0.5T + ap (MESO-COUNT-1 reported 104.1 ps that way)
    rows = [row("ab", "a", "b", 300, 40, 60, unsh=0.0)]
    s, out, regs = cap.plan(rows, T, AP, 0.0)
    o = out[0]
    assert o["kind"] == "tree" and o["depth"] == 4
    k = math.ceil((T / 2 + AP - (300 - 60)) / T)
    assert o["K_eff"] == k and abs(o["L_lo_ps"] - (k * T + 240)) < 0.06 and abs(o["margin_lo_ps"] - (k * T + 240 - T / 2)) < 0.06
    assert o["margin_lo_ps"] > AP + 1


def test_rtl_K_and_start_offsets_pad2_plus_J():
    # fix (2)+(3): RTL K = K_eff - n0, n0 = sum over the tree path of PAD + 2 + J(d); J = -floor((d - off)/T)
    rows = [row("ab", "a", "b", 1000, 40, 40), row("bc", "b", "c", 200, 40, 40), row("ac", "a", "c", 1150, 40, 40)]
    for pad in (0, 3):
        s, out, regs = cap.plan(rows, T, AP, 0.0, pad=pad)
        a = {g["region"]: g for g in regs}
        assert s["tree_root"] == "a" and a["a"]["origin_cycles"] == 0
        e = a["b"]["start_from"]
        off = 0.0 if e["edge"] == "rise" else T / 2
        assert e["offset_from_parent"] == pad + 2 - math.floor((1000 - off) / T)
        assert e["rtl"] == dict(module="ot_dp_landing_origin", PAD=pad, EDGE_FALL=int(e["edge"] == "fall"))
        for o in out:
            assert o["n0"] == a[o["dst"]]["origin_cycles"] - a[o["src"]]["origin_cycles"]
            assert o["K"] == o["K_eff"] - o["n0"] and o["rtl"]["K"] == o["K"] and o["rtl"]["DEPTH"] == o["depth"]
        assert cap.mc_check(rows, out, regs, T, 300)[1] == 0


def test_sample_edge_avoids_boundary():
    # a tree crossing at d ~ 0 (mod T) must sample on the falling edge; at d ~ T/2 on the rising edge
    rows = [row("ab", "a", "b", 5, 30, 30), row("bc", "b", "c", T / 2 + 5, 30, 30)]
    s, out, regs = cap.plan(rows, T, AP, 0.0)
    a = {g["region"]: g["start_from"] for g in regs}
    assert a["b"]["edge"] == "fall" and a["c"]["edge"] == "rise" and s["tree_edges_clean"] == 2
    assert a["b"]["sync_dist_ps"] > AP and a["c"]["sync_dist_ps"] > AP


def test_directed_tree_uses_only_forward_crossings():
    # one-way crossings: the start can only travel src -> dst
    rows = [row("ab", "a", "b", 0, 40, 40), row("bc", "b", "c", 0, 40, 40), row("ca", "c", "a", T / 2, 40, 40)]
    s, out, regs = cap.plan(rows, T, AP, 0.0)
    for g in regs:
        if g["start_from"]:
            o = by_port(out)[g["start_from"]["port"]]
            assert o["src"] == g["start_from"]["parent"] and o["dst"] == g["region"]
    assert s["regions_reached"] == 3


def test_unreachable_region_fails():
    rows = [row("ab", "a", "b", 0, 40, 40), row("cb", "c", "b", 0, 40, 40)]   # nothing reaches both a and c
    s, out, regs = cap.plan(rows, T, AP, 0.0)
    assert s["regions_reached"] == 2 and s["fail"] >= 1


def test_wide_spread_absorbed_by_depth_not_latency_variation():
    rows = [row("ab", "a", "b", 0, 50, 50), row("ab2", "a", "b", -148, 473, 477)]
    s, out, regs = cap.plan(rows, T, AP, 0.05)
    o = by_port(out)["ab2"]
    assert o["old_ring_lat_values"] == 2 and not o["old_ring_ok"]
    assert o["depth"] == 4 and o["margin_lo_ps"] >= AP - 1e-6 and o["margin_hi_ps"] >= AP - 1e-6


def test_ambiguous_tree_edge_window_and_mc():
    # b-c only through 1000 ps-spread crossings: the tree edge is ambiguous; its own lag is the sync window, a parallel
    # crossing gets one extra period; the Monte-Carlo chip check of the emitted K finds no violation, and K - 1 fails
    rows = [row("ab", "a", "b", 0, 40, 40), row("bc", "b", "c", 0, 500, 500), row("bc2", "b", "c", 0, 510, 510)]
    s, out, regs = cap.plan(rows, T, AP, 0.05)
    assert s["tree_edges_clean"] == 1 and len(s["tree_edges_ambiguous"]) == 1
    o = by_port(out)
    amb_port = s["tree_edges_ambiguous"][0]["port"]
    other = "bc2" if amb_port == "bc" else "bc"
    assert o[amb_port]["kind"] == "tree_ambiguous" and o[amb_port]["L_width_ps"] < T + 2 * 26.5 + 2 * 50 + 1
    assert o[other]["path_ambiguous_cycles"] == 1 and o[other]["L_width_ps"] > T + 1000 and o[other]["depth"] in (4, 8)
    assert cap.mc_check(rows, out, regs, T, 600)[1] == 0
    o[other]["K"] -= 1                                  # mutant: one count early -> chips violate
    assert cap.mc_check(rows, out, regs, T, 600)[1] > 0


def test_mc_catches_wrong_start_offset():
    # mutant of the start convention: K computed with PAD + 3 per edge (instead of + 2) is wrong on real chips
    rows = [row("ab", "a", "b", 300, 40, 40), row("bc", "b", "c", 300, 40, 40), row("ac", "a", "c", 600, 40, 40)]
    s, out, regs = cap.plan(rows, T, AP, 0.0)
    assert cap.mc_check(rows, out, regs, T, 300)[1] == 0
    for o in out:
        o["K"] -= {"ab": 1, "bc": 1, "ac": 2}[o["port"]]   # n0 one larger per tree hop
    assert cap.mc_check(rows, out, regs, T, 300)[1] > 0


def test_start_skew_moves_near_tie_edge_off_the_boundary():
    """DIE-HEAD-4b (NC-HEAD-PART chE/W*_t__0): static d in [150, 273.5] ps is 150 from the rise boundary and 143 from
    the fall one, so the plan alone picks rise; the start arrives 57-90 ps late (parent clk->Q), the sampled phase
    d - skew reaches 60 ps from the rise boundary.  With --start-skew the edge is fall, >= ap from either boundary with
    and without the skew, and the die_sta_related start-row checks (|skew| <= limit, skewed dist >= sync aperture) hold."""
    rows = [row("ab", "a", "b", 211.75, 61.75, 61.75)]
    s0, _, r0 = cap.plan([dict(r) for r in rows], T, AP, 0.0)
    assert {g["region"]: g["start_from"] for g in r0}["b"]["edge"] == "rise"
    rows1 = [dict(r) for r in rows]
    s1, out, r1 = cap.plan(rows1, T, AP, 0.0, start_skew=(57.0, 90.0))
    e = {g["region"]: g["start_from"] for g in r1}["b"]
    assert e["edge"] == "fall" and e["sync_values"] == 1 and e["sync_dist_ps"] >= AP
    assert e["start_skew_limit_ps"] >= 90.0
    lo, hi = 150.0 - 90.0, 273.5 - 57.0
    off = T / 2
    k = math.floor((lo - off) / T)
    assert min(lo - (off + k * T), off + (k + 1) * T - hi) >= 26.5
    assert cap.mc_check(rows1, out, r1, T, 300)[1] == 0
    # default (0, 0) is the unskewed plan
    assert cap.plan([dict(r) for r in rows], T, AP, 0.0, start_skew=(0.0, 0.0))[2] == r0


def test_start_skew_keeps_an_edge_that_already_clears_it():
    """d in [200, 300]: rise is 200 ps off, the skewed phase [110, 243] still clears ap and the STA limit, so the skew
    changes nothing (no edge is moved that does not need it)"""
    rows = [row("ab", "a", "b", 250.0, 50.0, 50.0)]
    r0 = cap.plan([dict(r) for r in rows], T, AP, 0.0)[2]
    r1 = cap.plan([dict(r) for r in rows], T, AP, 0.0, start_skew=(57.0, 90.0))[2]
    assert r1 == r0 and {g["region"]: g["start_from"] for g in r1}["b"]["edge"] == "rise"


def test_parse_skew():
    assert cap.parse_skew("57,90") == (57.0, 90.0)
    import argparse
    import pytest
    with pytest.raises(argparse.ArgumentTypeError):
        cap.parse_skew("90,57")
