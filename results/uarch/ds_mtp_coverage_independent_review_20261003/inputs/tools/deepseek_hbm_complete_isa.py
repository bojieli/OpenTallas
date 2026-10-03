"""Ordinary GPU warp recipes for the complete-program scalar numeric backend.

CPU execution batches independent warp invocations, NOT extra hardware lanes.
Finite outer-loop work is counted, with no issue/RF/shared throughput bypass.
Macro gaps (packed quantisers/blockdot/selection/IEEE sqrt) remain explicit.
"""
from collections import Counter
import inspect
from types import FunctionType,SimpleNamespace
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_gpu_attention_finish as C
import w19_gpu_compare_lowering as L
from w19_gpu_compare_vm import Machine
import w19_norm_opcode_proof as N
from w19_attention_typed_vm import wire_f32


def recipe(kind):
    p=[C.ins('LOAD','a',shared=True,source='a')]
    if kind in ['FADD','FMUL','DIV','MAX','MIN']:
        p.append(C.ins('LOAD','b',shared=True,source='b'))
        p+=L.compare('r','a','b',kind=='MAX','cmp_') if kind in ['MAX','MIN'] else [C.ins(kind,'r',['a','b'])]
    elif kind=='NEG':p.append(C.ins('XOR','r',['a','@SIGN']))
    elif kind=='ABS':
        p += [C.ins('LOAD','mask',shared=True,source='abs_mask'),C.ins('AND','r',['a','mask'])]
    elif kind=='BF16':p+=C.bf16_round('a','r')
    elif kind=='EXP':
        p[0]['dst']='x';p+=L.lower(C.exp_program());p.append(C.ins('XOR','r',['e','@ZERO']))
        # @ZERO is a F32 positivezero bitview; XOR does not canonicalise data.
    elif kind=='RSQRT':
        p += [C.ins('LOAD','seed',shared=True,source='seed'),C.ins('LOAD','halfcoef',shared=True,source='halfcoef'),
              C.ins('LOAD','corrcoef',shared=True,source='corrcoef'),C.ins('SHR','shift',['a','@U1']),
              L.op('ISUB','y',['seed','shift']),C.ins('FMUL','half',['a','halfcoef'])]
        for _ in range(3):
            p += [C.ins('FMUL','yy',['y','y']),C.ins('FMUL','hyy',['half','yy']),C.ins('XOR','neg',['hyy','@SIGN']),
                  C.ins('FADD','corr',['corrcoef','neg']),C.ins('FMUL','y',['y','corr'])]
        p.append(C.ins('XOR','r',['y','@ZERO']))
    else:raise ValueError('unbound GPU primitive')
    return p+[C.ins('STORE32',src=['r'],shared=True)]


def swiglu_program(routed):
    p=[C.ins('LOAD','g',shared=True,source='g'),C.ins('LOAD','u',shared=True,source='u'),
       C.ins('LOAD','limit',shared=True,source='limit')]
    if routed:p.append(C.ins('LOAD','route',shared=True,source='route'))
    p += [C.ins('FMIN','gc',['g','limit']),C.ins('XOR','nlimit',['limit','@SIGN']),
          C.ins('FMAX','ulo',['u','nlimit']),C.ins('FMIN','uc',['ulo','limit']),C.ins('XOR','x',['gc','@SIGN'])]
    p += C.exp_program()+[C.ins('FADD','den',['e','@ONE']),C.ins('DIV','sig',['gc','den']),C.ins('FMUL','a',['sig','uc'])]
    if routed:p.append(C.ins('FMUL','scaled',['route','a']))
    p += C.bf16_round('scaled' if routed else 'a','out')+[C.ins('STORE32',src=['out'],shared=True)]
    return L.lower(p)


