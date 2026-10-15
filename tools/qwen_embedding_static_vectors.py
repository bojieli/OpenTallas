#!/usr/bin/env python3
"""External declared stimuli/expected answers from selected released HBM ABI."""
import argparse
from pathlib import Path
import struct
p=argparse.ArgumentParser();p.add_argument('image_root',type=Path);p.add_argument('token',type=int);p.add_argument('output',type=Path)
a=p.parse_args()
if not 0<=a.token<151936: raise ValueError('token bounds')
with (a.image_root/'embedding_codes.bin').open('rb') as f:f.seek(a.token*4096);codes=f.read(4096)
with (a.image_root/'embedding_scales_bf16.bin').open('rb') as f:
 f.seek(a.token*2);rawscale=f.read(2)
 f.seek((a.token//16)*32);packed_scale=f.read(32)
if len(codes)!=4096 or len(rawscale)!=2:raise ValueError('incomplete released image')
scale=struct.unpack('<f',b'\0\0'+rawscale)[0]
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'codes.hex').write_text(''.join(f'{int.from_bytes(codes[i:i+64],"little"):0128x}\n' for i in range(0,4096,64)))
(a.output/'scale_sector.hex').write_text(f'{int.from_bytes(packed_scale,"little"):064x}\n')
(a.output/'scale.hex').write_text(f'{int.from_bytes(rawscale,"little"):04x}\n')
values=[struct.unpack('<b',bytes([x]))[0]*scale for x in codes]
(a.output/'expected.hex').write_text(''.join(f'{struct.unpack("<I",struct.pack("<f",x))[0]:08x}\n' for x in values))
