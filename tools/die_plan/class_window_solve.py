#!/usr/bin/env python3
"""class_window_solve.py PLAN --anchors T1,T2,... [--parts-re RE] --out PLAN_OUT [--report R.json]
UNIFY-TOOLS-0300 (FABLE-SUPERSET-0415 sections 5 / 10, QC-PLAN-R3 slw_fe pilot 11-20): the class window solver.

When several types become ONE superset type, the instances that used to be the other variants keep their neighbours'
old face windows (QC slw_fe: the v2 E face sat 124.6 um away from v1's, 66 G0 'src type geometry != dst type geometry'
errors), and v1 / v2 alternate along a slice column, so a column is re-pinned in one event or not at all.

The anchor types (the superset class rows) own their type-frame windows.  Every port with one end on an anchor instance
and the other end on a partition of a non-anchor type takes the anchor's die-frame geometry; the other end's TYPE window
(bus, or ft slot in / out end) is moved there in the other type's frame.  A re-pinned type then propagates the same way
to its own neighbours on the moved buses (fixed point), so a whole column settles in one pass.  A port that carries its
own face / window / layers is set to the same geometry.  Nothing is moved when the demands on one (type, bus) disagree
(two instances of a neighbour type would need different windows: that type must be unified or split first) or when an
anchor end disagrees with another anchor: those rows are listed as conflicts and the plan keeps the old window.
After the moves, windows that now overlap another window of the same type face and layer are listed (G0 'abutment'
would refuse them).  Multi-window (segments) ports are listed, never moved.

Report: moved [(type, bus, old, new)], conflicts, overlaps, skipped, mismatches before / after (the schema port
geometry rule over every port touching a moved or anchor type)."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

EPS = 1e-6


def die_to_type(P, part, die_face, win, order):
    """inverse of Plan.geom_to_die for one instance: die-frame (face, window, order) -> type-frame (face, window, order)"""
    p = P.parts[part]
    w, h = P.types[p["type"]]["outline_um"]
    o = p.get("orient", "R0")
    tf = P.type_face(part, die_face)
    a, b = win
    if tf in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    a, b = a - base, b - base
    if flip:
        a, b = ext - b, ext - a
        order = "lsb_high" if order == "lsb_low" else "lsb_low"
    return tf, [round(a, 6), round(b, 6)], order


def same(g1, g2):
    return (g1[0] == g2[0] and list(g1[2]) == list(g2[2]) and g1[3] == g2[3]
            and all(abs(x - y) <= EPS for x, y in zip(g1[1], g2[1])))


def end_geom(P, pr, side):
    """die-frame geometry of one port end in the port's own frame (dst faces flipped like schema.port_geom_from)"""
    try:
        return P.port_geom_from(pr, side)
    except (KeyError, TypeError):
        return None


def mismatches(P, raw, types):
    """the schema rule ('src type geometry != dst type geometry in the die frame') on ports touching `types`"""
    out = []
    for pr in raw["ports"]:
        ends = [pr[s]["part"] for s in ("src", "dst")]
        if not any(e in P.parts and P.parts[e]["type"] in types for e in ends):
            continue
        decl = []
        if all(k in pr for k in ("face", "layers", "window_um")):
            decl.append((pr["face"], [float(v) for v in pr["window_um"]], list(pr["layers"]), pr.get("order", "lsb_low")))
        for side in ("src", "dst"):
            g = end_geom(P, pr, side)
            if g:
                decl.append(g)
        if any(not same(a, b) for a, b in zip(decl, decl[1:])):
            out.append(pr["id"])
    return out


def type_end(t, bus):
    """(container dict, key names) of a type's bus or ft-slot end holding its window"""
    for b in t.get("buses", []):
        if b["name"] == bus:
            return b, dict(face="face", win="window_um", lay="layers", order="order")
    for sl in t.get("ft_slots", []):
        for sfx, stem in (("_i", "in"), ("_o", "out")):
            if bus == sl["name"] + sfx:
                return sl, dict(face=f"{stem}_face", win=f"{stem}_window_um", lay=f"{stem}_layers", order=f"{stem}_order",
                                lay_shared="layers", order_shared="order")
    return None, None


