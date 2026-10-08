#!/usr/bin/env python3
# clone.py eval LISTFILE PROTECT  |  remove REPO LISTFILE   (standalone clones; back up with clone_backup.sh first)
import subprocess,sys,os,json,glob,tempfile,time
mode,repo=sys.argv[1],sys.argv[2]
def sh(c,cwd=None,env=None):
    r=subprocess.run(c,shell=True,cwd=cwd,capture_output=True,text=True,errors='replace',env=env); return r.returncode,(r.stdout+r.stderr).strip()
SUDO='sudo -n ' if sh('sudo -n true')[0]==0 else ''
def inuse():
    _,o=sh(SUDO+"bash -c 'for p in /proc/[0-9]*; do readlink $p/cwd; ls -l $p/fd 2>/dev/null | sed -n \"s/.* -> //p\"; done' 2>/dev/null")
    s=set(x for x in o.split('\n') if x.startswith('/'))
    _,dm=sh(SUDO+"bash -c 'docker ps -q | xargs -r docker inspect -f \"{{range .Mounts}}{{.Source}} {{end}}\"' 2>/dev/null"); s|=set(dm.split())
    _,cm=sh(SUDO+"bash -c 'cat /proc/[0-9]*/cmdline 2>/dev/null | tr \"\\0\" \" \"'")
    return s,cm
if mode=='eval':
    prot=[l.strip() for l in open(sys.argv[3]) if l.strip()]
    IU,CM=inuse()
    wts=[l.strip() for l in open(repo) if l.strip()]
    for w in wts:
        rec={'wt':w}
        real=os.path.realpath(w)
        if real.rstrip('/') in ('/srv/opentallas/repos/OpenTallas-git','/home/ubuntu/OpenTallas','/home/ubuntu/wt-codex-closure-reliability'): rec['v']='MAIN'
        elif not os.path.isdir(w): rec['v']='MISSING'
        elif sh(f"find '{w}' \\( -path '*/.git/refs/diskrec' -o -path '*/.git/logs/refs/diskrec' \\) -prune -o -newermt '-24 hours' ! -path '*/.git/refs' ! -path '*/.git/logs/refs' ! -path '*/.git/logs' ! -path '*/.git' -print -quit 2>/dev/null")[1]: rec['v']='RECENT'
        elif any(x==w or x.startswith(w+'/') for x in IU): rec['v']='INUSE'
        elif w in CM: rec['v']='INUSE_CMD'
        elif any(p==w or p.startswith(w+'/') or w.startswith(p+'/') for p in prot): rec['v']='PROTECTED_REF'
        else:
            rch,head=sh('git rev-parse HEAD',w); rec['head']=head
            if rch or len(head)!=40: rec['v']='NOGIT'; print(json.dumps(rec),flush=True); continue
            _,st=sh('git status --porcelain',w)
            dirty=[x for x in st.split('\n') if x and not x.startswith('D ')]
            sha=head
            if dirty:
                idx=tempfile.mktemp(); env=dict(os.environ,GIT_INDEX_FILE=idx)
                sh('git read-tree HEAD',w,env)
                _,mods=sh("git diff --name-only HEAD",w); _,unt=sh("git ls-files --others --exclude-standard",w)
                add=[f for f in mods.split('\n')+unt.split('\n') if f and os.path.isfile(os.path.join(w,f)) and os.path.getsize(os.path.join(w,f))<50*2**20]
                for i in range(0,len(add),200): sh('git add -f -- '+' '.join("'"+a.replace("'","'\\''")+"'" for a in add[i:i+200]),w,env)
                _,tree=sh('git write-tree',w,env)
                msg=f'Backup of dirty worktree {w} before disk recovery 2026-10-07\n\n{len(add)} files preserved.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
                rc,sha=sh('git -c user.name="Bojie Li" -c user.email=bojieli@gmail.com commit-tree '+tree+' -p '+head+' -m "$M"',w,dict(os.environ,M=msg))
                os.unlink(idx)
                if rc: rec['v']='BACKUP_FAIL'; rec['err']=sha; print(json.dumps(rec),flush=True); continue
            name=os.path.basename(w.rstrip('/'))+'-'+str(abs(hash(w))%100000)
            sh(f'git -C {w} update-ref refs/diskrec/{name} {sha}'); rec['remote_url']=sh(f'git -C {w} remote get-url origin')[1]
            rec.update(v='CANDIDATE',sha=sha,ref='refs/diskrec/'+name,ndirty=len(dirty))
            rec['mb']=sh(f"du -sm '{w}' | cut -f1")[1]
        print(json.dumps(rec),flush=True)
else:
    IU,CM=inuse()
    for l in open(sys.argv[3]):
        w=l.strip()
        if not w: continue
        if sh(f"find '{w}' \\( -path '*/.git/refs/diskrec' -o -path '*/.git/logs/refs/diskrec' \\) -prune -o -newermt '-24 hours' ! -path '*/.git/refs' ! -path '*/.git/logs/refs' ! -path '*/.git/logs' ! -path '*/.git' -print -quit 2>/dev/null")[1] or any(x==w or x.startswith(w+'/') for x in IU):
            print('SKIP_RECHECK',w,flush=True); continue
        _,mb=sh(f"du -sm '{w}' | cut -f1")
        rc,o=sh(f"{SUDO}rm -rf --one-file-system -- '{w}'")
        if rc:
            rc2,o2=sh(f"{SUDO}rm -rf --one-file-system -- '{w}'") if 'Permission denied' in o else (rc,o)
            print(('REMOVED_SUDO' if rc2==0 else 'FAIL'),w,mb,o[-200:],flush=True)
        else: print('REMOVED',w,mb,flush=True)
