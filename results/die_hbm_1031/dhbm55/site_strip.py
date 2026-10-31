#!/usr/bin/env python3
"""DIE-HBM-55: q_b011 L15x1 E-strip siting (variant B).  Stations travel in the macro-free E strip (x 277.6-380),
bit y-ordered columns spread over the strip width; last station aligned in y with its W out pin so the final hop is a
straight M6 run over the macro column.  Only the named slot changes (other slots' sites reserved); hop <= budget."""
import json, sys
from pathlib import Path
import numpy as np
WT = Path('/srv/opentallas-scratch2/claude/wt/die-hbm-48')
sys.path.insert(0, str(WT / 'tools/die_plan')); sys.path.insert(0, str(WT))
import schema as S, ft_corridor as FC
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
plan, out, ledger_p = sys.argv[1:4]; types = sys.argv[4].split(','); slot = sys.argv[5]
bands = [tuple(map(float, b.split(':'))) for b in sys.argv[6].split(',')]   # per station x0:x1
budget = 405 * .98 - 2.0
raw = json.loads(Path(plan).read_text()); model = S.Plan(raw); ledger = []
for tn in types:
    ty = model.types[tn]; w, h = ty['outline_um']
    pins = {(bn, i): (x, y) for bn, i, _, x, y, _ in type_pins(model, tn)}
    boxes = list(S.placed_macro_boxes(ty, halo=FC.KEEPOFF).values())
    alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=FC.CELL, column_pitch=2.16,
                         row_pitch=.27, origin=(4.32, 4.32))
    for s in ty['ft_slots']:
        if s['name'] == slot or not s.get('bit_sites_um'): continue
        cw, ch = s['bit_site_cell_um']
        for st in s['bit_sites_um']:
            for x, y in st: alloc.reserve_rectangle((x, y, x + cw, y + ch))
    s = [s for s in ty['ft_slots'] if s['name'] == slot][0]
    k = int(s['stations']); n = k - 1; wd = s['width'] + 1
    assert len(bands) == n, (len(bands), n)
    A = np.array([pins[(slot + '_i', i)] for i in range(wd)]); B = np.array([pins[(slot + '_o', i)] for i in range(wd)])
    sites = []
    for j, (x0, x1) in enumerate(bands):
        f = (j + 1) / n
        ty_ = A[:, 1] + f * (B[:, 1] - A[:, 1])
        ncol = max(1, int((x1 - x0) // 2.16))
        o = np.argsort(ty_)
        st = np.zeros((wd, 2))
        for r, bi in enumerate(o):
            c = r % ncol
            tgt = (x0 + c * (x1 - x0) / max(1, ncol - 1) if ncol > 1 else x0, ty_[bi])
            p, _ = alloc.allocate(np.array(tgt), 1, max_radius_um=30.0); st[bi] = p[0]
        sites.append(st)
    chain = [A] + [p + np.array(FC.CELL) / 2 * 0 for p in sites] + [B]
    hops = [float(np.abs(q - p).sum(axis=1).max()) for p, q in zip(chain, chain[1:])]
    assert max(hops) <= budget, (tn, hops, budget)
    old = s.get('regs_um')
    s['regs_um'] = [A.mean(axis=0).round(4).tolist()] + [p.mean(axis=0).round(4).tolist() for p in sites]
    s['bit_site_cell_um'] = list(FC.CELL)
    s['bit_sites_um'] = [(p - np.array([FC.CELL[0] / 2, FC.CELL[1] / 2])).round(6).tolist() for p in sites]
    spans = [[round(float(np.ptp(p[:, 0])), 1), round(float(np.ptp(p[:, 1])), 1)] for p in sites]
    ledger.append(dict(type=tn, slot=slot, width=s['width'], hops_um=[round(x, 1) for x in hops], budget_um=round(budget, 2),
                       bands=bands, spans=spans, old_regs_um=old, new_regs_um=s['regs_um']))
    print(tn, slot, 'hops', [round(x, 1) for x in hops], 'spans', spans)
Path(out).write_text(json.dumps(raw, indent=0) + '\n'); Path(ledger_p).write_text(json.dumps(ledger, indent=1) + '\n')
