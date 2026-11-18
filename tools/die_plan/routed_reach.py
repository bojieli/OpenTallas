#!/usr/bin/env python3
"""ROUTED-REACH (KV-PV-RIDER 11-18, FABLE-PD-KV-2200 finding 1): register-hop reach measured ROUND the hard cores that
block signal routing, not on the straight Manhattan line.

Why: a plan station hop of 364 um Manhattan whose both L-paths cross a kv3_pv_pair core (LEF OBS on M1..M7, partition
signal ceiling M7) routes 692 um round it.  The G0 internal_station rule (check._hops_ok) and the stage composers
measured Manhattan only, so 29 KV D22 hops were > 405 um once routed.

Blocking core (die-agnostic): a hard_cores[] entry whose LEF OBS reaches the partition signal ceiling
(layer_budget.partition_signal_max, M7): any OBS RECT on a metal layer >= the ceiling.  A core whose OBS stops below it
(cland landing macros, pv join: OBS M1..M5) leaves M6/M7 over it, so it does not block a signal hop.  No readable LEF:
the declared hard_cores[].obs_max decides; neither -> not blocking, counted as `no_view` (the LEF-less core is reported,
never guessed solid: plans of every die keep G0 behaviour where views are not staged).
Box = origin_um + track_offset_um, outline_um swapped for 90-degree orients (the kit's macro placement).

Routed length: exact rectilinear shortest path among the blocking boxes (closed boxes are passable on their boundary,
interiors are not; zero-width slots between abutting boxes, or a box and the outline, are closed) inside the type outline, by Dijkstra on the
Hanan grid of the endpoints and box edges (a shortest rectilinear path among rectangles exists on that grid).  An
endpoint strictly inside a blocking box (a pin inside a core) escapes to the box boundary at its own cost.

G0: check.py calls check_plan(); every internal_stations hop (from_um -> regs_um[] -> to_um) of every non-hard type
with a routed length > reach (budgets.ft_station_max_um, <= 405) is a finding under check "routed_reach": a WARNING by
default (existing plans keep passing), an ERROR with `check.py --routed-reach error` or budgets.routed_reach "error";
"off" skips.  The summary always carries hops / detour_hops / max_routed_um / over.

Planner API (stage composers): blocking_boxes(t, ...), route(a, b, boxes, outline) -> (L, polyline),
points_on(polyline, fractions), hops(pts, boxes, outline).

CLI:  routed_reach.py check PLAN [--types RE] [--reach 405] [--json OUT] [--root REPO]   exit 1 = hops over the reach
"""
import argparse
import heapq
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCHEMA = "opentallas.routed_reach.v1"
REACH_UM = 405.0
EPS = 1e-6
ROT90 = ("R90", "R270", "MXR90", "MYR90")
_OBS_TOP = {}


def lnum(layer):
    m = re.fullmatch(r"M(\d+)", str(layer or ""))
    return int(m.group(1)) if m else 0


def obs_top(lef, root=None):
    """highest metal layer number with an OBS RECT in a one-macro LEF (0: no metal OBS); None if unreadable."""
    if not lef:
        return None
    p = Path(lef)
    if not p.is_absolute():
        p = Path(root or ROOT) / p
    key = str(p)
    if key not in _OBS_TOP:
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            _OBS_TOP[key] = None
            return None
        top = 0
        for o in re.finditer(r"(?ms)^[ \t]*OBS\b(.*?)^[ \t]*END[ \t]*$", txt):
            layer = 0
            for ln in o.group(1).splitlines():
                ml = re.match(r"\s*LAYER\s+(\S+)", ln)
                if ml:
                    layer = lnum(ml.group(1))
                elif layer and re.match(r"\s*(RECT|POLYGON)\b", ln):
                    top = max(top, layer)
        _OBS_TOP[key] = top
    return _OBS_TOP[key]


def core_box(h):
    dx, dy = h.get("track_offset_um") or [0.0, 0.0]
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ROT90:
        w, hh = hh, w
    x0, y0 = h["origin_um"][0] + dx, h["origin_um"][1] + dy
    return (float(x0), float(y0), float(x0 + w), float(y0 + hh))


