#!/usr/bin/env python3
"""adv_route_demand.py -- static advisory ADV-ROUTE-DEMAND (LEAF-ROUTE-CBC, COORD 11-22; owner 11-19: an estimator, never a gate).

Why: close-by-construction covered reach, depth, taps and reset but had no routing-demand view; S81 leaf types failed GRT
(t44 50k overflow at 2.6% fill) with hotspots at hard-core channels that the plan already showed.

Model (plan only, no netlist, no placement):
  supply  per G x G gcell and direction = routing tracks/um of M2..M8 (ASAP7 pitches) above the obs_max of any hard core
          covering the gcell, x SUPPLY_FRAC (PG straps, pin access, GRT derates; calibrated below)
  demand  RUDY (Spindler 2007) of every planned multi-bit wire the plan places: internal_stations (from_um -> regs_um ->
          to_um, `bits` wires per leg) and ft_slots (regs_um chain, `width` wires per leg); a leg's box is widened to
          max(G, bits / BUS_TRACKS) so a wide bus is never thinner than its own tracks
  util    = demand / supply per direction; a gcell is HOT at util >= WARN_UTIL (0.8)
Lines: one per type with hot gcells: peak util, hot area, the hottest region box, the cores that bound it and the
narrowest core channel there (a channel < CHANNEL_UM between two cores with traffic is the S81 leaf failure class), and
the station/ft rows that load it most.  The legs are routed straight (box spread), not detoured round cores: the
over-core supply (M6..M8 above an M5 obs) is where GRT overflowed on the S81 leaf kits (50-86% of overflow on cores).

CALIBRATION (11-23, LEAF-ROUTE-CBC; J7 plan h2_2249 vs the J7 wave kits' last-round GRT congestion-N.rpt, 10 leaf kits
with 4_cts dumps + 18 type totals from NOPROG-TABLE):
  location   recall: 73-100 % (median 99 %) of GRT overflow lies within 2 gcells of a gcell flagged >= 0.8; the top-2 % estimated
             gcells hold 11-72 % (median ~30 %) of the overflow; the flagged area is 4-32 % congested (precision): it is a
             where-to-look map, not a router.  50-86 % of the measured overflow sat over the M5-obs hcpost lane macros.
  ranking    poor INSIDE one family: Spearman(type score, GRT overflow) 0.34 at best (hot gcell count) over 16 s81sl_leaf types
             whose plans carry the same demand (t6 43 vs t21 58.7k overflow on ~equal plan load): the spread is placement/flow,
             not plan.  It separates families (kv_leaf 139-344 overflow, est. peak 2.6-3.6 vs leaf 9.9-18.8).
  So read a WARN as "this plan has a demand pinch here" (all 75 J8 s81sl_leaf types: vn->lane bank fan-in through 4-17 um
  channels), never as a pass/fail or a ranking.

    findings(raw, plan_path, tree=None, types=None, warn=WARN_UTIL) -> ["WARN ADV-ROUTE-DEMAND ..."]
    grid(t) -> dict(nx, ny, G, util, hot, ...) for one plan type (renders / calibration)
"""
import json
import math
from pathlib import Path
import re

CHECK = "ROUTE-DEMAND"
G = 10.0                 # gcell um
WARN_UTIL = 0.8
CHANNEL_UM = 30.0        # a core gap narrower than this carrying traffic is named
SUPPLY_FRAC = 0.5        # usable fraction of raw tracks (calibrated)
BUS_TRACKS = 20.0        # tracks/um a wide bus gets on its own (min leg width = bits / BUS_TRACKS)
MAX_LINES = 20
# ASAP7 routing layers M2..M8: (name, level, dir, pitch um)
LAYERS = (("M2", 2, "H", .036), ("M3", 3, "V", .036), ("M4", 4, "H", .048), ("M5", 5, "V", .048),
          ("M6", 6, "H", .064), ("M7", 7, "V", .064), ("M8", 8, "H", .080))
LVL = re.compile(r"M(\d+)")


def _sup(top):
    """(H, V) tracks/um above obstruction level `top` (0 = none)."""
    h = sum(1 / p for _, lv, d, p in LAYERS if lv > top and d == "H")
    v = sum(1 / p for _, lv, d, p in LAYERS if lv > top and d == "V")
    return h, v


def core_boxes(t):
    out = []
    for hc in t.get("hard_cores") or []:
        try:
            ox, oy = map(float, hc["origin_um"])
            w, h = map(float, hc["outline_um"])
        except (KeyError, TypeError, ValueError):
            continue
        if str(hc.get("orient", "R0")).endswith("90") or str(hc.get("orient", "")).endswith("270"):
            w, h = h, w
        m = LVL.match(str(hc.get("obs_max") or "M5"))
        out.append((ox, oy, ox + w, oy + h, int(m.group(1)) if m else 5, str(hc.get("inst", "?"))))
    return out


