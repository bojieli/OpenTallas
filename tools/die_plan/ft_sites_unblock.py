#!/usr/bin/env python3
"""PATH-KV 10-25: per-bit FT station sites that clear physical macros (schema.placed_macro_boxes:
hard cores + LEF contents; the check.check_ft_macro_sites gate of 0302d3b06a).
For every FT slot of the given types that has a station point inside a macro and no explicit
bit_sites_um: station j of bit b starts at check's own interpolated point (zroute(b), L_b*j/k);
points inside a macro box (+CLEAR) slide along that bit's route (|dt| <= L_b/(2k)), else move to the
nearest free grid point; every paired-bit hop (in pin -> s1 -> .. -> out pin) must stay <= budget.
Windows are unchanged.  A bit whose greedy move is stuck is re-sited whole by layered() (exact
L1 reachability on a 2.16-um grid, same station count); a legalisation miss retries with a tighter hop budget; only a
slot with no chain at its count gets +1 station (EXTRA_STATIONS, reported as stations_added: +1 cycle on its lanes,
regenerate the latency table with gen.py latency).  PATH-KV-REBASE 10-25: f7ch pv_v2/v6/v7/v12, 42 slots +1. Each point is legalised to a free row site
(RowAllocator, 1.404 x 0.27 cell) and written as bit_sites_um (all bits, all stages).
usage: ft_sites_unblock.py PLAN OUT TYPES [--report R]"""
import sys, json, argparse
from pathlib import Path
import numpy as np
T = Path(__file__).resolve()
sys.path.insert(0, str(T.parent))
import schema as S, check as C
from gen_phys import type_pins
sys.path.insert(0, str(T.parents[2]))
from tools.die_trial.legal_sites import RowAllocator
CELL = (1.404, .27); CLEAR = 4.32
FRAME = [0.0, 0.0]     # current type outline (main() sets it; layered() keeps stations inside the frame)

def inside(p, boxes):
    return any(x0 < p[0] < x1 and y0 < p[1] < y1 for x0, y0, x1, y1 in boxes)

def man(a, b): return abs(a[0]-b[0])+abs(a[1]-b[1])

def _move(pts, bits, k, grow, free, budget, tn, name):
    moved = 0
    for b in bits:
        ia, ib, r, L, ps = pts[b]
        for j in range(len(ps)):
            if not inside(ps[j], grow): continue
            prev = ia if j == 0 else ps[j-1]; nxt = ib if j == len(ps)-1 else ps[j+1]
            best = None
            for dt in sorted(np.arange(-L/(2*k), L/(2*k)+1e-9, 1.08), key=abs):
                q = C.point_at(r, min(max(L*(j+1)/k+dt, 0), L))
                if not inside(q, grow) and man(prev, q) <= budget and man(q, nxt) <= budget: best = q; break
            if best is None:
                d = np.abs(free-np.array(ps[j])).sum(1); okk = (np.abs(free-np.array(prev)).sum(1) <= budget) & (np.abs(free-np.array(nxt)).sum(1) <= budget)
                if not okk.any():
                    # greedy one-station move is stuck (the neighbours stay on their original points): re-site the
                    # whole bit with the layered reachability solver (same station count)
                    pts[b] = (ia, ib, r, L, layered(ia, ib, ps, k, grow, budget, tn, name, b))
                    moved += len(ps); break
                best = tuple(free[okk][np.argmin(d[okk])])
            ps[j] = (float(best[0]), float(best[1])); moved += 1
    return moved


def _l1_dt(mask, pitch):
    """Manhattan distance (um) from every grid cell to the nearest True cell of mask (two separable 1-D scans)."""
    big = 1e9
    d = np.where(mask, 0.0, big)
    for ax in (0, 1):
        d = np.moveaxis(d, ax, 0)
        for i in range(1, d.shape[0]): d[i] = np.minimum(d[i], d[i-1] + pitch)
        for i in range(d.shape[0]-2, -1, -1): d[i] = np.minimum(d[i], d[i+1] + pitch)
        d = np.moveaxis(d, 0, ax)
    return d


