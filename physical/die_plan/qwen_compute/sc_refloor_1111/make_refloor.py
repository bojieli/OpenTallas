"""SC-REFLOOR-1: sl_sc re-floor generator (positions only; cores keep shape; station COUNTS unchanged; face windows and
pins unchanged, so no neighbour type, port, RTL or cycle changes).

Root cause (route_supply record attribution on s25): every sc ft slot carries plan-explicit CLUMP bit sites (each
500-550-bit station squeezed into a ~24 x 24 um square; ft_spread skips slots that already have sites) on stations that
zig-zag (x_fw_fe_p2 dips 300 um along the W face and back; x_fw_st_b 330 um) and that stack two V bundles on the
column hugging the core W edge (x_ctl_su_c_p2 + x_fw_ctl_p1 at x 337) and a 456-b V bundle in the 23-um E gap
(x_su_l1_ctl at x 604.8).  At the cut level the slot has ~3x track margin in both directions.

Form R (this tool), per sc type:
  1. optional core shift W by --dx (8.64 lattice), points in the vacated band shifted with it (make_sc.py rule);
  2. every ft slot is re-routed on a Manhattan route from its in-pin centroid to its out-pin centroid: H wires may
     pass over the core (M6), V wires may not (only M7 over an M1-M5 core); V runs are assigned to columns by a
     greedy column-load map (wide bundles first) so no two bundles share a column; corner lanes (W>N, S>N, ...) take
     the cheaper of the core's W side and its E gap;
  3. the SAME number of stations is placed at equal arc length on the route (regs_um[0], the in-face register,
     is kept), any station inside the core keep-off slides along the route;
  4. explicit bit sites in BAND form: at each station the bits sit in a band ACROSS the travel direction, in in-pin
     order (no crossing), band width = max(bits / --dens tracks per um, interpolated window span), snapped to free
     legal row sites (tools.die_trial RowAllocator, the ft_spread grid and cell envelope).
usage: make_refloor.py SRC BASE.json OUT.json DELTA.json [--dx 0] [--match _sc_] [--dens 18] [--types a,b]"""
import argparse, hashlib, json, math, sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("base")
ap.add_argument("out")
ap.add_argument("delta")
ap.add_argument("--dx", type=float, default=0.0)
ap.add_argument("--match", default="_sc_")
ap.add_argument("--types", default="")
ap.add_argument("--dens", type=float, default=18.0, help="bits per um across a band (V/H usable ~44 tracks/um)")
ap.add_argument("--km", type=float, default=8.64, help="core keep-off margin for stations (um)")
ap.add_argument("--colsep", type=float, default=8.64)
ap.add_argument("--reach", type=float, default=405.0)
ap.add_argument("--face-um", type=float, default=32.4)
ap.add_argument("--wcol", type=float, default=1.5, help="cost per um of V run per bundle already in the column")
ap.add_argument("--wedge", type=float, default=0.6, help="cost per um of V run hugging the core edge")
ap.add_argument("--edge-um", type=float, default=10.8)
ap.add_argument("--band", action="append", default=[],
                help="TYPE_RE:band=x0,y0,x1,y1 landing band rect move (positions only), repeatable")
ap.add_argument("--wring", type=float, default=0.8)
ap.add_argument("--ring-grow", type=float, default=21.6)
ap.add_argument("--hjog2", action="store_true", help="also try 2-jog H routes (under/over a ring field)")
ap.add_argument("--legacy", action="store_true", help="first-run cost (column load x len/100 x 4, fixed detour rows)")
ap.add_argument("--vcol", default="", help="slot=x: the slot's V run is forced onto column x (deterministic lane plan)")
ap.add_argument("--side", default="", help="slot=E|W: corner/detour lanes forced to one side of the core")
ap.add_argument("--tries", type=int, default=12)
ap.add_argument("--bit-hop", type=float, default=394.9, help="per-bit hop limit = ft_spread budget 405 x .98 - 2")
ap.add_argument("--keep-sites", default="", help="slots whose plan sites/regs are kept unchanged")
a = ap.parse_args()
SRC = Path(a.src)
for p_ in (str(SRC / "tools" / "die_plan"), str(SRC)):
    sys.path.insert(0, p_)
import schema as S                       # noqa: E402
import gen_phys                          # noqa: E402
from tools.die_trial.legal_sites import RowAllocator   # noqa: E402

