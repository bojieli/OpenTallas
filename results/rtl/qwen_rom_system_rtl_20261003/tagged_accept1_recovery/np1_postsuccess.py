from pathlib import Path
import fcntl,json,os,subprocess,time,traceback
R=Path('/srv/opentallas-scratch/jobs/laplace-qwen-tagged-accept1-a60af57e4-r1')
S=Path('/srv/opentallas/repos/laplace-qwen-runtime-f6c5e4af1')
P=Path('/srv/opentallas-scratch/codex/qwen-tagged-P8191-np1-inputs-r1/plan')
Q=R/'top_resume_r2'
O=Q/'np1_continuation';O.mkdir(exist_ok=True)
lock=(O/'sole.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def status(phase,**kw):
 q=O/'state.tmp';q.write_text(json.dumps(dict(phase=phase,pid=os.getpid(),**kw),indent=2)+'\n');q.replace(O/'state.json')
def call(name,cmd):
 (O/(name+'.command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 with (O/(name+'.log')).open('x') as log:
  p=subprocess.Popen(cmd,cwd=S,stdout=log,stderr=subprocess.STDOUT);status(name,child=p.pid);rc=p.wait()
 (O/(name+'.exit')).write_text(str(rc)+'\n')
 if rc:raise RuntimeError(f'{name} exit {rc}')
try:
 status('WAIT_EXISTING_BUILD',supervisor=931445)
 while not (Q/'access.exit').exists():
  for name in ('die_model','die_compile'):
   p=Q/(name+'.exit')
   if p.exists() and int(p.read_text())!=0:raise RuntimeError(f'existing {name} failed; no retry')
  if not Path('/proc/931445').exists():raise RuntimeError('build supervisor gone without access terminal')
  time.sleep(10)
 if int((Q/'access.exit').read_text())!=0:raise RuntimeError('existing access failed; no retry')
 reuse='/srv/opentallas-scratch/claude/realmem/build_v2'
 coll='/srv/opentallas-scratch/jobs/russell-qwen-rom-combined-r1/build/coll'
 hook=S/'tools/runtime/qwen_combined/stream4_tagged_rows_hook.cpp'
 cmd=['/srv/opentallas-scratch/admit.sh','24','--','python3',str(S/'tools/qwen_rom_combined_stream4_link.py'),'--dspark','--die-build',str(R/'build/die'),'--hbm-build',str(R/'build/hbm'),'--coll-build',coll,'--reuse-build',reuse,'--baseline','/srv/opentallas-scratch/claude/realmem/runs/real2_p255.json','--compiled-params',str(R/'compiled_params.json'),'--verilator-root','/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator','--out',str(R/'np1_link'),'--native-tagged-source',str(hook),'--native-tagged-sha256','cb779e8b239164b8a61556c5c729e14d78740d6afefd89b68228ffcba46c21ee']
 call('link',cmd)
 inputs=json.loads((P/'inputs.json').read_text())
 cmd=['/srv/opentallas-scratch/admit.sh','48','--',str(R/'np1_link/qwen_rom_combined'),'--stages',str(P/'stages.txt'),str(R/'np1_run'),inputs['preload'],'--pos','8191','--token','24','--kv-dir',inputs['history'],'--kv-ideal','0','--core-period-fs','833333','--core-first-rise-fs','416666','--service-period-fs','1024000','--service-first-rise-fs','512000']
 call('runtime',cmd);status('RUNTIME_EXIT0_NUMERICAL_COMPARISON_PENDING')
except Exception as e:
 status('FAIL_PRESERVED',error=str(e),traceback=traceback.format_exc());raise
