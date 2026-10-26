from pathlib import Path
import hashlib,json,struct,subprocess
R=Path('/srv/opentallas-scratch/claude/codex-tok-head-b-connected-2100')
files={};bad=[];objects=0
for p in sorted((R/'out/obj_b').rglob('*')):
 if not p.is_file():continue
 data=p.read_bytes()
 files[str(p.relative_to(R))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 if p.suffix=='.o':
  objects+=1
  try:
   assert data[:6]==b'\x7fELF\x02\x01'
   shoff=struct.unpack_from('<Q',data,40)[0];entsize,count=struct.unpack_from('<HH',data,58)
   assert entsize==64 and count and shoff+entsize*count<=len(data)
   for i in range(count):
    typ=struct.unpack_from('<I',data,shoff+i*64+4)[0]
    off,size=struct.unpack_from('<QQ',data,shoff+i*64+24)
    assert typ==8 or off+size<=len(data)
  except (AssertionError,struct.error):bad.append(str(p.relative_to(R)))
source=json.loads((R/'source_identity.json').read_text());mismatch=[]
for e in source['files']:
 if hashlib.sha256((R/e['staged']).read_bytes()).hexdigest()!=e['sha256']:mismatch.append(e['staged'])
tools={}
for name in ['/usr/bin/g++','/usr/libexec/gcc/x86_64-linux-gnu/15/cc1plus','/usr/bin/make','/usr/bin/ar','/usr/bin/ld','/usr/bin/as','/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator_bin']:
 p=Path(name);tools[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
print(json.dumps(dict(objects=objects,bad_objects=bad,source_files=len(source['files']),source_mismatches=mismatch,tools=tools,files=files),indent=1))
