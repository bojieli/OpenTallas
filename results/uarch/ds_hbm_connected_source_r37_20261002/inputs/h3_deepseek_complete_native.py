#!/usr/bin/env python3
"""Complete DS source-PC to executable ordinary instruction IR.

Compilation never reads payloads. Numerical execution is a finite tensor-loop
interpreter: each array instruction expands into 128-lane batches, not unlimited
GPU lanes. No source opcode, golden function or Python kernel callback executes.
DIV is an external Epicurus primitive ABI; tests reuse the source-pinned exact
rational contract, never a macro handler or timing oracle.
"""
import argparse
from collections import Counter
import gzip
import importlib.util
import hashlib
import json
from pathlib import Path
import numpy as np
import h3_versioned_lowering as H
from deepseek_hbm_complete_memory import PersistentMemory

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = set(('linear_q swiglu all_gather hc_mixes hc_pre_norm hc_post mv q_norm_kv_row q_rope attend wo_a_part all_reduce router_act route expert_fetch moe_sum topk_merge linear_bf16 index_q index_scores topk_local kv_gather compressor cand_mask engram_fetch engram_mix cand_local cand_apply final_norm argmax_local').split())
NATIVE = {'LOAD','CONST','RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST','TAKE','SCATTER','FADD','FMUL','DIV','SQRT','FMAX','FMIN','FCMP_GT','FCMP_LT','FCMP_EQ','SELECT','BITCAST_U','BITCAST_F','SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD','I2F','F2I','LDEXP','PACKET_COMMIT','ASSERT','IOTA'}

