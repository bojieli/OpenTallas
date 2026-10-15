#!/usr/bin/env python3
"""Wrong plane-fragment association, preserving all physical word protection."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--images',required=True);ap.add_argument('--out',required=True)
a=ap.parse_args();source=Path(a.images);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
low215=(1<<215)-1;low76=(1<<76)-1;changed=0
for epoch in (1,2):
 p0=[int(s,16) for s in (source/f'epoch{epoch}_plane0.hex').read_text().splitlines()]
 p1=[int(s,16) for s in (source/f'epoch{epoch}_plane1.hex').read_text().splitlines()]
 assert len(p0)==len(p1)==32768
 for n,(w0,w1) in enumerate(zip(p0,p1)):
  # Invert logical fragment association while keeping plane role, c7a1, PC,
  # original reserved bits and unused plane1 data bits entirely legal.
  a0=(w0&~low215)|(w1&low76)
  a1=(w1&~low215)|(w0&low76)
  assert (a0>>215)==(w0>>215) and (a1>>215)==(w1>>215)
  assert (a1&low215)>>76==0
  changed+=a0!=w0 or a1!=w1
  p0[n]=a0;p1[n]=a1
 for plane,words in ((0,p0),(1,p1)):
  (out/f'epoch{epoch}_plane{plane}.hex').write_text(''.join(f'{w:064x}\n' for w in words))
 shutil.copyfile(source/f'epoch{epoch}_logical.hex',out/f'epoch{epoch}_logical.hex')
(out/'semantic_mutant.json').write_text(json.dumps(dict(mutant='wrong protected plane fragment association',changed_pairs=changed,
 protection='c7a1, PC, plane-role, original reserved fields and unused payload remain byte-legal; expected logical programme stays canonical',
 files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.hex')}),indent=2)+'\n')
print('PAIR_SEMANTIC_MUTANT_GENERATED changed_pairs='+str(changed))
