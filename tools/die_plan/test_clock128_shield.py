#!/usr/bin/env python3
"""CLOCK-128 shield lane: shielded clock wiring legal by construction.
python3 -m pytest tools/die_plan/test_clock128_shield.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_128 as C  # noqa: E402

ND = dict(width=0.16, space=0.08)
TR = {"M8": dict(pitch_um=0.08, offset_um=0.04), "M9": dict(pitch_um=0.08, offset_um=0.04)}


def grid(m9_pitch, W=60.0, H=60.0, w=0.48, m8_pitch=8.64):
    """die_infra.pg_rects-form VDD/VSS grid: M8 rows (pitch m8_pitch), M9 columns (pitch m9_pitch), VDD/VSS alternate"""
    out = []
    for L, pitch, span, other in (("M8", m8_pitch, H, W), ("M9", m9_pitch, W, H)):
        pos = pitch / 2
        while pos < span:
            for j, net in enumerate(("VDD", "VSS")):
                c = pos + j * pitch / 2
                if c + w / 2 > span:
                    continue
                out.append((net, L, 0.0, c - w / 2, other, c + w / 2) if L == "M8" else
                           (net, L, c - w / 2, 0.0, c + w / 2, other))
            pos += pitch
    return out


def router(pg):
    r = C.TrackRouter(ND, "VSS", TR, 8.64)
    r.reserve(C.pg_shapes(pg))
    return r


def census(pg, segs):
    return C.metal_census(C.pg_shapes(pg) + C.clock_shapes(segs, ND, "VSS"), ND["space"])


def test_census_catches_shield_on_vdd_and_clock_on_pg():
    pg = grid(8.64)
    vdd_m9 = next(r for r in pg if r[0] == "VDD" and r[1] == "M9")
    x = (vdd_m9[2] + vdd_m9[4]) / 2
    bad = census(pg, [("M9", x + 0.24, 5.0, x + 0.24, 40.0, "ck_a", "tree"),     # its shield sits on the VDD stripe
                      ("M9", x, 45.0, x, 50.0, "ck_b", "tree")])                  # clock metal on the VDD stripe
    assert bad["shorts_by_kind"].get("pg-shield") and bad["shorts_by_kind"].get("pg-tree")


def test_dense_m9_grid_uses_pg_flank_shields_sparse_m8_drawn_and_tied():
    pg = grid(0.864 * 2)                         # KV: 0.48 um stripes every 0.864 um, VDD/VSS alternate
    r = router(pg)
    c9, m9, _ = r.place("M9", 20.0, 3.0, 50.0, "ck_a")
    c8, m8, e8 = r.place("M8", 20.0, 3.0, 50.0, "ck_b")
    assert m9 == C.FLANK and m8 == C.DRAWN and e8 is not None
    segs = [("M9", c9, 3.0, c9, 50.0, "ck_a", "tree", m9), ("M8", 3.0, c8, 50.0, c8, "ck_b", "tree", m8, e8)]
    cen = census(pg, segs)
    assert cen["shorts"] == 0 and cen["spacing"] == 0
    assert not C.flank_census(pg, segs, ND)
    st = C.shield_stripes([("M8", 3.0, c8, 50.0, c8, e8)], ND)
    ties = C.shield_ties(st, pg, ND["width"])
    assert not ties["untied"] and not ties["shorts"]


def test_flank_needs_pg_on_both_sides_over_the_whole_span():
    pg = [r for r in grid(1.728) if not (r[1] == "M9" and r[3] == 0.0 and r[2] > 30.0)]   # M9 grid only for x <= 30
    ix = C.MetalIndex(ND["space"])
    for s in C.pg_shapes(pg):
        ix.add(s)
    r = router(pg)
    c, m, _ = r.place("M9", 20.0, 3.0, 50.0, "ck_a")
    assert m == C.FLANK and C.flanked(ix, C.seg_shapes("M9", c, 3.0, 50.0, "ck_a", ND, None)[0], C.flank_gap(ND))
    edge = max(x for n, L, x, *_ in pg if L == "M9")        # beside the last stripe: PG on one side only
    s = C.seg_shapes("M9", edge + 0.40, 3.0, 50.0, "ck_b", ND, None)[0]
    assert not C.flanked(ix, s, C.flank_gap(ND))


def test_short_segment_shield_extends_to_a_vss_tie():
    pg = grid(8.64)
    r = router(pg)
    c, m, e = r.place("M8", 20.0, 10.10, 10.60, "ck_a")      # 0.5-um drop between two VSS M9 stripes
    assert m == C.DRAWN and e > C.shield_geom(ND)[2]
    st = C.shield_stripes([("M8", 10.10, c, 10.60, c, e)], ND)
    assert not C.shield_ties(st, pg, ND["width"])["untied"]


def test_fixed_wires_router_separates_collinear_parent_drop_and_child_trunk():
    # parent net n0 -> cell A (drop along x = A + off), A's own net runs vertically from A: before the lane both sat on
    # the same M9 line (a clock-clock short between two nets)
    cells = {"A": dict(x=20.0, y=20.0), "B": dict(x=20.0, y=40.0), "P": dict(x=5.0, y=10.0)}
    M = dict(taps=[], meta=dict(root_um=[0.0, 0.0]))
    nets = [dict(name="n0", drv="P", loads=["A"]), dict(name="n1", drv="A", loads=["B"])]
    free = C.fixed_wires(M, cells, nets, 0.0, 0.0)
    pg = grid(8.64)
    assert census(pg, C.tree_segs(free))["shorts"]
    r = router(pg)
    w = C.fixed_wires(M, cells, nets, 0.0, 0.0, router=r)
    cen = census(pg, C.tree_segs(w))
    assert cen["shorts"] == 0 and cen["spacing"] == 0
    assert all(len(x["shield_modes"]) == len(x["segs"]) == len(x["shield_ext"]) for x in w)
    tcl = "\n".join(C.combo_tcl(w, ND, "VSS"))
    assert "proc fw {sw L x0 y0 x1 y1 {sh 1} {ex" in tcl
    assert abs(sum(x["wire_um"] for x in w) - sum(x["wire_um"] for x in free)) < 2 * 8.64


def test_no_legal_track_is_a_plan_error():
    # a solid VDD sheet on M8 and M9: nothing fits
    pg = [("VDD", "M8", 0.0, 0.0, 60.0, 60.0), ("VDD", "M9", 0.0, 0.0, 60.0, 60.0)]
    cells = {"A": dict(x=20.0, y=20.0), "P": dict(x=5.0, y=10.0)}
    M = dict(taps=[], meta=dict(root_um=[0.0, 0.0]))
    try:
        C.fixed_wires(M, cells, [dict(name="n0", drv="P", loads=["A"])], 0.0, 0.0, router=router(pg))
    except C.PlanError as e:
        assert {r["kind"] for r in e.rows} == {"no_clock_track"}
    else:
        raise AssertionError("expected a plan error")


def test_shield_union_merges_overlapping_same_track_shields_only():
    """CLOCK-KV-R10: a trunk and the leg that retraces it share one shield track; RCX double-counts coincident
    shapes, so the shield net carries one box per overlapping/abutting run, other tracks untouched"""
    boxes = [("M9", True, 0, 16, 0, 100), ("M9", True, 0, 16, 50, 200), ("M9", True, 0, 16, 200, 250),
             ("M9", True, 0, 16, 300, 400), ("M9", True, 24, 40, 0, 100), ("M8", False, 0, 16, 0, 100)]
    out, n = C.shield_union(boxes)
    assert n == 3
    assert sorted(out) == sorted([("M9", True, 0, 16, 0, 250), ("M9", True, 0, 16, 300, 400),
                                  ("M9", True, 24, 40, 0, 100), ("M8", False, 0, 16, 0, 100)])


def test_shield_merge_tcl_is_one_proc_and_call_on_the_shield_net():
    L = C.shield_merge_tcl("VSS", ND)
    assert len(L) == 2 and L[0].startswith("proc ot_merge_shields ") and L[1].startswith("ot_merge_shields VSS ")
    assert "odb::dbSBox_destroy" in L[0] and L[0].count("odb::dbSBox_create") == 2
    assert L[0].count("{") == L[0].count("}")


def test_combo_merge_shields_is_the_default():
    """COORD 10-26 21:28: --merge-shields is the DEFAULT for die_clock_mesh combo; --no-merge-shields keeps the
    pre-R10 shapes; an args object without the attribute (programmatic callers) also merges"""
    src = (Path(__file__).resolve().parent / "die_clock_mesh.py").read_text()
    assert '"--merge-shields", action=argparse.BooleanOptionalAction, default=True' in src
    assert 'merge_sh = bool(getattr(a, "merge_shields", True))' in src
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-shields", action=argparse.BooleanOptionalAction, default=True)
    assert ap.parse_args([]).merge_shields is True
    assert ap.parse_args(["--no-merge-shields"]).merge_shields is False


def _boxes(stripes, nd):
    """shield stripe centre lines -> shield_union boxes (layer, vertical, c_lo, c_hi, a_lo, a_hi) in integer nm"""
    hw = nd["width"] / 2
    nm = lambda v: int(round(v * 1000))
    out = []
    for lay, x0, y0, x1, y1 in stripes:
        if lay == "M8":
            out.append((lay, False, nm(y0 - hw), nm(y0 + hw), nm(min(x0, x1)), nm(max(x0, x1))))
        else:
            out.append((lay, True, nm(x0 - hw), nm(x0 + hw), nm(min(y0, y1)), nm(max(y0, y1))))
    return out


def _coverage(boxes):
    """the covered metal: per (layer, direction, track) the union of the along-axis intervals"""
    g = {}
    for b in boxes:
        g.setdefault(tuple(b[:4]), []).append((b[4], b[5]))
    cov = {}
    for k, iv in g.items():
        runs = []
        for lo, hi in sorted(iv):
            if runs and lo <= runs[-1][1]:
                runs[-1][1] = max(runs[-1][1], hi)
            else:
                runs.append([lo, hi])
        cov[k] = [tuple(r) for r in runs]
    return cov


def test_merge_default_changes_only_shield_shape_count_not_metal():
    """regression for the default flip: old default (no merge) vs new default (merge) on a trunk + the H-tree leg
    that retraces it on the same track + an unrelated strap -- identical covered metal on every track, fewer shapes,
    and every box that overlapped nothing is passed through unchanged"""
    segs = [("M9", 10.0, 0.0, 10.0, 100.0), ("M9", 10.0, 40.0, 10.0, 160.0),   # trunk + retracing leg (same x)
            ("M9", 10.0, 160.0, 10.0, 200.0),                                    # abutting continuation
            ("M9", 30.0, 0.0, 30.0, 50.0), ("M8", 0.0, 70.0, 60.0, 70.0),        # untouched tracks
            ("M8", 20.0, 90.0, 50.0, 90.0), ("M8", 45.0, 90.0, 80.0, 90.0)]      # M8 overlap
    old = _boxes(C.shield_stripes(segs, ND), ND)
    new, nmerged = C.shield_union(old)
    assert _coverage(new) == _coverage(old)                      # same metal on every track
    assert len(new) < len(old) and nmerged > 0                   # only the shape count changes
    single = [b for b in old if sum(1 for c in old if c[:4] == b[:4] and c[4] <= b[5] and b[4] <= c[5]) == 1]
    assert set(single) <= set(new)                               # non-overlapping shapes pass through unchanged
    # 2 stripes per segment: M9 x=10 (3 segs -> 1 run each side), M8 y=90 (2 segs -> 1 run each side)
    assert len(old) == 14 and len(new) == 8


def test_shield_union_is_coverage_preserving_on_random_boxes():
    import random
    rnd = random.Random(1026)
    for _ in range(200):
        boxes = [(rnd.choice(("M8", "M9")), rnd.random() < 0.5, c, c + 160, lo, lo + rnd.randint(1, 400))
                 for c in (rnd.choice((0, 240, 480)) for _ in range(rnd.randint(1, 12)))
                 for lo in (rnd.randint(0, 1000),)]
        new, _ = C.shield_union(boxes)
        assert _coverage(new) == _coverage(boxes)
        assert len(new) == sum(len(r) for r in _coverage(boxes).values())
