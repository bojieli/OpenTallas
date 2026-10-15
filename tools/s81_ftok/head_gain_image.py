#!/usr/bin/env python3
"""Extend existing four HCP parameter ROM masks; retain coefficient addresses0..343.
Main/M2 final gains occupy addresses512..831/832..1151. No extra macro.
"""
import argparse,hashlib,json
from pathlib import Path

def extend(src,out,main,draft):
 src,out=Path(src),Path(out);out.mkdir(parents=True,exist_ok=True)
 masks=[[int(s,16)for s in (src/f'hcx_post_p{m}.viamap.hex').read_text().split()]for m in range(4)]
 assert all(len(a)==512 for a in masks)
 old=[a.copy()for a in masks]
 vectors=[]
 for mode,path in enumerate((main,draft)):
  words=[int(s,16)for s in Path(path).read_text().split()]
  assert len(words)==5120 and all(0<=v<=0xffffffff and v&65535==0 for v in words)
  vectors.append(words)
  for q in range(320):
   addr=512+320*mode+q
   for m in range(4):
    payload=sum((words[q*16+4*m+l]>>16)<<(16*l)for l in range(4))
    for bit in range(72):
     at=8*bit+addr%8
     masks[m][addr//8]=(masks[m][addr//8]&~(1<<at))|(((payload>>bit)&1)<<at)
 for m in range(4):
  assert all(masks[m][r]==old[m][r]for r in range(512)if not 64<=r<144)
  (out/f'hcx_post_p{m}.viamap.hex').write_text(''.join(f'{x:0144x}\n'for x in masks[m]))
 for mode,words in enumerate(vectors):
  for q in range(320):
   addr=512+320*mode+q
   data=sum(((masks[m][addr//8]>>(8*b+addr%8))&1)<<(64*m+b)for m in range(4)for b in range(64))
   assert [((data>>(16*l))&65535)<<16 for l in range(16)]==words[16*q:16*q+16]
  (out/f'gain{mode}.mem').write_text(''.join(f'{x:08x}\n'for x in words))
 rec=dict(existing_macros=4,macro='ot_rom_4096x72_m8',coeff_reserved=[0,343],gain_reserved=[512,1151],
          original_parameter_rows_preserved=True,physical_new_macros=0,
          inputs={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in (main,draft)},
          original_parameter_masks={f'hcx_post_p{m}.viamap.hex':hashlib.sha256((src/f'hcx_post_p{m}.viamap.hex').read_bytes()).hexdigest()for m in range(4)},
          output_masks={f'hcx_post_p{m}.viamap.hex':hashlib.sha256((out/f'hcx_post_p{m}.viamap.hex').read_bytes()).hexdigest()for m in range(4)},
          qualification='ROM image and stream component; shared-port physical parent integration pending')
 (out/'gain_image.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('src','out','main','draft'):p.add_argument('--'+name,required=True)
 a=p.parse_args();extend(a.src,a.out,a.main,a.draft)
