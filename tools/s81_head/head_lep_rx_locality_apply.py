#!/usr/bin/env python3
"""Apply the reviewed zero-cycle LEP layout delta to its exact immutable plan.

This changes physical macro origins and three reset tap sites only. It does not
activate native clock ports, provide clocks, or authorize CTS/route.
"""
import argparse
import hashlib
import json
from pathlib import Path


def apply(base, delta, output):
    payload = Path(base).read_bytes()
    spec = json.loads(Path(delta).read_text())
    if hashlib.sha256(payload).hexdigest() != spec['base_sha256']:
        raise ValueError('base plan differs from the reviewed exact6 source')
    plan = json.loads(payload)
    typ = plan['partition_types'][spec['partition_type']]
    cores = {c['inst']: c for c in typ['hard_cores']}
    for move in spec['macro_origin_changes']:
        core = cores[move['instance']]
        if core['origin_um'] != move['before']:
            raise ValueError('macro origin mismatch: ' + move['instance'])
        core['origin_um'] = move['after']
    for move in spec['reset_site_changes']:
        taps = typ['reset']['local_taps_um']
        if taps[move['index']] != move['before']:
            raise ValueError('reset tap mismatch')
        taps[move['index']] = move['after']
    if 'wavefront_min_depth' in spec:
        if 'wavefront_min_depth' in typ['reset']:
            raise ValueError('base already has a reset depth floor')
        typ['reset']['wavefront_min_depth'] = spec['wavefront_min_depth']
    for change in spec.get('raw_export_rebind', []):
        port = change['port']
        rows = typ['reset_start_raw_exports']
        idx = next(i for i, row in enumerate(rows) if row['port'] == port)
        if rows[idx] != change['before']:
            raise ValueError('raw reset export differs: ' + port)
        rows[idx] = change['after']
        pins = typ['clock']['landing_contract']['pins']
        idx = next(i for i, pin in enumerate(pins) if pin['name'] == port)
        if pins[idx] != change['pin_before']:
            raise ValueError('raw reset export pin differs: ' + port)
        pins[idx] = change['pin_after']
    result = (json.dumps(plan, indent=2) + '\n').encode()
    if hashlib.sha256(result).hexdigest() != spec['candidate_sha256']:
        raise ValueError('candidate differs from reviewed geometry')
    Path(output).write_bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_plan')
    parser.add_argument('delta')
    parser.add_argument('output')
    args = parser.parse_args()
    apply(args.base_plan, args.delta, args.output)
