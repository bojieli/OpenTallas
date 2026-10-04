#!/usr/bin/env python3
"""Collect the full-shape DSpark speculative step (tools/qwen_dspark_step_plans.py jobs run by
tools/qwen_rom_rt_vprm_w12.py) into one record: exactness, draft / verify / commit cycles, AR baseline,
per-user accepted tok/s at the acceptance mix.

Measured (RTL, REAL_MEM path, P and P' of the golden): verify = sum of the 36 S1 layer stages + the p = 4
verify head H1; AR = sum of the 36 AR layer stages + the p = 1 head H0; commit = accept unit (head done to
acc_done) + the host commit the KV service registers (its write-done precondition is the layers' own drain,
inside the layer cycles); drafter layers D0..D4 at S = 3 (the packed drafter program).
Not in RTL, priced and labelled: the drafter's context ingest (fc 20,480 -> 4,096 + row all-gather + hidden
norm + 5 layers' context K/V for the a+1 committed tokens), its shared lm_head over S slots and the Markov
epilogue.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

F_HZ = 1.2e9


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--res', type=Path, required=True, help='dir of <job>.json results')
    ap.add_argument('--jobs', type=Path, required=True)
    ap.add_argument('--drafter-res', type=Path, help='dir of drafter_D<n>.json')
    ap.add_argument('--tau', type=float, required=True, help='mean committed tokens per step at the mix (incl. bonus)')
    ap.add_argument('--tau-source', required=True)
    ap.add_argument('--draft-unmeasured', type=json.loads, required=True, help='{"term": cycles, ...} priced parts')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    J = json.loads(a.jobs.read_text())
    L = sum(1 for k in J['jobs'] if k.startswith('L'))
    R = {k: json.loads((a.res / f'{k}.json').read_text()) for k in J['jobs'] if (a.res / f'{k}.json').exists()}
    missing = sorted(set(J['jobs']) - set(R))
    st = lambda job, stage: R[job]['stages'][stage]['cycles']  # noqa: E731
    exact = {k: r['status'] == 'pass' for k, r in R.items()}
    verify = sum(st(f'L{n}', f'S1L{n}') for n in range(L)) + st('H1', 'H1')
    verify2 = sum(st(f'L{n}', f'S2L{n}') for n in range(L)) + st('H2', 'H2')
    ar = sum(st(f'AR{n}', f'ARL{n}') for n in range(L)) + st('H0', 'H0')
    acc = R['H1']['accept']
    drafter = {}
    if a.drafter_res:
        for n in range(5):
            p = a.drafter_res / f'drafter_D{n}.json'
            if p.exists():
                d = json.loads(p.read_text())
                drafter[f'D{n}'] = {'cycles': d['stages'][f'D{n}']['cycles'], 'exact': d['status'] == 'pass'}
    draft_meas = sum(v['cycles'] for v in drafter.values())
    draft_priced = sum(a.draft_unmeasured.values())
    commit = None
    step = draft_meas + draft_priced + verify
    rec = {'schema': 'opentallas.qwen-dspark-step.v1', 'P': J['P'], 'P2': J['P2'], 'a': J['a'], 'missing_jobs': missing,
           'exact': exact, 'all_exact': all(exact.values()) and not missing,
           'verify_cycles_step1': verify, 'verify_cycles_step2': verify2, 'ar_token_cycles': ar,
           'verify_layers_step1': [st(f'L{n}', f'S1L{n}') for n in range(L)],
           'ar_layers': [st(f'AR{n}', f'ARL{n}') for n in range(L)], 'heads': {h: st(h, h) for h in ('H0', 'H1', 'H2')},
           'accept_rtl': acc, 'drafter_layers_rtl': drafter, 'draft_cycles_measured': draft_meas,
           'draft_cycles_priced': a.draft_unmeasured, 'draft_cycles_total': draft_meas + draft_priced,
           'step_cycles': step, 'tau': a.tau, 'tau_source': a.tau_source, 'clock_hz': F_HZ,
           'per_user_tok_s': a.tau * F_HZ / step, 'ar_tok_s': F_HZ / ar, 'speedup': a.tau * ar / step}
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('all_exact', 'verify_cycles_step1', 'ar_token_cycles', 'draft_cycles_total',
                                          'step_cycles', 'per_user_tok_s', 'ar_tok_s', 'speedup')}, indent=1))


if __name__ == '__main__':
    main()
