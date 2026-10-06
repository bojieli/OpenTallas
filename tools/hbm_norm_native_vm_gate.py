#!/usr/bin/env python3
"""One changed norm/vectorVM/native SRAM join; no passing component replay."""
import argparse,hashlib,json,os,runpy,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='rtl/hbm_accel/integrated_20261006/'
TOP='tb_hbm_integrated_norm_native_vm_join'
def sources():
 norm=json.loads((ROOT/'results/rtl/hbm_norm_vm_boundary_20261006/connected.json').read_text())['engine_21_sha256']
 backend=runpy.run_path(str(ROOT/'physical/hbm_die_abstracts_20261006/memory_control/run_vm_sfu_warm_join.py'))['SOURCES'][:-1]
 return list(dict.fromkeys(list(norm)+backend+['rtl/hdc/ot_hdc_cg.sv',BASE+'codex_norm_boundary/ot_hbm_integrated_norm_stream.sv',BASE+'codex_norm_boundary/ot_hbm_integrated_norm_vm.sv',BASE+'ot_hbm_integrated_stage_join.sv',BASE+'ot_hbm_integrated_norm_stage.sv',BASE+'ot_hbm_norm_native_vm_adapter.sv','rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv','rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv',BASE+TOP+'.sv']))
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def capacity(out):
 def sample():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=sample();time.sleep(.5);b=sample();d=[y-x for x,y in zip(a,b)]
 idle=os.cpu_count()*(d[3]+d[4])/sum(d);load=os.getloadavg()[0]
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/1024**2
 v=os.statvfs(out);disk=v.f_bavail*v.f_frsize/2**30
 rec=dict(load1=load,idle_CPU=idle,MemAvailable_GiB=mem,NVMe_free_GiB=disk,fit=load<128 and idle>=4 and mem>=196 and disk>=12)
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 return rec

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--admitted',action='store_true');a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 paths=sources();pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in paths}
 vec=ROOT/'results/rtl/hbm_integrated_sfu_provider_join_20261006/norm_selected_join/vectors'
 rec=dict(source_sha256=pins,N=32,D=64,seed=20261006,golden='hdc_golden_v41.rmsnorm_bf16 independent exact binary32/rounding',reservation_GiB=96,threads=4,basis='actual prior32SRAM enclosing frontend observed74.6GiB;96GiB capacity reservation plus100GiB reserve, no process/wall/file limits',full_parent_qualified=False,SSFF_qualified=False)
 dump(out/'prepared.json',rec)
 if a.prepare_only:return 0
 if socket.gethostname()!='climbing-locust' or not str(out).startswith('/srv/opentallas-scratch2/'):p.error('E2 NVMe only; no localhost/AGI heavy fallback')
 if (out/'terminal.json').exists():p.error('Terminal present; no replay')
 cap=capacity(out)
 if not cap['fit']:dump(out/'not_started.json',cap);return 75
 if not a.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','96','--','python3',str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 cfg=out/'hierarchical.vlt';cfg.write_text('`verilator_config\nhier_block -module "ot_hbm_die_vm_sfu_publication_root"\nhier_block -module "ot_dsrom_su_norm"\n')
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 cmd=[str(tool),'--binary','--timing','--hierarchical','-O1','-Wno-fatal','-Wno-WIDTH','--top-module',TOP,'--build-jobs','4','--verilate-jobs','1','--hierarchical-threads','1','--unroll-count','4','-fno-dfg','-Mdir',str(out/'obj'),str(cfg),*[str(ROOT/s) for s in paths]]
 dump(out/'command.json',dict(command=cmd))
 with (out/'compile.log').open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/'compile.resources'),*cmd],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 if rc:dump(out/'terminal.json',dict(status='COMPILE_FAIL',returncode=rc,**rec));return rc
 if not capacity(out)['fit']:dump(out/'pending.json',dict(binary=str(out/'obj'/('V'+TOP)),reason='before_runtime_fit_blocked'));return 75
 with (out/'run.log').open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/'run.resources'),str(out/'obj'/('V'+TOP)),'+DIR='+str(vec)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 passed=rc==0 and 'NORM_NATIVE_VM_JOIN_PASS' in (out/'run.log').read_text()
 dump(out/'terminal.json',dict(status='PASS' if passed else 'FAIL',returncode=rc,**rec));return 0 if passed else rc or 1
if __name__=='__main__':raise SystemExit(main())
