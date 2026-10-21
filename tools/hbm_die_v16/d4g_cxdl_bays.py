#!/usr/bin/env python3
"""Reserve full physical CXDL-S footprints and relocate colliding leaves into clear bays.

Consume the actual placement-only GEN manifest. Healthy leaves and all child
outlines remain fixed. Each relocated leaf gets a 216 x 302.4 um clear bay,
including at least 43.2 um for regional clock/relay cells around its outline.
Run on the fleet; the following ordinary placement GEN decides acceptance.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--plan-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    m = json.loads(a.manifest.read_text())
    g = json.loads((a.plan_dir / 'grants_d4g.json').read_text())
    pl = copy.deepcopy(m['placement'])
    targets = sorted({n for row in m['placement_problems'] for n in row[1:]
                      if n.startswith('cxdl_') and n.endswith('_s')})
    if len(targets) != 6:
        raise ValueError(f'expected the six source-bound colliding S leaves, got {targets}')
    grid, bw, bh = 43.2, 216.0, 302.4
    W, H = m['die_um']
    fixed = [v for n, v in pl.items() if n not in targets]
    boxes = np.asarray([[v['x'], v['y'], v['x']+v['w'], v['y']+v['h']] for v in fixed])
    bays, moves = [], []
    for n in targets:
        old = dict(pl[n])
        if (old['w'], old['h']) != (108.0, 216.0):
            raise ValueError(f'unreviewed physical outline {n}: {old}')
        # Candidate bay origins surround the existing leaf, rather than its
        # potentially millimetres-away Q partner. Keep those other sites fixed.
        ix, iy = round((old['x']-grid)/grid), round((old['y']-grid)/grid)
        candidates = sorted(((dx*dx+dy*dy, dx, dy) for dx in range(-30, 31)
                             for dy in range(-30, 31)))
        chosen = None
        for _, dx, dy in candidates:
            x, y = round((ix+dx)*grid, 3), round((iy+dy)*grid, 3)
            if x < 0 or y < 0 or x+bw > W or y+bh > H:
                continue
            hit = ((boxes[:, 0] < x+bw-0.01) & (boxes[:, 2] > x+0.01) &
                   (boxes[:, 1] < y+bh-0.01) & (boxes[:, 3] > y+0.01))
            if hit.any():
                continue
            chosen = (x, y)
            break
        if chosen is None:
            raise ValueError(f'no full clear bay within 1296 um of {n}')
        x, y = chosen
        pl[n]['x'], pl[n]['y'] = round(x+grid, 3), round(y+grid, 3)
        bays.append(dict(instance=n, x=x, y=y, w=bw, h=bh,
                         cell_band_um=43.2, owner='die regional clock and relay rows'))
        boxes = np.vstack((boxes, [x, y, x+bw, y+bh]))
        moves.append(dict(instance=n, old=[old['x'], old['y']],
                          new=[pl[n]['x'], pl[n]['y']],
                          displacement_um=math.hypot(pl[n]['x']-old['x'], pl[n]['y']-old['y'])))
    resized = []
    for s in g['slots']:
        n = s['name']
        if n.startswith('cxdl_') and n.endswith('_s') and n in pl:
            if s['outline'] != dict(w=pl[n]['w'], h=pl[n]['h']):
                resized.append(n)
            s['outline'] = dict(w=pl[n]['w'], h=pl[n]['h'])
        if n in targets:
            s['origin'].update(x=pl[n]['x'], y=pl[n]['y'])
            s['notes'] += ' | Full measured 108x216 CXDL-S leaf in a reserved 216x302.4 clear bay; old 33.48 estimate retired.'
    g['cxdl_clear_bays'] = bays
    a.out.mkdir(parents=True, exist_ok=False)
    for f in ('compact.P.json', 'lanes.json', 'd4g_region_map.json', 'coord_map.json'):
        (a.out / f).write_bytes((a.plan_dir / f).read_bytes())
    (a.out / 'grants_d4g.json').write_text(json.dumps(g, indent=1)+'\n')
    report = dict(source_manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
                  source_input_sha256=m['input_sha256'], repaired_overlap_count=len(m['placement_problems']),
                  die_um=m['die_um'], resized_stale_grants=resized, moves=moves, bays=bays,
                  qualification='PLAN_ONLY; existing placement GEN and new S4 relay/latency planning required')
    (a.out / 'cxdl_bay_report.json').write_text(json.dumps(report, indent=1)+'\n')
    print('CXDL_CLEAR_BAYS', len(bays), 'stale_grants_resized', len(resized),
          'max_move_um', max(x['displacement_um'] for x in moves))


if __name__ == '__main__':
    main()
