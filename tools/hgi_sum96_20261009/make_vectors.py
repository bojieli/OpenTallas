#!/usr/bin/env python3
"""Standalone CF-COLL candidate vectors: full96 ranks x256 words.
Numerical additions call the repository's independent DS golden. The normative
hbm-sim vector substitution is still required before endpoint adoption.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(96256)
x=rng.integers(-4096,4097,size=(4,96,256)).astype(np.float32)/np.float32(32)
x[0]=0;x[0,::2]=np.uint32(0x80000000).view(np.float32)
x[1,:,::3]=np.float32(2**24);x[1,1::3,::3]=np.float32(-2**24);x[1,2::3,::3]=np.float32(1)
x[2,:,0]=np.array([1,-1]*48,dtype=np.float32)
def tree(a):
 while len(a)>1:
  a=np.concatenate((G.add(a[0:len(a)//2*2:2],a[1:len(a)//2*2:2]),a[-1:]),axis=0) if len(a)%2 else G.add(a[::2],a[1::2])
 return a[0]
def line(a):return ''.join(f'{int(v):08x}' for v in a.view(np.uint32).reshape(-1)[::-1])
p=[];y=[]
for case in x:
 partial=np.stack([tree(case[g*8:g*8+8]) for g in range(12)])
 expected=tree(case)
 assert np.array_equal(tree(partial).view(np.uint32),expected.view(np.uint32))
 for tile in range(16):
  p.append(line(partial[:,tile*16:(tile+1)*16]));y.append(line(expected[tile*16:(tile+1)*16]))
(out/'partials.hex').write_text('\n'.join(p)+'\n');(out/'expected.hex').write_text('\n'.join(y)+'\n')
(out/'vectors.json').write_text(json.dumps({'cases':4,'ranks':96,'words_per_case':256,'tree':'adjacent rankpairs; oddsubtree carried','golden_source_sha256':hashlib.sha256(Path(G.__file__).read_bytes()).hexdigest(),'partial_lines':len(p),'status':'independentDSgolden candidate; normativehbm-sim pending'},indent=2)+'\n')
