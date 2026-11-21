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
import math
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
    if old["face"] == tf and old["window_um"]:          # S81-LEAF-CLASS-1730: per-end landing pins follow the window
        _follow_landing(t, {bus: (tf, sorted(old["window_um"]))}, {bus: (tf, sorted(win))})
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


def _usable(L, ln, win):
    """usable (off-PG) track count of one pin layer on a die-frame window, as schema._window_pins counts it"""
    lo, hi = sorted(win)
    p, off = L["pitch_um"], L["offset_um"]
    k0 = math.ceil((lo - off) / p - 1e-9)
    k1 = math.floor((hi - off) / p + 1e-9)
    return sum(1 for k in range(k0, k1 + 1) if not S.pg_blocked_any(L, ln, off + k * p))


def _end_pin_counts(raw, parts, bus, lays):
    """{layer: pins} of the ports on (any instance in parts, bus); None when no port binds it, widths disagree, or no
    port carries its own die-frame geometry (pins then come from the type frame, identical on every copy)"""
    prs = [pr for pr in raw["ports"] for sd in ("src", "dst") if pr[sd]["part"] in parts and pr[sd]["bus"] == bus]
    ws = {S.port_pins_count(pr) for pr in prs}
    if len(ws) != 1 or not any(all(k in pr for k in ("face", "layers", "window_um")) for pr in prs):
        return None
    w, nl = ws.pop(), len(lays)
    return {ln: len(range(li, w, nl)) for li, ln in enumerate(lays)}


def mirror_parity(raw, types, step_um=0.008, max_um=0.512):
    """UNIFY-TOOLS-R3 (S81-LEAF-CLASS-1730 J7, the '0.064 um mirror off-grid' G0 abutment rows): schema.spread picks
    the same type-frame tracks in a mirrored copy only when every layer with an ODD pin count has an ODD usable-track
    count on the window (an odd pick on an even track count has no mirror-symmetric choice, so an MY / R180 copy whose
    port carries die-frame geometry lands one M7 pitch off its R0 sibling).  For each type end of `types` that has
    instances in both flip states along its face axis, widen (or narrow) the type window by the smallest step that
    makes every odd-pin layer's usable count odd (only ends some port of which carries its own die-frame geometry:
    other ports take their pins in the type frame), keeping every layer able to hold its pins and the window clear of
    the type's other windows on that face / layer.  Moves the type window only: solve() then carries it to the
    neighbours and to port-level geometry.  Returns [(type, bus, old window, new window)] and [(type, bus, why)]."""
    P = S.Plan(raw)
    moved, left = [], []
    insts = {}
    for p in raw["partitions"]:
        insts.setdefault(p["type"], []).append(p["name"])
    for tn in types:
        t = raw["partition_types"][tn]
        parts = insts.get(tn, [])
        ends = [b["name"] for b in t.get("buses", []) if "window_um" in b] + [
            sl["name"] + sfx for sl in t.get("ft_slots", []) for sfx, wk in (("_i", "in_window_um"), ("_o", "out_window_um"))
            if wk in sl]
        for bus in ends:
            g = P._type_geom(parts[0], bus) if parts else None
            if g is None:
                continue
            tf, win, lays, order = g
            flips = {(P.orient(q) in (("MX", "R180") if tf in "EW" else ("MY", "R180"))) for q in parts}
            if len(flips) < 2:
                continue
            n = _end_pin_counts(raw, set(parts), bus, lays)
            if n is None:
                continue
            odd = [ln for ln in lays if n[ln] % 2]
            if not odd:
                continue

            def ok(w):
                return _parity_ok(P, parts, (tf, w, lays, order), n, odd)
            if ok(win):
                continue
            lo, hi = sorted(win)
            others = []
            for b2 in ends:
                g2 = P._type_geom(parts[0], b2) if b2 != bus else None
                if g2 and g2[0] == tf and set(g2[2]) & set(lays):
                    others.append(sorted(g2[1]))
            best = None
            k = 1
            while best is None and k * step_um <= max_um + 1e-9:
                d = round(k * step_um, 6)
                for w in ([lo, round(hi + d, 6)], [round(lo - d, 6), hi], [lo, round(hi - d, 6)], [round(lo + d, 6), hi]):
                    if w[1] - w[0] <= 0 or any(w[0] < b + EPS and a < w[1] + EPS for a, b in others):
                        continue
                    if ok(w):
                        best = w
                        break
                k += 1
            if best is None:
                left.append((tn, bus, f"no window within {max_um} um gives an odd usable count on {odd}"))
                continue
            set_type_end(t, bus, tf, best, lays, order)
            moved.append((tn, bus, [lo, hi], best))
            P = S.Plan(raw)
            # facing ends on class types of `types` take the same die window now, transitively (a t16 ft9_o moved by
            # a t44 resize carries on to the next t16 copy's ft9_i), else solve() sees two pinned ends disagree; their
            # usable counts are those of the same die windows, so the parity holds on them too
            work = [(tn, bus)]
            while work:
                ct, cb = work.pop()
                cparts = set(insts.get(ct, []))
                dem = {}
                for pr in raw["ports"]:
                    if pr.get("segments"):
                        continue
                    for a_side, o_side in (("src", "dst"), ("dst", "src")):
                        ap, op = pr[a_side]["part"], pr[o_side]["part"]
                        if ap in cparts and pr[a_side]["bus"] == cb and op in P.parts and P.parts[op]["type"] in types:
                            ga = end_geom(P, pr, a_side)
                            go = end_geom(P, pr, o_side)
                            if ga is None or go is None or same(ga, go):
                                continue
                            df = ga[0] if o_side == "src" else S.OPP[ga[0]]
                            tf2, w2, o2 = die_to_type(P, op, df, ga[1], ga[3])
                            dem.setdefault((P.parts[op]["type"], pr[o_side]["bus"]), []).append((tf2, w2, list(ga[2]), o2))
                for (tn2, b2), ds in sorted(dem.items()):
                    c, k = type_end(raw["partition_types"][tn2], b2)
                    if c is None:
                        continue
                    if any(not same(d, ds[0]) for d in ds[1:]):
                        left.append((tn2, b2, f"facing {ct}.{cb}: instances need different windows"))
                        continue
                    old2 = sorted(c.get(k["win"]) or [])
                    set_type_end(raw["partition_types"][tn2], b2, *ds[0])
                    moved.append((tn2, b2, old2, ds[0][1]))
                    work.append((tn2, b2))
                if dem:
                    P = S.Plan(raw)
    # facing moves may have handed a processed end an even count: list what still breaks the mirror pick
    for tn in types:
        parts = insts.get(tn, [])
        for b in raw["partition_types"][tn].get("buses", []) + [
                dict(name=sl["name"] + sfx) for sl in raw["partition_types"][tn].get("ft_slots", []) for sfx in ("_i", "_o")]:
            g = P._type_geom(parts[0], b["name"]) if parts else None
            if g is None or len({(P.orient(q) in (("MX", "R180") if g[0] in "EW" else ("MY", "R180"))) for q in parts}) < 2:
                continue
            n = _end_pin_counts(raw, set(parts), b["name"], g[2])
            if n and not _parity_ok(P, parts, g, n, [ln for ln in g[2] if n[ln] % 2]):
                left.append((tn, b["name"], "even usable count after facing-end moves"))
    return moved, left


