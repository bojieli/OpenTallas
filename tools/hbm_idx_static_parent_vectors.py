#!/usr/bin/env python3
"""Full-shape source-bound INDEX operands and independent exact score/top512 oracle."""
import sys
from pathlib import Path
import numpy as np
import hbm_idx_die_bench as B
import rtl_hdc_v41x_idx_campaign as C
import hdc_golden_v41 as G
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(2026101501)
# Optional explicit production shape; legacy invocation stays byte-identical.
nq=int(sys.argv[2]) if len(sys.argv)>2 else 4
tp=int(sys.argv[3]) if len(sys.argv)>3 else 96
rank=int(sys.argv[4]) if len(sys.argv)>4 else 3
assert nq in (2,4) and tp in (96,192) and 0<=rank<tp
n=min(nq*2736, (1048576//(8*tp))*8 + min(8,max(0,1048576%(8*tp)-8*rank)))
if len(sys.argv)==2:n=10928
q,w=B.query(rng)
qc,qu=B.qdq_codes(q)
kc,ku=B.qdq_codes(rng.standard_normal((n,128)).astype(np.float32))
exp,bad=C.golden(C.values(qc,qu),w,C.values(kc,ku),np.ones(n,dtype=bool),qu,ku)
assert not bad.any()
import os
if os.environ.get('IDX_VEC_CRAFT')=='1':
 # L2H-IDXSEL s3 (opt-in; unset = the legacy bytes): re-pick the n keys from a 3n pool of the same distribution so the
 # selector's two schedule margins are observable (scores are per-key, independent of the key's slot):
 #  T (the 512th score) is unique with pass-2 bin 0 (orderkey low 6 bits 0: found on the LAST op5 of pass 2, its tie
 #  budget 1 decided there) and sits in quadrant 0 line 0 (the first compaction line reads the fresh budget: an op6
 #  block one edge early takes the reset budget 0 and drops T); line 170 of quadrants 0..2 holds keys of T's pass-0 bin
 #  inside T's pass-1 bin with pass-2 bin 63 (the first op5 of pass 2: a drain one edge short misses them, rank_left stays
 #  above T's count at bin 0 and no tie budget is set: T is dropped).
 ok=lambda x:(~x)&0xffff if x&0x8000 else x^0x8000          # orderkey of bf16 bits
 pc,pu=B.qdq_codes(np.random.default_rng(2026102001).standard_normal((3*n,128)).astype(np.float32))
 pe,pb=C.golden(C.values(qc,qu),w,C.values(pc,pu),np.ones(3*n,dtype=bool),qu,pu)
 assert not pb.any()
 K=np.array([ok(int(x)) for x in pe],dtype=np.int64)
 order=np.argsort(-K,kind='stable')
 pick=None
 for r in range(300,4000):
  t=int(K[order[r]])
  if t&63 or int((K==t).sum())!=1:continue
  hi=np.where(((K>>6)==(t>>6))&((K&63)==63))[0]
  if len(hi)>=1:pick=(order[r],t,hi[:6]);break
 assert pick is not None,'no craftable threshold in the pool'
 iT,t,hi=pick
 above=[int(i) for i in order if K[i]>t and int(i) not in set(int(x) for x in hi)][:511-len(hi)]
 below=[int(i) for i in order if K[i]<t][:n-512]
 assert len(above)==511-len(hi) and len(below)==n-512
 slot=[None]*n
 slot[5]=int(iT)
 l170=[s_*2736+170*16+l for s_ in range(3) for l in range(2)][:len(hi)]
 for j,i in zip(l170,hi):slot[j]=int(i)
 rest=above+below
 np.random.default_rng(2026102002).shuffle(rest)
 it=iter(rest)
 for j in range(n):
  if slot[j] is None:slot[j]=next(it)
 kc,ku,exp=pc[slot],pu[slot],pe[slot]
 assert sorted(ok(int(x)) for x in exp)[-512]==t
keys=[B.key_word(kc[i],ku[i]) for i in range(n)]
lines=[]
for a in range(171):
 packed=0
 for s in range(nq):
  for p in range(8):
   index=s*2736+a*16+p*2
   two=sum((keys[index+j] if index+j<n else 0)<<(j*544) for j in range(2))
   payload=(two<<11)|(((p*128+a)&1023)<<1)|1   # service tag (128*port + beat) % 1024 (ot_hbm_idx_score_static)
   packed|=payload<<(s*8792+p*1099)
 lines.append(packed)
(out/'keylines.hex').write_text(''.join(f'{x:0{nq*2198}x}\n' for x in lines))
(out/'query.hex').write_text(''.join(f'{(x>>7)&((1<<1024)-1):0256x}\n' for x in B.qblocks(q,w)))
weights=sum((int(G.bits(np.float32(w[h])))>>16)<<(h*16) for h in range(32))
(out/'weights.hex').write_text(f'{weights:0128x}\n')
(out/'scores.hex').write_text(''.join(f'{int(x):04x}\n' for x in exp))
values=(exp.astype(np.uint32)<<16).view(np.float32)
chosen=set(sorted(range(n),key=lambda i:(-float(values[i]),i))[:512])
(out/'gold.hex').write_text(''.join(f'{int(i in chosen):x}\n' for i in range(n)))
