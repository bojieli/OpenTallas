"""No elapsed-time limit; preserve producer logs, incremental pages and memory evidence."""
import hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-qwen-trained-conversion-pve1');job=Path('/home/ubuntu/otjobs/qwen-trained-byte-conversion-pve1-20261002-r1');out=job/'images';admission=job/'GO.json';go=json.loads(admission.read_text());go_commit=(job/'GO.commit').read_text().strip();python='/home/ubuntu/.local/qwen-trained-provider-pve1/bin/python';snapshot=go['checkpoint_snapshot']
argv=[python,'tools/qwen_trained_byte_provider.py','--snapshot',snapshot,'--out',str(out),'--admission',str(admission),'--go-commit',go_commit];started=time.monotonic();record=dict(schema='opentallas.Qwen.trained-byte-conversion.run.v1',source_commit=go['source_commit'],GO_commit=go_commit,argv=argv,wall_limit=None,FSIZE='unlimited',RLIMIT_AS='unlimited',oracle_callbacks=0,actual_RTL=False)
(job/'run_start.json').write_text(json.dumps(record,indent=2)+'\n');base=Path('/sys/fs/cgroup')/next(x.split(':',2)[2]for x in Path('/proc/self/cgroup').read_text().splitlines()if x.startswith('0::')).lstrip('/')
with(job/'actual_producer.log').open('xb')as log,(job/'memory.jsonl').open('x')as mem:
 p=subprocess.Popen(argv,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 while True:
  sample=dict(elapsed_s=time.monotonic()-started,counters={})
  for name in ('memory.current','memory.peak','memory.events'):
   try:sample['counters'][name]=(base/name).read_text().strip()
   except OSError:sample['counters'][name]='unavailable'
  mem.write(json.dumps(sample)+'\n');mem.flush()
  rc=p.poll()
  if rc is not None:break
  if not set(os.sched_getaffinity(p.pid))<=set(go['cpus']):raise RuntimeError('producer affinity escaped admitted mask')
  time.sleep(5)
record.update(exit_code=rc,elapsed_s=time.monotonic()-started,producer_log_sha256=hashlib.sha256((job/'actual_producer.log').read_bytes()).hexdigest(),memory_terminal=sample['counters'],verdict='FAIL_INCOMPLETE')
manifest=out/'manifest.json'
if rc==0 and manifest.is_file():
 m=json.loads(manifest.read_text());record.update(verdict='PASS_COMPLETE_CHECKPOINT_BYTE_PRODUCTION_ONLY',manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),extents=len(m['images']),image_bytes=sum(x['bytes']for x in m['images'].values()))
(job/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(rc if rc else (0 if record['verdict'].startswith('PASS_')else 1))
