#!/usr/bin/env python3
"""Prepared D1 fixture runner. External fresh GO required; never selects full wrapper."""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
import w17_D1_frozen_caps as cap
ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'rtl/test/w17_D1_frozen_observer'
OLD=ROOT/'rtl/test/w17_owner_progress_watchdog'
REC=ROOT/'results/uarch/w17_D1_frozen_observer_20261002'
COMPILER=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def make_plan():
 m=json.loads((ROOT/'results/uarch/w17_owner_progress_watchdog_20261002/source_manifest.json').read_text())
 files={p:v['sha256'] for p,v in m['source_files'].items()}
 for p in list(PKG.iterdir())+[OLD/'owner_progress.hpp',OLD/'observer_dpi.cpp',OLD/'owner_progress_exports.sv']:
  if p.is_file():files[str(p.relative_to(ROOT))]=sha(p)
 for n in ('w17_D1_frozen_gate.py','w17_D1_frozen_caps.py','w17_D1_event_ledger.py'):
  p=ROOT/'tools'/n;files[str(p.relative_to(ROOT))]=sha(p)
 for n in ('test_w17_D1_event_ledger.py','test_w17_D1_frozen_package.py'):
  p=ROOT/'tests'/n;files[str(p.relative_to(ROOT))]=sha(p)
 for p in sorted(REC.iterdir()):
  if p.name not in ('plan.json','artifact_sha256.json') and not p.name.endswith('.log') and p.is_file():files[str(p.relative_to(ROOT))]=sha(p)
 return dict(status='FROZEN_REVIEW_REQUIRED_NO_GO',source_pin=PIN,prerequisites=['f69cd549c59ee35f56d6c71282f62c98398bd33f','8f9bf400ecb8122b1bb613bcf6448e877480cf14'],files_sha256=files,
  sources=[p for p in m['source_files'] if p.endswith(('.sv','.v'))],
  compiler={'path':str(COMPILER),'version':'Verilator 5.050 2026-07-01 rev v5.050','wrapper_sha256':'fb2cc573b1055cf096c90e1efc9966fe56bdb4b265c83590cf2a49f7a0defcdf','binary_sha256':'d3f42fa3b523cf1d7e38827134ac8560ac03b52466392eaf0001141ed4d9fe41'},
  caps=cap.CAPS,budget=dict(shared_compile_seconds=750,runtime_seconds_each=20,whole_seconds=900,reserve_seconds=50,aggregate_output_bytes=2147483648,aggregate_output_poll_seconds=.1,log_bytes=16777216,file_bytes=268435456,memory_reserve_bytes=25769803776,disk_reserve_bytes=17179869184),
  options=['--binary','--timing','--assert','--top-module','tb_D1','-j','2','-Wno-fatal','--unroll-count','1','--unroll-limit','131072','--output-split','20000','--output-split-cfuncs','2000','-CFLAGS','-O0','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0'],
  cases=[dict(name='HEALTHY',marker='OWNER_PROGRESS_HEALTHY_PASS'),dict(name='HOLD_REQ',marker='OWNER_PROGRESS_REFUSAL_PASS case=HOLD_REQ reason=2'),dict(name='HOLD_RSP',marker='OWNER_PROGRESS_REFUSAL_PASS case=HOLD_RSP reason=3'),dict(name='OVERALL',marker='OWNER_PROGRESS_REFUSAL_PASS case=OVERALL reason=6'),dict(name='WRITER',marker='D1_WRITER_QUALIFIED_PASS')],
  future_wrapper_selected=False,full_L0_compile=False,fulltoken=False,service_status='BOUND_MISSING',geometry_shrink=False,live_changes=False,auto_retry=False)
def validate_plan(path):
 p=json.loads(Path(path).read_text())
 if p!=make_plan():raise ValueError('plan/source/options/caps mismatch')
 for path,h in p['files_sha256'].items():
  if sha(ROOT/path)!=h:raise ValueError('source drift '+path)
 return p

def validate_go(go,plan_sha,head):
 if set(go)!= {'authorized_one_execution','plan_sha256','source_package_commit','scope'} or go['authorized_one_execution'] is not True or go['plan_sha256']!=plan_sha or go['source_package_commit']!=head or go['scope']!='D1_BOUNDED_SOURCE_FIXTURE_ONLY':
  raise ValueError('fresh exact-source GO required')
def headroom(out):
 mem=dict((line.split(':')[0],line.split(':')[1].strip()) for line in Path('/proc/meminfo').read_text().splitlines())
 available=int(mem['MemAvailable'].split()[0])*1024;free=shutil.disk_usage(out).free;load=os.getloadavg()[0]
 r=dict(available_memory_bytes=available,disk_free_bytes=free,load1=load,cpus=os.cpu_count())
 if available<cap.CAPS['MemoryMax']+25769803776 or free<2147483648+17179869184 or load>os.cpu_count()-2:raise ValueError('fresh headroom/reserve admission failed')
 return r

