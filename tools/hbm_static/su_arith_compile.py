#!/usr/bin/env python3
"""Independent NumPy FP32 golden and compiler raw-control image for real N512.

Baseline fixed-issue calendar; no controller, DPI, or CPU arithmetic in DUT.
Canonical operation lowering is intentionally separate from this mechanism gate.
"""
import json
from pathlib import Path
import sys
import numpy as np
from su_arith_generate import FIELDS

OPS=[('BYP',{}),('AB',dict(cp_m1=1,cm_m1=1)),('AA',dict(cp_m1=2,cm_m1=2)),
     ('MULIMM',dict(cp_m1=3,cm_m1=3)),('AD_C',dict(ca_ad=2)),
     ('AD_NEGB',dict(ca_ad=3)),('AD_D',dict(ca_ad=5)),
     ('M2_C',dict(cm_m2=1)),('E1_ADDIMM',dict(cs_e1=4)),
     ('E2_MULB',dict(ce_e2=1)),('BF16',dict(co_rnd=1)),
     ('AB_AD_C_BF16',dict(cp_m1=1,cm_m1=1,ca_ad=2,co_rnd=1))]


def pack(d):
    v=0
    for n,w in FIELDS:
        x=int(d.get(n,0)); assert 0<=x<1<<w,(n,x)
        v=(v<<w)|x
    return v


def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    lane=np.arange(512,dtype=np.float32)
    rows=[]
    for row in range(512):
        # Distinct every lane and row; finite non-denormal values.
        rows.append(np.float32((lane%31-15)*np.float32(.125)+(row%64)*np.float32(.03125)+(row//64)*np.float32(.25)))
    data=np.stack(rows).astype(np.float32)
    (out/'seed.mem').write_text('\n'.join(f'{x:08x}'for x in data.view(np.uint32).ravel())+'\n')
    a,b,c,d=(data[k*64:(k+1)*64]for k in range(4));gold=[]
    controls=[]
    for name,mods in OPS:
        x=a.copy()
        m=mods.get('cp_m1',0)
        if m:x=np.float32(a*(b if m==1 else a if m==2 else np.float32(1.25)))
        if mods.get('cm_m2'):x=np.float32(x*c)
        ad=mods.get('ca_ad',0)
        if ad:x=np.float32(x+(c if ad==2 else -b if ad==3 else d))
        if mods.get('cs_e1'):x=np.float32(x+np.float32(.375))
        if mods.get('ce_e2'):x=np.float32(x*b)
        bits=x.view(np.uint32)
        if mods.get('co_rnd'):bits=(bits+0x7fff+((bits>>16)&1))&0xffff0000
        gold.extend(bits.ravel())
        ctl=dict(no=1,ni=8192,ls=7,lvw=7,dst=1,co_dst=1,
                 cp_imm1=0x3fa00000,cm_imm1=0x3fa00000,ce_imm1=0x3fa00000,
                 ca_imm2=0x3ec00000,cs_imm2=0x3ec00000,**mods)
        controls.append(ctl)
    (out/'gold.mem').write_text('\n'.join(f'{x:08x}'for x in gold)+'\n')
    # Four distinct quarter address spaces, compiler-issued affine offset terms.
    terms=sum((1<<k)<<(24*(s*10+k))for s in range(5)for k in range(7))
    images=[]
    for ctl in controls:
        for cycle in range(176):
            combined=0
            for q in range(4):
                fields=dict(ctl,ld=int(cycle==0),ld_c=terms,emit=int(8<=cycle<72),
                            i_v=max(0,cycle-8)*128,
                            vb=sum(((q<<14)+(((s*64 if s<4 else 256)>>7)<<16)+(((s*64 if s<4 else 256)&127)<<7))<<(s*24)for s in range(5)))
                combined|=pack(fields)<<(q*1742)
            images.append(combined)
    (out/'control.mem').write_text('\n'.join(f'{x:01742x}'for x in images)+'\n')
    (out/'programme.json').write_text(json.dumps(dict(qualified=False,ops=[n for n,_ in OPS],
        issue_words_per_op=32768,issues_per_op=64,cycles_per_op=176,
        total_words=len(gold),source='independent NumPy FP32 RNE; full real N512/M128',
        lowerer_status='baseline fixture only; canonical SU records not yet scheduled',
        SRAM_response_offset=2,normal_fetch_extra_edges=2,gather_extra_edges=4),indent=2)+'\n')


if __name__=='__main__':main()