class Builder:
    def __init__(self): self.code=[]; self.shapes={}; self.outputs={}; self.providers={}
    def emit(self,op,*src,shape=(),**attrs):
        if op not in NATIVE: raise ValueError('non-native opcode '+op)
        dst='v'+str(len(self.code)); shape=tuple(shape)
        self.code.append(dict(op=op,dst=dst,src=list(src),shape=list(shape),attrs=attrs))
        self.shapes[dst]=shape; return dst
    def load(self,name,shape,dtype='F32',role='operand'):
        self.providers[name]=dict(shape=list(shape),dtype=dtype,role=role)
        return self.emit('LOAD',shape=shape,name=name,dtype=dtype)
    def iota(self,n):return self.emit('IOTA',shape=(n,))
    def const(self,value,dtype='F32'):
        a=np.asarray(value)
        if dtype=='F32':return self.emit('CONST',shape=a.shape,bits=np.asarray(value,np.float32).view(np.uint32).tolist(),dtype=dtype)
        return self.emit('CONST',shape=a.shape,value=a.tolist(),dtype=dtype)
    def op(self,op,a,b=None):
        shape=np.broadcast_shapes(self.shapes[a],self.shapes[b]) if b else self.shapes[a]
        return self.emit(op,*([a,b] if b else [a]),shape=shape)
    def reshape(self,a,shape):
        if np.prod(shape,dtype=np.int64)!=np.prod(self.shapes[a],dtype=np.int64): raise ValueError('reshape element count')
        return self.emit('RESHAPE',a,shape=shape)
    def slice(self,a,axis,start,stop,step=1):
        s=list(self.shapes[a]);s[axis]=len(range(*slice(start,stop,step).indices(s[axis])))
        return self.emit('SLICE',a,shape=s,axis=axis,start=start,stop=stop,step=step)
    def at(self,a,index,axis=0):
        r=self.slice(a,axis,index,index+1);s=list(self.shapes[r]);s.pop(axis);return self.reshape(r,s)
    def transpose(self,a,axes):return self.emit('TRANSPOSE',a,shape=[self.shapes[a][i] for i in axes],axes=list(axes))
    def broadcast(self,a,shape):return self.emit('BROADCAST',a,shape=shape)
    def concat(self,values,axis=0):
        s=list(self.shapes[values[0]]);s[axis]=sum(self.shapes[v][axis] for v in values)
        return self.emit('CONCAT',*values,shape=s,axis=axis)
    def stack(self,values,axis=0):
        return self.concat([self.reshape(v,list(self.shapes[v][:axis])+[1]+list(self.shapes[v][axis:])) for v in values],axis)
    def neg(self,a):return self.op('BITCAST_F',self.op('XOR',self.op('BITCAST_U',a),self.const(0x80000000,'U32')))
    def abs(self,a):return self.op('BITCAST_F',self.op('AND',self.op('BITCAST_U',a),self.const(0x7fffffff,'U32')))
    def bf16(self,a):
        u=self.op('BITCAST_U',a);lsb=self.op('AND',self.op('SHR',u,self.const(16,'U32')),self.const(1,'U32'))
        u=self.op('IADD',self.op('IADD',u,self.const(0x7fff,'U32')),lsb)
        return self.op('BITCAST_F',self.op('AND',u,self.const(0xffff0000,'U32')))
    def seq(self,terms,zero=False):
        if not terms: return self.const(0.)
        a=self.broadcast(self.const(0.),self.shapes[terms[0]]) if zero else terms[0]
        for t in terms if zero else terms[1:]:a=self.op('FADD',a,t)
        return a
    def reduce(self,a,axis=-1,mode='chunk8'):
        axis%=len(self.shapes[a]);axes=[i for i in range(len(self.shapes[a])) if i!=axis]+[axis]
        x=self.transpose(a,axes);s=self.shapes[x];n=s[-1]
        if n==0: return self.broadcast(self.const(0.),s[:-1])
        if mode=='seq':return self.seq([self.at(x,i,-1) for i in range(n)])
        if mode=='max':
            a=self.at(x,0,-1)
            for i in range(1,n):a=self.op('FMAX',a,self.at(x,i,-1))
            return a
        nc=(n+7)//8
        if nc*8!=n:x=self.concat([x,self.broadcast(self.const(0.),s[:-1]+(nc*8-n,))],len(s)-1)
        x=self.reshape(x,s[:-1]+(nc,8));a=self.broadcast(self.const(0.),s[:-1]+(nc,))
        for i in range(8):a=self.op('FADD',a,self.at(x,i,-1))
        padded=1<<(nc-1).bit_length()
        if padded!=nc:a=self.concat([a,self.broadcast(self.const(0.),s[:-1]+(padded-nc,))],len(s)-1)
        while self.shapes[a][-1]>1:a=self.op('FADD',self.slice(a,-1,0,None,2),self.slice(a,-1,1,None,2))
        return self.reshape(a,s[:-1])
    def exp(self,x):
        x=self.op('FMIN',self.op('FMAX',x,self.const(-87.)),self.const(88.))
        t=self.op('FMUL',x,self.const(1.4426950408889634));n=self.op('FADD',self.op('FADD',t,self.const(12582912.)),self.const(-12582912.))
        r=self.op('FADD',self.op('FADD',x,self.neg(self.op('FMUL',n,self.const(.693145751953125)))),self.neg(self.op('FMUL',n,self.const(1.428606765330187e-6))))
        p=self.const(1/720)
        for c in [1/120,1/24,1/6,.5,1.,1.]:p=self.op('FADD',self.op('FMUL',p,r),self.const(c))
        delta=self.op('SHL',self.op('F2I',n),self.const(23,'U32'))
        return self.op('BITCAST_F',self.op('IADD',self.op('BITCAST_U',p),delta))
    def rsqrt(self,x):
        y=self.op('BITCAST_F',self.op('ISUB',self.const(0x5f3759df,'U32'),self.op('SHR',self.op('BITCAST_U',x),self.const(1,'U32'))));half=self.op('FMUL',x,self.const(.5))
        for _ in range(3):y=self.op('FMUL',y,self.op('FADD',self.const(1.5),self.neg(self.op('FMUL',half,self.op('FMUL',y,y)))))
        return y
    def sigmoid(self,x):return self.op('DIV',self.const(1.),self.op('FADD',self.exp(self.neg(x)),self.const(1.)))
    def norm(self,x,gamma,eps):
        n=self.shapes[x][-1];ss=self.reduce(self.op('FMUL',x,x));r=self.rsqrt(self.op('FADD',self.op('DIV',ss,self.const(n)),self.const(eps)))
        r=self.reshape(r,self.shapes[r]+(1,))
        return self.bf16(self.op('FMUL',gamma,self.op('FMUL',x,r)))
    def dot(self,a,b):
        # a [M,K], b [N,K]; each product rounded before ordered chunk8.
        m,k=self.shapes[a];n,kb=self.shapes[b]
        if k!=kb:raise ValueError('dot K')
        return self.reduce(self.op('FMUL',self.reshape(a,(m,1,k)),self.reshape(b,(1,n,k))))
    def rope(self,x,c,s,inverse=False):
        rd=2*self.shapes[c][-1];n=self.shapes[x][-1];prefix=self.slice(x,-1,0,n-rd)
        a=self.slice(x,-1,n-rd,n,2);b=self.slice(x,-1,n-rd+1,n,2)
        re=self.op('FADD',self.op('FMUL',a,c),self.op('FMUL',b,s) if inverse else self.neg(self.op('FMUL',b,s)))
        im=self.op('FADD',self.op('FMUL',b,c),self.neg(self.op('FMUL',a,s)) if inverse else self.op('FMUL',a,s))
        pair=self.stack([self.bf16(re),self.bf16(im)],len(self.shapes[re]));pair=self.reshape(pair,self.shapes[x][:-1]+(rd,))
        return self.concat([prefix,pair],len(self.shapes[x])-1)
    def sinkhorn(self,comb,eps):
        mx=self.reshape(self.reduce(comb,axis=1,mode='max'),(4,1));e=self.exp(self.op('FADD',comb,self.neg(mx)))
        den=self.reshape(self.reduce(e,axis=1,mode='seq'),(4,1));comb=self.op('FADD',self.op('DIV',e,den),self.const(eps))
        for turn in range(39):
            axis=0 if turn%2==0 else 1
            den=self.reduce(comb,axis=axis,mode='seq');den=self.op('FADD',den,self.const(eps))
            comb=self.op('DIV',comb,self.reshape(den,(1,4) if axis==0 else (4,1)))
        return comb
    def take(self,x,ids,axis=0):
        s=list(self.shapes[x]);s[axis:axis+1]=list(self.shapes[ids]);return self.emit('TAKE',x,ids,shape=s,axis=axis)
    def topk(self,v,ids,k):
        # Finite sequential insertion selection, explicit lowest-global-ID tie.
        n=self.shapes[v][0];k=min(k,n);alive=self.broadcast(self.const(1,'U32'),(n,));values=[];indices=[]
        for _ in range(k):
            best=self.const(-np.inf);bid=self.const(0x7fffffffffffffff,'I64');bpos=self.const(0,'I64')
            for j in range(n):
                val=self.at(v,j);idx=self.at(ids,j);enabled=self.at(alive,j)
                greater=self.op('FCMP_GT',val,best);tie=self.op('AND',self.op('FCMP_EQ',val,best),self.op('FCMP_LT',idx,bid))
                win=self.op('AND',enabled,self.op('OR',greater,tie))
                best=self.emit('SELECT',win,val,best,shape=());bid=self.emit('SELECT',win,idx,bid,shape=());bpos=self.emit('SELECT',win,self.const(j,'I64'),bpos,shape=())
            values.append(best);indices.append(bid)
            alive=self.emit('SCATTER',alive,bpos,self.const(0,'U32'),shape=(n,),axis=0)
        return self.stack(values),self.stack(indices)
    def codec(self,x,fmt,block=32):
        # Format midpoint comparisons, exact binary products within finite scale ABI.
        shape=self.shapes[x];n=int(np.prod(shape));xb=self.reshape(x,(n//block,block));a=self.abs(xb)
        floor=1e-4 if fmt=='FP8' else 6*2.**(-126 if fmt=='FP4E8' else -9)
        mx=self.op('FMAX',self.reduce(a,mode='max'),self.const(floor))
        if fmt!='FP4E4':
            scaled=self.op('FMUL',mx,self.const(1/(448 if fmt=='FP8' else 6)))
            bits=self.op('BITCAST_U',scaled);ex=self.op('ISUB',self.op('AND',self.op('SHR',bits,self.const(23,'U32')),self.const(255,'U32')),self.const(127,'U32'))
            extra=self.op('FCMP_GT',self.op('AND',bits,self.const(0x7fffff,'U32')),self.const(0,'U32'))
            ex=self.op('IADD',ex,extra);scale=self.op('LDEXP',self.const(1.),ex)
            values=positive_codes(fmt=='FP8')
        else:
            # amax/6 uses exact midpoint comparisons: compare amax to 6*E4M3 midpoint.
            sv=positive_codes(True);scale=self.broadcast(self.const(0.),self.shapes[mx])
            for i in range(len(sv)-1):
                threshold=(sv[i]+sv[i+1])*3
                gt=self.op('FCMP_GT',mx,self.const(threshold));eq=self.op('FCMP_EQ',mx,self.const(threshold))
                hit=self.op('OR',gt,eq if (i+1)%2==0 else self.broadcast(self.const(0,'U32'),self.shapes[eq]))
                scale=self.emit('SELECT',hit,self.const(sv[i+1]),scale,shape=self.shapes[mx])
            values=positive_codes(False);ex=None
        sb=self.reshape(scale,(n//block,1));q=self.broadcast(self.const(0.),self.shapes[xb]);code=self.broadcast(self.const(0,'U32'),self.shapes[xb])
        for i in range(len(values)-1):
            # These binary tables and scales have exact F32 threshold products.
            th=self.op('FMUL',sb,self.const((values[i]+values[i+1])/2))
            gt=self.op('FCMP_GT',a,th);eq=self.op('FCMP_EQ',a,th)
            hit=self.op('OR',gt,eq if (i+1)%2==0 else self.broadcast(self.const(0,'U32'),self.shapes[eq]))
            q=self.emit('SELECT',hit,self.const(values[i+1]),q,shape=self.shapes[xb]);code=self.emit('SELECT',hit,self.const(i+1,'U32'),code,shape=self.shapes[xb])
        sign=self.op('FCMP_LT',xb,self.const(0.));code=self.op('OR',code,self.op('IMUL',sign,self.const(128 if fmt=='FP8' else 8,'U32')));q=self.emit('SELECT',sign,self.neg(q),q,shape=self.shapes[q])
        decoded=self.bf16(self.emit('FMUL',q,sb,shape=self.shapes[q],canonical_zero=False))
        flatcode=self.reshape(code,(n,))
        packed=flatcode if fmt=='FP8' else self.op('OR',self.slice(flatcode,0,0,None,2),self.op('SHL',self.slice(flatcode,0,1,None,2),self.const(4,'U32')))
        self.codec_metadata={'codes':packed,'scale':ex if ex is not None else scale,'format':fmt}
        return self.reshape(decoded,shape),q,ex
    def output(self,name,v):self.outputs[name]=v
    def finish(self):
        last={}
        for pc,i in enumerate(self.code):
            for v in i['src']:last[v]=pc
        for v in self.outputs.values():last[v]=len(self.code)
        live={};peak=0;peak_words=0;free=list(range(24));slots={};spill={};nextspill=0
        for pc,i in enumerate(self.code):
            for v in list(live):
                if last.get(v,-1)<pc:
                    if v in slots:free.append(slots[v])
                    del live[v]
            v=i['dst'];words=max(1,int(np.prod(i['shape'])));live[v]=words
            if free:slots[v]=free.pop(0);i['rf_scalar_slot']=slots[v]
            else:spill[v]=nextspill;nextspill+=words*4;i['logical_workspace_spill_offset']=spill[v]
            peak=max(peak,len(live));peak_words=max(peak_words,sum(live.values()))
        return dict(code=self.code,outputs=self.outputs,providers=self.providers,
            resources={'RF_read_ports':2,'RF_write_ports':1,'lanes_per_SM':128,'SMs_per_rank':32,
                'peak_live_scalar_values':peak,'address_control_registers':8,'RF_scalar_slots':24,
                'workspace_spill_bytes_logical':nextspill,'workspace_spill_resident_base':None,
                'peak_interpreter_live_words':peak_words,'unbounded_lanes_credited':False,
                'tensor_instruction_execution':'finite128lane batch loops; no host macro or callback',
                'shared_per_SM_bytes':65536,'workspace_shared_reservation_bytes':8192,
                'materialized_tensor_workspace_bytes':peak_words*4,'tensor_workspace_resident_base':None,
                'streaming_tiling_fit_proved':False,
                'instruction_batches128_by_opcode':dict(Counter({op:sum((max(1,int(np.prod(i['shape'])))+127)//128 for i in self.code if i['op']==op) for op in {i['op'] for i in self.code}})),
                'RF_transaction_geometry_bytes':{'two_operand_read':1024,'mirrored_logical_write':512},
                'no_extra_RF_ports':True,'predicate_SELECT_port_bits_per_lane':1,
                'hardware_latency':None,'area_slot_fit':None,'physical_qualified':False})


def positive_codes(fp8):
    if not fp8:return [0.,.5,1.,1.5,2.,3.,4.,6.]
    return [m/8*2.**-6 if e==0 else (1+m/8)*2.**(e-7) for e in range(16) for m in range(8) if not(e==15 and m==7)]

class Machine:
    def __init__(self,program,memory,div=None):
        self.program=program;self.memory=memory;self.div=div;self.events=[];self.fault=False;self.error_events=[]
    def run(self):
        r={};last={}
        for pc,i in enumerate(self.program['code']):
            for x in i['src']:last[x]=pc
        for x in self.program['outputs'].values():last[x]=len(self.program['code'])
        for pc,i in enumerate(self.program['code']):
            op=i['op'];at=i['attrs'];a=[r[x] for x in i['src']]
            if op=='IOTA':v=np.arange(i['shape'][0],dtype=np.int64)
            elif op=='LOAD':
                if at['name'] not in self.memory:raise ValueError('unbound native provider '+at['name'])
                v=np.asarray(self.memory[at['name']],dtype={'F32':np.float32,'U32':np.uint32,'I64':np.int64}[at['dtype']])
            elif op=='CONST':
                v=np.asarray(at['bits'],np.uint32).view(np.float32) if at['dtype']=='F32' else np.asarray(at['value'],dtype={'U32':np.uint32,'I64':np.int64}[at['dtype']])
            elif op=='RESHAPE':v=a[0].reshape(i['shape'])
            elif op=='SLICE':
                sl=[slice(None)]*a[0].ndim;sl[at['axis']]=slice(at['start'],at['stop'],at['step']);v=a[0][tuple(sl)]
            elif op=='TRANSPOSE':v=a[0].transpose(at['axes'])
            elif op=='CONCAT':v=np.concatenate(a,axis=at['axis'])
            elif op=='BROADCAST':v=np.broadcast_to(a[0],i['shape'])
            elif op=='TAKE':
                if np.any(a[1]<0) or np.any(a[1]>=a[0].shape[at['axis']]):raise ValueError('native address range')
                v=np.take(a[0],a[1].astype(np.int64),axis=at['axis'])
            elif op=='SCATTER':
                v=a[0].copy();idx=int(a[1]);
                if not 0<=idx<v.shape[at['axis']]:raise ValueError('native scatter range')
                sl=[slice(None)]*v.ndim;sl[at['axis']]=idx;v[tuple(sl)]=a[2]
            elif op in ('FADD','FMUL','DIV','SQRT'):
                with np.errstate(all='ignore'):
                    if op=='DIV':
                        if self.div is None:raise ValueError('Epicurus exact DIV provider required')
                        v,errors=self.div(a[0],a[1]);self.fault|=bool(np.any(errors))
                        if np.any(errors):self.error_events.append({'pc':pc,'op':op,'errors':np.asarray(errors,np.uint32).tolist()})
                    else:v=a[0]+a[1] if op=='FADD' else a[0]*a[1] if op=='FMUL' else np.sqrt(a[0])
                v=np.asarray(v,np.float32);self.fault|=bool(np.any(~np.isfinite(v)));v=(np.where(v==0,np.float32(0),v) if at.get('canonical_zero',True) else v).astype(np.float32)
            elif op in ('FMAX','FMIN'):v=np.maximum(*a) if op=='FMAX' else np.minimum(*a)
            elif op.startswith('FCMP'):v=np.asarray(a[0]>a[1] if op=='FCMP_GT' else a[0]<a[1] if op=='FCMP_LT' else a[0]==a[1],np.uint32)
            elif op=='SELECT':v=np.where(a[0]!=0,a[1],a[2])
            elif op=='BITCAST_U':v=a[0].astype(np.float32,copy=False).view(np.uint32)
            elif op=='BITCAST_F':v=a[0].astype(np.uint32,copy=False).view(np.float32)
            elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
                wide=any(x.dtype==np.int64 for x in a);dtype=np.int64 if wide else np.uint32
                x,y=[z.astype(dtype) for z in a]
                if op in ('SHR','SHL') and np.any((y<0)|(y>=64 if wide else y>=32)):raise ValueError('native shift range')
                with np.errstate(all='ignore'):
                    v={'SHR':lambda:x>>y,'SHL':lambda:x<<y,'AND':lambda:x&y,'OR':lambda:x|y,'XOR':lambda:x^y,'IADD':lambda:x+y,'ISUB':lambda:x-y,'IMUL':lambda:x*y,'IMOD':lambda:x%y}[op]().astype(dtype)
            elif op=='I2F':v=a[0].astype(np.float32)
            elif op=='F2I':v=a[0].astype(np.int64)
            elif op=='LDEXP':
                with np.errstate(all='ignore'):v=np.ldexp(a[0].astype(np.float32),a[1].astype(np.uint32).view(np.int32) if a[1].dtype==np.uint32 else a[1].astype(np.int32)).astype(np.float32)
                self.fault|=bool(np.any(~np.isfinite(v)))
            elif op=='ASSERT':
                if not np.all(a[0]):raise ValueError('native assertion '+at.get('reason',''))
                v=a[0].copy()
            elif op=='PACKET_COMMIT':
                if self.fault:raise ValueError('fault prevents successful publication')
                v=a[0].copy()
            else:raise ValueError('native instruction unimplemented '+op)
            if list(v.shape)!=i['shape']:raise ValueError('native shape '+op+str(v.shape)+str(i['shape']))
            r[i['dst']]=v.copy();self.events.append({'pc':pc,'op':op,'batches128':(v.size+127)//128,'bytes':v.nbytes,'fault':self.fault})
            for x in list(r):
                if last.get(x,-1)<=pc and x not in self.program['outputs'].values():del r[x]
        return {k:r[v].copy() for k,v in self.program['outputs'].items()}



def execute_finite(program, inputs, owner, transport=None):
    """Join native primitives to the existing finite SOFTWARE provider.

    Owner is (PC, version, rank, SM, provider_generation). Each accepted fragment
    uses the existing immutable ticket and is consumed before credit reuse.
    This logical store event does not assert causal physical visibility.
    """
    if not isinstance(owner,tuple) or len(owner)!=5 or any(not isinstance(x,(int,str)) for x in owner):
        raise ValueError('explicit versioned owner identity required')
    transport=PersistentMemory(credits=1) if transport is None else transport
    if transport.credits!=1:raise ValueError('selected owner depth1 contract')
    transport.fence();memory={}
    for name,spec in program['providers'].items():
        if name not in inputs:raise ValueError('unbound native provider '+name)
        dtype={'F32':np.float32,'U32':np.uint32,'I64':np.int64}[spec['dtype']]
        value=np.asarray(inputs[name],dtype=dtype)
        if list(value.shape)!=spec['shape']:raise ValueError('provider geometry '+name)
        key=('native_input',*owner,name);transport.write_object(key,value.tobytes())
        memory[name]=np.frombuffer(transport.read_object(key),dtype=dtype).copy().reshape(value.shape)
    vm=Machine(program,memory,primitive_div);outputs=vm.run()
    published={}
    if not vm.fault:
        for name,value in outputs.items():
            key=('native_output',*owner,name);transport.write_object(key,value.tobytes())
            published[name]=np.frombuffer(transport.read_object(key),dtype=value.dtype).copy().reshape(value.shape)
    transport.fence()
    return published,{'status':'FAULT_NO_OUTPUT_PUBLICATION' if vm.fault else 'PASS_NATIVE_LOGICAL_PROVIDER_JOIN',
        'owner':list(owner),'errors':vm.error_events,'instruction_events':vm.events,
        'provider':transport.summary(),'physical_visibility_qualified':False,'timing_cycles':None}


SCALAR_DEPENDENCY='results/uarch/h3_deepseek_complete_native_20261002/dependencies/h3_exact_scalar_contract.py'
_scalar_spec=importlib.util.spec_from_file_location('Epicurus_exact_scalar',ROOT/SCALAR_DEPENDENCY)
_scalar=importlib.util.module_from_spec(_scalar_spec);_scalar_spec.loader.exec_module(_scalar)

def primitive_div(a,b):
    """Reuse Epicurus exact rational contract; no new divider implementation."""
    a,b=np.broadcast_arrays(np.asarray(a,np.float32),np.asarray(b,np.float32));out=np.empty(a.shape,np.uint32);errors=np.empty(a.shape,np.uint32)
    for idx in np.ndindex(a.shape):out[idx],errors[idx]=_scalar.div_contract(int(a[idx].view(np.uint32)),int(b[idx].view(np.uint32)))
    return out.view(np.float32),errors

# Native compare/exchange network: no argsort/topk host callback.
def native_topk(b,v,ids,k):
    n=b.shapes[v][0];k=min(k,n)
    if not n:return b.broadcast(b.const(0.),(0,)),b.broadcast(b.const(0,'I64'),(0,))
    p=1<<(n-1).bit_length()
    if p>n:
        v=b.concat([v,b.broadcast(b.const(-np.inf),(p-n,))]);ids=b.concat([ids,b.broadcast(b.const(0x7fffffffffffffff,'I64'),(p-n,))])
    width=2
    while width<=p:
        distance=width//2
        while distance:
            lane=b.iota(p);j=b.op('XOR',lane,b.const(distance,'I64'));other=b.take(v,j);oi=b.take(ids,j)
            greater=b.op('FCMP_GT',v,other);tie=b.op('AND',b.op('FCMP_EQ',v,other),b.op('FCMP_LT',ids,oi));better=b.op('OR',greater,tie)
            take_best=b.op('FCMP_EQ',b.op('FCMP_EQ',b.op('AND',lane,b.const(width,'I64')),b.const(0,'I64')),b.op('FCMP_EQ',b.op('AND',lane,b.const(distance,'I64')),b.const(0,'I64')))
            take_self=b.op('FCMP_EQ',better,take_best)
            v=b.emit('SELECT',take_self,v,other,shape=(p,));ids=b.emit('SELECT',take_self,ids,oi,shape=(p,))
            distance//=2
        width*=2
    return b.slice(v,0,0,k),b.slice(ids,0,0,k)
Builder.topk=native_topk


def integer_sum(b,x,axis=-1):
    a=b.at(x,0,axis)
    for j in range(1,b.shapes[x][axis]):a=b.op('IADD',a,b.at(x,j,axis))
    return a


def linear_quantized(b,x,rows,k,fmt="fp8"):
    _,q,ex=b.codec(x,'FP8');q=b.reshape(q,(k//32,32));q=b.op('F2I',b.op('FMUL',q,b.const(512.)))
    if fmt=='fp4':
        codes=b.load('weight_codes',(rows,k//2),'U32','packed E2M1 weight low nibble first')
        lo=b.op('AND',codes,b.const(15,'U32'));hi=b.op('SHR',codes,b.const(4,'U32'));indices=b.reshape(b.stack([lo,hi],2),(rows,k))
        table=b.const([0,256,512,768,1024,1536,2048,3072,0,-256,-512,-768,-1024,-1536,-2048,-3072],'I64')
    else:
        indices=b.load('weight_codes',(rows,k),'U32','E4M3 weight bytes')
        good=b.op('FCMP_LT',b.op('AND',indices,b.const(127,'U32')),b.const(127,'U32'));b.emit('ASSERT',good,shape=(rows,k),reason='finite weight E4M3 codes')
        positive=[int(v*512) for v in positive_codes(True)]+[0];table=b.const(positive+[-v for v in positive],'I64')
    w=b.reshape(b.take(table,indices),(rows,k//32,32))
    scale=b.load('weight_scale_codes',(rows,k//32),'U32','paired UE8M0 weight scale bytes')
    b.emit('ASSERT',b.op('FCMP_LT',scale,b.const(255,'U32')),shape=(rows,k//32),reason='finite weight exponent codes')
    we=b.op('ISUB',scale,b.const(127,'I64'))
    prod=b.op('IMUL',w,b.reshape(q,(1,k//32,32)))
    acc=integer_sum(b,prod);power=b.op('ISUB',b.op('IADD',we,b.reshape(ex,(1,k//32))),b.const(18,'I64'))
    block=b.op('LDEXP',b.op('I2F',acc),power)
    return b.bf16(b.reduce(block))


def index_dot(b,q,k):
    # Decoded E2M1/UE8M0 values: exact common block scales supplied explicitly.
    heads,width=b.shapes[q];rows,_=b.shapes[k];blocks=width//32
    def unpack(name,count):
        packed=b.load(name+'_codes',(count,width//2),'U32','paired packed E2M1 nibbles, low nibble first')
        lo=b.op('AND',packed,b.const(15,'U32'));hi=b.op('SHR',packed,b.const(4,'U32'))
        code=b.reshape(b.stack([lo,hi],2),(count,width))
        table=b.const([0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12],'I64')
        return b.reshape(b.take(table,code),(count,blocks,32))
    qu=unpack('query',heads);ku=unpack('key',rows)
    qe=b.load('query_exp',(heads,blocks),'I64','query UE8M0 exponent source bundle');ke=b.load('key_exp',(rows,blocks),'I64','key paired4scale bytes')
    prod=b.op('IMUL',b.reshape(qu,(heads,1,blocks,32)),b.reshape(ku,(1,rows,blocks,32)))
    power=b.op('ISUB',b.op('IADD',b.reshape(qe,(heads,1,blocks)),b.reshape(ke,(1,rows,blocks))),b.const(2,'I64'))
    for source,units,ex in [(q,qu,qe),(k,ku,ke)]:
        decoded=b.reshape(b.bf16(b.op('LDEXP',b.op('FMUL',b.op('I2F',units),b.const(.5)),b.reshape(ex,b.shapes[ex]+(1,)))),b.shapes[source])
        b.emit('ASSERT',b.op('FCMP_EQ',source,decoded),shape=b.shapes[source],reason='index integer units/exponent match produced BF16 operand')
    dots=b.reduce(b.op('LDEXP',b.op('I2F',integer_sum(b,prod)),power));return b.bf16(dots)


def softplus(b,x):
    t=b.exp(b.neg(b.abs(x)));u=b.op('DIV',t,b.op('FADD',t,b.const(2.)));u2=b.op('FMUL',u,u);p=b.const(1/17)
    for i in range(7,-1,-1):p=b.op('FADD',b.op('FMUL',p,u2),b.const(1/(2*i+1)))
    log=b.op('FMUL',b.op('FMUL',u,p),b.const(2.));return b.op('FADD',b.op('FMAX',x,b.const(0.)),log)


def recipe(family,shape=None,attrs=None):
    """Emit standalone executable primitive program, with explicit provider ABI."""
    shape=shape or {};attrs=attrs or {};b=Builder();n=shape.get('n',5120);k=shape.get('k',5120);rows=shape.get('rows',4);heads=shape.get('heads',32);width=shape.get('width',128)
    eps=1e-20;heps=1e-6
    def load(name,s,dtype='F32',role='operand'):return b.load(name,s,dtype,role)
    def cstable(w,prefix='rope'):return load(prefix+'_cos',(min(32,w//2),),role='coefficient table row'),load(prefix+'_sin',(min(32,w//2),),role='coefficient table row')
    if family in ('mv','linear_bf16','wo_a_part','linear_q'):
        x=load('x',(k,));r=shape.get('rows',4)
        if family=='linear_q':out=linear_quantized(b,x,r,k,attrs.get("fmt","fp8"))
        else:
            w=load('weight',(r,k),role='immutable weight row stream');out=b.reduce(b.op('FMUL',w,b.reshape(b.bf16(x),(1,k))))
            if family=='linear_bf16':out=b.bf16(out)
        b.output('out',out)
    elif family in ('hc_pre_norm','final_norm'):
        h=load('h',(4,n));pre=load('pre',(4,));gain=load('gamma',(n,),role='immutable norm gain')
        mix=b.bf16(b.seq([b.op('FMUL',b.at(pre,j),b.at(h,j)) for j in range(4)]));out=b.norm(mix,gain,eps)
        b.output('x',out)
        if family=='hc_pre_norm':b.output('which_x',out)
    elif family=='hc_post':
        h=load('res',(4,n));y=load('y',(n,));post=load('post',(4,));comb=load('comb',(4,4));out=[]
        for j in range(4):
            mix=b.seq([b.op('FMUL',b.at(b.at(comb,i),j),b.at(h,i)) for i in range(4)])
            out.append(b.op('FADD',b.op('FMUL',b.at(post,j),y),mix))
        b.output('h',b.bf16(b.stack(out)))
        if attrs.get('which')=='ffn':b.output('pre',load('ffn_pre',(4,)))
    elif family=='hc_mixes':
        h=load('h',(4,n));flat=b.reshape(h,(4*n,));fn=load('hc_fn',(24,4*n),role='immutable HC coefficients');scale=load('hc_scale',(3,));base=load('hc_base',(24,))
        norm=b.rsqrt(b.op('FADD',b.op('DIV',b.reduce(b.op('FMUL',flat,flat)),b.const(4*n)),b.const(eps)))
        dot=b.reduce(b.op('FMUL',fn,b.reshape(b.bf16(flat),(1,4*n))));mix=b.op('FMUL',dot,norm)
        pre=b.op('FADD',b.sigmoid(b.op('FADD',b.op('FMUL',b.slice(mix,0,0,4),b.at(scale,0)),b.slice(base,0,0,4))),b.const(heps))
        post=b.op('FMUL',b.sigmoid(b.op('FADD',b.op('FMUL',b.slice(mix,0,4,8),b.at(scale,1)),b.slice(base,0,4,8))),b.const(2.))
        comb=b.reshape(b.op('FADD',b.op('FMUL',b.slice(mix,0,8,24),b.at(scale,2)),b.slice(base,0,8,24)),(4,4))
        b.output('pre',pre);b.output('post',post);b.output('comb',b.sinkhorn(comb,heps));b.output('res',h)
    elif family=='q_norm_kv_row':
        qa=load('qa',(shape.get('qa',1280),));kv=load('kvraw',(shape.get('kv',512),));c,s=cstable(shape.get('kv',512))
        b.output('qr',b.norm(qa,load('q_gamma',b.shapes[qa],role='norm gain'),eps))
        kv=b.norm(kv,load('kv_gamma',b.shapes[kv],role='norm gain'),eps);row,_,_=b.codec(b.rope(kv,c,s),'FP8')
        b.output('win_new',row);win=load('window',(shape.get('window',128),shape.get('kv',512)),role='initial/produced versioned window')
        newwin=b.concat([b.slice(win,0,1,None),b.reshape(row,(1,shape.get('kv',512)))]);b.output('window',b.emit('PACKET_COMMIT',newwin,shape=b.shapes[newwin],provider='window_append',requires='accepted write intent+publication generation; causal visibility separate'))
    elif family=='q_rope':
        q=load('q',(width,));c,s=cstable(width);b.output('q_own',b.rope(q,c,s))
    elif family=='index_q':
        q=load('iq',(heads,width));c,s=cstable(width);q=b.rope(q,c,s);out,_,_=b.codec(q,'FP4E8');b.output('iqf',out);b.output('query_codes',b.reshape(b.codec_metadata['codes'],(heads,width//2)));b.output('query_exp',b.reshape(b.codec_metadata['scale'],(heads,width//32)))
        b.output('iw',b.bf16(b.op('FMUL',load('iwr',(heads,)),load('index_w_scale',(),role='source scale constant'))))
    elif family=='index_scores':
        q=load('iqf',(heads,width));key=load('keys',(rows,width),role='paired68B packed rows');score=index_dot(b,q,key)
        terms=b.bf16(b.op('FMUL',b.op('FMAX',score,b.const(0.)),b.reshape(load('iw',(heads,)),(heads,1))))
        b.output('is_v',b.bf16(b.reduce(b.transpose(terms,(1,0)))));b.output('is_i',b.op('IADD',b.op('IMUL',b.op('IADD',b.op('IMUL',b.op('SHR',b.iota(rows),b.const(3,'I64')),b.const(96,'I64')),b.const(attrs.get('rank',0),'I64')),b.const(8,'I64')),b.op('AND',b.iota(rows),b.const(7,'I64'))))
    elif family=='attend':
        q=load('q_own',(1,width));kv=load('rows',(rows,width),role='window followed by selected rows in source order');c,s=cstable(width)
        score=b.op('FMUL',b.dot(q,kv),load('attn_scale',(),role='source attention scale'));mx=b.reshape(b.reduce(score,mode='max'),(1,1));e=b.exp(b.op('FADD',score,b.neg(mx)))
        pv=b.dot(b.bf16(e),b.transpose(kv,(1,0)));den=b.op('FADD',b.reduce(e),b.exp(b.op('FADD',load('sink',(1,),role='per-head sink constant'),b.neg(b.reshape(mx,(1,))))))
        out=b.bf16(b.op('DIV',pv,b.reshape(den,(1,1))));out=b.reshape(b.rope(out,c,s,True),(width,));b.output('o',out);b.output('o_own',out)
    elif family=='router_act':b.output('gsc',b.op('SQRT',softplus(b,load('gsc',(n,)))))
    elif family=='route':
        scores=load('gsc',(n,));biased=b.op('FADD',scores,load('bias',(n,),role='immutable router bias'));_,ids=b.topk(biased,b.iota(n),min(6,n))
        # Source sorts selected expert IDs ascending before denominator summation.
        _,ids=b.topk(b.neg(b.op('I2F',ids)),ids,min(6,n));picked=b.take(scores,ids);den=b.op('FADD',b.reduce(picked,mode='seq'),b.const(1e-20))
        b.output('router',biased);b.output('route_ids',ids);b.output('route_w',b.op('FMUL',b.op('DIV',picked,den),b.const(1.5)))
    elif family=='swiglu':
        g=b.op('FMIN',load('g',(n,)),b.const(10.));u=b.op('FMIN',b.op('FMAX',load('u',(n,)),b.const(-10.)),b.const(10.))
        a=b.op('FMUL',b.op('DIV',g,b.op('FADD',b.exp(b.neg(g)),b.const(1.))),u)
        if attrs.get('slot',0)<6:a=b.op('FMUL',load('route_weight',()),a)
        a=b.bf16(a);old=load('ea_old',(shape.get('ea',7*n),),role='partial output previous version');start=shape.get('ea_start',attrs.get('slot',0)*n)
        merged=b.concat([b.slice(old,0,0,start),a,b.slice(old,0,start+n,None)]);b.output('ea',merged)
    elif family=='moe_sum':
        xs=load('expert_outputs',(7,n));b.output('yf',b.bf16(b.seq([b.at(xs,j) for j in range(7)],zero=True)))
    elif family in ('topk_local','argmax_local','topk_merge'):
        v=load('scores',(n,));ids=b.op('IADD',b.iota(n),b.const(attrs.get('global_start',0),'I64')) if family=='argmax_local' else load('ids',(n,),'I64');kk=1 if family=='argmax_local' or attrs.get('what')=='argmax' else min(attrs.get('k',512),n)
        vals,ii=b.topk(v,ids,kk);b.output('values',vals);b.output('ids',ii)
        if family=='topk_merge' and attrs.get('what')=='sel':_,sortids=b.topk(b.neg(b.op('I2F',ii)),ii,kk);b.output('sel',sortids)
        if family=='topk_merge' and attrs.get('what')=='argmax':b.output('token',ii)
    elif family=='cand_local':
        ids=load('ids',(n,),'I64');v=load('scores',(n,));blocks=b.op('IADD',b.op('IMUL',b.iota(rows),b.const(96,'I64')),b.const(attrs.get('rank',0),'I64'))
        padded=rows*8
        if padded<n or padded-n>=8:raise ValueError('owned key blocks geometry')
        if padded>n:v=b.concat([v,b.broadcast(b.const(-np.inf),(padded-n,))])
        vals=b.reduce(b.reshape(v,(rows,8)),mode='max')
        newest=b.op('FCMP_EQ',blocks,b.const((attrs.get('global_n',n)-1)>>3,'I64'))
        vals=b.emit('SELECT',newest,b.const(np.inf),vals,shape=(rows,))
        vals,ii=b.topk(vals,blocks,min(attrs.get('k',2048),rows));b.output('cand_v',vals);b.output('cand_i',ii);b.output('cand_blocks',blocks)
    elif family=='cand_apply':
        ids=load('ids',(n,),'I64');selected=load('selected_blocks',(rows,),'I64');sv=load('selected_values',(rows,));keep=b.broadcast(b.const(0,'U32'),(n,))
        for j in range(rows):
            match=b.op('AND',b.op('FCMP_EQ',ids,b.at(selected,j)),b.op('FCMP_GT',b.at(sv,j),b.const(-np.inf)));keep=b.op('OR',keep,match)
        b.output('candidate_keep',keep)
    elif family=='cand_mask':
        keep=load('candidate_keep',((n+7)//8,),'U32');local_block=b.op('SHR',b.iota(n),b.const(3,'I64'))
        mask=b.take(keep,local_block);b.output('is_v',b.emit('SELECT',mask,load('scores',(n,)),b.const(-np.inf),shape=(n,)))
    elif family=='compressor':
        ratio=attrs.get('ratio',2);width=shape.get('width',512);cmp=load('cmp',(width*(2 if ratio>1 else 1),))
        if ratio>1:
            slots=load('open_group',(ratio-1,2,width),role='accepted persistent positions in ascending order')
            current=b.reshape(cmp,(1,2,width));allslots=b.concat([slots,current]);kvs=b.reshape(b.slice(allslots,1,0,1),(ratio,width));scs=b.reshape(b.slice(allslots,1,1,2),(ratio,width))
            e=b.exp(b.op('FADD',scs,b.neg(b.reduce(scs,axis=0,mode='max'))));den=b.reduce(e,axis=0,mode='seq');p=b.op('DIV',e,den);pooled=b.reduce(b.op('FMUL',kvs,p),axis=0,mode='seq');latent=b.bf16(pooled)
        else:latent=cmp
        if not attrs.get('closes',True) and ratio>1:
            b.output('open_group',b.emit('PACKET_COMMIT',current,shape=b.shapes[current],provider='open_group_append'));return b.finish()
        latent=b.norm(latent,load('gamma',(width,),role='compressor norm gain'),eps)
        wk=load('index_weight',(shape.get('index_width',128),width),role='index WK weight');ik=b.bf16(b.reduce(b.op('FMUL',wk,b.reshape(b.bf16(latent),(1,width)))))
        ik=b.norm(ik,load('index_gamma',b.shapes[ik],role='index norm gain'),eps);c,s=cstable(width);ki,ks=cstable(shape.get('index_width',128),'index_rope')
        ck,_,_=b.codec(b.rope(latent,c,s),'FP4E4',16);ik,_,_=b.codec(b.rope(ik,ki,ks),'FP4E8')
        b.output('new_ckv',b.emit('PACKET_COMMIT',ck,shape=b.shapes[ck],provider='paired_CKV_append',group=attrs.get('group'),requires='both accepted row intents+generation'))
        b.output('new_ik',b.emit('PACKET_COMMIT',ik,shape=b.shapes[ik],provider='paired_index_append',group=attrs.get('group'),requires='both accepted row intents+generation'))
    elif family=='engram_fetch':
        ns=shape.get('ngram',4);nh=shape.get('heads',8);raw=load('raw_recent_tokens',(ns,),'I64','history suffix newest first with explicit raw pad ID');token_map=load('token_map',(shape.get('vocab',129280),),'I64','immutable normalized tokenizer ID map');history=b.take(token_map,raw);mult=load('multipliers',(ns,),'I64','source odd multipliers');primes=load('primes',(ns-1,nh),'I64','source prime table');offs=load('offsets',((ns-1)*nh,),'I64','source offsets')
        rolling=None;out=[]
        for j in range(ns):
            term=b.op('IMUL',b.at(history,j),b.at(mult,j));rolling=term if rolling is None else b.op('XOR',rolling,term)
            if j:out.append(b.op('IMOD',rolling,b.at(primes,j-1)))
        ids=b.op('IADD',b.reshape(b.stack(out),((ns-1)*nh,)),offs);b.output('row_ids',ids)
        # Selected row payload decoding is explicit table lookup + per32 scale.
        observed_ids=load('selected_row_ids',((ns-1)*nh,),'I64','accepted row descriptor IDs');b.emit('ASSERT',b.op('FCMP_EQ',ids,observed_ids),shape=((ns-1)*nh,),reason='Engram row response identity')
        codes=load('selected_codes',((ns-1)*nh,shape.get('width',256)),'I64','accepted selected Engram row codes keyed by row_ids')
        ex=load('selected_exp',((ns-1)*nh,shape.get('width',256)//32),'I64','paired Engram UE8M0 sectors')
        table=load('E4M3_decode',(256,),role='format constants incl poison');decoded=b.take(table,codes);decoded=b.reshape(decoded,((ns-1)*nh,shape.get('width',256)//32,32))
        b.output('eg_rows',b.reshape(b.bf16(b.op('LDEXP',decoded,b.reshape(ex,((ns-1)*nh,shape.get('width',256)//32,1)))),((ns-1)*nh*shape.get('width',256),)))
    elif family=='engram_mix':
        h=load('h',(4,n));key=load('key',(4,n));value=load('value',(n,));w=b.op('FMUL',load('q_weight',(4,n),role='Engram q_weight BF1620480'),load('k_weight',(4,n),role='Engram k_weight BF1620480'));out=[]
        for j in range(4):
            hj=b.at(h,j);kj=b.at(key,j);r=[]
            for x in [hj,kj]:r.append(b.rsqrt(b.op('FADD',b.op('DIV',b.reduce(b.op('FMUL',x,x)),b.const(n)),b.const(eps))))
            dot=b.op('FMUL',b.op('FMUL',b.reduce(b.op('FMUL',b.op('FMUL',hj,b.at(w,j)),kj)),b.op('FMUL',r[0],r[1])),load('engram_scale',(),role='source scale constant'))
            mag=b.op('SQRT',b.op('FMAX',b.abs(dot),b.const(1e-6)));signed=b.emit('SELECT',b.op('FCMP_LT',dot,b.const(0.)),b.neg(mag),mag,shape=());gate=b.sigmoid(signed);out.append(b.op('FADD',hj,b.op('FMUL',gate,value)))
        out=b.bf16(b.stack(out));b.output('h',out);b.output('engram_h',out)
    elif family=='all_reduce':
        parts=load('parts',(8,n),role='eight rank partials in fixed group order');nodes=[b.at(parts,j) for j in range(8)]
        while len(nodes)>1:nodes=[b.op('FADD',nodes[j],nodes[j+1]) for j in range(0,len(nodes),2)]
        b.output('out',b.bf16(nodes[0]))
    elif family=='all_gather':
        parts=load('parts',(shape.get('ranks',96),n));masks=load('ownership_mask',(shape.get('ranks',96),n),'U32','nonoverlapping complete owned extents')
        # Ownership check is a provider admission condition; merge only accepted fragments.
        ownership=integer_sum(b,masks,axis=0)
        b.emit('ASSERT',b.op('FCMP_EQ',ownership,b.const(1,'U32')),shape=(n,),reason='gather exactly one owner per element')
        out=b.broadcast(b.const(0.),(n,))
        for j in range(shape.get('ranks',96)):out=b.emit('SELECT',b.at(masks,j),b.at(parts,j),out,shape=(n,))
        b.output('out',out)
    elif family=='kv_gather':
        ids=load('sel',(rows,),'I64');accepted=load('selected_row_ids',(rows,),'I64','accepted descriptors in source sorted-selection order')
        b.emit('ASSERT',b.op('FCMP_EQ',ids,accepted),shape=(rows,),reason='selected KV row descriptor identity')
        codes=load('selected_ckv_codes',(rows,width//2),'U32','288B row packed E2M1 codes from (row//8)%96 owner')
        scales=load('selected_ckv_scales',(rows,width//16),'U32','paired E4M3 block16 scale bytes')
        low=b.op('AND',codes,b.const(15,'U32'));high=b.op('SHR',codes,b.const(4,'U32'));nibbles=b.reshape(b.stack([low,high],2),(rows,width//16,16))
        values=b.take(b.const([0.,.5,1.,1.5,2.,3.,4.,6.,-0.,-.5,-1.,-1.5,-2.,-3.,-4.,-6.]),nibbles)
        positive=positive_codes(True)+[0.];table=b.const(positive+[-v for v in positive])
        b.emit('ASSERT',b.op('FCMP_LT',b.op('AND',scales,b.const(127,'U32')),b.const(127,'U32')),shape=b.shapes[scales],reason='finite selected KV E4M3 scales')
        scale=b.reshape(b.take(table,scales),(rows,width//16,1));row=b.reshape(b.bf16(b.emit('FMUL',values,scale,shape=b.shapes[values],canonical_zero=False)),(rows,width))
        b.output('selected',b.emit('PACKET_COMMIT',row,shape=b.shapes[row],provider='rank64_KV_gather',requires='paired row generation+closed delivery'))
    elif family=='expert_fetch':
        ids=load('route_ids',(min(6,n),),'I64');table=load('expert_descriptor_table',(n,3,shape.get('descriptor_words',4)),'I64','immutable w1/w3/w2 base/shape/format descriptors')
        b.output('descriptors',b.emit('PACKET_COMMIT',b.take(table,ids),shape=(min(6,n),3,shape.get('descriptor_words',4)),provider='accepted weight bulk-copy descriptors',requires='immutable IDs until all accepted intents retire'))
    else:raise ValueError('unhandled DS family '+family)
    return b.finish()

RESIDENCE='results/uarch/h3_distributed_norm_endpoint_20261002/DeepSeek.json.gz'
SOURCE='results/rtl/w19_hbm_tp96_program_oreduce.json'

def shape_for(o,values,rank):
    src=o['source']['op'];f=o['opcode'];sh={};at={k:src[k] for k in ('k','slot','which','what','group','closes','fmt') if k in src}
    counts={values[v]['name']:values[v]['elements_per_rank'][rank] for v in o['reads']+o['writes']}
    if src['kind']=='mv':
        lo,hi=src['rows'][rank];sh={'rows':hi-lo,'k':src['k']}
    elif f in ('hc_mixes','hc_pre_norm','hc_post','final_norm','engram_mix'):sh={'n':5120}
    elif f=='q_norm_kv_row':sh={'qa':1280,'kv':512,'window':128}
    elif f in ('q_rope','attend'):sh={'width':512,'rows':128+(512 if src.get('yarn') else 0)}
    elif f=='index_q':sh={'heads':32,'width':128}
    elif f=='index_scores':sh={'heads':32,'width':128,'rows':counts['is_i']}
    elif f in ('topk_local','cand_mask'):sh={'n':counts['is_i'],'rows':2048};at['k']=src.get('k',512)
    elif f=='cand_local':sh={'n':counts['is_i'],'rows':counts['cand_blocks']};at['global_n']=src['n'];at['k']=2048
    elif f=='cand_apply':sh={'n':counts['cand_blocks'],'rows':2048}
    elif f=='router_act':sh={'n':384*(rank+1)//96-384*rank//96}
    elif f=='route':sh={'n':384}
    elif f=='swiglu':
        lo=2304*rank//96;hi=2304*(rank+1)//96;sh={'n':hi-lo,'ea':7*2304,'ea_start':src['slot']*2304+lo}
    elif f=='moe_sum':sh={'n':5120*(rank+1)//96-5120*rank//96}
    elif f=='argmax_local':sh={'n':129280*(rank+1)//96-129280*rank//96}
    elif f=='compressor':
        cfg=json.loads((ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text());at['ratio']=cfg['compress_ratios'][src['layer']];sh={'width':512,'index_width':128}
    elif f=='engram_fetch':sh={'ngram':4,'heads':8,'width':256,'vocab':129280}
    elif f=='all_reduce':sh={'n':1024}
    elif f=='all_gather':
        # Separate recipe instance per buffer, exact extent in binding.
        sh={'n':max(max(values[v]['elements_per_rank']) for v in o['writes']),'ranks':96}
    elif f=='topk_merge':
        prefix=src['what'];sh={'n':sum(values[v]['elements_per_rank'][r] for v in o['reads'] if values[v]['name']==prefix+'_v' for r in range(96))};at['k']=src['k']
    elif f=='kv_gather':sh={'n':src.get('n',0) or sum(values[o['reads'][1]]['elements_per_rank'])//512,'rows':512,'width':512}
    elif f=='expert_fetch':sh={'n':384,'descriptor_words':4}
    else:raise ValueError('shape family '+f)
    if f in ('index_scores','cand_local'):at['rank']=rank
    if f=='argmax_local':at['global_start']=129280*rank//96
    return sh,at


def provider_binding(name,desc,o,values,position):
    src=o['source']['op'];L=src['layer'];f=o['opcode'];byname={values[v]['name']:v for v in o['reads']};aliases={
        'res':src.get('which','attn')+'_res','post':src.get('which','attn')+'_post','comb':src.get('which','attn')+'_comb',
        'y':'y' if src.get('which')=='attn' else 'yf', 'pre':'pre' if src.get('which')=='attn' or f=='final_norm' else 'attn_pre',
        'x':src.get('x','x') if f!='wo_a_part' else 'o_own','g':f"e{src.get('slot',0)}.g",'u':f"e{src.get('slot',0)}.u",'ea_old':'ea',
        'scores':'logits' if f=='argmax_local' else 'gsc' if f=='route' else ('cand_mv' if f=='topk_merge' and src.get('what')=='cand' else 'sel_v' if f=='topk_merge' and src.get('what')=='sel' else 'argmax_v' if f=='topk_merge' else 'is_v'),
        'ids':'cand_blocks' if f=='cand_apply' else 'argmax_i' if f=='argmax_local' or src.get('what')=='argmax' else 'cand_i' if src.get('what')=='cand' else 'sel_i' if src.get('what')=='sel' else 'is_i',
        'selected_blocks':'cand_mi','selected_values':'cand_mv','owned_blocks':'cand_blocks',
        'route_weight':'route_w','ffn_pre':'ffn_pre','q_own':'q_own','sel':'sel','cmp':'cmp',
        'key':'eg_kv','value':'eg_kv','q':'q','window':f'window.L{L}','keys':f"index_keys.L{src.get('src',L)}",
        'compressed_store':f"compressed.L{src.get('src',L)}",'rows':f'window.L{L}',
        'query_codes':'iqf','query_exp':'iqf','key_codes':f"index_keys.L{src.get('src',L)}",'key_exp':f"index_keys.L{src.get('src',L)}",'parts':src.get('buf',src.get('bufs',[''])[0]),'gsc':'gsc','expert_outputs':'e0.d'}
    operand=aliases.get(name,name)
    if operand in byname:
        return {'kind':'versioned_operand','version':byname[operand], 'residence_archive':RESIDENCE,
            'view':'source-defined rank/global slice, tensor shape '+str(desc['shape']),
            'additional_versions':o['reads'] if name in ('parts','expert_outputs','rows') else [],
            'native_address_view':{'g':'lo=2304*rank//96,hi=2304*(rank+1)//96','u':'lo=2304*rank//96,hi=2304*(rank+1)//96','gsc':'lo=384*rank//96,hi=384*(rank+1)//96' if f=='router_act' else 'full384','key':'flat[0:20480] reshape4x5120','value':'flat[20480:25600]','route_weight':'route_w[slot]','expert_outputs':'e0.d..e6.d[:,5120*rank//96:5120*(rank+1)//96]','parts':'group8 fixed rank order or explicit sparse rank fragments','rows':'oldest WINDOW128 then selected512 when yarn','scores':'source-local valid extent','x':'fullK with BF16 at explicit instruction'}.get(name,'full source value reshaped to declared LOAD shape'),
            'source_view_contract':o['source']['path']+':'+f}
    if name=='ea_old' and f=='swiglu' and src['slot']==0:return {'kind':'zero_initial_partial_destination','full_elements':16128,'new_version':o['writes'][0]}
    if name in ('weight','weight_codes','weight_scale_codes'):
        return {'kind':'immutable_weight_provider','logical_tensor':src.get('w'), 'row_intervals':src.get('rows'),
            'format':src.get('fmt'),'accepted_descriptor_identity':'layer,sorted route ID,slot,matrix,row,Kblock', 'provider_owner':'Kepler'}
    if name in ('gamma','q_gamma','kv_gamma','index_gamma','hc_fn','hc_scale','hc_base','bias','q_weight','k_weight','index_weight','sink'):
        tensor={'gamma':'norm.weight' if L==-1 else ('attn.compressor.norm.weight' if f=='compressor' else ('attn_norm.weight' if src.get('which')=='attn' else 'ffn_norm.weight')),
            'q_gamma':'attn.q_norm.weight','kv_gamma':'attn.kv_norm.weight','index_gamma':'attn.indexer.k_norm.weight',
            'hc_fn':f"hc_{src.get('which')}_fn",'hc_scale':f"hc_{src.get('which')}_scale",'hc_base':f"hc_{src.get('which')}_base",
            'bias':'ffn.gate.bias','q_weight':'engram.q_weight','k_weight':'engram.k_weight','index_weight':'attn.indexer.wk.weight','sink':'attn.attn_sink'}[name]
        return {'kind':'immutable_parameter_provider','logical_tensor':tensor if L==-1 else f'layers.{L}.'+tensor,'provider_owner':'Kepler','payload_read':False}
    return {'kind':'explicit_auxiliary_provider','name':name,'layer':L,'position':position,
        'role':desc['role'],'provider_owner':'Kepler','identity_from_versions':o['reads'],
        'unqualified_timing':True,'no_generated_payload_substitution':True}


def output_binding(name,o):
    f=o['opcode'];src=o['source']['op'];which=src.get('which','attn')
    maps={
        'hc_mixes':{which+'_pre':'pre',which+'_post':'post',which+'_comb':'comb',which+'_res':'res'},
        'hc_pre_norm':{'x':'x',which+'_x':'which_x'},'final_norm':{'x':'x'},
        'q_norm_kv_row':{'qr':'qr','win_new':'win_new',f"window.L{src['layer']}":'window'},
        'q_rope':{'q_own':'q_own'},'index_q':{'iqf':'iqf','iw':'iw'},
        'index_scores':{'is_i':'is_i','is_v':'is_v'},'cand_local':{'cand_v':'cand_v','cand_i':'cand_i','cand_blocks':'cand_blocks'},
        'cand_apply':{'candidate_keep':'candidate_keep'},'cand_mask':{'is_v':'is_v'},
        'topk_local':{'sel_v':'values','sel_i':'ids'},'attend':{'o':'o','o_own':'o_own'},
        'hc_post':{'h':'h','pre':'pre'},'router_act':{'gsc':'gsc'},
        'route':{'router':'router','route_ids':'route_ids','route_w':'route_w'},
        'swiglu':{'ea':'ea'},'moe_sum':{'yf':'yf'},'argmax_local':{'argmax_v':'values','argmax_i':'ids'},
        'engram_fetch':{'eg_rows':'eg_rows'},'engram_mix':{'h':'h','engram_h':'engram_h'},
        'kv_gather':{name:'selected'}}
    if src['kind']=='mv' or f=='all_reduce':return {'result':'out','native_store_view':'source owned row interval'}
    if f=='all_gather':
        if name.startswith('ea') and name[2:].isdigit():return {'result':'out','buffer':'ea','flat_slice':[int(name[2:])*2304,(int(name[2:])+1)*2304]}
        return {'result':'out','buffer':name,'native_store_view':'complete gathered buffer'}
    if f=='topk_merge':return {'result':'token' if name=='token' else 'sel' if name=='sel' else 'values' if name.endswith('_mv') else 'ids'}
    if f=='compressor':return {'result':'new_ik' if 'index_keys' in name or name=='new_ik' else 'new_ckv','native_store_view':'owned append group '+str(src['group']) if name.startswith(('compressed.','index_keys.')) else 'new row'}
    if f=='expert_fetch':return {'result':'descriptors'}
    if name not in maps.get(f,{}):raise ValueError('missing native output binding '+f+' '+name)
    return {'result':maps[f][name],'native_store_view':'source producer extent; every declared home receives own commit'}


def compile_all():
    b,g=H.ds();values=b.byid
    resident=json.loads(gzip.decompress((ROOT/RESIDENCE).read_bytes()));homes={}
    for i,h in enumerate(resident['homes']):homes.setdefault(h['version'],[]).append(i)
    templates={};cache={};instructions=[]
    for o in b.operations:
        instances={};rank_bindings=[]
        for rank in o['participants']:
            sh,at=shape_for(o,values,rank)
            if ('rows' in sh and sh['rows']==0 and o['opcode'] in ('linear_q','linear_bf16','mv','wo_a_part','index_scores')) or ('n' in sh and sh['n']==0):
                rank_bindings.append({'rank':rank,'empty_owned_extent':True});continue
            key=json.dumps([o['opcode'],sh,at],sort_keys=True)
            if key not in cache:
                p=recipe(o['opcode'],sh,at);p['family']=o['opcode'];p['shape_parameters']=sh;p['source_attributes']=at
                raw=json.dumps(p,sort_keys=True,allow_nan=True).encode();ident=hashlib.sha256(raw).hexdigest();cache[key]=ident;templates[ident]=p
            ident=cache[key];instances[ident]=True;buffer_programs=[]
            if o['opcode']=='all_gather':
                for read,write in zip(o['reads'],o['writes']):
                    if values[read]['name'] not in o['source']['op']['bufs']:continue
                    extent=max(values[write]['elements_per_rank']);vsh={'n':extent,'ranks':96};vkey=json.dumps(['all_gather',vsh,at],sort_keys=True)
                    if vkey not in cache:
                        vp=recipe('all_gather',vsh,at);vp['family']='all_gather';vp['shape_parameters']=vsh;vp['source_attributes']=at
                        vid=hashlib.sha256(json.dumps(vp,sort_keys=True).encode()).hexdigest();cache[vkey]=vid;templates[vid]=vp
                    vid=cache[vkey];instances[vid]=True;buffer_programs.append({'template':vid,'read_version':read,'write_version':write,'elements':extent})
            rank_bindings.append({'rank':rank,'template':ident,'buffer_programs':buffer_programs,
                'row_interval':o['source']['op'].get('rows',[None]*96)[rank] if o['source']['op']['kind']=='mv' else None,
                'SM_partition':'block256%32; complete chunk8 subtrees; exceptional scalar collector SM0',
                'loop_order':'template primitive program order, each tensor instruction finite128lane batches'})
        bindings={}
        for ident in instances:
            bindings[ident]={name:provider_binding(name,desc,o,values,g['position']) for name,desc in templates[ident]['providers'].items()}
        instructions.append({'pc':o['pc'],'family':o['opcode'],'source_op':o['source']['op'],
            'reads':[{'version':v,'home_indices':homes.get(v,[]),'external':values[v]['external_source']} for v in o['reads']],
            'writes':[{'version':v,'home_indices':homes.get(v,[]),'element_counts':values[v]['elements_per_rank'],'producer_extent':values[v]['producer_extent'],'native_result_binding':output_binding(values[v]['name'],o)} for v in o['writes']],
            'dependencies':o['dependencies'],'rank_bindings':rank_bindings,'provider_bindings':bindings,
            'source_outputs':[{ 'name':values[v]['name'],'version':v,'commit_each_home':True,'producer_extent':values[v]['producer_extent'],'native_result_binding':output_binding(values[v]['name'],o)} for v in o['writes']],
            'native_outer_loops':{'all_reduce_groups':o['source']['op'].get('groups',1),'all_gather_buffers':o['source']['op'].get('bufs',[]),'rank_owned_index_rows':o['source']['op'].get('n'),'selected_row_count':512 if o['opcode']=='kv_gather' else None},
            'rounding':'separate F32 FADD/FMUL/DIV; no FMA; chunk8 from+0/tree padded+0; seqsum starts first unless source specifies+0; BF16 only explicit bit sequence',
            'compound_output_fields':{'iqf':['query_codes','query_exp']} if o['opcode']=='index_q' else {},
            'output_commit':'write each declared version/home; aliases not free; accepted intents retain owner until provider retire',
            'service':{'native_opcode_costs':None,'requires_finite_RF_shared_transport_leases':True,'dependency_release':'all writes ACK+all consumers done; physical visibility separate'},
            'native_program_present':bool(instances),'empty_participants_are_not_opcode_callbacks':True})
    counts=Counter(o['family'] for o in instructions)
    if len(instructions)!=2213 or set(counts)!=FAMILIES:raise ValueError('full DS coverage required')
    pins=[__file__,str(ROOT/SCALAR_DEPENDENCY),str(ROOT/SOURCE),str(ROOT/RESIDENCE),str(ROOT/'tools/h3_versioned_lowering.py'),str(ROOT/'tools/deepseek_hbm_complete_memory.py'),str(ROOT/'tools/w19_hbm_tp96_isa.py'),str(ROOT/'tools/hdc_golden_v41.py'),str(ROOT/'tools/hdc_golden.py'),str(ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json')]
    return {'schema':'H3_DEEPSEEK_COMPLETE_NATIVE_V1','coverage':{'PCs':2213,'families':dict(sorted(counts.items())),'all_PC_programs_emitted':True,'golden_macro_callbacks':0},
        'instructions':instructions,'templates':templates,'residence_archive':RESIDENCE,
        'arithmetic_contract':{'HDC_V41_ARITH':'chunk8','HDC_V41_FUSE':[],'no_FMA':True},
        'native_primitive_ABI':sorted(NATIVE),'owners':{'lowering':'Peirce 01a0f95d-badc-74d3-bde3-f3eb28f089b8','DIV':'Epicurus','finite_calendar':'Dewey 01a0fc12-35e2-71f0-873e-d6aa6ab2d24e','providers':'Kepler 01a0f9c6-fde3-7111-8b3c-a4a505b9a010','unified_model':'Maxwell'},
        'provider_protocol_ABI':{'reserve_identity':['PC','version','rank','SM','provider_generation','fragment'],'identity_is_observer_not_extra_wire_serial':True,'read_request_depth_per_selected_owner':1,'write_request_depth_per_selected_owner':1,'accepted_intent_immutable':True,'retire_requires':['all fragments accepted','consumer release','matching reverse ACK'],'write_visibility':'independent causal provider event, not logical RF/WR ACK or timer','restart_requires':'selected owner zero+closed delivery fence+provenance; token cannot detect identical old ghost by itself','provider_owner':'Kepler'},
        'calendar_ABI':{'dependencies':'PC dependency IDs +SSA source dependencies +finite accepted provider obligations','RF_vectors_per_SM':512,'RF_copies':2,'shared_bytes_per_SM':65536,'service_upper_bound_without_ready_assumption':None,'cost_parameter_requirement':'positive declared per opcode, per port, per route/CDC, stalls and held ACK; missing never zero','owner':'Dewey'},
        'clock_costs':{'provisional_parameters_allowed':True,'missing_cost_is_not_zero':True,'native_ns_qualified':False,'full_token_cycles':None},
        'integer64_ABI':{'IADD_ISUB':'two32bit words+carry/borrow','IMUL':'four32bit partial products+carry; retain low64','IMOD':'unsigned/signed source-bounded division primitive; no host hash callback','resource_cost':None,'physical_endpoint_bound':False},
        'source_sha256':{str(Path(p).relative_to(ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in pins},
        'software_scope':'allPC primitive program emission/replay; numerical toy kernels, not checkpoint full-token execution',
        'scalar_dependency':{'owner':'Epicurus','source_commit':'99da9b345cb7c9048b642f93517fb63729ff873a','archive':SCALAR_DEPENDENCY,'ABI':'div_contract(F32bits,F32bits)->(F32bits,error); no reciprocal substitution'},
        'implementation_limits':['provider payloads and causal publication not exercised','workspace materialization/spill bases remain unallocated; software compiler demands explicit, not feasible hardware claim','allPC source replay is code/shape/version replay, not actual checkpoint token arithmetic execution'],
        'hardware_qualified':False,'RTL_written':False,'provider_qualified':False}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    p=compile_all();raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode()
    if a.verify:
        if gzip.decompress(a.out.read_bytes())!=raw:raise SystemExit('native whole source replay mismatch')
        print(json.dumps({'status':'PASS_ALL_2213_PC_30_FAMILY_NATIVE_SOURCE_REPLAY','templates':len(p['templates']),'payload_reads':0,'RTL_runs':0}))
    else:
        if a.out.exists():raise SystemExit('refuse overwrite evidence')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(gzip.compress(raw,mtime=0))
        census={'schema':p['schema'],'coverage':p['coverage'],'templates':len(p['templates']),'native_primitive_ABI':p['native_primitive_ABI'],'source_sha256':p['source_sha256'],'owners':p['owners'],'program_sha256':hashlib.sha256(a.out.read_bytes()).hexdigest(),'scope':p['software_scope'],'clock_costs':p['clock_costs']}
        (a.out.parent/'coverage.json').write_text(json.dumps(census,indent=2)+'\n');print(json.dumps(census['coverage']))

if __name__=='__main__':main()
