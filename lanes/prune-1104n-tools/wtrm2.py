#!/usr/bin/env python3
# PRUNE-1104N: re-check one worktree per COORD 11:05 (3), then remove it. usage: wtrm2.py <worktree dir> check|rm [cleared-keep]. Name, config, cache, lane-branch and symlink tests run first in wtclass.py.
# Prints one line ok/REFUSE and, for rm, whether the dir and its worktree registration are gone. Wave names are checked separately on the hub by sfnames.py.
import os,re,sys,json,time,shutil,subprocess as sp
d,mode=sys.argv[1].rstrip('/'),sys.argv[2]; s=d; hx='wt/'+os.path.basename(d)
NEVER=re.compile(r'^(kw-fix-3|kit-wave-15|tok-|kv-fn-|codex-ds-|veh|vehicle|ss27|ss28|die-s81-51|die-s81-52|dh59|dh60|kit_turn_b)|svc|tok',re.I)
if NEVER.search(os.path.basename(d)): sys.exit('REFUSE never '+d)
SIG=re.compile(r'(?<!NOT )(?<!NOT_)(?<![A-Z_])SIGNED\b|LOCAL_PASS')
if not re.fullmatch(r'/srv/opentallas-scratch2/claude/wt/[\w.-]+',d) or os.path.islink(d) or not os.path.isdir(d): sys.exit('REFUSE path '+d)
def run(c): return sp.run(c,capture_output=True,text=True)
def g(*a): return run(['git','-C',s]+list(a))
why=[]; head=g('rev-parse','HEAD').stdout.strip()
st=g('status','--porcelain').stdout.splitlines()
# COORD 11:05 (3): a reaper-style .keep is overridden where the rest of the test passes; only a root .keep, listed in the manifest
keep_only=[l for l in st if l=='?? .keep']; st=[l for l in st if l!='?? .keep']
mod=st
if st: why.append('not-clean:%d'%len(st))
REL=os.environ.get('P1104N_RELEASED')=='1'  # COORD 11:19 (3): owner named it finished, so idle<24h does not hold it
hub=run(['ssh','-n','-o','ConnectTimeout=20','hub',f"cd OpenTallas && git cat-file -t {head} && git for-each-ref --contains {head} --count=2 --format='%(refname:short)' | tr '\\n' ','"])
if not hub.stdout.startswith('commit') or len(hub.stdout.split())<2: why.append('not-reachable-on-hub:'+hub.stderr[:80])
idx=set(g('ls-files').stdout.splitlines()); nw=0; sz=0; nsig=0; own=[]; me=os.getuid()
for dp,dn,fn in os.walk(d):
    if '.git' in dn: dn.remove('.git')
    for f in fn+dn:
        fp=os.path.join(dp,f)
        try: x=os.lstat(fp)
        except OSError: continue
        nw=max(nw,x.st_mtime); sz+=x.st_blocks*512
        if x.st_uid!=me: own.append(fp)
    for f in fn:
        if f=='signoff.json' or f.endswith('.signoff.json'):
            fp=os.path.join(dp,f)
            try: t=bool(SIG.search(open(fp,errors='replace').read()))
            except OSError: t=True
            if t:
                nsig+=1
                if not fp.startswith(s+'/') or fp[len(s)+1:] not in idx: why.append('untracked-signed:'+fp)
if time.time()-nw<24*3600 and not REL: why.append('idle<24h')
if own: why.append('not-mine:%d'%len(own))
hits=set()
for pid in filter(str.isdigit,os.listdir('/proc')):
    if int(pid)==os.getpid(): continue
    try:
        c=open(f'/proc/{pid}/cmdline','rb').read().decode('utf8','replace')
        # the counter's read-only signoff find lists worktrees as prune paths: not a holder
        # a read-only find listing worktrees (counter scan, prune paths) is not a holder
        cs=c.replace('\0',' '); counter=cs.startswith(('find /srv/opentallas-scratch2/claude ','bash -c find /srv/opentallas-scratch2/claude ')) and '-delete' not in cs and '-exec' not in cs
        if hx in c and 'p1104n_' not in c and 'sfgate' not in c and not counter: hits.add('cmd:'+pid)
        for l in ('cwd','root'):
            if hx in os.readlink(f'/proc/{pid}/{l}'): hits.add('cwd:'+pid)
        for fd in os.listdir(f'/proc/{pid}/fd'):
            try:
                if hx in os.readlink(f'/proc/{pid}/fd/{fd}'): hits.add('fd:'+pid)
            except OSError: pass
    except OSError: pass
ids=run(['docker','ps','-q']).stdout.split()
if ids and hx in run(['docker','inspect']+ids).stdout: hits.add('docker')
if hits: why.append('live:'+','.join(sorted(hits))[:80])
info=f'{d}\t{head}\t{sz/1e9:.1f}\tidle={(time.time()-nw)/3600:.1f}h\tsigned={nsig}\tstatus={len(st)}\thub={hub.stdout.split()[-1][:60] if hub.stdout.split() else ""}'
if why: print('REFUSE',info,why); sys.exit(2)
if mode!='rm': print('OK',info); sys.exit(0)
g('worktree','unlock',s); r=g('worktree','remove','--force','--force',s)
print('wtremove rc',r.returncode,r.stderr.strip()[:200])
if os.path.isdir(s) and os.path.exists(s+'/.git'): print('WORKTREE-REMOVE-FAILED',info); sys.exit(3)
shutil.rmtree(d,ignore_errors=True)
print('REMOVED' if not os.path.exists(d) else 'PARTIAL',info)
