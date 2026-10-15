#!/usr/bin/env python3
"""Offline static reducer command compiler and independent NumPy golden vectors."""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hdc_golden_v41 import csum

LAT=8  # command issue -> commit / scalar (r1: one registered SRAM-operand stage; was 7)
def bits(x): return int(np.float32(x).view(np.uint32))
def bf(x): return ((x+0x7fff+((x>>16)&1))>>16)&65535
class Program:
 def __init__(self): self.c=0;self.commands=[];self.outputs=[];self.rows=[];self.ready={};self.sources=[]
 def emit(self,op,a=0,b=0,d=0,x=0,tag=0):
  reads=([a,b] if op in (2,5) else [a] if op in (1,3,4) else [])
  self.c=max([self.c]+[self.ready.get(v,0) for v in reads])
  self.commands.append((self.c,op,a,b,d,x,tag))
  if op!=4:self.ready[d]=self.c+LAT+1
  self.c+=1
 def export(self,a,tag,want):
  self.emit(4,a=a,tag=tag);self.outputs.append((self.commands[-1][0]+LAT,tag,want,bf(want)))
 def row(self,x,tag,wrong=False,sum_values=None):
  sum_values=x if sum_values is None else np.asarray(sum_values,dtype=np.float32)
  if not 1<=len(x)<=8192 or len(sum_values)!=len(x):raise ValueError("row requires1..8192 correspondingSCandE values")
  start=self.c;n=len(x);nc=(n+7)//8;npad=1<<(nc-1).bit_length()
  # Eight fixed interleaved max chains hide7-edge commit; compiler joins tree.
  for k in range(8): self.emit(0,d=k,x=0xff7fffff)
  for k,v in enumerate(x):
   self.emit(3,a=k%8,d=k%8,x=bits(v));self.sources.append((self.commands[-1][0],tag,'MAX_SCALED_SC',k))
  stride=1
  while stride<8:
   for k in range(0,8,stride*2):self.emit(5,a=k,b=k+stride,d=k)
   stride*=2
  vmax=bits(np.max(x));vmax=0 if vmax&0x7fffffff==0 else vmax
  self.export(0,tag*2,vmax)
  for k in range(npad): self.emit(0,d=k)
  # SRAM source reads are sample-major within chunk; each chunk retains sequential8.
  for offset in range(8):
   for chunk in range(nc):
    k=chunk*8+offset
    self.emit(1,a=chunk,d=chunk,x=bits(sum_values[k]) if k<n else 0)
    if k<n:self.sources.append((self.commands[-1][0],tag,'SUM_UNROUNDED_E',k))
  # One global padded tree. Wrong-tree variant first pads/reduces four quarters.
  if wrong and nc%4==0 and nc//4 & (nc//4-1):
   q=nc//4;roots=[]
   for j in range(4):
    ids=list(range(j*q,(j+1)*q))
    while len(ids)&(len(ids)-1): ids.append(nc);self.emit(0,d=nc)
    while len(ids)>1:
     nxt=[]
     for a,b in zip(ids[::2],ids[1::2]): self.emit(2,a=a,b=b,d=a);nxt.append(a)
     ids=nxt
    roots.append(ids[0])
   self.emit(2,a=roots[0],b=roots[1],d=roots[0]);self.emit(2,a=roots[2],b=roots[3],d=roots[2]);self.emit(2,a=roots[0],b=roots[2],d=0)
  else:
   stride=1
   while stride<npad:
    for k in range(0,npad,stride*2): self.emit(2,a=k,b=k+stride,d=k)
    stride*=2
  self.export(0,tag*2+1,bits(csum(sum_values)))
  self.rows.append(dict(n=n,tag=tag,cycles=self.c-start,quarter_cuts=[n*j//4 for j in range(5)]))
 def write(self,path):
  path.mkdir(parents=True,exist_ok=True)
  (path/'commands.txt').write_text(''.join(' '.join(map(str,r))+'\n' for r in self.commands))
  (path/'expected.txt').write_text(''.join(' '.join(map(str,r))+'\n' for r in self.outputs))
  (path/'source_schedule.txt').write_text(''.join(' '.join(map(str,r))+'\n' for r in self.sources))
  (path/'calendar.json').write_text(json.dumps(dict(cycles=self.c,command_count=len(self.commands),rows=self.rows,operand_rate='oneFP32/cycle with compiler-visibleRAWspacing9; operand producer must supportsample-majorSRAMreads; no fullSFU throughputqualification',latency=LAT),indent=2)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('out');a.add_argument('--wrong-tree',action='store_true');args=a.parse_args();rng=np.random.default_rng(151015);p=Program();tag=0
 for n,heads in [(128,16),(640,16),(5120,1),(8192,1)]:
  for h in range(heads):
   x=(rng.integers(-4096,4097,n).astype(np.float32)*np.exp2(rng.integers(-14,15,n)).astype(np.float32));x[0]=np.float32(-0.0);x[1]=np.float32(0.0)
   p.row(x,tag,args.wrong_tree);tag+=1
 for x in [np.full(1,np.float32(-0.0)),np.full(7,np.float32(1.00390625)),np.arange(9,dtype=np.float32),np.full(128,np.float32(-0.0)),np.arange(128,dtype=np.float32)*np.float32(2**-149),np.tile(np.array([1.00390625,2**-24,-1,0,1,-2**-24,0,0],dtype=np.float32),16)]:
  p.row(x,tag,args.wrong_tree);tag+=1
 p.write(Path(args.out))
if __name__=='__main__':main()
