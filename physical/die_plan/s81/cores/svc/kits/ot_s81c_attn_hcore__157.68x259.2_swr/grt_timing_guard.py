#!/usr/bin/env python3
"""HCORE route admission: insertion PASS alone does not establish timing."""
import json
import math
import sys
from pathlib import Path


def check(kit):
    records = {}
    for corner in ('tt', 'ff'):
        path = Path(kit) / f'postcts_gate_{corner}.json'
        data = json.loads(path.read_text())
        if data.get('corner', '').lower() != corner:
            raise ValueError(f'{corner}: missing/wrong corner')
        if data.get('parasitics') != 'global_routing' or data.get('verdict') != 'PASS':
            raise ValueError(f'{corner}: native GRT insertion gate did not pass')
        records[corner] = data
    for corner, key in [('tt', 'setup_wns_est_ps'), ('ff', 'hold_wns_est_ps')]:
        value = float(records[corner][key])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f'{corner}: {key}={value} blocks route')
    return records


if __name__ == '__main__':
    try:
        records = check(sys.argv[1])
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f'HCORE_GRT_TIMING FAIL: {exc}', file=sys.stderr)
        raise SystemExit(3)
    print('HCORE_GRT_TIMING PASS: TT setup and FF hold nonnegative; final SIGNED still required')
