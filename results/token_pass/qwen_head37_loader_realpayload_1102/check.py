#!/usr/bin/env python3
"""Check logged stage37 writes against the actual source event, independent of the loader RTL.
Expected per (slice,user): PROG kind3 at addr+64u, CROM kind1 at addr+128u (user_relocation: pidx +128, CROM +2048 elements),
shared BTAB kind2 at addr (no user offset). Payload = payload_hex exactly."""
import json,sys,re,collections
log,src,rel,out=sys.argv[1:5]
d=json.load(open(src));R=json.load(open(rel))
assert [u['pidx'] for u in R['allocation']['users']]==[16,144,272,400]
assert [u['crom_first'] for u in R['allocation']['users']]==[1088,3136,5184,7232]
exp=collections.defaultdict(list)
for sl in d['slices']:
    s=sl['slice']
    for u in range(4):
        for r in sl['prog_users'][u]:exp[(s,u)].append((3,r['addr']+64*u,int(r['payload_hex'],16)))
        for r in sl['crom']:exp[(s,u)].append((1,r['addr']+128*u,int(r['payload_hex'],16)))
        for r in sl['btab']:exp[(s,u)].append((2,r['addr'],int(r['payload_hex'],16)))
got=collections.defaultdict(list);dates=collections.defaultdict(list);cases={}
for line in open(log):
    m=re.match(r'W37 (\d+) (\d+) (\d+) (\d+) (\d+) ([0-9a-f]+)',line)
    if m:
        s,u,t,k,a=map(int,m.groups()[:5]);got[(s,u)].append((k,a,int(m.group(6),16)));dates[(s,u)].append(t)
    m=re.match(r'CASE stage(\d+) user(\d+) slice(\d+) writes(\d+) first(-?\d+) last(-?\d+) done(-?\d+)',line)
    if m:cases[tuple(map(int,m.groups()[:3]))]=tuple(map(int,m.groups()[3:]))
bad=[];summary={}
for key in sorted(exp):
    e=exp[key];g=got.get(key,[])
    if sorted(e)!=sorted(g):
        missing=len(set(e)-set(g));extra=len(set(g)-set(e))
        bad.append(dict(slice=key[0],user=key[1],expected=len(e),got=len(g),missing=missing,extra=extra))
    # first gain CROM write and last write dates (edges after start), and per-kind spans
    kinds=collections.defaultdict(list)
    for (k,a,_),t in zip(g,dates.get(key,[])):kinds[k].append(t)
    summary[f's{key[0]}u{key[1]}']=dict(writes=len(g),first=cases.get((37,key[1],key[0]),(0,-1))[1],last=cases.get((37,key[1],key[0]),(0,0,-1))[2],
        done=cases.get((37,key[1],key[0]),(0,0,0,-1))[3],prog=[min(kinds[3]),max(kinds[3])] if kinds[3] else None,
        crom=[min(kinds[1]),max(kinds[1])] if kinds[1] else None,btab=[min(kinds[2]),max(kinds[2])] if kinds[2] else None)
pre=[(k,v) for k,v in cases.items() if k[0]!=37]
res=dict(status='PASS' if not bad and len(exp)==48 else 'FAIL',mismatches=bad,cases=len(cases),
    prefix_cases=sorted(set((v[0],v[1],v[2],v[3]) for k,v in pre)),stage37=summary,
    stage37_date_set=sorted(set((v['writes'],v['first'],v['last'],v['done']) for v in summary.values())))
json.dump(res,open(out,'w'),indent=1);print(res['status'],len(bad),res['stage37_date_set'],res['prefix_cases'])
sys.exit(0 if res['status']=='PASS' else 1)
