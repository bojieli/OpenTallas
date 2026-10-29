#!/usr/bin/env python3
"""Decode exact high-level candidate; census is not a lowered hardware programme."""
import argparse, collections, hashlib, json, sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('image',type=Path); p.add_argument('--decoder-tools',type=Path,required=True); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
sys.path.insert(0,str(a.decoder_tools/'hbm_next'))
import isa_rows as I
b=a.image.read_bytes(); off=0; counts=collections.Counter(); expanded=collections.Counter(); fmts=collections.Counter(); sigs={}; detail=[]
while off<len(b):
 r,x,end=I.decode_one(b,off)
 if end<=off or end>len(b): raise ValueError('invalid decoder advance')
 op=r.unit+'.'+r.op; n=x.n if x else 1; counts[op]+=1; expanded[op]+=n
 if r.unit in ('SM','ATT'):
  operands={k:vars(v) for k,v in r.desc.items()}
  shape={k:{f:v for f,v in vars(d).items() if f!='base'} for k,d in r.desc.items()}
  s=dict(op=op,param=r.param,rows=n,rowx=vars(x) if x else None,operands=shape)
  key=json.dumps(s,sort_keys=True); e=sigs.setdefault(key,dict(**s,records=0,row_expansions=0,examples=[])); e['records']+=1; e['row_expansions']+=n
  if len(e['examples'])<2:e['examples'].append(dict(offset=off,operands=operands))
  detail.append(dict(offset=off,op=op,param=r.param,rows=n,operands=operands,rowx=vars(x) if x else None))
  for k,d in r.desc.items():fmts[f'{op}:{k}:{d.space}:{d.fmt}']+=1
 off=end
out=dict(image=str(a.image),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),records=sum(counts.values()),record_counts=dict(sorted(counts.items())),row_expansion_counts=dict(sorted(expanded.items())),sm_att_operand_formats=dict(sorted(fmts.items())),sm_att_shapes=list(sigs.values()),sm_att_records=detail,scope='Decoded high-level candidate only. No native two-quarter SM/ATT programme emitted; no unsupported-function elimination or source selection authorized.')
a.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ('records','record_counts','row_expansion_counts','sm_att_operand_formats')},indent=2))
