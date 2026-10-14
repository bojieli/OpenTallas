#!/usr/bin/env python3
"""Same-case canonical normalization fixtures for actual RTL pair outputs."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import qwen_nearhbm_attn_ref as R
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--pair0',type=Path,required=True);p.add_argument('--pair1',type=Path,required=True);a=p.parse_args()
R.NH,R.KVH,R.GQ,R.GROUPS=4,1,4,3072;R.S_SC,R.S_PV=R.G.attn_splits(128,3072)
q,k,v=R.make_case(8192,1,'normal');gold=R.golden_die(q,k,v);den=[]
for h in range(4):
 sc=R.G.mul(R.G.matvec_il(k[:,0,:],R.G.to_bf16(q[h]),128),R.SCALE)
 e=R.G.exp(R.G.add(sc,R.G.neg(sc.max())));den.append(R.G.lane_sum(e))
rz=R.G.reciprocal(np.array(den,dtype=np.float32));x=np.fromfile(a.pair0,dtype='<u4').view(np.float32).reshape(4,128);y=np.fromfile(a.pair1,dtype='<u4').view(np.float32).reshape(4,128)
assert R.same_bits(R.G.mul(R.G.add(x,y),rz[:,None]),gold)
a.out.mkdir(parents=True,exist_ok=True);(a.out/'pair0.bin').write_bytes(a.pair0.read_bytes());(a.out/'pair1.bin').write_bytes(a.pair1.read_bytes());R.G.bits(rz).astype('<u4').tofile(a.out/'reciprocal.bin');R.G.bits(gold).astype('<u4').tofile(a.out/'gold.bin')
r=dict(context=8192,position=8191,query_heads=4,kv_heads=1,groups=3072,splits=[128,256],source_pair0=str(a.pair0),source_pair1=str(a.pair1),files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.glob('*.bin')},scope='ACTUAL_RTL_PAIR_OUTPUTS_PLUS_GOLDEN_RECIPROCAL; FULL_QKZ_INTEGRATION_PENDING')
(a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
