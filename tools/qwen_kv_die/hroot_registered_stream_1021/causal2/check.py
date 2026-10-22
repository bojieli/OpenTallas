from pathlib import Path
import json,hashlib
p=Path('.')
a=p.joinpath('baseline.log').read_text().splitlines();b=p.joinpath('candidate.log').read_text().splitlines()
assert a==b, 'ORDERED_TRANSACTION_MISMATCH'
gold={int(s[-8:],16):int(s[:-8],16) for s in p.joinpath('native.mem').read_text().splitlines()};seen=[]
for s in b:
 if s.startswith('W '):
  _,addr,data=s.split();addr=int(addr,16);assert int(data,16)==gold[addr],s;seen.append(addr)
assert len(seen)==len(gold) and set(seen)==set(gold), 'MISSING_DUPLICATE_SECTOR'
r=dict(status='PASS',scope='legal RAW ROWS IKEY stream ordered transactions under independent random ready stalls; no shell guard/native/physical claim',writes=len(seen),descriptors=sum(s.startswith('D ')for s in b),source_sha256=hashlib.sha256(p.joinpath('qkd_host_native_engine.sv').read_bytes()).hexdigest())
p.joinpath('result.json').write_text(json.dumps(r,indent=2)+'\n');print('SPIPE6_STREAM_PASS',r)
