#!/usr/bin/env python3
"""Fail closed when actual HBM die instances use generic centroid placement or lack a placed home.

A complete home census is a structural admission condition, independent of timing/real-view qualification.
Coordinate legality, reach and native view lineage still require their own gates.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path


def audit(manifest, contract):
    placed = manifest['placement']
    rows = []
    for name, item in sorted(contract['instances'].items()):
        home = placed.get(name)
        reason = None
        if home is None:
            reason = 'missing_placed_home'
        elif home.get('rule', '').startswith('centroid'):
            reason = 'generic_centroid_fallback'
        elif not home.get('rule'):
            reason = 'missing_home_provenance'
        if reason:
            rows.append(dict(instance=name, master=item['master'], slot=item.get('slot'), reason=reason,
                             actual_home=home, area_um2=None if home is None else round(home['w'] * home['h'], 6)))
    extras = sorted(set(placed) - set(contract['instances']))
    return dict(schema='opentallas.hbm.placement_coverage.v1', verdict='FAIL' if rows or extras else 'PASS',
                actual_instances=len(contract['instances']), placed_instances=len(placed),
                defects=len(rows), by_reason=dict(Counter(x['reason'] for x in rows)),
                affected_area_um2=round(sum(x['area_um2'] or 0 for x in rows), 6),
                extra_placed_instances=extras, rows=rows, native_release_qualified=False,
                qualification='Placement provenance census only; no geometry, reset, clock or timing waiver.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    opener = gzip.open if a.contract.suffix == '.gz' else open
    with opener(a.contract, 'rt') as f:
        c = json.load(f)
    r = audit(json.loads(a.manifest.read_text()), c)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps({k: v for k, v in r.items() if k != 'rows'}))
    return 0 if r['verdict'] == 'PASS' else 3


if __name__ == '__main__':
    raise SystemExit(main())
