#!/usr/bin/env python3
"""Parallel station tap planning; publish deterministic reset release changes."""
import argparse
import copy
import json
import multiprocessing
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stationtaps_impl_2249 as I

RAW = None
ARGS = None


def solve_type(tn):
    path = Path(ARGS.work) / (tn + '.json')
    if path.exists():
        return json.loads(path.read_text())
    raw = copy.deepcopy(RAW)
    rows = I.base_rows(raw['partition_types'][tn])
    I.configure(raw['partition_types'][tn], ARGS.radius, rows)
    for iteration in range(8):
        plan = I.S.Plan(raw, ARGS.plan)
        taps = [(x, y) for _, x, y in I.S.tap_grid(plan, tn)]
        added = 0
        for point in I.chain_points(plan, tn):
            if min(I.man(point, tap) for tap in taps) > ARGS.radius + 1e-6:
                if not any(I.man(point, row[:2]) < 1e-3 for row in rows):
                    rows.append([round(point[0], 3), round(point[1], 3), 1.0])
                    added += 1
        if not added:
            result = dict(type=tn, rows=rows, iterations=iteration+1)
            path.write_text(json.dumps(result))
            return result
        raw['partition_types'][tn]['clock']['sink_sites_um'] = rows
    raise ValueError(f'{tn}: control-sink planning did not converge')


def main():
    global RAW, ARGS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('out')
    ap.add_argument('--radius', type=float, default=150)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--work', required=True)
    ap.add_argument('--sidecar-in', required=True)
    ap.add_argument('--sidecar-out', required=True)
    ARGS = ap.parse_args()
    start = time.time()
    RAW = json.loads(Path(ARGS.plan).read_text())
    Path(ARGS.work).mkdir(parents=True, exist_ok=True)
    types = I.stations(RAW)
    old_plan = I.S.Plan(copy.deepcopy(RAW), ARGS.plan)
    before = I.wf_signature(old_plan, types)
    old_cc = {tn: I.RT.consumer_count(I.RT.for_type(old_plan, tn)) for tn in types}
    print(f'BASELINE {len(types)} types {time.time()-start:.1f}s', flush=True)
    raw = copy.deepcopy(RAW)
    with multiprocessing.get_context('fork').Pool(ARGS.workers) as pool:
        for result in pool.imap_unordered(solve_type, types):
            I.configure(raw['partition_types'][result['type']], ARGS.radius, result['rows'])
            print(f"LOCAL {result['type']} rows={len(result['rows'])} iterations={result['iterations']}", flush=True)
    plan = I.S.Plan(raw, ARGS.out)
    after = I.wf_signature(plan, types)
    # Region placement and reset-wire endpoints remain fixed. Release dates may
    # change; they are explicitly emitted below for the compiler and boot plan.
    for tn, old in before['types'].items():
        for field in ('in_um', 'outs', 'entry_stages'):
            if old[field] != after['types'][tn][field]:
                raise ValueError(f'{tn}: physical reset endpoint changed: {field}')
    changes = {pn: dict(old=before['parts'][pn], new=row) for pn, row in after['parts'].items()
               if before['parts'][pn] != row}
    report = {}
    for tn in types:
        report[tn] = I.fix_contract(plan, tn, old_cc[tn])
    # Re-check the combined solution: per-type parallel discovery must not hide
    # a newly introduced global dependency or a missed reset/collector relay.
    worst = {}
    for tn in types:
        taps = [(x, y) for _, x, y in I.S.tap_grid(plan, tn)]
        worst[tn] = max(min(I.man(point, tap) for tap in taps) for point in I.chain_points(plan, tn))
        if worst[tn] > ARGS.radius + 1e-6:
            raise ValueError(f'{tn}: combined control-sink reach {worst[tn]} exceeds radius')
    sidecar = json.loads(Path(ARGS.sidecar_in).read_text())
    collector_types = sidecar.get('collector', {}).get('types', {})
    for tn in types:
        if tn in collector_types:
            lc = raw['partition_types'][tn]['clock']['landing_contract']
            for key in ('collector_tree', 'collector_local_sources', 'collector_children', 'collector_root_node'):
                dest = dict(collector_tree='tree', collector_local_sources='local_sources',
                            collector_children='children', collector_root_node='collector_root_node')[key]
                if key in lc:
                    collector_types[tn][dest] = lc[key]
    Path(ARGS.out).write_text(I.compact_plan.dumps(raw))
    Path(ARGS.sidecar_out).write_text(json.dumps(sidecar, separators=(',', ':'))+'\n')
    # Actual deterministic dates, not a claim that the old wavefront is unchanged.
    release = I.RT.wf_plan(plan)
    Path(ARGS.out+'.reset_release.json').write_text(json.dumps(release, separators=(',', ':'))+'\n')
    summary = dict(types=len(types), radius=ARGS.radius, max_control_reach_um=max(worst.values()),
                   reset_changes=changes, max_release_old=before['max_release'],
                   max_release_new=after['max_release'], elapsed_s=round(time.time()-start),
                   type_contracts=report)
    Path(ARGS.out+'.report.json').write_text(json.dumps(summary, indent=1)+'\n')
    print('STATION_TAPS_PASS '+json.dumps({k:v for k,v in summary.items()
                                        if k not in ('reset_changes','type_contracts')}), flush=True)


if __name__ == '__main__':
    main()
