#!/usr/bin/env python3
"""Fixed64-issue component programme for actual FULL lane+SIDE, common833.

Independent NumPy/hdc_golden arithmetic, including the specified softplus
polynomial order. This is a source component fixture, not a full layer price.
"""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/hbm_static')]
from hdc_golden import add,mul,exp,neg,rsqrt,z
from su_arith_compile import pack,physical_word
F=np.float32
CYC=384
OPS=[('EXP',1),('SIGM',4),('SILU',5),('RSQRT',2),('SQRT',3),('SPSQRT',6),('EGATE',7),('BYP',0)]
def div(a,b):return z(F(a/b))
def sqrt(a):return z(np.sqrt(a).astype(F))
def softplus_sqrt(a):
 t=exp(neg(np.abs(a)));u=div(t,add(t,F(2)));u2=mul(u,u)
 coeff=np.array([0x3D70F0F1,0x3D888889,0x3D9D89D9,0x3DBA2E8C,0x3DE38E39,0x3E124925,0x3E4CCCCD,0x3EAAAAAB,0x3F800000],np.uint32).view(F)
 p=np.full_like(a,coeff[0])
 for c in coeff[1:]:p=add(mul(p,u2),c)
 return sqrt(add(np.maximum(a,F(0)),mul(mul(u,p),F(2))))
def value(fn,a):
 if fn==1:return exp(a)
 if fn in(4,5):return div(a if fn==5 else np.ones_like(a),add(exp(neg(a)),F(1)))
 if fn==2:return rsqrt(a)
 if fn==3:return sqrt(a)
 if fn==6:return softplus_sqrt(a)
 if fn==7:
  s=np.copysign(sqrt(np.maximum(np.abs(a),F(1e-6))),a)
  return div(np.ones_like(a),add(exp(neg(s)),F(1)))
 return a

def main():
 out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
 lane=np.arange(512,dtype=F)
 data=np.stack([F(.25)+(lane%29)*F(.03125)+(r%64)*F(.0078125) for r in range(512)])
 # Positive finite fixture covers every function without invalid-domain inputs.
 a=data[:64].copy()
 (out/'seed.mem').write_text('\n'.join(f'{x:08x}' for x in data.view(np.uint32).ravel())+'\n')
 depths={0:0,1:64,4:87,5:87,2:49,3:31,6:198,7:120}
 terms=sum((1<<k)<<(24*(s*10+k)) for s in range(5) for k in range(7))
 images=[];gold=[];info=[]
 for name,fn in OPS:
  gold.extend(value(fn,a).view(np.uint32).ravel())
  # Standing selectors/destination remain live through the final consumer.
  ctl=dict(no=1,ni=8192,ls=7,lvw=0,dst=1,co_dst=1,ci_sfu=fn,cs_sfu=fn)
  for cycle in range(CYC):
   combined=0;v=max(0,min(63,cycle-8))
   for q in range(4):
    fields=dict(ctl,ld=int(cycle==0),ld_c=terms,emit=int(8<=cycle<72),i_v=v*128,
      vb=sum(physical_word(q,(s*64 if s<4 else 256)+v)<<(s*24) for s in range(5)))
    combined|=pack(fields)<<(q*1742)
   images.append(combined)
  info.append(dict(op=name,side_code=fn,issue_to_output=29+depths[fn],first_output=41+depths[fn]))
 (out/'gold.mem').write_text('\n'.join(f'{x:08x}' for x in gold)+'\n')
 (out/'control.mem').write_text('\n'.join(f'{x:01742x}' for x in images)+'\n')
 (out/'first.mem').write_text('\n'.join(f'{x["first_output"]:08x}' for x in info)+'\n')
 (out/'programme.json').write_text(json.dumps(dict(qualified=False,scope='common833 FULL lane plus SIDE component',MLAT=4,ALAT=4,PINREG=1,cycles_per_op=CYC,issues_per_op=64,ops=info),indent=2)+'\n')
if __name__=='__main__':main()
