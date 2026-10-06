#!/usr/bin/env python3
"""One actual index/SRAM adapter seed and physical SRAM UE negative on E2.
Small single-process Icarus gate; fresh CPU/RAM/NVMe fit, original guard.
Never run locally; never queue behind a RAM-only guard on an overloaded host.
"""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
 'rtl/hbm_accel/index/ot_hbm_accel_index_query_source.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_index_fp32_sram_adapter.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/tb_index_fp32_sram_adapter.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capacity():
 def sample():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=sample();time.sleep(1);b=sample();d=[y-x for x,y in zip(a,b)]
 nc=os.cpu_count();idle=nc*(d[3]+d[4])/sum(d);load=os.getloadavg()[0]
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 v=os.statvfs('/srv/opentallas-scratch2')
 return dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),CPU_count=nc,load1=load,idle_CPU=idle,MemAvailable_bytes=mem,NVMe_free_bytes=v.f_bavail*v.f_frsize,CPU_fit=idle>=1 and load+1<=nc)
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admitted',action='store_true');a=ap.parse_args()
 if '5.199.165.105' not in subprocess.check_output(['hostname','-I'],text=True).split():raise SystemExit('E2 only; refusing local simulation')
 guard=Path('/srv/opentallas-scratch/admit.sh');pins={s:sha(a.root/s) for s in SOURCES};cap=capacity()
 if not a.admitted:
  a.out.mkdir(parents=True,exist_ok=False)
  rec={'status':'CAPACITY_REFUSED','capacity':cap,'guard_sha256':sha(guard),'source_sha256':pins,'requested_CPU':1,'reservation_GiB':1,'basis':'single-process Icarus finite10x512x128 SRAM+17SECDED words; 1GiB reservation without process limits','whole_VM_parent_qualified':False}
  dump(a.out/'launch.json',rec)
  if not cap['CPU_fit'] or cap['MemAvailable_bytes']<101*1024**3 or cap['NVMe_free_bytes']<2*1024**3:return 66
  cmd=[str(guard),'1','--','python3',str(Path(__file__).resolve()),'--root',str(a.root),'--out',str(a.out),'--admitted']
  rec['status']='FRESH_CPU_FIT_BEFORE_GUARD';rec['command']=cmd;dump(a.out/'launch.json',rec)
  result=subprocess.call(cmd);rec['exit']=result;rec['guard_unchanged']=sha(guard)==rec['guard_sha256'];dump(a.out/'launch.json',rec);return result
 launch=json.loads((a.out/'launch.json').read_text());dump(a.out/'post_guard_capacity.json',cap)
 if pins!=launch['source_sha256'] or sha(guard)!=launch['guard_sha256']:return 65
 if not cap['CPU_fit']:return 66
 binary=a.out/'index_adapter.vvp';cmd=['iverilog','-g2012','-DOT_MEM_NO_INIT','-s','tb_index_fp32_sram_adapter','-o',str(binary),*[str(a.root/s) for s in SOURCES]]
 with (a.out/'compile.log').open('w') as log:ret=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 rec={'source_sha256':pins,'compile_command':cmd,'compile_exit':ret,'cases':[],'physical_closed':False,'actual_parent_bindings_qualified':False}
 if ret:dump(a.out/'terminal.json',rec);return ret
 for name,args,marker in [('exact_seed',[],'PASS_INDEX_FP32_REAL_SRAM'),('actual_SRAM_UE',['+SRAM_UE'],'PASS_REAL_SRAM_UE_REFUSED_INDEX_PUBLICATION')]:
  cmd=['vvp',str(binary),*args]
  with (a.out/f'{name}.log').open('w') as log:ret=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
  text=(a.out/f'{name}.log').read_text();passed=ret==0 and marker in text
  rec['cases'].append(dict(name=name,command=cmd,exit=ret,passed=passed));dump(a.out/'terminal.json',rec)
  if not passed:return ret or 1
 rec['verdict']='PASS';dump(a.out/'terminal.json',rec);return 0
if __name__=='__main__':raise SystemExit(main())
