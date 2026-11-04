#!/usr/bin/env python3
# PRUNE-1104N COORD 11:05 (3) classifier, read-only, on localhost. usage: wtclass.py host wt.tsv iwalk.tsv links.tsv out.tsv
import os,re,sys,json,time,glob,subprocess as sp,collections
h,wt,iw,lk,out=sys.argv[1:6]; now=time.time(); A='/tmp/p1104n_ap/'; R='/srv/opentallas-scratch2/claude/wt/'
NEVER=re.compile(r'^(kw-fix-3|kit-wave-15|tok-|kv-fn-|codex-ds-|veh|vehicle|ss27|ss28|die-s81-51|die-s81-52|dh59|dh60|kit_turn_b)|svc|tok',re.I)
uq={};
for l in open(iw):
    d,p,du,u,nw=l.rstrip('\n').split('\t')
    if d=='2' and p.startswith('wt/'): uq[p[3:]]=(float(u),float(du))
links=collections.Counter()
for l in open(lk,errors='replace'):
    s,_,t=l.rstrip('\n').partition('\t')
    m=re.search(r'/wt/([^/]+)',t)
    if m and not re.search(r'/wt/'+re.escape(m.group(1))+r'(/|$)',s): links[m.group(1)]+=1
cache=open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json'),errors='replace').read()
cfg=open(A+'kit_wave.json',errors='replace').read(); st=json.load(open(A+'kit_wave_state.json')); stj=json.dumps(st.get('protect_written',{}))
LIVE={'RUNNING','WAITING','LAUNCHING','ENQUEUED'}
live=' '.join(json.dumps(v) for v in st['items'].values() if v.get('status') in LIVE and not(v.get('status')=='ENQUEUED' and v.get('q_status')=='FAIL'))
jobs=' '.join(json.dumps(j) for j in json.load(open(A+'state.json'))['jobs'].values() if j.get('status') in('RUNNING','WAITING','QUEUED','ENQUEUED','LAUNCHING','PENDING','HELD'))
prot=''
for pf in('~/coord/PROTECTED-DBS.txt','~/coord/lanes/PROTECTED-DBS.txt'): prot+=open(os.path.expanduser(pf),errors='replace').read()
# lane branch: named in the queue or a lane file changed in the last 72 h, on a line that is not a prune line
txt=[]
for f in glob.glob(os.path.expanduser('~/coord/lanes/*')):
    if os.path.isfile(f) and not re.search('PRUNE-',os.path.basename(f)) and os.path.getsize(f)<50e6 and now-os.path.getmtime(f)<72*3600 and not f.endswith('COORD-REVIEW-QUEUE.md'):
        txt.append(open(f,errors='replace').read())
q=open(os.path.expanduser('~/coord/lanes/COORD-REVIEW-QUEUE.md'),errors='replace').read().split('\n')
cut=time.strftime('%Y-%m-%d',time.localtime(now-72*3600)); k=next((i for i,l in enumerate(q) if l.startswith('- '+cut)),0)
txt.append('\n'.join(l for l in q[k:] if 'PRUNE-' not in l)); txt='\n'.join(txt)
rows=[]; shas=set()
for l in open(wt):
    n,head,br,ok,nst,nw,own,sig,usig=l.rstrip('\n').split('\t'); rows.append((n,head,br,ok,int(nst),int(nw),int(own),int(sig),int(usig))); shas.add(head)
shas.discard('')
# the hub alias resolves from the fleet hosts, not from here
scr="cd OpenTallas\nfor s in "+' '.join(sorted(shas))+"; do echo $s $(git for-each-ref --contains $s --count=1 --format='%(refname:short)' 2>/dev/null); done\n"
hub=sp.run(['ssh','-o','ControlPath=none','intel2','ssh -o ConnectTimeout=20 hub bash -s'],input=scr,capture_output=True,text=True).stdout
if not hub.strip(): sys.exit('hub answered nothing')
ref={x.split()[0]:(x.split()+[''])[1] for x in hub.splitlines() if x.split()}
res=[];C=collections.Counter();G=collections.Counter()
for n,head,br,ok,nst,nw,own,sig,usig in rows:
    w=R+n; u,du=uq.get(n,(0,0)); why=None; tp=f'wt/{n}'
    bq=re.compile(r'(?<![\w/.-])'+re.escape(br)+r'(?![\w-])') if br and br not in('main','master') else None
    if NEVER.search(n): why='never-name'
    elif ok!='ok': why='no-git'
    elif now-nw<24*3600: why='idle<24h'
    elif nst: why='not-clean'
    elif usig: why='untracked-signed'
    elif own: why='not-mine'
    elif not ref.get(head): why='not-on-hub'
    elif links[n]: why='inbound-symlink'
    elif w in prot or tp+'/' in prot: why='protected'
    elif w+'/' in cache or w+'"' in cache: why='counter-cache'
    elif tp+'/' in cfg or w in cfg or w in stj: why='config'
    elif tp+'/' in live or w in live or w in jobs: why='live-row'
    elif bq and bq.search(txt): why='branch-in-lane-text-72h'
    elif re.search(r'(?<![\w-])'+re.escape(tp)+r'(?![\w-])',txt): why='path-in-lane-text-72h'
    C[why or 'PASS']+=1; G[why or 'PASS']+=u
    res.append((u,du,why or 'PASS',n,head,br,ref.get(head,''),time.strftime('%m-%d %H:%M',time.localtime(nw)),nst,sig,usig,links[n],own))
res.sort(reverse=True)
with open(out,'w') as o:
    o.write('GB_inode\tGB_du\tverdict\tname\thead\tbranch\thub_ref\tnewest\tstatus\tsigned\tuntracked_signed\tlinks_in\tnot_mine\n')
    for r in res: o.write('\t'.join(str(x) for x in r)+'\n')
print(h,{k:(C[k],round(G[k],1)) for k,_ in G.most_common()})
