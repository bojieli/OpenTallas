#!/usr/bin/env python3
"""DIE-REFLOOR (DIE-S81-89, 11-13): re-floor a die plan after partition types change size.

R-STREET legalize (street_rule.py) grows partition outlines (pre-approved) but only ESTIMATES the die (die_growth); it
never re-places partitions or re-derives the die ports.  A grown type then overlaps its neighbour, and a grown type in a
mirrored placement (MY / MX / R180) moves every perpendicular-face bus window in the die frame, so G0 reports
'port ... geometry ... in the die frame' mismatches (S81 la3: 253 errors).  This tool is the missing die stage.  It is
die-agnostic and only reads the plan.

    die_refloor.py refloor BASE.json CAND.json --out-plan OUT.json [--report REP.json] [--no-pad] [--no-sync-cycles]
    die_refloor.py check   PLAN.json [--report REP.json]
    die_refloor.py sidecar BASE.json PLAN.json SIDECAR_IN.json SIDECAR_OUT.json   (clock-landing regions[].box_um)

BASE is the last plan with a legal placement; CAND has the same partitions with changed partition_types (grown outlines,
added station registers).  Partition origins in CAND are ignored: they are re-solved from BASE.

MODEL (per axis, x then y; orients R0/MX/MY/R180 never swap width and height):
  * rigid ties: a port on a face PERPENDICULAR to the axis (N/S port for x, E/W port for y) fixes the relative position
    of its two partitions along the axis: their bus windows must coincide in the die frame.  The ties make rigid groups
    (union-find with offsets); two ties that disagree are a CONFLICT (reported, never forced).
  * order: two partitions that overlap in the other axis keep their BASE order and at least their BASE gap
    (abutted stays >= 0, a reserved channel keeps its width).  Longest path over the groups, lower bound = the base
    position, so partitions only move away from the die origin.
  * abutment: a port on a face PARALLEL to the axis needs the two faces to touch.  When the solve opens a gap there, one
    of the two partitions is PADDED (outline grows) on its type-high side, i.e. the side where its type frame ends, so no
    type-frame coordinate (cores, windows, stations, taps) moves: die-high side for an unflipped partition, die-low side
    for a flipped one (MY/R180 in x, MX/R180 in y).  A gap that neither side can close that way is a CONFLICT.  A type
    padded differently on two instances is a CONFLICT.  Pads change sizes, so the solve repeats until stable.
  * die: outline = solved extent + the base right/top margins; die.io / pg-domain rects follow their partition
    (type-frame exact), die.channels and the clock spine root the monotone edge map, clock.cohort.feed taps their
    source partition.  The clock-landing sidecar regions move with `sidecar` (bind needs one region per partition).
  * ports: face / window_um of every port are re-derived from its src type geometry; src != dst in the die frame is a
    CONFLICT.
  * lanes: register stages added on internal_stations bus rows are counted in lanes[].fixed_cycles
    (reach_fix.sync_fixed_cycles; the strict bind's native-station rule fixed_cycles = source + destination).

  * fit: with --fallback FB.json, while the die is over the reticle the grown type whose revert to its FB form cuts
    the overflow most is reverted (greedy, report reticle_reverted).

Exit 0 = clean (no conflicts, no overlaps, every port consistent and abutted, die inside the reticle), 1 = otherwise
(the plan is still written).
"""
import argparse
import bisect
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPP = dict(N="S", S="N", E="W", W="E")
EPS = 1e-6
RETICLE_UM = (26000.0, 33000.0)
DIE_PART = "@die"
FLIP = {0: ("MY", "R180"), 1: ("MX", "R180")}     # orients that mirror the axis


def r6(v):
    return round(float(v), 6)


