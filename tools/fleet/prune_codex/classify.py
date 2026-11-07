#!/usr/bin/env python3
# classify.py: per-host action plan for Codex trees. Output $CP_ROOT/plan/<host>.tsv + summary
# PRUNE-AUDIT-1 11-07 fixes: (a) tgt_above stopped BEFORE testing the tree top, so a cite of the top kept the top row and deleted every
# child; (b) a relative cite protected only its ancestors, never what is under it; (c) a cited file or a path below the scan depth kept
# nothing around it, so "dir/run.log retained" deleted the rest of dir; (d) a scan with an empty kw.tsv (collected before kwexpand ended) is refused unless PREVIEW=1.
import json,gzip,os,re,sys,time,collections,csv
ROOT=os.environ.get('CP_ROOT','/tmp/cp1106'); SCAN=os.environ.get('CP_SCAN',ROOT+'/scan')
HOSTS='epyc6 epyc5 localhost intel2 epyc4 intel1 epyc2'.split()
ALIAS={'epyc6','epyc5','epyc4','intel1'}
now=time.time(); SIX=6*3600
QHOURS=float(os.environ.get('QHOURS','24'))
def N(h,p):
    p=os.path.normpath(p)
    if p=='/home/ubuntu/scratch-root' or p.startswith('/home/ubuntu/scratch-root/'):
        p=('/srv/opentallas-scratch' if h=='localhost' else '/srv/opentallas-scratch3')+'/__SR'+p[len('/home/ubuntu/scratch-root'):] if h=='localhost' else '/srv/opentallas-scratch3'+p[len('/home/ubuntu/scratch-root'):]
    if h in ALIAS and p.startswith('/srv/opentallas-scratch/'): p='/srv/opentallas-scratch2/'+p[len('/srv/opentallas-scratch/'):]
    return p
def NA(p):  # any-host normalise
    return N('epyc6',p)
def ancs(p):
    o=[]
    while True:
        q=os.path.dirname(p)
        if q==p or len(q)<2: return o
        o.append(q); p=q
# ---- blockers
SRCNAME=re.compile(r'^(src.*|repo.*|wt|wc\d*|tools?|tools?[-_].*|kit_rtl.*|bind.*|flow.*|.*vehicle.*|veh.*|tok.*|opentallas.*|\.git|.*worktree.*|.*-src|.*_src|autopilot|hub.*)$')
TOPNAME=re.compile(r'(?:^|[-_])(bind|source|src|tools?|flow|veh\d*|vehicle|compiler|images|roms|ds|tok|token|kernel|model|history|ci)(?:[-_.]|\d|$)')
GENERIC=re.compile(r'^(kit-wave|runs?|items|kits|eco|builds?\d*|attempts?|work|results|out|logs|qwen_kvsys|qwen_compute|s81|s81_head|hbm|[0-9a-f]{12,40}|e\w{6,}|l48\w*|d44\w*|event\w*)$')
glob_t=collections.defaultdict(list) # target -> [(kind,host,source)]
for l in open(ROOT+'/global.tsv'):
    k,h,t,s=l.rstrip('\n').split('\t')
    if k=='QREL': continue
    if k=='A' and s=='OWNERS.tsv': continue   # failure ownership table: evidence log, not an input
    if k=='P' and 'codex' not in t and not any(True for _ in ()): pass
    glob_t[NA(t)].append((k,h,s))
qrel=set()
for l in open(ROOT+'/global.tsv'):
    k,h,t,s=l.rstrip('\n').split('\t')
    if k=='QREL': qrel.add(t)
proc=collections.defaultdict(list)
for h in HOSTS:
    for l in open(f'{SCAN}/{h}/proc.tsv'):
        k,t=l.rstrip('\n').split('\t')[:2]
        hh='any' if k in('cmd','dockercmd') else h
        proc[N(h,t)].append((k,hh,h))
