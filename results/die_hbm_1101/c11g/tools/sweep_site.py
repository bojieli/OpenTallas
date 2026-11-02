#!/usr/bin/env python3
"""DIE-HBM-57 (COORD 11-01 03:4x class sweep): per-bit ft station siting for EVERY HBM station slot that has no
bit_sites (all bits of a station on one point = the g50 root cause on q_b011/q_b110pv1/q_b101_nw).
Per slot (width >= MINW), internal station j keeps its planned point R_j as anchor and its bits spread toward their
own straight in->out line: target_b = R_j + a*(L_j(b) - R_j), L_j(b) = A_b + f_j*(B_b - A_b), f_j = the station's
cumulative share of the planned in->R1..->out route.  a is tried 1, .75, .5, .35, .25, .15; the first a whose
legalised per-bit hops stay <= max(budget 394.9, the slot's current clump max hop) wins; station count, latency and
the slot's other fields are unchanged; other slots' sites are reserved.  A slot no a satisfies is left as it was.
usage: sweep_site.py WT PLAN OUT LEDGER [--types a,b] [--minw 100]"""
import json, sys, argparse
from pathlib import Path
import numpy as np
WT = Path(sys.argv.pop(1))
sys.path.insert(0, str(WT / 'tools/die_plan')); sys.path.insert(0, str(WT))
import schema as S, ft_corridor as FC
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('ledger')
ap.add_argument('--types', default=''); ap.add_argument('--minw', type=int, default=100)
ap.add_argument('--alphas', default='1,.75,.5,.35,.25,.15'); ap.add_argument('--radius', type=float, default=120.0)
a = ap.parse_args()
budget = 405 * .98 - 2.0
raw = json.loads(Path(a.plan).read_text()); model = S.Plan(raw); ledger = []
want = set(t for t in a.types.split(',') if t)
alphas = [float(x) for x in a.alphas.split(',')]
for tn in sorted(raw['partition_types']):
    if want and tn not in want: continue
    ty = model.types[tn]; rt = raw['partition_types'][tn]
    todo = [s for s in rt.get('ft_slots') or [] if int(s.get('stations', 0)) > 1 and not s.get('bit_sites_um')
            and int(s['width']) >= a.minw and len(s.get('regs_um') or []) == int(s['stations'])]
    if not todo: continue
    w, h = ty['outline_um']
    pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(model, tn)}
    boxes = list(S.placed_macro_boxes(ty, halo=FC.KEEPOFF).values())
    def fresh():
        al = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=FC.CELL, column_pitch=2.16,
                          row_pitch=.27, origin=(4.32, 4.32))
        for s in rt['ft_slots']:
            if not s.get('bit_sites_um'): continue
            cw, ch = s['bit_site_cell_um']
            for st in s['bit_sites_um']:
                for x, y in st: al.reserve_rectangle((x, y, x + cw, y + ch))
        return al
    for s in todo:
        k = int(s['stations']); wd = int(s['width']) + 1; slot = s['name']
        try:
            A = np.array([pins[(slot + '_i', i)] for i in range(wd)]); B = np.array([pins[(slot + '_o', i)] for i in range(wd)])
        except KeyError as e:
            ledger.append(dict(type=tn, slot=slot, skipped=f'pin missing {e}')); print(tn, slot, 'SKIP pins', flush=True); continue
        R = np.array(s['regs_um'], dtype=float)
        # station0 = beside the in pins (g2 face-flop convention); route shares of R1..R(k-1)
        pts = [A.mean(axis=0)] + [R[j] for j in range(1, k)] + [B.mean(axis=0)]
        seg = [abs(q - p).sum() for p, q in zip(pts, pts[1:])]; cum = np.cumsum(seg) / max(1e-9, sum(seg))
        clump = [A] + [np.repeat(R[j][None], wd, 0) for j in range(1, k)] + [B]
        base = max(float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(clump, clump[1:]))
        lim = max(budget, base)
        rank = np.argsort(A[:, 1] + A[:, 0], kind='stable')
        best = None
        for al_ in alphas:
            alloc = fresh(); sites = []; fail = None
            for j in range(1, k):
                L = A + cum[j - 1] * (B - A); T = R[j][None] + al_ * (L - R[j][None])
                st = np.zeros((wd, 2))
                try:
                    for bi in rank:
                        p, _ = alloc.allocate(T[bi], 1, max_radius_um=a.radius); st[bi] = p[0]
                except Exception as e:
                    fail = f'legalise st{j}: {str(e)[:80]}'; break
                sites.append(st)
            if fail: print(tn, slot, 'a', al_, fail, flush=True); continue
            chain = [A] + sites + [B]
            hops = [float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])]
            print(tn, slot, 'a', al_, 'hops', [round(x, 1) for x in hops], 'lim', round(lim, 1), flush=True)
            if max(hops) <= lim: best = (al_, sites, hops); break
        if not best:
            ledger.append(dict(type=tn, slot=slot, width=s['width'], stations=k, kept='no alpha meets hop limit', base_max_hop=round(base, 1)))
            continue
        al_, sites, hops = best
        old = s['regs_um']
        s['regs_um'] = [A.mean(axis=0).round(4).tolist()] + [p.mean(axis=0).round(4).tolist() for p in sites]
        s['bit_site_cell_um'] = list(FC.CELL)
        s['bit_sites_um'] = [(p - np.array([FC.CELL[0] / 2, FC.CELL[1] / 2])).round(6).tolist() for p in sites]
        s['note'] = (s.get('note', '') + ' | DIE-HBM-57 class sweep: per-bit station sites (alpha %g, stations unchanged)' % al_).strip(' |')
        ext = [[round(float(p[:, 0].min()), 1), round(float(p[:, 0].max()), 1), round(float(p[:, 1].min()), 1), round(float(p[:, 1].max()), 1)] for p in sites]
        ledger.append(dict(type=tn, slot=slot, width=s['width'], stations=k, alpha=al_, hops_um=[round(x, 1) for x in hops],
                           limit_um=round(lim, 1), base_max_hop=round(base, 1), site_extent_x0x1y0y1=ext, old_regs_um=old, new_regs_um=s['regs_um']))
        # the next slot of this type must not reuse these sites
        rt_s = s
    model = S.Plan(raw)
Path(a.out).write_text(json.dumps(raw, indent=0) + '\n'); Path(a.ledger).write_text(json.dumps(ledger, indent=1) + '\n')
