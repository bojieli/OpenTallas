#!/usr/bin/env python3
# PRUNE-1103J candidates (local, read-only): usage cands.py host walk.tsv out.tsv
import sys,re,time,os,collections,glob
sys.argv_=sys.argv
host,w,out=sys.argv[1:4]
now=time.time(); ROOT='/srv/opentallas-scratch2'; CL=ROOT+'/claude'
rows={}
for l in open(w):
    d,p,kb,nw,sig,keep,fl,git=l.rstrip('\n').split('\t')
    rows[p]=dict(d=int(d),kb=int(kb),nw=int(nw),sig=int(sig),keep=int(keep),files=int(fl),git=int(git))
idx=collections.defaultdict(list)
for l in open('/tmp/p1103j_refs.tsv'):
    k,t=l.rstrip('\n').split('\t',1)
    c=t.split('/')
    for i in range(len(c)-1): idx[(c[i],c[i+1])].append((k,c,i))
ANCH=('srv','opentallas-scratch','opentallas-scratch2','home','ubuntu')
GENERIC=re.compile(r'^(attempt_\d+|run|runs|out|kit|kits|gen|lec|results|logs|reports|objects|asap7|base|src|items|signoff|work|tmp|rtl|build|\d+|[a-zA-Z]\d?|v\d+|eco\d*|wt|claude|kit-wave)$')
def refs(path):
    rel=path[len(ROOT)+1:].split('/')
    if len(rel)<2: return None
    best=None
    for k,c,i in idx.get((rel[-2],rel[-1]),()):
        x=i-1;y=len(rel)-3;ok=True;m=[rel[-2],rel[-1]]
        while x>=0 and y>=0:
            if c[x]!=rel[y]:
                ok=c[x] in ANCH or c[x].endswith(':')
                break
            m.append(rel[y]); x-=1;y-=1
        if ok and any(not GENERIC.match(q) for q in m):
            if k=='S': return ('S','/'.join(c))
            best=('L','/'.join(c))
    return best
import bisect
cache_words=set()
cf=os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')
cache_words=set(re.findall(r'[\w.+=-]+',open(cf,errors='replace').read()))
prot=[]
for l in open(os.path.expanduser('~/coord/PROTECTED-DBS.txt'),errors='replace'):
    for m in re.findall(r'/srv/opentallas-scratch2?/[^\s,;]+',l):
        prot.append(m.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip('/'))