# ------------------------------------------------------------------------------------------------------------ geometry
class Geo:
    """placement view: partition name -> (type name, origin, orient); sizes from a types dict (may be padded)."""

    def __init__(self, raw):
        self.raw = raw
        self.T = raw["partition_types"]
        self.parts = {p["name"]: p for p in raw["partitions"]}

    def size(self, n):
        w, h = self.T[self.parts[n]["type"]]["outline_um"]
        return float(w), float(h)

    def rect(self, n):
        x, y = map(float, self.parts[n]["origin_um"])
        w, h = self.size(n)
        return x, y, x + w, y + h

    def to_type(self, n, pt):
        x, y = float(pt[0]) - self.parts[n]["origin_um"][0], float(pt[1]) - self.parts[n]["origin_um"][1]
        w, h = self.size(n)
        o = self.parts[n].get("orient", "R0")
        return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]

    def to_die(self, n, pt):
        x, y = pt
        w, h = self.size(n)
        o = self.parts[n].get("orient", "R0")
        X, Y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]
        return r6(self.parts[n]["origin_um"][0] + X), r6(self.parts[n]["origin_um"][1] + Y)

    def flipped(self, n, ax):
        return self.parts[n].get("orient", "R0") in FLIP[ax]

    def type_geom(self, n, bus):
        t = self.T[self.parts[n]["type"]]
        for b in t.get("buses", []):
            if b["name"] == bus and "window_um" in b and "face" in b:
                return b["face"], [float(v) for v in b["window_um"]]
        for s in t.get("ft_slots", []):
            for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
                if bus == s["name"] + sfx and wk in s:
                    return s[fk], [float(v) for v in s[wk]]
        return None

    def die_face(self, n, tf):
        o = self.parts[n].get("orient", "R0")
        if tf in "NS" and o in FLIP[1]:
            return OPP[tf]
        if tf in "EW" and o in FLIP[0]:
            return OPP[tf]
        return tf

    def die_geom(self, n, bus):
        """(die face, [lo, hi] along the face) of a bus of placed partition n, or None."""
        g = self.type_geom(n, bus)
        if g is None:
            return None
        tf, (a, b) = g
        ax = 1 if tf in "EW" else 0                      # E/W windows run along y
        w, h = self.size(n)
        ext = (w, h)[ax]
        base = float(self.parts[n]["origin_um"][ax])
        if self.flipped(n, ax):
            a, b = ext - b, ext - a
        return self.die_face(n, tf), [r6(base + a), r6(base + b)]

    def port_geoms(self, q):
        """(src die geom, dst die geom seen from src) of a port; dst face is flipped to the src's side."""
        a, b = q["src"]["part"], q["dst"]["part"]
        gs = self.die_geom(a, q["src"]["bus"]) if a != DIE_PART and a in self.parts else None
        gd = self.die_geom(b, q["dst"]["bus"]) if b != DIE_PART and b in self.parts else None
        if gd is not None and a != DIE_PART:
            gd = (OPP[gd[0]], gd[1])
        return gs, gd

    def window_offset(self, n, bus, ax):
        """die coordinate of the window lo along ax minus the partition origin (depends on size and orient)."""
        g = self.type_geom(n, bus)
        tf, (a, b) = g
        ext = self.size(n)[ax]
        return ext - b if self.flipped(n, ax) else a


def port_face(geo, q):
    gs, gd = geo.port_geoms(q)
    g = gs or gd
    if g is not None:
        return g[0]
    return q.get("face")


# ------------------------------------------------------------------------------------------------------------ union-find
class UF:
    """union-find with offsets: pos[i] = pos[root] + off[i]."""

    def __init__(self, names):
        self.p = {n: n for n in names}
        self.o = {n: 0.0 for n in names}

    def find(self, n):
        if self.p[n] == n:
            return n, 0.0
        r, o = self.find(self.p[n])
        self.p[n] = r
        self.o[n] = self.o[n] + o
        return r, self.o[n]

    def union(self, a, b, d):
        """pos[b] - pos[a] = d.  Returns None when consistent, else the disagreement (um)."""
        ra, oa = self.find(a)
        rb, ob = self.find(b)
        if ra == rb:
            err = (ob - oa) - d
            return None if abs(err) < 1e-4 else err
        # pos[rb] = pos[ra] + oa + d - ob
        self.p[rb] = ra
        self.o[rb] = oa + d - ob
        return None


