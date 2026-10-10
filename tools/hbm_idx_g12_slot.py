#!/usr/bin/env python3
"""hbm-phys-1010 [idx] (lead decision 2026-10-10, R25GQ): slot of the 12-lane-a-stack native index score grid
(48 lanes a die; replaces hfd_idx_score_native_grid at 36/64 height).

The grid is an assembly of hardened sub-blocks (the 16M-cell flat L16 grid was never routable flat):
  hfd_idx_lrg         W column: 8 svc line ports -> 6 lines a beat (ik / ikc / q on the slot's W face)
  3 x L4 BK12 taps    stacked E of the lrg (W face abutting the lrg's E face), hfd_idx_score L=4 BK=12 LANE0=0/4/8
  hfd_idx_t3_join     top-right corner: 12 -> 16 lane gearbox, the unchanged 610 b native boundary (s / sc on top)
  E channel           taps' s / sc to the join (3 x 155 wires)
Outlines come from physical/qwen_die_masters/cfg/<block>.env (FW / FH).  Utilisation is an ESTIMATE until the L4 tap
synthesis measures it: slice cells from the L16 grid estimate (index/native/model.json scorer_cells_um2_estimate_per_stack
3.05 mm2 = 4 slices + 8 x 64-deep landing FIFOs), FIFO flops at 0.2916 um2 (ASAP7 DFFHQNx1).

usage: hbm_idx_g12_slot.py [--out physical/hbm_accel_die_views/index/native_g12/slot.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'physical/qwen_die_masters/cfg'
GAP = 10.8          # sub-block spacing (um)
ECH = 52.92         # E channel (taps' s / sc to the join)
FF = 0.2916         # um2 a flop
GY = 2.16


def outline(name):
    t = (CFG / f'{name}.env').read_text()
    return float(re.search(r'^FW=([\d.]+)', t, re.M)[1]), float(re.search(r'^FH=([\d.]+)', t, re.M)[1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'physical/hbm_accel_die_views/index/native_g12/slot.json')
    a = ap.parse_args()
    lw, lh = outline('hfd_idx_lrg')
    tw, th = outline('hfd_idx_score_b12_lane0')
    jw, jh = outline('hfd_idx_t3_join')
    W = round(lw + GAP + tw + ECH, 3)
    assert abs(lh - (3 * th + 2 * GAP)) < 1e-6, 'lrg column must span the tap stack'
    H = round(-(-(lh + GAP + jh) // GY) * GY, 3)
    model = json.loads((ROOT / 'physical/hbm_accel_die_views/index/native/model.json').read_text())
    l16 = model['floorplan']['scorer_cells_um2_estimate_per_stack']
    fifo16 = 8 * 64 * 1098 * FF
    slice_ = (l16 - fifo16) / 4
    cells = dict(taps=3 * (slice_ + 2 * 16 * 1098 * FF), lrg=8 * 64 * 1098 * FF * 1.35 + 6 * 1099 * FF,
                 join=3 * 128 * 153 * FF * 1.2 + 610 * FF)
    tot = sum(cells.values())
    subs = [dict(name='lrg', master='hfd_idx_lrg', x=0.0, y=0.0, w=lw, h=lh)]
    for t in range(3):
        subs.append(dict(name=f'tap{t}', master=f'hfd_idx_score_b12_lane{4 * t}', x=round(lw + GAP, 3),
                         y=round(t * (th + GAP), 3), w=tw, h=th))
    subs.append(dict(name='join', master='hfd_idx_t3_join', x=round(W - jw, 3), y=round(lh + GAP, 3), w=jw, h=jh))
    out = dict(schema='opentallas.hbm_idx_g12_slot.v1', generator='tools/hbm_idx_g12_slot.py',
               master='hfd_idx_score_native_g12', lanes_per_stack=12, lanes_per_die=48, slot_um=[W, H],
               slot_mm2=round(W * H / 1e6, 4), r25gq_36_64_slot_um=[2000.16, 1689.12], r25gp_l16_slot_um=[2000.16, 3000.264],
               sub_blocks=subs, e_channel_um=ECH,
               faces=dict(W='svc key lines ik 8 x 1099 + ikc 8 (lrg W face), q 571 from the selector (lrg W face)',
                          top='s 610 + sc to the selector (join top face, E end)', S='ck / rst'),
               cells_um2_estimate=dict({k: round(v) for k, v in cells.items()}, total=round(tot),
                                       basis='L16 grid estimate per slice + flop counts; NOT measured (slice synthesis '
                                             'never completed); re-derive from the b12 tap / lrg synth reports'),
               utilisation_estimate=round(tot / (W * H), 3),
               throughput=dict(keys_per_cycle=12, hbm_rate_keys_per_cycle=12.25,
                               note='12 keys / cycle / stack = 6 lines (1,088 b) a cycle, the owner >= 90 % HBM rule '
                                    'minimum (index/DESIGN.md sec. 2); scan at 228 beats a full stack vs 171 at L16'))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(slot_um=out['slot_um'], util=out['utilisation_estimate'], cells=out['cells_um2_estimate'])))


if __name__ == '__main__':
    main()
