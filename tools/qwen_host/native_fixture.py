#!/usr/bin/env python3
"""Original QKV descriptor/wire payload; golden native KV comes from qkd KV row layout."""
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import kv_ingest_ref as R
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
heads=int(sys.argv[2]) if len(sys.argv)>2 else 2
mode=sys.argv[3] if len(sys.argv)>3 else 'edge'
ref=R.QwenKV(36,heads,128,8192)
spans=[(L,base,lo,hi) for L in [0,17,35] for base,lo,hi in [(0,5,13),(128,0,16),(8176,4,16)]] if mode=='edge' else [(L,base,0,16) for L in [0,1] for base in range(0,64,16)]
golden={};descs=[];beats=[];nb=[]
for index,(L,base,lo,hi) in enumerate(spans):
 n=hi-lo
 kcode=((np.arange(n*heads*128).reshape(n,heads,128)*7+index*11)%126).astype(np.uint8)
 vcode=((np.arange(n*heads*128).reshape(n,heads,128)*13+index*17+128)%254).astype(np.uint8)
 # Remove E4M3 NaN encodings; signed finite grids are exactly BF16-representable.
 vcode=np.where((vcode&127)==127,vcode^1,vcode).astype(np.uint8)
 kv=[R.fp8_value(kcode).astype(np.float32),R.fp8_value(vcode).astype(np.float32)]
 kcode,vcode=[R.fp8_code(x) for x in kv]
 payload=b''.join((x.view(np.uint32)>>16).astype('<u2').tobytes() for x in kv)
 assert len(payload)%64==0
 words=[int.from_bytes(payload[i:i+64],'little') for i in range(0,len(payload),64)]
 descs.append(ref.block_desc(L,base//16,lo,hi,R.FMT_BF16,fence=1,tag=index))
 nb.append(len(words));beats.extend(words)
 for v,codes in enumerate([kcode,vcode]):
  for rel in range(0 if mode=='legacy' else n):
   t=base+lo+rel
   for g in range(heads):
    # Exact original qkd_kv_wq.sec_of and q+G PC binding, independently
    # assembled from layer/head/position/byte indices of the wire image.
    sec=(L<<11)|(v<<10)|(g<<9)|(((t>>6)&1)<<8)|((t>>9)<<3)|((t>>3)&7)
    stack=(t>>7)&3
    for q in range(4):
     addr=(sec<<7)|(stack<<5)|(q<<3)|(t&7)
     golden[addr]=int.from_bytes(codes[rel,g,q*32:(q+1)*32].tobytes(),'little')
 if mode=='legacy':
  # Independent original QwenKV image, for default-off regression.
  for v,codes in enumerate([kcode,vcode]):
   for g in range(heads):
    if v==0:
     for q in range(64):
      addr=ref.k_elem(L,g,base,2*q)//32
      payload=codes[:,g,2*q].tobytes()+codes[:,g,2*q+1].tobytes()
      golden[addr]=int.from_bytes(payload,'little')
    else:
     for rel in range(n):
      for q in range(4):
       addr=ref.v_elem(L,g,base+rel,32*q)//32
       golden[addr]=int.from_bytes(codes[rel,g,q*32:(q+1)*32].tobytes(),'little')

(out/'desc.mem').write_text(''.join(f'{d:064x}\n' for d in descs))
(out/'pay.mem').write_text(''.join(f'{d:0128x}\n' for d in beats))
(out/'nb.mem').write_text(''.join(f'{n:08x}\n' for n in nb))
(out/'native.mem').write_text(''.join(f'{data:064x}{addr:08x}\n' for addr,data in sorted(golden.items())))
meta=dict(heads=heads,descriptors=len(descs),beats=len(beats),sectors=len(golden),spans=spans,wire='original QKV BF16 descriptors, CTX8192,HD128',map='original qkd_kv_wq sec_of + PC q/G; no old K tile data accepted as native rows')
(out/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
