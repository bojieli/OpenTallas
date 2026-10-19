import tarfile,json,hashlib,re,collections,pathlib
base=pathlib.Path(__file__).parent
with tarfile.open(base/'receipt.tar.gz') as t:
 manifest=json.load(t.extractfile('manifest.json'));out={'scope':'read-only terminal collection; no simulation rerun','archive_sha256':hashlib.sha256((base/'receipt.tar.gz').read_bytes()).hexdigest(),'cases':{}}
 checked=0
 for member in t.getmembers():
  if '/files/' not in member.name:continue
  label,path=member.name.split('/files/',1);b=t.extractfile(member).read();assert hashlib.sha256(b).hexdigest()==manifest[label]['files']['/'+path]['sha256'];checked+=1
 for label in manifest:
  name=next(n for n in t.getnames() if n.startswith(label+'/files/') and n.endswith('run_u1.log' if label=='g7' else 'resume_cpp_stack_20261019.u1.log'))
  log=t.extractfile(name).read().decode();errors=[l for l in log.splitlines() if l.startswith('SMOKE_ERR')]
  out['cases'][label]={'verdict':'FAIL','return_code_is_not_verdict':True,'error_labels':errors,'nonfold_evidence':[l for l in log.splitlines() if not l.startswith('SMOKE_OFOLD')],'manifest_files':len(manifest[label]['files'])}
  assert 'SMOKE_FAIL' in log and 'SMOKE_PASS' not in log
  if label=='g7':
   early=[l for l in errors if int(re.search(r'@(\d+)',l)[1])<1024];assert len(early)==17
   assert 'KVA_RUN_AT step 0 cyc 2648' in log and 'SMOKE_ERR @2288 QK strip produced no K request or partial in a step' in log
   out['cases'][label]['startup_error_count']=len(early);out['cases'][label]['run_edge']=2648;out['cases'][label]['programme_check_edge']=2288
  else:
   assert len(errors)==1 and 'KVA_FAULT ECTL issuer of slg_WS_7 cyc 2796 (rel run0 148)' in log
 old=json.loads(t.extractfile(next(n for n in t.getnames() if n.endswith('resume_cpp_stack_20261019.inputs.json'))).read())
 matches={}
 for rel,sha in old.items():
  p=manifest['old_qk']['root']+'/run/'+rel;matches[rel]=manifest['old_qk']['files'][p]['sha256']==sha
 assert all(matches.values());out['old_qk_prior_build_hash_matches']=matches
 prev=json.load(open(base/'previous_frozen_files.json'))['files'];common=set(prev)&set(manifest['g7']['files']);changes=[p for p in common if prev[p]['sha256']!=manifest['g7']['files'][p]['sha256']];assert not changes
 out['g7_prior_c64_common_file_hash_matches']=len(common);out['g7_prior_c64_changed_common_paths']=changes;out['archive_members_hash_verified']=checked
 (base/'analysis.json').write_text(json.dumps(out,indent=2)+'\n');(base/'validation.txt').write_text(f'PASS: {checked} archived source/log files verify; {len(common)} common G7 paths match c64; four prior old QK build hashes match; both application FAIL verdicts preserved.\n')
 print((base/'validation.txt').read_text())
