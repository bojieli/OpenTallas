#!/usr/bin/env python3
"""Reuse verified released dense scale masks; permute command-frame metadata only."""
from __future__ import annotations
import argparse,copy,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_split.b2_frame import group_at,position_of
from qwen_scale_rom.build import REVISION,LOCK_SHA,INDEX_SHA

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def signature(p):
 s=p.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--manifest',type=Path,required=True)
 ap.add_argument('--manifest-sha',required=True)
 ap.add_argument('--mask-root',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args()
 if sha(a.manifest)!=a.manifest_sha:raise ValueError('immutable source manifest hash mismatch')
 old=json.loads(a.manifest.read_text())
 if (old['checkpoint_revision'],old['checkpoint_lock_sha256'],old['checkpoint_index_sha256'],old['groups'],old['instances_per_rank'])!=(REVISION,LOCK_SHA,INDEX_SHA,3072,384):
  raise ValueError('wrong released scale cohort')
 if sorted(r['rank']for r in old['ranks'])!=list(range(8)):raise ValueError('full8rank cohort required')
 result=copy.deepcopy(old)
 result.update(schema='opentallas.qwen-tp8-native-scale-rom.b2-reframe.v1',result_frame=2,
  source_manifest_sha256=a.manifest_sha,source_mask_root=str(a.mask_root),
  source_payload_changed=False,program_bytes_changed=False,
  qualification='Released payload SHA verification + physical active-slot permutation; no native token or controller schedule qualification')
 inventory={};cache={};ops=0;instances=0
 for rank in result['ranks']:
  src=a.mask_root/f"rank{rank['rank']}"
  expected=src/'expected_scale_words.hex'
  if sha(expected)!=rank['expected_words_sha256'] or len(expected.read_text().splitlines())!=30576:
   raise ValueError(f'expected payload mismatch {expected}')
  inventory[expected]=signature(expected)
  if len(rank['instances'])!=384 or len({v['instance']for v in rank['instances']})!=384:raise ValueError('bad actual macro inventory')
  for inst in rank['instances']:
   p=src/'masks'/(inst['instance']+'.viamap.hex')
   sig=signature(p)
   digest=cache.get(sig)
   if digest is None:
    digest=sha(p)
    if signature(p)!=sig:raise ValueError(f'source changed {p}')
    cache[sig]=digest
   if digest!=inst['sha256']:raise ValueError(f'actual macro payload mismatch {p}')
   inventory[p]=sig;instances+=1
  for stage in rank['stages']:
   for op in stage['program']['decoded_scale_operations']:
    split=op['split_log2']
    if not 7<=split<=11:raise ValueError('empty or unsupported b2 output split')
    before=op['active_port_slots']
    groups=[group_at(split,p,1)for p in before]
    if None in groups:raise ValueError('source manifest has inactive physical slot')
    after=sorted(position_of(split,g,2)for g in groups)
    if len(set(after))!=len(before):raise ValueError('nonbijective frame')
    op['source_active_port_slots']=before;op['active_port_slots']=after;ops+=1
 if a.out.exists():raise ValueError('output already exists; immutable source cohort must not be overwritten')
 # Validate all sources before creating the new cohort; links preserve exact bytes.
 for p,sig in inventory.items():
  if signature(p)!=sig:raise ValueError(f'source changed {p}')
 a.out.mkdir(parents=True)
 for rank in result['ranks']:
  dst=a.out/f"rank{rank['rank']}"; (dst/'masks').mkdir(parents=True)
  src=a.mask_root/f"rank{rank['rank']}"
  os.link(src/'expected_scale_words.hex',dst/'expected_scale_words.hex')
  for inst in rank['instances']:
   name=inst['instance']+'.viamap.hex';os.link(src/'masks'/name,dst/'masks'/name)
  (dst/'manifest.json').write_text(json.dumps(rank,indent=2)+'\n')
 result['reframe_source_sha256']={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__),ROOT/'tools/qwen_split/b2_frame.py']}
 result['verified_instances']=instances;result['reframed_program_operations']=ops
 (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 print(f'PASS b2 scale cohort: {instances} actual ROM mask IDs, {ops} program operations,8ranks; unchanged released payloads; manifest {sha(a.out/"manifest.json")}',flush=True)
if __name__=='__main__':main()
