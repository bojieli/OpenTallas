#!/usr/bin/env python3
"""Fleet-only real DCAL predicates and complete logical successor receipts."""
import hashlib,json,subprocess
from pathlib import Path
from fault_bench import generate

root=Path.cwd();out=root/'out';out.mkdir(exist_ok=True)
version=subprocess.check_output(['verilator','--version'],text=True).strip()
assert '5.050' in version,version
subprocess.run(['python3','tools/kv_fault_dcal_successor.py','--dir','.', '--exact-pins','exact_fault_native_pins.json.gz','--out','out/successor.json'],check=True)
c=json.loads((out/'successor.json').read_text())
summary={'qualified_release':False,'verilator':version,'tests':{},'input_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ('rtl','tools') for p in (root/d).iterdir() if p.is_file()}}
for mode in ('none','missing_dcal','wrong_clear'):
 d=out/mode;d.mkdir(exist_ok=True)
 rtl=(root/'rtl/qkd_d2d_cal_seq_bootcfg.sv').read_text()
 if mode=='wrong_clear':
  old='fault <= fault || s_fault || n_col || n_run || n_stale || n_early;'
  assert rtl.count(old)==1
  rtl=rtl.replace(old,"fault <= (halt_q || reload_q) ? 1'b0 : (fault || s_fault || n_col || n_run || n_stale || n_early);")
 (d/'dcal.sv').write_text(rtl)
 cmd=['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','--build-jobs','2','-I'+str(root/'rtl'),'--Mdir','obj']
 if mode=='missing_dcal':cmd+=['-GOMIT=1']
 cmd += [str(root/'rtl/ot_qwen_d2d_cal_seq.sv'),str(root/'rtl/ot_qwen_d2d_cal_seq_dies_mu.sv'),str(d/'dcal.sv'),str(root/'rtl/qkd_astk_phys.sv'),str(root/'tools/tb_dcal_fault.sv')]
 b=subprocess.run(cmd,cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(d/'build.log').write_text(b.stdout)
 if b.returncode:raise RuntimeError(b.stdout[-3000:])
 r=subprocess.run(['./obj/Vtb'],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(d/'run.log').write_text(r.stdout)
 expected='DCAL_REAL_PREDICATES_PASS' if mode=='none' else 'DCAL_FOLD_MISMATCH' if mode=='missing_dcal' else 'DCAL_STICKY_CLEAR_MISMATCH'
 passed=(r.returncode==0 if mode=='none' else r.returncode!=0) and expected in r.stdout
 summary['tests'][mode]={'pass':passed,'exit_code':r.returncode,'witness':r.stdout};print(mode,r.stdout,flush=True)
 if not passed:raise RuntimeError('BAD_VERDICT '+mode)
d=out/'all357';generate(c,d,candidate_mode=True)
b=subprocess.run(['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','--build-jobs','2','--Mdir','obj',str(root/'rtl/qkd_astk_phys.sv'),'tb.sv'],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(d/'build.log').write_text(b.stdout)
if b.returncode:raise RuntimeError(b.stdout[-3000:])
r=subprocess.run(['./obj/Vtb'],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(d/'run.log').write_text(r.stdout)
assert r.returncode==0 and 'FAULT_PLANE_PASS' in r.stdout,r.stdout
summary['tests']['all357']={'pass':True,'witness':r.stdout}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('DCAL_SUCCESSOR_FLEET_PASS',flush=True)
