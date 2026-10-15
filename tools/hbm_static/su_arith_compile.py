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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hdc_golden import add, mul, to_bf16

OPS=[('BYP',{}),('AB',dict(cp_m1=1,cm_m1=1)),('AA',dict(cp_m1=2,cm_m1=2)),
     ('MULIMM',dict(cp_m1=3,cm_m1=3)),('AD_C',dict(ca_ad=2)),
     ('AD_NEGB',dict(ca_ad=3)),('AD_D',dict(ca_ad=5)),
     ('M2_C',dict(cm_m2=1)),('E1_ADDIMM',dict(cs_e1=4)),
     ('E2_MULB',dict(ce_e2=1)),('BF16',dict(co_rnd=1)),
     ('AB_AD_C_BF16',dict(cp_m1=1,cm_m1=1,ca_ad=2,co_rnd=1)),
     ('MAXB',dict(cp_m1=6,cm_m1=6)),('M2_IMM',dict(cm_m2=2)),
     ('QM_POS_AD_Q',dict(cm_qm=1,ca_ad=1)),('QM_NEG_AD_Q',dict(cm_qm=2,ca_ad=1)),
     ('QM_ALT_NP_AD_Q',dict(cm_qm=3,ca_ad=1)),('QM_ALT_PN_AD_Q',dict(cm_qm=4,ca_ad=1)),
     ('AD_IMM',dict(ca_ad=4)),('E1_MULC',dict(cs_e1=1)),('E1_ADDC',dict(cs_e1=2)),
     ('E1_MULIMM',dict(cs_e1=3)),('E2_MULIMM',dict(ce_e2=2)),
     ('PRE_ARND',dict(cx_arnd=1)),('PRE_RELU',dict(cx_arelu=1)),
     ('PRE_MIN',dict(cx_amin=1)),('PRE_CCLIP',dict(cx_cclip=1,ca_ad=2)),
     ('PRE_COMBINED',dict(cx_arnd=1,cx_arelu=1,cx_amin=1,cx_cclip=1,ca_ad=2)),
     ('NORM_Y_ARITH',dict(cp_m1=1,cm_m1=1,cs_e1=1,co_rnd=1)),
     ('ROPE_ARITH_ADDRESS_JOIN_OPEN',dict(cp_m1=1,cm_m1=1,cm_qm=3,ca_ad=1,co_rnd=1)),
     ('FUSED_CHAIN_BF16',dict(cx_arnd=1,cx_arelu=1,cx_amin=1,cx_cclip=1,
          cp_m1=1,cm_m1=1,cm_m2=2,cm_qm=2,ca_ad=1,cs_e1=1,ce_e2=2,co_rnd=1))]


def pack(d):
    v=0
    for n,w in FIELDS:
        x=int(d.get(n,0)); assert 0<=x<1<<w,(n,x)
        v=(v<<w)|x
    return v


def physical_word(q,row,bank=0):
    """Actual F2 frame/quarter/bank mapping, not row*128 across frame cuts."""
    return ((row>>7)<<16)|(q<<14)|((row&127)<<7)|bank


