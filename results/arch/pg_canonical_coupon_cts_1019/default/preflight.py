from pathlib import Path
import hashlib,json,os,subprocess
p=Path.cwd();j=json.loads((p/'SOURCE_MANIFEST.json').read_text());bad=[]
for f in j['files']:
 q=p/f['path']
 if not q.exists() or hashlib.sha256(q.read_bytes()).hexdigest()!=f['sha256'] or (q.stat().st_mode & 0o111)!=(int(f['mode'],8)&0o111):bad.append(f['path'])
assert not bad,(len(bad),bad[:8])
for mode in ('default','strict'):
 job=json.loads((p/(mode+'_job_frozen.json')).read_text());assert job['source']['commit']==j['source'][:9]; assert 'COMMIT' not in json.dumps(job)
 plan=job['effective_helper_plan'];assert len(plan['files'])==(49 if mode=='default' else 53)
 for f in plan['files']:assert hashlib.sha256((p/f['path']).read_bytes()).hexdigest()==f['sha256'],f
img='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
id=json.loads(subprocess.check_output(['docker','image','inspect',img]))[0]['Id'];assert id=='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
print(json.dumps({'source':j['source'],'files':len(j['files']),'all_sha_exec_match':True,'frozen_helpers':[49,53],'image_id':id,'statvfs_available_gb':os.statvfs(p).f_bavail*os.statvfs(p).f_frsize/2**30}))
