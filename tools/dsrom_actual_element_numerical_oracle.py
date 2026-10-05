#!/usr/bin/env python3
"""Independent finite dyadic arithmetic specification. No RTL/helper imports or DUT reads."""
from fractions import Fraction
from functools import lru_cache
import json

Q_CODES=(0x00,0x01,0x07,0x08,0x38,0x3b,0x40,0x77,0x7e,0x80,0xb8,0xbd,0xc0,0xf7,0xfe)
FP4_CODES=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)
BF_CODES=(0x0000,0x3f00,0x3f80,0x3f81,0xbf80,0x4000,0x4b80,0xcb80,0x3380,0xb380,0x0080)
SCALES=(-16,-2,0,3,17)

def pow2(n): return Fraction(1<<n) if n>=0 else Fraction(1,1<<-n)
def rounded_integer(x):
    q,r=divmod(x.numerator,x.denominator)
    return q+int(2*r>x.denominator or (2*r==x.denominator and q&1))
def round32(value):
    """One binary32 RNE; zeros canonical+0 as pinned arithmetic contract."""
    value=Fraction(value)
    if not value:return 0
    sign=0x80000000 if value<0 else 0;x=abs(value)
    e=x.numerator.bit_length()-x.denominator.bit_length()
    if x<pow2(e):e-=1
    if e<-126:
        sig=rounded_integer(x/pow2(-149))
        return sign|sig if sig else 0
    sig=rounded_integer(x/pow2(e-23))
    if sig==1<<24:sig>>=1;e+=1
    if e>127:raise ValueError('synthetic numerical contract excludes overflow')
    return sign|((e+127)<<23)|(sig-(1<<23))
@lru_cache(None)
def f32(bits):
    sign=-1 if bits>>31 else 1;e=(bits>>23)&255;m=bits&0x7fffff
    if e==255:raise ValueError('nonfinite input outside finite oracle contract')
    return sign*(Fraction(m)*pow2(-149) if not e else Fraction((1<<23)|m)*pow2(e-150))
def add(a,b):return round32(f32(a)+f32(b))
def mul(a,b):return round32(f32(a)*f32(b))
@lru_cache(None)
def e4m3(code):
    sign=-1 if code&128 else 1;e=(code>>3)&15;m=code&7
    if code&127==127:raise ValueError('E4M3 NaN')
    return sign*(Fraction(m)*pow2(-9) if not e else Fraction(8+m)*pow2(e-10))
@lru_cache(None)
def e2m1(code):
    values=(Fraction(0),Fraction(1,2),Fraction(1),Fraction(3,2),Fraction(2),Fraction(3),Fraction(4),Fraction(6))
    return (-1 if code&8 else 1)*values[code&7]
def sequential(terms):
    total=0
    for term in terms:total=add(total,term)
    return total
def tree(nodes):
    nodes=list(nodes) or [0]
    nodes += [0]*((1<<(len(nodes)-1).bit_length())-len(nodes))
    while len(nodes)>1:nodes=[add(nodes[i],nodes[i+1]) for i in range(0,len(nodes),2)]
    return nodes[0]
def chunk8(terms):return tree([sequential(terms[i:i+8]) for i in range(0,len(terms),8)])
def xcode(pos,unit,block,lane,half):return Q_CODES[(lane*3+pos*7+unit*5+block*11+half*2)%len(Q_CODES)]
def xexp(pos,unit,block,half):return (-9,-1,0,2,8)[(pos+unit+block+half)%5]
def xbcode(pos,unit,block,lane):return BF_CODES[(lane*3+pos*7+unit*5+block*2)%len(BF_CODES)]
def profile(phase):
    family='bf16' if phase in (3,8,11) else 'fp4' if phase in (2,7,10) else 'fp8'
    return dict(phase=phase,family=family,active_segments=8 if phase<6 else 4,units_per_segment=1 if phase<6 else 2,nseg=2 if phase>=9 else 1,positions=6 if phase>=5 else 1,word_base=phase*256,empty=phase==0,idle_second=phase==4)