def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    lane=np.arange(512,dtype=np.float32)
    rows=[]
    for row in range(512):
        # Distinct every lane and row; finite non-denormal values.
        rows.append(np.float32((lane%31-15)*np.float32(.125)+(row%64)*np.float32(.03125)+(row//64)*np.float32(.25)))
    data=np.stack(rows).astype(np.float32)
    # Exercise input rounding ties, both tie parities, and signed-zero copy.
    # Other columns include non-BF16-exact mantissas. This is source data,
    # never a substitution for arithmetic in the RTL DUT.
    data[:64]+=np.float32(.0004)*((np.arange(512)%7)-3).astype(np.float32)
    data[:64,0]=np.uint32(0x3f808000).view(np.float32)
    data[:64,1]=np.uint32(0x3f818000).view(np.float32)
    data[:64,2]=np.uint32(0x80000000).view(np.float32)
    (out/'seed.mem').write_text('\n'.join(f'{x:08x}'for x in data.view(np.uint32).ravel())+'\n')
    a,b,c,d=(data[k*64:(k+1)*64]for k in range(4));gold=[]
    controls=[]
    for name,mods in OPS:
        aa=to_bf16(a)if mods.get('cx_arnd')else a.copy()
        if mods.get('cx_arelu'):aa=np.where(np.signbit(aa),np.float32(0),aa).astype(np.float32)
        if mods.get('cx_amin'):aa=np.minimum(aa,np.float32(.75)).astype(np.float32)
        cc=np.clip(c,np.float32(-.75),np.float32(.75))if mods.get('cx_cclip')else c
        x=aa.copy()
        m=mods.get('cp_m1',0)
        if m in(1,2,3):x=mul(aa,(b if m==1 else aa if m==2 else np.float32(1.25)))
        if m==6:x=np.maximum(aa,b).astype(np.float32)
        if mods.get('cm_m2'):x=mul(x,cc if mods['cm_m2']==1 else np.float32(1.25))
        qm=mods.get('cm_qm',0)
        negative=(np.ones(512,dtype=bool)if qm==2 else
                  np.arange(512)%2==0 if qm==3 else np.arange(512)%2==1 if qm==4 else
                  np.zeros(512,dtype=bool))
        q=mul(cc,np.where(negative,-d,d))if qm else None
        ad=mods.get('ca_ad',0)
        if ad:x=add(x,q if ad==1 else cc if ad==2 else -b if ad==3 else np.float32(.375)if ad==4 else d)
        e1=mods.get('cs_e1',0)
        if e1 in(1,3):x=mul(x,cc if e1==1 else np.float32(.375))
        if e1 in(2,4):x=add(x,cc if e1==2 else np.float32(.375))
        if mods.get('ce_e2'):x=mul(x,b if mods['ce_e2']==1 else np.float32(1.25))
        bits=x.view(np.uint32)
        if mods.get('co_rnd'):bits=(bits+0x7fff+((bits>>16)&1))&0xffff0000
        gold.extend(bits.ravel())
        ctl=dict(no=1,ni=8192,ls=7,lvw=7,dst=1,co_dst=1,
                 cp_imm1=0x3fa00000,cm_imm1=0x3fa00000,ce_imm1=0x3fa00000,
                 ca_imm2=0x3ec00000,cs_imm2=0x3ec00000,cx_imm3=0x3f400000,**mods)
        controls.append(ctl)
    (out/'gold.mem').write_text('\n'.join(f'{x:08x}'for x in gold)+'\n')
    # Four distinct quarter address spaces, compiler-issued affine offset terms.
    terms=sum((1<<k)<<(24*(s*10+k))for s in range(5)for k in range(7))
    images=[]
    for ctl in controls:
        for cycle in range(176):
            combined=0
            vector=max(0,min(63,cycle-8))
            for q in range(4):
                fields=dict(ctl,ld=int(cycle==0),ld_c=terms,emit=int(8<=cycle<72),
                            i_v=vector*128,
                            vb=sum(physical_word(q,(s*64 if s<4 else 256)+vector)<<(s*24)for s in range(5)))
                combined|=pack(fields)<<(q*1742)
            images.append(combined)
    (out/'control.mem').write_text('\n'.join(f'{x:01742x}'for x in images)+'\n')
    (out/'programme.json').write_text(json.dumps(dict(qualified=False,ops=[n for n,_ in OPS],
        issue_words_per_op=32768,issues_per_op=64,cycles_per_op=176,
        total_words=len(gold),source='independent hdc_golden NumPy FP32 RNE with specified canonical +0; full real N512/M128',
        lowerer_status='baseline fixture only; canonical SU records not yet scheduled',
        SRAM_response_offset=2,normal_fetch_extra_edges=2,gather_extra_edges=4),indent=2)+'\n')


if __name__=='__main__':main()