NOISE=re.compile(r'^/home/ubuntu/coord/|/claude/(?:[^/]+/)*(?:src[^/]*|repo|repo_[^/]*|wc\d*|moved[^/]*|[^/]*-moved-[^/]*|relocated[^/]*|tools|opentallas[^/]*)/|/claude/(?:wt/|prune|archive|arch|PRUNE|reaper)[^/]*|/(?:results/token_pass|results/rtl|tools/fleet)/|ARCHIVED\.json$|/cp1106|/arch1106|/scratch-prune|/home/ubuntu/[^/]*prune|/prune[^/]*/|/wave_cg_frz/|/kw\d+/(?:wave_|src_)|/hub-coord/|^/home/ubuntu/tmp/|/plandir/')
WEAK=('.txt','.tsv','.sdc')
STRONGJ=re.compile(r'^(freeze|PRD|kit_rtl|eco_loop|budget|PROVENANCE|AUTOPILOT|.*recipe.*|.*spec.*|.*plan.*|.*job.*|.*inputs.*|.*signoff.*|resume.*|bind.*|asbuilt.*|.*sidecar.*)')
refs=[]  # (kind,target,chost,citer,mtime)
nr=collections.Counter()
for h in HOSTS:
    # (d) the first run collected intel2 + localhost kw.tsv at 0 bytes while kwexpand was still running: a real host always has keyword rows
    kwf=f'{SCAN}/{h}/kw.tsv'
    if os.path.exists(kwf) and os.path.getsize(kwf)==0 and os.path.getsize(f'{SCAN}/{h}/refs.tsv.gz')>64:
        print('EMPTY-KW',h,'scan collected before kwexpand ended',file=sys.stderr)
        if not os.environ.get('PREVIEW'): sys.exit(f'refusing a plan on incomplete scan of {h}; rescan, or PREVIEW=1 for a manifest nobody deletes from')
    for f,comp in ((f'{SCAN}/{h}/refs.tsv.gz',True),(kwf,False)):
        if not os.path.exists(f): continue
        def rows():
            try:
                yield from (gzip.open(f,'rt',errors='replace') if comp else open(f,errors='replace'))
            except EOFError:
                print('TRUNCATED',f,file=sys.stderr)
                if not os.environ.get('PREVIEW'): raise
        for l in rows():
            c=l.rstrip('\n').split('\t')
            if len(c)<4: continue
            k,t,ci,mt=c[0],c[1],c[2],int(c[3] or 0)
            if k=='R':
                if NOISE.search(ci): nr['noise']+=1; continue
                if ci.endswith(WEAK) and not re.search(r'plan|pins|bind|\.f$',os.path.basename(ci)): nr['weak']+=1; continue
                if '/autopilot/review/' in ci or os.path.basename(ci).startswith('jobs_run'): nr['review']+=1; continue
                bn=os.path.basename(ci)
                if bn.endswith('.json') and not STRONGJ.search(bn) and now-mt>48*3600: nr['weakjson-old']+=1; continue
                if ci.startswith('/home/ubuntu/') and not ci.startswith('/home/ubuntu/scratch') and now-mt>48*3600: nr['home-old']+=1; continue
                tn,cn=N(h,t),N(h,ci)
                cm=os.path.commonpath([tn,cn])
                bm=os.path.basename(cm)
                if cm.count('/')>=5 and not GENERIC.match(bm) and os.path.basename(os.path.dirname(cm))!='items' and not SRCNAME.match(bm):
                    nr['self']+=1; continue
            nr[k]+=1
            refs.append((k,N(h,t),h,N(h,ci),mt))