def _parity_ok(P, parts, g, n, odd):
    tf, w, lays, order = g
    for q in parts:
        dw = P.geom_to_die(q, (tf, w, lays, order))[1]
        for ln in lays:
            m = _usable(P.layers[ln], ln, dw)
            if m < n[ln] or (ln in odd and m % 2 == 0):
                return False
    return True


def solve(raw, anchors, parts_re=None, column=False):
    """column=True (UNIFY-TOOLS whole-column mode): `anchors` is a priority list (first = strongest) of the class rows
    of EVERY class in the column.  Where two anchors meet with different windows, the weaker anchor's (type, bus) end
    takes the stronger one's geometry (once per bus, then propagates like any moved end) instead of a conflict, so all
    classes of a column settle in one event.  A window still conflicts when instances of one type need different
    windows (that type is not one class), or when two ends of equal strength disagree."""
    order = list(dict.fromkeys(anchors))
    parity, parity_left = mirror_parity(raw, order)      # UNIFY-TOOLS-R3: mirror-equivariant class windows first
    anchors = set(anchors)
    rank = {(t, None): i for i, t in enumerate(order)}      # strength of a pinned whole type / solved bus
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
                ob = (ot, pr[o_side]["bus"])
                a_rank = rank.get((at, pr[a_side]["bus"]), rank.get((at, None)))
                o_rank = rank.get(ob, rank.get((ot, None)))
                weaker_anchor = (column and ob not in pinned and (ot, None) in pinned and a_rank is not None
                                 and o_rank is not None and a_rank < o_rank)
                if (column and (at, pr[a_side]["bus"]) not in pinned and (at, None) in pinned and a_rank is not None
                        and o_rank is not None and o_rank < a_rank):
                    continue          # this end is the weaker anchor: the other direction moves it
                if ((ot, None) in pinned or ob in pinned) and not weaker_anchor:
                    conflicts.append(dict(port=pr["id"], why=f"two pinned ends disagree: {at}.{pr[a_side]['bus']} {ga} "
                                                             f"vs {ot}.{pr[o_side]['bus']} {go}"))
                    continue
                df = ga[0] if o_side == "src" else S.OPP[ga[0]]       # the other end's die face
                tf, win, order = die_to_type(P, op, df, ga[1], ga[3])
                demands.setdefault((ot, pr[o_side]["bus"]), []).append(((tf, win, list(ga[2]), order), pr["id"], op,
                                                                        a_rank))
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
            rs = [d[3] for d in ds if d[3] is not None]
            if rs:
                rank[(tn, bus)] = min(rs)
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
    return dict(anchors=sorted(anchors), mirror_parity=parity, mirror_parity_left=parity_left, moved=moved, conflicts=conflicts, overlaps=overlaps, skipped=list(skipped.values()),
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


# ---------------------------------------------------------------------------------------------------------------------
# S81-LEAF-CLASS-1730: class floorplan (pin / ft-window half of FABLE-SUPERSET-0415 U5/U6, OWNER 11-20 no growth).
#
# class_merge.py needs every member of a class to carry the representative's pin table (buses + ft_slots) before it
# re-types the instances.  Leaf members do not: each has its own ft slots (the lanes it passes) at its own windows.
# class_floorplan() builds ONE class pin table and moves every member onto it:
#   - slots: the exact-width union of the members' ft slots in the representative frame (key in_face, out_face, width;
#     multiplicity = the member maximum).  A lane only uses a slot of its own width (schema: port width == bus width),
#     so a class whose union does not fit its faces must be split first (exact_classes()).
#   - assignment: every member slot takes one class slot of its key; chosen by search so that every port between two
#     class instances joins the same die-frame window on both ends (the shift form of section 2.1 item 1 falls out:
#     a lane passing one class tile into the next lands on the next one's own or slot window).
#   - windows: the class ends tied by those ports form equality groups (union-find with the x / y flip of each
#     instance); groups are packed first-fit on the class faces, so no two class windows overlap.  The outline is
#     unchanged.  Window length per (face axis, width, layers) = the longest member window of that width.
#   - every class instance gets orient q = p * t (t = member frame -> representative frame), its port ends renamed to
#     the class slot names, and partitions[].spare_ends = the class slots it does not use (superset key on the type).
#   - solve() then re-pins the non-class neighbours onto the class windows (their slots may become Z form).
# ---------------------------------------------------------------------------------------------------------------------
import collections as _col
import copy as _copy
import itertools as _it
import re as _re

ORIENTS = ("R0", "MX", "MY", "R180")
FLIPS = {"R0": "", "MX": "NS", "MY": "EW", "R180": "NSEW"}


def omul(a, b):
    """product in the (abelian) orient group R0 / MX / MY / R180"""
    fa, fb = set(FLIPS[a]), set(FLIPS[b])
    f = fa ^ fb
    return {frozenset(): "R0", frozenset("NS"): "MX", frozenset("EW"): "MY", frozenset("NSEW"): "R180"}[frozenset(f)]


def oface(face, t):
    return S.OPP[face] if face in FLIPS[t] else face


def _ends_of_type(t):
    """member ends of one type: own buses and ft slots, as raw dicts"""
    return list(t.get("buses", [])), list(t.get("ft_slots", []))


def _win_len(win):
    return round(abs(float(win[1]) - float(win[0])), 6)


def exact_classes(raw, members, face_cap_pins_um=3.6, bit_cap=4500):
    """split one class (members [(type, t)]) into exact-width sub-classes whose slot union fits every face at
    face_cap_pins_um pins per um and carries <= bit_cap ft bits.  Greedy, largest member first, least added bits."""
    T = raw["partition_types"]

    def prof(tn, t):
        c = _col.Counter()
        for s in T[tn].get("ft_slots", []):
            c[(oface(s["in_face"], t), oface(s["out_face"], t), int(s["width"]))] += 1
        return c

    def union(ps):
        u = _col.Counter()
        for p in ps:
            for k, n in p.items():
                u[k] = max(u[k], n)
        return u

    def cost(u, tn, t):
        w, h = T[tn]["outline_um"]
        face = _col.Counter()
        for (a, b, wd), n in u.items():
            face[a] += wd * n
            face[b] += wd * n
        for b in T[tn].get("buses", []):
            face[oface(b["face"], t)] += int(b["width"])
        L = dict(N=w, S=w, E=h, W=h)
        bits = sum(wd * n for (_a, _b, wd), n in u.items())
        return bits <= bit_cap and all(face[k] <= face_cap_pins_um * L[k] for k in face), bits

    groups = []
    for tn, t in sorted(members, key=lambda m: (-sum(s["width"] for s in T[m[0]].get("ft_slots", [])), m[0])):
        p = prof(tn, t)
        best = None
        for gi, g in enumerate(groups):
            ok, b = cost(union(g["p"] + [p]), tn, t)
            if ok:
                inc = b - cost(union(g["p"]), tn, t)[1]
                if best is None or inc < best[0]:
                    best = (inc, gi)
        if best is None:
            groups.append(dict(m=[(tn, t)], p=[p]))
        else:
            groups[best[1]]["m"].append((tn, t))
            groups[best[1]]["p"].append(p)
    return [g["m"] for g in groups]


class _UF:
    """union-find over class ends with an affine relation start(v) = s * start(root) + c (s = +-1)"""

    def __init__(self):
        self.par, self.rel = {}, {}

    def find(self, v):
        if v not in self.par:
            self.par[v], self.rel[v] = v, (1, 0.0)
            return v, 1, 0.0
        if self.par[v] == v:
            return v, 1, 0.0
        r, s0, c0 = self.find(self.par[v])
        s1, c1 = self.rel[v]              # v = s1 * par + c1 ; par = s0 * r + c0
        s, c = s1 * s0, s1 * c0 + c1
        self.par[v], self.rel[v] = r, (s, c)
        return r, s, c

    def union(self, a, b, s, c, tol=1e-3):
        """impose start(b) = s * start(a) + c; False when that contradicts what is already known"""
        ra, sa, ca = self.find(a)
        rb, sb, cb = self.find(b)
        # b = sb*rb + cb ; a = sa*ra + ca ; want sb*rb + cb = s*(sa*ra + ca) + c
        if ra == rb:
            return sb == s * sa and abs(cb - (s * ca + c)) <= tol
        # rb = (s*sa*ra + s*ca + c - cb) / sb  (sb = +-1)
        self.par[rb] = ra
        self.rel[rb] = (s * sa * sb, (s * ca + c - cb) * sb)
        return True

    def copy(self):
        u = _UF()
        u.par, u.rel = dict(self.par), dict(self.rel)
        return u


FACE_LAYERS = dict(NS=["M7", "M5"], EW=["M6", "M4"])    # S81 leaf face pin layers when a slot declares none


def _axis(face):
    return "NS" if face in "NS" else "EW"


def class_floorplan(raw, classes, gap_um=1.2, margin_um=6.144, max_tries=500000):
    """Joint class floorplan of every class in `classes` = [(class_id, rep, [(type, t)])] (members incl. the
    representative, t = member frame -> representative frame).  Ports between instances of ANY two of these classes
    are solved together (whole column / slice region in one pass).  Edits raw in place (pin tables, orients, port ends,
    spare_ends, superset keys) and returns a report; raises ValueError when no assignment / packing exists (raw is
    then unchanged)."""
    T = raw["partition_types"]
    tcls, tt = {}, {}
    for cid, rep, members in classes:
        if rep not in dict(members):
            raise ValueError(f"class {cid}: representative {rep} is not a member")
        for tn, t in members:
            if tn in tcls:
                raise ValueError(f"type {tn} in two classes ({tcls[tn]}, {cid})")
            tcls[tn], tt[tn] = cid, t
    C = {}                                   # cid -> class data
    lens = {}
    mslots = {}
    for cid, rep, members in classes:
        R = T[rep]
        w, h = R["outline_um"]
        own = None
        for tn, t in members:
            if T[tn]["outline_um"] != R["outline_um"]:
                raise ValueError(f"class {cid}: {tn} outline {T[tn]['outline_um']} != {R['outline_um']}")
            o = sorted((b["name"], b["dir"], int(b["width"]), oface(b["face"], t)) for b in T[tn].get("buses", []))
            if own is None:
                own = o
            elif o != own:
                raise ValueError(f"class {cid}: {tn} own buses {o} differ from {own} in the class frame")
        count, lays = _col.Counter(), {}
        for tn, t in members:
            rows = []
            for s in T[tn].get("ft_slots", []):
                fi, fo = oface(s["in_face"], t), oface(s["out_face"], t)
                k = (fi, fo, int(s["width"]))
                li = list(s.get("in_layers") or s.get("layers") or FACE_LAYERS[_axis(fi)])
                lo = list(s.get("out_layers") or s.get("layers") or FACE_LAYERS[_axis(fo)])
                rows.append((s["name"], k, int(s.get("stations", 1))))
                for face, win, ly in ((fi, s.get("in_window_um"), li), (fo, s.get("out_window_um"), lo)):
                    lk = (_axis(face), k[2], tuple(ly))
                    lens[lk] = max(lens.get(lk, 0.0), _win_len(win))
                lays.setdefault((k, "i"), li)
                lays.setdefault((k, "o"), lo)
            for k, n in _col.Counter(r[1] for r in rows).items():
                count[k] = max(count[k], n)
            mslots[tn] = rows
        for b in R.get("buses", []):
            lk = (_axis(b["face"]), int(b["width"]), tuple(b["layers"]))
            lens[lk] = max(lens.get(lk, 0.0), _win_len(b["window_um"]))
        rt = dict(members)[rep]
        own_rows = {b["name"]: dict(face=oface(b["face"], rt), width=int(b["width"]), layers=list(b["layers"]),
                                    row=b) for b in R.get("buses", [])}
        keys = sorted(count)
        cname, i = {}, 0
        for k in keys:
            for j in range(count[k]):
                cname[(k, j)] = f"ft{i}"
                i += 1
        C[cid] = dict(rep=rep, members=members, w=w, h=h, line=dict(N=w, S=w, E=h, W=h), own=own_rows,
                      count=count, lays=lays, keys=keys, cname=cname)

    def var_geom(v):
        """(face, length) of a class end v = (cid, 'own', name) | (cid, 'slot', key, j, 'i'|'o')"""
        c = C[v[0]]
        if v[1] == "own":
            o = c["own"][v[2]]
            return o["face"], lens[(_axis(o["face"]), o["width"], tuple(o["layers"]))]
        _cid, _s, k, _j, e = v
        face = k[0] if e == "i" else k[1]
        return face, lens[(_axis(face), k[2], tuple(c["lays"][(k, e)]))]

    parts = {p["name"]: p for p in raw["partitions"]}
    inst = {}
    for pn, p in parts.items():
        if p["type"] in tcls:
            inst[pn] = dict(cls=tcls[p["type"]], type=p["type"], q=omul(p.get("orient", "R0"), tt[p["type"]]),
                            origin=p["origin_um"])

    def die_rel(pn, face):
        """(s, base): die coordinate along `face` of rep-frame coordinate x is base + s * x"""
        d = inst[pn]
        c = C[d["cls"]]
        ox, oy = d["origin"]
        if face in "EW":
            return (-1, oy + c["h"]) if d["q"] in ("MX", "R180") else (1, oy)
        return (-1, ox + c["w"]) if d["q"] in ("MY", "R180") else (1, ox)

    cports = []
    for pr in raw["ports"]:
        if pr["src"]["part"] in inst and pr["dst"]["part"] in inst:
            if pr.get("segments"):
                raise ValueError(f"multi-window port {pr['id']} between class instances")
            cports.append(pr)

    def end_var(pn, bus, assign):
        d = inst[pn]
        if bus in C[d["cls"]]["own"]:
            return (d["cls"], "own", bus)
        for sn, k, _st in mslots[d["type"]]:
            for e in ("i", "o"):
                if bus == f"{sn}_{e}":
                    a = assign.get(d["type"])
                    return None if a is None else (d["cls"], "slot", k, a[sn], e)
        raise ValueError(f"{pn}.{bus} is neither an own bus nor an ft slot end of {d['type']}")

    why = {}

    def impose(uf, pr, assign):
        va = end_var(pr["src"]["part"], pr["src"]["bus"], assign)
        vb = end_var(pr["dst"]["part"], pr["dst"]["bus"], assign)
        if va is None or vb is None:
            return True
        fa, la = var_geom(va)
        fb, lb = var_geom(vb)
        if oface(fa, inst[pr["src"]["part"]]["q"]) != S.OPP[oface(fb, inst[pr["dst"]["part"]]["q"])]:
            why[pr["id"]] = "faces do not abut"
            return False
        if abs(la - lb) > 1e-6:
            why[pr["id"]] = f"window lengths {la} vs {lb}"
            return False
        sa, ca = die_rel(pr["src"]["part"], fa)
        sb, cb = die_rel(pr["dst"]["part"], fb)
        ka = ca if sa > 0 else ca - la             # die start = s * x + k
        kb = cb if sb > 0 else cb - lb
        ok = uf.union(va, vb, sb * sa, sb * (ka - kb))
        if not ok:
            why[pr["id"]] = "window equality contradicts another port"
        return ok

    allv = []
    for cid, c in C.items():
        allv += [(cid, "own", n) for n in c["own"]]
        allv += [(cid, "slot", k, j, e) for k in c["keys"] for j in range(c["count"][k]) for e in "io"]
    maxline = max(max(c["line"].values()) for c in C.values())

    def groups_ok(uf):
        by = _col.defaultdict(list)
        for v in allv:
            if v in uf.par:
                r, sg, c0 = uf.find(v)
                face, ln = var_geom(v)
                by[(r, v[0], face, sg)].append((c0, c0 + ln))
        for ivs in by.values():
            ivs.sort()
            for (a1, b1), (a2, _b2) in zip(ivs, ivs[1:]):
                if a2 < b1 + gap_um - 1e-6:
                    return False
            if ivs[-1][1] - ivs[0][0] > maxline - 2 * margin_um:
                return False
        return True

    deg = _col.Counter()
    for pr in cports:
        deg[inst[pr["src"]["part"]]["type"]] += 1
        deg[inst[pr["dst"]["part"]]["type"]] += 1
    order = sorted(tcls, key=lambda tn: (-deg[tn], tn))
    ports_of = _col.defaultdict(list)
    for pr in cports:
        ports_of[inst[pr["src"]["part"]]["type"]].append(pr)
        ports_of[inst[pr["dst"]["part"]]["type"]].append(pr)

    def choices(tn):
        c = C[tcls[tn]]
        byk = _col.defaultdict(list)
        for sn, k, _st in mslots[tn]:
            byk[k].append(sn)
        per = [[dict(zip(sns, perm)) for perm in _it.permutations(range(c["count"][k]), len(sns))]
               for k, sns in sorted(byk.items())]
        for combo in (_it.product(*per) if per else [()]):
            d = {}
            for x in combo:
                d.update(x)
            yield d

    tries = [0]
    deepest = [0, None]

    def search(ix, uf, assign):
        if ix == len(order):
            return uf, assign
        tn = order[ix]
        for ch in choices(tn):
            tries[0] += 1
            if tries[0] > max_tries:
                return None
            a2 = dict(assign)
            a2[tn] = ch
            u2 = uf.copy()
            bad = None
            for pr in ports_of[tn]:
                ends = {inst[pr["src"]["part"]]["type"], inst[pr["dst"]["part"]]["type"]}
                if ends <= set(a2) and not impose(u2, pr, a2):
                    bad = pr["id"]
                    break
            if bad is None and not groups_ok(u2):
                bad = "overlap"
            if bad is not None:
                if ix >= deepest[0]:
                    deepest[0], deepest[1] = ix, (tn, bad, why.get(bad))
                continue
            r = search(ix + 1, u2, a2)
            if r is not None:
                return r
        return None

    uf0 = _UF()
    for pr in cports:
        va = end_var(pr["src"]["part"], pr["src"]["bus"], {})
        vb = end_var(pr["dst"]["part"], pr["dst"]["bus"], {})
        if va and vb and not impose(uf0, pr, {}):
            raise ValueError(f"own-bus port {pr['id']} cannot meet on one window: {why.get(pr['id'])}")
    res = search(0, uf0, {})
    if res is None:
        raise ValueError(f"no slot assignment joins every class-class port on one window ({tries[0]} tries; "
                         f"deepest failure at type {deepest[1]})")
    uf, assign = res
    # ---- pack equality groups, one line per (class, face)
    groups = _col.defaultdict(list)
    for v in allv:
        r, s, c0 = uf.find(v)
        groups[r].append((v, s, c0))
    placed = _col.defaultdict(list)
    pos = {}

    def fits(cid, face, a, b):
        if a < margin_um - 1e-6 or b > C[cid]["line"][face] - margin_um + 1e-6:
            return False
        return all(b + gap_um <= x + 1e-6 or a >= y + gap_um - 1e-6 for x, y in placed[(cid, face)])

    def try_root(g, u):
        iv = []
        for v, s, c0 in g:
            face, ln = var_geom(v)
            a = s * u + c0
            iv.append((v[0], face, a, a + ln))
        for i1, (c1, f1, a1, b1) in enumerate(iv):
            if not fits(c1, f1, a1, b1):
                return None
            for c2, f2, a2, b2 in iv[i1 + 1:]:
                if (c1, f1) == (c2, f2) and not (b1 + gap_um <= a2 + 1e-6 or a1 >= b2 + gap_um - 1e-6):
                    return None
        return iv

    gl = sorted(groups.values(), key=lambda g: (-len(g), -max(var_geom(v)[1] for v, _s, _c in g), str(g[0][0])))
    for g in gl:
        cands = set()
        for v, s, c0 in g:
            face, ln = var_geom(v)
            L = C[v[0]]["line"][face]
            pl = placed[(v[0], face)]
            for st in [margin_um, L - margin_um - ln] + [y + gap_um for _x, y in pl] + [x - gap_um - ln for x, _y in pl]:
                cands.add(round((st - c0) * s, 6))
        hit = None
        for u in sorted(cands):
            hit = try_root(g, u)
            if hit is not None:
                break
        if hit is None:
            raise ValueError(f"faces full: cannot place group {[x[0] for x in g][:6]}")
        for (v, s, _c0), (cid, face, a, b) in zip(g, hit):
            placed[(cid, face)].append((a, b))
            pos[v] = (face, [round(a, 6), round(b, 6)], s)

    def order_of(v):
        return "lsb_low" if pos[v][2] > 0 else "lsb_high"

    # ---- write the class windows onto every member (representative frame), keeping each member's own slot names:
    # class_merge --ft-superset then collapses the now-equal pin sets to one class slot each and re-points ports,
    # per-slot landing pins and landing edges (stable naming, UNIFY-TOOLS-R3 b8ab33d192d).
    report = dict(classes=[], class_class_ports=len(cports), tries=tries[0])
    moved_pins = 0
    for cid, c in C.items():
        geo = {}
        for k in c["keys"]:
            for j in range(c["count"][k]):
                vi, vo = (cid, "slot", k, j, "i"), (cid, "slot", k, j, "o")
                g = dict(width=k[2], in_face=pos[vi][0], out_face=pos[vo][0], in_window_um=pos[vi][1],
                         out_window_um=pos[vo][1], layers=list(c["lays"][(k, "i")]), order=order_of(vi))
                if order_of(vo) != g["order"]:
                    g["out_order"] = order_of(vo)
                if list(c["lays"][(k, "o")]) != g["layers"]:
                    g["out_layers"] = list(c["lays"][(k, "o")])
                geo[(k, j)] = g
        for tn, t in c["members"]:
            row = T[tn]
            old_ends = _end_table(row, t, c["w"], c["h"])          # in the representative frame
            _frame_landing(row, t, c["w"], c["h"])
            for b in row.get("buses", []):
                v = (cid, "own", b["name"])
                b["face"], b["window_um"], b["order"] = pos[v][0], pos[v][1], order_of(v)
            new_slots = []
            for sl in row.get("ft_slots", []):
                k = next(k for sn, k, _st in mslots[tn] if sn == sl["name"])
                ns = {x: y for x, y in sl.items() if x not in FT_GEOM}
                ns.update(_copy.deepcopy(geo[(k, assign[tn][sl["name"]])]))
                ns["regs_um"] = _straight_regs(ns, c["w"], c["h"], int(ns.get("stations", 1)))
                ns.pop("bit_sites_um", None)          # the corridor siting re-sites the bits
                ns.pop("bit_site_cell_um", None)
                new_slots.append(ns)
            row["ft_slots"] = new_slots
            moved_pins += _follow_landing(row, old_ends, _end_table(row, "R0", c["w"], c["h"]))
        names = {(k, j): f"{k[0]}>{k[1]}:{k[2]}#{j}" for k in c["keys"] for j in range(c["count"][k])}
        report["classes"].append(dict(cls=cid, rep=c["rep"], members=[m for m, _t in c["members"]],
                                      instances=sorted(pn for pn, d in inst.items() if d["cls"] == cid),
                                      slots=sum(c["count"].values()),
                                      ft_bits=sum(k[2] * n for k, n in c["count"].items()),
                                      assignment={tn: {sn: names[(k, assign[tn][sn])] for sn, k, _st in mslots[tn]}
                                                  for tn, _t in c["members"]}))
    for pn, d in inst.items():
        parts[pn]["orient"] = d["q"]
    report.update(landing_pins_moved=moved_pins, orients={pn: d["q"] for pn, d in inst.items()})
    return report


FT_GEOM = ("in_face", "out_face", "in_window_um", "out_window_um", "layers", "in_layers", "out_layers", "order",
           "in_order", "out_order", "regs_um", "bit_sites_um", "width")


def _flip_xy(xy, t, w, h):
    x, y = xy
    if "EW" in FLIPS[t] or t == "R180":
        x = w - x
    if t in ("MX", "R180"):
        y = h - y
    return [round(x, 6), round(y, 6)]


def _end_table(row, t, w, h):
    """{end bus name: (face, window)} of a type's own buses and ft slot ends, mapped by orient t (outline w x h)"""
    def m(face, win, axis_len):
        face2 = oface(face, t)
        a, b = sorted(float(v) for v in win)
        flip = (face in "NS" and t in ("MY", "R180")) or (face in "EW" and t in ("MX", "R180"))
        return face2, ([axis_len - b, axis_len - a] if flip else [a, b])
    out = {}
    for b in row.get("buses", []):
        if "window_um" in b:
            out[b["name"]] = m(b["face"], b["window_um"], w if b["face"] in "NS" else h)
    for s in row.get("ft_slots", []):
        for e, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if wk in s:
                out[s["name"] + e] = m(s[fk], s[wk], w if s[fk] in "NS" else h)
    return out


def _frame_landing(row, t, w, h):
    """member frame -> representative frame for the landing contract points and edge clock taps"""
    if t == "R0":
        return
    ck = row.get("clock") or {}
    lc = ck.get("landing_contract") or {}
    for p in lc.get("pins", []):
        if "xy_um" in p:
            p["xy_um"] = _flip_xy(p["xy_um"], t, w, h)
    for ch in lc.get("collector_children", []):
        if "xy_um" in ch:
            ch["xy_um"] = _flip_xy(ch["xy_um"], t, w, h)
    for e in ck.get("edge_clocks", []):
        if "tap_um" in e:
            e["tap_um"] = _flip_xy(e["tap_um"], t, w, h)


ROLE_FOLLOW = ("cland_tstart_in", "cland_tstart_out", "cland_rstart_in", "cland_rstart_out")
ROLE_NEAR_UM = 20.0
LAND_PIN = _re.compile(r"^(fclk_in|cland_fstart_in|fclk_out|cland_fstart_out)_(.+)$")


def _follow_landing(row, old, new):
    """move the per-end landing pins (fclk_in_<end>, cland_fstart_in_<end>, fclk_out_<end>, cland_fstart_out_<end>) and
    their edge clock taps with their end's window: same offset from the window centre, same face.  -> pins moved"""
    ck = row.get("clock") or {}
    lc = ck.get("landing_contract") or {}
    n = 0

    def shift(xy, end):
        if end not in old or end not in new or old[end] == new[end]:
            return None
        (f0, w0), (f1, w1) = old[end], new[end]
        if f0 != f1:
            return None
        d = (w1[0] + w1[1]) / 2.0 - (w0[0] + w0[1]) / 2.0
        x, y = xy
        return [round(x + d, 6), y] if f1 in "NS" else [x, round(y + d, 6)]

    moves = []
    for p in lc.get("pins", []):
        m = LAND_PIN.match(p["name"])
        if m and "xy_um" in p:
            xy = shift(p["xy_um"], m.group(2))
            if xy:
                moves.append((list(p["xy_um"]), xy))
                p["xy_um"] = xy
                n += 1
    # a count-aligned start / role pin sits beside the landing pins of the lane it starts with: it follows the
    # nearest moved landing pin on its own face line (within ROLE_NEAR_UM)
    for p in lc.get("pins", []):
        if p["name"] in ROLE_FOLLOW and "xy_um" in p and moves:
            x, y = p["xy_um"]
            best = None
            for (ox, oy), (nx, ny) in moves:
                if abs(oy - y) < 1e-3 and abs(ox - x) <= ROLE_NEAR_UM:
                    d = abs(ox - x)
                    if best is None or d < best[0]:
                        best = (d, [round(x + nx - ox, 6), y])
                elif abs(ox - x) < 1e-3 and abs(oy - y) <= ROLE_NEAR_UM:
                    d = abs(oy - y)
                    if best is None or d < best[0]:
                        best = (d, [x, round(y + ny - oy, 6)])
            if best:
                p["xy_um"] = best[1]
                n += 1
    for e in ck.get("edge_clocks", []):
        m = LAND_PIN.match(e.get("port", ""))
        if m and "tap_um" in e:
            xy = shift(e["tap_um"], m.group(2))
            if xy:
                e["tap_um"] = xy
    return n


def _straight_regs(sl, w, h, n):
    """provisional station points on the straight / L / Z path between the window centres (type frame); the
    corridor siting (ft_corridor.py) replaces them with legal per-bit sites"""
    def pt(face, win):
        c = (win[0] + win[1]) / 2.0
        return {"N": (c, h), "S": (c, 0.0), "E": (w, c), "W": (0.0, c)}[face]
    a, b = pt(sl["in_face"], sl["in_window_um"]), pt(sl["out_face"], sl["out_window_um"])
    return [[round(a[0] + (b[0] - a[0]) * (j + 0.5) / n, 3), round(a[1] + (b[1] - a[1]) * (j + 0.5) / n, 3)]
            for j in range(n)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--anchors", help="comma list of superset class types whose windows are kept")
    ap.add_argument("--classes", help="JSON [{cls, rep, members: [[type, orient member->rep], ...]}]: lay the class "
                                      "windows out jointly (class_floorplan) first; every class type is then an anchor")
    ap.add_argument("--parts-re", help="only ports whose two partitions both match (e.g. one slice column)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--column", action="store_true",
                    help="whole-column mode: --anchors is a priority list of every class row in the column; a weaker "
                         "anchor end takes a stronger one's window instead of a conflict")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    anchors = [x for x in (a.anchors or "").split(",") if x]
    fp = None
    if a.classes:
        cls = [(c["cls"], c["rep"], [tuple(m) for m in c["members"]]) for c in json.loads(Path(a.classes).read_text())]
        try:
            fp = class_floorplan(raw, cls)
        except ValueError as e:
            print(f"class_window_solve: class floorplan refused: {e}", file=sys.stderr)
            return 2
        anchors += [t for _c, _r, m in cls for t, _o in m if t not in anchors]
    if not anchors:
        print("class_window_solve: --anchors or --classes is required", file=sys.stderr)
        return 2
    miss = [x for x in anchors if x not in raw["partition_types"]]
    if miss:
        print(f"class_window_solve: unknown anchor types {miss}", file=sys.stderr)
        return 2
    rep = solve(raw, anchors, a.parts_re, column=a.column)
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    if fp is not None:
        rep["class_floorplan"] = fp
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if rep["mirror_parity"] or rep["mirror_parity_left"]:
        print(f"class_window_solve: mirror parity: {len(rep['mirror_parity'])} class windows resized, "
              f"{len(rep['mirror_parity_left'])} left {rep['mirror_parity_left'][:3]}")
    print(f"class_window_solve: {len(rep['moved'])} windows moved on {len(rep['types_touched']) - len(anchors)} types, "
          f"{len(rep['conflicts'])} conflicts, {len(rep['overlaps'])} overlaps, {len(rep['skipped'])} skipped; "
          f"port geometry mismatches {rep['mismatches_before']} -> {rep['mismatches_after']}")
    return 0 if not rep["conflicts"] and not rep["overlaps"] and not rep["mismatches_after"] else 1


if __name__ == "__main__":
    sys.exit(main())
