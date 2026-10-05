#!/usr/bin/env python3
"""Extract unchanged tile0/pair0,1 source sectors as RETURN test stimuli only.
No SRAM/consumer preload. This consumes the retained L0 image, not an oracle.
"""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
words=[];sectors=[];target=0;index=0
with a.source.open() as f:
 for line in f:
  for token in line.split():
   if index==target:
    words.append(int(token,16));target+=1
    if len(words)==16:
     for pair in range(2):sectors.append(sum(words[pair*8+k]<<(k*32) for k in range(8)))
     words=[]
     if len(sectors)==1024:break
     target=(len(sectors)//2)*6144*4
   index+=1
  if len(sectors)==1024:break
if len(sectors)!=1024:raise ValueError('incomplete actual L0 image')
payload=a.out/'returned_payload.hex';payload.write_text(''.join(f'{x:064x}\n' for x in sectors))
h=hashlib.sha256()
with a.source.open('rb') as f:
 for b in iter(lambda:f.read(1<<20),b''):h.update(b)
(a.out/'source.json').write_text(json.dumps(dict(source=str(a.source),source_sha256=h.hexdigest(),returned_payload_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),source_words=512,tile=0,pairs=[0,1],source_formula='(word*6144+tile*4+2*pair)*16',scope='return-port stimuli, never consumer/SRAM preload; not complete physical HBM issuer qualification'),indent=2)+'\n')