def set_type_end(t, bus, tf, win, lays, order):
    c, k = type_end(t, bus)
    if c is None:
        raise KeyError(f"{bus} not on type")
    old = dict(face=c.get(k["face"]), window_um=c.get(k["win"]))
    c[k["face"]], c[k["win"]] = tf, list(win)
    if "lay_shared" in k:          # ft slot: per-end keys only where they differ from the shared ones
        if list(c.get(k["lay_shared"]) or []) != list(lays):
            c[k["lay"]] = list(lays)
        else:
            c.pop(k["lay"], None)
        if c.get(k["order_shared"], "lsb_low") != order:
            c[k["order"]] = order
        else:
            c.pop(k["order"], None)
    else:
        c[k["lay"]] = list(lays)
        if order != "lsb_low" or "order" in c:
            c["order"] = order
    return old


def solve(raw, anchors, parts_re=None):
    anchors = set(anchors)
    rx = re.compile(parts_re) if parts_re else None
    pinned = {(t, None) for t in anchors}  # whole anchors or windows already solved
    moved, conflicts, skipped = [], [], {}
    frontier = set(pinned)       # (type, bus) whose geometry must propagate; None = every bus
    P = S.Plan(raw)
    touched = set(anchors)
    before = mismatches(P, raw, touched)
    while frontier:
        demands = {}                     # (type, bus) -> [(geom in type frame, from)]
        for pr in raw["ports"]:
            if pr.get("segments"):
                if any(pr[s]["part"] in P.parts and
                       ((P.parts[pr[s]["part"]]["type"], None) in frontier or
                        (P.parts[pr[s]["part"]]["type"], pr[s]["bus"]) in frontier)
                       for s in ("src", "dst")):
                    skipped[pr["id"]] = dict(port=pr["id"], why="multi-window port (segments)")
                continue
            for a_side, o_side in (("src", "dst"), ("dst", "src")):
                ap, op = pr[a_side]["part"], pr[o_side]["part"]
                if ap not in P.parts or op not in P.parts:
                    continue
                at, ot = P.parts[ap]["type"], P.parts[op]["type"]
                if (at, None) not in frontier and (at, pr[a_side]["bus"]) not in frontier:
                    continue
                if rx and not (rx.search(ap) and rx.search(op)):
                    continue
                ga = end_geom(P, pr, a_side)
                if ga is None:
                    continue
                go = end_geom(P, pr, o_side)
                if go is None:
                    continue          # no type window on that end: the port's own geometry follows (below)
                if same(ga, go):
                    continue
                if (ot, None) in pinned or (ot, pr[o_side]["bus"]) in pinned:
                    conflicts.append(dict(port=pr["id"], why=f"two pinned ends disagree: {at}.{pr[a_side]['bus']} {ga} "
                                                             f"vs {ot}.{pr[o_side]['bus']} {go}"))
                    continue
                df = ga[0] if o_side == "src" else S.OPP[ga[0]]       # the other end's die face
                tf, win, order = die_to_type(P, op, df, ga[1], ga[3])
                demands.setdefault((ot, pr[o_side]["bus"]), []).append(((tf, win, list(ga[2]), order), pr["id"], op))
        frontier = set()
        for (tn, bus), ds in sorted(demands.items()):
            g0 = ds[0][0]
            bad = [d for d in ds[1:] if not same(d[0], g0)]
            if bad:
                conflicts.append(dict(type=tn, bus=bus, why="instances need different windows (unify or split this type)",
                                      demands=[dict(port=d[1], part=d[2], geom=d[0]) for d in ds][:6]))
                continue
            c, _k = type_end(raw["partition_types"][tn], bus)
            if c is None:
                skipped[(tn, bus)] = dict(type=tn, bus=bus, why="bus has no type-frame window to move")
                continue
            old = set_type_end(raw["partition_types"][tn], bus, *g0)
            moved.append(dict(type=tn, bus=bus, old=old, new=dict(face=g0[0], window_um=g0[1], layers=g0[2], order=g0[3]),
                              ports=sorted({d[1] for d in ds})))
            frontier.add((tn, bus))
            touched.add(tn)
        # explicit port-level geometry follows its (now consistent) type ends
        pinned |= frontier
        P = S.Plan(raw)
        for pr in raw["ports"]:
            if rx and not all(pr[side]["part"] in P.parts and rx.search(pr[side]["part"])
                              for side in ("src", "dst")):
                continue
            if not all(k in pr for k in ("face", "layers", "window_um")) or pr.get("segments"):
                continue
            for side in ("src", "dst"):
                e = pr[side]["part"]
                if e in P.parts:
                    tn = P.parts[e]["type"]
                    if (tn, None) not in pinned and (tn, pr[side]["bus"]) not in pinned:
                        continue
                    g = end_geom(P, pr, side)
                    if g and not same(g, (pr["face"], pr["window_um"], pr["layers"], pr.get("order", "lsb_low"))):
                        pr.update(face=g[0], window_um=list(g[1]), layers=list(g[2]))
                        if g[3] != "lsb_low" or "order" in pr:
                            pr["order"] = g[3]
                    break
        P = S.Plan(raw)
    # An anchor may already carry the proposed window before solve() starts.
    overlaps = window_overlaps(raw, touched)
    after = mismatches(P, raw, touched)
    return dict(anchors=sorted(anchors), moved=moved, conflicts=conflicts, overlaps=overlaps, skipped=list(skipped.values()),
                mismatches_before=len(before), mismatches_after=len(after), mismatch_ports_after=after[:50],
                types_touched=sorted(touched))


