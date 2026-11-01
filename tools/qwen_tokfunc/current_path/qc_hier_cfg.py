#!/usr/bin/env python3
"""Emit Verilator partition boundaries for the functional whole-QC vehicle.

Glue stays visible to the package-boundary bring-up driver. Other partition
masters compile independently; the bound die connectivity is unchanged.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
from bind_smoke import parse_top


def emit(top, output):
    _, instances = parse_top(top)
    if not instances:
        raise ValueError('bound top contains no partition instances')
    flat = {item['module'] for item in instances if item['name'] == 'glue'}
    if len(flat) != 1:
        raise ValueError('expected exactly one glue partition master')
    modules = sorted({item['module'] for item in instances} - flat)
    if not modules:
        raise ValueError('no independent partition masters found')
    output.write_text('`verilator_config\n' + ''.join(
        f'hier_block -module "{module}"\n' for module in modules))
    return dict(instances=len(instances), hierarchical_masters=len(modules),
                flat_masters=sorted(flat), scope='Functional compilation partitioning only; no die RTL changes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--top', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(emit(args.top, args.out), sort_keys=True))
