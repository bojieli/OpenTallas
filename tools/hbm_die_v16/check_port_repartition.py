#!/usr/bin/env python3
"""Compare exact contract-bit populations before/after station face grouping.

This checks the relay layer's source/sink assignment (including remastered and
added ports). It proves no population loss, duplication or consumer change;
it does not prove the new station latency, geometry or clock/reset behavior.
Run large contracts on the fleet.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re


def load(path):
    return json.load(gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path))


def population(contract, rows):
    loads = defaultdict(list)
    for edge in contract['edges']:
        src, dst = edge['source'], edge['sink']
        for bit in range(src[3] - src[2]):
            loads[src[0], src[1], src[2] + bit].append((dst[0], dst[1], dst[2] + bit))
    by_driver = defaultdict(list)
    for (driver, port, bit), sinks in loads.items():
        by_driver[driver].append((port, bit, tuple(sorted(sinks))))
    row_bits, claimed, rows_of = {}, defaultdict(set), defaultdict(list)
    for index, row in enumerate(rows):
        driver, ports = row['driver'].split('.', 1)
        ports = set(ports.split('+'))
        rows_of[driver].append(index)
        row_bits[index] = [item for item in by_driver[driver]
                           if item[0] in ports and {s[0] for s in item[2]} == set(row['sinks'])]
        claimed[driver].update((p, b) for p, b, _ in row_bits[index])
    for index, row in enumerate(rows):
        driver = row['driver'].split('.', 1)[0]
        if not row_bits[index]:
            row_bits[index] = [item for item in by_driver[driver]
                               if item[:2] not in claimed[driver]
                               and {s[0] for s in item[2]} == set(row['sinks'])]
            claimed[driver].update((p, b) for p, b, _ in row_bits[index])
    stem = lambda p: re.sub(r'_[wnes]$', '', p)
    for driver, indices in rows_of.items():
        for port, bit, sinks in by_driver[driver]:
            if (port, bit) in claimed[driver]:
                continue
            candidates = [i for i in indices if set(rows[i]['sinks']) == {s[0] for s in sinks}]
            if not candidates:
                continue
            pick = next((i for i in candidates if stem(port) in {
                stem(p) for p in rows[i]['driver'].split('.', 1)[1].split('+')}), candidates[0])
            row_bits[pick].append((port, bit, sinks))
            claimed[driver].add((port, bit))
    result = Counter()
    for index, bits in row_bits.items():
        driver = rows[index]['driver'].split('.', 1)[0]
        result.update((driver, port, bit, sinks) for port, bit, sinks in bits)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('contract'); ap.add_argument('before'); ap.add_argument('after')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    contract = load(args.contract)
    before = population(contract, load(args.before)['rows'])
    after = population(contract, load(args.after)['rows'])
    lost, added = before - after, after - before
    duplicate = sum(n - 1 for n in after.values() if n > 1)
    digest = hashlib.sha256()
    for key, count in sorted(after.items()):
        digest.update((json.dumps([key, count], separators=(',', ':')) + '\n').encode())
    result = dict(verdict='FAIL' if lost or added or duplicate else 'PASS',
                  before_bits=sum(before.values()), after_bits=sum(after.values()),
                  lost_bits=sum(lost.values()), added_bits=sum(added.values()),
                  duplicate_bits=duplicate, population_sha256=digest.hexdigest(),
                  input_sha256={name: hashlib.sha256(Path(getattr(args, name)).read_bytes()).hexdigest()
                                for name in ('contract', 'before', 'after')},
                  examples=dict(lost=[list(x) for x in list(lost)[:4]],
                                added=[list(x) for x in list(added)[:4]]),
                  scope='exact current contract source-bit and full consumer tuple multiset; no physical/latency qualification')
    Path(args.out).write_text(json.dumps(result, indent=1) + '\n')
    print('PORT_REPARTITION', json.dumps(result))
    return 1 if result['verdict'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
