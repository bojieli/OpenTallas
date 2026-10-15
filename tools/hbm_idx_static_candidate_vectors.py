#!/usr/bin/env python3
import sys
from pathlib import Path
import numpy as np
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(101503)
rank=3;n=10928
bits=((rng.normal(size=n).astype(np.float32).view(np.uint32)>>16)&65535).tolist()
def gid(i):return 8*(96*(i//8)+rank)+(i%8)
def key(x):return (~x&65535)if x&32768 else x^32768
pos=gid(n-1)
inputs=[];outputs=[]
for frame in range(3):
 for a in range(171):
  si=0;co=0
  for q in range(4):
   vals=[];ids=[];lv=0
   for l in range(16):
    i=q*2736+a*16+l;ids.append(gid(i)&((1<<20)-1));v=bits[i] if i<n else 0
    if frame==1:v=65408 # allmasked still newest pinned ifvalid
    if i<n:lv|=1<<l
    vals.append(v)
   score=(sum(x<<(20*j)for j,x in enumerate(ids))<<290)|(sum(x<<(16*j)for j,x in enumerate(vals))<<34)|(lv<<18)|((a==170)<<1)|1
   si|=score<<(q*610)
   cv=[];ci=[];clv=0
   for b in range(2):
    xs=[vals[b*8+j]if(lv>>(b*8+j))&1 else 65408 for j in range(8)]
    if(ids[b*8]>>3)==pos>>3 and((lv>>(b*8))&1):xs[0]=32640
    mx=max(xs,key=key);cv.append(mx);ci.append(ids[b*8]>>3)
    if mx!=65408:clv|=1<<b
   c=(sum(x<<(17*j)for j,x in enumerate(ci))<<38)|(sum(x<<(16*j)for j,x in enumerate(cv))<<6)|(clv<<4)|(q<<2)|((a==170)<<1)|1
   co|=c<<(q*72)
  inputs.append(si);outputs.append(co)
(out/'candidate_in.hex').write_text(''.join(f'{x:0610x}\n'for x in inputs))
(out/'candidate_gold.hex').write_text(''.join(f'{x:072x}\n'for x in outputs))
(out/'candidate_pos.hex').write_text(f'{pos:05x}\n')
