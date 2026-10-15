#!/usr/bin/env python3
"""Constructive packing proposal for one four-result-group compute slab half.

This proves rectangle fit only. It explicitly retains unresolved routing,
registered glue, reset and functional transport gates rather than inventing
a physical qualification from area arithmetic.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def plan(width=1036.8, height=2462.4):
    leaves = []
    sources = {}
    for name, cell, count, role in [
        ('qfd_slab_pg_col', 'ot_qwen_slab_pg_col', 16, 'scale'),
        ('qfd_slab_pg_lanes', 'ot_qwen_slab_pg_lanes', 16, 'multiply'),
    ]:
        path = ROOT / 'physical/ref_tile' / name / 'views' / cell / (cell + '.lef')
        data = path.read_bytes()
        match = re.search(rb'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', data)
        w, h = map(float, match.groups())
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
        for i in range(count):
            if role == 'scale':
                x = 43.2 + (i % 2) * (w + 12.0)
                y = 21.6 + (i // 2) * (h + 12.0)
            else:
                x = 715.2
                y = 21.6 + (i // 4) * 456.0 + (i % 4) * (h + 4.32)
            leaves.append(dict(name=f'{role}_{i}', cell=cell,
                               group=i // 4, member=i % 4,
                               at=[round(x, 5), round(y, 5)],
                               size=[w, h], orient='R0',
                               clock=f'ck_{role}_{i}'))
    overlaps = []
    for i, a in enumerate(leaves):
        ax, ay = a['at']; aw, ah = a['size']
        assert ax >= 0 and ay >= 0 and ax + aw <= width and ay + ah <= height, a
        for b in leaves[:i]:
            bx, by = b['at']; bw, bh = b['size']
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                overlaps.append([a['name'], b['name']])
    assert not overlaps, overlaps
    area = sum(a['size'][0] * a['size'][1] for a in leaves)
    return dict(schema='opentallas.qwen.slab-frame-packing.v1',
                outline=[width, height], groups=4, block_words=8, leaves=leaves,
                evidence='tools/qwen_rom_fulldie_b3r2.py _tp8_globals: 24 result groups, 48 block words, 6 halves',
                source_sha256=sources, leaf_area_um2=round(area, 5),
                remaining_area_um2=round(width * height - area, 5),
                geometry_verdict='PASS', qualification='NOT QUALIFIED',
                unresolved=[
                    'multiplier 4.32-um row gaps need actual placement blockages and routing evidence; column gaps are 12 um',
                    '32 independent child clock pins require die phi-R delivery and reset assignment',
                    'all grouped column OR, request and multiplier paths need registered glue and measured per-pair reach',
                    '8 real block-word CDC FIFOs and level6-to-level7 exact pair reduction absent from BW_FIFO=0 group vehicle',
                    'secondary half carries 4 distinct level7 words: stale cf1 512b fragment bus must become 2048b plus metadata' ,
                    'exact production frame bench plus failing mutant and immutable-price latency measurement',
                    'native pin-register capture/launch of glue and full routed TT/FF/DRC closure',
                ])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print('SLAB FRAME RECTANGLES PASS: 32 real leaves, '
          f"{result['leaf_area_um2'] / 1e6:.5f} mm2 in "
          f"{result['outline']}; physical/functional qualification remains open")
