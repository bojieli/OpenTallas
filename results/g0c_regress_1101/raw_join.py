import argparse,collections,json,pathlib,sys
ap=argparse.ArgumentParser();ap.add_argument('tools');ap.add_argument('plan');ap.add_argument('out');a=ap.parse_args()
sys.path.insert(0,a.tools)
import schema as S,reset_tree as R
import taps
# Tools can be exported outside the sparse repo; resolve source bins in the plan's repo.
plan_path=pathlib.Path(a.plan).resolve()
repo=next((p for p in plan_path.parents if (p/'.git').exists()), pathlib.Path(a.tools).resolve().parents[1])
taps._root=lambda:repo
p=pathlib.Path(a.plan);P=S.Plan(json.loads(p.read_text()),p);rows=[]
for tn,t in P.types.items():
 declared=[r for r in t.get('reset_start_raw_exports',[]) if not r.get('existing_port')]
 if not declared:continue
 tree=R.for_type(P,tn);relays=R.start_relays(tree) if tree.get('start') else tree['relays'];by={r['name']:r for r in relays};matches=0;ds=[]
 for d in declared:
  actual=by.get(d['instance']);ok=actual is not None and actual['q']==d['net'] and all(abs(x-y)<=1e-6 for x,y in zip(actual['xy'],d['xy_um']))
  matches+=ok
  if not ok:ds.append(dict(declared=d,actual=actual))
 rows.append(dict(type=tn,declared=len(declared),matched=matches,mismatches=ds))
out=dict(plan=str(p),tools=a.tools,types=len(rows),exports=sum(r['declared'] for r in rows),matched=sum(r['matched'] for r in rows),rows=rows)
pathlib.Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(out['types'],out['exports'],out['matched'])
