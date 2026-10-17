#!/usr/bin/env python3
"""DIE-CLOCK: add tile masters' in-arc clock insertion R to a build.py targets file, from closure-loop
insertion.json receipts (opentallas.closure_loop.ck_insertion.v1: <corner>.boundary.mean).

  targets_from_insertion.py --base targets.json --out targets_d4b.json --pin ck \\
      physical/ref_tile/hbfd_rly_624_ew/views/hbfd_rly_624_EW/insertion.json ...
The master name is the receipt's view directory (views/<master>/insertion.json). R = [ss, ff, tt] boundary means
(the boundary registers are the tile pins' capture/launch flops; the die delivers each pin at phi - R).
"""
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--pin', default='ck')
    ap.add_argument('receipts', nargs='+', type=Path)
    a = ap.parse_args()
    t = json.loads(a.base.read_text()) if a.base else {'masters': {}}
    t.setdefault('masters', {})
    for r in a.receipts:
        d = json.loads(r.read_text())
        R = [d[c]['boundary']['mean'] for c in ('ss', 'ff', 'tt')]
        m = r.parent.name
        e = t['masters'].setdefault(m, {})
        e.setdefault('insertion_per_clock_pin_ps', {})[a.pin] = R
        e['insertion_source'] = str(r)
        print(m, a.pin, R)
    a.out.write_text(json.dumps(t, indent=1) + '\n')


if __name__ == '__main__':
    main()
