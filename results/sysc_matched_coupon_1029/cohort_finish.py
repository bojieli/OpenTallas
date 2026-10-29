import json,pickle
from pathlib import Path
import lec as E
w=Path('.')
assert json.loads((w/'rebuild.json').read_text())['equal']
base=json.loads((w/'cohort_base_proof.json').read_text())
assert all(s=='proved' for q in base.values() for s in q['status'].values())
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
names=json.loads((w/'names.json').read_text())
swept=E.aig_outputs('/srv/opentallas-scratch2/claude/codex-kv-kits-1028/sysc/kits5/kv3_sys_c/lec_current/miter_swept.aig')
assert len(swept)==len(names['onames'])
old_hyp=[(n,o) for n,o in zip(names['onames'],swept) if n.startswith(('hyp:','cons:'))]
assert all(o==0 for n,o in old_hyp),'old hypothesis not proved'
hints=json.loads((w/'cohort_hints.json').read_text())
for sd,k,h in hints:L.hyp[(sd,k)]=tuple(h)
m,kind=L.build();idx={n:i for i,n in enumerate(m.onames)}
new=[]
for sd,k,h in hints:new.extend(['hyp:both:'+k,'hyp:bothg:'+k])
points=[r['point'] for r in json.loads((w/'lec.json').read_text())['failing']]
assert len(points)==31
wanted=new+points
m.outs=[m.outs[idx[n]] for n in wanted];m.onames=wanted
log=[];status=E.prove(m,w,1000,log,tag='cohort_induction_compare')
(w/'cohort_finish.log').write_text('\n'.join(log));(w/'cohort_finish.json').write_text(json.dumps({'old_hypotheses_proved':len(old_hyp),'base_window':4,'hints':hints,'status':status},indent=2)+'\n')
print({'old_hypotheses_proved':len(old_hyp),'new_induction':{s:sum(status[n]==s for n in new) for s in set(status.values())},'31_compare':{s:sum(status[n]==s for n in points) for s in set(status.values())}},flush=True)
