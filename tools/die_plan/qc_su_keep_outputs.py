#!/usr/bin/env python3
"""Preserve the already-private registered outputs in an actual SU cut.

Input is Yosys proc/flatten/memory_collect/opt_clean JSON, before opt_merge.
This changes only keep attributes. Emit the whole design (ordinary retained
reset modules included); keep SRAM instance identities and supply their BBs.
No port, state, parameter or connection may change. Dead/comb/shared ports
fail rather than gaining a fabricated register or a cycle.
"""
import argparse
import copy
import json
from pathlib import Path

FF = {'$dff', '$adff', '$dffe', '$adffe', '$sdff', '$sdffe', '$sdffce',
      '$aldff', '$aldffe', '$dffsr', '$dffsre', '$_DFF_P_', '$_DFF_N_'}
ONE = '00000000000000000000000000000001'

def semantics(x):
    if isinstance(x, dict):
        return {k: semantics(v) for k, v in x.items() if k != 'attributes'}
    if isinstance(x, list):
        return [semantics(v) for v in x]
    return x

def transform(original, top):
    out = copy.deepcopy(original)
    m = out['modules'][top]
    drivers, loads, uses = {}, {}, {}
    for name, c in m['cells'].items():
        for port, bits in c['connections'].items():
            for i, bit in enumerate(bits):
                if c.get('port_directions', {}).get(port) == 'output':
                    drivers[bit] = (name, port, i)
                else:
                    loads.setdefault(bit, []).append((name, port, i))
    for name, p in m['ports'].items():
        for bit in p['bits']:
            uses.setdefault(bit, []).append(name)
    kept = []
    for name, p in m['ports'].items():
        if p['direction'] != 'output':
            continue
        for i, bit in enumerate(p['bits']):
            d = drivers.get(bit)
            if (d is None or m['cells'][d[0]]['type'] not in FF or d[1] != 'Q'
                    or loads.get(bit) or len(uses[bit]) != 1):
                raise ValueError(f'{name}[{i}] is not already a private registered output')
            m['cells'][d[0]].setdefault('attributes', {})['keep'] = ONE
            m['netnames'][name].setdefault('attributes', {})['keep'] = ONE
            kept.append(dict(pin=f'{name}[{i}]', cell=d[0], qbit=d[2]))
    if semantics(out) != semantics(original):
        raise AssertionError('output preservation changed design semantics')
    return out, dict(verdict='PASS', top=top, kept_outputs=kept, added_ff_bits=0,
                     added_cycles=0, check='all non-attribute JSON identical')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input'); p.add_argument('output'); p.add_argument('report')
    p.add_argument('--top', required=True)
    a = p.parse_args()
    out, report = transform(json.loads(Path(a.input).read_text()), a.top)
    Path(a.output).write_text(json.dumps(out))
    Path(a.report).write_text(json.dumps(report, indent=1) + '\n')

if __name__ == '__main__':
    main()