def worker(a):
 out=Path(a.out).resolve();steps=[];verdict='FAIL_PRESERVED_NO_RETRY'
 if out==ROOT or ROOT in out.parents:raise ValueError('external fresh output only')
 out.mkdir(exist_ok=False)
 try:
  plan=validate_plan(a.plan)
  if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean frozen source required')
  head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
  validate_go(json.loads(Path(a.go).read_text()),sha(a.plan),head)
  consume=Path(a.go).with_name(Path(a.go).name+'.consumed.json')
  with consume.open('x') as stream:json.dump(dict(source_commit=head,output=str(out),no_retry=True),stream)
  receipt=cap.caps_receipt(a.unit);write(out/'caps_before_compile.json',receipt)
  write(out/'source_snapshot.json',dict(commit=head,files_sha256=plan['files_sha256'],plan_sha256=sha(a.plan),GO_sha256=sha(a.go)))
  for key in ('VERILATOR_ROOT','VERILATOR_BIN','MAKEFLAGS','MFLAGS','CC','CXX','CXXFLAGS','CPPFLAGS','LDFLAGS','LD_PRELOAD','LD_LIBRARY_PATH','PERL5OPT','PERL5LIB'):
   if os.environ.get(key):raise ValueError('compiler environment override '+key)
  c=plan['compiler']
  if sha(COMPILER)!=c['wrapper_sha256'] or sha(COMPILER.with_name('verilator_bin'))!=c['binary_sha256']:raise ValueError('compiler hash')
  version=subprocess.check_output([str(COMPILER),'--version'],text=True,timeout=5).strip()
  if version!=c['version']:raise ValueError('compiler version')
  write(out/'compiler_receipt.json',c)
  write(out/'headroom_compile.json',headroom(out))
  command=[str(COMPILER)]+plan['options']+['--Mdir',str(out/'obj'),'-I'+str(OLD/'pinned/rtl/hdc/v41'),'-CFLAGS','-I'+str(OLD)]+[str(ROOT/p) for p in plan['sources']]+[str(OLD/'owner_progress_exports.sv'),str(PKG/'source_observer.sv'),str(PKG/'tb_D1.sv'),str(OLD/'observer_dpi.cpp')]
  step=cap.supervised(command,out/'compile.log',750,out);steps.append(step)
  cap.read_clean_runtime_events(receipt['kernel_cgroup'])
  if step['returncode']:raise ValueError('compile failed')
  binary=out/'obj/Vtb_D1';write(out/'binary_receipt.json',dict(sha256=sha(binary),bytes=binary.stat().st_size))
  for case in plan['cases']:
   write(out/(case['name']+'_headroom.json'),headroom(out))
   log=out/(case['name']+'.log');step=cap.supervised([str(binary),'+CASE='+case['name']],log,20,out);steps.append(step)
   cap.read_clean_runtime_events(receipt['kernel_cgroup'])
   text=log.read_text()
   if step['returncode'] or case['marker'] not in text or '%Fatal' in text or 'Assertion failed' in text:raise ValueError('first case failure '+case['name'])
  if any(sha(ROOT/p)!=h for p,h in plan['files_sha256'].items()):raise ValueError('source postcheck failed')
  verdict='PASS_BOUNDED_SOURCE_CALLBACK_FIXTURE_ONLY'
 except BaseException as e:write(out/'first_failure.json',dict(error=repr(e),no_retry=True))
 finally:
  write(out/'record.json',dict(verdict=verdict,steps=steps,output_peak_bytes=cap.OUTPUT_PEAK,core_four_bits_executed=False,original_progress_inferred=False,PHY_qualified=False,fulltoken=False,service_status='BOUND_MISSING',no_retry=True))
 return 0 if verdict.startswith('PASS') else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--write-plan',action='store_true');ap.add_argument('--validate-plan');ap.add_argument('--worker',action='store_true');ap.add_argument('--plan');ap.add_argument('--go');ap.add_argument('--out');ap.add_argument('--unit');a=ap.parse_args()
 if a.write_plan:write(REC/'plan.json',make_plan());print('FROZEN_NO_COMPILE')
 elif a.validate_plan:validate_plan(a.validate_plan);print('STATIC_PLAN_PASS_NO_COMPILER')
 elif a.worker:raise SystemExit(worker(a))
 else:raise SystemExit('No implicit execution. Reviewed external GO and capped systemd worker required.')
