"""DIE-PROTO-3: per-seam rows (src partition -> dst partition) from die_sta_related, same model/args as the main run.
Wraps die_sta_related.time_class; for every non-landed class call whose pairs cross partitions (the seam class) it also
times each (src part, dst part) group separately with the original function and writes OUT_ROWS (TSV, both corners).
usage: seam_rows.py OUT_ROWS -- <die_sta_related args...>   (run from tools/die_plan)"""
import sys, json
from collections import defaultdict
out = sys.argv[1]; argv = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, '.')
import die_sta_related as R
orig = R.time_class
rows = []
corner = {'c': None}
def tc(pairs, taps, *a, **k):
    res = orig(pairs, taps, *a, **k)
    if not k.get('landed') and pairs and all(taps[x]['part'] != taps[y]['part'] for x, y, *_ in pairs[:50]):
        g = defaultdict(list)
        for p in pairs: g[(taps[p[0]]['part'], taps[p[1]]['part'])].append(p)
        for (sp, dp), pl in g.items():
            r = orig(pl, taps, *a, **k)
            hm = r.get('hold_measured') or {}
            rv = r.get('real_view') or {}
            rows.append(dict(src=sp, dst=dp, pairs=len(pl), setup=r.get('worst_setup_slack_ps'), hold_all=r.get('worst_hold_slack_ps'),
                             skew=r.get('skew_diag_max_ps'), measured=hm.get('pairs_measured'), hold_measured=hm.get('hold_margin_ps'),
                             hold_status=hm.get('status'), kit_contract=(r.get('kit_contract_hold') or {}).get('worst_hold_bound_ps'),
                             need=(r.get('kit_contract_hold') or {}).get('window_needed_ps'), W=(r.get('kit_contract_hold') or {}).get('window_ps'),
                             missing=';'.join(sorted(hm.get('missing_views') or {})) if isinstance(hm.get('missing_views'), dict) else str(hm.get('missing_views') or '')))
    return res
R.time_class = tc
try:
    R.main(argv)
finally:
    n = len(rows) // 2
    with open(out, 'w') as f:
        cols = ['corner', 'src', 'dst', 'pairs', 'setup', 'hold_all', 'skew', 'measured', 'hold_measured', 'hold_status', 'kit_contract', 'need', 'W', 'missing']
        f.write('\t'.join(cols) + '\n')
        for i, r in enumerate(rows):
            r['corner'] = 'TT' if i < n else 'FF'
            f.write('\t'.join(str(r.get(c)) for c in cols) + '\n')
    print('SEAM_ROWS', len(rows), out)
