#!/usr/bin/env python3
"""FT-CHANNEL-ROUTE-1 (FABLE-FIX-S81-STRIP 11-17, FABLE-CLOSURE-STRATEGY lever 5): re-slot N<->S ft slots over the
vertical channels of a type by track capacity.  Cores, outlines, windows, pins and RTL never change.

Why: check.py ft_channel_tracks (r567) flags 25 channels in 20 S81 strip types.  The slots of a type were sited one by
one on the shortest path, so several bundles share one 26-43-um seam beside VE_m / VE_s / u_cap while a 60-190-um
street two cores away is empty (t34: 1,766 bits in the 30.4-um west seam -> GRT M6 2,199 + M8 1,254 overflow).

Form, per flagged type:
  capacity  every row gap between placed macros (and the outline) carries at most MAX x PER_UM x width bits of
            vertical wire, every column gap MAX x H_PER_UM x height bits of horizontal wire, and every channel of
            check.ft_channels MAX x PER_UM x width; a slot is charged ONCE per gap it runs through (wires, not sites:
            a station moved out of a seam does not hide its wires).  A bundle may cross a core that ends at M5 or
            below on M7 (0.6 of the M7 tracks over it, the ft_corridor rule); stations never sit on a core.
  route     the slots with sites in an over-limit channel (largest first; all N/S slots when that is not enough) are
            routed in window centre -> out window centre on the 4.32 lattice (Dijkstra, cost = length x (1 + use)),
            the slots left in place are charged from their sites and station line.  A slot that finds no route or
            no station chain is routed first in the next pass; a channel that station bands still crowd after a
            pass takes no station in the next.
  stations  the station count is kept.  Stage centres are chosen on the route by DP (min of the longest hop, the hop
            from the last stage to the out pin included; a stage in a channel narrower than 3 bands costs extra, two
            stages of one slot never share a channel).  Each stage is a band across the flow in bit order on free legal row sites
            (ft_throat_fix.band, ft_seam_fix.allocator: macro keep-off, clock halos, other slots' sites).
  accept    every channel of the type <= MAX by check.ft_channels, every lane hop touching a re-routed slot
            <= max(400, before), first hop within reach; else the type is left unchanged and the ledger says why.
  --add     a slot whose route is too long for its count gets +1..+2 stations (+1 cycle each on every lane row that
            crosses it, as ft_seam_fix --add; cycles pre-approved r567), reported per slot.

    ft_channel_route.py PLAN OUT LEDGER [--type REGEX] [--max 0.70] [--per-um 45.6] [--h-per-um 25.8] [--add]
                        [--rows-only] [--route-max F] [--over-use F]
Exit 0 when no channel of the selected types is over MAX after the run.
"""
import argparse, heapq, json, math, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402
import ft_spread as FS  # noqa: E402
import ft_seam_fix as SF  # noqa: E402
import ft_throat_fix as TF  # noqa: E402

G = 4.32
KEEP = 2.0
LIMIT = SF.LIMIT
H_PER_UM = 25.8                 # M4 + M6 at the same GRT derate as the 45.6 vertical figure (M3 + M5 + M7)
EPS = 1e-6
MAX_ADD = 2
OVER_OK = ("M1", "M2", "M3", "M4", "M5")        # hard_cores.obs_max that leaves M6 / M7 free over the core
OVER_USE = 0.6                  # ft_corridor rule: ft demand <= 0.6 of the tracks over a core
M7_SHARE = 0.2434               # M7 share of the M3 + M5 + M7 tracks (pitch 36 / 48 / 64 nm)
M6_SHARE = 0.4286               # M6 share of M4 + M6


