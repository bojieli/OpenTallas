#!/usr/bin/env python3
"""RIGID-REFLOOR (S81-T2-REFLOOR 11-23): move and re-size a set of partitions of a die plan as one rigid re-floor, and
re-pin only the seam ports whose two ends no longer agree.  Reusable for any die.

    python3 -I tools/die_plan/rigid_refloor.py price PLAN SPEC.json [--json OUT]
    python3 -I tools/die_plan/rigid_refloor.py apply PLAN SPEC.json OUT_PLAN [--report OUT.json]

SPEC (opentallas.rigid_refloor.v1):
    {"parts": {"<partition>": {"delta_um": [dx, dy]}            rigid move, outline kept
                              | {"rect_um": [x0, y0, x1, y1]}},  new placed bbox (re-shape when the size changes;
                                                                  the partition must be the only instance of its type)
     "die_outline_um": [W, H]            optional (die growth; the caller owns IO / PG / seal ring rows)
     "keep_internal": ["<partition>"]    optional: re-shaped partitions whose type-frame contents keep their DIE
                                         position (contents / cores / clock+reset records translated by the frame
                                         offset); default for every re-shaped partition.  "remap_internal": [...] instead
                                         scales them into the new outline (pass-through stations), and moves each
                                         clock landing band with the window of its bus / ft-slot end.
                                         Grid-mode clock taps of a re-shaped type are renamed to the new grid
                                         (nearest die position; grid+explicit added taps renumbered after it).
     "respace_limit": 405                optional (default 405; 0 = off): lane repair (fit_free_slots) on the slots of
                                         re-shaped / re-pinned types: stations re-spaced, added only where a hop
                                         exceeds it (+1 cycle each, latency.lanes re-derived and reported)
     "ride_internal": ["<partition>"]    optional: a part that moves AND grows; its internals ride with the SW corner
     "path_respace": false               optional: also run path_respace on the touched lanes afterwards
     "keep_frame": ["<partition>"]       optional: partitions whose pins must not change when a seam is re-sited
                                         (default order: re-shaped end re-pins first, then the cheaper type by hard
                                         cores + contents, then the end that moved)
     "pin_pitch_um": 1.2                 optional packing gap between re-sited windows on one face}

Model (schema.Plan): a port with window_um carries its die window; a port without one takes it from one end's type
bus / ft-slot window (_geom_from).  The pins of a type are the port windows seen in that type's frame, so:
  * both ends moved by the same vector along the seam -> the window moves with them, no type sees a change;
  * otherwise the window is re-sited: keep the end that did not move (or that is not re-shaped) in its own frame if
    the window still lies in the new face overlap, else slide it into the overlap (nearest), packing windows of one
    face in their old order so no two share a track.  Every end whose type-frame window changed is a RE-PIN of that
    type (reported per type and per face).
  * perpendicular gaps may open or close: a channel (die.channels[].between) whose two partitions moved gets its
    rect_um re-derived; a channel whose gap closed to 0 is removed (its ports become abutted); a NEW gap between two
    partitions that abutted is reported (CHANNEL-NEEDED) and given a channel row so G0 sees one channel width.
  * clock.landing_network edge relays (die frame) ride along with a rigidly moved pair, or are dropped for
    reach_relay_plan to re-place when the two ends moved apart; reset.die_relays sites inside a moved partition ride
    along with it.
  * ft slots whose in/out window changed get regs_um rebuilt on a straight / L route through the new windows (same
    station count) and their optional bit_sites_um dropped (re-sited by the kit flow), and are reported.
Checks: no two partitions overlap, every partition inside the die, every re-sited window inside both faces, every
seam port keeps a facing pair (else SEAM-LOST).  Plan arithmetic only: UNCHECKED until PRE / G0 / strict bind.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART, OPP  # noqa: E402

EPS = 1e-3
SCHEMA = "opentallas.rigid_refloor.v1"


def _rect(raw_types, p):
    w, h = raw_types[p["type"]]["outline_um"]
    x, y = p["origin_um"]
    return (x, y, x + w, y + h)


def _overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > EPS and min(a[3], b[3]) - max(a[1], b[1]) > EPS


def face_extent(rect, face):
    """(line, lo, hi) of a placed rect's die face."""
    x0, y0, x1, y1 = rect
    return {"N": (y1, x0, x1), "S": (y0, x0, x1), "E": (x1, y0, y1), "W": (x0, y0, y1)}[face]


def to_frame(part_rect, orient, face, win):
    """die window along `face` -> type-frame window (the 1-D transform of schema.geom_to_die, inverted)."""
    x0, y0, x1, y1 = part_rect
    a, b = sorted(win)
    if face in "EW":
        base, ext, flip = y0, y1 - y0, orient in ("MX", "R180")
    else:
        base, ext, flip = x0, x1 - x0, orient in ("MY", "R180")
    a, b = a - base, b - base
    if flip:
        a, b = ext - b, ext - a
    return [round(a, 6), round(b, 6)]


def from_frame(part_rect, orient, face, win):
    x0, y0, x1, y1 = part_rect
    a, b = sorted(win)
    if face in "EW":
        base, ext, flip = y0, y1 - y0, orient in ("MX", "R180")
    else:
        base, ext, flip = x0, x1 - x0, orient in ("MY", "R180")
    if flip:
        a, b = ext - b, ext - a
    return [round(base + a, 6), round(base + b, 6)]


def type_face(orient, die_face):
    if orient in ("MX", "R180") and die_face in "NS":
        return OPP[die_face]
    if orient in ("MY", "R180") and die_face in "EW":
        return OPP[die_face]
    return die_face


def load_spec(path):
    sp = json.loads(Path(path).read_text())
    if sp.get("schema", SCHEMA) != SCHEMA:
        raise ValueError(f"spec schema {sp.get('schema')} != {SCHEMA}")
    return sp


def new_layout(raw, spec):
    """{part: (old_rect, new_rect)} for every partition, after the spec; raises on unknown parts / shared types."""
    types = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    count = defaultdict(int)
    for p in raw["partitions"]:
        count[p["type"]] += 1
    out = {}
    for n, p in parts.items():
        r = _rect(types, p)
        out[n] = (r, r)
    for n, m in spec.get("parts", {}).items():
        if n not in parts:
            raise ValueError(f"spec part {n} is not a partition")
        r = out[n][0]
        if "delta_um" in m:
            dx, dy = m["delta_um"]
            nr = (r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy)
        elif "rect_um" in m:
            nr = tuple(float(v) for v in m["rect_um"])
            if (abs((nr[2] - nr[0]) - (r[2] - r[0])) > EPS or abs((nr[3] - nr[1]) - (r[3] - r[1])) > EPS) \
                    and count[parts[n]["type"]] > 1:
                raise ValueError(f"{n}: re-shape of type {parts[n]['type']} shared by {count[parts[n]['type']]} "
                                 f"partitions (split the type first)")
        else:
            raise ValueError(f"spec part {n}: needs delta_um or rect_um")
        out[n] = (r, tuple(round(v, 6) for v in nr))
    return out


def layout_findings(raw, lay, die_wh):
    errs = []
    W, H = die_wh
    names = sorted(lay)
    moved = {n for n in names if lay[n][0] != lay[n][1]}
    for n in moved:
        r = lay[n][1]
        if r[0] < -EPS or r[1] < -EPS or r[2] > W + EPS or r[3] > H + EPS:
            errs.append(f"OUTSIDE-DIE {n} {list(r)}")
    for a in moved:
        for b in names:
            if a != b and (b not in moved or a < b) and _overlap(lay[a][1], lay[b][1]):
                errs.append(f"OVERLAP {a} {list(lay[a][1])} x {b} {list(lay[b][1])}")
    # keep-outs: seal ring / corner channels without partitions (channels with no 'between')
    for c in raw["die"].get("channels", []):
        if c.get("between") or "rect_um" not in c:
            continue
        for n in moved:
            if _overlap(tuple(c["rect_um"]), lay[n][1]):
                errs.append(f"IN-KEEPOUT {n} x channel {c.get('name') or c.get('reason', '')[:40]}")
    return errs


def facing(ra, rb, face):
    """(gap, lo, hi) when rb lies across `face` of ra with an along-face overlap, else None."""
    la, a0, a1 = face_extent(ra, face)
    lb, b0, b1 = face_extent(rb, OPP[face])
    gap = (lb - la) if face in "NE" else (la - lb)
    lo, hi = max(a0, b0), min(a1, b1)
    if gap < -EPS or hi - lo <= EPS:
        return None
    return gap, lo, hi


def _type_win(t, bus):
    """(holder dict, key, face) of the declared type window for `bus` (bus or ft-slot end), or None."""
    for b in t.get("buses", []):
        if b["name"] == bus and "window_um" in b:
            return b, "window_um", b.get("face")
    for s_ in t.get("ft_slots", []):
        for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if bus == s_["name"] + sfx and wk in s_:
                return s_, wk, s_[fk]
    return None


def _qdelta(a, b, lo, hi, grid):
    """smallest shift that brings [a, b] inside [lo, hi], in whole multiples of the die grid when that still fits (a
    grid multiple keeps every layer's pin track: 8.64 um is a multiple of every M4-M7 pitch)."""
    if a < lo - EPS:
        d = lo - a
        q = math.ceil(d / grid - 1e-9) * grid if grid else d
        return q if b + q <= hi + EPS else d
    if b > hi + EPS:
        d = hi - b
        q = -math.ceil(-d / grid - 1e-9) * grid if grid else d
        return q if a + q >= lo - EPS else d
    return 0.0


