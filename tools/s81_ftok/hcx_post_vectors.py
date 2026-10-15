#!/usr/bin/env python3
"""Real HC operands -> resident tail parameter ROM + canonical raw-mix VM rows.

Raw mixes here are the golden reference for the isolated tail gate. This does
not claim a die-composed projection/all-gather/tail run.
"""
import argparse,json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import hdc_golden_v41 as G

def build(src,out):
 G.set_arith('chunk8');out.mkdir(parents=True,exist_ok=True)
 vm={int(s[:8],16):int(s[8:],16) for s in (src/'hu_vmi.mem').read_text().splitlines()}
 rom={int(s[:10],16):int(s[10:],16) for s in (src/'hu_hbm.mem').read_text().splitlines()}
 ex=[int(s[8:],16) for s in (src/'hu_exp.mem').read_text().splitlines()]
 eps=int(re.search(r"NEPS = 32'h([0-9A-Fa-f]+)",(src/'hu_sizes.svh').read_text()).group(1),16)
 masks=[[0]*512 for _ in range(4)]
 for block,line in enumerate((src/'hu_case.mem').read_text().splitlines()):
  rec=int(line[56:],16);a=(rec>>128)&((1<<256)-1);b=(rec>>384)&((1<<256)-1)
  ab=(a>>8)&((1<<40)-1);bs=((b>>8)&((1<<40)-1))>>5
  x=np.array([vm[ab+i] for i in range(20480)],np.uint32).view(np.float32)
  fn=np.empty((24,20480),np.uint32)
  for row in range(24):
   for k in range(8):
    for r in range(80):
     for l in range(32):fn[row,8*(r*32+l)+k]=(rom[bs+4+(8*row+k)*320+r*4+l//8]>>(32*(l%8)))&0xffffffff
  scale=G.rsqrt(G.add(G.div(G.split_sum(G.mul(x,x),G.HC_SS_SPLIT),np.float32(20480)),G.from_bits(eps)))
  raw=np.asarray(G.mul(G.matvec_c(fn.view(np.float32),x,G.HC_SPLIT,cls='he'),scale),np.float32).view(np.uint32).tolist()
  def rows(words):return ''.join(f'{sum(int(w)<<(32*i) for i,w in enumerate(words[j:j+16])):0128x}\n' for j in range(0,len(words),16))
  (out/f'raw{block}.mem').write_text(rows(raw+[0]*8))
  want=ex[block*24:(block+1)*24]
  (out/f'coef{block}.mem').write_text(rows(want[8:24]+want[:8]+[eps]+[0]*7))
  for beat in range(4):
   data=rom[bs+beat];addr=block*4+beat
   for m in range(4):
    payload=(data>>(64*m))&((1<<64)-1)
    for bit in range(64):
     if payload>>bit&1:masks[m][addr//8]|=1<<(8*bit+addr%8)
 for m in range(4):(out/f'hcx_post_p{m}.viamap.hex').write_text(''.join(f'{r:0144x}\n' for r in masks[m]))
 (out/'eps.mem').write_text(f'{eps:08x}\n')
 (out/'metadata.json').write_text(json.dumps(dict(source=str(src),scope='isolated native tail, rawmix reference inputs; no die composition',macros=4),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--src',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.src,a.out)
