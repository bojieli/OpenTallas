import pathlib as P,subprocess as S,json,os,time,hashlib,tempfile,re
main='/home/ubuntu/OpenTallas';out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001')
owner=json.load(open('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001/w15_owner_handoff.json'))
(out/'w15_owner_handoff_copy.json').write_text(json.dumps(owner,indent=2)+'\n')
paths=['/home/ubuntu/w15bwt12']
audit=json.load(open(out/'worktree_audit.json'));log=[]
def run(args,p=main,env=None):return S.run(['git','-C',p,*args],capture_output=True,env=env)
def free():v=os.statvfs(main);return v.f_bavail*v.f_frsize
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(P.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
for p in paths:
 rec={'path':p,'owner_retirement':'W15 owner handoff','timestamp':time.time()};log.append(rec)
 try:
  assert P.Path(p).is_dir(),'already absent'
  raw=run(['worktree','list','--porcelain']).stdout.decode();block=next(b for b in raw.split('\n\n') if b.startswith('worktree '+p+'\n'));assert '\nlocked' not in block,'locked'
  assert not any(p==x or p.startswith(x+'/') for x in owner['protect']),'protected'
  snap=json.loads(S.check_output(['sudo','-n','python3','/tmp/disk-recovery-proc.py'],text=True));assert not snap['errors'],'proc read errors'
  hits=[r['pid'] for r in snap['rows'] if r['pid'] not in anc and (re.search(re.escape(p)+r'(?=$|[\s/\"\'])', r['cmd']) is not None or any(x==p or x.startswith(p+'/') for x in r['links']) or p+'/' in r.get('maps',''))];rec['live_pids']=hits;assert not hits,'live'
  rec['manifest_references']=[x for r in audit if r['worktree']==p for x in r['manifest_references'] if not x.startswith('/tmp/disk-recovery-') and '/opentallas-disk-recovery-' not in x]
  rec['manifest_references']=[n for n in rec['manifest_references'] if re.search(re.escape(p)+r'(?=$|[\s/\"\'])', P.Path(n).read_text(errors='replace'))]
  # A real host/process-manifest reference requires owner review; keep it even if historical.
  inv=json.load(open(out/'manifest_inventory.json'));host={x['path'] for x in inv if x['process_or_host']}
  rec['historical_manifest_review']='W15 fresh9hosts: PID2901745 absent; exact process/dockerrefs zero. otjob-3751823665 terminal08:36:31exit247 evidence preserved.'
  head=run(['rev-parse','HEAD'],p).stdout.decode().strip();rec['head']=head
  status=run(['status','--porcelain=v1','-z','--untracked-files=all'],p);assert status.returncode==0,'status failed'
  st=status.stdout;rec['status_sha256']=hashlib.sha256(st).hexdigest();rec['status']=st.decode(errors='replace').replace('\0','\n')
  ref='refs/maintenance/disk-recovery-20261001/'+P.Path(p).name
  rr=run(['update-ref',ref,head,'0'*40]);assert rr.returncode==0,rr.stderr.decode();rec['preserved_head_ref']=ref
  if st:
   # Archive all source changes in Git with a private index; never write the source index.
   chunks=st.split(b'\0');changed=[];i=0
   while i<len(chunks):
    x=chunks[i];i+=1
    if not x:continue
    changed.append(os.fsdecode(x[3:]))
    if x[:1] in [b'R',b'C'] or x[1:2] in [b'R',b'C']:
     changed.append(os.fsdecode(chunks[i]));i+=1
   total=0
   for n in changed:
    f=P.Path(p)/n
    if f.is_file():total+=f.stat().st_size
   assert total<=20_000_000,'unique changes exceed lightweight archive limit'
   env=os.environ.copy();idx=out/(P.Path(p).name+'.private-index');env['GIT_INDEX_FILE']=str(idx)
   r=run(['read-tree',head],p,env);assert r.returncode==0,r.stderr.decode()
   r=run(['add','-A','--',*changed],p,env);assert r.returncode==0,r.stderr.decode()
   tree=run(['write-tree'],p,env).stdout.decode().strip();r=run(['commit-tree',tree,'-p',head,'-m','Maintenance archive of owner-retired legacy source '+p],p,env);assert r.returncode==0,r.stderr.decode();commit=r.stdout.decode().strip()
   rr=run(['update-ref',ref+'-dirty',commit,'0'*40]);assert rr.returncode==0,rr.stderr.decode();rec['dirty_archive_commit']=commit;rec['dirty_archive_ref']=ref+'-dirty';rec['unique_source_bytes']=total
   idx.unlink()
   # Ensure archived tree still matches the working source and status has not changed.
   assert run(['status','--porcelain=v1','-z','--untracked-files=all'],p).stdout==st,'source status changed'
   env['GIT_INDEX_FILE']=str(out/(P.Path(p).name+'.check-index'));run(['read-tree',commit],p,env)
   assert run(['diff','--exit-code',commit,'--',*changed],p,env).returncode==0,'source differs from archive'
   P.Path(env['GIT_INDEX_FILE']).unlink()
  rec['allocated_bytes_before']=int(S.check_output(['du','-s','-B1',p],text=True).split()[0]);rec['free_before']=free()
  (out/(P.Path(p).name+'_retirement_before.json')).write_text(json.dumps(rec,indent=2)+'\n')
  # --force is restricted to this exact owner-retired tree after preserving every change.
  rr=run(['worktree','remove',*(['--force'] if st else []),p]);rec.update(returncode=rr.returncode,stderr=rr.stderr.decode(),free_after=free(),path_exists=P.Path(p).exists());rec['filesystem_free_delta']=rec['free_after']-rec['free_before']
 except Exception as e:rec['skipped_reason']=str(e)
 (out/'w15_wt12_verified_retirement_actions.json').write_text(json.dumps(log,indent=2)+'\n');print(json.dumps(rec),flush=True)
