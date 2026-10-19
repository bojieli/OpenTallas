from pathlib import Path
import subprocess,json,sys,hashlib
name=sys.argv[1];cid=sys.argv[2]
r=Path('/srv/opentallas-scratch/claude/ref_gate')/name
info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
assert info['Name']=='/gate_grt_'+name
assert any(m.get('Source')==str(r/'src') and m.get('Destination')=='/src' for m in info['Mounts'])
binding=json.loads(Path(str(r)+'.source_snapshot.json').read_text())
assert binding.get('remote_run')==str(r)
rec={'name':name,'container_id':cid,'source_commit':binding.get('commit'),'source_binding':binding,'container':info,'processes':subprocess.check_output(['docker','top',cid,'-eo','pid,ppid,etime,%cpu,rss,args'],text=True),'logs':{},'artifacts':{}}
for p in r.glob('routes/gate/work/orfs/logs/**/*cts*log'):
 rec['logs'][str(p)]=p.read_text(errors='replace')
p=r/'execution.log';rec['execution_clock_source_records']=[s for s in p.read_text(errors='replace').splitlines() if s.startswith(('GATE_SOURCE','GATE_TOOL','GATE_CK','GATE_PC'))]
for p in r.glob('routes/gate/work/orfs/results/**/*'):
 if p.is_file() and p.suffix in ['.odb','.v','.sdc']:
  rec['artifacts'][str(p)]={'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
print(json.dumps(rec,indent=1))
