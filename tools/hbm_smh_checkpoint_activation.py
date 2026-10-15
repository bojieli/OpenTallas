#!/usr/bin/env python3
"""Externalactivation stimuli and golden answers only; never supplies DUT results."""
import hashlib,json
from pathlib import Path
import numpy as np
import dshbm_matched_sm_seq as MS
import hdc_golden_v41 as V
import rtl_gpu_sm_exact as S
ROOT=Path(__file__).resolve().parents[1]
def build():
 p=ROOT/'results/rtl/hbm_smh_static_feed_1014/checkpoint_wqa_rank0_verified';out=ROOT/'results/rtl/hbm_smh_static_feed_1014/native_activation';out.mkdir(exist_ok=True)
 rng=np.random.default_rng(20261015);X=[(rng.standard_normal(5120)*(.1*(n+1))).astype(np.float32) for n in range(8)]
 xcase=MS.gen_op('v41_fp8',1,5120,8,np.random.default_rng(13),X=X)
 (out/'xw.hex').write_text(''.join(f'{x:06304x}\n' for x in xcase['xw']))
 for sm in range(13):
  lines=[int(t,16) for t in (p/f'sm{sm:02d}.lines.hex').read_text().split()];wc=np.zeros((160,32),dtype=np.uint8);we=np.zeros(160,dtype=np.int64)
  for word,(r,g,t) in zip(lines,S.issue_order(1,5,8,True)):
   for j in range(4):
    b=(g*4+j)*8+t
    wc[b]=[(word>>(256*j+8*i))&255 for i in range(32)];we[b]=((word>>(1024+8*j))&255)-127
  gold=[]
  for x in X:
   xq,xe=V.quant_fp8(x);wq=V.E4M3[wc].astype(np.float64)
   terms=np.array([np.ldexp(np.float32(wq[b]@xq[b*32:(b+1)*32]),int(we[b]+xe[b])) for b in range(160)],dtype=np.float32)
   y=V.csum(terms.reshape(1,-1))[0];gold.append(int(np.array(y,dtype=np.float32).view(np.uint32)))
  (out/f'sm{sm:02d}.gold.hex').write_text(f'{sum(v<<(32*n) for n,v in enumerate(gold)):064x}\n')
 (out/'receipt.json').write_text(json.dumps(dict(seed=20261015,scope='declaredexternalSMactivationboundary; actualVMproducerunbound',shape=[8,5120],xw_addresses=40,xw_beats_per_address=13,xw_source_sha256=hashlib.sha256((out/'xw.hex').read_bytes()).hexdigest(),reference='originalgen_op xwritepacking; releasedcheckpointE4M3decode/UE8M0terms +V.csum golden chunkorder onlyoutsideDUT',source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['tools/hbm_smh_checkpoint_activation.py','tools/dshbm_matched_sm_seq.py','tools/hdc_golden_v41.py','tools/rtl_gpu_sm_exact.py']}),indent=2)+'\n')
if __name__=='__main__':build()
