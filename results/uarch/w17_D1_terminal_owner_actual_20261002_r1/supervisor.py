import json,hashlib,subprocess,os,resource,time,shutil,fcntl,datetime,sys
from pathlib import Path
ROOT=Path('/tmp/opentallas-D1-terminal-program-binding-model-20261002')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.w17_D1_terminal_owner_plan import sha,validate
P=ROOT/'results/uarch/w17_D1_terminal_program_binding_model_20261002/plan.json'
plan=json.loads(P.read_text());GO=json.loads((OUT/'authorization.json').read_text())
assert GO['approved'] and GO['source_commit']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
assert GO['plan_SHA256']==sha(P)
script=P.parent/'capture_terminal.gdb';assert GO['script_SHA256']==sha(script)
assert GO['binary_SHA256']==sha(plan['binary']['path']) and GO['program_SHA256']==sha(plan['program']['path'])
lease=open('/tmp/w17-D1-terminal-owner-capture-20261002-r1.lock','w')
fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
for lim in (resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE):
 assert resource.getrlimit(lim)==(-1,-1), 'restrictive inherited limit'
assert 8 in os.sched_getaffinity(0);os.sched_setaffinity(0,{8})
validate(P)
avail=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
assert avail>=(96+32+16)*2**30
assert shutil.disk_usage(OUT).free>=16*2**30
inputs={str(P):sha(P),str(script):sha(script),str(OUT/'authorization.json'):sha(OUT/'authorization.json'),str(Path(__file__)):sha(__file__)}
for k in ['binary','program','header','GDB']:inputs[plan[k]['path']]=sha(plan[k]['path'])
argv=[x.replace('SOURCE_ROOT',str(ROOT)) for x in plan['run_argv']]
receipt={'status':'STARTED','scope':plan['scope'],'source_commit':GO['source_commit'],'supervisor_PID':os.getpid(),'argv':argv,'inferior_argv':GO['required_argv'],'input_hashes':inputs,'admission':{'available_memory':avail,'reservation96_host32_peer16_bytes':144*2**30,'free_disk':shutil.disk_usage(OUT).free,'CPU':[8],'capacity_not_limits':True},'wall_limit':None,'AS_limit':None,'CPU_time_limit':None,'FS_limit':None,'MemoryMax':None,'replays':1,'fulltoken':False,'RTL_fidelity':'UNPROVEN','service_bound':'BOUND_MISSING','start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
save();t=time.monotonic()
try:
 with (OUT/'gdb.log').open('xb') as log:
  child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,cwd=Path(plan['binary']['path']).parent)
  receipt['GDB_PID']=child.pid;save();print(json.dumps({'supervisor_PID':os.getpid(),'GDB_PID':child.pid,'output':str(OUT)}),flush=True)
  code=child.wait()
 receipt.update(GDB_exit=code,wall_s=time.monotonic()-t,status='TERMINAL_CAPTURE_PENDING_OFFLINE_ATTRIBUTION',log_SHA256=sha(OUT/'gdb.log'))
except Exception as exc:receipt.update(status='FAIL_PRESERVED',error=str(exc));raise
finally:
 receipt['input_postchecks']={path:sha(path)==expected for path,expected in inputs.items()}
 if not all(receipt['input_postchecks'].values()):receipt['status']='FAIL_INPUT_POSTCHECK'
 receipt['terminal_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
