#!/usr/bin/env python3
"""Gate RP1 post-GRT measurements using complete status rows and all four related-pair checks."""
import math
from pathlib import Path
import re
import sys


def gate(kit):
    failures = []
    rows = {}
    pair_re = re.compile(r'^RP1_PAIR (TT|FF) (max|min) n (\d+) worst (\S+) bounded (\S+).*?verify (\S+)(?: |$)', re.M)
    status_re = re.compile(r'^RP1_M (TT|FF) setup_wns (\S+) setup_ep (\d+) hold_wns (\S+) hold_ep (\d+)$', re.M)
    for corner in ('TT', 'FF'):
        text = (Path(kit) / f'meas_route_{corner}.log').read_text()
        matches = [m for m in status_re.finditer(text) if m[1] == corner]
        if len(matches) != 1:
            failures.append(f'{corner}: expected one complete measurement row, got {len(matches)}')
            continue
        m = matches[0]
        rows[corner] = tuple(map(float, m.group(2, 3, 4, 5)))
        pairs = [m for m in pair_re.finditer(text) if m[1] == corner]
        if sorted(m[2] for m in pairs) != ['max', 'min']:
            failures.append(f'{corner}: expected one max and one min pair census')
        for m in pairs:
            n, worst, bounded, verify = int(m[3]), float(m[4]), m[5], float(m[6])
            if n <= 0 or not math.isfinite(worst) or not 0 <= worst <= 80 or bounded != '0' or not math.isfinite(verify) or abs(verify) > .35:
                failures.append(f'{corner} {m[2]}: unqualified pair n={n} worst={worst} bounded={bounded} verify={verify}')
    if 'TT' in rows and (not math.isfinite(rows['TT'][0]) or rows['TT'][0] < 0 or rows['TT'][1] != 0):
        failures.append(f'TT setup {rows["TT"][0]} / {rows["TT"][1]} endpoints')
    if 'FF' in rows and (not math.isfinite(rows['FF'][2]) or rows['FF'][2] < 0 or rows['FF'][3] != 0):
        failures.append(f'FF hold {rows["FF"][2]} / {rows["FF"][3]} endpoints')
    return failures


if __name__ == '__main__':
    try:
        failures = gate(sys.argv[1] if len(sys.argv) > 1 else '/work')
    except (OSError, ValueError, IndexError) as exc:
        failures = [str(exc)]
    print('RP1_GATE ' + ('FAIL: ' + '; '.join(failures) if failures else 'PASS TT setup / FF hold / exhaustive TT+FF pair <=80ps'))
    sys.exit(bool(failures))
