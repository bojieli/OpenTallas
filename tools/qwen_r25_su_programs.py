#!/usr/bin/env python3
"""Full-shape r25 Qwen SU programs in the existing vec bench encoding.

No stage cycle credit: these programs still need real N1024 RTL measurement.
The exp sum precedes BF16 publication; rounding before sum violates qwen_r25.
"""
import numpy as np
import rtl_hdc_v41x_vec_campaign as C
import hdc_golden as G
import hdc_golden_v41 as V
import hdc_isa_v41 as I


def op(**fields):
    f = C.op_defaults(); f.update(fields); C.encode(f); return f


def norm_program(heads, dim, x=0, gain=8192, scalar=16384, y=32768):
    return [op(nout=heads,nin=dim,abase=x,aso=dim,asi=1,
               red=I.RED_SUM,redsq=1,rbase=scalar,rso=1),
            op(nout=heads,nin=1,abase=scalar,aso=1,
               m1=I.M1_AIMM,imm1=C.f32u(1.0/dim),ad=I.AD_IMM,imm2=C.f32u(1e-6),
               sfu=I.SFU_RSQRT,dst=I.DST_VM,obase=scalar,oso=1),
            op(nout=heads,nin=dim,abase=x,aso=dim,asi=1,
               bbase=scalar,bso=1,cbase=gain,csi=1,
               m1=I.M1_AB,e1=I.E1_MULC,rnd=1,
               dst=I.DST_VM,obase=y,oso=dim,osi=1)]


def softmax_program(round_before_sum=False):
    # 8 Q heads x8192 rows. Two arrays fit the campaign's2^18-wordVM.
    # BF16 exp are attention PV operands, NOT probabilities divided by Z.
    x,e,p,mx,z = 0,65536,131072,196608,196616
    return [op(nout=8,nin=8192,abase=x,aso=8192,asi=1,
               red=I.RED_MAX,rbase=mx,rso=1),
            op(nout=8,nin=8192,abase=x,aso=8192,asi=1,bbase=mx,bso=1,
               ad=I.AD_NEGB,sfu=I.SFU_EXP,red=I.RED_SUM,rbase=z,rso=1,
               rnd=int(round_before_sum),dst=I.DST_VM,obase=e,oso=8192,osi=1),
            op(nout=8,nin=8192,abase=e,aso=8192,asi=1,rnd=1,
               dst=I.DST_VM,obase=p,oso=8192,osi=1)]


def swiglu_program():
    return [op(nout=1,nin=3072,abase=0,asi=1,cbase=4096,csi=1,
               sfu=I.SFU_SILU,e1=I.E1_MULC,rnd=1,
               dst=I.DST_VM,obase=8192,osi=1)]


def reference(stage, mutant=False, return_case=False):
    rng = np.random.default_rng(8191)
    mem = C.Mem(np.zeros(1<<C.VMA,np.uint32),np.zeros(1<<C.KVA,np.uint32),
                np.zeros((1<<C.CRA,2),np.uint32),np.zeros(1<<C.WRA,np.uint16))
    if stage in ('rmsnorm','qknorm'):
        heads,dim=(1,4096) if stage=='rmsnorm' else (10,128)
        x=rng.standard_normal((heads,dim)).astype(np.float32)
        gain=rng.uniform(.1,2,dim).astype(np.float32)
        mem.vm[:x.size]=C.fbits(x).reshape(-1);mem.vm[8192:8192+dim]=C.fbits(gain)
        ops=norm_program(heads,dim)
        inv=G.rsqrt(G.add(G.mul(V.csum(G.mul(x,x)),np.float32(1/dim)),np.float32(1e-6)))
        want=G.to_bf16(G.mul(G.mul(x,inv[:,None]),gain))
        checks=[(32768,C.fbits(want).reshape(-1))]
    elif stage=='softmax':
        x=rng.uniform(-15,15,(8,8192)).astype(np.float32)
        mem.vm[:x.size]=C.fbits(x).reshape(-1);ops=softmax_program(mutant)
        e=G.exp(G.add(x,G.neg(x.max(axis=1)[:,None])))
        checks=[(196616,C.fbits(V.csum(e))),
                (131072,C.fbits(G.to_bf16(e)).reshape(-1))]
    elif stage=='swiglu':
        g=rng.uniform(-10,10,3072).astype(np.float32)
        u=rng.standard_normal(3072).astype(np.float32)
        mem.vm[:3072]=C.fbits(g);mem.vm[4096:4096+3072]=C.fbits(u)
        ops=swiglu_program()
        want=G.to_bf16(G.mul(V.div(g,G.add(G.exp(G.neg(g)),np.float32(1))),u))
        checks=[(8192,C.fbits(want))]
    else:
        raise ValueError(stage)
    if return_case:
        return mem, ops, checks
    for f in ops:
        finite,*_=C.ref_op(f,mem)
        assert finite
    mismatches=sum(int(np.count_nonzero(mem.vm[a:a+len(w)]!=w)) for a,w in checks)
    return dict(stage=stage,ops=len(ops),mismatches=mismatches,
                scope='full tensor reference; no RTL cycles or checkpoint-quality claim')

def main():
    import argparse, json
    from pathlib import Path
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exe',type=Path)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--n',type=int,default=64)
    ap.add_argument('--m',type=int,default=16)
    a=ap.parse_args()
    records=[]
    if a.exe:
        if not a.out:
            ap.error('--out required with --exe')
        import hbm_su_c12 as S
        S.apply(C)
        old=C.run_case
        C.run_case=lambda exe,d,nops,x=None:old(exe,d,nops,x,timeout=None)
    for stage,mutant in [(s,False) for s in ('rmsnorm','qknorm','softmax','swiglu')]+[('softmax',True)]:
        rec=reference(stage,mutant)
        rec['negative']=mutant
        if a.exe:
            mem,ops,checks=reference(stage,mutant,return_case=True)
            compare,trace,_,_=C.run_program(a.exe,a.out/(stage+('_mutant' if mutant else '')),mem,ops,a.n,a.m,chain=False)
            got=trace['vm'];assert got is not None
            rec.update(rtl_compare=compare,n=a.n,m=a.m,
                rtl_golden_mismatches=sum(int(np.count_nonzero(got[x:x+len(w)]!=w)) for x,w in checks))
            assert compare['pass_'],compare
            assert (rec['rtl_golden_mismatches']>0)==mutant
        records.append(rec)
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'programs.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))

if __name__=='__main__':
    main()
