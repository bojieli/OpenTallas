#!/usr/bin/env python3
"""One pinned seed for full-shape enabled SFU64 / HC_POST64 parent gates.
Golden arithmetic comes from hdc_golden_v41 and the established HC-post
lowering order. No data or expected word is inferred from the DUT.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden as G
import hdc_golden_v41 as V
import dsrom_su_hcpost as H
F=np.float32
SEED=20261006

def bits(x):return np.asarray(x,dtype=F).view(np.uint32)
def pack(words):return sum(int(w)<<(32*i) for i,w in enumerate(words))
def write(path,rows,width):
 path.write_text(''.join(f'{int(r):0{(width+3)//4}x}\n' for r in rows))

def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);p=a.parse_args()
 p.out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(SEED)
 sr=[];sy=[]
 for idx,fn in enumerate(list(range(8))+[3,3]):
  x=(rng.integers(-128,129,64).astype(F)/F(16)).astype(F)
  if fn in (2,3):x=(np.abs(x)+F(.125)).astype(F)
  error=idx==8
  if error:x[0]=F(-1)
  with np.errstate(all='ignore'):
   eg=lambda z:V.sigmoid(np.where(z<F(0),G.neg(V.sqrt(np.maximum(np.abs(z),F(1e-6)).astype(F))),V.sqrt(np.maximum(np.abs(z),F(1e-6)).astype(F))).astype(F))
   funcs=[lambda z:z,G.exp,G.rsqrt,V.sqrt,V.sigmoid,V.silu,lambda z:V.sqrt(V.softplus(z)),eg]
   y=np.asarray(funcs[fn](x),F)
  if error:y[0]=F(0) # IEEE sqrt refusal: actual primitive returns 0 plus fault.
  assert np.all(np.isfinite(y))
  tag=0xc5000000+idx
  sr.append(pack(bits(x)) | (fn<<2048) | (tag<<2051))
  sy.append(pack(bits(y)) | (int(error)<<2048) | (tag<<2049))
 write(p.out/'sfu_req.mem',sr,2083);write(p.out/'sfu_exp.mem',sy,2081)
 hr=[];hy=[]
 for idx in range(3):
  res=(rng.integers(-8192,8193,(4,64)).astype(F)/F(256)).astype(F)
  y=(rng.integers(-8192,8193,64).astype(F)/F(256)).astype(F)
  comb=(rng.integers(-128,129,(4,4)).astype(F)/F(64)).astype(F)
  post=(rng.integers(-128,129,4).astype(F)/F(64)).astype(F)
  if idx==1:
   # Real cancellation/rounding sensitivity, still finite and golden ordered.
   res[:,0]=[F(1e8),F(-1e8),F(.125),F(.0625)];comb[:,0]=F(1);post[0]=F(.03125)
  out=H.golden(res,y,comb,post).reshape(4,64).T.reshape(-1)
  rwords=res.T.reshape(-1)
  tag=0xc6000000+idx
  request=pack(bits(np.concatenate([rwords,y,comb.reshape(-1),post]))) | (tag<<10880)
  result=pack(bits(out)) | (tag<<8193)
  hr.append(request);hy.append(result)
 write(p.out/'hc_req.mem',hr,10912);write(p.out/'hc_exp.mem',hy,8225)
 sources=['tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/dsrom_su_hcpost.py',str(Path(__file__).relative_to(ROOT))]
 meta=dict(seed=SEED,SFU=dict(lanes=64,cases=len(sr),opcodes=list(range(8)),fault_then_clean=[8,9]),
           HC_POST=dict(groups=64,outputs=256,cases=len(hr),golden_order='mul r0*c0+r1*c1, add r2, add r3, add y*p, BF16 RNE'),
           sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},
           files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.out.glob('*.mem')},
           scope='One seeded full-shape parent cohort per family; enabled gates not yet run')
 (p.out/'vectors.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
if __name__=='__main__':main()
