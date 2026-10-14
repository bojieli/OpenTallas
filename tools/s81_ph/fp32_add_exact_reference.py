#!/usr/bin/env python3
"""Independent exact dyadic binary32 addition, not an RTL implementation mirror.

All finite inputs are integers in units 2**-149. Add exactly, then quantize once
with round-to-nearest ties-to-even. API policy: canonical +0; any nonfinite
operand => (0,1); rounded overflow => (0,2); gradual underflow otherwise.
"""
import argparse,hashlib,json,random
from pathlib import Path

def reference(a,b):
    if ((a>>23)&255)==255 or ((b>>23)&255)==255:return 0,1
    def units(x):
        e=(x>>23)&255;m=(x&0x7fffff)+(0x800000 if e else 0)
        n=m<<(max(e,1)-1)
        return -n if x>>31 else n
    total=units(a)+units(b)
    if not total:return 0,0
    sign=0x80000000 if total<0 else 0;n=abs(total)
    if n<0x800000:return sign|n,0
    exponent=n.bit_length()-1-149;shift=max(0,n.bit_length()-24)
    mantissa,remainder=divmod(n,1<<shift)
    if shift and (remainder>(1<<(shift-1)) or (remainder==(1<<(shift-1)) and mantissa&1)):mantissa+=1
    if mantissa==0x1000000:mantissa>>=1;exponent+=1
    if exponent>127:return 0,2
    return sign|((exponent+127)<<23)|(mantissa&0x7fffff),0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--n',type=int,default=100000);ap.add_argument('--source',type=Path);ap.add_argument('--tree',type=Path,required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pairs=[]
    def add(x,y,c):pairs.append((x&0xffffffff,y&0xffffffff,c))
    directed=[0,0x80000000,1,0x80000001,0x007fffff,0x807fffff,0x00800000,0x80800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc00000,0x7f800001,0xffc12345]
    for x in directed:
        for y in directed:add(x,y,'directed_classes')
    for e in range(1,254):
        x=e<<23
        for lo in [0,1,2,0x7ffffe,0x7fffff]:
            z=x|lo;add(z,z^0x80000000,'exact_cancellation');add(z,((z+1)&0x7fffffff)|0x80000000,'near_cancellation')
        if e>24:
            half=(e-24)<<23
            for low in [0,1,2,3]:add(x|low,half,'RNE_ties');add((x|low)|0x80000000,half|0x80000000,'RNE_ties')
    rng=random.Random(0x5a810014)
    for i in range(a.n):
        mode=i%8;x=rng.getrandbits(32);y=rng.getrandbits(32)
        if mode==0:y=x^0x80000000;c='random_exact_cancellation'
        elif mode==1:x=(x&0x807fffff);y=(y&0x807fffff);c='random_subnormals'
        elif mode==2:x=(x&0x807fffff)|0x00800000;y=(y&0x807fffff)|0x00800000;c='normal_subnormal_boundary'
        elif mode==3:x=(x&0x807fffff)|0x7f000000;y=(y&0x807fffff)|0x7f000000;c='overflow_boundary'
        elif mode==4:x=(x&0x807fffff)|0x7f800000;c='nonfinite_policy'
        elif mode==5:y=((x+rng.randrange(-8,9))&0x7fffffff)|((1-(x>>31))<<31);c='random_near_cancellation'
        elif mode==6:y=(y&0x807fffff)|(x&0x7f800000);c='same_exponent'
        else:c='arbitrary_bit_patterns'
        add(x,y,c)
    counts={};lines=[];valid=0
    for i,(x,y,c) in enumerate(pairs):
        z,err=reference(x,y);counts[c]=counts.get(c,0)+1;lines.append(f'1 {x:08x} {y:08x} {z:08x} {err}\n');valid+=1
        if i%53==0:lines.append('0 00000000 80000000 00000000 0\n')
    vectors=out/'vectors.txt';vectors.write_text(''.join(lines))
    source=a.source or a.tree/'rtl/gpu/ot_fp32_add_rne_deep.sv';body=source.read_text();old="wire        s5_inc = s4_val[2] && ((|s4_val[1:0]) || s4_val[3]);";assert body.count(old)==1
    mutant=out/'deep_rne_tie_away_mutant.sv';mutant.write_text(body.replace(old,"wire        s5_inc = s4_val[2]; // owned arithmetic negative: ties away, not ties even"))
    receipt={'reference':'exact Python integers in units2^-149; one final RNE quantization, no imported RTL/rootgold model','policy':{'RNE':True,'gradual_underflow':True,'signed_zero':'canonical +0','infinity_or_NaN_operand':'y=0 err=1','rounded_overflow':'y=0 err=2'},'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'vectors_sha256':hashlib.sha256(vectors.read_bytes()).hexdigest(),'valid_vectors':valid,'classes':counts,'pipeline':'SPLIT7 KS1 exactly8 existing edges, valid bubbles and6 drained short-reset phases','owned_mutation':'s5 RNE tie decision replaced by guard-only ties-away in isolated copied source; historical original untouched','mutant_sha256':hashlib.sha256(mutant.read_bytes()).hexdigest()}
    (out/'reference.json').write_text(json.dumps(receipt,indent=2)+'\n');print(f'FP32_EXACT_REFERENCE vectors={valid} expected_checked={valid+6}')

if __name__=='__main__':main()
