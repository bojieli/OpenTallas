#!/usr/bin/env python3
"""One bounded CPU fixture: exact R-ARITH bits/counts and 8192 timing."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
import hdc_golden as G
from hdc_reduce_chunked_vectorized import reduce_chunked_vectorized
from hdc_reduce_chunked_vectorized_hook import install


def run():
    rng=np.random.default_rng(47)
    reference=G.reduce_chunked
    cases=[('finite',n,rng.standard_normal(n).astype(G.F))
           for n in (0,1,7,8,9,15,16,17,63,64,65,8192)]
    for n in (9,8192):
        sub=G.from_bits(np.resize(np.array([1,0x80000001,0x007fffff,0x807fffff,0x00010000,0x80010000,0,0x80000000],dtype=np.uint32),n))
        cancel=np.resize(np.array([2**24,1,-2**24,1,1,-1,0,-0.0],dtype=G.F),n)
        zeros=G.from_bits(np.resize(np.array([0,0x80000000],dtype=np.uint32),n))
        cases.extend([('subnormal',n,sub),('cancellation',n,cancel),('signed_zero',n,zeros)])
    checks=[]
    for kind,n,v in cases:
        values=[];counts=[];calls=[]
        for fn in (reference,reduce_chunked_vectorized):
            tally=[0,0];original_add=G.add
            def counted(a,b):
                tally[0]+=int(np.prod(np.broadcast_shapes(np.shape(a),np.shape(b))))
                tally[1]+=1
                return original_add(a,b)
            with patch.object(G,'add',counted):values.append(int(G.bits(fn(v))))
            counts.append(tally[0]);calls.append(tally[1])
        assert values[0]==values[1],(kind,n,'raw uint32 differs',values)
        assert counts[0]==counts[1],(kind,n,'missing-tail or padding added arithmetic',counts)
        chunks=max(1,(n+7)//8);padded=1<<(chunks-1).bit_length()
        assert counts[0]==n+padded-1,(kind,n,'scalar arithmetic count')
        if n==8192:assert calls[1]==18,(kind,n,'eight offset + ten tree calls')
        checks.append(dict(kind=kind,length=n,exact_uint32=True,scalar_adds=counts[0],original_calls=calls[0],vectorized_calls=calls[1]))
    v=rng.standard_normal(8192).astype(G.F)
    timing=[];bits=[]
    for fn in (reference,reduce_chunked_vectorized):
        start=time.perf_counter();value=fn(v);timing.append(time.perf_counter()-start);bits.append(int(G.bits(value)))
    assert bits[0]==bits[1]
    assert install(G,enabled=False) is False and G.reduce_chunked is reference
    try:
        assert install(G,enabled=True) and G.reduce_chunked is reduce_chunked_vectorized
        assert int(G.bits(G.lane_sum(v)))==bits[0]
    finally:G.reduce_chunked=reference
    root=Path(__file__).parent
    sources=['hdc_golden.py','hdc_reduce_chunked_vectorized.py','hdc_reduce_chunked_vectorized_hook.py','test_hdc_reduce_chunked_vectorized.py']
    return dict(verdict='PASS_EXACT_HOST_CHUNK8_COMPONENT',scope='one CPU component fixture; no producer/inference/GPU/hardware/rate qualification',checks=checks,default_off_hook_pass=True,timing=dict(length=8192,reference_seconds=timing[0],vectorized_seconds=timing[1],speedup=timing[0]/timing[1],exact_uint32=True),source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=run()
    with args.output.open('x') as file:json.dump(result,file,indent=2);file.write('\n')
    print(json.dumps(result['timing']))
