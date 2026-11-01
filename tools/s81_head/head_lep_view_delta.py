#!/usr/bin/env python3
"""Attach the existing SIGNED 777.6 x 492.48 LEP child views; no geometry or RTL change."""
import argparse
import copy
import json
import os
from pathlib import Path

MODULE = 'ot_s81hd_lep_pair'
VIEW = 'results/head_lep_pair_views_1101/' + MODULE


def apply(plan):
    out = copy.deepcopy(plan)
    if out.get('die', {}).get('name') != 's81_head':
        raise ValueError('HEAD plan required')
    cores = [c for c in out['partition_types']['hd_lep0N'].get('hard_cores', []) if c.get('module') == MODULE]
    if len(cores) != 4:
        raise ValueError('expected exactly four LEP pair children')
    for core in cores:
        if core.get('outline_um') != [777.6, 492.48]:
            raise ValueError('view is for the exact 777.6 x 492.48 signed child')
        if Path(core.get('pins_file', '')).name != 'lep_pair_pins_777.json':
            raise ValueError('selected child pin table must be the 777-um form')
        if core.get('lef') not in (None, VIEW + '.lef') or core.get('lib') not in (None, VIEW + '_tt.lib'):
            raise ValueError('a different selected view must be reviewed explicitly')
        core['lef'] = VIEW + '.lef'
        core['lib'] = VIEW + '_tt.lib'
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('fresh output required')
    out = apply(json.loads(args.plan.read_text()))
    # Pin tables belong to the supplied plan, even for an external prepared cohort.
    for typ in out['partition_types'].values():
        for core in typ.get('hard_cores', []):
            if core.get('pins_file'):
                asset = (args.plan.parent / core['pins_file']).resolve()
                if not asset.is_file():
                    raise ValueError('missing actual pin table: ' + str(asset))
                core['pins_file'] = os.path.relpath(asset, args.out.parent.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + '\n')
    print('HEAD_LEP_VIEW_DELTA 4 child references; 0 geometry/RTL/cycle changes')


if __name__ == '__main__':
    main()
