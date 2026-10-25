#!/usr/bin/env python3
"""KV-G3 10-24: per-bit FT station sites (ft_slots[].bit_sites_um, main tools/die_plan/ft_bit_sites.py contract) for a
partition type, so wide ft buses stay as parallel bit tracks instead of one blob per station.

Why: hub_Ei G3 kits (vC, vF with M9) fail GRT with LOCAL congestion (vF: 583 gcell overflows at 6.4 % usage) at
(630-650, 825-850) um, all on ft63/ft64/ft55/ft24/ft25 station nets: face_flops.tcl puts every flop of a station
(1,119 for ft63) around one point (ff_put_near spiral) and every bit of a straight-through slot jogs at the same x.
Here every bit i of slot S gets its OWN route from its in pin to its out pin (kit pins.json):
  * opposite faces: straight leg, jog, straight leg; the jog coordinate is staggered per bit (STAGGER_UM in bit order
    along the face) so the jogs nest without crossings (a down-shift turns the lowest track first);
  * turning slots: an L through (out.x, in.y) / (in.x, out.y) per bit (nested, no crossing for an ordered face);
station j (1..k-1) of bit i sits at L_i * j / k along that bit's own route (the plan hop model, check.py), snapped to
the nearest free legal cell site (rows 0.27 um from the core origin, x pitch COL_UM on the 0.054 um site grid), never
inside FACE_KEEP_UM of a face (the face-register bands) or a hard core / plan-cell site (+CLEAR).  Payload bits first,
then the epoch bit (the bus's last pin) -- ft_bit_sites.py order.  Sites are cell LOWER-LEFT corners.
Report: per slot max displacement from the ideal point and max per-bit hop (in pin -> s1 -> .. -> out pin).
vK (GEOM-REVIEW vJ hotspot, 10-24): options to thin out local station density and the jog bands --
  --stagger UM        per-bit jog stagger (default 0.096); a wider stagger spreads a wide slot's jog band (ft63:
                      1119 bits x 0.25 = 280 um instead of 107 um) -> fewer vertical tracks per um; hops unchanged
                      (rectilinear monotone route, length independent of the jog coordinate);
  --bin-cap F         at most F of the legal sites of any BIN_UM x BIN_UM bin hold a station flop (default 1.0 = off);
  --keepout TAPS.txt  lines "name x y": no station site within KEEPOUT_UM (--keepout-um, default 15) of a clock tap
                      (room for the tap's CTS root buffers and the reset relays placed at the tap).
usage: ft_bit_sites_gen.py die_plan.json TYPE KIT/pins.json OUT_plan.json [--report R.json] [--png P.png]
       [--stagger UM] [--bin-cap F] [--keepout TAPS.txt [--keepout-um R]]"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROW = 0.27
SITE = 0.054
CELL = (1.404, 0.27)        # envelope: DFFASRHQNx1 (epoch, async) 1.404 x 0.27; DFFHQNx1 1.08
COL_UM = 1.512              # 28 sites: x pitch of the station columns
ORIGIN = 4.32               # gen_phys CORE_MARGIN_UM (core lower-left; rows/sites start here)
FACE_KEEP_UM = 20.0
CLEAR = 4.32
STAGGER_UM = 0.096
BIN_UM = 10.0
BIN_CAP = 1.0
KEEPOUT_UM = 15.0
DEM_UM = 10.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plen(p):
    return sum(man(a, b) for a, b in zip(p, p[1:]))


def at(p, t):
    for a, b in zip(p, p[1:]):
        d = man(a, b)
        if t <= d:
            f = t / d if d else 0.0
            return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        t -= d
    return p[-1]


class Sites:
    """occupancy on the legal lattice (column index on COL_UM pitch, row index on ROW)"""

    def __init__(self, W, H, blocks):
        self.x0, self.y0 = ORIGIN, ORIGIN
        self.nx = int((W - 2 * ORIGIN - CELL[0]) / COL_UM)
        self.ny = int((H - 2 * ORIGIN) / ROW) - 1
        self.used = set()
        self.blocks = blocks
        self.W, self.H = W, H
        self.bins = defaultdict(int)
        # legal sites per bin (lattice), the cap counts station flops per bin
        self.bin_max = max(1, int(BIN_CAP * (BIN_UM / COL_UM) * (BIN_UM / ROW)))
        self.keep = []

    def _bin(self, c, r):
        return (int((self.x0 + c * COL_UM) // BIN_UM), int((self.y0 + r * ROW) // BIN_UM))

    def ok(self, c, r):
        if c < 0 or r < 0 or c > self.nx or r > self.ny or (c, r) in self.used:
            return False
        x, y = self.x0 + c * COL_UM, self.y0 + r * ROW
        if x < FACE_KEEP_UM or y < FACE_KEEP_UM or x + CELL[0] > self.W - FACE_KEEP_UM or y + CELL[1] > self.H - FACE_KEEP_UM:
            return False
        if BIN_CAP < 1.0 and self.bins[self._bin(c, r)] >= self.bin_max:
            return False
        if any(abs(x + CELL[0] / 2 - kx) < KEEPOUT_UM and abs(y + CELL[1] / 2 - ky) < KEEPOUT_UM for kx, ky in self.keep):
            return False
        return not any(a - CLEAR < x + CELL[0] and x < c2 + CLEAR and b - CLEAR < y + CELL[1] and y < d + CLEAR
                       for a, b, c2, d in self.blocks)

    def take(self, x, y, horiz):
        """nearest free site to the cell-centre target (x, y); for a horizontal-travel station prefer the same row
        (columns spread along x: the bit keeps its track), for a vertical one the same column"""
        c0 = round((x - CELL[0] / 2 - self.x0) / COL_UM)
        r0 = round((y - CELL[1] / 2 - self.y0) / ROW)
        for rad in range(0, 4000):
            cand = []
            for d in range(-rad, rad + 1):
                e = rad - abs(d)
                for s in ((d, e), (d, -e)) if e else ((d, 0),):
                    dc, dr = (s[0], s[1]) if horiz else (s[1], s[0])
                    # cost: travel-axis displacement is cheap (track kept), cross-axis is not
                    cand.append((abs(dc) * COL_UM * (0.25 if horiz else 1) + abs(dr) * ROW * (1 if horiz else 0.25),
                                 c0 + dc, r0 + dr))
            for _, c, r in sorted(cand):
                if self.ok(c, r):
                    self.used.add((c, r))
                    self.bins[self._bin(c, r)] += 1
                    return (round(self.x0 + c * COL_UM, 4), round(self.y0 + r * ROW, 4))
        raise RuntimeError(f"no free site near {x:.1f},{y:.1f}")


def bit_routes(a, b, fin, fout, rank, n, sgn, jog):
    """per-bit rectilinear route a -> b (in pin, out pin); jog = the slot's jog centre (straight-through slots)"""
    if (fin in "EW") != (fout in "EW"):
        return [a, (b[0], a[1]), b] if fin in "EW" else [a, (a[0], b[1]), b]
    off = (rank - (n - 1) / 2) * STAGGER_UM * sgn
    if fin in "EW":
        xm = jog + off
        return [a, (xm, a[1]), (xm, b[1]), b]
    ym = jog + off
    return [a, (a[0], ym), (b[0], ym), b]


