import pathlib as P,json,subprocess as S,os,re,time,hashlib
wt=P.Path('/tmp/opentallas-disk-recovery-20261001');out=wt/'results/maintenance/qwen_retirement_followup_20261001';main='/home/ubuntu/OpenTallas';owner=json.load(open(out/'owner_handoff.json'));actions=[]
remote={p.name:json.load(open(p)) for p in out.glob('*_checks.json')};assert len(remote)==9
for p,head in owner['retire'].items():assert all(not r['paths'][p] for r in remote.values()),'remote live reference'
for f in P.Path('/tmp/claude-1000/queue').glob('*.manifest'):(out/('queue_'+f.name+'.txt')).write_bytes(f.read_bytes())
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(P.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
for path,head in owner['retire'].items():
 r={'path':path,'head':head,'timestamp':time.time()};actions.append(r)
 try:
  snap=json.loads(S.check_output(['sudo','-n','python3','/tmp/disk-recovery-proc.py'],text=True));assert not snap['errors'];r['local_live_pids']=[x['pid'] for x in snap['rows'] if x['pid'] not in anc and (re.search(re.escape(path)+r'(?=$|[\s/\"\'])',x['cmd']) or any(t==path or t.startswith(path+'/') for t in x['links']) or path+'/' in x.get('maps',''))];assert not r['local_live_pids'],'local live'
  ps=S.run(['docker','ps','-aq'],capture_output=True,text=True);assert ps.returncode==0
  if ps.stdout.split():
   ins=S.run(['docker','inspect',*ps.stdout.split()],capture_output=True,text=True);assert ins.returncode==0
   hits=[]
   for c in json.loads(ins.stdout):
    if not c['State'].get('Running'):continue
    cfg=c['Config'];cwd=cfg.get('WorkingDir','');cmd=' '.join(cfg.get('Cmd') or [])
    if cwd==path or cwd.startswith(path+'/') or re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(m.get('Source','')==path or m.get('Source','').startswith(path+'/') for m in c.get('Mounts',[])):hits.append(c['Id'])
   r['local_docker_hits']=hits;assert not hits,'local Docker live'
  assert S.check_output(['git','-C',path,'rev-parse','HEAD'],text=True).strip()==head,'HEAD changed'
  st=S.check_output(['git','-C',path,'status','--porcelain=v1','--untracked-files=all'],text=True);assert not st,'dirty/untracked'
  raw=S.check_output(['git','-C',main,'worktree','list','--porcelain'],text=True);block=next(b for b in raw.split('\n\n') if b.startswith('worktree '+path+'\n'));assert '\nlocked' not in block,'locked'
  ref='refs/maintenance/qwen-followup-20261001/'+P.Path(path).name;S.run(['git','-C',main,'update-ref',ref,head,'0'*40],check=True);r['preserved_head_ref']=ref
  r['status']=st;r['remote_zero_refs_confirmed']=9;r['allocated_bytes']=int(S.check_output(['du','-s','-B1',path],text=True).split()[0]);v=os.statvfs(main);r['free_before']=v.f_bavail*v.f_frsize
  with open(out/(P.Path(path).name+'_before.json'),'x') as stream:json.dump(r,stream,indent=2)
  done=S.run(['git','-C',main,'worktree','remove',path],capture_output=True,text=True);v=os.statvfs(main);r.update(returncode=done.returncode,stderr=done.stderr,path_exists=P.Path(path).exists(),free_after=v.f_bavail*v.f_frsize);r['filesystem_free_delta']=r['free_after']-r['free_before']
 except Exception as e:r['skip_reason']=str(e)
 (out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n');print(json.dumps(r),flush=True)
for r in actions:
 if r.get('returncode')==0:assert S.check_output(['git','-C',main,'rev-parse',r['preserved_head_ref']],text=True).strip()==r['head'] and not P.Path(r['path']).exists()
(out/'summary.json').write_text(json.dumps({'removed_worktrees':sum(r.get('returncode')==0 for r in actions),'measured_interval_freed_bytes':sum(r.get('filesystem_free_delta',0) for r in actions if r.get('returncode')==0),'protected':owner['protect'],'new_builds':0,'main_edited':False,'pushed':False,'prior_remote_audit_sha':'f98e46d0e616ed18815ec705d405499417d19d72'},indent=2)+'\n')
(out/'audit_file_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='audit_file_hashes.json'},indent=2)+'\n')
S.run(['git','-C',str(wt),'add','--',*[str(p.relative_to(wt)) for p in sorted(out.iterdir()) if p.is_file()]],check=True);S.run(['git','-C',str(wt),'diff','--cached','--check'],check=True);S.run(['git','-C',str(wt),'commit','-m','maintenance: pin Qwen owner retirement followup and live protections'],check=True);print('AUDIT_SHA',S.check_output(['git','-C',str(wt),'rev-parse','HEAD'],text=True).strip());assert not S.check_output(['git','-C',str(wt),'status','--porcelain=v1'],text=True)
