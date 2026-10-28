"""Street / channel grid (generalised from OpenTallas tools/die_plan/streets.py, HBM-STREETS-1, METHODOLOGY 12.10c).

A STREET is free die area (no hard core, PHY or blockage) at least width_um wide in both axes, in the largest
4-connected free component (pockets enclosed by macros are not streets: a clock leg into them crosses a macro).
Rules checked:
  street_width   width_um >= width required by the DEMAND that must sit in a street cross-section:
                 clock repeater columns + hold-buffer columns + feed-through repeater columns (bits / bits_per_col),
                 divided by the fill margin (default 0.6), snapped up to the raster;
  street_reach   every point of every hard macro is <= reach_um from the street network along a row or column
                 (a repeated wire leaves the street straight into the macro).  Default reach = the model reach (405 um).
Legal clock-cell sites (repeaters, tree nodes) = street cells; an optional per-macro island list adds in-macro
sites (pushdown islands built into the macro).
"""
import math

import numpy as np


def required_width(dem, raster_um):
    """dem: dict(clock_cols, clock_col_um, hold_cols, hold_col_um, ft_bits, ft_bits_per_col, ft_col_um, fill)."""
    ft_cols = math.ceil(dem.get("ft_bits", 0) / max(1, dem.get("ft_bits_per_col", 64)))
    w = (dem.get("clock_cols", 1) * dem.get("clock_col_um", 4.32) + dem.get("hold_cols", 1) * dem.get("hold_col_um", 4.32)
         + ft_cols * dem.get("ft_col_um", 4.32)) / dem.get("fill", 0.6)
    return math.ceil(w / raster_um - 1e-9) * raster_um


def raster(W, H, rects, g):
    nx, ny = int(math.ceil(W / g)), int(math.ceil(H / g))
    occ = np.zeros((ny, nx), dtype=bool)
    for r in rects:
        i0 = max(0, int(math.ceil(r[0] / g - 0.5 - 1e-9)))
        i1 = min(nx - 1, int(math.floor(r[2] / g - 0.5 + 1e-9)))
        j0 = max(0, int(math.ceil(r[1] / g - 0.5 - 1e-9)))
        j1 = min(ny - 1, int(math.floor(r[3] / g - 0.5 + 1e-9)))
        if i1 >= i0 and j1 >= j0:
            occ[j0:j1 + 1, i0:i1 + 1] = True
    return occ


def _runs(free, axis):
    a = np.moveaxis(free, axis, -1)
    n = a.shape[-1]
    idx = np.arange(n)
    left = np.maximum.accumulate(np.where(~a, idx, -1), axis=-1)
    right = np.flip(np.minimum.accumulate(np.flip(np.where(~a, idx, n), axis=-1), axis=-1), axis=-1)
    return np.moveaxis(np.where(a, right - left - 1, 0), -1, axis)


def _dist(mask, axis):
    a = np.moveaxis(mask, axis, -1)
    n = a.shape[-1]
    idx = np.arange(n, dtype=np.float64)
    big = 1e18
    last = np.maximum.accumulate(np.where(a, idx, -big), axis=-1)
    nxt = np.flip(np.minimum.accumulate(np.flip(np.where(a, idx, big), axis=-1), axis=-1), axis=-1)
    return np.moveaxis(np.minimum(idx - last, nxt - idx), -1, axis)


def components(mask):
    """4-connected components (row runs + union-find) -> (labels, sizes)."""
    ny, nx = mask.shape
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    rows = []
    for j in range(ny):
        row = mask[j]
        if not row.any():
            rows.append([])
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur = []
        for s, e in zip(st.tolist(), en.tolist()):
            k = len(parent)
            parent.append(k)
            cur.append((s, e, k))
        prev = rows[-1] if rows else []
        p = 0
        for s, e, k in cur:
            while p < len(prev) and prev[p][1] <= s:
                p += 1
            q = p
            while q < len(prev) and prev[q][0] < e:
                ra, rb = find(k), find(prev[q][2])
                if ra != rb:
                    parent[ra] = rb
                q += 1
        rows.append(cur)
    lab = np.full(mask.shape, -1, dtype=np.int64)
    sizes = {}
    for j, cur in enumerate(rows):
        for s, e, k in cur:
            r = find(k)
            lab[j, s:e] = r
            sizes[r] = sizes.get(r, 0) + (e - s)
    return lab, sizes


