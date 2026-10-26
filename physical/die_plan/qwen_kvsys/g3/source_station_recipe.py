#!/usr/bin/env python3
"""Realize planned outgoing stations at their source without adding lane cycles.

Exact duplicate outgoing station records came from folding four quadrant plans.
Coalesce those records, retain every non-output record unchanged, and select the
native source-station realization already used by SYS_C for all actual outputs.
The binder independently checks each source count against fixed_cycles and
subtracts it from the receiver padding; this tool does not change any latency.
"""
import argparse
import copy
import json
from pathlib import Path


def apply(plan, recipe):
    plan, recipe = copy.deepcopy(plan), copy.deepcopy(recipe)
    selected, rows = [], []
    for name, typ in plan['partition_types'].items():
        buses = {b['name']: b for b in typ.get('buses', [])}
        seen, entries = {}, []
        outgoing = 0
        duplicates = 0
        for entry in typ.get('internal_stations', []):
            conn = entry.get('conn', '')
            bus = buses.get(conn[4:]) if conn.startswith('bus:') else None
            if bus is None or bus['dir'] != 'out':
                entries.append(entry)
                continue
            if not entry.get('regs_um'):
                raise ValueError(f'{name}.{conn}: empty outgoing station declaration')
            if conn in seen:
                if entry != seen[conn]:
                    raise ValueError(f'{name}.{conn}: conflicting outgoing station records')
                duplicates += 1
                continue
            seen[conn] = entry
            entries.append(entry)
            outgoing += 1
        if outgoing:
            selected.append(name)
            typ['internal_stations'] = entries
            rows.append(dict(type=name, output_buses=outgoing,
                             exact_duplicates_removed=duplicates,
                             source_stage_counts={k[4:]: len(v['regs_um']) for k, v in seen.items()}))
    if not selected:
        raise ValueError('plan has no outgoing station contracts')
    recipe['internal_stations_types'] = sorted(selected)
    recipe['note'] = recipe.get('note', '') + ' | KV1713: planned OUT stations at source; identical receiver stages removed, lane cycles unchanged'
    return plan, recipe, dict(types=sorted(selected), details=rows,
                             lane_cycles_changed=0,
                             exact_duplicates_removed=sum(r['exact_duplicates_removed'] for r in rows),
                             non_output_stations='preserved unchanged; not relocated by this recipe')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('recipe'); ap.add_argument('out')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    p, r, receipt = apply(json.loads(Path(a.plan).read_text()), json.loads(Path(a.recipe).read_text()))
    for name, value in [('die_plan.json', p), ('recipe.json', r), ('source_station_recipe.json', receipt)]:
        (out / name).write_text(json.dumps(value, indent=1) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
