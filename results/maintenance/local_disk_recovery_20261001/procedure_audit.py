import subprocess as sp,pathlib as P,json,hashlib,time,os
main='/home/ubuntu/OpenTallas'; out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/local_disk_recovery_20261001');out.mkdir(parents=True,exist_ok=True)
def git(*a,cwd=main):return sp.run(['git','-C',cwd,*a],capture_output=True,text=True)
raw=git('worktree','list','--porcelain').stdout
w=[]
for block in raw.strip().split('\n\n'):
 r={}
 for l in block.splitlines():
  k,_,v=l.partition(' ');r[k]=v
 w.append(r)
proc=json.loads(P.Path('/tmp/disk-recovery-proc.json').read_text());print('processes',len(proc['rows']),'errors',len(proc['errors']))
manifests=[];texts=[]
for name in P.Path('/tmp/disk-recovery-all-manifest-files.txt').read_text().splitlines():
 p=P.Path(name)
 if p.suffix not in ['.json','.txt','.tmp','.jsonl','.yaml','.yml','.tsv']:continue
 try:
  b=p.read_bytes();s=b.decode(errors='replace')
 except OSError:continue
 # Every manifest is inspected for path references; distinguish process/host metadata by content too.
 host=('hosts' in s or 'pid' in s or 'processes' in s or 'command' in s or 'cwd' in s)
 manifests.append({'path':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'process_or_host':host})
 texts.append((name,s))
print('manifests inspected',len(manifests),'process/host',sum(m['process_or_host'] for m in manifests))
audit=[]
for r in w:
 p=r['worktree']; reason=[]
 if p==main:reason.append('main')
 if 'locked' in r:reason.append('locked')
 if 'recovery' in p or r.get('HEAD')=='89eace61f6c5a33b9814e2ab5775dcbf9b5f3ca2':reason.append('protected recovery/new stream')
 hits=[x['pid'] for x in proc['rows'] if p in x['cmd'] or any(t==p or t.startswith(p+'/') for t in x['links']) or p+'/' in x.get('maps','')]
 if hits:reason.append('live process reference')
 r['process_pids']=hits
 # Protect any external manifest reference, even historical or ambiguous.
 refs=[n for n,s in texts if not n.startswith(p+'/') and p in s]
 if refs:reason.append('external manifest reference')
 r['manifest_references']=refs
 preferred=('/scratchpad/' in p or ('detached' in r and p.startswith('/tmp/')))
 if not preferred:reason.append('outside old scratch trial/baseline scope')
 if not reason:
  st=git('status','--porcelain=v1','--untracked-files=all','--ignored=matching',cwd=p)
  r['status']=st.stdout;r['status_error']=st.stderr
  if st.returncode or st.stdout:reason.append('dirty/untracked/ignored or unreadable')
  if git('merge-base','--is-ancestor',r['HEAD'],'89eace61f6c5a33b9814e2ab5775dcbf9b5f3ca2').returncode:reason.append('HEAD not merged in pinned main')
  if not reason:
   du=sp.run(['du','-s','-B1',p],capture_output=True,text=True)
   if du.returncode:reason.append('size unreadable')
   else:r['allocated_bytes']=int(du.stdout.split()[0])
 r['exclude_reasons']=reason;audit.append(r)
(out/'worktree_audit.json').write_text(json.dumps(audit,indent=2)+'\n');(out/'manifest_inventory.json').write_text(json.dumps(manifests,indent=2)+'\n')
(out/'process_audit.json').write_text(json.dumps({'process_count':len(proc['rows']),'read_errors':proc['errors'],'worktree_references':[{'pid':x['pid'],'paths':[r['worktree'] for r in audit if x['pid'] in r['process_pids']]} for x in proc['rows'] if any(x['pid'] in r['process_pids'] for r in audit)]},indent=2)+'\n')
(out/'worktrees_before.txt').write_text(raw)
(out/'manifest_search_errors.txt').write_text(P.Path('/tmp/disk-recovery-all-manifest-errors').read_text())
for r in audit:
 if '/scratchpad/' in r['worktree'] or not r['exclude_reasons']:print(r['worktree'],r.get('allocated_bytes'),r['exclude_reasons'],r.get('status','')[:160])
