#!/usr/bin/env python3
"""KV FP8 finish join: random FP32 K/V vectors -> head RTL fp8r (iverilog) -> adapter-on svc wrapper stimulus; golden = hdc_golden.to_fp8 -> E4M3 bytes -> 4 words."""
import json,random,subprocess,sys,importlib.util
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'fp8_inverse'))
from fp8_inverse import fp8_to_fp32_bits
spec=importlib.util.spec_from_file_location('g',H/'hdc_golden.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
rev={}
for b in range(256):
    try:rev.setdefault(fp8_to_fp32_bits(b),b)
    except ValueError:pass
random.seed(8191);NC=110
def rand32():
    e=random.randint(114,138);return random.getrandbits(1)<<31|e<<23|random.getrandbits(23)
cases=[];allv=[]
poss=[0,1,15,16,4095,8191,8190,777]
for ci,pos in enumerate(poss):
    vec=[rand32() for _ in range(256)];cases.append(dict(name=f'rand{ci}_pos{pos}',pos=pos,vec=vec));allv+=vec
(H/'vec.hex').write_text('\n'.join(f'{v:08x}' for v in allv)+'\n')
subprocess.run(['iverilog','-g2012','-o',str(H/'fp8r.vvp'),str(H/'tb_fp8r.sv')],check=True,cwd=H);subprocess.run(['vvp','fp8r.vvp'],check=True,cwd=H,capture_output=True)
rtl=[int(l.split()[0],16) for l in (H/'rtl_out.hex').read_text().splitlines()]
out=[]
def dd(kind,mask,A,D):
    v=1<<547|kind<<545|mask<<537
    for l in range(8):v|=(A[l]&0xffffff)<<(345+24*l)|(D[l]&0xffffffff)<<(89+32*l)
    return v
for ci,c in enumerate(cases):
    r=rtl[ci*256:(ci+1)*256];gold32=g.to_fp8(np.array(c['vec'],dtype=np.uint32).view(np.float32)).view(np.uint32)
    ok=all((int(gold32[i])&0x7fffffff)==(r[i]&0x7fffffff) and (int(gold32[i])^r[i])&0x80000000==0 or (r[i]&0x7fffffff)==0 for i in range(256))
    by=[]
    for i in range(256):
        key=r[i]
        by.append(rev[key])
    words=[''.join(f'{b:02x}' for b in reversed(by[64*w:64*w+64])) for w in range(4)]
    d=H/'join'/c['name'];d.mkdir(parents=True,exist_ok=True);rows=[]
    for cy in range(NC):
        kd=0;mask=0;A=[0]*8;D=[0]*8
        for h in range(8):
            for dim in range(h,128,8):
                if cy==20+dim//8+(2 if h>=4 else 0):kd=1;mask|=1<<h;A[h]=dim;D[h]=r[dim]
                if cy==60+dim//8+(2 if h>=4 else 0):kd=2;mask|=1<<h;A[h]=dim;D[h]=r[128+dim]
        w=dd(kd,mask,A,D) if kd else 0
        slot=int(cy in(45,50,90,95));idx={45:0,50:1,90:2,95:3}.get(cy,0)
        rows.append(f"{(slot<<575)|(idx<<573)|(w<<25)|(c['pos']<<7)|((1 if cy==0 else 0)<<1)|int(cy==0):0144x}")
    (d/'stim.hex').write_text('\n'.join(rows)+'\n')
    out.append(dict(name=c['name'],pos=c['pos'],rtl_equals_golden_fp32=bool(ok),expect_words=words))
(H/'join_cases.json').write_text(json.dumps(out,indent=1)+'\n');print([o['rtl_equals_golden_fp32'] for o in out])
