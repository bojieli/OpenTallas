#!/usr/bin/env python3
"""STATION-ROUTE-SPREAD (OPUS-FIX-KV-PV-R3 11-20, COORD: die-agnostic): plan station chains whose stations are bunched at one
end (KV pv R8 bundle-mate fault rows: 6 FIRM stations within 100 um of the out face while the launch flop sits 2.1 mm away,
pv_v1n u_vport_E.fault -> u_ist_o_vport_E_N_f_0 at -7,679 ps; S81 vp_sr +1 stage co-sited with its launch) get their
stations re-sited along the real route from the PLACED driver to the PLACED sink, every hop <= --reach (300 um, the hop cap).

Reads a placed geometry dump of the newest kit of the type (tools/autopilot/geom_dump.tcl, AUTO-GEOM format): station k
of internal_stations conn bus:<B> is the cell set u_ist_<B>_<k>[./...]; the chain's driver is the cell / pin that drives
station 0's data input through BUF / INV (nets with at most 2*bits+2 sinks, so clock / reset / enable fanout is ignored);
its sink is what the last station's output reaches through BUF / INV.  The route is a shortest Manhattan path around the
hard-macro boxes (kind M, + --halo) on a --grid-um grid, with a bend penalty.  Stations go to equal route fractions
k/(n+1); n = max(current, ceil(L / reach) - 1) (added stations = added cycles, OWNER pre-approved; --keep-count keeps n
and reports the hop it leaves).  The plan's regs_um order is kept: a row whose regs_um[k] sits at station n-1-k is
written reversed.  Only rows whose current worst hop (driver -> stations -> sink, placed) is over --reach are changed.

  python3 -I station_route_spread.py PLAN TYPE GEOM OUT_PLAN REPORT.json [--reach 300] [--keep-count] [--conn RE]
          [--grid-um 5] [--halo 2]

Plan delta only (internal_stations[].regs_um / from_um / to_um / note of the changed rows; every other byte kept).
Not a gate; the report lists every chain with hop before / after and the cycles it adds.  An added station changes the
bus latency: re-run gen.py latency and LATCHECK on the event (a bundle mate with a cycle-matched partner is listed)."""
import argparse
import heapq
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import geom_rules  # noqa: E402
from reset_leg_plan import dumper  # noqa: E402  (byte-format-preserving plan writer)

REACH_UM = 300.0


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centroid(pts):
    pts = list(pts)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None


def _xy(D, r):
    if r[0] == "p":
        p = D.pin_by_k.get(r[1])
        return (p["x"], p["y"]) if p else None
    c = D.cells.get(r[1])
    return geom_rules.ctr(c) if c else None


def stations(D, bus):
    """{k: [cell id]} of u_ist_<bus>_<k> sequential cells"""
    rx = re.compile(r"(?:^|[./])u_ist_" + re.escape(bus) + r"_(\d+)(?:[./\[$]|$)")
    out = {}
    for cid, c in D.cells.items():
        if c[0] != "S":
            continue
        m = rx.search(c[6].replace("\\", ""))
        if m:
            out.setdefault(int(m.group(1)), []).append(cid)
    return out


def _data_ins(D, cid, lim):
    for n, isclk in D.cell_in.get(cid, []):
        if not isclk and len(D.nets[n][2]) <= lim:
            yield n


def back(D, cid, own, lim):
    """XY of the drivers of cell cid's data inputs (through B cells), not counting cells of the chain itself"""
    pts = []
    for n in _data_ins(D, cid, lim):
        r = D.nets[n][1]
        for _ in range(40):
            if r is None:
                break
            if r[0] == "i" and D.kind(r[1]) == "B":
                ins = list(_data_ins(D, r[1], lim))
                if not ins:
                    break
                r = D.nets[ins[0]][1]
                continue
            if not (r[0] == "i" and r[1] in own):
                xy = _xy(D, r)
                if xy:
                    pts.append(xy)
            break
    return pts


def fwd(D, cid, own, lim):
    pts = []
    front = [n for n in D.drives.get(cid, [])]
    seen = set()
    for _ in range(40):
        nf = []
        for n in front:
            if n in seen:
                continue
            seen.add(n)
            for s in D.nets[n][2]:
                if s[0] == "i" and D.kind(s[1]) == "B":
                    nf.extend(D.drives.get(s[1], []))
                elif not (s[0] == "i" and s[1] in own):
                    xy = _xy(D, s)
                    if xy:
                        pts.append(xy)
        if not nf:
            break
        front = nf
    return pts


