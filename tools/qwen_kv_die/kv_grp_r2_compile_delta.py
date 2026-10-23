#!/usr/bin/env python3
"""KDIE5-RTL 10-22: the KV static schedule with and without the r2 group successors (OT_KV_GRP_R2), on one die's ages.

    OT_KV_GRP_R2=0|1 python3 tools/qwen_kv_die/kv_grp_r2_compile_delta.py --ages <run>/die_ages_fwd.json --out X.json [--no-mu]

Runs kv_static_programme.compile_all(profile('die', ages)) and records what the r2 deltas move: the group launch age
(profile groups), the K / V go events and leads, every group's landing / front calendar constants (H0, XU, paces), the
phase-launch legality of every launch, the ownership roots (leave), the attention calendar samples and the token cycles.
--no-mu: the 4-user frame images (mu_images, kv_frame_search) are skipped -- the release point's frame search currently
fails on main for BOTH settings (lanes/KV-PROG17 blocker 3), so the delta is recorded on the single-user compile and the
record says so.  Run it twice (0 / 1) and diff, or use --compare A.json B.json.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools/qwen_kv_die'))


def run(a):
    from tools.qwen_kv_die import kv_static_programme as P
    if a.no_mu:
        P.MU = False
    ages = json.loads(Path(a.ages).read_text())
    pr = P.profile('die', ages)
    r = P.compile_all(pr, 0x0b0b)
    if a.write:
        P.write(r, Path(a.write))      # the full compiled die directory (report.json for run_phase_launch_token.py)
    ph = r.get('phase') or {}
    rec = dict(schema='opentallas.kdie5_rtl.grp_r2_compile_delta.v1', grp_r2=os.environ.get('OT_KV_GRP_R2', '0'),
               mu_images='skipped (--no-mu)' if a.no_mu else 'compiled', ages=str(a.ages),
               groups_age=pr['groups'], cal_deltas_grp_r2=r['cal_deltas'].get('grp_r2'),
               leads=r['leads'], link=r['link'], ownership=r['ownership'],
               groups={k: {kk: v[kk] for kk in ('H0_front', 'H0_landing', 'XU', 'K', 'V')} for k, v in r['groups'].items()},
               phase=dict(outside_window=len(ph.get('outside_window', []) or []) if ph else None,
                          keys=sorted(ph) if ph else None),
               attention={k: r['attention'][k] for k in ('compiled_rx_cmd', 'compiled_tx_first', 'compiled_end', 'service_end')},
               attention_samples={T: s['fields'] for T, s in r['attention']['samples'].items()})
    Path(a.out).write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps(dict(grp_r2=rec['grp_r2'], groups_age=rec['groups_age'], kgo_event=r['leads'].get('kgo_event'),
                          lead_k=r['leads'].get('k'), lead_v=r['leads'].get('v'), own=r['ownership'].get('words', [])[:3],
                          phase_outside=rec['phase']['outside_window'], token_cycles=r['link']['token_cycles'])))


def compare(a, b):
    A, B = (json.loads(Path(x).read_text()) for x in (a, b))
    out = {}
    for k in ('groups_age', 'leads', 'link', 'ownership', 'phase', 'attention', 'attention_samples'):
        if A[k] != B[k]:
            out[k] = dict(base=A[k], r2=B[k]) if not isinstance(A[k], dict) else \
                {kk: dict(base=A[k].get(kk), r2=B[k].get(kk)) for kk in sorted(set(A[k]) | set(B[k])) if A[k].get(kk) != B[k].get(kk)}
    gd = {g: {kk: (A['groups'][g][kk], B['groups'][g][kk]) for kk in A['groups'][g] if A['groups'][g][kk] != B['groups'][g][kk]}
          for g in A['groups']}
    out['groups_changed'] = {g: v for g, v in gd.items() if v}
    print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ages')
    ap.add_argument('--out')
    ap.add_argument('--no-mu', action='store_true')
    ap.add_argument('--write', help='also write the compiled programme directory (kv_static_programme.write)')
    ap.add_argument('--compare', nargs=2)
    a = ap.parse_args()
    compare(*a.compare) if a.compare else run(a)
