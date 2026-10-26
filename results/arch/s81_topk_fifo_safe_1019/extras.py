import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'src/tools/s81_dv/layer_prog')
import lower_bk as B
root=Path('ties');(root/'ops').mkdir(parents=True, exist_ok=True)
# Independent float comparison golden. Exact repeated scores, signed zeros and infinities;
# sparse original indices cover all four ranges and approach the 20-bit ceiling.
s=np.full(1<<20, -np.inf, dtype=np.float64)
pos=np.concatenate([r*262144+np.arange(512)*511 for r in range(4)]).astype(np.int64)
vals=np.tile(np.array([-np.inf,-1.,-0.,0.,1.,1.,1.,np.inf]),256)
s[pos]=vals
order=np.lexsort((pos, -vals)); gold=np.sort(pos[order[:512]])
ops={'attn.idx.score':s,'attn.idx.topk_local':pos,'attn.idx.topk_final':gold}
m={}
for name,v in ops.items():
 v.tofile(root/'ops'/f'{name}.bin');m[name]={'dtype':str(v.dtype),'shape':list(v.shape)}
(root/'ops.json').write_text(json.dumps(m))
p=B.job_topk_final(root,boot_done=True,indexed13=True)
assert p['golden_ok'];B.write_bench(p,'bench_sram/indexed13_ties')
# Corrupt a selected original index in the ingress only: output must detect wrong identity.
q=json.loads(json.dumps(p))
q['ingress']=[tuple(x) for x in p['ingress']]
# Locate first payload type8 on lane0. Change its first candidate index by +1 (scores intact).
# A selected candidate is lane0 element7 (+inf); alter index bit0 of tuple7.
for i,(e,w) in enumerate(q['ingress']):
 if w & 1 and (w>>4)&3==0 and not ((w>>6)&1) and ((w>>16)&15)==8:
  # tuple7 index low bit is data[268] -> high part bit12 -> V bit32.
  e2,w2=q['ingress'][i+1];q['ingress'][i+1]=(e2,w2^(1<<32));break
else: raise AssertionError('no type8')
B.write_bench(p,'bench_sram/indexed13_identity',mutant='corrupt',mplan=q)

# Signed zero equality tie: all candidates compare equal; lowest original 512 win.
s[pos]=np.where(np.arange(pos.size)%2, -0.0, 0.0)
ops['attn.idx.score']=s
ops['attn.idx.topk_final']=pos[:512]
for name,v in ops.items(): v.tofile(root/'ops'/f'{name}.bin')
p=B.job_topk_final(root,boot_done=True,indexed13=True)
assert p['golden_ok'];B.write_bench(p,'bench_sram/indexed13_zeros')
# Negative infinity equality and ninf output bits.
s[pos]=-np.inf
s.tofile(root/'ops'/'attn.idx.score.bin')
p=B.job_topk_final(root,boot_done=True,indexed13=True)
assert p['golden_ok'];B.write_bench(p,'bench_sram/indexed13_ninf')
