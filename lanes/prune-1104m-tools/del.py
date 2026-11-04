#!/usr/bin/env python3
# PRUNE-1104M: re-verify each manifest row on the host right before rm; never touches anything failing a check. usage: del.py manifest.tsv list|del
import os,sys,re,time,json,subprocess,shutil
man,mode=sys.argv[1:3]
ROOT='/srv/opentallas-scratch2'; SIG=re.compile(r'"(verdict|status|result)"\s*:\s*"(SIGNED|LOCAL_PASS[A-Z_]*)"')
# PRUNE-1104M: only a one-line KW-FIX spill-target marker is not protection (COORD 22:56 and 03:2x); empty or other text protects.
SPILL=re.compile(r'^KW-FIX-\d+\b[^\n]*spill target[^\n]*$')
# COORD ruling 11-04: attempts only. a = codex-kv-wave-1131/.keep (idle>6h, uncited); b = empty kit-wave/.keep, kit-wave/hbm/.keep (idle>24h, no plan-cache citation). Env P1104M_RULE.
RULE=os.environ.get('P1104M_RULE','').split(',')
CITED=set(l.strip() for l in open('/tmp/p1104m_cited.txt')) if os.path.exists('/tmp/p1104m_cited.txt') else set()
need24=[False]
def keep_protects(f,cl='dir'):
    try: t=open(f,errors='replace').read().strip()
    except OSError: return True
    if SPILL.match(t): return False
    if cl=='attempt':
        if 'a' in RULE and f==ROOT+'/claude/codex-kv-wave-1131/.keep': return False
        if 'b' in RULE and t=='' and f in(ROOT+'/claude/kit-wave/.keep',ROOT+'/claude/kit-wave/hbm/.keep'):
            need24[0]=True; return False
    return True
PROT=[]
for pf in ('/tmp/p1104m_prot.txt',):
    for ln in open(pf,errors='replace'):
        for w in re.findall(r'/srv/opentallas-scratch2?/[^\s,;]+',ln): PROT.append(w.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip('/'))
def isprot(p): return any(q==p or q.startswith(p+'/') or p.startswith(q+'/') for q in PROT)
def mentions(it,a,ats):
    # a newer attempt that resumes from this one by path (from PRUNE-1103I kw.py)
    for b in ats:
        if b==a: continue
        r=subprocess.run(f"find {it}/attempt_{b} -maxdepth 3 -type f -size -1024k \\( -name '*.json' -o -name '*.sh' -o -name '*.mk' -o -name '*.tcl' -o -name '*.env' -o -name '*.f' \\) -print0 | xargs -0 -r grep -lsF -- '/attempt_{a}/' | head -1",shell=True,capture_output=True,text=True)
        if r.stdout.strip(): return r.stdout.strip()
    return None
ATT=re.compile(r'^(.*/items/[^/]+)/attempt_(\d+)$')
def openset():
    S=set()
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        try:
            for x in('cwd','root'):
                try: S.add(os.readlink(f'/proc/{pid}/{x}'))
                except OSError: pass
            try:
                for fd in os.listdir(f'/proc/{pid}/fd'):
                    try: S.add(os.readlink(f'/proc/{pid}/fd/{fd}'))
                    except OSError: pass
            except OSError: pass
            a=open(f'/proc/{pid}/cmdline','rb').read().replace(b'\0',b' ').decode('utf8','replace')
            S.update(re.findall(r'/srv/opentallas-scratch2?/[^\s\'"]+',a))
        except OSError: pass
    ids=subprocess.run(['docker','ps','-q'],capture_output=True,text=True,timeout=120).stdout.split()
    if ids:
        for c in json.loads(subprocess.run(['docker','inspect']+ids,capture_output=True,text=True,timeout=240).stdout):
            for m in c.get('Mounts',[]): S.add(m.get('Source',''))
    return {p.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip(';/') for p in S if p.startswith('/srv/')}
def scan(d):
    nw=0;sz=0;sig=False;keep=False
    for dp,dn,fn in os.walk(d):
        try: nw=max(nw,os.lstat(dp).st_mtime)
        except OSError: pass
        for f in fn:
            fp=os.path.join(dp,f)
            try: st=os.lstat(fp)
            except OSError: continue
            nw=max(nw,st.st_mtime);sz+=st.st_blocks*512
            if f=='.keep': keep=True
            if f=='signoff.json' or f.endswith('.signoff.json'):
                try:
                    if SIG.search(open(fp,errors='replace').read()): sig=True
                except OSError: sig=True
    return nw,sz,sig,keep
S=openset(); last=time.time(); fr=0; n=0; sk={}
def skip(p,w):
    sk[w]=sk.get(w,0)+1; print('SKIP',w,p,flush=True)
rows=[l.rstrip('\n').split('\t') for l in open(man)][1:]
for r in rows:
    p=r[0].split(':',1)[1]; cl=r[4]; now=time.time()
    if now-last>120: S=openset(); last=now
    if not os.path.isdir(p) or os.path.islink(p): skip(p,'gone'); continue
    if not p.startswith(ROOT+'/claude/'): skip(p,'outside'); continue
    if isprot(p): skip(p,'protected'); continue
    if cl not in('attempt','dir'): skip(p,'class'); continue
    if cl=='dir' and subprocess.run(['find',p,'-name','.git','-print','-quit'],capture_output=True,text=True).stdout.strip(): skip(p,'git'); continue
    if any(q==p or q.startswith(p+'/') for q in S) or (cl=='dir' and any(p.startswith(q+'/') and q.count('/')>4 for q in S)): skip(p,'open'); continue
    need24[0]=False
    if p in CITED: skip(p,'cited-text'); continue
    a=os.path.dirname(p); kp=False
    while a.startswith(ROOT+'/claude'):
        if os.path.exists(a+'/.keep') and keep_protects(a+'/.keep',cl): kp=True
        a=os.path.dirname(a)
    if kp: skip(p,'keep-ancestor'); continue
    if cl=='attempt':
        m=ATT.match(p)
        it=m.group(1); ats=[int(x[8:]) for x in os.listdir(it) if re.fullmatch(r'attempt_\d+',x)]
        if not ats or int(m.group(2))>=max(ats): skip(p,'no-newer-attempt'); continue
        if mentions(it,int(m.group(2)),ats): skip(p,'resume-mention'); continue
    nw,sz,sig,keep=scan(p)
    if sig: skip(p,'signed'); continue
    if keep: skip(p,'keep'); continue
    lim=6*3600 if cl=='attempt' and not need24[0] else 24*3600
    if now-nw<lim: skip(p,'recent'); continue
    if mode=='del':
        shutil.rmtree(p,ignore_errors=True)
        if os.path.exists(p): print('PARTIAL',p,flush=True)
    fr+=sz; n+=1
print('DONE',mode,'rows',len(rows),'ok',n,'GB %.1f'%(fr/1e9),'skips',sk,flush=True)
