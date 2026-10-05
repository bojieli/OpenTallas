#!/usr/bin/env python3
"""Remote CPU component only: qualified leaf vs opt-in affine layout leaf."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time
from unittest.mock import patch
os.environ.setdefault('HDC_SU_WIDTH', '1024')
os.environ.setdefault('HDC_KV_FMT', 'fp8')
import numpy as np
import hdc_golden as G
import hdc_program as P
import hdc_dynamic_kv_layout as L
from hdc_dynamic_kv_vectorized import me_dynamic_kv as reference
from test_hdc_dynamic_kv_vectorized import fixture, machine

class ArrayProbe(np.ndarray):
    def __new__(cls, data):
        obj = data.copy().view(cls)
        obj.reads = set()
        return obj
    def __array_finalize__(self, source):
        self.reads = getattr(source, 'reads', set())
    def __getitem__(self, address):
        if not isinstance(address, slice):
            a = np.asarray(address)
            assert np.all((a >= 0) & (a < self.size))
            self.reads.update(a.reshape(-1).tolist())
        return super().__getitem__(address)


def compare(f, dyn, vm, kv, pos, *, audit=False, mutant=None):
    values = []
    counts = []
    reads = []
    views = 0
    for fn in (reference, L.me_dynamic_kv_layout):
        obj = machine(vm, kv, pos, probe=(audit and fn is reference))
        if audit and fn is not reference:
            obj.vm, obj.kv = ArrayProbe(vm), ArrayProbe(kv)
        count = {'mul': 0, 'add': 0}
        def counted(name, original):
            def apply(a, b):
                count[name] += int(np.prod(np.broadcast_shapes(np.shape(a), np.shape(b))))
                return original(a, b)
            return apply
        original_view = L._weight_view
        def view(kv, base, shape, steps):
            nonlocal views
            views += 1
            if mutant == 'weight_stride':
                steps = (steps[0] + P.W, *steps[1:])
            if audit:
                grid = np.ix_(*(np.arange(size) for size in shape))
                addresses = base + sum(a * step for a, step in zip(grid, steps))
                kv.reads.update(addresses.reshape(-1).tolist())
            return original_view(kv, base, shape, steps)
        with patch.object(L, '_weight_view', view), \
             patch.object(G, 'mul', counted('mul', G.mul)), \
             patch.object(G, 'add', counted('add', G.add)):
            if mutant == 'omit_bf16' and fn is not reference:
                with patch.object(G, 'to_bf16', lambda x: x):
                    fn(obj, f, dyn)
            else:
                fn(obj, f, dyn)
        data = obj.vm.data if audit and fn is reference else obj.vm
        values.append((G.bits(data).copy(), G.bits(obj.logits).copy(), obj.argmax))
        counts.append(count)
        if audit:
            reads.append((obj.vm.reads, obj.kv.reads))
    for a, b in zip(*values):
        assert np.array_equal(a, b), 'result uint32/amax mismatch'
    assert counts[0] == counts[1], ('scalar arithmetic count', counts)
    if audit:
        assert reads[0] == reads[1], 'valid VM/KV read-set mismatch'
        if f['me_mmode'] == 1 and f['me_k'] + dyn[f['me_d_k']] > 0 and f['me_tiles'] + dyn[f['me_d_tiles']] > 0 or (f['me_d_tiles'] == P.I.DYN_TTILES and f['me_k'] > 0):
            assert views > 0, 'fast path not exercised'
    return counts[0]


def literal(kind, positions):
    # Dewey source-decoded current L0 rank0 PC11 QK / PC13 PV.
    f, dyn, vm, kv = fixture(kind, 128 if kind == 'QK' else positions, positions)
    f.update(me_wbase=0 if kind == 'QK' else 131072,
             me_xbase=15104 if kind == 'QK' else 16240,
             me_obase=1015 if kind == 'QK' else 5111, me_js=65536,
             me_xjs=128 if kind == 'QK' else 8192,
             me_ojs=512 if kind == 'QK' else 8,
             me_rmax=int(kind == 'QK'), me_mbase=16192,
             me_d_wbase=0, me_d_xbase=0)
    if kind == 'QK':
        f.update(me_nout=0, me_d_nout=P.I.DYN_T)
        dyn[P.I.DYN_T]=positions
    rng=np.random.default_rng(620926)
    vm=rng.standard_normal(160000).astype(P.F)
    kv=G.kv_round(rng.standard_normal(4300000).astype(P.F))
    return f, dyn, vm, kv


def run():
    P.GR=6144
    checks=[]
    for kind, K in [('QK',k) for k in (0,1,127,128,129)] + [('PV',k) for k in (0,1,511,512,513)]:
        for rounding in (False, True):
            f,dyn,vm,kv=fixture(kind,K,17,round_input=rounding,amax=True)
            count=compare(f,dyn,vm,kv,16,audit=True)
            checks.append(dict(kind=kind,K=K,positions=17,round_input=rounding,scalar_operations=count))
    # Fallback and limited tile coverage; current writes must affect next call.
    for mode in (0,1):
        f,dyn,vm,kv=fixture('PV',513,33,mode=mode,amax=True)
        f['me_tiles']=0 if mode==1 else 1
        compare(f,dyn,vm,kv,32,audit=True)
    f,dyn,vm,kv=fixture('QK',129,17,amax=True)
    compare(f,dyn,vm,kv,16,audit=True)
    kv[80:300]=np.float32(0.75); vm[48:500]=np.float32(-0.25)
    compare(f,dyn,vm,kv,16,audit=True)
    mutants=[]
    for mutant in ('weight_stride','omit_bf16'):
        f,dyn,vm,kv=fixture('QK',127,17,amax=True)
        try:
            compare(f,dyn,vm,kv,16,audit=True,mutant=mutant)
        except AssertionError as exc:
            mutants.append(dict(mutant=mutant,verdict='REJECTED',reason=str(exc)))
        else:
            raise AssertionError('mutation escaped: '+mutant)
    timings=[]
    for kind in ('QK','PV'):
        f,dyn,vm,kv=literal(kind,8191)
        compare(f,dyn,vm,kv,8190)
        measured=[[],[]]
        for repeat in range(5):
            for idx in (repeat%2,1-repeat%2):
                obj=machine(vm,kv,8190)
                start=time.perf_counter()
                (reference,L.me_dynamic_kv_layout)[idx](obj,f,dyn)
                measured[idx].append(time.perf_counter()-start)
        med=[float(np.median(a)) for a in measured]
        timings.append(dict(kind=kind,positions=8191,exact_uint32=True,
            qualified_seconds=measured[0],candidate_seconds=measured[1],
            qualified_median=med[0],candidate_median=med[1],speedup=med[0]/med[1]))
    pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    gain=all(t['speedup']>=1.10 for t in timings)
    return dict(verdict='PASS_EXACT_MATERIAL_HOST_COMPONENT_GAIN' if gain else 'REJECT_NOT_MATERIAL',
        scope='CPU leaf only; no whole-producer/inference/GPU/hardware rate credit; opt-in only',
        checks=checks,additional_checks=['mode0 fallback','empty tile coverage','current VM/KV rewrite'],
        mutants=mutants,timings=timings,source_sha256=pins,
        environment=dict(host=platform.node(),python=platform.python_version(),numpy=np.__version__,
                         cpu_affinity=sorted(os.sched_getaffinity(0))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=run()
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(verdict=result['verdict'],timings=result['timings'])),flush=True)
