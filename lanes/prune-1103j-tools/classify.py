#!/usr/bin/env python3
# PRUNE-1103J classify walk rows of one host (local, read-only). usage: classify.py host walk.tsv
import sys,re,time,os,collections
host,w=sys.argv[1:3]
now=time.time()
rows={}
for l in open(w):
    d,p,kb,nw,sig,keep,fl,git=l.rstrip('\n').split('\t')
    rows[p]=dict(d=int(d),kb=int(kb),nw=int(nw),sig=int(sig),keep=int(keep),files=int(fl),git=int(git))
# reference index
S=set();L=set();SX=collections.defaultdict(set)
tok=[]
for l in open('/tmp/p1103j_refs.tsv'):
    k,t=l.rstrip('\n').split('\t',1); tok.append((k,t))
CL='/srv/opentallas-scratch2/claude'
# map token -> rel components below claude if token has 'claude/' (or wt/ kit-wave/ etc)
idx=collections.defaultdict(list)
for k,t in tok:
    c=t.split('/')
    for i in range(len(c)-1):
        idx[(c[i],c[i+1])].append((k,c,i))
def refs(path):
    """return (kind,token) if some token names this path or a descendant (matching >=2 trailing comps), or 'claude/<x>' for depth-1"""
    rel=path[len('/srv/opentallas-scratch2/'):].split('/')
    # rel like ['claude','wt','foo',...]
    a,b=rel[-2],rel[-1]
    best=None
    for k,c,i in idx.get((a,b),()):
        # verify earlier comps agree as far as both go
        x=i-1;y=len(rel)-3;ok=True
        while x>=0 and y>=0:
            if c[x]!=rel[y]:
                ok = c[x] in('srv','opentallas-scratch','opentallas-scratch2','home','ubuntu') or c[x].endswith(':')
                if not ok: pass
                break
            x-=1;y-=1
        if ok:
            if k=='S': return ('S','/'.join(c))
            best=('L','/'.join(c))
    return best
def has_keep_anc(p):
    a=os.path.dirname(p)
    while len(a)>len('/srv/opentallas-scratch2'):
        if a in keep_self: return True
        a=os.path.dirname(a)
    return False
keep_self=set()
EXCL=re.compile(r'(^|/)(tok-[^/]*|kv-fn-[^/]*|codex-ds-[^/]*|codex-token-[^/]*)(/|$)|veh')
def cls(p,r):
    rel=p[len(CL)+1:] if p.startswith(CL+'/') else p[len('/srv/opentallas-scratch2/'):]
    age=(now-r['nw'])/3600
    if r['sig']: return 'signed'
    if r['keep']: return 'keep'
    if EXCL.search(rel): return 'excl-name'
    if age<24: return 'recent'
    f=refs(p)
    if f: return 'ref'+f[0]
    return 'idle'
top=[(p,r) for p,r in rows.items() if r['d']==2 and p.startswith(CL+'/')]
tot=collections.Counter()
for p,r in top: tot[cls(p,r)]+=r['kb']
print(host,'depth1 of claude GB by class:',{k:round(v/1e6) for k,v in tot.items()})
print('\ntop dirs:')
for p,r in sorted(top,key=lambda x:-x[1]['kb'])[:45]:
    print(f"{r['kb']/1e6:7.1f}G age={(now-r['nw'])/3600:7.1f}h sig={r['sig']:4d} keep={r['keep']:3d} {cls(p,r):9s} {p[len(CL)+1:]}")
print('\nnon-claude:')
for p,r in rows.items():
    if r['d']==1 and p!=CL: print(f"{r['kb']/1e6:7.1f}G age={(now-r['nw'])/3600:7.1f}h sig={r['sig']} keep={r['keep']} {p}")
