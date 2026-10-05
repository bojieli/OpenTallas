#!/usr/bin/env python3
"""HC20480 scalar opcode execution plus source-bound physical RF ownership.

Existing typed Machine.run is reused. IADDR has purpose-only source metadata:
it is an opaque address token in RF ownership, never a numeric address claim.
No full mixes/attention rerun, GPU job, compiler-spill or physical port credit.
"""
import argparse
import copy
import io
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_norm_opcode_proof as M
import w16_gpu_hc_dot_schedule as D

F=np.float32
MODEL='results/uarch/w16_gpu_hc_dot_schedule_20261001/cost_r1.json'
INPUTS='results/uarch/w16_gpu_hc_dot_schedule_20261001/inputs_r1.json'
PRODUCER='results/quality/w19_hc_nonlinear_proof_20261001'


def sha(b):return hashlib.sha256(b).hexdigest()


def recipe():
    return [dict(op,src=['@F20480' if s=='@F5120' else s for s in op['src']]) for op in D.N.scalar_norm_program()]


class ScalarVM(M.Machine):
    def __init__(self,program,total,eps,p):
        _,self.admission=D.lower(program,p)
        self.program,self.memory=program,{'ordered global chunk8 tree result':M.f32(total)}
        self.constants=M.constants(eps);self.constants['@F20480']=M.f32(F(20480))
        self.regs,self.trace,self.stores={},[],[]


def numeric(program,x,eps,p):
    if x.shape!=(4,5120) or x.dtype!=F or not np.isfinite(x).all() or not np.array_equal(x.view(np.uint32),G.to_bf16(x).view(np.uint32)):
        raise ValueError('finite full4x5120 BF16 producer activation required')
    total=F(V.csum(G.mul(x.reshape(-1),x.reshape(-1))))
    vm=ScalarVM(program,total,eps,p).run()
    with M.golden_trace() as trace:
        expected=G.rsqrt(V.add(V.div(total,F(20480)),F(eps)))
    M.check_float_trace(vm,trace)
    if not M.equal(vm.regs['y'].f32(),np.asarray(expected,F)):
        raise AssertionError('HC20480 normscalar output mismatch')
    return vm,total


def physical_ownership(code,issue,vm,p):
    """Issue reads must own the expected SSA value; retired writes own RF cells.

Actual owner allocator/calendar supplies register indices and cycle events.
Core outputs/types are from unchanged typed VM, addresses are opaque tokens.
"""
    if len(code)!=len(issue) or len(code)!=len(vm.trace)+6:
        raise ValueError('actual scalar/address recipe binding count')
    prefix=[op for op in code if op['op']=='IADDR']
    if len(prefix)!=6 or any(op['op']!='IADDR' for op in code[:6]):
        raise ValueError('source address prefix must remain six opaque operations')
    if [op['op'] for op in code[6:]]!=[r['op'] for r in vm.trace]:
        raise ValueError('core scalar recipe changed')
    owners={};rfvalues={};pending=[];reservations=set();receipts=[];ssa={};last_cycle=-1
    def retire(cycle):
        nonlocal pending
        due=sorted([w for w in pending if w[0]<=cycle])
        pending=[w for w in pending if w[0]>cycle]
        for when,reg,name,value in due:
            owners[reg]=name;rfvalues[reg]=value
    for pc,(op,event) in enumerate(zip(code,issue)):
        if event['pc']!=pc or event['warp']!=0 or event['partition']!=0 or (last_cycle>=0 and event['cycle']<last_cycle+p['warp_issue_interval']):
            raise ValueError('singlewarp issue binding/order')
        if event['retire']!=event['cycle']+D.latency(op,p):
            raise ValueError('unpriced latency/retirement')
        if event['src']!=op['physical_src'] or event['dst']!=op['physical_dst']:
            raise ValueError('physical operand binding differs from source')
        if len(op['physical_src'])>2:
            raise ValueError('RF read port budget')
        retire(event['cycle']);last_cycle=event['cycle'];reads=[]
        for expected,reg in zip(op['src'],op['physical_src']):
            if expected in D.CONSTANTS:
                if reg!=D.CONTROL.get(expected,expected):raise ValueError('constant/control RF binding')
                reads.append({'value':expected,'register':reg,'scope':'reservedcontrol' if isinstance(reg,int) else 'readonly immediate'})
            else:
                if not isinstance(reg,int) or reg not in range(28) or owners.get(reg)!=expected:
                    raise ValueError('RF read-before-write/ownership alias: '+expected)
                value=ssa[expected]
                reads.append({'value':expected,'register':reg,**value})
        dst=op['physical_dst']
        if not isinstance(dst,int) or dst not in range(28):raise ValueError('reserved RF write/spill')
        slot=(event['partition'],event['retire'])
        if slot in reservations:raise ValueError('RF write reservation collision')
        reservations.add(slot)
        value=None
        if pc<6:
            result={'kind':'OPAQUE_IADDR','sha256':None}
        else:
            # Execute the physical-register operands through the same typed
            # core, not by copying the logical result into the RF. LOAD's
            # address token is explicitly outside numeric address scope.
            single=M.Machine.__new__(M.Machine)
            single.program=[dict(vm.program[pc-6],dst=f'r{dst}',
                src=[] if op['op']=='LOAD' else [f'r{reg}' if isinstance(reg,int) else reg for reg in op['physical_src']])]
            single.memory=vm.memory;single.constants=vm.constants
            single.regs={f'r{reg}':v for reg,v in rfvalues.items() if v is not None}
            single.trace=[];single.stores=[]
            single.run();value=single.regs[f'r{dst}']
            result={'kind':value.kind,'sha256':sha(value.data.tobytes())}
            expected=vm.trace[pc-6]
            if result['kind']!=expected['kind'] or result['sha256']!=expected['sha256']:
                raise ValueError('physical RF numeric result mismatch')
        ssa[op['dst']]=result;pending.append((event['retire'],dst,op['dst'],value))
        receipts.append({'pc':pc,'op':op['op'],'issue':event['cycle'],'retire':event['retire'],'reads':reads,'write_register':dst,'write_value':op['dst'],**result})
    retire(max(e['retire'] for e in issue))
    if owners.get(code[-1]['physical_dst'])!=code[-1]['dst']:
        raise ValueError('final published scalar RF owner changed')
    return {'instructions':len(code),'opaque_address_instructions':6,'numeric_opcodes':len(vm.trace),
            'final_scalar_register':code[-1]['physical_dst'],'final_scalar_value':code[-1]['dst'],
            'final_scalar_sha256':vm.trace[-1]['sha256'],'reserved_controls':[28,29,30,31],
            'one_partition_write_reservations':len(reservations),'receipts':receipts}


