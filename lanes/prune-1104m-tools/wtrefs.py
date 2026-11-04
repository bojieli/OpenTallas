#!/usr/bin/env python3
# PRUNE-1104M read-only: text files anywhere on this host's scratch roots that cite one of the worktrees by path. usage: wtrefs.py out name...
import os,sys,re
out=sys.argv[1]; names=sys.argv[2:]
ROOTS=['/home/ubuntu/scratch-root/claude','/srv/opentallas-scratch2/claude']
EXT=re.compile(r'(\.(f|json|sh|tcl|mk|env|yaml|yml|txt|py|sdc|cfg|tsv|manifest)|Makefile|config\.mk)$')
pat=re.compile('|'.join(re.escape(n)+r'(?![\w.-])' for n in names).encode())
self_=['/home/ubuntu/scratch-root/claude/'+n for n in names]
o=open(out+'.tmp','w'); nf=0
for R in ROOTS:
    dev=os.lstat(R).st_dev
    for dp,dn,fn in os.walk(R):
        if any(dp==s or dp.startswith(s+'/') for s in self_): dn[:]=[]; continue
        dn[:]=[d for d in dn if d not in('.git','objects','results','__pycache__')]
        for f in fn:
            if not EXT.search(f): continue
            fp=os.path.join(dp,f)
            try:
                st=os.lstat(fp)
                if st.st_size>2_000_000 or not os.path.isfile(fp) or os.path.islink(fp): continue
                b=open(fp,'rb').read()
            except OSError: continue
            nf+=1
            m=pat.search(b)
            if m: o.write(f"{m.group().decode()}\t{fp}\t{int(st.st_mtime)}\n"); o.flush()
o.close(); os.rename(out+'.tmp',out); print('scanned',nf)
