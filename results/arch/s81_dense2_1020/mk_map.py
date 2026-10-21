"""DENSE2 10-20: split stage map from an actual-allocator probe summary (xs_stage_map.build_split), its distinct specs,
and K spec chunks for parallel exact runs.  usage: mk_map.py PROBE_SUMMARY R TAG [NSTAGES] [K]"""
import json, sys
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D / 'root/tools/s81_dv/layer_prog'))
import xs_stage_map as SM
probe, R, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
c = SM.probe_costs_split(probe, R)
nmin = SM.min_stages_split(c)
n = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != 'min' else nmin
K = int(sys.argv[5]) if len(sys.argv) > 5 else 4
m = SM.build_split(n, c, f'{n}-stage DENSE2 split ({tag}: a_proj rows [0,{R}) on A), balanced on actual probe load')
(D / f'stage_map_{tag}_{n}.json').write_text(json.dumps(m, indent=1) + '\n')
sp = SM.specs_of(m)
sp.sort(key=lambda s: -s['experts'])
(D / f'specs_{tag}_{n}.json').write_text(json.dumps(sp, indent=1) + '\n')
for k in range(K):
    (D / f'specs_{tag}_{n}_c{k}.json').write_text(json.dumps(sp[k::K], indent=1) + '\n')
w = max(m['stages'], key=lambda s: s['model_load'])
print('DENSE2_MAP', json.dumps(dict(tag=tag, R=R, min_stages=nmin, stages=m['stages_count'], layer_dies=4 * m['stages_count'],
      specs=len(sp), worst_model_fill_pct=w['model_fill_pct'], worst_stage=w['stage'], slope=c['slope'],
      dense_A={k: v['q'] for k, v in c['dense_split2']['A'].items()}, dense_B={k: v['q'] for k, v in c['dense_split2']['B'].items()})))