class Jogs:
    """straight-through slots all jogging at the partition middle made a ~130 um vertical band carry every shifted bus
    (hub_Ei GRT hot spot): choose each slot's jog centre (widest first) in the middle half of its span on a JOG_GRID
    so the summed cross-track demand (bits x |shift| spread over the slot's stagger band) per column stays lowest."""
    GRID = 10.0

    def __init__(self, W, H):
        self.d = {"x": defaultdict(float), "y": defaultdict(float)}

    def pick(self, axis, lo, hi, n, shift):
        band = max(self.GRID, n * STAGGER_UM)
        best = None
        x = lo + (hi - lo) * 0.25
        while x <= lo + (hi - lo) * 0.75:
            cols = range(int((x - band / 2) // self.GRID), int((x + band / 2) // self.GRID) + 1)
            cost = max(self.d[axis][c] for c in cols) + 1e-3 * abs(x - (lo + hi) / 2)
            if best is None or cost < best[0]:
                best = (cost, x, cols)
            x += self.GRID
        _, x, cols = best
        for c in cols:
            self.d[axis][c] += n * abs(shift) / len(cols)
        return x


def main():
    global STAGGER_UM, BIN_CAP, KEEPOUT_UM
    pf, tn, pinsf, outf = sys.argv[1:5]
    opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d  # noqa: E731
    STAGGER_UM = opt("--stagger", STAGGER_UM)
    BIN_CAP = opt("--bin-cap", BIN_CAP)
    KEEPOUT_UM = opt("--keepout-um", KEEPOUT_UM)
    keep_f = opt("--keepout", "")
    rep_f = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    raw = json.load(open(pf))
    t = raw["partition_types"][tn]
    W, H = t["outline_um"]
    blocks = []
    for c in (t.get("hard_cores") or []) + [c for c in t.get("contents", []) if "origin_um" in c]:
        (ox, oy), (cw, ch) = c["origin_um"], c.get("outline_um", [4.32, 4.32])
        blocks.append((ox, oy, ox + cw, oy + ch))
    for e in t.get("internal_stations", []):
        for x, y in e["regs_um"]:
            blocks.append((x - 3, y - 3, x + 3, y + 3))
    S = Sites(W, H, blocks)
    if keep_f:
        S.keep = [(float(a[1]), float(a[2])) for a in (ln.split() for ln in open(keep_f)) if len(a) >= 3]
    J = Jogs(W, H)
    pins = defaultdict(dict)
    for q in json.load(open(pinsf)):
        pins[q["bus"]][q["bit"]] = (q["x"], q["y"])
    rep = dict(schema="opentallas.kv_g3.ft_bit_sites.v1", type=tn, cell_um=list(CELL), col_um=COL_UM, slots={},
               stagger_um=STAGGER_UM, bin_um=BIN_UM, bin_cap=BIN_CAP, keepout_um=KEEPOUT_UM if keep_f else None,
               keepouts=len(S.keep))
    draw = []
    dem = {"H": defaultdict(int), "V": defaultdict(int)}    # planned bit routes crossing each DEM_UM gcell

    def raster(r):
        for u, v in zip(r, r[1:]):
            if abs(u[1] - v[1]) < 1e-6:      # horizontal
                y = int(u[1] // DEM_UM)
                for gx in range(int(min(u[0], v[0]) // DEM_UM), int(max(u[0], v[0]) // DEM_UM) + 1):
                    dem["H"][(gx, y)] += 1
            else:
                x = int(u[0] // DEM_UM)
                for gy in range(int(min(u[1], v[1]) // DEM_UM), int(max(u[1], v[1]) // DEM_UM) + 1):
                    dem["V"][(x, gy)] += 1
    # widest slots first: they need straight tracks most
    for s in sorted(t["ft_slots"], key=lambda s: -s["width"]):
        k = int(s.get("stations", 1))
        if k < 2:
            continue
        nm = s["name"]
        A, B = pins[nm + "_i"], pins[nm + "_o"]
        n = s["width"] + 1
        if len(A) != n or len(B) != n:
            raise SystemExit(f"{tn} {nm}: pins.json has {len(A)}/{len(B)} pins for width+1 = {n}")
        fin, fout = s.get("in_face", "W"), s.get("out_face", "E")
        ax = 1 if fin in "EW" else 0                      # coordinate that orders the bits along the in face
        order = sorted(range(n), key=lambda i: A[i][ax])
        rank = {i: r for r, i in enumerate(order)}
        mono = all(B[order[r]][ax] <= B[order[r + 1]][ax] for r in range(n - 1)) if (fin in "EW") == (fout in "EW") else None
        dshift = sum(B[i][ax] - A[i][ax] for i in range(n)) / n
        sgn = 1 if dshift < 0 else -1                      # down-shift: lowest track turns first
        jog = None
        if (fin in "EW") == (fout in "EW"):
            lo, hi = (min(A[0][0], B[0][0]), max(A[0][0], B[0][0])) if fin in "EW" else \
                     (min(A[0][1], B[0][1]), max(A[0][1], B[0][1]))
            jog = J.pick("x" if fin in "EW" else "y", lo, hi, n, dshift)
        stages = [[None] * n for _ in range(k - 1)]
        disp = hop = 0.0
        for i in order:
            r = bit_routes(A[i], B[i], fin, fout, rank[i], n, sgn, jog)
            raster(r)
            L = plen(r)
            pts = [A[i]]
            for j in range(1, k):
                p = at(r, L * j / k)
                # travel direction at that point
                seg = next(((u, v) for u, v in zip(r, r[1:]) if min(u[0], v[0]) - 1e-6 <= p[0] <= max(u[0], v[0]) + 1e-6
                            and min(u[1], v[1]) - 1e-6 <= p[1] <= max(u[1], v[1]) + 1e-6), (r[0], r[1]))
                horiz = abs(seg[0][1] - seg[1][1]) < 1e-6
                xy = S.take(p[0], p[1], horiz)
                stages[j - 1][i] = [xy[0], xy[1]]
                c = (xy[0] + CELL[0] / 2, xy[1] + CELL[1] / 2)
                disp = max(disp, man(c, p))
                pts.append(c)
            pts.append(B[i])
            hop = max(hop, max(man(u, v) for u, v in zip(pts, pts[1:])))
            if i % 16 == 0:
                draw.append((r, pts[1:-1]))
        s["bit_sites_um"] = stages
        s["bit_site_cell_um"] = list(CELL)
        s.pop("regs_um", None)      # superseded by explicit per-bit sites (check.py hop model still uses L*j/k)
        rep["slots"][nm] = dict(width=s["width"], stations=k, jog_um=jog, max_disp_um=round(disp, 2), max_bit_hop_um=round(hop, 1),
                                order_preserved=mono)
    rep["max_bit_hop_um"] = max((v["max_bit_hop_um"] for v in rep["slots"].values()), default=0)
    rep["max_disp_um"] = max((v["max_disp_um"] for v in rep["slots"].values()), default=0)
    rep["sites"] = len(S.used)
    rep["max_bin_sites"] = max(S.bins.values(), default=0)
    rep["bin_sites_cap"] = S.bin_max
    # planned ft route demand (wires per DEM_UM gcell edge-on): the GRT hot-spot predictor for the ft bundles
    for d in ("H", "V"):
        top = sorted(dem[d].items(), key=lambda kv: -kv[1])[:5]
        rep[f"route_demand_{d}"] = dict(gcell_um=DEM_UM, max=top[0][1] if top else 0,
                                        top=[[k[0] * DEM_UM, k[1] * DEM_UM, v] for k, v in top])
    win = opt("--window", "")
    if win:
        x0, y0, x1, y1 = (float(v) for v in win.split(","))
        inw = lambda k: x0 <= k[0] * DEM_UM < x1 and y0 <= k[1] * DEM_UM < y1  # noqa: E731
        rep["window"] = dict(box_um=[x0, y0, x1, y1],
                             route_demand_max={d: max((v for k, v in dem[d].items() if inw(k)), default=0) for d in "HV"},
                             station_sites=sum(1 for (c, r_) in S.used
                                               if x0 <= S.x0 + c * COL_UM < x1 and y0 <= S.y0 + r_ * ROW < y1))
    Path(outf).write_text(json.dumps(raw, indent=1) + "\n")
    if rep_f:
        Path(rep_f).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("type", "sites", "max_bit_hop_um", "max_disp_um")}))
    if png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, ax = plt.subplots(figsize=(12, 12 * H / W + 1))
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
        for r, st in draw:
            ax.plot([q[0] for q in r], [q[1] for q in r], color="#bbb", lw=0.2)
        xs = [x for (c, r_) in S.used for x in [S.x0 + c * COL_UM]]
        ys = [S.y0 + r_ * ROW for (c, r_) in S.used]
        ax.plot(xs, ys, ",", color="tab:red")
        ax.set_aspect("equal")
        ax.set_title(f"{tn}: {len(S.used)} explicit ft station sites (red), every 16th bit route (grey)", fontsize=8)
        fig.tight_layout()
        fig.savefig(png, dpi=150)


if __name__ == "__main__":
    main()
