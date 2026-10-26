#!/usr/bin/env python3
"""Collect the necessary same-binary STG MAT producer-contract component repair.

Cycle fields are actual event pin-publication dates and the final sampled status,
not a claim of upstream MAC execution or full-token timing.
"""
import argparse
import json
from pathlib import Path
import re

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('root', type=Path)
ap.add_argument('--lm-only', action='store_true')
a = ap.parse_args()
root = a.root
names = ['lm', 'amax_local'] if a.lm_only else ['calibrate', 'qkv', 'gu', 'od', 'drop_last_k']
rows = {}
for name in names:
    work = root / 'run' / name
    text = (work / 'bench.out').read_text() if (work / 'bench.out').exists() else ''
    line = text.splitlines()[0] if text else 'NOT_RUN'
    negative = name in ('drop_last_k', 'amax_local')
    verdict = 'PASS' if name == 'calibrate' and 'CALIBRATE OK' in text else 'NOT_RUN'
    match = re.search(r'^DV_LOWER_MAT \S+ (PASS|FAIL|REFUSED) (\d+)/(\d+)', text, re.M)
    if match:
        verdict = match.group(1)
    row = dict(verdict=verdict, expected='FAIL' if negative else 'PASS', summary=line,
               expected_outcome=verdict == ('FAIL' if negative else 'PASS'))
    if name == 'calibrate' and (work / 'stn_ages.json').exists():
        row['ages'] = json.loads((work / 'stn_ages.json').read_text())
        row['expected_outcome'] &= not row['ages'].get('faults')
    events = list(work.glob('*.ev'))
    if len(events) == 1:
        stn, producer = [], []
        for line in events[0].read_text().splitlines():
            edge, port, payload = line.split()
            edge, port, value = int(edge), int(port), int(payload, 16)
            if port == 0 and value & 1 and (value >> 1) & 7 == 2:
                stn.append(edge)
            if 2 <= port < 26:
                if (value >> 512) & 1:
                    producer.append(edge)
                if (value >> 1026) & 1:
                    producer.append(edge)
        if producer:
            row['pin_event_cycles'] = dict(first_stn_entry=min(stn) if stn else None,
                first_cluster_word=min(producer), last_cluster_word=max(producer),
                cluster_word_publications=len(producer),
                cluster_stream_span_inclusive=max(producer) - min(producer) + 1)
    row['vm_write_edges'] = dict(first=None, last=None, reason='reused testbench has no VM-write probe; legacy anchor span is not an observed VM latency')
    for log in work.glob('*.log'):
        readback = re.findall(r'^(\d+) S0DD [0-9a-f]+$', log.read_text(), re.M)
        if readback:
            row['d2d_readback_publication_edges'] = dict(first=int(readback[0]), last=int(readback[-1]), scope='readback observation, not VM-write timestamps')
        status = re.findall(r'^(\d+) S0AG ([0-9a-f]+)$', log.read_text(), re.M)
        if status:
            edge, value = status[-1]
            row['final_status_sample'] = dict(edge=int(edge), aggregate=int(value, 16),
                                              station_drained=not bool(int(value, 16) & (1 << 9)))
    rows[name] = row
receipt = dict(scope='STN/VM component at cluster-output cut; no upstream MAC/full-token claim',
    source=json.loads((root / 'SOURCE.json').read_text()),
    verdict='PASS (scoped component)' if all(v['expected_outcome'] for v in rows.values()) else 'INCOMPLETE/FAIL',
    running_partial_math='BF16 x; per-chunk FP32 add(acc,mul(w,x)) from +0 at every k; canonical pairwise tree over 64 chunks; final prefix bit-equal to existing l6_parts golden',
    cycle_basis='event dates at STN command entry and cluster input pins; final sampled status is a completion upper bound',
    cases=rows)
(root / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps(dict(verdict=receipt['verdict'], cases={k: v['verdict'] for k, v in rows.items()})))
