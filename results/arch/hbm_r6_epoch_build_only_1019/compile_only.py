#!/usr/bin/env python3
"""Exact observer successor compile only. Never invoke the produced executable."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,tarfile,traceback,shutil
kit=Path(__file__).resolve().parent
root=Path(os.environ['OT_SCRATCH'])/'claude/hbm-r6-epoch-build-only-1019'
root.mkdir(parents=True,exist_ok=False)
os.chdir(root)
def emit(name,data):
 Path(name).write_text(json.dumps(data,indent=2)+'\n')
def sha(p):
 with open(p,'rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def status(phase,**kw):emit('STATUS.json',dict(phase=phase,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),pid=os.getpid(),root=str(root),**kw))
def check():
 expected=json.loads((kit/'original_snapshot_hashes.json').read_text());rows=[]
 for n,h in expected.items():
  if n=='generated_clockfix/tb.sv':h='8de7e47d5bde1d767a73fb3d1d2c88bb02f2dfe5366c9c25f6e31e1a1e927be3'
  actual=sha(n);assert actual==h,(n,actual,h);rows.append(dict(path=n,sha256=actual))
 return dict(verdict='PASS',files=len(rows),fixtures=307,selected=53,rows=rows)
try:
 status('STAGING')
 with tarfile.open(kit/'original_snapshot.tar')as t:t.extractall(root,filter='data')
 shutil.copy2(kit/'observer_tb.sv','generated_clockfix/tb.sv')
 shutil.copy2(kit/'tb_generate.py','tb_generate.f3cd6b6cc.py')
 assert sha('tb_generate.f3cd6b6cc.py')=='4f3f1f22730814317fb6a6ad2e0831789f251a488665897fbfe1553afdd19fb7'
 emit('preflight_source_fixture_audit.json',check())
 args=json.loads((kit/'compile_args.json').read_text())
 for i,a in enumerate(args):
  if a=='-y':Path(args[i+1]).mkdir(parents=True,exist_ok=True)
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 assert sha(tool.with_name('verilator_bin'))=='d3f42fa3b523cf1d7e38827134ac8560ac03b52466392eaf0001141ed4d9fe41'
 emit('resource_start.json',dict(host=os.uname().nodename,meminfo=Path('/proc/meminfo').read_text(),disk=shutil.disk_usage(root)._asdict(),threads=8,reserved_gb=320,additional_scratch_gb=60,cache='clean normal build; original obj_r6 untouched'))
 status('BUILDING',command=[str(tool)]+args)
 with open('build.log','wb')as log:
  rc=subprocess.run(['/usr/bin/time','-v','-o','resource_time.txt',str(tool)]+args,stdout=log,stderr=subprocess.STDOUT).returncode
 emit('postbuild_source_fixture_audit.json',check())
 if rc:status('FIRST_BUILD_FAILURE',exit_code=rc);sys.exit(rc)
 subprocess.run([sys.executable,'audit_consumed_sources.py','--mdir','obj_epoch','--output','consumed_source_audit.json'],check=True)
 baseline=json.loads((kit/'baseline_actual_consumption.json').read_text())['files'];actual=json.loads(Path('consumed_source_audit.json').read_text())['files']
 want={r['path']:r['sha256']for r in baseline};got={r['path']:r['sha256']for r in actual}
 want['generated_clockfix/tb.sv']='8de7e47d5bde1d767a73fb3d1d2c88bb02f2dfe5366c9c25f6e31e1a1e927be3'
 assert len(got)==47 and got==want,(len(got),set(got)^set(want))
 emit('actual_consumption_comparison.json',dict(verdict='PASS',actual=47,allowed=53,only_changed_input='generated_clockfix/tb.sv',files=got))
 excerpts=[]
 for f in sorted(Path('obj_epoch').glob('*.cpp')):
  lines=f.read_text().splitlines()
  indexes=[i for i,l in enumerate(lines)if 'observed_serial_edge' in l or 'observed_start_at_edge' in l]
  for i in indexes:
   excerpts.append(dict(file=f.name,line=i+1,context='\n'.join(lines[max(0,i-8):i+9])))
 emit('scheduler_observer_excerpts.json',dict(review='PENDING human generated active/NBA/negedge inspection',excerpts=excerpts))
 binary=Path('obj_epoch/Vtb');assert binary.is_file()
 emit('executable_receipt.json',dict(sha256=sha(binary),bytes=binary.stat().st_size,execution='NOT_INVOKED; separate numerical grant required',source_commit='f3cd6b6cc'))
 status('BUILD_ONLY_COMPLETE_NUMERICAL_NOT_AUTHORIZED',executable_sha256=sha(binary),scheduler_review='PENDING')
except BaseException as e:
 if not isinstance(e,SystemExit):
  Path('failure_traceback.txt').write_text(traceback.format_exc());status('FIRST_RUNNER_FAILURE',error=repr(e))
 raise
