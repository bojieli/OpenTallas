"""pg_track_census.py (FLOW-PGCAP-1 11-13): read-only census of GRT guides on PG-stripe rows/columns with no DRT-legal
track (the DRT-0255 class that pg_track_truth.tcl removes).  Run inside the ORFS image on a 5_1_grt.odb:
  ODB=/work/run/results/asap7/<dp>/base/5_1_grt.odb NETS="<net> ..." openroad -python -exit pg_track_census.py
A track t on layer L (M4+) is spacing-illegal at a PG stripe [lo, hi] (across the preferred direction) when
t + hw + sp > lo and t - hw - sp < hi.  A run guide whose across-span holds tracks but no legal one is DEAD.  Prints the
per-layer DEAD / run guide counts, and for each net in NETS its guides with legal / total tracks."""
import sys, bisect
import openroad as O
import os; odb_path = os.environ["ODB"]; want = set(os.environ.get("NETS", "").split())
T = O.Tech(); D = O.Design(T); D.readDb(odb_path); b = D.getBlock(); u = b.getDbUnitsPerMicron()
tech = b.getTech() if hasattr(b, 'getTech') else T.getDB().getTech()
ill = {}   # layer -> sorted list of illegal intervals (track coords) per stripe, with along-span
grid = {}
for net in b.getNets():
    if not net.isSpecial() or net.getSigType() not in ('POWER', 'GROUND'):
        continue
    for sw in net.getSWires():
        for w in sw.getWires():
            if w.isVia():
                continue
            L = w.getTechLayer()
            if L is None or L.getType() != 'ROUTING' or L.getRoutingLevel() < 4:
                continue
            hor = L.getDirection() == 'HORIZONTAL'
            x0, y0, x1, y1 = w.xMin(), w.yMin(), w.xMax(), w.yMax()
            if hor and (x1 - x0) <= (y1 - y0):
                continue
            if (not hor) and (y1 - y0) <= (x1 - x0):
                continue
            ln = L.getName()
            if ln not in grid:
                tg = b.findTrackGrid(L)
                if tg is None:
                    continue
                g = tg.getGridY() if hor else tg.getGridX()
                grid[ln] = (sorted(g), L.getWidth() // 2, L.getSpacing(), hor)
            lo, hi, a0, a1 = (y0, y1, x0, x1) if hor else (x0, x1, y0, y1)
            ill.setdefault(ln, []).append((lo, hi, a0, a1))

def tracks(ln, lo, hi):
    g = grid[ln][0]
    return g[bisect.bisect_left(g, lo):bisect.bisect_right(g, hi)]

IDX = {}
def legal(ln, t, a0, a1):
    _, hw, sp, _ = grid[ln]
    if ln not in IDX:
        S = sorted(ill.get(ln, [])); IDX[ln] = (S, [s[0] for s in S], max([s[1] - s[0] for s in S] or [0]))
    S, los, mw = IDX[ln]
    i0 = bisect.bisect_left(los, t - hw - sp - mw); i1 = bisect.bisect_right(los, t + hw + sp)
    for (lo, hi, s0, s1) in S[i0:i1]:
        if s1 < a0 or s0 > a1:
            continue
        if t + hw + sp > lo and t - hw - sp < hi:
            return False
    return True

dead = {}; tot = {}; deadnets = set()
for net in b.getNets():
    if net.isSpecial():
        continue
    nm = net.getName()
    for gd in net.getGuides():
        L = gd.getLayer(); ln = L.getName()
        if ln not in grid:
            continue
        r = gd.getBox(); hor = grid[ln][3]
        lo, hi, a0, a1 = (r.yMin(), r.yMax(), r.xMin(), r.xMax()) if hor else (r.xMin(), r.xMax(), r.yMin(), r.yMax())
        if (a1 - a0) <= (hi - lo):   # via-stack / point guide, not a run along the layer
            if nm not in want:
                continue
        ts = tracks(ln, lo, hi)
        nl = sum(1 for t in ts if legal(ln, t, a0, a1))
        tot[ln] = tot.get(ln, 0) + 1
        if ts and nl == 0:
            dead[ln] = dead.get(ln, 0) + 1; deadnets.add(nm)
        if nm in want:
            print('GUIDE', nm, ln, [round(v / u, 3) for v in (r.xMin(), r.yMin(), r.xMax(), r.yMax())], 'tracks', len(ts), 'legal', nl)
print('CENSUS', odb_path, 'dead_guides', dead, 'run_guides', tot, 'dead_nets', len(deadnets))