# ------------------------------------------------------------------------------------------------------------ solver
def overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def channel_ports(raw):
    """port ids routed through a planned die channel (die.channels[].ports): their faces are apart by design."""
    return {q for c in (raw.get("die") or {}).get("channels", []) or [] for q in c.get("ports", [])}


def solve_axis(base, geo, ax, ports, log):
    """positions along ax for every partition of geo (sizes from geo.T), given base placement. Returns
    (pos, conflicts, gaps): gaps = [(port id, low part, high part, gap um)] for abut ports left open."""
    names = sorted(geo.parts)
    oth = 1 - ax
    bpos = {n: float(base.parts[n]["origin_um"][ax]) for n in names}
    brect = {n: base.rect(n) for n in names}
    size = {n: geo.size(n)[ax] for n in names}
    uf = UF(names)
    conflicts = []
    abut = []
    perp = "NS" if ax == 0 else "EW"
    chan = channel_ports(geo.raw)
    for q in ports:
        a, b = q["src"]["part"], q["dst"]["part"]
        if a not in geo.parts or b not in geo.parts:
            continue
        ga = geo.type_geom(a, q["src"]["bus"])
        gb = geo.type_geom(b, q["dst"]["bus"])
        if ga is None or gb is None:
            continue
        f = geo.die_face(a, ga[0])
        if f in perp:
            # window lo coincide: pos[a] + off_a == pos[b] + off_b
            d = geo.window_offset(a, q["src"]["bus"], ax) - geo.window_offset(b, q["dst"]["bus"], ax)
            err = uf.union(a, b, d)
            if err is not None:
                conflicts.append(dict(kind="tie", axis="xy"[ax], port=q["id"], src=a, dst=b, err_um=round(err, 4)))
        elif q["id"] not in chan:
            lo, hi = (a, b) if f in ("E", "N") else (b, a)
            abut.append((q["id"], lo, hi))
    # order constraints between groups (base order, base gap), for pairs overlapping in the other axis
    cons = []
    for i, n in enumerate(names):
        r = brect[n]
        for m in names[i + 1:]:
            s = brect[m]
            if overlap(r[oth], r[oth + 2], s[oth], s[oth + 2]) <= EPS:
                continue
            if s[ax] >= r[ax + 2] - EPS:
                cons.append((n, m, s[ax] - r[ax + 2]))
            elif r[ax] >= s[ax + 2] - EPS:
                cons.append((m, n, r[ax] - s[ax + 2]))
            # base overlap (should not exist) is ignored
    root = {n: uf.find(n) for n in names}
    groups = sorted(set(v[0] for v in root.values()))
    lb = {g: -1e18 for g in groups}
    for n in names:
        g, o = root[n]
        # a partition mirrored along ax grows (legalize growth or pad) on its die-low side: its high edge is the anchor
        grow = size[n] - base.size(n)[ax] if geo.flipped(n, ax) else 0.0
        lb[g] = max(lb[g], bpos[n] - grow - o)
    # longest path by relaxation (graph is a DAG unless ties contradict order -> detect by iteration cap)
    gpos = dict(lb)
    edges = []
    for lo, hi, gap in cons:
        gl, ol = root[lo]
        gh, oh = root[hi]
        edges.append((gl, gh, ol + size[lo] + gap - oh, lo, hi))
    for it in range(len(groups) + 2):
        changed = False
        for gl, gh, w, lo, hi in edges:
            if gl == gh:
                continue
            if gpos[gl] + w > gpos[gh] + 1e-6:
                gpos[gh] = gpos[gl] + w
                changed = True
        if not changed:
            break
    else:
        conflicts.append(dict(kind="cycle", axis="xy"[ax], msg="ties contradict the base order (positive cycle)"))
    # ALAP pull (DIE-S81-89): a group that is the LOW side of an abutted port follows its high neighbour (the gap then
    # opens where no port crosses, e.g. between frame groups) instead of being padded.  Reverse topological order over
    # the order edges; a group without such a port stays at its ASAP position.
    abut_lo = {root[lo][0] for _, lo, hi in abut if root[lo][0] != root[hi][0]}
    succ = {}
    indeg = {g: 0 for g in groups}
    for gl, gh, w, lo, hi in edges:
        if gl != gh:
            succ.setdefault(gl, []).append((gh, w))
            indeg[gh] += 1
    order, stack = [], [g for g in groups if indeg[g] == 0]
    while stack:
        g = stack.pop()
        order.append(g)
        for h, _ in succ.get(g, ()):
            indeg[h] -= 1
            if indeg[h] == 0:
                stack.append(h)
    if len(order) == len(groups):
        final = {}
        for g in reversed(order):
            if g in abut_lo and succ.get(g):
                final[g] = max(gpos[g], min(final[h] - w for h, w in succ[g]))
            else:
                final[g] = gpos[g]
        gpos = final
    pos = {n: r6(gpos[root[n][0]] + root[n][1]) for n in names}
    # intra-group order violations (a rigid group that now overlaps itself)
    for gl, gh, w, lo, hi in edges:
        if gl == gh and pos[hi] < pos[lo] + size[lo] - 1e-4:
            conflicts.append(dict(kind="rigid_overlap", axis="xy"[ax], lo=lo, hi=hi,
                                  overlap_um=round(pos[lo] + size[lo] - pos[hi], 4)))
    gaps = []
    for pid, lo, hi in abut:
        g = pos[hi] - (pos[lo] + size[lo])
        if abs(g) > 1e-4:
            gaps.append((pid, lo, hi, round(g, 4)))
    return pos, conflicts, gaps


