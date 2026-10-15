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
n=10928
q,w=B.query(rng)
qc,qu=B.qdq_codes(q)
kc,ku=B.qdq_codes(rng.standard_normal((n,128)).astype(np.float32))
exp,bad=C.golden(C.values(qc,qu),w,C.values(kc,ku),np.ones(n,dtype=bool),qu,ku)
assert not bad.any()
keys=[B.key_word(kc[i],ku[i]) for i in range(n)]
lines=[]
for a in range(171):
 packed=0
 for s in range(4):
  for p in range(8):
   index=s*2736+a*16+p*2
   two=sum((keys[index+j] if index+j<n else 0)<<(j*544) for j in range(2))
   payload=(two<<11)|(((a*8+p)&1023)<<1)|1
   packed|=payload<<(s*8792+p*1099)
 lines.append(packed)
(out/'keylines.hex').write_text(''.join(f'{x:08792x}\n' for x in lines))
(out/'query.hex').write_text(''.join(f'{(x>>7)&((1<<1024)-1):0256x}\n' for x in B.qblocks(q,w)))
weights=sum((int(G.bits(np.float32(w[h])))>>16)<<(h*16) for h in range(32))
(out/'weights.hex').write_text(f'{weights:0128x}\n')
(out/'scores.hex').write_text(''.join(f'{int(x):04x}\n' for x in exp))
values=(exp.astype(np.uint32)<<16).view(np.float32)
chosen=set(sorted(range(n),key=lambda i:(-float(values[i]),i))[:512])
(out/'gold.hex').write_text(''.join(f'{int(i in chosen):x}\n' for i in range(n)))
