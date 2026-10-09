#!/usr/bin/env python3
"""Smallest full-K exact Markov dot+join vehicle, released weights plus stress rows."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
SNAP=Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')
def rows(name,ids):
 idx=json.loads((SNAP/'model.safetensors.index.json').read_text())['weight_map']
 with open(SNAP/idx[name],'rb') as f:
  n=int.from_bytes(f.read(8),'little');h=json.loads(f.read(n))[name]
  assert h['shape']==[129280,256] and h['dtype']=='BF16',h
  off=8+n+h['data_offsets'][0]
  out=[]
  for i in ids:
   f.seek(off+i*512);out.append(np.frombuffer(f.read(512),dtype='<u2').copy())
 return np.array(out),dict(file=idx[name],header=h)
def write(p,arr):
 p.write_text(''.join(f'{int(v):0{arr.dtype.itemsize*2}x}\n' for v in arr))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 import hdc_golden_v41 as G
 G.set_arith('chunk8')
 rowids=[0,1,31,1000,21946,32319,32320,129279]*5
 tokens=[21946,0,129279,7,1001]*8
 w,wh=rows('mtp.2.markov_head.head.weight',rowids);x,xh=rows('mtp.2.markov_head.embed.weight',tokens)
 rng=np.random.default_rng(20261008)
 # Eight stress rows include mixed signs/magnitudes, ties/cancellation and zeros.
 ws=rng.integers(0,65536,(8,256),dtype=np.uint16);xs=rng.integers(0,65536,(8,256),dtype=np.uint16)
 ws=(ws&np.uint16(0x807f))|np.uint16(0x3f00);xs=(xs&np.uint16(0x807f))|np.uint16(0x3e80)
 ws[0]=0;xs[1]=0;ws[2,1::2]^=np.uint16(0x8000)
 w=np.concatenate([w,ws]);x=np.concatenate([x,xs]);
 wf=(w.astype(np.uint32)<<16).view(np.float32);xf=(x.astype(np.uint32)<<16).view(np.float32)
 mk=G.csum(G.mul(wf,xf))
 head=np.asarray(rng.uniform(-4,4,48),dtype=np.float32);gold=G.add(head,mk)
 for name,arr in [('w',w),('x',x)]:
  (a.out/(name+'.hex')).write_text(''.join(f'{sum(int(row[16*b+l])<<(16*l) for l in range(16)):064x}\n' for row in arr for b in range(16)))
 write(a.out/'head.hex',head.view(np.uint32));write(a.out/'gold.hex',gold.view(np.uint32))
 src=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/test/dsrom_markov_20261008/tb_markov_row.sv']
 results=[]
 for mutant in [0,1]:
  exe=a.out/f'bench_{mutant}.vvp'
  subprocess.run(['iverilog','-g2012','-s','tb_markov_row',f'-Ptb_markov_row.MUTANT={mutant}','-o',str(exe),*[str(ROOT/s) for s in src]],check=True,capture_output=True)
  p=subprocess.run(['vvp',str(exe),f'+DIR={a.out}'],text=True,capture_output=True)
  (a.out/f'run_{mutant}.log').write_text(p.stdout+p.stderr)
  results.append(dict(mutant=mutant,exit=p.returncode,pass_=('PASS released256' in p.stdout),log=f'run_{mutant}.log'))
  if (mutant==0 and (p.returncode or not results[-1]['pass_'])) or (mutant and not p.returncode): raise RuntimeError(results[-1])
 rec=dict(schema='opentallas.dsrom.markov-row-exact.v1',scope='48 independent256-term row transactions;40 released pairs plus8 stress; not ROM lookup or whole-vocab integration',checkpoint=SNAP.name,headers=dict(head=wh,embed=xh),rows=rowids,tokens=tokens,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src},results=results,physical_qualified=False,adopted=False)
 (a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
