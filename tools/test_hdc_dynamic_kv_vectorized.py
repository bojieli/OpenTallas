#!/usr/bin/env python3
"""One CPU component exactness/timing fixture; no checkpoint or inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('HDC_SU_WIDTH', '1024')
os.environ.setdefault('HDC_KV_FMT', 'fp8')
import numpy as np
import hdc_golden as G
import hdc_program as P
from hdc_dynamic_kv_vectorized import me_dynamic_kv


class ReadProbe:
    def __init__(self, data):
        self.data = data
        self.reads = set()
    def __getitem__(self, address):
        a = np.asarray(address)
        assert np.all((a >= 0) & (a < self.data.size)), 'invalid source address read'
        self.reads.update(a.reshape(-1).tolist())
        return self.data[address]
    def __setitem__(self, address, bits):
        self.data[address] = bits


def fixture(kind, K, positions, round_input=True, mode=1, amax=False):
    # Actual W16/IL8/G6144 and actual QK128/PV512 splits. GQA aliases each
    # four heads to the same KV home, with strided/nonzero source bases.
    S = 128 if kind == 'QK' else 512
    width = K if kind == 'QK' else 128
    f = {name: 0 for name, _ in P.I.FIELDS}
    f.update(me_wsrc=1, me_split=S.bit_length()-1, me_nout=positions if kind=='QK' else width,
             me_tiles=1, me_k=K, me_wbase=3, me_xbase=32, me_obase=1024,
             me_xcs=1, me_xks=S, me_xjs=max(1,K), me_jsh=2,
             me_ts=max(1,K) if kind=='QK' else 1,
             me_wcs=1 if kind=='QK' else width//P.W,
             me_ks=S if kind=='QK' else (width//P.W)*S,
             me_js=((positions+P.W-1)//P.W)*max(1,K) if kind=='QK' else K*(width//P.W),
             me_ots=1, me_ojs=(positions+P.W-1)//P.W if kind=='QK' else width//P.W,
             me_mmode=mode, me_oen=1, me_round=int(round_input), me_rmax=1,
             me_mbase=16, me_amax=int(amax), me_amc=int(amax))
    if kind=='QK':
        f.update(me_tiles=0, me_d_tiles=P.I.DYN_TTILES)
    dyn=[0]*7
    # Nonzero actual runtime dynamics applied by both implementations.
    dyn[P.I.DYN_KWRITE]=2; f['me_d_wbase']=P.I.DYN_KWRITE
    dyn[P.I.DYN_VWRITE]=16; f['me_d_xbase']=P.I.DYN_VWRITE
    if kind=='PV':
        f.update(me_k=0, me_d_k=P.I.DYN_T);dyn[P.I.DYN_T]=K
    # VM output homes are padded to complete W-lane position words.
    vm_size=16384+8*max(((positions+P.W-1)//P.W)*P.W,width,K)
    kv_size=(f['me_wbase']+dyn[f['me_d_wbase']])*P.W + (2*((positions+P.W-1)//P.W)*max(1,K)*P.W if kind=='QK' else 2*max(1,K)*width)
    rng=np.random.default_rng(47+K+positions)
    vm=rng.standard_normal(vm_size).astype(np.float32)
    vm[48:56]=G.from_bits(np.array([0,0x80000000,1,0x80000001,0x00010000,0x80010000,0x3f808000,0xbf808000],dtype=np.uint32))
    kv=G.kv_round(rng.standard_normal(kv_size).astype(np.float32))
    kv[::11]=np.float32(-0.0)
    return f,dyn,vm,kv


def machine(vm,kv,pos,probe=False):
    return SimpleNamespace(vm=ReadProbe(vm.copy()) if probe else vm.copy(),
                           kv=ReadProbe(kv.copy()) if probe else kv.copy(),pos=pos,
                           logits=np.array([np.float32(-123)],dtype=np.float32),argmax=None)


def run():
    old_gr=P.GR;P.GR=6144
    checks=[];timings=[]
    try:
        specs=[('QK',k,17) for k in (0,1,127,128,129)]+[('PV',k,17) for k in (0,1,511,512,513)]
        for number,(kind,K,positions) in enumerate(specs):
            f,dyn,vm,kv=fixture(kind,K,positions,round_input=number%2==0,mode=number%2,amax=number%3==0)
            ref=machine(vm,kv,positions-1,True);got=machine(vm,kv,positions-1,True)
            counts=[]
            for fn,obj in ((P.Machine.me,ref),(me_dynamic_kv,got)):
                count={'mul':0,'add':0}
                def counted(name,original):
                    def apply(a,b):
                        count[name]+=np.broadcast_shapes(np.shape(a),np.shape(b))[-1] if np.ndim(a)==1 and np.ndim(b)==1 else np.prod(np.broadcast_shapes(np.shape(a),np.shape(b)))
                        return original(a,b)
                    return apply
                with patch.object(G,'mul',counted('mul',G.mul)),patch.object(G,'add',counted('add',G.add)):
                    fn(obj,f,dyn)
                counts.append(count)
            assert np.array_equal(G.bits(ref.vm.data),G.bits(got.vm.data)),(kind,K,'VM bits')
            assert np.array_equal(G.bits(ref.logits),G.bits(got.logits)) and ref.argmax==got.argmax,(kind,K,'amax')
            assert ref.kv.reads==got.kv.reads and ref.vm.reads==got.vm.reads,(kind,K,'causal source read sets')
            assert counts[0]==counts[1],(kind,K,'extra zero arithmetic',counts)
            checks.append(dict(kind=kind,K=K,positions=positions,exact_uint32=True,same_read_addresses=True,same_scalar_operation_counts=True))
        for kind,K,positions in [('QK',128,8191),('PV',8191,8191)]:
            f,dyn,vm,kv=fixture(kind,K,positions)
            values=[];seconds=[]
            for fn in (P.Machine.me,me_dynamic_kv):
                obj=machine(vm,kv,positions-1)
                start=time.perf_counter();fn(obj,f,dyn);seconds.append(time.perf_counter()-start)
                values.append(G.bits(obj.vm).copy())
            assert np.array_equal(*values),(kind,'full-context component bits')
            timings.append(dict(kind=kind,K=K,positions=positions,reference_seconds=seconds[0],vectorized_seconds=seconds[1],speedup=seconds[0]/seconds[1],exact_uint32=True))
    finally:P.GR=old_gr
    root=Path(__file__).parent
    pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['hdc_program.py','hdc_golden.py','hdc_isa.py','hdc_dynamic_kv_vectorized.py','test_hdc_dynamic_kv_vectorized.py']}
    return dict(verdict='PASS_COMPONENT_EXACT_DYNAMIC_KV',scope='CPU host component only; no full-model/hardware latency or rate qualification',checks=checks,timings=timings,source_sha256=pins)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=run()
    with args.output.open('x') as file:json.dump(result,file,indent=2);file.write('\n')
    print(json.dumps(result['timings']))
