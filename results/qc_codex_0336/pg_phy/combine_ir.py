"""Join actual per-load supply and return voltages; never sum unrelated maxima."""
import argparse
import csv
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('psm', type=Path)
p.add_argument('--supply', default='VDDPHY')
p.add_argument('--nominal', type=float, default=.7)
p.add_argument('--limit-mv', type=float, default=35)
a = p.parse_args()

def rows(net):
    result = {}
    with (a.psm / f'ir_{net}.csv').open() as f:
        for row in csv.DictReader(f):
            inst = row['Instance']
            if inst in result:
                raise ValueError(f'duplicate load identity {inst}')
            result[inst] = row
    return result

v, g = rows(a.supply), rows('VSS')
missing = sorted(set(v) - set(g))
if missing:
    raise ValueError(f'missing return samples for {missing[:10]}')
combined = []
for inst, row in v.items():
    supply, ground = float(row['Voltage']), float(g[inst]['Voltage'])
    combined.append(dict(instance=inst, supply_v=supply, return_v=ground,
                         combined_drop_mv=1000*(a.nominal-supply+ground)))
if not combined:
    raise ValueError('no actual load samples')
worst = max(combined, key=lambda x:x['combined_drop_mv'])
print(json.dumps(dict(scope='actual same-load supply/return join; source model remains coupon-specific',
                     supply=a.supply, samples=len(combined), worst=worst,
                     limit_mv=a.limit_mv,
                     verdict='PASS' if worst['combined_drop_mv']<=a.limit_mv else 'FAIL'),indent=1))
