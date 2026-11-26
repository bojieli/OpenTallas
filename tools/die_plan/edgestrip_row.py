#!/usr/bin/env python3
"""EDGESTRIP-1 (VIS-DIE-S81, COORD 11-23 ruling): one S81 die plan transform.

For every type with a die pin window >= MIN_BITS wide, the hard cores behind the window must leave a core-free strip
>= STRIP_UM (69.12 = 8 x 8.64, the col converging threshold) between the face and the nearest core whose span overlaps
the window. Form = the COL-H9R0-STRIP form generalised (VIS-S81-COL colstrip_row.py): the whole type interior (hard
cores, contents, stations, relay sites/polylines, ft bit sites, clock taps/landing stages/collectors, reset anchors,
place regions) moves rigidly by (DX, DY) in steps of 8.64 um inside the unchanged outline. Face-anchored points (within
EDGE um of an edge) and points in the strip of the face the floor moves TOWARD (closer than that face's old core margin)
stay. Buses, ports, windows and outlines never change.

Per axis the shift range is [lo, hi]: lo/hi from the blocked faces (strip >= STRIP_UM behind every >=MIN_BITS window)
and from the core margin on every face (>= CORE_MARGIN, 17.28, as COL). dX first (E/W windows use core y spans, which
dX does not change), then dY on the dX-shifted cores. When lo > hi the type gets the shift that maximises the smaller
blocked strip (PARTIAL) and is listed for a re-shape.

usage: edgestrip_row.py PLAN_IN [--apply OUT] [--ops OPS] [--report REP] [--types a,b] [--exclude-re RE]
"""
import argparse
import copy
import json
import math
import re
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("plan")
ap.add_argument("--apply")
ap.add_argument("--ops")
ap.add_argument("--report")
ap.add_argument("--types", default="")
ap.add_argument("--exclude-re", default="")
ap.add_argument("--min-bits", type=int, default=256)
ap.add_argument("--strip", type=float, default=69.12)
ap.add_argument("--core-margin", type=float, default=17.28)
ap.add_argument("--step", type=float, default=8.64)
ap.add_argument("--edge", type=float, default=2.2)
a = ap.parse_args()

P = json.load(open(a.plan))
T = P["partition_types"]
parts = {p["name"]: p for p in P["partitions"]}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
R = lambda v: round(v, 4)
NONPOINT = {"outline_um", "track_offset_um", "bit_site_cell_um", "window_um", "in_window_um", "out_window_um", "bits",
            "halo_um", "size_um", "pitch_um", "range", "span_um"}
SKIP_SUBTREES = {"buses", "dead_inputs", "relay_depth", "verilog_defines", "count_straps"}


def type_face(part, dface):
    o = parts[part].get("orient", "R0")
    if dface in "NS":
        return OPP[dface] if o in ("MX", "R180") else dface
    return OPP[dface] if o in ("MY", "R180") else dface


def to_type_span(part, dface, lo, hi):
    p = parts[part]
    W, H = T[p["type"]]["outline_um"]
    o = p.get("orient", "R0")
    if dface in "NS":
        base, ext, flip = p["origin_um"][0], W, o in ("MY", "R180")
    else:
        base, ext, flip = p["origin_um"][1], H, o in ("MX", "R180")
    a_, b_ = lo - base, hi - base
    if flip:
        a_, b_ = ext - b_, ext - a_
    return a_, b_


# windows per type (type frame): type -> face -> [(lo, hi, bits, pid)]
WIN = {}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_port_window_pair as PW   # same fallback as ADV-EDGE-STRIP: port without face/window -> src/dst type geometry
for pr in P["ports"]:
    w = int(pr.get("width", 1) or 1)
    if w < a.min_bits:
        continue
    if "window_um" not in pr or "face" not in pr:
        g = PW._side_geom(parts, T, pr, "src") or PW._side_geom(parts, T, pr, "dst")
        if not g:
            continue
        pr = dict(pr, face=g[0], window_um=g[1])
    s, d = pr["src"]["part"], pr["dst"]["part"]
    fp = s if s != "@die" else d
    sides = [(fp, pr["face"])]
    oth = d if fp == s else s
    if oth in parts and oth != fp:
        sides.append((oth, OPP[pr["face"]]))
    lo, hi = sorted(pr["window_um"])
    for part, df in sides:
        if part not in parts:
            continue
        tn = parts[part]["type"]
        tf = type_face(part, df)
        x, y = to_type_span(part, df, lo, hi)
        WIN.setdefault(tn, {}).setdefault(tf, []).append((x, y, w, pr["id"]))


def boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        if "origin_um" not in c or "outline_um" not in c:
            continue
        x, y = c["origin_um"]
        w, h = c["outline_um"]
        out.append([x, y, x + w, y + h, c.get("inst")])
    for c in t.get("contents") or []:             # placed macros (sram/rom) are obstacles too and move as units
        if isinstance(c, dict) and "origin_um" in c and "outline_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            out.append([x, y, x + w, y + h, c.get("inst")])
    return out


def strips(B, wins, W, H):
    """face -> min strip behind any >=MIN_BITS window (None = no core behind)."""
    res = {}
    for f, ws in wins.items():
        best = None
        for lo, hi, _, _ in ws:
            for x0, y0, x1, y1, _ in B:
                s0, s1 = (x0, x1) if f in "NS" else (y0, y1)
                if min(s1, hi) - max(s0, lo) <= 0.01:
                    continue
                d = {"S": y0, "N": H - y1, "W": x0, "E": W - x1}[f]
                best = d if best is None else min(best, d)
        res[f] = best
    return res


def axis_range(B, wins, W, H, axis):
    """allowed shift [lo, hi] along axis ('x' or 'y') and the blocked faces' needs."""
    lowf, highf = ("W", "E") if axis == "x" else ("S", "N")
    i0, i1, ext = (0, 2, W) if axis == "x" else (1, 3, H)
    mn = min(b[i0] for b in B)
    mx = max(b[i1] for b in B)
    lo = a.core_margin - mn          # keep core margin on the low face
    hi = (ext - a.core_margin) - mx  # and on the high face
    st = strips(B, {f: wins[f] for f in (lowf, highf) if f in wins}, W, H)
    need_lo, need_hi = -1e9, 1e9
    if st.get(lowf) is not None and st[lowf] < a.strip - 1e-6:
        need_lo = a.strip - st[lowf]            # move away from the low face
    if st.get(highf) is not None and st[highf] < a.strip - 1e-6:
        need_hi = -(a.strip - st[highf])        # move away from the high face
    # a blocked face that is fine now must stay fine: shifting toward it is limited
    if st.get(lowf) is not None and st[lowf] >= a.strip - 1e-6:
        lo = max(lo, a.strip - st[lowf])
    if st.get(highf) is not None and st[highf] >= a.strip - 1e-6:
        hi = min(hi, st[highf] - a.strip)
    return lo, hi, need_lo, need_hi, st


def choose(lo, hi, need_lo, need_hi):
    """smallest |d| (multiple of step) with max(lo, need_lo) <= d <= min(hi, -need_hi... ) etc."""
    L = max(lo, need_lo if need_lo > -1e8 else -1e9)
    Hh = min(hi, need_hi if need_hi < 1e8 else 1e9)
    st = a.step
    if L <= Hh + 1e-6:
        if L <= 0 <= Hh:
            return 0.0, "OK"
        d = math.ceil(L / st - 1e-9) * st if L > 0 else math.floor(Hh / st + 1e-9) * st
        if L - 1e-6 <= d <= Hh + 1e-6:
            return R(d), "OK"
        # step grid does not fit: fall back to 2.16 grid
        st2 = 2.16
        d = math.ceil(L / st2 - 1e-9) * st2 if L > 0 else math.floor(Hh / st2 + 1e-9) * st2
        if L - 1e-6 <= d <= Hh + 1e-6:
            return R(d), "OK"
    # infeasible: balance the two needs inside the margin range
    if need_lo > -1e8 and need_hi < 1e8:
        d = (need_lo + need_hi) / 2.0
    elif need_lo > -1e8:
        d = need_lo
    elif need_hi < 1e8:
        d = need_hi
    else:
        d = 0.0
    d = max(lo, min(hi, d))
    d = math.floor(d / 2.16) * 2.16 if d > 0 else math.ceil(d / 2.16) * 2.16
    return R(d), "PARTIAL"


