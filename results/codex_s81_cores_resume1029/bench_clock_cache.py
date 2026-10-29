#!/usr/bin/env python3
"""Actual H0 sizing-kernel comparison, no change to any progressing job."""
import importlib.util,json,sys,time
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r/'src/results/core_lat_r8_1026'));sys.path.insert(0,str(r/'src/tools/die_plan'))
import l0r_r8_uf3 as A
from clock_model_cache import geometry_cache
U,V=A.U,A.V3
x=json.load(open(r/'h0_family/dsdv_eng_rr_h0/plan_d1.json'))[0];fit=json.load(open(r/'src/results/model_refit3_1026/uf_phys3_v1.json'))
for c in sorted({n[3]for n in x['nodes_xy']}):
 if c not in U.SIZES:U.SIZES.append(c)
p=A.PlanFromRecord(x,str(r/'h0_family/dsdv_eng_rr_h0/geo.txt'));libs=U.load_libs(str(r/'lib'))
node=next(n for n in p.nodes if p.nodes[n]['kind']=='leaf');old=p.nodes[node]['cell']
candidates=[old,'BUFx8_ASAP7_75t_R','BUFx12f_ASAP7_75t_R','BUFx24_ASAP7_75t_R']
def evaluate():
 return V.basis_leaf(p,libs,'TT','max',fit['PMAX']),V.basis_leaf(p,libs,'FF','min',fit['PMIN'])
t0=time.perf_counter();ref=[]
for c in candidates:p.nodes[node]['cell']=c;ref.append(evaluate())
t1=time.perf_counter()
with geometry_cache(U)as stats:
 got=[]
 for c in candidates:p.nodes[node]['cell']=c;got.append(evaluate())
 t2=time.perf_counter();assert got==ref
 # A changed sink point must invalidate its leaf geometry, not reuse stale Elmore.
 point=p.nodes[node]['sinks'][0];p.nodes[node]['sinks'][0]=(point[0]+1.08,point[1]);changed=evaluate();assert changed!=got[-1]
 stats={k:v()._asdict()for k,v in stats.items()}
p.nodes[node]['cell']=candidates[-1];uncached_changed=evaluate();assert changed==uncached_changed
p.nodes[node]['sinks'][0]=point;p.nodes[node]['cell']=old
out=dict(scope='Actual H0 pre-build kernel only; existing sizing job untouched',leaf=node,candidates=candidates,leaf_results_per_candidate=len(ref[0][0]),exact_full_dict_equality=True,geometry_mutant_changed_and_exact=True,uncached_seconds=t1-t0,cached_seconds=t2-t1,speedup=(t1-t0)/(t2-t1),cache_stats=stats)
json.dump(out,open(r/'clock_cache_bench.json','w'),indent=1);print(json.dumps(out,indent=1))