def site_ports(raw, lay, pin_gap=1.2, keep_frame=(), slide=()):
    """per port: dict(id, face, old die window, new die window, ends=[(part, old frame win, new frame win)], status)."""
    P = S.Plan(raw)
    grid = float(raw["die"].get("grid_um", 0) or 0)
    types = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    moved = {n for n, (a, b) in lay.items() if a != b}
    reshaped = {n for n, (a, b) in lay.items() if abs((a[2] - a[0]) - (b[2] - b[0])) > EPS
                or abs((a[3] - a[1]) - (b[3] - b[1])) > EPS}
    rows = []

    def cost(n):
        t = types[parts[n]["type"]]
        return len(t.get("hard_cores") or []) + len(t.get("contents") or []) + (1000 if n in keep_frame else 0)

    for pid, pr in P.ports.items():
        ends = [pr[s]["part"] for s in ("src", "dst") if pr[s]["part"] != DIE_PART]
        if not any(e in moved for e in ends):
            continue
        f = pr.get("face")
        win = pr.get("window_um")
        if f is None or win is None:
            rows.append(dict(id=pid, status="NO-GEOM", ends=ends))
            continue
        row = dict(id=pid, face=f, old=list(sorted(win)), explicit="_geom_from" not in pr, ends=ends,
                   geom_from=pr.get("_geom_from"))
        if len(ends) == 1:      # die IO port on a moved partition: the die edge must still hold
            n = ends[0]
            ln, lo, hi = face_extent(lay[n][1], f if pr["src"]["part"] != DIE_PART else OPP[f])
            row.update(status="DIE-IO-MOVED", new=None)
            rows.append(row)
            continue
        s, d = pr["src"]["part"], pr["dst"]["part"]
        (rs0, rs1), (rd0, rd1) = lay[s], lay[d]
        fo = facing(rs1, rd1, f)
        if fo is None:
            row.update(status="SEAM-LOST", new=None)
            rows.append(row)
            continue
        gap, lo, hi = fo
        old_gap = facing(rs0, rd0, f)[0] if facing(rs0, rd0, f) else None
        row.update(gap_old=old_gap, gap_new=round(gap, 6), lo=lo, hi=hi)
        axis = 1 if f in "EW" else 0
        ds = rs1[axis] - rs0[axis]
        dd = rd1[axis] - rd0[axis]
        a, b = sorted(win)
        L = b - a
        if s not in reshaped and d not in reshaped and abs(ds - dd) <= EPS:
            row.update(status="RIGID", new=[round(a + ds, 6), round(b + ds, 6)])
            rows.append(row)
            continue
        cands = []
        # keep a non-reshaped end in its own frame (prefer the end that did not move, then the other)
        # keep the frame of the costlier type (hard cores + contents: a re-pin there is a heavy re-sign); tie -> the
        # end that did not move
        order = sorted([(s, ds), (d, dd)], key=lambda e: (e[0] in reshaped, -cost(e[0]), abs(e[1]) > EPS))
        for n, dv in order:
            if n in reshaped or pid in slide:       # a re-layered port re-pins both ends anyway: pack it
                continue
            cands.append(("KEEP-" + n, [a + dv, b + dv]))
        cands.append(("SLIDE", [a, b]))
        pick = None
        for tag, (ca, cb) in cands:
            if ca >= lo - EPS and cb <= hi + EPS:
                pick = (tag, [ca, cb])
                break
        if pick is None:
            if L > hi - lo + EPS:
                row.update(status="NO-ROOM", new=None)
                rows.append(row)
                continue
            pick = ("SLIDE", [a + _qdelta(a, b, lo, hi, grid), b + _qdelta(a, b, lo, hi, grid)])
        row.update(status=pick[0] if pick[0] != "SLIDE" else "SLIDE", new=[round(v, 6) for v in pick[1]],
                   axis=axis)
        rows.append(row)
    _pack(rows, P, pin_gap, grid)
    # frame windows per end, old and new
    for row in rows:
        if row.get("new") is None or len(row["ends"]) < 2:
            continue
        fr = []
        pr = P.ports[row["id"]]
        for side in ("src", "dst"):
            n = pr[side]["part"]
            df = row["face"] if side == "src" else OPP[row["face"]]
            o = parts[n].get("orient", "R0")
            ow = to_frame(lay[n][0], o, df, row["old"])
            nw = to_frame(lay[n][1], o, df, row["new"])
            fr.append(dict(part=n, side=side, bus=pr[side]["bus"], die_face=df, type_face=type_face(o, df),
                           old=ow, new=nw, changed=any(abs(x - y) > EPS for x, y in zip(ow, nw))))
        row["frames"] = fr
    return rows


def _pack(rows, P, gap, grid=0.0):
    """windows re-sited onto one (partition, die face) must not overlap each other or a window that stays."""
    by = defaultdict(list)
    for r in rows:
        if r.get("new") is None or len(r["ends"]) < 2:
            continue
        pr = P.ports[r["id"]]
        a, b = pr["src"]["part"], pr["dst"]["part"]
        f = r["face"] if a < b else OPP[r["face"]]
        by[(min(a, b), max(a, b), f)].append(r)
    for _key, lst in by.items():
        moving = [r for r in lst if r["status"] not in ("RIGID",) and not r["status"].startswith("KEEP-")]
        # windows that stay are obstacles; two KEEP windows kept in DIFFERENT frames (one end each) can land on each
        # other: RIGID first, then KEEP in old order, and a KEEP window that clashes with one already kept slides
        fixed = []
        for r in sorted((r for r in lst if r not in moving), key=lambda r: (r["status"] != "RIGID", r["old"][0])):
            a, b = r["new"]
            if r["status"] != "RIGID" and any(a < t[1] + gap - 0.1 and b > t[0] - gap + 0.1 for t in fixed):
                r["status"] = "SLIDE"
                moving.append(r)
            else:
                fixed.append((a, b))
        fixed.sort()
        if not moving:
            continue
        moving.sort(key=lambda r: (r["old"][0], r["new"][0]))     # keep the old order on the face
        lo = max(r["lo"] for r in moving)
        hi = min(r["hi"] for r in moving)
        q = (lambda d: math.ceil(d / grid - 1e-9) * grid) if grid else (lambda d: d)

        def place(start_shift):
            """first fit in old order from each window's own slid start (+ start_shift), stepping over the fixed
            windows and the windows placed before it; returns False when the run leaves [lo, hi]."""
            taken = list(fixed)
            for r in moving:
                L = r["new"][1] - r["new"][0]
                st = max(r["new"][0] + start_shift, lo)
                for _ in range(len(taken) + len(moving) + 2):
                    # 0.1 um slack: B1 packs windows 1.15-1.19 apart (track-snapped pin_gap); that spacing is legal
                    clash = [t for t in taken if st < t[1] + gap - 0.1 and st + L > t[0] - gap + 0.1]
                    if not clash:
                        break
                    st = st + q(max(t[1] for t in clash) + gap - st)
                r["_new"] = [round(st, 6), round(st + L, 6)]
                taken.append(tuple(r["_new"]))
            return all(r["_new"][0] >= lo - EPS and r["_new"][1] <= hi + EPS for r in moving)

        ok = place(0.0)
        if not ok:          # pushed past the top: retry the run from the bottom of the common range
            ok = place(lo - min(r["new"][0] for r in moving))
        if not ok and grid:     # grid steps waste up to one step per window: pack tight (pin gap only) from the bottom
            q = lambda d: d     # noqa: E731
            ok = place(lo - min(r["new"][0] for r in moving))
        for r in moving:
            if ok:
                r["new"] = r["_new"]
            else:
                r["status"] = "NO-ROOM"
            r.pop("_new", None)


def channel_rows(raw, lay):
    """re-derived channel rects for channels between moved partitions; closed gaps; new gaps."""
    out = dict(update=[], closed=[], new_gap=[])
    for i, c in enumerate(raw["die"].get("channels", [])):
        bt = c.get("between")
        if not bt or not any(lay.get(n, (0, 0))[0] != lay.get(n, (0, 0))[1] for n in bt):
            continue
        a, b = (lay[n][1] for n in bt)
        if a[2] <= b[0] + EPS or b[2] <= a[0] + EPS:
            l, r = (a, b) if a[2] <= b[0] + EPS else (b, a)
            rect = (l[2], max(l[1], r[1]), r[0], min(l[3], r[3]))
            width = r[0] - l[2]
        elif a[3] <= b[1] + EPS or b[3] <= a[1] + EPS:
            lo, hi = (a, b) if a[3] <= b[1] + EPS else (b, a)
            rect = (max(lo[0], hi[0]), lo[3], min(lo[2], hi[2]), hi[1])
            width = hi[1] - lo[3]
        else:
            out["closed"].append(dict(index=i, name=c.get("name"), why="overlap"))
            continue
        if width <= EPS:
            out["closed"].append(dict(index=i, name=c.get("name"), why="abutted"))
        elif rect[2] - rect[0] <= EPS or rect[3] - rect[1] <= EPS:
            out["closed"].append(dict(index=i, name=c.get("name"), why="no facing overlap"))
        else:
            out["update"].append(dict(index=i, name=c.get("name"), rect_um=[round(v, 6) for v in rect],
                                      width_um=round(width, 6)))
    return out


def reset_depths(raw, tns):
    """{type: built wavefront reset depth (reset_tree)} on the plan as given; {} entries 'error' when not buildable."""
    if not tns:
        return {}
    try:
        import reset_tree as RT
        P = S.Plan(raw)
    except Exception as e:
        return {tn: f"error {type(e).__name__}" for tn in tns}
    out = {}
    for tn in tns:
        try:
            out[tn] = int(RT._wf_type_tree(P, tn)["depth"])
        except Exception as e:
            out[tn] = f"error {type(e).__name__}"
    return out


