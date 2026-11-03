#!/usr/bin/env python3
# PRUNE-1103B: intermediate stage DBs ([1-5]_*.odb) + objects/ of idle (>24h) ORFS runs.
import os, sys, time, json, subprocess, re
mode, root, host, manifest, protf = sys.argv[1:6]
now = time.time(); IDLE = 24*3600
prot = [l.split()[1] for l in open(protf) if l.strip() and not l.startswith('#') and len(l.split())>1 and l.split()[0]==host]
EXCL = re.compile(r'^(tok-|kv-fn-|codex-ds-)|veh')
LIVE = {'die-s81-51'}
# open paths
openp = set()
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        openp.add(os.readlink(f'/proc/{pid}/cwd'))
        for fd in os.listdir(f'/proc/{pid}/fd'):
            try: openp.add(os.readlink(f'/proc/{pid}/fd/{fd}'))
            except OSError: pass
    except OSError: pass
try:
    ids = subprocess.run(['docker','ps','-q'],capture_output=True,text=True,timeout=60).stdout.split()
    if ids:
        js = json.loads(subprocess.run(['docker','inspect']+ids,capture_output=True,text=True,timeout=120).stdout)
        for c in js:
            for m in c.get('Mounts',[]): openp.add(m.get('Source',''))
except Exception as e: print('docker?',e, file=sys.stderr)
def touched(run):
    for p in openp:
        if p.startswith(run+'/') or p==run or (run.startswith(p+'/') and p.count('/')>4): return True
    return False
rows=[]; tot=0; skip={}
def sk(k): skip[k]=skip.get(k,0)+1
for top in sorted(os.listdir(root)):
    tp=os.path.join(root,top)
    if not os.path.isdir(tp) or os.path.islink(tp): continue
    if EXCL.search(top) or top in LIVE: sk('excl'); continue
    for dp, dns, fns in os.walk(tp):
        if os.path.basename(dp)!='results' or 'asap7' not in dns: continue
        dns[:] = []
        run=os.path.dirname(dp)
        if any(run.startswith(p.rstrip('/')) or p.startswith(run+'/') for p in prot): sk('prot'); continue
        # .keep in run or ancestors (ignore repo results/rtl .keep)
        a=run; kp=False
        while len(a)>=len(tp):
            if os.path.exists(os.path.join(a,'.keep')): kp=True; break
            a=os.path.dirname(a)
        if kp: sk('keep'); continue
        newest=0; files=[]; odbs={}; signed=False
        for d2,_,f2 in os.walk(run):
            for f in f2:
                fp=os.path.join(d2,f)
                try: st=os.lstat(fp)
                except OSError: continue
                newest=max(newest,st.st_mtime)
                if f=='signoff.json':
                    try:
                        if 'SIGNED' in open(fp).read(): signed=True
                    except OSError: pass
                rel=fp[len(run)+1:]
                if os.path.islink(fp) or st.st_nlink>1: continue
                if rel.startswith('results/') and re.match(r'[1-6]_.*\.odb$',f):
                    odbs.setdefault(d2,[]).append((f,fp,st.st_size,st.st_mtime))
        def stg(f):
            m=re.match(r'(\d)_(\d)?',f); return (int(m.group(1)), int(m.group(2) or 9), f)
        for d2,L in odbs.items():
            L.sort(key=lambda x: stg(x[0]))
            for f,fp,sz,mt in L[:-1]:
                if f[0] in '12345': files.append((fp,sz,mt))
        pj=os.path.join(os.path.dirname(run),'signoff.json')
        if os.path.exists(pj):
            try:
                if 'SIGNED' in open(pj).read(): signed=True
            except OSError: pass
        if signed: sk('signed'); continue
        if now-newest<IDLE: sk('recent'); continue
        if touched(run): sk('open'); continue
        for fp,sz,mt in files:
            rows.append((fp,sz,mt)); tot+=sz
with open(manifest,'w') as m:
    for fp,sz,mt in rows:
        m.write(f"{host}\t{fp}\t{sz/1e9:.3f}\t{time.strftime('%F %H:%M',time.localtime(mt))}\tidle>24h ORFS run, not SIGNED/.keep/PROTECTED/open: lower-stage DB [1-5]_*.odb; highest-stage odb per results dir + logs/reports/objects kept (stage-resume stays possible)\n")
print(mode, 'files',len(rows),'GB %.1f'%(tot/1e9),'skips',skip)
if mode=='del':
    fr=0
    for fp,sz,mt in rows:
        try:
            st=os.lstat(fp)
            if now-st.st_mtime<IDLE: continue
            os.unlink(fp); fr+=sz
        except OSError: pass
    print('deleted GB %.1f'%(fr/1e9))