G = 8.64
CELL = (1.404, .27)
KEEPOFF = 2.0
CORE_MARGIN = 4.32
BUDGET = a.reach * .98 - 2.0
raw = open(a.base, "rb").read()
P = json.loads(raw)
T = P["partition_types"]
names = [n for n in T if a.match in n and len(T[n].get("hard_cores") or []) == 1]
if a.types:
    names = [n for n in names if n in a.types.split(",")]
keep = set(filter(None, a.keep_sites.split(",")))
SIDE = dict(kv.split("=") for kv in filter(None, a.side.split(",")))
VCOL = {k: float(v) for k, v in (kv.split("=") for kv in filter(None, a.vcol.split(",")))}


def pts_of(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("window_um", "outline_um", "rect_um", "origin_um", "resized_from_um", "origin_rect_um",
                     "ft_slots"):
                continue
            yield from pts_of(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(x, (int, float)) for x in o):
            yield path, o
        else:
            for i, v in enumerate(o):
                yield from pts_of(v, f"{path}[{i}]")


edits = []
# ---- 1. core shift (before the Plan object is built, so pins / boxes see the new core)
for tn in names:
    t = T[tn]
    c = t["hard_cores"][0]
    (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
    if a.dx:
        nx = round(x0 - a.dx, 4)
        assert abs(nx / G - round(nx / G)) < 1e-6, nx
        # the vacated band (make_sc.py rule) PLUS the core's own pins/taps inside or on the old outline move with it
        lo, hi = nx - 4.32, x0 + w + 0.5
        moved = 0
        for pa, xy in pts_of(t):
            if pa.startswith(".hard_cores"):
                continue
            if lo <= xy[0] <= hi and y0 - 4.32 <= xy[1] <= y0 + h + 4.32:
                xy[0] = round(xy[0] - a.dx, 4)
                moved += 1
        c["origin_um"] = [nx, y0]
        edits.append(dict(type=tn, core_was=[x0, y0], core_now=[nx, y0], points_shifted=moved))

import re as _re
for spec in a.band:
    tre, _, rest = spec.partition(":")
    bn, _, rc = rest.partition("=")
    rc = [float(v) for v in rc.split(",")]
    for tn in names:
        if not _re.search(tre, tn):
            continue
        bd = T[tn]["clock"]["landing_contract"]["bands"][bn]
        edits.append(dict(type=tn, band=bn, was=bd["rect_um"], now=rc))
        bd["rect_um"] = rc
PL = S.Plan(P)


def seg_len(r):
    return sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(r, r[1:]))


def at_len(r, s):
    for p, q in zip(r, r[1:]):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        if s <= L + 1e-9:
            f = s / L if L > 0 else 0
            return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f), ("H" if abs(q[0] - p[0]) > abs(q[1] - p[1]) else "V")
        s -= L
    p, q = r[-2], r[-1]
    return tuple(r[-1]), ("H" if abs(q[0] - p[0]) > abs(q[1] - p[1]) else "V")


def inside(p, K):
    return K[0] < p[0] < K[2] and K[1] < p[1] < K[3]


def vseg_hits(r, K):
    """V segment of the route crosses the core keep-off (wire on M3/M5 blocked; only M7 over the core)."""
    for p, q in zip(r, r[1:]):
        if abs(p[0] - q[0]) < 1e-6 and K[0] < p[0] < K[2]:
            lo, hi = min(p[1], q[1]), max(p[1], q[1])
            if hi - lo > 1e-6 and hi > K[1] and lo < K[3]:
                return True
    return False


