"""Finite necessary geometry bounds, actual macro endpoints plus selected FF edges."""
import gzip,json,sys,collections
from pathlib import Path
r=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(exist_ok=True)
g=json.load(gzip.open(r/'core_source_graph_v3.json.gz'));d=json.load(gzip.open(r/'core_reader_join_eio2/MACRO_READER_CONSTRAINTS.json.gz'));bounds={}
for ff,es in d['FF_macro_constraints'].items():
 u=[x['xy_um'][0]+x['xy_um'][1]for x in es];v=[x['xy_um'][0]-x['xy_um'][1]for x in es];bounds[ff]=[max(u)-402,min(u)+402,max(v)-402,min(v)+402]
bounds={k:bounds.get(k,[0,1792.8,-1032.48,760.32])for k in g['ff_nodes']}
adj={k:set()for k in bounds};edges=set()
for ff,terms in g['relevant_ff_input_sources'].items():
 if ff not in bounds:continue
 for ti in terms:
  t=g['terms'][ti]
  if t[0]=='FF' and str(t[1]) in bounds and str(t[1])!=ff:
   other=str(t[1]);adj[ff].add(other);adj[other].add(ff);edges.add(tuple(sorted((ff,other))))
q=collections.deque(bounds);queued=set(bounds);updates=0;bad=[]
while q:
 a=q.popleft();queued.discard(a)
 for b in adj[a]:
  aa=bounds[a];bb=bounds[b];new=[max(bb[0],aa[0]-399),min(bb[1],aa[1]+399),max(bb[2],aa[2]-399),min(bb[3],aa[3]+399)]
  if new[0]>new[1]+1e-7 or new[2]>new[3]+1e-7:
   bad.append({'source':a,'source_name':g['ff_nodes'][a]['name'],'capture':b,'capture_name':g['ff_nodes'][b]['name'],'source_bounds':aa,'prior_capture_bounds':bb,'tightened_capture_bounds':new});q.clear();break
  if any(abs(x-y)>1e-7 for x,y in zip(bb,new)):
   bounds[b]=new;updates+=1
   if b not in queued:q.append(b);queued.add(b)
summary={'status':'NECESSARY_BOUNDS_ONLY_NOT_PLACEMENT','all_existing_standard_FFs':len(bounds),'macro_adjacent_FFs':len(d['FF_macro_constraints']),'undirected_data_FF_edges':len(edges),'macro_pin_reserve_budget_um':402,'FF_center_budget_um':399,'interval_updates':updates,'empty_after_propagation':len(bad),'failures':bad,'limits':['All DATA-cone FF associations included; clock/reset geometry notincluded','Unique sites/macros/halos/obstacles notchecked','Unqualified EIO foldpinpolicy/nativeR90 support remainheld']}
(o/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(o/'TIGHTENED_READER_BOUNDS.json.gz','wt')as f:json.dump({'summary':summary,'bounds':bounds,'edges':sorted(edges)},f,separators=(',',':'))
print(json.dumps(summary))
