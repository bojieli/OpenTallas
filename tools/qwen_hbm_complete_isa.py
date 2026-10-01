#!/usr/bin/env python3
"""Qwen scalar recipes in ordinary two-source GPU instructions, software proof.

Instruction latencies/area, shared bank maps and full issue calendars are
unqualified. No FMA, native EXP or native reciprocal/divide substitutes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from qwen_hbm_complete_program import compile_program

ARITY={'FADD':2,'FMUL':2,'XOR':2,'AND':2,'SHR':2,'SHL':2,
       'IADD':2,'ISUB':2,'UGT':2,'ULT':2,'FCMPGT':2,'F2I':1}

class Builder:
    def __init__(self,inputs):self.inputs=list(inputs);self.instructions=[];self.constants={};self.serial=0
    def constant(self,name,value,kind='F32'):
        bits=int(np.asarray(value,np.float32).view(np.uint32)) if kind=='F32' else int(value)&0xffffffff
        key='@'+name
        if key in self.constants and self.constants[key]!=bits:raise ValueError('constant identity')
        self.constants[key]=bits
        return key
    def emit(self,opcode,*src):
        if opcode not in ARITY or len(src)!=ARITY[opcode]:raise ValueError('ordinary two-source arity')
        dst=f'r{self.serial}';self.serial+=1
        self.instructions.append(dict(opcode=opcode,dst=dst,src=list(src),core_serial_cycles=None))
        return dst
    def negate(self,value):return self.emit('XOR',value,self.constant('SIGN',0x80000000,'U32'))
    def select(self,predicate,yes,no):
        # No ternary instruction or unpriced third RF read. A 0/1 predicate
        # becomes a full word mask, followed by a two-source bitwise select.
        mask=self.emit('ISUB',self.constant('UZERO',0,'U32'),predicate)
        difference=self.emit('XOR',yes,no)
        selected=self.emit('AND',mask,difference)
        return self.emit('XOR',no,selected)
    def clamp(self,value,bound,maximum):
        gt=self.emit('FCMPGT',value,bound)
        return self.select(gt,value,bound) if maximum else self.select(gt,bound,value)
    def exp(self,value):
        x=self.clamp(value,self.constant('EXP_MIN',-87),True)
        x=self.clamp(x,self.constant('EXP_MAX',88),False)
        t=self.emit('FMUL',x,self.constant('LOG2E',1.4426950408889634))
        n=self.emit('FADD',self.emit('FADD',t,self.constant('MAGIC',12582912)),self.constant('NEG_MAGIC',-12582912))
        hi=self.emit('FMUL',n,self.constant('LN2_HI',.693145751953125))
        lo=self.emit('FMUL',n,self.constant('LN2_LO',1.428606765330187e-6))
        reduced=self.emit('FADD',self.emit('FADD',x,self.negate(hi)),self.negate(lo))
        coefficients=[1/720,1/120,1/24,1/6,.5,1,1]
        p=self.constant('POLY0',coefficients[0])
        for index,c in enumerate(coefficients[1:],1):p=self.emit('FADD',self.emit('FMUL',p,reduced),self.constant(f'POLY{index}',c))
        exponent=self.emit('SHL',self.emit('F2I',n),self.constant('U23',23,'U32'))
        return self.emit('IADD',p,exponent)
    def reciprocal(self,value):
        seed=self.constant('RECIP_SEED',0x7ef311c7,'U32')
        above=self.emit('UGT',value,seed)
        finite=self.emit('ULT',value,self.constant('POS_INF',0x7f800000,'U32'))
        over=self.emit('AND',above,finite)
        y=self.select(over,self.constant('UZERO',0,'U32'),self.emit('ISUB',seed,value))
        for _ in range(3):
            correction=self.emit('FADD',self.constant('TWO',2),self.negate(self.emit('FMUL',value,y)))
            y=self.emit('FMUL',y,correction)
        return y
    def rsqrt(self,value):
        half=self.emit('FMUL',value,self.constant('HALF',.5))
        shifted=self.emit('SHR',value,self.constant('U1',1,'U32'))
        y=self.emit('ISUB',self.constant('RSQRT_SEED',0x5f3759df,'U32'),shifted)
        for _ in range(3):
            yy=self.emit('FMUL',y,y);hy=self.emit('FMUL',half,yy)
            corr=self.emit('FADD',self.constant('ONE_HALF',1.5),self.negate(hy))
            y=self.emit('FMUL',y,corr)
        return y
    def bf16(self,value):
        shift=self.constant('U16',16,'U32')
        odd=self.emit('AND',self.emit('SHR',value,shift),self.constant('U1',1,'U32'))
        bias=self.emit('IADD',self.constant('U7FFF',0x7fff,'U32'),odd)
        rounded=self.emit('IADD',value,bias)
        return self.emit('AND',rounded,self.constant('UFFFF0000',0xffff0000,'U32'))
    def finish(self,result):
        last={}
        for index,instruction in enumerate(self.instructions):
            for source in instruction['src']:
                if not source.startswith('@'):last[source]=index
        last[result]=len(self.instructions)
        live={x for x in self.inputs if x in last};peak=len(live)
        for index,instruction in enumerate(self.instructions):
            live.add(instruction['dst']);peak=max(peak,len(live))
            for name in list(live):
                if last.get(name,-1)<=index:live.remove(name)
        return dict(inputs=self.inputs,result=result,constants_U32=self.constants,instructions=self.instructions,
                    peak_live_value_registers_per_lane=peak,address_loop_registers=8,
                    RF_operand_bits_per_warp32=sum(len(i['src'])*32*32 for i in self.instructions),
                    RF_write_bits_per_warp32=len(self.instructions)*32*32,
                    input_landing_and_output_store_cycles=None,instruction_fetch_bits=None,
                    serial_cycles=None,fast_cycles=None,physical_qualified=False)

def recipe(kind):
    b=Builder(['a','b'] if kind in ('FADD','FMUL','SILU_GATE','NORMALIZE') else ['a'])
    if kind in ('FADD','FMUL'):result=b.emit(kind,'a','b')
    elif kind=='EXP':result=b.exp('a')
    elif kind=='RECIP':result=b.reciprocal('a')
    elif kind=='RSQRT':result=b.rsqrt('a')
    elif kind=='BF16':result=b.bf16('a')
    elif kind=='NORMALIZE':result=b.emit('FMUL','a',b.reciprocal('b'))
    elif kind=='SILU_GATE':
        exponent=b.exp(b.negate('a'))
        denominator=b.emit('FADD',exponent,b.constant('ONE',1))
        gate=b.emit('FMUL','a',b.reciprocal(denominator))
        result=b.emit('FMUL',gate,'b')
    else:raise ValueError('unbound ordinary GPU recipe')
    return b.finish(result)

def evaluate(program,**inputs):
    if set(inputs)!=set(program['inputs']):raise ValueError('exact runtime recipe inputs')
    registers={k:np.asarray(v,np.float32).view(np.uint32) for k,v in inputs.items()}
    constants={k:np.asarray(v,np.uint32) for k,v in program['constants_U32'].items()}
    for instruction in program['instructions']:
        code=instruction['opcode'];sources=instruction['src']
        if code not in ARITY or len(sources)!=ARITY[code]:raise ValueError('ordinary opcode arity')
        args=[]
        for source in sources:
            if source not in registers and source not in constants:raise ValueError('unbound RF source')
            args.append(registers[source] if source in registers else constants[source])
        if instruction['dst'] in registers:raise ValueError('SSA write collision')
        if code in ('FADD','FMUL'):
            a,b=[v.view(np.float32) for v in args]
            with np.errstate(over='ignore',invalid='ignore'):v=(a+b if code=='FADD' else a*b).astype(np.float32)
            value=np.where(v==0,np.float32(0),v).astype(np.float32).view(np.uint32)
        elif code in ('XOR','AND'):value=args[0]^args[1] if code=='XOR' else args[0]&args[1]
        elif code in ('IADD','ISUB'):
            wide=args[0].astype(np.uint64)+args[1].astype(np.uint64) if code=='IADD' else args[0].astype(np.uint64)-args[1].astype(np.uint64)
            value=wide.astype(np.uint32)
        elif code in ('SHR','SHL'):
            if np.any(args[1]>=32):raise ValueError('shift aperture')
            value=args[0]>>args[1] if code=='SHR' else args[0]<<args[1]
        elif code in ('UGT','ULT'):value=(args[0]>args[1] if code=='UGT' else args[0]<args[1]).astype(np.uint32)
        elif code=='FCMPGT':
            a,b=[v.view(np.float32) for v in args]
            if np.any(np.isnan(a)) or np.any(np.isnan(b)):raise ValueError('NaN compare wrapper unbound')
            value=(a>b).astype(np.uint32)
        elif code=='F2I':
            a=args[0].view(np.float32)
            if not np.all(np.isfinite(a)) or np.any(a!=np.trunc(a)) or np.any(a<-126) or np.any(a>127):raise ValueError('bounded integral F2I')
            value=a.astype(np.int32).view(np.uint32)
        registers[instruction['dst']]=np.asarray(value,np.uint32)
    return registers[program['result']].view(np.float32)

def striped_lines(base,size):
    """Read footprint, including partial endpoints; not service or cache credit."""
    if base<0 or size<=0:raise ValueError('address interval')
    first=base//128;last=(base+size-1)//128
    count=last-first+1
    return [max(0,(last-stack)//4-(first-1-stack)//4) for stack in range(4)]

def matrix_demands(graph):
    extents={(rank['die'],e['name']):e for rank in graph['memory_allocation'] for e in rank['extents']}
    result=[]
    for op in graph['instructions']:
        if op['opcode']!='MATRIX':continue
        d=graph['weight_descriptors'][op['attributes']['weight']];die=d['die']
        key=f"L{d['layer']}.{d['name']}" if d['layer'] is not None else 'head'
        codes=extents[die,key+'.codes'];scales=extents[die,key+'.scales']
        per_stack=striped_lines(codes['base'],codes['bytes'])
        scale_lines=striped_lines(scales['base'],scales['bytes'])
        local=[0]*4;cross=[0]*4;SM_total=[0]*4
        for sm in range(32):
            start=(d['rows']*sm)//32;stop=(d['rows']*(sm+1))//32
            if stop==start:continue
            lines=striped_lines(codes['base']+start*d['K'],(stop-start)*d['K'])
            quad=(sm//16)*2+(sm%8)//4
            for stack,n in enumerate(lines):
                SM_total[stack]+=n
                (local if quad==stack else cross)[stack]+=n
        result.append(dict(id=op['id'],weight=d['key'],dependencies=op['dependencies'],die=die,
                           output_rows=d['rows'],K=d['K'],golden_split=d['split'],weight_INT8_bytes=codes['bytes'],
                           code_base=codes['base'],row_BF16_scale_base=scales['base'],row_BF16_scale_bytes=scales['bytes'],
                           unique_code_128B_lines_by_stack=per_stack,unique_scale_128B_lines_by_stack=scale_lines,
                           uncached_per_SM_code_128B_lines_by_stack=SM_total,
                           candidate_local_code_line_requests_by_stack=local,candidate_cross_quad_code_line_requests_by_stack=cross,
                           candidate_quad_formula='SMrow=sm//8,SMcol=sm%8;quad=(SMrow//2)*2+SMcol//4;stack owns same-index quad',
                           addressed_SM_row_interval='[floor(rows*sm/32),floor(rows*(sm+1)/32));RMAX256 descriptor per tile,globaloffset=start+256*tile',
                           source_line_stripe='128B global line:stack=line%4,stackline=line//4',
                           client_count=36,read_sectors_per_line=4,
                           max_read_command_sectors=32,read_command_count_lower_bound_by_stack=[(n*4+31)//32 for n in per_stack],
                           command_count_scope='lower bound only; real coalescer grouping/tags/credits/epochs/clients and arbitration NOT bound',
                           request_return_service_fast_cycles=None,shared_bank_addresses=None,write_ACK_commit_route=None,
                           callback_timeline=None,hardware_lowering_qualified=False))
    return result

def manifest():
    kinds=['FADD','FMUL','EXP','RECIP','RSQRT','BF16','SILU_GATE','NORMALIZE']
    recipes={kind:recipe(kind) for kind in kinds}
    graph=compile_program();counts=Counter(op['opcode'] for op in graph['instructions'])
    direct={'RESIDUAL':'FADD','ROW_SCALE':'FMUL','SCALAR_MUL':'FMUL','SILU_GATE':'SILU_GATE','NORMALIZE':'NORMALIZE'}
    elementwise=[]
    for op in graph['instructions']:
        if op['opcode'] not in direct:continue
        shape=graph['register_shapes'][op['outputs'][0]]
        if any(not isinstance(d,int) for d in shape):raise ValueError('direct recipe symbolic output requires priced loop')
        elements=int(np.prod(shape)) if shape else 1
        p=recipes[direct[op['opcode']]];warps=(elements+31)//32
        elementwise.append(dict(id=op['id'],opcode=op['opcode'],recipe=direct[op['opcode']],dependencies=op['dependencies'],
                                inputs=op['inputs'],outputs=op['outputs'],participants=op['participants'],
                                elements_per_participant=elements,warp32_invocations_per_participant=warps,
                                inactive_tail_lanes_per_participant=warps*32-elements,
                                opcode_issues_per_participant={k:v*warps for k,v in Counter(i['opcode'] for i in p['instructions']).items()},
                                RF_operand_bits_per_participant=p['RF_operand_bits_per_warp32']*warps,
                                RF_write_bits_per_participant=p['RF_write_bits_per_warp32']*warps,
                                RF_bits_scope='conservative includes constant operands as RF reads; value bits plus8address-loop registers, not full RF floorplan',
                                constants_fetch_and_address_loop_cost=None,placement_and_shared_bank_map=None,
                                issue_writeback_serial_cycles=None,shared_service_fast_cycles=None))
    return dict(schema='opentallas.qwen-ordinary-scalar-lowering.v1',recipes=recipes,
                graph_source='tools/qwen_hbm_complete_program.py',instructions=len(graph['instructions']),
                semantic_instance_counts=dict(counts),direct_elementwise_recipes=direct,elementwise_instruction_instances=elementwise,
                matrix_weight_demand_instances=matrix_demands(graph),
                incomplete_macro_lowerings=[name for name in counts if name not in direct],
                SFU_policy='EXP/reciprocal/rsqrt expanded into ordinary separate ADD/MUL and integer instructions; no native SFU or DIV replacement',
                prerequisites=['Typed INT/compare area and contextual clock','Full operator chunk/tree reduction and register/address loops','Exact RF issue/writeback calendar','Shared bank/address maps and masks','Quad placement/locality','Loaded finite combined750Bpc controller/request-return/NoC/CDC/credits calendar'],
                full_program_GPU_lowering_qualified=False,physical_build_ready=False,token_cycles=None,token_rate=None)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    with args.out.open('x') as stream:json.dump(manifest(),stream,indent=2);stream.write('\n')
