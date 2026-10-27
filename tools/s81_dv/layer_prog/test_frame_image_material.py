#!/usr/bin/env python3
"""Check native production image material against explicit source CFG and MAT words."""
import os
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_dv'),str(ROOT/'tools/s81_static_control'),str(Path(__file__).parent)]
import lower_xs as X
import v41_die_images_w17w10 as I
from field_cfg7_image import decode_bank

def main():
 f=I.Field(16,1,0,active=1,pp=True,fast=True)
 f.cfg=[[[0]*25 for _ in range(16)]]
 f.cfg[0][0]=[(0xabc000000000+i*0x12345)&((1<<48)-1) for i in range(25)]
 f.words[0]={0:0x123456789abcdef,1:0xfedcba987654321}
 f.words[1]={0:0x987654321abcdef}
 with patch.dict(os.environ,{'OT_XS_APROJ_RANK_TAGS':'0'}):
  material=X.frame_image_material(f,[0],[0],[5],'u_f_0L00',[0,1])
  assert len(material)==18
  for pair in (0,5):
   for bank in range(7):
    words=decode_bank([int(v,16) for v in material[f'u_f_0L00_c{pair}_{bank}.viamap.hex'].splitlines()])
    for row in range(4096):
     want=f.cfg[0][0][row*7+bank] if pair==0 and row*7+bank<25 else 0
     assert words[row]==want,(pair,bank,row,words[row],want)
  # The real wrong-bank mechanism control is not identical to the right source values.
  wrong=decode_bank([int(v,16) for v in material['u_f_0L00_c0_1.viamap.hex'].splitlines()])
  assert wrong[0]!=f.cfg[0][0][0]
  for mb in (0,1):
   for parity in (0,1):
    rows=[int(v,16) for v in material[f'u_f_0L00_e0'+('b' if mb else '')+f'_{parity}.viamap.hex'].splitlines()]
    for addr in range(4096):
     got=sum(((rows[addr//8]>>(bit*8+addr%8))&1)<<bit for bit in range(276))
     assert got==f.words[mb].get(addr*2+parity,0),(mb,parity,addr)
  try:X.frame_image_material(f,[0],[0],[5],'../alias')
  except ValueError:pass
  else:raise AssertionError('foreign image path accepted')
 print('FRAME_IMAGE_MATERIAL_PASS: 57344 CFG rows,16384 MAT words; exact native names; wrong-bank/path controls')
if __name__=='__main__':main()
