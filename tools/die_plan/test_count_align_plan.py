"""Tests for tools/die_plan/count_align_plan.py (MESO-COUNT-1)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("cap", Path(__file__).with_name("count_align_plan.py"))
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
T = 833.0


def row(port, s, d, dd, up, dn, margin=None):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=1000.0, unshared_b_ps=1000.0,
                margin_ps=(T / 2 - max(abs(dd + up), abs(dd - dn))) if margin is None else margin)


def test_clean_triangle_depth4_latency2():
    rows = [row("ab", "a", "b", 0, 50, 50), row("bc", "b", "c", 10, 50, 50), row("ca", "c", "a", -10, 60, 60)]
    s, out = cap.plan(rows, T, T / 8, 0.05)
    assert s["tree_components"] == 1 and s["tree_edges"] == 2 and s["tree_edges_clean"] == 2
    nt = [o for o in out if o["kind"] == "nontree"]
    assert len(nt) == 1 and nt[0]["path_ambiguous_cycles"] == 0 and nt[0]["depth"] == 4 and nt[0]["lat_cycles"] == 2
    assert s["fail"] == 0 and s["old_ring_not_cycle_fixed"] == 0


def test_wide_spread_root_crossing_absorbed_by_depth_not_latency_variation():
    # a crossing whose derated phase spread (950 ps) exceeds one period: the old ring's latency is not cycle-fixed,
    # the count-aligned ring fits it in the DEPTH-4 window at one fixed latency
    rows = [row("ab", "a", "b", 0, 50, 50), row("ab2", "a", "b", -148, 473, 477)]
    s, out = cap.plan(rows, T, T / 8, 0.05)
    o = {x["port"]: x for x in out}["ab2"]
    assert o["old_ring_lat_values"] == 2 and not o["old_ring_ok"]
    assert o["depth"] == 4 and o["L_lo_ps"] >= T / 2 + T / 8 - 1e-6 and o["L_hi_ps"] <= 3.5 * T - T / 8 + 1e-6


def test_ambiguous_tree_edge_widens_paths_through_it():
    # b-c only connects through a 1000 ps-spread crossing: the tree edge is ambiguous (2 values), a parallel
    # non-tree crossing b->c gets one extra period of window
    rows = [row("ab", "a", "b", 0, 40, 40), row("bc", "b", "c", 0, 500, 500), row("bc2", "b", "c", 0, 510, 510)]
    s, out = cap.plan(rows, T, T / 8, 0.05)
    assert s["tree_edges_clean"] == 1 and len(s["tree_edges_ambiguous"]) == 1
    o = {x["port"]: x for x in out}["bc2"]
    assert o["path_ambiguous_cycles"] == 1 and o["L_width_ps"] > T + 1000
    assert o["depth"] in (4, 8)


def test_disconnected_regions_reported():
    rows = [row("ab", "a", "b", 0, 40, 40), row("cd", "c", "d", 0, 40, 40)]
    s, _ = cap.plan(rows, T, T / 8, 0.05)
    assert s["tree_components"] == 2
