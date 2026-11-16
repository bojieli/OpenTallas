#!/usr/bin/env python3
"""CLKSITE-QC-SNAP-1115: stamped per-type clock-site reserve rows for a whole die (QC) from a die_trial kit clock/tree.json.

Same method as CLKSITE-RESERVE-1115 hd_tile, applied to every plan type with >= 2 instances:
  1. clksite_stamp_native.stamp_tree on each such type (one template per topology class, M7 PG slide <= --max-slide, site legal in
     every instance of the class, tap terminals snapped to the M9 x / M8 y tracks clear of the M8 PG rails = generator default);
  2. every remaining tree node that lies inside a partition tile (single-instance types, tiles the stamp did not take) is slid in x
     (<= --max-slide, 0.054 steps, nearest first) off the M7 PG pairs to a legal kit clock site;
  3. clksite_reserve rows (clock.reserved_sites_um, kind die_clock_tree, M1-M7, merged rects) per type from that tree;
  4. report: rects per type, PG conflicts (tree cell body box vs M7 PG pair, type frame) before / after, legality.
usage: clksite_qc_rows.py PLAN TREE.json OUT_DIR [--max-slide 1.7] [--rep-um 150] [--max-rects 100] [--types T,T] [--no-snap-tap-pins]
Writes OUT_DIR/STAMPED_TREE.json, ROWS.json (+ROWS.report.json), REPORT.json."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as K
import clksite_stamp_native as NA


def tile_of(P, x, y):
    for n in P.parts:
        r = P.rect(n)
        if r[0] <= x < r[2] and r[1] <= y < r[3]:
            return n


def type_box_x(P, n, x, y):
    """type-frame x extent of the 2.70 x 0.81 cell box of a die-frame node (x, y) = body lower-left"""
    pts = [P.to_type(n, (x + dx, y + dy)) for dx in (-K.HALO[0], K.BODY[0] + K.HALO[0]) for dy in (-K.HALO[1], K.BODY[1] + K.HALO[1])]
    return min(p[0] for p in pts), max(p[0] for p in pts)


def pg_conflicts(P, T):
    """[(node, tile)] tree nodes inside a partition tile whose cell box overlaps an M7 PG pair"""
    bad = []
    for k, v in T["nodes"].items():
        n = tile_of(P, v["x"], v["y"])
        if not n:
            continue
        x0, x1 = type_box_x(P, n, v["x"], v["y"])
        if K._pg_overlap(x0, x1) is not None:
            bad.append((int(k), n))
    return bad


def slide_rest(P, T, site, max_slide, far_slide=4.32):
    """slide every conflicting in-tile node in x to the nearest die clock site clear of the PG pairs.
    Pass 1 <= max_slide; pass 2 (only nodes pass 1 could not clear) <= far_slide (half the 8.64 um PG pitch).  A node whose own
    position is already NOT a legal kit site is not held to legality at the new position (the kit placed it there).
    -> (moved, far_moved, stuck)"""
    moved, far, stuck = 0, 0, []
    for lim, is_far in ((max_slide, False), (far_slide, True)):
        steps = sorted((i * 0.054 for i in range(-int(lim / 0.054), int(lim / 0.054) + 1)), key=abs)
        todo = [k for k, n in pg_conflicts(P, T)] if not is_far else list(stuck)
        stuck = []
        for k in todo:
            v = T["nodes"][str(k)]
            n = tile_of(P, v["x"], v["y"])
            was_legal = site is None or site.legal((v["x"], v["y"]))
            for d in steps:
                x, y = round(v["x"] + d, 4), v["y"]
                if tile_of(P, x, y) != n:
                    continue
                x0, x1 = type_box_x(P, n, x, y)
                if K._pg_overlap(x0, x1) is None and (site is None or not was_legal or site.legal((x, y))):
                    break
            else:
                stuck.append(k)
                continue
            if d:
                v["x"] = x
                if "req_xy" in v:
                    v["req_xy"] = [x, y]
                moved += 1
                far += int(is_far)
                nb = T["node_buf"].get(str(k))
                if nb in T["sites"]:
                    T["sites"][nb] = [x, y]
                for tp in T["taps"]:
                    if tp["node"] == k:
                        tp["xy"] = [x, y]
    return moved, far, stuck


def clone(T):
    """stamp_tree edits node dicts / kids lists of its input in place: give it a private copy so a reverted stamp leaves T intact"""
    return dict(T, nodes={k: dict(v, kids=list(v.get("kids", []))) for k, v in T["nodes"].items()},
                taps=[dict(t) for t in T["taps"]], node_buf=dict(T["node_buf"]), parent_of=dict(T["parent_of"]),
                sites=dict(T["sites"]))


def dangling(T):
    """edges of the tree that point at a missing node or are not mirrored in the kids list -> count"""
    nd = T["nodes"]
    bad = 0
    for k, v in nd.items():
        p = v.get("parent")
        if p is not None and (str(p) not in nd or int(k) not in nd[str(p)].get("kids", [])):
            bad += 1
        bad += sum(1 for c in v.get("kids", []) if str(c) not in nd)
    return bad


def run(P, T, site, max_slide=1.7, rep_um=150.0, types=None, snap=True, stamp=True):
    cnt = {}
    for n, p in P.parts.items():
        cnt[p["type"]] = cnt.get(p["type"], 0) + 1
    todo = sorted(t for t, c in cnt.items() if c >= 2 and (types is None or t in types)) if stamp else []
    before = len(pg_conflicts(P, T))
    rep = dict(types_multi=len(todo), stamped_types=0, stamp={}, skipped_types=[])
    for tn in todo:
        try:
            T2, r = NA.stamp_tree(P, clone(T), tn, max_slide, rep_um, site=site, snap_tap_pins=snap)
        except Exception as e:     # a type without in-tile nodes etc.
            rep["skipped_types"].append([tn, repr(e)[:120]])
            continue
        bad = dangling(T2)
        if bad:      # a node slid across a tile border into a neighbouring type tile: keep the tree as it was before this type
            rep["skipped_types"].append([tn, "dangling edges %d after stamp (reverted)" % bad])
            continue
        T = T2
        rep["stamped_types"] += 1
        rep["stamp"][tn] = {k: r.get(k) for k in ("instances", "stamped", "no_legal_slide", "legs_over_405", "slid_sites", "unchanged")}
    after_stamp = len(pg_conflicts(P, T))
    moved, far, stuck = slide_rest(P, T, site, max_slide)
    rep.update(dangling_edges=dangling(T), pg_conflicts_before=before, pg_conflicts_after_stamp=after_stamp, rest_slid=moved, rest_slid_beyond_max_slide=far, pg_conflicts_after=len(pg_conflicts(P, T)),
               stuck_nodes=stuck[:50])
    return T, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("out")
    ap.add_argument("--max-slide", type=float, default=1.7); ap.add_argument("--rep-um", type=float, default=150.0)
    ap.add_argument("--max-rects", type=int, default=100); ap.add_argument("--max-waste-frac", type=float, default=0.002)
    ap.add_argument("--types")
    ap.add_argument("--no-snap-tap-pins", action="store_true")
    ap.add_argument("--no-stamp", action="store_true", help="TREE is already a stamped tree: only slide the rest + rows")
    a = ap.parse_args(argv)
    import schema as S
    import die_trial as D
    import clksite_reserve as C
    import abstract_cutout as AC
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    P = S.Plan(S.load(a.plan), Path(a.plan))
    site = D.clock_site(P)
    T, rep = run(P, json.load(open(a.tree)), site, a.max_slide, a.rep_um, set(a.types.split(",")) if a.types else None,
                 not a.no_snap_tap_pins, not a.no_stamp)
    (out / "STAMPED_TREE.json").write_text(json.dumps(T))
    win, _ = D.island_windows(P, AC.tree_sites(str(out / "STAMPED_TREE.json")), snap=0.0, margin=0.25)
    rows, rr = C.plan_rows(P, win, a.max_rects, C.LAYERS, "CLKSITE-QC-SNAP-1115", max_waste_frac=a.max_waste_frac)
    (out / "ROWS.json").write_text(json.dumps(rows, indent=1) + "\n")
    (out / "ROWS.report.json").write_text(json.dumps(rr, indent=1) + "\n")
    rep.update(rows_types=len(rows["rows"]), rects_per_type={t: v["rects_out"] for t, v in rr.items()},
               rects_total=sum(v["rects_out"] for v in rr.values()), over_cap={t: v["over_cap"] for t, v in rr.items() if v["over_cap"]})
    (out / "REPORT.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("stamp", "rects_per_type")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
