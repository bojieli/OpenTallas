#!/usr/bin/env python3
"""ROWX-BUDGET: S81 AR / MTP tok/s for each static per-owner budget option.  Same composition as
results/rtl/s81_l14_idx_k3_1026/compose_tok_s.py (TOK-DS-6b: base token path + every non-superseded s81 ledger row's
added cycles; SVC.ROWS_INGRESS A/B priced with accepted_cost.py compute), with the SVC.ROWS_INGRESS measured value
3809 replaced by each option's per-half ingress q cycles (both halves run in parallel).  Ingress = 15 peer owners x B
rows x 8 tiles / 2 halves per PK2 word = 60 B words + 1 header per pass (lanes/S81-ROWX.md).  Export (8 x NXW entry
cycles before GO) and the cross-die transport are NOT counted, exactly as the 3809 ledger row does not count them;
'+export' columns add them serially as an upper sensitivity.  usage: price_options.py (repo root)"""
import json, subprocess, sys
L = json.load(open('results/arch/accepted_cost_ledger_1013.json'))
TP = {w: json.load(open(f'results/arch/token_path_20261009/{f}.json'))['totals'] for w, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp'))}
MATCH = {'SVC.ROWS_INGRESS.A': ('(^|\\.)L(2|8|14|20)\\.attn\\.rows_allgather$', 1032.9),
         'SVC.ROWS_INGRESS.B': ('(^|\\.)L(24|28|32|36)\\.attn\\.rows_allgather$', 1024.0)}
def ingress(B, passes):            # per half, q cycles
    return passes * (60 * B + 1)
OPTS = [('ledger now (bench pair format, 476 rows x 8)', 3809, 0),
        ('data-exact (476 x 4 + 1; needs per-token schedule)', 1905, 0),
        ('B=40, 1 pass, NXW=20', ingress(40, 1), 8 * 20),
        ('B=80, 1 pass, NXW=40', ingress(80, 1), 8 * 40),
        ('B=40 x 2 passes (budget 80), NXW=20+20', ingress(40, 2), 2 * 8 * 20),
        ('B=120, 2 passes NXW=40+20', ingress(40, 1) + ingress(80, 1), 8 * 60),
        ('B=160, 2 passes NXW=40+40 (> XN=128: list faults first)', ingress(80, 2), 8 * 80)]
rows = [r for r in L['rows'] if r['design'] == 's81' and r['status'] != 'superseded']
def cost(m, pr, me):
    return json.loads(subprocess.check_output([sys.executable, 'tools/throughput/accepted_cost.py', 'compute', 's81',
                      '--unit', 'X', '--match', m, '--price', str(pr), '--measured', str(me)]))['per_workload']
res = []
for name, C, exp in OPTS:
    o = dict(option=name, ingress_q_cycles=C, export_entry_cycles=exp)
    for tag, CC in (('', C), ('+export', C + exp)):
        for wl in ('ar', 'mtp'):
            add = 0.0
            for r in rows:
                if r['group'] in MATCH:
                    m, pr = MATCH[r['group']]; add += cost(m, pr, CC)[wl]['added_cycles']
                else:
                    p = r.get('per_workload', {}).get(wl); add += p['added_cycles'] if p else 0.0
            c, t = TP[wl]['cycles'], TP[wl]['tok_s']
            o[f'{wl}{tag}'] = dict(tok_s=round(t * c / (c + add), 1), loss_pct=round(100 * (1 - c / (c + add)), 3))
    res.append(o)
base = res[0]
for o in res:
    for k in ('ar', 'mtp', 'ar+export', 'mtp+export'):
        o[k]['delta_tok_s_vs_ledger'] = round(o[k]['tok_s'] - base[k.split('+')[0]]['tok_s'], 1)
        o[k]['delta_loss_pp_vs_ledger'] = round(o[k]['loss_pct'] - base[k.split('+')[0]]['loss_pct'], 3)
print(json.dumps(dict(floor='OWNER 10-15: S81 MTP > 3,000 tok/s', options=res), indent=1))
