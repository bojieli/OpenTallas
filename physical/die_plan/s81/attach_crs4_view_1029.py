#!/usr/bin/env python3
"""Attach the measured SIGNED crs4 libraries without changing physical contracts."""
import argparse
import copy
import json
from pathlib import Path


def attach(plan, root):
    view = root / 'cores/views/crs4_signed_1029'
    receipt = json.loads((view / 'signoff.json').read_text())
    if receipt['verdict'] != 'SIGNED':
        raise ValueError('crs4 view must be SIGNED')
    lec = json.loads((view / 'lec_post.json').read_text())
    if lec['verdict'] != 'EQUIVALENT':
        raise ValueError('crs4 routed netlist must be EQUIVALENT')
    policy = receipt['policy']
    if (policy['period_ps'], policy['uncertainty_setup_ps'], policy['uncertainty_hold_ps']) != (833, 60, 25):
        raise ValueError('crs4 timing policy differs')
    actual = {}
    for pin in json.loads((view / 'pins.json').read_text()):
        name = pin['bus'] if pin['bit'] is None else f"{pin['bus']}[{pin['bit']}]"
        actual[name] = (pin['layer'], pin['x'], pin['y'])
    out = copy.deepcopy(plan)
    count = 0
    for name, part in out['partition_types'].items():
        for core in part.get('hard_cores', []):
            if core['module'] != 'dsfd_cfifo_crs4':
                continue
            declared = {p['name']: (p['layer'], p['x'], p['y']) for p in
                        json.loads((root / core['pins_file']).read_text())['pins']}
            if declared != actual:
                raise ValueError(f'{name}: crs4 physical pin contract differs from SIGNED view')
            if core['outline_um'] != [280.8, 69.12]:
                raise ValueError(f'{name}: crs4 outline differs')
            core['lib'] = 'physical/die_plan/s81/cores/views/crs4_signed_1029/dsfd_cfifo_crs4_tt.lib'
            count += 1
    if not count:
        raise ValueError('no crs4 hard cores in plan')
    return out, count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('out')
    args = parser.parse_args()
    result, count = attach(json.loads(Path(args.plan).read_text()), Path(__file__).resolve().parent)
    Path(args.out).write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print(f'ATTACH_CRS4_VIEW PASS {count} references; geometry/pins/clock/RTL/cycles unchanged')