print('refs',nr,len(refs),file=sys.stderr)
# ---- wave state
wave={}  # (host,attemptpath) -> (status,plan_current,die,item)
st=json.load(open(ROOT+'/kit_wave_state.json'))['items']
planc={}
for r in csv.DictReader(open(ROOT+'/kit_wave_stages.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    planc[(r['die'],r['item'],r['block_sha'][:12])]=r
    planc.setdefault((r['die'],r['item']),r)
    if r['plan_current']=='yes': planc[(r['die'],r['item'])]=r
AT=re.compile(r'^(?:(\w+):)?(/.*?/attempt_\d+)(?:/|$)')
HN={'local':'localhost'}
live_attempts=set(); open_attempts={}; term=collections.Counter()
LIVE={'ENQUEUED','RUNNING','QUEUED','PENDING','PENDING-DEP','WAIT-PARENT','RETRY-INFRA','PLACE','LAUNCHED','STARTED'}
for key,v in st.items():
    s=v.get('status'); ev=v.get('evidence') or ''; kit=v.get('kit') or ''
    m=AT.match(ev) or AT.match(kit)
    if not m: continue
    h=HN.get(m.group(1),m.group(1) or 'any'); a=NA(m.group(2))
    r=planc.get((v.get('die'),v.get('item')),{})
    pc=r.get('plan_current','')
    term[(s,pc)]+=1
    if s in LIVE or s not in('FAIL','CANCELLED','SUPERSEDED','SIGNED'):
        live_attempts.add(a)
    elif s in('FAIL','CANCELLED') and pc=='yes':
        open_attempts[a]=(v.get('die'),v.get('item'),s,h,ev)
print('wave',term.most_common(),'live',len(live_attempts),'open',len(open_attempts),file=sys.stderr)
# newest resume ODB of each open attempt, over all hosts: TRIM there only, other hosts' copies go
ODB_BAD=re.compile(r'fail|tmp|partial',re.I)
trimhost={}; trimkeep={}
for h in HOSTS:
    for l in open(f'{SCAN}/{h}/odbs.tsv'):
        p,sz,mt=l.rstrip('\n').split('\t'); p=N(h,p); sz=int(sz); mt=int(mt)
        m=re.search(r'^(.*/attempt_\d+)/',p)
        if not m or m.group(1) not in open_attempts: continue
        if ODB_BAD.search(os.path.basename(p)): continue
        if '/plandir/' in p or '/rtl' in p: continue
        a=m.group(1)
        if a not in trimkeep or mt>trimkeep[a][1]: trimkeep[a]=(p,mt,sz); trimhost[a]=h
for a,v in open_attempts.items():
    trimhost.setdefault(a,v[3])
# ---- counted refs from the cache
cache=json.load(open(os.environ.get('CACHE','/home/ubuntu/.local/state/fleet-viz/release_tree_plan_cache.json')))
counted=collections.defaultdict(list) # (die,kind,name)->[(host,path)]
HM={'local':'localhost'}
for die,v in cache['plans'].items():
    for kind in('signed_cores','signed_types'):
        for name,rl in (v.get(kind) or {}).items():
            for ref in rl:
                a=ref.split(' ')[0]; hh,_,p=a.partition(':')
                counted[(die,kind,name)].append((HM.get(hh,hh),N(HM.get(hh,hh),p)))
print('counted designs',len(counted),file=sys.stderr)
cited_counted=collections.defaultdict(set)
for k,rl in counted.items():
    for h,p in rl: cited_counted[(h,p)].add(k)
# signed-record rows that are counted: routed_db etc from the cache
srec={}
for r in cache['signed_records']:
    srec[(HM.get(r.get('scan_host'),r.get('scan_host')),N(HM.get(r.get('scan_host'),r.get('scan_host')),r['path']))]=r
PATHR=re.compile(r'^/(?:srv|home)/')
def strs(o):
    if isinstance(o,dict):
        for v in o.values(): yield from strs(v)
    elif isinstance(o,list):
        for v in o: yield from strs(v)
    elif isinstance(o,str) and PATHR.match(o): yield o
countedref=collections.defaultdict(set) # host -> file/dir paths kept for counted rows
for (h,p),ks in cited_counted.items():
    r=srec.get((h,p))
    if r:
        for s in strs(r): countedref[h].add(N(h,s))
    countedref[h].add(p)
    q=os.path.join(os.path.dirname(p),'PROVENANCE.json'); countedref[h].add(q)
COPY=re.compile(r'/(plandir|views|physical|rtl|rtl_bindov|bind[^/]*|src[^/]*|repo[^/]*|results|core_views|childviews?)/')
# ---- per host load
D={};C={};REC={};KEEPS={};GIT={}
for h in HOSTS:
    d={}
    for l in gzip.open(f'{SCAN}/{h}/dirs.jsonl.gz','rt'):
        r=json.loads(l); r['path']=N(h,r['path']); d[r['path']]=r
    D[h]=d
    ch=collections.defaultdict(list)
    for p in d: ch[os.path.dirname(p)].append(p)
    C[h]=ch
    REC[h]=[json.loads(l) for l in open(f'{SCAN}/{h}/rec.jsonl')]
    for r in REC[h]:
        r['path']=N(h,r['path']); r['kit']=N(h,r['kit']) if r['kit'] else ''
GITH=collections.defaultdict(dict)
for h in HOSTS:
    for l in open(f'{SCAN}/{h}/git.tsv'):
        c=l.rstrip('\n').split('\t'); GITH[h][N(h,c[0])]=c[1]
KEEPD=collections.defaultdict(set)
for h in HOSTS:
    for l in open(f'{SCAN}/{h}/keeps.tsv'):
        k,p=l.rstrip('\n').split('\t'); KEEPD[h].add(os.path.dirname(N(h,p)) if k=='KEEP' else N(h,p))
# real closures and record dirs
closed=collections.defaultdict(dict); recdirs=collections.defaultdict(set)
for h in HOSTS:
    for r in REC[h]:
        p=r['path']
        rel=p.split('/claude/',1)[-1]
        cop=bool(COPY.search('/'+rel)) or any(a in GITH[h] for a in ancs(p))
        r['copy']=cop
        if cop: continue
        if r['kit']:
            closed[h].setdefault(r['kit'],[]).append(p)
        else: recdirs[h].add(os.path.dirname(p))
# protected paths (P list): exact
def blockers_for(h):
    "target->list of reasons applying to host h"
    b=collections.defaultdict(list)
    for t,l in glob_t.items():
        for k,hh,s in l:
            if hh in('any',h) or (hh=='local' and h=='localhost'): b[t].append(k+':'+s[:60])
    for t,l in proc.items():
        for k,hh,src in l:
            if hh in('any',h): b[t].append('proc:'+k+'@'+src)
    for p in countedref[h]: b[p].append('counted')
    return b
def under(p,dead):  # any ancestor-or-self in dead
    if p in dead: return True
    return any(a in dead for a in ancs(p))
TOPDEPTH={}
def classify(h,dead_all):
    d=D[h]; ch=C[h]; b=blockers_for(h)
    for t in list(b):
        if t in d: continue
        for a in ancs(t):
            if a in d:
                if not GENERIC.match(os.path.basename(a)): b[a]+=b[t]
                break
    below=collections.defaultdict(list)   # dir -> reasons from targets at-or-below
    atabove=collections.defaultdict(list)
    for t,rs in b.items():
        below[t]+=rs
        for a in ancs(t):
            if a in d: below[a].append(rs[0])
    active=collections.Counter()
    for k,t,ch_,ci,mt in refs:
        if under(ci,dead_all[ch_]): continue
        # same-host for links/git/alternates, cross-host for text cites
        if k in('L','G','A') and ch_!=h: continue
        active[k]+=1
        b[t].append(f'ref{k}:{ch_}:{ci}')
        below[t].append(f'ref{k}:{ch_}:{ci}')
        for a in ancs(t):
            if a in d: below[a].append(f'ref{k}:{ch_}:{ci}')
    def tgt_above(p,top):
        for a in ancs(p):
            if len(a)<len(top): break
            if a in b and not GENERIC.match(os.path.basename(a)):
                r=b[a][0]
                return r,a
            if a==top: break
        return None
    plan=[]
    # queue relative cites
    relq=set()
    for t in qrel:
        relq.add(t)
    tops=[p for p,r in d.items() if r['depth']==0]
    def rel_of(p):
        return p.split('/claude/',1)[1] if '/claude/' in p else p.replace('/home/ubuntu/','')
    def isqrel(p):
        r=rel_of(p)
        if r in relq: return True
        for t in relq:
            if t.startswith(r+'/'): return True
        return False
    # (b2) a relative cite that overshoots the scan ("cache28GB", "foo/codex-x/y") protects the deepest scanned dir it names. A bare cite of a
    # whole wave root is not retention of every attempt under it: live attempts already stay through KEEP-LIVE-WAVE.
    rel_d={rel_of(p) for p in d}
    eff=set()
    for t in relq:
        c=t.split('/')
        for i,x in enumerate(c):
            if x.startswith('codex-') or (x=='wt' and i+1<len(c)): c=c[i:]; break
        q='/'.join(c)
        while q and q not in rel_d: q=q.rsplit('/',1)[0] if '/' in q else ''
        if q and not ('/' not in q and re.search(r'-wave-|^kit-wave',q)): eff.add(q)
    relq=eff
    relq_anc=set()
    for t in relq:
        c=t.split('/')
        for i in range(1,len(c)+1): relq_anc.add('/'.join(c[:i]))
    def rel_cited_above(p):
        r=rel_of(p)
        if r in relq: return True
        return any(a in relq for a in ancs('/'+r)) or any(a[1:] in relq for a in ancs('/'+r))
    def visit(p,top,topkeep):
        r=d[p]
        base=os.path.basename(p); depth=r['depth']
        if r.get('self_stub'): plan.append((p,'KEEP-STUB',r,'')); return
        if rel_cited_above(p) and p not in GITH[h]: plan.append((p,'KEEP-QUEUE',r,'relative cite at or above')); return
        if p in KEEPD[h] and depth>0: plan.append((p,'KEEP-MARKER',r,'.keep')); return
        if r.get('err'): plan.append((p,'KEEP-ERR',r,'unreadable')); return
        if depth==0 and TOPNAME.search(base.replace('codex-','').replace('wt-','').replace('scratch-','')) and not p in GITH[h]:
            plan.append((p,'KEEP-SOURCE',r,'tree name')); return
        if depth>0 and SRCNAME.match(base): plan.append((p,'KEEP-SOURCE',r,'dir name')); return
        # git checkout
        if p in GITH[h]:
            if r['locked']: plan.append((p,'KEEP-GITLOCKED',r,'')); return
            if now-r['newest']<SIX: plan.append((p,'KEEP-RECENT',r,'git %.1fh'%((now-r['newest'])/3600))); return
            if below.get(p): plan.append((p,'KEEP-REF',r,below[p][0])); return
            ab=tgt_above(p,top)
            if ab: plan.append((p,'KEEP-REF',r,ab[0])); return
            if rel_of(p) in relq_anc: plan.append((p,'KEEP-QUEUE',r,'relative cite')); return
            if under(p,set()) : pass
            plan.append((p,'GITRM',r,GITH[h][p])); return
        if p in closed[h]:
            if now-r['newest']<SIX: plan.append((p,'KEEP-RECENT',r,'closed kit')); return
            pb=[x for x in below.get(p,[]) if x.startswith(('proc:','A:'))]
            if pb: plan.append((p,'KEEP-REF',r,'closed kit '+pb[0])); return
            plan.append((p,'CLOSED',r,closed[h][p][0])); return
        if p in recdirs[h]: plan.append((p,'KEEP-RECORD',r,'signed record, no kit')); return
        if p in live_attempts: plan.append((p,'KEEP-LIVE-WAVE',r,'')); return
        # any reason at or below?
        why=None
        if now-r['newest']<SIX: why='recent %.1fh'%((now-r['newest'])/3600)
        elif below.get(p): why=below[p][0]
        elif r['keep']: why='keep below'
        elif r['stub']: why='stub below'
        elif r['git']: why='git below'
        elif r['locked']: why='locked'
        elif any(c for c in closed[h] if c.startswith(p+'/')): why='closed below'
        elif any(c.startswith(p+'/') for c in recdirs[h]): why='record below'
        elif any(a.startswith(p+'/') for a in live_attempts): why='live attempt below'
        elif any(a.startswith(p+'/') and trimhost.get(a)==h for a in open_attempts): why='open attempt below'
        elif rel_of(p) in relq_anc: why='queue relative'
        elif depth==0 and p in KEEPD[h]: why='top keep'
        if why is None:
            ab=tgt_above(p,top)
            if ab: plan.append((p,'KEEP-REF',r,ab[0])); return
            if p in open_attempts and trimhost.get(p)==h:
                plan.append((p,'TRIM',r,'%s %s %s %s'%(open_attempts[p][:3]+(trimkeep.get(p,('',))[0],)))); return
            plan.append((p,'DELETE',r,'')); return
        if p in open_attempts and why and not (why.startswith(('recent','proc','keep'))):
            plan.append((p,'KEEP-REF',r,why)); return
        kids=ch.get(p,[])
        if not kids:
            plan.append((p,'KEEP-LEAF',r,why)); return
        kb=0
        for k in kids:
            visit(k,top,topkeep); kb+=d[k]['bytes']
        rest=r['bytes']-kb
        if rest>=(1<<30): plan.append((p,'KEEP-RESID',dict(r,bytes=rest),why))
    for t in tops: visit(t,t,False)
    return plan
# fixpoint across hosts
dead={h:set() for h in HOSTS}
for it in range(5):
    allp={}
    grew=0
    for h in HOSTS:
        pl=classify(h,dead); allp[h]=pl
        nd=set(p for p,a,r,w in pl if a in('DELETE','GITRM'))
        if nd-dead[h]: grew+=len(nd-dead[h])
        dead[h]|=nd
    print('iter',it,'grew',grew,file=sys.stderr,flush=True)
    if not grew: break
# counted coverage: every counted design must keep >=1 ref outside the delete units
removed=collections.Counter(); blockers=collections.defaultdict(set)
for k,rl in counted.items():
    surv=[(h,p) for h,p in rl if h not in dead or h=='origin/main' or not under(p,dead[h])]
    if not surv:
        removed[k]+=1
        for h,p in rl:
            if h in dead:
                for a in ancs(p):
                    if a in dead[h]: blockers[h].add(a)
print('counted designs with no surviving ref if plan applied:',len(removed),list(removed)[:10],file=sys.stderr)
os.makedirs(ROOT+'/plan',exist_ok=True)
for h in HOSTS:
    b=blockers_for(h); tg=set(t for t in b if not any(x.startswith('proc:') for x in b[t]))
    for k,t,ch_,ci,mt in refs:
        if under(ci,dead[ch_]): continue
        if k in('L','G','A') and ch_!=h: continue
        tg.add(t)
    open(f'{ROOT}/plan/prot_{h}.txt','w').write('\n'.join(sorted(tg))+'\n')
json.dump(dict(trimkeep=trimkeep,open={k:v for k,v in open_attempts.items()},trimhost=trimhost),open(ROOT+'/plan/trim.json','w'))
for h in HOSTS:
    with open(f'{ROOT}/plan/{h}.tsv','w') as f:
        for p,a,r,w in sorted(allp[h]):
            if a in('DELETE','GITRM') and p in blockers[h]: a='KEEP-COUNTED-SOLE'
            f.write('%s\t%s\t%d\t%d\t%d\t%s\t%s\n'%(p,a,r['bytes'],r['files'],r['newest'],time.strftime('%m-%d %H:%M',time.localtime(r['newest'])),(w or '').replace('\t',' ')[:300]))
    c=collections.Counter(); n=collections.Counter()
    for p,a,r,w in allp[h]:
        c[a]+=r['bytes']; n[a]+=1
    print(h,' '.join(f'{a}={c[a]/1e9:.0f}G/{n[a]}' for a in sorted(c,key=lambda x:-c[x])))
