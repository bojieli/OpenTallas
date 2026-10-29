import json,collections as C,sys
d=json.load(open(sys.argv[1]));F=d['failures']
rank={'too_close':0,'local_uncovered':1,'local_hit':2,'riser_m8':3}
first=C.Counter();deep=C.Counter();firstsrc=C.Counter();deepdet=C.Counter();ncols=C.Counter();pins=C.Counter();cells=set()
for f in F:
    pins[f['pin']]+=1;cells.add(f['cell'])
    dg=[x for x in f['diag'] if x['stage']!='too_close']
    ncols[len(dg)]+=1
    if not dg: first['no_column']+=1;deep['no_column']+=1;continue
    a=dg[0];k=a['stage']+(':'+a['src']+'/'+a['layer']+'/part'+str(a['part']) if a['stage']=='local_hit' else (':part'+str(a['part']) if a['stage']=='local_uncovered' else ''))
    first[k]+=1
    b=max(dg,key=lambda x:rank[x['stage']]);deep[b['stage']]+=1
    if b['stage']=='riser_m8':
        agg=C.Counter()
        for x in dg:
            if x['stage']=='riser_m8':agg.update(x['counts'])
        deepdet[max(agg,key=agg.get) if agg else 'no_ys']+=1
    elif b['stage']=='local_hit':
        deepdet['local_hit:'+b['src']]+=1
    else: deepdet[b['stage']]+=1
out=dict(n_fail=len(F),n_pass=len(d['records']),cells=len(cells),pins=dict(pins),candidate_columns=dict(sorted(ncols.items())),
 first_obstacle_nearest_column=dict(first.most_common()),deepest_stage=dict(deep.most_common()),deepest_dominant_obstacle=dict(deepdet.most_common()))
print(json.dumps(out,indent=1))
