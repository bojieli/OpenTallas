#!/usr/bin/env python3
"""Count actual flattened FEC flop bits by their delivered clock input.

This is source sizing evidence, never CTS, area, pin or phase qualification.
Run proc/opt/memory_map/flatten before exporting the Yosys JSON. Unknown
clock producers, latches and residual memory cells fail closed.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

SEQUENTIAL = {'$dff', '$dffe', '$adff', '$adffe', '$sdff', '$sdffe',
              '$sdffce', '$aldff', '$aldffe', '$dffsr', '$dffsre'}


def census(netlist, top, clocks):
    module = netlist['modules'][top]
    clock_bits = {}
    for name in clocks:
        port = module['ports'][name]
        if port['direction'] != 'input' or len(port['bits']) != 1:
            raise ValueError('delivered clock must be a scalar input: ' + name)
        bit = port['bits'][0]
        if not isinstance(bit, int) or bit in clock_bits:
            raise ValueError('clock input has a constant or aliased bit: ' + name)
        clock_bits[bit] = name
    counts, cells = Counter(), Counter()
    for name, cell in module['cells'].items():
        kind = cell['type']
        cells[kind] += 1
        if kind in SEQUENTIAL:
            clock = cell['connections']['CLK']
            if len(clock) != 1 or clock[0] not in clock_bits:
                raise ValueError('flop clock is not a declared delivered input: ' + name)
            counts[clock_bits[clock[0]]] += len(cell['connections']['Q'])
        elif kind in {'$ff', '$sr', '$fsm', '$anyseq', '$anyconst'} or any(
                x in kind.lower() for x in ('latch', 'mem', 'dff', 'ffsr')):
            raise ValueError('unsupported state cell: ' + name + ' ' + kind)
        elif not kind.startswith('$'):
            raise ValueError('unflattened or black-box module: ' + name + ' ' + kind)
    missing = sorted(set(clocks) - counts.keys())
    if missing:
        raise ValueError('declared clock owns no flop bits: ' + ', '.join(missing))
    return dict(schema='ot.hbm.fec.clock_census.v1', top=top,
                scope='ACTUAL_FLATTENED_FLOP_SIZING_ONLY', native_qualified=False,
                clock_flop_bits=dict(sorted(counts.items())),
                total_flop_bits=sum(counts.values()), maximum_root_bits=max(counts.values()),
                cells_by_type=dict(sorted(cells.items())),
                measured_cts_exception_required=any(n > 15000 for n in counts.values()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--netlist', required=True, type=Path)
    ap.add_argument('--top', required=True)
    ap.add_argument('--clock', action='append', required=True)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    result = census(json.loads(a.netlist.read_text()), a.top, a.clock)
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('total_flop_bits', 'maximum_root_bits',
                                           'measured_cts_exception_required')}))


if __name__ == '__main__':
    main()
