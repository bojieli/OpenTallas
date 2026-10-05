import datetime,hashlib,importlib.util,json,os,resource,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/home/ubuntu/w18work/main_gate_4033c6b12_src')
RUN=Path('/home/ubuntu/w18work/main_gate_4033c6b12_run')
OUT=RUN/'evidence';OUT.mkdir(exist_ok=False)
assert not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip()
spec=importlib.util.spec_from_file_location('driver',ROOT/'tools/rtl_chip_v41x_karb_local.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=list(dict.fromkeys([*g.SOURCES,'tools/w18/hash_parallel_gate.py','rtl/test/tb_chip_v41x_karb_local_hash_parallel.sv']))
before={p:sha(ROOT/p) for p in inputs}
mem={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
disk=shutil.disk_usage(RUN)
assert mem['MemAvailable']>16*1024**3 and disk.free>8*1024**3
ver=subprocess.run([g.VERILATOR,'--version'],capture_output=True,text=True,check=True)
pre=dict(source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),source_root=str(ROOT),sources=before,main_rtl_inputs=g.KARB_RTL,mem_available_bytes=mem['MemAvailable'],disk_free_bytes=disk.free,load_average=os.getloadavg(),affinity_cpus=sorted(os.sched_getaffinity(0))[-4:],jobs=2,per_process_address_space_limit_bytes=8*1024**3,stage_timeout_seconds=2400,verilator=dict(path=g.VERILATOR,sha256=sha(g.VERILATOR),version=ver.stdout.strip()),observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runner_sha256=sha(Path(__file__)))
(OUT/'preflight.json').write_text(json.dumps(pre,indent=1)+'\n')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
status=[]
def bounded(cmd,name):
 def limits():
  os.sched_setaffinity(0,set(pre['affinity_cpus']));os.nice(10)
  resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
  resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))
 full=['/usr/bin/time','-v','-o',str(OUT/(name+'.resources.log')),'timeout','--kill-after=20s','2400s',*cmd]
 with (OUT/(name+'.log')).open('x') as log:
  p=subprocess.Popen(full,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
  (RUN/'live.json').write_text(json.dumps(dict(stage=name,pid=p.pid,cmd=full))+'\n')
  print(name,'PID',p.pid,flush=True);rc=p.wait()
 status.append(dict(stage=name,command=cmd,returncode=rc))
 print(name,'rc',rc,flush=True)
 return rc
baseline=OUT/'baseline_full.json'
bounded(['python3','tools/rtl_chip_v41x_karb_local.py','--jobs','2','--keep',str(RUN/'baseline_build'),'--output',str(baseline)],'baseline_full')
if not baseline.exists():
 (OUT/'orchestration_failure.json').write_text(json.dumps(dict(stages=status,reason='baseline produced no terminal record; no reconciliation launched'),indent=1)+'\n');raise SystemExit(1)
bounded(['python3','tools/w18/hash_parallel_gate.py','--baseline',str(baseline),'--exhaustive-record',str(OUT/'exhaustive.json'),'--output',str(OUT/'reconciliation_fresh.json')],'reconciliation_fresh')
after={p:sha(ROOT/p) for p in inputs}
(OUT/'completion.json').write_text(json.dumps(dict(stages=status,source_pins_unchanged=after==before,sources_after=after,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),adoption=False,claim='Functional results for pinned main 4033c6b12 only; historical physical verdicts unchanged'),indent=1)+'\n')
(RUN/'live.json').unlink(missing_ok=True)
