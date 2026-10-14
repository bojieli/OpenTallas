#!/usr/bin/env python3
"""Count generic synthesized FFs by actual top clock port; no physical qualification."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def census(path):
    raw = path.read_bytes()
    design = json.loads(raw)
    tops = [m for m in design['modules'].values()
            if int(str(m.get('attributes', {}).get('top', '0')), 2) == 1]
    if len(tops) != 1:
        raise ValueError(f'Expected one synthesized top, found {len(tops)}')
    top = tops[0]
    clocks = {bit: f'{name}[{index}]'
              for name, port in top['ports'].items()
              if 'clk' in name or name in ('ck', 'clock')
              for index, bit in enumerate(port['bits'])}
    counts = collections.Counter()
    unknown = []
    for name, cell in top['cells'].items():
        if 'DFF' not in cell['type']:
            continue
        conn = cell['connections']
        clock = conn.get('C', conn.get('CLK', []))
        if len(clock) != 1 or clock[0] not in clocks:
            unknown.append({'cell': name, 'type': cell['type'], 'clock_bits': clock})
            continue
        counts[clocks[clock[0]]] += len(conn['Q'])
    return {'netlist_sha256': hashlib.sha256(raw).hexdigest(),
            'generic_flipflops_by_clock': dict(sorted(counts.items())),
            'total_classified_flipflops': sum(counts.values()),
            'unclassified_ff': unknown,
            'scope': 'Generic synthesis clock/state census only; blackboxed child bodies excluded. No measured outline, clock span, insertion, timing or physical qualification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist', type=Path)
    args = parser.parse_args()
    print(json.dumps(census(args.netlist), indent=2))