class Streets:
    """street raster + legal-site queries.  keepouts: [(x0, y0, x1, y1, name, kind)]."""

    def __init__(self, W, H, keepouts, raster_um=8.64, width_um=None, demand=None, reach_um=405.0, islands=()):
        self.W, self.H, self.g = W, H, raster_um
        self.keepouts = list(keepouts)
        self.req_width = required_width(demand or {}, raster_um) if demand is not None else raster_um
        self.width = width_um if width_um is not None else self.req_width
        self.reach = reach_um
        occ = raster(W, H, self.keepouts, raster_um)
        self.free = ~occ
        k = max(1, int(math.ceil(self.width / raster_um - 1e-9)))
        wide = self.free & (_runs(self.free, 1) >= k) & (_runs(self.free, 0) >= k)
        lab, sizes = components(wide)
        self.main = max(sizes, key=sizes.get) if sizes else None
        self.net = (lab == self.main) if self.main is not None else np.zeros_like(wide)
        self.pockets = len(sizes) - (1 if sizes else 0)
        self.pocket_area_mm2 = float(sum(v for kk, v in sizes.items() if kk != self.main)) * raster_um ** 2 / 1e6
        # legal clock-cell sites: any free cell (a cell needs only one site; streets narrower than width are still
        # legal sites, they only fail the street-width rule) + declared in-macro island windows
        self.site = self.free.copy()
        self.islands = list(islands)
        for r in self.islands:
            sub = raster(W, H, [r], raster_um)
            self.site |= sub

    # --- queries ---------------------------------------------------------------------------------------------
    def cell(self, x, y):
        i = min(self.free.shape[1] - 1, max(0, int(x // self.g)))
        j = min(self.free.shape[0] - 1, max(0, int(y // self.g)))
        return i, j

    def legal(self, x, y):
        i, j = self.cell(x, y)
        return bool(self.site[j, i])

    def macro_at(self, x, y):
        for r in self.keepouts:
            if r[0] < x < r[2] and r[1] < y < r[3]:
                return r
        return None

    def nearest_site(self, x, y, max_move):
        """nearest legal site (Manhattan, raster centres) within max_move um, or None."""
        if self.legal(x, y):
            return (x, y), 0.0
        i0, j0 = self.cell(x, y)
        R = int(math.ceil(max_move / self.g))
        best = None
        ny, nx = self.site.shape
        for r in range(1, R + 1):
            for di in range(-r, r + 1):
                dj = r - abs(di)
                for sj in ((dj, -dj) if dj else (0,)):
                    i, j = i0 + di, j0 + sj
                    if 0 <= i < nx and 0 <= j < ny and self.site[j, i]:
                        p = ((i + 0.5) * self.g, (j + 0.5) * self.g)
                        d = abs(p[0] - x) + abs(p[1] - y)
                        if d <= max_move and (best is None or d < best[1]):
                            best = (p, d)
            if best is not None:
                return best
        return None

    def reach_report(self):
        dist = np.minimum(_dist(self.net, 0), _dist(self.net, 1)) * self.g
        ny, nx = self.free.shape
        rows = []
        for r in self.keepouts:
            if r[5] != "hard_core":
                continue
            i0 = max(0, int(math.floor(r[0] / self.g)))
            i1 = min(nx, max(i0 + 1, int(math.ceil(r[2] / self.g))))
            j0 = max(0, int(math.floor(r[1] / self.g)))
            j1 = min(ny, max(j0 + 1, int(math.ceil(r[3] / self.g))))
            d = float(dist[j0:j1, i0:i1].max())
            rows.append(dict(name=r[4], street_dist_um=None if d >= 1e17 else round(d, 1)))
        return rows

    def summary(self):
        g = self.g
        reach = self.reach_report()
        over = [r for r in reach if r["street_dist_um"] is None or r["street_dist_um"] > self.reach + 1e-6]
        return dict(raster_um=g, width_um=self.width, required_width_um=self.req_width, reach_um=self.reach,
                    street_area_mm2=round(float(self.net.sum()) * g * g / 1e6, 4),
                    free_area_mm2=round(float(self.free.sum()) * g * g / 1e6, 4),
                    pockets=self.pockets, pocket_area_mm2=round(self.pocket_area_mm2, 4),
                    macros=len(reach), macros_over_reach=len(over),
                    worst=sorted(over, key=lambda r: -(r["street_dist_um"] or 1e9))[:10])
