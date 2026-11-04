#!/usr/bin/env python3
# PRUNE-1104M p4 (COORD rulings 01:2x) runs on epyc2. usage: p4.py scan out.tsv | del manifest.tsv
# Stage copies: marked outermost dirs idle>6h, no SIGNED, no .keep at any depth or above, not protected, busy test = dropbusy (cmdline, cwd, docker mount).
import os,re,sys,time,subprocess,json
R='/srv/opentallas-scratch2/claude'; SIG=re.compile(r'SIGNED|LOCAL_PASS_NEEDS_PARENT'); MK='.ot-run-spill-copy'
def prot(r):
    for ln in open('/tmp/p1104m_prot.txt',errors='replace'):
        for w in ln.split():
            w=w.split(':',1)[1] if re.match(r'^[A-Za-z0-9_.-]+:/',w) else w
            w=w.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip('/')
            if w.startswith('/') and (w==r or w.startswith(r+'/') or r.startswith(w+'/')): return True
    return False
def busy_set():
    me=set();p=os.getpid()
    while p>1:
        me.add(p); p=int(open(f'/proc/{p}/stat').read().rsplit(')',1)[1].split()[1])
    cmds=[];cwds=[]
    for d in os.listdir('/proc'):
        if not d.isdigit() or int(d) in me: continue
        try:
            cmds.append(open(f'/proc/{d}/cmdline','rb').read().replace(b'\0',b' ').decode('utf8','replace')); cwds.append(os.readlink(f'/proc/{d}/cwd'))
        except OSError: pass
    q=subprocess.run(['docker','ps','-q'],capture_output=True,text=True)
    if q.returncode: sys.exit('docker cannot answer')
    mounts=[]
    if q.stdout.split():
        m=subprocess.run(['docker','inspect','-f','{{range .Mounts}}{{.Source}}\n{{end}}']+q.stdout.split(),capture_output=True,text=True)
        if m.returncode: sys.exit('docker inspect failed')
        mounts=m.stdout.split()
    return cmds,cwds,mounts
def busy(r,B):
    a=r.replace('/srv/opentallas-scratch2/','/srv/opentallas-scratch/')
    c,w,m=B
    for t in(r,a):
        if any(t in x for x in c) or any(x==t or x.startswith(t+'/') for x in w) or any(x==t or x.startswith(t+'/') or t.startswith(x+'/') for x in m if x.count('/')>3): return True
    return False
def scan(d):
    nw=0;sz=0;sig=keep=False
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
def anc_keep(p):
    a=os.path.dirname(p)
    while a.startswith(R):
        if os.path.exists(a+'/.keep') and not re.match(r'^KW-FIX-\d+\b[^\n]*spill target[^\n]*$',open(a+'/.keep',errors='replace').read().strip()): return a
        a=os.path.dirname(a)
    return None
def check(p,lim,B):
    if not p.startswith(R+'/') or os.path.islink(p) or not os.path.isdir(p): return 'gone',0
    if prot(p): return 'protected',0
    k=anc_keep(p)
    if k: return 'keep-ancestor',0
    if busy(p,B): return 'busy',0
    nw,sz,sig,keep=scan(p)
    if sig: return 'signed',sz
    if keep: return 'keep',sz
    if time.time()-nw<lim: return 'recent',sz
    return None,sz
if sys.argv[1]=='scan':
    marks=[]
    for dp,dn,fn in os.walk(R):
        if MK in fn:
            marks.append(dp); dn[:]=[]   # outermost only
    B=busy_set(); o=open(sys.argv[2],'w')
    for p in marks:
        why,sz=check(p,6*3600,B)
        try: org=open(p+'/'+MK,errors='replace').read().strip()[:60]
        except OSError: org='?'
        nw=max((os.lstat(os.path.join(dp,x)).st_mtime for dp,_,fn in [next(os.walk(p))] for x in fn),default=0)
        o.write(f"{p}\t{sz/1e9:.2f}\t{why or 'OK'}\t{org}\n")
    o.close()
else:
    rows=[l.rstrip('\n').split('\t') for l in open(sys.argv[2])][1:]
    fr=0
    for r in rows:
        p=r[0].split(':',1)[1]; lim=(24 if r[4]=='dir' else 6)*3600
        B=busy_set(); why,sz=check(p,lim,B)
        if why: print('SKIP',why,p,flush=True); continue
        if sys.argv[1]=='del':
            subprocess.run(['rm','-rf','--',p]); 
            if os.path.exists(p): print('PARTIAL',p,flush=True)
        fr+=sz; print('DEL',p,f'{sz/1e9:.2f}',flush=True)
    print('DONE',sys.argv[1],'GB %.1f'%(fr/1e9),flush=True)
