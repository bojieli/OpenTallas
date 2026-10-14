#!/usr/bin/env python3
"""Bind the it2 tree pad ledger (590 legs / 1,855 x 512-bit pad cycles) to compact ot_qwen_tree_delay masters.

A leg that needs k extra cycles is a W->E chain of fixed-LAT tiles whose LATs sum to k exactly (every tile is a pure
LAT-deep flop chain, d on W, q on E, so chaining adds no cycle).  The plan is a PLAN: it becomes a binding only when
each master it names has a closed LEF + ETM view.  Usage: tree_delay_bind.py <ledger.json> <out.json> [--depths 1,8,21]
"""
import argparse, collections, json

OUTLINE = {1: (10.8, 64.8), 2: (17.28, 64.8), 3: (21.6, 64.8), 4: (28.08, 64.8), 8: (49.68, 64.8), 16: (92.88, 64.8),
           21: (129.6, 259.2)}     # um: ot_qwen_tree_delay<N>_t kits (baaa52fff, util ~0.52); 21 = the bf10180f4 outline
FLOP_UM2 = 209.0 / 512                                                   # measured d1 gate: 209 um2 std for 512 flops
RELAY_FRAME = 52.68 * 30.216                                             # existing single-cycle 512-bit relay frame


def split(k, depths):
    """fewest tiles whose depths sum to k (unbounded coin change; depths always contain 1)"""
    best = [None] * (k + 1)
    best[0] = []
    for n in range(1, k + 1):
        for d in depths:
            if d <= n and best[n - d] is not None and (best[n] is None or len(best[n - d]) + 1 < len(best[n])):
                best[n] = best[n - d] + [d]
    return sorted(best[k], reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ledger'); ap.add_argument('out'); ap.add_argument('--depths', default='1,2,3,4,8,16')
    a = ap.parse_args()
    led = json.load(open(a.ledger))
    depths = sorted(int(x) for x in a.depths.split(','))
    need = collections.Counter(); inst = collections.Counter(); legs = {}
    for bus, p in led['proposed_pads'].items():
        k = p['extra_cycles']
        need[k] += 1
        legs[bus] = dict(extra_cycles=k, tiles=split(k, depths), masters=[f'ot_qwen_tree_delay{d}_t' for d in split(k, depths)], source=p['source'], destination=p['destination'])
        inst.update(legs[bus]['tiles'])
    cyc = sum(k * n for k, n in need.items())
    area = sum(OUTLINE[d][0] * OUTLINE[d][1] * n for d, n in inst.items() if d in OUTLINE)
    out = dict(status='PLAN_ONLY_PENDING_CLOSED_VIEWS', ledger=a.ledger, die_sha256=led.get('die_sha256'),
               legs=len(legs), pad_cycles=cyc, legs_by_extra_cycles={str(k): need[k] for k in sorted(need)},
               depths=depths, instances_by_depth={str(d): inst[d] for d in sorted(inst)}, instances=sum(inst.values()),
               outline_um={str(d): OUTLINE.get(d) for d in depths},
               area_um2=dict(submitted_outlines=round(area, 1) if all(d in OUTLINE for d in inst) else None,
                             relay_frames_1855=round(RELAY_FRAME * cyc, 1),
                             std_cells_only=round(FLOP_UM2 * 512 * cyc, 1),
                             at_util_0p52=round(FLOP_UM2 * 512 * cyc / 0.52, 1)),
               max_tiles_on_one_leg=max(len(v['tiles']) for v in legs.values()), leg_binding=legs)
    json.dump(out, open(a.out, 'w'), indent=1)
    print({k: v for k, v in out.items() if k != 'leg_binding'})


if __name__ == '__main__':
    main()
