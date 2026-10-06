#!/usr/bin/env python3
"""Hierarchical ENABLE1: one arithmetic master, child golden, real full-width held wrapper.
Only EPYC2, fresh load<128 and >=16 idle CPUs pre/post unchanged admission.
Never starts a RAM-only queued guard when CPU capacity is absent. No deadlines,
process memory limits, individual output caps or rerun of completed positives.
"""
import argparse,datetime,hashlib,json,math,os,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'physical/hbm_die_abstracts_20261006/compute'
RESULT=ROOT/'results/physical/hbm_die_abstracts_20261006/compute/enabled_r1'


def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()


def write(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def usage_cpu():
 v=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
 return sum(v[:8]),v[3]+v[4]


def capacity(out,phase):
 t0,i0=usage_cpu();time.sleep(.5);t1,i1=usage_cpu()
 idle=(i1-i0)/(t1-t0)*os.cpu_count()
 m={k:v for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
 st=os.statvfs(out)
 d=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=socket.gethostname(),phase=phase,
        cpus=os.cpu_count(),load1=os.getloadavg()[0],idle_cpus=idle,
        available_gib=int(m['MemAvailable'].split()[0])/1024**2,
        disk_free_gib=st.f_bavail*st.f_frsize/2**30)
 d['cpu_fit']=d['load1']<d['cpus'] and idle>=16
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
 return d


def run(cmd,out,stem):
 # Time records measured peak RSS for the actual full-shape compiler/runtime;
 # it sets no limit. Completed objects and failed logs are retained.
 with (out/(stem+'.log')).open('w') as f:
  rc=subprocess.call(['/usr/bin/time','-v','-o',str(out/(stem+'.resources')), *cmd],
                     cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 write(out/(stem+'.json'),dict(returncode=rc,command=cmd,
       resources_sha256=sha(out/(stem+'.resources')),log_sha256=sha(out/(stem+'.log'))))
 return rc,(out/(stem+'.log')).read_text()


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--family',choices=['sfu','hc'],required=True)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--admitted',action='store_true')
 a=ap.parse_args()
 if socket.gethostname()!='climbing-locust' or not Path('/srv/opentallas-scratch/admit.sh').exists():
  ap.error('EPYC2 climbing-locust only; no local/other-host fallback')
 out=a.out.resolve()
 if not str(out).startswith('/srv/opentallas-scratch2/'):
  ap.error('job outputs must be NVMe2')
 out.mkdir(parents=True,exist_ok=True)
 if (out/'terminal.json').exists():ap.error('immutable terminal evidence exists; no repeat')
 inv=json.loads((RESULT/'admission_inventory.json').read_text())['families'][a.family]
 receipt=capacity(out,'post_admission' if a.admitted else 'pre_admission')
 if not receipt['cpu_fit']:
  write(out/'not_started.json',dict(reason='FRESH_CPU_FIT_BLOCKED',capacity=receipt));return 75
 if receipt['disk_free_gib']<inv['disk_inventory_gib']:
  write(out/'not_started.json',dict(reason='DISK_INVENTORY_BLOCKED',capacity=receipt));return 75
 if not a.admitted:
  if receipt['available_gib']<inv['declared_peak_gib']+100:
   write(out/'not_started.json',dict(reason='RAM_PLUS_UNCHANGED_RESERVE_BLOCKED',capacity=receipt));return 75
  cmd=['/srv/opentallas-scratch/admit.sh',str(inv['declared_peak_gib']),'--',sys.executable,str(Path(__file__).resolve()),
       '--family',a.family,'--out',str(out),'--admitted']
  return subprocess.call(cmd)
 source=json.loads((BASE/'enabled_sources.json').read_text())
 for p,h in source['files'].items():
  if sha(ROOT/p)!=h:raise ValueError('Source/vector hash mismatch: '+p)
 if (out/'source.json').exists() and json.loads((out/'source.json').read_text())!=source:
  raise ValueError('source differs from held attempt; choose a new immutable attempt')
 write(out/'source.json',source)
 name='HC_POST' if a.family=='hc' else 'SFU'
 # Hierarchical compiler cuts arithmetic children; full-width protected wrapper
 # stays real. One parameter specialization per identical child, not 64 flattened
 # arithmetic copies. No external archive reuse without a complete matching pin.
 verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 if not verilator.is_file():raise ValueError('Pinned Verilator 5.050 missing; no old-tool fallback')
 version=subprocess.check_output([str(verilator),'--version'],text=True).strip()
 if 'Verilator 5.050' not in version:raise ValueError('Verilator version mismatch: '+version)
 cmd=[str(verilator),'--binary','--timing','--hierarchical','-O2',
      '-Wno-fatal','-Wno-WIDTH','--top-module','tb_enabled_quarter',
      '-Mdir',str(out/'obj'),'--build-jobs','16','--verilate-jobs','1','--hierarchical-threads','1','--unroll-count','4',str(BASE/'hierarchical.vlt')]
 if a.family=='hc':cmd.append('-DHC_POST')
 cmd+=['-f',str(BASE/'sources.f'),str(BASE/'tb_enabled_quarter.sv')]
 binary=out/'obj/Vtb_enabled_quarter'
 if (out/'enable1_elaboration_pass.json').exists():
  prior=json.loads((out/'enable1_elaboration_pass.json').read_text())
  if sha(binary)!=prior['binary_sha256']:
   raise ValueError('held enabled binary changed; do not replay')
 else:
  rc,log=run(cmd,out,'enable1_elaboration')
  if rc:
   write(out/'terminal.json',dict(status='ENABLE1_ELABORATION_FAIL',returncode=rc));return rc
  # Retain all generated makefiles/hierarchy plans for master-count review.
  plans={str(p.relative_to(out)):sha(p) for p in (out/'obj').rglob('*')
         if p.is_file() and (p.suffix=='.mk' or 'hier' in p.name)}
  write(out/'hierarchy_inventory.json',dict(tool_version=version,verilator_sha256=sha(verilator),
        expected_masters=inv['unique_arithmetic_masters'],generated_plans=plans,
        archive_policy='No historical archives imported; same-source generated masters reused across instances'))
  write(out/'enable1_elaboration_pass.json',dict(status='PASS',scope='actual enabled full-width wrapper with hierarchical real children',
        family=name,binary_sha256=sha(binary)))
 for stage in ['single_child','golden','negative_held']:
  if stage in ['single_child','golden'] and (out/(stage+'_pass.json')).exists():
   continue # reuse the same immutable full-shape passing cohort, never repeat
  # Recheck at each independent CPU stage; no memory-only continuation launch.
  if not capacity(out,'before_'+stage)['cpu_fit']:
   write(out/'stage_pending.json',dict(status='CPU_FIT_BLOCKED',next_stage=stage));return 75
  cmd=[str(binary),'+DIR='+str(RESULT/'vectors')]
  if stage=='single_child':cmd.append('+CHILD_ONLY')
  if stage=='negative_held':cmd.append('+NEG_HOLD')
  rc,log=run(cmd,out,stage)
  if stage=='single_child':
   passed=rc==0 and f'SINGLE_CHILD_GOLDEN_PASS family={name}' in log
   if not passed:
    write(out/'terminal.json',dict(status='SINGLE_CHILD_GOLDEN_FAIL',returncode=rc));return rc or 1
   write(out/'single_child_pass.json',dict(status='PASS',family=name,seed=20261006,binary_sha256=sha(binary)))
  elif stage=='golden':
   passed=rc==0 and f'ENABLED_FULLSHAPE_PASS family={name}' in log
   if not passed:
    write(out/'terminal.json',dict(status='FULLSHAPE_GOLDEN_FAIL',returncode=rc));return rc or 1
   write(out/'golden_pass.json',dict(status='PASS',family=name,binary_sha256=sha(binary),
         seed=20261006,scope='One full-shape parent cohort incl POR cancellation, held response, request/result CE repair and UE refusal'))
  else:
   passed=rc!=0 and 'NEGATIVE_HELD_CODEWORD_INJECTED' in log and 'HELD_RESPONSE_CHANGED' in log
   write(out/'terminal.json',dict(status='PASS' if passed else 'NEGATIVE_HELD_NOT_CAUGHT',
         negative_returncode=rc,source_sha256=sha(BASE/'enabled_sources.json'),
         family=name,scope='Enabled component exactness only; parent physical/clock and remaining HC paths OPEN'))
   return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
