#!/usr/bin/env python3
"""Actual Machine SU semantics on explicit golden-score component boundary."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from hgi_sim import machine as MC
from hgi_sim.records import MDesc,Rec
from hgi_sim.qwen_compiler import sut
import hdc_isa_v41 as I
p=argparse.ArgumentParser();p.add_argument('--scores',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
cfg=ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json';C=json.loads(cfg.read_text());assert C['head_dim']==512
scale=int(np.asarray(np.float32(C['head_dim']**-0.5)).view(np.uint32))
packed=[int(x,16) for x in a.scores.read_text().split()];assert len(packed)==768
meta=dict(qualification=False,boundary='Explicit golden QK score image used by live numerical HG1 proof; not actual RTL score-producer qualification',input_sha256=hashlib.sha256(a.scores.read_bytes()).hexdigest(),config_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),head_dim=512,scale_fp32_hex=f'{scale:08x}',H=16,T=[128,640],arith='Actual hgi_sim.machine.u_su_vop SFU_EXP and RED_SUM from Machine; no replacement polynomial',VM_fixture_word_bases=dict(SC=0,MB=1024,E=2048,SE=4096,EB=8192),native_allocation=False)
offset=0
for T in (128,640):
 out={k:[] for k in ['SC','MB','E','SE','EB']}
 for h in range(16):
  raw=[(packed[offset+r]>>(h*33))&0xffffffff for r in range(T)]
  assert all(((packed[offset+r]>>(h*33+32))&1)==0 for r in range(T))
  die=MC.Die(0,MC.Hbm());M=MC.Machine([die]);die.vm[:T]=np.asarray(raw,dtype=np.uint32)
  def V(base,n=1,bcast=False):return MDesc(space='VM',fmt='FP32',base=base,n=n,ibcast=int(bcast))
  records=[Rec('SU','VOP',sut=sut(m1=I.M1_AIMM,imm1=scale,red=I.RED_MAX,red_whole=1),desc=dict(A=V(0,T),R=V(1024)),tag='attend.max'),
   Rec('SU','VOP',sut=sut(m1=I.M1_AIMM,imm1=scale,ad=I.AD_NEGB,sfu=I.SFU_EXP,red=I.RED_SUM,red_whole=1,dst=I.DST_VM),desc=dict(A=V(0,T),B=V(1024,T,True),O=V(2048,T),R=V(4096)),tag='attend.exp_sum'),
   Rec('SU','VOP',sut=sut(rnd=1,dst=I.DST_VM),desc=dict(A=V(2048,T),O=V(8192,T)),tag='attend.bf16_p')]
  for record in records:MC.u_su_vop(M,record,0)
  for name,base,n in [('SC',0,T),('MB',1024,1),('E',2048,T),('SE',4096,1),('EB',8192,T)]:out[name].extend(int(v) for v in die.vm[base:base+n])
 for name,values in out.items():
  (a.out/f'{name}{T}.hex').write_text(''.join(f'{v:08x}\n' for v in values))
 offset+=T
meta['output_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.glob('*.hex')}
meta['source_sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'tools/hgi_sim/machine.py',ROOT/'tools/hgi_sim/lib.py',ROOT/'tools/hdc_golden.py',ROOT/'tools/hgi_sim/ds_native.py',Path(__file__).resolve()]}
(a.out/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n');print('PASS actualMachine SC→MB→E/SE→BF16EB fixture H16 T128/640 scale'+meta['scale_fp32_hex'])
