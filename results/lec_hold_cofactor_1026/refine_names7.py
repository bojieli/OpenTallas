"""Reuse the exact saved AIG context, dropping every failed induction obligation."""
import sys,pickle,json,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
added=[]
# Actual enabled cuts in both adders: 0,1,3,4,5,6,8.
for ch in ('u_c0','u_c1'):
 b=f'ff:u_dut.u_e.g_mac[1].g_ch3.{ch}'
 for n,stage in enumerate((0,1,3,4,5,6,8)):
  k=f'{b}.u_add.u_c{stage}.g_r.v';g=f'{b}.pv[{n}]'
  if k in L.gp and g in L.gp and ('gold',k) not in L.hyp:
   h=('eq','gold',g,0);L.hyp['gold',k]=h;added.append(('gold',k,h))
# er[1] is zero at creation: E_NONE=00 / E_NONFINITE=01.
# These bit positions follow the actual o1..o8 packing in ot_v41_fadd.
for k in L.gonly:
 if k.endswith('.u_c8.g_r.r[66]'):
  b=k[:-len('.u_c8.g_r.r[66]')]
  for stage,bit in ((1,99),(2,99),(3,97),(4,97),(5,68),(6,73),(7,68),(8,66)):
   q=f'{b}.u_c{stage}.g_r.r[{bit}]'
   if q in L.gp and ('gold',q) not in L.hyp:
    h=('const',0);L.hyp['gold',q]=h;added.append(('gold',q,h))
print('additional_derived_pipeline_pairs',len(added),flush=True)
(work/'added.json').write_text(json.dumps(added,indent=2))
log=[];rnd=0
while True:
 m,_=L.build(with_compare=False,with_hyp=True)
 st=LC.prove(m,work,1000,log,tag='hyp'+str(rnd))
 bad=[n for n,s in st.items() if s!='proved']
 print('induction',rnd,dict(collections.Counter(st.values())),flush=True)
 if not bad:break
 (work/('hyp'+str(rnd)+'_failed.json')).write_text(json.dumps(bad,indent=2))
 before=dict(L.hyp);LC.drop_failed(L,bad)
 if L.hyp==before:raise RuntimeError('failed obligations could not be dropped')
 rnd+=1
m,kind=L.build(with_compare=True,with_hyp=True)
st=LC.prove(m,work,1000,log,tag='compare')
print('statuses',dict(collections.Counter(st.values())),flush=True)
for n,s in st.items():
 if s!='proved':print('BAD',s,n,flush=True)
(work/'log').write_text('\n'.join(log));(work/'statuses.json').write_text(json.dumps(st))
(work/'hyp.json').write_text(json.dumps([[sd,k,h]for(sd,k),h in L.hyp.items()]))
with open(work/'context.pickle','wb') as f:pickle.dump(L,f)
