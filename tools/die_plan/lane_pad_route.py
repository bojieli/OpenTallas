#!/usr/bin/env python3
"""S81-COLGEN-1 11-14 (FABLE-TYPES-S81-COL C4): site the stages of a lane pad along the REAL route north of the wall.

Problem: `ot_dp_dly #(.W(1265), .D(5)) u_lpad_frame_int_i1` (plan internal_stations conn "bus:frame_int_i1") has its five
stages at y 0 under the bf_col3_c wall (x 691-899, y 52-250): the 52-um strip carries 5 x 1,265 bits, 2,509 gcells overflow
(44,569).  Editing coordinates by hand does not close it (DIE-S81-92: a last hop of ~1000 um appears), because the stages
must follow a wire that can really be routed: walls (bf modules, zero M6 capacity above the strip) forbid the straight
line, and a free gap narrower than `min_channel_um` is no channel.

What this does, per plan type and internal_stations entry (--bus NAME, or --all for every bus entry that needs it):
  1. walls = hard cores whose module matches --walls-re (default ot_v41_bf_col3|ot_v41_bf16_half), grown by
     min_channel_um / 2 on every side, and grown to the die edge on a side where the gap to the edge is < min_channel_um
     (so the 52-um strip under the wall belongs to the wall);
  2. route = shortest Manhattan polyline from_um -> to_um on the Hanan grid of those boxes (bend penalty; travel inside the
     grown part of the box holding an end point costs `strip_penalty` x, so the lane leaves the strip at the nearest gap);
  3. stage j of n sits at arclength L*(j+1)/(n+1), slid forward along the route off every core outline (+ halo) and out of
     the grown wall zones; n starts at the entry's stage count and grows until EVERY hop (from_um -> s0 -> .. -> to_um,
     Manhattan, the G0 rule check._hops_ok) is <= limit (default 400 <= 405 reach).
Each extra stage is +1 cycle on every lane through the pad (owner pre-approved latency cost, DIE-S81-92 owns the lane
latency row; kit_istations adds the stages to the bound module, bind_cells counts them).  Nothing here edits latency.
usage: lane_pad_route.py PLAN.json TYPE (--bus NAME ... | --all) [--limit 400] [--min-channel 100] [--walls-re RE]
         [--halo 1.0] [--strip-penalty 4] [--out DELTA.json] [--apply PLAN_OUT.json]
       lane_pad_route.py tapgroup PLAN.json OUT.json TYPE_RE [BUS,BUS]   (one tap group per u_lpad_<bus> pipeline)
  DELTA = {"type": T, "entries": [{conn, index, regs_um, route_um, stages_before, stages_after, max_hop_um, ...}]}
  --apply writes PLAN_OUT with those regs_um (and a note); an entry that still fails the hop rule is an error."""
import heapq
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LIMIT, MIN_CHANNEL, HALO, STRIP_PENALTY, BEND = 400.0, 100.0, 1.0, 4.0, 20.0
WALLS_RE = r"ot_v41_bf_col3|ot_v41_bf16_half"
EPS = 1e-6


class RouteError(ValueError):
    pass


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hops(a, regs, b):
    pts = [tuple(a)] + [tuple(r) for r in regs] + [tuple(b)]
    return [manhattan(p, q) for p, q in zip(pts, pts[1:])]


def core_boxes(t):
    """{inst: (x0, y0, x1, y1, module)} of the type's placed hard cores (track offset applied, like check.py)."""
    out = {}
    for hc in t.get("hard_cores", []):
        if "origin_um" not in hc or "outline_um" not in hc:
            continue
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
        out[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1], hc.get("module", ""))
    return out


