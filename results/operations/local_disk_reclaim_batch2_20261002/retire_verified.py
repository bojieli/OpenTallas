#!/usr/bin/env python3
"""Remove only the explicitly audited inactive clean worktrees; preserve refs and receipts."""
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;proof=json.loads((R/'inactivity.final.json').read_text());saved=json.loads((R/'preservation.receipt.json').read_text())
assert not proof['errors'] and not any(proof['candidate_hits'].values()) and not proof['manifest_references']
assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(proof['time_utc'])).total_seconds()<120,'Audit stale'
stat=os.statvfs('/');before=dict(available_bytes=stat.f_bavail*stat.f_frsize,free_bytes=stat.f_bfree*stat.f_frsize)
records=[]
for v in saved['candidates']:
 p=Path(v['path']);assert p.parent==Path('/tmp') and (p.name.startswith('opentallas-v41-') or p.name=='opentallas-core-cancel-join-exec-20261002-r1')
 assert subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD']).decode().strip()==v['head']
 assert not subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=normal'])
 assert subprocess.check_output(['git','--git-dir',v['git_common_dir'],'rev-parse',v['preserved_ref']]).decode().strip()==v['head']
 assert hashlib.sha256(Path(v['cache_archive']).read_bytes()).hexdigest()==v['cache_archive_sha256']
 subprocess.run(['git','--git-dir',v['git_common_dir'],'worktree','remove','--force',str(p)],check=True)
 assert not p.exists()
 records.append(dict(path=str(p),preserved_ref=v['preserved_ref'],head=v['head'],removed_allocated_bytes=v['allocated_candidate_bytes'],removed=True))
 subprocess.run(['sync','-f','/tmp'],check=True)
 now=os.statvfs('/');receipt=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),before=before,after=dict(available_bytes=now.f_bavail*now.f_frsize,free_bytes=now.f_bfree*now.f_frsize),candidate_bytes_removed=sum(x['removed_allocated_bytes'] for x in records),filesystem_available_delta_bytes=now.f_bavail*now.f_frsize-before['available_bytes'],retired=records,unique_sources_and_evidence_preserved=True,existing_jobs_signalled=0,current_checkpoints_removed=0,guard_and_drain_monitors_untouched=True,external_activity_can_affect_df_delta=True)
 (R/'reclaim.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
# Receipt is updated after each completed removal so partial progress remains reviewable.
print(json.dumps(receipt,indent=2))
