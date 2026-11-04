#!/usr/bin/env python3
# PRUNE-1104N COORD 10:49 (1): delete listed latest-attempt dirs, re-verifying each on the host. usage: ltdel.py list.txt list|del [n]; SIGNED test is any SIGNED/LOCAL_PASS verdict word except NOT SIGNED.
import os,sys,re,time,json,subprocess,shutil
L,mode=sys.argv[1:3]; N=int(sys.argv[3]) if len(sys.argv)>3 else 10**9
ROOT='/srv/opentallas-scratch2/claude'
SIG=re.compile(r'(?<!NOT )(?<!NOT_)(?<![A-Z_])SIGNED\b|LOCAL_PASS')
SPILL=re.compile(r'^KW-FIX-\d+\b[^\n]*spill target[^\n]*$')  # one-line spill marker is not protection, COORD 22:56 and 03:2x
# COORD 11:19 (1): empty markers on these, confirmed empty per host; a marker with content is real. The size test stays below.
OKKEEP={ROOT+x+'/.keep' for x in('/kit-wave','/kit-wave/hbm','/kit-wave/qwen_kvsys/event28w_c','/kit-wave/qwen_compute/5346b95c915','/kit-wave/qwen_compute','/codex-head-wave-1131','/codex-head-lep-wave-1101')}
NT=re.compile(r'/(ss27|ss28|die-s81-51|die-s81-52|dh59|dh60|kit_turn_b|tok-[^/]*|kv-fn-[^/]*|codex-ds-[^/]*|veh[^/]*|vehicle[^/]*)(/|$)|/die-hbm-63/eco(/|$)')
PROT=[]
for ln in open('/tmp/p1104n_prot.txt',errors='replace'):
    PROT+=[w.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip('/') for w in re.findall(r'/srv/opentallas-scratch2?/[^\s,;]+',ln)]
def isprot(p): return any(q==p or q.startswith(p+'/') or p.startswith(q+'/') for q in PROT)
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
    links={};nl={};bl={};nw=0;sig=False;keep=False
    for dp,dn,fn in os.walk(d):
        nw=max(nw,os.lstat(dp).st_mtime)
        for f in fn:
            fp=os.path.join(dp,f)
            try: s=os.lstat(fp)
            except OSError: continue
            nw=max(nw,s.st_mtime); links[s.st_ino]=links.get(s.st_ino,0)+1; nl[s.st_ino]=s.st_nlink; bl[s.st_ino]=s.st_blocks*512
            if f=='.keep': keep=True
            if f=='signoff.json' or f.endswith('.signoff.json'):
                try:
                    if SIG.search(open(fp,errors='replace').read()): sig=True
                except OSError: sig=True
    return nw,sum(bl[i] for i in bl if links[i]>=nl[i]),sig,keep
S=openset(); last=time.time(); fr=0;n=0;sk={}
def skip(p,w): sk[w]=sk.get(w,0)+1; print('SKIP',w,p,flush=True)
for p in [l.strip() for l in open(L) if l.strip()]:
    if n>=N: break
    now=time.time()
    if now-last>120: S=openset(); last=now
    if not os.path.isdir(p) or os.path.islink(p): skip(p,'gone'); continue
    if not p.startswith(ROOT+'/') or '/items/' not in p: skip(p,'outside'); continue
    if isprot(p): skip(p,'protected'); continue
    if NT.search(p): skip(p,'no-touch'); continue
    if any(q==p or q.startswith(p+'/') for q in S): skip(p,'open'); continue
    a=os.path.dirname(p); kp=False
    while a.startswith(ROOT):
        k=a+'/.keep'
        if os.path.exists(k) and not (k in OKKEEP and os.path.getsize(k)==0) and not SPILL.match(open(k,errors='replace').read().strip()): kp=True
        a=os.path.dirname(a)
    if kp: skip(p,'keep-ancestor'); continue
    nw,u,sig,keep=scan(p)
    if sig: skip(p,'signed'); continue
    if keep: skip(p,'keep'); continue
    if now-nw<6*3600: skip(p,'recent'); continue
    if mode=='del':
        shutil.rmtree(p,ignore_errors=True)
        if os.path.exists(p): print('PARTIAL',p,flush=True)
    print('OK',p,'%.2f'%(u/1e9),flush=True); fr+=u;n+=1
print('DONE',mode,'ok',n,'GB %.1f'%(fr/1e9),'skips',sk,flush=True)
