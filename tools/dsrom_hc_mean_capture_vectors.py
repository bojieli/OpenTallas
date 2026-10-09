#!/usr/bin/env python3
"""Run on an admitted remote host. Released h_in or deterministic full-shape fallback."""
import argparse
import json
from pathlib import Path
import numpy as np

def make(out, rank=0, root=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    inputs=[];outputs=[];sources=[]
    for layer in (37,38,39):
        if root:
            path=Path(root)/f'ctx1048576_L{layer}.npz'
            h=np.load(path)['h_in'].astype(np.float32)
            if h.shape!=(4,5120):
                raise ValueError(f'{path}: expected released HC4 x5120, got {h.shape}')
            sources.append(str(path))
        else:
            rng=np.random.default_rng(3700+layer)
            h=rng.standard_normal((4,5120),dtype=np.float32)
            u=h.view(np.uint32)
            h=((u+np.uint32(0x7fff)+((u>>16)&1))&np.uint32(0xffff0000)).view(np.float32)
        h=h[:,rank*1280:(rank+1)*1280].copy()
        # Explicit cancellation witnesses are appended in the synthetic gate;
        # released checkpoint inputs are left byte-identical.
        if not root:
            h[:,0]=np.asarray([1e20,-1e20,1,1],dtype=np.float32)
            bits=h[:,0].view(np.uint32)
            h[:,0]=((bits+np.uint32(0x7fff)+((bits>>16)&1))&np.uint32(0xffff0000)).view(np.float32)
        assert np.isfinite(h).all()
        assert not (h.view(np.uint32)&65535).any(), 'h_in must be exactly BF16'
        acc=h[0].copy()
        for copy in (1,2,3):
            acc=np.add(acc,h[copy],dtype=np.float32)
            acc=np.where(acc==0,np.float32(0),acc).astype(np.float32)
        mean=np.multiply(acc,np.float32(0.25),dtype=np.float32)
        mean=np.where(mean==0,np.float32(0),mean).astype(np.float32)
        u=mean.view(np.uint32)
        bf=((u+np.uint32(0x7fff)+((u>>16)&1))>>16).astype(np.uint16)
        hb=(h.view(np.uint32)>>16).astype(np.uint16)
        for beat in range(160):
            fields=[int(hb[c,beat*8+i]) for c in range(4) for i in range(8)]
            inputs.append(''.join(f'{x:04x}' for x in fields[::-1]))
        for frame in range(40):
            outputs.append(''.join(f'{int(x):04x}' for x in bf[frame*32:(frame+1)*32][::-1]))
    (out/'input.hex').write_text('\n'.join(inputs)+'\n')
    (out/'expected.hex').write_text('\n'.join(outputs)+'\n')
    (out/'source.json').write_text(json.dumps({'shape':[3,4,1280],'rank':rank,
        'source_files':sources,'synthetic_cancellation_witness':not bool(root),
        'arithmetic':'three sequential FP32 adds, FP32*0.25, BF16 RNE'},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--rank',type=int,choices=range(4),default=0)
    p.add_argument('--released-root');a=p.parse_args()
    make(a.out,a.rank,a.released_root)