def dodge_cores(t, pts, margin=1.08):
    """station points strictly inside a hard-core box of the type (plan_gate_pre.core_boxes, GEOM-STATION-IN-CORE)
    move to the nearest point just outside that box (kept inside the outline); a few passes for abutted cores."""
    try:
        import plan_gate_pre as PGP
        boxes = PGP.core_boxes(t)
    except Exception:
        return pts
    if not boxes:
        return pts
    w, h = t["outline_um"]

    def free(q):
        return 0.5 <= q[0] <= w - 0.5 and 0.5 <= q[1] <= h - 0.5 and \
            not any(x0 < q[0] < x1 and y0 < q[1] < y1 for _i, x0, y0, x1, y1 in boxes)
    out = []
    for x, y in pts:
        if any(x0 < x < x1 and y0 < y < y1 for _i, x0, y0, x1, y1 in boxes):
            xs = [e for _i, x0, _y0, x1, _y1 in boxes for e in (x0 - margin, x1 + margin)]
            ys = [e for _i, _x0, y0, _x1, y1 in boxes for e in (y0 - margin, y1 + margin)]
            cands = [q for q in [(e, y) for e in xs] + [(x, e) for e in ys] if free(q)]
            if not cands:       # no single-axis escape: nearest corner
                cands = [q for q in ((a, b) for a in xs for b in ys) if free(q)]
            if cands:
                x, y = min(cands, key=lambda q: abs(q[0] - x) + abs(q[1] - y))
        out.append([round(x, 4), round(y, 4)])
    return out


def _route_regs(slot, outline):
    """straight / L polyline from the in-window centre to the out-window centre, `stations` points incl. both ends."""
    w, h = outline

    def end(face, win):
        c = (win[0] + win[1]) / 2.0
        return {"N": (c, h), "S": (c, 0.0), "E": (w, c), "W": (0.0, c)}[face]

    p0 = end(slot["in_face"], slot["in_window_um"])
    p1 = end(slot["out_face"], slot["out_window_um"])
    if slot["in_face"] in "EW" and slot["out_face"] in "EW" or slot["in_face"] in "NS" and slot["out_face"] in "NS":
        if slot["in_face"] in "EW":
            xm = (p0[0] + p1[0]) / 2.0
            pts = [p0, (xm, p0[1]), (xm, p1[1]), p1]
        else:
            ym = (p0[1] + p1[1]) / 2.0
            pts = [p0, (p0[0], ym), (p1[0], ym), p1]
    else:
        knee = (p1[0], p0[1]) if slot["in_face"] in "EW" else (p0[0], p1[1])
        pts = [p0, knee, p1]
    segs = list(zip(pts, pts[1:]))
    total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segs)
    n = max(int(slot.get("stations", 1)), 1)
    out = []
    for k in range(n):
        t = total * k / n       # face register at the in window, then one station per 1/n of the route (the seam
        # leg to the next partition's in-face station is the n-th step), like the generated slots
        for a, b in segs:
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            if t <= L + 1e-9 or (a, b) == segs[-1]:
                f = 0.0 if L == 0 else min(t / L, 1.0)
                out.append([round(a[0] + (b[0] - a[0]) * f, 4), round(a[1] + (b[1] - a[1]) * f, 4)])
                break
            t -= L
    return out


_POINT_KEYS = ("xy", "xy_um", "pin_xy_um", "tap_um", "pin_um", "origin_um", "from_um", "to_um", "leaf_um")
_RECT_KEYS = ("rect_um", "origin_rect_um", "reseated_from_um", "resized_from_um")


def _shift_frame(o, dx, dy, depth=0):
    """translate type-frame points / rects (known key names) by (dx, dy); windows / outlines are not touched."""
    if depth > 12:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in _POINT_KEYS and isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                o[k] = [round(v[0] + dx, 6), round(v[1] + dy, 6)]
            elif k in _RECT_KEYS and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
                o[k] = [round(v[0] + dx, 6), round(v[1] + dy, 6), round(v[2] + dx, 6), round(v[3] + dy, 6)]
            elif k in ("regs_um", "sink_sites_um", "local_taps_um") and isinstance(v, list):
                o[k] = [[round(p[0] + dx, 6), round(p[1] + dy, 6)] + list(p[2:]) if isinstance(p, list) and len(p) >= 2
                        and all(isinstance(x, (int, float)) for x in p[:2]) else p for p in v]
            elif k == "bit_sites_um" and isinstance(v, list):
                o[k] = [[[round(q[0] + dx, 6), round(q[1] + dy, 6)] for q in st] for st in v]
            elif k == "sites_um" and isinstance(v, list):
                o[k] = [[round(p[0] + dx, 6), round(p[1] + dy, 6)] if isinstance(p, list) and len(p) == 2 else p
                        for p in v]
            else:
                _shift_frame(v, dx, dy, depth + 1)
    elif isinstance(o, list):
        for v in o:
            _shift_frame(v, dx, dy, depth + 1)


def _clamp_frame(o, w, h, depth=0):
    """clamp type-frame points / rects (known key names) into [0, w] x [0, h] (remapped pass-through types)."""
    cx = lambda v: round(min(max(v, 0.0), w), 6)  # noqa: E731
    cy = lambda v: round(min(max(v, 0.0), h), 6)  # noqa: E731
    if depth > 12:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in _POINT_KEYS and isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                o[k] = [cx(v[0]), cy(v[1])]
            elif k in _RECT_KEYS and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
                x0, y0, x1, y1 = v
                bw, bh = min(x1 - x0, w), min(y1 - y0, h)
                nx0, ny0 = min(max(x0, 0.0), w - bw), min(max(y0, 0.0), h - bh)
                o[k] = [round(nx0, 6), round(ny0, 6), round(nx0 + bw, 6), round(ny0 + bh, 6)]
            elif k in ("regs_um", "sink_sites_um", "local_taps_um", "sites_um") and isinstance(v, list):
                o[k] = [[cx(p[0]), cy(p[1])] + list(p[2:]) if isinstance(p, list) and len(p) >= 2
                        and all(isinstance(x, (int, float)) for x in p[:2]) else p for p in v]
            else:
                _clamp_frame(v, w, h, depth + 1)
    elif isinstance(o, list):
        for v in o:
            _clamp_frame(v, w, h, depth + 1)


def _scale_frame(o, sx, sy, w, h, depth=0):
    """remapped pass-through types: type-frame points scaled into the new outline (order and spacing kept); rects keep
    their size, their centre is scaled, and they are clamped inside."""
    if depth > 12:
        return
    pt = lambda v: [round(min(max(v[0] * sx, 0.0), w), 6), round(min(max(v[1] * sy, 0.0), h), 6)] + list(v[2:])  # noqa
    isnum = lambda v, n: isinstance(v, list) and len(v) >= n and all(isinstance(x, (int, float)) for x in v[:n])  # noqa
    if isinstance(o, dict):
        for k, v in o.items():
            if k in _POINT_KEYS and isnum(v, 2) and len(v) == 2:
                o[k] = pt(v)
            elif k in _RECT_KEYS and isnum(v, 4) and len(v) == 4:
                x0, y0, x1, y1 = v
                bw, bh = min(x1 - x0, w), min(y1 - y0, h)
                cx, cy = (x0 + x1) / 2 * sx, (y0 + y1) / 2 * sy
                nx0, ny0 = min(max(cx - bw / 2, 0.0), w - bw), min(max(cy - bh / 2, 0.0), h - bh)
                o[k] = [round(nx0, 6), round(ny0, 6), round(nx0 + bw, 6), round(ny0 + bh, 6)]
            elif k in ("regs_um", "sink_sites_um", "local_taps_um", "sites_um") and isinstance(v, list):
                o[k] = [pt(q) if isnum(q, 2) else q for q in v]
            else:
                _scale_frame(v, sx, sy, w, h, depth + 1)
    elif isinstance(o, list):
        for v in o:
            _scale_frame(v, sx, sy, w, h, depth + 1)


def _bands_follow_windows(t, old_t):
    """remapped types: a clock landing band named after a bus / ft-slot end keeps its place next to that end's window:
    moved along the face by the window shift, and with the face when the outline shrank on that side."""
    ow, oh = old_t["outline_um"]
    nw, nh = t["outline_um"]
    wins, owins = {}, {}
    for src, dst in ((old_t, owins), (t, wins)):
        for b in src.get("buses", []):
            if "window_um" in b and b.get("face"):
                dst[b["name"]] = (b["face"], b["window_um"])
        for s_ in src.get("ft_slots", []):
            for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
                if wk in s_:
                    dst[s_["name"] + sfx] = (s_[fk], s_[wk])
    ck, ock = t.get("clock") or {}, old_t.get("clock") or {}
    moved = []
    for path in (("band_fixed_um",), ("landing_contract", "bands")):
        cur, old = ck, ock
        for k in path:
            cur, old = (cur or {}).get(k), (old or {}).get(k)
        if not isinstance(cur, dict) or not isinstance(old, dict):
            continue
        for name, band in cur.items():
            ob = old.get(name)
            if name not in wins or name not in owins or not isinstance(ob, dict) or "rect_um" not in ob:
                continue
            f, nwin = wins[name]
            _, owin = owins[name]
            x0, y0, x1, y1 = ob["rect_um"]
            d = min(nwin) - min(owin)
            if f in "EW":
                y0, y1 = y0 + d, y1 + d
                if f == "E":
                    x0, x1 = x0 + (nw - ow), x1 + (nw - ow)
            else:
                x0, x1 = x0 + d, x1 + d
                if f == "N":
                    y0, y1 = y0 + (nh - oh), y1 + (nh - oh)
            band["rect_um"] = [round(x0, 6), round(y0, 6), round(x1, 6), round(y1, 6)]
            moved.append(name)
    return sorted(set(moved))


RESET_CLEAR_UM = 4.32       # reset_tree.CLEAR_UM


