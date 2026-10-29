#!/usr/bin/env python3
"""Rebuild HEAD CA/START tables from a current raw plan and measured clock.

RUN/clk/tree.json and RUN/out_{TT,FF}/arr_{TT,FF}.txt must be the exact
clock's source-edge-resolved readout. No earlier K, origin, or crossing table
is reused. Core/ring latency inputs stay explicit; this prepares the bind and
does not qualify missing physical views or the START implementation.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[2]
T = W / 'tools/die_plan'
H = W / 'tools/s81_head'
sys.path.insert(0, str(H))
import fallback_land as F


def region_rows(ocv, table, mapping):
    """Keep the exact current external crossing set and its measured bounds."""
    ports = {p['port']: p for p in table['ports']}
    out = dict(ocv, corners={})
    for key, corner in ocv['corners'].items():
        if corner.get('all') is None:
            continue
        rows = []
        for r in corner['all']:
            if r['port'] not in ports:
                assert mapping[r['src']] == mapping[r['dst']], ('undeclared crossing', r['port'])
                continue
            p = ports[r['port']]
            assert (r['src'], r['dst']) == (p['src'], p['dst']), ('stale endpoints', r['port'])
            rows.append(dict(r, src_part=r['src'], dst_part=r['dst'], physical_src=r['src'],
                             physical_dst=r['dst'], src=mapping[r['src']], dst=mapping[r['dst']]))
        assert {r['port'] for r in rows} == set(ports), ('incomplete current crossing set', key)
        out['corners'][key] = dict(corner, all=rows, crossings=len(rows),
                                  worst_margin_ps=min(r['margin_ps'] for r in rows),
                                  under_100=sum(r['margin_ps'] < 100 for r in rows),
                                  under_0=sum(r['margin_ps'] < 0 for r in rows))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True, type=Path)
    p.add_argument('--regions', required=True, type=Path)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--ca-ring', required=True, type=Path)
    p.add_argument('--core-tt', type=float, default=450)
    p.add_argument('--core-ff', type=float, default=380)
    p.add_argument('--clock-cell', choices=['auto', 'buf', 'inv', 'inv2'], default='auto')
    p.add_argument('--start-max-hop-um', type=float, default=405)
    a = p.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    plan = json.loads(a.plan.read_text())
    mapping = json.loads(a.regions.read_text())['part_region']
    table = F.table(plan, 'map:' + str(a.regions.resolve()))
    (out/'table.json').write_text(json.dumps(table, indent=1))
    def step(name, args):
        with (out/(name+'.log')).open('x') as f:
            rc = subprocess.call([sys.executable]+list(map(str, args)), cwd=W, stdout=f, stderr=subprocess.STDOUT)
        print(name, 'rc', rc, flush=True)
        if rc:
            raise SystemExit(rc)
    step('proof0', [H/'head_mk_proof_lca.py', a.run, a.regions, out/'proof0'])
    step('fall_TT', [T/'tap_fall_merge.py', out/'proof0', 'TT', a.run/'out_TT/arr_TT.txt', '--tree', a.run/'clk/tree.json', '--out', out/'proofT'])
    step('fall_FF', [T/'tap_fall_merge.py', out/'proofT', 'FF', a.run/'out_FF/arr_FF.txt', '--tree', a.run/'clk/tree.json', '--out', out/'proof'])
    step('physical_ocv', [H/'landed_phase_ocv.py', a.plan, a.run, '--tools', T, '--clock-cell', a.clock_cell, '--core-lat', f'TT={a.core_tt:g},FF={a.core_ff:g}', '--port-taps', '--out', out/'physical_ocv.json'])
    ocv = region_rows(json.loads((out/'physical_ocv.json').read_text()), table, mapping)
    (out/'region_ocv.json').write_text(json.dumps(ocv, indent=1))
    step('plan', [T/'count_align_plan.py', out/'region_ocv.json', '--corner', f'TT_droop-regions_corelat{a.core_tt:g},FF_droop-regions_corelat{a.core_ff:g}', '--sta-proof', out/'proof', '--sta-plan', a.plan, '--sta-clock-cal', 'spice_edge', '--sta-cppr-lca', '--sta-clock-ocv', 'table', '--sta-clock-droop', 'shared', '--sta-droop-regions', out/'proof/droop_regions.json', '--sta-core-latency-ff', a.core_ff, '--sta-ca-ring', a.ca_ring, '--sta-clock-cell', a.clock_cell, '--start-tree', 'clock', '--start-clean', 'width', '--start-max-hop-um', a.start_max_hop_um, '--start-retime-max', 64, '--mc-chips', 2000, '--out', out/'plan.json'])
    summary = json.loads((out/'plan.json').read_text())['summary']
    iv = summary['sta_interval']
    assert summary['crossings'] == len(table['ports']) and iv['rows'] == len(table['ports'])
    assert not any(iv.get(k, 0) for k in ['missing', 'unbound', 'rows_without_measured_fall']), iv
    assert summary['fail'] == 0 and summary['below_100ps'] == 0, summary
    step('bind', [T/'count_align_bind.py', out/'plan.json', '--parts', 'table', '--table', out/'table.json', '--table-out', out/'regions_ca.json', '--out', out/'bind.json', '--strap-form', '--plan-die', a.plan, '--straps-out', out/'straps.json'])
    step('emit_start', [T/'start_stage_emit.py', 'emit', out/'bind.json', out/'proof', '--ctree', a.run/'clk', '--plan', a.plan, '--out', out/'start_stages'])
    scope = {'plan': str(a.plan), 'regions': len(table['regions']), 'crossings': len(table['ports']),
             'core_budget_ps': {'TT': a.core_tt, 'FF': a.core_ff},
             'scope': 'Fresh CA plan/bind preparation; emitted START clock and real core views still need their implementation gates',
             'release': 'NOT_CLAIMED'}
    (out/'scope.json').write_text(json.dumps(scope, indent=1))
    print(json.dumps(scope), flush=True)

if __name__ == '__main__':
    main()
