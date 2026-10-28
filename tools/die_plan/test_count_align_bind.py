"""Tests for tools/die_plan/count_align_bind.py (MESO-INTEG-1)."""
import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402

T = 833.0


def row(port, s, d, dd, up=40, dn=40):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=1000.0, unshared_b_ps=1000.0,
                margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))


def run(rows, pad=0, samples=400):
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    b = CB.bind(summ, out, T, pad)
    return summ, out, b, CB.verify(b, {r["port"]: r for r in rows}, samples, T / 8, 0.05)


def test_tree_latency_uses_the_sync_window():
    # rise sync: lag window [T, 2T); d = 0.8 T sits in [c, T) where the old model said latency 1, the RTL gives 2
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30)]
    summ, out, b, v = run(rows)
    o = out[0]
    assert o["kind"] == "tree" and o["lat_cycles"] == 2
    assert b["ports"]["ab"]["K"] == -1 and b["regions"]["b"]["n_nominal"] == 1 + 1   # registered start: LAUNCH = 1
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0


def test_loops_consistent_and_physical_sim_clean():
    # a 5-region ring with both directions and a chord: loops close with sum(sched_lat) == sum(K + 1)
    names = "abcde"
    rows = []
    for i in range(5):
        u, w = names[i], names[(i + 1) % 5]
        rows += [row(f"{u}{w}", u, w, 120 * (i - 2)), row(f"{w}{u}", w, u, -120 * (i - 2) + 30, 200, 260)]
    rows.append(row("ac", "a", "c", -500, 300, 300))
    for pad in (0, 2):
        summ, out, b, v = run(rows, pad)
        assert summ["fail"] == 0 and summ["tree_components"] == 1 and not summ["tree_edges_reversed"]
        assert v["fundamental_cycles"] == len(rows) - 4
        assert not v["identity_and_loop_errors"], v["identity_and_loop_errors"]
        assert v["sim_window_violations"] == 0 and v["sim_min_margin_low_ps"] >= 0
        assert all(c["K"] >= -1 - pad for c in b["ports"].values() if c["tree"])
    # schedule latency does not depend on PAD; RTL K does
    _, _, b0, _ = run(rows, 0)
    _, _, b2, _ = run(rows, 2)
    assert all(b0["ports"][p]["sched_lat"] == b2["ports"][p]["sched_lat"] for p in b0["ports"])
    assert any(b0["ports"][p]["K"] != b2["ports"][p]["K"] for p in b0["ports"])