def legalize_taps(t, grid=8.64):
    """remapped types with an explicit clock tap table: every tap inside the outline minus the tap clearance and at
    least one clearance from the earlier taps (taps.explicit_tap_sites rule), nudged in grid steps; returns the moved
    tap names."""
    moved = []
    rs = t.get("reset") or {}
    if rs.get("local_taps_um"):     # reset_tree.consumer_taps: inside the outline minus CLEAR_UM (4.32)
        w, h = t["outline_um"]
        c = RESET_CLEAR_UM + 0.01       # margin: w - 4.32 in floats can fall a hair inside the bound
        for j, xy in enumerate(rs["local_taps_um"]):
            nx, ny = min(max(float(xy[0]), c), w - c), min(max(float(xy[1]), c), h - c)
            if [round(nx, 6), round(ny, 6)] != [round(float(xy[0]), 6), round(float(xy[1]), 6)]:
                rs["local_taps_um"][j] = [round(nx, 6), round(ny, 6)]
                moved.append(f"reset_local_{j}")
    ck = t.get("clock") or {}
    table = [p for p in ck.get("taps", []) if p.get("kind") != "core" and isinstance(p.get("xy"), list)]
    if not table:
        return moved
    clear = float(S.type_tap_clear(t))
    w, h = t["outline_um"]
    lo_x, hi_x, lo_y, hi_y = clear, w - clear, clear, h - clear
    taken = []
    for p in table:
        x0 = min(max(float(p["xy"][0]), lo_x), hi_x)
        y0 = min(max(float(p["xy"][1]), lo_y), hi_y)
        free = lambda x, y: not any(abs(x - a) < clear - 1e-8 and abs(y - b) < clear - 1e-8 for a, b in taken)  # noqa
        x, y = x0, y0
        if not free(x, y):
            for k in range(1, 400):
                cands = [(x0, y0 + k * grid), (x0, y0 - k * grid), (x0 + k * grid, y0), (x0 - k * grid, y0)]
                ok = [(a, b) for a, b in cands if lo_x <= a <= hi_x and lo_y <= b <= hi_y and free(a, b)]
                if ok:
                    x, y = ok[0]
                    break
        if [round(x, 6), round(y, 6)] != [round(float(v), 6) for v in p["xy"]]:
            moved.append(p["name"])
        p["xy"] = [round(x, 6), round(y, 6)]
        taken.append((x, y))
    return moved


def frame_offset(old_rect, new_rect, orient):
    """type-frame translation that keeps a die point fixed when a partition re-shapes from old_rect to new_rect."""
    (ox0, oy0, ox1, oy1), (nx0, ny0, nx1, ny1) = old_rect, new_rect
    dxd = (ox0 - nx0) if orient in ("R0", "MX") else (nx1 - ox1)
    dyd = (oy0 - ny0) if orient in ("R0", "MY") else (ny1 - oy1)
    return dxd, dyd


TAP_REF_RE = re.compile(r"\bclk_t\d+\b")


class _TapView:
    """the two attributes schema._grid_taps / tap_pitch read (types, budgets), without building a whole Plan."""

    def __init__(self, raw, types=None):
        self.types = types if types is not None else raw["partition_types"]
        self.budgets = dict(S.DEFAULT_BUDGETS, **raw.get("budgets", {})) if hasattr(S, "DEFAULT_BUDGETS") \
            else dict(raw.get("budgets", {}))


def _rename(o, fn, depth=0):
    if depth > 14:
        return o
    if isinstance(o, dict):
        return {fn(k) if isinstance(k, str) else k: _rename(v, fn, depth + 1) for k, v in o.items()}
    if isinstance(o, list):
        return [_rename(v, fn, depth + 1) for v in o]
    if isinstance(o, str):
        return fn(o)
    return o


def tap_renames(old_types, new_types, raw, tn, offset):
    """{old clock tap name: new name} of a re-shaped type: a grid tap goes to the new grid tap nearest its die position
    (frame offset applied), grid+explicit added taps are renumbered after the new grid (schema rule clk_t<len(grid)+i>)."""
    try:
        og = S._grid_taps(_TapView(raw, old_types), tn)
        ng = S._grid_taps(_TapView(raw, new_types), tn)
    except Exception:   # a tap mode that needs inputs not in the plan: leave the names alone (reported by PRE)
        return {}
    dx, dy = offset
    m = {}
    for name, x, y in og:
        best = min(ng, key=lambda t: abs(t[1] - (x + dx)) + abs(t[2] - (y + dy)))
        m[name] = best[0]
    ck = new_types[tn].get("clock", {})
    if ck.get("tap_mode") == "grid+explicit":
        for i, a in enumerate(ck.get("added_taps") or []):
            m[a["name"]] = f"clk_t{len(ng) + i}"
    # "clk" (tap 0) is also the clock port / bus name everywhere: it keeps its name
    out = {k: v for k, v in m.items() if k != v and k != "clk"}
    # a stored clock.taps list carries its own names (they are the keys the type is bound by): renaming it would give
    # two taps one name when old grid taps share a nearest new one, so a type with a stored list keeps its names; and a
    # map that is not one-to-one is never applied
    stored = [q.get("name") for q in (ck.get("taps") or []) if isinstance(q, dict)]
    if stored and ck.get("tap_mode") != "grid+explicit":
        return {}
    if len(set(m.values())) != len(m) or len({out.get(n, n) for n in stored}) != len(stored):
        return {}
    return out


def rewindow(raw, table):
    """spec "rewindow": {port id: window length um} -- a seam port between two type buses on a SHORTER window, same
    layers and same pin count (denser pins; the G0 face budget still judges the density).  The low die coordinate
    stays; the seam re-site then packs the shorter window.  Runs on the OLD layout, before any move."""
    if not table:
        return {}
    import schema as S_
    P = S_.Plan(raw)
    parts = {q["name"]: q for q in raw["partitions"]}
    per = float(P.budgets["face_pins_per_um"])
    out = {}
    for pid, length in sorted(table.items()):
        pr = next(q for q in raw["ports"] if q["id"] == pid)
        if not pr.get("window_um"):
            raise ValueError(f"rewindow {pid}: windowless port")
        w0, w1 = sorted(pr["window_um"])
        length = float(length)
        if not 0.0 < length < w1 - w0:
            raise ValueError(f"rewindow {pid}: {length} is not shorter than {w1 - w0:.3f}")
        if pr["width"] / length > per + 1e-6:
            raise ValueError(f"rewindow {pid}: {pr['width'] / length:.2f} pins/um > the die budget {per:g}")
        new = [round(w0, 6), round(w0 + length, 6)]
        for side, face in (("src", pr["face"]), ("dst", OPP[pr["face"]])):
            e = pr[side]
            t = raw["partition_types"][parts[e["part"]]["type"]]
            b = next((b for b in t.get("buses", []) if b["name"] == e["bus"]), None)
            if b is None:
                raise ValueError(f"rewindow {pid}: {e['part']}.{e['bus']} is not a type bus")
            fw = to_frame(P.rect(e["part"]), parts[e["part"]].get("orient", "R0"), face, new)
            b["window_um"] = [round(v, 6) for v in fw]
        pr["window_um"] = list(new)
        out[pid] = dict(old=[w0, w1], new=new, pins_per_um=round(pr["width"] / length, 3))
    return out


def relayer(raw, table):
    """spec "relayer": {port id: [layers]} -- a seam port re-pinned on more layers (owner-approved three-layer seam pins):
    the port and the bus of each end get the new layer list, and the window shrinks to len * n_old / n_new from its
    low die coordinate (same pin count, denser stack).  Both ends must be type buses (ft slots carry one layer list
    for both faces).  Runs on the OLD layout, before any move, so the seam re-site sees the shorter window."""
    if not table:
        return {}
    import schema as S_
    P = S_.Plan(raw)
    parts = {q["name"]: q for q in raw["partitions"]}
    out = {}
    for pid, layers in sorted(table.items()):
        pr = next(q for q in raw["ports"] if q["id"] == pid)
        if not pr.get("window_um"):
            raise ValueError(f"relayer {pid}: windowless port")
        n0, n1 = len(pr.get("layers") or []), len(layers)
        if not (n0 and n1 > n0):
            raise ValueError(f"relayer {pid}: {pr.get('layers')} -> {layers} is not a layer increase")
        if set(layers) & {"M1", "M2"}:      # M1 / M2 carry the partition follow-pin rails (gen_phys pdn), no signal pins
            raise ValueError(f"relayer {pid}: M1 / M2 are follow-pin layers, not pin layers")
        w0, w1 = sorted(pr["window_um"])
        new = [round(w0, 6), round(w0 + (w1 - w0) * n0 / n1, 6)]
        ends = []
        for side, face in (("src", pr["face"]), ("dst", OPP[pr["face"]])):
            e = pr[side]
            t = raw["partition_types"][parts[e["part"]]["type"]]
            b = next((b for b in t.get("buses", []) if b["name"] == e["bus"]), None)
            if b is None:
                raise ValueError(f"relayer {pid}: {e['part']}.{e['bus']} is not a type bus")
            fw = to_frame(P.rect(e["part"]), parts[e["part"]].get("orient", "R0"), face, new)
            b["layers"], b["window_um"] = list(layers), [round(v, 6) for v in fw]
            ends.append(f"{t and parts[e['part']]['type']}.{e['bus']}")
        pr["layers"], pr["window_um"] = list(layers), new
        out[pid] = dict(layers=list(layers), old=[w0, w1], new=new, ends=ends)
    return out