def pad_round(raw_new, base, geo_cur, pos, gaps, ax, pads, conflicts):
    """close abut gaps by padding (type-high side).  Returns True when a pad changed."""
    changed = False
    want = {}
    for pid, lo, hi, g in gaps:
        if g < 0:
            conflicts.append(dict(kind="abut_overlap", axis="xy"[ax], port=pid, lo=lo, hi=hi, gap_um=g))
            continue
        # lo pads at its die-high side if not flipped; hi pads at its die-low side if flipped
        if not geo_cur.flipped(lo, ax):
            cand = lo
        elif geo_cur.flipped(hi, ax):
            cand = hi
        else:
            conflicts.append(dict(kind="unpaddable_gap", axis="xy"[ax], port=pid, lo=lo, hi=hi, gap_um=g))
            continue
        want.setdefault(cand, set()).add(round(g, 4))
    for n, gs in want.items():
        if len(gs) > 1:
            conflicts.append(dict(kind="pad_disagree", axis="xy"[ax], part=n, gaps_um=sorted(gs)))
        g = min(gs)
        tn = geo_cur.parts[n]["type"]
        cur = pads.setdefault(tn, {}).get("xy"[ax])
        newp = round((cur or 0.0) + g, 4)
        pads[tn]["xy"[ax]] = newp
        o = list(raw_new["partition_types"][tn]["outline_um"])
        o[ax] = r6(float(o[ax]) + g)
        raw_new["partition_types"][tn]["outline_um"] = o
        changed = True
    return changed


def edge_map(base, geo_new, ax):
    """monotone map of die coordinates along ax: sorted (old edge, new edge) pairs from every partition's lo/hi edge."""
    pts = {}
    for n in base.parts:
        r0, r1 = base.rect(n), geo_new.rect(n)
        for k in (ax, ax + 2):
            pts[round(r0[k], 4)] = max(pts.get(round(r0[k], 4), -1e18), r1[k])
    xs = sorted(pts)
    ys = [pts[x] for x in xs]
    for i in range(1, len(ys)):                 # monotone
        ys[i] = max(ys[i], ys[i - 1])
    return xs, ys


def map_coord(m, v):
    xs, ys = m
    v = float(v)
    i = bisect.bisect_right(xs, v + 1e-9) - 1
    if i < 0:
        return r6(v)
    return r6(ys[i] + (v - xs[i]))


def map_rect(mx, my, r):
    return [map_coord(mx, r[0]), map_coord(my, r[1]), map_coord(mx, r[2]), map_coord(my, r[3])]