def shift_type(t, dx, dy, W, H, margins_old, band=None):
    """rigid shift of the interior by (dx, dy); band = (axis_of_band, [(lo, hi), ...]) limits it to cores whose span
    on that axis intersects the band and to points whose coordinate on that axis lies in the band."""
    new = copy.deepcopy(t)
    cnt = [0]

    def inband(v0, v1=None):
        if band is None:
            return True
        v1 = v0 if v1 is None else v1
        return any(min(v1, h) - max(v0, l) > 0.01 or (v1 == v0 and l - 1e-6 <= v0 <= h + 1e-6) for l, h in band[1])

    def stays(x, y):
        if x <= a.edge or x >= W - a.edge or y <= a.edge or y >= H - a.edge:
            return True
        if dx > 0 and W - x < margins_old["E"]:
            return True
        if dx < 0 and x < margins_old["W"]:
            return True
        if dy > 0 and H - y < margins_old["N"]:
            return True
        if dy < 0 and y < margins_old["S"]:
            return True
        if band is not None and not inband(y if band[0] == "y" else x):
            return True
        return False

    OLDB, NEWB = [], []

    def inside(x, y, bs):
        return any(b[0] + 0.01 < x < b[2] - 0.01 and b[1] + 0.01 < y < b[3] - 0.01 for b in bs)

    def mv(p):
        x, y = p
        q = [R(x + dx), R(y + dy)]
        use_q = not (stays(x, y) and not inside(x, y, OLDB))
        a_, b_ = (q, p) if use_q else (p, q)
        if inside(a_[0], a_[1], NEWB) and not inside(b_[0], b_[1], NEWB):
            use_q = not use_q          # never put a point into a moved core when the other choice is free
        if use_q:
            cnt[0] += 1
            return snap_out(q)
        return p

    def snap_out(q):
        """a moved point must not lie in any core/macro (plan_gate_pre GEOM refuses moved in-core sites even when the
        J8 site was in-core and tolerated): push it to the nearest free spot just outside the box edge."""
        x, y = q
        for _ in range(6):
            hit = [b for b in ALLB if b[0] + 0.01 < x < b[2] - 0.01 and b[1] + 0.01 < y < b[3] - 0.01]
            if not hit:
                return [R(x), R(y)]
            b = hit[0]
            cands = [(x - b[0], b[0] - 0.54, y), (b[2] - x, b[2] + 0.54, y), (y - b[1], x, b[1] - 0.54), (b[3] - y, x, b[3] + 0.54)]
            cands = [c for c in cands if 0.3 < c[1] < W - 0.3 and 0.3 < c[2] < H - 0.3]
            free = [c for c in cands if not any(o[0] + 0.01 < c[1] < o[2] - 0.01 and o[1] + 0.01 < c[2] < o[3] - 0.01 for o in ALLB)]
            c = min(free or cands)
            x, y = c[1], c[2]
        return [R(x), R(y)]

    def walk(o, key=None):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in SKIP_SUBTREES or k in NONPOINT:
                    continue
                if isinstance(v, list) and len(v) == 2 and all(isinstance(z, (int, float)) for z in v):
                    o[k] = mv(v)
                else:
                    walk(v, k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, list) and len(v) == 2 and all(isinstance(z, (int, float)) for z in v):
                    o[i] = mv(v)
                else:
                    walk(v, key)

    for c in (new.get("hard_cores") or []) + [m for m in (new.get("contents") or []) if isinstance(m, dict)]:
        if "origin_um" in c and "outline_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            if band is None or (inband(y, y + h) if band[0] == "y" else inband(x, x + w)):
                c["origin_um"] = [R(x + dx), R(y + dy)]
                OLDB.append((x, y, x + w, y + h))
                NEWB.append((x + dx, y + dy, x + w + dx, y + h + dy))
    ALLB = [tuple(b[:4]) for b in boxes(new)]
    for k, v in list(new.items()):
        if k in ("hard_cores", "outline_um") or k in SKIP_SUBTREES or k in NONPOINT:
            continue
        if k == "contents":                        # macros moved above as boxes; nothing else in contents is a point
            continue
        if isinstance(v, (dict, list)):
            tmp = {k: v}
            walk(tmp)
            new[k] = tmp[k]
    return new, cnt[0]


