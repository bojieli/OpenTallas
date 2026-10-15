#!/usr/bin/env python3
"""Actual project goldens; compiler checkpoint-ordered fixed SIDE schedule."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import hdc_golden_v41 as V
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(1015)
N=4096
positive=np.exp2(rng.uniform(-12,12,N)).astype(np.float32)
signed=rng.uniform(-90,90,N).astype(np.float32)
directed=np.array([0.,-0.,1e-8,-1e-8,1e-6,-1e-6,.25,-.25,.5,-.5,1.,-1.,2.,-2.,87.,-87.,88.,-88.],dtype=np.float32)
inputs={2:positive.copy(),3:positive.copy(),6:signed.copy(),7:signed.copy()}
for fn,x in inputs.items():
 d=np.abs(directed) if fn in [2,3] else directed
 x[:len(d)]=d
inputs[2][:2]=np.float32(1e-12)
# RSQRT domain excludes zero: finite reciprocal square root contract.
y={2:G.rsqrt(inputs[2]),3:V.sqrt(inputs[3]),6:V.sqrt(V.softplus(inputs[6]))}
x=inputs[7];mag=V.sqrt(np.maximum(np.abs(x),np.float32(1e-6)).astype(np.float32))
y[7]=V.sigmoid(np.where(x<0,G.neg(mag),mag).astype(np.float32))
D={2:37,3:31,6:162,7:104}
calendar={};next_issue=0;last_due=-1
for chunk in range(N//128):
 for fn in [6,3,2,7]:
  for j in range(chunk*128,(chunk+1)*128):
   issue=max(next_issue,last_due+1-(D[fn]-1));due=issue+D[fn]-1
   inp=(1<<35)|(fn<<32)|int(G.bits(inputs[fn][j]));exp=(1<<35)|(fn<<32)|int(G.bits(y[fn][j]))
   calendar[issue]=calendar.get(issue,0)|inp
   calendar[due]=calendar.get(due,0)|(exp<<36)
   next_issue=issue+1;last_due=due
rows=last_due+3
(out/'schedule.hex').write_text(''.join(f'{calendar.get(i,0):018x}\n' for i in range(rows)))
sources={str(Path(p).relative_to(Path(__file__).resolve().parents[2])):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [G.__file__,V.__file__]}
(out/'manifest.json').write_text(json.dumps(dict(rows=rows,functions=D,exact_words=N*4,words_per_function=N,golden_sources=sources,arithmetic='G.rsqrt,V.sqrt,V.sqrt(V.softplus),projectMachine.su.egate=V.sigmoid(sign*V.sqrt(max(abs(x),1e-6)))',schedule='compiler checkpoint ordered; output due issue+fixedDepth-1 post-edge; no outputcollisions'),indent=2)+'\n')
print(rows)
