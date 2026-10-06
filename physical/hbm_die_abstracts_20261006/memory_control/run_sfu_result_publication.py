#!/usr/bin/env python3
"""One changed SFU64 native VM publication join gate; no numerical child replay on E2 or owner-authorized AGI.
Small single-process Icarus gate; fresh CPU/RAM/NVMe fit, original guard.
Never run locally; never queue behind a RAM-only guard on an overloaded host.
"""
import argparse,hashlib,json,os,subprocess,time,runpy
from pathlib import Path
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv',
 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
 'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
 'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_die_vm_multicast_root.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_index_fp32_sram_adapter.sv',
 'physical/hbm_die_abstracts_20261006/integration/ot_hbm_vm_publication_parent.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_vm_sfu_result_publication.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/tb_vm_sfu_result_publication.sv']
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
  rec={'status':'CAPACITY_REFUSED','capacity':cap,'guard_sha256':sha(guard),'source_sha256':pins,'requested_CPU':1,'reservation_GiB':1,'basis':'single-process Icarus32existingSRAMs+new35W6publisher rows, finite2rowmechanism;1GiB capacity reservation, no process limits','whole_VM_parent_qualified':False}
  dump(a.out/'launch.json',rec)
  if not cap['CPU_fit'] or cap['MemAvailable_bytes']<cap['guard_reserve_bytes']+cap['guard_ramping_bytes']+1024**3 or cap['NVMe_free_bytes']<2*1024**3:return 66
  cmd=[str(guard),'1','--','python3',str(Path(__file__).resolve()),'--root',str(a.root),'--out',str(a.out),'--admitted']
  rec['status']='FRESH_CPU_FIT_BEFORE_GUARD';rec['command']=cmd;dump(a.out/'launch.json',rec)
  result=subprocess.call(cmd);rec['exit']=result;rec['guard_unchanged']=sha(guard)==rec['guard_sha256'] and sha(Path('/srv/opentallas-scratch/admit_core.py'))==cap['guard_core_sha256'];dump(a.out/'launch.json',rec);return result
 launch=json.loads((a.out/'launch.json').read_text());dump(a.out/'post_guard_capacity.json',cap)
 if pins!=launch['source_sha256'] or sha(guard)!=launch['guard_sha256'] or cap['guard_core_sha256']!=launch['capacity']['guard_core_sha256']:return 65
 if not cap['CPU_fit']:return 66
 binary=a.out/'sfu_publication.vvp';cmd=['iverilog','-g2012','-DOT_MEM_NO_INIT','-s','tb_vm_sfu_result_publication','-o',str(binary),*[str(a.root/s) for s in SOURCES]]
 with (a.out/'compile.log').open('w') as log:ret=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 rec={'source_sha256':pins,'compile_command':cmd,'compile_exit':ret,'cases':[],'physical_closed':False,'actual_parent_bindings_qualified':False}
 if ret:dump(a.out/'terminal.json',rec);return ret
 for name,args,marker in [('exact_64FP32',[],'PASS_NATIVE_SFU_RESULT_PUBLICATION'),('actual_error_tail',['+TAIL_ERROR'],'PASS_SFU_RESULT_ERROR_REFUSED'),('actual_ACK_high_TOKEN17',['+ACK_TOKEN'],'PASS_SFU_RESULT_ACK_TOKEN_REFUSED')]:
  cmd=['vvp',str(binary),*args]
  with (a.out/f'{name}.log').open('w') as log:ret=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
  text=(a.out/f'{name}.log').read_text();passed=ret==0 and marker in text
  rec['cases'].append(dict(name=name,command=cmd,exit=ret,passed=passed));dump(a.out/'terminal.json',rec)
  if not passed:return ret or 1
 rec['verdict']='PASS';dump(a.out/'terminal.json',rec);return 0
if __name__=='__main__':raise SystemExit(main())
