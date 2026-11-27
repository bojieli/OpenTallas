#!/usr/bin/env python3
"""ft_core_detour.py -- C-FT-CROSSES-CORE generator fix: re-site hop-chain stations so no planned hop needs a path through a core.

PRE ADV-FT-CROSSES-CORE (adv_fp_floorplan.core_crossings, report only) flags planned legs whose straight pin-to-pin path
crosses a hard-core box.  Core interiors carry no routing capacity, so such a leg detours through the bordering streets, and
C-STREET (ADV-FP-STREET) counts those bits as detours on the streets.  This tool removes the crossing at its SOURCE (it never
resizes a street).

FLAG (default OFF): plan top-level  "ft_core_detour": {"enable": 1}  (optional "types": [...]).  With the key absent `apply`
returns the plan object untouched and the CLI copies the input bytes (byte-identical).

What it does (zero added cycles): for every hop chain of a flagged type -- ft_slots stations (bit sites translated rigidly with
the station) and internal_stations regs_um chains -- a DP over candidate station points (the station's own site, a 7 x 7 lattice
within 60 um, and the outer corners of nearby cores at +2.5 um) picks points so that every hop is Manhattan-clear (a Manhattan L
between the two points crosses no core: the router is Manhattan) and no hop exceeds max(405 x 0.98 - 2 um, its current length),
including the hop to the fixed end (to_um / out-face centre).  Cost = non-clear hops, then total station displacement.  The chain
is replaced only when it has strictly fewer non-clear hops.  Station COUNT, port windows, pins, cores and outlines never change,
so there is no producer / consumer / LATCHECK cycle effect (LEG405 is held, never relaxed).  A ft-slot station moves only where
its translated bit sites stay >= 1 um outside every core.
Chains that cannot be made clear without a longer path (e.g. hd_tile reg line>ad1 > eA2, 128 b) are left unchanged: they need
+k stations (owner-delegated latency, to be carried through producer, consumer and LATCHECK by the type's row) or a pin / core
re-site, and are reported by the ledger as bad_hops_after > 0.

    ft_core_detour.py PLAN [--out PLAN2] [--types a,b] [--ledger L.json]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import adv_fp_floorplan as A  # noqa: E402

FLAG = "ft_core_detour"


def enabled(raw):
    v = (raw or {}).get(FLAG) if isinstance(raw, dict) else None
    return bool(isinstance(v, dict) and v.get("enable"))


def _cores(ty):
    return [c for c in ty.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]


REACH_BUDGET = 394.9    # ft_corridor hop budget: 405 x 0.98 - 2 um (Manhattan)
GRID_R, GRID_N = 60.0, 7  # candidate lattice around a station: +-60 um, 7 x 7
CORNER_CLR = 2.5          # candidate corner points sit this far outside a core edge (pin-access ring + 0.5)
MAX_CAND_PTS = 80


def _boxes(ty):
    return [A._box(c) for c in _cores(ty) if c["outline_um"][0] * c["outline_um"][1] > A.MIN_CORE_UM2]


def clear_straight(a, b, bx):
    return all(A._inside_um(a, b, x) < A.CROSS_MIN_UM for x in bx)


def clear_manhattan(a, b, bx):
    """a Manhattan L (either corner) between a and b crosses no core box: the router is Manhattan, so this is the
    realistic crossing test (the straight pin-to-pin diagonal over-counts)."""
    return A._l_clear(a, b, bx)


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


CELL = (1.404, 0.27)     # one bit-site footprint (ft_corridor.CELL)
SITE_CELL_UM = 12.0      # one station per 12-um cell (ADV-STATION-STACK / V1NSITE bank pitch)
EDGE = 4.32              # CORE_AREA margin used by ADV-BITSITE-AREA
KEEPOFF = 2.0            # placed-macro keep-off for stations / sites (ft_corridor.KEEPOFF)


class Ctx:
    """per-type legality: macro boxes (keep-off), core area, one-station-per-cell occupancy, foreign bit-site hash."""

    def __init__(self, ty):
        import schema as S
        self.W, self.H = ty["outline_um"]
        self.bx = _boxes(ty)
        try:
            self.mbx = list(S.placed_macro_boxes(ty, halo=KEEPOFF).values())
        except Exception:
            self.mbx = [(b[0] - KEEPOFF, b[1] - KEEPOFF, b[2] + KEEPOFF, b[3] + KEEPOFF) for b in self.bx]
        self.occ = {}
        self.sites = {}
        for kind in ("internal_stations", "ft_slots"):
            for n, s in enumerate(ty.get(kind) or []):
                for q in s.get("regs_um") or []:
                    self._occ(q, +1)
                for k, st in enumerate(s.get("bit_sites_um") or []):
                    for p in st:
                        if p and isinstance(p[0], (int, float)):
                            self.sites.setdefault(self._sk(p), []).append((kind, n, k))

    @staticmethod
    def _ck(q):
        return (int(q[0] // SITE_CELL_UM), int(q[1] // SITE_CELL_UM))

    @staticmethod
    def _sk(p):
        return (int(p[0] // CELL[0]), int(p[1] // CELL[1]))

    def _occ(self, q, d):
        k = self._ck(q)
        self.occ[k] = self.occ.get(k, 0) + d

    def point_ok(self, q, own=None):
        if not (EDGE <= q[0] <= self.W - EDGE and EDGE <= q[1] <= self.H - EDGE):
            return False
        if any(b[0] < q[0] < b[2] and b[1] < q[1] < b[3] for b in self.mbx):
            return False
        n = self.occ.get(self._ck(q), 0) - (1 if own is not None and self._ck(own) == self._ck(q) else 0)
        return n <= 0

    def sites_ok(self, sites, dx, dy, me):
        for p in sites:
            x, y = p[0] + dx, p[1] + dy
            if not (EDGE <= x <= self.W - EDGE and EDGE <= y <= self.H - EDGE):
                return False
            if any(b[0] < x < b[2] and b[1] < y < b[3] for b in self.mbx):
                return False
            kx, ky = self._sk((x, y))
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    for o in self.sites.get((kx + i, ky + j), ()):
                        if o != me:
                            return False
        return True


def _cand_points(p, bx, ctx, fixed):
    if fixed:
        return [tuple(p)]
    pts = [tuple(p)]
    step = 2 * GRID_R / (GRID_N - 1)
    for i in range(GRID_N):
        for j in range(GRID_N):
            pts.append((p[0] - GRID_R + i * step, p[1] - GRID_R + j * step))
    for x0, y0, x1, y1 in bx:
        if x0 - GRID_R - 20 < p[0] < x1 + GRID_R + 20 and y0 - GRID_R - 20 < p[1] < y1 + GRID_R + 20:
            for cx in (x0 - CORNER_CLR, x1 + CORNER_CLR):
                for cy in (y0 - CORNER_CLR, y1 + CORNER_CLR):
                    pts.append((cx, cy))
    out, seen = [], set()
    for q in pts:
        q = (round(q[0], 3), round(q[1], 3))
        if q in seen or (q != tuple(p) and not ctx.point_ok(q, own=p)):
            continue
        seen.add(q)
        out.append(q)
    out.sort(key=lambda q: _man(q, p))
    return out[:MAX_CAND_PTS]


def resite_chain(fixed, stations, bx, ctx, end=None, pinned=(), sites_ok=None):
    """zero-cycle re-site of one hop chain.  fixed = the fixed start point, stations = [(x, y)] in order (indexes in `pinned`
    never move), end = fixed end point.  DP over candidate points per station: every hop Manhattan-clear and <= max(REACH_BUDGET,
    its current length); cost = non-clear hops first, then total displacement.  Returns (new stations, bad hops before, after)."""
    pts0 = [tuple(fixed)] + [tuple(s) for s in stations] + ([tuple(end)] if end else [])
    bad0 = sum(0 if clear_manhattan(a, b, bx) else 1 for a, b in zip(pts0, pts0[1:]))
    if bad0 == 0:
        return list(stations), 0, 0
    cap = [max(REACH_BUDGET, _man(a, b)) for a, b in zip(pts0, pts0[1:])]
    cands = [_cand_points(s, bx, ctx, k in pinned) for k, s in enumerate(stations)]
    if sites_ok is not None:
        cands = [[q for q in c if sites_ok(k, q)] or [tuple(stations[k])] for k, c in enumerate(cands)]
    ns = len(cands)
    if end:
        cands.append([tuple(end)])
    INF = float("inf")
    prev, prevpts, back = [(0.0, None)], [tuple(fixed)], []
    for k, cs in enumerate(cands):
        cur = []
        for q in cs:
            best = (INF, None)
            for pi, pp in enumerate(prevpts):
                if _man(pp, q) > cap[k]:
                    continue
                c = prev[pi][0] + (_man(q, stations[k]) * 0.01 if k < ns else 0.0) + (0 if clear_manhattan(pp, q, bx) else 1e4)
                if c < best[0]:
                    best = (c, pi)
            cur.append(best)
        back.append(cur)
        prev, prevpts = cur, cs
    if not prev or min(c for c, _ in prev) == INF:
        return list(stations), bad0, bad0
    k = min(range(len(prev)), key=lambda i: prev[i][0])
    path = []
    for lvl in range(len(cands) - 1, -1, -1):
        path.append(cands[lvl][k])
        k = back[lvl][k][1]
    path.reverse()
    path = path[:ns]
    pts1 = [tuple(fixed)] + [tuple(q) for q in path] + ([tuple(end)] if end else [])
    bad1 = sum(0 if clear_manhattan(a, b, bx) else 1 for a, b in zip(pts1, pts1[1:]))
    if bad1 >= bad0:
        return list(stations), bad0, bad0
    return [list(q) for q in path], bad0, bad1


def detour_type(raw, tn, ledger):
    """re-site, in place, the crossing hop chains of type tn: ft_slots INTERIOR stations (first and last stay: the neighbouring
    partition's hop into this slot, ADV-G0-HOPS, depends on them; bit sites translate rigidly with the station and must stay
    inside the core area, off every macro keep-off and clear of all other bit sites) and internal_stations regs_um.  Station
    COUNT never changes (no new cycle); one station per 12-um cell (no ADV-STATION-STACK).  True when anything changed."""
    ty = raw["partition_types"][tn]
    ctx = Ctx(ty)
    bx = ctx.bx
    changed = 0
    for n, s in enumerate(ty.get("ft_slots") or []):
        regs = s.get("regs_um") or []
        if len(regs) < 4:
            continue
        st = [tuple(q) for q in regs[1:]]
        bs = s.get("bit_sites_um") or []

        def ok(k, q, st=st, bs=bs, n=n):
            if k >= len(bs) or not bs[k]:
                return True
            return ctx.sites_ok(bs[k], q[0] - st[k][0], q[1] - st[k][1], ("ft_slots", n, k))
        end = (A._face_center(s.get("out_face"), s["out_window_um"], ctx.W, ctx.H)
               if s.get("out_face") and s.get("out_window_um") else None)
        new, b0, b1 = resite_chain(regs[0], st, bx, ctx, end=end, pinned={0, len(st) - 1}, sites_ok=ok)
        if b1 < b0:
            for k, q in enumerate(new):
                if tuple(q) == st[k]:
                    continue
                dx, dy = q[0] - st[k][0], q[1] - st[k][1]
                ctx._occ(regs[k + 1], -1)
                ctx._occ(q, +1)
                if k < len(bs):
                    for p in bs[k]:
                        ctx.sites.get(ctx._sk(p), []).remove(("ft_slots", n, k))
                    bs[k] = [[round(p[0] + dx, 6), round(p[1] + dy, 6)] for p in bs[k]]
                    for p in bs[k]:
                        ctx.sites.setdefault(ctx._sk(p), []).append(("ft_slots", n, k))
                regs[k + 1] = [round(q[0], 4), round(q[1], 4)]
            changed += 1
        ledger.append(dict(type=tn, kind="ft_slot", slot=s.get("name"), bad_hops_before=b0, bad_hops_after=b1))
    for s in ty.get("internal_stations") or []:
        regs, fr = s.get("regs_um") or [], s.get("from_um")
        if not regs or not fr or s.get("bit_sites_um"):
            continue
        st = [tuple(q) for q in regs]
        new, b0, b1 = resite_chain(fr, st, bx, ctx, end=s.get("to_um"))
        if b1 < b0:
            for k, q in enumerate(new):
                ctx._occ(st[k], -1)
                ctx._occ(q, +1)
            s["regs_um"] = [[round(q[0], 4), round(q[1], 4)] for q in new]
            changed += 1
        if b0:
            ledger.append(dict(type=tn, kind="station_chain", conn=s.get("conn"), bad_hops_before=b0, bad_hops_after=b1))
    return bool(changed)


def apply(raw, types=None, max_cand=None):
    """returns (raw, ledger).  Flag absent -> raw untouched, empty ledger."""
    if not enabled(raw):
        return raw, []
    cfg = raw[FLAG]
    ledger = []
    want = set(types or cfg.get("types") or [])
    for tn, ty in sorted(raw["partition_types"].items()):
        if want and tn not in want:
            continue
        if A.core_crossings(ty):
            detour_type(raw, tn, ledger)
    return raw, ledger


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--types")
    ap.add_argument("--ledger")
    a = ap.parse_args()
    src = Path(a.plan)
    raw = json.loads(src.read_text())
    if not enabled(raw):
        print(f"{FLAG}: flag absent, plan unchanged")
        if a.out and Path(a.out) != src:
            shutil.copyfile(src, a.out)
        return 0
    raw, ledger = apply(raw, a.types.split(",") if a.types else None)
    Path(a.out or a.plan).write_text(json.dumps(raw, indent=0) + "\n")
    if a.ledger:
        Path(a.ledger).write_text(json.dumps(ledger, indent=1) + "\n")
    n = sum(1 for x in ledger if x["bad_hops_after"] < x["bad_hops_before"])
    print(f"{FLAG}: {n} chain(s) re-sited, {sum(1 for x in ledger if x['bad_hops_after'])} chain(s) still with a non-clear hop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