class Grid:
    def __init__(self, die, boxes, g):
        self.x0, self.y0, x1, y1 = die
        self.g = g
        self.nx = int(math.ceil((x1 - self.x0) / g)) + 1
        self.ny = int(math.ceil((y1 - self.y0) / g)) + 1
        self.blk = bytearray(self.nx * self.ny)
        for (a, b, c, d) in boxes:
            for i in range(max(0, int((a - self.x0) / g)), min(self.nx, int(math.ceil((c - self.x0) / g)) + 1)):
                for j in range(max(0, int((b - self.y0) / g)), min(self.ny, int(math.ceil((d - self.y0) / g)) + 1)):
                    self.blk[i * self.ny + j] = 1

    def cell(self, p):
        return (min(self.nx - 1, max(0, int(round((p[0] - self.x0) / self.g)))),
                min(self.ny - 1, max(0, int(round((p[1] - self.y0) / self.g)))))

    def free_near(self, c):
        if not self.blk[c[0] * self.ny + c[1]]:
            return c
        best = None
        for r in range(1, max(self.nx, self.ny)):
            for i in range(c[0] - r, c[0] + r + 1):
                for j in (c[1] - r, c[1] + r) if abs(i - c[0]) != r else range(c[1] - r, c[1] + r + 1):
                    if 0 <= i < self.nx and 0 <= j < self.ny and not self.blk[i * self.ny + j]:
                        d = abs(i - c[0]) + abs(j - c[1])
                        if best is None or d < best[0]:
                            best = (d, (i, j))
            if best:
                return best[1]
        return c

    def route(self, A, B, bend=4.0):
        """grid A*: shortest Manhattan path A -> B around blocked cells, + bend penalty (in grid steps); polyline um"""
        s, t = self.free_near(self.cell(A)), self.free_near(self.cell(B))
        ny = self.ny
        h = lambda c: abs(c[0] - t[0]) + abs(c[1] - t[1])  # noqa: E731
        start = (s[0], s[1], -1)
        dist = {start: 0.0}
        prev = {}
        pq = [(h(s), 0.0, start)]
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        end = None
        while pq:
            _, d, st = heapq.heappop(pq)
            if d > dist.get(st, 1e18):
                continue
            if (st[0], st[1]) == t:
                end = st
                break
            for k, (dx, dy) in enumerate(dirs):
                i, j = st[0] + dx, st[1] + dy
                if not (0 <= i < self.nx and 0 <= j < ny) or self.blk[i * ny + j]:
                    continue
                nd = d + 1.0 + (bend if st[2] not in (-1, k) else 0.0)
                ns = (i, j, k)
                if nd < dist.get(ns, 1e18):
                    dist[ns] = nd
                    prev[ns] = st
                    heapq.heappush(pq, (nd + h((i, j)), nd, ns))
        if end is None:
            return None
        cells = [end]
        while cells[-1] in prev:
            cells.append(prev[cells[-1]])
        cells.reverse()
        pts = [A] + [(self.x0 + c[0] * self.g, self.y0 + c[1] * self.g) for c in cells] + [B]
        # keep corners only
        out = [pts[0]]
        for k in range(1, len(pts) - 1):
            a, b, c = out[-1], pts[k], pts[k + 1]
            if (abs(a[0] - b[0]) < 1e-9 and abs(b[0] - c[0]) < 1e-9) or (abs(a[1] - b[1]) < 1e-9 and abs(b[1] - c[1]) < 1e-9):
                continue
            out.append(b)
        out.append(pts[-1])
        return out


def plen(pts):
    return sum(md(a, b) for a, b in zip(pts, pts[1:]))


def at(pts, f):
    d = plen(pts) * f
    for a, b in zip(pts, pts[1:]):
        l = md(a, b)
        if d <= l or b is pts[-1]:
            if l == 0:
                return b
            g = min(1.0, d / l)
            return (a[0] + (b[0] - a[0]) * g, a[1] + (b[1] - a[1]) * g)
        d -= l
    return pts[-1]


