"""Reuse the exact saved AIG context, dropping every failed induction obligation."""
import sys,pickle,json,collections,re
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
added=[]
for k in L.tonly:
 m=re.match(r'(ff:.*\.q0_sg)#t\[(\d+)\]$',k)
 if m and ('gate',k) not in L.hyp:
  i=int(m[2]);g=f'{m[1]}[{i//16}][{i%16}]'
  if g in L.gp:
   h=('eq','gold',g,0);L.hyp['gate',k]=h;added.append(('gate',k,h))
for k in L.tonly:
 if '.g_mi.u_c2x.q#t[' in k and ('gate',k) not in L.hyp:
  g=k.replace('#t[','[')
  if g in L.gp:
   h=('eq','gold',g,0);L.hyp['gate',k]=h;added.append(('gate',k,h))
for mac in (0,1):
 for ch in ('u_c0','u_c1'):
  b=f'ff:u_dut.u_e.g_mac[{mac}].g_ch3.{ch}'
  for i in range(7):
   k=f'{b}.u_t.g_line.line[{11*i+2}]';g=f'{b}.pl[{i}]'
   if k in L.gp and g in L.gp and ('gold',k) not in L.hyp:
    h=('eq','gold',g,0);L.hyp['gold',k]=h;added.append(('gold',k,h))
print('additional_source_shape_pairs',len(added),flush=True)
(work/'added.json').write_text(json.dumps(added,indent=2))
log=[];rnd=0
while True:
 m,_=L.build(with_compare=False,with_hyp=True)
 st=LC.prove(m,work,1000,log,tag='hyp'+str(rnd))
 bad=[n for n,s in st.items() if s!='proved']
 print('induction',rnd,dict(collections.Counter(st.values())),flush=True)
 if not bad:break
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