def apply(raw, spec, pin_gap=1.2):
    base_raw = raw
    raw = copy.deepcopy(raw)
    relayered = relayer(raw, spec.get("relayer") or {})
    rewin = rewindow(raw, spec.get("rewindow") or {})
    lay = new_layout(raw, spec)
    die_wh = tuple(spec.get("die_outline_um") or raw["die"]["outline_um"])
    rep = dict(schema=SCHEMA, layout_findings=layout_findings(raw, lay, die_wh), relayered=relayered, rewindowed=rewin)
    rows = site_ports(raw, lay, pin_gap, set(spec.get("keep_frame", [])), set(relayered) | set(rewin) | set(spec.get("slide", [])))
    types = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    reshaped = {n for n, (a, b) in lay.items() if abs((a[2] - a[0]) - (b[2] - b[0])) > EPS
                or abs((a[3] - a[1]) - (b[3] - b[1])) > EPS}
    remap = set(spec.get("remap_internal", []))
    old_types = {parts[n]["type"]: copy.deepcopy(types[parts[n]["type"]]) for n in reshaped}
    # remapped types keep their published reset release depth (reset.wavefront_min_depth pads, never shortens): the
    # landing START / local-reset anchors name relays by depth, and a shallower squeezed tree would orphan them
    old_depth = reset_depths(raw, [parts[n]["type"] for n in sorted(reshaped) if n in remap])
    # 1. re-shaped types: internal frame offset (keep die positions) BEFORE windows are written
    for n in sorted(reshaped):
        t = types[parts[n]["type"]]
        o = parts[n].get("orient", "R0")
        old_rect = lay[n][0]
        if n in set(spec.get("ride_internal", [])):     # the part moves and grows: internals ride with its SW corner
            mx, my = lay[n][1][0] - old_rect[0], lay[n][1][1] - old_rect[1]
            old_rect = (old_rect[0] + mx, old_rect[1] + my, old_rect[2] + mx, old_rect[3] + my)
        dx, dy = frame_offset(old_rect, lay[n][1], o)
        nw, nh = lay[n][1][2] - lay[n][1][0], lay[n][1][3] - lay[n][1][1]
        ow, oh = t["outline_um"]
        for k in ("contents", "hard_cores", "internal_stations", "relay_sites", "clock", "reset", "count_straps",
                  "ft_slots"):
            if k in t:
                if n in remap and k != "ft_slots":
                    _scale_frame(t[k], nw / ow, nh / oh, nw, nh)
                else:
                    _shift_frame(t[k], dx, dy)
        # bus / ft windows: shift along their own face axis
        for b in t.get("buses", []):
            if "window_um" in b and b.get("face"):
                d = dy if b["face"] in "EW" else dx
                b["window_um"] = [round(b["window_um"][0] + d, 6), round(b["window_um"][1] + d, 6)]
        for s_ in t.get("ft_slots", []):
            for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
                if wk in s_:
                    d = dy if s_[fk] in "EW" else dx
                    s_[wk] = [round(s_[wk][0] + d, 6), round(s_[wk][1] + d, 6)]
        t["outline_um"] = [round(nw, 6), round(nh, 6)]
        ins = (raw.get("reset", {}).get("in_sites") or {}).get(parts[n]["type"])
        if isinstance(ins, list) and len(ins) == 2:
            raw["reset"]["in_sites"][parts[n]["type"]] = [round(min(max(ins[0] + dx, 0.0), nw), 6),
                                                         round(min(max(ins[1] + dy, 0.0), nh), 6)]
        tn = parts[n]["type"]
        ren = {} if (t.get("clock") or {}).get("tap_mode", "grid") not in ("grid", "grid+sinks", "grid+explicit") \
            else tap_renames({**types, tn: old_types[tn]}, types, raw, tn, (dx, dy))
        if ren:
            fn = lambda x, ren=ren: TAP_REF_RE.sub(lambda mm: ren.get(mm.group(0), mm.group(0)), x)  # noqa: E731
            types[tn] = t = _rename(t, fn)
            ppp = ((raw.get("clock") or {}).get("tap_window") or {}).get("per_port_ps") or {}
            if isinstance(ppp.get(tn), dict):
                merged = {}
                for k, v in ppp[tn].items():
                    k2 = fn(k)
                    merged[k2] = max(merged.get(k2, v), v)
                ppp[tn] = merged
        rep.setdefault("reshaped", []).append(dict(part=n, type=tn, frame_offset_um=[dx, dy],
                                                   outline_um=[nw, nh], remap=n in remap, tap_renames=ren))
    # 2. partitions
    for n, (a, b) in lay.items():
        if a != b:
            parts[n]["origin_um"] = [b[0], b[1]]
    if spec.get("die_outline_um"):
        raw["die"]["outline_um"] = list(spec["die_outline_um"])
    # 3. ports + type windows
    port_by = {p["id"]: p for p in raw["ports"]}
    repin = defaultdict(lambda: defaultdict(list))
    slot_changed = defaultdict(set)
    for r in rows:
        if r.get("new") is None or r["status"] in ("RIGID", "NO-GEOM", "DIE-IO-MOVED", "NO-ROOM"):
            if r.get("status") == "RIGID" and "window_um" in port_by[r["id"]]:
                port_by[r["id"]]["window_um"] = r["new"]
            continue
        if "window_um" in port_by[r["id"]]:
            port_by[r["id"]]["window_um"] = r["new"]
        for fr in r.get("frames", []):
            t = types[parts[fr["part"]]["type"]]
            tw = _type_win(t, fr["bus"])
            if tw is not None:
                holder, key, tf = tw
                cur = holder[key]
                if any(abs(x - y) > EPS for x, y in zip(sorted(cur), fr["new"])):
                    holder[key] = fr["new"]
                    if "in_face" in holder:
                        slot_changed[parts[fr["part"]]["type"]].add(holder["name"])
            if fr["changed"]:
                repin[parts[fr["part"]]["type"]][fr["type_face"]].append(r["id"])
    # windowless ports whose geom end is a re-shaped / moved type are already carried by the type window above.
    # a re-shaped type's window that no port re-sited and that left its face is clamped back onto it (reported)
    clamped = []
    for n in sorted(reshaped):
        t = types[parts[n]["type"]]
        w, h = t["outline_um"]
        holders = [(b, "window_um", b.get("face")) for b in t.get("buses", []) if "window_um" in b and b.get("face")]
        holders += [(s_, wk, s_[fk]) for s_ in t.get("ft_slots", []) for fk, wk in (("in_face", "in_window_um"),
                                                                                    ("out_face", "out_window_um"))
                    if wk in s_]
        for hd, wk, f in holders:
            a, b = sorted(hd[wk])
            ext = h if f in "EW" else w
            if a < -EPS or b > ext + EPS:
                L = min(b - a, ext)
                na = min(max(a, 0.0), ext - L)
                hd[wk] = [round(na, 6), round(na + L, 6)]
                clamped.append(f"{parts[n]['type']}.{hd.get('name')}.{wk}")
                if "in_face" in hd:
                    slot_changed[parts[n]["type"]].add(hd["name"])
    rep["windows_clamped"] = clamped
    rep["reset_min_depth"] = {}
    for tn, d in old_depth.items():
        if isinstance(d, int):
            rs = types[tn].setdefault("reset", {})
            if int(rs.get("wavefront_min_depth") or 0) < d:
                rs["wavefront_min_depth"] = d
                rep["reset_min_depth"][tn] = d
    rep["taps_legalized"] = {parts[n]["type"]: legalize_taps(types[parts[n]["type"]],
                                                             float(raw["die"].get("grid_um", 8.64) or 8.64))
                             for n in sorted(reshaped)}
    rep["added_taps_cleared"] = {}
    for n in sorted(reshaped):          # grid re-centres / outline change: added taps the bind would refuse -> nearest legal
        tn = parts[n]["type"]
        if (types[tn].get("clock") or {}).get("added_taps"):
            try:
                import s81_hi_corridor as HC
                mv = HC.clear_added_taps(types[tn], budgets=raw.get("budgets"))
            except ImportError:
                mv = []
            if mv:
                rep["added_taps_cleared"][tn] = mv
    rep["bands_moved"] = {parts[n]["type"]: _bands_follow_windows(types[parts[n]["type"]], old_types[parts[n]["type"]])
                          for n in sorted(reshaped) if n in remap}
    # 4. ft slots with a changed window: re-shaped types rebuild regs (off hard cores); re-pinned-only types keep their
    #    station sites (they were legal and core-free; a lane the slide breaks is refit by fit_free_slots); exact bit
    #    sites are dropped either way
    reshaped_types = {parts[n]["type"] for n in reshaped}
    for n in sorted(reshaped):
        t = types[parts[n]["type"]]
        for s_ in t.get("ft_slots", []):
            slot_changed[parts[n]["type"]].add(s_["name"])
    for tn, names in slot_changed.items():
        t = types[tn]
        for s_ in t.get("ft_slots", []):
            if s_["name"] in names and "in_window_um" in s_ and "out_window_um" in s_:
                if "regs_um" in s_ and tn in reshaped_types:
                    s_["regs_um"] = dodge_cores(t, _route_regs(s_, t["outline_um"]))
                s_.pop("bit_sites_um", None)
                s_.pop("bit_site_cell_um", None)
    # 5. channels
    ch = channel_rows(raw, lay)
    chans = raw["die"].get("channels", [])
    for u in ch["update"]:
        chans[u["index"]]["rect_um"] = u["rect_um"]
        chans[u["index"]]["width_um"] = u["width_um"]
    for c in sorted(ch["closed"], key=lambda c: -c["index"]):
        chans.pop(c["index"])
    # new gaps between formerly abutted port ends -> one channel row per partition pair
    pairs = defaultdict(list)
    for r in rows:
        if r.get("gap_new") is not None and (r.get("gap_old") or 0) <= EPS < r["gap_new"]:
            pr = port_by[r["id"]]
            pairs[tuple(sorted((pr["src"]["part"], pr["dst"]["part"])))].append(r["id"])
    have = {tuple(sorted(c["between"])) for c in chans if c.get("between")}
    for (a, b), pids in sorted(pairs.items()):
        if (a, b) in have:
            continue
        ra, rb = lay[a][1], lay[b][1]
        if ra[2] <= rb[0] + EPS or rb[2] <= ra[0] + EPS:
            l, rr = (ra, rb) if ra[2] <= rb[0] + EPS else (rb, ra)
            rect, width = (l[2], max(l[1], rr[1]), rr[0], min(l[3], rr[3])), rr[0] - l[2]
        else:
            lo, hi = (ra, rb) if ra[3] <= rb[1] + EPS else (rb, ra)
            rect, width = (max(lo[0], hi[0]), lo[3], min(lo[2], hi[2]), hi[1]), hi[1] - lo[3]
        lays = sorted({ln for pid in pids for ln in (port_by[pid].get("layers") or ["M7", "M5"])})
        chans.append(dict(between=[a, b], layers=lays, name=f"rigid_refloor_{a}__{b}", ports=sorted(pids),
                          reason="rigid_refloor.py: gap opened by a rigid re-floor; seam nets cross on die route",
                          rect_um=[round(v, 6) for v in rect], width_um=round(width, 6)))
        ch["new_gap"].append(dict(between=[a, b], ports=len(pids), width_um=round(width, 6)))
    rep["channels"] = ch
    # 5b. a channel whose ports lost their gap is closed above; ports listed in a removed channel are now abutted
    # 6. reset die relays that sit inside a moved partition ride along
    moved = {n: (b[0] - a[0], b[1] - a[1]) for n, (a, b) in lay.items() if a != b and n not in reshaped}
    dr_moved = []
    for k, v in (raw.get("reset", {}).get("die_relays") or {}).items():
        sites = v.get("sites_um") or []
        new = []
        for (x, y) in sites:
            hit = next((n for n, (dx, dy) in moved.items()
                        if lay[n][0][0] - EPS <= x <= lay[n][0][2] + EPS and lay[n][0][1] - EPS <= y <= lay[n][0][3] + EPS),
                       None)
            if hit:
                dx, dy = moved[hit]
                new.append([round(x + dx, 6), round(y + dy, 6)])
                dr_moved.append(dict(relay=k, inside=hit))
            else:
                new.append([x, y])
        if sites:
            v["sites_um"] = new
    rep["die_relays_moved"] = dr_moved
    # 7. clock landing-network edges: die-frame relays ride along when both ends moved by one vector; when the ends
    #    moved apart the relays are dropped so reach_relay_plan re-places them on a clean provider (reported)
    allmv = {n: (b[0] - a[0], b[1] - a[1]) for n, (a, b) in lay.items() if a != b}
    ln_rows = dict(translated=[], dropped=[])
    for e in ((raw.get("clock") or {}).get("landing_network") or {}).get("edges", []):
        if "relays" not in e:
            continue
        vs = {allmv.get(e["src"].get("part"), (0.0, 0.0)), allmv.get(e["dst"].get("part"), (0.0, 0.0))}
        if vs == {(0.0, 0.0)}:
            continue
        if len(vs) == 1:
            dx, dy = vs.pop()
            for r in e["relays"]:
                if isinstance(r.get("xy_um"), list):
                    r["xy_um"] = [round(r["xy_um"][0] + dx, 6), round(r["xy_um"][1] + dy, 6)]
            ln_rows["translated"].append(e["id"])
        else:
            e.pop("relays")
            ln_rows["dropped"].append(e["id"])
    rep["landing_relays"] = ln_rows
    rep["ports"] = summarize(rows)
    rep["repin_types"] = {tn: {f: sorted(set(v)) for f, v in fs.items()} for tn, fs in sorted(repin.items())}
    rep["ft_slots_rebuilt"] = {tn: sorted(v) for tn, v in sorted(slot_changed.items())}
    rep["port_rows"] = rows
    rep["die_relays_stale"] = drop_stale_die_relays(raw)
    lim = spec.get("respace_limit", 405.0)
    if lim:
        free = set(reshaped) | {n for n in parts if parts[n]["type"] in slot_changed}
        if free:
            P0, ch, unfix = fit_free_slots(raw, free, float(lim))
            rep["free_slots_fit"] = dict(stations=ch, lane_cycles=relatency(raw, P0) if ch else {},
                                         unfixable_leads=unfix)
        over = new_hop_overs(base_raw, raw, float(lim))
        rep["hops_after_fit"] = over
        if spec.get("path_respace") or over:
            rep["respace"] = respace(raw, rows, slot_changed, float(lim), bool(spec.get("respace_add", True)),
                                     only=None if spec.get("path_respace") else set(over))
        # proof on the FINAL plan (after every station edit): a lane newly over the limit is blocking
        rep["hops_over_new"] = new_hop_overs(base_raw, raw, float(lim))
        rep["stations_over_new"] = new_station_overs(base_raw, raw, float(lim))
    lp = landing_pins(base_raw, raw, float(spec.get("respace_limit", 405.0) or 405.0))
    rep["landing_pins"] = lp
    # an edge that follows no port (cland_mon_* monitor bundles to the collector) is re-relayed by the tail
    # (reach_relay_plan) and judged by G0 there: advisory here; a port-following edge still over the limit blocks
    lim_l = float(spec.get("respace_limit", 405.0) or 405.0)
    rep["landing_over"] = {k: v for k, v in lp.items() if (v[1] is None or v[1] > lim_l + 1e-6)
                           and not str(v[2]).startswith("no port")}
    rep["landing_relay_tail"] = sorted(k for k, v in lp.items() if str(v[2]).startswith("no port"))
    rep["content_outside"] = content_outside(raw, base_raw, sorted({parts[n]["type"] for n in reshaped}))
    rep["station_in_core_new"] = stations_in_core(raw, base_raw)
    return raw, rep


