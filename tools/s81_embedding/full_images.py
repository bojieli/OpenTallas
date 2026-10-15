#!/usr/bin/env python3
"""Full resident ROM images from released raw BF16 checkpoint, no activations.

One complete immutable table copy across 4 logical homes /12 physical HEADs.
Each image is exactly the memory compiler's8192x274,mux8 physical via layout.
"""
import argparse,hashlib,json,pathlib,sys
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_checkpoint import Checkpoint,DEFAULT_CHECKPOINT
VQ=32320;WORDS=320;DEPTH=8192;BANKS=1263

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def words_for_bank(checkpoint,owner,bank):
 lo=bank*DEPTH;hi=min(lo+DEPTH,VQ*WORDS)
 first,last=lo//WORDS,(hi+WORDS-1)//WORDS
 raw=checkpoint.raw('embed.weight',(owner*VQ+first)*10240,(last-first)*10240)
 rows=np.frombuffer(raw,dtype='<u2').reshape(-1,40,16,8)
 ordered=rows.transpose(0,1,3,2).reshape(-1,16)[lo-first*WORDS:hi-first*WORDS]
 words=np.zeros((DEPTH,16),dtype='<u2');words[:len(ordered)]=ordered
 return words

def encode(words):
 # Eight adjacent logical addresses become each physical row. Transpose bits
 # into physical column bit*8+address%8, exactly phys_col in real macro model.
 data=words.view(np.uint8).reshape(1024,8,32)
 bits=np.unpackbits(data,axis=2,bitorder='little')
 packed=np.packbits(bits.transpose(0,2,1),axis=2,bitorder='little').reshape(1024,256)
 # Upper18logical bits correspond to144 unused physical columns; pad zeros.
 return ''.join('0'*36+row[::-1].tobytes().hex()+'\n' for row in packed)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',type=pathlib.Path,default=DEFAULT_CHECKPOINT)
 ap.add_argument('--out',type=pathlib.Path,required=True)
 ap.add_argument('--owners',type=int,nargs='+',default=[0,1,2,3]);args=ap.parse_args()
 args.out.mkdir(parents=True,exist_ok=False)
 c=Checkpoint(args.checkpoint)
 try:
  _,_,desc=c.descriptor('embed.weight')
  if desc['dtype']!='BF16' or desc['shape']!=[129280,5120]:raise ValueError(desc)
  records=[]
  for owner in args.owners:
   if not 0<=owner<4:raise ValueError(owner)
   for bank in range(BANKS):
    p=args.out/f's81_embed_o{owner}_b{bank}.viamap.hex'
    p.write_text(encode(words_for_bank(c,owner,bank)))
    records.append(dict(owner=owner,bank=bank,physical_head=3*owner+bank//421,
      path=p.name,sha256=sha(p),logical_words=min(DEPTH,VQ*WORDS-bank*DEPTH)))
   print(f'owner{owner}: complete{BANKS}resident macro images',flush=True)
  index=args.checkpoint/'model.safetensors.index.json'
  record=dict(schema='opentallas.s81.full-embedding-images.v1',tensor='embed.weight',shape=desc['shape'],dtype=desc['dtype'],
   checkpoint=str(args.checkpoint),index_sha256=sha(index),tensor_descriptor=desc,source_bytes_read=c.read_bytes,
   complete_full_vocab=(sorted(args.owners)==[0,1,2,3]),macros=records)
  (args.out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
 finally:c.close()
if __name__=='__main__':main()
