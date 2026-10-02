#!/usr/bin/env python3
"""Single authorized run of unchanged9f9b capped runner; preserve first result."""
import hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/dsrom_l20_isolated_scale_execution_20261002'
GO_REV='9604860cae70ee78a34038a8f001aafbfffd92e0'
GO_PATH='results/rtl/parent_L20_isolated_scale_GO_20261002/GO.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not OUT.exists(),'First result already exists; no retry'
 go_bytes=subprocess.check_output(['git','show',GO_REV+':'+GO_PATH],cwd=ROOT)
 go=json.loads(go_bytes);runner=ROOT/'tools/dsrom_l20_scale_capped_runner.py'
 prep=ROOT/'results/uarch/dsrom_l20_scale_optin_preparation_20261002/preparation.json'
 assert sha(runner)==go['runner_sha256'] and sha(prep)==go['preparation_sha256']
 OUT.mkdir(parents=True);(OUT/'GO.json').write_bytes(go_bytes)
 shell=Path(tempfile.mkdtemp(prefix='l20-isolated-scale-resource-wrappers-'))
 tools={};env=os.environ.copy()
 for name in ['iverilog','vvp']:
  exe=Path(shutil.which(name));v=subprocess.run([str(exe),'-V'],capture_output=True,text=True)
  (OUT/(name+'_version.txt')).write_text(v.stdout+v.stderr)
  tools[name]={'path':str(exe),'binary_sha256':sha(exe),'version_exit':v.returncode,'version_file_sha256':sha(OUT/(name+'_version.txt'))}
  # GNUtime records actual child use. Original runner applies its limits to
  # this wrapper; limits propagate unchanged to the compiler/runtime.
  wrapper=shell/name
  wrapper.write_text('#!/bin/sh\nexec /usr/bin/time -v -o '+str(OUT/(name+'_resource.txt'))+' '+str(exe)+' "$@"\n')
  wrapper.chmod(0o700)
  tools[name]['resource_wrapper_sha256']=sha(wrapper)
 env['PATH']=str(shell)+os.pathsep+env['PATH']
 start=time.monotonic()
 p=subprocess.run(['python3',str(runner),'--compile-go',str(OUT/'GO.json')],cwd=ROOT,env=env,capture_output=True,text=True)
 (OUT/'runner_stdout.txt').write_text(p.stdout);(OUT/'runner_stderr.txt').write_text(p.stderr)
 state=json.loads(p.stdout.splitlines()[-1]) if p.stdout.strip().startswith('{') else {'status':'FAIL_RUNNER','stderr':p.stderr}
 scratch=Path(state['scratch']) if 'scratch' in state else None
 if scratch:
  for f in ['compile.log','simulate.log','result.json']:
   if (scratch/f).exists():shutil.copyfile(scratch/f,OUT/f)
 terminal=(OUT/'simulate.log').read_text().strip() if (OUT/'simulate.log').exists() else ''
 expected='PASS 21088 beats including full512 rows, sidebands, optoff equality, invalid fault'
 exact=terminal==expected and p.returncode==0 and state.get('status')=='PASS_ISOLATED_EXECUTED_FIXTURE_ONLY'
 record={'schema':'opentallas.dsrom.L20-isolated-quantizer-executed.v1','verdict':'PASS_ISOLATED_QUANTIZER_ONLY' if exact else 'FAIL_FIRST_RUN_NO_RETRY','terminal_exact_match':exact,'expected_terminal':expected,'actual_terminal':terminal,'runner_exit':p.returncode,'wall_seconds_including_compile_and_sim':time.monotonic()-start,'source_commit':'9f9b8e8e6b18731ee68bd74ac4907180a5eef5db','GO_pin':{'commit':GO_REV,'path':GO_PATH,'sha256':hashlib.sha256(go_bytes).hexdigest()},'runner_sha256':sha(runner),'preparation_sha256':sha(prep),'executor_sha256':sha(Path(__file__)),'tools':tools,'runner_result':state,'actual_workdir_bytes':sum(q.stat().st_size for q in scratch.rglob('*') if q.is_file()) if scratch else None,'scope':{'full_QE':False,'collector':False,'PnR':False,'reservation_credit':False,'full_token_credit':False,'SS_FF_credit':False,'full_FP32_exhaustive_credit':False},'files_sha256':{q.name:sha(q) for q in OUT.iterdir() if q.is_file()}}
 (OUT/'execution.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'verdict':record['verdict'],'terminal':terminal,'scratch':str(scratch),'wall_seconds':record['wall_seconds_including_compile_and_sim']}))
 if not exact:raise SystemExit(1)
if __name__=='__main__':main()
