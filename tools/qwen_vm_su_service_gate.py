#!/usr/bin/env python3
"""Replay minimum actual-bank protocol gate; two-state PASS and four-state failure remain distinct."""
import argparse,hashlib,json,subprocess,shutil,os,resource
from pathlib import Path
BOOK=Path('results/rtl/qwen_vm_su_service_gate_20261007')
BENCH=Path('rtl/test/qwen_vm_su_service_gate_20261007/tb_qwen_su_service_gate.sv')
SRC=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hdc/ot_hdc_cg.sv','physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv','rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv','rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_finite_vm_adapter.sv']
FIXTURE=Path('results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex')
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def run(a):
 root=a.root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=out/'src';src.mkdir()
 pins=json.loads((root/BOOK/'source_manifest.json').read_text())
 for p,h in pins.items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,('pinned source differs',p)
 model=json.loads((root/'results/rtl/qwen_hbm_activation_vm_realization_20261005/native_adapter_prebuild.json').read_text());assert model['functional_component_compile_allowed'] and model['macro_count']==288
 # Store measured admission context; this is a small protocol fixture, no whole-SU/array compile.
 (out/'admission.json').write_text(json.dumps(dict(load=os.getloadavg(),memory=Path('/proc/meminfo').read_text(),disk_free_bytes=shutil.disk_usage(out).free,macro_count=288,workers=2),indent=2)+'\n')
 paths=[]
 for p in SRC:
  q=src/Path(p).name;q.write_bytes((root/p).read_bytes());paths.append(str(q))
 for name,p in [('bench.sv',BENCH),('progress.sv',BOOK/'progress.sv')]:
  q=src/name;q.write_bytes((root/p).read_bytes());paths.append(str(q))
 (out/'inventory.json').write_text(json.dumps({p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in src.iterdir()},indent=2)+'\n')
 command=[a.verilator,'--binary','--timing','-j','2','--threads','1','-Wno-fatal','--top-module','tb_qwen_su_service_gate','--Mdir',str(out/'obj'),*paths]
 with (out/'build.log').open('w') as f:subprocess.run(command,stdout=f,stderr=f,check=True)
 results={}
 for n,marker in enumerate(['PASS captured_SU_conflict','FOREIGN_ACK_REJECTED native_held progress0','UNPAID_NATIVE_ADVANCE','PREMATURE_CHASE_WITH_UNPAID_FRAME']):
  p=subprocess.run([str(out/'obj/Vtb_qwen_su_service_gate'),'+FIXTURE='+str(root/FIXTURE),f'+NEGATIVE={n}'],text=True,capture_output=True,preexec_fn=no_core)
  (out/f'case{n}.log').write_text(p.stdout+p.stderr)
  assert marker in p.stdout and ((p.returncode==0)==(n==0)),(n,p.returncode)
  results[n]=dict(exit_code=p.returncode,marker=marker)
 (out/'terminal.json').write_text(json.dumps(dict(two_state_protocol=results,four_state='unqualified; preserved Icarus failures in repository evidence',full_source_integration=False),indent=2)+'\n')
 print(json.dumps(results))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--verilator',required=True);run(p.parse_args())
