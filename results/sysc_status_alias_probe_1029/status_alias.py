import json,pickle
from pathlib import Path
import lec as E
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
E.noreset_classify(L)
p='ff:u_dut.u_bound.u_d2d_kv.u_core.u_st.'
fields=[(0,'vm_drained',1),(1,'collective_drained',1),(2,'collective_busy',1),(3,'crom_fault',1),(4,'execution_active',1),(5,'admit_ready',1),(7,'result_done',1),(8,'result_fault',1),(9,'result_cause',4),(13,'result_tag',59),(72,'result_gen',2),(74,'result_token',18),(92,'result_value',32),(124,'result_cycles',32)]
hints=[];base=[];missing=[]
for offset,name,width in fields:
 for b in range(width):
  g=p+f'cap[{offset+b}]';t=p+name+(f'[{b}]' if width>1 else '')
  if g not in L.gp or t not in L.tp:missing.append((g,t));continue
  assert g in L.gonly and t in L.tonly,(g,t)
  hints.append(['gate',t,['eq','gold',g,0]])
  base.append({'gold':g,'gate':t,'gold_base':L.rst_val.get(('gold',g)),'gate_base':L.rst_val.get(('gate',t))})
(w/'status_alias_hints.json').write_text(json.dumps(hints,indent=2)+'\n');(w/'status_alias_base.json').write_text(json.dumps(base,indent=2)+'\n')
print('candidate_aliases',len(hints),'missing',len(missing),'base_known_equal',sum(q['gold_base'][0] is not None and q['gold_base'][0]==q['gate_base'][0] for q in base),flush=True)
for sd,k,h in json.loads((w/'cohort_hints.json').read_text())+hints:L.hyp[(sd,k)]=tuple(h)
m,kind=L.build();idx={n:i for i,n in enumerate(m.onames)}
new=['hyp:gate:'+q[1] for q in hints]
points=[q['point'] for q in json.loads((w/'lec.json').read_text())['unproven_points']]
want=new+points;m.outs=[m.outs[idx[n]] for n in want];m.onames=want
log=[];status=E.prove(m,w,1000,log,tag='status_alias_induction_compare')
(w/'status_alias.log').write_text('\n'.join(log));(w/'status_alias_result.json').write_text(json.dumps({'status':status,'base':base,'missing':missing},indent=2)+'\n')
print({'new_alias_induction':{s:sum(status[n]==s for n in new) for s in set(status.values())},'376_compare':{s:sum(status[n]==s for n in points) for s in set(status.values())}},flush=True)
