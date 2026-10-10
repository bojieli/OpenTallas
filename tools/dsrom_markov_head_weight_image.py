#!/usr/bin/env python3
"""Released row-congruent images for one actual32-row A successor.
Two real4096x274 macros alternate the512payload words; unused274-256 bitszero.
Padded rows never replace released rows and are masked bydriver VALID_ROWS/globalid.
"""
import argparse,hashlib,json,struct
from pathlib import Path
KEY='mtp.2.markov_head.head.weight'
REV='dba1be0a40aa45a94ad051997016db3960a90277'
DEFAULT=Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots')/REV

def generate(snapshot,out,row0,valid_rows=32,instance='mk'):
 if row0<0 or row0>131071 or not 0<=valid_rows<=32:raise ValueError('row descriptor bounds')
 if not instance or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in instance):raise ValueError('instance name')
 out.mkdir(parents=True,exist_ok=False)
 idxpath=snapshot/'model.safetensors.index.json';idx=json.loads(idxpath.read_text())['weight_map'];shard=snapshot/idx[KEY]
 physical=[[0]*512 for _ in range(2)];payload=hashlib.sha256();real=0
 spread=[sum(((b>>k)&1)<<(8*k) for k in range(8)) for b in range(256)]
 with shard.open('rb') as f:
  n=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(n))[KEY]
  if header['shape']!=[129280,256] or header['dtype']!='BF16':raise ValueError('released head shape/dtype')
  offset=8+n+header['data_offsets'][0]
  for row in range(32):
   if row<valid_rows and row0+row<129280:
    f.seek(offset+(row0+row)*512);data=f.read(512)
    if len(data)!=512:raise ValueError('truncated tensor')
    real+=1;payload.update(data)
   else:data=bytes(512)
   for beat in range(16):
    logical=16*row+beat;macro=logical%2;addr=logical//2
    word=int.from_bytes(data[32*beat:32*(beat+1)],'little')
    expanded=sum(spread[(word>>(8*j))&255]<<(64*j) for j in range(32))
    physical[macro][addr//8]|=expanded<<(addr%8)
 for macro in (0,1):(out/f'{instance}_{macro}.viamap.hex').write_text(''.join(f'{v:0548x}\n' for v in physical[macro]))
 receipt=dict(schema='opentallas.md6.markovweight-image.v1',checkpoint_revision=REV,key=KEY,shard=idx[KEY],header=header,index_sha256=hashlib.sha256(idxpath.read_bytes()).hexdigest(),row0=row0,VALID_ROWS=valid_rows,released_rows_copied=real,padded_rows=32-real,payload_sha256=payload.hexdigest(),mapping='macro=(16*local_row+beat)%2; addr=(16*local_row+beat)//2',ROM_ECC=False,images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.viamap.hex')})
 (out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--snapshot',type=Path,default=DEFAULT);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--row0',type=int,required=True);ap.add_argument('--valid-rows',type=int,default=32);ap.add_argument('--instance',default='mk')
 a=ap.parse_args();generate(a.snapshot,a.out,a.row0,a.valid_rows,a.instance)
