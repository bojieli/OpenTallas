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