def lane_max_hops(raw):
    import check as C
    P = S.Plan(copy.deepcopy(raw))
    out = {}
    for lid in P.lanes:
        try:
            h = C.lane_pin_hops(P, lid, C.lane_geometry(P, lid)[1])
        except Exception as e:
            out[lid] = f"{type(e).__name__}"
            continue
        out[lid] = max(h) if h else 0.0
    return out


def new_hop_overs(base, raw, limit):
    """{lane: [base max hop, new max hop]}: lanes over `limit` now that were not (or are worse), and lanes that newly
    fail to evaluate; same model as G0 hops (check.lane_pin_hops), whole die."""
    a, b = lane_max_hops(base), lane_max_hops(raw)
    out = {}
    for lid, v in b.items():
        u = a.get(lid)
        if isinstance(v, str):
            if not isinstance(u, str):
                out[lid] = [u, v]
        elif v > limit + 1e-6 and (isinstance(u, str) or u is None or u <= limit + 1e-6 or v > u + 0.5):
            out[lid] = [u if isinstance(u, (str, type(None))) else round(u, 1), round(v, 1)]
    return out


def landing_pins(base, raw, limit):
    """clock.landing_network edges (landing_contract scalar pins, one per end) whose end-to-end hop the re-floor
    broke: an edge named cland_<x>__<port id> follows its port -- each end pin keeps its distance from its own face
    (on the new face line of its part) and moves along the face by the port's window shift.  Only types used once
    are re-pinned (a shared type's pin moves in every copy).  Returns rows {edge: [old hop, new hop, how]}."""
    net = (raw.get("clock") or {}).get("landing_network") or {}
    edges = net.get("edges") or []
    if not edges:
        return {}
    Pb, Pn = S.Plan(copy.deepcopy(base)), S.Plan(copy.deepcopy(raw))
    uses = defaultdict(int)
    for q in raw["partitions"]:
        uses[q["type"]] += 1
    eb = {e["id"]: e for e in ((base.get("clock") or {}).get("landing_network") or {}).get("edges") or []}

    def pin(P, types, part, name):
        t = types[P.parts[part]["type"]]
        return next((q for q in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []
                     if q.get("name") == name), None)

    def hop(P, types, e):
        a = [P.to_die(e[s_]["part"], pin(P, types, e[s_]["part"], e[s_]["bus"])["xy_um"]) for s_ in ("src", "dst")]
        pts = [a[0]] + [tuple(r_["xy_um"]) for r_ in e.get("relays") or []] + [a[1]]
        return max(abs(u[0] - v[0]) + abs(u[1] - v[1]) for u, v in zip(pts, pts[1:]))

    def faceline(rect, f):
        return {"E": rect[2], "W": rect[0], "N": rect[3], "S": rect[1]}[f]
    out = {}
    for e in edges:
        try:
            h1 = hop(Pn, raw["partition_types"], e)
            h0 = hop(Pb, base["partition_types"], eb[e["id"]]) if e["id"] in eb else None
        except Exception as x:
            out[e["id"]] = [None, None, f"unmeasured {type(x).__name__}"]
            continue
        if h1 <= limit + 1e-6 and (h0 is None or h1 <= h0 + 0.5):
            continue
        pid = e["id"].split("__", 1)[1] if "__" in e["id"] else None
        if e.get("relays") or pid not in Pn.ports or pid not in Pb.ports:
            out[e["id"]] = [h0 and round(h0, 1), round(h1, 1), "no port to follow" if not e.get("relays") else "relays"]
            continue
        f = Pn.ports[pid].get("face")
        try:
            c0, c1 = Pb.port_point(pid), Pn.port_point(pid)
        except Exception as x:
            out[e["id"]] = [h0 and round(h0, 1), round(h1, 1), f"port geometry {type(x).__name__}"]
            continue
        ax = 1 if f in "EW" else 0
        moves, why = [], None
        for side in ("src", "dst"):
            part = e[side]["part"]
            pf = f if Pn.ports[pid]["src"]["part"] == part else OPP[f]
            tn = Pn.parts[part]["type"]
            q = pin(Pn, raw["partition_types"], part, e[side]["bus"])
            q0 = Pb.to_die(part, pin(Pb, base["partition_types"], part, e[side]["bus"])["xy_um"])
            new = list(q0)
            new[ax] = q0[ax] + (c1[ax] - c0[ax])
            new[1 - ax] = faceline(Pn.rect(part), pf) + (q0[1 - ax] - faceline(Pb.rect(part), pf))
            xy = Pn.to_type(part, new)
            w, h = raw["partition_types"][tn]["outline_um"]
            xy = [round(min(max(xy[0], 0.0), w), 6), round(min(max(xy[1], 0.0), h), 6)]
            if any(abs(a - b) > 1e-6 for a, b in zip(xy, q["xy_um"])):
                if uses[tn] > 1:
                    why = f"shared type {tn}"
                    break
                moves.append((q, xy))
        if why:
            out[e["id"]] = [h0 and round(h0, 1), round(h1, 1), why]
            continue
        for q, xy in moves:
            q["xy_um"] = xy
        Pn = S.Plan(copy.deepcopy(raw)) if moves else Pn
        out[e["id"]] = [h0 and round(h0, 1), round(hop(Pn, raw["partition_types"], e), 1), f"followed {pid}"]
    return out


