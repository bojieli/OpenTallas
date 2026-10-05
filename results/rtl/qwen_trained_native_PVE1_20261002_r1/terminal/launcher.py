"""Pinned full checkpoint native token runner; observer sampling only."""
import json,subprocess,time,hashlib,os,signal
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-qwen-trained-native-execution');job=Path('/home/ubuntu/otjobs/qwen-trained-native-token-pve1-20261002-r1');go=json.loads((job/'GO.json').read_text());gc=(job/'GO.commit').read_text().strip();started=time.monotonic()
argv=['/home/ubuntu/.local/qwen-trained-provider-pve1/bin/python','-u','tools/qwen_bounded_trained_driver.py','--images',go['qualified_images']['images'],'--out',str(job/'native'),'--admission',str(job/'GO.json'),'--go-commit',gc,'--token','9707']
record=dict(schema='opentallas.Qwen.full-trained-native-supervisor.v1',source_commit=go['source_commit'],GO_commit=gc,argv=argv,wall_limit=None,FSIZE='unlimited',RLIMIT_AS='unlimited',actual_RTL=False,oracle_callbacks=0)
(job/'run_start.json').write_text(json.dumps(record,indent=2)+'\n');cg=Path('/sys/fs/cgroup')/next(x.split(':',2)[2]for x in Path('/proc/self/cgroup').read_text().splitlines()if x.startswith('0::')).lstrip('/')
with(job/'actual_native.log').open('xb')as log,(job/'resources.jsonl').open('x')as samples:
 p=subprocess.Popen(argv,cwd=root,stdout=log,stderr=subprocess.STDOUT);reason=None
 try:
  while True:
   sample=dict(elapsed_s=time.monotonic()-started,counters={})
   for name in ('memory.current','memory.peak','memory.events'):
    try:sample['counters'][name]=(cg/name).read_text().strip()
    except OSError:sample['counters'][name]='unavailable'
   v=os.statvfs(job);sample['disk_available_bytes']=v.f_bavail*v.f_frsize;sample['job_bytes']=sum(x.stat().st_size for x in job.rglob('*')if x.is_file());samples.write(json.dumps(sample)+'\n');samples.flush();rc=p.poll()
   if rc is not None:break
   if not set(os.sched_getaffinity(p.pid))<=set(go['cpus']):reason='AFFINITY_ESCAPE'
   if sample['disk_available_bytes']<go['disk_headroom_bytes']:reason='ACTUAL_DISK_HEADROOM_EXHAUSTED'
   if sample['job_bytes']>go['aggregate_output_bytes']:reason='ACTUAL_AGGREGATE_OUTPUT_EXHAUSTED'
   if reason:p.terminate();rc=p.wait();break
   time.sleep(10)
 except BaseException:
  p.terminate();p.wait();raise
terminal=job/'native/terminal.json';native=json.loads(terminal.read_text())if terminal.is_file()else None
record.update(exit_code=rc,elapsed_s=time.monotonic()-started,termination_reason=reason,native_terminal=native,native_terminal_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest()if terminal.is_file()else None,actual_native_log_sha256=hashlib.sha256((job/'actual_native.log').read_bytes()).hexdigest(),resources_terminal=sample,verdict='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED'if rc==0 and native and native['verdict']=='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED'else'FAIL_INCOMPLETE')
(job/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['verdict'].startswith('PASS_')else 1)