def blocking_boxes(t, ceiling="M7", root=None):
    """(boxes [(x0, y0, x1, y1, inst)], info {inst: source}) of the type's hard cores that block signal routing."""
    top = lnum(ceiling)
    boxes, info = [], {}
    for h in t.get("hard_cores", []) or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        ot = obs_top(h.get("lef"), root)
        if ot is not None:
            src, blk = f"lef OBS M{ot}" if ot else "lef no OBS", ot >= top
        elif h.get("obs_max"):
            src, blk = f"obs_max {h['obs_max']}", lnum(h["obs_max"]) >= top
        else:
            src, blk = "no_view", False
        info[h["inst"]] = src
        if blk:
            boxes.append(core_box(h) + (h["inst"],))
    return boxes, info


def _strict_in(p, b):
    return b[0] + EPS < p[0] < b[2] - EPS and b[1] + EPS < p[1] < b[3] - EPS


def _closed_in(p, b):
    return b[0] - EPS <= p[0] <= b[2] + EPS and b[1] - EPS <= p[1] <= b[3] + EPS


def _seg_clear(p, q, boxes):
    """axis-parallel segment p-q does not enter a box interior"""
    if abs(p[1] - q[1]) < EPS:
        lo, hi, y = min(p[0], q[0]), max(p[0], q[0]), p[1]
        return not any(b[1] + EPS < y < b[3] - EPS and lo < b[2] - EPS and hi > b[0] + EPS for b in boxes)
    lo, hi, x = min(p[1], q[1]), max(p[1], q[1]), p[0]
    return not any(b[0] + EPS < x < b[2] - EPS and lo < b[3] - EPS and hi > b[1] + EPS for b in boxes)


def _on_edge(p, q, boxes):
    """axis-parallel segment p-q runs along a box edge (over a nonzero length)"""
    if abs(p[1] - q[1]) < EPS:
        lo, hi, y = min(p[0], q[0]), max(p[0], q[0]), p[1]
        return any((abs(y - b[1]) < EPS or abs(y - b[3]) < EPS) and lo < b[2] - EPS and hi > b[0] + EPS for b in boxes)
    lo, hi, x = min(p[1], q[1]), max(p[1], q[1]), p[0]
    return any((abs(x - b[0]) < EPS or abs(x - b[2]) < EPS) and lo < b[3] - EPS and hi > b[1] + EPS for b in boxes)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _escapes(p, boxes):
    """[(point, cost)]: p itself when free, else its projections onto the boundary of the box it sits in."""
    inside = [b for b in boxes if _strict_in(p, b)]
    if not inside:
        return [(tuple(p), 0.0)]
    b = inside[0]
    return [((b[0], p[1]), p[0] - b[0]), ((b[2], p[1]), b[2] - p[0]), ((p[0], b[1]), p[1] - b[1]),
            ((p[0], b[3]), b[3] - p[1])]


