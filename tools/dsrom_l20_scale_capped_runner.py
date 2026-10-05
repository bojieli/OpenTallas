#!/usr/bin/env python3
"""Review preflight by default. Compilation requires an explicit source-bound GO record.
This runner gates only the isolated quantizer fixture, never QE/collector/engine/P&R.
"""
import argparse, hashlib, json, os, resource, signal, subprocess, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'results/uarch/dsrom_l20_scale_optin_preparation_20261002/preparation.json'
FIX=ROOT/'tests/fixtures/dsrom_l20_scale_optin_20261002'
SOURCES=['tb_l20_scale_optin.sv','source/original/ot_hdc_delay.sv','source/original/ot_hdc_fp4qdq.sv','source/optin/ot_hdc_fp4qdq_l20_scale_optin.sv']
LIMITS={'memory_bytes':2*1024**3,'cpu_seconds_each_process':120,'wall_seconds_each_process':180,'individual_file_bytes':64*1024**2,'total_workdir_bytes':128*1024**2,'file_descriptors':64,'compile_parallel_jobs':1}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def limits():
 os.setsid()
 resource.setrlimit(resource.RLIMIT_AS,(LIMITS['memory_bytes'],)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(LIMITS['cpu_seconds_each_process'],)*2)
 resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['individual_file_bytes'],)*2)
 resource.setrlimit(resource.RLIMIT_NOFILE,(LIMITS['file_descriptors'],)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def run(cmd,wd,log):
 with log.open('wb') as out:
  p=subprocess.Popen(cmd,cwd=wd,stdout=out,stderr=subprocess.STDOUT,preexec_fn=limits)
  start=time.monotonic();reason=None
  while p.poll() is None:
   if time.monotonic()-start>LIMITS['wall_seconds_each_process']:reason='wall cap'
   if sum(q.stat().st_size for q in wd.rglob('*') if q.is_file())>LIMITS['total_workdir_bytes']:reason='workdir cap'
   if reason:
    os.killpg(p.pid,signal.SIGKILL);p.wait();raise RuntimeError(reason+'; no retries')
   time.sleep(.2)
  if p.returncode:raise RuntimeError('bounded fixture failed '+str(p.returncode)+'; no retries; '+str(log))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--compile-go',type=Path,help='explicit locally reviewed isolated fixture GO JSON, not a model verdict');a=ap.parse_args()
 prep=json.loads(PREP.read_text())
 for name,digest in prep['files_sha256'].items():assert sha(ROOT/name)==digest,name
 state={'status':'SOURCE_HASH_AND_RESOURCE_PREFLIGHT_ONLY','compiler_invoked':False,'limits':LIMITS,'sources':SOURCES,'full_QE_elaboration':False,'collector_engine_elaboration':False,'prepared_status':prep['execution'],'preparation_sha256':sha(PREP)}
 if a.compile_go is None:print(json.dumps(state,sort_keys=True));return
 go=json.loads(a.compile_go.read_text())
 assert go.get('scope')=='dsrom_l20_isolated_scale_quantizer_fixture'
 assert go.get('compile_allowed') is True and go.get('simulate_allowed') is True
 assert go.get('preparation_sha256')==sha(PREP)
 assert go.get('runner_sha256')==sha(Path(__file__))
 assert go.get('source_prepreview_reviewed') is True
 # Private source-bound scratch, originals and evidence remain untouched.
 wd=Path(tempfile.mkdtemp(prefix='dsrom-l20-scale-reviewed-'))
 for name in ['inputs','golden','codes','scales','faults']:
  (wd/(name+'.hex')).write_bytes((FIX/(name+'.hex')).read_bytes())
 exe=wd/'fixture.vvp'
 compilecmd=['iverilog','-g2012','-s','tb_l20_scale_optin','-o',str(exe)]+[str(FIX/s) for s in SOURCES]
 try:
  run(compilecmd,wd,wd/'compile.log');run(['vvp',str(exe)],wd,wd/'simulate.log')
  text=(wd/'simulate.log').read_text();assert 'PASS ' in text
  state.update(status='PASS_ISOLATED_EXECUTED_FIXTURE_ONLY',compiler_invoked=True,scratch=str(wd),simulation_sha256=sha(wd/'simulate.log'))
 except Exception as e:
  state.update(status='FAIL_BOUNDED_FIXTURE',compiler_invoked=True,scratch=str(wd),reason=str(e))
  (wd/'result.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state));raise SystemExit(1)
 (wd/'result.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
if __name__=='__main__':main()
