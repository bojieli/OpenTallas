#!/usr/bin/env python3
"""B2o = B2n re-floorplanned (COORD 2026-10-25 00:21 PDT rulings (2)+(3) on B2n@871717c83).  Derived deterministically
from B2n (B2n stays); every input is in B2o_inputs/*.json:

    python3 physical/die_plan/hbm_arch/b2o.py [--src B2n] [--out B2o]

Problems fixed (COORD directive to HBM-B2O):
  1. the SU types were ~50 % empty after the exp-lane reshape, inside a middle region whose size came from the
     hub <-> root transit (6 b-columns of 708-um strips carrying 8-10 kbit of hub <-> root pins on every face);
  2. hub -> root L74 short and the hub perimeter full (a star).
Steps:
  1. floorplan  B2o_inputs/floorplan.json: the middle region becomes three rows (NW frame; NE = MY mirror, one pin
                table per type): R1 = exp-lane SU types two cells high + their SFU-core partners, Rh = io | hc ring
                2 x 4 | HUB as a spine whose E face ABUTS ROOT (hub <-> root = one neighbour hop, no transit
                partitions), R4 = the 2x2 SU types + the SFU / IDX partitions that talk to them or to the hub.  Widths
                are the types' compact core grids at the row height ('auto', cores_b2 shelf / column packer on the
                8.64 lattice) plus a share of the row slack ('auto+'); rows abut, no unassigned area.  SM rows, PHY
                row, spt / spb / vsN columns keep their x; everything above the middle region moves down; root keeps
                1382.4 wide and grows root_ext_um into vsN2 / vsN4.
  2. lanes      every lane re-routed on the new abutment graph: PathFinder over partition hops (cost = route length
                + one 360-um hop per partition crossing + face / transit congestion with history), NW primaries and
                their 'm' mirrors routed as MY images, die-level lanes only through die-level partitions; lane ids,
                widths, kinds and END buses (type pin names) kept; ports / ft slots re-emitted (B2n naming).
  3. lane_delta B2o_inputs/lane_delta.json: L74 (hub -> root) widened toward the RTL need (ruling 1: >= ceil(need/3)
                per static beat), now on the hub / root abutting face.
  4. windows    b2n.rewindow / enforce_mirror / fix_mirror_pins (2 pin layers, <= 5.6 pins / um, mirror tables).
  5. contents   every changed soft type: hard cores (outline + pins FROZEN, b2n_core_outlines.json) and soft leaves
                re-placed by cores_b2.place_flow (data flow: core_conns.json partners, bus windows), core taps carried,
                partition tap re-sited; R3-INTERNAL stations re-derived from core_conns (cores_b2 rule, HOP 360).
  6. b2n.restation (ft slot + internal stations <= 405), b2m.clock (H-tree + taps), reset wavefront, latency table.
"""
import argparse
import collections
import heapq
import json
import math
import re
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
import b2n as B  # noqa: E402
import cores_b2 as CB  # noqa: E402

LAT = 8.64
INP = HERE / "B2o_inputs"
SIDECARS = ["census_map.json", "core_conns.json", "cores_b2.json", "cores", "inputs"]
FACE_CAP = 5.6 * 0.92          # usable face pins / um of contact (2 layers, PIN_DENS, window gaps)
FT_CAP = 5.0                   # transit bits / um of partition extent (M4-M7 x ft_track_frac x cut 0.6, check.py cuts)
HOP_UM = 360.0                 # one partition crossing = 2 boundary flops ~ one station hop


def lat(v):
    return round(round(v / LAT) * LAT, 4)


def lat_up(v):
    return round(math.ceil(v / LAT - 1e-9) * LAT, 4)


def mir(n):
    return "NE_" + n[3:] if n.startswith("NW_") else "NW_" + n[3:] if n.startswith("NE_") else n


def single(n):
    return mir(n) == n


# ------------------------------------------------------------------------------------------------ 1. floorplan
def items_of(t):
    hc = t.get("hard_cores", []) or []
    ins = {h["inst"] for h in hc}
    out = [(h["inst"], h["outline_um"][0], h["outline_um"][1]) for h in hc]
    for c in t.get("contents", []):
        if "outline_um" in c and "origin_um" in c and c["inst"] not in ins and \
                not any(i.startswith(c["inst"] + "_") for i in ins):
            out.append((c["inst"], c["outline_um"][0], c["outline_um"][1]))
    return out


IO_TYPES = ("NW_io", "NE_io")


def compact_w(t, H):
    """smallest 8.64-lattice width whose shelf (or column) pack fits the type's cores + soft leaves at height H, plus
    one lattice of face band on each side (place_flow keeps HALO from the faces and between items)."""
    it = items_of(t)
    if not it:
        return 0.0
    if t.get("module", "").endswith(IO_TYPES):      # SerDes partitions keep their PHY macro at the die-edge site
        cs = [c for c in t.get("contents", []) if "origin_um" in c and "outline_um" in c]
        assert max(c["origin_um"][1] + c["outline_um"][1] for c in cs) + LAT <= H + 1e-6
        return lat_up(max(c["origin_um"][0] + c["outline_um"][0] for c in cs) + LAT)
    for k in range(4, 3000):
        W = k * LAT
        if CB.pack(it, W, H) or CB.pack_columns(it, W, H):
            return round(W, 4)
    raise SystemExit(f"compact_w: {t.get('module')} does not fit height {H}")


def layout(plan, FP, log):
    """NW + die-level rects from the row spec; NE = MY mirror.  Returns {part: (x, y, w, h)}, new die H, dy_top."""
    T = plan["partition_types"]
    P = S.Plan(plan)
    W, H0 = plan["die"]["outline_um"]
    half = None
    smh = FP["sm_row_h"]
    rows = FP["rows"]
    mid0 = smh
    hm = sum(rows[r] for r in FP["row_order"])
    dy = hm - FP["old_mid_h"]
    mid1 = mid0 + hm
    rect = {}
    yr, y = {}, mid0
    for r in FP["row_order"]:
        yr[r] = (y, rows[r])
        y += rows[r]
    widths = {}
    for r, seq in FP["seq"].items():
        y0, h = yr[r]
        # pass 1: autos
        need = []
        for it in seq:
            if it[0] == "col":
                parts, spec = it[1], it[2]
                sh = h / len(parts)
                w = max(compact_w(T[P.parts[p]["type"]], sh) for p in parts)
            else:
                parts, spec = [it[0]], it[1]
                w = compact_w(T[P.parts[it[0]]["type"]], h)
            need.append((parts, spec, lat_up(w)))
        # pass 2: positions; 'to:X' segments split the row, 'auto+' share the slack of their segment
        x = 0.0
        seg = []
        for parts, spec, w in need:
            seg.append([parts, spec, 0.0 if spec.startswith("to:") else w, w])
            if spec.startswith("to:"):
                xe = float(spec[3:])
                fixed = sum(s[2] for s in seg)
                flex = [s for s in seg if s[1] == "auto+"]
                last = seg[-1]
                slack = xe - x - fixed - last[3]
                if flex and slack > 0:
                    tot = sum(s[2] for s in flex)
                    acc = 0.0
                    for s in flex:
                        add = round(math.floor(slack * s[2] / tot / LAT + 1e-9) * LAT, 4)
                        s[2] += add
                        acc += add
                    slack -= acc
                last[2] = round(last[3] + slack, 4)
                assert last[2] >= last[3] - 1e-3, (f"row {r}: segment up to {xe} overfull: last {last[0]} gets "
                                                   f"{last[2]:.1f} < compact {last[3]:.1f} ({[(s[0], s[3]) for s in seg]})")
                for s in seg:
                    ps, w_ = s[0], s[2]
                    sh = h / len(ps)
                    for i, p in enumerate(ps):
                        rect[p] = (round(x, 4), round(y0 + i * sh, 4), round(w_, 4), round(sh, 4))
                    widths[tuple(ps)] = (round(w_, 2), s[1])
                    x = round(x + w_, 4)
                seg = []
        assert not seg and abs(x - 13357.44) < 1e-3, f"row {r} ends at {x}"
    # fixed partitions: SM rows, PHY row, spt / spb / vsN columns, root
    ext = FP["root_ext_um"]
    for n, p in P.parts.items():
        if n.startswith("NE_") or n in rect:
            continue
        x0, y0, x1, y1 = P.rect(n)
        if n == "root":
            rect[n] = (x0, mid0 - ext, x1 - x0, hm + 2 * ext)
        elif n == "vsN2":
            rect[n] = (x0, y0, x1 - x0, (mid0 - ext) - y0)
        elif n == "vsN4":
            rect[n] = (x0, mid1 + ext, x1 - x0, (y1 + dy) - (mid1 + ext))
        elif y0 >= FP["old_mid_h"] + smh - 1e-3:
            rect[n] = (x0, round(y0 + dy, 4), x1 - x0, y1 - y0)
        elif y1 <= smh + 1e-3:
            rect[n] = (x0, y0, x1 - x0, y1 - y0)
        else:
            raise SystemExit(f"layout: middle-region partition {n} not in floorplan.json")
    for n in list(rect):
        if n.startswith("NW_"):
            x, y_, w, h = rect[n]
            rect[mir(n)] = (round(W - x - w, 4), y_, w, h)
    rows_log = "; ".join(f"{r} {rows[r]:g}: " + ", ".join(f"{'/'.join(k).replace('NW_', '')} {v[0]:g}"
                                                         for k, v in widths.items() if rect[k[0]][1] >= yr[r][0] - 1e-3
                                                         and rect[k[0]][1] < yr[r][0] + yr[r][1] - 1e-3)
                         for r in FP["row_order"])
    log.append(f"floorplan: middle region {FP['old_mid_h']:g} -> {hm:g} um (die H {H0:g} -> {H0 + dy:g}); {rows_log}")
    return rect, round(H0 + dy, 4), dy, widths


