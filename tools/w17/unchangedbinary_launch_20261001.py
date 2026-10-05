import os,json,hashlib,pathlib,subprocess,datetime,fcntl
out=pathlib.Path('/home/ubuntu/w17-watchdog-unchanged-20261001-r1')
queue=pathlib.Path('/tmp/claude-1000/queue')
lock=open(queue/'W17.L0.owner.lock','a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
src=pathlib.Path('/tmp/claude-1000/wt/w17-fs'); images=pathlib.Path('/home/ubuntu/w17work/die/ctx1048576_s20260930'); binary=pathlib.Path('/home/ubuntu/w17work/dierun2/v41_die_rt')
old=json.load(open('/home/ubuntu/w17work/dierun2/out_l0a/result.json'))
errors=[]
for base,key in [(src,'source_sha256'),(images,'image_record_sha256')]:
 for p,h in old[key].items():
  if sha(base/p)!=h:errors.append(str(base/p))
assert sha(binary)==old['host_binary_sha256'],'binary drift'
assert not errors,errors
assert subprocess.check_output(['git','-C',str(src),'status','--porcelain']).strip()==b''
for d in pathlib.Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:a=(d/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 assert not (a and a[0].endswith(b'/v41_die_rt')),('duplicate binary',d.name)
assert os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')>16*1024**3
cmd=['timeout','--signal=TERM','--kill-after=30s','2400s',str(binary),str(images),str(out),'12000']
record=dict(owner='codex/w17-stall-bounded',status='RESERVED',supervisor_pid=os.getpid(),source_commit=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip(),source=str(src),binary=str(binary),binary_sha256=sha(binary),image_root=str(images),source_sha256=old['source_sha256'],image_record_sha256=old['image_record_sha256'],command=cmd,environment=dict(RT_SKIP='1',RT_THREADS='16',RT_WATCHDOG='11000'),started=datetime.datetime.now(datetime.timezone.utc).isoformat(),protected=[str(src),str(binary.parent),str(images)],scope='unchanged historical binary watchdog diagnostic; no full-token qualification')
handoff=queue/'W17.unchangedbinary-owner.json'
def save():
 (out/'launch.json').write_text(json.dumps(record,indent=2)+'\n');handoff.write_text(json.dumps(record,indent=2)+'\n')
save()
with open(queue/'W17.manifest','a') as f:f.write('\nlocal | '+record['started']+' | EXCLUSIVE L0 owner codex/w17-stall-bounded reserved unchangedbinary watchdog12000 WD11000 threads16 wall2400s source d2e629028; handoff W17.unchangedbinary-owner.json | '+str(out)+' | terminal.json | no existing local v41_die_rt; preserve source/binary/images until terminal\n')
with open(out/'run.log','xb') as log:
 p=subprocess.Popen(cmd,cwd=src,env=dict(os.environ,**record['environment']),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 record.update(status='RUNNING',timeout_pid=p.pid);save()
 rc=p.wait()
record.update(status='TERMINAL',returncode=rc,finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),binary_unchanged=sha(binary)==record['binary_sha256'])
(out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');save()
with open(queue/'W17.manifest','a') as f:f.write('\n# W17 unchangedbinary diagnostic terminal rc='+str(rc)+' evidence '+str(out/'terminal.json')+'; old failure unchanged.\n')
