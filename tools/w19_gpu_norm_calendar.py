#!/usr/bin/env python3
"""Ordinary GPU HC pre/post/norm instruction calendars; no tensor evaluation/RTL.

Latency/ports are proposed model inputs. Transport and physical costs remain
unqualified. This additive tool leaves corrected r3 kernel pins untouched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from w19_gpu_simd_contract import chunk_program, schedule_warps, instruction

ROOT=Path(__file__).resolve().parents[1]
ARITY={'LOAD':0,'STORE16':1,'WIDEN':1,'FMUL':2,'FADD':2,'DIV':2,
       'SHFL':1,'SHR':2,'AND':2,'IADD':2,'ISUB':2,'XOR':2}
CONSTANTS={'@F5120','@EPS','@FHALF','@FONEHALF','@USEED','@U16','@U1',
           '@U7FFF','@UFFFF0000','@SIGN'}


def op(code,dst=None,src=(),shared=False,**attrs):
    latency=21 if code=='DIV' else 9 if code in ['FMUL','FADD'] else 2 if code=='LOAD' else 3
    return instruction(code,dst,src,latency,shared,**attrs)


def bf16_round(src,dst):
    # G.to_bf16: (bits +0x7fff+((bits>>16)&1)) &0xffff0000.
    # Register bitcasts are typed views, not numerical conversions.
    return [op('SHR','hi',[src,'@U16']),op('AND','lsb',['hi','@U1']),
            op('IADD','bias',[src,'@U7FFF']),op('IADD','rounded',['bias','lsb']),
            op('AND',dst,['rounded','@UFFFF0000'])]


def vector_program(kind):
    p=[]
    for j in range(4):
        p += [op('LOAD',f'b{j}',shared=True,source=f'residual[{j}][global_dim]'),
              op('WIDEN',f'x{j}',[f'b{j}']),
              op('LOAD',f'c{j}',shared=True,source=f'pre[{j}]' if kind=='pre' else f'comb[{j},k]'),
              op('FMUL',f'p{j}',[f'c{j}',f'x{j}'])]
    # V.seqsum starts at p0; no extra zero FADD.
    p += [op('FADD','s1',['p0','p1']),op('FADD','s2',['s1','p2']),op('FADD','mix',['s2','p3'])]
    if kind=='post':
        p += [op('LOAD','yb',shared=True,source='y[global_dim]'),op('WIDEN','y',['yb']),
              op('LOAD','post',shared=True,source='post[k]'),op('FMUL','yp',['post','y']),
              op('FADD','out',['yp','mix'])]
    elif kind!='pre':raise ValueError('unknown vector kernel')
    p += bf16_round('out' if kind=='post' else 'mix','bf16')
    p += [op('STORE16',src=['bf16'],shared=True,byte_enable=True,source_bits='31:16')]
    return p


def scalar_norm_program():
    p=[op('LOAD','sum',shared=True,source='ordered global chunk8 tree result'),
       op('DIV','mean',['sum','@F5120']),op('FADD','v',['mean','@EPS']),
       op('SHR','shift',['v','@U1']),op('ISUB','y',['@USEED','shift']),
       op('FMUL','half',['v','@FHALF'])]
    for i in range(3):
        p += [op('FMUL','yy',['y','y']),op('FMUL','hyy',['half','yy']),
              op('XOR','neg',['hyy','@SIGN']),op('FADD','corr',['@FONEHALF','neg']),
              op('FMUL','y',['y','corr'])]
    return p


def scale_program():
    p=[op('LOAD','xb',shared=True,source='BF16 hc_pre result'),op('WIDEN','x',['xb']),
       op('LOAD','r',shared=True,source='published norm scalar'),
       op('LOAD','wb',shared=True,source='BF16 norm gain'),op('WIDEN','w',['wb']),
       op('FMUL','xr',['x','r']),op('FMUL','out',['w','xr'])]
    return p+bf16_round('out','bf16')+[op('STORE16',src=['bf16'],shared=True,byte_enable=True,source_bits='31:16')]


def calendar(program,warps):
    if not 1<=warps<=32:raise ValueError('finite 32 resident warps per SM')
    written=set()
    for ins in program:
        if ins['op'] not in ARITY or len(ins['src'])!=ARITY[ins['op']]:raise ValueError('opcode arity')
        if ins['dst'] and ins['dst'].startswith('@'):raise ValueError('readonly constant')
        if (ins['dst'] is None)!=(ins['op']=='STORE16'):raise ValueError('destination')
        if any(s not in written and s not in CONSTANTS for s in ins['src']):raise ValueError('unwritten source or unknown constant')
        if ins['dst']:written.add(ins['dst'])
    pc=[0]*warps;ready=[{} for _ in pc];slots=[set() for _ in range(4)]
    cursor=[0]*4;t=0;retire=0;count=Counter();shared=0
    while any(i<len(program) for i in pc):
        used=False
        for part in range(4):
            pool=list(range(part,warps,4))
            for advance in range(len(pool)):
                k=(cursor[part]+advance)%len(pool);w=pool[k]
                if pc[w]==len(program):continue
                ins=program[pc[w]];end=t+ins['latency']
                if ins['shared'] and used:continue
                if any(ready[w].get(s,0)>t for s in ins['src']):continue
                if ins['dst'] and end in slots[part]:continue
                if ins['dst']:ready[w][ins['dst']]=end;slots[part].add(end)
                count[ins['op']]+=1;retire=max(retire,end)
                if ins['shared']:used=True;shared+=1
                pc[w]+=1;cursor[part]=(k+1)%len(pool);break
        t+=1
        if t>100000:raise ValueError('deadlock')
    live=set();peak=0
    for ins in reversed(program):
        # Reserve a separate destination through writeback; no destructive
        # operand alias credit. Eight more registers cover address/loop state.
        peak=max(peak,len(live | ({ins['dst']} if ins['dst'] else set())))
        live.discard(ins['dst']);live.update(s for s in ins['src'] if s not in CONSTANTS)
        peak=max(peak,len(live))
    if peak+8>32:raise ValueError('RF register budget exceeded')
    return dict(cycles=max(t,retire),warp_instructions=dict(count),shared_issue_cycles=shared,
                RF_write_slots=sum(map(len,slots)),warps=warps,
                peak_live_value_registers=peak,reserved_address_loop_registers=8)


def build():
    pre=vector_program('pre');post=vector_program('post');scalar=scalar_norm_program();scale=scale_program()
    paths=['tools/w19_gpu_norm_calendar.py','tools/w19_gpu_simd_contract.py','tools/w19_hbm_tp96_isa.py',
           'tools/hdc_golden.py','tools/hdc_golden_v41.py',
           'results/rtl/w19_checkpoint_production_20261001/gpu-simd-lowering-candidate-r3.json',
           'results/rtl/w19_hbm_tp96_program_oreduce.json']
    graph=json.loads((ROOT/paths[-1]).read_text())
    binding=[dict(layer=l['layer'],op=o['id'],function=o['fn']) for l in graph['layers'] for o in l['ops']
             if o['kind']=='local' and o['fn'] in ['hc_pre_norm','hc_post','final_norm']]
    collector=[op('LOAD','partial',shared=True,source='lane<20 SMpartial[lane],otherwise +0')]
    for level in range(5):
        collector += [op('SHFL','other',['partial'],offset=1<<level),
                      op('FADD','partial',['partial','other'],predicate=f'lane%{1<<(level+1)}==0')]
    return dict(schema='opentallas.w19.gpu-norm-calendar.v1',status='MODEL_CANDIDATE_NOT_RTL',
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        organisation=dict(SMs=32,lanes_per_SM=128,warp=32,resident_warps=32,RF_read_ports=2,RF_write_ports=1,
                          shared_issue_bytes_per_SM_cycle=128,shared_capacity_bytes_per_SM=65536,
                          add_mul_LAT=7,RF_operand_cycles=2,SIMD_clock_GHz=.9),
        recipes=dict(pre=pre,post=post,norm_scalar=scalar,scale=scale,norm_collector=collector),
        source_graph_binding=binding,
        calendars=dict(pre=calendar(pre,8),post=calendar(post,32),norm_local=schedule_warps(chunk_program(True),1),
                       norm_scalar=calendar(scalar,1),scale=calendar(scale,8),norm_collector=calendar(collector,1)),
        allocation=dict(pre='20 SMs; SMs0..19 each produce256 consecutive dims (8warp32)',
                        norm='20 SMs; each32 consecutive chunk8 sums=256dims; warp32 tree per SM;20partials padded32+0 then ordered five-stage tree',
                        post='20 SMs; each1024 consecutive outputs (32warps); k=global_output//5120,dim=global_output%5120; five SMs per k',
                        unused_SM='participate in grid fence; no throughput or clock gating credit',
                        pre_shared_bytes_per_active_SM=4*256*2+256*2+256*2+4096,
                        post_shared_bytes_per_active_SM=4*1024*2+1024*2+1024*2+4096),
        norms=dict(length=5120,chunk8_count=640,padded_chunks=1024,local_tree_levels=5,global_tree_levels=5,
                   global_tree_compute_cycles_candidate=5*(3+9),global_tree_transport_cycles=None,
                   order='local contiguous32chunk power-of-two subtrees, then20partials padded32; identical topology to640chunks padded1024',
                   source='rmsnorm_bf16: DIV(sum,F32(len(x))),FADD(eps),rsqrt3Newton,FMUL(x,r),FMUL(w,xr),BF16RNE'),
        constants={'@F5120':'F32 5120','@EPS':'source model eps actual F32 constant',
                   '@FHALF':'0x3f000000','@FONEHALF':'0x3fc00000','@USEED':'0x5f3759df',
                   '@U16':16,'@U1':1,'@U7FFF':'0x7fff','@UFFFF0000':'0xffff0000','@SIGN':'0x80000000'},
        instruction_semantics='typed FP32/U32 register bit views; no host values. FADD/FMUL/DIV golden RNE canonical+0; XOR NEG retains signzero; integer ops modulo32; BF16 RNE preserves golden bit formula',
        prerequisites=['RF/shared physical port/area/routes including STORE16 byte enables and packed bank conflicts',
                       'inputrefill/transpose,globaltree collect+broadcast,gridfence NoC/CDC costs in Ram graph',
                       'actual opcode/precision wrappers and finite DIV service; scoped to one scalar active lane',
                       'whole token model admission and production SIMD RF staging RTL connected exact gate'],
        full_cycles=None,physical_qualified=False,full_token_qualified=False,adopted=False)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    if args.out.exists():a.error('refuse overwrite evidence')
    args.out.write_text(json.dumps(build(),indent=2)+'\n')
