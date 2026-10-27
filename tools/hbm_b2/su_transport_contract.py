#!/usr/bin/env python3
"""Compare the existing SU transport contract against a proposed MU plan.

Physical cut arithmetic alone cannot establish unchanged SU latency. This audit
keeps original logical connection names and reports payload width, wire width,
serializer II and pipeline depth changes. Duplicate copy legs are retained as a
multiset, rather than lost by a conn-keyed dict. Optional complete static launch
traces expose serializer service conflicts; an absent trace remains UNCHECKED.
No change to the plan or schedule is made.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def station_contract(s):
    wires = int(s['bits'])
    k = int(s.get('serial_k') or 1)
    if wires <= 0 or k <= 0:
        raise ValueError('non-positive transport width or serializer II')
    payload = int(s.get('bits_parallel') or wires)
    if payload > wires * k:
        raise ValueError(f'payload {payload} exceeds {wires} wires x {k} beats')
    return (payload, wires, k, len(s['regs_um']) + k - 1)


def inventory(plan):
    result = {}
    for typ, part in plan['partition_types'].items():
        for s in part.get('internal_stations', []):
            key = typ + ':' + s['conn']
            result.setdefault(key, []).append(station_contract(s))
    return {k: sorted(v) for k, v in result.items()}


def compare(baseline, candidate, traces=None):
    base, cand = inventory(baseline), inventory(candidate)
    changes = []
    for key, old in base.items():
        new = cand.get(key, [])
        if old == new:
            continue
        changes.append(dict(connection=key, baseline=old, candidate=new,
                            disposition='MISSING' if not new else 'REPRICE_OR_PROVE_SU_SLOTS'))
    trace_results = []
    serialized = {key: max(r[2] for r in rows) for key, rows in cand.items() if max(r[2] for r in rows) > 1}
    for key, ii in serialized.items():
        raw = (traces or {}).get(key)
        if raw is None:
            trace_results.append(dict(connection=key, serializer_ii=ii, status='UNMEASURED_LINK_DUTY'))
            continue
        cycles = raw.get('launch_cycles', [])
        if cycles != sorted(cycles) or any(type(x) is not int or x < 0 for x in cycles):
            raise ValueError('launch cycles must be sorted non-negative integers')
        bad = [[a, b] for a, b in zip(cycles, cycles[1:]) if b - a < ii]
        complete = raw.get('complete_static_schedule') is True
        trace_results.append(dict(connection=key, serializer_ii=ii, conflicts=bad,
                                  status='SERVICE_CONFLICT' if bad else ('STATIC_SERVICE_FITS' if complete else 'PARTIAL_TRACE_ONLY')))
    return dict(schema='opentallas.su_transport_contract.v1',
                transport='UNCHANGED' if not changes else 'DELTA_REQUIRES_SU_PRICE',
                baseline_connections=len(base), candidate_connections=len(cand),
                changes=changes, added_connections=sorted(set(cand) - set(base)),
                serializer_service=trace_results,
                existing_su_transport_preserved=(not changes and all(x['status'] == 'STATIC_SERVICE_FITS' for x in trace_results)),
                scope='transport contract only; compute throughput, static resource overlap and physical timing remain separate gates')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--launch-traces', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    load = lambda x: json.loads((x / 'die_plan.json' if x.is_dir() else x).read_text())
    result = compare(load(a.baseline), load(a.candidate), load(a.launch_traces) if a.launch_traces else None)
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(result['transport'], 'changed', len(result['changes']), 'unmeasured serializers',
          sum(x['status'] == 'UNMEASURED_LINK_DUTY' for x in result['serializer_service']))


if __name__ == '__main__':
    main()
