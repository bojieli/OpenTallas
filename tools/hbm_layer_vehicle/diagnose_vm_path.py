#!/usr/bin/env python3
"""Diagnostic observation only: preserve drives/preload, inspect input and output state."""
import json,re,shutil,sys
from pathlib import Path

def make(source,boundary,output):
    src, out=Path(source),Path(output)
    arrays=[[int(x,16) for x in (src/f'{n}.mem').read_text().split()] for n in ('hdr','val','msk')]
    events=[x for x in zip(*arrays) if x[0]>>62==1]
    original=list(events)
    outs=json.loads(Path(boundary).read_text())['outputs']
    probes=[('input_early',1,0x8021,256),('input_before_commit',2670,0x8021,256),('output_late',3300,0x8023,256)]
    for cycle in range(2600,2801,10):
        for name in ('pgp_SW__busy','pgp_SW__valid','pgp_SW__fault'):
            probes.append((f'{name}@{cycle}',cycle,next(i for i,e in enumerate(outs) if e['name']==name),1))
    bit=0; manifest=[]
    for name,cycle,port,width in probes:
        manifest.append(dict(name=name,cycle=cycle,port=port,width=width,first_rec=bit))
        for j in range(width):
            h=(2<<62)|(1<<60)|(port<<44)|((bit+1)<<32)|cycle
            events.append((h,0,1<<j)); bit+=1
    events.sort(key=lambda x:((x[0]>>60)&3,x[0]&0xffffffff,x[0]>>62))
    assert [x for x in events if x[0]>>62==1]==original
    assert len(events)<6309
    events.extend([(3<<62,0,0)]*(6309-len(events)))
    out.mkdir(parents=True,exist_ok=False)
    for col,name in enumerate(('hdr','val','msk')):
        (out/f'{name}.mem').write_text(''.join(f'{r[col]:x}\n' for r in events))
    shutil.copyfile(src/'vm_pre.txt',out/'vm_pre.txt')
    (out/'diagnostic.json').write_text(json.dumps(dict(scope='diagnostic_only',qualifies_full_token=False,qualifies_native_layer=False,probes=manifest,bits=bit,drives=len(original)),indent=2)+'\n')

def collect(output):
    out=Path(output); meta=json.loads((out/'diagnostic.json').read_text()); bits={}
    for line in (out/'run.log').read_text().splitlines():
        m=re.fullmatch(r'SLICE_REC rec=(\d+) cyc=(\d+) (FAIL|COMMIT_OK)',line)
        if m:
            rec=int(m[1]); assert rec not in bits; bits[rec]=(int(m[2]),m[3]=='FAIL')
    assert len(bits)==meta['bits'],(len(bits),meta['bits'])
    for p in meta['probes']:
        value=0
        for j in range(p['width']):
            cycle,one=bits[p['first_rec']+j]; assert cycle==p['cycle']; value|=int(one)<<j
        p['observed']=f"{value:0{(p['width']+3)//4}x}"
    (out/'observed.json').write_text(json.dumps(meta,indent=2)+'\n')

if __name__=='__main__':
    if sys.argv[1]=='make':make(*sys.argv[2:])
    elif sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise ValueError('mode')
