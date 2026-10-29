import json,pickle
from pathlib import Path
import lec as E
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
E.noreset_classify(L)
p='ff:u_dut.u_bound.u_d2d_kv.u_core.u_end.u_link.u_ctl.s1_c'
hints=[];rows=[]
for i in range(6,24):
 k=f'{p}[{i}]';rep=f'{p}[{i%6}]'
 row={'key':k,'rep':rep,'matched':k in L.matched,'sides':{}}
 for sd,cp in [('gold',L.gc),('gate',L.tc)]:
  row['sides'][sd]={'raw_D_same':cp.get(k)==cp.get(rep),'reset':L.rst_val.get((sd,k)),'rep_reset':L.rst_val.get((sd,rep))}
 if k in L.matched:hints.append(['both',k,['eq','gold',rep,0]])
 rows.append(row)
(w/'cohort_base.json').write_text(json.dumps(rows,indent=2)+'\n');(w/'cohort_hints.json').write_text(json.dumps(hints,indent=2)+'\n')
print(json.dumps({'pairs':len(rows),'hints':len(hints),'different_D':[(r['key'],sd) for r in rows for sd,v in r['sides'].items() if not v['raw_D_same']],'bad_base':[(r['key'],sd,v['reset'],v['rep_reset']) for r in rows for sd,v in r['sides'].items() if v['reset'] is None or v['reset'][0] is None or v['reset'][0]!=v['rep_reset'][0]]}),flush=True)
