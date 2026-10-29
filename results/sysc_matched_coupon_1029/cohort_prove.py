import json,pickle
from pathlib import Path
import lec as E
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
E.noreset_classify(L);log=[];rec={}
p='ff:u_dut.u_bound.u_d2d_kv.u_core.u_end.u_link.u_ctl.s1_c'
pairs=[(f'{p}[{i}]',f'{p}[{i%6}]') for i in range(6,24)]
for sd,d,cp,points in [('gold',L.gold,L.gc,L.gp),('gate',L.gate,L.tc,L.tp)]:
 levels={};R=E.reset_vars(d,points,levels=levels,declared=L.kit_reset_ports)
 # Cofactor ONLY the declared/detected reset inputs at their existing asserted polarity.
 a=E.Aig();a.ni=d['I']+d['L'];v={0:0}
 for i in range(1,a.ni+1):v[i]=R.get(i,2*i)
 def val(l):return v[l>>1]^(l&1)
 for j,(u,z) in enumerate(zip(d['ands'][::2],d['ands'][1::2])):v[d['I']+d['L']+1+j]=a.AND(val(u),val(z))
 rd=dict(d);rd['ands']=a.ands;rd['A']=len(a.ands)//2;rd['latches']=[val(x) for x in d['latches']]
 roots=[val(cp[k]) for pair in pairs for k in pair]
 m=E.raw_prefix_miter(rd,roots,4)
 m.outs=[m.XOR(m.outs[2*i],m.outs[2*i+1]) for i in range(len(pairs))]
 m.onames=[f'base4:{sd}:{k}={r}' for k,r in pairs]
 status=E.prove(m,w,1000,log,tag=f'cohort_base4_{sd}')
 rec[sd]={'reset_inputs':levels,'status':status}
(w/'cohort_base_proof.json').write_text(json.dumps(rec,indent=2)+'\n');(w/'cohort_base_proof.log').write_text('\n'.join(log))
print({sd:{q:list(v['status'].values()).count(q) for q in set(v['status'].values())} for sd,v in rec.items()},flush=True)
