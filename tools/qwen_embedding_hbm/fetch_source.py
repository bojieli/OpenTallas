#!/usr/bin/env python3
"""Fetch only the exact locked shard containing the actual embedding tensor."""
from pathlib import Path
import argparse,hashlib,json,os,urllib.request
ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 lock=json.loads((ROOT/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
 files={x['path']:x for x in lock['expected_files']}
 def fetch(name):
  expected=files[name];dest=a.out/name
  if dest.exists():
   digest=hashlib.sha256()
   with dest.open('rb') as f:
    for b in iter(lambda:f.read(8<<20),b''):digest.update(b)
   if dest.stat().st_size==expected['size_bytes'] and digest.hexdigest()==expected['sha256']:return dest
   raise ValueError(f'existing snapshot payload differs:{dest}')
  temp=dest.with_suffix(dest.suffix+'.partial')
  if temp.exists():raise ValueError('existing partial download needs live-owner audit')
  url=f"https://huggingface.co/{lock['repository']}/resolve/{lock['revision']}/{name}"
  digest=hashlib.sha256();total=0
  with urllib.request.urlopen(url) as response,temp.open('xb') as out:
   while True:
    b=response.read(8<<20)
    if not b:break
    out.write(b);digest.update(b);total+=len(b)
    if total%(256<<20)==0:print('SOURCE_DOWNLOAD',name,total,flush=True)
  if total!=expected['size_bytes'] or digest.hexdigest()!=expected['sha256']:raise ValueError('locked source checksum mismatch')
  os.rename(temp,dest);print('PASS_LOCKED_SOURCE',name,total,digest.hexdigest(),flush=True);return dest
 index=fetch(lock['checkpoint_index']);mapping=json.loads(index.read_text())['weight_map']
 shard=mapping['model.embed_tokens.weight'];fetch(shard)
 (a.out/'source_binding.json').write_text(json.dumps(dict(checkpoint_revision=lock['revision'],tensor='model.embed_tokens.weight',index=files[lock['checkpoint_index']],shard=files[shard]),indent=2)+'\n')
if __name__=='__main__':main()
