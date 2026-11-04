#!/usr/bin/env python3
# PRUNE-1103K check (c): parse release_tree_plan_cache.json. A ref/record is inside a listed worktree only with its own host.
import json,os,re,collections,sys
c=json.load(open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json')))
L={'epyc2':sys.argv[1:]}
ALL={n for v in L.values() for n in v}
ROOTS=('/home/ubuntu/scratch-root/claude/','/srv/opentallas-scratch3/claude/','/srv/opentallas-scratch2/claude/','/srv/opentallas-scratch/claude/')
def nm(path):
    for r in ROOTS:
        if (path or '').startswith(r):
            rel=path[len(r):]
            for n in ALL:
                if rel==n or rel.startswith(n+'/'): return n
    return None
def wt_of(host,path): return nm(path) if host=='epyc2' else None
def anyname(path): return nm(path)
def rp(ref):
    h,_,rest=ref.partition(':'); return h,rest.split(' ')[0]
res={n:dict(counted=collections.defaultdict(list),unique=[],refs=0) for n in ALL}
for pk,p in c['plans'].items():
    for dn in ('signed_types','signed_cores','signed_designs'):
        for key,refs in (p.get(dn) or {}).items():
            rr=[rp(r) for r in refs]
            ins=[(h,q,wt_of(h,q)) for h,q in rr]
            # strict alternative: a path whose worktree NAME is not on the list on any host
            out=[(h,q) for h,q in rr if not anyname(q)]
            main=[x for x in out if x[0]=='origin/main']
            for h,q,w in ins:
                if w:
                    res[w]['refs']+=1
                    res[w]['counted'][(p['die'],dn,key)].append(q)
                    if not out: res[w]['unique'].append((p['die'],dn,key,q,len(rr)))
# per key: alternative census
print('== credited keys: alternatives outside any listed-name path')
rows=[]
for pk,p in c['plans'].items():
    for dn in ('signed_types','signed_cores','signed_designs'):
        for key,refs in (p.get(dn) or {}).items():
            rr=[rp(r) for r in refs]; out=[x for x in rr if not anyname(x[1])]
            wt=[x for x in rr if not anyname(x[1]) and '/wt/' in x[1]]
            mainc=sum(1 for x in out if x[0]=='origin/main')
            nw=sum(1 for x in out if '/wt/' not in x[1] and x[0]!='origin/main')
            touched=any(wt_of(*x) for x in rr)
            if touched: rows.append((p['die'],dn,key,len(rr),len(out),mainc,nw))
print('touched keys',len(rows),'min outside-alternatives',min((r[4] for r in rows),default=None))
for r in sorted(rows,key=lambda r:r[4])[:15]: print(' ',r)
print('keys with no origin/main and no non-wt alt:',[r[:3] for r in rows if r[5]==0 and r[6]==0][:30])
print('== per worktree')
for n in sorted(ALL):
    r=res[n]; print(n,'counted refs',r['refs'],'keys',len(r['counted']),'UNIQUE',len(r['unique']))
    for u in r['unique'][:30]: print('   UNIQUE',u)
# all signed_records inside: every record has same top elsewhere?
sr=c['signed_records']
tops=collections.defaultdict(set)
for x in sr:
    if not anyname(x['path']): tops[x['top']].add((x['scan_host'],x['path']))
print('== signed_records inside, top without any record outside listed names')
creditkeys=set()
for p in c['plans'].values():
    for dn in ('signed_types','signed_cores','signed_designs'): creditkeys|=set((p.get(dn) or {}).keys())
for n in sorted(ALL):
    ins=[x for x in sr if wt_of(x['scan_host'],x['path'])==n]
    un=[x for x in ins if not tops.get(x['top'])]
    print(n,'records',len(ins),'no-outside-top',len(un),[x['top'] for x in un][:12])
print('== records OUTSIDE whose pins_path/prov_file/routed_db point inside a listed worktree (same host)')
agg=collections.Counter(); ex={}
for x in sr:
    if wt_of(x['scan_host'],x['path']): continue
    for f in ('pins_path','prov_file','routed_db','signed_lef'):
        v=x.get(f)
        if isinstance(v,str):
            w=wt_of(x['scan_host'],v)
            if w: agg[(w,f,x['top'])]+=1; ex[(w,f,x['top'])]=(x['scan_host'],x['path'],v)
print(len(agg))
for k,v in list(agg.items())[:40]: print(' ',k,v,ex[k])
print('== records INSIDE w/ extra pointers: count of resign/prov')
for n in sorted(ALL):
    ins=[x for x in sr if wt_of(x['scan_host'],x['path'])==n]
    print(n,collections.Counter('resign' if x.get('resign') else ('versioned' if x.get('versioned') else ('legacy' if x.get('legacy') else 'plain')) for x in ins), 'pins outside tree', sum(1 for x in ins if not wt_of(x['scan_host'],x['pins_path'])))
