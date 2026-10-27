#!/usr/bin/env python3
"""Serialize a validated finite job217 programme onto the existing native F20 host ABI."""
import argparse,json
from pathlib import Path

def records(words,target,count,wsc,pk5,pb5):
 if not 16<=target<=255:raise ValueError('plan-allocated target16..255 required; no default target')
 if not 1<=count<=256 or len(words)!=count:raise ValueError('exact finiteprogramme count required')
 out=[]
 def write(a,d):out.append({'addr':a,'data':d})
 def cfg256(word):
  if not 0<=word<1<<256:raise ValueError('host payload exceeds256bits')
  for k in range(8):write(0xf24,(word>>(32*k))&0xffffffff)
 write(0xf20,target)
 for w in words:
  if not 0<=w<1<<281:raise ValueError('job217 programme entry exceeds281bits')
  cfg256(w&((1<<256)-1));cfg256(w>>256)
 write(0xf20,(512<<8)|target)
 cfg256((0x46323137<<32)|(1<<24)|(pb5<<23)|(pk5<<17)|(wsc<<9)|count)
 write(0xf28,(count*2)<<12);write(0xf2c,1)
 # The F30 launch must be issued by the real START authority after actual
 # target ready/active/fault roundtrip and the current native calendar guard.
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--programme',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--target',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=json.loads(a.receipt.read_text())
 if not r.get('executable_programme_emitted') or r.get('status')!='COMPILED_OPT_IN':p.error('validated current calendar programme required; MISSING inputs never emit bootstrap')
 words=[int(x,16) for x in a.programme.read_text().splitlines() if x.strip()];cfg=r['calendar']['root_config'];out=records(words,a.target,r['entries'],cfg['wsc'],cfg['pk5'],cfg['pb5']);a.out.write_text(json.dumps({'target':a.target,'writes':out,'launch':'PENDING actual target-ready and current START authority; F30 deliberately not emitted','source_plan_commit':r['calendar']['source_plan_commit'],'source_image_sha256':r['image_sha256'],'hostleaf_to_provider_start_cycles':3,'mission_cycles_per_record_added':0},indent=2)+'\n');print('FUSED_BOOT_CONFIG_WRITES',len(out))
if __name__=='__main__':main()
