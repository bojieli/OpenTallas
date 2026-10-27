#!/usr/bin/env python3
"""S81-ROWX2: price the two approved ROWX configs with the TOK-DS-6b composition (same method as
results/rowx_budget_1026/price_options.py: base token path + every non-superseded s81 ledger row; SVC.ROWS_INGRESS A/B
re-priced with accepted_cost.py compute, measured 3809 replaced by the config's per-half ingress q cycles).
  B=80 fallback  : held-list export, 1 pass NXW 40; ingress 60 x 80 + 1 = 4,801; export 8 x 40 = 320 entry cycles.
  RO slots       : rank-order export, NP 7 x NXW 40, XP 320; ingress 512 x 8 / 2 + 1 = 2,049 (any selection);
                   export 7 x 320 = 2,240 entry cycles (last word at 6 x 320 + 8 x 40 = 2,240).
'+export' adds the export entry cycles serially (upper sensitivity; the 3809 row counts neither export nor transport).
ledger % = accepted_cost.py table's s81 total (17.045) - (this config's A+B e2e % - the 3809 A+B e2e %, same compute) (binding workload) with A/B replaced.
usage: run from the repo root of claude/rowx-budget-1026@9f97c5c993 (its ledger carries the SVC.ROWS_INGRESS rows):
  python3 results/rtl/s81_rowx2_1026/price_rowx2.py > price_rowx2.json"""
import json, subprocess, sys
L = json.load(open('results/arch/accepted_cost_ledger_1013.json'))
TP = {w: json.load(open(f'results/arch/token_path_20261009/{f}.json'))['totals'] for w, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp'))}
MATCH = {'SVC.ROWS_INGRESS.A': ('(^|\\.)L(2|8|14|20)\\.attn\\.rows_allgather$', 1032.9),
         'SVC.ROWS_INGRESS.B': ('(^|\\.)L(24|28|32|36)\\.attn\\.rows_allgather$', 1024.0)}
OPTS = [('ledger now (bench pair format 3809)', 3809, 0), ('B=80 fallback (held list, NXW 40, 1 pass)', 60 * 80 + 1, 8 * 40),
        ('RO rank-order slots (NP 7 x NXW 40, XP 320)', 512 * 8 // 2 + 1, 7 * 320)]
rows = [r for r in L['rows'] if r['design'] == 's81' and r['status'] != 'superseded']
import re
TAB = subprocess.check_output([sys.executable, 'tools/throughput/accepted_cost.py', 'table'], text=True)
TOTAL = float(re.search(r'^s81: accepted [0-9.]+ % \+ proposed [0-9.]+ % = ([0-9.]+) %', TAB, re.M).group(1))
def comp(m, pr, me):
    return json.loads(subprocess.check_output([sys.executable, 'tools/throughput/accepted_cost.py', 'compute', 's81',
                      '--unit', 'X', '--match', m, '--price', str(pr), '--measured', str(me)]))
res = []
for name, C, exp in OPTS:
    o = dict(option=name, ingress_q_cycles=C, export_entry_cycles=exp)
    for tag, CC in (('', C), ('+export', C + exp)):
        cache = {g: comp(m, pr, CC) for g, (m, pr) in MATCH.items()}
        for wl in ('ar', 'mtp'):
            add = 0.0
            for r in rows:
                if r['group'] in MATCH: add += cache[r['group']]['per_workload'][wl]['added_cycles']
                else:
                    p = r.get('per_workload', {}).get(wl); add += p['added_cycles'] if p else 0.0
            c, t = TP[wl]['cycles'], TP[wl]['tok_s']
            o[f'{wl}{tag}'] = dict(tok_s=round(t * c / (c + add), 1), loss_pct=round(100 * (1 - c / (c + add)), 3))
        o[f'ab_e2e_pct{tag}'] = sum(cache[r['group']]['e2e_loss_pct'] for r in rows if r['group'] in MATCH)
    res.append(o)
# ledger % = the table total + (this config's A + B e2e % - the 3809 A + B e2e % from the same compute): the stored rows
# were priced AR-binding (1.322 + 1.326); compute now binds MTP for these rows, so only the delta is applied to the table
for o in res:
    for tag in ('', '+export'):
        o[f'ledger_pct{tag}'] = round(TOTAL + o[f'ab_e2e_pct{tag}'] - res[0]['ab_e2e_pct'], 3)
print(json.dumps(dict(floor='OWNER 10-15: S81 MTP > 3,000 tok/s', options=res), indent=1))