class Grid:
    def __init__(self, t, per, hper, lim, over_use=OVER_USE):
        self.W, self.H = map(float, t["outline_um"])
        self.nx, self.ny = int(math.ceil(self.W / G)), int(math.ceil(self.H / G))
        named = S.placed_macro_boxes(t)
        self.boxes = list(named.values())
        low = {c["inst"] for c in t.get("hard_cores") or [] if c.get("obs_max") in OVER_OK} if over_use > 0 else set()
        self.blk = np.zeros((self.nx, self.ny), bool)
        self.cap, self.used, self.rect = [], [], []
        self.lim = lim; self.hset = set()
        soft = {}
        for name, (x0, y0, x1, y1) in named.items():
            i0, i1 = int(math.floor((x0 - KEEP) / G + .5)), int(math.ceil((x1 + KEEP) / G - .5))
            j0, j1 = int(math.floor((y0 - KEEP) / G + .5)), int(math.ceil((y1 + KEEP) / G - .5))
            sl = (slice(max(i0, 0), max(i1, 0)), slice(max(j0, 0), max(j1, 0)))
            if name in low:                                 # a core that ends at M5 or below: wires may cross on M6 / M7
                v = self._add((x0, y0, x1, y1), over_use * per * M7_SHARE * (x1 - x0))
                h = self._hadd((x0, y0, x1, y1), over_use * hper * M6_SHARE * (y1 - y0) * lim)
                soft[name] = (sl, v, h)
            else:
                self.blk[sl] = True
        self.vreg = [[() for _ in range(self.ny)] for _ in range(self.nx)]
        self.hreg = [[() for _ in range(self.ny)] for _ in range(self.nx)]
        for j in range(self.ny):                                    # row gaps: vertical wire
            y = (j + .5) * G
            row = sorted((b[0], b[2]) for b in self.boxes if b[1] - EPS < y < b[3] + EPS)
            self._gaps(row, self.W, lambda lo, hi: self._add((lo, j * G, hi, (j + 1) * G), lim * per * (hi - lo)),
                       lambda i, r: self.vreg[i].__setitem__(j, self.vreg[i][j] + (r,)), self.nx)
        for i in range(self.nx):                                    # column gaps: horizontal wire
            x = (i + .5) * G
            col = sorted((b[1], b[3]) for b in self.boxes if b[0] - EPS < x < b[2] + EPS)
            self._gaps(col, self.H, lambda lo, hi: self._hadd((i * G, lo, (i + 1) * G, hi), lim * hper * (hi - lo)),
                       lambda j, r: self.hreg[i].__setitem__(j, self.hreg[i][j] + (r,)), self.ny)
        for sl, v, h in soft.values():                              # over-core cells carry only the core's own budget
            for i in range(sl[0].start, min(sl[0].stop, self.nx)):
                for j in range(sl[1].start, min(sl[1].stop, self.ny)):
                    if not self.blk[i, j]:
                        self.vreg[i][j] = (v,); self.hreg[i][j] = (h,)
        self.chan = []                                              # the check's channels: vertical wire + sites
        for (lo, y0, hi, y1) in channel_rects(t):
            r = self._add((lo, y0, hi, y1), lim * per * (hi - lo)); self.chan.append(r)
            for i in range(max(int(lo / G), 0), min(int(math.ceil(hi / G)), self.nx)):
                if not lo - EPS <= (i + .5) * G < hi + EPS:
                    continue
                for j in range(max(int(y0 / G), 0), min(int(math.ceil(y1 / G)), self.ny)):
                    if y0 - EPS <= (j + .5) * G <= y1 + EPS:
                        self.vreg[i][j] = self.vreg[i][j] + (r,)

    def _add(self, rect, cap):
        self.rect.append(rect); self.cap.append(cap); self.used.append({}); return len(self.cap) - 1

    def _hadd(self, rect, cap):
        r = self._add(rect, cap); self.hset.add(r); return r

    def _gaps(self, spans, L, add, put, n):
        x = 0.0; gaps = []
        for a, b in spans:
            if a > x + EPS:
                gaps.append((x, a))
            x = max(x, b)
        if L > x + EPS:
            gaps.append((x, L))
        for lo, hi in gaps:
            r = add(lo, hi)
            for k in range(max(int(lo / G), 0), min(int(math.ceil(hi / G)), n)):
                if lo - EPS <= (k + .5) * G <= hi + EPS:
                    put(k, r)

    def load(self, r, skip):
        return sum(v for k, v in self.used[r].items() if k != skip)

    def charge(self, name, bits, regs):
        for r in regs:
            self.used[r][name] = bits

    def regs_at(self, x, y):
        i, j = min(max(int(x / G), 0), self.nx - 1), min(max(int(y / G), 0), self.ny - 1)
        return self.vreg[i][j]

    def route(self, name, bits, a, b, route_max, fan=None):
        """cells of the cheapest path a -> b for a bundle of `bits` (None when no path keeps every gap in capacity).
        fan(cell) marks the slot's own pin fan (under its window at a face): the bits spread to their pins there, so a
        horizontal step between two fan cells is not charged as a whole bundle."""
        nx, ny = self.nx, self.ny
        fan = fan or (lambda c: False)
        ok = {}

        def fits(r):
            if r not in ok:                                 # a column gap (horizontal run, mostly the fan to the pins
                c = self.cap[r] / self.lim if r in self.hset else self.cap[r] * route_max      # under a core) may fill
                ok[r] = self.load(r, name) + bits <= c + EPS
            return ok[r]

        def use(regs):
            return max([(self.load(r, name) + bits) / max(self.cap[r], 1.0) for r in regs] or [0.0])
        dist = {a: 0.0}; prev = {}; pq = [(0.0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            i, j = u
            for di, dj in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                v = (i + di, j + dj)
                if not (0 <= v[0] < nx and 0 <= v[1] < ny) or (self.blk[v] and v != b):
                    continue
                regs = (self.vreg[i][j] + self.vreg[v[0]][v[1]]) if dj else \
                    (() if fan(u) and fan(v) else self.hreg[i][j] + self.hreg[v[0]][v[1]])
                if not all(fits(r) for r in regs):
                    continue
                pu = prev.get(u)
                bend = 0.0 if pu is None or (pu[0] - i, pu[1] - j) == (-di, -dj) else 2.0
                nd = d + G * (1.0 + 0.6 * use(regs)) + bend
                if nd < dist.get(v, 1e18) - 1e-9:
                    dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if b not in prev and a != b:
            return None
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        return path[::-1]

    def path_regs(self, path, fan=None):
        out = set(); fan = fan or (lambda c: False)
        for u, v in zip(path, path[1:]):
            out.update((self.vreg[u[0]][u[1]] + self.vreg[v[0]][v[1]]) if u[0] == v[0]
                       else (() if fan(u) and fan(v) else self.hreg[u[0]][u[1]] + self.hreg[v[0]][v[1]]))
        return out


def channel_rects(t):
    """every channel rectangle of check.ft_channels, also the ones that hold no ft bit site today."""
    boxes = list(S.placed_macro_boxes(t).values())
    W = float((t.get("outline_um") or [0, 0])[0])
    seen, out = set(), []
    for (x0, y0, x1, y1) in boxes:
        ov = [b for b in boxes if b[1] < y1 - C.EPS and b[3] > y0 + C.EPS]
        west = max([b[2] for b in ov if b[2] <= x0 + C.EPS] + [0.0])
        east = min([b[0] for b in ov if b[0] >= x1 - C.EPS] + [W])
        for lo, hi in ((west, x0), (x1, east)):
            key = (round(lo, 3), round(hi, 3), round(y0, 3), round(y1, 3))
            if hi - lo > C.EPS and key not in seen:
                seen.add(key); out.append((lo, y0, hi, y1))
    return out


def all_channels(t, per):
    return C.ft_channels(t, per)


def over(t, per, lim):
    return [(r, b, u) for r, b, u in all_channels(t, per) if u > lim + EPS]


def in_rect(r, x, y):
    return r[0] - EPS <= x < r[2] - EPS and r[1] - EPS <= y <= r[3] + EPS


def pin_fan(g, s, depth=86.4):
    """cells under the slot's own windows within `depth` of the face."""
    zones = []
    for face, win in ((s["in_face"], s["in_window_um"]), (s["out_face"], s["out_window_um"])):
        lo, hi = sorted(win)
        zones.append((lo - G, hi + G, (g.H - depth, g.H) if face == "N" else (0.0, depth)))
    return lambda c: any(x0 <= (c[0] + .5) * G <= x1 and y[0] <= (c[1] + .5) * G <= y[1] for x0, x1, y in zones)


def face_cell(g, face, win):
    x = min(max(int((win[0] + win[1]) / 2 / G), 0), g.nx - 1)
    return (x, g.ny - 1) if face == "N" else (x, 0)


def band_ok(g, c, ext, thick):
    """the band rectangle (ext across x, thick along y) lies in free lattice cells inside the 4.32 frame."""
    x0, x1, y0, y1 = c[0] - ext / 2, c[0] + ext / 2, c[1] - thick / 2, c[1] + thick / 2
    if x0 < G or y0 < G or x1 > g.W - G or y1 > g.H - G:
        return False
    return not any(b[0] - KEEP < x1 and b[2] + KEEP > x0 and b[1] - KEEP < y1 and b[3] + KEEP > y0 for b in g.boxes)


def stage_plan(g, path, k, ext, thick, win_w, lim, ban):
    """k - 1 stage centres on the path (S0 at path[0]); returns (centres, worst hop) or (None, why).  A band may enter
    a channel only when the bundle itself runs through it (first try); `ban` channels take no band of a bundle that
    does not run through them in any case."""
    own = {r for r in g.path_regs(path) if r in g.chan}
    plan, why = _stage_plan(g, path, k, ext, thick, win_w, lim, ban, own, False)
    if plan is None:
        plan, why = _stage_plan(g, path, k, ext, thick, win_w, lim, ban, own, True)
    return plan, why


def _stage_plan(g, path, k, ext, thick, win_w, lim, ban, own, stray_ok):
    pts = [((i + .5) * G, (j + .5) * G) for i, j in path]
    n = len(pts); arc = [m * G for m in range(n)]
    L = arc[-1]
    vert = {m for m in range(1, n - 1) if path[m - 1][0] == path[m][0] == path[m + 1][0]}
    cand = []
    offs = sorted(((dx * G, dy * G) for dx in range(-5, 6) for dy in range(-10, 11)), key=lambda o: abs(o[0]) + abs(o[1]))
    cen = {}
    for m in range(1, n - 1):
        for ox, oy in offs:                                 # nearest free band centre off the route line (<= 43.2 um)
            if (ox and m not in vert) or (oy and m in vert):
                continue
            c = (pts[m][0] + ox, pts[m][1] + oy)
            e = next((q for q in (ext, ext * 0.75, ext * 0.6) if band_ok(g, c, q, thick * ext / q)), None)
            if e is None:
                continue
            bx = (c[0] - e / 2, c[1] - thick, c[0] + e / 2, c[1] + thick)
            ch = [r for r in g.chan if g.rect[r][0] < bx[2] and g.rect[r][2] > bx[0] and g.rect[r][1] < bx[3] and g.rect[r][3] > bx[1]]
            stray = [r for r in ch if r not in own]
            if stray and (not stray_ok or any(g.rect[r] in ban for r in stray)):
                continue                                    # no band in a channel the bundle does not run through
            tight = any(g.rect[r][2] - g.rect[r][0] < 3 * ext for r in ch)
            cen[m] = c
            cand.append((m, e, tuple(ch), (0.0 if m in vert else 40.0) + (60.0 if tight else 0.0), abs(ox) + abs(oy)))
            break                                           # (a band on a horizontal run costs 40 um, in a tight channel 60)
    if not cand:
        return None, "no free band position on the route"
    edge = max(0.0, (win_w - ext) / 2)                      # lateral run of the outermost bit, window -> band
    tail = lambda q: L - arc[q[0]] + edge + abs(ext - q[1]) / 2 + q[4]      # last stage -> out pin (the next S0 sits on it)
    INF = 1e18
    # DP over (stage index, candidate): min over chains of the longest hop (+ a cost for stages inside narrow channels)
    best = [{} for _ in range(k)]; seen = [{} for _ in range(k)]
    for q in cand:
        d = arc[q[0]] + edge + abs(ext - q[1]) / 2 + q[4]
        if d <= lim:
            best[1][q] = (d + q[3], None); seen[1][q] = set(q[2])
    for s in range(2, k):
        for q in cand:
            bq = (INF, None)
            for p, (cost, _) in best[s - 1].items():
                if p[0] >= q[0]:
                    continue
                if set(q[2]) & seen[s - 1][p]:
                    continue                                # two stages of one slot in one channel count twice
                d = arc[q[0]] - arc[p[0]] + abs(p[1] - q[1]) / 2 + p[4] + q[4]
                if d > lim:
                    continue
                c = max(cost, d + q[3])
                if c < bq[0]:
                    bq = (c, p)
            if bq[1] is not None:
                best[s][q] = bq; seen[s][q] = seen[s - 1][bq[1]] | set(q[2])
    ends = [(max(c, tail(q)), q) for q, (c, _) in best[k - 1].items() if tail(q) <= lim]
    if not ends:
        return None, "route %.0f um too long for %d stations" % (L, k)
    cost, q = min(ends, key=lambda z: (z[0], -z[1][0]))
    chain = [q]
    for s in range(k - 1, 1, -1):
        q = best[s][q][1]; chain.append(q)
    chain = chain[::-1]
    return [(cen[m], e) for m, e, _, _, _ in chain], cost


def place_slot(P, raw, tn, s, g, path, add, lim_touch, rec, ban):
    t = raw["partition_types"][tn]
    W = int(s["width"]); k0 = int(s["stations"]); olds = [list(x) for x in s["bit_sites_um"]]
    W1 = len(olds[0]); cell = s.get("bit_site_cell_um", list(FS.CELL))
    tpu = FS._tracks(s, False)
    ext = W / (TF.TARGET * tpu) / 0.95 + FS.CELL[0]
    thick = TF.band_thickness(W1, ext, False) + 2 * 0.27
    win_w = abs(s["in_window_um"][1] - s["in_window_um"][0])
    order = TF.ranks(olds[0], False)
    lids = SF.slot_lanes(P, tn, s["name"])
    keep = json.dumps(s); why = None
    for extra in range(0, (MAX_ADD if add else 0) + 1):
        k = k0 + extra
        plan, why = stage_plan(g, path, k, ext, thick, win_w, lim_touch - 6.0, ban)
        if plan is None:
            continue
        s["bit_sites_um"] = []
        al = SF.allocator(t)
        sites, regs = [], [list(json.loads(keep)["regs_um"][0])]
        for (c, e) in plan:
            gband = TF.band(al, np.array(c, float), order, W1, e, False, cell)
            if gband is None:
                why = "no free row sites for a band at (%.0f, %.0f)" % c; break
            for bx, by in gband:
                al.reserve_rectangle((bx, by, bx + cell[0], by + cell[1]))
            cen = np.array(gband, float).mean(0) + np.array(cell) / 2
            sites.append(gband); regs.append([round(float(cen[0]), 4), round(float(cen[1]), 4)])
        else:
            s["bit_sites_um"] = sites; s["regs_um"] = regs; s["stations"] = k
            touch, _ = SF.max_slot_hop(P, lids, tn, s["name"])
            if touch <= lim_touch + EPS and SF.first_hop_ok(P, tn, s):
                rec.update(stations=[k0, k], worst_hop_um=round(touch, 1), route_um=round((len(path) - 1) * G, 1),
                           centres=[r for r in regs[1:]], lanes=len(lids))
                if extra:
                    rec["added"] = extra; rec["lane_rows"] = lids
                return True
            why = "hop %.1f um > %.1f after siting at %d stations" % (touch, lim_touch, k)
        s.clear(); s.update(json.loads(keep))
    s.clear(); s.update(json.loads(keep)); rec["why"] = why
    return False


def charge_fixed(g, s):
    regs = set()
    for st in s.get("bit_sites_um") or []:
        for x, y in st[::8]:
            regs.update(g.regs_at(x, y))
    pts = [r[:2] for r in s.get("regs_um") or []]
    for a, b in zip(pts, pts[1:]):
        n = max(2, int((abs(a[0] - b[0]) + abs(a[1] - b[1])) / G))
        for m in range(n + 1):
            regs.update(g.regs_at(a[0], a[1] + (b[1] - a[1]) * m / n))        # vertical leg at the upstream x
    g.charge(s["name"], int(s["width"]) + 1, regs)


def attempt(P, raw, tn, a, sel, order, ban, add):
    """route + site the slots of `sel` in `order`; -> (ok, slot records, [(n, lanes)], channels left over, failed slot)."""
    t = raw["partition_types"][tn]
    names = [s["name"] for s in sel]
    g = Grid(t, a.per_um, a.h_per_um, a.max, a.over_use)
    for s in t["ft_slots"]:
        if s["name"] not in names:
            charge_fixed(g, s)
    slots, added = [], []
    for s in sorted(sel, key=lambda x: order.index(x["name"])):
        r = dict(slot=s["name"], width=int(s["width"])); slots.append(r)
        bits = int(s["width"]) + 1
        lids = SF.slot_lanes(P, tn, s["name"])
        lim_touch = max(LIMIT, SF.max_slot_hop(P, lids, tn, s["name"])[0])
        A, B = face_cell(g, s["in_face"], s["in_window_um"]), face_cell(g, s["out_face"], s["out_window_um"])
        fan = pin_fan(g, s)
        path = g.route(s["name"], bits, A, B, a.route_max, fan)
        if path is None:
            r["why"] = "no route within channel capacity"
            return False, slots, added, [], s["name"]
        g.charge(s["name"], bits, g.path_regs(path, fan))
        if not place_slot(P, raw, tn, s, g, path, add, lim_touch, r, ban):
            return False, slots, added, [], s["name"]
        if r.get("added"):
            added.append((r["added"], r["lane_rows"]))
    left = over(t, a.per_um, a.max)
    return not left, slots, added, left, None


def fix_type(P, raw, tn, a, rec):
    t = raw["partition_types"][tn]
    keep = json.dumps(t["ft_slots"])

    def restore():
        for x, y in zip(t["ft_slots"], json.loads(keep)):
            x.clear(); x.update(y)
    ns = [s for s in t["ft_slots"] if s.get("in_face", "W") in "NS" and s.get("out_face", "E") in "NS"
          and s["in_face"] != s["out_face"] and s.get("bit_sites_um") and len(s.get("regs_um") or []) == int(s["stations"])]
    ov = over(t, a.per_um, a.max)
    hit = [s for s in ns if any(in_rect(r, x, y) for r, _, _ in ov for st in s["bit_sites_um"] for x, y in st[::4])]
    rec.update(over_before=len(ov), worst_before=round(max(u for _, _, u in all_channels(t, a.per_um)), 3))
    wide = [s for s in ns if int(s["width"]) >= 16]
    done = []
    for add in ((False, True) if a.add else (False,)):
        for sel in (hit, wide):
            names = [s["name"] for s in sel]
            if not names or (names, add) in done:
                continue
            done.append((names, add))
            order = [s["name"] for s in sorted(sel, key=lambda x: -int(x["width"]))]
            ban, tried = [], set()
            for it in range(8):
                tried.add(tuple(order))
                ok, slots, added, left, bad = attempt(P, raw, tn, a, sel, order, ban, add)
                if ok:
                    for n, lids in added:
                        for lid in lids:
                            row = raw["latency"]["lanes"][lid]
                            for fld in ("stations", "cycles", "natural"):
                                row[fld] = int(row[fld]) + n
                    for s in sel:
                        s["note"] = (s.get("note", "") + " | ft_channel_route 11-17: re-slotted by channel capacity").strip(" |")
                    rec.update(ok=True, slots=slots, rerouted=names, over_after=0, passes=it + 1,
                               worst_after=round(max(u for _, _, u in all_channels(t, a.per_um)), 3),
                               stations_added=sum(n for n, _ in added), cycles_added=sum(n * len(l) for n, l in added))
                    return True
                rec.setdefault("attempts", []).append(dict(rerouted=names, add=add, order=list(order), slots=slots, over_left=[
                    dict(x=[round(r[0], 2), round(r[2], 2)], y=[round(r[1], 2), round(r[3], 2)], bits=b, util=round(u, 3))
                    for r, b, u in left]))
                restore()
                if left:                                    # wires fit, station bands crowd a channel: keep stations out
                    new = [r for r, _, _ in left if r not in ban]
                    if not new:
                        break
                    ban += new; continue
                order = [bad] + [n for n in order if n != bad]       # the slot that failed routes first
                if tuple(order) in tried:
                    break
    rec["ok"] = False
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--type", default=r".")
    ap.add_argument("--max", type=float, default=C.FT_CHANNEL_TRACK_MAX)
    ap.add_argument("--per-um", type=float, default=C.FT_CHANNEL_TRACKS_PER_UM)
    ap.add_argument("--h-per-um", type=float, default=H_PER_UM)
    ap.add_argument("--route-max", type=float, default=1.0, help="fraction of the gap capacity (MAX x tracks) the router "
                    "may fill: < 1 routes to a design target under the gate, e.g. 0.857 = 0.60 of the tracks")
    ap.add_argument("--over-use", type=float, default=OVER_USE, help="share of the M7 (M6) tracks over an M5-ceiling core "
                    "that ft bundles may take (0 = never cross a core)")
    ap.add_argument("--add", action="store_true"); ap.add_argument("--rows-only", action="store_true")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    led = []; bad = 0
    for tn in sorted(raw["partition_types"]):
        t = raw["partition_types"][tn]
        if not re.search(a.type, tn) or not t.get("ft_slots"):
            continue
        try:
            if not over(t, a.per_um, a.max):
                continue
        except ValueError:
            continue
        rec = dict(type=tn)
        ok = fix_type(P, raw, tn, a, rec)
        bad += not ok
        led.append(rec)
        print(tn, "OK" if ok else "FAIL", rec.get("worst_before"), "->", rec.get("worst_after"), "rerouted", rec.get("rerouted"),
              "stations+", rec.get("stations_added"), "lane cycles+", rec.get("cycles_added"), flush=True)
    done = sorted(r["type"] for r in led if r.get("ok"))
    if a.rows_only:
        Path(a.out).write_text(json.dumps({tn: raw["partition_types"][tn] for tn in done}) + "\n")
    else:
        raw["note"] = "FT-CHANNEL-ROUTE-1 ft_channel_route <- " + raw.get("note", "")[:200]
        Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    print("types over %.2f: %d, fixed %d" % (a.max, len(led), len(done)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