def apply_rects(plan, rect, newH, dy, log):
    """partition origins / type outlines from the rects (orientation kept: the type frame origin is the rect's
    lower-left for R0 and MY alike in schema); die outline; die IO windows + PHY pg domains move with their partition
    (relative position kept)."""
    P0 = S.Plan(plan)
    old = {n: P0.rect(n) for n in P0.parts}
    T = plan["partition_types"]
    seen = {}
    for p in plan["partitions"]:
        n = p["name"]
        x, y, w, h = rect[n]
        tn = p["type"]
        if tn in seen:
            assert abs(seen[tn][0] - w) < 1e-3 and abs(seen[tn][1] - h) < 1e-3, f"type {tn}: instances differ {seen[tn]} vs {(w, h)}"
        seen[tn] = (w, h)
        p["origin_um"] = [round(x, 4), round(y, 4)]
    changed = []
    for tn, (w, h) in seen.items():
        t = T[tn]
        ow, oh = t["outline_um"]
        if abs(ow - w) > 1e-3 or abs(oh - h) > 1e-3:
            assert not t.get("hard"), f"hard type {tn} would change outline {ow}x{oh} -> {w}x{h}"
            t["outline_um"] = [round(w, 4), round(h, 4)]
            changed.append(tn)
    plan["die"]["outline_um"] = [plan["die"]["outline_um"][0], newH]
    P1 = S.Plan(plan)
    moved_io = []
    for wdw in plan["die"].get("io", []):
        n = wdw["part"]
        ox0, oy0, ox1, oy1 = old[n]
        nx0, ny0, nx1, ny1 = P1.rect(n)
        r = wdw["rect_um"]
        # keep the window's offset from the partition corner on the die edge it sits on
        dxx = nx0 - ox0 if abs(r[0] - ox0) < abs(r[2] - ox1) else nx1 - ox1
        dyy = ny0 - oy0 if abs(r[1] - oy0) < abs(r[3] - oy1) else ny1 - oy1
        wdw["rect_um"] = [round(r[0] + dxx, 4), round(r[1] + dyy, 4), round(r[2] + dxx, 4), round(r[3] + dyy, 4)]
        for d in plan["die"].get("pg", {}).get("domains", []):
            if wdw["name"] in d.get("io", []):
                for k in ("rect_um",):
                    q = d[k]
                    d[k] = [round(q[0] + dxx, 4), round(q[1] + dyy, 4), round(q[2] + dxx, 4), round(q[3] + dyy, 4)]
                if "bumps" in d:
                    q = d["bumps"]["rect_um"]
                    d["bumps"]["rect_um"] = [round(q[0] + dxx, 4), round(q[1] + dyy, 4), round(q[2] + dxx, 4),
                                             round(q[3] + dyy, 4)]
        if abs(dxx) > 1e-3 or abs(dyy) > 1e-3:
            moved_io.append(f"{wdw['name']} {dxx:+g},{dyy:+g}")
    # NE die-edge windows = MY images of their NW twins (B2n's NE_io window sat 316 um off the shoreline because its
    # PHY core was not mirrored; B2o mirrors the NE_io contents, place_contents)
    Wd = plan["die"]["outline_um"][0]
    byname = {w["name"]: w for w in plan["die"].get("io", [])}
    pgd = {n: d for d in plan["die"].get("pg", {}).get("domains", []) for n in d.get("io", [])}

    def mrect(r):
        return [round(Wd - r[2], 4), r[1], round(Wd - r[0], 4), r[3]]
    for wdw in plan["die"].get("io", []):
        if not wdw["part"].startswith("NE_"):
            continue
        tw = next((x for x in plan["die"]["io"] if x["part"] == mir(wdw["part"]) and x["iface"] == wdw["iface"]), None)
        if tw is None or P1.parts[wdw["part"]]["type"] not in IO_TYPES:
            continue
        wdw["rect_um"] = mrect(tw["rect_um"])
        wdw["sites"] = tw["sites"]
        wdw["basis"] = re.sub(r"shoreline \d+ um", "shoreline 0 um (B2o: MY image of " + tw["name"] + ")", wdw["basis"])
        if wdw["name"] in pgd and tw["name"] in pgd:
            d, dt = pgd[wdw["name"]], pgd[tw["name"]]
            d["rect_um"] = mrect(dt["rect_um"])
            d["bumps"]["rect_um"] = mrect(dt["bumps"]["rect_um"])
        moved_io.append(f"{wdw['name']} = MY({tw['name']})")
    log.append(f"outlines: {len(changed)} types changed ({', '.join(sorted(changed))}); io windows moved: "
               f"{'; '.join(moved_io)}")
    return changed


