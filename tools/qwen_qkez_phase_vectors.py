#!/usr/bin/env python3
"""Canonical QK/exp/Z expectations from actual native FP32-Q/FP8-K vector bytes.
No P.V output or alternate golden reduction order is accepted by this phase gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import qwen_nearhbm_attn_ref as R


def build(path):
    meta=json.loads((path/'meta.json').read_text()); t=meta['ctx']
    if meta['q_heads']!=4 or meta['kv_heads']!=1 or meta['hd']!=128: raise ValueError('native one-head profile required')
    for name,sha in meta['hashes'].items():
        if hashlib.sha256((path/name).read_bytes()).hexdigest()!=sha: raise ValueError(name)
    q=np.array([int(x,16) for x in (path/'q.hex').read_text().split()],dtype=np.uint32).view(np.float32).reshape(4,128)
    rows=(path/'kv.hex').read_text().splitlines()[:t]
    k=R.FP8_VAL[np.array([list(bytes.fromhex(row)[::-1]) for row in rows],dtype=np.uint8)].astype(np.float32)
    sc=[]; ex=[]; ma=[]; ze=[]
    for h in range(4):
        s=R.G.mul(R.G.matvec_il(k,R.G.to_bf16(q[h]),128),R.SCALE)
        m=s.max(); e=R.G.exp(R.G.add(s,R.G.neg(m)))
        sc.extend(R.G.bits(s));ex.extend(R.G.bits(R.G.to_bf16(e))>>16)
        ma.append(R.G.bits(m));ze.append(R.G.bits(R.G.lane_sum(e)))
    hashes={}
    for name,arr in [('score',sc),('exp_bf16',ex),('max',ma),('denom',ze),('recip',R.G.bits(R.G.reciprocal(np.asarray(ze,dtype=np.uint32).view(np.float32))))]:
        p=path/(name+'.hex');p.write_text(''.join(f'{int(x):08x}\n' for x in arr));hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    record=dict(scope='QK_EXP_Z_PHASE_ONLY',ctx=t,score_split=128,denominator_chunk=8,score_words=4*t,exponent_words=4*t,maxima=4,denominators=4,input_hashes=meta['hashes'],phase_hashes=hashes)
    (path/'phase_meta.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('vectors',type=Path);build(p.parse_args().vectors)
