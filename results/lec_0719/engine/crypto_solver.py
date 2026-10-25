import json,pathlib,sys,time
import pycryptosat
import lec_fsm as lec
p=pathlib.Path('eng_crypto');a=lec.read_aig(p/'r0.aig');names=json.load(open(p/'names.json'))
s=pycryptosat.Solver(threads=1)
def clause(lits):
 if 1 in lits:return
 s.add_clause([((x>>1) if not(x&1) else -(x>>1)) for x in lits if x>1])
base=a['I']+a['L']
for i in range(a['A']):
 n=2*(base+i+1);x,y=a['ands'][2*i:2*i+2]
 clause([n^1,x]);clause([n^1,y]);clause([n,x^1,y^1])
nx=0
for lit,terms,c in json.load(open(p/'xor.json')):
 vs=[lit>>1]+[t>>1 for t in terms];rhs=bool(c^(lit&1))
 from collections import Counter
 vs=[v for v,n in Counter(vs).items() if n&1]
 if not vs:
  assert not rhs
  continue
 s.add_xor_clause(vs,rhs);nx+=1
print('cnf_complete',a['A'],'redundant_exact_xors',nx,flush=True)
res={}
for name in ['ff:u_dut.u_lkp.u_e.fault','ff:u_dut.u_lkp.u_e.st_bad']:
 i=names.index(name);lit=a['outputs'][i];t=time.time();sat,_=s.solve(assumptions=[(lit>>1) if not(lit&1) else -(lit>>1)])
 res[name]=dict(sat=sat,seconds=time.time()-t);print(name,res[name],flush=True)
json.dump(res,open(p/'status_proof.json','w'),indent=1)
assert all(r['sat'] is False for r in res.values()),res
