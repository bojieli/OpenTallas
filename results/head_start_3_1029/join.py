import json,collections,sys
T=833.333
ca=json.load(open(sys.argv[1])); plan=json.load(open(sys.argv[2])); st=json.load(open(sys.argv[3]))
S={s['id']:s for s in st['stages']}
P={g['region']:g for g in plan['regions']}
X=[r for r in ca['rows'] if r['cross']]
c=collections.Counter(); ex=[]
for r in X:
    s=S.get(r['cap']); g=P.get(s['region']) if s else None
    sf=(g or {}).get('start_from') or {}
    plan_edge=sf.get('edge'); built='fall' if s and s['edge_fall'] else 'rise'
    fail=r['asbuilt']<0
    c[(fail, plan_edge==built, s['clock_from'] if s else None, r['k']%2)]+=1
    if fail and len(ex)<4: ex.append(dict(cap=r['cap'],launch=r['launch_setup'],s=r['s'],h=r['h'],k=r['k'],plan_edge=plan_edge,built=built,clock_from=s['clock_from'],launch_clock_from=S.get(r['launch_setup'],{}).get('clock_from'),interval=sf.get('sample_interval_ps'),sync=sf.get('sync_dist_ps'),off=sf.get('offset_from_parent'),parent=sf.get('parent'),launch_region=S.get(r['launch_setup'],{}).get('region')==sf.get('parent')))
for k,v in sorted(c.items(),key=str): print('fail=%s plan==built=%s cap_clock_from=%s halfstep_odd=%s : %d'%(*k,v))
for e in ex: print(json.dumps(e,ensure_ascii=True))
# launch clock_from vs capture clock_from among fails
d=collections.Counter((r['asbuilt']<0, S[r['cap']]['clock_from'], S.get(r['launch_setup'],{}).get('clock_from')) for r in X if r['cap'] in S)
print(d)
e=collections.Counter(); ks=collections.Counter()
for r in X:
    s=S.get(r['cap']); g=P[s['region']]; sf=g['start_from']; par=P.get(sf['parent'],{}).get('start_from') or {}
    pe=par.get('edge','root'); ls=S.get(r['launch_setup'])
    lb='fall' if ls and ls['edge_fall'] else 'rise'
    e[(r['asbuilt']<0, pe, lb, sf['edge'])]+=1
print('fail, plan parent edge, built launch edge, capture edge'); [print(k,v) for k,v in sorted(e.items(),key=str)]