def legs(t):
    """[(x0, y0, x1, y1, bits, label)] planned multi-bit wire legs of a type."""
    out = []
    for s in t.get("internal_stations") or []:
        try:
            n = int(s.get("bits") or 0)
            pts = [s["from_um"]] + list(s.get("regs_um") or []) + [s["to_um"]]
        except (KeyError, TypeError):
            continue
        lab = "%s>%s" % (str(s.get("launch", "?")).replace("core:", "")[-22:], str(s.get("capture", "?"))[-22:])
        for a, b in zip(pts, pts[1:]):
            out.append((float(a[0]), float(a[1]), float(b[0]), float(b[1]), n, lab))
    for f in t.get("ft_slots") or []:
        n = int(f.get("width") or 0)
        pts = list(f.get("regs_um") or [])
        for a, b in zip(pts, pts[1:]):
            out.append((float(a[0]), float(a[1]), float(b[0]), float(b[1]), n, "ft " + str(f.get("name", "?"))))
    return out


CALIB_ENV = "OT_GRT_CALIB_JSON"
_CALIB = {}


def calibration(env=None):
    """GRT-EST-OPTIMISTIC: {family: multiplier} from $OT_GRT_CALIB_JSON, else tools/die_plan/grt_est_calibration.json next to this module; {} when absent.
    Only status "calibrated" families scale.  Advisory: the usable supply is divided by the multiplier."""
    import os
    path = (env if env is not None else os.environ).get(CALIB_ENV) or str(Path(__file__).resolve().parent / "grt_est_calibration.json")
    if path not in _CALIB:
        try:
            d = json.loads(Path(path).read_text())
            _CALIB[path] = {f: float(v["multiplier"]) for f, v in (d.get("families") or {}).items()
                            if v.get("status") == "calibrated" and float(v.get("multiplier", 1)) > 1.0}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            _CALIB[path] = {}
    return _CALIB[path]


def type_multiplier(tn):
    try:
        import grt_est_calibrate as GC
    except ImportError:
        return 1.0, None
    fam = GC.family_of(tn)
    return (calibration().get(fam, 1.0), fam) if fam else (1.0, None)


def grid(t, supply_frac=None, g=G):
    sf = SUPPLY_FRAC if supply_frac is None else supply_frac
    W, H = map(float, t["outline_um"])
    nx, ny = int(math.ceil(W / g)), int(math.ceil(H / g))
    full = _sup(0)
    sh = [[full[0]] * ny for _ in range(nx)]
    sv = [[full[1]] * ny for _ in range(nx)]
    cores = core_boxes(t)
    owner = [[None] * ny for _ in range(nx)]
    for c in cores:
        h, v = _sup(c[4])
        for i in range(max(0, int(c[0] / g)), min(nx, int(math.ceil(c[2] / g)))):
            for j in range(max(0, int(c[1] / g)), min(ny, int(math.ceil(c[3] / g)))):
                # a gcell more than half covered by the core takes its supply
                cx0, cx1 = max(c[0], i * g), min(c[2], (i + 1) * g)
                cy0, cy1 = max(c[1], j * g), min(c[3], (j + 1) * g)
                if (cx1 - cx0) * (cy1 - cy0) >= 0.5 * g * g:
                    sh[i][j] = min(sh[i][j], h); sv[i][j] = min(sv[i][j], v); owner[i][j] = c[5]
    dh = [[0.0] * (ny + 1) for _ in range(nx + 1)]
    dv = [[0.0] * (ny + 1) for _ in range(nx + 1)]
    contrib = []
    for (x0, y0, x1, y1, n, lab) in legs(t):
        if n <= 0:
            continue
        w, h = abs(x1 - x0), abs(y1 - y0)
        wmin = max(g, n / BUS_TRACKS)
        bw, bh = max(w, wmin), max(h, wmin)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        bx0, bx1, by0, by1 = cx - bw / 2, cx + bw / 2, cy - bh / 2, cy + bh / 2
        # tracks per um: H demand = n * w / (bw * bh) per um of height ...
        dH = n * max(w, 0.0) / (bw * bh) if w > 0 else 0.0
        dV = n * max(h, 0.0) / (bw * bh) if h > 0 else 0.0
        i0, i1 = max(0, int(bx0 / g)), min(nx, int(math.ceil(bx1 / g)))
        j0, j1 = max(0, int(by0 / g)), min(ny, int(math.ceil(by1 / g)))
        if i1 <= i0 or j1 <= j0:
            continue
        for d, val in ((dh, dH), (dv, dV)):
            if val:
                d[i0][j0] += val; d[i1][j0] -= val; d[i0][j1] -= val; d[i1][j1] += val
        contrib.append((i0, i1, j0, j1, dH, dV, lab, n))
    for d in (dh, dv):
        for i in range(nx + 1):
            row = d[i]
            for j in range(1, ny + 1):
                row[j] += row[j - 1]
        for i in range(1, nx + 1):
            a, b = d[i], d[i - 1]
            for j in range(ny + 1):
                a[j] += b[j]
    util = [[0.0] * ny for _ in range(nx)]
    for i in range(nx):
        for j in range(ny):
            # a direction with no tracks over a core (M7 obs: no V) is detoured by GRT, not overflowed: not counted
            uh = dh[i][j] / (sh[i][j] * sf) if sh[i][j] > 0 else 0.0
            uv = dv[i][j] / (sv[i][j] * sf) if sv[i][j] > 0 else 0.0
            util[i][j] = max(uh, uv)
    return {"nx": nx, "ny": ny, "G": g, "W": W, "H": H, "util": util, "cores": cores, "owner": owner, "contrib": contrib}