def station_overs(raw, limit):
    """{type.slot: route / stations} over `limit` (G0 R3 stations rule, non full-stage slots), whole die."""
    import check as C
    P = S.Plan(copy.deepcopy(raw))
    out = {}
    for lid in P.lanes:
        try:
            xs = C.lane_geometry(P, lid)[2]
        except Exception:
            continue
        for x in xs:
            tn = P.parts[x["part"]]["type"]
            if P.types[tn].get("ft_full_stage_placement_file"):
                continue
            sp = float(x.get("len_um") or 0.0) / max(1, int(x["stations"]))
            if sp > limit + 1e-6:
                out[f"{tn}.{x['slot']}"] = round(sp, 1)
    return out


def new_station_overs(base, raw, limit):
    a = station_overs(base, limit)
    return {k: v for k, v in station_overs(raw, limit).items() if k not in a}


def content_outside(raw, base, tns):
    """hard cores / clock + reset taps of re-shaped types that lie outside the type outline (and did not before)."""
    def bad(t):
        w, h = t["outline_um"]
        out = set()
        for c in t.get("hard_cores") or []:
            try:
                (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
            except (KeyError, TypeError, ValueError):
                continue
            if x < -1e-3 or y < -1e-3 or x + cw > w + 1e-3 or y + ch > h + 1e-3:
                out.add(f"core {c.get('inst')}")
        ck = t.get("clock") or {}
        pts = [(p.get("name"), p.get("xy")) for k in ("taps", "added_taps") for p in (ck.get(k) or []) if isinstance(p, dict)]
        pts += [(f"reset_local_{j}", xy) for j, xy in enumerate((t.get("reset") or {}).get("local_taps_um") or [])]
        for s_ in t.get("ft_slots") or []:
            pts += [(f"{s_['name']}.regs[{j}]", q) for j, q in enumerate(s_.get("regs_um") or [])]
        for name, q in pts:
            if isinstance(q, (list, tuple)) and len(q) >= 2 and not (-1e-3 <= q[0] <= w + 1e-3 and -1e-3 <= q[1] <= h + 1e-3):
                out.add(f"site {name}")
        return out
    res = {}
    for tn in tns:
        d = bad(raw["partition_types"][tn]) - bad(base["partition_types"][tn])
        if d:
            res[tn] = sorted(d)[:40]
    return res


def stations_in_core(raw, base):
    """plan_gate_pre GEOM-STATION-IN-CORE sites the re-floor introduced."""
    try:
        import plan_gate_pre as PGP
        key = lambda r: (r[0], r[1], r[2], r[3])      # noqa: E731
        old = {key(r) for r in PGP.geom_overlaps(base)}
        return sorted(f"{r[0]} {r[1]} in {r[3]}" for r in PGP.geom_overlaps(raw) if key(r) not in old)[:60]
    except Exception as e:
        return [f"UNCHECKED {type(e).__name__}: {e}"[:160]]


def drop_stale_die_relays(raw):
    """reset.die_relays declare the solved wavefront parent / rst_o site of each child; a re-floor can change the solve
    (reset_tree: a declaration that no longer matches is an error, never re-used).  Entries whose parent / site differ
    from reset_tree.wf_solve on the moved plan are dropped here so reach_relay_plan re-plans them.  Returns
    {child: [old parent, old site, new parent, new site]} (or {"error": ...} when the plan has no solvable wavefront)."""
    dr = (raw.get("reset") or {}).get("die_relays")
    if not dr:
        return {}
    try:
        import reset_tree as RT
        P = S.Plan(raw)
        P.reset["die_relays"] = {}
        sol = RT.wf_solve(P)
    except Exception as e:      # no wavefront reset in this plan form: leave the declarations to reach_relay_plan
        return {"error": f"{type(e).__name__}: {e}"[:200]}
    out = {}
    for child in sorted(dr):
        d = dr[child]
        pr = sol["parent"].get(child)
        if pr is None or [pr[0], pr[1]] != [d.get("parent"), d.get("site")]:
            out[child] = [d.get("parent"), d.get("site")] + ([pr[0], pr[1]] if pr else [None, None])
            del dr[child]
    if not dr:
        raw["reset"].pop("die_relays", None)
    return out


def fit_free_slots(raw, parts_free, limit, margin=10.0):
    """ft slots whose geometry this re-floor changed (re-shaped types and types with a re-sited slot window): repair
    the lanes the move broke.  For every lane, the FF-to-FF hops (check.lane_pin_hops, through the seam pins) are
    measured on the moved plan; a run of consecutive crossings through such partitions is refit only if a hop inside
    it (or its two boundary legs) exceeds `limit`.  A refit puts each crossing's stations evenly along its own route
    from the in pin (face register at the pin, then one per 1/k of the crossing), starting at the old count, and adds
    one station at a time to the crossing with the longest step until every step is <= limit - margin.  A lane only
    gains cycles.  Returns the pre-change Plan (latency baseline), {type.slot: [old, new]} and the legs a refit
    cannot fix (fixed station to the run's first pin already over the limit)."""
    import check as C
    import die_hop_scan as DHS
    import ft_full_stage as FFS
    P = S.Plan(copy.deepcopy(raw))      # the pre-change view (also the latency baseline)
    eff = limit - margin
    changes, seen, unfixable = {}, set(), {}
    uses = {}
    for pt in P.parts.values():
        uses[pt["type"]] = uses.get(pt["type"], 0) + 1

    def man(u, v):
        m = (v[0], u[1])
        return [(u, m), (m, v)]

    def walk(segs, t):
        for u, v in segs:
            L = abs(u[0] - v[0]) + abs(u[1] - v[1])
            if t <= L + 1e-9:
                f = 0.0 if L == 0 else t / L
                return (u[0] + (v[0] - u[0]) * f, u[1] + (v[1] - u[1]) * f)
            t -= L
        return segs[-1][1]

    for lid in P.lanes:
        try:
            xs = P.lane_crossings(lid)
        except Exception:
            continue
        if not any(part in parts_free and slot for part, slot, _a, _b in xs):
            continue
        _pts, regs, info = C.lane_geometry(P, lid)
        hops = C.lane_pin_hops(P, lid, regs)
        starts, idx = [], 1
        for x in info:
            starts.append(idx)
            idx += int(x["stations"])
        c = 0
        while c < len(xs):
            if not (xs[c][0] in parts_free and xs[c][1]) or (xs[c][0], xs[c][1]) in seen \
                    or uses[P.parts[xs[c][0]]["type"]] > 1:
                c += 1
                continue
            e = c
            while e + 1 < len(xs) and xs[e + 1][0] in parts_free and xs[e + 1][1] \
                    and (xs[e + 1][0], xs[e + 1][1]) not in seen and uses[P.parts[xs[e + 1][0]]["type"]] == 1:
                e += 1
            # crossings at either end of the run whose own hops (entry, steps, exit) all hold keep their stations: a
            # slot with no declared sites has its first station at the port, which a refit would lose
            def viol(i):        # G0 R3 stations rule: slot route / stations <= limit (non full-stage slots)
                return float(info[i].get("len_um") or 0.0) / max(1, int(info[i]["stations"])) > limit + 1e-6
            ok_c = {i: max(hops[starts[i] - 1:starts[i] - 1 + int(info[i]["stations"])] or [0.0]) <= limit + 1e-6
                    and not viol(i) for i in range(c, e + 1)}
            e_run = e
            def man_d(u, v):
                return abs(u[0] - v[0]) + abs(u[1] - v[1])

            def exit_leg(i):        # last station of crossing i -> seam port (src face) -> the next partition's own face
                q = P.port_point(xs[i + 1][2])
                x0, y0, x1, y1 = P.rect(xs[i + 1][0])
                f = (min(max(q[0], x0), x1), min(max(q[1], y0), y1))
                return man_d(regs[starts[i + 1] - 1], q) + man_d(q, f)
            while c < e and ok_c[c] and exit_leg(c) <= limit + 1e-6:
                c += 1
            while e > c and ok_c[e] and max(hops[starts[e] - 1:starts[e] + int(info[e]["stations"])] or [0.0]) <= limit + 1e-6:
                e -= 1
            run = list(range(c, e + 1))
            nxt_i = starts[e] + int(info[e]["stations"])
            if max(hops[starts[c] - 1:nxt_i] or [0.0]) <= limit + 1e-6 and not any(viol(i) for i in run):
                c = e_run + 1
                continue
            prev = regs[starts[c] - 1]
            nxt = regs[nxt_i] if nxt_i < len(regs) else regs[-1]
            d = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])      # noqa: E731

            def onto(part, q):      # a port point (src face) seen from the dst partition: its own facing face
                x0, y0, x1, y1 = P.rect(part)
                return (min(max(q[0], x0), x1), min(max(q[1], y0), y1))
            ins = [onto(xs[i][0], P.port_point(xs[i][2])) for i in run]
            outs = [P.port_point(xs[i][3]) for i in run]
            routes = [man(ins[j], outs[j]) for j in range(len(run))]
            L = [sum(abs(u[0] - v[0]) + abs(u[1] - v[1]) for u, v in r) for r in routes]
            # after crossing j: out pin -> (seam / channel) -> next crossing's in face, or the next fixed station
            gap = [d(outs[j], P.port_point(xs[run[j + 1]][2])) + d(P.port_point(xs[run[j + 1]][2]), ins[j + 1])
                   for j in range(len(run) - 1)] + [d(outs[-1], nxt)]
            carry = d(prev, P.port_point(xs[run[0]][2])) + d(P.port_point(xs[run[0]][2]), ins[0])
            # each crossing in turn: the fewest stations (from the old count) whose DODGED points (hard-core boxes are
            # part of the search, not applied after it) keep entry leg, every step and exit leg under the limit;
            # candidates = uniform spacing L/k at several entry offsets; ties by the smallest worst step
            fitted = []
            for j, i in enumerate(run):
                part, slot = xs[i][0], xs[i][1]
                tn = P.parts[part]["type"]
                w, h = P.ptype(part)["outline_um"]
                k0 = max(1, int(info[i]["stations"]), math.ceil(float(info[i].get("len_um") or 0.0) / limit - 1e-9))
                try:        # a normal slot's first station is its input face register (G0 / check.lane_geometry)
                    normal = DHS.normal_slot(P, tn, slot, full=FFS.load(P, tn))
                except Exception:
                    normal = False
                best = None
                for kj in range(k0, k0 + math.ceil(L[j] / eff) + 3):
                    sp = L[j] / kj
                    top = max(0.0, min(eff - carry, sp))
                    for f in ((0.0,) if normal else (1.0, 0.85, 0.7, 0.5, 0.3, 0.15, 0.0)):
                        dl = top * f
                        pts = []
                        for m in range(kj):
                            tx, ty = P.to_type(part, walk(routes[j], min(dl + L[j] * m / kj, L[j])))
                            # 0.05 um inside the outline: a station at the face pin stays at the pin (B1 form)
                            pts.append([round(min(max(tx, 0.05), w - 0.05), 3), round(min(max(ty, 0.05), h - 0.05), 3)])
                        pts = dodge_cores(raw["partition_types"][tn], pts)
                        dp = [P.to_die(part, q) for q in pts]
                        legs = [carry + d(ins[j], dp[0])] + [d(u, v) for u, v in zip(dp, dp[1:])]
                        ex = d(dp[-1], outs[j]) + gap[j]
                        # a carry already over the limit is not this slot's to repair: judged as if it fitted
                        worst = max([ex] + legs[1:] + [legs[0] if carry <= eff else d(ins[j], dp[0]) + eff])
                        if best is None or worst < best[0] - 1e-9:
                            best = (worst, pts, ex, legs[0])
                    if best[0] <= limit - 2.0:
                        break
                if best[0] > limit:
                    unfixable[f"{lid}:{part}.{slot}"] = round(best[0], 1)
                fitted.append(best[1])
                carry = best[2]
            for j, i in enumerate(run):
                part, slot = xs[i][0], xs[i][1]
                pts = fitted[j]
                tsl = next(s_ for s_ in raw["partition_types"][P.parts[part]["type"]]["ft_slots"] if s_["name"] == slot)
                k0 = int(tsl.get("stations", 1))
                tsl["regs_um"] = pts
                tsl["stations"] = len(pts)
                tsl.pop("bit_sites_um", None)
                tsl.pop("bit_site_cell_um", None)
                seen.add((part, slot))
                if len(pts) != k0:
                    changes[f"{P.parts[part]['type']}.{slot}"] = [k0, len(pts)]
            c = e_run + 1
    return P, changes, unfixable


