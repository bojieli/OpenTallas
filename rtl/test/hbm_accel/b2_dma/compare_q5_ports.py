#!/usr/bin/env python3
"""Compare all accepted per-port request payloads; permit cycle offsets, reject drops/order changes.
The deliberately reset-aborted record is marked by the bench and compared by its independent
functional reset gate, since a latency change changes how many beats happen before that reset.
"""
import argparse
from collections import defaultdict
from pathlib import Path

def read(path):
    rows = defaultdict(list)
    skip = set()
    lines = Path(path).read_text().splitlines()
    if not any(x.startswith('B2_DMA_Q PASS checked=') for x in lines):
        raise ValueError(f'{path}: exact behavioral PASS absent')
    for line in lines:
        if not line.startswith('Q5TRACE '):
            continue
        _, epoch, port, *payload = line.split()
        if port == 'ABORT':
            skip.add(epoch)
            continue
        if epoch not in skip:
            rows[(epoch, port)].append(tuple(payload))
    return rows

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('flat')
    p.add_argument('partition')
    args = p.parse_args()
    a, b = read(args.flat), read(args.partition)
    mismatches = []
    for key in sorted(set(a) | set(b)):
        if a[key] != b[key]:
            i = next((i for i, (x,y) in enumerate(zip(a[key],b[key])) if x != y), min(len(a[key]),len(b[key])))
            mismatches.append((key, i, len(a[key]), len(b[key]), a[key][i:i+1],b[key][i:i+1]))
    if mismatches:
        for item in mismatches[:12]: print('Q5_PORTS DIFFERENT', item)
        raise SystemExit(1)
    count = sum(map(len, a.values()))
    if count == 0: raise ValueError('trace is empty')
    print(f'Q5_PORTS PASS checked={count} streams={len(a)} all_payloads_in_order=1')

if __name__ == '__main__': main()