LAYER_PITCH = 2.16
LAYER_SLACK = 1.5      # um under the greedy budget (smax - 2): the row-site legalisation keeps the rest

def layered(ia, ib, ps, k, grow, budget, tn, name, b):
    """k-1 macro-free station points for one bit, every hop (ia -> s1 -> .. -> ib) <= budget - LAYER_SLACK, each
    station nearest to its original point among the points from which the rest of the chain is still completable:
    forward sets F_j (reachable from ia in j hops), backward sets G_j (ib reachable in k-j hops), then a sequential
    choice s_j in F(s_{j-1}) & G_j.  Exact on the 2.16-um grid (L1 distance transform), fails closed."""
    bud = budget - LAYER_SLACK
    xs = np.arange(min(ia[0], ib[0], *(p[0] for p in ps)) - bud, max(ia[0], ib[0], *(p[0] for p in ps)) + bud, LAYER_PITCH)
    ys = np.arange(min(ia[1], ib[1], *(p[1] for p in ps)) - bud, max(ia[1], ib[1], *(p[1] for p in ps)) + bud, LAYER_PITCH)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    free = (X > 8.64) & (Y > 8.64) & (X < FRAME[0] - 8.64) & (Y < FRAME[1] - 8.64)
    for x0, y0, x1, y1 in grow: free &= ~((X > x0) & (X < x1) & (Y > y0) & (Y < y1))
    near = lambda q: free & (np.abs(X - q[0]) + np.abs(Y - q[1]) <= bud)
    G = [None] * (k - 1)
    G[k-2] = near(ib)
    for j in range(k - 3, -1, -1): G[j] = free & (_l1_dt(G[j+1], LAYER_PITCH) <= bud)
    out, prev = [], ia
    for j in range(k - 1):
        c = near(prev) & G[j]
        if not c.any(): raise SystemExit(f'{tn}/{name} bit {b} stage {j+1}: no macro-free chain of {k} hops <= {bud:.1f} um')
        dd = np.where(c, np.abs(X - ps[j][0]) + np.abs(Y - ps[j][1]), np.inf)
        i = np.unravel_index(np.argmin(dd), dd.shape)
        prev = (float(X[i]), float(Y[i])); out.append(prev)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('types')
    ap.add_argument('--report'); a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    smax = min(405.0, raw.get('budgets', {}).get('ft_station_max_um', 405.0)); budget = smax-2.0
    rep = []
    for tn in a.types.split(','):
        ty = raw['partition_types'][tn]; W, H = ty['outline_um']; FRAME[:] = [W, H]
        gate = list(S.placed_macro_boxes(ty, halo=0.0).values())
        grow = [(x0-CLEAR, y0-CLEAR, x1+CLEAR, y1+CLEAR) for x0, y0, x1, y1 in gate]
        pins = {}
        for bus, bit, _l, x, y, face in type_pins(P, tn): pins.setdefault(bus, {})[bit] = (x, y, face)
        al = RowAllocator((4.32, 4.32, W-4.32, H-4.32), blocked=grow, cell_size=CELL, column_pitch=2.16,
                          row_pitch=.27, origin=(4.32, 4.32))
        for s in ty['ft_slots']:
            for st in s.get('bit_sites_um') or []:
                for x, y in st: al.reserve_rectangle((x, y, x+CELL[0], y+CELL[1]))
        g = np.mgrid[8.64:W-4.32:2.16, 8.64:H-4.32:2.16].reshape(2, -1).T
        ok = np.ones(len(g), bool)
        for x0, y0, x1, y1 in grow: ok &= ~((g[:, 0] > x0) & (g[:, 0] < x1) & (g[:, 1] > y0) & (g[:, 1] < y1))
        free = g[ok]
        for s in sorted(ty['ft_slots'], key=lambda s: -s['width']):
            if s.get('bit_sites_um') or s.get('regs_um'): continue
            k0 = int(s.get('stations', 1)); name = s['name']
            if k0 < 2: continue
            # same station count first; a legalisation miss (crowded wide bus) retries with a tighter hop budget
            for k, bud in [(k, b_) for k in range(k0, k0 + 1 + EXTRA_STATIONS) for b_ in (budget, budget - RETRY_TIGHTEN)]:
                r_ = _slot(s, k, pins, gate, grow, free, bud, smax, al, tn, name, k0)
                if r_ is None or 'infeasible' not in r_: break
            if r_ is None: continue
            rep.append(r_); print(r_, flush=True)
    Path(a.out).write_text(json.dumps(raw, indent=0)+'\n')
    if a.report: Path(a.report).write_text(json.dumps(rep, indent=1)+'\n')


