#!/usr/bin/env python3
"""One immutable connected gate. Intended for the fleet-guarded clean source.

No physical launch. No runtime golden callback. No process/CPU/wall/file caps.
Output is exclusively created, preventing a second compile into an existing run.
"""
import argparse,hashlib,json,os,resource,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003/r2'
MANIFEST_SHA='ac8e25679722d2746fadc8c040a779102089d865e33ccdcff906b845b5f67573'
def verify():
 raw=(BASE/'manifest.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('frozen connected gate manifest')
 for r in json.loads(raw):
  p=ROOT/r['path']
  if not p.resolve().is_relative_to(ROOT.resolve()):raise ValueError('source scope')
  if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('source mismatch '+r['path'])
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):raise ValueError('source not clean')
def sample():
 def snap():
  d={}
  for line in Path('/proc/stat').read_text().splitlines():
   f=line.split()
   if f and f[0].startswith('cpu') and f[0][3:].isdigit():
    v=list(map(int,f[1:]));d[int(f[0][3:])]=(sum(v[:8]),v[3]+v[4])
  return d
 a=snap();time.sleep(.5);b=snap();idle=[]
 for c in os.sched_getaffinity(0):
  t=b[c][0]-a[c][0];i=b[c][1]-a[c][1];idle.append(dict(cpu=c,idle_fraction=i/t if t else 0))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 return dict(allowed_cpu_idle=idle,aggregate_idle_core_equivalent=sum(x['idle_fraction'] for x in idle),load=os.getloadavg(),available_memory_bytes=mem)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
 verify();a.out.mkdir(parents=True,exist_ok=False)
 h=sample();reasons=[]
 if h['aggregate_idle_core_equivalent']<1:reasons.append('NO_SINGLE_WORKER_HEADROOM')
 if h['available_memory_bytes']<4*2**30:reasons.append('NO_FOUR_GIB_RESERVATION')
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 r=dict(source_commit=head,headroom=h,status='PREFLIGHT',HDL_gate='NOT_RUN',physical_gate=False,whole_token_gate=False,
        scope='source-bound PC40 selected exact RF/FMAX/ACK/W6/FMIN gate; protocol-scoped issuer and drain authorities, no trained payload claim',refusals=reasons,
        inherited_rlimits={k:resource.getrlimit(getattr(resource,k)) for k in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE','RLIMIT_DATA']})
 def save(): (a.out/'terminal.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
 save()
 if reasons or a.prepare_only:r['status']='REFUSED_BEFORE_COMPILE' if reasons else 'READY';save();print(json.dumps(r));return
 cpu=max(h['allowed_cpu_idle'],key=lambda x:x['idle_fraction'])['cpu'];r['allocated_cpu']=cpu;r['aggregate_workers']=1
 def affinity():os.sched_setaffinity(0,{cpu})
 inp=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs'
 files=[inp/'ot_gpu_w6_secded_pkg.sv',inp/'ot_hdc_prefix.sv',inp/'ot_gpu_rf_visibility_fence_w6.sv',inp/'ot_gpu_rf_service.sv',
 ROOT/'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_c0_fmax_leaf_r2.sv',ROOT/'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_c0_connected_bridge_r2.sv',
 ROOT/'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_pc40_fmin_consumer.sv',ROOT/'rtl/experimental/hbm_c0_connected_20261003/r2/ot_gpu_pc40_connected_source.sv',ROOT/'rtl/test/hbm_c0_connected_20261003/r2/tb.sv']
 (a.out/'compile_sources.json').write_text(json.dumps([dict(path=str(x),sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in files],indent=2)+'\n')
 for name,cmd in [('compile',['iverilog','-g2012','-s','tb','-o',str(a.out/'gate.vvp')]+[str(x) for x in files]),('runtime',['vvp',str(a.out/'gate.vvp')])]:
  r['status']=name.upper();r[name+'_command']=cmd;save();start=time.monotonic()
  with (a.out/(name+'.log')).open('w') as log:
   result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,preexec_fn=affinity)
  r[name+'_RC']=result.returncode;r[name+'_seconds']=time.monotonic()-start;save()
  if result.returncode:r['status']='FAIL_'+name.upper();save();raise SystemExit(result.returncode)
 log=(a.out/'runtime.log').read_text()
 r['HDL_gate']='PASS_CONNECTED_SELECTED_EXACT' if 'CONNECTED_PC40_PASS' in log else 'FAIL_NO_CONNECTED_TERMINAL'
 r['status']=r['HDL_gate'];r['binary_sha256']=hashlib.sha256((a.out/'gate.vvp').read_bytes()).hexdigest()
 r['source_lease_trace']=[l for l in log.splitlines() if l.startswith('EVENT ')]
 save();print(json.dumps(r))
if __name__=='__main__':main()
