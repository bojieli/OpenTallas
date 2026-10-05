#!/usr/bin/env python3
"""Polynomial source-order native stages in a reused explicit AW27 workspace.

Each SSA instruction executes once. Every source/destination array transfer uses
<=512B immutable provider tickets. Live ranges free pages only after reverse
consume; addresses never wrap. Intended for selection/metadata and bounded
families, not an unpriced per-op roundtrip performance lever.
"""
import math
from collections import Counter
import numpy as np
import h3_deepseek_complete_native as N
import h3_deepseek_streaming_linear as S

CAP=33554432;PAGE=512


class Arena:
    def __init__(self,base=0,occupied=()):
        if base<0 or base%PAGE or base+CAP>1<<27:raise ValueError('AW27 workspace aperture')
        if any(base<end and start<base+CAP for start,end in occupied):raise ValueError('workspace overlaps existing provider home')
        self.base=base;self.free=[(base,CAP)];self.live={};self.peak=0
    def reserve(self,name,n):
        if name in self.live:raise ValueError('duplicate SSA owner')
        length=max(PAGE,((n+511)//512)*512)
        for j,(base,size) in enumerate(self.free):
            if size>=length:
                self.free[j:j+1]=[(base+length,size-length)] if size>length else [];self.live[name]=(base,length,n)
                self.peak=max(self.peak,sum(x[1] for x in self.live.values()));return base
        raise RuntimeError('finite workspace capacity exhausted; no modulo alias')
    def release(self,name,memory):
        memory.fence();base,length,_=self.live.pop(name);self.free.append((base,length));self.free.sort();merged=[]
        for addr,n in self.free:
            if merged and merged[-1][0]+merged[-1][1]==addr:merged[-1]=(merged[-1][0],merged[-1][1]+n)
            else:merged.append((addr,n))
        self.free=merged


def plan(program):
    f=S.footprint(program);counts=f['scalar_evaluations_by_opcode'];extra=sum(512 for _ in program['code'])
    bound=f['typed_live_bytes']+f['transient_and_output_reserve_bytes']+extra
    return {'source_order_stages':len(program['code']),'scalar_evaluations_by_opcode':counts,'primitive_scalars':sum(counts.values()),
        'recomputed_dependency_scalars':0,'typed_live_bytes':f['typed_live_bytes'],'page_padding_conservative_bytes':extra,
        'workspace_upper_bytes':bound,'workspace_cap':CAP,'AW':27,'fits':bound<=CAP,'128lane_batches':sum((max(1,math.prod(i['shape']))+127)//128 for i in program['code']),
        'algorithm':'exact source native stage order, live-range page reuse, no alternate comparison/tie/rounding contract',
        'source_read_and_dest_write_512B_transfers':'ceil(shape*dtype/512) per actual operand read/dest write; executed counts reported',
        'latency_cycles':None,'hardware_admitted':False,'route_and_port_costs_required':True}


class StagedMachine:
    def __init__(self,program,inputs,owner,base=0,occupied=()):
        self.program=program;self.inputs=inputs;self.owner=tuple(owner);self.arena=Arena(base,occupied)
        self.memory=N.PersistentMemory(credits=1);self.spec={};self.events=[];self.counts=Counter();self.commands=Counter();self.bytes=Counter();self.fault=False
        if not plan(program)['fits']:raise ValueError('source-order staged program exceeds bounded live-range cap')
    def write(self,name,value):
        raw=value.tobytes();base=self.arena.reserve(name,len(raw));self.spec[name]=(value.shape,value.dtype)
        for off in range(0,len(raw),512):
            self.memory.transact(('arena',*self.owner,base+off),write=True,payload=raw[off:off+512]);self.commands['write']+=1;self.bytes['write']+=len(raw[off:off+512])
    def read(self,name):
        base,length,n=self.arena.live[name];shape,dtype=self.spec[name];parts=[]
        for off in range(0,n,512):
            parts.append(self.memory.transact(('arena',*self.owner,base+off)));self.commands['read']+=1;self.bytes['read']+=len(parts[-1])
        return np.frombuffer(b''.join(parts),dtype=dtype).copy().reshape(shape)
    def run(self):
        last={};outputs=self.program['outputs'];end=len(self.program['code'])
        for pc,i in enumerate(self.program['code']):
            for v in i['src']:last[v]=pc
        for v in outputs.values():last[v]=end
        for pc,i in enumerate(self.program['code']):
            for v in list(self.arena.live):
                if last.get(v,-1)<pc:self.arena.release(v,self.memory);del self.spec[v]
            op=i['op'];prefix=[];memory={};src=[]
            for j,v in enumerate(i['src']):
                value=self.read(v);name='a'+str(j);key='s'+str(j);memory[name]=value;src.append(key)
                dtype='F32' if value.dtype==np.float32 else 'U32' if value.dtype==np.uint32 else 'I64'
                prefix.append({'dst':key,'src':[],'op':'LOAD','shape':list(value.shape),'attrs':{'name':name,'dtype':dtype}})
            node={**i,'dst':'out','src':src}
            if op=='LOAD':memory[i['attrs']['name']]=self.inputs[i['attrs']['name']]
            if op=='PACKET_COMMIT' and self.fault:raise ValueError('fault prevents successful publication')
            vm=N.Machine({'code':prefix+[node],'outputs':{'out':'out'}},memory,N.primitive_div);value=vm.run()['out'];self.fault|=vm.fault
            self.write(i['dst'],value);self.counts[op]+=max(1,value.size)
            self.events.append({'stage':pc,'op':op,'batches128':(max(1,value.size)+127)//128,'live_bytes':sum(x[1] for x in self.arena.live.values())})
        observed={name:self.read(v) for name,v in outputs.items()};self.memory.fence()
        for v in list(self.arena.live):self.arena.release(v,self.memory)
        return ({} if self.fault else observed),{'status':'FAULT_NO_VERSION_PUBLICATION' if self.fault else 'PASS_SOURCE_ORDER_STAGED_NATIVE',
            'executed_primitive_scalars':dict(self.counts),'recomputed_dependency_scalars':0,'provider_commands':dict(self.commands),'provider_bytes':dict(self.bytes),
            'workspace_peak_bytes':self.arena.peak,'workspace_AW':27,'stages':self.events,'provider':self.memory.summary(),'physical_visibility_qualified':False,'latency_cycles':None}