def window_overlaps(raw, types):
    out = []
    for tn in sorted(types):
        t = raw["partition_types"][tn]
        ends = []
        for b in t.get("buses", []):
            if "window_um" in b and "face" in b:
                ends.append((b["name"], b["face"], sorted(b["window_um"]), set(b.get("layers", []))))
        for sl in t.get("ft_slots", []):
            for sfx, stem in (("_i", "in"), ("_o", "out")):
                if f"{stem}_window_um" in sl:
                    ends.append((sl["name"] + sfx, sl[f"{stem}_face"], sorted(sl[f"{stem}_window_um"]),
                                 set(sl.get(f"{stem}_layers", sl.get("layers", [])))))
        ends.sort(key=lambda e: (e[1], e[2][0]))
        for i, a in enumerate(ends):
            for b in ends[i + 1:]:
                if b[1] != a[1] or b[2][0] >= a[2][1] - EPS:
                    break
                if a[3] & b[3]:
                    out.append(dict(type=tn, a=a[0], b=b[0], face=a[1], a_win=a[2], b_win=b[2]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--anchors", required=True, help="comma list of superset class types whose windows are kept")
    ap.add_argument("--parts-re", help="only ports whose two partitions both match (e.g. one slice column)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    anchors = [x for x in a.anchors.split(",") if x]
    miss = [x for x in anchors if x not in raw["partition_types"]]
    if miss:
        print(f"class_window_solve: unknown anchor types {miss}", file=sys.stderr)
        return 2
    rep = solve(raw, anchors, a.parts_re)
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"class_window_solve: {len(rep['moved'])} windows moved on {len(rep['types_touched']) - len(anchors)} types, "
          f"{len(rep['conflicts'])} conflicts, {len(rep['overlaps'])} overlaps, {len(rep['skipped'])} skipped; "
          f"port geometry mismatches {rep['mismatches_before']} -> {rep['mismatches_after']}")
    return 0 if not rep["conflicts"] and not rep["overlaps"] and not rep["mismatches_after"] else 1


if __name__ == "__main__":
    sys.exit(main())
