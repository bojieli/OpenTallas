#!/usr/bin/env python3
"""Bounded demand-scheduled tiles for the frozen complete native DS IR.

No tensor-sized intermediate is allocated. Views map scalar coordinates; arithmetic
executes the original SSA edge in order. A bounded LRU allows recomputation, which
is counted, never ideal overlap. This is software compilation/execution, not RTL.
External immutable inputs and published outputs are provider objects, not scratch.
"""
import argparse
from collections import Counter, OrderedDict
import gzip
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
import h3_deepseek_complete_native as N

ROOT=Path(__file__).resolve().parents[1]
PROGRAM='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
AW=27;SMS=32;TILE=128;CACHE=16384;HOT_CACHE=256;FRAME_BYTES=128;FRAME_CAP=4096
STACK_PER_SM=FRAME_BYTES*FRAME_CAP
MEMO_PER_SM=CACHE*32
WORKSPACE_PER_SM=STACK_PER_SM+MEMO_PER_SM
DTYPES={'F32':np.float32,'U32':np.uint32,'I64':np.int64}


def size(shape):return math.prod(shape)
def unflatten(index,shape):
    result=[]
    for dim in reversed(shape):result.append(index%dim);index//=dim
    return tuple(reversed(result))
def flatten(coords,shape):
    value=0
    for c,dim in zip(coords,shape):
        if not 0<=c<dim:raise ValueError('native coordinate range')
        value=value*dim+c
    return value

def broadcast_index(index,out_shape,in_shape):
    coords=unflatten(index,out_shape);coords=coords[len(coords)-len(in_shape):] if in_shape else ()
    return flatten(tuple(0 if d==1 else c for c,d in zip(coords,in_shape)),in_shape)


def bind_workspace(base,occupied=(),aw=AW):
    """One explicitly allocated, reused frame stack per SM, no widened AW."""
    length=SMS*WORKSPACE_PER_SM
    if not isinstance(base,int) or base<0 or base%512 or aw!=AW or base+length>1<<AW:
        raise ValueError('AW27/alignment/finite workspace aperture')
    for start,end in occupied:
        if start<0 or end<start or end>1<<AW:raise ValueError('invalid occupied provider range')
        if base<end and start<base+length:raise ValueError('workspace aliases resident provider object')
    return {'base':base,'bytes':length,'AW':AW,'SMs':SMS,'per_SM_bytes':WORKSPACE_PER_SM,
            'physical_provider_qualified':False,'allocator_binding_required':True}


