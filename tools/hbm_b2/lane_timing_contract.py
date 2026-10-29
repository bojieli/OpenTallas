#!/usr/bin/env python3
"""Export added HBM lanes to the existing compiler LAT ABI, preserving partial-pair failures.

This is a compiler preparation tool, not a die gate or a source signal mapper. Each LAT
comes only from Plan.lane_latency. Pair completeness is additive NEW capacity versus the
strict bind's missing bits; existing lane capacity is already consumed by that bind.
Never infer an RTL delay from a partition pair: several functional lanes can have
unrelated dates, and a partially built pair cannot carry its entire missing bus.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
from gen import lane_param
from schema import Plan


def build(raw, added, unplanned):
    p = Plan(raw)
    rows, pair_lanes = [], defaultdict(list)
    params = set()
    for a in added['built']:
        lid = a['lane']
        ln = p.lanes[lid]
        first, last = p.ports[ln['ports'][0]], p.ports[ln['ports'][-1]]
        src, dst = first['src']['part'], last['dst']['part']
        if (src, dst, first['width']) != (a['src'], a['dst'], a['bits']):
            raise ValueError(f'{lid}: report endpoints/width differ from plan')
        lat = p.lane_latency(lid)
        if lat['cycles'] != a['cycles']:
            raise ValueError(f'{lid}: report cycles {a["cycles"]} != plan {lat["cycles"]}')
        param = lane_param(lid, ln)
        if param in params:
            raise ValueError(f'duplicate LAT parameter {param}')
        params.add(param)
        row = dict(lane=lid, param=param, src=src, dst=dst, bits=first['width'],
                   cycles=lat['cycles'], components=lat)
        rows.append(row)
        pair_lanes[(src, dst)].append(row)
    pairs = []
    for u in unplanned['rows']:
        key = u['src'], u['dst']
        ls = pair_lanes.get(key, [])
        have, need = sum(x['bits'] for x in ls), u['unplanned_bits']
        pairs.append(dict(src=key[0], dst=key[1], required_new_bits=need,
                          new_bits=have, uncovered_bits=max(0, need-have),
                          capacity_complete=have >= need, lanes=[x['lane'] for x in ls],
                          cycles=sorted({x['cycles'] for x in ls}),
                          source_mapping='REQUIRED: bind assigns actual signal bits to lanes'))
    # Even complete aggregate capacity is not a signal/clock/reset contract.
    return dict(schema='opentallas.hbm.added_lane_timing.v1',
                status='COMPILER_PREPARATION_ONLY', executable=False,
                reason='actual signal-to-lane map and qualified clock/reset/START dates required',
                lanes=rows, pairs=pairs,
                totals=dict(lanes=len(rows), pairs=len(pairs),
                            capacity_complete=sum(x['capacity_complete'] for x in pairs),
                            incomplete=sum(not x['capacity_complete'] for x in pairs),
                            new_bits=sum(x['bits'] for x in rows),
                            uncovered_bits=sum(x['uncovered_bits'] for x in pairs)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--added', required=True)
    ap.add_argument('--unplanned', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    inputs = {k: Path(getattr(a, k)).read_bytes() for k in ('plan', 'added', 'unplanned')}
    r = build(*(json.loads(inputs[k]) for k in ('plan', 'added', 'unplanned')))
    r['inputs_sha256'] = {k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()}
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(r, indent=1)+'\n')
    sv = ['// COMPILER PREPARATION ONLY; bind signal map + clock dates remain required.',
          'package hbm_added_lane_lat_pkg;']
    sv.extend(f'  localparam int {x["param"]} = {x["cycles"]}; // {x["lane"]}: {x["src"]}->{x["dst"]}, {x["bits"]} bits'
              for x in sorted(r['lanes'], key=lambda x: x['param']))
    sv.append('endpackage')
    dest.with_suffix('.sv').write_text('\n'.join(sv)+'\n')
    print(json.dumps(r['totals']))


if __name__ == '__main__':
    main()