def move_point(base, geo, part, pt):
    """a die point that belongs to partition `part` (inside or on its outline): same type-frame point, new placement."""
    return list(geo.to_die(part, base.to_type(part, pt)))


def move_rect(base, geo, part, r):
    a = move_point(base, geo, part, (r[0], r[1]))
    b = move_point(base, geo, part, (r[2], r[3]))
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]


def is_rect(v):
    return isinstance(v, list) and len(v) == 4 and all(isinstance(u, (int, float)) for u in v)


def remap_die_frame(Q, base, geo, mx, my):
    """die-frame geometry outside the partitions: io / pg-domain rects follow their partition (type-frame exact);
    channels and anything without an owner follow the monotone edge maps; clock.cohort.feed taps 'a->b' follow a."""
    n = 0
    part_of_io = {}
    for io in Q["die"].get("io", []) or []:
        p = io.get("part") if io.get("part") in geo.parts else None
        part_of_io[io.get("name")] = p
        for k, v in list(io.items()):
            if k.endswith("_um") and is_rect(v):
                io[k] = move_rect(base, geo, p, v) if p else map_rect(mx, my, v)
                n += 1
            elif k.endswith("_um") and isinstance(v, list) and v and all(is_rect(u) for u in v):
                io[k] = [move_rect(base, geo, p, u) if p else map_rect(mx, my, u) for u in v]
                n += len(v)
    for d in ((Q["die"].get("pg") or {}).get("domains") or []):
        ps = [part_of_io.get(i) for i in d.get("io", []) or [] if part_of_io.get(i)]
        p = ps[0] if ps else None
        def mv(v):
            return move_rect(base, geo, p, v) if p else map_rect(mx, my, v)
        for obj in (d, d.get("bumps") or {}):
            for k, v in list(obj.items()):
                if k.endswith("_um") and is_rect(v):
                    obj[k] = mv(v)
                    n += 1
                elif k.endswith("_um") and isinstance(v, list) and v and all(is_rect(u) for u in v):
                    obj[k] = [mv(u) for u in v]
                    n += len(v)
    for c in Q["die"].get("channels", []) or []:
        if "rect_um" in c:
            c["rect_um"] = map_rect(mx, my, c["rect_um"])
            n += 1
    sp = (Q.get("clock") or {}).get("spine") or {}
    if "root_um" in sp:
        sp["root_um"] = [map_coord(mx, sp["root_um"][0]), map_coord(my, sp["root_um"][1])]
        n += 1
    feed = ((Q.get("clock") or {}).get("cohort") or {}).get("feed") or {}
    for k, v in list((feed.get("tap") or {}).items()):
        a = k.split("->")[0]
        feed["tap"][k] = move_point(base, geo, a, v) if a in geo.parts else [map_coord(mx, v[0]), map_coord(my, v[1])]
        n += 1
    return n


def remap_sidecar(base_raw, new_raw, side):
    """clock-landing sidecar: regions[].box_um (die frame, one region per partition) follow their partition: the low
    corner moves with the partition origin, the high corner with origin + size (centre containment kept)."""
    base, geo = Geo(base_raw), Geo(new_raw)
    n = 0
    for r in side.get("regions") or []:
        ps = [p for p in r.get("parts") or [] if p in geo.parts]
        if len(ps) != 1:
            continue
        p = ps[0]
        (bx, by), (nx, ny) = base.parts[p]["origin_um"], geo.parts[p]["origin_um"]
        (bw, bh), (nw, nh) = base.size(p), geo.size(p)
        b = r["box_um"]
        r["box_um"] = [r6(b[0] + nx - bx), r6(b[1] + ny - by), r6(b[2] + nx - bx + nw - bw), r6(b[3] + ny - by + nh - bh)]
        n += 1
    return n


