#!/usr/bin/env python3
"""Compose the Qwen3-8B ROM DSpark speculative step from its MEASURED RTL components (owner rule: simulate the
minimum component, compose analytically; no full 36-layer speculative runs).

Components (tools/qwen_rom_rt_vprm_w12.py results, VPRM REAL_MEM die, each bit-exact against the GPU ISA golden):
  c_L0   decoder layer 0: verify block P..P+3 (S1), host commit of a+1, verify block P'..P'+3 over the HBM the RTL
         left (S2) -- the multi-position KV service and accept / rollback on one layer
  c_AR0  decoder layer 0, AR (p = 1) at P on the same path (the baseline)
  c_H0   lm_head p = 1; c_H1 / c_H2 the p = 4 verify heads with the accept unit
  c_D0   drafter layer 0 (the packed DSpark drafter program, S = 3)
Composition (analytical, labelled): verify = 36 x S1(L0) + H1; AR token = 36 x AR(L0) + H0; draft = 5 x D0 +
drafter lm_head over S slots (linear in the measured p = 1 and p = 4 heads) + PRICED context ingest and Markov
epilogue (not in RTL; tools/qwen_rom_dspark_drafter_rom.py model); commit = the accept unit's RTL cycles after the
head plus the KV service's one-cycle commit (the K/V write-done it requires is inside every layer's cycles).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

F_HZ = 1.2e9


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--res', type=Path, required=True)
    ap.add_argument('--runs', type=Path, required=True, help='run dirs (token.log of the heads for accept timing)')
    ap.add_argument('--tau', type=float, default=None,
                    help='override; default = the published third-party Qwen3-8B tau at --slots draft tokens '
                         '(tools/third_party_tau.py; OT_TAU_SOURCE=self_measured gives the superseded 3.0375)')
    ap.add_argument('--tau-source', default=None)
    ap.add_argument('--priced', type=json.loads, required=True, help='{"ingest": c, "markov": c} with their source')
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--drafter-layers', type=int, default=5)
    ap.add_argument('--slots', type=int, default=3)
    ap.add_argument('--drafter-job', default='c_D0', help='result name of the drafter-layer run')
    ap.add_argument('--map', type=json.loads, default={}, help='role -> result/run name, e.g. {"c_L0": "k_L0"} (target-context jobs)')
    ap.add_argument('--claim-boundary', help='replaces the default (P = 255) claim boundary')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    superseded = None
    if a.tau is None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import third_party_tau as tpt
        a.tau = tpt.tau_qwen3_8b(a.slots)
        a.tau_source = a.tau_source or tpt.tau_src('qwen3_8b', a.slots)
        superseded = tpt.SUPERSEDED['qwen3_8b'] if a.tau != tpt.SUPERSEDED['qwen3_8b']['tau'] else None
    elif a.tau_source is None:
        ap.error('--tau needs --tau-source')
    if a.drafter_job != 'c_D0':
        a.map.setdefault('c_D0', a.drafter_job)
    nm = lambda k: a.map.get(k, k)  # noqa: E731
    R = {k: json.loads((a.res / f'{nm(k)}.json').read_text()) for k in ('c_L0', 'c_AR0', 'c_H0', 'c_H1', 'c_H2', 'c_D0')}
    cyc = lambda k, s: R[k]['stages'][s]['cycles']  # noqa: E731
    s1, s2, ar, h0, h1, h2, d0 = (cyc('c_L0', 'S1L0'), cyc('c_L0', 'S2L0'), cyc('c_AR0', 'ARL0'), cyc('c_H0', 'H0'),
                                  cyc('c_H1', 'H1'), cyc('c_H2', 'H2'), cyc('c_D0', 'D0'))
    # the accept unit starts on the last head stage's done; the host clocks at most ACCEPT_WINDOW more edges for it
    # (qwen_rom_rt_w12_vprm.cpp), so an ACCEPT line printed after the stage bounds its latency by that window
    ACCEPT_WINDOW = 64
    acc_lat = {}
    for h in ('c_H1', 'c_H2'):
        t = (a.runs / nm(h) / 'token.log').read_text()
        end = int(re.search(r'STAGE \S+ done .*?end_cyc=(\d+)', t).group(1))
        accs = [int(m.group(1)) for m in re.finditer(r'ACCEPT die=\d .*?cyc=(\d+)', t)]
        acc_lat[h] = (max(accs) - end) if accs else (ACCEPT_WINDOW if 'ACCEPT die=' in t else None)
    head_per_pos = (h1 - h0) / 3
    draft_head = h0 + (a.slots - 1) * head_per_pos
    draft_meas = a.drafter_layers * d0
    draft = draft_meas + draft_head + sum(v for k, v in a.priced.items() if k != 'source')
    commit = max(v for v in acc_lat.values() if v is not None) + 1
    verify = a.layers * s1 + h1
    ar_tok = a.layers * ar + h0
    step = draft + verify + commit
    rec = {
        'schema': 'opentallas.qwen-dspark-step-composed.v1',
        'exact': {k: r['status'] == 'pass' for k, r in R.items()},
        'outputs_bit_exact': {k: bool(r['checks']) and all(c['mismatches'] == 0 for c in r['checks'].values()) or
                              (k in ('c_H0', 'c_H1', 'c_H2') and r['tokens_ok']) for k, r in R.items()},
        'faults': {k: re.findall(r'STAGE (\S+) done .*?seq_fault=(\d+) core_fault=(\d+) coll_fault=(\d+)',
                                 (a.runs / nm(k) / 'token.log').read_text()) for k in R},
        'fault_trace': {k: re.findall(r'FAULTTRACE .*', (a.runs / nm(k) / 'token.log').read_text())
                        for k in R},
        'components_cycles': {'verify_layer_L0_step1_P': s1, 'verify_layer_L0_step2_Pprime': s2, 'ar_layer_L0_P': ar,
                              'head_p1': h0, 'verify_head_p4_step1': h1, 'verify_head_p4_step2': h2,
                              'drafter_layer_D0_S3': d0, 'accept_after_head': acc_lat},
        'memory_stalls': {k: R[k]['stages'] for k in ('c_L0', 'c_AR0', 'c_D0')},
        'accept_rtl': {k: R[k]['accept'] for k in ('c_H1', 'c_H2')},
        'commits': R['c_L0']['commits'],
        'composed': {'verify_cycles': verify, 'ar_token_cycles': ar_tok,
                     'draft_cycles': draft, 'draft_terms': {'drafter_layers_rtl': draft_meas,
                                                            'drafter_lm_head_S_slots_from_measured_heads': draft_head,
                                                            'priced_not_rtl': a.priced},
                     'commit_cycles': commit, 'step_cycles': step},
        'bounds': {
            'verify_layer_increment_per_extra_position': (s1 - ar) / 3,
            'speedup_if_draft_were_free': a.tau * ar_tok / (verify + commit),
            # verify layer cycles at which the composed step only breaks even / gains the owner's 1% (draft, head, commit as measured)
            'verify_layer_cycles_break_even': (a.tau * ar_tok - draft - h1 - commit) / a.layers,
            'verify_layer_cycles_for_1pct_gain': (a.tau * ar_tok / 1.01 - draft - h1 - commit) / a.layers,
            'drafter_su_serial_stall_cycles_per_layer': R['c_D0']['stages']['D0']['memory']['die0']['stall_bridge'],
        },
        'tau': a.tau, 'tau_source': a.tau_source, **({'tau_superseded': superseded} if superseded else {}), 'clock_hz': F_HZ,
        'per_user_accepted_tok_s': a.tau * F_HZ / step, 'ar_tok_s': F_HZ / ar_tok, 'speedup_vs_ar': a.tau * ar_tok / step,
        'jobs': {k: nm(k) for k in R},
        'claim_boundary': a.claim_boundary or ('Layer, head and drafter-layer cycles measured on the VPRM REAL_MEM RTL at P=255 (in-tile KV slices, '
                           'not near-HBM attention); 36- and 5-layer totals composed from layer 0; drafter context ingest and '
                           'Markov epilogue priced (model), not RTL; no SS/FF closure of the new logic.'),
    }
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('outputs_bit_exact', 'components_cycles', 'composed', 'bounds', 'per_user_accepted_tok_s',
                                          'ar_tok_s', 'speedup_vs_ar')}, indent=1))


if __name__ == '__main__':
    main()
