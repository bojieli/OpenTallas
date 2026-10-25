#!/usr/bin/env python3
"""S81-PLAN3/CCONN2 10-25 (from S81-PLAN2/CCONN WIP; COORD ruling 10-25 + S81-CORES RULINGS (3) 05:40): core
re-placement + parent-slot growth delta for the derived-connectivity hard-core types (13 landed col_h* frames, gunit,
bk_sel) and the 16 hub-C dsdv_slice_*_C types that hold ot_s81dv_xfin.

Derived core connectivity (gen_plan_v4.derived_core_conns, still opt-in OT_S81_DERIVED_CORE_CONNS=1) is filtered by
(a) Codex's fail-closed INPUT/INPUT alias filter (core_conns_directions.py) and (b) the clock-net filter (a core port
on the contents' clk is CTS distribution, not a data hop).  G0C R3-INTERNAL then needs every core<->core and bus
window<->core bundle <= 405 um or a FIRM internal_stations[] entry:

  1. qbank_S growth (S81-CORES kit CTS DPL-0038): dsfd_qbank_S 60.48 x 17.28 -> 60.48 x 25.92 (+1 lattice row; up
     when free, else down, else re-sited); inputs/core_pins/dsfd_qbank_S.json N pins +8.64 (--pins).
  2. gunit: explicit two-cluster re-placement (GUNIT_SITES).  Other types: least-displacement single-core moves
     (CCONN mover) + lattice annealing for small types.
  3. FIRM internal stations (HOP 401 um, L-paths, sites nudged off cores) for what no site closes; bus stations add
     +1 cycle to every lane landing on / leaving that bus (lanes[].fixed_cycles + latency table); core<->core
     stations need frame RTL (kit_istations fails closed outside leaf CS_* chains).
  4. bk_sel deferred (DEFER): no core site closes c/g <-> 4 x 648-um q in a 1226.88 slot -> COORD decision.
  5. xfin: 181.44^2 -> 362.88^2 in every hub-C slice (right of xr, eg above, FT corridors avoided, MX handled);
     inputs/core_pins/ot_s81dv_xfin.json E/N faces moved out, groups re-spread (--pins).

    python3 physical/die_plan/s81/delta_cconn_1025.py PLAN [OUT] [--pins] [--sidecar CORE_CONNS.json] [--report R.json]
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(REPO), str(REPO / "tools" / "die_plan")]

G = 8.64
REACH = 405.0 - 9.0          # placement target: a lattice step inside the 405-um R3 limit
HALO = 4.32                  # clearance between hard cores (half a lattice step)
FT_KEEP = 4.32               # clearance around FT station bit-site boxes
QBS = ("dsfd_qbank_S", 25.92)


def _box(h):
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    return [x, y, x + w, y + hh]


def _d(a, b):
    return max(a[0] - b[2], b[0] - a[2], 0) + max(a[1] - b[3], b[1] - a[3], 0)


def _dp(p, b):
    return max(b[0] - p[0], 0, p[0] - b[2]) + max(b[1] - p[1], 0, p[1] - b[3])


def _ov(a, b, c):
    return a[0] < b[2] + c and b[0] < a[2] + c and a[1] < b[3] + c and b[1] < a[3] + c


def _ft_boxes(t):
    out = []
    for s in t.get("ft_slots", []):
        bs = s.get("bit_sites_um")
        if isinstance(bs, str):
            bs = json.loads(bs)
        for st in bs or []:
            pts = st if st and isinstance(st[0], list) else [st]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append([min(xs) - FT_KEEP, min(ys) - FT_KEEP, max(xs) + FT_KEEP, max(ys) + FT_KEEP])
        for r in s.get("regs_um", []):
            out.append([r[0] - FT_KEEP, r[1] - FT_KEEP, r[0] + FT_KEEP, r[1] + FT_KEEP])
    return out


def _partners(conns, bt):
    """{inst: {('core', other) | ('bus', name, (x, y))}} both directions."""
    pr = {}
    for ci, ports in conns.items():
        for tgs in ports.values():
            for tg in tgs:
                k, _, n = tg.partition(":")
                if k == "core":
                    pr.setdefault(ci, set()).add(("core", n))
                    pr.setdefault(n, set()).add(("core", ci))
                elif k == "bus" and n in bt:
                    pr.setdefault(ci, set()).add(("bus", n, tuple(bt[n][1])))
    return pr


def _worst(ci, b, boxes, pr):
    w = 0.0
    for p in pr.get(ci, ()):
        w = max(w, _d(b, boxes[p[1]]) if p[0] == "core" else _dp(p[2], b))
    return w


def _violations(boxes, pr, lim):
    v = []
    for ci in sorted(pr):
        for p in sorted(pr[ci], key=str):
            if p[0] == "core" and ci < p[1] and _d(boxes[ci], boxes[p[1]]) > lim:
                v.append((ci, p[1]))
            elif p[0] == "bus" and _dp(p[2], boxes[ci]) > lim:
                v.append((ci, None))
    return v


def _site(ci, boxes, W, H, ft, pr, edge):
    """least-displacement lattice site for ci with every partner <= REACH; None if there is none."""
    x0, y0, x1, y1 = boxes[ci]
    w, h = x1 - x0, y1 - y0
    others = [b for k, b in boxes.items() if k != ci]
    best = None
    nx, ny = int((W - w - edge) // G), int((H - h - edge) // G)
    lo = int(round(edge / G))
    for ix in range(lo, nx + 1):
        x = ix * G
        for iy in range(lo, ny + 1):
            y = iy * G
            cost = abs(x - x0) + abs(y - y0)
            if best is not None and cost >= best[0]:
                continue
            b = [x, y, x + w, y + h]
            if _worst(ci, b, boxes, pr) > REACH:
                continue
            if any(_ov(b, o, HALO) for o in others) or any(_ov(b, f, 0) for f in ft):
                continue
            best = (cost, b)
    return best


def _anneal(boxes, pr, W, H, ft, edge, seed=1, iters=60000):
    """small types (<= 12 cores, e.g. gunit / bk_sel): lattice simulated annealing of ALL core sites, cost = sum of
    partner excess over REACH + overlap; returns new boxes (or the input when it does not improve)."""
    import math
    import random
    rnd = random.Random(seed)
    ks = sorted(boxes)
    wh = {k: (boxes[k][2] - boxes[k][0], boxes[k][3] - boxes[k][1]) for k in ks}

    def cost(bx):
        c = 0.0
        for k in ks:
            for p in pr.get(k, ()):
                if p[0] == "core" and k < p[1]:
                    c += max(0.0, _d(bx[k], bx[p[1]]) - REACH)
                elif p[0] == "bus":
                    c += max(0.0, _dp(p[2], bx[k]) - REACH)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                A, B = bx[a], bx[b]
                ox = min(A[2], B[2]) + HALO - max(A[0], B[0])
                oy = min(A[3], B[3]) + HALO - max(A[1], B[1])
                if ox > 0 and oy > 0:
                    c += 50.0 * min(ox, oy) + 1000.0
            if any(_ov(bx[a], f, 0) for f in ft):
                c += 1000.0
        return c
    cur = {k: list(v) for k, v in boxes.items()}
    cc = c0 = cost(cur)
    best, bc = {k: list(v) for k, v in cur.items()}, cc
    T0 = 400.0
    for it in range(iters):
        T = T0 * (1 - it / iters) + 1e-3
        k = rnd.choice(ks)
        w, h = wh[k]
        nb = dict(cur)
        if rnd.random() < 0.15:
            k2 = rnd.choice(ks)
            x, y = cur[k2][0], cur[k2][1]
            x2, y2 = cur[k][0], cur[k][1]
            w2, h2 = wh[k2]
            nb[k] = [x, y, x + w, y + h]
            nb[k2] = [x2, y2, x2 + w2, y2 + h2]
        else:
            step = max(G, T)
            x = cur[k][0] + rnd.gauss(0, step)
            y = cur[k][1] + rnd.gauss(0, step)
            x = min(max(edge, round(x / G) * G), math.floor((W - w - edge) / G) * G)
            y = min(max(edge, round(y / G) * G), math.floor((H - h - edge) / G) * G)
            nb[k] = [x, y, x + w, y + h]
        if any(b[0] < edge - 1e-6 or b[1] < edge - 1e-6 or b[2] > W - edge + 1e-6 or b[3] > H - edge + 1e-6
               for b in nb.values()):
            continue
        nc = cost(nb)
        if nc <= cc or rnd.random() < math.exp((cc - nc) / T):
            cur, cc = nb, nc
            if cc < bc:
                best, bc = {kk: list(v) for kk, v in cur.items()}, cc
                if bc == 0:
                    break
    return (best, bc, c0) if bc < c0 else (boxes, c0, c0)


# ------------------------------------------------------------------------------------------------ S81-PLAN3/CCONN2
# gunit (2885.76 x 1226.88, one partition): the 10 cores sat on one shelf row in RTL order, so l0<->l4 / l4<->l5 /
# l5<->l5f / l1<->l3 / l0<->l2 bundles ran 484-2082 um.  Re-placed as two clusters around the S-face windows they talk to:
#   west  l3 | l1 (above) + l1c, l2 at unit_i0 (1478)          east  l5 at xtier_i1/o1 (1599/1661) + l5f, l4 above l5,
#   l0 above l2 (l0<->l2 / l0<->l4 / l0<->l0r), l0r above l0, l4r above l4.  Every bundle <= 405 um except l3.vi_s <-
#   xtier_i0: l3 talks to BOTH xtier_i0 (x 36, lane from s_2N_x06 ft1_o) and xtier_o0 (x 1538): 1502 um apart > 345.6 +
#   2 x 405, so no l3 site serves both; l3 sits within reach of xtier_o0 and the vi_s bundle gets 1 FIRM bus station
#   (+1 cycle, lane xtier__s_3S_C__gunit fixed_cycles 0 -> 1, LAT 59 -> 60).  Moving the xtier_i0 window would move the
#   s_2N_x06 ft1_o window and its FT slot (another type), so the station is the local structural fix.
GUNIT_SITES = {        # inst: origin (type frame, R0); outlines unchanged
    "u_gunit.u_l3": (812.16, 17.28), "u_gunit.u_l1": (812.16, 207.36), "u_gunit.u_l1c": (708.48, 207.36),
    "u_gunit.u_l2": (1175.04, 17.28), "u_gunit.u_l0": (1175.04, 207.36), "u_gunit.u_l0r": (1175.04, 397.44),
    "u_gunit.u_l5": (1537.92, 17.28), "u_gunit.u_l5f": (1900.8, 17.28), "u_gunit.u_l4": (1537.92, 336.96),
    "u_gunit.u_l4r": (1537.92, 423.36),
}
# bk_sel (4328.64 x 1226.88): u_c and u_g each talk to all four 648 x 648 dsdv_bksel_q cores and u_tx / u_g to the S-face
# windows tl_o0 / xtier_o0 (x 1163 / 1407).  Two q rows need 1296 + gaps > 1157.76 um of slot height and in one row the
# outer q cores sit >= 480 um from any c / g site (> 405 even with c centred over the q1 | q2 seam); u_tx (561.6 tall)
# fits neither under nor over the q row next to its windows.  No core move closes it: left to a COORD decision
# (q reshape 972 x 432 -> 2 x 2 q block around a c / g / tx column, or priced stations on the q0 / q3 links + RTL).
DEFER = {"bk_sel__t2": "no core site closes c/g <-> 4 x q (648 um squares, 1226.88-um slot): COORD decision (q reshape or "
                       "stations + RTL)"}
HOP = 401.0            # station spacing target (check.py limit 405 on track-offset boxes)


def _near(a, b):
    """nearest point pair (pa on box a, pb on box b)."""
    def ax(a0, a1, b0, b1):
        if a1 < b0:
            return a1, b0
        if b1 < a0:
            return a0, b1
        m = (max(a0, b0) + min(a1, b1)) / 2
        return m, m
    x = ax(a[0], a[2], b[0], b[2])
    y = ax(a[1], a[3], b[1], b[3])
    return [x[0], y[0]], [x[1], y[1]]


def _clamp(p, b):
    return [min(max(p[0], b[0]), b[2]), min(max(p[1], b[1]), b[3])]


def _stations(p, q, boxes, skip):
    """regs on an L path p -> q, equal Manhattan hops <= HOP; tries x-first then y-first, avoiding hard-core boxes."""
    d = abs(p[0] - q[0]) + abs(p[1] - q[1])
    n = max(0, -(-d // HOP) - 1)
    n = int(n)
    best = None
    for order in ("xy", "yx"):
        regs = []
        for j in range(1, n + 1):
            s = d * j / (n + 1)
            if order == "xy":
                dx = min(s, abs(q[0] - p[0]))
                x = p[0] + dx * (1 if q[0] >= p[0] else -1)
                y = p[1] + (s - dx) * (1 if q[1] >= p[1] else -1)
            else:
                dy = min(s, abs(q[1] - p[1]))
                y = p[1] + dy * (1 if q[1] >= p[1] else -1)
                x = p[0] + (s - dy) * (1 if q[0] >= p[0] else -1)
            regs.append([round(x, 3), round(y, 3)])
        def bad(r):
            return any(b[0] - 1.0 < r[0] < b[2] + 1.0 and b[1] - 1.0 < r[1] < b[3] + 1.0
                       for k, b in boxes.items() if k not in skip)
        pts = [p] + regs + [q]
        for j in range(1, len(pts) - 1):        # nudge a site off a hard core (lattice offsets <= 8 x 8.64 um)
            if not bad(pts[j]):
                continue
            for r_ in sorted(((dx * G, dy * G) for dx in range(-8, 9) for dy in range(-8, 9)), key=lambda o: abs(o[0]) + abs(o[1])):
                c = [round(pts[j][0] + r_[0], 3), round(pts[j][1] + r_[1], 3)]
                if (not bad(c) and abs(c[0] - pts[j - 1][0]) + abs(c[1] - pts[j - 1][1]) <= 404.0
                        and abs(c[0] - pts[j + 1][0]) + abs(c[1] - pts[j + 1][1]) <= 404.0):
                    pts[j] = c
                    break
        regs = pts[1:-1]
        inside = sum(1 for r in regs if bad(r))
        if best is None or inside < best[0]:
            best = (inside, regs)
    return best[1], best[0]


def _lef_dir(t, ci, p):
    import core_conns_directions as D
    h = next(h for h in t["hard_cores"] if h["inst"] == ci)
    try:
        return D.lef_directions(REPO / h["lef"]).get(p) if h.get("lef") else None
    except (OSError, ValueError):
        return None


def residual_stations(t, conns, bt, rep):
    """FIRM internal_stations[] for every bundle still > 405 um after the moves (R3-INTERNAL keys as check.py reads them)."""
    boxes = {h["inst"]: (lambda b, o: [b[0] + o[0], b[1] + o[1], b[2] + o[0], b[3] + o[1]])(
        _box(h), h.get("track_offset_um", [0.0, 0.0])) for h in t["hard_cores"]}
    out, cyc = [], {}
    for ci, ports in sorted(conns.items()):
        for lp, tgs in sorted(ports.items()):
            for tg in tgs:
                k, _, nm = tg.partition(":")
                if k == "core":
                    if nm not in boxes:
                        continue
                    pa, pb = _near(boxes[ci], boxes[nm])
                    if abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) <= 405.0 - 0.5:
                        continue
                    dr = _lef_dir(t, ci, lp)
                    if dr == "INPUT":
                        drv = [q for q, v in conns.get(nm, {}).items() if "core:" + ci in v and _lef_dir(t, nm, q) == "OUTPUT"]
                        conn, launch, cap, fr, to = (f"core:{nm}.{drv[0]}|core:{ci}", f"{nm}.{drv[0]}", f"{ci}.{lp}", pb, pa) \
                            if drv else (f"core:{ci}.{lp}|core:{nm}", f"{ci}.{lp}", nm, pa, pb)
                    else:
                        conn, launch, cap, fr, to = f"core:{ci}.{lp}|core:{nm}", f"{ci}.{lp}", nm, pa, pb
                    skip = {ci, nm}
                    key = ("core", tuple(sorted([ci, nm])))
                elif k == "bus" and nm in bt:
                    bp = list(bt[nm][1])
                    cp = _clamp(bp, boxes[ci])
                    if abs(bp[0] - cp[0]) + abs(bp[1] - cp[1]) <= 405.0 - 0.5:
                        continue
                    dr = _lef_dir(t, ci, lp)
                    if dr == "OUTPUT":
                        conn, launch, cap, fr, to = f"bus:{nm}", f"{ci}.{lp}", f"{ci}.{lp}", cp, bp
                    else:
                        conn, launch, cap, fr, to = f"bus:{nm}", f"face bus {nm}", f"{ci}.{lp}", bp, cp
                    skip = {ci}
                    key = ("bus", nm)
                else:
                    continue
                regs, inside = _stations(fr, to, boxes, skip)
                d = abs(fr[0] - to[0]) + abs(fr[1] - to[1])
                out.append(dict(conn=conn, from_um=[round(v, 3) for v in fr], to_um=[round(v, 3) for v in to], regs_um=regs,
                                launch=launch, capture=cap,
                                note=f"S81-PLAN3/CCONN2 10-25 R3: derived core bundle {round(d)} um > 405 after the core "
                                     f"moves: {len(regs)} FIRM station(s), +{len(regs)} cycle(s)" +
                                     (f"; {inside} site(s) over a hard core (re-site)" if inside else "")))
                cyc[key] = max(cyc.get(key, 0), len(regs))
                if inside:
                    rep.setdefault("stations_over_core", []).append(conn)
    return out, cyc


def bump_lanes(raw, tn, cyc, rep):
    """+n fixed cycles on the lanes that land on (or leave) a bus that got n FIRM internal bus stations."""
    parts = {p["name"] for p in raw["partitions"] if p["type"] == tn}
    pid = {p["id"]: p for p in raw["ports"]}
    lat = raw["latency"]["lanes"]
    for (kind, nm), n in sorted(cyc.items()):
        if kind != "bus" or not n:
            continue
        for ln in raw["lanes"]:
            a, z = pid[ln["ports"][0]], pid[ln["ports"][-1]]
            hit = (z["dst"]["part"] in parts and z["dst"]["bus"] == nm) or (a["src"]["part"] in parts and a["src"]["bus"] == nm)
            if not hit:
                continue
            ln["fixed_cycles"] = ln.get("fixed_cycles", 0) + n
            e = lat.get(ln["id"])
            if e:
                frm = e["cycles"]
                for f in ("cycles", "fixed", "natural"):
                    e[f] += n
                rep.setdefault("lane_latency", {})[ln["id"]] = [frm, e["cycles"]]


# ------------------------------------------------------------------------------------------------ xfin (S81-CORES (3))
# COORD 05:40 S81-CORES RULINGS (3): xfin's kit failed GPL at 255 % (75,438.654 um2 of cells in 181.44^2): the hub-C
# parent slot (the 16 dsdv_slice_*_C types, 1442.88 x 1226.88, cap | xr | eg+xf) has the room, so xfin grows top-down to
# 362.88 x 362.88 (131,682 um2, measured-cell fill 0.573) and eg (the xfin -> eg copy link, xf N face -> eg S face) re-sits on top of
# it.  Site search per type (S81-PLAN2/XFIN search.py): xf on the cap/xr row edge right of xr (>= 17.28 um gap), eg above
# xf (>= 60 % x overlap), both clear of every FT station polyline (half window + 10 um) and of cap / xr.
XF = ("ot_s81dv_xfin", 362.88)
XF_GAP, XF_EDGE, EG = 17.28, 34.56, 259.2


def _segbox(p, q, box):
    import math
    def d(tt):
        x = p[0] + (q[0] - p[0]) * tt
        y = p[1] + (q[1] - p[1]) * tt
        return math.hypot(max(box[0] - x, 0, x - box[2]), max(box[1] - y, 0, y - box[3]))
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if d(m1) < d(m2):
            hi = m2
        else:
            lo = m1
    return min(d(lo), d(0), d(1))


def xfin_sizes():
    """362.88^2 first, then lattice rectangles sized for measured cell area / 60% fill (aspect <= 1.8) by aspect: ONE outline for every
    instance (one module = one hardened view)."""
    return [(XF[1], XF[1])] + sorted(((a * G, b * G) for a in range(30, 60) for b in range(30, 60)
                                      if 75438.654 / 0.60 <= a * b * G * G <= 140000 and max(a, b) / min(a, b) <= 1.8
                                      and (a, b) != (42, 42)), key=lambda s_: (max(s_) / min(s_), s_))


def xfin_grow(t, rep, size, dry=False):
    import math
    hc = {c["inst"]: c for c in t.get("hard_cores", [])}
    xf, eg = hc.get("u_c.u_xf"), hc.get("u_c.u_eg")
    if not xf or xf["module"] != XF[0] or xf["outline_um"][0] >= XF[1] - 1e-6:
        return None
    W, H = t["outline_um"]
    mx = xf.get("orient", "R0") == "MX"
    r0y = (lambda y, h: round(H - y - h - G, 3)) if mx else (lambda y, h: round(y, 3))     # type frame <-> R0 frame (involution)
    fy = (lambda y: H - y) if mx else (lambda y: y)
    fixed = []
    for k in ("u_c.u_cap", "u_c.u_xr"):
        c = hc[k]
        x0, y0 = c["origin_um"]
        w, h = c["outline_um"]
        y0 = r0y(y0, h)
        fixed.append((x0, y0, x0 + w, y0 + h))
    fts = []
    for s in t.get("ft_slots", []):
        hw = max(abs(s["in_window_um"][1] - s["in_window_um"][0]), abs(s["out_window_um"][1] - s["out_window_um"][0])) / 2
        fts.append((hw + 10, [(r[0], fy(r[1])) for r in s["regs_um"]]))

    def ftok(b):
        for hal, pts in fts:
            if any(_segbox(p, q, b) < hal for p, q in zip(pts, pts[1:])):
                return False
            if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in pts):
                return False
        return True

    def gapok(a, b):
        return (a[2] + XF_GAP <= b[0] + 1e-6 or b[2] + XF_GAP <= a[0] + 1e-6 or a[3] + XF_GAP <= b[1] + 1e-6
                or b[3] + XF_GAP <= a[1] + 1e-6)
    xr = fixed[1]
    best = None
    best = _xf_search(size[0], size[1], xr, fixed, W, H, ftok, gapok)
    if best is None or dry:
        return best
    (xx, xy), (ex, ey), (w, h) = best[1], best[2], best[3]
    old = dict(xf=[xf["origin_um"], xf["outline_um"]], eg=eg["origin_um"])
    xf["outline_um"] = [round(w, 3), round(h, 3)]
    xf["origin_um"] = [round(xx, 3), r0y(xy, h)]
    eg["origin_um"] = [round(ex, 3), r0y(ey, EG)]
    return dict(old=old, xf=[xf["origin_um"], xf["outline_um"]], eg=eg["origin_um"], mx=mx)


def _xf_search(w, h, xr, fixed, W, H, ftok, gapok):
    """xf right of xr (>= 17.28 gap), on the cap / xr row edge first, then lifted in 4-lattice steps (FT corridors
    along the row edge); eg above xf (>= 60 % x overlap, 17.28 gap)."""
    best = None
    for yb in [XF_EDGE + k * 4 * G for k in range(0, 40)]:
        if yb + h + XF_GAP + EG > H - XF_EDGE + 1e-6:
            break
        x0 = math.ceil((xr[2] + XF_GAP) / G - 1e-9) * G
        while x0 + w <= W - XF_EDGE + 1e-6:
            xb = (x0, yb, x0 + w, yb + h)
            if ftok(xb) and all(gapok(xb, f) for f in fixed):
                ey = math.ceil((yb + h + XF_GAP) / G - 1e-9) * G
                for ex in [x0 + k * G for k in range(-15, int(w / G) + 1)]:
                    eb = (ex, ey, ex + EG, ey + EG)
                    ov = min(eb[2], xb[2]) - max(eb[0], xb[0])
                    if ov < 0.6 * EG or eb[0] < XF_EDGE or eb[2] > W - XF_EDGE or eb[3] > H - XF_EDGE:
                        continue
                    if not (ftok(eb) and all(gapok(eb, f) for f in fixed)):
                        continue
                    cost = (x0 - xr[2]) + 0.5 * abs((ex + EG / 2) - (x0 + w / 2)) + (eb[3] - XF_EDGE) * 0.3
                    if best is None or cost < best[0]:
                        best = (cost, (x0, yb), (ex, ey), (w, h))
            x0 += G
        if best:
            return best
    return best


def xfin_pins(path, size):
    """ot_s81dv_xfin plan pin table resized from its current square outline: E-face pins x += dW, N-face pins y += dH, and every face's
    bus groups re-spread along the longer face (group start scaled, shifts in 0.576-um multiples = whole M4 / M5 tracks;
    a group's internal pitch is kept)."""
    import re
    txt = open(path).read()
    d = json.loads(txt)
    old = max(max(p["x"] for p in d["pins"]), max(p["y"] for p in d["pins"])) + 0.042
    if abs(old - size[0]) < 1e-3 and abs(old - size[1]) < 1e-3:
        return False
    if old > min(size) + 1e-3:
        raise ValueError("xfin pin-table shrink is not supported")
    w_new, h_new = size
    Q = 0.576
    faces = {}
    for p in d["pins"]:
        f = "S" if p["y"] < 1 else "N" if p["y"] > old - 1 else "W" if p["x"] < 1 else "E"
        faces.setdefault(f, []).append(p)
    for f, ps in faces.items():
        along = "x" if f in "NS" else "y"
        s_new = w_new if f in "NS" else h_new
        sc = s_new / old
        groups = {}
        for p in ps:
            groups.setdefault(re.sub(r"\[\d+\]$", "", p["name"]), []).append(p)
        prev_end = None
        for g, gp in sorted(groups.items(), key=lambda kv: min(p[along] for p in kv[1])):
            a0 = min(p[along] for p in gp)
            a1 = max(p[along] for p in gp)
            sh = round(a0 * (sc - 1) / Q) * Q
            if prev_end is not None and a0 + sh < prev_end + 0.192:
                sh += math.ceil((prev_end + 0.192 - a0 - sh) / Q) * Q
            if a1 + sh > s_new - 0.5:
                sh -= math.ceil((a1 + sh - (s_new - 0.5)) / Q) * Q
            for p in gp:
                p[along] = round(p[along] + sh, 4)
            prev_end = a1 + sh
        for p in ps:
            if f == "E":
                p["x"] = round(p["x"] + w_new - old, 4)
            elif f == "N":
                p["y"] = round(p["y"] + h_new - old, 4)
    d["source"] = d.get("source", "") + (" | S81-PLAN3/CCONN2 10-25: outline current -> %gx%g (COORD S81-CORES (3), "
                                         "parent-slot growth): E/N faces moved out, bus groups re-spread along each face"
                                         % (w_new, h_new))
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    open(path, "w").write((json.dumps(d, indent=1) if txt.startswith("{\n") else json.dumps(d)) + "\n")
    return True


def qbank_s_pins(path):
    """N-face (upper half) pins of dsfd_qbank_S up by the +8.64 row; S / lower W, E pins unchanged (S81-PLAN2/CCONN)."""
    txt = open(path).read()
    d = json.loads(txt)
    if any(p["y"] > 17.28 for p in d["pins"]):
        return False
    for p in d["pins"]:
        if p["y"] > 8.64:
            p["y"] = round(p["y"] + QBS[1] - 17.28, 4)
    d["source"] = d.get("source", "") + " | S81-PLAN2/CCONN 10-25: +8.64 um row (60.48 x 25.92), upper-half pins +8.64"
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    open(path, "w").write((json.dumps(d, indent=1) if txt.startswith("{\n") else json.dumps(d)) + "\n")
    return True


def apply(raw):
    import gen_plan_v4 as GP
    import check as C
    import schema as S
    T = raw["partition_types"]
    GP.CORE_CONNS_OUT.clear()
    GP.derived_core_conns(T)
    derived = {k: v for k, v in GP.CORE_CONNS_OUT.items()}
    P = S.Plan(raw, None)
    rep = dict(types={}, qbank_S=dict(grown_up=0, grown_down=0, replaced=0), xfin={})
    for tn in sorted(derived):
        if tn in DEFER:
            rep["deferred"] = {tn: DEFER[tn]}
            continue
        t = T[tn]
        conns = derived[tn]
        bt = C._bus_targets(P, tn)
        pr = _partners(conns, bt)
        W, H = t["outline_um"]
        hcs = {h["inst"]: h for h in t["hard_cores"]}
        boxes = {k: _box(h) for k, h in hcs.items()}
        edge = min(min(b[0], b[1], W - b[2], H - b[3]) for b in boxes.values())
        edge = max(0.0, min(edge, 2 * G))
        ft = _ft_boxes(t)
        moved, overlap = {}, set()
        # 1. qbank_S +1 lattice row (S81-CORES kit CTS DPL-0038, util 118 %)
        for k, h in hcs.items():
            if h["module"] != QBS[0] or h["outline_um"][1] >= QBS[1] - 1e-6:
                continue
            dh = QBS[1] - h["outline_um"][1]
            b = boxes[k]
            up, dn = [b[0], b[1], b[2], b[3] + dh], [b[0], b[1] - dh, b[2], b[3]]
            ok = lambda nb: (nb[1] >= edge - 1e-6 and nb[3] <= H - edge + 1e-6 and
                             not any(_ov(nb, o, HALO) for kk, o in boxes.items() if kk != k) and
                             not any(_ov(nb, f, 0) for f in ft))
            if ok(up):
                boxes[k] = up
                rep["qbank_S"]["grown_up"] += 1
            elif ok(dn):
                boxes[k] = dn
                rep["qbank_S"]["grown_down"] += 1
            else:
                boxes[k] = up
                overlap.add(k)
                rep["qbank_S"]["replaced"] += 1
            h["outline_um"] = [h["outline_um"][0], QBS[1]]
        for k in sorted(overlap):
            s = _site(k, boxes, W, H, ft, pr, edge)
            if s:
                moved[k] = [round(v, 3) for v in boxes[k][:2]], s[1][:2]
                boxes[k] = s[1]
                overlap.discard(k)
        before = _violations(boxes, pr, 405.0)
        annealed = None
        if tn == "gunit__t1":
            # 2. gunit: explicit two-cluster re-placement (see GUNIT_SITES)
            for k, (x, y) in GUNIT_SITES.items():
                b = boxes[k]
                moved[k] = ([round(v, 3) for v in b[:2]], [x, y])
                boxes[k] = [x, y, x + b[2] - b[0], y + b[3] - b[1]]
            ks = sorted(boxes)
            assert not any(_ov(boxes[a], boxes[b], HALO) for i, a in enumerate(ks) for b in ks[i + 1:]), "gunit overlap"
        else:
            # 3. least-displacement single-core moves (S81-PLAN2/CCONN mover), small types: lattice annealing
            unresolved = []
            for it in range(200):
                v = [x for x in _violations(boxes, pr, 405.0) if x not in unresolved]
                if not v:
                    break
                a, b = v[0]
                cands = [a] if b is None else sorted([a, b], key=lambda c: (len(pr.get(c, ())),
                                                                             (boxes[c][2] - boxes[c][0]) *
                                                                             (boxes[c][3] - boxes[c][1])))
                done = False
                for c in cands:
                    s = _site(c, boxes, W, H, ft, pr, edge)
                    if s:
                        moved.setdefault(c, ([round(x, 3) for x in boxes[c][:2]], None))
                        moved[c] = (moved[c][0], s[1][:2])
                        boxes[c] = s[1]
                        done = True
                        break
                if not done:
                    unresolved.append((a, b))
            if unresolved and len(hcs) <= 12:
                bx0 = {k: list(v) for k, v in boxes.items()}
                nb, c1, c0 = min((_anneal(bx0, pr, W, H, ft, edge, seed=s) for s in range(1, 9)), key=lambda r: r[1])
                if c1 < c0:
                    boxes = nb
                    annealed = dict(excess_um_before=round(c0, 1), excess_um_after=round(c1, 1))
                    for k in hcs:
                        if boxes[k][:2] != bx0[k][:2]:
                            moved.setdefault(k, ([round(x, 3) for x in bx0[k][:2]], None))
                            moved[k] = (moved[k][0], boxes[k][:2])
        for k, h in hcs.items():
            h["origin_um"] = [round(boxes[k][0], 3), round(boxes[k][1], 3)]
        # 4. FIRM stations for what no core site can close
        trep = {}
        ist, cyc = residual_stations(t, conns, bt, trep)
        if ist:
            t["internal_stations"] = [e for e in t.get("internal_stations", []) if "CCONN2" not in e.get("note", "")] + ist
            bump_lanes(raw, tn, cyc, trep)
        rep["types"][tn] = dict(bundle_pairs_before=len(before),
                                moved={k: dict(frm=v[0], to=[round(x, 3) for x in v[1]]) for k, v in moved.items() if v[1]},
                                overlap_left=sorted(overlap), annealed=annealed,
                                stations=[dict(conn=e["conn"], capture=e["capture"], regs=len(e["regs_um"])) for e in ist],
                                station_cycles={f"{k[0]}:{'|'.join(k[1]) if k[0] == 'core' else k[1]}": n for k, n in cyc.items()},
                                **trep)
    # 5. xfin parent-slot growth
    xts = [tn for tn in sorted(T) if any(h["module"] == XF[0] for h in T[tn].get("hard_cores", []))]
    for size in xfin_sizes():
        miss = [tn for tn in xts if not xfin_grow(T[tn], rep, size, dry=True)]
        if not miss:
            break
        rep.setdefault("xfin_size_rejected", {})[f"{size[0]:g}x{size[1]:g}"] = miss
    else:
        size = None
    rep["xfin_size"] = size
    for tn in xts if size else ():
        rep["xfin"][tn] = xfin_grow(T[tn], rep, size)
    return rep, derived


def write_sidecar(derived, path):
    side = json.load(open(path))
    side.update(derived)
    open(path, "w").write(json.dumps(side, indent=0, sort_keys=True))


def main():
    pf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else pf
    raw = json.load(open(pf))
    if any("CCONN2" in e.get("note", "") for t in raw["partition_types"].values() for e in t.get("internal_stations", [])):
        sys.exit("delta_cconn_1025: already applied to %s (FIRM CCONN2 stations / lane cycles present)" % pf)
    rep, derived = apply(raw)
    if "--pins" in sys.argv:
        rep["qbank_S_pins_rewritten"] = qbank_s_pins(HERE / "inputs" / "core_pins" / "dsfd_qbank_S.json")
        rep["xfin_pins_rewritten"] = xfin_pins(HERE / "inputs" / "core_pins" / "ot_s81dv_xfin.json", rep["xfin_size"]) \
            if rep["xfin_size"] else None
    if "--sidecar" in sys.argv:
        write_sidecar(derived, sys.argv[sys.argv.index("--sidecar") + 1])
    sys.path.insert(0, str(REPO / "results" / "s81_plan2_1025"))
    import pdump                     # the plan's own layout (round-trips die_plan.json byte for byte)
    txt = pdump.dumps(raw)
    open(out, "w").write(txt)
    if "--report" in sys.argv:
        open(sys.argv[sys.argv.index("--report") + 1], "w").write(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep["types"].items():
        print(tn, "pairs>405 before", r["bundle_pairs_before"], "moved", len(r["moved"]), "stations", len(r["stations"]),
              "cycles", r["station_cycles"], "over_core", len(r.get("stations_over_core", [])), "lanes", r.get("lane_latency"))
    print("qbank_S", rep["qbank_S"], "xfin types", len(rep["xfin"]), "size", rep["xfin_size"],
          "rejected", rep.get("xfin_size_rejected", {}).get("345.6x345.6"), "deferred", rep.get("deferred"))


if __name__ == "__main__":
    main()
