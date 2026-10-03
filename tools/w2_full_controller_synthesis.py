#!/usr/bin/env python3
"""Uncapped exact-full-source SS synthesis; no P&R or simulator launch."""
import argparse,datetime,hashlib,json,os,resource,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
TARGET='w2_full219_pc7_ss'
TOP='ot_w2_nc6_protected_completion_reset_quarantine'
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():raise SystemExit('dirty tracked source')
 prior=json.loads((ROOT/'results/uarch/w2_full_controller_physical_context_20261003/model.json').read_text())
 for n,h in prior['source_sha256'].items():
  if digest(ROOT/n)!=h:raise SystemExit('source mismatch '+n)
 def available():return int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
 # User-reported prospective806GB constructor plus32GiB host reserve; admission only, no cgroup/process cap.
 reserve=806_000_000_000+32*1024**3
 headroom=available();disk=os.statvfs(out);diskfree=disk.f_bavail*disk.f_frsize
 if headroom<=reserve:raise SystemExit('insufficient measured capacity alongside prospective constructor')
 for r in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE]:resource.setrlimit(r,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 cmd=['docker','run','--rm','--name','hubble-w2-full219-ss-20261003-r1','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{ROOT}:/src:ro','-v',f'{out}:/work','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec make DESIGN_CONFIG=/src/physical/w2_full_controller_synthesis_20261003/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 /work/results/asap7/w2_full219_pc7_ss/base/1_2_yosys.v']
 receipt=dict(schema='w2.full219.source-synthesis.v1',UTC=stamp(),source_commit=commit,source_sha256=prior['source_sha256'],parameters={**prior['parameters'],'PC_ID':7},top=TOP,cmd=cmd,supervisor_PID=os.getpid(),memory_available_B=headroom,prospective_constructor_and_host_reserve_B=reserve,available_disk_B=diskfree,limits='No wall/CPU/AS/file/cgroup memory caps; NUM_CORES16 is parallelism only',all_top_ports_exposed=True,blackboxes=False,pruned_proxy=False,scope='SS source technology mapping; NOT P&R/SSFF closure/function equivalence/service rate/token qualification')
 (out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n');t=time.monotonic()
 with (out/'synthesis.log').open('w') as log:
  child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);receipt['docker_client_PID']=child.pid;(out/'start.json').write_text(json.dumps(receipt,indent=2)+'\n');rc=child.wait()
 receipt.update(terminal_UTC=stamp(),exit_code=rc,wall_s=time.monotonic()-t,status='MAPPED_SOURCE_AVAILABLE_CENSUS_PENDING' if rc==0 else 'SOURCE_SYNTHESIS_FAIL',runtime=False,PnR=False)
 (out/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(rc)
if __name__=='__main__':main()
