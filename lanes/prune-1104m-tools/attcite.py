#!/usr/bin/env python3
# PRUNE-1104M read-only: which manifest attempts does any text file outside the attempt itself cite by path. usage: attcite.py manifest.tsv cited.txt
import os,sys,re
rows=[l.split('\t')[0].split(':',1)[1] for l in list(open(sys.argv[1]))[1:]]
R='/srv/opentallas-scratch2/claude'
key={}
for p in rows:
    m=re.search(r'[^/]+/items/[^/]+/attempt_\d+$',p); key[m.group().encode()]=p
pat=re.compile(b'(?:'+b'|'.join(re.escape(k) for k in sorted(key,key=len,reverse=True))+rb')(?![\w.-])')
pset=set(rows); EXT=re.compile(r'(\.(f|json|sh|tcl|mk|env|yaml|yml|txt|py|sdc|cfg|tsv|manifest)|Makefile|config\.mk)$')
cited={}; nf=0
for dp,dn,fn in os.walk(R):
    dn[:]=[d for d in dn if d not in('.git','objects','results','__pycache__')]
    own=re.match(r'(.*/items/[^/]+/attempt_\d+)(/|$)',dp); own=own.group(1) if own else None
    for f in fn:
        if not EXT.search(f): continue
        fp=os.path.join(dp,f)
        try:
            st=os.lstat(fp)
            if st.st_size>2_000_000 or os.path.islink(fp) or not os.path.isfile(fp): continue
            b=open(fp,'rb').read()
        except OSError: continue
        nf+=1
        for m in pat.finditer(b):
            t=key[m.group()]
            if t!=own and t not in cited: cited[t]=fp
open(sys.argv[2]+'.tmp','w').write(''.join(k+'\n' for k in cited)); os.rename(sys.argv[2]+'.tmp',sys.argv[2])
open(sys.argv[2]+'.why','w').write(''.join(f'{k}\t{v}\n' for k,v in cited.items()))
print('scanned',nf,'rows',len(rows),'cited',len(cited))