def test_wrong_K_is_caught_by_the_physical_sim():
    rows = [row("ab", "a", "b", 0), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    summ, out, b, v = run(rows)
    assert v["sim_window_violations"] == 0
    nt = next(p for p, c in b["ports"].items() if not c["tree"])
    b["ports"][nt]["K"] -= 1          # one count early: lag one period short, under the low edge
    v2 = CB.verify(b, {r["port"]: r for r in rows}, 200, T / 8, 0.05)
    assert v2["identity_and_loop_errors"] and v2["sim_window_violations"] > 0


def test_reversed_tree_edge_is_refused():
    rows = [row("ab", "a", "b", 0), row("cb", "c", "b", 0)]   # c only reachable against a crossing's direction
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    if summ["tree_root"] == "b":
        assert len(summ["tree_edges_reversed"]) == 2
    assert summ["tree_edges_reversed"]
    with pytest.raises(CB.BindError, match="child -> parent"):
        CB.bind(summ, out, T)


def test_annotate_table_prices_each_crossing():
    rows = [row("ab", "a", "b", 0), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    _, _, b, _ = run(rows)
    table = dict(regions=[], ports=[dict(port=p, src=c["src"], dst=c["dst"], src_region=c["src"], dst_region=c["dst"],
                                         width=8, lane="L" + p) for p, c in b["ports"].items()])
    t = CB.annotate_table(table, b)
    assert {r["port"]: r["added_cycles"] for r in t["ports"]} == {p: c["sched_lat"] for p, c in b["ports"].items()}
    assert CB.lane_cycles(t) == {"L" + p: c["sched_lat"] for p, c in b["ports"].items()}
    assert t["count_aligned"]["regions"][b["root"]]["parent"] is None


def test_tree_wander_shifts_the_window_up_one_period():
    # 7 ns unshared -> 350 ps wander: a rise window [T, 2T) would dip under 0.5T + ap; K_tree moves up by one
    rows = [dict(row("ab", "a", "b", 0.2 * T), unshared_a_ps=7000.0, unshared_b_ps=7000.0)]
    summ, out, b, v = run(rows)
    assert out[0]["tree_shift"] == 1 and b["ports"]["ab"]["K"] == 0 and out[0]["lat_cycles"] == 3
    assert v["sim_window_violations"] == 0


# DIE-KV-3/CAORIGIN (COORD 21:14 ASK 3): one origin per region + timed start relay to the region's other partitions
def multi_rows():
    """regions a, b, c; a holds a1/a2, c holds c1/c2/c3; crossings hit relayed senders and receivers"""
    pr = dict(a1="a", a2="a", b="b", c1="c", c2="c", c3="c")
    ph = dict(a=0, b=300, c=-250)
    edges = [("a1", "b"), ("b", "c1"), ("c2", "a2"), ("a2", "c3"), ("c3", "b"), ("b", "a2"), ("c1", "a1"), ("a2", "b"),
             ("b", "c2")]
    rows = [row(f"{u}_{v}", pr[u], pr[v], ph[pr[v]] - ph[pr[u]], 60, 60) for u, v in edges]
    return rows, {f"{u}_{v}": (u, v) for u, v in edges}


def test_multi_partition_regions_get_one_origin_and_relays():
    rows, parts = multi_rows()
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    br = CB.bind(summ, out, T, 0)                       # region frames (MESO-INTEG-1)
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    b = CB.bind(summ, out, T, 0, parts)
    v = CB.verify(b, {r["port"]: r for r in rows}, 400, T / 8, 0.05)
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0, v
    # one origin per region; the child origin is the partition its tree port lands in
    for x, rg in b["regions"].items():
        org = [q for q, p in b["parts"].items() if p["region"] == x and p["role"] == "origin"]
        assert org == [rg["origin_part"]]
        if rg["parent"] is not None:
            assert b["ports"][rg["tree_port"]]["dst_part"] == rg["origin_part"]
    # dN = partition count origin - one-origin-per-region origin: the relay stages plus the relayed tree senders
    dn = {q: p["n_nominal"] - br["regions"][p["region"]]["n_nominal"] for q, p in b["parts"].items()}
    assert sum(1 for p in b["parts"].values() if p["role"] == "relay") == 3 and set(dn.values()) - {0} 
    for pid, c in b["ports"].items():
        assert c["sched_lat"] == br["ports"][pid]["sched_lat"]            # schedule / TOK latency unchanged
        if not c["tree"]:
            assert c["K"] == br["ports"][pid]["K"] - dn[c["dst_part"]] + dn[c["src_part"]]
        else:
            assert c["K"] == br["ports"][pid]["K"]
    assert v["fundamental_cycles"] == len(rows) - (len(b["parts"]) - 1 - 3)   # partition tree: tree ports + 3 relays
    s = CB.relay_summary(b)
    assert s["multi_partition_regions"] == 2 and s["relay_pins"] == dict(tx_out=2, rx_in=3)


def test_relay_offset_ignored_is_caught():
    rows, parts = multi_rows()
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    b = CB.bind(summ, out, T, 0, parts)
    rel = {q: (p["stages"] if p["role"] == "relay" else 0) for q, p in b["parts"].items()}
    hit = [p for p, c in b["ports"].items() if not c["tree"] and rel[c["dst_part"]] != rel[c["src_part"]]]
    assert hit
    c = b["ports"][hit[0]]
    c["K"] += rel[c["dst_part"]] - rel[c["src_part"]]                    # region-frame K: relay offset dropped
    v = CB.verify(b, {r["port"]: r for r in rows}, 200, T / 8, 0.05)
    assert v["identity_and_loop_errors"] and v["sim_window_violations"] > 0


def test_annotate_table_writes_partition_roles():
    rows, parts = multi_rows()
    summ, out = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05)
    b = CB.bind(summ, out, T, 0, parts)
    table = dict(regions=[], ports=[dict(port=p, src=c["src_part"], dst=c["dst_part"], src_region=c["src"],
                                         dst_region=c["dst"], width=8, lane="L" + p) for p, c in b["ports"].items()])
    assert CB.table_parts(table) == parts
    t = CB.annotate_table(table, b)
    ca = t["count_aligned"]
    assert ca["relay_stages"] == 2 and set(ca["parts"]) == set(b["parts"])
    assert all(ca["regions"][x]["origin_part"] == b["regions"][x]["origin_part"] for x in b["regions"])
    table["ports"][0]["dst"] = "zz"
    with pytest.raises(CB.BindError, match="bind partitions"):
        CB.annotate_table(table, b)
