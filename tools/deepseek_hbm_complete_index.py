"""TP96 index score arithmetic lowered to standard GPU FP32/INT32 instructions.

One warp32 holds the32 heads of one owned key; bounded outer loops <=1024
keys preserve global IDs. Input is already-produced QDQ BF16-valued data.
Packed HBM ingress/decoder, staging bank mapping and service timing remain
UNBOUND; this CPU interpreter is not DUT RTL and performs no FP64 score math.
"""
from collections import Counter
import numpy as np
import w19_index32_integer_kernel as K
import w19_gpu_compare_lowering as L
import w19_gpu_attention_finish as C
from deepseek_hbm_complete_isa import WarpBackend

ARITY={**K.ARITY,'XOR':2,'IEQ':2,'INE':2,'FCMP_GT':2,'FCMP_LT':2,'FMUL':2,'FADD':2,'F2I':1,'STORE':1,'SHFL':1}
CONST={**L.CONST,'@ZERO':0,'@U16':16,'@U1':1,'@U7FFF':0x7fff,'@UFFFF0000':0xffff0000}


class SIMT:
    def __init__(self,shape,memory,initial=None):
        if len(shape)!=2 or shape[-1]!=32:raise ValueError('warp32 layout')
        self.shape=shape;self.memory=memory;self.regs={} if initial is None else {k:self.array(v) for k,v in initial.items()};self.stores={};self.counts=Counter();self.metrics=Counter()
    def array(self,v):return np.broadcast_to(np.asarray(v,np.uint32),self.shape).copy()
    def read(self,x):
        if isinstance(x,int):return self.array(x&0xffffffff)
        if x in CONST:return self.array(CONST[x])
        if x not in self.regs:raise ValueError('unwritten register '+x)
        return self.regs[x]
    def run(self,p,active=None):
        active=np.ones(self.shape,bool) if active is None else active
        for i in p:
            mask=active.copy();code=i['op']
            stride=i.get('predicate_stride')
            if stride:mask &= np.arange(32)[None,:]%stride==0
            warps=int(np.count_nonzero(np.any(mask,axis=1)))
            if not warps:continue
            args=[self.array(self.memory[i['src'][0]])] if code=='LOAD' else [self.read(x) for x in i['src']]
            self.counts[code]+=warps
            self.metrics['legacy_interpreter_proxy_cycles_NOT_service_budget']+=warps*(9 if code in ['FADD','FMUL'] else 5 if code.startswith('FCMP') else 2 if code=='LOAD' else 3)
            self.metrics['RF_read_bits_including_immediates']+=warps*32*32*len(i['src'])
            if code.startswith('B'):
                a,b=[x.view(np.int32) for x in args];take=(a==b) if code=='BEQ' else (a<b) if code=='BLT' else (a>b)
                yes=mask&take;no=mask&~take
                self.metrics['divergent_warp_branches']+=int(np.count_nonzero(np.any(yes,axis=1)&np.any(no,axis=1)))
                self.run(i['yes'],yes);self.run(i['no'],no);continue
            if code not in ARITY or len(args)!=ARITY[code]:raise ValueError('ordinary opcode arity')
            a=args[0];b=args[1] if len(args)>1 else None
            if code in ['LOAD','MOV']:r=a
            elif code=='CLZ':r=np.fromiter((32-int(x).bit_length() for x in a.reshape(-1)),np.uint32,a.size).reshape(self.shape)
            elif code=='IADD':r=(a.astype(np.uint64)+b.astype(np.uint64)).astype(np.uint32)
            elif code=='ISUB':r=((a.astype(np.uint64)-b.astype(np.uint64))&np.uint64(0xffffffff)).astype(np.uint32)
            elif code=='IMUL':r=(a.astype(np.uint64)*b.astype(np.uint64)).astype(np.uint32)
            elif code=='AND':r=a&b
            elif code=='OR':r=a|b
            elif code=='XOR':r=a^b
            elif code in ['IEQ','INE']:r=(a==b if code=='IEQ' else a!=b).astype(np.uint32)
            elif code in ['SHL','SHR']:
                if np.any(b[mask]>=32):raise ValueError('unbounded GPU shift')
                r=a<<np.minimum(b,31) if code=='SHL' else a>>np.minimum(b,31)
            elif code.startswith('FCMP'):
                with np.errstate(invalid='ignore'):r=(a.view(np.float32)>b.view(np.float32) if code=='FCMP_GT' else a.view(np.float32)<b.view(np.float32)).astype(np.uint32)
            elif code in ['FADD','FMUL']:
                with np.errstate(over='ignore',under='ignore',invalid='ignore'):
                    f=a.view(np.float32)+b.view(np.float32) if code=='FADD' else a.view(np.float32)*b.view(np.float32)
                r=np.where(f==0,np.float32(0),f).astype(np.float32).view(np.uint32)
            elif code=='F2I':
                f=a.view(np.float32)
                if np.any(~np.isfinite(f[mask])) or np.any(f[mask]!=np.trunc(f[mask])) or np.any(np.abs(f[mask])>126):raise ValueError('bounded integral F2I')
                with np.errstate(invalid='ignore'):r=f.astype(np.int32).view(np.uint32)
            elif code=='SHFL':r=np.take(a,(np.arange(32)+i['offset'])%32,axis=-1)
            elif code=='STORE':
                self.metrics['shared_warp_issues']+=warps;self.metrics['shared_requested_bytes']+=warps*128
                old=self.stores.get(i['dst'],np.zeros(self.shape,np.uint32));self.stores[i['dst']]=np.where(mask,a,old);continue
            if code=='LOAD':
                self.metrics['shared_warp_issues']+=warps;self.metrics['shared_requested_bytes']+=warps*(4 if i.get('broadcast') else 128)
            self.metrics['RF_write_bits']+=warps*32*32
            old=self.regs.get(i['dst'],np.zeros(self.shape,np.uint32));self.regs[i['dst']]=np.where(mask,r,old).astype(np.uint32)
        return self
    def summary(self):return {'warp_opcodes':dict(self.counts),'costs':dict(self.metrics),'full_GPU_cycles':None,'branch_reconvergence_and_routes_qualified':False,
                             'legacy_interpreter_timing_adopted':False,'canonical_service_cycles':None,
                             'timing_authority':'deepseek_hbm_complete_canonical; FCMP9 and unknown integer variants UNBOUND; proxy counters forbidden in service budget'}


