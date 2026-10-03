import os,json,time,subprocess,hashlib
from pathlib import Path
ROOTS=[Path('/home/ubuntu/w18work'),Path('/tmp/claude-1000/wt')]
OUT=Path('/tmp/maxwell-legacy-retirement-20261003');CUTOFF=1759276800 # 2025 overridden below
import datetime
CUTOFF=datetime.datetime(2026,10,1,tzinfo=datetime.timezone.utc).timestamp()
SUFFIX={'.odb','.o','.a','.pch'}
def refs():
 r=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  for tag in ('cwd','root','exe'):
   try:r.append((p.name,tag,os.readlink(p/tag)))
   except OSError:pass
  try:
   for f in (p/'fd').iterdir():
    try:r.append((p.name,'fd',os.readlink(f)))
    except OSError:pass
  except OSError:pass
  try:r.append((p.name,'cmdline',(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')))
  except OSError:pass
 return r
R=refs();excluded={};eligible=[];gitrecords=[]
def active(d):return [(pid,k,t) for pid,k,t in R if str(d) in t and pid!=str(os.getpid())]
for root in ROOTS:
 for d in sorted(root.iterdir()):
  if not d.is_dir():continue
  hits=active(d)
  if hits or (root==ROOTS[0] and d.name in ('karb21','rebase','jobs')):
   excluded[str(d)]={'reason':'process reference or explicit dependency exclusion','hits':hits};continue
  if root==ROOTS[1]:
   if not d.name.startswith(('w11-','w13-')):
    excluded[str(d)]={'reason':'not selected obsolete legacy family'};continue
   def git(*a):return subprocess.run(['git','-C',str(d),*a],capture_output=True,text=True)
   head=git('rev-parse','HEAD')
   status=git('status','--porcelain','--untracked-files=normal')
   if head.returncode or status.returncode or status.stdout:
    excluded[str(d)]={'reason':'nonclean/non-git','status':status.stdout[:1000]};continue
   tracked=set(git('ls-files').stdout.splitlines())
   ref='refs/retirement/maxwell-20261003/'+d.name
   save=git('update-ref',ref,head.stdout.strip())
   if save.returncode:raise RuntimeError(save.stderr)
   gitrecords.append({'directory':str(d),'HEAD':head.stdout.strip(),'ref':ref,'source_kept':True})
  else:tracked=set()
  for base,ds,fs in os.walk(d):
   ds[:]=[x for x in ds if x not in ('.git','node_modules')]
   for f in fs:
    p=Path(base)/f
    if p.suffix not in SUFFIX or p.is_symlink():continue
    st=p.stat()
    if st.st_mtime>=CUTOFF or st.st_ctime>=CUTOFF:continue
    if root==ROOTS[1] and str(p.relative_to(d)) in tracked:continue
    eligible.append({'path':str(p),'size':st.st_size,'allocated_bytes':st.st_blocks*512,'inode':st.st_ino,'device':st.st_dev,'mtime':st.st_mtime,'ctime':st.st_ctime})
manifest={'cutoff_utc':'2026-10-01T00:00:00Z','excluded':excluded,'git_refs':gitrecords,'candidates':eligible,'candidate_allocated_bytes':sum(x['allocated_bytes'] for x in eligible),'sources_logs_json_all_preserved':True}
(OUT/'before.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'candidates':len(eligible),'allocated_bytes':manifest['candidate_allocated_bytes'],'clean_legacy_refs':len(gitrecords),'excluded_directories':list(excluded)},indent=2))
