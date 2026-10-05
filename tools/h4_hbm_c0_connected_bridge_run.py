#!/usr/bin/env python3
"""Functional RF/FMAX/W6 test runner. No synthesis or physical launch.

Source-pinned clean tree; fresh allowed-CPU and RAM headroom; no time, file,
address-space, swap or memory caps. Outputs belong on persistent storage.
"""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003'
MANIFEST_SHA='4e5345f735483eb6c84eddf73ddbef222f3b8a5ac6283d5f978adfc371d923fc'
def snapshot():
 d={}
 for line in Path('/proc/stat').read_text().splitlines():
  f=line.split()
  if f and f[0].startswith('cpu') and f[0][3:].isdigit():
   v=list(map(int,f[1:]));d[int(f[0][3:])]=(sum(v[:8]),v[3]+v[4])
 return d
def headroom():
 a=snapshot();time.sleep(.3);b=snapshot();scores=[]
 for cpu in os.sched_getaffinity(0):
  total=b[cpu][0]-a[cpu][0];idle=b[cpu][1]-a[cpu][1]
  scores.append((cpu,idle/total if total else 0))
 mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')}
 # Reserve one idle core for this serial compiler/simulator, no affinity escape.
 eligible=[cpu for cpu,f in scores if f>=.8]
 return dict(idle_fraction_by_allowed_cpu=scores,eligible_cpus=eligible,
  memory_available_bytes=mem['MemAvailable'],memory_reservation_bytes=4*2**30,
  reservation_basis='small functional fixture: 128 comparator lanes, 260 codec words, two 512-vector RF fixtures; 4GiB conservative planning reserve, NOT a process limit')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
 args.out.mkdir(parents=True,exist_ok=True)
 raw=(BASE/'manifest.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('frozen manifest identity')
 for row in json.loads(raw):
  path=ROOT/row['path']
  if not path.resolve().is_relative_to(ROOT.resolve()):raise ValueError('source scope')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('source/artifact differs: '+row['path'])
 clean=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)==''
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 h=headroom();reasons=[]
 if not clean:reasons.append('SOURCE_TREE_NOT_CLEAN')
 if not h['eligible_cpus']:reasons.append('NO_ALLOWED_CPU_HEADROOM')
 if h['memory_available_bytes']<h['memory_reservation_bytes']:reasons.append('NO_RAM_HEADROOM')
 receipt=dict(commit=commit,headroom=h,refusals=reasons,HDL_gate='NOT_RUN',physical_gate='NOT_RUN',numerical_production_gate='NOT_RUN',scope='functional source-selected fixture; issuer/drain inputs are protocol witnesses')
 def save(): (args.out/'terminal.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
 save()
 if reasons or args.prepare_only:
  receipt['status']='REFUSED_BEFORE_COMPILE' if reasons else 'READY_TO_RUN';save();print(json.dumps(receipt));return
 inp=BASE/'inputs'; sources=[inp/'ot_gpu_w6_secded_pkg.sv',inp/'ot_hdc_prefix.sv',inp/'ot_gpu_rf_visibility_fence_w6.sv',inp/'ot_gpu_rf_service.sv',ROOT/'rtl/experimental/hbm_c0_connected_20261003/ot_gpu_c0_fmax_leaf.sv',ROOT/'rtl/experimental/hbm_c0_connected_20261003/ot_gpu_c0_connected_bridge.sv',ROOT/'rtl/test/hbm_c0_connected_20261003/tb.sv']
 affinity=[h['eligible_cpus'][0]]
 def pin():os.sched_setaffinity(0,affinity)
 commands=[['iverilog','-g2012','-s','tb','-o',str(args.out/'sim.vvp')]+[str(x) for x in sources],['vvp',str(args.out/'sim.vvp')]]
 for name,command in zip(('compile','run'),commands):
  with (args.out/(name+'.log')).open('w') as log:
   result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,preexec_fn=pin)
  receipt[name+'_exit']=result.returncode;save()
  if result.returncode:receipt['status']='FAIL_'+name.upper();save();raise SystemExit(result.returncode)
 text=(args.out/'run.log').read_text()
 receipt['HDL_gate']='PASS' if 'PASS actual RF/FMAX/W6 controller' in text else 'FAIL_NO_TERMINAL'
 receipt['status']=receipt['HDL_gate'];save();print(json.dumps(receipt))
if __name__=='__main__':main()
