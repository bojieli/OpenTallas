import hashlib,json,os,resource,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path('/home/ubuntu/w18work/main_gate_4033c6b12_src'); RUN=Path(__file__).resolve().parent; OUT=RUN/'evidence'
assert (OUT/'completion.json').exists() and not (RUN/'live.json').exists()
pre=json.loads((OUT/'preflight.json').read_text())
def limited():
 os.sched_setaffinity(0,set(pre['affinity_cpus']));os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
base=['python3',str(ROOT/'tools/w18/hash_parallel_gate.py'),'--baseline',str(OUT/'baseline_full.json'),'--exhaustive-record',str(OUT/'exhaustive.json'),'--exhaustive-log',str(OUT/'exhaustive.log')]
cmd=['/usr/bin/time','-v','-o',str(OUT/'reconciliation_cached.resources.log'),'timeout','--kill-after=20s','120s',*base,'--output',str(OUT/'reconciliation_cached.json')]
with (OUT/'reconciliation_cached.log').open('x') as f:
 r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,preexec_fn=limited)
assert r.returncode==0
negative=[]
with tempfile.TemporaryDirectory(prefix='w18_main_provenance_') as d:
 sandbox=Path(d)
 for s in pre['sources']:
  p=sandbox/s;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/s,p)
 cases=[('stale_rtl',pre['main_rtl_inputs'][0]),('stale_bench','rtl/test/tb_chip_v41x_karb_local_hash_parallel.sv')]
 for name,s in cases:
  p=sandbox/s;original=p.read_bytes();p.write_bytes(original+b'\n// intentional provenance rejection regression\n')
  cmd=[*base];cmd[1]=str(sandbox/'tools/w18/hash_parallel_gate.py');cmd+=['--output',str(OUT/(name+'_must_not_exist.json'))]
  r=subprocess.run(cmd,cwd=sandbox,env=env,capture_output=True,text=True,timeout=30,preexec_fn=limited)
  (OUT/(name+'.log')).write_text(r.stdout+r.stderr)
  assert r.returncode!=0 and 'Exhaustive provenance mismatch: sources' in r.stderr and not Path(cmd[-1]).exists()
  negative.append(dict(name=name,changed_source=s,returncode=r.returncode,output_exists=False,command=cmd));p.write_bytes(original)
 changed=OUT/'changed_log_negative_input.log';changed.write_bytes((OUT/'exhaustive.log').read_bytes()+b'\n')
 cmd=[*base];cmd[-1]=str(changed);cmd+=['--output',str(OUT/'changed_log_must_not_exist.json')]
 r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30,preexec_fn=limited)
 (OUT/'changed_log.log').write_text(r.stdout+r.stderr)
 assert r.returncode!=0 and 'Exhaustive log digest mismatch' in r.stderr and not Path(cmd[-1]).exists()
 negative.append(dict(name='changed_log',returncode=r.returncode,output_exists=False,command=cmd))
(OUT/'cli_provenance_negative.json').write_text(json.dumps(dict(source_commit=pre['source_commit'],tests=negative,pass_=True),indent=1)+'\n')
print('cached PASS; stale RTL, stale bench and changed log rejected')