links=[]
for l in open(w+'.links'):
    a,b=l.rstrip('\n').split('\t',1)
    links.append((a,b.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/')))
tg=sorted((b,a) for a,b in links)
tb=[x[0] for x in tg]
def link_in(p):
    i=bisect.bisect_left(tb,p)
    while i<len(tb) and (tb[i]==p or tb[i].startswith(p+'/')):
        if not tg[i][1].startswith(p+'/'): return tg[i][1]
        i+=1
    return None
live=[]
for f in glob.glob('/tmp/p1103j_live_*.txt'):
    live+=[l.strip().replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/').rstrip('/;') for l in open(f) if l.strip()]
def live_hit(p):
    att=bool(ATT0.match(p))
    return any(x==p or x.startswith(p+'/') or (not att and p.startswith(x+'/') and x.count('/')>4) for x in live)
ATT0=re.compile(r'^.*/items/[^/]+/attempt_\d+$')
GEN=re.compile(r'^(attempt_\d+|run|out|kit|kits|gen|lec|results|logs|src|eco\d*|v\d+|[a-zA-Z]\d?)$')
childs=collections.defaultdict(list)
for p in rows: childs[os.path.dirname(p)].append(p)
def exact_ref(p):
    rel=p[len(ROOT)+1:].split('/')
    if len(rel)<2: return False
    for k,c,i in idx.get((rel[-2],rel[-1]),()):
        if i+1!=len(c)-1: continue
        x=i-1;y=len(rel)-3;ok=True;m=[rel[-2],rel[-1]]
        while x>=0 and y>=0:
            if c[x]!=rel[y]:
                ok=c[x] in ANCH or c[x].endswith(':')
                break
            m.append(rel[y]); x-=1;y-=1
        if ok and any(not GENERIC.match(q) for q in m): return True
    return False
def full_ref(p):
    f=refs(p)
    if f: return f
    b=os.path.basename(p)
    if os.path.dirname(p) in (CL,CL+'/wt') and b in cache_words: return ('S','cacheword:'+b)
    if os.path.dirname(p)==CL and any(c[i]==b for k,c,i in idx_any.get(b,())): return ('L','name:'+b)
    if any(p==q or q.startswith(p+'/') or p.startswith(q+'/') for q in prot): return ('S','protected')
    if link_in(p): return ('S','symlink-in:'+link_in(p))
    if live_hit(p): return ('S','live-cmdline')
    for c in childs.get(p,()):
        f=full_ref(c)
        if f: return f
    return None
idx_any=collections.defaultdict(list)
for pair,lst in idx.items():
    for k,c,i in lst:
        if i==0: idx_any[c[0]].append((k,c,0))
# signed-file/.keep ancestors handled by rollup + explicit ancestor .keep from walk? ancestors need a file test: rows carry only counts,
# so the delete step re-checks ancestors on host.
EXCL=re.compile(r'(^|/)(tok-[^/]*|kv-fn-[^/]*|codex-ds-[^/]*|codex-token-[^/]*|[^/]*tok[^/]*|signed-keep|hub-backup|ref|rescue|manifests|home|autopilot|prune[^/]*|ss24[^/]*|[^/]*(KEEP|keep)[^/]*)(/|$)|veh|vehicle')
CODEX=re.compile(r'^(wt/)?codex')
ATT=re.compile(r'^(.*/items/[^/]+)/attempt_(\d+)$')
newest=collections.defaultdict(int)
for p in rows:
    m=ATT.match(p)
    if m: newest[m.group(1)]=max(newest[m.group(1)],int(m.group(2)))
res=collections.Counter(); out_rows=[]; kept=collections.Counter(); keptl=collections.defaultdict(list)
# class 1 superseded attempts
for p,r in rows.items():
    m=ATT.match(p)
    if not m or int(m.group(2))>=newest[m.group(1)]: continue
    age=(now-r['nw'])/3600; rel=p[len(CL)+1:]
    why=None
    if r['sig']: why='signed'
    elif r['keep']: why='keep'
    elif EXCL.search(rel): why='excl'
    elif age<6: why='recent'
    else:
        f=full_ref(p)
        if f: why='ref'+f[0]
    if why: kept['att-'+why]+=r['kb']; continue
    res['attempt']+=r['kb']; out_rows.append((p,r,'attempt',f"superseded kit-wave attempt (newer attempt_{newest[m.group(1)]})"))
# class 2/3 whole dirs, top-down
kids=collections.defaultdict(list)
for p in rows: kids[os.path.dirname(p)].append(p)
def visit(p):
    r=rows[p]; rel=p[len(CL)+1:] if p.startswith(CL+'/') else p[len(ROOT)+1:]
    age=(now-r['nw'])/3600
    if ATT.match(p) or '/items/' in p: return
    if EXCL.search(rel): kept['excl']+=r['kb']; return
    if p.startswith(CL) and CODEX.match(rel) and not re.match(r'codex-[^/]*wave',rel): kept['codex']+=r['kb']; keptl['codex'].append((p,r)); return
    if rel in('moved','autopilot','kit-wave','wt') or rel.startswith('moved/'):
        if rel=='moved' or rel.startswith('moved/'): kept['moved']+=r['kb']; return
    ch=kids.get(p,[])
    block=None
    if r['sig']: block='signed'
    elif r['keep']: block='keep'
    elif age<24: block='recent'
    else:
        f=full_ref(p)
        if f: block='ref'+f[0]
    if not block and p not in (CL,) and rel.count('/')>=0 and rel not in('wt','kit-wave'):
        cl='wt' if rel.startswith('wt/') else 'dir'
        res[cl]+=r['kb']; out_rows.append((p,r,cl,'idle>24h unsigned no .keep unreferenced')); return
    csig=sum(rows[c]['sig'] for c in ch); ckeep=sum(rows[c]['keep'] for c in ch)
    names={os.path.basename(c) for c in ch}
    atomic=(p!=CL and rel!='kit-wave' and not re.match(r'^kit-wave/[^/]+$',rel)) and (r['git'] or rel.startswith('wt/') or r['sig']>csig or r['keep']>ckeep or names&{'run','results','signoff','physical','tools','objects','refs'} or any(n.startswith('resign') for n in names))
    if ch and r['d']<5 and not atomic and not exact_ref(p):
        before=sum(rows[c]['kb'] for c in ch)
        for c in ch: visit(c)
        if r['kb']-before>1e6: kept['unrolled-files']+=r['kb']-before
    else:
        kept[block or 'leaf']+=r['kb']; keptl[block or 'leaf'].append((p,r))
visit(CL)
for p in sorted(kids.get(ROOT,[])):
    if p!=CL: kept['nonclaude-root']+=rows[p]['kb']
with open(out,'w') as o:
    for p,r,cl,why in sorted(out_rows,key=lambda x:-x[1]['kb']):
        o.write(f"{host}\t{p}\t{r['kb']/1e6:.2f}\t{time.strftime('%F %H:%M',time.localtime(r['nw']))}\t{cl}\t{why}\n")
print(host,'ELIGIBLE GB',{k:round(v/1e6,1) for k,v in res.items()},'n',len(out_rows))
print('KEPT GB',{k:round(v/1e6,1) for k,v in kept.items()})
for k in('refL','refS','recent','signed','keep','codex'):
    print(' largest kept',k)
    for p,r in sorted(keptl[k],key=lambda x:-x[1]['kb'])[:14]:
        print(f"   {r['kb']/1e6:6.1f}G age={(now-r['nw'])/3600:6.1f}h sig={r['sig']} keep={r['keep']} {p[len(ROOT)+1:]}")
print(' largest eligible')
for p,r,cl,why in sorted(out_rows,key=lambda x:-x[1]['kb'])[:30]:
    print(f"   {r['kb']/1e6:6.1f}G age={(now-r['nw'])/3600:6.1f}h {cl} {p[len(ROOT)+1:]}")