# ------------------------------------------------------------------------------------------------ 2. lanes
def reroute(plan, log, iters=60):
    P = S.Plan(plan)
    T = plan["partition_types"]
    R, adj = B._adjacency(P, minc=60.0)
    hard = {n for n in P.parts if T[P.parts[n]["type"]].get("hard")}
    # the hub is the star: its perimeter carries its own 50+ kbit, never transit (B2n had 1 slot through it)
    noxit = {n for n in P.parts if P.parts[n]["type"] in NO_TRANSIT}
    ports = {p["id"]: p for p in plan["ports"]}
    lanes = {l["id"]: l for l in plan["lanes"]}

    def mid(a, b):
        f, lo, hi = adj[a][b]
        x0, y0, x1, y1 = R[a]
        c = 0.5 * (lo + hi)
        return dict(N=(c, y1), S=(c, y0), E=(x1, c), W=(x0, c))[f]

    def cen(n):
        x0, y0, x1, y1 = R[n]
        return (0.5 * (x0 + x1), 0.5 * (y0 + y1))

    def md(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])

    def ext(n, d):
        x0, y0, x1, y1 = R[n]
        return (y1 - y0) if d == "H" else (x1 - x0)

    def tdirs(fi, fo):
        if fi in "EW" and fo in "EW":
            return (("H", 1.0),)
        if fi in "NS" and fo in "NS":
            return (("V", 1.0),)
        return (("H", 1.0), ("V", 1.0))
    jobs = []
    for lid, L in lanes.items():
        if lid.endswith("m") and lid[:-1] in lanes:
            continue
        p0, p1 = ports[L["ports"][0]], ports[L["ports"][-1]]
        a, b = p0["src"]["part"], p1["dst"]["part"]
        w = int(p0["width"])
        hasm = (lid + "m") in lanes
        role = "die" if (single(a) and single(b)) else ("pri" if hasm else "solo")
        role = role + ("+m" if hasm else "")
        if hasm:
            q0, q1 = ports[lanes[lid + "m"]["ports"][0]], ports[lanes[lid + "m"]["ports"][-1]]
            assert (q0["src"]["part"], q1["dst"]["part"]) == (mir(a), mir(b)), f"{lid}m is not the mirror of {lid}"
        jobs.append((lid, a, b, w, role, p0["kind"]))
    jobs.sort(key=lambda j: (-j[3], j[0]))
    hist = defaultdict(float)

    def route_all():
        use = defaultdict(float)
        tuse = defaultdict(float)

        def ecost(a, b):
            k = tuple(sorted((a, b)))
            f, lo, hi = adj[a][b]
            cap = max(hi - lo - 4.0, 1.0) * FACE_CAP
            x = use[k] / cap
            return 600.0 * x * x + (3000.0 if x > 0.9 else 0.0) + (30000.0 * (x - 1.0) if x > 1.0 else 0.0) + hist[("e", k)]

        def tcost(n, fi, fo):
            c = 0.0
            for d, _f in tdirs(fi, fo):
                cap = ext(n, d) * FT_CAP
                x = tuse[(n, d)] / cap
                c += 600.0 * x * x + (3000.0 if x > 0.9 else 0.0) + (30000.0 * (x - 1.0) if x > 1.0 else 0.0) + hist[("t", n, d)]
            return c

        out = {}
        for lid, a, b, w, role, kind in jobs:
            blk = set(hard) - {a, b}
            if role.startswith("die"):
                blk |= {n for n in P.parts if not single(n)}
            # Dijkstra over (node, entry face); state cost includes the in-partition leg length
            pq = [(md(cen(a), cen(a)) * 0.0, 0, a, None, (a,))]
            best = {}
            got = None
            cnt = 0
            while pq:
                c, _, n, fi, path = heapq.heappop(pq)
                if n == b:
                    got = path
                    break
                key = (n, fi)
                if key in best:
                    continue
                best[key] = c
                here = cen(n) if fi is None else mid(path[-2], n)
                for m in adj[n]:
                    if m in path or (m in blk) or (m != b and (m in hard or m in noxit)):
                        continue
                    fo = adj[n][m][0]
                    if fi is not None and fo == fi:          # no U-turn (in face == out face)
                        continue
                    if fi is not None and n != a:
                        tc = tcost(n, fi, fo) * (w + 1) / 1000.0
                    else:
                        tc = 0.0
                    pm = mid(n, m)
                    leg = md(here, pm) * (0.5 if fi is None else 1.0)
                    nc = c + leg + HOP_UM + tc + ecost(n, m) * (w + 1) / 1000.0
                    if m == b:
                        nc += 0.5 * md(pm, cen(b))
                    cnt += 1
                    heapq.heappush(pq, (nc, cnt, m, OPPF_[fo], path + (m,)))
            if got is None:
                raise SystemExit(f"reroute: no path {lid} {a}->{b} ({role})")
            out[lid] = got
            paths = [got] + ([tuple(mir(x) for x in got)] if role.endswith("+m") else [])
            for pth in paths:
                for x, y in zip(pth, pth[1:]):
                    assert y in adj[x], f"mirror path broken {pth}"
                    use[tuple(sorted((x, y)))] += w + 1
                for h in range(1, len(pth) - 1):
                    fi = OPPF_[adj[pth[h - 1]][pth[h]][0]]
                    fo = adj[pth[h]][pth[h + 1]][0]
                    for d, f_ in tdirs(fi, fo):
                        tuse[(pth[h], d)] += (w + 1) * f_
        return out, use, tuse

    best = None
    for it in range(iters):
        out, use, tuse = route_all()
        exc = sum(max(0.0, v - max(adj[k[0]][k[1]][2] - adj[k[0]][k[1]][1] - 4.0, 1.0) * FACE_CAP) for k, v in use.items()) + \
            sum(max(0.0, v - ext(n, d) * FT_CAP) for (n, d), v in tuse.items())
        if best is None or exc < best[0]:
            best = (exc, out, use, tuse, it)
        over = 0
        for k, v in use.items():
            f, lo, hi = adj[k[0]][k[1]]
            cap = max(hi - lo - 4.0, 1.0) * FACE_CAP
            if v > cap:
                hist[("e", k)] += 2000.0 * (v / cap - 1.0) + 300.0
                over += 1
        for (n, d), v in tuse.items():
            cap = ext(n, d) * FT_CAP
            if v > cap:
                hist[("t", n, d)] += 2000.0 * (v / cap - 1.0) + 300.0
                over += 1
        if not over:
            break
    exc, out, use, tuse, bit = best
    worst_e = sorted(((v / (max(adj[k[0]][k[1]][2] - adj[k[0]][k[1]][1] - 4.0, 1.0) * FACE_CAP), k, int(v))
                      for k, v in use.items()), reverse=True)[:6]
    worst_t = sorted(((v / (ext(n, d) * FT_CAP), n, d, int(v)) for (n, d), v in tuse.items()), reverse=True)[:6]
    # ---- emit ports / slots
    for t in T.values():
        if "ft_slots" in t:
            t["ft_slots"] = []
    newports = []
    for lid, a, b, w, role, kind in jobs:
        got = out[lid]
        pths = [(lid, got, 0)] + ([(lid + "m", tuple(mir(x) for x in got), 1)] if role.endswith("+m") else [])
        base = int(lid[1:])
        for lid_, pth, mi in pths:
            L = lanes[lid_]
            oldp = [ports[q] for q in L["ports"]]
            sb0, db1 = oldp[0]["src"]["bus"], oldp[-1]["dst"]["bus"]

            def bn(part, nm):
                return nm if (not single(part) or not mi) else nm.replace(f"L{base}", f"L{base}m", 1)
            pids = []
            for h in range(len(pth) - 1):
                x, y = pth[h], pth[h + 1]
                face, lo, hi = adj[x][y]
                sb = sb0 if h == 0 else bn(x, f"L{base}x{h}_o")
                db = db1 if h == len(pth) - 2 else bn(y, f"L{base}x{h + 1}_i")
                n = w + 1
                Lw = max(n / B.PIN_DENS + 0.5, B.MIN_WIN)
                # desired window centre: toward the lane's far end, clipped into the contact
                tgt = (0.5 * (R[pth[-1]][0] + R[pth[-1]][2]), 0.5 * (R[pth[-1]][1] + R[pth[-1]][3])) if h else \
                    (0.5 * (R[pth[-1]][0] + R[pth[-1]][2]), 0.5 * (R[pth[-1]][1] + R[pth[-1]][3]))
                c = tgt[0] if face in "NS" else tgt[1]
                c = min(max(c, lo + Lw / 2 + 1.0), hi - Lw / 2 - 1.0)
                pr = dict(id=f"{lid_}_{h}", src=dict(part=x, bus=sb), dst=dict(part=y, bus=db), width=w, kind=kind,
                          face=face, layers=list(B.FACE_LAYERS[face]),
                          window_um=[B.snap(c - Lw / 2), B.snap(c + Lw / 2)])
                if mi and face in "NS":
                    pr["order"] = "lsb_high"
                newports.append(pr)
                pids.append(pr["id"])
            for h in range(1, len(pth) - 1):
                p = pth[h]
                nm = f"L{base}x{h}" if not (single(p) and mi) else f"L{base}mx{h}"
                t = T[P.parts[p]["type"]]
                sl = t.setdefault("ft_slots", [])
                tf = {P.die_face(p, g): g for g in "NSEW"}
                fin = tf[OPPF_[adj[pth[h - 1]][p][0]]]
                fout = tf[adj[p][pth[h + 1]][0]]
                ex = next((s for s in sl if s["name"] == nm), None)
                if ex:
                    assert (ex["in_face"], ex["out_face"], ex["width"]) == (fin, fout, w), f"slot {nm} in {t['module']} differs"
                else:
                    sl.append(dict(name=nm, in_face=fin, out_face=fout, width=w, stations=1))
            L["ports"] = pids
            L["note"] = f"{pth[0]}->{pth[-1]} {kind}" + (" (mirror)" if mi else "") + " (B2o re-route)"
    plan["ports"] = newports
    for t in T.values():
        if t.get("ft_slots") == [] and not t.get("hard"):
            pass
    hops = [len(out[j[0]]) - 1 for j in jobs]
    log.append(f"re-route: {len(jobs)} primaries ({sum(1 for j in jobs if j[4].endswith('+m'))} mirrored) on the new abutment "
               f"graph, PathFinder best of {it + 1} rounds = round {bit + 1} (overflow {exc:.0f} pin-equivalents); hops mean {sum(hops) / len(hops):.2f} max {max(hops)}; worst face "
               + ", ".join(f"{k[0]}|{k[1]} {r:.2f}" for r, k, _ in worst_e[:3]) + "; worst transit "
               + ", ".join(f"{n}.{d} {r:.2f}" for r, n, d, _ in worst_t[:3]))
    return out, worst_e, worst_t


OPPF_ = {"E": "W", "W": "E", "N": "S", "S": "N"}
NO_TRANSIT = ("q_hub",)


# ------------------------------------------------------------------------------------------------ 3. lane delta
def lane_delta(plan, log, path=INP / "lane_delta.json"):
    if not path.exists():
        return []
    D = json.loads(path.read_text())
    T = plan["partition_types"]
    P = S.Plan(plan)
    ports = {p["id"]: p for p in plan["ports"]}
    lanes = {l["id"]: l for l in plan["lanes"]}
    rows = []
    for e in D.get("widen", []):
        for lid, w in zip(e["lanes"], e["width"]):
            for x in (lid, lid + "m"):
                if x not in lanes:
                    continue
                L = lanes[x]
                w0 = int(ports[L["ports"][0]]["width"])
                if w <= w0:
                    continue
                for pid in L["ports"]:
                    ports[pid]["width"] = w
                p0, p1 = ports[L["ports"][0]], ports[L["ports"][-1]]
                for part, bus in ((p0["src"]["part"], p0["src"]["bus"]), (p1["dst"]["part"], p1["dst"]["bus"])):
                    next(b for b in T[P.parts[part]["type"]]["buses"] if b["name"] == bus)["width"] = w
                for part, sn in B._lane_slots(P, x):
                    next(s for s in T[P.parts[part]["type"]]["ft_slots"] if s["name"] == sn)["width"] = w
                rows.append(f"{x} {w0}->{w} ({len(L['ports'])} hop{'s' if len(L['ports']) > 1 else ''})")
    log.append(f"lane delta ({path.name}): " + "; ".join(rows) + f" -- {D.get('why', '')}")
    return rows


# ------------------------------------------------------------------------------------------------ 5. contents
ORIENTS = ("R0", "MX", "MY", "R180")
NRM = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))


def opt(o, x, y, cw, ch):
    """core-frame point -> placed-core offset for a hard-core orient (MX flips y, MY flips x, R180 both)."""
    return (cw - x if o in ("MY", "R180") else x, ch - y if o in ("MX", "R180") else y)


