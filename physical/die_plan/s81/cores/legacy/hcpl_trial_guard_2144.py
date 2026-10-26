#!/usr/bin/env python3
"""Check immutable HCPL GRT cohort before the single approved DRT trial."""
import hashlib
import json
import re
import sys
from pathlib import Path


def check(kit):
    kit = Path(kit)
    record = json.loads((kit / 'hcpl_trial_cohort.json').read_text())
    if record.get('permission') != 'ONE_DRT_TRIAL_UNAFFECTED_MASTER':
        raise ValueError('missing specific conditional trial approval')
    if record.get('master') != 'ot_dsrom_su_hcpost_lane_pr' or record.get('outline_um') != [114.48, 114.48]:
        raise ValueError('wrong master/outline')
    for rel, expected in record['sha256'].items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('cohort input must be kit-relative')
        if hashlib.sha256((kit / path).read_bytes()).hexdigest() != expected:
            raise ValueError('cohort changed: ' + rel)
    cfg = (kit / 'config.mk').read_text()
    for c, value in [('TT', 250.0), ('FF', 202.5)]:
        m = re.search(rf'^export OT_VCLK_{c} = (\S+)$', cfg, re.M)
        if not m or float(m[1]) != value:
            raise ValueError('native boundary changed: ' + c)
    for c in ('TT', 'FF'):
        text = (kit / f'postgrt_{c}.log').read_text()
        m = re.search(r'HCPL_SHIFT TIMING (TT|FF) setup ([-\d.]+) nsetup (\d+) hold ([-\d.]+) nhold (\d+)', text)
        if not m or m[1] != c:
            raise ValueError('missing native GRT timing: ' + c)
        if (c == 'TT' and (float(m[2]) < 0 or int(m[3]))) or (c == 'FF' and (float(m[4]) < 0 or int(m[5]))):
            raise ValueError('native GRT timing fails: ' + m[0])
        if f'HCPL_SHIFT OWNERSHIP_PASS {c} groups 32 FF 702' not in text:
            raise ValueError('clock ownership changed: ' + c)
    return record


if __name__ == '__main__':
    try:
        check(sys.argv[1])
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print('HCPL_TRIAL_COHORT FAIL ' + str(exc), file=sys.stderr)
        raise SystemExit(3)
    print('HCPL_TRIAL_COHORT PASS; normal canary and mode=trial still required')
