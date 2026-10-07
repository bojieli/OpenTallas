#!/usr/bin/env python3
"""Changed SFU64/provider/reverse-ACK gate. No full-parent job or repeated child gate.
Uses unchanged Carson vectors and actual protected shared provider. EPYC NVMe only,
fresh CPU/RAM/disk before/after unchanged guard; no waiter or retry.
"""
import argparse,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOP='tb_hbm_integrated_sfu_provider_join'
BASE='rtl/hbm_accel/integrated_20261006/'
VECTOR='results/physical/hbm_die_abstracts_20261006/compute/enabled_r1/vectors'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sources(native=False):
 export=json.loads((ROOT/'results/uarch/hbm_integrated_sfu_provider_join_20261006/namespace_export.json').read_text())
 paths=list(export['files'])+[
  'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
  'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
  'physical/hbm_die_abstracts_20261006/compute/ot_hbm_compute_frame1024.sv',
  'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv',
  BASE+'ot_hbm_integrated_stage_join.sv',BASE+'ot_hbm_integrated_sfu_c12_stage.sv',
  BASE+'ot_hbm_integrated_sfu_provider_join.sv',BASE+TOP+'.sv',
  'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv',
  'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv']
 if native:
  import runpy
  paths+=runpy.run_path(str(ROOT/'physical/hbm_die_abstracts_20261006/memory_control/run_vm_sfu_warm_join.py'))['SOURCES'][:-1]
 return list(dict.fromkeys(paths))

def capacity(out,phase,need=32):
 def cpu():
  v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]));return sum(v[:8]),v[3]+v[4]
 t,i=cpu();time.sleep(.5);u,j=cpu();idle=(j-i)/(u-t)*os.cpu_count()
 m={k:v for k,v in (s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())}
 st=os.statvfs(out)
 d=dict(phase=phase,host=socket.gethostname(),load1=os.getloadavg()[0],cpus=os.cpu_count(),idle_cpus=idle,
        available_gib=int(m['MemAvailable'].split()[0])/1024**2,disk_free_gib=st.f_bavail*st.f_frsize/2**30)
 d['fit']=d['load1']<128 and idle>=16 and d['available_gib']>=100+need and d['disk_free_gib']>=12
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
 return d

