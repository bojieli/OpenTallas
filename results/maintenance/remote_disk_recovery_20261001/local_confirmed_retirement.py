import pathlib as P,json,os,subprocess as S,time,hashlib,tarfile,re,shutil
out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/remote_disk_recovery_20261001');main='/home/ubuntu/OpenTallas';w10=json.load(open(out/'W10.cleanup-handoff.json'));w11=json.load(open(out/'W11.w11land-retirement-confirmed.json'));actions=[];remote=[]
for f in out.glob('*_probe_raw.json'):
 r=json.load(open(f));assert not r['process_read_errors'];assert r['docker_query_returncode']==r['docker_inspect_returncode']==0;remote.append((f.name,r))
assert len(remote)==9,'all9remote probes required'
# Validate the owner archive against all currently-present original metadata files.
verified=[]
with tarfile.open(w10['light_archive'],'r:gz') as tar:
 for m in tar.getmembers():
  if not m.isfile():continue
  source=P.Path('/home/ubuntu/w10qjobs')/m.name
  assert '..' not in P.Path(m.name).parts,'unsafe archive path'
  b=tar.extractfile(m).read();sha=hashlib.sha256(b).hexdigest()
  assert not source.exists() or hashlib.sha256(source.read_bytes()).hexdigest()==sha,'owner archive stale '+str(source)
  verified.append({'archive_member':m.name,'sha256':sha,'source_verified_if_exists':True})
(out/'w10_archive_member_validation.json').write_text(json.dumps(verified,indent=2)+'\n')
for label,pin in [('w10',w10['source_pin']),('w11','12f5d457')]:
 full=S.check_output(['git','-C',main,'rev-parse',pin+'^{commit}'],text=True).strip();ref='refs/maintenance/remote-recovery-20261001/local-'+label+'-source';S.run(['git','-C',main,'update-ref',ref,full,'0'*40],check=True)
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(P.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
def proc_hits(rows,path):
 return [r['pid'] for r in rows if r['pid'] not in anc and (re.search(re.escape(path)+r'(?=$|[\s/\"\'])',r.get('cmd',r.get('command',''))) or any(x==path or x.startswith(path+'/') for x in r['links']) or path+'/' in r.get('maps',''))]
def docker_current():
 ps=S.run(['docker','ps','-aq'],capture_output=True,text=True);assert ps.returncode==0,ps.stderr
 if not ps.stdout.split():return []
 ins=S.run(['docker','inspect',*ps.stdout.split()],capture_output=True,text=True);assert ins.returncode==0,ins.stderr
 return [{'id':x['Id'],'state':x['State'],'working_dir':x['Config'].get('WorkingDir',''),'cmd':x['Config'].get('Cmd'),'mounts':x.get('Mounts',[])} for x in json.loads(ins.stdout)]
def docker_hits(cs,path):
 hits=[]
 for c in cs:
  if not c['state'].get('Running'):continue
  cwd=c.get('working_dir','');cmd=' '.join(c.get('cmd') or [])
  if cwd==path or cwd.startswith(path+'/') or re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(m.get('Source','')==path or m.get('Source','').startswith(path+'/') for m in c['mounts']):hits.append(c['id'])
 return hits
free=lambda:os.statvfs(main).f_bavail*os.statvfs(main).f_frsize
for path in [w11['path'],*w10['retire']]:
 p=P.Path(path);r={'path':path,'timestamp':time.time(),'owner_clearance':'W11 entire legacy checkpoint' if path==w11['path'] else 'W10 explicit child list'};actions.append(r)
 try:
  assert p.is_dir() and not p.is_symlink(),'absent/symlink';assert not (p/'.git').exists(),'source worktree unexpectedly'
  if path!=w11['path']:assert p.parent==P.Path('/home/ubuntu/w10qjobs/work') and p.name!='c8','not exact child or protectedc8'
  snap=json.loads(S.check_output(['sudo','-n','python3','/tmp/disk-recovery-proc.py'],text=True));assert not snap['errors'];cs=docker_current();r['local_process_hits']=proc_hits(snap['rows'],path);r['local_docker_hits']=docker_hits(cs,path)
  assert not r['local_process_hits'] and not r['local_docker_hits'],'local live'
  r['remote_process_docker_hits']={host:{'process':proc_hits(s['processes'],path),'docker':docker_hits(s['docker_containers'],path)} for host,s in remote}
  assert not any(x['process'] or x['docker'] for x in r['remote_process_docker_hits'].values()),'remote live reference'
  r['manifest_mentions']=[{'manifest':f.name,'lines':[l for l in f.read_text(errors='replace').splitlines() if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',l)]} for f in out.glob('local_queue_*.manifest.txt') if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',f.read_text(errors='replace'))]
  r['manifest_review']='Latest owner explicit retirement supersedes historical references; all current process/Docker references checked.'
  r['evidence_preservation']='w11_evidence_preservation.json' if path==w11['path'] else 'w10_evidence_preservation.json'
  r['files']=[{'relative':str(f.relative_to(p)),'bytes':f.stat().st_size} for f in p.rglob('*') if f.is_file()]
  r['allocated_bytes']=int(S.check_output(['du','-s','-B1',path],text=True).split()[0]);r['free_before']=free()
  with open(out/(p.name+'_local_retirement_before.json'),'x') as f:json.dump(r,f,indent=2)
  shutil.rmtree(p)
  r.update(free_after=free(),removed=not p.exists());r['filesystem_free_delta']=r['free_after']-r['free_before']
 except Exception as e:r['skip_reason']=str(e)
 (out/'local_owner_confirmed_retirement_actions.json').write_text(json.dumps(actions,indent=2)+'\n');print(path,r.get('removed'),r.get('filesystem_free_delta'),r.get('skip_reason'),flush=True)
