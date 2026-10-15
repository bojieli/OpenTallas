#!/usr/bin/env python3
"""Read a compute placement dump and search an actual legal upper-leaf repack.

This is a placement proposal, never a routed timing or congestion certificate.
The lower bound uses rectangle separation and 490-um registered reach. Real
pin rectangles, relay frames, clock phases and metal cuts remain required.
"""
import argparse
import copy
import json
import math
from pathlib import Path


def gap(a, b):
    return sum(max(0, a[k] - b[k] - b[s], b[k] - a[k] - a[s])
               for k, s in [('x', 'w'), ('y', 'h')])


def overlap(a, b):
    return all(min(a[k]+a[s], b[k]+b[s])-max(a[k], b[k]) > 1e-5
               for k, s in [('x', 'w'), ('y', 'h')])


def relays(a, b):
    return max(0, math.ceil(round(gap(a, b), 5)/490)-1)


def validate(instances, die):
    bad = []
    for n, a in enumerate(instances):
        if a['x'] < 0 or a['y'] < 0 or a['x']+a['w'] > die['w']+.001 or a['y']+a['h'] > die['h']+.001:
            bad.append(['outside', a['n']])
        for b in instances[n+1:]:
            if overlap(a, b):
                bad.append(['overlap', a['n'], b['n']])
    return bad


def score(leaves, by):
    bands = [by[f'sp_band_lanes_{b}'] for b in range(3)]
    # All lane slices must receive equal stage ages; price the longest lane.
    incoming = [max(relays(b, l) for l in leaves) for b in bands]
    returning = max(relays(l, bands[0]) for l in leaves)
    return dict(input_relays=incoming, return_relays=returning,
                critical_roundtrip_relays=max(incoming)+returning)


def propose(dump):
    original = copy.deepcopy(dump['insts'])
    by = {i['n']: i for i in original}
    parent = by['tt_up4_0']
    baseline = score([parent], by)
    # Mirror the complete band-0 stack, retaining its original outer envelope.
    modified = copy.deepcopy(original)
    ix = {i['n']: i for i in modified}
    lane, port, res = [ix[f'sp_{k}_0'] for k in ['band_lanes', 'port_tiles', 'res_ser']]
    bottom = lane['y']
    res['y'] = bottom
    port['y'] = bottom+518.4+4.32
    lane['y'] = bottom+518.4+2462.4+8.64
    for i in [lane, port, res]:
        i['o'] = 'MX'
    # E-half tracks the W-half port slot. It keeps R0: source face pins need
    # an independent exact reroute/assignment before production adoption.
    ix['sp_port_tiles_0_f1']['y'] = port['y']
    flip_score = score([parent], ix)
    fixed = [i for i in modified if i['n'] != parent['n']]
    vm = ix['sp_vector_memory']
    f1right = max(i['x']+i['w'] for i in fixed if i['n'].startswith('sp_port_tiles_') and i['n'].endswith('_f1'))
    x = math.floor((f1right+vm['x']-64.8)/2/.216)*.216
    best = None
    for ytick in range(2200, 4000):
        y = ytick*4.32
        leaves = [dict(n=f'tt_up4_leaf{k}', m='ot_qfd_band_upper',
                       x=round(x, 4), y=round(y+k*224.64, 4),
                       w=64.8, h=205.2, o='R0') for k in range(4)]
        if any(overlap(a, b) for a in leaves for b in fixed):
            continue
        metrics = score(leaves, ix)
        key = (metrics['critical_roundtrip_relays'], max(metrics['input_relays']), sum(metrics['input_relays']), abs(y-13000))
        if best is None or key < best[0]:
            best = key, leaves, metrics
    if best is None:
        raise ValueError('no legal upper-leaf stack in existing west VM channel')
    _, leaves, metrics = best
    actual = fixed+leaves
    errors = validate(actual, dump['die'])
    baseline_errors = validate(original, dump['die'])
    changed = [i for i in actual if i['n'] not in by or i != by[i['n']]]
    return dict(schema='opentallas.qwen.placement-repack-projection.v1',
                evidence_scope='legal source rectangle proposal; geometric lower bounds only',
                die=dump['die'], baseline=baseline, band0_flip_only=flip_score,
                candidate=metrics, placements=changed, retired=['tt_up4_0'],
                baseline_geometry_errors=baseline_errors, candidate_geometry_errors=errors,
                saved_critical_stages=baseline['critical_roundtrip_relays']-metrics['critical_roundtrip_relays'],
                cuts=dict(qualified=False, reason='exact per-bit paths and relay sites absent; cannot infer <=0.60 from rectangles'),
                production_relay_cost=dict(qualified=False, reason='full relay planner and actual layer measurement required'),
                warnings=['MX band-0 pins/clocks must be regenerated from actual child orientations.',
                          'Vertical direct-leaf stack requires exact per-leaf pin/clock joins and equal fixed ages.',
                          'Global rectangle validity does not prove pin access or relay-frame fit.'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dump', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = propose(json.loads(args.dump.read_text()))
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['baseline', 'band0_flip_only', 'candidate', 'saved_critical_stages', 'candidate_geometry_errors']}))
    if result['candidate_geometry_errors']:
        raise SystemExit('candidate is not geometrically legal')


if __name__ == '__main__':
    main()
