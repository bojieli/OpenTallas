#!/usr/bin/env python3
"""QC-KITS-1 (2026-10-27): which QC partition types does the pending plan event leave untouched?
Inputs (read-only):
  MAIN   physical/die_plan/qwen_compute/die_plan.json on main (sha 54a1aeb5, 68 types)
  CAND   candidate_oneqc0733.json (sha e4829ce2, 88 types; base of the d43 delta; epyc2 qc-mesh-r17/pkg/inputs)
  D43    results/qc_clk_mesh3/r17/plan_delta/plan_d43.json.gz (sha f2c91d03, INFRA-FIRST-QC-R17)
  WIN    island windows of the d43b top tree (epyc2 qc-mesh-r17/pkg/build/basekit/island_windows.json)
  STA    results/qc_clk_mesh3/r18/runs/f64/sta_cv_die_sta_related.json (R18 die STA, worst seam pairs)
Per type: (a) main -> d43 change (keys), (b) cand -> d43 change, (c) d43b top-tree island windows vs the plan's
die_islands_um (site centres), (d) landing-contract clock pins (S81 BLOCKER A: landing SDC vs sdc_lint),
(e) critical = on a worst seam pair named by the R18 die STA.
Usage: qc_kits_worklist.py MAIN CAND D43 WIN OUT.tsv"""
import gzip, hashlib, json, sys, collections

def load(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))

main, cand, d43, win = (load(p) for p in sys.argv[1:5])
out = sys.argv[5]
win = win['windows']
h = lambda x: hashlib.sha1(json.dumps(x, sort_keys=True).encode()).hexdigest()
CRIT = {'sl_E0_hc0': 'worst TT setup + FF zero-logic hold pair (c_E0_tn_00<->sl_E0_hc0)',
        'c_E0_tn_00': 'worst FF zero-logic hold pair (c_E0_tn_00->sl_E0_hc0)',
        'sl_W1_su_c': 'worst kit-contract hold pair d43b (sl_W1_su_c->c_W1_bn_10)',
        'c_W1_bn_10': 'worst kit-contract hold pair d43b (sl_W1_su_c->c_W1_bn_10)',
        'sl_W2_su_c': 'kit-contract core-view FAIL -1.89 (sl_W2_su_c->sl_W2_su_l1)',
        'sl_W2_su_l1': 'kit-contract core-view FAIL -1.89 (sl_W2_su_c->sl_W2_su_l1)'}
ptype = {p['name']: p['type'] for p in d43['partitions']}
crit = collections.defaultdict(list)
for n, why in CRIT.items():
    crit[ptype[n]].append(f'{n}: {why}')
inst = collections.Counter(p['type'] for p in d43['partitions'])
base = lambda t: t.split('__')[0].replace('_e2', '').replace('_v1r', '_v1')
cen = lambda b: (round((b[0] + b[2]) / 2, 2), round((b[1] + b[3]) / 2, 2))
tm, tc, td = main['partition_types'], cand['partition_types'], d43['partition_types']
rows = []
for t in sorted(td):
    v = td[t]
    mt = t if t in tm else base(t)
    if mt in tm:
        ks = sorted(k for k in set(tm[mt]) | set(v) if json.dumps(tm[mt].get(k), sort_keys=True) != json.dumps(v.get(k), sort_keys=True))
        m_chg = ('split:' if mt != t else '') + ','.join(ks) if ks else 'same'
    else:
        m_chg = 'new'
    c_chg = 'same' if h(tc.get(t)) == h(v) else 'CHANGED'
    isl = {cen(b) for b in v.get('clock', {}).get('die_islands_um') or []}
    ww = {cen(b) for b in (win.get(t) or win.get(base(t)) or [])}
    lc = v.get('clock', {}).get('landing_contract') or {}
    lck = sum(1 for p in lc.get('pins', []) if p['kind'] == 'clock')
    untouched = m_chg == 'same' and c_chg == 'same' and (not ww or ww <= isl)
    rows.append([t, mt, inst[t], len(v.get('hard_cores') or []), m_chg, c_chg, len(isl), len(ww), len(isl & ww),
                 lck, 'A' if lck else '', 'YES' if untouched else 'no', '; '.join(crit.get(t, []))])
hdr = ['type', 'main_type', 'instances', 'hard_cores', 'main_to_d43', 'cand_to_d43', 'plan_islands', 'd43b_tree_windows',
       'overlap', 'landing_clock_pins', 's81_blocker', 'untouched', 'critical_seam']
with open(out, 'w') as f:
    f.write('\t'.join(hdr) + '\n')
    for r in sorted(rows, key=lambda r: (r[12] == '', r[0])):
        f.write('\t'.join(map(str, r)) + '\n')
n_un = sum(r[11] == 'YES' for r in rows)
print(json.dumps(dict(types_d43=len(td), types_main=len(tm), untouched=n_un,
                      main_types_absent_in_d43=sorted(set(tm) - set(td)),
                      cand_to_d43_changed=sum(r[5] != 'same' for r in rows),
                      d43b_windows_not_in_plan=sum(1 for r in rows if r[7] and r[8] < r[7]),
                      blocker_A=sorted(r[0] for r in rows if r[10]),
                      critical=sorted({r[0] for r in rows if r[12]}),
                      sha=dict((k, hashlib.sha256(open(p, 'rb').read() if not p.endswith('.gz') else gzip.open(p).read()).hexdigest()[:8])
                               for k, p in zip(['main', 'cand', 'd43', 'win'], sys.argv[1:5]))), indent=1))
