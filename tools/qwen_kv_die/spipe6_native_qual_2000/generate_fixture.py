from pathlib import Path
import hashlib,json,numpy as np
import kv_ingest_ref as R
p=Path('.');old={n:(p/('seed_'+n)).read_bytes() for n in ['desc.mem','pay.mem','native.mem','fixture.json']};gold={int(l[-8:],16):int(l[:-8],16) for l in old['native.mem'].decode().splitlines()};descs=[];pay=[];added={};cases=[]
def append(desc,payload,case):
 descs.append(desc);pay.extend(R.beats_of(payload));cases.append(case)
def put(a,data):
 assert a not in gold and a not in added,hex(a)
 added[a]=int.from_bytes(data,'little')
def records(n,rb,tag):return [bytes((j*13+i*17+tag)%255+1 for j in range(rb)) for i in range(n)]
raw=bytes((i*7+5)%256 for i in range(96));base=0x3300fffe
append(R.desc(R.M_RAW,a0=base,n0=3,nb=2,fence=1,tag=200),raw,dict(mode='RAW',sectors=3,base=base))
for i in range(3):put(base+i,raw[i*32:(i+1)*32])
for first,n,rb,pitch,base,stride,ns,ring,tag in [(16,2,33,31,0xf0000000,0x50000000,2,0,201),(127,2,33,31,0x35000000,0,1,128,202)]:
 recs=records(n,rb,tag);payload=b''.join(recs);image=R.rows_image(8192,recs,first,rb,pitch,0,128,1,0,ns,ring)
 append(R.desc(R.M_ROWS,a0=base,a1=stride,a2=pitch,a3=ring,n0=first,n1=rb,n2=n,n6=ns.bit_length()-1,nb=(len(payload)+63)//64,fence=1,tag=tag),payload,dict(mode='ROWS',first=first,rows=n,ring=ring,pitch=pitch,base=base,stride=stride,stacks=ns))
 for i in range(n):
  stk,loc=R.row_slot(first+i,1,0,ns,ring)
  for sec in range(pitch):
   index=(stk*128+loc*pitch+sec)*32;put((base+(0 if ring else stk*stride)+loc*pitch+sec)&0xffffffff,image[index:index+32].tobytes())
recs=records(32,68,203);payload=b''.join(recs);image=R.ikey_image(8192,recs,1008,0,0,1,0,1);base=0x36000000
append(R.desc(R.M_IKEY,a0=base,n0=1008,n2=32,nb=(len(payload)+63)//64,fence=1,tag=203),payload,dict(mode='IKEY',first=1008,keys=32,cross_superblock=True,base=base))
for i,row in enumerate(image.reshape(-1,32)):
 if np.any(row):put(base+i,row.tobytes())
for n,rawbytes in old.items():(p/('original_'+n)).write_bytes(rawbytes)
(p/'desc.mem').write_text(''.join(f'{x:064x}\n' for x in descs)+old['desc.mem'].decode());(p/'pay.mem').write_text(''.join(f'{x:0128x}\n' for x in pay)+old['pay.mem'].decode());gold.update(added);(p/'native.mem').write_text(''.join(f'{v:064x}{k:08x}\n' for k,v in sorted(gold.items())))
meta=json.loads(old['fixture.json']);meta.update(descriptors=meta['descriptors']+len(descs),beats=meta['beats']+len(pay),sectors=len(gold),added_stream_cases=cases,original_fixture_sha256={k:hashlib.sha256(v).hexdigest() for k,v in old.items()},golden_reference_sha256=hashlib.sha256(Path('kv_ingest_ref.py').read_bytes()).hexdigest(),scope='single bounded actual engine cold/occupied reset fixture, frozen original RTL vs fresh native copy; not arbitrary-state/full-state proof');(p/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta)
