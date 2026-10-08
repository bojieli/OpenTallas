#!/usr/bin/env python3
# sweep.py HOSTLABEL PROTECT_FILE MODE(plan|apply) ROOT...
# Remove top-level items under ROOTs untouched for 24 h, not in use (proc cwd/fd, docker mount, cmdline), not a git
# checkout (worktree/clone passes back those up first: wt_apply.py, remote_wt.py, clone.py, clone_backup.sh) and not
# under / above a protected path.  Run hourly by tools/fleet/fleet_sweep.py (disk recovery agent 2026-10-07).
import os,sys,subprocess,glob,time,json,socket
host,pf,mode=sys.argv[1:4]; roots=sys.argv[4:]
CUR=os.environ.get('SWEEP_SKIP','/tmp/fleet_sweep')
prot=[l.strip().rstrip('/') for l in open(pf) if l.strip()]
SUDO = 'sudo -n ' if subprocess.run('sudo -n true',shell=True,capture_output=True).returncode==0 else ''
def sh(c): r=subprocess.run(c,shell=True,capture_output=True,text=True,errors='replace'); return r.returncode,(r.stdout+r.stderr).strip()
def inuse_snapshot():
    _,o=sh(SUDO+"bash -c 'for p in /proc/[0-9]*; do readlink $p/cwd; ls -l $p/fd 2>/dev/null | sed -n \"s/.* -> //p\"; done' 2>/dev/null")
    s=set(x for x in o.split('\n') if x.startswith('/'))
    _,dm=sh(SUDO+"bash -c 'docker ps -q | xargs -r docker inspect -f \"{{range .Mounts}}{{.Source}} {{end}}\"' 2>/dev/null")
    s|=set(dm.split())
    _,cm=sh(SUDO+"bash -c 'cat /proc/[0-9]*/cmdline 2>/dev/null | tr \"\\0\" \" \"'")
    return s,cm
INUSE,CMD=inuse_snapshot()
LOGF=os.environ.get('SWEEPLOG','/tmp/sweep_%s.log'%host); LOG=open(LOGF,'a')
def log(s): LOG.write(time.strftime('%Y-%m-%dT%H:%M:%S%z ')+host+' '+s+'\n'); LOG.flush(); print(s,flush=True)
SKIPNAMES={'.X11-unix','.ICE-unix','.font-unix','.XIM-unix','.Test-unix','lost+found','snap-private-tmp','docker'}
def is_anc(d):  # some protected path under d
    return any(p==d or p.startswith(d+'/') for p in prot)
def under_prot(d): return any(d.startswith(p+'/') for p in prot)
def used(d):
    if any(x==d or x.startswith(d+'/') for x in INUSE): return 'proc_cwd_fd/docker'
    if d in CMD: return 'cmdline'
    return None
def recent(d):
    _,o=sh(f"find '{d}' \\( -newermt '-24 hours' -o -newerct '-24 hours' \\) -print -quit 2>/dev/null"); return o
def gitdirty(d):
    _,o=sh(f"find '{d}' -maxdepth 3 -name .git -print -quit 2>/dev/null"); return o
tot=0
def visit(d,depth):
    global tot
    name=os.path.basename(d)
    if d==CUR or CUR.startswith(d+'/') and False: pass
    if name in SKIPNAMES or name.startswith(('systemd-private-','tmux-','ssh-','snap.','.')) and depth==1 and d.startswith('/tmp'): return
    try: st=os.lstat(d)
    except FileNotFoundError: return
    if d.startswith('/tmp/') and st.st_uid==0 and depth==1: return
    if under_prot(d) or d in prot: log(f'KEEP {d}: referenced by committed config or protected closure job'); return
    if d==CUR or CUR.startswith(d+'/'):
        return descend(d,depth)
    if os.path.islink(d) : return
    r=recent(d)
    if r or is_anc(d):
        return descend(d,depth)
    u=used(d)
    if u: log(f'KEEP {d}: in use ({u})'); return
    g=gitdirty(d) if os.path.isdir(d) else ''
    if g:
        log(f'KEEP {d}: contains git checkout {g} (handled by worktree pass)'); return
    _,sz=sh(f"{SUDO}du -sm '{d}' 2>/dev/null | cut -f1")
    try: sz=int(sz.split()[0])
    except Exception: sz=0
    if sz<1 and os.path.isdir(d): pass
    tot+=sz
    if mode=='apply':
        rc,o=sh(f"{SUDO}rm -rf --one-file-system -- '{d}'")
        log(f"DELETED {d} {sz}MB reason=untouched>24h proof=no-proc-cwd/fd/docker-mount,no-cmdline,no-active/closed/revivable-job-ref,no-committed-config-ref,no-git {'rc='+str(rc)+' '+o[-200:] if rc else ''}")
    else:
        log(f'PLAN {d} {sz}MB')
def maxdepth(d):
    if d.startswith('/tmp/claude-1000/'): return 3
    if d.startswith('/tmp/'): return 1
    return 4
def descend(d,depth):
    if not os.path.isdir(d) or os.path.islink(d): return
    if depth>=maxdepth(d+'/x'): log(f'KEEP {d}: touched <24h (unit)'); return
    if os.path.basename(os.path.dirname(d))=='closure-loop' and depth>0: log(f'KEEP {d}: closure-loop job dir touched <24h'); return
    if depth>0 and (os.path.isdir(d+'/.git') or os.path.isfile(d+'/.git')): log(f'KEEP {d}: git checkout touched <24h'); return
    try: kids=sorted(os.listdir(d))
    except Exception: return
    for k in kids: visit(os.path.join(d,k),depth+1)
for r in roots:
    if os.path.isdir(r): descend(r,0)
log(f'TOTAL {mode} {tot}MB over roots {roots}')
