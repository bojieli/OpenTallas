#!/usr/bin/env python3
"""Verify every resident macro mask bit against released raw checkpoint words.

This verifies immutable ROM personalization, not computation or physical timing.
"""
import argparse,hashlib,json,pathlib,sys
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from dsrom_checkpoint import Checkpoint,DEFAULT_CHECKPOINT
from full_images import words_for_bank

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',type=pathlib.Path,default=DEFAULT_CHECKPOINT);ap.add_argument('--images',type=pathlib.Path,required=True);a=ap.parse_args()
 manifest=json.loads((a.images/'manifest.json').read_text());c=Checkpoint(a.checkpoint);records=[]
 if not manifest['complete_full_vocab'] or len(manifest['macros'])!=5052:raise ValueError('complete5052image inventory required')
 seen=set()
 try:
  for r in manifest['macros']:
   key=(r['owner'],r['bank'])
   if key in seen:raise ValueError('duplicate physical bank')
   seen.add(key)
   p=a.images/r['path'];text=p.read_text()
   if hashlib.sha256(text.encode()).hexdigest()!=r['sha256']:raise ValueError('personalization hash changed')
   lines=text.splitlines()
   if len(lines)!=1024 or any(len(x)!=548 for x in lines):raise ValueError('physical mask geometry')
   phys=np.frombuffer(bytes.fromhex(''.join(lines)),dtype=np.uint8).reshape(1024,274)
   if np.any(phys[:,:18]):raise ValueError('unused18logical bits must be zero')
   addresses=np.unpackbits(phys[:,18:][:,::-1],axis=1,bitorder='little').reshape(1024,256,8).transpose(0,2,1)
   recovered=np.packbits(addresses,axis=2,bitorder='little').reshape(8192,32).copy().view('<u2').reshape(8192,16)
   expected=words_for_bank(c,*key)
   if not np.array_equal(recovered,expected):raise ValueError(('released payload mismatch',key))
   records.append({'owner':key[0],'bank':key[1],'words':r['logical_words'],'payload_sha256':hashlib.sha256(recovered.tobytes()).hexdigest()})
 finally:c.close()
 if seen!={(o,b) for o in range(4) for b in range(1263)}:raise ValueError('missing resident banks')
 record=dict(schema='opentallas.s81.full-embedding-mask-readback.v1',pass_all=True,vocabulary=129280,verified_nonpadding_words=sum(r['words'] for r in records),verified_payload_bytes=129280*5120*2,physical_macros=len(records),source_checkpoint=str(a.checkpoint),verified=records)
 (a.images/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
 print('PASS all5052physicalROMvia masks recovered to all129280releasedBF16rows',flush=True)
if __name__=='__main__':main()
