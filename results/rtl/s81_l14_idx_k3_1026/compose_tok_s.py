#!/usr/bin/env python3
"""TOK-DS-6 (COORD RULING TOK-DS-6, owner 10-15 floor S81 MTP > 3,000 tok/s): S81 AR / MTP tok/s with ALL accepted +
proposed (non-superseded) ledger rows.  Composition = base token-path cycles + the sum of every row's added cycles per
workload (each row priced by accepted_cost.py against the base DAG; MTP wave terms on the base worst verify stage S029).
Rows without an MTP pricing are priced here with accepted_cost.py compute (SVC.ROWS_INGRESS A/B: rows_allgather) or are
0 / lookahead (ENGRAM, HEADB4_GO, PV_DRAIN gain counted 0).  usage: compose_tok_s.py (run from the repo root)"""
import json
import subprocess
import sys

L = json.load(open('results/arch/accepted_cost_ledger_1013.json'))
TP = {w: json.load(open(f'results/arch/token_path_20261009/{f}.json'))['totals'] for w, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp'))}
EXTRA = {'SVC.ROWS_INGRESS.A': ('(^|\\.)L(2|8|14|20)\\.attn\\.rows_allgather$', 1032.9, 3809.0),
         'SVC.ROWS_INGRESS.B': ('(^|\\.)L(24|28|32|36)\\.attn\\.rows_allgather$', 1024.0, 3809.0)}
rows = [r for r in L['rows'] if r['design'] == 's81' and r['status'] != 'superseded']
out = dict(rows=len(rows), per_row={}, workloads={})
for wl in ('ar', 'mtp'):
    add, add_acc = 0.0, 0.0
    for r in rows:
        p = r.get('per_workload', {}).get(wl)
        if p is None and r['group'] in EXTRA:
            m, pr, me = EXTRA[r['group']]
            p = json.loads(subprocess.check_output([sys.executable, 'tools/throughput/accepted_cost.py', 'compute', 's81',
                                                    '--unit', 'X', '--match', m, '--price', str(pr), '--measured', str(me)]))['per_workload'][wl]
        a = p['added_cycles'] if p else 0.0
        out['per_row'].setdefault(r['group'][:48], {})[wl] = a if p else 'not on this path (0)'
        add += a
        add_acc += a if r['status'] == 'accepted' else 0.0
    c, t = TP[wl]['cycles'], TP[wl]['tok_s']
    out['workloads'][wl] = dict(base_cycles=c, base_tok_s=t, added_cycles=round(add, 1), cycles=round(c + add, 1),
                                tok_s=round(t * c / (c + add), 1), loss_pct=round(100 * (1 - c / (c + add)), 3),
                                tok_s_accepted_only=round(t * c / (c + add_acc), 1))
out['floor'] = dict(rule='OWNER 10-15 22:30: S81 >15 % OK if MTP > 3,000 tok/s', mtp_tok_s=out['workloads']['mtp']['tok_s'],
                    pass_=out['workloads']['mtp']['tok_s'] > 3000)
print(json.dumps(out, indent=1))
