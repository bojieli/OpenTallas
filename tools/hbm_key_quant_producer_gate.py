#!/usr/bin/env python3
"""Remote minimum key quantizer gate: independent golden vs actual arithmetic."""
import argparse, hashlib, json, subprocess
from pathlib import Path
import numpy as np
from rtl_hdc_v41_blockdot_campaign import aq_expect, hexw, G
ROOT=Path(__file__).resolve().parents[1]
RTL=['rtl/hbm_accel/index/ot_hbm_key_quant_producer.sv',
 'rtl/hdc/v41/ot_hdc_actquant.sv','rtl/hdc/ot_hdc_delay.sv',
 'rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
 'rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/test/hbm_accel/tb_hbm_key_quant_producer.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);a.out=a.out.resolve()
 rng=np.random.default_rng(20261009);inputs=[];outputs=[]
 for k in range(32):
  payload=0
  for b in range(4):
   x=(rng.standard_normal(32)*10.**rng.uniform(-25,25)).astype(np.float32)
   if k==0:x[:]=np.float32(0)
   if k==1:x=rng.choice(np.array([0.,-0.,1e-45,-1e-45,2.**-126],np.float32),32)
   if k==2:x=G.to_bf16(x)
   f,e,codes,_=aq_expect(x,True)
   assert not f and -127<=e<=125
   inputs.append(f'{hexw(G.bits(x),32):0256x}')
   payload|=hexw([int(c)&15 for c in codes],4)<<(128*b)
   payload|=(e+127)<<(512+8*b)
  outputs.append(f'{payload:0136x}')
 (a.out/'input.hex').write_text('\n'.join(inputs)+'\n')
 (a.out/'expected.hex').write_text('\n'.join(outputs)+'\n')
 record={'scope':'actual128-element FP4 arithmetic+68-byte retention only; projection/norm/RoPE/HBM fence unbound',
  'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in RTL},'cases':{}}
 for name,mut in [('positive',False),('packing_mutant',True)]:
  paths=[ROOT/n for n in RTL]
  if mut:
   src=(ROOT/RTL[0]).read_text().replace('q[8*l+:4]','q[8*l+4+:4]')
   assert src!=(ROOT/RTL[0]).read_text()
   mp=a.out/'mutant.sv';mp.write_text(src);paths[0]=mp
  exe=a.out/(name+'.vvp')
  with (a.out/(name+'.compile.log')).open('w') as log:
   rc=subprocess.call(['iverilog','-g2012','-s','tb_hbm_key_quant_producer','-o',str(exe),*[str(x) for x in paths]],stdout=log,stderr=subprocess.STDOUT)
  if rc:raise RuntimeError(f'{name} elaboration failed')
  with (a.out/(name+'.log')).open('w') as log:
   rc=subprocess.call(['vvp',str(exe),f'+INPUT={a.out}/input.hex',f'+EXPECTED={a.out}/expected.hex'],stdout=log,stderr=subprocess.STDOUT)
  record['cases'][name]={'rc':rc,'expected':1 if mut else 0}
  assert (rc!=0)==mut
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
