#!/usr/bin/env python3
"""Provider-backed complete Qwen graph executor.

The NumPy provider is software functional execution, NEVER RTL/DUT evidence.
No golden intermediates or per-layer inputs are accepted. The only runtime
inputs are token and position; every successor consumes actual predecessor data.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from qwen_hbm_complete_program import compile_program,coverage,ROOT
F=np.float32

def z(x):
    x=np.asarray(x,dtype=F);return np.where(x==0,F(0),x).astype(F)
def add(a,b):return z(np.asarray(a,dtype=F)+np.asarray(b,dtype=F))
def mul(a,b):return z(np.asarray(a,dtype=F)*np.asarray(b,dtype=F))
def neg(a):return np.asarray(a,dtype=F).view(np.uint32).__xor__(np.uint32(0x80000000)).view(F)
def bf16(a):
    b=np.asarray(a,dtype=F).view(np.uint32).astype(np.uint64)
    return (((b+0x7fff+((b>>16)&1))>>16)<<16).astype(np.uint32).view(F)
def tree(parts):
    while len(parts)>1:parts=[add(parts[i],parts[i+1]) for i in range(0,len(parts),2)]
    return parts[0]
def chunk8(a):
    a=np.asarray(a,dtype=F).reshape(-1);parts=[]
    for i in range(0,max(1,len(a)),8):
        value=F(0)
        for x in a[i:i+8]:value=add(value,x)
        parts.append(value)
    parts += [F(0)]*((1<<(len(parts)-1).bit_length())-len(parts))
    return tree(parts)
def rsqrt(a):
    a=np.asarray(a,dtype=F);y=(np.uint32(0x5f3759df)-(a.view(np.uint32)>>1)).view(F);half=mul(a,F(.5))
    for _ in range(3):y=mul(y,add(F(1.5),neg(mul(half,mul(y,y)))))
    return y
def reciprocal(a):
    a=np.asarray(a,dtype=F);b=a.view(np.uint32)
    saturated=((b&0x80000000)==0)&((b&0x7f800000)!=0x7f800000)&(b>0x7ef311c7)
    y=np.where(saturated,np.uint32(0),np.uint32(0x7ef311c7)-b).astype(np.uint32).view(F)
    for _ in range(3):y=mul(y,add(F(2),neg(mul(a,y))))
    return y
def exp(a):
    a=np.clip(np.asarray(a,dtype=F),F(-87),F(88));t=mul(a,F(1.4426950408889634))
    n=add(add(t,F(12582912)),F(-12582912))
    r=add(add(a,neg(mul(n,F(.693145751953125)))),neg(mul(n,F(1.428606765330187e-6))))
    coeff=[F(1/720),F(1/120),F(1/24),F(1/6),F(.5),F(1),F(1)]
    p=np.full_like(r,coeff[0])
    for c in coeff[1:]:p=add(mul(p,r),c)
    return (p.view(np.uint32).astype(np.int64)+(n.astype(np.int64)<<23)).astype(np.uint32).view(F)
def rstd(a,eps):return rsqrt(add(mul(chunk8(mul(a,a)),F(1/len(a))),F(eps)))
def matrix(codes,x,split,interleaved=False):
    codes=np.asarray(codes);x=np.asarray(x,dtype=F).reshape(-1)
    if codes.shape[0]>256:
        return np.concatenate([matrix(codes[r:r+256],x,split,interleaved) for r in range(0,codes.shape[0],256)])
    codes=codes.astype(F)
    if codes.shape[1]!=len(x):raise ValueError('matrix input extent')
    if not interleaved and len(x)%split:raise ValueError('contiguous K split must divide K')
    parts=[]
    for s in range(split):
        acc=np.zeros(codes.shape[0],dtype=F)
        indices=range(s,len(x),split) if interleaved else range(s*(len(x)//split),(s+1)*(len(x)//split))
        for k in indices:acc=add(acc,mul(codes[:,k],x[k]))
        parts.append(acc)
    return tree(parts)
FP8_TABLE=np.array([F(i/512) if i<8 else F((1+(i%8)/8)*2**((i//8)-7)) for i in range(127)],dtype=F)
def fp8_encode(a):
    a=np.asarray(a,dtype=F);magnitude=np.abs(a).astype(np.float64)
    _,ex=np.frexp(magnitude);quantum=np.ldexp(1.,np.maximum(ex-1,-6)-3)
    rounded=np.minimum(np.round(magnitude/quantum)*quantum,448).astype(F)
    code=np.searchsorted(FP8_TABLE,rounded).astype(np.uint8)
    return code|np.where((a<0)&(rounded!=0),128,0).astype(np.uint8)
def fp8_decode(a):
    a=np.asarray(a,dtype=np.uint8)
    if np.any((a&127)==127):raise ValueError('FP8 NaN backing')
    return z(FP8_TABLE[a&127]*np.where(a&128,-1,1))

class PersistentMemory:
    """Finite address-checked software backing with explicit write publication."""
    def __init__(self,program):
        self.program=program;self.bytes={};self.pending={};self.published={};self.next_tag=0;self.events=[]
        self.extents={(d['die'],e['name']):e for d in program['memory_allocation'] for e in d['extents']}
        self.leases={};self.next_lease=0;self.last_lease=None
    def _address(self,die,layer,kind,head,position,dim):
        c=self.program['config'];context=self.program['context_capacity'];hd=c['head_dim'];kv=c['num_key_value_heads']//self.program['TP']
        if not 0<=position<context or not 0<=head<kv or not 0<=dim<hd:raise ValueError('KV aperture')
        index=((head*(context//16)+position//16)*hd+dim)*16+position%16 if kind=='K' else (head*context+position)*hd+dim
        e=self.extents[die,f'L{layer}.{kind}']
        if index>=e['bytes']:raise ValueError('KV address extent')
        return die,e['base']+index
    def submit_KV(self,layer,die,position,k,v):
        key=(layer,die,position)
        if key in self.published or key in [x['key'] for x in self.pending.values()]:raise ValueError('KV overwrite without retired generation')
        if len(self.pending)>=self.program['TP']*4:raise ValueError('finite writer credits exhausted')
        payload=[]
        for kind,values in [('K',k),('V',v)]:
            codes=fp8_encode(values)
            for head in range(codes.shape[0]):
                for dim in range(codes.shape[1]):payload.append((self._address(die,layer,kind,head,position,dim),int(codes[head,dim])))
        tag=self.next_tag;self.next_tag+=1;self.pending[tag]=dict(key=key,payload=payload)
        self.events.append(dict(event='write_accepted_not_published',tag=tag,layer=layer,die=die,position=position,bytes=len(payload),cycles=None))
        return tag
    def fence(self,tag):
        if tag not in self.pending:raise ValueError('unknown or retired write tag')
        p=self.pending.pop(tag)
        for address,code in p['payload']:self.bytes[address]=code
        self.published[p['key']]=tag
        self.events.append(dict(event='software_backing_commit_and_publication',tag=tag,cycles=None))
        return dict(tag=tag,key=p['key'])
    def read_KV(self,layer,die,position,fence):
        if fence['key']!=(layer,die,position) or self.published.get(fence['key'])!=fence['tag']:raise ValueError('stale publication fence')
        if len(self.leases)>=36*self.program['TP']:raise ValueError('finite consumer leases exhausted')
        c=self.program['config'];kv=c['num_key_value_heads']//self.program['TP'];hd=c['head_dim']
        result=[]
        for kind in ('K','V'):
            data=np.empty((kv,position+1,hd),dtype=np.uint8)
            for pos in range(position+1):
                if (layer,die,pos) not in self.published:raise ValueError('unpublished persistent previous token')
                for head in range(kv):
                    for dim in range(hd):data[head,pos,dim]=self.bytes[self._address(die,layer,kind,head,pos,dim)]
            result.append(fp8_decode(data))
        self.events.append(dict(event='persistent_KV_read',layer=layer,die=die,positions=position+1,bytes=2*kv*(position+1)*hd,cycles=None))
        lease=self.next_lease;self.next_lease+=1;self.last_lease=lease
        self.leases[lease]=dict(key=(layer,die,position),done=set())
        self.events.append(dict(event='software_reader_lease_acquired',lease=lease,layer=layer,die=die,position=position,cycles=None))
        return result
    def consumer_done(self,lease,stage):
        if lease not in self.leases or stage not in ('SCORES','PV'):raise ValueError('unknown consumer lease or stage')
        state=self.leases[lease]
        if stage in state['done']:raise ValueError('duplicate consumer completion')
        if stage=='PV' and 'SCORES' not in state['done']:raise ValueError('PV before score dependency completion')
        state['done'].add(stage)
        self.events.append(dict(event='software_consumer_done_after_result',lease=lease,stage=stage,cycles=None))
        if state['done']=={'SCORES','PV'}:
            del self.leases[lease]
            self.events.append(dict(event='software_reader_lease_released',lease=lease,cycles=None))

class FixtureWeights:
    """Small deterministic parameter fixture; no expected activations/oracle."""
    def __init__(self,program):self.program=program;self.cache={}
    def matrix(self,key):
        if key not in self.cache:
            d=self.program['weight_descriptors'][key];seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
            rng=np.random.default_rng(seed)
            self.cache[key]=(rng.integers(-4,5,(d['rows'],d['K']),dtype=np.int8),np.full(d['rows'],F(.03125)))
        return self.cache[key]
    def constant(self,layer,kind):
        size=self.program['config']['head_dim'] if kind in ('q','k') else self.program['config']['hidden_size']
        return np.ones(size,dtype=F)
    def embedding(self,token):
        c=self.program['config'];return np.array([F(((token+i)%9)-4)*F(.125) for i in range(c['hidden_size'])])

class CheckpointWeights:
    """Lazy shipped checkpoint/W8 recipe; weights only, never oracle features."""
    def __init__(self,program,snapshot,*,row_batch=256,lock=None):
        self.program=program;self.snapshot=Path(snapshot);self.cache={};self.constants={};self.layer=None;self.tensor_pins={}
        if not 1<=row_batch<=256:raise ValueError('bounded checkpoint row batch')
        self.row_batch=row_batch;self.reads=[];self.file_pins={};self.file_stats={}
        lock=lock or json.loads((ROOT/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
        self.expected={x['path']:x for x in lock['expected_files']}
        self.checkpoint_revision=lock['revision']
        for name in ('config.json','model.safetensors.index.json'):
            expected=next(x for x in lock['expected_files'] if x['path']==name)
            if hashlib.sha256((self.snapshot/name).read_bytes()).hexdigest()!=expected['sha256']:raise ValueError('checkpoint metadata pin')
        self.index=json.loads((self.snapshot/'model.safetensors.index.json').read_text())['weight_map']
        if json.loads((self.snapshot/'config.json').read_text())!=program['config']:raise ValueError('checkpoint geometry drift')
    def tensor(self,key):
        return self.read_tensor(key)
    def _verified_file(self,name):
        path=self.snapshot/name;stat=path.stat();identity=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
        if name in self.file_pins:
            if self.file_stats[name]!=identity:raise ValueError('checkpoint shard changed after admission')
            return path
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(8<<20),b''):digest.update(block)
        expected=self.expected[name]
        if stat.st_size!=expected['size_bytes'] or digest.hexdigest()!=expected['sha256']:raise ValueError('checkpoint shard source pin')
        after=path.stat()
        if identity!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('checkpoint shard changed while hashing')
        self.file_pins[name]=digest.hexdigest();self.file_stats[name]=identity
        return path
    def read_tensor(self,key,start=None,stop=None):
        from safetensors import safe_open
        import torch
        filename=self.index[key];path=self._verified_file(filename)
        with safe_open(str(path),framework='pt',device='cpu') as handle:
            source=handle.get_slice(key);shape=source.get_shape()
            if start is None:
                if len(shape)>1:raise ValueError('matrix tensors require bounded row reads')
                value=handle.get_tensor(key)
            else:
                if len(shape)!=2 or not 0<=start<stop<=shape[0] or stop-start>self.row_batch:raise ValueError('bounded row aperture')
                value=source[start:stop]
        if value.dtype!=torch.bfloat16:raise ValueError('checkpoint BF16 source format')
        self._verified_file(filename)
        digest=hashlib.sha256(value.contiguous().view(torch.int16).numpy().tobytes()).hexdigest()
        read=dict(tensor=key,shard=filename,shape=shape,row_start=start,row_stop=stop,sha256=digest,bytes=value.numel()*2)
        self.reads.append(read);self.tensor_pins[key if start is None else f'{key}[{start}:{stop}]']=digest
        return value
    def provenance(self):
        return dict(checkpoint_revision=self.checkpoint_revision,verified_shards=self.file_pins,reads=self.reads,
                    max_source_rows_per_read=self.row_batch,images_written=False,downloads=False,
                    actual_hardware_memory_provider=False)
    def constant(self,layer,kind):
        key=f'model.layers.{layer}.self_attn.{kind}_norm.weight' if kind in ('q','k') else 'model.norm.weight'
        if key not in self.constants:self.constants[key]=self.tensor(key).float().numpy()
        return self.constants[key]
    def embedding(self,token):
        from qwen3_deployment_quality import quantize_w8
        key='model.embed_tokens.weight'
        w=self.read_tensor(key,token,token+1)
        q,s,_=quantize_w8(w.float());return mul(q[0].numpy().astype(F),s.float().numpy()[0,0])
    def matrix(self,key):
        import torch
        from qwen3_deployment_quality import quantize_w8
        d=self.program['weight_descriptors'][key]
        if self.layer!=d['layer']:self.cache={};self.layer=d['layer']
        if key in self.cache:return self.cache[key]
        norm=self.tensor(d['folded_norm']) if d['folded_norm'] else None
        axis='columns' if d['name'] in ('o','down') else 'rows'
        qs=[];ss=[]
        for source in d['checkpoint_sources']:
            from safetensors import safe_open
            path=self._verified_file(self.index[source])
            with safe_open(str(path),framework='pt',device='cpu') as handle:rows,k=handle.get_slice(source).get_shape()
            start,end=(d['die']*(rows//2),(d['die']+1)*(rows//2)) if axis=='rows' else (0,rows)
            for r in range(start,end,self.row_batch):
                w=self.read_tensor(source,r,min(end,r+self.row_batch)).float()
                if norm is not None:w=w*norm.float()[None,:]
                q,s,_=quantize_w8(w)
                if axis=='columns':q=q[:,d['die']*(k//2):(d['die']+1)*(k//2)]
                qs.append(q.contiguous().numpy());ss.append(s.float().numpy().reshape(-1))
        self.cache[key]=(np.concatenate(qs),np.concatenate(ss))
        return self.cache[key]

class SoftwareGPUProvider:
    kind='software_functional_unqualified'
    def __init__(self,program,weights=None,memory=None):
        self.program=program;self.weights=weights or FixtureWeights(program);self.memory=memory or PersistentMemory(program)
        self.calls=[];self.KV_leases={}
    def execute(self,op,args):
        name=op['opcode'];a=op['attributes'];c=self.program['config'];hd=c['head_dim'];tp=self.program['TP']
        self.calls.append(op['id'])
        if name=='EMBED':out=[self.weights.embedding(int(args[0]))]
        elif name=='RSTD':out=[rstd(args[0],a['epsilon'])]
        elif name=='MATRIX':
            d=self.program['weight_descriptors'][a['weight']];q,_=self.weights.matrix(a['weight']);out=[matrix(q,bf16(args[0]),d['split'])]
        elif name=='ROW_SCALE':out=[mul(args[0],self.weights.matrix(a['weight'])[1])]
        elif name=='SCALAR_MUL':out=[mul(args[0],args[1])]
        elif name=='QKV_SPLIT':
            q=c['num_attention_heads']//tp*hd;k=c['num_key_value_heads']//tp*hd
            out=[args[0][:q].reshape(-1,hd),args[0][q:q+k].reshape(-1,hd),args[0][q+k:].reshape(-1,hd)]
        elif name=='HEAD_NORM':out=[np.array([mul(mul(row,rstd(row,a['epsilon'])),self.weights.constant(a['layer'],a['kind'])) for row in args[0]])]
        elif name=='ROPE':
            inv=(1/(a['theta']**(np.arange(0,hd,2,dtype=np.float64)/hd))).astype(F)
            angle=(F(args[1])*inv).astype(F);co=np.cos(angle.astype(np.float64)).astype(F);si=np.sin(angle.astype(np.float64)).astype(F);half=hd//2
            out=[np.array([np.concatenate([add(mul(row[:half],co),mul(row[half:],neg(si))),add(mul(row[half:],co),mul(row[:half],si))]) for row in args[0]])]
        elif name=='KV_WRITE':out=[self.memory.submit_KV(a['layer'],a['die'],int(args[2]),args[0],args[1])]
        elif name=='KV_FENCE':out=[self.memory.fence(args[0])]
        elif name=='KV_READ':
            out=self.memory.read_KV(a['layer'],a['die'],int(args[1]),args[0])
            for value in out:self.KV_leases[id(value)]=self.memory.last_lease
        elif name=='SCORES':
            query=bf16(args[0]);keys=args[1]
            out=[np.array([mul(matrix(keys[head//a['head_groups']],row,a['split'],True),F(1/np.sqrt(hd))) for head,row in enumerate(query)])]
            self.memory.consumer_done(self.KV_leases.pop(id(keys)),'SCORES')
        elif name=='EXP_SUM':
            values=np.array([exp(add(row,neg(np.max(row)))) for row in args[0]])
            out=[bf16(values),np.array([chunk8(row) for row in values])]
        elif name=='PV':
            out=[np.array([matrix(args[1][head//a['head_groups']].T,row,a['split'],True) for head,row in enumerate(args[0])])]
            self.memory.consumer_done(self.KV_leases.pop(id(args[1])),'PV')
        elif name=='NORMALIZE':out=[mul(args[0],reciprocal(args[1])[:,None]).reshape(-1)]
        elif name=='ALL_REDUCE':
            result=args[0]
            for part in args[1:]:result=add(result,part)
            out=[mul(result,self.weights.matrix(a['post_scale_weight'])[1])]
        elif name=='RESIDUAL':out=[add(args[0],args[1])]
        elif name=='SILU_GATE':
            gate,up=np.split(args[0],2);out=[mul(mul(gate,reciprocal(add(exp(neg(gate)),F(1)))),up)]
        elif name=='FINAL_NORM':out=[mul(mul(args[0],rstd(args[0],a['epsilon'])),self.weights.constant(None,'final'))]
        elif name=='ARGMAX':
            index=int(np.argmax(args[0]));out=[(float(args[0][index]),index+a['global_row_offset'])]
        elif name=='ARGMAX_REDUCE':out=[min(args,key=lambda x:(-x[0],x[1]))[1]]
        else:raise ValueError('no ordinaryGPU semantic lowering '+name)
        return out

def execute(program,provider,token,position,*,observer=None,stop_after_layer=None):
    if not 0<=token<program['config']['vocab_size'] or not 0<=position<program['context_capacity']:raise ValueError('runtime input aperture')
    registers={'token':int(token),'position':int(position)};done=set();trace=[]
    for op in program['instructions']:
        if any(d not in done for d in op['dependencies']):raise ValueError('instruction dependency not retired')
        args=[registers[x] for x in op['inputs']];out=provider.execute(op,args)
        if len(out)!=len(op['outputs']):raise ValueError('provider result count')
        for name,value in zip(op['outputs'],out):
            if name in registers:raise ValueError('runtime SSA overwrite')
            registers[name]=value
        if observer is not None:observer(op,out)
        for consumed in op['inputs']:
            if program['register_last_use'].get(consumed)==op['id'] and consumed not in ('token','position'):
                del registers[consumed]
        done.add(op['id']);trace.append(dict(id=op['id'],opcode=op['opcode'],dependencies=op['dependencies'],provider_kind=provider.kind,cycles=None))
        if stop_after_layer is not None and f'L{stop_after_layer}.X' in op['outputs']:break
    complete=program['result_register'] in registers
    return dict(status='SOFTWARE_PROGRAM_COMPLETED' if complete else 'SOFTWARE_PREFIX_COMPLETED',next_token=int(registers[program['result_register']]) if complete else None,position=position,
        instructions_retired=len(done),trace=trace,memory_events=list(provider.memory.events),
        fullshape=program['config']['num_hidden_layers']==36 and program['config']['hidden_size']==4096,
        complete_program_executed=complete,actual_RTL_executed=False,full_token_RTL=False,token_cycles=None,token_rate=None)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--program',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--token',type=int,required=True);p.add_argument('--steps',type=int,default=1);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();program=json.loads(a.program.read_text());provider=SoftwareGPUProvider(program,CheckpointWeights(program,a.snapshot))
    results=[];token=a.token
    for position in range(a.steps):
        result=execute(program,provider,token,position);results.append(result);token=result['next_token']
    a.out.mkdir(parents=True,exist_ok=False)
    for i,result in enumerate(results):
        with (a.out/f'token{i}.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
