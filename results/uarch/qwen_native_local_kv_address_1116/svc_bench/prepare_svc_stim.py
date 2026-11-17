#!/usr/bin/env python3
"""Stimulus for the adapter-on qfd_native59_svc_obs1 wrapper bench. Row = {slot1,idx2,dd548,pos18,stage6,lcv1}=576b (144 hex)."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'fp8_inverse'))
from fp8_inverse import fp8_to_fp32_bits
G=json.load(open(H/'fp8_inverse'/'golden256.json'));B=G['bytes_seat_order']
NC=110
def dd(kind,mask,addrs,datas):
    v=1<<547|kind<<545|mask<<537
    for l in range(8):
        v|=(addrs[l]&0xffffff)<<(345+24*l);v|=(datas[l]&0xffffffff)<<(89+32*l)
    return v
cases=[]
for pos in (0,15,16,8191):cases.append(dict(name=f'pos{pos}',pos=pos,expect='PASS'))
cases+=[dict(name='epoch8192',pos=8192,expect='FAULT'),dict(name='dim128',pos=16,expect='FAULT',mut='dim'),
        dict(name='kindbit_in_dim',pos=16,expect='FAULT',mut='kindbit'),dict(name='codecNaN',pos=16,expect='FAULT',mut='codec'),
        dict(name='wrongdata',pos=16,expect='TYPED_DATA_FAIL',mut='data')]
for c in cases:
    d=H/c['name'];d.mkdir(exist_ok=True);rows=[]
    for cy in range(NC):
        kd=0;mask=0;A=[0]*8;D=[0]*8
        for h in range(8):
            for dim in range(h,128,8):
                if cy==20+dim//8+(2 if h>=4 else 0):
                    k=dim;val=fp8_to_fp32_bits(B[dim])
                    if c.get('mut')=='dim' and dim==0:k=128
                    if c.get('mut')=='kindbit' and dim==0:k|=1<<20
                    if c.get('mut')=='codec' and dim==0:val=0x7fc00000
                    if c.get('mut')=='data' and dim==0:val=fp8_to_fp32_bits(1)
                    kd=1;mask|=1<<h;A[h]=k;D[h]=val
                if cy==60+dim//8+(2 if h>=4 else 0):
                    kd=2;mask|=1<<h;A[h]=dim;D[h]=fp8_to_fp32_bits(B[128+dim])
        if kd==2 and any(cy==20+d//8+(2 if h>=4 else 0) for h in range(8) for d in range(h,128,8)):raise SystemExit('overlap')
        w=dd(kd,mask,A,D) if kd else 0
        slot=int(cy in (45,50,90,95));idx={45:0,50:1,90:2,95:3}.get(cy,0)
        lcv=int(cy==0);stage=1 if cy==0 else 0
        row=(slot<<575)|(idx<<573)|(w<<25)|(c['pos']<<7)|(stage<<1)|lcv
        rows.append(f'{row:0144x}')
    (d/'stim.hex').write_text('\n'.join(rows)+'\n')
(H/'cases.json').write_text(json.dumps(cases,indent=1)+'\n')
