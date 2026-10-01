#!/usr/bin/env python3
"""Detached diagnostic follow-up; no adoption or full-token PASS from PC progress."""
import pathlib,json,time,os,hashlib,fcntl,subprocess,re,sys,datetime
BASE=pathlib.Path('/home/ubuntu/w17-watchdog-unchanged-20261001-r1')
Q=pathlib.Path('/tmp/claude-1000/queue')
receipt=json.loads((BASE/'launch.json').read_text())
def write(p,r):p.write_text(json.dumps(r,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(out):
 result={}
 for rank in range(4):
  expected=(pathlib.Path(receipt['image_root'])/f'r{rank}/expect_vm.hex').read_text().split()
  f=out/f'vm{rank}.hex'
  got=f.read_text().split() if f.exists() else []
  bad=[i for i,(x,y) in enumerate(zip(expected,got)) if int(x,16)!=int(y,16)]
  result[f'r{rank}']=dict(expected_words=len(expected),actual_words=len(got),mismatches=len(bad),first=bad[:8],exact=len(got)==len(expected) and not bad)
 return result
while not (BASE/'terminal.json').exists():time.sleep(15)
r=json.loads((BASE/'terminal.json').read_text());log=(BASE/'run.log').read_text()
pcs=[list(map(int,m.groups())) for m in re.finditer(r'pc (\d+) (\d+) (\d+) (\d+)',(BASE/'progress.log').read_text() if (BASE/'progress.log').exists() else '')]
advanced=any(all(p>9 for p in row) for row in pcs)
analysis=dict(diagnostic_terminal=r,all_ranks_advanced_beyond_pc9=advanced,vm=check(BASE),scope='PC progress is diagnostic only; exactness requires DONE all ranks and complete VM comparison',analysed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(BASE/'analysis.json',analysis)
# Acquire after original supervisor releases its exclusive lock; no overlapping L0.
lock=open(Q/'W17.L0.owner.lock','a+');fcntl.flock(lock,fcntl.LOCK_EX)
if not advanced:
 analysis['next_action']='HE internal progress probe against existing die0 archive: adapter load count/state, HCP active/run/output index, valid/last at5900 and10500; no repeat of this unchanged watchdog diagnostic'
 write(BASE/'analysis.json',analysis);write(Q/'W17.HE-progress-next.json',analysis)
 with open(Q/'W17.manifest','a') as f:f.write('\n# Unchangedbinary diagnostic did not advance all ranks beyondPC9; terminal analysed '+str(BASE/'analysis.json')+'; HE progress probe required, no fulltoken queued.\n')
 subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('he_progress_probe_20261001.py'))],check=False)
 sys.exit(0)
# Image-derived HE service envelope, diagnostic safety factor not performance calibration.
sys.path.insert(0,receipt['source']+'/tools')
from hdc_isa_v41 import decode
ops=[decode(int(w,16),full_shape=True) for w in (pathlib.Path(receipt['image_root'])/'r0/prog.hex').read_text().split()]
he=[int(d['he_k'])+((int(d['he_k'])+7)//8)*max(1,int(d['he_nout']))*max(1,int(d.get('mx_m',0))) for d in ops if d['unit']==5]
wd=max(11000,4*max(he or [10240])+128)
out=pathlib.Path('/home/ubuntu/w17-fulltoken-unchanged-20261001-r1');out.mkdir(exist_ok=False)
for base,key in [(pathlib.Path(receipt['source']),'source_sha256'),(pathlib.Path(receipt['image_root']),'image_record_sha256')]:
 for p,h in receipt[key].items():assert sha(base/p)==h,('pin drift',p)
assert sha(receipt['binary'])==receipt['binary_sha256']
for d in pathlib.Path('/proc').iterdir():
 if not d.name.isdigit():continue
 try:a=(d/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 assert not(a and a[0].endswith(b'/v41_die_rt')),('duplicate',d.name)
assert os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')>16*1024**3
command=['timeout','--signal=TERM','--kill-after=30s','28800s',receipt['binary'],receipt['image_root'],str(out),'200000']
full=dict(receipt,status='RESERVED',supervisor_pid=os.getpid(),command=command,environment=dict(RT_SKIP='1',RT_THREADS='16',RT_WATCHDOG=str(wd)),stall_window=dict(HE_min_cycles=he,formula='load chunks + ceil(chunks/HHW8)*outputs*positions',watchdog=wd,diagnostic_margin='4x max image HE service +128; conservative diagnostic envelope, not calibrated performance'),dependency=str(BASE/'analysis.json'))
write(out/'launch.json',full);write(Q/'W17.unchangedbinary-owner.json',full)
with open(Q/'W17.manifest','a') as f:f.write('\nlocal | auto after PC9 advance | EXCLUSIVE unchangedbinary fulltoken diagnostic WD'+str(wd)+' cycles200000 wall28800s; source '+receipt['source_commit']+' | '+str(out)+' | analysis.json | original watchdog terminal analysed, no L20 changes\n')
with open(out/'run.log','xb') as logf:
 p=subprocess.Popen(command,cwd=receipt['source'],env=dict(os.environ,**full['environment']),stdout=logf,stderr=subprocess.STDOUT,start_new_session=True)
 full.update(status='RUNNING',timeout_pid=p.pid);write(out/'launch.json',full);write(Q/'W17.unchangedbinary-owner.json',full)
 rc=p.wait()
full.update(status='TERMINAL',returncode=rc);write(out/'terminal.json',full)
vm=check(out);text=(out/'run.log').read_text();done=re.findall(r'DONE die=(\d+)',text)
final=dict(returncode=rc,done_ranks=sorted(set(done)),vm=vm,verdict='PASS_EXACT' if rc==0 and set(done)==set('0123') and all(v['exact'] for v in vm.values()) else 'FAIL_OR_INCOMPLETE',source_binding=str(out/'launch.json'),adopt=False)
write(out/'analysis.json',final);write(Q/'W17.unchangedbinary-owner.json',full)
with open(Q/'W17.manifest','a') as f:f.write('\n# unchangedbinary fulltoken terminal analysed '+final['verdict']+' '+str(out/'analysis.json')+'; no adoption.\n')