def oface(o, f):
    if o in ("MX", "R180") and f in "NS":
        f = OPPF_[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPPF_[f]
    return f


def place_flow2(items, W, H, attract, band=LAT, chan=LAT, step=None, passes=4, ocore=None, face_fn=None,
                total_fn=None, eject_rounds=10, eject_max=30):
    """cores_b2.place_flow with PIN-AWARE attraction (GEOM face rule): attract {key: [(weight, target, (ox, oy))]},
    target = a fixed type-frame point or another item key (its centre); (ox, oy) = the centroid of the port's pins in
    the item frame, so the cost is the distance from the PINS (not the item centre) to the partner and a core whose
    port sits on its N face lands below its partner.  8.64 lattice, >= band from the faces, >= chan between items."""
    import numpy as np
    dims = {k: (CB.snap(w), CB.snap(h)) for k, w, h in items}
    if step is None:
        step = max(LAT, CB.snap(max(W, H) / 140))
    pos, cen, ori = {}, {}, {}
    ocore = ocore or {}

    def tpoints(k):
        out = []
        for wgt, p, off in attract.get(k, ()):
            if isinstance(p, str):
                if p not in cen:
                    continue
                p = cen[p]
            out.append((wgt, p, off))
        return out

    def place(k, ignore=False, fine=False):
        ws, hs = dims[k]
        st = LAT * 2 if fine else step
        xs = np.arange(band, W - band - ws + 1e-6, st)
        ys = np.arange(band, H - band - hs + 1e-6, st)
        xs = np.unique(np.append(xs, math.floor((W - band - ws) / LAT + 1e-9) * LAT))
        ys = np.unique(np.append(ys, math.floor((H - band - hs) / LAT + 1e-9) * LAT))
        xs = np.ceil(xs / LAT - 1e-9) * LAT
        ys = np.ceil(ys / LAT - 1e-9) * LAT
        xs = xs[(xs >= band - 1e-6) & (xs + ws <= W - band + 1e-6)]
        ys = ys[(ys >= band - 1e-6) & (ys + hs <= H - band + 1e-6)]
        if not len(xs) or not len(ys):
            return False
        X, Y = np.meshgrid(xs, ys)
        X, Y = X.ravel(), Y.ravel()
        ok = np.ones(X.shape, bool)
        for q, (rx, ry) in pos.items():
            if q == k or ignore:
                continue
            rw, rh = dims[q]
            ok &= ~((X < rx + rw + chan - 1e-6) & (rx < X + ws + chan - 1e-6) & (Y < ry + rh + chan - 1e-6)
                    & (ry < Y + hs + chan - 1e-6))
        if not ok.any():
            return False
        tp = tpoints(k)
        best_o = "R0"
        if tp:
            cost = None
            for o in (ORIENTS if k in ocore else ("R0",)):
                cw, ch = ocore.get(k, (ws, hs))
                cst = sum(wg * (np.abs(X + opt(o, off[0], off[1], cw, ch)[0] - p[0])
                                + np.abs(Y + opt(o, off[0], off[1], cw, ch)[1] - p[1])) for wg, p, off in tp)
                if face_fn is not None:
                    cst = cst + 1e9 * face_fn(k, X + ws / 2, Y + hs / 2, o, cen)
                if cost is None:
                    cost, oarr = cst, np.zeros(X.shape, int)
                else:
                    better = cst < cost - 1e-6
                    cost = np.where(better, cst, cost)
                    oarr = np.where(better, ORIENTS.index(o), oarr)
        else:
            near = [cen[q] for q in cen]
            cost = (sum(np.abs(X + ws / 2 - c[0]) + np.abs(Y + hs / 2 - c[1]) for c in near) if near
                    else Y * W + X)
            if face_fn is not None:
                cost = cost + 1e9 * face_fn(k, X + ws / 2, Y + hs / 2, "R0", cen)
        cost = np.where(ok, cost, np.inf)
        i = int(np.argmin(cost))
        if tp:
            best_o = ORIENTS[int(oarr[i])]
        if ignore:
            return (round(float(X[i]), 4), round(float(Y[i]), 4)), best_o, float(cost[i])
        ori[k] = best_o
        ORI_CUR[k] = best_o
        pos[k] = (round(float(X[i]), 4), round(float(Y[i]), 4))
        cen[k] = (pos[k][0] + ws / 2, pos[k][1] + hs / 2)
        return True

    tot = {k: sum(a[0] for a in attract.get(k, ())) for k, _, _ in items}
    order = sorted(dims, key=lambda k: (tot[k] == 0, -(dims[k][0] * dims[k][1]) ** 0.5 * (1 + tot[k]) ** 0.25, k))
    for k in order:
        if not place(k):
            return None
    for _ in range(passes):
        for k in order:
            old = pos.pop(k)
            cen.pop(k)
            oo = ori.get(k, "R0")
            if not place(k):
                pos[k] = old
                ori[k] = oo
                cen[k] = (old[0] + dims[k][0] / 2, old[1] + dims[k][1] / 2)
    # eject phase: a core whose ports still face away moves to its best spot ignoring the others, the (few) items it
    # lands on are re-placed; kept only when the exact type-wide count of away-facing ports drops
    if face_fn is not None and total_fn is not None:
        cur = total_fn(pos, ori)
        for _ in range(eject_rounds):
            if not cur:
                break
            badk = [k for k in order if float(face_fn(k, np.array([cen[k][0]]), np.array([cen[k][1]]),
                                                      ori.get(k, "R0"), cen)[0]) > 0]
            if os.environ.get("B2O_DEBUG"):
                print("eject", cur, badk[:12], file=sys.stderr)
            if not badk:
                break
            moved_any = False
            for k in badk:
                snap_ = (dict(pos), dict(cen), dict(ori), dict(ORI_CUR))
                spot = place(k, ignore=True)
                if not spot:
                    continue
                (sx, sy), so, _ = spot
                ws, hs = dims[k]
                hit = [q for q, (rx, ry) in pos.items() if q != k and sx < rx + dims[q][0] + chan - 1e-6 and
                       rx < sx + ws + chan - 1e-6 and sy < ry + dims[q][1] + chan - 1e-6 and ry < sy + hs + chan - 1e-6]
                if len(hit) > eject_max:
                    continue
                for q in hit:
                    pos.pop(q)
                    cen.pop(q)
                pos[k] = (sx, sy)
                cen[k] = (sx + ws / 2, sy + hs / 2)
                ori[k] = so
                ORI_CUR[k] = so
                okp = all(place(q, fine=True) for q in sorted(hit, key=lambda q: -dims[q][0] * dims[q][1]))
                v = total_fn(pos, ori) if okp else None
                if os.environ.get("B2O_DEBUG"):
                    print("  try", k, (sx, sy), so, "hit", len(hit), "ok", okp, v, file=sys.stderr)
                if okp and v < cur:
                    cur = v
                    moved_any = True
                else:
                    pos.clear(); pos.update(snap_[0]); cen.clear(); cen.update(snap_[1])
                    ori.clear(); ori.update(snap_[2]); ORI_CUR.clear(); ORI_CUR.update(snap_[3])
            if not moved_any:
                break
    return pos, ori


def type_links(t, side):
    """check.py core_faces connectivity of one type: {hard core: {port: [(kind, name)]}} from buses[].leaf,
    contents[].bind (bus / epoch / net) and the core_conns.json sidecar (a core matches a leaf equal to it or split
    from it), plus the net -> leaf ends table."""
    conns, net_ends = defaultdict(list), defaultdict(set)
    for b in t.get("buses", []):
        if b.get("leaf") and "." in b["leaf"]:
            li, lp = b["leaf"].split(".", 1)
            conns[(li, lp)].append(("bus", b["name"]))
    for c in t.get("contents", []):
        for lp, v in c.get("bind", {}).items():
            k, _, nm = v.partition(":")
            if k in ("bus", "epoch") and nm:
                conns[(c["inst"], lp)].append(("bus", nm))
            elif k == "net" and nm:
                conns[(c["inst"], lp)].append(("net", nm))
                net_ends[nm].add(c["inst"])
    for ci, ports in side.items():
        for lp, lst in ports.items():
            for v in lst:
                k, _, nm = v.partition(":")
                conns[(ci, lp)].append((k, nm))
    out = {}
    for h in t.get("hard_cores", []) or []:
        ci = h["inst"]
        m = defaultdict(list)
        for (li, lp), tg in conns.items():
            if li == ci or ci.startswith(li + "_"):
                m[lp].extend(tg)
        if m:
            out[ci] = dict(m)
    return out, net_ends


def core_face_score(ci, o, geo, pfaces, poff, links, bt, cent=None, net_ends=None, WH=None):
    """check.py core_faces rule for one core at geo[ci] in orient o: (ports away (mean cos < -0.1), -sum mean cos).
    Partners as check.py: cores / leaves = centres, nets = the other leaf ends, faces; buses = the face window when
    the pin centroid is within HOP of it (longer bus links get R3-INTERNAL stations whose last register sits beside
    the pins, which always faces)."""
    x0, y0, w, h = geo[ci]
    cx, cy = x0 + w / 2, y0 + h / 2
    cent = cent or {}
    bad, tot = 0, 0.0
    for port, tg in links.get(ci, {}).items():
        fc = pfaces.get((ci, port))
        if not fc:
            continue
        ax, ay = opt(o, poff[(ci, port)][0], poff[(ci, port)][1], w, h)
        ax, ay = x0 + ax, y0 + ay
        pts = []
        for kd, nm in tg:
            if kd == "bus":
                if nm in bt:
                    tx, ty = bt[nm][1]
                    if abs(tx - ax) + abs(ty - ay) <= B.HOP:
                        pts.append((tx, ty))
            elif kd == "net":
                pts += [cent_(oi, geo, cent) for oi in sorted((net_ends or {}).get(nm, ()))
                        if oi != ci and not ci.startswith(oi + "_") and cent_(oi, geo, cent)]
            elif kd in ("core", "leaf") and nm != ci and cent_(nm, geo, cent):
                pts.append(cent_(nm, geo, cent))
            elif kd == "face" and nm in NRM and WH:
                pts.append(dict(N=(cx, WH[1]), S=(cx, 0.0), E=(WH[0], cy), W=(0.0, cy))[nm])
        dirs = []
        for tx, ty in pts:
            d = math.hypot(tx - cx, ty - cy)
            if d > 1e-6:
                dirs.append(((tx - cx) / d, (ty - cy) / d))
        if not dirs:
            continue
        cs = [max(NRM[oface(o, f)][0] * ux + NRM[oface(o, f)][1] * uy for ux, uy in dirs) for f in fc]
        m = sum(cs) / len(cs)
        bad += m < -0.1
        tot += m
    return bad, -tot


def make_face_fn(links, net_ends, pfaces, poff, bt, dims, split, WH):
    """vectorised core_faces penalty for place_flow2: number of away-facing ports (check.py rule) of core k placed with
    centre arrays (X, Y) in orient o, given the current centres of the placed items, plus the ports of placed cores
    whose partner is k (their mean cos changes with k's position)."""
    import numpy as np
    fcount = {key: collections.Counter(v) for key, v in pfaces.items()}
    rev = defaultdict(list)
    for j, pm in links.items():
        for port, tg in pm.items():
            for kd, nm in tg:
                if kd in ("core", "leaf"):
                    rev[nm].append((j, port))
                    for sp in split:
                        pass
    def partners(ci, port, cen, cx=None, cy=None):
        pts = []
        for kd, nm in links[ci][port]:
            if kd == "bus":
                if nm in bt:
                    pts.append(("bus", bt[nm][1]))
            elif kd == "net":
                pts += [("pt", cen[oi]) for oi in sorted(net_ends.get(nm, ())) if oi != ci and not ci.startswith(oi + "_")
                        and oi in cen]
            elif kd in ("core", "leaf") and nm != ci and nm in cen:
                pts.append(("pt", cen[nm]))
            elif kd == "face" and nm in NRM:
                pts.append(("face", nm))
        return pts

    def mean_cos(fc, ux, uy):
        n = sum(fc.values())
        acc = 0.0
        for f, c in fc.items():
            nx, ny = NRM[f]
            acc = acc + c * np.max(np.stack([nx * a + ny * b for a, b in zip(ux, uy)]), axis=0)
        return acc / n

    def fn(k, X, Y, o, cen):
        bad = np.zeros(X.shape)
        w, h = dims[k]
        for port in links.get(k, {}):
            if (k, port) not in fcount:
                continue
            fc = collections.Counter({oface(o, f): c for f, c in fcount[(k, port)].items()})
            fc2 = collections.Counter()
            for f, c in fcount[(k, port)].items():
                fc2[oface(o, f)] += c
            ax_, ay_ = opt(o, poff[(k, port)][0], poff[(k, port)][1], w, h)
            ux, uy, masks = [], [], []
            for kind, p in partners(k, port, cen):
                if kind == "face":
                    tx = np.where(p in "NS", X, WH[0] if p == "E" else 0.0)
                    ty = np.where(p in "EW", Y, WH[1] if p == "N" else 0.0)
                else:
                    tx, ty = np.full(X.shape, p[0]), np.full(X.shape, p[1])
                dx, dy = tx - X, ty - Y
                d = np.hypot(dx, dy) + 1e-9
                a, b = dx / d, dy / d
                if kind == "bus":       # beyond HOP an internal station beside the pins carries it: always faces
                    far = (np.abs(p[0] - (X - w / 2 + ax_)) + np.abs(p[1] - (Y - h / 2 + ay_))) > B.HOP
                    a = np.where(far, np.nan, a)
                    b = np.where(far, np.nan, b)
                ux.append(a)
                uy.append(b)
            if not ux:
                continue
            nx_ = [np.nan_to_num(a, nan=-9.0) for a in ux]
            ny_ = [np.nan_to_num(b, nan=0.0) for b in uy]
            # partners that are all 'far bus' -> port unchecked
            valid = np.any(np.stack([~np.isnan(a) for a in ux]), axis=0)
            n = sum(fc2.values())
            acc = 0.0
            for f, c in fc2.items():
                nx, ny = NRM[f]
                vals = np.stack([np.where(np.isnan(a), -9.0, nx * np.nan_to_num(a) + ny * np.nan_to_num(b))
                                 for a, b in zip(ux, uy)])
                acc = acc + c * np.max(vals, axis=0)
            m = acc / n
            bad += (valid & (m < -0.1)).astype(float)
        for j, port in rev.get(k, ()):
            if j not in cen or (j, port) not in fcount or j == k:
                continue
            jo = ORI_CUR.get(j, "R0")
            fc2 = collections.Counter()
            for f, c in fcount[(j, port)].items():
                fc2[oface(jo, f)] += c
            cx, cy = cen[j]
            others = [p for kind, p in partners(j, port, {q: v for q, v in cen.items() if q != k})
                      if kind == "pt" or (kind == "bus" and abs(p[0] - cx) + abs(p[1] - cy) <= B.HOP)]
            ux = [np.full(X.shape, (p[0] - cx) / (math.hypot(p[0] - cx, p[1] - cy) + 1e-9)) for p in others]
            uy = [np.full(X.shape, (p[1] - cy) / (math.hypot(p[0] - cx, p[1] - cy) + 1e-9)) for p in others]
            d = np.hypot(X - cx, Y - cy) + 1e-9
            ux.append((X - cx) / d)
            uy.append((Y - cy) / d)
            n = sum(fc2.values())
            acc = 0.0
            for f, c in fc2.items():
                nx, ny = NRM[f]
                acc = acc + c * np.max(np.stack([nx * a + ny * b for a, b in zip(ux, uy)]), axis=0)
            bad += ((acc / n) < -0.1).astype(float)
        return bad
    return fn


ORI_CUR = {}
OLD_WH = {}             # type -> B2n outline (set by main from the source plan)


def flip_track_offset(P, h, pins, insts):
    """sub-lattice track_offset_um that puts every pin of a flipped hard core back on its plan track (a flip maps
    x -> w - x, so a core width that is not a multiple of the track pitches moves its pins between tracks); checked
    in the type frame and in every instance frame (check.py hard_cores rule).  Returns [dx, dy] or None."""
    o = h.get("orient", "R0")
    cw, ch = h["outline_um"]
    ox, oy = h["origin_um"]
    byl = defaultdict(list)
    for q in pins:
        if q["layer"] in P.layers and q["layer"] != "M1" and len(byl[q["layer"]]) < 64:
            byl[q["layer"]].append(q)

    def ok(axis, d):
        for ln, qs in byl.items():
            L = P.layers[ln]
            if (L["dir"] == "V") != (axis == "x"):
                continue
            for q in qs:
                tx, ty = opt(o, q["x"], q["y"], cw, ch)
                tx, ty = ox + tx + (d if axis == "x" else 0.0), oy + ty + (d if axis == "y" else 0.0)
                frames = [(tx, ty)] + [P.to_die(pi, (tx, ty)) for pi in insts
                                       if ln not in CK.MIRROR_SKIP or P.parts[pi].get("orient", "R0") == "R0"]
                for fx, fy in frames:
                    if not CK.on_track(fx if axis == "x" else fy, L):
                        return False
        return True
    steps = sorted({round(i * 0.004, 4) * sg for i in range(0, 49) for sg in (1, -1)}, key=lambda v: (abs(v), v))
    dx = next((d for d in steps if ok("x", d)), None)
    dy = next((d for d in steps if ok("y", d)), None)
    return None if dx is None or dy is None else [round(dx, 4) + 0.0, round(dy, 4) + 0.0]


def swap_opt(pos, ori, dims, insts, split, W, H, pfaces, poff, links, bt, net_ends, band=LAT, chan=LAT, rounds=4):
    """local search after placement: pairwise position swaps of items (hard cores and soft leaves) that are legal
    (inside the band, >= chan apart) and lower the number of away-facing core ports (check.py core_faces), with the
    orients of the swapped cores re-chosen.  Returns (pos, ori, swaps)."""
    keys = sorted(pos)

    def geo_cent(pz):
        geo = {k: (pz[k][0], pz[k][1], dims[k][0], dims[k][1]) for k in pz if k in insts}
        cent = {k: (pz[k][0] + dims[k][0] / 2, pz[k][1] + dims[k][1] / 2) for k in pz}
        for sp in split:
            bs = [geo[i] for i in insts if i.startswith(sp + "_")]
            cent[sp] = ((min(b[0] for b in bs) + max(b[0] + b[2] for b in bs)) / 2,
                        (min(b[1] for b in bs) + max(b[1] + b[3] for b in bs)) / 2)
        return geo, cent

    def total(pz, oz):
        geo, cent = geo_cent(pz)
        return sum(core_face_score(ci, oz.get(ci, "R0"), geo, pfaces, poff, links, bt, cent=cent, net_ends=net_ends,
                                   WH=(W, H))[0] for ci in insts)

    def legal(k, x, y, pz, skip):
        w, h = dims[k]
        if x < band - 1e-6 or y < band - 1e-6 or x + w > W - band + 1e-6 or y + h > H - band + 1e-6:
            return False
        for q, (qx, qy) in pz.items():
            if q in skip:
                continue
            qw, qh = dims[q]
            if x < qx + qw + chan - 1e-6 and qx < x + w + chan - 1e-6 and y < qy + qh + chan - 1e-6 and qy < y + h + chan - 1e-6:
                return False
        return True

    def reorient(pz, oz, ks):
        geo, cent = geo_cent(pz)
        oz = dict(oz)
        for ci in ks:
            if ci in insts:
                oz[ci] = min(ORIENTS, key=lambda o: (core_face_score(ci, o, geo, pfaces, poff, links, bt, cent=cent,
                                                                     net_ends=net_ends, WH=(W, H)), ORIENTS.index(o)))
        return oz
    cur = total(pos, ori)
    nsw = 0
    for _ in range(rounds):
        if not cur:
            break
        geo, cent = geo_cent(pos)
        badc = [ci for ci in sorted(insts) if core_face_score(ci, ori.get(ci, "R0"), geo, pfaces, poff, links, bt,
                                                              cent=cent, net_ends=net_ends, WH=(W, H))[0]]
        # the failing cores and their partners
        focus = set(badc)
        for ci in badc:
            for port, tg in links.get(ci, {}).items():
                focus |= {nm for kd, nm in tg if kd in ("core", "leaf") and nm in pos}
        improved = False
        for a in sorted(focus):
            best = None
            for b in keys:
                if b == a:
                    continue
                (ax, ay), (bx, by) = pos[a], pos[b]
                # swap anchored at the lower-left corners and at the centres (different sizes)
                for na, nb in (((bx, by), (ax, ay)),
                               ((lat(bx + dims[b][0] / 2 - dims[a][0] / 2), lat(by + dims[b][1] / 2 - dims[a][1] / 2)),
                                (lat(ax + dims[a][0] / 2 - dims[b][0] / 2), lat(ay + dims[a][1] / 2 - dims[b][1] / 2)))):
                    pz = dict(pos)
                    pz[a], pz[b] = na, nb
                    if not (legal(a, *na, pz, {a, b}) and legal(b, *nb, pz, {a, b})):
                        continue
                    a_, b_ = dims[a], dims[b]
                    if (na[0] < nb[0] + b_[0] + chan - 1e-6 and nb[0] < na[0] + a_[0] + chan - 1e-6 and
                            na[1] < nb[1] + b_[1] + chan - 1e-6 and nb[1] < na[1] + a_[1] + chan - 1e-6):
                        continue
                    oz = reorient(pz, ori, [a, b])
                    v = total(pz, oz)
                    if v < cur and (best is None or v < best[0]):
                        best = (v, pz, oz)
            if best:
                cur, pos, ori = best
                nsw += 1
                improved = True
                if not cur:
                    break
        if not improved:
            break
    return pos, ori, nsw


def cent_(nm, geo, cent):
    if nm in geo:
        g = geo[nm]
        return (g[0] + g[2] / 2, g[1] + g[3] / 2)
    return cent.get(nm)


def orient_opt(geo, ori, pfaces, poff, links, bt, insts, **kw):
    """per-core orient that minimises away-facing ports (partner points are core centres / windows, independent of
    the other cores' orients, so the choice is separable)."""
    out = dict(ori)
    for ci in insts:
        out[ci] = min(ORIENTS, key=lambda o: (core_face_score(ci, o, geo, pfaces, poff, links, bt, **kw), ORIENTS.index(o) > 0,
                                              o != ori.get(ci, "R0")))
    bad = sum(core_face_score(ci, out[ci], geo, pfaces, poff, links, bt, **kw)[0] for ci in insts)
    return out, bad


def place_contents(plan, out, types, log):
    """data-flow placement of every listed soft type's hard cores + soft leaves (cores_b2.place_flow), core taps
    carried with their core, partition clock / reset tap re-sited, R3-INTERNAL stations re-derived."""
    P = S.Plan(plan)
    T = plan["partition_types"]
    conns = json.loads((out / "core_conns.json").read_text())
    rows, fails = [], []
    chosen = {}
    for tn in sorted(types):
        if os.environ.get("B2O_PROGRESS"):
            print(f"place_contents {tn}", flush=True)
        t = T[tn]
        if t.get("hard"):
            continue
        W, H = t["outline_um"]
        t_old_wh = OLD_WH.get(tn, (W, H))
        hcs = t.get("hard_cores", []) or []
        insts = {h["inst"] for h in hcs}
        split = {c["inst"] for c in t.get("contents", []) if c["inst"] not in insts and
                 any(i.startswith(c["inst"] + "_") for i in insts)}
        softs = [c for c in t.get("contents", []) if "origin_um" in c and "outline_um" in c and c["inst"] not in insts
                 and c["inst"] not in split]
        if not hcs and not softs:
            for k in ("clock", "reset"):
                if "tap_um" in t.get(k, {}):
                    t[k]["tap_um"] = [lat(W / 2), lat(H / 2)]
            continue
        fixed_io = tn in ("NW_io", "NE_io") or any(w["part"] for w in plan["die"].get("io", [])
                                                   if P.parts[w["part"]]["type"] == tn)
        items = [(h["inst"], h["outline_um"][0], h["outline_um"][1]) for h in hcs] + \
                [(c["inst"], c["outline_um"][0], c["outline_um"][1]) for c in softs]
        old = {h["inst"]: tuple(h["origin_um"]) for h in hcs}
        old.update({c["inst"]: tuple(c["origin_um"]) for c in softs})
        ori = {}
        if fixed_io:
            ow_ = OLD_WH.get(tn, (W, H))[0]
            if tn.startswith("NE_"):        # PHY at the E die edge: MY image of the B2n W-edge-relative layout
                pos = {k: (math.floor((W - old[k][0] - w) / LAT + 1e-9) * LAT, old[k][1]) for k, w, h in items}
            else:
                pos = {k: (old[k][0], old[k][1]) for k, w, h in items}
            move_digital_io(items, pos, t)
            assert all(0 <= pos[k][0] and pos[k][0] + w <= W + 1e-6 and pos[k][1] + h <= H + 1e-6 for k, w, h in items), tn
        else:
            bt = CK._bus_targets(P, tn)
            cc = conns.get(tn, {})
            pfaces, poff = {}, {}
            for h in hcs:
                try:
                    pins = json.loads((out / h["pins_file"]).read_text())
                except OSError:
                    pins = []
                cw, ch = h["outline_um"]
                grp = defaultdict(list)
                for q in pins:
                    grp[CB.base(q["name"])].append(q)
                for port, qs in grp.items():
                    pfaces[(h["inst"], port)] = [CK._core_face("R0", q["x"], q["y"], cw, ch) for q in qs]
                    poff[(h["inst"], port)] = (sum(q["x"] for q in qs) / len(qs), sum(q["y"] for q in qs) / len(qs), len(qs))
            attract = defaultdict(list)
            for ci, pmap in cc.items():
                if ci not in insts:
                    continue
                for port, tg in pmap.items():
                    if (ci, port) not in poff:
                        continue
                    ox, oy, npn = poff[(ci, port)]
                    for x in tg:
                        kd, _, nm = x.partition(":")
                        if kd == "bus" and nm in bt:
                            attract[ci].append((npn, tuple(bt[nm][1]), (ox, oy)))
                        elif kd == "core" and nm in insts:
                            attract[ci].append((npn, nm, (ox, oy)))
                            attract[nm].append((npn * 0.0 + 1e-3, ci, (0.0, 0.0)))
            dims = {k: (w, h) for k, w, h in items}
            ocore = {h["inst"]: tuple(h["outline_um"]) for h in hcs}
            links, net_ends = type_links(t, cc)
            cands = []
            for band, chan in ((LAT, LAT), (0.0, LAT), (0.0, 0.0)):
                pz = None
                ORI_CUR.clear()
                ffn = make_face_fn(links, net_ends, pfaces, poff, bt, dims, split, (W, H))

                def tfn(pz, oz):
                    geo = {k: (pz[k][0], pz[k][1], dims[k][0], dims[k][1]) for k in pz if k in insts}
                    cent = {k: (pz[k][0] + dims[k][0] / 2, pz[k][1] + dims[k][1] / 2) for k in pz}
                    for sp in split:
                        bs = [geo[i] for i in insts if i.startswith(sp + "_")]
                        cent[sp] = ((min(b[0] for b in bs) + max(b[0] + b[2] for b in bs)) / 2,
                                    (min(b[1] for b in bs) + max(b[1] + b[3] for b in bs)) / 2)
                    return sum(core_face_score(ci, oz.get(ci, "R0"), geo, pfaces, poff, links, bt, cent=cent,
                                               net_ends=net_ends, WH=(W, H))[0] for ci in insts)
                for step in (None, LAT * 2):
                    pz = place_flow2(items, W, H, attract, band=band, chan=chan, step=step, ocore=ocore, face_fn=ffn,
                                     total_fn=tfn)
                    if pz:
                        break
                if pz:
                    cands.append(("flow", pz[0], pz[1]))
                    break
            # warped B2n: every item pulled to its B2n centre mapped linearly into the new outline (keeps the
            # left/right and above/below order the frozen pins were placed for), then legalised by the same flow
            ow_, oh_ = t_old_wh
            for wf_ in ((0.5, 1.0, 0.25, 2.0) if (abs(ow_ - W) > 1e-3 or abs(oh_ - H) > 1e-3) and len(items) > 3 else ()):
                if any(c_[0] == "warp" and c_[3] == 0 for c_ in cands if len(c_) > 3):
                    break
                att2 = defaultdict(list, {k: list(v) for k, v in attract.items()})
                for k, w_, h_ in items:
                    wt_ = max(1.0, wf_ * sum(a[0] for a in attract.get(k, ())))
                    tx_ = (old[k][0] + w_ / 2) * W / ow_
                    ty_ = (old[k][1] + h_ / 2) * H / oh_
                    att2[k].append((wt_, (tx_, ty_), (w_ / 2, h_ / 2)))
                pz = None
                for band_, chan_ in ((LAT, LAT), (0.0, LAT), (0.0, 0.0)):
                    for step in (None, LAT * 2):
                        ORI_CUR.clear()
                        pz = place_flow2(items, W, H, att2, band=band_, chan=chan_, step=step, ocore=ocore,
                                         face_fn=ffn, total_fn=tfn)
                        if pz:
                            break
                    if pz:
                        cands.append(("warp", pz[0], pz[1], tfn(pz[0], pz[1])))
                        break
            # rigid B2n cluster (keeps the relative core geometry the pins were placed for), best bus-distance offset
            bx0 = min(old[k][0] for k in old); by0 = min(old[k][1] for k in old)
            bx1 = max(old[k][0] + dims[k][0] for k in old); by1 = max(old[k][1] + dims[k][1] for k in old)
            if bx1 - bx0 <= W + 1e-6 and by1 - by0 <= H + 1e-6:
                mx_, my_ = (LAT if bx1 - bx0 <= W - 2 * LAT + 1e-6 else 0.0), (LAT if by1 - by0 <= H - 2 * LAT + 1e-6 else 0.0)
                best = None
                for i in range(max(1, int((W - (bx1 - bx0) - 2 * mx_ + 1e-6) // LAT) + 1)):
                    for j in range(max(1, int((H - (by1 - by0) - 2 * my_ + 1e-6) // LAT) + 1)):
                        ox_, oy_ = mx_ + i * LAT - bx0, my_ + j * LAT - by0
                        c_ = sum(a[0] * (abs(old[k][0] + ox_ + a[2][0] - a[1][0]) + abs(old[k][1] + oy_ + a[2][1] - a[1][1]))
                                 for k in attract for a in attract[k] if not isinstance(a[1], str))
                        if best is None or c_ < best[0]:
                            best = (c_, ox_, oy_)
                _, ox_, oy_ = best
                cands.append(("rigid", {k: (round(old[k][0] + ox_, 4), round(old[k][1] + oy_, 4)) for k in old},
                              {k: "R0" for k in insts}))
            for nm_, fn in (("pack", CB.pack), ("columns", CB.pack_columns)):
                if not cands:
                    pz = fn(items, W, H)
                    if pz:
                        cands.append((nm_, {k: (lat(v[0]), lat(v[1])) for k, v in pz.items()}, {k: "R0" for k in insts}))

            def score(c):
                pz = c[1]
                geo = {k: (pz[k][0], pz[k][1], dims[k][0], dims[k][1]) for k in pz if k in insts}
                cent = {k: (pz[k][0] + dims[k][0] / 2, pz[k][1] + dims[k][1] / 2) for k in pz}
                for sp in split:
                    bs = [geo[i] for i in insts if i.startswith(sp + "_")]
                    x0_, y0_ = min(b[0] for b in bs), min(b[1] for b in bs)
                    x1_, y1_ = max(b[0] + b[2] for b in bs), max(b[1] + b[3] for b in bs)
                    cent[sp] = ((x0_ + x1_) / 2, (y0_ + y1_) / 2)
                ori, bad = orient_opt(geo, c[2], pfaces, poff, links, bt, insts, cent=cent, net_ends=net_ends, WH=(W, H))
                cost = sum(a[0] * (abs(pz[k][0] + a[2][0] - (a[1][0] if not isinstance(a[1], str) else pz[a[1]][0] + dims[a[1]][0] / 2))
                                   + abs(pz[k][1] + a[2][1] - (a[1][1] if not isinstance(a[1], str) else pz[a[1]][1] + dims[a[1]][1] / 2)))
                           for k in attract for a in attract[k] if k in pz)
                return (bad, cost), ori
            pos = None
            if cands:
                sc = [(score(c), c) for c in cands]
                (sb, ori), c = min(sc, key=lambda z: z[0][0])
                pos = dict(c[1])
                if sb[0]:
                    pos, ori, nsw = swap_opt(pos, ori, dims, insts, split, W, H, pfaces, poff, links, bt, net_ends,
                                             band=(LAT if c[0] == "flow" else 0.0))
                    sb = (score((c[0], pos, ori))[0][0], sb[1])
                chosen[tn] = (c[0], sb[0], sum(1 for v in ori.values() if v != "R0"))
            if not pos:
                fails.append(f"{tn}: contents do not fit {W:g}x{H:g}")
                continue
        moved = {}
        for h in hcs:
            nx, ny = pos[h["inst"]]
            o0 = h.get("orient", "R0")
            assert o0 == "R0", f"{tn} {h['inst']}: B2n core already oriented {o0}"
            moved[h["inst"]] = (tuple(h["origin_um"]), (nx, ny), ori.get(h["inst"], "R0"), tuple(h["outline_um"]))
            h["origin_um"] = [round(nx, 4), round(ny, 4)]
            h["track_offset_um"] = [0.0, 0.0]
            if ori.get(h["inst"], "R0") != "R0":
                h["orient"] = ori[h["inst"]]
                pins_ = json.loads((out / h["pins_file"]).read_text())
                pins_ = pins_.get("pins", pins_) if isinstance(pins_, dict) else pins_
                to = flip_track_offset(P, h, pins_, [n for n, p_ in P.parts.items() if p_["type"] == tn])
                if to is None:
                    fails.append(f"{tn} {h['inst']}: no track offset puts the {h['orient']} pins on the plan tracks")
                else:
                    h["track_offset_um"] = to
            else:
                h.pop("orient", None)
        for c in t.get("contents", []):
            if c["inst"] in pos and "origin_um" in c:
                c["origin_um"] = [round(pos[c["inst"]][0], 4), round(pos[c["inst"]][1], 4)]
            if c["inst"] in split and "origin_um" in c:
                bs = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                       h["origin_um"][1] + h["outline_um"][1]) for h in hcs if h["inst"].startswith(c["inst"] + "_")]
                x0_, y0_ = min(b[0] for b in bs), min(b[1] for b in bs)
                c["origin_um"] = [round(x0_, 4), round(y0_, 4)]
                c["outline_um"] = [round(max(b[2] for b in bs) - x0_, 4), round(max(b[3] for b in bs) - y0_, 4)]
        taps = t.get("clock", {}).get("taps", [])
        for tp in taps:
            ci = tp["name"].partition(".")[0]
            if tp.get("kind") == "core" and ci in moved:
                (ox0, oy0), (nx, ny), o, (cw, ch) = moved[ci]
                rx, ry = opt(o, tp["xy"][0] - ox0, tp["xy"][1] - oy0, cw, ch)
                tp["xy"] = [round(nx + rx, 4), round(ny + ry, 4)]
        for tp in taps:
            if tp.get("kind") == "core":
                x, y = S.tap_clear(t, tp["xy"][0], tp["xy"][1], [tuple(o["xy"]) for o in taps if o is not tp], clear=4.32)
                tp["xy"] = [round(x, 4), round(y, 4)]
        boxes = [(h["origin_um"][0], h["origin_um"][1], h["outline_um"][0], h["outline_um"][1]) for h in hcs]
        tp = CB.free_point((W / 2, H / 2), boxes, W, H)
        tp = S.tap_clear(t, tp[0], tp[1], [tuple(o["xy"]) for o in taps], clear=4.32)
        for k in ("clock", "reset"):
            if k in t:
                t[k]["tap_um"] = [round(tp[0], 4), round(tp[1], 4)]
        rows.append(tn)
    log.append(f"contents: {len(rows)} types re-placed (pin-aware data flow vs rigid B2n cluster, fewer away-facing core "
               f"ports first, per-core orient R0/MX/MY/R180 chosen by the core_faces rule; pins / outlines unchanged): "
               + ", ".join(f"{k} {v[0]}{'' if not v[2] else ' ' + str(v[2]) + ' flipped'}{'' if not v[1] else ' AWAY ' + str(v[1])}"
                           for k, v in sorted(chosen.items())) + ")"
               + (f"; NOT FIT: {'; '.join(fails)}" if fails else ""))
    return fails


def internal_stations(plan, out, types, log):
    """R3-INTERNAL (cores_b2 rule, HOP = b2n.HOP): every core port whose partner (partition bus window or core) is
    over HOP away gets a relay chain on macro-free corridors; bus legs start at the face window."""
    P = S.Plan(plan)
    T = plan["partition_types"]
    conns = json.loads((out / "core_conns.json").read_text())
    n_e = n_r = 0
    fails = []
    for tn in sorted(types):
        if os.environ.get("B2O_PROGRESS"):
            print(f"place_contents {tn}", flush=True)
        t = T[tn]
        if t.get("hard") or not t.get("hard_cores"):
            continue
        W, H = t["outline_um"]
        hcs = t["hard_cores"]
        geo = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["outline_um"][0], h["outline_um"][1]) for h in hcs}
        boxes = list(geo.values())
        bt = CK._bus_targets(P, tn)
        router0 = CB.RelayRouter(boxes, W, H, B.HOP)
        router1 = CB.RelayRouter(boxes, W, H, B.REACH - 1.0)

        def router(a_, b_):
            try:
                return router0(a_, b_)
            except ValueError:
                return router1(a_, b_)      # narrow corridors: hops up to the 405-um reach (b2n.restation rule)
        free = (lambda p: CB.free_point(p, boxes, W, H))
        ist = []
        cc = conns.get(tn, {})
        for h in hcs:
            k = h["inst"]
            if k not in cc:
                continue
            pins = json.loads((out / h["pins_file"]).read_text())
            byp = defaultdict(list)
            fcs = defaultdict(list)
            o = h.get("orient", "R0")
            cw, ch = h["outline_um"]
            for p in pins:
                rx, ry = opt(o, p["x"], p["y"], cw, ch)
                byp[CB.base(p["name"])].append((geo[k][0] + rx, geo[k][1] + ry))
                fcs[CB.base(p["name"])].append(oface(o, CK._core_face("R0", p["x"], p["y"], cw, ch)))
            for port, tg in cc[k].items():
                if port not in byp:
                    continue
                pp = byp[port]
                A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
                for x in tg:
                    kd, _, nm = x.partition(":")
                    if kd == "bus":
                        if nm not in bt:
                            continue
                        Bp = tuple(bt[nm][1])
                    elif kd == "core" and nm in geo:
                        g2 = geo[nm]
                        Bp = (min(max(A[0], g2[0]), g2[0] + g2[2]), min(max(A[1], g2[1]), g2[1] + g2[3]))
                    else:
                        continue
                    d = abs(A[0] - Bp[0]) + abs(A[1] - Bp[1])
                    if d <= B.HOP:
                        continue
                    try:
                        if kd == "bus":
                            f_ = collections.Counter(fcs[port]).most_common(1)[0][0]
                            nc = free((A[0] + NRM[f_][0] * 4 * LAT, A[1] + NRM[f_][1] * 4 * LAT))
                            regs = router(Bp, nc) + [nc]
                            aa, bb, launch, capture = Bp, A, f"face bus {nm}", f"{k}.{port}"
                        else:
                            regs = router(A, Bp)
                            aa, bb, launch, capture = A, Bp, f"{k}.{port}", nm
                    except ValueError as ex:
                        fails.append(f"{tn} {k}.{port}->{nm}: {ex}")
                        continue
                    ist.append(dict(conn=(f"bus:{nm}" if kd == "bus" else f"{k}.{port}|{nm}"),
                                    from_um=[round(aa[0], 3), round(aa[1], 3)], to_um=[round(bb[0], 3), round(bb[1], 3)],
                                    regs_um=[[round(x_, 3), round(y_, 3)] for x_, y_ in regs], bits=len(pp),
                                    launch=launch, capture=capture,
                                    note=f"B2o R3-INTERNAL (cores_b2 rule): {d:.0f} um core link, {len(regs)} station(s), "
                                         f"hops <= {B.HOP:g} um"))
                    n_r += len(regs)
        n_e += len(ist)
        if ist:
            t["internal_stations"] = ist
        else:
            t.pop("internal_stations", None)
    log.append(f"internal stations: {n_e} core links over {B.HOP:g} um, {n_r} stations"
               + (f"; {len(fails)} unroutable: {'; '.join(fails[:4])}" if fails else ""))
    return fails


def fix_cross_hops(plan, log, lim=0.9 * 405.0):
    """partition-boundary hops: a slot whose first station had to leave a macro-blocked window (free point far from
    the face) makes the hop from the upstream slot's last station long; the upstream slot gets one more station on
    its own out-window (type frame, same for every instance of the type).  Only where a lane hop exceeds
    0.9 x 405 (check.py reach rule)."""
    added = []
    for _ in range(4):
        P = S.Plan(plan)
        todo = {}
        for lid in P.lanes:
            ln = P.lanes[lid]
            prev = P.port_point(ln["ports"][0])
            prev_x = None
            for part, slot, a, b in P.lane_crossings(lid):
                s_ = P.slot(part, slot) or {}
                st = [P.to_die(part, tuple(r)) for r in s_.get("regs_um", [])]
                if st and abs(st[0][0] - prev[0]) + abs(st[0][1] - prev[1]) > lim and prev_x is not None:
                    todo.setdefault(prev_x[:2], prev_x[2])
                if st:
                    prev = st[-1]
                    prev_x = (P.parts[part]["type"], slot, P.to_type(part, P.port_point(b)))
            end = P.port_point(ln["ports"][-1])
            if prev_x is not None and abs(end[0] - prev[0]) + abs(end[1] - prev[1]) > lim:
                todo.setdefault(prev_x[:2], prev_x[2])
        if not todo:
            break
        for (tn, sn), wp in sorted(todo.items()):
            t = plan["partition_types"][tn]
            sl = next(x for x in t["ft_slots"] if x["name"] == sn)
            w, h = t["outline_um"]
            fp = CB.free_point((min(max(wp[0], 4.32), w - 4.32), min(max(wp[1], 4.32), h - 4.32)), B._boxes(t), w, h)
            sl["regs_um"].append([round(fp[0], 3), round(fp[1], 3)])
            sl["stations"] = len(sl["regs_um"])
            added.append(f"{tn}.{sn}")
    log.append(f"boundary hops: {len(added)} slot(s) got a station on their out-window (macro-blocked downstream "
               f"window): {', '.join(added[:12])}{' ...' if len(added) > 12 else ''}")
    return added


# ------------------------------------------------------------------------------------------------ PHY keepouts
def phy_keepouts(plan, log):
    """All replicated instances share the union of their type-frame PHY-window reservations."""
    P = S.Plan(plan)
    unions = defaultdict(set)
    boxes = [io["rect_um"] for io in plan["die"].get("io", [])]
    boxes += [d["rect_um"] for d in plan["die"].get("pg", {}).get("domains", [])]
    for pn, part in P.parts.items():
        x0, y0, x1, y1 = P.rect(pn)
        for a, b, c, d in boxes:
            a, b, c, d = max(a, x0), max(b, y0), min(c, x1), min(d, y1)
            if a >= c or b >= d:
                continue
            corners = [P.to_type(pn, (x, y)) for x in (a, c) for y in (b, d)]
            box = (min(x for x, y in corners), min(y for x, y in corners),
                   max(x for x, y in corners), max(y for x, y in corners))
            unions[part["type"]].add(tuple(round(v, 4) for v in box))
    for tn, boxes in unions.items():
        plan["partition_types"][tn].setdefault("clock", {})["keepouts_um"] = [list(b) for b in sorted(boxes)]
    log.append(f"clock keepouts: PHY-window union in {len(unions)} uniform partition types")


def move_digital_io(items, pos, t):
    """Keep real PHY macros fixed; place digital endpoint cores outside their analog reservations."""
    W, H = t["outline_um"]
    ko = t.get("clock", {}).get("keepouts_um", [])
    dims = {k: (w, h) for k, w, h in items}
    analog = {h["inst"] for h in t.get("hard_cores", []) if "pdie_serdes" in h.get("module", "")}
    done = {k: pos[k] for k in analog}
    def overlap(a, b):
        return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
    for k, w, h in sorted(items, key=lambda q: (q[0] not in analog, q[0])):
        if k in analog:
            continue
        ox, oy = pos[k]
        blocks = list(ko) + [(x - LAT, y - LAT, x + dims[j][0] + LAT, y + dims[j][1] + LAT)
                             for j, (x, y) in done.items()]
        def legal(x, y):
            return LAT <= x and x + w <= W - LAT + 1e-6 and LAT <= y and y + h <= H - LAT + 1e-6 and \
                not any(overlap((x, y, x + w, y + h), b) for b in blocks)
        if not legal(ox, oy):
            cands = [(i * LAT, j * LAT) for i in range(1, int((W - w) / LAT))
                     for j in range(1, int((H - h) / LAT)) if legal(i * LAT, j * LAT)]
            if not cands:
                raise ValueError(f"digital endpoint {t['module']}.{k} cannot fit outside PHY keepout")
            pos[k] = min(cands, key=lambda q: (abs(q[0] - ox) + abs(q[1] - oy), q))
        done[k] = pos[k]


# ------------------------------------------------------------------------------------------------ native core shapes
from native_core_shapes import native_core_pins


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "B2n"))
    ap.add_argument("--out", default=str(HERE / "B2o"))
    ap.add_argument("--floorplan", default=str(INP / "floorplan.json"))
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in SIDECARS:
        s, d = src / f, out / f
        if s.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        elif s.exists():
            shutil.copy2(s, d)
    plan = json.loads((src / "die_plan.json").read_text())
    base = json.loads((src / "die_plan.json").read_text())
    FP = json.loads(Path(a.floorplan).read_text())
    log = []
    native_core_pins(plan, out, log)
    plan["die"]["name"] = "hbm_arch_B2o"
    plan["die"]["label"] = plan["die"]["label"].replace("B2n = ", "B2o = B2n re-floorplanned (compact SU rows, hub "
                                                        "spine abutting root); B2n = ", 1)
    import os
    import pickle
    cache = os.environ.get("B2O_STAGE_CACHE")      # developer speed-up only: reuse steps 1-4 of an identical run
    if cache and Path(cache).exists():
        plan, log, widths, changed, we, wt, worst = pickle.loads(Path(cache).read_bytes())
    else:
        if os.environ.get("B2O_PROGRESS"): print("layout", flush=True)
        rect, newH, dy, widths = layout(plan, FP, log)
        changed = apply_rects(plan, rect, newH, dy, log)
        phy_keepouts(plan, log)
        if os.environ.get("B2O_PROGRESS"): print("reroute", flush=True)
        routes, we, wt = reroute(plan, log)
        lane_delta(plan, log)
        B.rewindow(plan, log)
        touched, pairs = B.enforce_mirror(plan, log)
        worst = B.rewindow(plan, log, fixed_ids=touched)
        B.fix_mirror_pins(plan, pairs, log)
        if cache:
            Path(cache).write_bytes(pickle.dumps((plan, log, widths, changed, we, wt, worst)))
    T = plan["partition_types"]
    OLD_WH.update({tn: tuple(t["outline_um"]) for tn, t in base["partition_types"].items()})
    soft_with = [tn for tn, t in T.items() if not t.get("hard")]
    place_fail = place_contents(plan, out, [tn for tn in soft_with if tn in changed or T[tn].get("hard_cores")], log)
    ist_fail = internal_stations(plan, out, soft_with, log)
    fails = B.restation(plan, log)
    fix_cross_hops(plan, log)
    import b2m as B2M  # noqa: E402
    B2M.clock(plan, out, log)
    for t in T.values():
        fb = t.get("ft_budget")
        if fb is not None:
            for ln in B.DIE_ONLY:
                fb.pop(ln, None)
            if not fb:
                t.pop("ft_budget")
    B.reset_wavefront(plan, log)
    P = S.Plan(plan)
    plan["latency"]["lanes"] = {lid: P.lane_latency(lid) for lid in P.lanes}
    c0 = base["latency"]["lanes"]
    dc = {lid: plan["latency"]["lanes"][lid]["cycles"] - c0[lid]["cycles"] for lid in c0}
    up = [v for v in dc.values() if v > 0]
    dn = [v for v in dc.values() if v < 0]
    log.append(f"latency vs B2n: {len(up)} lanes +cycles (sum +{sum(up)}), {len(dn)} lanes -cycles (sum {sum(dn)}), "
               f"net {sum(dc.values()):+d}")
    plan["note"] = plan.get("note", "") + " | B2o derived by physical/die_plan/hbm_arch/b2o.py: " + "; ".join(log)
    (out / "die_plan.json").write_text(json.dumps(plan, indent=0) + "\n")
    (out / "die_io.json").write_text(json.dumps(plan["die"]["io"], indent=1) + "\n")     # sidecar = die.io (moved)
    rep = dict(log=log, floorplan_widths={"/".join(k): v for k, v in widths.items()}, infeasible_faces=worst,
               unroutable=fails, contents_unfit=place_fail, internal_unroutable=ist_fail,
               route_worst_face=[[r, list(k), v] for r, k, v in we], route_worst_transit=[list(x) for x in wt],
               lane_cycle_delta={k: v for k, v in dc.items() if v})
    (out / "b2o_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    lc = dict(schema="opentallas.hbm_b2o_lane_cycles.v1", plan="physical/die_plan/hbm_arch/B2o (claude/hbm-b2o-1024)",
              base="physical/die_plan/hbm_arch/B2n @871717c83",
              rule="B2o re-floorplan (B2o_inputs/floorplan.json) + full lane re-route + decision 12 stations (b2o.py)",
              summary=dict(lanes=len(dc), lanes_up=len(up), sum_up=sum(up), lanes_down=len(dn), sum_down=sum(dn),
                           net=sum(dc.values())),
              lanes={lid: dict(b2n=c0[lid]["cycles"], b2o=v["cycles"], delta=v["cycles"] - c0[lid]["cycles"],
                               route=P.lanes[lid].get("note", ""))
                     for lid, v in sorted(plan["latency"]["lanes"].items(),
                                          key=lambda kv: (int(kv[0][1:].rstrip("m")), kv[0]))})
    if out.resolve() == (HERE / "B2o").resolve():
        (ROOT / "results/arch/hbm_arch_1024/b2o_lane_cycles.json").write_text(json.dumps(lc, indent=1) + "\n")
    print("\n".join(log))
    for x in (worst[:5] + fails[:10] + place_fail[:5] + ist_fail[:5]):
        print("  !", x)


if __name__ == "__main__":
    main()