def band_move(B, wins, W, H, f):
    """cores behind blocked windows on face f plus every core sharing their orthogonal band (transitively) move
    inward; returns (d, band_axis, band, status) or None."""
    axis = "x" if f in "WE" else "y"
    oi0, oi1 = (1, 3) if axis == "x" else (0, 2)
    seeds = []
    for lo, hi, _, _ in wins.get(f, []):
        for b in B:
            s0, s1 = b[oi0], b[oi1]
            if min(s1, hi) - max(s0, lo) <= 0.01:
                continue
            d = {"S": b[1], "N": H - b[3], "W": b[0], "E": W - b[2]}[f]
            if d < a.strip - 1e-6:
                seeds.append(b)
    if not seeds:
        return None
    band = sorted((b[oi0], b[oi1]) for b in seeds)
    while True:
        M = [b for b in B if any(min(b[oi1], h) - max(b[oi0], l) > 0.01 for l, h in band)]
        nb = []
        for l, h in sorted((b[oi0], b[oi1]) for b in M):
            if nb and l <= nb[-1][1] + 0.01:
                nb[-1][1] = max(nb[-1][1], h)
            else:
                nb.append([l, h])
        nb = [tuple(x) for x in nb]
        if nb == band:
            break
        band = nb
    if len(M) == len(B):
        return None
    need = a.strip - min({"S": b[1], "N": H - b[3], "W": b[0], "E": W - b[2]}[f] for b in seeds)
    ext = W if axis == "x" else H
    if f in "WS":
        room = (ext - a.core_margin) - max(b[2 if axis == "x" else 3] for b in M)
        st_opp = strips(M, {OPP[f]: wins[OPP[f]]} if OPP[f] in wins else {}, W, H).get(OPP[f])
        if st_opp is not None:
            room = min(room, max(0.0, st_opp - a.strip)) if st_opp >= a.strip else 0.0
        sign = 1
    else:
        room = min(b[0 if axis == "x" else 1] for b in M) - a.core_margin
        st_opp = strips(M, {OPP[f]: wins[OPP[f]]} if OPP[f] in wins else {}, W, H).get(OPP[f])
        if st_opp is not None:
            room = min(room, max(0.0, st_opp - a.strip)) if st_opp >= a.strip else 0.0
        sign = -1
    d = math.ceil(need / a.step - 1e-9) * a.step
    status = "OK"
    if d > room + 1e-6:
        d = math.ceil(need / 2.16 - 1e-9) * 2.16
        if d > room + 1e-6:
            d = math.floor(room / 2.16 + 1e-9) * 2.16
            status = "PARTIAL"
    if d <= 0:
        return None
    return R(sign * d), ("y" if axis == "x" else "x"), band, status


def checks(tn, new, W, H):
    probs = []
    B = boxes(new)
    for x0, y0, x1, y1, inst in B:
        if x0 < a.core_margin - 0.01 or y0 < a.core_margin - 0.01 or x1 > W - a.core_margin + 0.01 or y1 > H - a.core_margin + 0.01:
            probs.append(f"core {inst} past margin")
    for i, b in enumerate(B):
        for c in B[i + 1:]:
            if min(b[2], c[2]) - max(b[0], c[0]) > 0.01 and min(b[3], c[3]) - max(b[1], c[1]) > 0.01:
                probs.append(f"core {b[4]} overlaps {c[4]}")
    pts = []
    for k, v in (new.get("relay_sites") or {}).items():
        pts.append(("relay", k, v))
    for st in new.get("internal_stations") or []:
        for p in st.get("regs_um") or []:
            pts.append(("ist", st.get("name") or st.get("id"), p))
    for kind, k, v in pts:
        for x0, y0, x1, y1, inst in B:
            if x0 + 0.5 < v[0] < x1 - 0.5 and y0 + 0.5 < v[1] < y1 - 0.5:
                probs.append(f"{kind} {k} inside {inst}")
                break
    return probs