for tn in names:
    t = T[tn]
    W, H = map(float, t["outline_um"])
    c = t["hard_cores"][0]
    (cx0, cy0), (cw, ch) = c["origin_um"], c["outline_um"]
    K = (cx0 - a.km, cy0 - a.km, cx0 + cw + a.km, cy0 + ch + a.km)
    RINGS = {bn_: bd_["rect_um"] for bn_, bd_ in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands")
                                                   or {}).items() if bd_.get("rect_um")}
    RB = 10.8
    RNX, RNY = int(math.ceil(W / RB)), int(math.ceil(H / RB))
    occm = np.zeros((RNY, RNX), bool)
    occm[int(K[1] // RB + 1):int(math.ceil(K[3] / RB)) - 1, int(K[0] // RB + 1):int(math.ceil(K[2] / RB)) - 1] = True

    def free_area(r):
        a0, b0 = int(max(0, r[0]) // RB), int(max(0, r[1]) // RB)
        a1, b1 = int(math.ceil(min(W, r[2]) / RB)), int(math.ceil(min(H, r[3]) / RB))
        return float((~occm[b0:b1, a0:a1]).sum()) * RB * RB
    RH = np.zeros((RNY, RNX)); RV = np.zeros((RNY, RNX))
    RING_OWN = {}
    for bn_, bd_ in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).items():
        r_ = bd_.get("rect_um")
        if not r_:
            continue
        flops = float(bd_.get("padded_data_storage_flops") or bd_.get("live_data_storage_flops") or 0)
        bits = float(bd_.get("width") or 0)
        need = max((r_[2] - r_[0]) * (r_[3] - r_[1]), flops * 10.0)
        rr = list(map(float, r_))
        for _ in range(2000):
            if free_area(rr) >= need:
                break
            best_c = None
            for sd in (0, 1, 2, 3):
                cand = list(rr)
                cand[sd] += -RB if sd < 2 else RB
                cand = [max(0.0, cand[0]), max(0.0, cand[1]), min(W, cand[2]), min(H, cand[3])]
                if cand == rr:
                    continue
                strip = free_area(cand) - free_area(rr)
                area_add = (cand[2] - cand[0]) * (cand[3] - cand[1]) - (rr[2] - rr[0]) * (rr[3] - rr[1])
                if area_add <= 0 or strip < 0.5 * area_add:
                    continue
                w_, h_ = cand[2] - cand[0], cand[3] - cand[1]
                asp = max(w_, h_) / max(min(w_, h_), 1e-6)
                if best_c is None or asp < best_c[0]:
                    best_c = (asp, cand)
            if best_c is None:
                break
            rr = best_c[1]
        hgt, wid = max(rr[3] - rr[1], RB), max(rr[2] - rr[0], RB)
        m_ = np.zeros((RNY, RNX))
        m_[int(rr[1] // RB):int(math.ceil(rr[3] / RB)), int(rr[0] // RB):int(math.ceil(rr[2] / RB))] = 1.0
        RH += m_ * (2.5 * bits / hgt) / 41.7
        RV += m_ * (2.5 * bits / wid) / 44.6
        RING_OWN[bn_] = (m_ * (2.5 * bits / hgt) / 41.7, m_ * (2.5 * bits / wid) / 44.6)
    pins = {}
    for bn, i, _, x, y, _f in gen_phys.type_pins(PL, tn):
        pins[(bn, i)] = (x, y)
    boxes = list(S.placed_macro_boxes(t, halo=KEEPOFF).values())
    m = CORE_MARGIN
    alloc = RowAllocator((m, m, W - m, H - m), blocked=boxes, cell_size=CELL, column_pitch=2.16, row_pitch=.27,
                         origin=(m, m))
    for s in t["ft_slots"]:
        if s["name"] in keep and s.get("bit_sites_um"):
            cw_, ch_ = s.get("bit_site_cell_um") or CELL
            for st in s["bit_sites_um"]:
                for x, y in st:
                    alloc.reserve_rectangle((x, y, x + cw_, y + ch_))
    colload = np.zeros(int(math.ceil(W)) + 1)        # V bits per um column (1-um bins)
    rowload = np.zeros(int(math.ceil(H)) + 1)
    rep = []
    order = sorted([s for s in t["ft_slots"] if s["name"] not in keep], key=lambda s: -int(s["width"]))
    for s in order:
        nm, wd, k = s["name"], int(s["width"]), int(s.get("stations", 1))
        try:
            A = np.array([pins[(nm + "_i", i)] for i in range(wd + 1)], float)
            B = np.array([pins[(nm + "_o", i)] for i in range(wd + 1)], float)
        except KeyError as ex:
            rep.append(dict(slot=nm, skipped=f"pin missing {ex}"))
            continue
        a_, b_ = tuple(A.mean(0)), tuple(B.mean(0))
        fi, fo = s["in_face"], s["out_face"]
        band = wd / a.dens                       # um the bundle needs across its travel direction
        cands = []
        ys = np.arange(G, H - G, G)
        xs = np.arange(G, W - G, G)

        def vcost(x, y0_, y1_):
            # column load the run would share (bits/um / dens = how many bundles already sit there) x run length,
            # plus the core edge strip (GRT halves M3-M7 within 2 gcells of the macro, and the band must not touch K)
            lo, hi = int(max(0, x - band / 2)), int(min(W, x + band / 2)) + 1
            ln = abs(y1_ - y0_)
            ov = min(max(0.0, hi - lo), 1e9)
            share = float(colload[lo:hi].mean()) / a.dens if hi > lo else 0.0
            edge = 0.0
            ylo, yhi = min(y0_, y1_), max(y0_, y1_)
            if yhi > K[1] and ylo < K[3]:
                d_edge = min(abs(x - K[0]), abs(x - K[2]))
                if d_edge < band / 2 + a.edge_um:
                    edge = (band / 2 + a.edge_um - d_edge) / (band / 2 + a.edge_um)
                if (x + band / 2 > W - CORE_MARGIN or x - band / 2 < CORE_MARGIN):
                    edge += 1.0
            return (a.wcol * share + a.wedge * edge) * ln

        def hcost(y, x0_, x1_):
            lo, hi = int(max(0, y - band / 2)), int(min(H, y + band / 2)) + 1
            share = float(rowload[lo:hi].mean()) / a.dens if hi > lo else 0.0
            return a.wcol * share * abs(x1_ - x0_)

        own = {nm + "_i", nm + "_o"}
        OWNH = sum((RING_OWN[o_][0] for o_ in own if o_ in RING_OWN), np.zeros((RNY, RNX)))
        OWNV = sum((RING_OWN[o_][1] for o_ in own if o_ in RING_OWN), np.zeros((RNY, RNX)))

        def ringcost(p, q):
            # route_supply ring model replica (grown ring areas, 2.5 tracks/bit across them): the run pays the ring
            # load ratio of every bin it crosses, excluding its own rings
            c_ = 0.0
            if abs(p[0] - q[0]) < 1e-6:
                i_ = int(min(max(p[0] // RB, 0), RNX - 1))
                j0_, j1_ = sorted((int(min(max(p[1] // RB, 0), RNY - 1)), int(min(max(q[1] // RB, 0), RNY - 1))))
                c_ = float((RV[j0_:j1_ + 1, i_] - OWNV[j0_:j1_ + 1, i_]).sum()) * RB
            elif abs(p[1] - q[1]) < 1e-6:
                j_ = int(min(max(p[1] // RB, 0), RNY - 1))
                i0_, i1_ = sorted((int(min(max(p[0] // RB, 0), RNX - 1)), int(min(max(q[0] // RB, 0), RNX - 1))))
                c_ = float((RH[j_, i0_:i1_ + 1] - OWNH[j_, i0_:i1_ + 1]).sum()) * RB
            return a.wring * c_

        def rcost_legacy(r, kind):
            c_ = 0.0
            for p, q in zip(r, r[1:]):
                if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) > 1e-6:
                    lo, hi = int(max(0, p[0] - band / 2)), int(min(W, p[0] + band / 2)) + 1
                    c_ += float(colload[lo:hi].mean()) * abs(q[1] - p[1]) / 100.0
            if kind == "VHV":
                lo, hi = int(max(0, r[1][1] - band / 2)), int(min(H, r[1][1] + band / 2)) + 1
                c_ += float(rowload[lo:hi].mean()) * abs(r[2][0] - r[1][0]) / 400.0
            return 4.0 * c_

        def rcost(r):
            c_ = 0.0
            for p, q in zip(r, r[1:]):
                if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) > 1e-6:
                    c_ += vcost(p[0], p[1], q[1])
                elif abs(p[1] - q[1]) < 1e-6 and abs(p[0] - q[0]) > 1e-6:
                    c_ += hcost(p[1], p[0], q[0])
                c_ += ringcost(p, q)
            return c_
        routes = []
        for xm in xs:
            routes.append(([a_, (xm, a_[1]), (xm, b_[1]), b_], "HVH"))
        for ym in ys:
            routes.append(([a_, (a_[0], ym), (b_[0], ym), b_], "VHV"))
        if fi in "EW" and fo in "EW" and a.hjog2:
            x2s = sorted({round(K[0] - G, 2), round(min(W - 8.0, (K[2] + W) / 2), 2)} | set(map(float, xs[::8])))
            for x1 in xs[::4]:
                for ym in ys[::2]:
                    for x2 in x2s:
                        routes.append(([a_, (x1, a_[1]), (x1, ym), (x2, ym), (x2, b_[1]), b_], "HVHVH"))
        tops = [y for y in (K[3] + G * j for j in (1, 3, 5, 7, 9)) if y < H - 40]
        bots = [y for y in (K[1] - G * j for j in (1, 3, 5, 7, 9)) if y > 40]
        if a.legacy:
            tops, bots = [K[3] + G], [K[1] - G]
        if VCOL.get(nm) is not None:
            tops = [y for y in (K[3] + G * j for j in range(1, 12)) if y < H - 40]
            bots = [y for y in (K[1] - G * j for j in range(1, 60, 2)) if y > 40]
        side = SIDE.get(nm)
        vc = VCOL.get(nm)
        if vc is not None:
            routes = []
        for xsx in ([vc] if vc is not None else list(xs if a.legacy else xs[::2])):
            if K[0] < xsx < K[2]:
                continue
            if side == "E" and xsx < K[2] or side == "W" and xsx > K[0]:
                continue
            for y1 in tops + bots:
                for y2 in (bots if y1 in tops else tops):
                    routes.append(([a_, (a_[0], y1), (xsx, y1), (xsx, y2), (b_[0], y2), b_], "DET"))
                routes.append(([a_, (xsx, a_[1]), (xsx, y1), (b_[0], y1), b_], "HVHV"))
                routes.append(([a_, (a_[0], y1), (xsx, y1), (xsx, b_[1]), b_], "VHVH"))
        for r, kind in routes:
            if side and kind in ("HVH", "VHV") and vseg_hits(r, K):
                continue
            cands.append((r, kind, None))
        valid = []
        why = {}
        for r, kind, cc in cands:
            r = [tuple(map(float, p)) for p in r]
            if vseg_hits(r, K):
                why["vhit"] = why.get("vhit", 0) + 1
                continue
            cc = rcost_legacy(r, kind) if a.legacy else rcost(r)
            if any(not (-1e-6 <= p[0] <= W + 1e-6 and -1e-6 <= p[1] <= H + 1e-6) for p in r):
                why["bounds"] = why.get("bounds", 0) + 1
                continue
            if vseg_hits(r, K):
                why["vhit"] = why.get("vhit", 0) + 1
                continue
            L = seg_len(r)
            st = []
            sl = []
            okr = True
            for j in range(1, k):
                s0 = L * j / k
                p, d = at_len(r, s0)
                sj = s0
                if inside(p, K):
                    ok = None
                    for dl in np.arange(G / 2, L, G / 2):
                        for sg in (-1, 1):
                            s2 = min(max(s0 + sg * dl, 0), L)
                            q, d2 = at_len(r, s2)
                            if not inside(q, K):
                                ok = (q, d2, s2)
                                break
                        if ok:
                            break
                    if ok is None:
                        okr = False
                        break
                    p, d, sj = ok
                st.append((p, d))
                sl.append(sj)
            if not okr or sl != sorted(sl):
                why["order"] = why.get("order", 0) + 1
                continue
            hops = np.diff([0.0] + sl + [L])
            if hops.max() > BUDGET:
                why["hop"] = why.get("hop", 0) + 1
                continue
            # face penalty: a run parallel to and within FACE_UM of the outline (landing rings / face pins live there)
            fp = 0.0
            for p, q in (zip(r[1:-1], r[2:-1]) if a.legacy and len(r) > 3 else [] if a.legacy else zip(r, r[1:])):
                ln = abs(q[0] - p[0]) + abs(q[1] - p[1])
                if abs(p[0] - q[0]) < 1e-6 and (p[0] < a.face_um or p[0] > W - a.face_um):
                    fp += ln
                if abs(p[1] - q[1]) < 1e-6 and (p[1] < a.face_um or p[1] > H - a.face_um):
                    fp += ln
            score = L + cc + 3.0 * fp if not a.legacy else L + cc + 3.0 * fp + 0.5 * max(0.0, hops.max() - 300.0)
            valid.append((score, r, kind, st, hops, L, cc))
        valid.sort(key=lambda v: v[0])
        if not valid:
            rep.append(dict(slot=nm, skipped="no legal route", why=why, a=a_, b=b_, k=k))
            continue
        ax_in = 0 if fi in "NS" else 1
        order_b = np.argsort(A[:, ax_in], kind="stable")
        span_in = float(np.ptp(A[:, ax_in]))
        ax_out = 0 if fo in "NS" else 1
        span_out = float(np.ptp(B[:, ax_out]))

        def make_sites(st, narrow):
            sites = []
            for j, (p, d) in enumerate(st, 1):
                f = j / k
                perp = 1 if d == "H" else 0                  # band axis: y for H travel, x for V travel
                ext = band if narrow else min(max(band, (1 - f) * span_in + f * span_out), max(band, 120.0))
                n = wd + 1
                pitch_perp = 0.27 if perp == 1 else 2.16
                per_line = max(1, int(ext / pitch_perp))
                lines = int(math.ceil(n / per_line))
                pitch_along = 2.16 if perp == 1 else 0.27
                tgt = np.zeros((n, 2))
                for rank, bi in enumerate(order_b):
                    li, pi = divmod(rank, per_line)
                    u = (pi + 0.5) / per_line - 0.5
                    v = (li - (lines - 1) / 2) * pitch_along
                    tgt[bi] = (p[0] + v, p[1] + u * ext) if perp == 1 else (p[0] + u * ext, p[1] + v)
                out = np.zeros_like(tgt)
                for bi in np.argsort(tgt[:, perp], kind="stable"):
                    q, _ = alloc.allocate(tuple(tgt[bi]), 1, max_radius_um=120.0)
                    out[bi] = q[0]
                sites.append([[round(float(x - CELL[0] / 2), 6), round(float(y - CELL[1] / 2), 6)] for x, y in out])
            chain = [A] + [np.array(sv) + np.array(CELL) / 2 for sv in sites] + [B]
            return sites, [float(np.abs(q - p).sum(1).max()) for p, q in zip(chain, chain[1:])]
        pick = None
        fallback = None
        tried = 0
        for v in valid[:a.tries]:
            for narrow in (False, True):
                base_used = set(alloc.used)
                sites, hop_bits = make_sites(v[3], narrow)
                tried += 1
                if max(hop_bits) <= a.bit_hop:
                    pick = (v, sites, hop_bits, narrow)
                    break
                if fallback is None or max(hop_bits) < max(fallback[2]) - 1e-9:
                    fallback = (v, sites, hop_bits, narrow)
                alloc.used = base_used
            if pick:
                break
        if pick is None:
            v, _, _, narrow = fallback
            sites, hop_bits = make_sites(v[3], narrow)
            pick = (v, sites, hop_bits, narrow)
        (_, r, kind, st, hops, L, cc), sites, hop_bits, narrow = pick
        for p, q in zip(r, r[1:]):
            if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) > 1:
                lo, hi = int(max(0, p[0] - band / 2)), int(min(W, p[0] + band / 2)) + 1
                colload[lo:hi] += wd / max(hi - lo, 1)
            elif abs(p[1] - q[1]) < 1e-6 and abs(p[0] - q[0]) > 1:
                lo, hi = int(max(0, p[1] - band / 2)), int(min(H, p[1] + band / 2)) + 1
                rowload[lo:hi] += wd / max(hi - lo, 1)
        s["regs_um"] = [list(s["regs_um"][0])] + [[round(p[0], 3), round(p[1], 3)] for p, _ in st]
        s["bit_site_cell_um"] = list(CELL)
        s["bit_sites_um"] = sites
        rep.append(dict(slot=nm, width=wd, stations=k, route=kind, route_um=round(L, 1), narrow=narrow, tried=tried,
                        waypoints=[[round(x, 1), round(y, 1)] for x, y in r],
                        hops_um=[round(float(h_), 1) for h_ in hops], bit_hops_max_um=[round(h_, 1) for h_ in hop_bits],
                        over_budget=[i for i, h_ in enumerate(hop_bits) if h_ > a.reach]))
    edits.append(dict(type=tn, slots=rep))

s_ = json.dumps(P, indent=1)
open(a.out, "w").write(s_)
sha = hashlib.sha256(s_.encode()).hexdigest()
json.dump(dict(tool="SC-REFLOOR-1 make_refloor.py", base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha,
               args=vars(a), edits=edits), open(a.delta, "w"), indent=1)
for e in edits:
    if "slots" in e:
        bad = [r for r in e["slots"] if r.get("over_budget") or r.get("skipped")]
        print(e["type"], "slots", len(e["slots"]), "problems", [(r["slot"], r.get("over_budget"), r.get("skipped"),
                                                                  r.get("bit_hops_max_um")) for r in bad])
    else:
        print(e)
print("sha256", sha[:12])
