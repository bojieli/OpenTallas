"""Reuse the exact saved AIG context, dropping every failed induction obligation."""
import sys,pickle,json,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
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
