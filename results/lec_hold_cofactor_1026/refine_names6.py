"""Reuse the exact saved AIG context, dropping every failed induction obligation."""
import sys,pickle,json,collections,re
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
added=[]
for k in L.tonly:
 m=re.match(r'(ff:.*\.(?:p0|q0|q1)_sg)#t\[(\d+)\]$',k)
 if m and ('gate',k) not in L.hyp:
  i=int(m[2]);g=f'{m[1]}[{i//16}][{i%16}]'
  if g in L.gp:
   h=('eq','gold',g,0);L.hyp['gate',k]=h;added.append(('gate',k,h))
for ch in ('u_c0','u_c1'):
 b=f'ff:u_dut.u_e.g_mac[1].g_ch3.{ch}'
 k=b+'.u_add.u_c8.g_r.v';g=b+'.pv[6]'
 if k in L.gp and g in L.gp and ('gold',k) not in L.hyp:
  h=('eq','gold',g,0);L.hyp['gold',k]=h;added.append(('gold',k,h))
for k in L.gonly:
 if k.endswith('.u_c8.g_r.r[66]') and ('gold',k) not in L.hyp:
  b=k[:-len('.u_c8.g_r.r[66]')]
  for q in (k,b+'.u_c6.g_r.r[73]'):
   if q in L.gp and ('gold',q) not in L.hyp:
    h=('const',0);L.hyp['gold',q]=h;added.append(('gold',q,h))
print('additional_predecessor_pairs',len(added),flush=True)
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
