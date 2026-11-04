#!/usr/bin/env python3
# PRUNE-1103J: re-verify each manifest row on the host right before rm; never touches anything failing a check. usage: del.py manifest.tsv list|del
import os,sys,re,time,json,subprocess,shutil
man,mode=sys.argv[1:3]
ROOT='/srv/opentallas-scratch2'; SIG=re.compile(r'"verdict"\s*:\s*"(SIGNED|LOCAL_PASS_NEEDS_PARENT)"')
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
    if any(q==p or q.startswith(p+'/') for q in S) or (cl=='dir' and any(p.startswith(q+'/') and q.count('/')>4 for q in S)): skip(p,'open'); continue
    a=os.path.dirname(p); kp=False
    while a.startswith(ROOT+'/claude'):
        if os.path.exists(a+'/.keep'): kp=True
        a=os.path.dirname(a)
    if kp: skip(p,'keep-ancestor'); continue
    if cl=='attempt':
        m=ATT.match(p)
        it=m.group(1); ats=[int(x[8:]) for x in os.listdir(it) if re.fullmatch(r'attempt_\d+',x)]
        if not ats or int(m.group(2))>=max(ats): skip(p,'no-newer-attempt'); continue
    nw,sz,sig,keep=scan(p)
    if sig: skip(p,'signed'); continue
    if keep: skip(p,'keep'); continue
    lim=6*3600 if cl=='attempt' else 24*3600
    if now-nw<lim: skip(p,'recent'); continue
    if mode=='del':
        shutil.rmtree(p,ignore_errors=True)
        if os.path.exists(p): print('PARTIAL',p,flush=True)
    fr+=sz; n+=1
print('DONE',mode,'rows',len(rows),'ok',n,'GB %.1f'%(fr/1e9),'skips',sk,flush=True)
