#!/usr/bin/env python3
"""DIE-HBM-57: move only the station bit cells that sit on a probe blockage of a leaf 'reuse' content (no macros in
placed_macro_boxes, e.g. q_su11 u_cxdl_Q1_q/_s, u_hc_Q1 -> g2 DPL-0033 'placed in rows' on every su11 probe since d44p)
to the nearest free legal row site (RowAllocator, macros + those contents blocked, all other station sites reserved).
nudge_c.py WT PLAN OUT TYPE[,TYPE...] CONTENT[,CONTENT...]"""
import json, sys
from pathlib import Path
import numpy as np
WT = Path(sys.argv[1]); sys.path.insert(0, str(WT / 'tools/die_plan')); sys.path.insert(0, str(WT))
import schema as S, ft_corridor as FC
from tools.die_trial.legal_sites import RowAllocator
plan, out, types, conts = sys.argv[2], sys.argv[3], sys.argv[4].split(','), set(sys.argv[5].split(','))
raw = json.loads(Path(plan).read_text()); model = S.Plan(raw)
for tn in types:
    ty = model.types[tn]; rt = raw['partition_types'][tn]; w, h = ty['outline_um']
    cb = [(c['origin_um'][0] - FC.KEEPOFF, c['origin_um'][1] - FC.KEEPOFF, c['origin_um'][0] + c['outline_um'][0] + FC.KEEPOFF,
           c['origin_um'][1] + c['outline_um'][1] + FC.KEEPOFF) for c in rt.get('contents', []) if c['inst'] in conts]
    boxes = list(S.placed_macro_boxes(ty, halo=FC.KEEPOFF).values()) + cb
    al = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=FC.CELL, column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    hit = []
    for s in rt['ft_slots']:
        if not s.get('bit_sites_um'): continue
        cw, ch = s['bit_site_cell_um']
        for j, st in enumerate(s['bit_sites_um']):
            for b, (x, y) in enumerate(st):
                if any(min(x + cw, x1) - max(x, x0) > 1e-3 and min(y + ch, y1) - max(y, y0) > 1e-3 for x0, y0, x1, y1 in cb):
                    hit.append((s, j, b))
                else:
                    al.reserve_rectangle((x, y, x + cw, y + ch))
    mv = {}
    for s, j, b in hit:
        cw, ch = s['bit_site_cell_um']; x, y = s['bit_sites_um'][j][b]
        p, _ = al.allocate(np.array([x + cw / 2, y + ch / 2]), 1, max_radius_um=200.0)
        nx, ny = float(p[0][0]) - cw / 2, float(p[0][1]) - ch / 2
        s['bit_sites_um'][j][b] = [round(nx, 6), round(ny, 6)]
        d = abs(nx - x) + abs(ny - y); k = (s['name'], j + 1); mv[k] = max(mv.get(k, (0, 0))[0], d), mv.get(k, (0, 0))[1] + 1
    for (sl, j), (dm, n) in sorted(mv.items()):
        s = next(x for x in rt['ft_slots'] if x['name'] == sl)
        P = np.array(s['bit_sites_um'][j - 1]) + np.array(s['bit_site_cell_um']) / 2
        s['regs_um'][j] = P[np.abs(P - P.mean(axis=0)).sum(axis=1).argmin()].round(4).tolist()
        s['note'] = (s.get('note', '') + f' | DIE-HBM-57 nudge: stage {j} {n} bits off reuse contents (max {dm:.1f} um)').strip(' |')
        print(tn, sl, 'stage', j, 'moved', n, 'max', round(dm, 1), flush=True)
Path(out).write_text(json.dumps(raw) + '\n')
