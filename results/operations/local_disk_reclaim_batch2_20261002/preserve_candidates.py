#!/usr/bin/env python3
import datetime,hashlib,json,os,subprocess,tarfile
from pathlib import Path
R=Path(__file__).resolve().parent;paths=json.loads((R/'candidate-paths.json').read_text());records=[]
def git(p,*args):return subprocess.check_output(['git','-C',str(p),*args])
for path in paths:
 p=Path(path);head=git(p,'rev-parse','HEAD').decode().strip();status=git(p,'status','--porcelain','--untracked-files=normal');assert not status,'Dirty tree: '+path
 common=git(p,'rev-parse','--path-format=absolute','--git-common-dir').decode().strip();ref='refs/retired/local-disk-batch2-20261002/'+p.name
 git(p,'update-ref',ref,head);assert git(p,'rev-parse',ref).decode().strip()==head
 ordinary=[x.decode() for x in git(p,'ls-files','-o','--exclude-standard','-z').split(b'\0') if x];assert not ordinary
 ignored=[x.decode() for x in git(p,'ls-files','-o','-i','--exclude-standard','-z').split(b'\0') if x]
 ignored_bytes=sum((p/x).stat().st_size for x in ignored if (p/x).is_file());assert ignored_bytes<16777216,'Ignored files too large for lightweight preservation'
 noncache=[x for x in ignored if not (x.startswith('.pytest_cache/') or ('/__pycache__/' in '/'+x and x.endswith('.pyc')))];assert not noncache,'Non-cache ignored files require separate source/evidence review: '+str(noncache)
 archive=R/(p.name+'.ignored-cache.tar.gz')
 with tarfile.open(archive,'w:gz') as t:
  for name in ignored:t.add(p/name,arcname=name,recursive=False)
 patch=R/(p.name+'.tracked.patch');patch.write_bytes(git(p,'diff','--binary','HEAD'));assert patch.stat().st_size==0
 # Git objects retain every tracked source/evidence/checkpoint byte; caches are separately archived.
 tracked=len([x for x in git(p,'ls-files','-z').split(b'\0') if x]);size=int(subprocess.check_output(['du','-sx','-B1',path]).split()[0])
 records.append(dict(path=path,head=head,tree=git(p,'rev-parse','HEAD^{tree}').decode().strip(),preserved_ref=ref,git_common_dir=common,tracked_files_retained_in_commit=tracked,status_clean=True,ordinary_untracked_files=[],ignored_files=ignored,ignored_bytes=ignored_bytes,cache_archive=str(archive),cache_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),patch_path=str(patch),patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),allocated_candidate_bytes=size))
(R/'preservation.receipt.json').write_text(json.dumps(dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidates=records,source_changes_lost=0,tracked_evidence_retained_in_git=True),indent=2)+'\n')
print('Preserved',len(records),'HEAD refs and all ignored files;',sum(x['allocated_candidate_bytes'] for x in records),'candidate bytes')
