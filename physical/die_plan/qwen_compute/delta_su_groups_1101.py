#!/usr/bin/env python3
"""Materialize the 36 planned SU lane cores from their five exact bound leaves.

The existing exact_post_bind_group tool projects the planned lane reset onto
all original members before cutting, requires unchanged release depth/START
role, and compares the materialized module to the committed core RTL. This is
an actual zero-cycle grouping, not a module-name alias or reset exception.

Usage: delta_su_groups_1101.py PLAN [PLAN_OUT]
"""
import json
import re
import sys
from pathlib import Path


def apply(plan):
    changed = []
    for name, typ in plan['partition_types'].items():
        contents = {c['inst']: c['module'] for c in typ.get('contents', [])}
        for core in typ.get('hard_cores', []):
            if not re.fullmatch(r'qfd_qc_su_lane_[we]_l[0-7]', core['module']):
                continue
            lane = re.fullmatch(r'u_lane([0-7])', core['inst'])[1]
            members = [dict(inst='u_'+kind+lane, module=contents['u_'+kind+lane], reset_pin='rst_n')
                       for kind in ('exp', 'head', 'lrly', 'rcp', 'rsq')]
            contract = dict(kind='exact_post_bind_group', reset_pin='rst_n',
                            memory_alignment=3, kv_wr_pipe=1, members=members)
            if core.get('bound_group') != contract:
                core['bound_group'] = contract
                changed.append(name+'/'+core['inst'])
    count = sum(bool(c.get('bound_group')) for t in plan['partition_types'].values()
                for c in t.get('hard_cores', [])
                if re.fullmatch(r'qfd_qc_su_lane_[we]_l[0-7]', c['module']))
    if count != 36:
        raise ValueError(f'expected 36 planned SU lane cores, found {count}')
    return changed


def main():
    src = Path(sys.argv[1]); dst = Path(sys.argv[2]) if len(sys.argv)>2 else src
    plan = json.loads(src.read_text()); changed = apply(plan)
    dst.write_text(json.dumps(plan)+'\n')
    print(json.dumps(dict(changed=len(changed), cores=changed, added_cycles=0)))


if __name__ == '__main__':
    main()
