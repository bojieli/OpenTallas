#!/usr/bin/env python3
"""DIE-HBM-56: one-block ft station siting (generalises DIE-HBM-55 site_strip.py, variant B method).
Per slot, every internal station (j=1..k-1) gets per-bit sites (bit_sites_um) spread over a free box instead of one point;
station count unchanged (latency unchanged), station0 stays beside its input pin (g2/face_flops convention).
spec = TYPE:SLOT:J:MODE:x0:x1[:y0:y1]
  MODE yo  : y target = in->out interpolation (J/(k-1))*(1-q), q = optional 7th field (share of dy left to the last hop, default 0 = last station at out-pin y); x columns interleaved over x0..x1
  MODE il  : grid over box x0..x1 x y0..y1, bits y-ranked, interleaved over columns
  MODE lin : x linear in bit rank (low in-y rank -> x1, high -> x0), y cycles over the box rows
Only the named slots change; other slots' sites are reserved; every per-bit hop must be <= budget (assert)."""
import json, sys
from pathlib import Path
import numpy as np
WT = Path(sys.argv.pop(1))
sys.path.insert(0, str(WT / 'tools/die_plan')); sys.path.insert(0, str(WT))
import schema as S, ft_corridor as FC
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
plan, out, ledger_p = sys.argv[1:4]; specs = [a.split(':') for a in sys.argv[4:]]
budget = 405 * .98 - 2.0
raw = json.loads(Path(plan).read_text()); model = S.Plan(raw); ledger = []
by_slot = {}
for sp in specs: by_slot.setdefault((sp[0], sp[1]), []).append(sp)
for (tn, slot), sps in by_slot.items():
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
    spec_j = {int(sp[2]): sp for sp in sps}
    assert sorted(spec_j) == list(range(1, k)), (tn, slot, k, sorted(spec_j))
    A = np.array([pins[(slot + '_i', i)] for i in range(wd)]); B = np.array([pins[(slot + '_o', i)] for i in range(wd)])
    rank = np.argsort(np.argsort(A[:, 1], kind='stable'), kind='stable')
    sites = []
    for j in range(1, k):
        sp = spec_j[j]; mode = sp[3]; x0, x1 = float(sp[4]), float(sp[5])
        st = np.zeros((wd, 2)); ncol = max(1, int((x1 - x0) // 2.16))
        if mode == 'yo':
            f = j / n * (1 - (float(sp[6]) if len(sp) > 6 else 0.0))
            tys = A[:, 1] + f * (B[:, 1] - A[:, 1])
            tgt = [(x0 + (r % ncol) * (x1 - x0) / max(1, ncol - 1) if ncol > 1 else x0, tys[b]) for b, r in enumerate(rank)]
        else:
            y0, y1 = float(sp[6]), float(sp[7]); nrow = max(1, int((y1 - y0) // .27))
            if mode == 'il':
                nr = -(-wd // ncol)
                tgt = [(x0 + (r % ncol) * (x1 - x0) / max(1, ncol - 1), y0 + (r // ncol) * (y1 - y0) / max(1, nr - 1)) for b, r in enumerate(rank)]
            else:
                tgt = [(x1 - r / max(1, wd - 1) * (x1 - x0), y0 + (r * 7 % nrow) * .27) for b, r in enumerate(rank)]
        for bi in np.argsort(rank):
            p, _ = alloc.allocate(np.array(tgt[bi]), 1, max_radius_um=60.0); st[bi] = p[0]
        sites.append(st)
    chain = [A] + sites + [B]
    hb = np.stack([np.abs(q - p).sum(axis=1) for p, q in zip(chain, chain[1:])])
    hops = hb.max(axis=1).tolist()
    ok = max(hops) <= budget
    old = s.get('regs_um')
    s['regs_um'] = [A.mean(axis=0).round(4).tolist()] + [p.mean(axis=0).round(4).tolist() for p in sites]
    s['bit_site_cell_um'] = list(FC.CELL)
    s['bit_sites_um'] = [(p - np.array([FC.CELL[0] / 2, FC.CELL[1] / 2])).round(6).tolist() for p in sites]
    ext = [[round(float(p[:, 0].min()), 1), round(float(p[:, 0].max()), 1), round(float(p[:, 1].min()), 1), round(float(p[:, 1].max()), 1)] for p in sites]
    ledger.append(dict(type=tn, slot=slot, width=s['width'], stations=k, specs=sps, hops_um=[round(x, 1) for x in hops],
                       budget_um=round(budget, 2), hop_ok=ok, site_extent_x0x1y0y1=ext, old_regs_um=old, new_regs_um=s['regs_um']))
    print(tn, slot, 'k', k, 'hops', [round(x, 1) for x in hops], 'ok', ok, 'ext', ext, flush=True)
    assert ok, (tn, slot, hops)
Path(out).write_text(json.dumps(raw, indent=0) + '\n'); Path(ledger_p).write_text(json.dumps(ledger, indent=1) + '\n')
