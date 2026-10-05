#!/usr/bin/env python3
"""Execute owner MoE recipe with existing typed VM on all true TP96 row slices.

Inputs are disclosed synthetic BF16 expert slots, not deployed activations.
No recipe/manual lowering rewrite, GPU job, model generator edit or rate claim.
"""
import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import hdc_golden as G
import w19_hbm_tp96_isa as I
import w19_gpu_elementwise_calendar as E
import w19_norm_opcode_proof as M

F=np.float32
CALENDAR="results/quality/w16_w19_composed_schedule_20261001/moe_sum_calendar.json"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class MoEVM(M.Machine):
    """Bind the owner's immutable zero constant/calendar; reuse run unchanged."""
    def __init__(self,program,memory,rf_budget=32):
        self.admission=E.provider()['calendar'](program,2)
        if self.admission['peak_live_value_registers']+8>rf_budget:
            raise ValueError('RF register budget exceeded')
        self.program,self.memory=program,memory
        self.constants=M.constants(1e-20)
        self.constants['@F32_POS_ZERO']=M.f32(F(0))
        self.regs,self.trace,self.stores={},[],[]


class RankOracle:
    def __init__(self,rank,slots):
        self.r,self.slots=rank,slots
        self.reads=[];self.output=None
    def get(self,name,r0,r1):
        e=int(name[1:name.index('.')])
        if name!=f'e{e}.d' or [r0,r1]!=I.even(5120)[self.r]:
            raise ValueError('oracle slot/row ownership')
        self.reads.append(name)
        return self.slots[e,r0:r1]
    def put(self,name,y,lo,n):
        if name!='yf' or lo!=I.even(5120)[self.r][0] or n!=5120:
            raise ValueError('oracle output ownership')
        self.output=y.copy()


@contextmanager
def original_add_trace():
    saved=G.add;trace=[]
    def add(a,b):
        v=saved(a,b);trace.append(v.copy());return v
    try:
        G.add=add;yield trace
    finally:
        G.add=saved


def run_rank(recipe,slots,rank):
    if slots.shape!=(7,5120) or slots.dtype!=F or not np.isfinite(slots).all() or not np.array_equal(slots.view(np.uint32),G.to_bf16(slots).view(np.uint32)):
        raise ValueError('seven finite full5120 BF16 producer slots required')
    lo,hi=I.even(5120)[rank];rows=hi-lo
    mem={}
    for e in range(7):
        staged=np.zeros(64,F);staged[:rows]=slots[e,lo:hi]
        mem[f'e{e}.d[rank_local_row] BF16']=M.bf16_memory(staged)
    vm=MoEVM(recipe,mem).run()
    rk=RankOracle(rank,slots)
    executor=SimpleNamespace(m=SimpleNamespace(k_exp=6))
    with original_add_trace() as golden:
        I.Executor.f_moe_sum(executor,rk,{})
    if rk.reads!=[f'e{e}.d' for e in range(7)]:
        raise AssertionError('routed6+shared producer order')
    adds=[t['value'].f32()[:rows] for t in vm.trace if t['op']=='FADD']
    if len(adds)!=7 or len(golden)!=7:
        raise AssertionError('seven FADD boundaries from +0 required')
    for pc,(v,ref) in enumerate(zip(adds,golden)):
        if not M.equal(v,ref):raise AssertionError(f'FADD boundary{pc} mismatch')
    out=vm.stored_f32()
    if not M.equal(out[:rows],rk.output):raise AssertionError('BF16 output mismatch')
    if np.any(out[rows:].view(np.uint32)!=0):raise AssertionError('padded inactive host lanes changed')
    return out[:rows].copy(),vm,{'rank':rank,'range':[lo,hi],'rows':rows,'padded_lanes':64-rows,'seven_FADDs':'PASS',
        'output_sha256':sha(out[:rows].tobytes()),'golden_output_sha256':sha(rk.output.tobytes()),'producer_reads':rk.reads}


def inputs():
    yield 'seeded_BF16',G.to_bf16(np.random.default_rng(190036).normal(size=(7,5120)).astype(F))
    for name,values in [
        ('order_cancellation',[2**25,1,-2**25,1,0,0,0]),
        ('BF16_even_tie',[1,2**-8,0,0,0,0,0]),
        ('BF16_odd_tie',[1,2**-7,2**-8,0,0,0,0]),
        ('no_early_BF16',[1]+[2**-9]*6),
        ('canonical_zero',[-0.0]*7),
        ('shared_slot_only',[0,0,0,0,0,0,1])]:
        yield name,np.repeat(np.array(values,F)[:,None],5120,axis=1)
    tiny=np.array(0x00010000,np.uint32).view(F)
    yield 'gradual_BF16_underflow',np.full((7,5120),tiny,F)