def _regions(gr, thr):
    nx, ny, u = gr["nx"], gr["ny"], gr["util"]
    seen = set(); regs = []
    for i in range(nx):
        for j in range(ny):
            if u[i][j] < thr or (i, j) in seen:
                continue
            st = [(i, j)]; seen.add((i, j)); cells = []
            while st:
                a, b = st.pop(); cells.append((a, b))
                for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= c < nx and 0 <= d < ny and (c, d) not in seen and u[c][d] >= thr:
                        seen.add((c, d)); st.append((c, d))
            regs.append(cells)
    regs.sort(key=lambda cs: -sum(u[a][b] for a, b in cs))
    return regs


def channels(cores, box, lim=CHANNEL_UM):
    """narrow gaps between two cores that face each other near `box` (x0, y0, x1, y1): [(gap, axis, a, b)]."""
    x0, y0, x1, y1 = box
    near = [c for c in cores if c[2] >= x0 - lim and c[0] <= x1 + lim and c[3] >= y0 - lim and c[1] <= y1 + lim]
    out = []
    for i in range(len(near)):
        for j in range(i + 1, len(near)):
            a, b = near[i], near[j]
            gx = max(b[0] - a[2], a[0] - b[2]); gy = max(b[1] - a[3], a[1] - b[3])
            oy = min(a[3], b[3]) - max(a[1], b[1]); ox = min(a[2], b[2]) - max(a[0], b[0])
            if 0 < gx < lim and oy > 0:
                out.append((round(gx, 2), "x", a[5], b[5]))
            elif 0 < gy < lim and ox > 0:
                out.append((round(gy, 2), "y", a[5], b[5]))
    return sorted(out)


def _short(n):
    return n.replace("u_lf.", "").replace("u_vp.", "vp.")


def type_lines(tn, t, warn=WARN_UTIL):
    mult, fam = type_multiplier(tn)
    gr = grid(t, SUPPLY_FRAC / mult) if mult > 1.0 else grid(t)
    regs = _regions(gr, warn)
    if not regs:
        return []
    g, u = gr["G"], gr["util"]
    hot = sum(len(r) for r in regs)
    peak = max(u[a][b] for r in regs for a, b in r)
    r = regs[0]
    xs = [a for a, _ in r]; ys = [b for _, b in r]
    box = (min(xs) * g, min(ys) * g, (max(xs) + 1) * g, (max(ys) + 1) * g)
    ch = channels(gr["cores"], box)
    on_core = sum(1 for a, b in r if gr["owner"][a][b]) / len(r)
    # top contributors in the region
    tot = {}
    rs = set(r)
    for (i0, i1, j0, j1, dH, dV, lab, n) in gr["contrib"]:
        k = sum(1 for a, b in r if i0 <= a < i1 and j0 <= b < j1)
        if k:
            tot[lab] = tot.get(lab, 0.0) + k * (dH + dV)
    top = sorted(tot.items(), key=lambda kv: -kv[1])[:3]
    s = (f"WARN ADV-{CHECK} {tn}: {hot} gcell(s) ({hot * g * g / 1e3:.1f}k um2) at est. routing util >= {warn} "
         f"(peak {peak:.2f}{f', calibrated x{mult:g} family {fam}' if mult > 1.0 else ''}); worst region x{box[0]:.0f}-{box[2]:.0f} y{box[1]:.0f}-{box[3]:.0f} "
         f"({len(r)} gcells, {on_core:.0%} over cores)")
    if ch:
        s += "; channel " + ", ".join(f"{c[0]:g} um {c[1]} {_short(c[2])}|{_short(c[3])}" for c in ch[:2])
    if top:
        s += "; load: " + ", ".join(lab for lab, _ in top)
    s += "; fix: widen the channel / spread the banks / move the legs off the cores (pre-approved growth) and probe place+GRT"
    return [s]


def findings(raw, plan_path=None, tree=None, types=None, warn=WARN_UTIL, **_kw):
    P = raw.get("partition_types") or {}
    if not P:
        return [f"WARN ADV-{CHECK} not checked: plan has no partition_types"]
    out = []
    for tn in sorted(P):
        if types and not re.search(types, tn):
            continue
        t = P[tn]
        if not isinstance(t, dict) or not t.get("outline_um"):
            continue
        if not (t.get("internal_stations") or t.get("ft_slots")):
            continue
        try:
            out += type_lines(tn, t, warn)
        except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
            out.append(f"WARN ADV-{CHECK} {tn}: not checked: {type(e).__name__}: {str(e)[:120]}")
    return out
