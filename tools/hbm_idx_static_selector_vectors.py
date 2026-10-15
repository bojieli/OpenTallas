#!/usr/bin/env python3
"""Full10928/partial4100 exact BF16 top512 membership, including all-tie case."""
import sys
from pathlib import Path
import numpy as np
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261015)
for frame in range(3):
 n=4100 if frame==2 else 10928
 values=(rng.normal(size=n)*4).astype(np.float32)
 if frame==1:values[:]=1
 bits=(values.view(np.uint32)>>16).astype(np.uint16)
 vals=(bits.astype(np.uint32)<<16).view(np.float32)
 chosen=set(sorted(range(n),key=lambda i:(-float(vals[i]),i))[:512])
 lines=[]
 for a in range(171):
  packed=0
  for q in range(4):
   for l in range(16):
    i=q*2736+a*16+l
    entry=((i<<17)|(int(bits[i])<<1)|1) if i<n else 0
    packed|=entry<<(q*592+l*37)
  lines.append(packed)
 (out/f'lines{frame}.hex').write_text(''.join(f'{v:0592x}\n' for v in lines))
 (out/f'gold{frame}.hex').write_text(''.join(f'{int(i in chosen):x}\n' for i in range(10944)))
 (out/f'scores{frame}.hex').write_text(''.join(f'{int(bits[i]) if i<n else 0:04x}\n' for i in range(10944)))
