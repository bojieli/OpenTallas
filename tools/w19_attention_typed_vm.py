#!/usr/bin/env python3
"""Additive typed CPU proof backend for actual attention calendar opcodes.

Reuses norm Machine/Value primitives. This is software numeric verification,
never production arithmetic, GPU timing or RTL qualification. LOADs must be
bound to explicit fixture inputs or preceding interpreter stores/registers.
"""
import re
import numpy as np
import hdc_golden as G
import w19_norm_opcode_proof as N
import w19_gpu_attention_finish as C
from w19_gpu_simd_contract import schedule_warps


def constants(attn_scale):
    f={'@ZERO':0.,'@NEG_INF':-np.inf,'@ONE':1.,'@ATTN_SCALE':attn_scale,
       '@EXP_MIN':G.EXP_MIN,'@EXP_MAX':G.EXP_MAX,'@LOG2E':G.LOG2E,
       '@MAGIC':G.MAGIC,'@NEG_MAGIC':G.neg(G.MAGIC),'@LN2_HI':G.LN2_HI,'@LN2_LO':G.LN2_LO,
       '@F32_POS_ZERO':0.}
    f.update({f'@POLY{i}':v for i,v in enumerate(G.EXP_POLY)})
    u={'@SIGN':0x80000000,'@U23':23,'@U16':16,'@U1':1,'@U7FFF':0x7fff,'@UFFFF0000':0xffff0000}
    return {**{k:N.f32(v) for k,v in f.items()},
            **{k:N.Value('U32',np.asarray(v,np.uint32)) for k,v in u.items()}}


def gpu_max_min(a,b,maximum):
    """Golden np.maximum/minimum operand policy, NOT native GPU fmax/fmin.

    Left NaN -> left bits; otherwise right NaN -> right bits; ordered equal
    values -> RIGHT bits (including +/-0). No NaN payload/quiet-bit rewriting.
    A GPU implementation needs an explicitly priced compare/select wrapper.
    """
    with np.errstate(invalid='ignore'):
        choose=np.isnan(a)|(~np.isnan(b)&(a>b if maximum else a<b))
    return np.where(choose,a,b).astype(np.float32)


class Machine(N.Machine):
    def __init__(self,program,memory,attn_scale,active_lanes=32,dot=False):
        self.admission=schedule_warps(program,1) if dot else C.calendar(program,active_lanes)
        self.program=program;self.memory=memory;self.constants=constants(attn_scale)
        self.regs={};self.trace=[];self.stores=[]

    def run(self):
        original=self.program
        for pc,i in enumerate(original):
            code=i['op'];attrs=i['attributes'];dst=i['dst'];args=[self.read(s) for s in i['src']]
            old=self.regs.get(dst)
            if code in ['FMAX','FMIN']:
                v=N.f32(gpu_max_min(args[0].f32(),args[1].f32(),code=='FMAX'))
            elif code=='F2I':
                a=args[0].f32()
                if not np.all(np.isfinite(a)) or np.any(a!=np.trunc(a)) or np.any(a<-126) or np.any(a>127):
                    raise ValueError('EXP F2I requires bounded integralF32 [-126,127]')
                v=N.Value('U32',a.astype(np.int32).view(np.uint32))
            elif code=='SHL':
                a,b=[x.u32() for x in args]
                if np.any(b>=32):raise ValueError('invalid shift')
                v=N.Value('U32',np.asarray(a<<b,np.uint32))
            elif code in ['SHFL','SHFL_PAIR']:
                a=args[0].f32()
                if a.shape[-1]!=32:raise ValueError('shuffle needs warp32 lane axis')
                v=N.f32(np.take(a,(np.arange(32)+attrs['offset'])%32,axis=-1))
            elif code in ['LDS32','LDS_PACKED_BF16']:
                if dst not in self.memory:raise ValueError('unbound dot LOAD '+dst)
                v=self.memory[dst]
                if v.kind!=('F32' if code=='LDS32' else 'U32'):raise ValueError('dot load datatype')
            elif code=='BF16_WIDEN':
                if args[0].kind!='U32':raise ValueError('packedBF16 load needsU32')
                bits=((args[0].u32()>>(16*attrs['half']))&np.uint32(0xffff))<<16
                v=N.Value('F32',bits.view(np.float32))
            elif code in ['STORE32','STS_PARTIAL']:
                v=N.f32(args[0].f32());self.stores.append(v)
            elif code=='STORE16':
                if attrs.get('source_bits')!='31:16':raise ValueError('STORE16 bits')
                # STORE16 itself means a two-byte store. Byte enables are
                # required production pins, not proof of a port implementation.
                v=N.Value('U16',(args[0].u32()>>16).astype(np.uint16));self.stores.append(v)
            else:
                self.program=[i]
                N.Machine.run(self)
                row=self.trace.pop();v=row['value']
            pred=attrs.get('predicate')
            if pred and dst:
                if old is None:raise ValueError('predicated update needs previousdst')
                a=v.data
                match=re.fullmatch(r'lane\s*%\s*(\d+)\s*==\s*0',pred)
                if not match:raise ValueError('unsupported destination predicate')
                mask=np.arange(a.shape[-1])%int(match[1])==0
                v=N.Value(v.kind,np.where(mask,a,old.data).astype(a.dtype))
            if dst:self.regs[dst]=N.Value(v.kind,v.data)
            self.trace.append(dict(pc=pc,op=code,dst=dst,src=i['src'],kind=v.kind,
                                   shape=list(v.data.shape),sha256=N.sha(v.data.tobytes()),value=v))
        self.program=original
        return self


def dot_memory(a,b):
    """Packing only: tensor fixture operands already shaped (...,warp32,8)."""
    if a.shape!=b.shape or a.shape[-2:]!=(32,8):raise ValueError('dot lane layout')
    N.bf16_memory(b)  # assert source producer BF16, not a new rounding point
    out={f'w{k}':N.f32(a[...,k]) for k in range(8)}
    bits=b.view(np.uint32)>>16
    out.update({f'b{k}':N.Value('U32',(bits[...,2*k]|(bits[...,2*k+1]<<16)).astype(np.uint32)) for k in range(4)})
    return out


def wire_f32(store):
    return (store.data.astype(np.uint32)<<16).view(np.float32) if store.kind=='U16' else store.f32()


def collector(left,right):
    p=[C.ins('LOAD','a',shared=True,source='left'),C.ins('LOAD','b',shared=True,source='right'),
       C.ins('FADD','sum',['a','b']),C.ins('STORE32',src=['sum'],shared=True)]
    return Machine(p,{'left':N.f32(left),'right':N.f32(right)},1,1).run()
