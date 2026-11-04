#!/usr/bin/env python3
# PRUNE-1104N COORD 10:49 (1): read-only host scan of attempt dirs. Each latest attempt and each non-attempt item child: by-inode freed bytes (inodes with all links inside the dir),
# newest mtime, SIGNED count, .keep count. usage: ltscan.py out.tsv [wave-root-glob ...]
import os,re,sys,glob,time
out=sys.argv[1]; R='/srv/opentallas-scratch2/claude'
SIG=re.compile(r'"(verdict|status|result)"\s*:\s*"(SIGNED|LOCAL_PASS[A-Z_]*)"')
roots=[]
for g in sys.argv[2:] or ['kit-wave/*/*/items','codex-*wave*/items','codex-*wave*/*/items','codex-*wave*/*/*/items','codex-*wave*/*/*/*/items']:
    roots+=glob.glob(f'{R}/{g}')
def stat(d):
    links={};nl={};bl={};nw=0;sig=0;keep=0;du=0
    for dp,dn,fn in os.walk(d):
        try: nw=max(nw,os.lstat(dp).st_mtime)
        except OSError: pass
        for f in fn:
            p=os.path.join(dp,f)
            try: s=os.lstat(p)
            except OSError: continue
            nw=max(nw,s.st_mtime)
            links[s.st_ino]=links.get(s.st_ino,0)+1; nl[s.st_ino]=s.st_nlink; bl[s.st_ino]=s.st_blocks*512
            if f=='.keep': keep+=1
            if f=='signoff.json' or f.endswith('.signoff.json'):
                try:
                    if SIG.search(open(p,errors='replace').read()): sig+=1
                except OSError: sig+=1
    return sum(bl[i] for i in bl if links[i]>=nl[i]),sum(bl.values()),nw,sig,keep
with open(out+'.tmp','w') as o:
    for r in sorted(roots):
        for i in sorted(os.listdir(r)):
            it=f'{r}/{i}'
            if not os.path.isdir(it): continue
            ch=os.listdir(it); ats=[int(x[8:]) for x in ch if re.fullmatch(r'attempt_\d+',x)]; top=max(ats) if ats else None
            for c in ch:
                p=f'{it}/{c}'
                if os.path.islink(p) or not os.path.isdir(p): continue
                m=re.fullmatch(r'attempt_(\d+)',c)
                if m and int(m.group(1))!=top: continue
                u,d,nw,sg,k=stat(p)
                o.write(f"{'latest' if m else 'other'}\t{p}\t{u}\t{d}\t{int(nw)}\t{sg}\t{k}\n")
os.rename(out+'.tmp',out); print('done',out,time.strftime('%H:%M'))