def route(a, b, boxes, outline=None):
    """(length um, polyline [a, ..., b]) of the shortest rectilinear path a -> b round the box interiors (inside the
    outline [W, H] when given).  (inf, None) when no path exists."""
    a, b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
    sa, sb = _escapes(a, boxes), _escapes(b, boxes)
    # boxes holding an endpoint stay obstacles; the endpoint enters through its escape points
    if not any(_strict_in(p, x) for p in (a, b) for x in boxes):
        # fast path: an L-path that neither enters a box nor runs along a box edge (a slot) is the route
        for m in ((b[0], a[1]), (a[0], b[1])):
            if all(_seg_clear(*s, boxes) and not _on_edge(*s, boxes) for s in ((a, m), (m, b))):
                return man(a, b), [a, m, b]
    xs = {p[0] for p, _ in sa + sb} | {v for x in boxes for v in (x[0], x[2])}
    ys = {p[1] for p, _ in sa + sb} | {v for x in boxes for v in (x[1], x[3])}
    if outline:
        W, H = outline
        xs = {min(max(v, 0.0), W) for v in xs} | {0.0, float(W)}
        ys = {min(max(v, 0.0), H) for v in ys} | {0.0, float(H)}
    xs, ys = sorted(xs), sorted(ys)
    xi, yi = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(ys)}

    def free(i, j):
        return not any(_strict_in((xs[i], ys[j]), x) for x in boxes)

    def edge_ok(p, q):
        if not _seg_clear(p, q, boxes):
            return False
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        d = (0.0, 1e-3) if abs(p[1] - q[1]) < EPS else (1e-3, 0.0)
        up, dn = (m[0] + d[0], m[1] + d[1]), (m[0] - d[0], m[1] - d[1])
        # a zero-width slot (between abutting boxes, or between a box and the outline) is closed
        return not (walled(up) and walled(dn))

    def walled(q):
        if outline and not (-EPS < q[0] < outline[0] + EPS and -EPS < q[1] < outline[1] + EPS):
            return True
        return any(_strict_in(q, x) for x in boxes)
    dist, prev, pq = {}, {}, []
    for p, c in sa:
        k = (xi[min(xs, key=lambda v: abs(v - p[0]))], yi[min(ys, key=lambda v: abs(v - p[1]))])
        if c < dist.get(k, float("inf")):
            dist[k] = c
            prev[k] = None
            heapq.heappush(pq, (c, k))
    goal = {}
    for p, c in sb:
        k = (xi[min(xs, key=lambda v: abs(v - p[0]))], yi[min(ys, key=lambda v: abs(v - p[1]))])
        goal[k] = min(goal.get(k, float("inf")), c)
    best, bk = float("inf"), None
    while pq:
        d, k = heapq.heappop(pq)
        if d > dist.get(k, float("inf")) + EPS or d >= best:
            continue
        if k in goal and d + goal[k] < best:
            best, bk = d + goal[k], k
        i, j = k
        for ni, nj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)) or not free(ni, nj):
                continue
            p, q = (xs[i], ys[j]), (xs[ni], ys[nj])
            if not edge_ok(p, q):
                continue
            nd = d + man(p, q)
            if nd < dist.get((ni, nj), float("inf")) - EPS:
                dist[(ni, nj)] = nd
                prev[(ni, nj)] = k
                heapq.heappush(pq, (nd, (ni, nj)))
    if bk is None:
        return float("inf"), None
    path, k = [], bk
    while k is not None:
        path.append((xs[k[0]], ys[k[1]]))
        k = prev[k]
    path = [a] + path[::-1] + [b]
    out = [path[0]]
    for p in path[1:]:                       # drop repeats and collinear interior points
        if man(p, out[-1]) < EPS:
            continue
        if len(out) >= 2 and ((abs(out[-2][0] - out[-1][0]) < EPS and abs(out[-1][0] - p[0]) < EPS) or
                              (abs(out[-2][1] - out[-1][1]) < EPS and abs(out[-1][1] - p[1]) < EPS)):
            out[-1] = p
            continue
        out.append(p)
    return best, out


def length(poly):
    return sum(man(p, q) for p, q in zip(poly, poly[1:]))


def points_on(poly, fracs):
    """points at arc fractions (0..1) along a polyline"""
    L = length(poly)
    out = []
    for f in fracs:
        d = f * L
        for p, q in zip(poly, poly[1:]):
            s = man(p, q)
            if d <= s + EPS and s > 0:
                r = d / s
                out.append((p[0] + (q[0] - p[0]) * r, p[1] + (q[1] - p[1]) * r))
                break
            d -= s
        else:
            out.append(tuple(poly[-1]))
    return out


def hops(pts, boxes, outline=None):
    """[(i, manhattan, routed)] of consecutive chain points"""
    out = []
    for i, (p, q) in enumerate(zip(pts, pts[1:])):
        m = man(p, q)
        L, _ = route(p, q, boxes, outline) if boxes else (m, None)
        out.append((i, m, L))
    return out


def type_hops(t, ceiling="M7", root=None):
    """[{conn, hop, from, to, man, routed}] of every internal_stations hop of a type"""
    boxes, info = blocking_boxes(t, ceiling, root)
    W, H = t["outline_um"]
    rows = []
    for e in t.get("internal_stations", []) or []:
        if "from_um" not in e or "to_um" not in e:
            continue
        pts = [tuple(e["from_um"])] + [tuple(r) for r in e.get("regs_um", [])] + [tuple(e["to_um"])]
        for i, m, L in hops(pts, boxes, (W, H)):
            rows.append(dict(conn=e.get("conn", ""), hop=i, a=list(pts[i]), b=list(pts[i + 1]), man=round(m, 3),
                             routed=round(L, 3) if L != float("inf") else -1.0, bits=e.get("bits")))
    return rows, boxes, info


