#!/usr/bin/env python3
"""Matched unchanged ME RTL with compact vs expanded real checkpoint weights."""
import argparse,hashlib,json,os,struct,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));os.environ['HDC_V41_ARITH']='chunk8'
import hdc_golden_v41 as G
RTL=['rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/v41/ot_hdc_actquant.sv',*[f'rtl/hdc/v41x/ot_hdc_v41x_wgt_{x}.sv' for x in ['bdot','red','mac','tile']],'rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv','rtl/chip/ot_chip_v41x_woa_fp8_decode.sv','rtl/chip/ot_chip_v41x_woa_compact_bank.sv','rtl/test/tb_chip_v41x_woa_compact_me.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(a):
 a.scratch.mkdir(parents=True,exist_ok=True);idx=json.loads((a.snapshot/'model.safetensors.index.json').read_text())['weight_map'];pins={}
 def arr(k):
  p=a.snapshot/idx[k]
  with p.open('rb') as f:n=struct.unpack('<Q',f.read(8))[0];raw=f.read(n)
  m=json.loads(raw)[k];pins[k]={'shape':m['shape'],'header_sha256':hashlib.sha256(raw).hexdigest(),'blob':p.resolve().name}
  return np.memmap(p,dtype=np.uint8,mode='r',offset=8+n+m['data_offsets'][0],shape=tuple(m['shape']))
 w=arr('layers.25.attn.wo_a.weight');s=arr('layers.25.attn.wo_a.scale');x=G.to_bf16(np.sin(np.arange(8192,dtype=np.float32)*np.float32(.03125))); y=np.zeros(2048,np.float32)
 comp=[];exp=[]
 for g in range(2):
  for r in range(a.rows):
   row=g*1024+r;codes=w[row];scale=s[row//32];dense=G.to_bf16((G.E4M3[codes]*np.exp2(np.repeat(scale.astype(np.int32)-127,32))).astype(np.float32));y[g*1024+r]=G.csum(G.mul(dense,x[g*4096:(g+1)*4096]))
   for beat in range(64):
    for c in range(8):
     cols=beat*64+np.arange(8)*8+c;raw=bytes(codes[cols])+bytes([scale[beat*2],scale[beat*2+1]])
     addr=((g*65536+r*64+beat)*8+c);comp.append(f'@{addr:x}\n{int.from_bytes(raw,"little"):020x}\n');exp.append(f'@{addr:x}\n{int.from_bytes(dense[cols].tobytes(),"little"):064x}\n')
 (a.scratch/'compact.hex').write_text(''.join(comp));(a.scratch/'expanded.hex').write_text(''.join(exp))
 for name,v in [('acc',x),('za',y)]: (a.scratch/(name+'.hex')).write_text(''.join(f'{int(b):08x}\n' for b in v.view(np.uint32)))
 exe=a.scratch/'obj'/'Vtb_chip_v41x_woa_compact_me'
 cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-O0','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--top-module','tb_chip_v41x_woa_compact_me','-Mdir',str(a.scratch/'obj'),*[str(ROOT/f) for f in RTL],'-CFLAGS','-O0','-j','4']
 subprocess.run(cmd,check=True,stdout=open(a.scratch/'build.log','w'),stderr=subprocess.STDOUT)
 arms={}
 for mode in ['expanded','compact']:
  t=time.monotonic();run=subprocess.run([str(exe),f'+DIR={a.scratch}',f'+ROWS={a.rows}']+(['+COMPACT'] if mode=='compact' else []),capture_output=True,text=True)
  (a.scratch/(mode+'.log')).write_text(run.stdout+run.stderr)
  if run.returncode:raise RuntimeError(run.stdout[-1500:]+run.stderr[-1500:])
  import re
  m=re.search(r'WOA_PASS rows_per_group=(\d+) exact_rows=(\d+) bank_reads=(\d+) cycles=(\d+)',run.stdout)
  assert m;arms[mode]=dict(zip(['rows_per_group','exact_rows','bank_reads','cycles'],map(int,m.groups())));arms[mode]['wall_seconds']=time.monotonic()-t
 assert arms['expanded']['cycles']==arms['compact']['cycles']
 d=dict(schema='opentallas.v41.woa_compact_me.v1',status='pass_local_matched_ME_not_full_layer',layer=25,activation='deterministic BF16 sin vector, not checkpoint token activation',checkpoint=pins,arms=arms,source_sha256={f:sha(ROOT/f) for f in RTL+['tools/rtl_v41_woa_compact_me.py','tools/hdc_golden_v41.py','tools/hdc_golden.py']},image_sha256={f:sha(a.scratch/f) for f in ['compact.hex','expanded.hex','acc.hex','za.hex']},contract=dict(banks=8,bits_per_bank_word=80,values_per_beat=64,read_latency_cycles=2,extra_cycles=0,bank_depth_full_rank=131072,code_scale_logical_bytes_full_rank=10485760,scale_replication='two UE8M0 bytes perbank/address; no sharedscaleport assumption',physical_macro_binding='pending; 80-bit independentbank contract only'))
 a.output.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(arms))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rows',type=int,default=16);a=p.parse_args();assert a.rows>0 and a.rows<=1024 and a.rows%16==0;main(a)
