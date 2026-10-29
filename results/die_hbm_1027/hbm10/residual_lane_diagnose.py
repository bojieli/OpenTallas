"""Read-only missing-lane capacity upper bound from existing bound output; no new routes or latency adoption.
usage: residual_lane_diagnose.py PLAN_DIR LATENCY.json SOURCE_MANIFEST.json OUT.json
"""
import collections,json,sys
from pathlib import Path
D,F,A,O=map(Path,sys.argv[1:5]);P=json.load(open(D/'die_plan.json'));L=json.load(open(F))['buses'];A=json.load(open(A))
ports={q['id']:q for q in P['ports']};used=collections.Counter();missing=collections.defaultdict(collections.Counter)
for l in L:
 if l['lane'] is None:
  for b in l['source_bits']:missing[(l['src'],l['dst'])]['.'.join(map(str,b[1:3]))]+=1
 else:used[l['lane']]+=l['width']
assert not A.get('plan_cells'),'supply actual reserved_buses export for a plan-cell event; do not infer reservations'
edges=[]
for l in P['lanes']:
 hp=[ports[q] for q in l['ports']];cap=min(int(q['width']) for q in hp)
 edges.append(dict(id=l['id'],src=hp[0]['src']['part'],dst=hp[-1]['dst']['part'],capacity=cap,reserved=False,used=used[l['id']],left=max(0,cap-used[l['id']])))
unknown=set(used)-{e['id'] for e in edges};assert not unknown,unknown
assert all(e['used']<=e['capacity'] for e in edges),'saved allocation no longer fits current plan'
def flow(src,dst,field):
 cap=collections.defaultdict(int);adj=collections.defaultdict(set)
 for e in edges:
  a,b=e['src'],e['dst'];cap[(a,b)]+=e[field];adj[a].add(b);adj[b].add(a)
 total=0;paths=[]
 while True:
  par={src:None};q=[src]
  for a in q:
   for b in sorted(adj[a]):
    if b not in par and cap[(a,b)]>0:par[b]=a;q.append(b)
   if dst in par:break
  if dst not in par:break
  n=dst;path=[n];v=10**12
  while par[n] is not None:v=min(v,cap[(par[n],n)]);n=par[n];path.append(n)
  path=path[::-1]
  for a,b in zip(path,path[1:]):cap[(a,b)]-=v;cap[(b,a)]+=v
  paths.append(dict(parts=path,bits=v));total+=v
 cut=[e for e in edges if e['src'] in par and e['dst'] not in par]
 return dict(maxflow_bits=total,augmenting_paths=paths,mincut_edges=cut)
rows=[]
for (s,d),cs in sorted(missing.items()):
 direct=[e for e in edges if e['src']==s and e['dst']==d]
 pre=flow(s,d,'capacity');post=flow(s,d,'left')
 rows.append(dict(src=s,dst=d,actual_missing_bits=sum(cs.values()),actual_driver_widths=dict(cs),direct_lanes=direct,
                  capacity_before_reservations=pre,capacity_after_reservations=pre,
                  residual_after_saved_actual_allocations=post,
                  note='Max-flow is an independent per-pair upper bound; not a simultaneous allocation or cycle-compatible route.'))
report=dict(status='DIAGNOSTIC ONLY; no route/latency/source edits',reservation_basis='Existing sourcefix manifest has no plan_cells, so reserved_buses is empty',
            lane_count=len(edges),reservations=[],pairs=rows)
O.write_text(json.dumps(report,indent=1)+'\n')
for r in rows:
 print(f"{r['src']}->{r['dst']}: missing{r['actual_missing_bits']} pre{r['capacity_before_reservations']['maxflow_bits']} reservedSame residual{r['residual_after_saved_actual_allocations']['maxflow_bits']} directLeft{sum(e['left'] for e in r['direct_lanes'])}")