def plan_report(raw, types=None, reach=None, root=None):
    ceil = ((raw.get("die") or {}).get("layer_budget") or {}).get("partition_signal_max") or \
        (raw.get("layer_budget") or {}).get("partition_signal_max") or "M7"
    reach = float(reach or min(float((raw.get("budgets") or {}).get("ft_station_max_um", REACH_UM)), REACH_UM))
    rx = re.compile(types) if types else None
    out = dict(schema=SCHEMA, ceiling=ceil, reach_um=reach, types={}, hops=0, detour_hops=0, max_routed_um=0.0,
               max_man_um=0.0, over=[], blocking_cores=0, no_view_cores=0)
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if t.get("hard") or (rx and not rx.search(tn)) or not t.get("internal_stations"):
            continue
        rows, boxes, info = type_hops(t, ceil, root)
        out["blocking_cores"] += len(boxes)
        out["no_view_cores"] += sum(1 for v in info.values() if v == "no_view")
        mr = max([r["routed"] for r in rows] or [0.0])
        out["types"][tn] = dict(hops=len(rows), blocking=len(boxes), detour=sum(1 for r in rows if r["routed"] > r["man"] + 1.0),
                                max_routed_um=mr, over=sum(1 for r in rows if r["routed"] > reach + EPS or r["routed"] < 0))
        out["hops"] += len(rows)
        out["detour_hops"] += out["types"][tn]["detour"]
        out["max_routed_um"] = max(out["max_routed_um"], mr)
        out["max_man_um"] = max([out["max_man_um"]] + [r["man"] for r in rows])
        out["over"] += [dict(type=tn, **r) for r in rows if r["routed"] > reach + EPS or r["routed"] < 0]
    return out


def check_plan(P, R, mode=None, root=None, max_msgs=60):
    """G0 entry: findings under check "routed_reach" (WARN default; mode / budgets.routed_reach "error" -> ERROR)."""
    mode = mode or P.budgets.get("routed_reach", "warn")
    if mode == "off":
        return dict(mode="off")
    raw = dict(P.raw)
    raw.setdefault("layer_budget", dict(partition_signal_max=P.layer_budget["partition_signal_max"]))
    rep = plan_report(raw, reach=None, root=root)
    for k, o in enumerate(sorted(rep["over"], key=lambda r: -r["routed"])):
        msg = (f"type {o['type']}: internal_stations {o['conn']} hop {o['hop']} {o['a']} -> {o['b']} routes "
               f"{o['routed']:.0f} um round the blocking cores (Manhattan {o['man']:.0f}) > {rep['reach_um']:g} um")
        if mode == "error":
            R.err("routed_reach", msg, type=o["type"])
        elif k < max_msgs:
            R.warn("routed_reach", msg, type=o["type"])
    return dict(mode=mode, hops=rep["hops"], detour_hops=rep["detour_hops"], max_routed_um=rep["max_routed_um"],
                max_man_um=rep["max_man_um"], over=len(rep["over"]), blocking_cores=rep["blocking_cores"],
                no_view_cores=rep["no_view_cores"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check")
    c.add_argument("plan")
    c.add_argument("--types")
    c.add_argument("--reach", type=float)
    c.add_argument("--json")
    c.add_argument("--root", help="repo root the LEF paths resolve against (default: this checkout)")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    rep = plan_report(raw, a.types, a.reach, a.root)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"ROUTED_REACH hops {rep['hops']} detour {rep['detour_hops']} max_routed {rep['max_routed_um']:.1f} "
          f"max_man {rep['max_man_um']:.1f} over {len(rep['over'])} (reach {rep['reach_um']:g}, ceiling {rep['ceiling']}, "
          f"blocking cores {rep['blocking_cores']}, no_view {rep['no_view_cores']})")
    for o in sorted(rep["over"], key=lambda r: -r["routed"])[:40]:
        print(f"  {o['type']} {o['conn']} hop {o['hop']} routed {o['routed']:.0f} man {o['man']:.0f} bits {o['bits']}")
    return 1 if rep["over"] else 0


if __name__ == "__main__":
    sys.exit(main())
