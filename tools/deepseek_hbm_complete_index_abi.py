"""Ordinary U32 bit widening for actual F32 score -> F64 storage ABI.

No FP64 arithmetic. Source np.astype(F64) quiets NaNs while preserving sign
and payload. Finite/subnormal values widen exactly, signedzero stays signed.
Both output words are explicit STOREs; physical provider/ports still unbound.
"""
import numpy as np
import deepseek_hbm_complete_index as X
ins=X.K.ins
branch=X.K.branch

def program():
    p=[ins('LOAD','x','input'),ins('AND','sign','x',0x80000000),
       ins('SHR','exp','x',23),ins('AND','exp','exp',255),ins('AND','mant','x',0x7fffff)]
    normal=[ins('IADD','wide_exp','exp',896),ins('SHL','hi','wide_exp',20),
        ins('SHR','fraction_hi','mant',3),ins('OR','hi','hi','fraction_hi'),
        ins('SHL','lo','mant',29)]
    special=[ins('MOV','hi',0x7ff00000),ins('SHR','fraction_hi','mant',3),
        ins('OR','hi','hi','fraction_hi'),ins('SHL','lo','mant',29),
        branch('BEQ','mant',0,[],[ins('OR','hi','hi',0x80000)])]
    subnormal=[ins('CLZ','lz','mant'),ins('ISUB','floor',31,'lz'),
        ins('SHL','top',1,'floor'),ins('XOR','fraction','mant','top'),
        ins('IADD','wide_exp','floor',874),ins('SHL','hi','wide_exp',20),
        branch('BGT','floor',20,
            [ins('ISUB','shift','floor',20),ins('SHR','fraction_hi','fraction','shift'),
             ins('ISUB','shift',52,'floor'),ins('SHL','lo','fraction','shift')],
            [ins('ISUB','shift',20,'floor'),ins('SHL','fraction_hi','fraction','shift'),ins('MOV','lo',0)]),
        ins('OR','hi','hi','fraction_hi')]
    zero_or_subnormal=[branch('BEQ','mant',0,[ins('MOV','hi',0),ins('MOV','lo',0)],subnormal)]
    p += [branch('BEQ','exp',255,special,[branch('BEQ','exp',0,zero_or_subnormal,normal)]),
        ins('OR','hi','hi','sign'),ins('STORE','high_word','hi'),ins('STORE','low_word','lo')]
    return p

def widen(values):
    a=np.asarray(values,np.float32);flat=a.reshape(-1);pad=(-len(flat))%32
    memory={'input':np.pad(flat,(0,pad)).reshape(-1,32).view(np.uint32)}
    m=X.SIMT(memory['input'].shape,memory).run(program())
    # Packet construction only; no native F64 arithmetic or conversion.
    lo=m.stores['low_word'].reshape(-1)[:len(flat)];hi=m.stores['high_word'].reshape(-1)[:len(flat)]
    words=np.empty((len(flat),2),dtype='<u4');words[:,0]=lo;words[:,1]=hi
    return words.reshape(a.shape+(2,)),m
