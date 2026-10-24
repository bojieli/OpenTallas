#!/usr/bin/env python3
"""ELEM-HBM/SPLIT2: collect the per-module sw2.py reports into results/split_wrappers_b2l.json.

    python3 collect_results.py [--work DIR] [--gen RC_FILE]

verdict per module: PASS = wrapper built, miter PASS (equivalence proven) AND the mutant control FAILs (caught);
otherwise FAIL / NOT_BUILT with the reason.  Failed verdicts already recorded are kept under history (never
overwritten).  --gen adds the generator rc per view (lines '<rc> <view>').
"""
import argparse
import datetime
import glob
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
HAC = os.path.dirname(HERE)
OUT = os.path.join(HAC, 'results', 'split_wrappers_b2l.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default='/srv/opentallas-scratch/claude/elem-hbm/split2/work')
    ap.add_argument('--gen', default='')
    a = ap.parse_args()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    hist = old.get('history', [])
    mods = {}
    for f in sorted(glob.glob(os.path.join(a.work, '*', 'reports', '*.json'))):
        r = json.load(open(f))
        m = r['module']
        mi, mu = r.get('miter') or {}, r.get('mutant') or {}
        if r.get('verdict') == 'NOT_BUILT' or 'error' in r:
            v = 'NOT_BUILT'
        elif mi.get('verdict') == 'PASS' and mu.get('caught'):
            v = 'PASS'
        elif mi.get('verdict') == 'PASS':
            v = 'INCOMPLETE (mutant control not caught)' if mu else 'INCOMPLETE (no mutant control)'
        else:
            v = 'FAIL'
        row = dict(verdict=v, family=r['family'], kind=r.get('kind'), views=r.get('views'),
                   wrapper=f'physical/die_plan/hbm_arch_cores/wrappers/{m}.sv' if v != 'NOT_BUILT' else None,
                   bit_map=f'physical/die_plan/hbm_arch_cores/results/split_wrappers_b2l/{m}.map.json'
                   if v != 'NOT_BUILT' else None,
                   canonical_top=r.get('canonical_top'), master_twin=r.get('twin'), master_params=r.get('params'),
                   include=r.get('include'), exclude=r.get('exclude'), plan_buses=r.get('plan_buses'),
                   plan_bits=r.get('plan_bits'), pins_tables=r.get('pins_tables'),
                   portset_mismatch=r.get('portset_mismatch'), merged_ff_bits=r.get('merged_ff_bits'),
                   dead_bits=r.get('dead_bits'), tied_canonical_bits=r.get('n_tied'),
                   open_canonical_bits=r.get('open_canonical_bits'),
                   unread_plan_inputs=r.get('n_unread_plan_inputs'), member_checks=r.get('member_checks'),
                   miter=dict(verdict=mi.get('verdict'), equiv_cells=mi.get('equiv_cells'),
                              unproven=mi.get('unproven'), notes=mi.get('notes'), cmd=mi.get('cmd'),
                              unproven_e_g=mi.get('unproven_e_g')) if mi else None,
                   mutant=dict(swap=mu.get('swap'), verdict=mu.get('verdict'), unproven=mu.get('unproven'),
                               caught=mu.get('caught'), dir=mu.get('dir')) if mu else None,
                   error=r.get('error'), problems=r.get('problems'))
        prev = (old.get('modules') or {}).get(m)
        if prev and prev.get('verdict') not in ('PASS', None) and prev != row:
            hist.append(dict(module=m, superseded=prev, at=old.get('generated')))
        mods[m] = row
    gen = {}
    if a.gen and os.path.exists(a.gen):
        for ln in open(a.gen):
            p = ln.split()
            if len(p) >= 2:
                gen[p[1]] = int(p[0])
        for m, row in mods.items():
            row['generator_rc'] = {v: gen.get(v) for v in (row.get('views') or [])}
    head = subprocess.run(['git', '-C', HAC, 'rev-parse', '--short=10', 'HEAD'], capture_output=True, text=True).stdout.strip()
    res = dict(schema='ELEM-HBM/SPLIT2 B2l split-piece wrapper exactness: per plan module, the wrapper (pure wiring '
                      'plan pins -> canonical piece top) proven equivalent to the master piece it was cut from',
               method='physical/die_plan/hbm_arch_cores/split/sw2.py docstring (yosys equiv_make/equiv_simple -seq 4/'
                      'equiv_induct -seq 4 of gold = master twin piece with plan pins on the netcut nets vs gate = '
                      'wrapper + canonical top; mutant = two plan input bits swapped must FAIL)',
               plan='physical/die_plan/hbm_arch/B2l/die_plan.json', views='physical/die_plan/hbm_arch_cores/views_b2l.json',
               tool_commit=head, generated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               summary={k: sum(1 for r in mods.values() if r['verdict'].split()[0] == k)
                        for k in ('PASS', 'FAIL', 'NOT_BUILT', 'INCOMPLETE')},
               modules=dict(sorted(mods.items())), history=hist)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), indent=1)
    print(json.dumps(res['summary']))


if __name__ == '__main__':
    main()
