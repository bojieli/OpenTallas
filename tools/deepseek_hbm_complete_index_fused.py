"""Opt-in ordinary GPU finite shader with an exact exceptional continuation.

Query/key domain is classified from actual decoded bits, never a format tag.
All four block rounding points, four+0 pads, BF16 and head tree remain explicit.
Invariant query units may be prepared once; no fullphase fit/timing admission.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import FunctionType
import hashlib
import itertools
from pathlib import Path
import weakref
import numpy as np
import deepseek_hbm_complete_index as X
import deepseek_hbm_complete_index_blas as B
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_index_exceptional as E
ins=X.K.ins
branch=X.K.branch

def classified(values):
    a=np.asarray(values,np.float32).reshape(-1,32)
    m=X.SIMT(a.shape,{'input':a.view(np.uint32)}).run(C.classify_program())
    flags=m.stores['flags'][:,0].copy();collectors=[]
    while True:
        count=len(flags);pad=(-count)%32;memory={'flags':np.pad(flags,(0,pad)).reshape(-1,32)}
        collector=X.SIMT(memory['flags'].shape,memory)
        # Initialize every lane before SHFL reads padded partners. No free
        # initialized RF or shared padding is assumed by the typed program.
        collector.run([ins('MOV','value',0)])
        active=np.arange(memory['flags'].size).reshape(memory['flags'].shape)<count
        collector.run([ins('LOAD','value','flags')],active)
        program=[]
        for shift in [16,8,4,2,1]:
            program += [{'op':'SHFL','dst':'other','src':['value'],'offset':shift},ins('OR','value','value','other')]
        program += [{**ins('STORE','flags','value'),'predicate_stride':32}]
        collector.run(program);collectors.append(collector);flags=collector.stores['flags'][:,0].copy()
        if len(flags)==1:break
    return bool(int(flags[0])),[m]+collectors

def rewrite(program,mapping):
    result=[]
    for i in deepcopy(program):
        i['src']=[mapping.get(s,s) if isinstance(s,str) else s for s in i['src']]
        if 'dst' in i:i['dst']=mapping.get(i['dst'],i['dst'])
        if i['op'].startswith('B'):
            i['yes']=rewrite(i['yes'],mapping);i['no']=rewrite(i['no'],mapping)
        result.append(i)
    return result

def inline(op,dst,a,b,priority=None):
    return [ins('MOV','a',a),ins('MOV','b',b)]+B.ieee_program(op,priority)[2:-1]+[ins('MOV',dst,'r')]

def program():
    p=[ins('MOV','float_acc',0)]
    for block in range(4):
        p += [ins('LOAD','eq',f'eq{block}'),{**ins('LOAD','ek',f'ek{block}'),'broadcast':True}]
        mapping={'acc':'block_acc',**{f'q{j}':f'q{block}_{j}' for j in range(32)},
                 **{f'k{j}':f'k{block}_{j}' for j in range(32)}}
        body=rewrite(X.K.program(),mapping)
        for i in body:
            if i['op']=='LOAD' and i['src'][0].startswith('k'):i['broadcast']=True
        p+=body+inline('FADD','float_acc','float_acc','bits','left')
    for _ in range(4):p+=inline('FADD','float_acc','float_acc',0,'left')
    p+=C.bf16_bits('bf','float_acc','score_')+X.L.compare('positive','bf','@ZERO',True,'max_')
    p += [ins('LOAD','weight','weights')]+inline('FMUL','weighted','positive','weight','right')
    p+=C.bf16_bits('terms_reg','weighted','terms_')+[ins('MOV','v','terms_reg')]
    for i in X.reduce_program()[1:]:
        if i['op']=='FADD':
            body=inline('FADD',i['dst'],*i['src'],'right' if i.get('predicate_stride')==8 else 'left')
            if i.get('predicate_stride'):body=[{**item,'predicate_stride':i['predicate_stride']} for item in body]
            p+=body
        elif i['op']=='STORE':p.append({**i,'predicate_stride':32})
        else:p.append(i)
    return p

@dataclass(frozen=True)
class Prepared:
    query_hash:str
    units:tuple
    exponents:tuple
    query_classification:object
    query_decoders:tuple
    exceptional:bool
    decoded_hash:str
    epoch:int
    source_pins:tuple

# Process-local software authority, not a hardware capability or producer pin.
# Identity is checked through a weak reference, so id reuse cannot renew a lease.
_REGISTRY={}
_EPOCHS=itertools.count(1)
_SOURCE_PINS=tuple((Path(m.__file__).name,hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest())
                   for m in (X,B,C,E,X.K,X.L,C.G,C.V)) + ((Path(__file__).name,hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),)

def _content(prepared):
    return hashlib.sha256(b''.join(a.tobytes() for a in prepared.units+prepared.exponents)).hexdigest()

def release_query(prepared):
    record=_REGISTRY.get(id(prepared))
    if record is None or record[0]() is not prepared:raise ValueError('foreign or expired query lease')
    del _REGISTRY[id(prepared)]

def _validate(prepared,q):
    record=_REGISTRY.get(id(prepared))
    if record is None or record[0]() is not prepared:raise ValueError('foreign cloned or expired query lease')
    _,expected,units,exponents=record
    actual=(prepared.query_hash,prepared.decoded_hash,prepared.exceptional,prepared.epoch,prepared.source_pins)
    if actual!=expected:raise ValueError('altered factory query metadata')
    if hashlib.sha256(q.tobytes()).hexdigest()!=expected[0]:raise ValueError('wrong produced query version')
    if _content(prepared)!=expected[1]:raise ValueError('clobbered factory query content')
    return units,exponents,expected[2]

def prepare_query(q):
    q=np.asarray(q,np.float32)
    if q.shape!=(32,128):raise ValueError('actual32queryheads')
    exceptional,classification=classified(q)
    decoded=[] if exceptional else [X.decode(q[:,j*32:(j+1)*32]) for j in range(4)]
    # Bytes-backed arrays cannot be made writeable by callers. Registry keeps
    # these exact snapshots for consumption after validation.
    def immutable(a):return np.frombuffer(a.tobytes(),dtype=a.dtype).reshape(a.shape)
    units=tuple(immutable(d[0]) for d in decoded);exponents=tuple(immutable(d[1]) for d in decoded)
    prepared=Prepared(hashlib.sha256(q.tobytes()).hexdigest(),units,exponents,classification,tuple(d[2] for d in decoded),exceptional,hashlib.sha256(b''.join(a.tobytes() for a in units+exponents)).hexdigest(),next(_EPOCHS),_SOURCE_PINS)
    identity=id(prepared)
    def expire(ref):
        record=_REGISTRY.get(identity)
        if record is not None and record[0] is ref:_REGISTRY.pop(identity,None)
    _REGISTRY[identity]=(weakref.ref(prepared,expire),(prepared.query_hash,prepared.decoded_hash,prepared.exceptional,prepared.epoch,prepared.source_pins),units,exponents)
    return prepared

def decode_owned(values):
    values=np.asarray(values,np.float32);count=len(values)
    class Owned(X.SIMT):
        def run(self,p,active=None):
            owned=np.arange(self.shape[0]*32).reshape(self.shape)<count
            return super().run(p,owned if active is None else active&owned)
    # The pinned decoder has no cross-lane instructions: dead padding lanes
    # cannot affect live results. Preserve its arithmetic and output checks.
    decoder=FunctionType(X.decode.__code__,{**X.decode.__globals__,'SIMT':Owned})
    return decoder(values)


def scores(q,keys,weights,original_batch_size,opt_in=False,prepared=None,trace=False):
    if not opt_in:return B.source_sized_scores(q,keys,weights,original_batch_size)
    B.pinned_runtime()
    if original_batch_size not in [5456,5464,10920,10928,16384]:raise ValueError('unproved original macro shape')
    q=np.asarray(q,np.float32);keys=np.asarray(keys,np.float32);weights=np.asarray(weights,np.float32)
    if q.shape!=(32,128) or keys.ndim!=2 or keys.shape[1]!=128 or not 1<=len(keys)<=64 or weights.shape!=(32,):raise ValueError('bounded actual source shape')
    prepared=prepare_query(q) if prepared is None else prepared
    trusted_units,trusted_exponents,trusted_exceptional=_validate(prepared,q)
    special,key_classification=classified(keys)
    if special or trusted_exceptional:
        out,programs=B.source_sized_scores(q,keys,weights,original_batch_size)
        return out,{'path':'ordinary exceptional continuation','programs':prepared.query_classification+key_classification+programs,
            'GPU_dispatch_flag_gather_and_epoch_bound':False,'FP64_arithmetic':0}
    decoded=[decode_owned(keys[:,j*32:(j+1)*32]) for j in range(4)]
    memory={'weights':weights[None,:].view(np.uint32)}
    for block,(ku,ke,_) in enumerate(decoded):
        memory.update({f'q{block}_{j}':trusted_units[block][:,j][None,:].view(np.uint32) for j in range(32)})
        memory.update({f'k{block}_{j}':ku[:,j,None].view(np.uint32) for j in range(32)})
        memory[f'eq{block}']=trusted_exponents[block][None,:].view(np.uint32)
        memory[f'ek{block}']=ke[:,None].view(np.uint32)
    run=E.TracedSIMT((len(keys),32),memory,kernel='finite_fused_index') if trace else X.SIMT((len(keys),32),memory)
    run.run(program())
    return run.stores['final'][:,0].view(np.float32),{'path':'finite fused ordinary GPU shader',
        'programs':prepared.query_classification+key_classification+list(prepared.query_decoders)+[d[2] for d in decoded]+[run],
        'fused_kernel':run,'query_preparation_reused':True,'FP64_arithmetic':0,
        'GPU_dispatch_flag_gather_and_epoch_bound':False,'physical_RF_shared_and_timing_qualified':False}
