#!/usr/bin/env python3
"""One existing full-geometry native QE leaf; no runtime/full core/new math."""
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PARAMS = dict(AW=30, NW=21, BL=16, IL=8, NBMAX=192, CHUNK8=1, WEIGHT_STALL=0, QLB=272, MP=1)
SOURCES = ['rtl/hdc/v41/ot_hdc_v41_qe.sv', 'rtl/hdc/v41/ot_hdc_actquant.sv',
 'rtl/hdc/v41/ot_hdc_fp4qdq.sv', 'rtl/hdc/v41/ot_hdc_blockdot.sv',
 'rtl/hdc/v41/ot_hdc_chunk8_stack.sv', 'rtl/hdc/ot_hdc_delay.sv',
 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
 'rtl/proto/ot_fp32_add_rne_pipe.sv']

def model():
 return dict(scope='Existing full-geometry QE leaf, mode1/2/3 provider only; LINQ remains separate field actor',
  parameters=PARAMS, native_input=dict(elements_per_edge=32, bytes_per_edge=128),
  native_outputs=dict(w_data_bits=1024,w_mask_bits=32,w_addr_bits=30,
   kvb_codes_bits=256,kvb_scale_bits=8,kvb_src_addr_bits=30),
  existing_math=dict(actquant_II=1,actquant_latency=13,fp4qdq_II=1,fp4qdq_latency=8),
  adapter=dict(prefetch_scalar_words_max=6144,prefetch_payload_bits=196608,
   held_output_words_max=6144,held_output_payload_bits=196608,
   held_output_address_bits=184320,held_descriptor_bits=2048,
   requests_inflight=1,extra_read_edges='sum of actual scalar SourceIo response waits; positive before GO',
   output_waits='actual scalar VM matched visibility or CKV qualified backend visibility; never admission as ACK',
   memory_port_peak_not_measured=True,extra_physical_staging_fit=None),
  existing_uarch_basis='tools/uarch_model.py quant segmented-result/reduction model; actual leaf keeps all parameters/math unchanged',
  build=dict(admission_peak_GiB=32,workers=16,
   basis='SU-only full256 leaf measured 13.9GB frontend; QE full16 linear lanes plus existing quantizers, conservative32GiB admission estimate, not cap',
   no_time_AS_memory_file_caps=True),
  new_RTL=False,full_token_or_clock_or_rate_qualified=False,
  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 m=model()
 if a.model:print(json.dumps(m,indent=2,sort_keys=True));return 0
 if not a.out:raise ValueError('--out required')
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise RuntimeError('clean source required')
 a.out.mkdir(parents=True,exist_ok=False)
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';obj=a.out/'obj'
 cmd=[str(tool),'--cc','--top-module','ot_hdc_v41_qe','--prefix','VDsromQeQuant',
  '--Mdir',str(obj),'--output-split','20000','--output-split-cfuncs','200','-Wno-fatal','-CFLAGS','-O0']
 cmd += [f'-G{k}={v}' for k,v in PARAMS.items()]+[str(ROOT/p) for p in SOURCES]
 r=dict(model=m,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  supervisor_pid=os.getpid(),verilator_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
  verilator_version=subprocess.check_output([str(tool),'--version'],text=True).strip(),stages=[],commands=[cmd])
 rc=1
 try:
  for name,command in [('frontend',cmd),('archive',['make','-C',str(obj),'-f','VDsromQeQuant.mk','-j16','OPT_FAST=-O0','OPT_SLOW=-O0','VDsromQeQuant__ALL.a'])]:
   if name=='archive':r['commands'].append(command)
   t=time.monotonic()
   with (a.out/(name+'.log')).open('w') as log:
    proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    r[name+'_pid']=proc.pid;(a.out/'start.json').write_text(json.dumps(r,indent=2)+'\n');rc=proc.wait()
   r['stages'].append(dict(name=name,exit=rc,wall_seconds=time.monotonic()-t))
   if rc:break
  if not rc:r['artifacts']={f:dict(bytes=(obj/f).stat().st_size,sha256=hashlib.sha256((obj/f).read_bytes()).hexdigest()) for f in ['VDsromQeQuant.h','VDsromQeQuant__ALL.a','VDsromQeQuant__verFiles.dat','VDsromQeQuant.mk','VDsromQeQuant_classes.mk']}
 finally:
  r['exit']=rc;r['verdict']='PASS_NATIVE_QE_ARCHIVE_ONLY' if not rc else 'FAIL_PRESERVED'
  (a.out/'terminal.json').write_text(json.dumps(r,indent=2)+'\n')
 return rc
if __name__=='__main__':raise SystemExit(main())
