#!/usr/bin/env python3
"""Run the pinned gold4 minimum integration gate; never regenerate golden inputs."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parent
S=R/'src'
G=pathlib.Path('/srv/opentallas-scratch/claude/dsrom-fh-close/slices/fused-gold4')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def resources():
 m={l.split(':')[0]:int(l.split()[1])*1024 for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemTotal:','MemAvailable:','MemFree:'))}
 d=os.statvfs(R)
 return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),load=list(os.getloadavg()),cpus=os.cpu_count(),memory_bytes=m,disk_available_bytes=d.f_bavail*d.f_frsize)
def save(name,data):(R/name).write_text(json.dumps(data,indent=2)+'\n')
save('resources_after_admission.json',resources())
m=resources();assert m['load'][0]+16<=3*m['cpus'];assert m['memory_bytes']['MemAvailable']>=16*2**30+max(32*2**30,.1*m['memory_bytes']['MemTotal'])
pin=json.loads((R/'source_pin.json').read_text())
for p,h in pin['local_source_hashes'].items():assert sha(S/p)==h,p
assert not (R/'safe2').exists() and not (R/'safe1').exists(), 'Fresh build directories required; inspect/reuse existing job instead'
before=inventory(G);save('golden_before.json',before)
manifest=json.loads((G/'manifest.json').read_text());assert manifest['prompt']=='gold4' and manifest['gamma']==5
assert len(manifest['slices'])==1 and manifest['slices'][0]['name']=='draft_1'
env=os.environ.copy();env['PATH']='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:'+env['PATH']
save('tool_versions.json',{'verilator':subprocess.check_output(['verilator','--version'],env=env,text=True).strip(),'python':sys.version})
rows=[]
for level in [2]:
 cmd=['python3','tools/dsrom_fused_draft_head.py','run','--capture-cut','--capture-return-extra','6','--fault-retire','--checked-permission','--margin','--safe','--safe-level',str(level),'--fpipe-level','3','--slices',str(G),'--run-dir',str(R/f'safe{level}'),'--jobs','16']
 save(f'command_safe{level}.json',{'cwd':str(S),'argv':cmd,'source_commit':pin['source_commit'],'source_pin_sha256':sha(R/'source_pin.json')})
 t=time.time()
 with (R/f'safe{level}.build.log').open('w') as log:
  rc=subprocess.run(['/usr/bin/time','-v',*cmd],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 row=dict(safe=level,fpipe=3,returncode=rc,wall_seconds=time.time()-t)
 save(f'safe{level}.terminal.json',row);rows.append(row)
 # A compiler error is infrastructure evidence, not a numerical result.
 if not (R/f'safe{level}/result.json').exists():break
 save('progress.json',rows)
after=inventory(G);save('golden_after.json',after);assert before==after,'Golden inputs changed during the campaign'
save('resources_after.json',resources())
save('campaign_terminal.json',{'runs':rows,'golden_unchanged':True,'source_commit':pin['source_commit'],'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(json.dumps(rows),flush=True)
