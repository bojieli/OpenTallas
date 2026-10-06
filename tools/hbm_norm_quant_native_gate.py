#!/usr/bin/env python3
"""One production norm transport gate, retained gold and existing32SRAM root."""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def capacity(out,phase):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=cpu();time.sleep(.5);b=cpu();d=[y-x for x,y in zip(a,b)]
 idle=os.cpu_count()*(d[3]+d[4])/sum(d)
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))/1024**2
 v=os.statvfs(out);disk=v.f_bavail*v.f_frsize/2**30;load=os.getloadavg()[0]
 rec=dict(phase=phase,host=socket.gethostname(),load1=load,idle_CPU=idle,MemAvailable_GiB=mem,NVMe_free_GiB=disk,fit=load<128 and idle>=4 and mem>=196 and disk>=12)
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 return rec

def main():
 p=argparse.ArgumentParser();p.add_argument('--engine',action='store_true');p.add_argument('--recipe',type=Path);p.add_argument('--bench-source',default='6bb9b0cf2');p.add_argument('--source',type=Path,required=True);p.add_argument('--gold',type=Path,required=True);p.add_argument('--reuse',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--admitted',action='store_true');a=p.parse_args()
 src=a.source.resolve();gold=a.gold.resolve();reuse=a.reuse.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if os.cpu_count()<128 or not str(out).startswith('/srv/opentallas-scratch'):p.error('EPYC NVMe only')
 if (out/'terminal.json').exists():p.error('Terminal exists; no repeated gate')
 recipe=a.recipe.resolve() if a.recipe else src/'results/rtl/hbm_norm_quant_native_publication_20261006/source_preparation.json'
 prep=json.loads(recipe.read_text())
 if a.engine:
  if a.bench_source=='6bb9b0cf2':p.error('Actualengine requires new Gauss fixture pin; retained-output gate cannot qualify engine')
  if any(prep[k]!=v for k,v in dict(N=64,D=5120,KIND=0,AW=24,PUBLISH_QUANT=1,INPUT_CP=1).items()):p.error('Actualengine requires selected fullgeometry')
  if not prep.get('arithmetic_instantiated'):p.error('Recipe does not instantiate actualengine')
  engine=json.loads((src/'results/rtl/hbm_norm_vm_boundary_20261006/connected.json').read_text())['engine_21_sha256']
  for f,h in engine.items():
   if prep['source_sha256'].get(f)!=h:raise ValueError('Actualengine missing or changed dependency '+f)
  bench=src/next(f for f in prep['sources'] if Path(f).name==prep['top']+'.sv')
  import re
  if not re.search(r'ot_hbm_integrated_norm_stage\s*#\s*\(',bench.read_text()):p.error('Fixture must instantiate actual protectednormstage')
 for f,h in prep['source_sha256'].items():
  if sha(src/f)!=h:raise ValueError('Source pin mismatch '+f)
 grecord=json.loads((src/'results/rtl/hbm_norm_quant_native_publication_20261006/retained_gold_source.json').read_text())
 for f,h in grecord['files_sha256'].items():
  if sha(gold/f)!=h:raise ValueError('Retainedgold mismatch '+f)
 old=json.loads((reuse/'prepared.json').read_text())['source_sha256']
 backend=[f for f in prep['sources'] if f.startswith('physical/') and not Path(f).name.startswith('tb_')]+['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv']
 for f in backend:
  if old.get(f)!=prep['source_sha256'][f]:raise ValueError('Reusable backend dependency mismatch '+f)
 record=dict(bench_source=a.bench_source,production_source='16e5cb9f8',source_sha256=prep['source_sha256'],golden_sha256=grecord['files_sha256'],reservation_GiB=96,threads=4,basis='measured native enclosing frontend74.6GiB plus unchanged100GiB reserve',arithmetic_instantiated=a.engine,arithmetic_qualified=False,whole_parent_qualified=False,SSFF_qualified=False)
 dump(out/'prepared.json',record)
 if not capacity(out,'post_guard' if a.admitted else 'pre_guard')['fit']:
  dump(out/'not_started.json',dict(reason='CURRENT_CAPACITY_BLOCKED'));return 75
 if not a.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','96','--','python3',str(Path(__file__).resolve()),'--source',str(src),'--gold',str(gold),'--reuse',str(reuse),'--out',str(out),'--admitted','--bench-source',a.bench_source,*(['--recipe',str(recipe)] if a.recipe else []),*(['--engine'] if a.engine else [])])
 name='Vot_hbm_die_vm_sfu_publication_root_2';child=reuse/'obj'/name
 if not list(child.glob('*.a')):raise ValueError('Missing completed child library')
 shutil.copytree(child,out/'obj'/name,dirs_exist_ok=True)
 dump(out/'reuse.json',dict(previous=str(reuse),source_verified=True,library_sha256={f.name:sha(f) for f in child.glob('*.a')},compatibility_checked_by_compiler=True,original_objects_preserved=True))
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 version=subprocess.check_output([str(tool),'--version'],text=True).strip()
 if not version.startswith('Verilator 5.050 '):raise ValueError('Pinned5.050 required')
 cfg=src/'results/rtl/hbm_norm_quant_native_publication_20261006/hierarchical.vlt'
 if a.engine:
  cfg=out/'hierarchical.vlt'
  cfg.write_text('`verilator_config\nhier_block -module "ot_hbm_die_vm_sfu_publication_root"\nhier_block -module "ot_dsrom_su_norm"\n')
 cmd=[str(tool),*prep['compiler_options'],'-Mdir',str(out/'obj'),str(cfg),*[str(src/f) for f in prep['sources']]]
 dump(out/'command.json',dict(command=cmd,tool=version))
 with (out/'compile.log').open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/'compile.resources'),*cmd],cwd=src,stdout=log,stderr=subprocess.STDOUT)
 if rc:dump(out/'terminal.json',dict(status='COMPILE_FAIL',returncode=rc,**record));return rc
 results=[]
 for case in prep['cases']:
  if not capacity(out,'before_'+case['name'])['fit']:
   dump(out/'pending.json',dict(reason='CURRENT_CPU_RAM_DISK_FIT_BLOCKED',binary=str(out/'obj'/('V'+prep['top'])),completed_cases=results));return 75
  name=case['name'];logpath=out/(name+'.log')
  with logpath.open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/(name+'.resources')),str(out/'obj'/('V'+prep['top'])),'+DIR='+str(gold),*case['plusargs']],cwd=gold,stdout=log,stderr=subprocess.STDOUT)
  passed=rc==0 and case['marker'] in logpath.read_text();result=dict(case=name,status='PASS' if passed else 'FAIL',returncode=rc);results.append(result);dump(out/(name+'.json'),result)
  if not passed:dump(out/'terminal.json',dict(status='FAIL',cases=results,**record));return rc or 2
 dump(out/'terminal.json',dict(status='PASS',cases=results,**record));return 0
if __name__=='__main__':raise SystemExit(main())
