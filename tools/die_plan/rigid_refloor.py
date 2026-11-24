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
                                         clamps them into the new outline (pass-through stations).
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


def site_ports(raw, lay, pin_gap=1.2, keep_frame=()):
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
            if n in reshaped:
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
        if len(moving) < 2:
            continue
        moving.sort(key=lambda r: (r["old"][0], r["new"][0]))     # keep the old order on the face
        lo = max(r["lo"] for r in moving)
        hi = min(r["hi"] for r in moving)
        need = sum(r["new"][1] - r["new"][0] for r in moving) + gap * (len(moving) - 1)
        if need > hi - lo + EPS:
            for r in moving:
                r["status"] = "NO-ROOM"
            continue
        q = (lambda d: math.ceil(d / grid - 1e-9) * grid) if grid else (lambda d: d)
        cur = None
        for r in moving:
            L = r["new"][1] - r["new"][0]
            st = r["new"][0]
            if cur is not None and st < cur + gap:
                st = st + q(cur + gap - st)
            r["new"] = [round(st, 6), round(st + L, 6)]
            cur = st + L
        over = cur - hi
        if over > EPS:      # pushed past the top: shift the packed run down as one block
            over = q(over)
            for r in moving:
                r["new"] = [round(r["new"][0] - over, 6), round(r["new"][1] - over, 6)]
        if any(r["new"][0] < r["lo"] - EPS or r["new"][1] > r["hi"] + EPS for r in moving):
            for r in moving:
                r["status"] = "NO-ROOM"


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
    n = max(int(slot.get("stations", 2)), 2)
    out = []
    for k in range(n):
        t = total * k / (n - 1)
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


def frame_offset(old_rect, new_rect, orient):
    """type-frame translation that keeps a die point fixed when a partition re-shapes from old_rect to new_rect."""
    (ox0, oy0, ox1, oy1), (nx0, ny0, nx1, ny1) = old_rect, new_rect
    dxd = (ox0 - nx0) if orient in ("R0", "MX") else (nx1 - ox1)
    dyd = (oy0 - ny0) if orient in ("R0", "MY") else (ny1 - oy1)
    return dxd, dyd


def apply(raw, spec, pin_gap=1.2):
    raw = copy.deepcopy(raw)
    lay = new_layout(raw, spec)
    die_wh = tuple(spec.get("die_outline_um") or raw["die"]["outline_um"])
    rep = dict(schema=SCHEMA, layout_findings=layout_findings(raw, lay, die_wh))
    rows = site_ports(raw, lay, pin_gap, set(spec.get("keep_frame", [])))
    types = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    reshaped = {n for n, (a, b) in lay.items() if abs((a[2] - a[0]) - (b[2] - b[0])) > EPS
                or abs((a[3] - a[1]) - (b[3] - b[1])) > EPS}
    remap = set(spec.get("remap_internal", []))
    # 1. re-shaped types: internal frame offset (keep die positions) BEFORE windows are written
    for n in sorted(reshaped):
        t = types[parts[n]["type"]]
        o = parts[n].get("orient", "R0")
        dx, dy = frame_offset(lay[n][0], lay[n][1], o)
        nw, nh = lay[n][1][2] - lay[n][1][0], lay[n][1][3] - lay[n][1][1]
        for k in ("contents", "hard_cores", "internal_stations", "relay_sites", "clock", "reset", "count_straps",
                  "ft_slots"):
            if k in t:
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
        if n in remap:
            for k in ("contents", "hard_cores", "internal_stations", "relay_sites", "clock", "reset", "count_straps"):
                if k in t:
                    _clamp_frame(t[k], nw, nh)
        ins = (raw.get("reset", {}).get("in_sites") or {}).get(parts[n]["type"])
        if isinstance(ins, list) and len(ins) == 2:
            raw["reset"]["in_sites"][parts[n]["type"]] = [round(min(max(ins[0] + dx, 0.0), nw), 6),
                                                         round(min(max(ins[1] + dy, 0.0), nh), 6)]
        rep.setdefault("reshaped", []).append(dict(part=n, type=parts[n]["type"], frame_offset_um=[dx, dy],
                                                   outline_um=[nw, nh], remap=n in remap))
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
    # 4. ft slots with a changed window: rebuild regs, drop exact bit sites
    for n in sorted(reshaped):
        t = types[parts[n]["type"]]
        for s_ in t.get("ft_slots", []):
            slot_changed[parts[n]["type"]].add(s_["name"])
    for tn, names in slot_changed.items():
        t = types[tn]
        for s_ in t.get("ft_slots", []):
            if s_["name"] in names and "in_window_um" in s_ and "out_window_um" in s_:
                if "regs_um" in s_:
                    s_["regs_um"] = _route_regs(s_, t["outline_um"])
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
    return raw, rep


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