def template_plan(program):
    depths={};work={};fanout=Counter()
    for ins in program['code']:
        depths[ins['dst']]=1+max((depths[x] for x in ins['src']),default=0)
        # Upper bound when SELECT evaluates all arguments; cache hits lower it.
        work[ins['dst']]=1+sum(work[x] for x in ins['src'])
        fanout.update(ins['src'])
    depth=max(depths.values(),default=0)
    if depth>FRAME_CAP:raise ValueError('finite continuation stack exceeded')
    validation_ops={'ASSERT','PACKET_COMMIT','FADD','FMUL','SQRT','DIV','LDEXP','TAKE','SCATTER','SHR','SHL','F2I'}
    validation_work=sum(size(i['shape'])*work[i['dst']] for i in program['code'] if i['op'] in validation_ops)
    address_ops={i['dst']:4*len(i['shape'])+8 for i in program['code']}
    outputs={name:{'SSA':v,'elements':size(next(i['shape'] for i in program['code'] if i['dst']==v)),
                   'dependency_evaluation_upper_bound_per_element':work[v]} for name,v in program['outputs'].items()}
    return {'continuation_depth_bound':depth,'continuation_bytes_bound':depth*FRAME_BYTES,
            'source_order_validation_evaluation_upper_bound':validation_work,'address_integer_steps_upper_bound_per_evaluation':max(address_ops.values(),default=8),'address_integer_steps_cost':'positive explicit native INT address/divmod cost; not free view or ideal provider routing',
            'output_tiles128':sum((v['elements']+127)//128 for v in outputs.values()),'outputs':outputs,
            'schedule':'named outputs in declared order; row-major tiles128; each lane original SSA dependency postorder; bounded cache; explicit counted recomputation',
            'reduction_order':'unchanged SSA FADD/IMUL/IADD edges; no regrouping, fused multiply or partial tree reorder',
            'tensor_intermediate_bytes':0,'shared_cache_bytes_per_SM':HOT_CACHE*32,'provider_memo_bytes_per_SM':MEMO_PER_SM,
            'two_operand_tile_bytes_per_SM':2*512,'output_tile_bytes_per_SM':512,
            'provider_read_credit_per_SM':1,'provider_write_credit_per_SM':1,
            'accepted_fragment_MAX_bytes':512,'stack_workspace_per_SM_bytes':STACK_PER_SM,
            'bounded_external_stack_ports':'one frame push/pop128B; key12+3dependency_keys36+3typed64args27+cursor/control16+return12=103B, pad128; exact dynamic events counted, no free stack traffic',
            'RF_control_words32_per_SM':32,'new_physical_storage':False,'native_costs_measured':False,
            'source_materialized_intermediate_bytes':program['resources']['materialized_tensor_workspace_bytes']}


class ArrayProvider:
    """Toy payload adapter for existing logical PersistentMemory, not PHY."""
    def __init__(self,program,values,owner):
        if len(owner)!=5:raise ValueError('PC/version/rank/SM/generation owner required')
        self.values=values;self.spec=program['providers'];self.owner=tuple(owner)
        self.memory=N.PersistentMemory(credits=1);self.cache_key=None;self.cache_payload=None
        self.read_bytes=0;self.output_bytes=0
        for name,spec in self.spec.items():
            if name not in values or list(np.asarray(values[name]).shape)!=spec['shape']:raise ValueError('unbound/invalid provider geometry '+name)
    def read(self,name,index):
        spec=self.spec[name];dtype=np.dtype(DTYPES[spec['dtype']]);arr=np.asarray(self.values[name],dtype=dtype).reshape(-1)
        if not 0<=index<arr.size:raise ValueError('provider flat range')
        byte=index*dtype.itemsize;off=(byte//512)*512;key=('tile_input',*self.owner,name,off)
        if key!=self.cache_key:
            # Initial fixture contents of this fragment only; no tensor preload.
            if key not in self.memory.values:self.memory.preload(key,arr[off//dtype.itemsize:(off+512)//dtype.itemsize].tobytes())
            self.cache_payload=self.memory.transact(key);self.cache_key=key;self.read_bytes+=len(self.cache_payload)
        return np.frombuffer(self.cache_payload,dtype=dtype,count=1,offset=byte-off)[0]
    def publish(self,name,off,payload):
        if len(payload)>512:raise ValueError('fragment length')
        self.memory.transact(('tile_output',*self.owner,name,off),write=True,payload=payload);self.output_bytes+=len(payload)
    def fence(self):self.memory.fence()


class TileExecutor:
    def __init__(self,program,provider,work_limit=2000000):
        self.program=program;self.provider=provider;self.code={i['dst']:i for i in program['code']}
        self.plan=template_plan(program);self.cache=OrderedDict();self.hot=OrderedDict();self.slots={};self.free_slots=list(range(CACHE));self.counts=Counter();self.work_limit=work_limit;self.total=0;self.memo_reads=0;self.memo_writes=0;self.frame_pushes=0;self.frame_pops=0
        self.max_frames=0;self.fault=False;self.errors=[];self.assertions=set();self.commits=set()
    def _deps(self,ins,index):
        op=ins['op'];src=ins['src'];shape=ins['shape'];attrs=ins['attrs'];coord=unflatten(index,shape)
        def ref(v,k):return (v,k)
        if op in ('LOAD','CONST','IOTA'):return []
        if op in ('RESHAPE','PACKET_COMMIT','ASSERT'):return [ref(src[0],index)]
        if op=='BROADCAST':return [ref(src[0],broadcast_index(index,shape,self.code[src[0]]['shape']))]
        if op=='SLICE':
            old=self.code[src[0]]['shape'];axis=attrs['axis'];start,stop,step=slice(attrs['start'],attrs['stop'],attrs['step']).indices(old[axis]);c=list(coord);c[axis]=start+c[axis]*step
            return [ref(src[0],flatten(c,old))]
        if op=='TRANSPOSE':
            old=self.code[src[0]]['shape'];c=[0]*len(old)
            for axis,original in enumerate(attrs['axes']):c[original]=coord[axis]
            return [ref(src[0],flatten(c,old))]
        if op=='CONCAT':
            axis=attrs['axis'];c=list(coord);pos=c[axis]
            for v in src:
                old=self.code[v]['shape']
                if pos<old[axis]:c[axis]=pos;return [ref(v,flatten(c,old))]
                pos-=old[axis]
            raise ValueError('concat range')
        if op=='TAKE':
            old=self.code[src[0]]['shape'];ids=self.code[src[1]]['shape'];axis=attrs['axis']
            j=flatten(coord[axis:axis+len(ids)],ids);key=ref(src[1],j)
            # Address read precedes dependent data read; explicit continuation.
            if key not in self.cache:return [key]
            selected=int(self.cache[key]);c=coord[:axis]+(selected,)+coord[axis+len(ids):]
            return [key,ref(src[0],flatten(c,old))]
        if op=='SCATTER':
            key=ref(src[1],0)
            if key not in self.cache:return [key]
            idx=int(self.cache[key]);axis=attrs['axis'];old=self.code[src[0]]['shape']
            if not 0<=idx<old[axis]:raise ValueError('scatter range')
            if coord[axis]==idx:
                rest=coord[:axis]+coord[axis+1:];return [key,ref(src[2],flatten(rest,self.code[src[2]]['shape']))]
            return [key,ref(src[0],index)]
        return [ref(v,broadcast_index(index,shape,self.code[v]['shape'])) for v in src]
    def _primitive(self,ins,index,args):
        op=ins['op'];at=ins['attrs']
        if op=='LOAD':return self.provider.read(at['name'],index)
        if op=='CONST':return np.asarray(at['bits'],np.uint32).view(np.float32).reshape(-1)[index] if at['dtype']=='F32' else np.asarray(at['value'],dtype=DTYPES[at['dtype']]).reshape(-1)[index]
        if op=='IOTA':return np.int64(index)
        if op in ('RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST'):return args[0]
        if op in ('TAKE','SCATTER'):return args[-1]
        if op=='ASSERT':
            if not args[0]:raise ValueError('native assertion '+at.get('reason',''))
            self.assertions.add(ins['dst']);return args[0]
        if op=='PACKET_COMMIT':
            if self.fault:raise ValueError('fault prevents successful publication')
            self.commits.add(ins['dst']);return args[0]
        a=[np.asarray(x) for x in args]
        with np.errstate(all='ignore'):
            if op in ('FADD','FMUL','SQRT','DIV','LDEXP'):
                if op=='DIV':
                    v,error=N.primitive_div(a[0],a[1])
                    if error:self.fault=True;self.errors.append({'SSA':ins['dst'],'index':index,'error':int(error)})
                elif op=='FADD':v=np.float32(a[0]+a[1])
                elif op=='FMUL':v=np.float32(a[0]*a[1])
                elif op=='SQRT':v=np.float32(np.sqrt(a[0]))
                else:
                    exponent=a[1].astype(np.uint32).view(np.int32) if a[1].dtype==np.uint32 else a[1].astype(np.int32)
                    v=np.float32(np.ldexp(np.float32(a[0]),exponent))
                v=np.float32(v);self.fault|=not np.isfinite(v)
                return np.float32(0) if v==0 and at.get('canonical_zero',True) else v
            if op in ('FMAX','FMIN'):return np.maximum(*a)[()] if op=='FMAX' else np.minimum(*a)[()]
            if op.startswith('FCMP'):return np.uint32(a[0]>a[1] if op=='FCMP_GT' else a[0]<a[1] if op=='FCMP_LT' else a[0]==a[1])
            if op=='SELECT':return args[1] if args[0]!=0 else args[2]
            if op=='BITCAST_U':return np.float32(args[0]).view(np.uint32)
            if op=='BITCAST_F':return np.uint32(args[0]).view(np.float32)
            if op=='I2F':return np.float32(args[0])
            if op=='F2I':return np.int64(args[0])
            wide=any(x.dtype==np.int64 for x in a);dtype=np.int64 if wide else np.uint32;x,y=[dtype(v) for v in args]
            if op in ('SHR','SHL') and not 0<=y<(64 if wide else 32):raise ValueError('shift range')
            if op=='IMOD' and y==0:raise ValueError('integer divisor zero')
            return dtype({'SHR':lambda:x>>y,'SHL':lambda:x<<y,'AND':lambda:x&y,'OR':lambda:x|y,'XOR':lambda:x^y,'IADD':lambda:x+y,'ISUB':lambda:x-y,'IMUL':lambda:x*y,'IMOD':lambda:x%y}[op]())
    def value(self,root,index):
        # Explicit continuations avoid the host recursion limit and tensor stack.
        stack=[{'key':(root,index),'deps':None,'args':[],'cursor':0}];self.frame_pushes+=1
        while stack:
            self.max_frames=max(self.max_frames,len(stack))
            if len(stack)>FRAME_CAP:raise ValueError('continuation stack cap')
            f=stack[-1];key=f['key'];ins=self.code[key[0]]
            if key in self.cache:
                v=self.cache[key]
                if key not in self.hot:
                    payload=self.provider.memory.transact(('tile_memo',*self.provider.owner,self.slots[key]));self.memo_reads+=1
                    ident,position,kind,raw=struct.unpack('<IQB8s11x',payload)
                    if ident!=int(key[0][1:]) or position!=key[1]:raise ValueError('workspace memo generation identity')
                    v=np.frombuffer(raw,dtype=(np.float32,np.uint32,np.int64)[kind],count=1)[0]
                self.hot[key]=v;self.hot.move_to_end(key)
                if len(self.hot)>HOT_CACHE:self.hot.popitem(last=False)
                self.cache.move_to_end(key);stack.pop();self.frame_pops+=1
                if stack:stack[-1]['args'].append(v);stack[-1]['cursor']+=1
                else:return v
                continue
            if f['deps'] is None:f['deps']=self._deps(ins,key[1])
            # Dynamic address dependency may require a second continuation.
            if ins['op'] in ('TAKE','SCATTER') and f['cursor']==len(f['deps']) and len(f['deps'])==1:
                f['deps']=self._deps(ins,key[1])
            if f['cursor']<len(f['deps']):
                stack.append({'key':f['deps'][f['cursor']],'deps':None,'args':[],'cursor':0});self.frame_pushes+=1;continue
            v=self._primitive(ins,key[1],f['args']);self.counts[ins['op']]+=1
            self.total+=1
            if self.total>self.work_limit:raise RuntimeError('finite native work budget exhausted')
            if len(self.cache)==CACHE:
                evicted,_=self.cache.popitem(last=False);self.free_slots.append(self.slots.pop(evicted));self.hot.pop(evicted,None)
            slot=self.free_slots.pop();self.slots[key]=slot
            dtype=np.asarray(v).dtype;kind=0 if dtype==np.float32 else 1 if dtype==np.uint32 else 2
            raw=np.asarray(v,dtype=(np.float32,np.uint32,np.int64)[kind]).tobytes().ljust(8,b'\0')
            payload=struct.pack('<IQB8s11x',int(key[0][1:]),key[1],kind,raw)
            self.provider.memory.transact(('tile_memo',*self.provider.owner,slot),write=True,payload=payload);self.memo_writes+=1
            self.cache[key]=v;self.hot[key]=v
            if len(self.hot)>HOT_CACHE:self.hot.popitem(last=False)
        raise AssertionError('missing result')
    def run(self):
        self.provider.fence()
        # Source-order fault/address validation, including dead SSA, precedes logical
        # publication. Recomputations retain SSA order and count real port/work demand.
        for ins in self.program['code']:
            if ins['op'] in ('ASSERT','PACKET_COMMIT','FADD','FMUL','SQRT','DIV','LDEXP','TAKE','SCATTER','SHR','SHL','F2I'):
                for j in range(size(ins['shape'])):self.value(ins['dst'],j)
        result={}
        for name,root in self.program['outputs'].items():
            shape=self.code[root]['shape'];n=size(shape);collected=[]
            for off in range(0,n,TILE):
                vals=[self.value(root,j) for j in range(off,min(n,off+TILE))];tile=np.asarray(vals)
                if not self.fault:
                    # I64 has two32word fragments; never exceed LENMAX16.
                    raw=tile.tobytes()
                    for b in range(0,len(raw),512):self.provider.publish(name,off*tile.dtype.itemsize+b,raw[b:b+512])
                collected.extend(vals)
            # Collection is a test observation only, external output residence.
            result[name]=np.asarray(collected).reshape(shape)
        self.provider.fence()
        return ({} if self.fault else result),{'status':'FAULT_NO_OUTPUT_PUBLICATION' if self.fault else 'PASS_BOUNDED_NATIVE_TILES',
            'opcode_evaluations':dict(self.counts),'total_evaluations':sum(self.counts.values()),'max_continuation_frames':self.max_frames,
            'max_cache_entries':len(self.cache),'memo_read_commands':self.memo_reads,'memo_write_commands':self.memo_writes,'memo_workspace_bytes_per_SM':MEMO_PER_SM,'frame_push_commands':self.frame_pushes,'frame_pop_commands':self.frame_pops,'frame_command_bytes':FRAME_BYTES,'tile_elements':TILE,'tensor_scratch_bytes':0,'provider':self.provider.memory.summary(),
            'read_fragment_bytes':self.provider.read_bytes,'output_fragment_bytes':self.provider.output_bytes,
            'error_events':self.errors,'physical_provider_qualified':False,'timing_cycles':None}


def compile_schedule(program):
    plans={key:template_plan(t) for key,t in program['templates'].items()}
    return {'schema':'H3_DS_BOUNDED_NATIVE_TILES_V1','coverage':program['coverage'],'source_program':PROGRAM,
            'source_program_sha256':hashlib.sha256((ROOT/PROGRAM).read_bytes()).hexdigest(),
            'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'templates':plans,
            'PC_rank_SM_bindings':[{'pc':o['pc'],'family':o['family'],'rank_bindings':o['rank_bindings'],'reads':o['reads'],'writes':o['writes'],'dependencies':o['dependencies'],'provider_bindings':o['provider_bindings']} for o in program['instructions']],
            'workspace':{'AW':AW,'per_SM_frame_bytes':STACK_PER_SM,'SMs_per_rank':SMS,'rank_bytes':SMS*WORKSPACE_PER_SM,'per_SM_memo_bytes':MEMO_PER_SM,'base':None,
                         'allocation_policy':'require explicit aligned disjoint range below2^27, bind_workspace rejects overlap/overflow; no enlarged provider',
                         'shared_bytes_per_SM':HOT_CACHE*32+1536,'physical_fit_qualified':False},
            'memory_ports':{'RF_R':2,'RF_W':1,'provider_MAX_fragment_bytes':512,'read_credit':1,'write_credit':1,'frame_push_pop_bytes':FRAME_BYTES},
            'cost_composition':{'latency':None,'positive_opcode_port_CDC_costs_required':True,'recomputation_upper_bound':'per output element dependency_evaluation_upper_bound_per_element; measured executor counts for toy, no ideal cache/overlap','clock_transfer_credit':False},
            'limits':['AW27 scratch range needs actual allocator and retained input/output home nonoverlap certification','external weight/row output providers retain original extents and version homes; not all provider apertures qualified','dependent gathers/scalar recomputation are conservative software schedule, not GPU throughput or timing proof','32SM/source rank assignment retained; no serializedSM0 substitution','test output collection/fixture backing bytes are observations, not tile scratch or physical storage'],
            'hardware_admitted':False,'RTL_builds':0}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('refuse overwrite evidence')
    p=json.loads(gzip.decompress((ROOT/PROGRAM).read_bytes()));s=compile_schedule(p)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(gzip.compress(json.dumps(s,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    print(json.dumps({'coverage':s['coverage'],'templates':len(s['templates']),'AW':AW,'rank_scratch_bytes':s['workspace']['rank_bytes'],'maximum_frames':max(t['continuation_depth_bound'] for t in s['templates'].values()),'physical_fit_qualified':False}))
if __name__=='__main__':main()
