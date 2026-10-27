"""Negative control: invert one actual gate output while retaining every proved invariant."""
import sys,pickle,json,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
target=next(k for k in sorted(L.tc) if k.startswith('po:') and k in L.gc and L.tc[k]>1)
L.tc[target]^=1
m,_=L.build(with_compare=True,with_hyp=True)
log=[];st=LC.prove(m,work,1000,log,tag='mutant_output')
bad={k:s for k,s in st.items()if s!='proved'}
rec={'mutant':'invert one gate output bit','target':target,'counts':dict(collections.Counter(st.values())),
     'bad':bad,'caught':bad=={target:'differs'}}
print(json.dumps(rec,indent=2),flush=True)
(work/'result.json').write_text(json.dumps(rec,indent=2));(work/'log').write_text('\n'.join(log))
if not rec['caught']:raise SystemExit(1)