def main():
 global TOP
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--reuse-native-models',type=Path);ap.add_argument('--reuse-vm-model',type=Path);ap.add_argument('--native-vm',action='store_true');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--admitted',action='store_true');a=ap.parse_args()
 if a.native_vm:TOP='tb_hbm_integrated_sfu_native_vm_join'
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 pins={p:sha(ROOT/p) for p in sources(a.native_vm)+[VECTOR+'/sfu_req.mem',VECTOR+'/sfu_exp.mem',
  BASE+'sfu_c12_selected/hierarchical.vlt','tools/hbm_integrated_sfu_provider_gate.py']}
 m=dict(top=TOP,sources=pins,ENABLE=1,LANES=64,contexts=[1048575,8191],seed=20261006,
        expected='actual64-lane golden through native32SRAM root' if a.native_vm else 'unchanged Carson64-lane golden; all8 opcodes in10 cases',
        native_vm_publication=a.native_vm,
        negatives=['TOKEN17 joint completion refusal','warm held completion drain'] if a.native_vm else ['checked readback mismatch','TOKEN17 publication mismatch','real W6 landing two-bit UE'],
        required_memory_gib=96 if a.native_vm else 32,threads=16,disk_inventory_gib=12,
        inventory_basis='native r3 measured frontend74.6GiB;96GiB capacity reservation, completed native models reused' if a.native_vm else 'actual SFU hierarchical admission_inventory.json plus1440FF finite landing/controller',
        whole_parent_qualified=False,physical_qualified=False)
 manifest=out/'prepared.json'
 if manifest.exists() and json.loads(manifest.read_text())!=m:raise ValueError('Pinned changed source: choose new attempt, retain old failure')
 write(manifest,m)
 if a.prepare_only:print('SOURCE_AND_GOLDEN_PREPARED; no compiler/runtime');return 0
 if os.cpu_count()<128 or not str(out).startswith(('/srv/opentallas-scratch2/','/srv/opentallas-scratch/')):
  ap.error('EPYC NVMe only; no local/AGI fallback')
 if (out/'terminal.json').exists():ap.error('Terminal exists; no repeat')
 need=m['required_memory_gib']
 c=capacity(out,'post_guard' if a.admitted else 'pre_guard',need)
 if not c['fit']:write(out/'not_started.json',dict(reason='CURRENT_CAPACITY_BLOCKED',capacity=c));return 75
 if not a.admitted:
  return subprocess.call(['/srv/opentallas-scratch/admit.sh',str(need),'--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted',*(['--native-vm'] if a.native_vm else []),*(['--reuse-native-models',str(a.reuse_native_models)] if a.reuse_native_models else []),*(['--reuse-vm-model',str(a.reuse_vm_model)] if a.reuse_vm_model else [])])
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 version=subprocess.check_output([str(tool),'--version'],text=True).strip()
 if 'Verilator 5.050' not in version:raise ValueError('Pinned5.050 required')
 cfg=ROOT/(BASE+'sfu_c12_selected/hierarchical.vlt')
 if a.native_vm:
  if not a.reuse_native_models or not a.reuse_vm_model:ap.error('Native changed fixture requires completed SFU and VM models; no whole flat build')
  import shutil
  cfg=out/'hierarchical.vlt'
  cfg.write_text('`verilator_config\nhier_block -module "ot_hbm_selected_c12__ot_hbm_sfu_result_c12"\nhier_block -module "ot_hbm_die_vm_sfu_publication_root"\n')
  import runpy
  child_dependencies=set(runpy.run_path(str(ROOT/'physical/hbm_die_abstracts_20261006/memory_control/run_vm_sfu_warm_join.py'))['SOURCES'][:-1])
  child_dependencies.update(json.loads((ROOT/'results/uarch/hbm_integrated_sfu_provider_join_20261006/namespace_export.json').read_text())['files'])
  child_dependencies.update(['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','physical/hbm_die_abstracts_20261006/compute/ot_hbm_compute_frame1024.sv','rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv'])
  copied=[]
  for previous,name in [(a.reuse_native_models,'Vot_hbm_selected_c12___05Fot_hbm_sfu_result_c12'),(a.reuse_vm_model,'Vot_hbm_die_vm_sfu_publication_root_2')]:
   previous=previous.resolve()
   old=json.loads((previous/'prepared.json').read_text())
   prior=old.get('source_sha256',old.get('sources',{}))
   # Every shared dependency except changed testbench/compiler configuration must match.
   for path,value in prior.items():
    if path in child_dependencies and path in pins and pins[path]!=value:
     raise ValueError('Changed RTL cannot reuse model: '+path)
   child=previous/'obj'/name
   if not list(child.glob('*.a')):raise ValueError('Missing completed child '+str(child))
   shutil.copytree(child,out/'obj'/name,dirs_exist_ok=True)
   copied.append(dict(previous=str(previous),model=name,library_sha256={p.name:sha(p) for p in child.glob('*.a')}))
  write(out/'reuse.json',dict(models=copied,child_RTL_unchanged=True,parent_always_rebuilt=True,original_objects_preserved=True))
 cmd=[str(tool),'--binary','--timing','--hierarchical','-O2','-Wno-fatal','-Wno-WIDTH',
      '--top-module',TOP,'-Mdir',str(out/'obj'),'--build-jobs','16','--verilate-jobs','1',
      '--hierarchical-threads','1','--unroll-count','4',
      str(cfg)]+[str(ROOT/p) for p in sources(a.native_vm)]
 write(out/'command.json',dict(command=cmd,tool_version=version))
 with (out/'compile.log').open('x') as log:
  rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/'compile.resources'),*cmd],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 if rc:write(out/'terminal.json',dict(status='COMPILE_FAIL',returncode=rc));return rc
 if not capacity(out,'before_changed_numeric',need)['fit']:
  write(out/'pending.json',dict(reason='CPU_FIT_BLOCKED',binary=str(out/'obj'/('V'+TOP))));return 75
 with (out/'run.log').open('x') as log:
  rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/'run.resources'),str(out/'obj'/('V'+TOP)),'+DIR='+str(ROOT/VECTOR)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 passed=rc==0 and ('SFU_NATIVE_VM_JOIN_PASS' if a.native_vm else 'SFU_PROVIDER_JOIN_PASS') in (out/'run.log').read_text()
 write(out/'terminal.json',dict(status='PASS' if passed else 'FAIL',returncode=rc,source_sha256=pins,
       full_parent_qualified=False,SSFF_qualified=False))
 return 0 if passed else (rc or 2)
if __name__=='__main__':raise SystemExit(main())