def relatency(raw, P0):
    """latency.lanes re-derived after station-count changes (path_respace rule: add the gen.latency_table delta)."""
    import gen
    P2 = S.Plan(raw)
    lat0 = raw.get("latency", {}).get("lanes", {})
    c0, c1 = gen.latency_table(P0), gen.latency_table(P2)
    cycles = {}
    for lid in c1:
        if c0.get(lid) == c1[lid] or lid not in lat0:
            continue
        row = dict(lat0[lid])
        for k, v in c1[lid].items():
            if c0[lid].get(k) != v:
                row[k] = (row.get(k, 0) + v - c0[lid].get(k, 0)) if isinstance(v, (int, float)) \
                    and not isinstance(v, bool) else v
        cycles[lid] = [lat0[lid].get("cycles"), row.get("cycles")]
        raw["latency"]["lanes"][lid] = row
    return cycles


def respace(raw, rows, slot_changed, limit, allow_add=True, only=None):
    """path_respace on the lanes that cross a re-sited port or a changed slot only (the rest of the die is not touched):
    re-space the stations first (0 cycles); with allow_add one station at a time is added to the binding slot (+1 cycle
    on every lane through it) and latency.lanes is re-derived the path_respace way (gen.latency_table delta).  Returns
    per-lane status, max hop before -> after, and the priced cycle changes."""
    import path_respace as PR
    P = S.Plan(copy.deepcopy(raw))      # the pre-change view (also the latency baseline)
    ports = {r["id"] for r in rows if r.get("frames") and any(f["changed"] for f in r["frames"])}
    slots = {(tn, sl) for tn, v in slot_changed.items() for sl in v}
    lanes = []
    for lid, ln in P.lanes.items():
        hit = bool(ports & set(ln.get("ports", [])))
        if not hit:
            try:
                hit = any((P.parts[part]["type"], slot) in slots for part, slot, _a, _b in P.lane_crossings(lid))
            except Exception:
                hit = False
        if hit:
            lanes.append(lid)
    if only is not None:
        lanes = [lid for lid in P.lanes if lid in only]
    decided, out = {}, {}
    for lid in sorted(lanes):
        try:
            lane = PR.Lane(P, lid)
            res = PR.plan_lane(P, lane, limit, allow_add, decided)
        except Exception as e:      # a lane form path_respace does not model: reported, left as is
            out[lid] = dict(status="error", why=f"{type(e).__name__}: {e}"[:200])
            continue
        out[lid] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in res.items() if k not in ("new", "old")}
        if res["status"] != "fixed" or res.get("exact"):
            continue
        tp = {}
        for c, pts in res["new"].items():
            cr = lane.cross[c]
            key = (cr["tn"], cr["slot"])
            tp[key] = [[round(x, 3) for x in P.to_type(cr["part"], q)] for q in pts]
            if key in decided and decided[key] != tp[key]:
                out[lid]["status"] = "replica_conflict"
                break
        else:
            decided.update(tp)
    added = {}
    for (tn, slot), pts in decided.items():
        sl = next(s_ for s_ in raw["partition_types"][tn]["ft_slots"] if s_["name"] == slot)
        if len(pts) != int(sl.get("stations", 1)):
            added[f"{tn}.{slot}"] = [int(sl.get("stations", 1)), len(pts)]
        sl["regs_um"] = pts
        sl["stations"] = len(pts)
        sl.pop("bit_sites_um", None)
        sl.pop("bit_site_cell_um", None)
    cycles = relatency(raw, P) if added else {}
    return dict(lanes=out, slots_respaced=sorted(f"{a}.{b}" for a, b in decided), stations_added=added,
                lane_cycles=cycles)


def summarize(rows):
    c = defaultdict(int)
    for r in rows:
        c[r["status"] if not r["status"].startswith("KEEP-") else "KEEP"] += 1
    ends = defaultdict(set)
    for r in rows:
        for fr in r.get("frames", []):
            if fr["changed"]:
                ends[fr["part"]].add(r["id"])
    return dict(by_status=dict(sorted(c.items())), ports_touched=len(rows),
                ports_repinned=len({r["id"] for r in rows for fr in r.get("frames", []) if fr["changed"]}),
                parts_repinned={k: len(v) for k, v in sorted(ends.items())})


def sha12(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("price")
    a.add_argument("plan")
    a.add_argument("spec")
    a.add_argument("--json")
    b = sub.add_parser("apply")
    b.add_argument("plan")
    b.add_argument("spec")
    b.add_argument("out")
    b.add_argument("--report")
    args = ap.parse_args(argv)
    raw = S.load(args.plan)
    spec = load_spec(args.spec)
    new, rep = apply(raw, spec, float(spec.get("pin_pitch_um", 1.2)))
    rep["base_plan"] = dict(path=str(args.plan), sha12=sha12(args.plan))
    rep["spec"] = dict(path=str(args.spec), sha12=sha12(args.spec))
    bad = rep["layout_findings"] + [f"{r['status']} {r['id']}" for r in rep["port_rows"]
                                    if r["status"] in ("SEAM-LOST", "NO-ROOM", "NO-GEOM", "DIE-IO-MOVED")]
    bad += [f"HOP-OVER {k} {v[0]} -> {v[1]}" for k, v in sorted((rep.get("hops_over_new") or {}).items())]
    bad += [f"LANDING-HOP {k} {v}" for k, v in sorted((rep.get("landing_over") or {}).items())]
    bad += [f"STATION-SPACING {k} {v}" for k, v in sorted((rep.get("stations_over_new") or {}).items())]
    bad += [f"CONTENT-OUTSIDE {k} {len(v)}: {v[:3]}" for k, v in sorted((rep.get("content_outside") or {}).items())]
    bad += [f"STATION-IN-CORE {x}" for x in rep.get("station_in_core_new") or []]
    rep["blocking"] = bad
    print(f"RIGID-REFLOOR parts moved {sum(1 for p in spec['parts'])} reshaped {len(rep.get('reshaped', []))} "
          f"ports {rep['ports']['ports_touched']} repinned {rep['ports']['ports_repinned']} "
          f"types repinned {len(rep['repin_types'])} channels upd {len(rep['channels']['update'])} "
          f"closed {len(rep['channels']['closed'])} new {len(rep['channels']['new_gap'])} blocking {len(bad)}")
    print("by_status", json.dumps(rep["ports"]["by_status"]))
    for x in bad[:40]:
        print("BLOCK", x)
    for tn, fs in rep["repin_types"].items():
        print("REPIN", tn, " ".join(f"{f}:{len(v)}" for f, v in sorted(fs.items())))
    out_json = args.json if args.cmd == "price" else args.report
    if out_json:
        Path(out_json).write_text(json.dumps(rep, indent=1, default=list))
    if args.cmd == "apply":
        Path(args.out).write_text(json.dumps(new, indent=1))
        print(f"WROTE {args.out} {sha12(args.out)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
