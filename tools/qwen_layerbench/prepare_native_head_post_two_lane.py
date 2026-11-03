#!/usr/bin/env python3
"""Prepare finite station-boundary REFERENCE vectors; no RTL execution."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference',type=Path,required=True)
p.add_argument('--boot',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
streams={}
for line in (a.reference/'L6_prefix_streams_REFERENCE.tsv').read_text().splitlines():
 if line.startswith('#'):continue
 b,s,k,j,v=line.split();key=tuple(map(int,(b,k,j,s)));assert key not in streams;streams[key]=v
rows=[]
for b,n in [(0,8),(148,3)]:
 for k in range(8):
  for j in range(n):
   for s in range(8):rows.append(streams[(b,k,j,s)])
assert len(rows)==704
(a.out/'l6_REFERENCE.hex').write_text('\n'.join(rows)+'\n')
gold=[]
for line in (a.reference/'full512_scaled_REFERENCE.tsv').read_text().splitlines():
 if not line.startswith('#'):gold.append(line.split()[-1])
assert len(gold)==11
(a.out/'scaled_REFERENCE.hex').write_text('\n'.join(gold)+'\n')
boots=json.loads(a.boot.read_text());assert [(x['slice'],x['kind'],x['addr'])for x in boots]==[(1,2,72),(1,2,76),(8,2,264)]
(a.out/'genuine_btab.hex').write_text('\n'.join(x['payload_hex']for x in boots)+'\n')
receipt=dict(status='PREP_NOT_SIMULATED',scope='real two-lane sender/receiver station and shared BTAB; eight sequential lane contexts; explicit REFERENCE L6 inputs; no executed full ME, global phase, AMAX or ROOT claim',clock='nominal component833ps; selected distinct region providers not substituted or qualified',publication='near inputs14component edges before corresponding far; same own-input schedule to sender and receiver; native sender output register and receiver PIN_IN establish neighbor lead, subject to exact native SRAM source review',count=dict(contexts=16,reference_L6_vectors=704,scaled_rows=176),inputs={str(x):sha(x)for x in [a.boot,a.reference/'L6_prefix_streams_REFERENCE.tsv',a.reference/'full512_scaled_REFERENCE.tsv']},outputs={x.name:sha(x)for x in a.out.glob('*.hex')})
(a.out/'prep_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt['status'],receipt['count'])
