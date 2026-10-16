#!/usr/bin/env python3
"""Audit adopted C5 allocator ownership and report a hop-only rate screen.

This does not recut the executable graph, adopt costs, or qualify native RTL.
The existing headline is an explicit model anchor, not a new immutable price.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOC = 'results/arch/s81_rom_trade_1015/alloc/p1973s89h'   # providers homed on each layer's first dense stage
LEDGER = 'results/arch/accepted_cost_ledger_1013.json'
PROGRAMS = 'results/rtl/s81_ctrl_20261008/programs'


def audit(root=ROOT):
    paths = [f'{ALLOC}/{n}.json' for n in ('inventory', 'stage_map', 'mapping_verdict', 'home_order_check')] + [LEDGER]
    data = [json.loads((root / p).read_text()) for p in paths]
    inv, sm, verdict, home, ledger = data
    assert home['home_at_first_dense_stage_PASS'] and not home['violations']
    assert all(sm['provider_homes'][k] == v for k, v in home['first_dense_stage'].items())
    stages, tp, pairs = inv['stages'], inv['TP'], inv['pairs_per_rank_die']
    assert (stages, tp, pairs, inv['BF_dual_pairs']) == (89, 4, 1973, 424)
    ranks = {(d['stage'], d['rank']) for d in sm['rank_dies']}
    assert ranks == {(s, r) for s in range(stages) for r in range(tp)}
    assert len({d['die_id'] for d in sm['rank_dies']}) == stages * tp
    bounds = sm['region_bounds']
    assert len(bounds) == 129 and bounds[0] == 0 and bounds[-1] == pairs
    assert all(15 <= b-a <= 16 for a, b in zip(bounds, bounds[1:]))
    assert len(set(sm['BF_site_IDs'])) == inv['BF_dual_pairs']
    assert all(0 <= b < pairs for b in sm['BF_site_IDs'])
    assert verdict['counts']['declarations'] == verdict['counts']['placed'] == 46719
    assert verdict['decoder_matrix_capacity_PASS'] and not verdict['failures']
    layer_stages = sm['layer_matrix_stages']
    assert set(layer_stages) == {str(i) for i in range(40)}
    assert all(x == sorted(set(x)) and all(0 <= s < stages for s in x) for x in layer_stages.values())
    assert set(s for x in layer_stages.values() for s in x) == set(range(stages))
    # The measured full-KP4 hop plus published mean cable flight, as in rom_trade.py.
    hop_cycles = 1004 + 171 / 84
    added_us = (stages - 81) * hop_cycles / 1200
    anchors = {'ar': 1447.7, 'mtp': 4238.4}
    tau = {'ar': 1.0, 'mtp': 4.159}
    rates = {}
    rows = [r for r in ledger['rows'] if r['design'] == 's81']
    for wl in anchors:
        hop_only = tau[wl] * 1e6 / (tau[wl] * 1e6 / anchors[wl] + added_us)
        factors, sums = {}, {}
        for status in ('accepted', 'proposed'):
            factors[status] = math.prod(1 - r['per_workload'][wl]['e2e_loss_pct']/100
                                       for r in rows if r['status'] == status and wl in r['per_workload'])
            sums[status] = sum(r['per_workload'][wl]['e2e_loss_pct'] for r in rows
                               if r['status'] == status and wl in r['per_workload'])
        rates[wl] = dict(hop_only_tok_s=hop_only,
                         existing_accepted_rows_sensitivity_tok_s=hop_only*factors['accepted'],
                         existing_accepted_and_proposed_sensitivity_tok_s=hop_only*factors['accepted']*factors['proposed'],
                         additive_accepted_tok_s=hop_only*(1-sums['accepted']/100),
                         additive_accepted_and_proposed_tok_s=hop_only*(1-(sums['accepted']+sums['proposed'])/100),
                         loss_sum_pct=sums,
                         workload_factor=factors)
    progs = sorted((root / PROGRAMS).glob('S[0-9][0-9][0-9].json'))
    return dict(schema='opentallas.s81.c5-schedule-audit.v1',
                physical_allocator=dict(source=ALLOC, provider_home_order_PASS=True,
                                        provider_home_fix='p1973s89 homed layers 9,18,27,32,36 one stage after their first dense matrix (backward hop); p1973s89h homes them on it (fixed point)',
                                        stages=stages, rank_dies=len(ranks), pairs_per_die=pairs, bf_per_die=424,
                                        roots=128, placements=46719, capacity_pass=True,
                                        layer_last_stage={str(int(k)+1):max(v) for k,v in layer_stages.items()},
                                        scan_service_homes=sm['scan_service_homes']),
                executable_programs=dict(count=len(progs), source=PROGRAMS,
                                         matches_89_stage_allocator=False,
                                         note='Historical 59 groups; no 89-stage native operator recut is present.'),
                rate_screen=dict(grade='MODEL_ONLY_HOP_DELTA', anchor_stages=81, target_stages=89,
                                 added_hops=8, added_stream_cycles=8*hop_cycles, added_us=added_us,
                                 headline_anchor_tok_s=anchors, rates=rates,
                                 caveat='Multiplying existing per-workload ledger losses is a sensitivity only; overlap, changed stage boundaries, relay placement, and native service profiles are unresolved. No row or price changes.'),
                blocking=['Recut actual operator graph and source-pinned issue/return allocations onto all 89 stages.',
                          'Produce owned native durations and actual VM service reservations for every emitted job.',
                          'Measure A2-F service and physical relay counts; 900 um planning reach is not measured.',
                          'Integrate HC capture +1 serial edge only after complete parent calendar measurement.',
                          'Close physical pin, clock, route, and full native program composition.'],
                native_qualified=False, executable_dispatch_eligible=False,
                sources={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a=ap.parse_args(); result=audit(); a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['rate_screen'],indent=2))


if __name__ == '__main__':
    main()