def walls(t, walls_re=WALLS_RE, min_channel=MIN_CHANNEL):
    """[(raw box, grown box)] of the wall cores; grown = + min_channel/2, and to the die edge where the gap is thinner
    than min_channel."""
    w, h = t["outline_um"]
    m = min_channel / 2.0
    out = []
    for inst, (x0, y0, x1, y1, mod) in sorted(core_boxes(t).items()):
        if not re.search(walls_re, mod):
            continue
        g = [x0 - m, y0 - m, x1 + m, y1 + m]
        if x0 < min_channel:
            g[0] = 0.0
        if y0 < min_channel:
            g[1] = 0.0
        if w - x1 < min_channel:
            g[2] = w
        if h - y1 < min_channel:
            g[3] = h
        # a side grown to the die edge reaches 1 um past it, so the edge line itself is inside the zone (strip travel)
        out.append(((x0, y0, x1, y1), (g[0] if g[0] > 0.0 else -1.0, g[1] if g[1] > 0.0 else -1.0,
                                       g[2] if g[2] < w else w + 1.0, g[3] if g[3] < h else h + 1.0)))
    return out


def _inside(p, b, eps=EPS):
    return b[0] - eps <= p[0] <= b[2] + eps and b[1] - eps <= p[1] <= b[3] + eps


def _seg_overlap(a, c, b):
    """length of the axis-aligned segment a-c inside the OPEN interior of box b (0 when it only touches)."""
    if abs(a[0] - c[0]) < EPS:            # vertical
        if not (b[0] + EPS < a[0] < b[2] - EPS):
            return 0.0
        lo, hi = sorted((a[1], c[1]))
        return max(0.0, min(hi, b[3]) - max(lo, b[1]))
    if not (b[1] + EPS < a[1] < b[3] - EPS):
        return 0.0
    lo, hi = sorted((a[0], c[0]))
    return max(0.0, min(hi, b[2]) - max(lo, b[0]))


def route(t, a, b, walls_re=WALLS_RE, min_channel=MIN_CHANNEL, strip_penalty=STRIP_PENALTY):
    """shortest wall-avoiding Manhattan polyline a -> b (list of [x, y], collinear points dropped)."""
    a, b = tuple(a), tuple(b)
    W = walls(t, walls_re, min_channel)
    wd, ht = float(t["outline_um"][0]), float(t["outline_um"][1])

    def holds(p, g):
        """the end point p is in zone g, or sits on a die edge that g was grown to (the strip it enters through)"""
        return _inside(p, g) or (p[1] <= EPS and g[1] < 0) or (p[1] >= ht - EPS and g[3] > ht) or \
            (p[0] <= EPS and g[0] < 0) or (p[0] >= wd - EPS and g[2] > wd)

    free_raw = [(r, g) for r, g in W if not (holds(a, g) or holds(b, g))]                # plain blockers
    own = [(r, g) for r, g in W if holds(a, g) or holds(b, g)]                            # blockers an end enters through
    xs, ys = {a[0], b[0], 0.0, float(t["outline_um"][0])}, {a[1], b[1], 0.0, float(t["outline_um"][1])}
    for r, g in W:
        xs.update((g[0], g[2], r[0], r[2]))
        ys.update((g[1], g[3], r[1], r[3]))
    W_, H_ = float(t["outline_um"][0]), float(t["outline_um"][1])
    xs, ys = sorted(x for x in xs if 0.0 <= x <= W_), sorted(y for y in ys if 0.0 <= y <= H_)   # zones reach 1 um past the die edge
    xs = sorted(set(xs + [(p + q) / 2 for p, q in zip(xs, xs[1:])]))
    ys = sorted(set(ys + [(p + q) / 2 for p, q in zip(ys, ys[1:])]))
    ix = {round(x, 6): i for i, x in enumerate(xs)}
    iy = {round(y, 6): i for i, y in enumerate(ys)}

    def ext(r):
        """a core touching the die edge also blocks the edge line (travel along y = 0 under it is not free)"""
        return (r[0] if r[0] > EPS else -1.0, r[1] if r[1] > EPS else -1.0,
                r[2] if r[2] < wd - EPS else wd + 1.0, r[3] if r[3] < ht - EPS else ht + 1.0)

    def cost(p, q):
        if any(_seg_overlap(p, q, g) > EPS for _r, g in free_raw):
            return None
        d = manhattan(p, q)
        extra = 0.0
        for r, g in own:
            if _seg_overlap(p, q, ext(r)) > EPS:
                return None
            extra += _seg_overlap(p, q, g) * (strip_penalty - 1.0)
        return d + extra

    start = (ix[round(a[0], 6)], iy[round(a[1], 6)])
    goal = (ix[round(b[0], 6)], iy[round(b[1], 6)])
    best = {(start, None): 0.0}
    prev = {}
    pq = [(0.0, start, None)]
    while pq:
        c0, n, d0 = heapq.heappop(pq)
        if c0 > best.get((n, d0), math.inf):
            continue
        if n == goal:
            pts, key = [], (n, d0)
            while key is not None:
                pts.append(key[0])
                key = prev.get(key)
            pts = [[xs[i], ys[j]] for i, j in reversed(pts)]
            out = [pts[0]]
            for k in range(1, len(pts) - 1):
                p, q, r = pts[k - 1], pts[k], pts[k + 1]
                if not ((abs(p[0] - q[0]) < EPS and abs(q[0] - r[0]) < EPS) or (abs(p[1] - q[1]) < EPS and abs(q[1] - r[1]) < EPS)):
                    out.append(q)
            out.append(pts[-1])
            return out
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = (n[0] + dx, n[1] + dy)
            if not (0 <= m[0] < len(xs) and 0 <= m[1] < len(ys)):
                continue
            w = cost((xs[n[0]], ys[n[1]]), (xs[m[0]], ys[m[1]]))
            if w is None:
                continue
            nd = (dx, dy)
            c1 = c0 + w + (BEND if d0 not in (None, nd) else 0.0)
            if c1 < best.get((m, nd), math.inf):
                best[(m, nd)] = c1
                prev[(m, nd)] = (n, d0)
                heapq.heappush(pq, (c1, m, nd))
    raise RouteError(f"no wall-avoiding route {list(a)} -> {list(b)} (min_channel {min_channel} closes every gap)")


