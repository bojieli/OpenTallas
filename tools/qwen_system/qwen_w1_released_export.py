#!/usr/bin/env python3
"""Export released real bank payloads under the exact existing row W8 contract."""
import argparse,hashlib,json,sys
from pathlib import Path
import torch
from safetensors import safe_open
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen3_deployment_quality import quantize_w8
p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--out',required=True);a=p.parse_args()
torch.set_num_threads(4)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
receipts=[]
with safe_open(a.checkpoint,framework='pt',device='cpu') as f:
 t=f.get_slice('markov_head.markov_w1.weight')
 if t.get_shape()!=[151936,256]:raise ValueError('wrong released shape')
 for bank,n in [(0,4096),(37,384)]:
  w=t[bank*4096:bank*4096+n,:]
  q,s,_=quantize_w8(w)
  scales=s.view(torch.int16).to(torch.int32).numpy().reshape(-1)&65535
  codes=q.numpy().view('uint8')
  # Existing native contract: FP32 exact INT8*BF16, canonical positive zero.
  values=(q.float()*s.float()).contiguous().view(torch.int32).numpy().view('uint32')
  d=out/f'bank{bank}';d.mkdir(exist_ok=True)
  for m in range(8):
   with (d/f'macro{m}.hex').open('w') as o:
    for r in range(4096):
     word=0
     if r<n:
      for c in range(32):word|=int(codes[r,m*32+c])<<(c*8)
      if m==0:word|=int(scales[r]&255)<<256
      if m==1:word|=int(scales[r]>>8)<<256
     o.write(f'{word:067x}\n')
  with (d/'values.hex').open('w') as o:
   for v in values.reshape(-1):o.write(f'{int(v):08x}\n')
  with (d/'scales.hex').open('w') as o:
   for v in scales:o.write(f'{int(v):04x}\n')
  receipts.append({'bank':bank,'rows':n,'files':{str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob('*.hex'))}})
(out/'receipt.json').write_text(json.dumps({'revision':'03326e5043815da1f81b109078b2889737c26017','tensor':'markov_head.markov_w1.weight','contract':'source exactquantize_w8, no norm folding; candidate W8 arithmetic, NOT original BF16 quality proof','banks':receipts},indent=2)+'\n')
