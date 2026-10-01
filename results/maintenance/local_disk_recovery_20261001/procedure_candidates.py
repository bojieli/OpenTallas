import json,subprocess as S,pathlib as P
out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001');a=json.load(open(out/'worktree_audit.json'));c=[]
for r in a:
 p=r['worktree']
 if 'detached' not in r or not P.Path(p).exists() or r['process_pids'] or 'locked' in r:continue
 if any(s in p for s in ['recovery','w15','w18work','integration','qcnam-run']):continue
 if r['HEAD']=='89eace61f6c5a33b9814e2ab5775dcbf9b5f3ca2':continue
 refs=[s for s in r['manifest_references'] if not s.startswith('/tmp/disk-recovery-') and '/opentallas-disk-recovery-' not in s]
 if refs:continue
 if S.run(['git','-C',p,'merge-base','--is-ancestor',r['HEAD'],'89eace61f'],capture_output=True).returncode:continue
 st=S.run(['git','-C',p,'status','--porcelain=v1','--untracked-files=all'],capture_output=True)
 if st.returncode or st.stdout:continue
 c.append({'path':p,'head':r['HEAD']})
(out/'clean_merged_legacy_candidates.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(c,indent=2))