def _length(poly):
    return sum(manhattan(p, q) for p, q in zip(poly, poly[1:]))


def _point_at(poly, s):
    for p, q in zip(poly, poly[1:]):
        d = manhattan(p, q)
        if s <= d + EPS:
            f = 0.0 if d == 0 else s / d
            return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
        s -= d
    return tuple(poly[-1])


def sites(t, poly, a, b, n0, limit=LIMIT, halo=HALO, walls_re=WALLS_RE, min_channel=MIN_CHANNEL, step=2.0, nmax=40):
    """(regs_um, n): n >= n0 stages along poly with every hop <= limit, off all core outlines and out of the wall zones."""
    cores = [(x0 - halo, y0 - halo, x1 + halo, y1 + halo) for (x0, y0, x1, y1, _m) in core_boxes(t).values()]
    zones = [g for _r, g in walls(t, walls_re, min_channel)]
    bad = [z for z in cores] + zones
    # the entry / exit points themselves may sit in a zone (the face is in the strip); stages may not
    L = _length(poly)
    ok_at = {}

    def allowed(s):
        k = round(s, 3)
        if k not in ok_at:
            ok_at[k] = not any(_inside(_point_at(poly, s), z, eps=-EPS) for z in bad)
        return ok_at[k]

    def nearest(s, lo):
        """allowed arclength closest to s (either side), not below lo"""
        for k in range(int(L / step) + 2):
            for c in ((s + k * step, s - k * step) if k else (s,)):
                if lo <= c <= L and allowed(c):
                    return c
        return None

    for n in range(max(1, n0), nmax + 1):
        regs, lo, ok = [], 0.0, True
        for j in range(n):
            s = nearest(L * (j + 1) / (n + 1), lo)
            if s is None:
                ok = False
                break
            p = _point_at(poly, s)
            regs.append([round(p[0], 3), round(p[1], 3)])
            lo = s + step
        if ok and max(hops(a, regs, b)) <= limit + EPS:
            return regs, n
    raise RouteError(f"no site set within {nmax} stages keeps every hop <= {limit:g} um (route length {L:.0f})")