def cfg_word(p,k):
    seg=k if k<8 else k-17
    if k<8:
        row=(0x100+seg//p['nseg']) if seg<p['active_segments'] else 0x8000+seg
        return row|((seg%p['nseg'])<<16)|(p['nseg']<<21)|(int(p['family']=='fp4')<<26)|(1<<27)|(1<<28)|(int(p['family']=='bf16')<<42)
    if k<16:
        s=k-8
        return int(not p['empty'] and s<p['active_segments'])|((s*p['units_per_segment'])<<1)|(p['units_per_segment']<<9)|(s<<16)|(s<<19)|(int(p['family']=='bf16')<<22)
    if k==16:return p['word_base']<<6 # pair loader ORs positions-1 at bits5:3
    row=0x200+seg//p['nseg']
    return (0x8000+seg) if p['idle_second'] or seg>=p['active_segments'] else row

def word_address(p,seg,local_unit,block,half=0):
    halves=2 if p['family']=='fp8' else 1
    return p['word_base']+block*p['active_segments']*p['units_per_segment']*halves+seg*p['units_per_segment']*halves+local_unit*halves+half

def build_inputs():
    """Input-only immutable image. No expected numbers are present here."""
    result=dict(schema='synthetic.dsrom274.input.v1',profiles=[profile(i) for i in range(12)],cfg_words={},ROM_words={'0':{},'1':{}},Q_CODES=Q_CODES,FP4_CODES=FP4_CODES,BF_CODES=BF_CODES,SCALES=SCALES)
    for p in result['profiles']:
        for k in range(25):result['cfg_words'][str(p['phase']*25+k)]=hex(cfg_word(p,k))
        if p['empty']:continue
        for seg in range(p['active_segments']):
            for u in range(p['units_per_segment']):
                for b in range(8):
                    for half in range(2 if p['family']=='fp8' else 1):
                        addr=word_address(p,seg,u,b,half)
                        for macro in range(2):
                            seed=p['phase']*13+macro*17+seg*7+u*11+b*3+half*5
                            if p['family']=='bf16':word=sum(BF_CODES[(seed+l*3)%len(BF_CODES)]<<(16*l) for l in range(16))
                            elif p['family']=='fp8':
                                word=sum(Q_CODES[(seed+l*7)%len(Q_CODES)]<<(8*l) for l in range(32))
                                word|=(127+SCALES[(seed+b)%len(SCALES)])<<256
                            else:
                                word=sum(FP4_CODES[(seed+l*5)%16]<<(4*l) for l in range(32))
                                word|=(127+SCALES[(seed+b)%len(SCALES)])<<128
                                word|=sum(FP4_CODES[(seed+l*7+3)%16]<<(136+4*l) for l in range(32))
                                word|=(127+SCALES[(seed+b+2)%len(SCALES)])<<264
                            result['ROM_words'][str(macro)][str(addr)]=hex(word)
    return result

def block_term(word,p,pos,unit,b,half,mutant=None):
    fp4=p['family']=='fp4';offset=136*half if fp4 else 0;stride=4 if fp4 else 8
    we=((word>>(128+136*half if fp4 else 256))&255)-127
    if mutant=='exponent_offbyone':we+=1
    products=[e4m3(xcode(pos,unit,b,l,half))*(e2m1((word>>(offset+stride*l))&15) if fp4 else e4m3((word>>(8*l))&255)) for l in range(32)]
    dot=round32(sum(products,Fraction(0)))
    if mutant=='round_each_product':dot=sequential([round32(x) for x in products])
    return round32(f32(dot)*pow2(xexp(pos,unit,b,half)+we))

def partial(image,phase,macro,seg,pos,mutant=None):
    p=image['profiles'][phase];nodes=[]
    for u in range(p['units_per_segment']):
        unit=seg*p['units_per_segment']+u
        if p['family']=='bf16':
            lanes=[]
            for lane in range(16):
                terms=[]
                for b in range(8):
                    word=int(image['ROM_words'][str(macro)][str(word_address(p,seg,u,b))],16)
                    wl=15-lane if mutant=='BF_lane_reversed' else lane
                    terms.append(mul(((word>>(16*wl))&65535)<<16,xbcode(pos,unit,b,lane)<<16))
                lanes.append(sequential(terms[::-1] if mutant=='chunk_order_reversed' else terms))
            nodes.append(tree(lanes[0::2]+lanes[1::2] if mutant=='tree_lane_order_interleaved' else lanes))
        else:
            chunks=[]
            for half in (0,1):
                terms=[]
                for b in range(8):
                    addr=word_address(p,seg,u,b,half if p['family']=='fp8' else 0)
                    word=int(image['ROM_words'][str(macro)][str(addr)],16)
                    terms.append(block_term(word,p,pos,unit,b,half,mutant))
                chunks.append(sequential(terms[::-1] if mutant=='chunk_order_reversed' else terms))
            nodes.extend([add(*chunks)] if p['family']=='fp4' else chunks)
    return tree(nodes[0::2]+nodes[1::2] if mutant=='segment_order_interleaved' else nodes)

def expected(image):
    result=[]
    for p in image['profiles']:
        if p['empty']:continue
        for macro in range(2):
            if macro==1 and p['idle_second']:continue
            for seg in range(p['active_segments']):
                for pos in range(p['positions']):
                    result.append(dict(phase=p['phase'],macro=macro,segment_slot=seg,position=pos,row=(0x100 if not macro else 0x200)+seg//p['nseg'],lo=seg%p['nseg'],nseg=p['nseg'],error=0,value_hex=f'{partial(image,p["phase"],macro,seg,pos):08x}'))
    return result

def parent_rows(image,rows):
    groups={}
    for row in rows:groups.setdefault((row['phase'],row['macro'],row['row'],row['position']),[]).append(row)
    parents=[]
    for key,parts in sorted(groups.items()):
        ordered=sorted(parts,key=lambda x:x['lo']);value=tree([int(x['value_hex'],16) for x in ordered])
        parents.append(dict(phase=key[0],macro=key[1],row=key[2],position=key[3],lo=0,k=0 if len(parts)==1 else 1,nseg=parts[0]['nseg'],value_hex=f'{value:08x}',bf16_hex=f'{((value+0x7fff+((value>>16)&1))&0xffff0000):08x}',source_partial_values=[x['value_hex'] for x in ordered]))
    return parents
