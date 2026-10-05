import os,pathlib as P,subprocess as S,json,time,hashlib,shutil,re
paths=['/home/ubuntu/w19-production-recovery','/home/ubuntu/w19-production-protocol.vvp','/home/ubuntu/w19-vvp11','/home/ubuntu/w19-ivl11']
result={'timestamp':time.time(),'hostname':os.uname().nodename,'cpu_count':os.cpu_count(),'loadavg':os.getloadavg(),'root_free_bytes':shutil.disk_usage('/').free,'tmp_free_bytes':shutil.disk_usage('/tmp').free,'home_free_bytes':shutil.disk_usage('/home/ubuntu').free,'processes':[],'process_read_errors':[],'candidates':[],'manifests':[]}
mem={k:int(v.strip().split()[0])*1024 for k,v in (l.split(':',1) for l in P.Path('/proc/meminfo').read_text().splitlines())};result['mem_available_bytes']=mem['MemAvailable'];result['mem_total_bytes']=mem['MemTotal']
for d in P.Path('/proc').iterdir():
 if not d.name.isdigit():continue
 r={'pid':int(d.name),'links':[]}
 try:r['command']=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except FileNotFoundError:continue
 except PermissionError:result['process_read_errors'].append(str(d/'cmdline'));continue
 for key in ['cwd','exe','root']:
  try:r[key]=os.readlink(d/key);r['links'].append(r[key])
  except FileNotFoundError:pass
  except PermissionError:result['process_read_errors'].append(str(d/key))
 try:
  for fd in (d/'fd').iterdir():
   try:r['links'].append(os.readlink(fd))
   except FileNotFoundError:pass
   except PermissionError:result['process_read_errors'].append(str(fd))
  r['maps']=(d/'maps').read_text(errors='replace')
 except FileNotFoundError:pass
 except PermissionError:result['process_read_errors'].append(str(d))
 result['processes'].append(r)
ps=S.run(['docker','ps','-aq'],capture_output=True,text=True);result['docker_query_returncode']=ps.returncode;result['docker_error']=ps.stderr
if ps.returncode==0 and ps.stdout.split():
 ins=S.run(['docker','inspect',*ps.stdout.split()],capture_output=True,text=True);result['docker_inspect_returncode']=ins.returncode
 if ins.returncode==0:result['docker_containers']=[{'id':r['Id'],'name':r['Name'],'state':r['State'],'working_dir':r['Config'].get('WorkingDir'),'cmd':r['Config'].get('Cmd'),'mounts':r.get('Mounts'),'memory_limit':r['HostConfig'].get('Memory'),'nano_cpus':r['HostConfig'].get('NanoCpus')} for r in json.loads(ins.stdout)]
else:result['docker_inspect_returncode']=ps.returncode;result['docker_containers']=[]
for root in ['/tmp/claude-1000','/home/ubuntu']:
 if not P.Path(root).is_dir():continue
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in ['.git','node_modules','.cache','.local','.venv','.venvs']]
  for name in files:
   if 'manifest' not in name.lower() and not ('process' in name.lower() and name.endswith(('.json','.txt'))):continue
   f=P.Path(base)/name
   try:
    b=f.read_bytes();s=b.decode(errors='replace');host=('host |' in s or 'hosts' in s or 'pid' in s.lower() or 'cwd' in s or 'process' in s or f.suffix=='.manifest')
    result['manifests'].append({'path':str(f),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'host_process':host,'text':s if host else None})
   except (OSError,ValueError):continue
for p in paths:
 f=P.Path(p);r={'path':p,'exists':f.exists(),'symlink':f.is_symlink()}
 if f.exists():
  r['allocated_bytes']=int(S.check_output(['du','-s','-B1',p],text=True).split()[0])
  if f.is_dir():
   g=S.run(['git','-C',p,'rev-parse','--show-toplevel'],capture_output=True,text=True);r['git_top']=g.stdout.strip() if g.returncode==0 else None
   if r['git_top']==p:
    r['git_head']=S.check_output(['git','-C',p,'rev-parse','HEAD'],text=True).strip();r['git_status']=S.check_output(['git','-C',p,'status','--porcelain=v1','--untracked-files=all'],text=True);r['worktree_list']=S.check_output(['git','-C',p,'worktree','list','--porcelain'],text=True)
  r['files']=[]
  fs=list(f.rglob('*')) if f.is_dir() else [f]
  for x in fs:
   if x.is_file():r['files'].append({'relative':str(x.relative_to(f)) if f.is_dir() else x.name,'bytes':x.stat().st_size,'symlink':x.is_symlink()})
 result['candidates'].append(r)
result['tools']={name:shutil.which(name) for name in ['docker','git','python3','iverilog','vvp','verilator','yosys','openroad']}
result['docker_images']=S.run(['docker','images','--format','{{.Repository}}:{{.Tag}} {{.ID}}'],capture_output=True,text=True).stdout.splitlines()
print(json.dumps(result))