def plan_entry(t, entry, **kw):
    """sited entry (dict) for one internal_stations bus entry of type t"""
    limit = kw.get("limit", LIMIT)
    a, b = entry["from_um"], entry["to_um"]
    poly = route(t, a, b, kw.get("walls_re", WALLS_RE), kw.get("min_channel", MIN_CHANNEL), kw.get("strip_penalty", STRIP_PENALTY))
    regs, n = sites(t, poly, a, b, len(entry["regs_um"]), limit, kw.get("halo", HALO), kw.get("walls_re", WALLS_RE),
                    kw.get("min_channel", MIN_CHANNEL))
    h = hops(a, regs, b)
    return dict(conn=entry["conn"], regs_um=regs, route_um=[[round(x, 3), round(y, 3)] for x, y in poly],
                length_um=round(_length(poly), 1), stages_before=len(entry["regs_um"]), stages_after=n,
                cycles_added=n - len(entry["regs_um"]), max_hop_um=round(max(h), 1), hops_um=[round(x, 1) for x in h],
                max_hop_before_um=round(max(hops(a, entry["regs_um"], b)), 1),
                strip_regs_before=sum(1 for r in entry["regs_um"] if any(_inside(r, z) for z in
                                                                         [g for _r, g in walls(t, kw.get("walls_re", WALLS_RE),
                                                                                              kw.get("min_channel", MIN_CHANNEL))])))


REACH = 405.0          # G0 ft_station_max_um: a hop above it is an ERROR; --limit (400) is the margin the sites are built to


def needs_fix(t, entry, reach=REACH, walls_re=WALLS_RE, min_channel=MIN_CHANNEL):
    """True when a stage sits in a wall zone (the strip under the wall) or a hop exceeds the G0 reach"""
    zones = [g for _r, g in walls(t, walls_re, min_channel)]
    return any(_inside(r, z, eps=-EPS) for r in entry["regs_um"] for z in zones) or \
        max(hops(entry["from_um"], entry["regs_um"], entry["to_um"])) > reach + EPS


def run(plan, tn, buses=(), every=False, apply=False, **kw):
    t = plan["partition_types"][tn]
    rows, idx, errors = [], {}, []
    for i, e in enumerate(t.get("internal_stations", [])):
        c = e.get("conn", "")
        if not c.startswith("bus:"):
            continue
        name = c[4:]
        if name in buses or (every and needs_fix(t, e, REACH, kw.get("walls_re", WALLS_RE), kw.get("min_channel", MIN_CHANNEL))):
            try:
                r = plan_entry(t, e, **kw)
            except RouteError as exc:
                if name in buses:
                    raise
                errors.append(dict(type=tn, conn=c, error=str(exc)))       # --all: report, leave the entry as it is
                continue
            r["index"] = i
            rows.append(r)
            idx[i] = r
    missing = [b for b in buses if not any(r["conn"] == "bus:" + b for r in rows)]
    if missing and not kw.get("tolerate_missing"):
        raise RouteError(f"{tn}: no internal_stations entry for bus {missing}")
    if apply:
        for i, r in idx.items():
            e = t["internal_stations"][i]
            e["regs_um"] = r["regs_um"]
            e["note"] = (e.get("note", "") + f" | S81-COLGEN-1 C4 lane-pad route (north of the wall): {r['stages_after']} stages, "
                         f"max hop {r['max_hop_um']} um, +{r['cycles_added']} cycle(s)").strip(" |")
    return dict(type=tn, limit_um=kw.get("limit", LIMIT), entries=rows, errors=errors)


LPAD_TAP_RE = r"(?:^|[/.])(u_lpad_[A-Za-z0-9_]+)[/.]"


