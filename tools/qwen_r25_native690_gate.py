#!/usr/bin/env python3
"""Execute compiled native690 ROM words with exact quarter layouts/reference.

This is compiler arithmetic/ABI evidence, not quarter RTL execution. RTL parent
must consume these same words through the finite ROM/dispatcher/provider.
"""
import argparse,json,resource
from pathlib import Path
import numpy as np
import qwen_r25_native690 as B

def decode(C,w):
    return {name:(w>>C.POFF[name][0])&((1<<bits)-1) for name,bits in C.PFIELDS}

def read_banks(path):
    return [[int(x,16) for x in (path/f'Q{q}.hex').read_text().split()] for q in range(4)],[int(x,16) for x in (path/'META.hex').read_text().split()]

def execute(C,mem,banks,metadata,stage,valid=8192,mutation=None):
    fault=False;ops=0
    for pc in range(stage['pc'],stage['pc']+stage['count']):
        meta=metadata[pc];assert meta>>41==1
        mask=(meta>>37)&15;window=(meta>>36)&1;row0=(meta>>16)&((1<<20)-1);rows=meta&65535
        if window and row0>=valid and mutation!='unmasked_tail':continue
        for q in range(4):
            if not (mask>>q)&1:continue
            f=decode(C,banks[q][pc])
            if window:f['nin']=min(rows,valid-row0)
            if mutation=='unmasked_tail' and window:f['nin']=rows
            if mutation=='round_before_sum' and f['red'] and f['sfu']:f['rnd']=1
            if mutation=='missing_gain' and f['e1']==C.I.E1_MULC:f['e1']=C.I.E1_BYP
            if mutation=='wrong_rope_sign' and f['qm']==C.I.QM_POS:f['qm']=C.I.QM_NEG
            if mutation=='wrong_silu' and f['sfu']==C.I.SFU_SILU:f['sfu']=C.I.SFU_SIGM
            lay=C.layout(f,256,64)
            if lay['bad']:raise AssertionError('clipped instruction exceeds real quarter layout')
            if mutation is None and f['red']==C.I.RED_SUM:
                out,finite,_=C.elements(f,mem)
                values=C.G.mul(out,out) if f['redsq'] else out
                segments=values.reshape(f['nout'],f['nin'])
                for sg in segments:
                    if C.unit_sum(sg,lay['S'],lay['vw'])!=C.fbits(C.V.csum(sg)):
                        raise AssertionError('actual N256/M64 reducer tree changed chunk8 order')
            ok,*_=C.ref_op(f,mem);fault|=not ok;ops+=1
    return dict(nonfinite=fault,quarter_instructions=ops)

