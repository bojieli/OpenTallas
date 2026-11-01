import pickle,json
from pathlib import Path
b=Path(__file__).parent
L,m,kind=pickle.load(open(b/'state_normalized.pkl','rb'))
m.write(b/'normalized_baseline.aig')
base='ff:u_dut.u_bound.u_u_r{}.g_mode_payload[0].u_m2.used_q[{}]'
hints=[]
for r in (5,6,7):
 for bit in (0,1):
  k=base.format(r,bit);rep=base.format(4,bit);h=['eq','gold',rep,0]
  assert k in L.gp and ('gold',k) not in L.hyp
  L.hyp[('gold',k)]=tuple(h);hints.append(['gold',k,h])
mm,kk=L.build();mm.write(b/'normalized_candidate_miter.aig');print('candidate',mm.ni,len(mm.outs),len(mm.ands)//2)
# Inductive obligations include every existing profile hypothesis plus new equalities.
hm,_=L.build(with_compare=False,with_hyp=True);hm.write(b/'normalized_candidate_hyp.aig')
# Mutating only one newly asserted relation to complement must leave the obligation nonzero.
L.hyp[('gold',base.format(5,0))]=('eq','gold',base.format(4,0),1)
mu,_=L.build(with_compare=False,with_hyp=True);mu.write(b/'normalized_mutant_hyp.aig')
(b/'hints.json').write_text(json.dumps(hints,indent=1)+'\n')
