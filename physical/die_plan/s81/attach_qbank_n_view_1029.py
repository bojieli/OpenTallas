#!/usr/bin/env python3
"""Attach the measured E1 qbank_N view after exact physical-contract checks."""
import argparse
import copy
import json
from pathlib import Path


VIEW = 'cores/views/e1_dsfd_qbank_N_1029'
MODULE = 'dsfd_qbank_N'


def attach(plan, root):
    view = Path(root) / VIEW
    receipt = json.loads((view / 'signoff.json').read_text())
    if receipt['verdict'] != 'SIGNED':
        raise ValueError('qbank_N native view must be SIGNED')
    policy = receipt['policy']
    if (policy['period_ps'], policy['uncertainty_setup_ps'], policy['uncertainty_hold_ps']) != (833, 60, 25):
        raise ValueError('qbank_N timing policy differs')
    lec = json.loads((view / 'lec_routed.json').read_text())
    if lec['verdict'] != 'EQUIVALENT':
        raise ValueError('qbank_N routed netlist is not equivalent')
    actual = {}
    for pin in json.loads((view / 'pins.json').read_text()):
        name = pin['bus'] if pin['bit'] is None else f"{pin['bus']}[{pin['bit']}]"
        actual[name] = (pin['layer'], pin['x'], pin['y'])
    out = copy.deepcopy(plan)
    count = 0
    for name, part in out['partition_types'].items():
        for core in part.get('hard_cores', []):
            if core['module'] != MODULE:
                continue
            declared = {p['name']: (p['layer'], p['x'], p['y']) for p in
                        json.loads((Path(root) / core['pins_file']).read_text())['pins']}
            if declared != actual:
                raise ValueError(f'{name}: qbank_N physical pin contract differs from SIGNED view')
            if core['outline_um'] != [60.48, 8.64]:
                raise ValueError(f'{name}: qbank_N outline differs')
            core['lib'] = f'physical/die_plan/s81/{VIEW}/{MODULE}_tt.lib'
            count += 1
    if not count:
        raise ValueError('no qbank_N hard cores in plan')
    return out, count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('out')
    args = parser.parse_args()
    result, count = attach(json.loads(Path(args.plan).read_text()), Path(__file__).resolve().parent)
    Path(args.out).write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print(f'ATTACH_QBANK_N_VIEW PASS {count} references; physical contracts/RTL/cycles unchanged')
