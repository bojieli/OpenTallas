#!/usr/bin/env python3
"""Root-readable /proc + Docker + active launcher audit; never signals or deletes."""
import datetime,json,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent;paths=json.loads((R/'candidate-paths.json').read_text());hits={p:[] for p in paths};errors=[];broad=[];aliases={p:{p} for p in paths}
def under(value,root):return value==root or value.startswith(root.rstrip('/')+'/')
try:
 ids=subprocess.check_output(['docker','ps','-aq'],text=True).split();containers=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)) if ids else []
 for c in containers:
  for m in c.get('Mounts',[]):
   source=m.get('Source','');dest=m.get('Destination','')
   for p in paths:
    if under(source,p):hits[p].append(dict(kind='docker_bind',container=c['Id'],name=c.get('Name'),source=source,state=c['State'].get('Status')))
    elif under(p,source) and source:
     alias=dest.rstrip('/')+p[len(source):];aliases[p].add(alias);broad.append(dict(candidate=p,container=c['Id'],source=source,destination=dest,candidate_alias=alias))
except (OSError,ValueError,subprocess.SubprocessError) as e:errors.append('Docker inspection failed: '+type(e).__name__)
checks=dict(processes=0,cwd_links=0,root_links=0,fd_links=0,map_files=0,command_lines=0,active_launcher_sources=0)
launchers=set()
def inspect(value,pid,kind):
 for p,aa in aliases.items():
  if any(under(value.removesuffix(' (deleted)'),a) for a in aa):hits[p].append(dict(kind=kind,pid=pid,path=value))
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 pid=int(proc.name);checks['processes']+=1
 try:
  s=(proc/'stat').read_text();a=s[s.rindex(')')+2:].split();state=a[0]
  if state=='Z':continue
  for field in ['cwd','root','exe']:
   try:value=os.readlink(proc/field);inspect(value,pid,'process_'+field);checks['cwd_links' if field=='cwd' else 'root_links']+=1
   except FileNotFoundError:pass
  raw=(proc/'cmdline').read_bytes();args=[x.decode(errors='replace') for x in raw.split(b'\0') if x];checks['command_lines']+=1
  for value in (proc/'environ').read_bytes().split(b'\0'):
   for candidate in paths:
    if candidate.encode() in value:hits[candidate].append(dict(kind='environment_future_dependency',pid=pid))
  for value in args:
   for p,aa in aliases.items():
    if any(alias in value for alias in aa):hits[p].append(dict(kind='command_reference',pid=pid))
  cwd=os.readlink(proc/'cwd')
  for arg in args:
   if arg.endswith(('.sh','.py')) and ' ' not in arg:
    path=Path(arg) if arg.startswith('/') else Path(cwd)/arg
    if path.is_file() and path.stat().st_size<1048576:launchers.add(path)
  for fd in (proc/'fd').iterdir():
   try:inspect(os.readlink(fd),pid,'open_fd');checks['fd_links']+=1
   except FileNotFoundError:pass
  for line in (proc/'maps').read_text().splitlines():
   aa=line.split(None,5)
   if len(aa)>5:inspect(aa[5],pid,'memory_map')
  checks['map_files']+=1
 except (FileNotFoundError,ProcessLookupError):pass
 except PermissionError:errors.append('Unreadable live process '+str(pid))
 except OSError as e:
  if e.errno not in [2,3,22]:errors.append('Process audit OS error '+str(pid)+':'+str(e.errno))
source_refs=[]
for path in launchers:
 try:
  data=path.read_text(errors='replace');checks['active_launcher_sources']+=1
  for candidate in paths:
   if candidate in data:hits[candidate].append(dict(kind='active_launcher_future_dependency',launcher=str(path)))
 except OSError:errors.append('Active launcher unreadable: '+str(path))
# Read queue manifests and structured handoffs; retained historical references need explicit classification.
manifest_refs=[]
for f in Path('/tmp/claude-1000/queue').rglob('*'):
 if not f.is_file() or f.suffix not in ['.manifest','.json','.sh'] or R in f.parents:continue
 try:
  if f.stat().st_size>1048576:continue
  for n,line in enumerate(f.read_text(errors='replace').splitlines(),1):
   for candidate in paths:
    if candidate in line:manifest_refs.append(dict(candidate=candidate,path=str(f),line=n,text=line[:1500]))
 except OSError:errors.append('Queue record unreadable: '+str(f))
print(json.dumps(dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,candidate_hits=hits,errors=errors,docker_ancestor_mounts=broad,manifest_references=manifest_refs,root_readable_proc=True),indent=2))
