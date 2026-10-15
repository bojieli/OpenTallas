#!/usr/bin/env python3
"""Fixed native scalar SIDE calendar with actual mapped SRAM inputs/outputs."""
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import hdc_golden_v41 as V
from sfu_control_image import pack
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(37162104)
ops=[('RSQRT',2,False),('SQRT',3,False),('SPSQRT',6,False),('EGATE',7,False),('DIVIMM_EPS_RSQRT',2,True)]
seeds=[];golds=[];rs=[];controls=[]
def addr(row):return ((row>>7)<<16)|((row&127)<<7)
for op,(name,fn,norm) in enumerate(ops):
 vals=np.exp2(rng.uniform(-8,8,64)).astype(np.float32) if fn in [2,3] else rng.uniform(-90,90,64).astype(np.float32)
 if fn==7:vals[:8]=np.array([0,-0.,1e-8,-1e-8,1e-6,-1e-6,.25,-.25],dtype=np.float32)
 data=np.full(512,np.float32(.125+op),dtype=np.float32);data[:64]=vals
 r=G.add(V.div(vals,np.float32(512)),np.float32(1e-6)) if norm else vals
 if fn==2:y=G.rsqrt(r)
 elif fn==3:y=V.sqrt(r)
 elif fn==6:y=V.sqrt(V.softplus(r))
 else:
  mag=V.sqrt(np.maximum(np.abs(r),np.float32(1e-6)).astype(np.float32));y=V.sigmoid(np.where(r<0,G.neg(mag),mag).astype(np.float32))
 seeds.extend(G.bits(data));golds.extend(G.bits(y));rs.extend(G.bits(r))
 for c in range(320):
  idx=max(0,min(63,c-8))
  f=dict(ld=int(c==0),no=1,ni=8192,ls=0,lvw=0,dst=1,co_dst=1,
   emit=int(8<=c<72),i_v=idx*128,vb=sum(addr((s*64 if s<4 else 256)+idx)<<(s*24) for s in range(5)),
   ci_sfu=fn,cs_sfu=fn)
  if norm:f.update(cp_m1=5,cm_m1=5,cp_imm1=0x44000000,cm_imm1=0x44000000,ca_ad=4,ca_imm2=0x358637bd)
  controls.append(pack(f))
for name,items,width in [('seed',seeds,8),('gold',golds,8),('r',rs,8),('control',controls,436)]:
 (out/(name+'.hex')).write_text(''.join(f'{int(x):0{width}x}\n' for x in items))
(out/'manifest.json').write_text(json.dumps(dict(ops=ops,inputs_per_op=64,cycles_per_op=320,total_scalar_outputs=320,actual_scalar_capacity=1,SRAM_readers=6,SRAM_read_extra_edges=2,SRAM_write_extra_edges=1,programme='raw1742 compiler ABI, one registered nativeheadbroadcast; normativeDIVIMM512+EPS1e-6→RSQRT actual19edgeM1'),indent=2)+'\n')