def blob(repo,path):return subprocess.check_output(['git','show','HEAD:'+path],cwd=repo)


def execute(out):
    repo=Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():raise ValueError('clean source required')
    out.mkdir(parents=True,exist_ok=False)
    modelraw=blob(repo,MODEL);model=json.loads(modelraw);p=json.loads(blob(repo,INPUTS));program=recipe()
    schedule,issue=D.replay(program,1,p)
    if schedule!=model['norm_calendar_input']['norm_scalar_schedule']:raise ValueError('published owner normscalar calendar mismatch')
    nodes=[v for v in model['node_costs'].values() if v['phase']=='hc_norm_scalar_kernel']
    if len(nodes)!=80 or any(n['logical_SM_owners']!=[24] for n in nodes):raise ValueError('HCnorm scalar SM24 ownership drift')
    code,allocation=D.lower(D.address_program(program),p)
    if allocation!=schedule['allocation']:raise ValueError('published RF allocation mismatch')
    raw=blob(repo,PRODUCER+'/proof.json');producer=json.loads(raw)
    if producer['verdict']!='PASS':raise ValueError('HCproducer notPASS')
    records=[]
    for i,f in enumerate(producer['fixtures']):
        name=f'fixture_{i}.npz';data=blob(repo,PRODUCER+'/'+name)
        if sha(data)!=producer['artifacts'][name]:raise ValueError('producer artifact hash mismatch')
        with np.load(io.BytesIO(data),allow_pickle=False) as a:x=a['activation'].copy()
        vm,total=numeric(program,x,f['norm_eps'],p)
        boundariesraw=blob(repo,PRODUCER+f'/boundaries_{i}.json')
        if sha(boundariesraw)!=producer['artifacts'][f'boundaries_{i}.json']:raise ValueError('producer boundary hash mismatch')
        boundaries=json.loads(boundariesraw);r=next(b for b in boundaries if b['instruction']=='rsqrt.output')
        if sha(vm.regs['y'].f32().tobytes())!=r['golden_sha256']:raise ValueError('retained producer scalar bits mismatch')
        ownership=physical_ownership(code,issue,vm,p)
        (out/f'RF_{i}.json').write_text(json.dumps(ownership,indent=2)+'\n')
        traces=[{k:v for k,v in t.items() if k!='value'} for t in vm.trace]
        (out/f'opcodes_{i}.json').write_text(json.dumps(traces,indent=2)+'\n')
        np.savez_compressed(out/f'fixture_{i}.npz',activation=x,ordered_sum=total,norm_scalar=vm.regs['y'].f32())
        records.append({'name':f['name'],'producer_path':PRODUCER+'/'+name,'producer_sha256':sha(data),'producer_scalar_sha256':r['golden_sha256'],'norm_eps':f['norm_eps'],
                        'norm_scalar_sha256':sha(vm.regs['y'].f32().tobytes()),'numeric_opcode_count':21,'physical_RF_events':27,'verdict':'PASS'})
    pins=['tools/w19_hc_scalar_rf_proof.py','tests/test_w19_hc_scalar_rf_proof.py','tools/w16_gpu_hc_dot_schedule.py','tools/w19_gpu_norm_calendar.py','tools/w19_norm_opcode_proof.py','tools/hdc_golden.py','tools/hdc_golden_v41.py',MODEL,INPUTS]
    proof={'schema':'opentallas.w19.hc-scalar-rf.cpu-proof.v1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
           'source_pins':{p:sha(blob(repo,p)) for p in pins},'producer_proof_sha256':sha(raw),'owner_calendar':schedule,'owner_model_sha256':sha(modelraw),
           'SM_owner':24,'warp':0,'active_numeric_lane':0,'shape':[4,5120],'DIV_denominator':20480,'fixtures':records,'verdict':'PASS',
           'scope':'21HCnorm numericopcodes and27RFownership events;6IADDR opaque ownership only. Source calendar195cycles analytical unmeasured, not hardware timing or compiled register allocation.',
           'remaining':['actual IADDR address semantics/transport','chunk tree/collector execution','fullHCscalar exp/sigmoid/Sinkhorn typedopcode/compiler RF allocation','physicalRF/SSFF/wholegraph admission'],
           'GPU_campaign_launched':False,'physical_qualified':False,'full_token_qualified':False,'rate':None,'adoption':False,'QC_NAM':'original completedFAIL unchanged',
           'artifacts':{p.name:sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'verdict':'PASS','fixtures':len(records),'numeric_opcodes':len(records)*21,'RF_events':len(records)*27,'proof':str(out/'proof.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);execute(p.parse_args().out)
