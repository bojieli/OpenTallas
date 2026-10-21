#!/usr/bin/env python3
"""Carry original relay-note coordinates through an additional channel-cut plan.

The physical plan has already moved through the first map. Combining the two
piecewise translations lets die_case_v16 keep consuming the original contract
notes without dropping either displacement. This extension opens X margins;
the die's existing reticle-bound Y placement stays unchanged.
"""
import argparse
import copy
import json
from pathlib import Path


def inverse_x(band, x):
    shift = band.get('shift', 0.0)
    for cut, width in sorted(band.get('cuts', [])):
        if x <= cut + shift:
            return x - shift
        if x <= cut + shift + width:
            return cut
        shift += width
    return x - shift


def extend(prior, extra):
    out = copy.deepcopy(prior)
    spec = out['spec']
    if extra.get('ycuts'):
        raise ValueError('this implementation extends X margins only')
    by_name = {b['name']: b for b in extra['bands']}
    for band in spec['bands']:
        addition = by_name[band['name']]
        cuts = list(band.get('cuts', []))
        cuts.extend([inverse_x(band, x), width] for x, width in addition.get('cuts', []))
        merged = {}
        for x, width in cuts:
            merged[x] = merged.get(x, 0.0) + width
        band['cuts'] = sorted([x, width] for x, width in merged.items())
        band['shift'] = band.get('shift', 0.0) + addition.get('shift', 0.0)
    spec['why'] = spec.get('why', '') + ' | ' + extra.get('why', '')
    out['extension'] = extra
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('prior_map', type=Path)
    p.add_argument('extra_spec', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(extend(json.loads(a.prior_map.read_text()),
                                        json.loads(a.extra_spec.read_text())), indent=1) + '\n')
