#!/usr/bin/env python3
"""Prepare/run one captured numerical stage per target through CP + held join.

Existing compiled-program fixtures and golden snapshots are inputs; this tool
does not generate a numerical producer or repeat a source-only c12 campaign.
--prepare performs no build. --run refuses capacity misses before any compiler.
Kant dispatches on E2 with the unchanged guard and measured inventory reservation.
"""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
import hbm_su_c12 as C12
import rtl_hdc_v41x_vec_campaign as VC

ROOT=Path(__file__).resolve().parents[1]
BENCH='rtl/test/hbm_accel/integrated_20261006/tb_hbm_integrated_su_c12.sv'
HARNESS='rtl/test/hbm_accel/integrated_20261006/hbm_integrated_su_c12_main.cpp'
EXTRA=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv',
 'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_stage_join.sv',
 'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',BENCH,HARNESS]
FILES=['vm.hex','kv.hex','cr.hex','wr.hex','prog.hex','expected_vm.hex','expected_kv.hex']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sources(fp_mode='rtl'):
 sw=dict(C12.SWAP);sw['rtl/hdc/ot_hdc_fastfp_lat.sv']=C12.C12_UNITS if fp_mode=='rtl' else C12.C12_UNITS_DPI
 lib=VC.LIB
 if fp_mode=='dpi_beh':
  import dshbm_baseline_measure as D
  lib=D.fp_dpi_lib(lib,beh_prefix=True)
 paths=[]
 for p in lib+VC.RTL:
  name=str(p.relative_to(ROOT));paths+=sw.get(name,[name])
 return list(dict.fromkeys(paths+EXTRA))
def prepare(spec,out,fp_mode='rtl'):
 r=json.loads(spec.read_text())
 if set(r['cases'])!={'DS1M','Qwen8K'}:raise ValueError('Both actual target fixtures required')
 out.mkdir(parents=True,exist_ok=False)
 for target,c in r['cases'].items():
  if c['position']!={'DS1M':1048575,'Qwen8K':8191}[target]:raise ValueError('target context mismatch')
  if c['nops']<1 or not c.get('source_capture'):raise ValueError('actual captured program/operand provenance required')
  d=out/target;d.mkdir()
  for name in FILES:
   p=Path(c['directory'])/name
   if sha(p)!=c['sha256'][name]:raise ValueError('changed actual input/golden '+str(p))
   shutil.copyfile(p,d/name)
  if c.get('external_producer'):raise ValueError('this minimum stage has no invented external producer')
 r.update(fp_mode=fp_mode,source_sha256={p:sha(ROOT/p) for p in sources(fp_mode)},
          include_sha256={'rtl/test/tb_hdc_v41x_vec_fields.svh':sha(ROOT/'rtl/test/tb_hdc_v41x_vec_fields.svh')},
          c12_parameters=dict(C12.P,redrogs=2),arithmetic_scope=('bit-level RTL' if fp_mode=='rtl' else 'existing qualified c12 dpi_beh primitive stand-ins; full control/ports RTL; no integrated bit-RTL qualification'),scope='actual CP/73-bit protected descriptor/c12/local-VM stage; not whole token or installed HBM provider',
          physical_qualified=False,all_levers_whole_token=False)
 (out/'prepared.json').write_text(json.dumps(r,indent=2)+'\n')