def decode_program():
    # Canonical power-of-two representation of already-QDQ BF16 values.
    # max code<=6 permits e=floor(log2(max))-2, clamped to-126. All original
    # E2M1 values remain exact signed twice-code integers in [-12,12].
    p=[K.ins('MOV','amax',0)]
    for j in range(32):
        p += [K.ins('LOAD','v',f'v{j}'),K.ins('AND','abs','v',0x7fffffff)]
        p += L.compare('amax','amax','abs',True,'cmp_')
    nonzero=[K.ins('SHR','exp','amax',23),K.branch('BEQ','exp',0,
              [K.ins('AND','mant','amax',0x7fffff),K.ins('CLZ','lz','mant'),K.ins('ISUB','floor',-118,'lz')],
              [K.ins('ISUB','floor','exp',127)]),K.ins('ISUB','e','floor',2),
             K.branch('BLT','e',-126,[K.ins('MOV','e',-126)],[])]
    p += [K.branch('BEQ','amax',0,[K.ins('MOV','e',-126)],nonzero),K.ins('ISUB','bias',128,'e'),K.ins('SHL','factor','bias',23)]
    for j in range(32):
        p += [K.ins('LOAD','v',f'v{j}'),K.ins('FMUL','scaled','v','factor'),K.ins('F2I','unit','scaled'),K.ins('STORE',f'unit{j}','unit')]
    return p


def decode(values):
    values=np.asarray(values,np.float32)
    if values.ndim!=2 or values.shape[1]!=32 or not np.all(np.isfinite(values)) or np.any(values.view(np.uint32)&0xffff):raise ValueError('finite alreadyBF16 QDQ blocks required')
    n=len(values);pad=(-n)%32;v=np.pad(values,((0,pad),(0,0)))
    m=SIMT((len(v)//32,32),{f'v{j}':v[:,j].reshape(-1,32).view(np.uint32) for j in range(32)}).run(decode_program())
    units=np.stack([m.stores[f'unit{j}'].view(np.int32).reshape(-1)[:n] for j in range(32)],axis=-1)
    if not np.all(np.isin(units,K.UNITS)):raise ValueError('input is not common-scale E2M1 QDQ; do not approximate')
    return units,m.regs['e'].view(np.int32).reshape(-1)[:n],m


def block(q,k,qe,ke):
    n=len(k);memory={**{f'q{j}':q[:,j][None,:].view(np.uint32) for j in range(32)},
                    **{f'k{j}':k[:,j,None].view(np.uint32) for j in range(32)}}
    p=K.program()
    for i in p:
        if i['op']=='LOAD' and i['src'][0].startswith('k'):i['broadcast']=True
    m=SIMT((n,32),memory,{'eq':qe[None,:].view(np.uint32),'ek':ke[:,None].view(np.uint32)}).run(p)
    return m.regs['bits'].view(np.float32).copy(),m


def reduce_program():
    p=[K.ins('LOAD','v','terms'),K.ins('MOV','acc',0)]
    for j in range(8):
        p += [{'op':'SHFL','dst':'t','src':['v'],'offset':j},
              {**K.ins('FADD','acc','acc','t'),'predicate_stride':8}]
    for off,stride in [(8,16),(16,32)]:
        p += [{'op':'SHFL','dst':'t','src':['acc'],'offset':off},
              {**K.ins('FADD','acc','acc','t'),'predicate_stride':stride}]
    p += C.bf16_round('acc','out')+[K.ins('STORE','final','out')]
    return p


def scores(q,keys,weights,backend=None):
    q=np.asarray(q,np.float32);keys=np.asarray(keys,np.float32);weights=np.asarray(weights,np.float32)
    if q.shape!=(32,128) or keys.ndim!=2 or keys.shape[1]!=128 or weights.shape!=(32,):raise ValueError('actual32head128dim source shape')
    if not len(keys):return np.empty(0,np.float32),[]
    if len(keys)>1024:raise ValueError('finite outerloop must slice <=1024keys; no truncation')
    backend=WarpBackend() if backend is None else backend;decq=[decode(q[:,j*32:(j+1)*32]) for j in range(4)];decisions=[d[2] for d in decq];blocks=[]
    for j in range(4):
        kd,ke,m=decode(keys[:,j*32:(j+1)*32]);decisions.append(m)
        got,m=block(decq[j][0],kd,decq[j][1],ke);decisions.append(m);blocks.append(got)
    acc=np.zeros((len(keys),32),np.float32)
    for j in range(8):acc=backend.call('FADD',acc,blocks[j] if j<4 else np.float32(0))
    score=backend.call('BF16',acc);positive=backend.call('MAX',score,np.float32(0))
    terms=backend.call('BF16',backend.call('FMUL',positive,weights[None,:]))
    m=SIMT((len(keys),32),{'terms':terms.view(np.uint32)}).run(reduce_program());decisions.append(m)
    return m.stores['final'][:,0].view(np.float32).copy(),decisions
