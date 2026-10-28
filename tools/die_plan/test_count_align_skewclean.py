"""MESO-START-2 (COORD 03:0x, approved planner change): with --start-skew, a start-tree edge is CLEAN only if its interval
clears the sync aperture + max|skew| (26.5 + 87.5 = 114 ps); otherwise it is AMBIGUOUS and gets PAD + 1 where its
tree-crossing low margin is short (OWNER 12.15b).  Opt-in (--start-skew-clean); the default byte path is unchanged."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402

T = 833.0
AP = T / 8
SAP = 26.5
SKEW = (55.2, 87.5)


def row(port, s, d, lo, hi, unsh=0.0):
    dd = 0.5 * (lo + hi)
    return dict(port=port, src=s, dst=d, d_ps=dd, p_up_ps=hi - dd, p_dn_ps=dd - lo, unshared_a_ps=unsh,
                unshared_b_ps=unsh, margin_ps=0.0)


def rows_at(dist, unsh=0.0):
    """a -> b start edge whose rise boundary (0) lies `dist` below the interval and whose fall boundary (T/2) is inside
    +- ap (fall ambiguous), plus a reverse crossing b -> a that rides the start-tree path back (ambiguous on both edges, so the tree keeps a -> b; tight low margin, so a
    start that resolves one count late on a -> b breaks it).  unsh: a -> b unshared clock (wander 0.05 x unsh)"""
    return [row("ab", "a", "b", dist, 400.0, unsh), row("ba", "b", "a", -500.0, -60.0)]


def doc(rows, wf=0.0, **kw):
    s, out, regs = CAP.plan([dict(r) for r in rows], T, AP, wf, SAP, 0, None, SKEW, **kw)
    s.update(period_ps=T, aperture_ps=AP, sync_aperture_ps=SAP, pad=0, start_skew_ps=list(SKEW))
    return CB.plan_doc(s, out, regs)


def edge(p, region="b"):
    return next(g["start_from"] for g in p["regions"] if g["region"] == region)


def test_default_path_unchanged_without_flag():
    a = CAP.plan([dict(r) for r in rows_at(113.0)], T, AP, 0.0, SAP, 0, None, SKEW)
    b = CAP.plan([dict(r) for r in rows_at(113.0)], T, AP, 0.0, SAP, 0, None, SKEW, skew_clean=False)
    assert a == b and "start_skew_clean" not in a[0]
    assert "start_skew_ps" not in CB.bind(doc(rows_at(113.0)))  # bind sim only skews when the plan asked


def test_mutant_113ps_edge_gets_pad():
    """MUTANT: a CLEAN-looking edge at 113 ps (< 26.5 + 87.5) must become ambiguous with PAD 1 under the flag"""
    p0 = doc(rows_at(113.0))
    e0 = edge(p0)
    assert e0["sync_values"] == 1 and e0["edge"] == "rise" and e0["rtl"]["PAD"] == 0
    assert e0["start_skew_limit_ps"] < SKEW[1]          # die_sta_related clean start row FAILs without the flag
    p1 = doc(rows_at(113.0), skew_clean=True)
    e1 = edge(p1)
    # ambiguous now; the rise sync window leaves 390 ps low margin (>= 187.5) at zero wander, so no PAD is needed
    assert e1["sync_values"] == 2 and e1["rtl"]["PAD"] == 0 and e1["start_skew_limit_ps"] >= SKEW[1]
    assert p1["summary"]["start_skew_clean"]["tree_edges_amb_by_skew"] == 1
    # with 250 ps post-start wander (5 ns unshared) the low margin drops to 140 < 100 + 87.5 -> PAD 1 on that edge
    p0 = doc(rows_at(113.0, 5000.0), 0.05)
    assert edge(p0)["sync_values"] == 1 and edge(p0)["start_skew_limit_ps"] < SKEW[1]
    p1 = doc(rows_at(113.0, 5000.0), 0.05, skew_clean=True)
    e1 = edge(p1)
    assert e1["sync_values"] == 2 and e1["rtl"]["PAD"] == 1 and e1["pad_override"]
    assert e1["start_skew_limit_ps"] >= SKEW[1]          # ambiguous row: margin - 100 >= |skew|
    sc = p1["summary"]["start_skew_clean"]
    assert sc["padded_edges"] == 1 and sc["tree_edges_amb_by_skew"] == 1 and sc["added_latency_cycles_pad"] == 1
    assert sc["need_clean_dist_ps"] == 114.0
    tx = next(o for o in p1["crossings"] if o["port"] == "ab")
    assert tx["kind"] == "tree_ambiguous" and min(tx["margin_lo_ps"], tx["margin_hi_ps"]) >= 100 + SKEW[1]


def test_edge_clearing_114_stays_clean_without_pad():
    p = doc(rows_at(115.0), skew_clean=True)
    e = edge(p)
    assert e["sync_values"] == 1 and e["rtl"]["PAD"] == 0 and e["start_skew_limit_ps"] >= SKEW[1]
    assert p["summary"]["start_skew_clean"]["padded_edges"] == 0
    assert p["summary"]["start_skew_clean"]["added_latency_cycles_vs_noflag"] == 0


def test_bind_startup_check_with_skew():
    """bind start-up sim samples d - skew: the flagged plan has 0 violations; the unflagged 113-ps plan (mutant: the
    old CLEAN reading) violates once the skew is simulated; stripping the PAD from the flagged plan is refused"""
    p1 = doc(rows_at(113.0, 5000.0), 0.05, skew_clean=True)
    b1 = CB.bind(p1)
    assert b1["start_skew_ps"] == list(SKEW)
    v1 = CB.verify(b1, 3000)
    assert v1["identity_and_loop_errors"] == [] and v1["sim_window_violations"] == 0
    b0 = CB.bind(doc(rows_at(113.0)))
    b0["start_skew_ps"] = list(SKEW)
    assert CB.verify(b0, 3000)["sim_window_violations"] > 0
    e = edge(p1)
    e["rtl"] = dict(e["rtl"], PAD=0)
    with pytest.raises(CB.BindError):
        CB.bind(p1)


def test_mc_samples_skew_and_flag_needs_skew():
    rs = [dict(r) for r in rows_at(113.0)]
    s, out, regs = CAP.plan(rs, T, AP, 0.0, SAP, 0, None, SKEW, skew_clean=True)
    assert CAP.mc_check(rs, out, regs, T, 600, SAP, start_skew=SKEW)[1] == 0
    rs0 = [dict(r) for r in rows_at(113.0)]
    s0, out0, regs0 = CAP.plan(rs0, T, AP, 0.0, SAP, 0, None, SKEW)
    assert CAP.mc_check(rs0, out0, regs0, T, 600, SAP, start_skew=SKEW)[1] > 0
    with pytest.raises(ValueError):
        CAP.plan([dict(r) for r in rows_at(113.0)], T, AP, 0.0, SAP, 0, None, (0.0, 0.0), skew_clean=True)
