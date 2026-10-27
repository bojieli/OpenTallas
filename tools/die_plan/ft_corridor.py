#!/usr/bin/env python3
"""Corridor FT siting for partitions whose core field leaves only narrow channels (S81 svc rs grids, col frames).

ft_sites.place() treats every hard core (+ 8.64-um halo) as a wall for both stations and wires: on a regular core grid
with 15-17-um channels that leaves only the perimeter margins, so whole bundles (500-1100 b) are routed around the
field and each station's bits are packed at one point (S81 PROTO G2 10-25: 305k GRT overflow in a 34-um margin).

Industry practice instead: the bundle runs STRAIGHT over the cores on the free upper layers (cores own M1-M5; M6/M7
are free over them, ft demand checked <= 0.6 of those tracks), and the pipeline registers sit in the inter-core
channels the corridor crosses, one bit per legal site spread along the channel in bit order (a register column,
not a stacked clump).  This tool does that, per ft slot:

  path      straight (opposite faces, windows aligned), L (adjacent faces) or Z (opposite faces, offset windows;
            jog over the core field) between the in- and out-window centres; bit lanes keep their window offsets;
  stations  the slot's registered depth is kept (static schedule: slot['stations'] unchanged); the k-1 internal
            station positions are chosen on the path by DP among positions where the whole bit band is in free space
            (channels / gaps crossing the corridor), minimising the deviation from even spacing with every hop
            <= the reach budget;
  bits      each bit gets the nearest free row-legal site to its lane point at the station (RowAllocator, cores with
            a 1.08-um keep-off, no halo wall), so a station is a column across the channel in bit order.

Only these types' ft_slots regs_um / bit_sites_um change; outlines, cores, windows, pins, stations do not.

    ft_corridor.py PLAN --types a,b [--out PLAN] [--ledger L.json] [--jog type/slot=y_or_x ...]
                   [--reach UM] [--margin F] [--keep-going]
hop budget = reach x margin - 2 um (default 405 x 0.98 -> 394.9 um, an internal margin); the KV hop gate is the
measured 405-um repeated reach (COORD GEOM-21 10-27) -> --margin 1.  --keep-going sites every type it can and lists the
types that fail; a failed type is left unchanged (no partial siting inside a type).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
from gen_phys import type_pins  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402

INWARD = dict(N=(0, -1), S=(0, 1), E=(-1, 0), W=(1, 0))
CELL = (1.404, .27)
KEEPOFF = 1.08          # flop keep-off from a core edge (pin access ring), not a wall for the corridor
MAX_PROJ = 40.0         # a lane point may move at most this far to reach free space at a station
PROJ_W = 4.0            # DP weight of the mean projection distance (prefer stations fully in a channel)
SLACK = 10.0            # allocator displacement allowance per hop
LANE_UM_PER_BIT = 0.0458  # Z-jog lane width per bit: 0.6 of the M5 (0.048) + M7 (0.064) tracks (ASAP7 GRT pitches)
LANE_SPAN = (0.15, 0.85)
LANE_PACK = "bin"         # bin: lanes binned into core/leg-free intervals; walk: one even sequence over the span  # jog lanes of one type are spread over this fraction of the jog axis (widened if too narrow)


def _face_coord(face, xy):
    """coordinate along the face (x on N/S, y on E/W)."""
    return xy[0] if face in "NS" else xy[1]


def build_path(fin, fout, ca, cb, w, h, jog=None):
    """centre polyline (list of points) from the in-window centre ca to the out-window centre cb."""
    ca, cb = np.asarray(ca, float), np.asarray(cb, float)
    if S.OPP[fin] == fout:
        if abs(_face_coord(fin, ca) - _face_coord(fin, cb)) < 1.0:
            return [ca, cb]
        if fin in "NS":
            y = h / 2 if jog is None else jog
            return [ca, np.array([ca[0], y]), np.array([cb[0], y]), cb]
        x = w / 2 if jog is None else jog
        return [ca, np.array([x, ca[1]]), np.array([x, cb[1]]), cb]
    if fin == fout:
        raise ValueError("same-face slot")
    # adjacent faces: first leg leaves fin perpendicular, turns once onto the out-window coordinate
    corner = np.array([ca[0], cb[1]]) if fin in "NS" else np.array([cb[0], ca[1]])
    return [ca, corner, cb]


def _cum(path):
    seg = [float(np.abs(b - a).sum()) for a, b in zip(path, path[1:])]
    return seg, np.concatenate([[0.0], np.cumsum(seg)])


def point_dir(path, s):
    seg, cum = _cum(path)
    i = min(int(np.searchsorted(cum, s, side="right")) - 1, len(seg) - 1)
    i = max(i, 0)
    a, b = path[i], path[i + 1]
    d = (b - a) / max(seg[i], 1e-9)
    return a + d * (s - cum[i]), d


def in_boxes(pts, boxes):
    hit = np.zeros(len(pts), bool)
    for x0, y0, x1, y1 in boxes:
        hit |= (pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1)
    return hit


def place_slot(slot, a, b, fin, fout, w, h, boxes, alloc, budget, jog=None, step=2.0, look=8.0, band=None,
               jog_lane=None):
    """retry with a tighter hop target when the bit spread (L corners, lane offsets) exceeds the slack."""
    base = set(alloc.used)
    for proj in (MAX_PROJ, 3 * MAX_PROJ, 6 * MAX_PROJ):
        extra = 0.0
        for _ in range(12):
            alloc.used = set(base)
            try:
                return _place_slot(slot, a, b, fin, fout, w, h, boxes, alloc, budget, jog, step, look, extra, proj, band,
                                   jog_lane)
            except HopError as e:
                extra += e.excess + 2.0
            except NoChain:
                break
    raise ValueError(f"{slot['name']}: no chain within {budget:.1f} um after tightening by {extra:.0f} um")


class HopError(ValueError):
    def __init__(self, excess):
        super().__init__(excess)
        self.excess = excess


def project(pts, boxes, bounds):
    """nearest free point (outside every keep-off box, inside bounds) for each point: rectangles only, so the answer
    is the point itself or its exit through one side of the box it is in (two passes for abutting boxes)."""
    x0, y0, x1, y1 = bounds
    q = np.column_stack((np.clip(pts[:, 0], x0, x1), np.clip(pts[:, 1], y0, y1)))
    for _ in range(3):
        moved = False
        for bx0, by0, bx1, by1 in boxes:
            inside = (q[:, 0] > bx0) & (q[:, 0] < bx1) & (q[:, 1] > by0) & (q[:, 1] < by1)
            if not inside.any():
                continue
            moved = True
            p = q[inside]
            opts = np.stack([np.column_stack((np.full(len(p), bx0 - .01), p[:, 1])),
                             np.column_stack((np.full(len(p), bx1 + .01), p[:, 1])),
                             np.column_stack((p[:, 0], np.full(len(p), by0 - .01))),
                             np.column_stack((p[:, 0], np.full(len(p), by1 + .01)))])
            dist = np.abs(opts - p[None]).sum(axis=2)
            for k_, lim in enumerate(((x0, None), (None, x1), (y0, None), (None, y1))):
                c = opts[k_][:, k_ // 2]
                if lim[0] is not None:
                    dist[k_][c < lim[0]] = np.inf
                if lim[1] is not None:
                    dist[k_][c > lim[1]] = np.inf
            pick = np.argmin(dist, axis=0)
            q[inside] = opts[pick, np.arange(len(p))]
        if not moved:
            break
    bad = in_boxes(q, boxes)
    return q, np.where(bad, np.inf, np.abs(q - pts).sum(axis=1))


class NoChain(ValueError):
    pass


def _band_offsets(pts, c, band, axis):
    """lane offsets re-mapped linearly (bit order kept) into the corridor band [lo, hi] along `axis`."""
    off = pts - c
    if band is None:
        return off, c
    v = pts[:, axis]
    lo, hi = band
    t = (v - v.min()) / max(np.ptp(v), 1e-9)
    nc = c.copy()
    nc[axis] = (lo + hi) / 2
    off = np.zeros_like(pts)
    off[:, axis] = lo + t * (hi - lo) - nc[axis]
    return off, nc


def _place_slot(slot, a, b, fin, fout, w, h, boxes, alloc, budget, jog, step, look, extra, max_proj, band=None,
                jog_lane=None):
    """returns (sites per internal station [(width+1)x2 centres], centroids, path, ledger dict)."""
    k = int(slot["stations"])
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    off_in, off_out = a - ca, b - cb
    if band is not None:
        # corridor band (straight legs only): the bundle runs inside [lo, hi] across the type, compressing once at
        # each end, so every station column sits where the band is free of cores
        axis = 1 if fin in "EW" else 0
        off_in, ca = _band_offsets(a, ca, band, axis)
        off_out, cb = _band_offsets(b, cb, band, axis)
    path = build_path(fin, fout, ca, cb, w, h, jog)
    seg, cum = _cum(path)
    L = cum[-1]
    nb = len(a)

    zjog = len(path) == 4 and jog_lane is not None
    if zjog:
        # GEOM-23 10-27: on the jog of a Z path the bundle keeps its own lane (width jog_lane um): each bit's window
        # offset is rotated with the bundle direction (no crossing at the turn) and scaled into the lane, instead of
        # every bit collapsing onto the jog line (hub_Ei: 3,187 b on one ~20-um column)
        d1 = (path[1] - path[0]) / max(seg[0], 1e-9)
        d2 = (path[2] - path[1]) / max(seg[1], 1e-9)
        c, sn = float(d1 @ d2), float(d1[0] * d2[1] - d1[1] * d2[0])
        o = off_in @ np.array([[c, -sn], [sn, c]]).T
        span = float(np.ptp(o, axis=0).max())
        off_jog = o * (jog_lane / span if span > 1e-9 else 0.0)
        # each bit runs its own Manhattan polyline: in pin -> turn at its lane coordinate -> out-window row -> out pin,
        # and a station sits at the same FRACTION of every bit's own length (equal per-bit hops, no corner overshoot)
        ax = 0 if fin in "EW" else 1                  # coordinate of the jog leg
        t_i = path[1][ax] + off_jog[:, ax]
        P = np.stack([a, a.copy(), b.copy(), b], axis=1)
        P[:, 1, ax] = t_i
        P[:, 2, ax] = t_i
        Pseg = np.abs(np.diff(P, axis=1)).sum(axis=2)          # (nb, 3)
        Pcum = np.concatenate([np.zeros((nb, 1)), np.cumsum(Pseg, axis=1)], axis=1)

    def bit_points(s):
        u = (s / L) * Pcum[:, -1]
        j = np.clip((u >= Pcum[:, 1]).astype(int) + (u >= Pcum[:, 2]), 0, 2)
        r = np.arange(nb)
        f = (u - Pcum[r, j]) / np.maximum(Pseg[r, j], 1e-9)
        return P[r, j] + (P[r, j + 1] - P[r, j]) * f[:, None]

    def lane_points(s):
        if zjog:
            return bit_points(s)
        p, d = point_dir(path, s)
        last = s >= (cum[-2] if len(cum) > 2 else 0.0)
        off = off_out if last else off_in
        perp = np.array([abs(d[1]), abs(d[0])])
        return p + off * perp

    if k <= 1:
        return [], [], path, dict(len_um=round(L, 1), stations=k)
    bounds = (4.32 + 1, 4.32 + 1, w - 4.32 - 1, h - 4.32 - 1)
    cs, Q, Dm = [], [], []
    for s in np.arange(step, L - step / 2, step):
        q, dist = project(lane_points(s), boxes, bounds)
        if dist.max() <= max_proj:
            cs.append(s)
            Q.append(q)
            Dm.append(float(dist.mean()))
    cands = np.array(cs)
    Q = np.array(Q)
    Dm = np.array(Dm)
    n = len(cands)
    if n < k - 1:
        raise NoChain(f"{slot['name']}: {n} free station positions on a {L:.0f}-um path, need {k - 1}")
    ideal = L / k
    # allocator allowance: SLACK, but never more than the room between the even hop and the budget less 3 um (2-um
    # candidate grid + 1); the
    # final per-bit hop check against `budget` (HopError -> retry tighter) stays the gate
    H = budget - min(SLACK, max(1.0, budget - ideal - 3.0)) - extra
    INF = 1e18
    pen = PROJ_W * Dm ** 2
    hop_a = np.abs(Q - a[None]).sum(axis=2).max(axis=1)
    hop_b = np.abs(Q - b[None]).sum(axis=2).max(axis=1)
    cost = np.full((k - 1, n), INF)
    prev = np.full((k - 1, n), -1, int)
    cost[0] = np.where(hop_a <= H, (hop_a - ideal) ** 2 + pen, INF)
    for i in range(1, n):
        lo = np.searchsorted(cands, cands[i] - H - 1)
        if lo >= i:
            continue
        hop = np.abs(Q[lo:i] - Q[i][None]).sum(axis=2).max(axis=1)
        ok = (hop <= H) & (cands[i] - cands[lo:i] > 2.0)
        add = np.where(ok, (hop - ideal) ** 2 + pen[i], INF)
        for j in range(1, k - 1):
            c = cost[j - 1, lo:i] + add
            m = int(np.argmin(c))
            if c[m] < INF:
                cost[j, i] = c[m]
                prev[j, i] = lo + m
    final = cost[k - 2] + np.where(hop_b <= H, (hop_b - ideal) ** 2, INF)
    i = int(np.argmin(final))
    if final[i] >= INF:
        raise NoChain(f"{slot['name']}: no station chain with hops <= {H:.0f} um on a {L:.0f}-um path")
    chosen = [i]
    for j in range(k - 2, 0, -1):
        i = prev[j, i]
        chosen.append(int(i))
    chosen = chosen[::-1]
    sites, cents = [], []
    for c in chosen:
        q = Q[c]
        d = point_dir(path, cands[c])[1]
        perp = np.array([abs(d[1]), abs(d[0])])
        out = np.zeros((nb, 2))
        for bi in np.argsort(q @ perp):
            p, _ = alloc.allocate(q[bi], 1, max_radius_um=40.0)
            out[bi] = p[0]
        sites.append(out)
        cents.append(out.mean(axis=0))
    chain = [a, *sites, b]
    hops = [float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])]
    if max(hops) > budget + 1e-6:
        raise HopError(max(hops) - budget)
    disp = max(float(np.abs(sites[j] - Q[c]).sum(axis=1).max()) for j, c in enumerate(chosen))
    return sites, cents, path, dict(len_um=round(L, 1), stations=k,
                                    positions_um=[round(float(cands[c]), 1) for c in chosen],
                                    proj_mean_um=[round(float(Dm[c]), 1) for c in chosen],
                                    max_proj_um=max_proj, hops_um=[round(x, 1) for x in hops], max_alloc_disp_um=round(disp, 2),
                                    path=[[round(float(v), 2) for v in p] for p in path])


def jog_lanes(ty, pins, w, h, fixed=None):
    """GEOM-23 10-27: one jog lane per Z slot (opposite faces, offset windows) instead of every slot jogging on the
    type's midline.  Lane width = (width + 1) x LANE_UM_PER_BIT; the lanes of one jog axis are packed in order of the
    in-window centre over LANE_SPAN of that axis (widened to the full outline minus 8.64 um when they do not fit),
    with equal gaps.  Returns {slot: (jog coordinate, lane width)}; a slot with an explicit --jog keeps it."""
    fixed = fixed or {}
    groups = {}
    for slot in ty.get("ft_slots", []):
        fin, fout, name = slot["in_face"], slot["out_face"], slot["name"]
        if S.OPP.get(fin) != fout:
            continue
        wd = slot["width"] + 1
        ca = np.mean([pins[(name + "_i", i)] for i in range(wd)], axis=0)
        cb = np.mean([pins[(name + "_o", i)] for i in range(wd)], axis=0)
        if abs(_face_coord(fin, ca) - _face_coord(fin, cb)) < 1.0:
            continue
        axis = 1 if fin in "NS" else 0           # NS slots jog along y, EW slots along x
        groups.setdefault(axis, []).append((_face_coord(fin, ca), name, wd * LANE_UM_PER_BIT))
    # KV-PLAN-DELTA-2 10-27: the vertical (horizontal) legs of the other slots of the type -- L slots and straight
    # slots with a face on the jog axis -- occupy their window span (at least their own lane width) on that axis;
    # Z lanes are packed into the remaining free span only, so a Z jog never stacks onto another bundle's leg
    occ = {0: [], 1: []}
    for slot in ty.get("ft_slots", []):
        fin, fout, name = slot["in_face"], slot["out_face"], slot["name"]
        if name in {n for g in groups.values() for _, n, _ in g}:
            continue
        wd = slot["width"] + 1
        for face, nm in ((fin, "_i"), (fout, "_o")):
            axis = 0 if face in "NS" else 1      # an N/S face pin window = a vertical leg at those x
            v = [pins[(name + nm, i)][axis] for i in range(wd)]
            c, half = (min(v) + max(v)) / 2, max((max(v) - min(v)) / 2, wd * LANE_UM_PER_BIT / 2)
            occ[axis].append((c - half, c + half))
    # and the jog leg of a Z slot runs in a core-free channel: macro x (y) spans are occupied for x (y) lanes, so
    # its stations do not get projected onto a core edge as one stacked column (hgi_v8 ft26: 1056 b at x 555)
    for x0, y0, x1, y1 in S.placed_macro_boxes(ty, halo=KEEPOFF).values():
        occ[0].append((x0, x1))
        occ[1].append((y0, y1))
    out = {}
    for axis, g in groups.items():
        g.sort()
        ext = h if axis == 1 else w
        lo, hi = LANE_SPAN[0] * ext, LANE_SPAN[1] * ext
        need = sum(x[2] for x in g)

        def free_span(lo, hi):
            iv = sorted((max(lo, a), min(hi, b)) for a, b in occ[axis] if b > lo and a < hi)
            fr, cur = [], lo
            for a, b in iv:
                if a > cur:
                    fr.append((cur, a))
                cur = max(cur, b)
            if cur < hi:
                fr.append((cur, hi))
            return fr
        fr = free_span(lo, hi)
        if need * 1.25 > sum(b - a for a, b in fr):
            lo, hi = 8.64, ext - 8.64
            fr = free_span(lo, hi)
        if LANE_PACK == "walk":
            # walk: one evenly gapped sequence in window order over the free span, skipping occupied spans (a lane
            # never straddles one; it may overrun the last free interval end) -- chosen per type by the GEOM census
            F = sum(b - a for a, b in fr)
            gap = max(0.0, (F - need) / len(g))
            fi, pos = 0, fr[0][0] + gap / 2
            for _, name, lw in g:
                while fi < len(fr) - 1 and pos + lw > fr[fi][1]:
                    fi += 1
                    pos = max(pos, fr[fi][0])
                out[name] = (fixed.get(name, pos + lw / 2), lw)
                pos += lw + gap
            continue
        # bin the lanes (in window order) into the free intervals, then spread each bin evenly inside its interval;
        # when they do not all fit, fall back to the whole span (lanes may then lie over macros: stations project)
        bins, fi, used = [[] for _ in fr], 0, 0.0
        for item in g:
            while fi < len(fr) and used + item[2] > (fr[fi][1] - fr[fi][0]):
                fi, used = fi + 1, 0.0
            if fi == len(fr):
                break
            bins[fi].append(item)
            used += item[2]
        if fi == len(fr):
            fr, bins = [(lo, hi)], [list(g)]
        for (a0, a1), bn in zip(fr, bins):
            if not bn:
                continue
            gap = max(0.0, (a1 - a0 - sum(x[2] for x in bn)) / len(bn))
            pos = a0 + gap / 2
            for _, name, lw in bn:
                out[name] = (fixed.get(name, pos + lw / 2), lw)
                pos += lw + gap
    return out


def place(raw, types, reach_um=405., margin=.98, jogs=None, bands=None, failed=None):
    """site every ft slot of each type; failed=list -> a type that cannot be sited is restored and appended there"""
    import copy
    model = S.Plan(raw)
    ledger = []
    for tn in types:
        if failed is None:
            ledger += _place_type(model, tn, reach_um, margin, jogs or {}, bands or {})
            continue
        keep = copy.deepcopy(model.types[tn]["ft_slots"])
        try:
            ledger += _place_type(model, tn, reach_um, margin, jogs or {}, bands or {}, errs=[])
        except ValueError as ex:
            model.types[tn]["ft_slots"][:] = keep
            failed.append(dict(type=tn, error=str(ex)))
            print(f"{tn}: FAIL {ex}")
    return ledger


def _place_type(model, tn, reach_um, margin, jogs, bands, errs=None):
    ledger = []
    ty = model.types[tn]
    w, h = ty["outline_um"]
    pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(model, tn)}
    # walls = every placed physical macro (hard cores AND LEF-bearing SRAM/ROM contents, e.g. sys_c u_ucie_rom), the
    # same obstacle set the G0 geometry gate checks (schema.placed_macro_boxes), with the KEEPOFF pin-access ring
    boxes = list(S.placed_macro_boxes(ty, halo=KEEPOFF).values())
    alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL,
                         column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    budget = reach_um * margin - 2.0
    lanes = jog_lanes(ty, pins, w, h, {k.split("/", 1)[1]: v for k, v in jogs.items() if k.startswith(tn + "/")})
    for slot in sorted(ty["ft_slots"], key=lambda s: -s["width"]):
        name = slot["name"]
        wd = slot["width"] + 1
        a = np.array([pins[(name + "_i", i)] for i in range(wd)])
        b = np.array([pins[(name + "_o", i)] for i in range(wd)])
        jg, lw = lanes.get(name, (jogs.get(f"{tn}/{name}"), None))
        try:
            sites, cents, path, led = place_slot(slot, a, b, slot["in_face"], slot["out_face"], w, h, boxes, alloc,
                                                 budget, jog=jg, band=bands.get(f"{tn}/{name}"), jog_lane=lw)
        except ValueError as ex:
            if errs is None:
                raise
            errs.append(str(ex))
            continue
        if lw is not None:
            led.update(jog_um=round(float(jg), 3), jog_lane_um=round(float(lw), 3))
        slot["regs_um"] = [a.mean(axis=0).round(4).tolist()] + [c.round(4).tolist() for c in cents]
        slot["bit_site_cell_um"] = list(CELL)
        slot["bit_sites_um"] = [(p - np.array([CELL[0] / 2, CELL[1] / 2])).round(6).tolist() for p in sites]
        led.update(type=tn, slot=name, width=slot["width"], budget_um=round(budget, 2))
        ledger.append(led)
        print(f"{tn}/{name}: {slot['width']} b, {led['len_um']} um, {led['stations']} hops "
              f"{led.get('hops_um')} disp {led.get('max_alloc_disp_um')} proj {led.get('proj_mean_um')}")
    if errs:
        raise ValueError(f"{len(errs)} slot(s): " + " | ".join(errs))
    return ledger


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types", required=True)
    ap.add_argument("--out")
    ap.add_argument("--ledger")
    ap.add_argument("--jog", action="append", default=[], help="type/slot=coord: Z-path jog coordinate")
    ap.add_argument("--band", action="append", default=[], help="type/slot=lo,hi: corridor band of a straight slot")
    ap.add_argument("--reach", type=float, default=405.)
    ap.add_argument("--margin", type=float, default=.98)
    ap.add_argument("--keep-going", action="store_true")
    ap.add_argument("--lane-pack", choices=("bin", "walk"), default="bin")
    ap.add_argument("--lane-um-per-bit", type=float, default=None,
                    help="Z-jog lane width per bit (default LANE_UM_PER_BIT); KV GEOM-24 gate 0.6 x 32 tr/um -> >= 0.0521")
    a = ap.parse_args()
    global LANE_PACK
    LANE_PACK = a.lane_pack
    if a.lane_um_per_bit:
        global LANE_UM_PER_BIT
        LANE_UM_PER_BIT = a.lane_um_per_bit
    raw = json.loads(Path(a.plan).read_text())
    jogs = {k: float(v) for k, v in (j.split("=") for j in a.jog)}
    bands = {k: tuple(map(float, v.split(","))) for k, v in (j.split("=") for j in a.band)}
    failed = [] if a.keep_going else None
    ledger = place(raw, a.types.split(","), reach_um=a.reach, margin=a.margin, jogs=jogs, bands=bands, failed=failed)
    if failed:
        ledger.append(dict(failed_types=failed))
    Path(a.out or a.plan).write_text(json.dumps(raw, indent=0) + "\n")
    if a.ledger:
        Path(a.ledger).write_text(json.dumps(ledger, indent=1) + "\n")


if __name__ == "__main__":
    main()
