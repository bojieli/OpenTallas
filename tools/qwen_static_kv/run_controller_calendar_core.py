#!/usr/bin/env python3
"""Core833ps controller: fixed reservations and independent physical JEDEC checks."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from controller_calendar_image import Run,compile_image
ROOT=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('out',type=Path);a.add_argument('--binary',type=Path);a.add_argument('--target',type=Path,help='actual compiled target6..9 hex; use PC0 low16/high16 words');a.add_argument('--mutant',type=int,default=0,choices=(0,1,2));a.add_argument('--legacy-miter',action='store_true');a.add_argument('--miter-mutant',type=int,default=0);a.add_argument('--timing-mutant',type=int,default=0,choices=(0,1));x=a.parse_args();out=x.out.resolve();out.mkdir(parents=True,exist_ok=True)
runs=[Run(10,command=(256<<20)|1,layer_row=True),Run(80,command=(1<<31)|1),Run(150,256,8,3,mask=1),Run(600,command=(512<<33)|(768<<20)|1,layer_row=True),Run(700,command=(1<<31)|1),Run(1000,256,8,6,mask=1)]
if x.target:
 w=[int(t,16)for t in x.target.read_text().splitlines()][:32]
 if len(w)!=32:raise ValueError('target needs at least32 controller words')
 packed=[lo+(hi<<64)for lo,hi in zip(w[:16],w[16:])]
 runs=[]
 for v in packed:
  if not v:continue
  runs.append(Run((v&65535)+2,(v>>16)&1023,((v>>26)&15)+1,(v>>30)&255,
                  command=(v>>38)&((1<<43)-1),mask=(v>>81)&7,
                  layer_row=bool(v&(1<<84)),static_read=bool(v&(1<<85)),
                  context_mode=(v>>86)&3,context_descriptor=bool(v&(1<<88))))
 z=compile_image(runs,deadline=1800)
 if z['words']!=packed:raise ValueError('controller target decode/reencode differs')
else:z=compile_image(runs,deadline=1800)

expected_rd=[0]*4096
for edge,e in z['events'].items():expected_rd[edge]=int(e['mask']==1)
(out/'expected_rd.hex').write_text(''.join(f'{e:x}\n'for e in expected_rd))
(out/'image.hex').write_text(''.join(f'{w:032x}\n'for w in z['words']))
files=[f'rtl/qwen_sys/static_kv_20261014/{n}.sv'for n in ['qkd_controller_hbm_calendar','qkd_static_kv_return_calendar','qkd_ctrl_pc_host_static','qkd_ctrl_pc_host_static_core','qkd_ctrl_pc_children','ot_qkd_static_ctrl_pc_emb','ot_qkd_static_kv_timing','ot_qkd_static_emb_cdc','qkd_static_kv_write_observer']]+['rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv','rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv','rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv','rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv','rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/test/qwen_static_kv/tb_controller_calendar_core.sv','rtl/test/qwen_static_kv/ot_qkd_static_kv_timing_legacy_ref.sv']
v=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
obj=out/'obj';cmd=[v,'--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_controller_calendar_core',f'-GMUT={x.mutant}',f'-GTIMING_MUT={x.timing_mutant}',f'-GDEFAULT_MITER={int(x.legacy_miter)}',f'-GMITER_MUT={x.miter_mutant}','--Mdir',str(obj)]+[str(ROOT/f)for f in files]
if not x.binary:
 with(out/'build.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=x.binary.resolve()if x.binary else obj/'Vtb_controller_calendar_core'
results=[]
for jit in(0,8,16):
 p=subprocess.run([str(binary),f'+IMAGE={out}/image.hex',f'+JITTER={jit}',f'+EXPECT={out}/expected_rd.hex'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/f'run{jit}.log').write_text(p.stdout);results.append(dict(jitter=jit,exit=p.returncode,output=p.stdout[-1000:]))
 if p.returncode:break
receipt=dict(compiled_target=None if x.target is None else str(x.target),controller_ps=1024.0 if x.legacy_miter else 833.0,legacy_miter=x.legacy_miter, physical_checks='independent PHY-pin tRCD/tRP/tRAS/tRTP/tCCDL/tRRDS/tRRDL/tFAW/tRFCpb', scope='actual PROFILE0/ELASTIC1 controller; compiler fixed K256+V256; PHY only modeled; 36 persistent layer rows/epochs; no host writes/all128PC/native die',source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},results=results,image_sha256=hashlib.sha256((out/'image.hex').read_bytes()).hexdigest(),compiler_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in ('tools/qwen_static_kv/controller_calendar_image.py','tools/qwen_static_kv/run_controller_calendar_core.py')},binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),native_full_layer=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if x.miter_mutant:
 assert x.legacy_miter and results[0]['exit']!=0 and 'LEGACY_MITER' in results[0]['output'],results
 raise SystemExit(0)
if x.timing_mutant:
 assert results[0]['exit']!=0 and 'PHYSICAL_MIN' in results[0]['output'],results
 raise SystemExit(0)
if x.mutant:
 assert results[0]["exit"]!=0 and "FAIL native calendar"in results[0]["output"],results
 raise SystemExit(1)
assert all(r["exit"]==0 for r in results),results[-1]["output"]