# ------------------------------------------------------------------------------------------------------------ checks
def plan_check(raw):
    """[(kind, detail)] overlaps, port geometry mismatches, unabutted ports, partitions outside the die."""
    geo = Geo(raw)
    out = []
    names = sorted(geo.parts)
    R = {n: geo.rect(n) for n in names}
    W, H = map(float, raw["die"]["outline_um"])
    chan = channel_ports(raw)
    xs = sorted(names, key=lambda n: R[n][0])
    for i, n in enumerate(xs):
        a = R[n]
        if a[0] < -EPS or a[1] < -EPS or a[2] > W + EPS or a[3] > H + EPS:
            out.append(("outside_die", n))
        for m in xs[i + 1:]:
            b = R[m]
            if b[0] >= a[2] - 1e-4:
                break
            if overlap(a[0], a[2], b[0], b[2]) > 1e-4 and overlap(a[1], a[3], b[1], b[3]) > 1e-4:
                out.append(("overlap", "%s/%s" % (n, m)))
    for q in raw["ports"]:
        a, b = q["src"]["part"], q["dst"]["part"]
        gs, gd = geo.port_geoms(q)
        pg = (q["face"], [r6(v) for v in q["window_um"]]) if "face" in q and "window_um" in q else None
        decl = [g for g in (pg, gs, gd) if g is not None]
        if any(g[0] != decl[0][0] or any(abs(u - v) > 1e-4 for u, v in zip(g[1], decl[0][1])) for g in decl):
            out.append(("port_geometry", q["id"]))
            continue
        if a in geo.parts and b in geo.parts and decl and q["id"] not in chan:
            f = decl[0][0]
            ra, rb = R[a], R[b]
            touch = {"N": ra[3] - rb[1], "S": rb[3] - ra[1], "E": ra[2] - rb[0], "W": rb[2] - ra[0]}[f]
            if abs(touch) > 1e-4:
                out.append(("port_not_abutted", q["id"]))
    return out


# ------------------------------------------------------------------------------------------------------------ refloor
def refloor(base_raw, cand_raw, pad=True, max_rounds=12, log=print):
    base = Geo(base_raw)
    Q = copy.deepcopy(cand_raw)
    for p in Q["partitions"]:
        p["origin_um"] = list(base.parts[p["name"]]["origin_um"])
    if {p["name"] for p in Q["partitions"]} != set(base.parts):
        raise ValueError("BASE and CAND must have the same partitions")
    pads = {}
    conflicts = []
    prev_sig = None
    ports = Q["ports"]
    for rnd in range(max_rounds):
        geo = Geo(Q)
        rc = []
        newpos = {}
        allgaps = {}
        for ax in (0, 1):
            pos, c, gaps = solve_axis(base, geo, ax, ports, log)
            newpos[ax] = pos
            rc += c
            allgaps[ax] = gaps
        for p in Q["partitions"]:
            p["origin_um"] = [newpos[0][p["name"]], newpos[1][p["name"]]]
        geo = Geo(Q)
        changed = False
        sig = tuple(sorted((pid, g) for ax in (0, 1) for pid, lo, hi, g in allgaps[ax]))
        if sig and sig == prev_sig:
            # the same gaps re-open after padding: a pad pushes its own neighbour (rigid conflict upstream)
            conflicts = rc + [dict(kind="pad_no_progress", gaps=len(sig), ports=[s_[0] for s_ in sig[:20]])]
            break
        prev_sig = sig
        if pad:
            for ax in (0, 1):
                # an axis with a rigid conflict is not padded: the pads would chase the conflict (no fixed point)
                if any(c.get("axis") == "xy"[ax] and c["kind"] in ("tie", "rigid_overlap", "cycle") for c in rc):
                    continue
                changed |= pad_round(Q, base, geo, newpos[ax], allgaps[ax], ax, pads, rc)
        if not changed:
            conflicts = rc
            break
        log("  round %d: padded %d types" % (rnd + 1, len(pads)))
    else:
        conflicts = rc + [dict(kind="no_converge", rounds=max_rounds)]
    geo = Geo(Q)
    # die outline: keep the base far margins
    W0, H0 = map(float, base_raw["die"]["outline_um"])
    bx1 = max(base.rect(n)[2] for n in base.parts)
    by1 = max(base.rect(n)[3] for n in base.parts)
    nx1 = max(geo.rect(n)[2] for n in geo.parts)
    ny1 = max(geo.rect(n)[3] for n in geo.parts)
    W1, H1 = r6(nx1 + (W0 - bx1)), r6(ny1 + (H0 - by1))
    Q["die"]["outline_um"] = [W1, H1]
    mx, my = edge_map(base, geo, 0), edge_map(base, geo, 1)
    moved_rects = remap_die_frame(Q, base, geo, mx, my)
    # ports: re-derive from the src type geometry
    rederived = 0
    for q in Q["ports"]:
        gs, gd = geo.port_geoms(q)
        g = gs or gd
        if gs is not None and gd is not None and (gs[0] != gd[0] or any(abs(u - v) > 1e-4 for u, v in zip(gs[1], gd[1]))):
            conflicts.append(dict(kind="port_geometry", port=q["id"], src=gs, dst=gd))
        if g is not None and "window_um" in q:
            if q.get("face") != g[0] or any(abs(u - v) > 1e-6 for u, v in zip(q["window_um"], g[1])):
                rederived += 1
            q["face"], q["window_um"] = g[0], list(g[1])
    moved = sum(1 for n in base.parts if base.parts[n]["origin_um"] != geo.parts[n]["origin_um"])
    grown = {tn: [base_raw["partition_types"][tn]["outline_um"], cand_raw["partition_types"][tn]["outline_um"]]
             for tn in cand_raw["partition_types"] if tn in base_raw["partition_types"]
             and base_raw["partition_types"][tn]["outline_um"] != cand_raw["partition_types"][tn]["outline_um"]}
    lo, hi = sorted((W1, H1)), sorted(RETICLE_UM)
    rep = dict(die_before=[W0, H0], die_after=[W1, H1], dW=r6(W1 - W0), dH=r6(H1 - H0),
               area_pct=round(100.0 * (W1 * H1 / (W0 * H0) - 1), 3),
               reticle_fits=lo[0] <= hi[0] + EPS and lo[1] <= hi[1] + EPS,
               reticle_headroom_um=[round(hi[0] - lo[0], 2), round(hi[1] - lo[1], 2)],
               grown_types=grown, padded_types=pads, moved_partitions=moved, ports_rederived=rederived,
               die_rects_moved=moved_rects, conflicts=conflicts)
    return Q, rep