class WarpBackend:
    def __init__(self):self.opcodes=Counter();self.metrics=Counter();self.launches=Counter();self.max_live=0;self.cache={}
    def call(self,kind,*values):
        arrays=np.broadcast_arrays(*[np.asarray(x,np.float32) for x in values]);shape=arrays[0].shape;n=arrays[0].size
        if n==0:return np.empty(shape,np.float32)
        lanes=min(n,32);warps=(n+lanes-1)//lanes;size=warps*lanes
        memory={}
        for key,x in zip(['a','b'],arrays):
            # A finite outer loop revisits the same physical32-lane warp.
            # Inactive tail values never publish results. Padding costs counted.
            v=np.zeros(size,np.float32);v[:n]=x.reshape(-1);memory[key]=N.f32(v.reshape(warps,lanes))
        memory.update(seed=N.Value('U32',np.asarray(0x5f3759df,np.uint32)),halfcoef=N.f32(.5),corrcoef=N.f32(1.5),
                      abs_mask=N.Value('U32',np.asarray(0x7fffffff,np.uint32)))
        if kind not in self.cache:self.cache[kind]=recipe(kind)
        p=self.cache[kind];m=Machine(p,memory,1,lanes).run();cal=m.admission
        self.account(kind,p,m,warps,lanes,n,size)
        return wire_f32(m.stores[-1]).reshape(-1)[:n].reshape(shape)
    def account(self,kind,p,m,warps,lanes,n,size):
        cal=m.admission
        self.launches[kind]+=1;self.max_live=max(self.max_live,cal['peak_live_value_registers'])
        self.metrics['warp_invocations']+=warps;self.metrics['active_values']+=n;self.metrics['inactive_tail_values']+=size-n
        self.metrics['serial_issue_candidate_cycles_no_overlap']+=warps*cal['cycles']
        self.metrics['shared_issue_candidate_cycles']+=warps*cal['shared_issue_cycles']
        for i in p:
            self.opcodes[i['op']]+=warps
            self.metrics['RF_operand_bits_including_immediates']+=warps*lanes*32*len(i['src'])
            if i['dst']:self.metrics['RF_write_bits']+=warps*lanes*32
            if i['shared']:self.metrics['shared_requested_bytes']+=warps*lanes*4
    def swiglu(self,g,u,limit,route=None):
        arrays=np.broadcast_arrays(np.asarray(g,np.float32),np.asarray(u,np.float32));shape=arrays[0].shape;n=arrays[0].size
        if n==0:return np.empty(shape,np.float32)
        lanes=min(n,32);warps=(n+lanes-1)//lanes;size=warps*lanes;memory={}
        for key,a in zip(['g','u'],arrays):
            v=np.zeros(size,np.float32);v[:n]=a.reshape(-1);memory[key]=N.f32(v.reshape(warps,lanes))
        memory['limit']=N.f32(limit)
        if route is not None:memory['route']=N.f32(route)
        p=swiglu_program(route is not None);m=Machine(p,memory,1,lanes).run()
        self.account('SWIGLU_ROUTED' if route is not None else 'SWIGLU_SHARED',p,m,warps,lanes,n,size)
        return wire_f32(m.stores[-1]).reshape(-1)[:n].reshape(shape)
    def snapshot(self):return dict(self.metrics)
    def summary(self):return {'warp_opcodes':dict(self.opcodes),'metrics':dict(self.metrics),'launches':dict(self.launches),
        'peak_live_value_regs':self.max_live,'address_loop_regs':8,'RF_ports':'2R1W','warp_lanes':32,
        'shared_service_bytes_per_SM_0p9GHz_cycle':128,'shared_service_bytes_per_fast_1p2GHz_cycle':96,
        'clock_GHz_candidate':0.9,'issue_policy':'serialized per recipe/warp; no fusion or concurrent SM overlap credit',
        'full_graph_cycles':None,'INT_SFU_area_mm2':None,'physical_qualified':False}


def clone_numeric_modules(backend,rope_provider):
    # Clone functions with immutable alternate globals. Never mutate golden
    # modules, their imported function objects, or pinned source files.
    overrides={name:(lambda *a,k=kind:backend.call(k,*a)) for name,kind in
       [('add','FADD'),('mul','FMUL'),('neg','NEG'),('to_bf16','BF16'),('exp','EXP'),('rsqrt','RSQRT')]}
    ge=dict(vars(G));ge.update(overrides)
    for name,fn in vars(G).items():
        if inspect.isfunction(fn) and fn.__globals__ is G.__dict__ and name not in overrides:
            ge[name]=FunctionType(fn.__code__,ge,name,fn.__defaults__,fn.__closure__)
    gp=SimpleNamespace(**ge);ve={**vars(V),'G':gp}
    for name in list(ve):
        if name in ge and ve[name] is getattr(G,name,None):ve[name]=ge[name]
    ve['div']=lambda a,b:backend.call('DIV',a,b)
    ve['rope_cs']=rope_provider
    for name,fn in vars(V).items():
        if inspect.isfunction(fn) and fn.__globals__ is V.__dict__ and name not in ['div','rope_cs']:
            ve[name]=FunctionType(fn.__code__,ve,name,fn.__defaults__,fn.__closure__)
    return gp,SimpleNamespace(**ve),ve
