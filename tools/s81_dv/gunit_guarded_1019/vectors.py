#!/usr/bin/env python3
"""Direct HC-tail boundary vectors; same ordered golden operations as Model.hc_mixes."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import hdc_golden_v41 as g
g.set_arith('chunk8')
F=np.float32
rng=np.random.default_rng(1019)
words=[]
for case in range(8):
    mixes=(rng.standard_normal(24)*[.2,1,4,12][case%4]).astype(F)
    base=(rng.standard_normal(24)*.5).astype(F)
    scale=rng.uniform(.2,2,3).astype(F)
    eps=F(1e-6)
    pre=g.add(g.sigmoid(g.add(g.mul(mixes[:4],scale[0]),base[:4])),eps)
    post=g.mul(g.sigmoid(g.add(g.mul(mixes[4:8],scale[1]),base[4:8])),F(2))
    comb=g.add(g.mul(mixes[8:],scale[2]),base[8:]).reshape(4,4)
    e=g.exp(g.add(comb,g.neg(np.max(comb,axis=1,keepdims=True))))
    rs=g.seqsum([e[:,k] for k in range(4)])
    comb=g.add(g.div(e,rs[:,None]),eps)
    def cols(cm):return g.div(cm,g.add(g.seqsum([cm[j,:] for j in range(4)]),eps)[None,:])
    def rows(cm):return g.div(cm,g.add(g.seqsum([cm[:,k] for k in range(4)]),eps)[:,None])
    comb=cols(comb)
    for _ in range(19):comb=cols(rows(comb))
    vals=np.concatenate([mixes,base,scale,pre,post,comb.reshape(-1)]).astype(F)
    words.extend(vals.view(np.uint32).tolist())
Path(sys.argv[1]).write_text(''.join(f'{v:08x}\n' for v in words))
