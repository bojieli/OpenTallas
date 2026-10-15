#!/usr/bin/env python3
"""Bind actual canonical Qwen SwiGLU VM fixture to fixed SFU programme.

No numerical oracle is generated here. Expected BF16 words come directly from
su_prod_vec's machine execution; the RTL performs actual exp/div/multiplies.
"""
from pathlib import Path
import hashlib
import json
import sys
from sfu_control_image import encode
from sfu_vector_calendar import compile_vector

fixture=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
meta=json.loads((fixture/'su_prod.json').read_text())
assert len(meta['cases'])==1 and meta['cases'][0]['tag']=='swiglu'
case=meta['cases'][0]
assert case['roles']=={'A':[168960,172031,3072],'B':[172032,175103,3072],'C':[12672,12672,1],'O':[175104,178175,3072]}
def read_vm(path):
    words={}
    for line in path.read_text().splitlines():
        sector=int(line[:8],16);payload=int(line[8:],16)
        for i in range(8):words[sector*8+i]=payload>>(32*i)&0xffffffff
    return words
vin=read_vm(fixture/'su_vmi.mem');vout=read_vm(fixture/'su_vme.mem')
for name,base,count,source in [('gate',168960,3072,vin),('up',172032,3072,vin),('route',12672,1,vin),('gold',175104,3072,vout)]:
    (out/(name+'.hex')).write_text(''.join(f'{source[base+i]:08x}\n' for i in range(count)))
program=compile_vector(words=3072,bases=(0,12672,0,0,0),strides=(1,0,1,1,1),
                       amin=1,cclip=1,imm3=0x7f7fffff,sfu=5,e1=1,e2=1,rnd=1)
words=encode(program)
assert len(words)==368
(out/'image.hex').write_text(''.join(f'{word:0436x}\n' for word in words))
manifest=dict(canonical_program=meta['program'],canonical_case=case,
              source_fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir() if p.is_file()},
              mapping='G->operandA local0,route->real scalar operandB addr12672,U->operandC local0,O->outputlocal0',
              arithmetic='G=min(G,lim);clipU;SILU(G)*U*route;BF16',
              programme_rows=len(words),standalone_component=True,native_qualified=False)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

vm_words={}
for i in range(3072):
    vm_words[i]=vin[168960+i]
    vm_words[1026*8+i]=vin[172032+i]
vm_words[2052*8]=vin[12672]
(out/'vm_init.hex').write_text(''.join(f'{sum(vm_words.get(sector*8+w,0)<<(32*w) for w in range(8)):064x}\n' for sector in range(2056)))
