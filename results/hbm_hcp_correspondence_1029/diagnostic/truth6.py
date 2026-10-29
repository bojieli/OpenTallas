import pickle,json
from pathlib import Path
import lec_engine as lec
r=Path(__file__).parent
with (r/'normalized.pkl').open('rb') as f:L=pickle.load(f)
m,kind=L.build(with_compare=True,with_hyp=True)
k='ff:u_dut.u_fcore.u_core.u_core.nout_r[1]'
lits=[L.dlit[s,k] for s in ('gold','gate')]
vs=sorted(set().union(*(m.cone_inputs(l) for l in lits)))
fixed={v:sum(((i>>j)&1)<<i for i in range(8)) for j,v in enumerate(vs)}
y,mask=lec.cone_sim(m,lits,fixed,1,77)
print('INPUTS',[kind[v] for v in vs],flush=True)
for i in range(8):print('ROW',[(fixed[v]>>i)&1 for v in vs],'GOLD',(y[0]>>i)&1,'GATE',(y[1]>>i)&1,flush=True)
# Every original failing comparison is retained: display representative support.
d=json.loads((r/'inputs/lec.json').read_text())
print('ORIGINAL_FAILURE_KINDS',__import__('collections').Counter(tuple(e['cone_unmatched']) for e in d['failing']),flush=True)
