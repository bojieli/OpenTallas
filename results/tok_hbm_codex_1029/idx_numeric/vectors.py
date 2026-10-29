"""Independent FP4 golden applied to request-addressed six-row VM contents."""
import sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'tools'))
import hdc_golden_v41 as g
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(102903)
levels=np.array([0,.5,1,1.5,2,3,4,6.])
mem=[0]*65536;gold=[]
for row in range(6):
 x=(rng.normal(size=(32,128))*np.exp2(rng.integers(-10,8,size=(32,1)))).astype(np.float32)
 for h in range(32):
  codes=scales=0
  for b in range(4):
   v=x[h,b*32:b*32+32]
   a=np.maximum(np.max(np.abs(v)),g.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
   e=int(g._ceil_log2(g.mul(a,g.FP4_MAX_INV)))
   q=g._round_grid(np.clip(v.astype(np.float64)*np.exp2(-e),-6,6),0,1)
   nib=[int(np.argmin(abs(levels-abs(t))))+(8 if orig<0 else 0) for t,orig in zip(q,v)]
   codes|=sum(n<<(4*(b*32+i)) for i,n in enumerate(nib));scales|=(e+127)<<(b*8)
   words=v.view(np.uint32)
   for base in [0x4400,0x6400]:
    for s in range(4):mem[base+row*512+(h*4+b)*4+s]=sum(int(w)<<(i*32) for i,w in enumerate(words[s*8:s*8+8]))
  w=0x3f00+row*32+h;gold.append((w,scales,codes))
  for base in [0x4000,0x6000]:mem[base+row*8+h//16]|=w<<((h%16)*16)
(out/'vm.hex').write_text(''.join(f'{v:064x}\n' for v in mem))
(out/'gold.hex').write_text(''.join(f'{w:04x}{s:08x}{c:0128x}\n' for w,s,c in gold))
