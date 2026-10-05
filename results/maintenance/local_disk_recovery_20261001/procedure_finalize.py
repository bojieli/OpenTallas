import pathlib as P,json,subprocess as S,os,datetime,hashlib,shutil
wt=P.Path('/tmp/opentallas-disk-recovery-20261001');out=wt/'results/maintenance/local_disk_recovery_20261001';main='/home/ubuntu/OpenTallas'
files=['qwen_retirement_actions.json','w15_retirement_actions.json','w15_boundary_verified_retirement_actions.json','w15_wt12_verified_retirement_actions.json','w19_retirement_actions.json','qc_retirement_actions.json']
records=[json.load(open(p)) for p in out.glob('*_removal_after.json')]
for n in files:records += [r for r in json.load(open(out/n)) if r.get('returncode')==0]
assert len(records)==len({r['path'] for r in records})
validation=[]
for r in records:
 assert not P.Path(r['path']).exists()
 ref=r.get('preserved_ref',r.get('preserved_head_ref'));assert S.check_output(['git','-C',main,'rev-parse',ref],text=True).strip()==r['head']
 if 'dirty_archive_ref' in r:
  assert S.check_output(['git','-C',main,'rev-parse',r['dirty_archive_ref']],text=True).strip()==r['dirty_archive_commit']
  S.run(['git','-C',main,'cat-file','-e',r['dirty_archive_commit']+'^{tree}'],check=True)
 validation.append({'path':r['path'],'head_ref_valid':True,'dirty_archive_valid':'dirty_archive_ref' in r})
checkpoints=json.load(open(out/'w19_checkpoint_actions.json'))
for r in checkpoints:
 if not r.get('removed'):continue
 assert not P.Path(r['path']).exists()
 assert S.check_output(['git','-C',main,'rev-parse',r['preserved_ref']],text=True).strip()==r['metadata_blob']
 b=S.check_output(['git','-C',main,'cat-file','blob',r['metadata_blob']]);assert b==(out/r['metadata_archive']).read_bytes()
 validation.append({'checkpoint':r['path'],'metadata_blob_ref_valid':True})
(out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
summary=json.load(open(out/'summary.json'));summary.update(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),removed_worktrees=len(records),removed_checkpoint_directories=sum(r.get('removed',False) for r in checkpoints),measured_removal_interval_free_delta_bytes=sum(r['filesystem_free_delta'] for r in records)+sum(r.get('filesystem_free_delta',0) for r in checkpoints if r.get('removed')),du_sum_before_bytes=sum(r['allocated_bytes_before'] for r in records)+sum(r.get('allocated_bytes_before',0) for r in checkpoints if r.get('removed')),filesystem_available_bytes_after=os.statvfs(main).f_bavail*os.statvfs(main).f_frsize,main_head_observed_after=S.check_output(['git','-C',main,'rev-parse','HEAD'],text=True).strip(),additional_dot_manifest_files_inspected=304,dirty_archive_commits=[{'path':r['path'],'commit':r['dirty_archive_commit'],'ref':r['dirty_archive_ref']} for r in records if 'dirty_archive_commit' in r])
summary['protected']=['/home/ubuntu/w15bwt7,8,9,13,14','W15d98SRAM/recovery/source/output','Qwen partition recovery run and jobs','QC readiness watcher source and state','active Qwen/DSROM/HBM recovery targets','locked and live source snapshots','qcnam-run and quality runs','parent-integration']
summary['limits'].append('Initial audit .manifest omission corrected and disclosed: all304 .manifest files plus12 queue manifests read, historical mentions reviewed; independently fresh process checks and preserved refs protect prior removed sources.')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'worktrees_after.txt').write_text(S.check_output(['git','-C',main,'worktree','list','--porcelain'],text=True).rstrip()+'\n')
(out/'main_status_observed_after.txt').write_text(S.check_output(['git','-C',main,'status','--porcelain=v1'],text=True))
coord=json.load(open(out/'owner_coordination.json'));coord['protected']+=['/home/ubuntu/w19-production','/home/ubuntu/qwen-partition-recovery-run','/home/ubuntu/qwen-recovery-jobs','/tmp/claude-1000/qcnam/readiness-watch-72b3718d1'];coord['protected']=[x for x in coord['protected'] if x!='/home/ubuntu/w15bwt*'];coord['protected']+=['/home/ubuntu/w15bwt'+str(n) for n in [7,8,9,13,14]];(out/'owner_coordination.json').write_text(json.dumps(coord,indent=2)+'\n')
for n in ['w15-retired','w15-wt12','w19-retired','w19-checkpoints','qc-retired']:
 shutil.copyfile('/tmp/disk-recovery-'+n+'.py',out/('procedure_'+n+'.py'))
shutil.copyfile('/tmp/disk-recovery-finalize.py',out/'procedure_finalize.py')
# Normalize only maintenance procedure copies / worktree inventory whitespace for commit hygiene.
for p in out.glob('procedure_*.py'):
 p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
p=out/'worktrees_before.txt';p.write_text(p.read_text().rstrip()+'\n')
(out/'audit_file_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='audit_file_hashes.json'},indent=2)+'\n')
S.run(['git','-C',str(wt),'add','--',*[str(p.relative_to(wt)) for p in sorted(out.iterdir()) if p.is_file()]],check=True)
S.run(['git','-C',str(wt),'diff','--cached','--check'],check=True)
S.run(['git','-C',str(wt),'commit','-m','maintenance: pin local disk recovery audit and preserved legacy sources'],check=True)
sha=S.check_output(['git','-C',str(wt),'rev-parse','HEAD'],text=True).strip();print('AUDIT_SHA',sha);print(json.dumps(summary,indent=2));print('AUDIT_STATUS',S.check_output(['git','-C',str(wt),'status','--porcelain=v1'],text=True))
