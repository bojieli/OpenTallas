import pathlib as P,subprocess as S,json,os,time,hashlib,tarfile,shutil,re
main='/home/ubuntu/OpenTallas';out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001');handoff=json.load(open(out/'w19_owner_handoff_original.json'));actions=[]
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(P.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
free=lambda:os.statvfs(main).f_bavail*os.statvfs(main).f_frsize
for path in handoff['retired_candidates'][2:]:
 p=P.Path(path);rec={'path':path,'owner':'W19 owner retired checkpoints','ready_commit':handoff['ready_commit'],'timestamp':time.time()};actions.append(rec)
 try:
  assert p.is_dir() and not p.is_symlink(),'absent or symlink'
  assert p.parent==P.Path('/tmp/claude-1000/w19'),'outside exact checkpoint parent'
  assert not (p/'.git').exists(),'worktree source unexpectedly'
  snap=json.loads(S.check_output(['sudo','-n','python3','/tmp/disk-recovery-proc.py'],text=True));assert not snap['errors']
  hits=[r['pid'] for r in snap['rows'] if r['pid'] not in anc and (re.search(re.escape(path)+r'(?=$|[\s/\"\'])',r['cmd']) or any(x==path or x.startswith(path+'/') for x in r['links']) or path+'/' in r.get('maps',''))];rec['live_pids']=hits;assert not hits,'live reference'
  files=[];keep=[];total=0
  for f in sorted(p.rglob('*')):
   if f.is_symlink():raise RuntimeError('symlink checkpoint requires owner review')
   if not f.is_file():continue
   b=f.read_bytes();omit=f.name=='sim.vvp' and f.parent.name.startswith('build_')
   files.append({'relative_path':str(f.relative_to(p)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'preserved':not omit,'reason':'generated Icarus compiled simulator' if omit else 'preserve all other checkpoint contents'})
   if not omit:keep.append(f);total+=len(b)
  assert total<20_000_000,'noncompiled checkpoint archive too large'
  archive=out/(p.name+'_checkpoint_metadata.tar.gz')
  with tarfile.open(archive,'w:gz',dereference=False) as tar:
   for f in keep:tar.add(f,arcname=str(f.relative_to(p)),recursive=False)
  blob=S.check_output(['git','-C',main,'hash-object','-w',str(archive)],text=True).strip();ref='refs/maintenance/disk-recovery-20261001/checkpoint-'+p.name
  S.run(['git','-C',main,'update-ref',ref,blob,'0'*40],check=True)
  rec.update(files=files,metadata_archive=archive.name,metadata_blob=blob,preserved_ref=ref,allocated_bytes_before=int(S.check_output(['du','-s','-B1',path],text=True).split()[0]),free_before=free())
  (out/(p.name+'_checkpoint_before.json')).write_text(json.dumps(rec,indent=2)+'\n')
  # Exact owner-listed checkpoint only. Archive/ref already persisted; never follow symlinks.
  shutil.rmtree(p)
  rec.update(free_after=free(),removed=not p.exists());rec['filesystem_free_delta']=rec['free_after']-rec['free_before']
 except Exception as e:rec['skipped_reason']=str(e)
 (out/'w19_checkpoint_actions.json').write_text(json.dumps(actions,indent=2)+'\n');print(path,rec.get('removed'),rec.get('filesystem_free_delta'),rec.get('skipped_reason'),flush=True)