only = set(a.types.split(",")) if a.types else None
exc = re.compile(a.exclude_re) if a.exclude_re else None
rep = []
ops = []
for tn in sorted(WIN):
    if only and tn not in only:
        continue
    if exc and exc.search(tn):
        continue
    t = T[tn]
    W, H = t["outline_um"]
    B = boxes(t)
    if not B:
        continue
    st0 = strips(B, WIN[tn], W, H)
    blocked = {f: s for f, s in st0.items() if s is not None and s < a.strip - 1e-6}
    if not blocked:
        continue
    margins_old = {"W": min(b[0] for b in B), "S": min(b[1] for b in B), "E": W - max(b[2] for b in B),
                   "N": H - max(b[3] for b in B)}
    moves = []
    cur = copy.deepcopy(t)
    Bc = boxes(cur)
    stat = []
    for axis, faces in (("x", ("W", "E")), ("y", ("S", "N"))):
        lo, hi, nlo, nhi, _ = axis_range(Bc, WIN[tn], W, H, axis)
        d, sa = choose(lo, hi, nlo, nhi)
        if sa == "OK":
            if d:
                mo = {"W": min(b[0] for b in Bc), "S": min(b[1] for b in Bc), "E": W - max(b[2] for b in Bc),
                      "N": H - max(b[3] for b in Bc)}
                cur, _ = shift_type(cur, d if axis == "x" else 0.0, d if axis == "y" else 0.0, W, H, mo)
                moves.append({"axis": axis, "d": d, "band": None})
            stat.append("OK")
            Bc = boxes(cur)
            continue
        for f in faces:
            Bc = boxes(cur)
            bm = band_move(Bc, WIN[tn], W, H, f)
            if bm is None:
                continue
            d, bax, band, sb = bm
            mo = {"W": min(b[0] for b in Bc), "S": min(b[1] for b in Bc), "E": W - max(b[2] for b in Bc),
                  "N": H - max(b[3] for b in Bc)}
            cur, _ = shift_type(cur, d if axis == "x" else 0.0, d if axis == "y" else 0.0, W, H, mo, band=(bax, band))
            moves.append({"axis": axis, "d": d, "band": [bax, [list(x) for x in band]], "face": f, "status": sb})
        Bc = boxes(cur)
        st_ax = strips(Bc, {f: WIN[tn][f] for f in faces if f in WIN[tn]}, W, H)
        stat.append("OK" if all(v is None or v >= a.strip - 1e-6 for v in st_ax.values()) else "PARTIAL")
    st1 = strips(boxes(cur), WIN[tn], W, H)
    status = "OK" if all(x == "OK" for x in stat) else "PARTIAL"
    r = dict(type=tn, W=W, H=H, blocked={f: R(s) for f, s in blocked.items()}, moves=moves, status=status,
             strips_after={f: (None if s is None else R(s)) for f, s in st1.items()},
             margins_old={f: R(v) for f, v in margins_old.items()})
    if not moves:
        r["status"] = "NO-MOVE-" + status
        rep.append(r)
        continue
    new = cur
    r["problems"] = sorted(set(checks(tn, new, W, H)) - set(checks(tn, t, W, H)))[:20]
    rep.append(r)
    for key in sorted(set(new) | set(t)):
        if new.get(key) != t.get(key):
            ops.append({"op": "replace", "path": f"/partition_types/{tn}/{key}", "value": new[key]})
    T[tn] = new
    dx = sum(m["d"] for m in moves if m["axis"] == "x" and m["band"] is None)
    dy = sum(m["d"] for m in moves if m["axis"] == "y" and m["band"] is None)
    # die-level type-frame reset entry site
    ins = (P.get("reset") or {}).get("in_sites") or {}
    if tn in ins:
        x, y = ins[tn]
        if not (x <= a.edge or x >= W - a.edge or y <= a.edge or y >= H - a.edge):
            ins[tn] = [R(x + dx), R(y + dy)]
            ops.append({"op": "replace", "path": f"/reset/in_sites/{tn}", "value": ins[tn]})

from collections import Counter
print("types", len(rep), Counter(r["status"] for r in rep))
print("with problems", sum(1 for r in rep if r.get("problems")))
fam = Counter((re.sub(r"__.*", "", r["type"]), r["status"]) for r in rep)
for k, v in sorted(fam.items()):
    print(" ", k, v)
if a.report:
    json.dump(rep, open(a.report, "w"), indent=0)
if a.ops:
    json.dump({"schema": "opentallas.s81.die_row.v1", "row": "EDGESTRIP-1", "lane": "VIS-DIE-S81",
               "params": vars(a), "ops": ops}, open(a.ops, "w"))
    print("ops", len(ops))
if a.apply:
    json.dump(P, open(a.apply, "w"))
    print("wrote", a.apply)