def sample(work):
 def cpu():return [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
 a=cpu();time.sleep(1);b=cpu();delta=[y-x for x,y in zip(a,b)]
 mem=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
 return dict(load=list(os.getloadavg()),idle_cores=os.cpu_count()*(delta[3]+delta[4])/sum(delta),
             available_bytes=mem,disk_free=shutil.disk_usage(work).free)
def run(work,reservation,inventory,threads,activity,phase='all'):
 r=json.loads((work/'prepared.json').read_text())
 if any(sha(ROOT/p)!=h for p,h in r['source_sha256'].items()):raise ValueError('pinned stage source changed')
 if any(sha(ROOT/p)!=h for p,h in r['include_sha256'].items()):raise ValueError('instruction field include changed')
 for target,c in r['cases'].items():
  for name in FILES:
   if sha(work/target/name)!=c['sha256'][name]:raise ValueError('prepared input/golden changed')
 if phase!='build-run' and (work/'build.exit').exists():raise FileExistsError('preserve prior build; no implicit retry/rebuild')
 required_cores=1 if phase=='frontend' else threads
 if phase=='build-run' and (not (work/'frontend.exit').exists() or (work/'frontend.exit').read_text().strip()!='0'):
  raise ValueError('completed unchanged frontend required')
 # Unchanged protected admission; explicit CPU/disk checks precede and follow it.
 import sys
 sys.path.insert(0,'/srv/opentallas-scratch');import admit_core
 pre=sample(work)
 if pre['load'][0]+required_cores>=min(110,os.cpu_count()) or pre['idle_cores']<required_cores+1 or pre['disk_free']<2*inventory:
  raise RuntimeError('CPU/disk capacity miss; no compiler launched: '+json.dumps(pre))
 if not admit_core.try_admit(reservation*2**30):raise RuntimeError('unchanged admission declined')
 post=sample(work)
 if post['load'][0]+required_cores>=min(110,os.cpu_count()) or post['idle_cores']<required_cores+1 or post['disk_free']<2*inventory:
  raise RuntimeError('post-admission CPU/disk miss; no compiler launched: '+json.dumps(post))
 (work/('admission_'+phase+'.json')).write_text(json.dumps(dict(pre=pre,post=post,reservation_GiB=reservation,
       prior_actual_inventory_bytes=inventory,threads=threads,execution_caps=None),indent=2)+'\n')
 obj=work/'obj'
 cmd=[VC.VERILATOR,'--cc','--exe',*(['--build'] if phase=='all' else []),'--timing','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT',
      '--top-module','tb_hdc_v41x_vec','--prefix','Vtb','-Mdir',str(obj),'-j',str(threads),
      '-GN=1024','-GM=256','-GBCAST_STAGES=7','-GRET_STAGES=8','-GMLAT=6','-GALAT=6',
      *C12.vflags().split(),*[f'-G{k}={v}' for k,v in dict(VMA=VC.VMA,KVA=VC.KVA,CRA=VC.CRA,WRA=VC.WRA,XBA=VC.XBA).items()],
      '-I'+str(ROOT/'rtl/test')]
 if activity:cmd+=['--trace-fst']
 cmd += [str(ROOT/p) for p in sources(r.get('fp_mode','rtl'))]+['-CFLAGS','-O1']
 if phase=='build-run':cmd=['make','-C',str(obj),'-f','Vtb.mk','-j',str(threads),'OPT_FAST=-O0','OPT_SLOW=-O0']
 (work/('build_command_'+phase+'.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 with (work/('build_'+phase+'.log')).open('x') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 (work/('frontend.exit' if phase=='frontend' else 'build.exit')).write_text(str(rc)+'\n')
 if rc or phase=='frontend':return rc
 rows=[];exe=obj/'Vtb'
 for target,c in r['cases'].items():
  d=work/target
  base=[str(exe),*[f'+{flag}={d/name}' for flag,name in [('VM','vm.hex'),('KV','kv.hex'),('CR','cr.hex'),('WR','wr.hex'),('PROG','prog.hex'),('VMO','vmo.hex'),('KVO','kvo.hex')]],
        f"+NPROG={c['nops']}",f"+POSITION={c['position']}"]
  if activity:base += ['+ACTIVITY='+str(d/'activity.fst')]
  with (d/'runtime.log').open('w') as f:rc=subprocess.run(base,stdout=f,stderr=subprocess.STDOUT).returncode
  log=(d/'runtime.log').read_text();tr=VC.parse_trace(log)
  bad={name:int((VC.read_hex(d/got)!=VC.read_hex(d/want)).sum()) if (d/got).exists() else None
       for name,got,want in [('vm','vmo.hex','expected_vm.hex'),('kv','kvo.hex','expected_kv.hex')]}
  ok=rc==0 and 'PASS_INTEGRATED_STAGE_DRAIN' in log and tr['end'] and tr['end'][1]=='ok' and not(tr['faults'] or tr['orders']) and all(v==0 for v in bad.values())
  rows.append(dict(target=target,rc=rc,numerical_exact=bool(ok),mismatches=bad,trace=tr))
  (work/'result.json').write_text(json.dumps(dict(source=r,rows=rows,binary_sha256=sha(exe),
      physical_qualified=False,all_levers_whole_token=False),indent=2)+'\n')
  if not ok:return 1
  # One meaningful foreign-owner negative in the SAME changed binary.
  negative=[x for x in base if not x.startswith('+ACTIVITY=')]+['+JOIN_NEGATIVE=1']
  with (d/'foreign_owner.log').open('w') as f:nrc=subprocess.run(negative,stdout=f,stderr=subprocess.STDOUT).returncode
  if nrc or 'PASS_INTEGRATED_STAGE_REJECT' not in (d/'foreign_owner.log').read_text():return 1
 return 0
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--work',type=Path,required=True)
 p.add_argument('--run',action='store_true');p.add_argument('--reservation-gib',type=int);p.add_argument('--prior-inventory-bytes',type=int)
 p.add_argument('--threads',type=int,choices=range(16,25),default=16);p.add_argument('--activity',action='store_true')
 p.add_argument('--fp',choices=['rtl','dpi_beh'],default='rtl')
 p.add_argument('--phase',choices=['all','frontend','build-run'],default='all');a=p.parse_args()
 if a.prepare:prepare(a.prepare.resolve(),a.work.resolve(),a.fp)
 if a.run:
  if not a.reservation_gib or not a.prior_inventory_bytes:p.error('measured reservation and actual prior inventory required')
  raise SystemExit(run(a.work.resolve(),a.reservation_gib,a.prior_inventory_bytes,a.threads,a.activity,a.phase))
