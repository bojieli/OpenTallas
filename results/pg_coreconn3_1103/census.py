import sys,json,collections,time
sys.path.insert(0,"tools/die_plan")
import schema, gen_phys
t0=time.time()
P=schema.Plan(json.load(open("physical/die_plan/s81/plan_h2_2249.json")))
skip=0;pub=collections.Counter();ptypes=set();bad=[];err=[];ntypes=0
for tn in P.types:
    mac=gen_phys.type_macros(P,tn)
    if not mac or not gen_phys.core_pg_on(P,tn): continue
    ntypes+=1
    try:
        exc={i for d in gen_phys.phy_pg_domains(P,tn) for i in d[4]}
        g=gen_phys.core_pg_grids(P,tn,mac,exclude=exc)
        skip+=sum("skipped" in l for l in g)
        pb=gen_phys.core_pg_published(P,tn,mac,exclude=exc)
        for i in pb: pub[[m[1] for m in mac if m[0]==i][0]]+=1; ptypes.add(tn)
        u=gen_phys.core_pg_unconnected(gen_phys.PDN+"\n".join(g),mac,exclude=exc,strict=gen_phys._core_pg_strict(P,tn),published=set(pb))
        if u: bad.append((tn,u[:2]))
    except Exception as e: err.append((tn,str(e)[:200]))
print(json.dumps(dict(plan="physical/die_plan/s81/plan_h2_2249.json",macro_types_core_pg_on=ntypes,skipped_uses=skip,
     published_uses=sum(pub.values()),published_types=len(ptypes),published_by_view=dict(pub),unconnected=bad,errors=err,
     seconds=round(time.time()-t0,1)),indent=1))
