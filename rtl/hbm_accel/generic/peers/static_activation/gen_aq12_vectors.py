#!/usr/bin/env python3
"""External stimuli/answers from the unchanged released math utility; no RTL math oracle."""
import argparse, hashlib, importlib.util, json, pathlib, sys
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',type=pathlib.Path,required=True);p.add_argument('--golden-tools',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 sys.path.insert(0,str(a.golden_tools));import hdc_golden_v41 as G
 raw=np.array([int(x,16) for x in a.raw.read_text().split()],dtype=np.uint32)
 assert raw.size==40960
 rng=np.random.default_rng(20261015)
 regenerated=np.concatenate([(rng.standard_normal(5120)*(.1*(n+1))).astype(np.float32) for n in range(8)]).view(np.uint32)
 assert np.array_equal(raw,regenerated),'raw SeedX artifact differs from exact released utility generation'
 cases=[(x.copy(),False,'native') for x in raw.reshape(-1,32)]
 def add(x,label):
  b=np.array(x,dtype=np.float32).view(np.uint32).copy();cases.append((b,bool(np.any((b>>23&255)==255)),label))
 add(np.zeros(32),'zero');add(np.array([0.,-0.]*16),'signed_zero')
 for s in range(-120,121,6):add(np.ldexp(np.arange(-16,16,dtype=np.float32),s),'power_sweep')
 for b in [1,0x7fffff,0x800000,0x38d1b716,0x38d1b717,0x38d1b718,0x7f7fffff]:
  x=np.full(32,np.array(b,dtype=np.uint32).view(np.float32),dtype=np.float32);x[1::2]=-x[1::2];add(x,'floor_subnormal_max')
 values=G.E4M3[:127]
 for start in range(0,126,15):
  x=np.zeros(32,dtype=np.float32);x[0]=448.
  for j in range(15):
   i=(start+j)%126;v=(values[i]+values[i+1])*.5;x[j+1]=v;x[j+16]=-v
  for s in [-8,0,8]:add(np.ldexp(x,s),'exact_RNE_midpoints')
 rng=np.random.default_rng(50217)
 for _ in range(256):
  b=rng.integers(0,2**32,size=32,dtype=np.uint32);b=np.where((b>>23&255)==255,b&np.uint32(0xff7fffff),b).astype(np.uint32);add(b.view(np.float32),'finite_bits')
 for b in [0x7f800000,0xff800000,0x7fc12345,0xffc12345,0x7f800001,0xff800001]:
  for j in [0,7,16,31]:
   x=np.linspace(-1,1,32,dtype=np.float32).view(np.uint32);x[j]=b;cases.append((x,True,'nonfinite'))
 if len(cases)%2:add(np.zeros(32),'padding')
 code={int(np.array(v,np.float64).view(np.uint64)):i for i,v in enumerate(G.E4M3) if np.isfinite(v)}
 # The published quant_fp8 model returns exact E4M3 numerical values. Invert
 # its public table, preserving signed zero, to obtain the raw eight-bit ABI.
 xs=[];qs=[];es=[];ys=[];fs=[];labels={}
 with np.errstate(over='ignore',invalid='ignore',under='ignore'):
  for b,nf,label in cases:
   labels[label]=labels.get(label,0)+1;xs.append(sum(int(w)<<(32*i) for i,w in enumerate(b)));fs.append(int(nf))
   if nf:qs.append(0);es.append(0);ys.append(0);continue
   x=b.view(np.float32);q,e=G.quant_fp8(x);y=G.bits(G.qdq_fp8(x))>>16
   qc=[code[int(np.array(v,np.float64).view(np.uint64))] for v in q]
   qs.append(sum(c<<(8*i) for i,c in enumerate(qc)));es.append(int(e[0])&1023);ys.append(sum(int(w)<<(16*i) for i,w in enumerate(y)))
 a.out.mkdir(parents=True,exist_ok=True)
 for name,data,width in [('x',xs,256),('q',qs,64),('e',es,3),('y',ys,128),('fault',fs,1)]:
  (a.out/(name+'.hex')).write_text(''.join(f'{v:0{width}x}\n' for v in data))
 sources=[a.raw,a.golden_tools/'hdc_golden.py',a.golden_tools/'hdc_golden_v41.py']
 receipt={'blocks':len(cases),'native_blocks':1280,'native_shape':[8,5120],'native_issue_edges_two_roots':640,'labels':labels,'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest(),'SeedX_recreated_byte_identical':True,'golden':'actual hdc_golden_v41.quant_fp8 + publicE4M3 table inverse, qdq_fp8 for y; nonfinite onlyfault defined','source_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in sources}}
 (a.out/'vectors.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
