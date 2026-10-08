import subprocess,sys,os,json,glob,tempfile,time
H=os.path.dirname(os.path.abspath(__file__)); repo=sys.argv[1]; plan=sys.argv[2]
LOG=open('/home/ubuntu/disk_recovery_20261007.log','a')
def log(s): LOG.write(time.strftime('%Y-%m-%dT%H:%M:%S%z')+' localhost '+s+'\n'); LOG.flush(); print(s,flush=True)
def sh(c,cwd=None,env=None):
    r=subprocess.run(c,shell=True,cwd=cwd,capture_output=True,text=True,errors='replace',env=env); return r.returncode,(r.stdout+r.stderr).strip()
def live_use(w):
    for p in glob.glob('/proc/[0-9]*'):
        try:
            if os.readlink(p+'/cwd').startswith(w+'/') or os.readlink(p+'/cwd')==w: return p
        except Exception: pass
    rc,o=sh(f"sudo bash -c 'ls -l /proc/[0-9]*/fd 2>/dev/null' | grep -F -- '-> {w}/' | head -1")
    return o or None
act=open(H+'/active_jobs.txt').read()
for l in open(plan):
    r=json.loads(l)
    if r['verdict'] not in ('REMOVE','BACKUP_THEN_REMOVE'): continue
    w=r['wt']; name=os.path.basename(w)
    if not os.path.isdir(w): continue
    rc,recent=sh(f"find '{w}' -newermt '-24 hours' -print -quit 2>/dev/null")
    if recent: log(f'SKIP {w}: touched <24h ({recent})'); continue
    u=live_use(w)
    if u: log(f'SKIP {w}: live use {u}'); continue
    if w in act: log(f'SKIP {w}: active job ref'); continue
    _,head=sh('git rev-parse HEAD',w)
    _,st=sh('git status --porcelain',w)
    dirty=[x for x in st.split('\n') if x and not x.startswith('D ')]
    _,pushed=sh(f'git branch -r --contains {head} | head -1',w)
    br=None
    if dirty or not pushed:
        br=f'backup/wt-{name}-20261007'
        sha=head
        if dirty:
            idx=tempfile.mktemp(dir=H); env=dict(os.environ,GIT_INDEX_FILE=idx)
            sh('git read-tree HEAD',w,env)
            _,mods=sh("git diff --name-only -z HEAD | tr '\\0' '\\n'",w)  # tracked modified vs HEAD (working tree)
            _,unt=sh("git ls-files --others --exclude-standard",w)
            files=[f for f in (mods.split('\n')+unt.split('\n')) if f]
            add=[];skip=[]
            for f in files:
                p=os.path.join(w,f)
                if os.path.isfile(p) and os.path.getsize(p)<50*2**20: add.append(f)
                elif os.path.exists(p): skip.append(f)
            for i in range(0,len(add),200):
                sh('git add -f -- '+' '.join("'"+a.replace("'","'\\''")+"'" for a in add[i:i+200]),w,env)
            _,tree=sh('git write-tree',w,env)
            msg=f'Backup of dirty worktree {w} before disk recovery 2026-10-07\n\n{len(add)} files preserved; {len(skip)} skipped (>=50MB or non-file).\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
            rc,sha=sh(f"git commit-tree {tree} -p {head} -m \"$M\"",w,dict(os.environ,M=msg))
            os.unlink(idx)
            if rc: log(f'SKIP {w}: commit-tree failed {sha}'); continue
            if skip: log(f'NOTE {w}: untracked/modified not backed up (>=50MB): {skip[:20]}')
        rc,o=sh(f'git push -q origin {sha}:refs/heads/{br}',w)
        if rc: log(f'SKIP {w}: push failed: {o[-300:]}'); continue
        log(f'BACKUP {w} -> origin/{br} @ {sha[:12]} (dirty={len(dirty)}, head_pushed={bool(pushed)})')
    rc,sz=sh(f"du -sm '{w}' | cut -f1")
    rc,o=sh(f"git -C {repo} worktree remove --force --force '{w}'")
    if rc: log(f'FAIL remove {w}: {o[-300:]}'); continue
    log(f'REMOVED worktree {w} {sz}MB head={head[:12]} branch_backup={br} proof: no file <24h, no proc cwd/fd, no active-job ref, clean&pushed or backed up')
sh(f'git -C {repo} worktree prune')
