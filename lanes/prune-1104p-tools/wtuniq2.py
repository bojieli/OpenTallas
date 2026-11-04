#!/usr/bin/env python3
# PRUNE-1104P, COORD order: "none uniquely counted" with symlinks followed. For each cited path: resolve through git links (mode 120000) at HEAD and at origin/main, each in its own tree, then compare the final blobs. Reports aliases read. usage: wtuniq2.py worktree paths.txt
import subprocess as sp,sys,collections,posixpath
w,pf=sys.argv[1:3]
def g(*a): return sp.run(['git','-C',w]+list(a),capture_output=True,text=True).stdout
def entry(rev,p):
    o=g('ls-tree',rev,'--',p).strip()
    if not o: return None
    m,t,rest=o.split(None,2); return m,rest.split('\t')[0]
def resolve(rev,p):
    seen=0; link=False
    while True:
        # walk parents too, so a link in a directory component is followed
        parts=p.split('/'); moved=False
        for i in range(1,len(parts)+1):
            sub='/'.join(parts[:i]); e=entry(rev,sub)
            if e is None: return None,link,p
            if e[0]=='120000':
                tgt=g('cat-file','blob',e[1]); link=True; seen+=1
                if seen>16 or tgt.startswith('/'): return 'LINK-OUT:'+tgt,link,p
                p=posixpath.normpath(posixpath.join(posixpath.dirname(sub),tgt,*parts[i:])); moved=True; break
        if not moved: return entry(rev,p)[1],link,p
print('HEAD',g('rev-parse','HEAD').strip(),'main',g('log','-1','--format=%h %ad','--date=format:%m-%d %H:%M','origin/main').strip())
C=collections.Counter(); bad=[]; al=[]
for l in open(pf):
    r=l.strip()
    if not r: continue
    h,lh,ph=resolve('HEAD',r); m,lm,pm=resolve('origin/main',r)
    if lh or lm: al.append((r,ph,pm,(h or '')[:12],(m or '')[:12],h==m))
    if h is None: k='not-in-HEAD'
    elif m is None: k='main-absent'
    elif h==m: k='same'
    else: k='differs'
    C[k]+=1
    if k!='same': bad.append((k,r,(h or '')[:12],(m or '')[:12]))
print(dict(C)); print('aliases',len(al))
for a in al: print('ALIAS',a)
for b in bad[:40]: print('BAD',b)