def lane_pad_tap_group(plan, type_re, buses=None):
    """S81-COLGEN-2 (FABLE-PD-S81-2250: col_h10_r1 -361 ps hold = the 5 ranks of u_lpad_frame_int_i1 on grid taps 262 vs 597 ps):
    set clock.tap_group.re on every matching type so that ALL ranks and bits of one lane-pad pipeline u_lpad_<bus> form one
    tap group (clock_taps.tcl group form: the group goes whole to ONE tap, the one nearest its sink centroid, pinned
    against the cap pass).  buses = None -> every u_lpad_* pipeline of the type, else only those bus names.
    A type that already declares a different clock.tap_group is not touched (reported in `conflict`).
    Returns {"set": [types], "unchanged": [types], "conflict": [types]}."""
    key = r"u_lpad_[A-Za-z0-9_]+" if not buses else "u_lpad_(?:" + "|".join(re.escape(b) for b in sorted(buses)) + ")"
    rx = r"(?:^|[/.])(" + key + r")[/.]"
    out = {"set": [], "unchanged": [], "conflict": [], "re": rx}
    for tn in sorted(plan["partition_types"]):
        if not re.search(type_re, tn):
            continue
        clock = plan["partition_types"][tn].setdefault("clock", {})
        cur = (clock.get("tap_group") or {}).get("re")
        if cur is None:
            clock["tap_group"] = {"re": rx}
            out["set"].append(tn)
        elif cur == rx:
            out["unchanged"].append(tn)
        else:
            out["conflict"].append(tn)
    return out


def run_many(plan, type_re, buses=(), every=False, apply=False, **kw):
    """run() over every partition type whose name matches type_re (a type without the bus entry is skipped)"""
    out = []
    for tn in sorted(plan["partition_types"]):
        if re.search(type_re, tn):
            r = run(plan, tn, buses, every, apply, tolerate_missing=True, **kw)
            if r["entries"] or r["errors"]:
                out.append(r)
    return dict(type_re=type_re, limit_um=kw.get("limit", LIMIT), types=out)


def main(argv):
    if len(argv) > 1 and argv[1] == "tapgroup":
        plan = json.loads(Path(argv[2]).read_text())
        res = lane_pad_tap_group(plan, argv[4], argv[5].split(",") if len(argv) > 5 else None)
        Path(argv[3]).write_text(json.dumps(plan, indent=1))
        print(f"lane_pad tap_group {res['re']}: set {len(res['set'])}, unchanged {len(res['unchanged'])}, conflict {res['conflict']}")
        return 0
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("type", help="partition type name, or a regex with --re")
    ap.add_argument("--re", action="store_true", help="TYPE is a regex over the partition type names")
    ap.add_argument("--bus", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=float, default=LIMIT)
    ap.add_argument("--min-channel", type=float, default=MIN_CHANNEL)
    ap.add_argument("--walls-re", default=WALLS_RE)
    ap.add_argument("--halo", type=float, default=HALO)
    ap.add_argument("--strip-penalty", type=float, default=STRIP_PENALTY)
    ap.add_argument("--out")
    ap.add_argument("--apply")
    a = ap.parse_args(argv[1:])
    if not a.bus and not a.all:
        ap.error("--bus NAME or --all")
    plan = json.loads(Path(a.plan).read_text())
    kw = dict(limit=a.limit, min_channel=a.min_channel, walls_re=a.walls_re, halo=a.halo, strip_penalty=a.strip_penalty)
    res = run_many(plan, a.type, a.bus, a.all, bool(a.apply), **kw) if a.re else run(plan, a.type, a.bus, a.all, bool(a.apply), **kw)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
    if a.apply:
        Path(a.apply).write_text(json.dumps(plan, indent=1))
    for r in (res["types"] if a.re else [res]):
        for er in r["errors"]:
            print(f"{er['type']} {er['conn']}: SKIPPED {er['error']}")
        _print(r)
    return 0


def _print(res):
    for r in res["entries"]:
        print(f"{res['type']} " + f"{r['conn']}: {r['stages_before']} -> {r['stages_after']} stages (+{r['cycles_added']} cycle), route {r['length_um']} um, "
              f"max hop {r['max_hop_before_um']} -> {r['max_hop_um']} um, strip stages before {r['strip_regs_before']}")


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except RouteError as exc:
        print(f"lane_pad_route: {exc}", file=sys.stderr)
        sys.exit(1)
