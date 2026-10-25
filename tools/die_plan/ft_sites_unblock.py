#!/usr/bin/env python3
"""PATH-KV 10-25: per-bit FT station sites that clear physical macros (schema.placed_macro_boxes:
hard cores + LEF contents; the check.check_ft_macro_sites gate of 0302d3b06a).
For every FT slot of the given types that has a station point inside a macro and no explicit
bit_sites_um: station j of bit b starts at check's own interpolated point (zroute(b), L_b*j/k);
points inside a macro box (+CLEAR) slide along that bit's route (|dt| <= L_b/(2k)), else move to the
nearest free grid point; every paired-bit hop (in pin -> s1 -> .. -> out pin) must stay <= budget.
Station counts, windows and lane cycles are UNCHANGED. Each point is legalised to a free row site
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
                if not okk.any(): raise SystemExit(f'{tn}/{name} bit {b} stage {j+1}: no macro-free point within reach')
                best = tuple(free[okk][np.argmin(d[okk])])
            ps[j] = (float(best[0]), float(best[1])); moved += 1
    return moved

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('types')
    ap.add_argument('--report'); a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    smax = min(405.0, raw.get('budgets', {}).get('ft_station_max_um', 405.0)); budget = smax-2.0
    rep = []
    for tn in a.types.split(','):
        ty = raw['partition_types'][tn]; W, H = ty['outline_um']
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
            k = int(s.get('stations', 1)); name = s['name']
            if k < 2: continue
            pi, po = pins[name+'_i'], pins[name+'_o']; bits = sorted(set(pi) | set(po))
            pts = {}; bad = 0
            for b in bits:
                A = pi.get(b) or po[b]; B = po.get(b) or pi[b]
                ia = {'E': (A[0]-1, A[1]), 'W': (A[0]+1, A[1]), 'N': (A[0], A[1]-1), 'S': (A[0], A[1]+1)}[A[2]]
                ib = {'E': (B[0]-1, B[1]), 'W': (B[0]+1, B[1]), 'N': (B[0], B[1]-1), 'S': (B[0], B[1]+1)}[B[2]]
                r = C.zroute(ia, ib, A[2], B[2]); L = C.plen(r)
                pts[b] = (ia, ib, r, L, [C.point_at(r, L*j/k) for j in range(1, k)])
                bad += sum(inside(p, gate) for p in pts[b][4])
            if not bad: continue
            moved = 0; worst = 0.
            try:
                self_check = _move(pts, bits, k, grow, free, budget, tn, name)
            except SystemExit as e:
                rep.append(dict(type=tn, slot=name, width=s['width'], stations=k, in_macro_points=bad, infeasible=str(e)))
                print(rep[-1], flush=True); continue
            moved = self_check
            for b in []:
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
                        if not okk.any(): raise SystemExit(f'{tn}/{name} bit {b} stage {j+1}: no macro-free point within reach')
                        best = tuple(free[okk][np.argmin(d[okk])])
                    ps[j] = (float(best[0]), float(best[1])); moved += 1
            sites = [[None]*len(bits) for _ in range(k-1)]
            for b in bits:
                ia, ib, r, L, ps = pts[b]
                for j, p in enumerate(ps):
                    q, _ = al.allocate(np.array(p), 1, max_radius_um=20.)
                    c = q[0]; sites[j][b] = [round(float(c[0]-CELL[0]/2), 6), round(float(c[1]-CELL[1]/2), 6)]
                chain = [ia] + [(x+CELL[0]/2, y+CELL[1]/2) for x, y in (sites[j][b] for j in range(k-1))] + [ib]
                worst = max(worst, max(man(u, v) for u, v in zip(chain, chain[1:])))
            if worst > smax: raise SystemExit(f'{tn}/{name}: legalised hop {worst:.1f} > {smax}')
            s['bit_site_cell_um'] = list(CELL); s['bit_sites_um'] = sites
            rep.append(dict(type=tn, slot=name, width=s['width'], stations=k, in_macro_points=bad, moved=moved, max_bit_hop_um=round(worst, 2)))
            print(rep[-1], flush=True)
    Path(a.out).write_text(json.dumps(raw, indent=0)+'\n')
    if a.report: Path(a.report).write_text(json.dumps(rep, indent=1)+'\n')
main()
