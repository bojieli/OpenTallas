#!/usr/bin/env python3
"""Map the current head tile graph to exact vocabulary rows and position straps.

A source-composition manifest, not a plan mutation or a physical mask release.
The existing controller adds c_rbase to the chain's local17-bit row. Preserve
that contract: ROW0=128*local_bundle; rank_base is the prefix sum of model
rank sizes253/253/252/252. Weight images use rank_base+ROW0. Disabled slots
have TEN=0 and no weight image; they retain the same tile/strap footprint.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def chain_order(plan):
    parts = {p['name']: p for p in plan['partitions']}
    tile_names = {p['name'] for p in plan['partitions'] if p['type'] == 'hd_tile'}
    spines = sorted((p['name'] for p in plan['partitions'] if p['type'] in ('hd_spn', 'hd_spn_end')),
                    key=lambda n: int(re.fullmatch(r'sp(\d+)', n)[1]))
    outgoing = {}
    for port in plan['ports']:
        src, dst = port['src'], port['dst']
        if port['width'] != 565:
            continue
        key = (src['part'], src['bus'])
        if key in outgoing:
            raise ValueError(f'ambiguous chain output {key}')
        outgoing[key] = (dst['part'], dst['bus'])
    order = []
    for spine in spines:
        for side, start, finish in [('W', 'xw_o', 'bw_i'), ('E', 'xe_o', 'be_i')]:
            node = outgoing[(spine, start)]
            seen = set()
            chain = []
            while node != (spine, finish):
                if node in seen:
                    raise ValueError(f'cycle in {spine}{side} at {node}')
                seen.add(node)
                name, bus = node
                typ = parts[name]['type']
                if typ == 'hd_tile':
                    if bus != 'i':
                        raise ValueError(f'tile entered through {name}.{bus}')
                    chain.append(name)
                    node = outgoing[(name, 'o')]
                elif typ in ('hd_turn_a', 'hd_turn_b'):
                    if bus != 't_i':
                        raise ValueError(f'turn entered through {name}.{bus}')
                    node = outgoing[(name, 't_o')]
                else:
                    raise ValueError(f'unexpected chain provider {name}:{typ}')
            if len(chain) != 22:
                raise ValueError(f'{spine}{side} has {len(chain)} tiles, expected22')
            order.extend((name, f'{spine}{side}', j) for j, name in enumerate(chain))
    names = [x[0] for x in order]
    if len(names) != 264 or len(set(names)) != len(names) or set(names) != tile_names:
        raise ValueError('tile graph must cover all264 slots exactly once')
    return order


def build(plan_path):
    plan = json.loads(plan_path.read_text())
    order = chain_order(plan)
    vocabulary, rows_per_bundle, total_bundles, nranks = 129280, 128, 1010, 4
    counts = [total_bundles // nranks + int(r < total_bundles % nranks) for r in range(nranks)]
    ranks, base, intervals = [], 0, []
    for rank, active in enumerate(counts):
        slots = []
        for index, (name, chain, offset) in enumerate(order):
            enabled = index < active
            local_row0 = index * rows_per_bundle if enabled else 0
            global_row0 = base + local_row0 if enabled else None
            if enabled:
                intervals.append((global_row0, global_row0 + rows_per_bundle))
            slots.append(dict(part=name, slot=index, chain=chain, chain_index=offset,
                              mask_params=dict(ROW0=local_row0, TEN=int(enabled)),
                              weight_row0=global_row0,
                              weight_rows=rows_per_bundle if enabled else 0))
        ranks.append(dict(rank=rank, controller_row_base=base, active_bundles=active,
                          dark_slots=len(order)-active, slots=slots))
        base += active * rows_per_bundle
    cursor = 0
    for lo, hi in sorted(intervals):
        if lo != cursor:
            raise ValueError(f'vocabulary overlap/gap at{cursor}: next{lo}')
        cursor = hi
    if cursor != vocabulary or base != vocabulary:
        raise ValueError(f'incomplete vocabulary coverage{cursor}/{vocabulary}')
    return dict(schema='opentallas.s81.head-row-map.v1', status='SOURCE CONTRACT; physical mask realization pending',
                plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(), vocabulary=vocabulary,
                rank_layout='contiguous prefixes; existing local-row+c_rbase controller convention',
                slot_order='spine top-to-bottom, W then E, actual directed chain traversal',
                rows_per_bundle=rows_per_bundle, added_cycles=0, ranks=ranks,
                coverage=dict(enabled_bundles=len(intervals), rows=cursor, duplicate_rows=0, missing_rows=0),
                implementation='18 same-footprint mask-programmed TIEHI/TIELO cells per ot_s81hd_strap; no new die pins')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, default=ROOT/'physical/die_plan/s81_head/die_plan.json')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = build(args.plan)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status='PASS', coverage=result['coverage'],
                          active=[r['active_bundles'] for r in result['ranks']],
                          dark=[r['dark_slots'] for r in result['ranks']],
                          bases=[r['controller_row_base'] for r in result['ranks']])))