def memory(C):
    return C.Mem(np.zeros(1<<C.VMA,np.uint32),np.zeros(1<<C.KVA,np.uint32),np.zeros((1<<C.CRA,2),np.uint32),np.zeros(1<<C.WRA,np.uint16))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tools',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    S,R,C,I=B.load(a.tools);G=S.G;V=S.V
    a.out.mkdir(parents=True,exist_ok=False)
    # Model artifact exists before actual native compilation.
    (a.out/'model_before_compile.json').write_text(json.dumps(B.model(),indent=2)+'\n')
    c=B.Compiler(S,R,C,I).build();c.write(a.out/'rom')
    banks,metadata=read_banks(a.out/'rom');assert C.PW==690
    for e in c.entries:
        for q,f in enumerate(e['fields']):
            if f is not None:assert decode(C,banks[q][e['pc']])==f
    rng=np.random.default_rng(8195);results=[]
    for mutant in (False,True):
        # Exact full RMS tree duplicated; only outputs split between quarters.
        m=memory(C);x=rng.standard_normal(4096).astype(np.float32);gain=rng.uniform(.1,2,4096).astype(np.float32)
        m.vm[229376:233472]=C.fbits(x);m.vm[237568:241664]=C.fbits(gain)
        want=G.to_bf16(G.mul(G.mul(x,G.rsqrt(G.add(G.mul(V.csum(G.mul(x,x)),np.float32(1/4096)),np.float32(1e-6)))),gain))
        rec=execute(C,m,banks,metadata,c.stages['rmsnorm4096'],mutation='missing_gain' if mutant else None)
        mism=int(np.count_nonzero(m.vm[:4096]!=C.fbits(want)));assert bool(mism)==mutant and not rec['nonfinite']
        results.append(dict(stage='rmsnorm4096',negative=mutant,mismatches=mism,**rec))
    for mutant in (False,True):
        m=memory(C);x=rng.standard_normal((10,128)).astype(np.float32);qg=rng.uniform(.1,2,128).astype(np.float32);kg=rng.uniform(.1,2,128).astype(np.float32)
        m.vm[:1280]=C.fbits(x).reshape(-1);m.vm[8192:8320]=C.fbits(qg);m.vm[8320:8448]=C.fbits(kg)
        r=G.rsqrt(G.add(G.mul(V.csum(G.mul(x,x)),np.float32(1/128)),np.float32(1e-6)))
        want=G.mul(G.mul(x,r[:,None]),np.vstack([qg]*8+[kg]*2))
        rec=execute(C,m,banks,metadata,c.stages['qknorm128'],mutation='missing_gain' if mutant else None)
        mism=int(np.count_nonzero(m.vm[16384:17664]!=C.fbits(want).reshape(-1)));assert bool(mism)==mutant and not rec['nonfinite']
        results.append(dict(stage='qknorm128',negative=mutant,mismatches=mism,**rec))
    # FP32 QK→RoPE; independent rotate_half reference at each speculative position.
    for pos in range(8191,8195):
        for mutant in (False,True):
            m=memory(C);x=rng.standard_normal((10,128)).astype(np.float32)
            angles=np.float32(pos)*np.power(1e6,-np.arange(0,128,2,dtype=np.float64)/128).astype(np.float32)
            cos=np.tile(np.cos(angles).astype(np.float32),2);sin=np.tile(np.sin(angles).astype(np.float32),2);signed=sin.copy();signed[:64]=G.neg(signed[:64])
            m.vm[16384:17664]=C.fbits(x).reshape(-1);m.vm[4096:4224]=C.fbits(cos);m.vm[4224:4352]=C.fbits(signed)
            want=G.add(G.mul(x,cos),G.mul(np.concatenate((G.neg(x[:,64:]),x[:,:64]),axis=1),sin));want[:8]=G.to_bf16(want[:8])
            rec=execute(C,m,banks,metadata,c.stages['rope128'],mutation='wrong_rope_sign' if mutant else None)
            mism=int(np.count_nonzero(m.vm[:1280]!=C.fbits(want).reshape(-1)));assert bool(mism)==mutant and not rec['nonfinite']
            results.append(dict(stage='rope128',position=pos,negative=mutant,mismatches=mism,**rec))
    for mutant in (False,True):
        m=memory(C);g=rng.uniform(-10,10,3072).astype(np.float32);u=rng.standard_normal(3072).astype(np.float32)
        m.vm[:3072]=C.fbits(g);m.vm[4096:7168]=C.fbits(u)
        want=G.to_bf16(G.mul(V.div(g,G.add(G.exp(G.neg(g)),np.float32(1))),u))
        rec=execute(C,m,banks,metadata,c.stages['swiglu3072'],mutation='wrong_silu' if mutant else None)
        mism=int(np.count_nonzero(m.vm[8192:11264]!=C.fbits(want)));assert bool(mism)==mutant and not rec['nonfinite']
        results.append(dict(stage='swiglu3072',negative=mutant,mismatches=mism,**rec))
    for valid in range(8192,8196):
        for mutant in (None,'round_before_sum','unmasked_tail'):
            m=memory(C);x=rng.uniform(-15,15,(8,B.CAP)).astype(np.float32);x[:,valid:]=np.nan
            m.vm[:8*B.CAP]=C.fbits(x).reshape(-1)
            # Dirty intermediate tails/partials prove real initialization, not a clean-memory assumption.
            m.vm[B.EXP:B.PUB+8*B.CAP]=0x7fc00001;m.vm[B.MP:B.T2+32]=0x7fc00001
            e=G.exp(G.add(x[:,:valid],G.neg(x[:,:valid].max(axis=1)[:,None])));want_e=G.to_bf16(e);want_z=V.csum(e)
            rec=execute(C,m,banks,metadata,c.stages['softmax8x8224'],valid,mutant)
            actual=C.ffrom(m.vm[B.PUB:B.PUB+8*B.CAP]).reshape(8,B.CAP)
            mism=int(np.count_nonzero(C.fbits(actual[:,:valid])!=C.fbits(want_e)))+int(np.count_nonzero(m.vm[B.Z:B.Z+8]!=C.fbits(want_z)))
            if mutant is None:assert mism==0 and not rec['nonfinite'] and np.all(actual[:,valid:]==0)
            else:assert mism>0 or rec['nonfinite']
            results.append(dict(stage='softmax8x8224',valid_length=valid,negative=mutant,mismatches=mism,**rec))
    (a.out/'gate.json').write_text(json.dumps(dict(status='PASS_COMPILED_NATIVE_WORD_REFERENCE_AND_LAYOUT',N=256,M=64,quarters=4,actual_quarter_RTL=False,slots=len(c.entries),cases=results,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),indent=2)+'\n')
    print('NATIVE690_COMPILER_PASS slots='+str(len(c.entries))+' cases='+str(len(results)))
if __name__=='__main__':main()
