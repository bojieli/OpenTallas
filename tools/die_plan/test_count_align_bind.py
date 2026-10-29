"""Tests for tools/die_plan/count_align_bind.py (MESO-INTEG-1, MESO-RECONCILE-1: binds the plan's emitted params)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402

T = 833.0


def row(port, s, d, dd, up=40, dn=40, unsh=1000.0):
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=up, p_dn_ps=dn, unshared_a_ps=unsh, unshared_b_ps=unsh,
                margin_ps=T / 2 - max(abs(dd + up), abs(dd - dn)))


def plan(rows, pad=0, wander=0.05):
    s, out, regs = CAP.plan([dict(r) for r in rows], T, T / 8, wander, 26.5, pad)
    s.update(period_ps=T, aperture_ps=T / 8, sync_aperture_ps=26.5, pad=pad)
    return CB.plan_doc(s, out, regs)


def run(rows, pad=0, samples=400):
    p = plan(rows, pad)
    b = CB.bind(p)
    return p, b, CB.verify(b, samples)


def test_two_start_conventions_are_one_quantity():
    # MESO-INTEG-1 m + 1 + PAD (from the parent origin) == MESO-COUNT-2 PAD + 2 + J(d) (from the parent launch edge),
    # every phase incl. exact boundaries, both sample edges, PAD 0..3
    for pad in range(4):
        for edge in ("rise", "fall"):
            for i in range(-4 * 64, 4 * 64 + 1):
                d = i * T / 64
                assert CB.integ_step(d, edge, T, pad) == CB.count2_step(d, edge, T, pad)
            for d in (-1234.5, -0.001, 0.0, 0.001, 416.5, 416.499, 833.0, 1700.2):
                assert CB.integ_step(d, edge, T, pad) == CB.count2_step(d, edge, T, pad)


def test_bind_takes_plan_params_and_checks_identity():
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    p, b, v = run(rows)
    xs = {o["port"]: o for o in p["crossings"]}
    for pid, c in b["ports"].items():
        assert c["K"] == xs[pid]["rtl"]["K"] and c["depth"] == xs[pid]["rtl"]["DEPTH"] and c["sched_lat"] == xs[pid]["lat_cycles"]
    for g in p["regions"]:
        assert b["regions"][g["region"]]["n_nominal"] == g["origin_cycles"]
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0


def test_tree_K_is_plan_K_one_below_or_equal_integ_fixed_K():
    # d = 0.8 T clean rise tree edge: MESO-INTEG-1 fixed K_tree = -1 - PAD (lag 1.8 T, latency 2); the plan picks the
    # smallest K keeping the derated lag >= 0.5 T + ap: lag 0.8 T, latency 1, K = -2 - PAD.  Same origins.
    for pad in (0, 2):
        p, b, v = run([row("ab", "a", "b", 0.8 * T, 30, 30, unsh=0.0)], pad)
        c = b["ports"]["ab"]
        assert c["tree"] and b["regions"]["b"]["n_nominal"] == pad + 2
        assert c["K"] == -2 - pad and c["sched_lat"] == 1
        assert v["sim_window_violations"] == 0 and v["sim_min_margin_low_ps"] >= T / 8 - 0.1


def test_loops_consistent_and_physical_sim_clean():
    names = "abcde"
    rows = []
    for i in range(5):
        u, w = names[i], names[(i + 1) % 5]
        rows += [row(f"{u}{w}", u, w, 120 * (i - 2)), row(f"{w}{u}", w, u, -120 * (i - 2) + 30, 200, 260)]
    rows.append(row("ac", "a", "c", -500, 300, 300))
    for pad in (0, 2):
        p, b, v = run(rows, pad)
        assert p["summary"]["fail"] == 0 and p["summary"]["regions_reached"] == 5
        assert v["fundamental_cycles"] == len(rows) - 4
        assert not v["identity_and_loop_errors"], v["identity_and_loop_errors"]
        assert v["sim_window_violations"] == 0
    _, b0, _ = run(rows, 0)
    _, b2, _ = run(rows, 2)
    assert all(b0["ports"][q]["sched_lat"] == b2["ports"][q]["sched_lat"] for q in b0["ports"])
    assert any(b0["ports"][q]["K"] != b2["ports"][q]["K"] for q in b0["ports"])


def test_wrong_K_is_caught():
    rows = [row("ab", "a", "b", 0), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    p, b, v = run(rows)
    assert v["sim_window_violations"] == 0
    nt = next(q for q, c in b["ports"].items() if not c["tree"])
    b["ports"][nt]["K"] -= 1
    v2 = CB.verify(b, 200)
    assert v2["identity_and_loop_errors"] and v2["sim_window_violations"] > 0


def test_tampered_origin_step_is_refused():
    p = plan([row("ab", "a", "b", 300), row("bc", "b", "c", 100)])
    g = next(g for g in p["regions"] if g["start_from"])
    g["start_from"]["offset_from_parent"] += 1
    with pytest.raises(CB.BindError, match="offset_from_parent"):
        CB.bind(p)
    p = plan([row("ab", "a", "b", 300), row("bc", "b", "c", 100)])
    for g in p["regions"]:
        if g["start_from"]:
            g["start_from"]["edge"] = "fall" if g["start_from"]["edge"] == "rise" else "rise"
            # flipping the sample edge changes J by the half-period boundary for d = 300 -> conventions disagree
    with pytest.raises(CB.BindError):
        CB.bind(p)


def test_failed_plan_is_refused():
    p = plan([row("ab", "a", "b", 0), row("ba", "b", "a", 0, 3000, 3000)])
    assert p["summary"]["fail"] == 1
    with pytest.raises(CB.BindError, match="no RTL"):
        CB.bind(p)


def test_annotate_table_prices_each_crossing():
    rows = [row("ab", "a", "b", 0), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    _, b, _ = run(rows)
    table = dict(regions=[], ports=[dict(port=q, src=c["src"], dst=c["dst"], src_region=c["src"], dst_region=c["dst"],
                                         width=8, lane="L" + q) for q, c in b["ports"].items()])
    t = CB.annotate_table(table, b)
    assert {r["port"]: r["added_cycles"] for r in t["ports"]} == {q: c["sched_lat"] for q, c in b["ports"].items()}
    assert CB.lane_cycles(t) == {"L" + q: c["sched_lat"] for q, c in b["ports"].items()}
    assert t["count_aligned"]["regions"][b["root"]]["parent"] is None


def test_start_skew_limit_emitted_per_tree_edge():
    p = plan([row("ab", "a", "b", 300, 40, 40), row("bc", "b", "c", 100, 40, 40)])
    for g in p["regions"]:
        e = g["start_from"]
        if e and e["sync_values"] == 1:
            assert math.isclose(e["start_skew_limit_ps"], round(e["sync_dist_ps"] - 26.5, 1), abs_tol=0.11)
    assert p["summary"]["start_skew_limit_clean_min_ps"] is not None


def test_edge_pad_delays_child_origin_and_adds_tree_cycles_only():
    # MESO-RECONCILE (COORD 22:53 HEAD (b)): per-start-tree-edge PAD.  Edge PAD p on the tree edge into b delays b (and
    # its subtree) by p - PAD counts and holds that tree crossing's RTL K, so its latency grows by p - PAD; identity and
    # every loop sum still hold.
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    for pad in (0, 2):
        p0 = plan(rows, pad)
        s, out, regs = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05, 26.5, pad, {"b": pad + 1})
        s.update(period_ps=T, aperture_ps=T / 8, sync_aperture_ps=26.5, pad=pad)
        p1 = CB.plan_doc(s, out, regs)
        b1 = CB.bind(p1)
        v1 = CB.verify(b1, 400)
        assert not v1["identity_and_loop_errors"] and v1["sim_window_violations"] == 0
        assert s["edge_pad"] == {"b": pad + 1}
        o0 = {g["region"]: g for g in p0["regions"]}
        o1 = {g["region"]: g for g in p1["regions"]}
        assert o1["b"]["origin_cycles"] == o0["b"]["origin_cycles"] + 1
        assert o1["b"]["start_from"]["rtl"]["PAD"] == pad + 1 and b1["regions"]["b"]["pad"] == pad + 1
        x0 = {o["port"]: o for o in p0["crossings"]}
        x1 = {o["port"]: o for o in p1["crossings"]}
        tree = o1["b"]["start_from"]["port"]
        assert x1[tree]["rtl"]["K"] == x0[tree]["rtl"]["K"]
        assert x1[tree]["lat_cycles"] == x0[tree]["lat_cycles"] + 1
        assert abs(x1[tree]["margin_lo_ps"] - x0[tree]["margin_lo_ps"] - T) < 0.2


def test_edge_pad_rejects_non_tree_edge_and_below_default():
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    with pytest.raises(ValueError):
        CAP.plan([dict(r) for r in rows], T, T / 8, 0.05, 26.5, 0, {"nosuch": 1})
    with pytest.raises(ValueError):
        CAP.plan([dict(r) for r in rows], T, T / 8, 0.05, 26.5, 2, {"b": 1})
    assert CAP.parse_edge_pad(["tW0b10=1", "x=y=2"]) == {"tW0b10": 1, "x=y": 2}


# DIE-KV-3/CAORIGIN (COORD 21:14 ASK 3), ported onto the plan-param bind v2: one origin per region + timed start relay
# to the region's other partitions
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
    br = CB.bind(plan(rows))                           # one origin per region
    b = CB.bind(plan(rows), parts=parts)
    v = CB.verify(b, 400)
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0, v
    for x, rg in b["regions"].items():
        org = [q for q, p in b["parts"].items() if p["region"] == x and p["role"] == "origin"]
        assert org == [rg["origin_part"]]
        if rg["parent"] is not None:
            assert b["ports"][rg["tree_port"]]["dst_part"] == rg["origin_part"]
    dn = {q: p["n_nominal"] - br["regions"][p["region"]]["n_nominal"] for q, p in b["parts"].items()}
    assert sum(1 for p in b["parts"].values() if p["role"] == "relay") == 3 and set(dn.values()) - {0}
    for pid, c in b["ports"].items():
        assert c["sched_lat"] == br["ports"][pid]["sched_lat"]            # schedule / TOK latency unchanged
        if not c["tree"]:
            assert c["K"] == br["ports"][pid]["K"] - dn[c["dst_part"]] + dn[c["src_part"]]
        else:
            assert c["K"] == br["ports"][pid]["K"]                        # tree K = plan K
    assert v["fundamental_cycles"] == len(rows) - (len(b["parts"]) - 1 - 3)   # partition tree: tree ports + 3 relays
    s = CB.relay_summary(b)
    assert s["multi_partition_regions"] == 2 and s["relay_pins"] == dict(tx_out=2, rx_in=3)


def test_relay_offset_ignored_is_caught():
    rows, parts = multi_rows()
    b = CB.bind(plan(rows), parts=parts)
    rel = {q: (p["stages"] if p["role"] == "relay" else 0) for q, p in b["parts"].items()}
    hit = [p for p, c in b["ports"].items() if not c["tree"] and rel[c["dst_part"]] != rel[c["src_part"]]]
    assert hit
    c = b["ports"][hit[0]]
    c["K"] += rel[c["dst_part"]] - rel[c["src_part"]]                    # region-frame K: relay offset dropped
    v = CB.verify(b, 200)
    # a 2-count K error can stay inside the D4 window (wrong WORD, not a window violation): the frame identity and the
    # loop sums catch it here, the RTL loop bench (mutant_noshift) catches the wrong words
    assert any(e.startswith("identity " + hit[0]) for e in v["identity_and_loop_errors"])
    assert any(e.startswith("loop ") for e in v["identity_and_loop_errors"])


def test_relay_with_edge_pad_keeps_identity():
    rows, parts = multi_rows()
    p0 = plan(rows)
    child = [g["region"] for g in p0["regions"] if g["start_from"]][0]
    s, out, regs = CAP.plan([dict(r) for r in rows], T, T / 8, 0.05, 26.5, 0, {child: 1})
    s.update(period_ps=T, aperture_ps=T / 8, sync_aperture_ps=26.5, pad=0)
    b = CB.bind(CB.plan_doc(s, out, regs), parts=parts)
    v = CB.verify(b, 400)
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0, v
    assert b["regions"][child]["pad"] == 1


def test_annotate_table_writes_partition_roles():
    rows, parts = multi_rows()
    b = CB.bind(plan(rows), parts=parts)
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


def test_ocv_parts_partition_level_rows_fall_back_to_src_dst():
    # DIE-S81-17: S81 landed_phase_ocv rows are partition-level (no src_part/dst_part); --parts ocv must bind them with
    # the partition = src/dst (count_align_plan.row_ports identity), and named rows keep their src_part/dst_part
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30), row("bc", "b", "c", 100), row("ca", "c", "a", -60, 200, 200)]
    parts = CB.ocv_parts(rows)
    assert parts == {"ab": ("a", "b"), "bc": ("b", "c"), "ca": ("c", "a")}
    _, pr = CAP.row_ports(rows)
    assert all((pr[s], pr[d]) == (s, d) for s, d in parts.values())
    b = CB.bind(plan(rows), parts=parts)
    v = CB.verify(b, 400)
    assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0, v
    br = CB.bind(plan(rows))
    assert {p: c["K"] for p, c in b["ports"].items()} == {p: c["K"] for p, c in br["ports"].items()}
    named = [dict(r, src_part="a1", dst_part="b1") if r["port"] == "ab" else r for r in rows]
    assert CB.ocv_parts(named)["ab"] == ("a1", "b1") and CB.ocv_parts(named)["bc"] == ("b", "c")


def test_ocv_parts_fail_closed_on_missing_or_conflicting_endpoints():
    # S81-LP-1: the go16 KeyError recurrence came from a stale tool snapshot; the main tool now refuses rows it cannot
    # place with a named BindError instead of a bare KeyError, and refuses corner rows that disagree on a port's pair
    rows = [row("ab", "a", "b", 0.8 * T, 30, 30), row("bc", "b", "c", 100)]
    bad = [dict(rows[0]), rows[1]]
    del bad[0]["src"]
    with pytest.raises(CB.BindError, match="row 'ab' has no src/dst partition"):
        CB.ocv_parts(bad)
    with pytest.raises(CB.BindError, match="port ab rows disagree"):
        CB.ocv_parts(rows + [dict(rows[0], src_part="a2")])
    assert CB.ocv_parts(rows + [dict(rows[0])]) == {"ab": ("a", "b"), "bc": ("b", "c")}   # same pair per corner: OK
