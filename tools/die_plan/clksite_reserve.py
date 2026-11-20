#!/usr/bin/env python3
"""CLKSITE-RESERVE-1115: per-type reservation of the die clock cell sites (lever 1, FABLE-CLOSURE-STRATEGY).

A die clock cell placed inside a partition needs its site free of type metal and its abstract free of solid OBS.
This tool turns the cell sites of a die into ROW FILES (rows_apply.py format) that set, per partition type,
  clock.reserved_sites_um = [{rect_um, kind: "die_clock_tree", route_layers: "M1-M7"}, ...]
gen_phys.reserved_sites_tcl then emits a placement blockage AND M1-M7 routing obstructions in the type build, and
die_trial.write_kit cuts the same rectangles out of the plan abstract AND the closed view LEF (M1-M7 + M7 PG).
Rectangles are MERGED (merge_rects): one rect per overlap cluster, then coarse grid buckets until at most
--max-rects per type remain, so every cut master keeps a small OBS count (fragmented windows cost 9.4 -> 75 GB per unit).

usage:
  clksite_reserve.py PLAN.json OUT_ROWS.json --tree TREE.json [TREE.json..]   (die_trial kit clock/tree.json, die frame)
  clksite_reserve.py PLAN.json OUT_ROWS.json --from-islands                    (plan clock.die_islands_um template;
                                                                               die_islands_um is deleted by the row)
options: --max-rects 100  --margin-um 0.25  --layers M1-M7  --lane NAME  --types T,T  --types-uncovered
Existing reserved_sites_um rows of another kind (landing_ring_bank) are kept.  A merged rect that would touch a planned
hard core is not formed (the members stay separate).  Neither is one that would run more than 10 um along a hard core
within --edge-gap-um (5) of it: a reserved rect is an M1-M7 obstruction, so that would wall in the core's edge pins.
There the fine site rects are kept and --max-rects is exceeded (report: over_cap; walls must be 0).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LAYERS = "M1-M7"


def _touch(a, b, g=0.0):
    return not (a[0] > b[2] + g or b[0] > a[2] + g or a[1] > b[3] + g or b[1] > a[3] + g)


def _bbox(rs):
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


def _area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


class _RectIndex:
    """Spatial lookup for the production-shape fixed FT-cell columns."""
    def __init__(self, rects, pitch=50.0):
        import math
        self.pitch, self.rows = pitch, {}
        for r in rects:
            for i in range(math.floor(r[0] / pitch), math.floor(r[2] / pitch) + 1):
                for j in range(math.floor(r[1] / pitch), math.floor(r[3] / pitch) + 1):
                    self.rows.setdefault((i, j), []).append(r)

    def hits(self, r):
        import math
        for i in range(math.floor(r[0] / self.pitch), math.floor(r[2] / self.pitch) + 1):
            for j in range(math.floor(r[1] / self.pitch), math.floor(r[3] / self.pitch) + 1):
                if _hits(r, self.rows.get((i, j), ())):
                    return True
        return False


def _hits(r, blockers):
    if isinstance(blockers, _RectIndex):
        return blockers.hits(r)
    return any(r[0] < b[2] - 1e-9 and b[0] < r[2] - 1e-9 and r[1] < b[3] - 1e-9 and b[1] < r[3] - 1e-9 for b in blockers)


def _cluster(rects):
    """union-find on touching/overlapping rects (sweep over x); lossless apart from bbox of an L shape"""
    n = len(rects)
    par = list(range(n))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    order = sorted(range(n), key=lambda i: rects[i][0])
    act = []
    for i in order:
        act = [j for j in act if rects[j][2] >= rects[i][0]]
        for j in act:
            if _touch(rects[i], rects[j]):
                par[f(i)] = f(j)
        act.append(i)
    groups = {}
    for i in range(n):
        groups.setdefault(f(i), []).append(rects[i])
    return list(groups.values())


EDGE_GAP_UM = 5.0        # a merged rect this close to a hard-core edge is a wall in front of the core's pins
EDGE_MAX_LEN_UM = 10.0   # ... unless it is shorter than this (FABLE-PD-KV-HG1 B-1, HEAD NF14: keep the fine site rects)


def _wall(bb, blockers, gap=EDGE_GAP_UM, max_len=EDGE_MAX_LEN_UM):
    """True when bb is longer than max_len and lies within gap of a blocker (hard core): reserved sites are M1-M7 routing
    obstructions, so such a rect closes the channel the core's edge pins escape through.  gap None/0 = rule off."""
    if not gap or max(bb[2] - bb[0], bb[3] - bb[1]) <= max_len:
        return False
    return _hits((bb[0] - gap, bb[1] - gap, bb[2] + gap, bb[3] + gap), blockers)


