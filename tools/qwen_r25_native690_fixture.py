"""Deterministic full-shape native quarter inputs and independent golden outputs.

Call only on admitted remote jobs. Returns actual VM bits, constants and
quarter-disjoint expected address ranges; no service ready/completion model.
"""
import numpy as np
import qwen_r25_native690 as B

def fixture(stage,tools,*,valid=8192,quarter=0,position=8191,seed=8195):
    if not 0<=quarter<4:raise ValueError('quarter')
    S,R,C,I=B.load(tools);G,V=S.G,S.V
    m=C.Mem(np.zeros(1<<C.VMA,np.uint32),np.zeros(1<<C.KVA,np.uint32),np.zeros((1<<C.CRA,2),np.uint32),np.zeros(1<<C.WRA,np.uint16))
    rng=np.random.default_rng(seed);checks=[]
    if stage=='rmsnorm4096':
        x=rng.standard_normal(4096).astype(np.float32);gain=rng.uniform(.1,2,4096).astype(np.float32)
        m.vm[229376:233472]=C.fbits(x);m.vm[237568:241664]=C.fbits(gain)
        inv=G.rsqrt(G.add(G.mul(V.csum(G.mul(x,x)),np.float32(1/4096)),np.float32(1e-6)))
        want=G.to_bf16(G.mul(G.mul(x,inv),gain))
        lo=quarter*1024;checks=[(lo,C.fbits(want[lo:lo+1024])),(220000+quarter,np.atleast_1d(C.fbits(inv)))]
    elif stage=='softmax8x8224':
        if not 8192<=valid<=8195:raise ValueError('causal valid length')
        x=rng.uniform(-15,15,(8,B.CAP)).astype(np.float32);x[:,valid:]=np.nan
        m.vm[:8*B.CAP]=C.fbits(x).reshape(-1)
        m.vm[B.EXP:B.PUB+8*B.CAP]=0x7fc00001;m.vm[B.MP:B.T2+32]=0x7fc00001
        e=G.exp(G.add(x[:,:valid],G.neg(x[:,:valid].max(axis=1)[:,None])))
        want=np.zeros((8,B.CAP),np.float32);want[:,:valid]=G.to_bf16(e)
        den=V.csum(e);head=quarter*2
        checks=[(B.PUB+head*B.CAP,C.fbits(want[head:head+2]).reshape(-1)),(B.Z+head,C.fbits(den[head:head+2]))]
    else:raise ValueError('fixture currently binds full RMS and causal softmax')
    assert m.vm[B.ZERO]==0
    return m,checks


def write(stage,tools,out,**kwargs):
    from pathlib import Path
    S,R,C,I=B.load(tools);m,checks=fixture(stage,tools,**kwargs)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    C.write_hex(out/'VM.hex',m.vm,32)
    for k,(addr,want) in enumerate(checks):C.write_hex(out/f'CHECK{k}_{addr}.hex',want,32)
    return checks
