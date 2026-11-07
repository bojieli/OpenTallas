#!/usr/bin/env python3
"""vpp.py IN OUT DEF[,DEF..]: resolve `ifdef/`ifndef/`elsif/`else/`endif for the named defines only (others = undefined)."""
import sys,re
src=open(sys.argv[1]).read().split('\n'); defs=set(x for x in sys.argv[3].split(',') if x)
out=[];st=[]  # stack of (active_parent, taken, active)
act=True
for ln in src:
    m=re.match(r'\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w*)',ln)
    if m:
        k,n=m.groups()
        if k in('ifdef','ifndef'):
            c=(n in defs)==(k=='ifdef'); st.append([act,c,act and c]); act=act and c
        elif k=='elsif':
            p,t,_=st[-1]; c=(not t) and (n in defs); st[-1]=[p,t or c,p and c]; act=p and c
        elif k=='else':
            p,t,_=st[-1]; st[-1]=[p,True,p and not t]; act=p and not t
        else:
            p,_,_=st.pop(); act=p
        continue
    if act: out.append(ln)
assert not st
open(sys.argv[2],'w').write('\n'.join(out))
