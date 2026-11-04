#!/usr/bin/env python3
# PRUNE-1104M read-only: which strong-corpus files cite non-latest idle attempts of a host walk, and how many GB. usage: attstrong.py host
import re,sys,os,glob,time,collections
h=sys.argv[1]; H=os.path.expanduser('~'); now=time.time()
rows={}; newest=collections.defaultdict(int); ATT=re.compile(r'^(.*/items/[^/]+)/attempt_(\d+)$')
for l in open(f'/tmp/p1104m_walk_{h}.tsv'):
    d,p,kb,nw,sig,keep,fl,git=l.rstrip('\n').split('\t'); m=ATT.match(p)
    if m: newest[m.group(1)]=max(newest[m.group(1)],int(m.group(2))); rows[p]=(int(kb),int(nw),int(sig),int(keep),m)
elig={}
for p,(kb,nw,sig,keep,m) in rows.items():
    if int(m.group(2))<newest[m.group(1)] and not sig and not keep and now-nw>6*3600:
        elig[p.split('/claude/',1)[1]]=kb
strong=[H+'/.local/state/fleet-viz/release_tree_plan_cache.json',H+'/coord/PROTECTED-DBS.txt']+glob.glob(H+'/.local/state/fleet-viz/*.json')
strong+=[f for f in glob.glob(H+'/coord/autopilot/*') if os.path.isfile(f) and not f.endswith(('log.txt','.lock'))]+glob.glob(H+'/.local/state/ot-run/spill_pending/*')
T=re.compile(r'[\w.+=@/-]*/items/[\w.+=@-]+/attempt_\d+')
hit=collections.defaultdict(set)
for f in set(strong):
    try: s=open(f,errors='replace').read()
    except OSError: continue
    for t in set(T.findall(s)):
        for k in ([t.split('/claude/',1)[1]] if '/claude/' in t else []):
            if k in elig: hit[f].add(k)
tot=set().union(*hit.values()) if hit else set()
print(h,'idle non-latest unsigned attempts',len(elig),'GB %.1f'%(sum(elig.values())/1e6),'cited',len(tot),'GB %.1f'%(sum(elig[k] for k in tot)/1e6))
for f,s in sorted(hit.items(),key=lambda x:-len(x[1])): print(' ',len(s),'GB %.1f'%(sum(elig[k] for k in s)/1e6),f.replace(H,'~'))
top=collections.Counter()
for k in tot: top['/'.join(k.split('/')[:5])]+=elig[k]
for k,v in top.most_common(10): print('   ',round(v/1e6,1),k)
