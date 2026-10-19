#!/usr/bin/env python3
# L2H-P3 diag: span histogram of die nets (driver->farthest load) by driver-master family, for the f4c_t9p3 relayed case.
import collections, json, sys
from pathlib import Path
sys.path.insert(0, 'tools/hbm_die_v15')
import die_relay_pass as RP
case, contract, out = sys.argv[1], sys.argv[2], sys.argv[3]
C = json.loads(Path(contract).read_text())
pl, nets, directions, top_inputs = RP.load_case(Path(case), C)
edges = [0, 405, 450, 500, 600, 810, 1215, 2000, 4000, 8000, 1e9]
H = collections.defaultdict(lambda: [0]*(len(edges)-1)); W = collections.defaultdict(list); inst = collections.defaultdict(collections.Counter)
for n, ends in nets.items():
    drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']; lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
    if len(drv) != 1 or not lds: continue
    d0 = drv[0]; span = max(RP.md(d0[2], l[2]) for l in lds)
    dm = pl[d0[0]]['master']; lm = pl[lds[0][0]]['master']
    fam = (dm.split('_')[0] + '_' + dm.split('_')[1] if dm.startswith('hbfd') else 'tile') + '->' + (lm.split('_')[0] + '_' + lm.split('_')[1] if lm.startswith('hbfd') else 'tile')
    for i in range(len(edges)-1):
        if span < edges[i+1]: H[fam][i] += 1; break
    if span > 405: inst[fam][(d0[0], lds[0][0])] += 1
res = {'edges': edges, 'hist': H, 'top_pairs': {f: [(a, b, c) for (a, b), c in v.most_common(15)] for f, v in inst.items()},
       'pairs_over': {f: len(v) for f, v in inst.items()}}
Path(out).write_text(json.dumps(res, indent=1)); print(json.dumps({'hist': H, 'pairs_over': res['pairs_over']}))
