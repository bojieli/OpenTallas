#!/usr/bin/env python3
"""TOK-KV-2 10-28: collect the TOK-KV-2 chain (run on intel1): verdicts (kv_verdict.py, fail-closed) + token timing.
    python3 -I collect.py K W   (K = run dir tok-kv-2-1028, W = kv_dieslice tool dir) -> K/result.json + stdout
Expected: boot_n nominal PASS / mut_frame CAUGHT; tok_n PASS (36/36 layers bit-exact); tok_m CAUGHT (bind5m must fail);
m3_kswap_n CAUGHT.  Timing from tok_n FAR_LAYER lines (core cycles, 833 ps): layer stride = cal_start[n+1]-cal_start[n];
token period estimate = 36 x median stride (one-token sim: no second token start is observed) -> tok/s vs COMPOSER-ONLY 4089.4.
"""
import json, re, statistics, subprocess, sys
from pathlib import Path

K, W = Path(sys.argv[1]), Path(sys.argv[2])
EXP = {'boot_n/nominal': ('pass', 0), 'boot_n/mut_frame': ('fail', 0), 'runs/tok_n': ('pass', 36),
       'runs/tok_m': ('fail', 36), 'runs/m3_kswap_n': ('fail', 36)}
out = {'runs': {}}
for r, (x, nl) in EXP.items():
    d = K / r
    a = [sys.executable, '-I', str(W / 'kv_verdict.py'), str(d)] + (['--layers', str(nl)] if nl else []) + \
        (['--expect', 'fail'] if x == 'fail' else [])
    p = subprocess.run(a, capture_output=True, text=True)
    out['runs'][r] = {'expect': x, 'verdict': (p.stdout.strip() or p.stderr.strip())[:300], 'ok': p.returncode == 0}
log = K / 'runs/tok_n/sim.log'
if log.is_file():
    lay = {}
    for m in re.finditer(r'^FAR_LAYER layer (\d+) cal_start (-?\d+) result_first (\d+) result_last (\d+) ok (\d+) bad (\d+)',
                         log.read_text(errors='replace'), re.M):
        lay[int(m.group(1))] = tuple(int(g) for g in m.groups()[1:])
    cs = [lay[n][0] for n in sorted(lay)]
    st = [b - a for a, b in zip(cs, cs[1:])]
    if st:
        per = 36 * statistics.median(st)
        out['timing'] = {'layers_seen': len(lay), 'stride_median': statistics.median(st), 'stride_min': min(st),
                         'stride_max': max(st), 'span_l0_start_to_last_result': lay[max(lay)][2] - cs[0],
                         'period_est_cycles': per, 'tok_s_est': 1e12 / 833 / per, 'composer_only_tok_s': 4089.4,
                         'delta_pct': 100 * (1e12 / 833 / per / 4089.4 - 1)}
(K / 'result.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
