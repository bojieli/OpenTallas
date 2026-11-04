#!/usr/bin/env python3
# PRUNE-1104N COORD 10:49 (1) classifier, read-only. usage: ltclass.py host lt.tsv out.tsv; needs /tmp/p1104n_ap/ (fresh copies from the autopilot hub) and /tmp/p1104n_apcite.txt (file:match, spec and job dirs).
import json,re,os,sys,time,collections,glob,calendar
h,lt,out=sys.argv[1:4]; A='/tmp/p1104n_ap/'; now=time.time(); ROOT='/srv/opentallas-scratch2/'
PAT=re.compile(r'(?:([\w-]+):)?(/srv/opentallas-scratch2?/[^\s\'"|,;]*?/items/[^/\s\'"|,;]+/(?:attempt_\d+|gen|[\w.-]+))(?=[/\s\'"|,;]|$)')
def norm(p): return p.replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/')
rows=[]
for l in open(lt):
    k,p,u,d,nw,s,kp=l.rstrip('\n').split('\t'); rows.append(dict(kind=k,p=p,u=int(u),d=int(d),nw=int(nw),sig=int(s),keep=int(kp)))
R={r['p']:r for r in rows}
# which scanned dir does a text path fall in
def cover(path):
    m=re.search(r'^(.*/items/[^/]+/[^/]+)',path); return m.group(1) if m else None
st=json.load(open(A+'kit_wave_state.json'))['items']
LIVE={'RUNNING','WAITING','LAUNCHING','ENQUEUED'}
def row_live(v): return v.get('status') in LIVE and not (v.get('status')=='ENQUEUED' and v.get('q_status')=='FAIL')
cit=collections.defaultdict(list); byitem=collections.defaultdict(list)
for key,v in st.items():
    byitem[(v.get('die'),v.get('item'))].append(v)
    s=json.dumps(v)
    for m in PAT.finditer(s):
        if m.group(1) and m.group(1)!=h: continue
        c=cover(norm(m.group(2)))
        if c in R: cit[c].append(('state',v.get('status'),v.get('q_status'),row_live(v),key))
stage=collections.defaultdict(list); stitem=collections.defaultdict(list)
L=list(open(A+'kit_wave_stages.tsv',errors='replace')); H=L[0].rstrip('\n').split('\t')
for l in L[1:]:
    f=dict(zip(H,l.rstrip('\n').split('\t')))
    stitem[(f.get('die'),f.get('item'))].append(f)
    for m in PAT.finditer(l):
        if m.group(1) and m.group(1)!=h: continue
        c=cover(norm(m.group(2)))
        if c in R: stage[c].append(f)
jobs=collections.defaultdict(list); RUNJ={'RUNNING','WAITING','QUEUED','ENQUEUED','LAUNCHING','PENDING','HELD'}
J=json.load(open(A+'state.json'))['jobs']
for jid,j in J.items():
    s=json.dumps(j); jh=j.get('ran_on') or j.get('host')
    for m in PAT.finditer(s):
        ch=m.group(1) or jh
        if ch!=h and ch is not None: continue
        c=cover(norm(m.group(2)))
        if c in R: jobs[c].append((jid,j.get('status')))
# spec and job-dir files naming the dir
speclive=collections.defaultdict(list)
dir2=collections.defaultdict(list)
for key,v in st.items(): dir2[os.path.basename(os.path.dirname(v.get('dir','')))].append(v)
for l in open('/tmp/p1104n_apcite.txt',errors='replace'):
    f,_,mt=l.rstrip('\n').partition('\t')
    m=PAT.search(mt)
    if not m or (m.group(1) and m.group(1)!=h): continue
    c=cover(norm(m.group(2)))
    if c not in R: continue
    x=re.search(r'/autopilot/(kit_wave|jobs)/([^/]+)',f)
    if not x: speclive[c].append('other:'+f); continue
    if x.group(1)=='jobs':
        jst=J.get(x.group(2),{}).get('status')
        if jst is None or jst in RUNJ: speclive[c].append(f'job:{x.group(2)}:{jst}')
    else:
        vs=dir2.get(x.group(2),[])
        if not vs or any(row_live(v) for v in vs): speclive[c].append(f"spec:{x.group(2)}:{'live' if vs else 'norow'}")
strong=open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json'),errors='replace').read()
cfg=open(A+'kit_wave.json',errors='replace').read()
lane=collections.defaultdict(list); pats={}
for r in rows:
    q=re.search(r'[^/]+/items/[^/]+/[^/]+$',r['p']).group(); pats[q]=r['p']
