#!/usr/bin/env python3
"""Nonempty compact-table mechanism fixture, not current programme qualification."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import programme_store_fixture as P

a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
b=args.out;b.mkdir(parents=True,exist_ok=True)
m=json.loads(gzip.decompress((Path(__file__).parent/'table_manifest.json.gz').read_bytes()))
words=P.logical_images(m)[0]
for lane in range(4):
    rows=P.physical_rows(words,lane)
    (b/f'table_s0_m{lane}.viamap.hex').write_text(''.join(f'{x:0532x}\n' for x in rows))
# Independent inverse of actual physical ROM model indexing.
lanes=[[int(x,16) for x in (b/f'table_s0_m{i}.viamap.hex').read_text().split()] for i in range(4)]
def word(addr):
    out=0
    for j,rows in enumerate(lanes):
        lane=sum(((rows[addr//8]>>(bit*8+addr%8))&1)<<bit for bit in range(266))
        out|=lane<<(266*j)
    return out
records=[];valid=nonzero=0
for st in range(1,37):
 for user in range(4):
  for k in range(88):
   row=106*(st-1)+(6*user+k if k<6 else 24+k-6)
   w=word(row);payload=w&((1<<1024)-1);v=(w>>1024)&1;kind=(w>>1025)&3;addr=(w>>1027)&((1<<24)-1)
   assert not(w>>1051)
   if v:
    assert kind in (1,2,3)
    addr=addr+[0,272,344,416][user] if kind==2 else addr | (user<<(6 if kind==3 else 7))
    valid+=1;nonzero+=int(payload!=0)
   records.append(payload|(v<<1024)|(kind<<1025)|(addr<<1027))
assert valid==nonzero==12672
(b/'expected.hex').write_text(''.join(f'{x:0263x}\n' for x in records))
(b/'fixture.json').write_text(json.dumps(dict(source='committed compact manifest at b8e6c6f863fcda1c73be9211a0a47528e3b82055; mechanism-only, not selected current programme qualification',records=len(records),valid=valid,nonzero_payloads=nonzero,mask_sha256={f'table_s0_m{i}.viamap.hex':hashlib.sha256((b/f'table_s0_m{i}.viamap.hex').read_bytes()).hexdigest() for i in range(4)}),indent=2)+'\n')