def reticle_over(rep):
    lo, hi = sorted(rep["die_after"]), sorted(RETICLE_UM)
    return max(0.0, lo[0] - hi[0]) + max(0.0, lo[1] - hi[1])


def fit_reticle(base_raw, cand_raw, fallback_raw, types=None, pad=True, log=print):
    """greedy: while the re-floored die is over the reticle, give back the grown type (CAND type replaced by its
    FALLBACK form) whose revert cuts the overflow most (ties: the smaller growth).  Returns (CAND', reverted, rep)."""
    C = copy.deepcopy(cand_raw)
    quiet = lambda *a: None  # noqa: E731
    Q, rep = refloor(base_raw, C, pad=pad, log=quiet)
    reverted = []
    while reticle_over(rep) > EPS:
        ov = reticle_over(rep)
        grown = [tn for tn, t in C["partition_types"].items() if (types is None or tn in types)
                 and tn in fallback_raw["partition_types"]
                 and t["outline_um"] != fallback_raw["partition_types"][tn]["outline_um"]]
        if not grown:
            break
        best = None
        for tn in grown:
            C2 = dict(C, partition_types=dict(C["partition_types"]))
            C2["partition_types"][tn] = fallback_raw["partition_types"][tn]
            _, r2 = refloor(base_raw, C2, pad=pad, log=quiet)
            g = sum(float(a) - float(b) for a, b in zip(C["partition_types"][tn]["outline_um"],
                                                        fallback_raw["partition_types"][tn]["outline_um"]))
            key = (ov - reticle_over(r2), -g)
            if best is None or key > best[0]:
                best = (key, tn, r2)
        (gain, _), tn, r2 = best
        C["partition_types"][tn] = copy.deepcopy(fallback_raw["partition_types"][tn])
        reverted.append(dict(type=tn, overflow_before=round(ov, 2), overflow_after=round(reticle_over(r2), 2)))
        log("  reticle fit: reverted %s -> overflow %.2f um" % (tn, reticle_over(r2)))
        rep = r2
    return C, reverted, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("refloor")
    a.add_argument("base")
    a.add_argument("cand")
    a.add_argument("--out-plan", required=True)
    a.add_argument("--report")
    a.add_argument("--no-pad", action="store_true")
    a.add_argument("--no-sync-cycles", action="store_true")
    a.add_argument("--fallback", help="plan whose partition_types are the no-growth form of each grown type; when the "
                   "re-floored die is over the reticle, grown types are reverted to it greedily until it fits")
    a.add_argument("--fit-types", help="file with the type names --fallback may revert (one per line; default all)")
    sc = sub.add_parser("sidecar")
    sc.add_argument("base")
    sc.add_argument("plan")
    sc.add_argument("sidecar_in")
    sc.add_argument("sidecar_out")
    c = sub.add_parser("check")
    c.add_argument("plan")
    c.add_argument("--report")
    args = ap.parse_args(argv)
    if args.cmd == "sidecar":
        side = json.loads(Path(args.sidecar_in).read_text())
        n = remap_sidecar(json.loads(Path(args.base).read_text()), json.loads(Path(args.plan).read_text()), side)
        Path(args.sidecar_out).write_text(json.dumps(side, separators=(",", ":")))
        print("DIE_REFLOOR_SIDECAR regions moved %d" % n)
        return 0
    if args.cmd == "check":
        raw = json.loads(Path(args.plan).read_text())
        errs = plan_check(raw)
        kinds = {}
        for k, d in errs:
            kinds.setdefault(k, []).append(d)
        if args.report:
            Path(args.report).write_text(json.dumps(kinds, indent=1))
        print("DIE_REFLOOR_CHECK %s" % (" ".join("%s=%d" % (k, len(v)) for k, v in sorted(kinds.items())) or "clean"))
        return 1 if errs else 0
    base = json.loads(Path(args.base).read_text())
    cand = json.loads(Path(args.cand).read_text())
    reverted = None
    if args.fallback:
        fb = json.loads(Path(args.fallback).read_text())
        only = set(Path(args.fit_types).read_text().split()) if args.fit_types else None
        cand, reverted, _ = fit_reticle(base, cand, fb, types=only, pad=not args.no_pad)
    Q, rep = refloor(base, cand, pad=not args.no_pad)
    if reverted is not None:
        rep["reticle_reverted"] = reverted
    if not args.no_sync_cycles:
        sys.path.insert(0, str(HERE))
        import reach_fix as RF
        rep["fixed_cycles"] = RF.sync_fixed_cycles(base, Q, args.base)
    errs = plan_check(Q)
    rep["check"] = {}
    for k, d in errs:
        rep["check"].setdefault(k, []).append(d)
    Path(args.out_plan).write_text(json.dumps(Q, indent=1) + "\n")
    if args.report:
        Path(args.report).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print("DIE_REFLOOR die %s -> %s (dW %.2f dH %.2f, %.2f%%) reticle_fits=%s headroom %s; moved %d parts, padded %d "
          "types, %d ports re-derived, %d conflicts, check %s" % (
              rep["die_before"], rep["die_after"], rep["dW"], rep["dH"], rep["area_pct"], rep["reticle_fits"],
              rep["reticle_headroom_um"], rep["moved_partitions"], len(rep["padded_types"]), rep["ports_rederived"],
              len(rep["conflicts"]), {k: len(v) for k, v in rep["check"].items()} or "clean"))
    if "fixed_cycles" in rep:
        fc = rep["fixed_cycles"]
        print("DIE_REFLOOR fixed_cycles: %d lanes changed, %d bind-rule broken, +%d lane cycles" % (
            len(fc["lanes"]), len(fc["rule_broken"]), fc.get("lane_cycles_added", 0)))
    return 0 if not rep["conflicts"] and not errs and rep["reticle_fits"] else 1


if __name__ == "__main__":
    sys.exit(main())