def _bad(bb, blockers, gap, point_blockers=()):
    return _hits(bb, blockers) or _hits(bb, point_blockers) or _wall(bb, blockers, gap)


def _bucket(rects, s, blockers, gap=EDGE_GAP_UM, point_blockers=()):
    buckets = {}
    for r in rects:
        buckets.setdefault((int(((r[0] + r[2]) / 2) // s), int(((r[1] + r[3]) / 2) // s)), []).append(r)
    out = []
    for g in buckets.values():
        bb = _bbox(g)
        out += [bb] if (len(g) == 1 or not _bad(bb, blockers, gap, point_blockers)) else g
    return out


def merge_rects(rects, max_rects=100, blockers=(), pre_n=1500, max_waste_um2=None, edge_gap_um=EDGE_GAP_UM, point_blockers=()):
    """-> (merged rects sorted, stats).  1) bbox of every overlap cluster; 2) if still > pre_n, small grid buckets
    (4 um, doubling) as a speed pre-pass; 3) greedy agglomeration: repeatedly merge the pair with the LEAST wasted area
    (bbox - a - b) until <= max_rects or the waste budget max_waste_um2 is spent (then the cap is exceeded, reported as over_cap).  A merge whose bbox touches a blocker (hard core) is never formed, and
    neither is one that would run more than EDGE_MAX_LEN_UM along a blocker within edge_gap_um of it (a wall on the
    core's pin edge): there the fine site rects stay and the cap gives way (edge_gap_um=0 restores the old merge).
    Optional point_blockers prevent merge padding over register sites without applying the core-edge wall rule."""
    import heapq
    if point_blockers and not isinstance(point_blockers, _RectIndex):
        point_blockers = _RectIndex(point_blockers)
    rects = [tuple(r) for r in rects]
    base_area = sum(_area(r) for r in rects)
    # stage 1 (lossless): drop duplicates and rects contained in another
    out = sorted(set(rects), key=lambda r: -_area(r))
    kept = []
    for r in out:
        if not any(k[0] <= r[0] and k[1] <= r[1] and k[2] >= r[2] and k[3] >= r[3] for k in kept):
            kept.append(r)
    out = kept
    pre_waste = 0.0
    s = 4.0
    while len(out) > pre_n and s < 1e5:        # speed pre-pass for very large sets, its waste is charged to the budget
        before = sum(_area(r) for r in out)
        out = _bucket(out, s, blockers, edge_gap_um, point_blockers)
        pre_waste = max(0.0, sum(_area(r) for r in out) - before)
        s *= 2
    out = sorted(out)
    waste = pre_waste
    if len(out) > max_rects:
        live = {i: r for i, r in enumerate(out)}
        nxt = len(out)
        heap = []

        def push(i, j):
            bb = _bbox([live[i], live[j]])
            if not _bad(bb, blockers, edge_gap_um, point_blockers):
                heapq.heappush(heap, (_area(bb) - _area(live[i]) - _area(live[j]), i, j))
        ids = sorted(live)
        for x, i in enumerate(ids):
            for j in ids[x + 1:]:
                push(i, j)
        while len(live) > max_rects and heap:
            w, i, j = heapq.heappop(heap)
            if i not in live or j not in live:
                continue
            if max_waste_um2 is not None and waste + w > max_waste_um2:
                break
            waste += w
            bb = _bbox([live.pop(i), live.pop(j)])
            live[nxt] = bb
            for k in list(live):
                if k != nxt:
                    push(k, nxt)
            nxt += 1
        out = list(live.values())
    out = sorted(set((round(a, 4), round(b, 4), round(c, 4), round(d, 4)) for a, b, c, d in out))
    st = dict(rects_in=len(rects), rects_out=len(out), area_in_um2=round(base_area, 3),
              area_out_um2=round(sum(_area(r) for r in out), 3), over_cap=max(0, len(out) - max_rects), waste_um2=round(waste, 3),
              walls=sum(1 for r in out if _wall(r, blockers)))
    return out, st


def plan_rows(plan, windows, max_rects=100, layers=LAYERS, lane="CLKSITE-RESERVE-1115", delete_islands=False,
              max_waste_frac=0.002, edge_gap_um=EDGE_GAP_UM, protect_points=False):
    """plan: schema.Plan (needs .types, core_obs via die_trial); windows {type: [rect]} -> (row file dict, report)"""
    import die_trial as D
    rows, rep = {}, {}
    for tn, rs in sorted(windows.items()):
        t = plan.types[tn]
        w, h = t["outline_um"]
        blockers = [(x0, y0, x1, y1) for (x0, y0, x1, y1, *_r) in D.core_obs(t)]
        rs = [(max(0.0, a), max(0.0, b), min(w, c), min(h, d)) for a, b, c, d in rs]
        rs = [r for r in rs if r[2] > r[0] and r[3] > r[1] and not _hits(r, blockers)]
        point_blockers = []
        if protect_points:
            import clksite_points as CP
            point_blockers = list(D.fixed_ft_rects(t))
            for cls, container, index, _ in CP.points(t):
                if cls != "ft_bit":
                    x, y = container[index]
                    g = CP.CLEAR_UM
                    point_blockers.append((x - g, y - g, x + g, y + g))
        merged, st = merge_rects(rs, max_rects, blockers, max_waste_um2=max_waste_frac * w * h,
                                edge_gap_um=edge_gap_um, point_blockers=point_blockers)
        keep = [r for r in (t.get("clock") or {}).get("reserved_sites_um", []) if r.get("kind") != "die_clock_tree"]
        new = keep + [dict(rect_um=list(m), kind="die_clock_tree", route_layers=layers) for m in merged]
        rows[tn] = {"clock.reserved_sites_um": new}
        if delete_islands and (t.get("clock") or {}).get("die_islands_um"):
            rows[tn]["clock.die_islands_um"] = {"$delete": True}
        rep[tn] = st
    return dict(lane=lane, rows=rows), rep


def _covered(w, rows, eps=1e-6):
    """window w inside the UNION of rows (a tall clock cell spans several merged row rects): split w at every row edge
    that crosses it and require each piece to sit in one row"""
    if any(w[0] >= r[0] - eps and w[1] >= r[1] - eps and w[2] <= r[2] + eps and w[3] <= r[3] + eps for r in rows):
        return True
    near = [r for r in rows if _touch(r, w)]
    xs = sorted({w[0], w[2]} | {v for r in near for v in (r[0], r[2]) if w[0] < v < w[2]})
    ys = sorted({w[1], w[3]} | {v for r in near for v in (r[1], r[3]) if w[1] < v < w[3]})
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if not any(r[0] - eps <= cx <= r[2] + eps and r[1] - eps <= cy <= r[3] + eps for r in near):
                return False
    return True


def uncovered_types(plan_types, windows):
    """HEAD-CROSSING-1119 r12 (FABLE-PD-HEAD-0015 A1): after a die clock rerun, the types whose cell windows are not all
    inside their existing die_clock_tree rows (M5-M7-only keepout rows excluded) -> {type: uncovered window count}.
    These are exactly the types whose rows must be regenerated; a fixed type list missed 12 moved trunk cells.  A type
    with no die_clock_tree row at all is not reserved by design and is not reported (the contain-check rule).
    Pass margin-0 windows (cell bodies) so a cell that moved inside its merged row is not reported."""
    out = {}
    for tn, rs in windows.items():
        rows = [r["rect_um"] for r in ((plan_types.get(tn) or {}).get("clock") or {}).get("reserved_sites_um", [])
                if r.get("kind") == "die_clock_tree" and r.get("route_layers", LAYERS) != "M5-M7"]
        n = sum(1 for w in rs if not _covered(w, rows))
        if n and rows:
            out[tn] = n
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--tree", nargs="+")
    ap.add_argument("--from-islands", action="store_true")
    ap.add_argument("--max-rects", type=int, default=100)
    ap.add_argument("--max-waste-frac", type=float, default=0.002, help="merge waste budget per type, fraction of the outline area")
    ap.add_argument("--margin-um", type=float, default=0.25)
    ap.add_argument("--native-origins", action="store_true", help="tree sites are native cell lower-left origins")
    ap.add_argument("--protect-points", action="store_true", help="merged boxes cannot cover fixed FT cells or planned register points")
    ap.add_argument("--edge-gap-um", type=float, default=EDGE_GAP_UM,
                    help="no merged rect longer than %g um within this distance of a hard core (0 = old merge)" % EDGE_MAX_LEN_UM)
    ap.add_argument("--layers", default=LAYERS)
    ap.add_argument("--lane", default="CLKSITE-RESERVE-1115")
    ap.add_argument("--types")
    ap.add_argument("--types-uncovered", action="store_true",
                    help="regenerate only the types with a tree cell window outside their current die_clock_tree rows "
                         "(after a die clock rerun: every type whose cells moved, never a fixed list); combines with --types")
    a = ap.parse_args(argv)
    if bool(a.tree) == a.from_islands:
        ap.error("give exactly one of --tree or --from-islands")
    import die_trial as D
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    if a.from_islands:
        win = {tn: [tuple(r) for r in (t.get("clock") or {}).get("die_islands_um", [])] for tn, t in P.types.items()}
        win = {k: v for k, v in win.items() if v}
    else:
        import abstract_cutout as AC
        sites = [s for p in a.tree for s in AC.tree_sites(p)]
        win, _ = D.island_windows(P, sites, snap=0.0, margin=a.margin_um, native_origins=a.native_origins)
    if a.types_uncovered and a.from_islands:
        ap.error("--types-uncovered needs --tree")
    if a.types:
        keep = set(a.types.split(","))
        win = {k: v for k, v in win.items() if k in keep}
    if a.types_uncovered:
        win0, _ = D.island_windows(P, sites, snap=0.0, margin=0.0, native_origins=a.native_origins)
        moved = uncovered_types(P.types, win0)
        print("UNCOVERED " + json.dumps(moved, sort_keys=True))
        win = {k: v for k, v in win.items() if k in moved}
    rows, rep = plan_rows(P, win, a.max_rects, a.layers, a.lane, delete_islands=a.from_islands, max_waste_frac=a.max_waste_frac,
                          edge_gap_um=a.edge_gap_um, protect_points=a.protect_points)
    Path(a.out).write_text(json.dumps(rows, indent=1) + "\n")
    tot = dict(types=len(rep), rects_in=sum(r["rects_in"] for r in rep.values()),
               rects_out=sum(r["rects_out"] for r in rep.values()),
               max_rects_per_type=max([r["rects_out"] for r in rep.values()] or [0]),
               area_out_um2=round(sum(r["area_out_um2"] for r in rep.values()), 1),
               walls=sum(r["walls"] for r in rep.values()))
    Path(a.out).with_suffix(".report.json").write_text(json.dumps(dict(total=tot, per_type=rep), indent=1) + "\n")
    print(json.dumps(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
