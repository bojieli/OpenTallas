#!/usr/bin/env python3
"""Stream exact deployed boot281 or HOST hb283 words from the compact released HBM image."""
from pathlib import Path
import argparse,json,hashlib,zlib

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('out',type=Path)
 p.add_argument('--rope',type=Path,help='directory containing canonical rope_manifest.json and4MiBpayload')
 p.add_argument('--format',choices=['boot281','hb283'],default='boot281')
 p.add_argument('--tokens',type=int,nargs='+',help='Selected rows plus their complete scale sectors; otherwise full image')
 a=p.parse_args();m=json.loads((a.image/'manifest.json').read_text());v,h=m['source_shape']
 code=a.image/m['embedding_codes']['file'];scale=a.image/m['embedding_scales']['file']
 for path,key in [(code,'embedding_codes'),(scale,'embedding_scales')]:
  if digest(path)!=m[key]['sha256']:raise ValueError('payload SHA mismatch: '+str(path))
 toks=range(v) if a.tokens is None else sorted(set(a.tokens))
 if any(t<0 or t>=v for t in toks):raise ValueError('token outside actual vocabulary')
 groups=range(v//16) if a.tokens is None else sorted({t//16 for t in toks})
 rope_raw=None
 if a.rope:
  if a.tokens is not None:raise ValueError('RoPE fullbootstrap requires completeembeddingimage')
  rm=json.loads((a.rope/'rope_manifest.json').read_text());rp=a.rope/rm['file']
  if digest(rp)!=rm['sha256'] or rp.stat().st_size!=4194304:raise ValueError('RoPE payload identity/size mismatch')
  rope_raw=rp.read_bytes()
 count=checksum=0
 with code.open('rb') as c,scale.open('rb') as s,a.out.open('x') as out:
  def emit(e,data):
   nonlocal count,checksum
   if len(data)!=32:raise ValueError('incomplete sector')
   payload=int.from_bytes(data,'little');checksum=(checksum+zlib.crc32(e.to_bytes(4,'little')+data))&0xffffffff;count+=1
   word=(payload<<25)|e if a.format=='boot281' else (payload<<27)|(e<<2)|1
   out.write(f'{word:071x}\n')
  for t in toks:
   c.seek(t*h)
   for i in range(h//32):emit(t*128+i,c.read(32))
  for g in groups:
   s.seek(g*32);emit(v*128+g,s.read(32))
  if a.tokens is None and (count!=m['hbm']['sectors'] or checksum!=m['hbm']['boot_checksum']):raise ValueError('full bootstrap checksum mismatch')
  if rope_raw is not None:
   for i in range(131072):emit(19457304+i,rope_raw[i*32:(i+1)*32])
  if a.format=='hb283':out.write(f'{(((checksum<<32)|count)<<27)|3:071x}\n')
 rec=dict(schema='opentallas.qwen-embedding-hbm-boot.v1',format=a.format,sectors=count,checksum=checksum,
  image_manifest_sha256=digest(a.image/'manifest.json'),output_sha256=digest(a.out),tokens=a.tokens,rope_manifest_sha256=digest(a.rope/'rope_manifest.json') if a.rope else None)
 a.out.with_suffix(a.out.suffix+'.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec))
if __name__=='__main__':main()
