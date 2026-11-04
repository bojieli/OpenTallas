#!/usr/bin/env python3
# PRUNE-1104N COORD 11:05 (3), read-only: facts per worktree under wt/. usage: wtscan.py out.tsv
import os,re,sys,json,time,subprocess as sp
from concurrent.futures import ThreadPoolExecutor as TP
R='/srv/opentallas-scratch2/claude/wt'; out=sys.argv[1]; me=os.getuid()
SIG=re.compile(r'(?<!NOT )(?<!NOT_)(?<![A-Z_])SIGNED\b|LOCAL_PASS')
def g(s,*a): return sp.run(['git','-C',s]+list(a),capture_output=True,text=True)
def one(n):
    d=f'{R}/{n}'
    if os.path.islink(d) or not os.path.isdir(d): return None
    if not os.path.exists(d+'/.git'): return (n,'','','no-git',0,0,0,0,0)
    head=g(d,'rev-parse','HEAD').stdout.strip(); br=g(d,'branch','--show-current').stdout.strip()
    st=g(d,'status','--porcelain').stdout.splitlines()
    idx=set(g(d,'ls-files').stdout.splitlines()); nw=0;own=0;sig=0;usig=0
    for dp,dn,fn in os.walk(d):
        if '.git' in dn: dn.remove('.git')
        for f in fn+dn:
            fp=os.path.join(dp,f)
            try: x=os.lstat(fp)
            except OSError: continue
            nw=max(nw,x.st_mtime)
            if x.st_uid!=me: own+=1
        for f in fn:
            if f=='signoff.json' or f.endswith('.signoff.json'):
                fp=os.path.join(dp,f)
                try: t=bool(SIG.search(open(fp,errors='replace').read()))
                except OSError: t=True
                if t:
                    sig+=1
                    if fp[len(d)+1:] not in idx: usig+=1
    return (n,head,br,'ok',len(st),int(nw),own,sig,usig)
names=sorted(os.listdir(R))
with TP(4) as ex: rows=[r for r in ex.map(one,names) if r]
with open(out+'.tmp','w') as o:
    for r in rows: o.write('\t'.join(map(str,r))+'\n')
os.rename(out+'.tmp',out); print('done',len(rows),time.strftime('%H:%M'))