def execute(out):
    repo=Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():
        raise ValueError('clean source required')
    out.mkdir(parents=True,exist_ok=False)
    raw=subprocess.check_output(['git','show','HEAD:'+CALENDAR],cwd=repo)
    cal=json.loads(raw)
    if cal!=E.build():raise ValueError('owner calendar source reproduction mismatch')
    recipe=cal['recipe'];rows=cal['rank_rows']
    if rows!=[b-a for a,b in I.even(5120)] or set(rows)!={53,54}:raise ValueError('TP96 row ownership changed')
    graphraw=subprocess.check_output(['git','show','HEAD:results/rtl/w19_hbm_tp96_program_oreduce.json'],cwd=repo)
    graphpin=cal['source_pins']['results/rtl/w19_hbm_tp96_program_oreduce.json']['sha256']
    if sha(graphraw)!=graphpin:raise ValueError('current producer graph changed')
    records=[]
    for case,(name,slots) in enumerate(inputs()):
        output=np.empty(5120,F);rank_records=[];traces=[]
        for rank in range(96):
            y,vm,rec=run_rank(recipe,slots,rank)
            lo,hi=rec['range'];output[lo:hi]=y;rank_records.append(rec)
            traces.append({'rank':rank,'opcodes':[{k:v for k,v in t.items() if k!='value'} for t in vm.trace]})
        np.savez_compressed(out/f'fixture_{case}.npz',slots=slots,output=output)
        tracebytes=json.dumps(traces,separators=(',',':')).encode()
        (out/f'opcodes_{case}.json.gz').write_bytes(gzip.compress(tracebytes,mtime=0))
        early=np.zeros(5120,F)
        for e in range(7):early=G.to_bf16(G.add(early,slots[e]))
        serial=np.zeros(5120,F)
        for e in [0,2,1,3,4,5,6]:serial=G.add(serial,slots[e])
        wrong_order=G.to_bf16(serial)
        records.append({'name':name,'input_disclosure':'synthetic sevenBF16 slots;6routed+shared sourcebound producer types, not actual token trajectory',
                        'rank_receipts':rank_records,'opcode_boundaries':96*len(recipe),'input_sha256':sha(slots.tobytes()),'output_sha256':sha(output.tobytes()),
                        'negative_controls':{'early_BF16_different_words':int(np.count_nonzero(early.view(np.uint32)!=output.view(np.uint32))),
                                             'reordered_slots_different_words':int(np.count_nonzero(wrong_order.view(np.uint32)!=output.view(np.uint32)))},'verdict':'PASS'})
    if not any(r['negative_controls']['early_BF16_different_words'] for r in records) or not any(r['negative_controls']['reordered_slots_different_words'] for r in records):
        raise AssertionError('negative control sensitivity missing')
    pins=['tools/w19_moe_opcode_proof.py','tests/test_w19_moe_opcode_proof.py','tools/w19_gpu_elementwise_calendar.py','tools/w19_norm_opcode_proof.py','tools/w19_hbm_tp96_isa.py','tools/hdc_golden.py']
    proof={'schema':'opentallas.w19.moe-opcode.cpu-proof.v1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
           'source_pins':{p:sha((repo/p).read_bytes()) for p in pins},'calendar_path':CALENDAR,'calendar_sha256':sha(raw),'calendar':cal['calendar'],
           'row_distribution':{'53_rows':rows.count(53),'54_rows':rows.count(54)},'logical_lanes':64,'resident_warps':2,
           'fixtures':records,'verdict':'PASS','physical_qualified':False,'full_token_qualified':False,'GPU_campaign_launched':False,'rate':None,'adoption':False,
           'mask_scope':'CPU pads reads lanesrows..63 with+0, excludes those lanes from storedrankoutput; no production masking/staging qualification',
           'QC_NAM':'original completed fullFAIL unchanged','artifacts':{p.name:sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');(out/'owner_calendar.json').write_bytes(raw)
    print(json.dumps({'verdict':'PASS','fixtures':len(records),'rank_cases':len(records)*96,'opcode_boundaries':sum(r['opcode_boundaries'] for r in records),'proof':str(out/'proof.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    execute(p.parse_args().out)
