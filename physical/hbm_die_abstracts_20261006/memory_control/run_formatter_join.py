#!/usr/bin/env python3
"""One changed formatter/gather join seed and high-token transport negative on E2 or owner-authorized AGI.
Small single-core Verilator gate; fresh CPU/RAM/NVMe fit, original guard.
Never run locally; never queue behind a RAM-only guard on an overloaded host.
"""
import argparse,hashlib,json,os,subprocess,time,runpy
from pathlib import Path
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv',
 'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv',
 'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_bridge.sv',
 'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_owner.sv',
 'rtl/hbm_accel/index/ot_hbm_accel_index_w15_planemajor_formatter.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_integrated_formatter_provider.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/tb_hbm_formatter_provider_join.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capacity(scratch):
 def sample():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=sample();time.sleep(1);b=sample();d=[y-x for x,y in zip(a,b)]
 nc=os.cpu_count();idle=nc*(d[3]+d[4])/sum(d);load=os.getloadavg()[0]
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 v=os.statvfs(scratch)
 core=Path('/srv/opentallas-scratch/admit_core.py')
 # Read the unmodified guard implementation's own small-host reserve rule.
 # __main__ is not invoked, so this read-only probe cannot admit/queue a job.
 policy=runpy.run_path(str(core))
 reserve=policy['RESERVE'];recent=policy['RECENT'];ramp_seconds=policy['RAMP_S']
 try:ramping=sum(r[1] for r in json.loads(recent.read_text()) if time.time()-r[0]<ramp_seconds)
 except (FileNotFoundError,ValueError):ramping=0
 return dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),CPU_count=nc,load1=load,idle_CPU=idle,MemAvailable_bytes=mem,NVMe_free_bytes=v.f_bavail*v.f_frsize,CPU_fit=idle>=1 and load+1<=nc,guard_core_sha256=sha(core),guard_reserve_bytes=reserve,guard_ramping_bytes=ramping)
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admitted',action='store_true');a=ap.parse_args()
 ips=subprocess.check_output(['hostname','-I'],text=True).split()
 if not set(ips)&{'5.199.165.105','155.103.253.226'}:raise SystemExit('E2 or owner-authorized AGI only; refusing local simulation')
 guard=Path('/srv/opentallas-scratch/admit.sh');pins={s:sha(a.root/s) for s in SOURCES};cap=capacity(a.root)
 if not a.admitted:
  a.out.mkdir(parents=True,exist_ok=False)
  rec={'status':'CAPACITY_REFUSED','capacity':cap,'guard_sha256':sha(guard),'source_sha256':pins,'requested_CPU':1,'reservation_GiB':4,'basis':'one-core Verilator build/runtime, existing protected gather owner plus formatter, finite1MiB provider fixture; 4GiB capacity reservation, no process limits','whole_VM_parent_qualified':False}
  dump(a.out/'launch.json',rec)
  if not cap['CPU_fit'] or cap['MemAvailable_bytes']<cap['guard_reserve_bytes']+cap['guard_ramping_bytes']+4*1024**3 or cap['NVMe_free_bytes']<2*1024**3:return 66
  cmd=[str(guard),'4','--','python3',str(Path(__file__).resolve()),'--root',str(a.root),'--out',str(a.out),'--admitted']
  rec['status']='FRESH_CPU_FIT_BEFORE_GUARD';rec['command']=cmd;dump(a.out/'launch.json',rec)
  result=subprocess.call(cmd);rec['exit']=result;rec['guard_unchanged']=sha(guard)==rec['guard_sha256'] and sha(Path('/srv/opentallas-scratch/admit_core.py'))==cap['guard_core_sha256'];dump(a.out/'launch.json',rec);return result
 launch=json.loads((a.out/'launch.json').read_text());dump(a.out/'post_guard_capacity.json',cap)
 if pins!=launch['source_sha256'] or sha(guard)!=launch['guard_sha256'] or cap['guard_core_sha256']!=launch['capacity']['guard_core_sha256']:return 65
 if not cap['CPU_fit']:return 66
 # Tool package is extracted privately; no global package or peer tool mutation.
 tool=a.out/'tool';tool.mkdir()
 with (a.out/'tool.log').open('w') as log:
  ret=subprocess.call(['apt-get','download','verilator'],cwd=tool,stdout=log,stderr=subprocess.STDOUT)
  if ret:return ret
  deb=list(tool.glob('verilator*.deb'))
  if len(deb)!=1:return 65
  ret=subprocess.call(['dpkg-deb','-x',str(deb[0]),str(tool/'unpacked')],stdout=log,stderr=subprocess.STDOUT)
  if ret:return ret
 env=os.environ.copy();env['VERILATOR_ROOT']=str(tool/'unpacked/usr/share/verilator')
 executable=tool/'unpacked/usr/bin/verilator'
 with (a.out/'tool.version').open('w') as log:
  subprocess.check_call([str(executable),'--version'],env=env,stdout=log,stderr=subprocess.STDOUT)
 cmd=[str(executable),'--binary','--timing','--threads','1','-j','1','-Wno-fatal','--top-module','tb_hbm_formatter_provider_join','--Mdir',str(a.out/'build'),*[str(a.root/s) for s in SOURCES]]
 with (a.out/'compile.log').open('w') as log:ret=subprocess.call(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 rec={'source_sha256':pins,'compile_command':cmd,'compile_exit':ret,'cases':[],'physical_closed':False,'actual_parent_bindings_qualified':False,'private_tool_deb_sha256':sha(deb[0])}
 if ret:dump(a.out/'terminal.json',rec);return ret
 cmd=[str(a.out/'build/Vtb_hbm_formatter_provider_join')]
 with (a.out/'exact_and_token_negative.log').open('w') as log:ret=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 output=(a.out/'exact_and_token_negative.log').read_text()
 passed=ret==0 and 'PASS_FORMATTER_PROVIDER_JOIN ' in output
 rec['cases'].append(dict(name='causal_arena_exact_and_TOKEN17_negative',command=cmd,exit=ret,passed=passed));rec['verdict']='PASS' if passed else 'FAIL';dump(a.out/'terminal.json',rec)
 return 0 if passed else ret or 1
if __name__=='__main__':raise SystemExit(main())