def type_delta(tname, t, D, reach=REACH_UM, keep=False, conn_re=None, grid_um=5.0, halo=2.0):
    boxes = [(c[2] - halo, c[3] - halo, c[4] + halo, c[5] + halo) for c in D.cells.values() if c[0] == "M"]
    G = None
    rows = []
    for it in t.get("internal_stations", []):
        conn = it.get("conn", "")
        if not conn.startswith("bus:") or (conn_re and not re.search(conn_re, conn)):
            continue
        bus = conn[4:]
        regs = it.get("regs_um") or []
        st = stations(D, bus)
        n = len(regs)
        rec = {"conn": conn, "stations": n}
        if not n or sorted(st) != list(range(n)):
            rec["skip"] = f"placed stations {sorted(st)[:8]} != plan {n}"
            rows.append(rec)
            continue
        own = {c for v in st.values() for c in v}
        bits = max(1, int(it.get("bits", 1)))
        lim = 2 * bits + 2
        A = centroid(p for c in st[0] for p in back(D, c, own, lim))
        B = centroid(p for c in st[n - 1] for p in fwd(D, c, own, lim))
        P = [centroid(geom_rules.ctr(D.cells[c]) for c in st[k]) for k in range(n)]
        if A is None or B is None:
            rec["skip"] = "no placed driver / sink"
            rows.append(rec)
            continue
        chain = [A] + P + [B]
        before = max(md(a, b) for a, b in zip(chain, chain[1:]))
        # plan order: regs[k] at station k, or reversed
        fwd_err = sum(md(tuple(regs[k]), P[k]) for k in range(n))
        rev_err = sum(md(tuple(regs[n - 1 - k]), P[k]) for k in range(n))
        rev = rev_err < fwd_err
        rec.update(driver_um=[round(A[0], 3), round(A[1], 3)], sink_um=[round(B[0], 3), round(B[1], 3)],
                   hop_before_um=round(before, 1), reversed=rev)
        if before <= reach:
            rows.append(rec)
            continue
        if G is None:
            G = Grid(D.die, boxes, grid_um)
        rt = G.route(A, B)
        if rt is None:
            rec["skip"] = "no route around the hard macros"
            rows.append(rec)
            continue
        L = plen(rt)
        m = n if keep else max(n, int(math.ceil(L / reach)) - 1)
        sites = [at(rt, (k + 1) / (m + 1)) for k in range(m)]
        new = [[round(x, 3), round(y, 3)] for x, y in sites]
        if rev:
            new = new[::-1]
        hop_after = L / (m + 1)
        rec.update(route_um=round(L, 1), stations_new=m, added_cycles=m - n, hop_after_um=round(hop_after, 1),
                   launch=it.get("launch", ""))
        it["regs_um"] = new
        it["from_um"], it["to_um"] = ([rec["sink_um"], rec["driver_um"]] if rev else [rec["driver_um"], rec["sink_um"]])
        it["note"] = (it.get("note", "") + f" | STATION-ROUTE-SPREAD: {n} -> {m} station(s) on the placed route "
                      f"{L:.0f} um driver -> sink, hop {before:.0f} -> {hop_after:.0f} um (+{m - n} cycle(s))").strip(" |")
        rows.append(rec)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("geom"); ap.add_argument("out_plan"); ap.add_argument("report")
    ap.add_argument("--reach", type=float, default=REACH_UM)
    ap.add_argument("--keep-count", action="store_true")
    ap.add_argument("--conn", default=None)
    ap.add_argument("--grid-um", type=float, default=5.0)
    ap.add_argument("--halo", type=float, default=2.0)
    a = ap.parse_args(argv)
    rb = Path(a.plan).read_bytes()
    plan = json.loads(rb)
    dump = dumper(rb, plan)   # chosen on the unchanged plan
    t = plan["partition_types"][a.type]
    rows = type_delta(a.type, t, geom_rules.Design(a.geom), a.reach, a.keep_count, a.conn, a.grid_um, a.halo)
    Path(a.out_plan).write_text(dump(plan))
    ch = [r for r in rows if "stations_new" in r]
    Path(a.report).write_text(json.dumps({"type": a.type, "reach_um": a.reach, "rows": rows}, indent=1) + "\n")
    print(f"{a.type}: chains {len(rows)}, over {a.reach:.0f} um re-sited {len(ch)}, added cycles "
          f"{sum(r['added_cycles'] for r in ch)}, skipped {sum(1 for r in rows if 'skip' in r)}")
    for r in ch:
        print(f"  {r['conn']}: {r['stations']} -> {r['stations_new']} stations, hop {r['hop_before_um']} -> {r['hop_after_um']} um, route {r['route_um']} um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