OWN=re.compile(r'resume|\beco\b|stage.resum|\bkeep\b|do not (delete|prune|touch)|re-?sign|near.miss',re.I); ltext=collections.defaultdict(list)
TOK=re.compile(r'[\w.+-]+/items/[\w.+=-]+/[\w.+=-]+')
for f in glob.glob(os.path.expanduser('~/coord/lanes/*'))+glob.glob(os.path.expanduser('~/coord/*.md')):
    if not os.path.isfile(f) or re.search('PRUNE-',os.path.basename(f)) or os.path.getsize(f)>50e6: continue
    for ln in open(f,errors='replace'):
        if f.endswith('COORD-REVIEW-QUEUE.md') and re.search(r'KIT-WAVE \[|\bLAUNCH\b',ln): continue
        if '/items/' not in ln: continue
        for t in TOK.findall(ln):
            if t in pats:
                k=lane if OWN.search(ln) else ltext   # the ruling excludes rows an owner NAMED for stage resume or ECO; a bare mention is a text mention, disclosed in the manifest
                k[pats[t]].append((os.path.basename(f),ln[:180].strip()))
prot=[]
for pf in ('~/coord/PROTECTED-DBS.txt','~/coord/lanes/PROTECTED-DBS.txt'):
    for ln in open(os.path.expanduser(pf),errors='replace'):
        prot+=[norm(w).rstrip('/') for w in re.findall(r'/srv/opentallas-scratch2?/[^\s,;]+',ln)]
NT=re.compile(r'/(ss27|ss28|die-s81-51|die-s81-52|dh59|dh60|kit_turn_b|tok-[^/]*|kv-fn-[^/]*|codex-ds-[^/]*|veh[^/]*|vehicle[^/]*)(/|$)|/die-hbm-63/eco(/|$)')
def ts(s):
    try: return calendar.timegm(time.strptime(s[:16],'%Y-%m-%d %H:%M'))
    except Exception: return 0
res=[];C=collections.Counter();G=collections.Counter()
for r in rows:
    p=r['p']; m=re.search(r'/kit-wave/([^/]+)/([^/]+)/items/([^/]+)/([^/]+)$',p) or re.search(r'/()([^/]+)/items/([^/]+)/([^/]+)$',p)
    die,ev,item,sub=m.groups(); why=None
    sr=stage.get(p,[]); sv=cit.get(p,[]); jr=jobs.get(p,[])
    evrows=[f for f in stitem.get((die,item),[]) if f.get('event')==ev]
    pcno=any(f.get('plan_current')=='no' for f in sr+evrows)
    failed=any(f.get('status')=='FAIL' or (f.get('status')=='SUPERSEDED' and 'was FAIL' in f.get('reason','')) for f in sr) or any(x[1]=='FAIL' or x[2]=='FAIL' for x in sv)
    jterm=any(s in('DONE-CRASH','DONE-STRUCTURAL','DONE-TIMEOUT','DONE-FAIL','FAIL','NEAR-MISS','CANCELLED','WITHDRAWN') for _,s in jr)
    newer=[f for f in stitem.get((die,item),[]) if (f.get('event')!=ev) and ts(f.get('updated',''))>r['nw']+60 and not any(f is g for g in sr)]
    if r['sig']: why='signed'
    elif r['keep']: why='keep-inside'
    elif NT.search(p) or any(q==p or q.startswith(p+'/') or p.startswith(q+'/') for q in prot): why='no-touch-or-protected'
    elif (now-r['nw'])<6*3600: why='recent'
    elif any(x[3] for x in sv) : why='live-row'
    elif any(s in RUNJ for _,s in jr): why='live-job'
    elif p in speclive: why='live-spec'
    elif p in strong: why='counter-cache'
    elif p in cfg: why='kit_wave.json'
    elif p in lane: why='lane-text'
    elif not (failed or jterm): why='not-terminal-failed' if (sr or sv or jr) else 'no-record'
    elif not (pcno or newer): why='no-relaunch-and-plan-current'
    C[why or 'ELIGIBLE']+=1; G[why or 'ELIGIBLE']+=r['u']
    res.append((why or 'ELIGIBLE',r,die,ev,item,sr,sv,jr,pcno,newer))
res.sort(key=lambda x:-x[1]['u'])
with open(out,'w') as o:
    o.write('host_path\tGB_inode\tGB_du\tnewest\tverdict\tkind\tdie\tevent\titem\tstage_status\tplan_current_no\tnewer_row\tjob\tlane_or_spec\n')
    for w,r,die,ev,item,sr,sv,jr,pcno,newer in res:
        ss=';'.join(sorted({f.get('status','')+'/'+f.get('class','') for f in sr}))[:60]
        n=(newer[0].get('event','')+'@'+newer[0].get('updated','')) if newer else ''
        o.write(f"{h}:{r['p']}\t{r['u']/1e9:.2f}\t{r['d']/1e9:.2f}\t{time.strftime('%m-%d %H:%M',time.localtime(r['nw']))}\t{w}\t{r['kind']}\t{die}\t{ev}\t{item}\t{ss}\t{pcno}\t{n}\t{';'.join(s for _,s in jr)[:50]}\t{(lane.get(r['p']) or speclive.get(r['p']) or ltext.get(r['p']) or [''])[0]}\n")
print(h,{k:(C[k],round(G[k]/1e9,1)) for k in G})
