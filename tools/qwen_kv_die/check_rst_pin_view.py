#!/usr/bin/env python3
"""Refuse an absent or native-failing opt-in reset root view before binding it."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
from native_pin_audit import audit_one


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--view', required=True)
    p.add_argument('--cell', default='qkd_rst_region_pr')
    a = p.parse_args()
    view = ROOT / a.view
    required = [view / 'insertion.json', view / 'abstract.json', view / f'{a.cell}.lef']
    required += [view / f'{a.cell}_{c}.lib' for c in ('tt', 'ff')]
    missing = [str(f) for f in required if not f.is_file()]
    if missing:
        print(json.dumps(dict(status='FAIL', missing=missing)))
        return 1
    rec = audit_one((str(ROOT), a.cell, a.view))
    # All ten inputs (including every delay strap) remain in the raw audit.
    ok = (rec.get('pass') is True and rec.get('insertion') is True
          and rec.get('inputs') == 10 and rec.get('outputs') == 1
          and rec.get('spread_ps', float('inf')) <= 80)
    rec.update(status='PASS' if ok else 'FAIL',
               hashes={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in required})
    print(json.dumps(rec, sort_keys=True))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