RETRY_TIGHTEN = 8.0    # um
EXTRA_STATIONS = 1     # a slot whose bits have no macro-free chain at its station count gets +1 station (+1 cycle,
                       # repriced by gen.py latency); never more -- a second miss fails closed in the report

def _slot(s, k, pins, gate, grow, free, budget, smax, al, tn, name, k0):
    """site one slot at k stations; None = no macro hit at the original count; dict with 'infeasible' = no chain."""
    if True:
        if True:
            pi, po = pins[name+'_i'], pins[name+'_o']; bits = sorted(set(pi) | set(po))
            pts = {}; bad = 0
            for b in bits:
                A = pi.get(b) or po[b]; B = po.get(b) or pi[b]
                ia = {'E': (A[0]-1, A[1]), 'W': (A[0]+1, A[1]), 'N': (A[0], A[1]-1), 'S': (A[0], A[1]+1)}[A[2]]
                ib = {'E': (B[0]-1, B[1]), 'W': (B[0]+1, B[1]), 'N': (B[0], B[1]-1), 'S': (B[0], B[1]+1)}[B[2]]
                r = C.zroute(ia, ib, A[2], B[2]); L = C.plen(r)
                pts[b] = (ia, ib, r, L, [C.point_at(r, L*j/k) for j in range(1, k)])
                bad += sum(inside(p, gate) for p in pts[b][4])
            if not bad:
                if k == k0: return None
                s['stations'] = k       # the +1-station interpolation already clears every macro
                return dict(type=tn, slot=name, width=s['width'], stations=k, stations_added=k-k0, in_macro_points=0, moved=0)
            moved = 0; worst = 0.
            try:
                self_check = _move(pts, bits, k, grow, free, budget, tn, name)
            except SystemExit as e:
                return dict(type=tn, slot=name, width=s['width'], stations=k, in_macro_points=bad, infeasible=str(e))
            moved = self_check
            sites = [[None]*len(bits) for _ in range(k-1)]
            for b in bits:
                ia, ib, r, L, ps = pts[b]
                for j, p in enumerate(ps):
                    q, _ = al.allocate(np.array(p), 1, max_radius_um=20.)
                    c = q[0]; sites[j][b] = [round(float(c[0]-CELL[0]/2), 6), round(float(c[1]-CELL[1]/2), 6)]
                chain = [ia] + [(x+CELL[0]/2, y+CELL[1]/2) for x, y in (sites[j][b] for j in range(k-1))] + [ib]
                worst = max(worst, max(man(u, v) for u, v in zip(chain, chain[1:])))
            if worst > smax:
                # this station count has no legal chain (its row sites stay reserved: RowAllocator has no release)
                return dict(type=tn, slot=name, width=s['width'], stations=k, in_macro_points=bad,
                            infeasible=f'legalised hop {worst:.2f} > {smax}')
            if k != k0: s['stations'] = k
            s['bit_site_cell_um'] = list(CELL); s['bit_sites_um'] = sites
            return dict(type=tn, slot=name, width=s['width'], stations=k, stations_added=k-k0, in_macro_points=bad, moved=moved, max_bit_hop_um=round(worst, 2))


if __name__ == "__main__":
    main()
