#!/usr/bin/env python3
"""Finish a B2o geometry generation with the latest reset/clock-domain obstacle contracts.

This is a model/plan step. It does not authorize partition P&R or claim clock timing closure.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import b2m
import b2n
import b2o
import schema as S
import reset_tree as RT


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan_dir')
    args = ap.parse_args()
    out = Path(args.plan_dir)
    path = out / 'die_plan.json'
    plan = json.loads(path.read_text())
    log = []
    b2o.phy_keepouts(plan, log)
    cmap = json.loads((out / 'census_map.json').read_text())
    cmap['parts']['b2_ep1_root'] = 'root'
    (out / 'census_map.json').write_text(json.dumps(cmap, indent=1) + '\n')
    for tn, t in plan['partition_types'].items():
        if t.get('hard'):
            continue  # A hard PHY input is its actual macro interface, not a stdcell buffer site.
        taken = []
        for tp in t.get('clock', {}).get('taps', []):
            xy = S.tap_clear(t, *tp['xy'], taken, clear=4.32, strict=True)
            tp['xy'] = list(xy)
            taken.append(xy)
        for key in ('clock', 'reset'):
            if 'tap_um' in t.get(key, {}):
                t[key]['tap_um'] = list(S.tap_clear(t, *t[key]['tap_um'], taken, clear=4.32, strict=True))
    b2n.reset_wavefront(plan, log)
    clock = b2m.clock(plan, out, log)
    for t in plan['partition_types'].values():
        fb = t.get('ft_budget', {})
        for layer in ('M8', 'M9'):
            fb.pop(layer, None)
        if not fb:
            t.pop('ft_budget', None)
    plan['note'] += ' | native-finalize: PHY domain-aware clock/reset site guards; clock corridors and native HC views remain separately gated'
    path.write_text(json.dumps(plan, indent=0) + '\n')
    offsets = RT.wf_plan(S.Plan(plan))
    (out / 'reset_offsets.json').write_text(json.dumps(offsets, indent=1) + '\n')
    result = dict(log=log, clock=clock, reset_max_release=offsets['max_release'],
                  scope='PLAN/MODEL ONLY; clock metal corridor RC, native W128 hard cores and actual-bit FT hops gate separately')
    (out / 'native_finalize.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(reset_max_release=offsets['max_release'], taps=clock['taps'], drivers=clock['drivers'])))


if __name__ == '__main__':
    main()
