#!/usr/bin/env python3
"""Build actual two4096-page native HCfn via masks for all40main+3MTP sets.
Each output's canonical FP32 coefficients occupy6880 of8192 reserved addresses.
No coefficient compression or quantization;10 spare bits/macro remainzero.
"""
import argparse,hashlib,json
from pathlib import Path
from hcx_projection_vectors import load

def build(root,out,row):
 masks=[[[[0]*512 for _ in range(2)]for _ in range(4)]for _ in range(8)]
 params=[[0]*512 for _ in range(4)]
 sources=[]
 for layer in range(43):
  src=root/('vec' if layer<40 else 'vecm')/(f'L{layer:02d}' if layer<40 else f'M{layer-40}R0')
  vm,rom,eps,cases=load(src)
  assert len(cases)==2
  sources.append(dict(layer=layer,path=str(src),hbm_sha256=hashlib.sha256((src/'hu_hbm.mem').read_bytes()).hexdigest()))
  for block,line in enumerate(cases):
   d=int(line[56:],16);b=(d>>384)&((1<<256)-1);bs=((b>>8)&((1<<40)-1))>>5
   for beat in range(4):
    paddr=8*layer+4*block+beat;data=rom[bs+beat]
    for m in range(4):
     payload=(data>>(64*m))&((1<<64)-1)
     while payload:
      bit=(payload&-payload).bit_length()-1
      params[m][paddr//8]|=1<<(8*bit+paddr%8);payload&=payload-1
   for bank in range(8):
    for run in range(80):
     addr=80*(2*layer+block)+run;pg=addr>>12;low=addr&4095
     for m in range(4):
      payload=0
      for j in range(8):
       lane=m*8+j;sec=bs+4+(8*row+bank)*320+run*4+lane//8
       w=(rom[sec]>>(32*(lane%8)))&0xffffffff;payload|=w<<(32*j)
      # Transpose address muxbit into actual physical266-bit ROM mask rows.
      while payload:
       bit=(payload&-payload).bit_length()-1
       masks[bank][m][pg][low//8]|=1<<(bit*8+low%8)
       payload&=payload-1
  print(f'HCX_RESIDENT layer{layer} row{row} addresses{160*layer}..{160*layer+159}',flush=True)
 out.mkdir(parents=True,exist_ok=True)
 for bank in range(8):
  for m in range(4):
   for pg in range(2):
    (out/f'hcx_r0_b{bank}_l{m}_p{pg}.viamap.hex').write_text(''.join(f'{x:0532x}\n'for x in masks[bank][m][pg]))
 for m in range(4):(out/f'hcx_post_p{m}.viamap.hex').write_text(''.join(f'{x:0144x}\n'for x in params[m]))
 (out/'resident_manifest.json').write_text(json.dumps(dict(row=row,layers=43,words_per_layer=40960,FP32_payload_bits=43*40960*32,ROM_payload_capacity_bits=64*4096*256,macros=64,macro='ot_rom_4096x266_m8',native_addresses=[0,6879],source=sources),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--row',type=int,required=True);a=p.parse_args()
 if not 0<=a.row<24:p.error('row must be0..23')
 build(a.vectors,a.out,a.row)
