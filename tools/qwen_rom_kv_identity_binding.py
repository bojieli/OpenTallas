#!/usr/bin/env python3
"""TP4 ROM ownership -> existing r14 identity_t and reverse-credit wires.

Additive ABI contract, no RTL admission. Endpoint package bit remains outside
r14's one-bit die; all rank bits also survive in immutable producer identity.
The layer-local PAW12 producer PC uses spare producer8/caller4 bits. Production
must supply the actual issued PC; default0 is only a diagnostic API default.
"""
from qwen_rom_persistent_kv_g0 import Owner

FIELDS=(('die',1),('stack',2),('sector',34),('producer',64),('transport',32),
        ('caller',16),('client',6),('irs_slot',5),('irs_serial',32))

def identity(owner,stack,sector,transport,client,slot,pc=0):
    if not (0<=stack<4 and 0<=sector<703125000 and 0<=transport<2**32 and
            client in (1,2,3) and 0<=slot<16 and 0<=pc<4096):
        raise ValueError('provider aperture')
    producer=((pc&255)<<56)|(owner.user<<40)|(owner.rank<<38)|(owner.layer<<32)|owner.epoch
    return dict(die=owner.rank&1,stack=stack,sector=sector,producer=producer,
                transport=transport,caller=((pc>>8)<<8)|(owner.rank<<6)|owner.layer,
                client=client,irs_slot=slot,irs_serial=transport)

def pack(values):
    if set(values)!=set(name for name,bits in FIELDS): raise ValueError('identity fields')
    result=0
    for name,bits in FIELDS:
        value=values[name]
        if not 0<=value<1<<bits: raise ValueError('identity width')
        result=(result<<bits)|value
    return result

def unpack(word):
    if not 0<=word<2**192: raise ValueError('identity width')
    fields={}
    for name,bits in reversed(FIELDS): fields[name]=word&((1<<bits)-1);word>>=bits
    return fields

def validate(word,endpoint,expected,expected_pc=0):
    actual=unpack(word)
    if endpoint!=expected.rank>>1: raise ValueError('package endpoint mismatch')
    producer=actual['producer']
    owner=Owner((producer>>40)&65535,(producer>>38)&3,(producer>>32)&63,producer&0xffffffff)
    pc=((actual['caller']>>8)&15)<<8 | (producer>>56)
    if owner!=expected or actual['caller']>>12 or pc!=expected_pc or actual['die']!=owner.rank&1 or actual['caller']&255!=(owner.rank<<6)|owner.layer:
        raise ValueError('owner identity mismatch')
    if actual['transport']!=actual['irs_serial'] or actual['client'] not in (1,2,3) or actual['irs_slot']>=16 or actual['sector']>=703125000:
        raise ValueError('transaction identity mismatch')
    return actual

def reverse_credit(word,physical_tag,beat,write):
    # Literal tb_hbm_finite_stage:193'b0,we,id,tag12,beat5,1'b0.
    if not 0<=physical_tag<4096 or not 0<=beat<32 or write not in (0,1):
        raise ValueError('reverse credit aperture')
    unpack(word)
    return (write<<210)|(word<<18)|(physical_tag<<6)|(beat<<1)
