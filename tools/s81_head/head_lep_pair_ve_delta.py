#!/usr/bin/env python3
"""DIE-HEAD-77-LEP2: attach the SIGNED LEP pair vE views (clk moved to the S face) to hd_lep0N, plus 4 early core taps.

Why: hd_lep0N fails because CTS reaches the four pair clk pins, which sat in the pair interior at (388.92, 246.24), only
through long leads: tap insertion 1251 ps against a 450 ps target, hold -850. vE (COORD 15:0x RE-FORM) has the same
netlist and CTS tree with clk on the S face M5 (397.464, 0.24), which faces the hd_lep0N middle street in all 4 placements.

Changes, hd_lep0N only:
  1. hard_cores[ot_s81hd_lep_pair].lef / lib -> VIEW (detailed LEF: the plain abstract fails DRT-0073);
  2. clock.core_taps = 'early' and clock.taps = one core tap per pair beside the transformed vE clk pin (schema.tap_clear
     picks the nearest channel off the TX banks, 6-43 um from the pin), insertion = SIGNED TT pin-register mean from
     VIEW/clock_contract.json (early_core_taps.add_from_means).
  3. The clk pin on a face is an exception to METHODOLOGY 12.8a (COORD 15:0x), recorded in each pair's note.

Not changed: pin tables, outlines, origins, RTL, cycles, die nets, sidecar, clock.insertion_ps (450; vE pair TT mean is 529).

usage: head_lep_pair_ve_delta.py PLAN OUT --root REPO_ROOT
"""
import argparse
import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
import early_core_taps as E  # noqa: E402

TYPE = 'hd_lep0N'
MODULE = 'ot_s81hd_lep_pair'
VIEW = 'results/head_lep_pair_views_vE_1106/' + MODULE
EXPECT = {'u_core.u.g_pp[0].u_pair': (1278.744, 509.52), 'u_core.u.g_pp[1].u_pair': (466.584, 665.52),
          'u_core.u.g_pp[2].u_pair': (466.584, 509.52), 'u_core.u.g_pp[3].u_pair': (1261.416, 665.52)}
NOTE = ('DIE-HEAD-77-LEP2: SIGNED vE view, clk on the S face M5 (397.464,0.24); exception to METHODOLOGY 12.8a '
        '(COORD 15:0x RE-FORM). Parent must use this detailed LEF.')


def apply(plan, root):
    out = copy.deepcopy(plan)
    if out.get('die', {}).get('name') != 's81_head':
        raise ValueError('HEAD plan required')
    t = out['partition_types'][TYPE]
    cores = [c for c in t.get('hard_cores', []) if c.get('module') == MODULE]
    if len(cores) != 4:
        raise ValueError('expected exactly four LEP pair children')
    if t['clock'].get('taps') or t['clock'].get('core_taps'):
        raise ValueError(TYPE + ' already declares core taps: review explicitly')
    for c in cores:
        if c.get('outline_um') != [777.6, 492.48]:
            raise ValueError('vE is for the exact 777.6 x 492.48 child')
        c['lef'] = VIEW + '.lef'
        c['lib'] = VIEW + '_tt.lib'
        c['note'] = (c.get('note', '') + ' | ' + NOTE).lstrip(' |')
    taps = E.add_from_means(t, modules={MODULE}, root=root)
    got = {x['name'].rsplit('.', 1)[0]: tuple(x['xy']) for x in taps}
    if len(taps) != 4 or set(got) != set(EXPECT):
        raise ValueError(f'expected 4 pair taps, got {sorted(got)}')
    for k, xy in EXPECT.items():
        if max(abs(a - b) for a, b in zip(got[k], xy)) > 50.0:  # tap_clear steps off TX banks into the nearest channel (6-43 um)
            raise ValueError(f'{k}: tap {got[k]} is far from the vE clk pin {xy}')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--root', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        ap.error('fresh output required')
    out = apply(json.loads(a.plan.read_text()), a.root)
    for typ in out['partition_types'].values():  # pin tables stay those of the supplied plan
        for c in typ.get('hard_cores', []):
            if c.get('pins_file'):
                f = (a.plan.parent / c['pins_file']).resolve()
                if f.is_file():
                    c['pins_file'] = os.path.relpath(f, a.out.parent.resolve())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    for x in out['partition_types'][TYPE]['clock']['taps']:
        print('TAP', x['name'], x['xy'], x['insertion_ps'])
    print('HEAD_LEP_PAIR_VE_DELTA 4 views, 4 early taps; 0 geometry/RTL/cycle changes')


if __name__ == '__main__':
    main()
