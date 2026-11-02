import json,gzip,pathlib,sys
r=pathlib.Path(sys.argv[1]);o=pathlib.Path(sys.argv[2]);g=json.load(gzip.open(r/'core_source_graph_v3.json.gz'));p=json.load(gzip.open(o/'READER_SITE_PROPOSAL.json.gz'));xy={x['ff']:x['center_um']for x in p['rows']};bad=[];n=0;unplaced=0;maxdist=0
for b,ts in g['relevant_ff_input_sources'].items():
 if b not in xy:continue
 for ti in ts:
  t=g['terms'][ti]
  if t[0]!='FF' or str(t[1])==b:continue
  a=str(t[1])
  if a not in xy:unplaced+=1;continue
  d=sum(abs(x-y)for x,y in zip(xy[a],xy[b]));n+=1;maxdist=max(maxdist,d)
  if d>399+1e-7:bad.append({'source':g['ff_nodes'][a]['name'],'capture':g['ff_nodes'][b]['name'],'source_node':a,'capture_node':b,'distance_um':round(d,6)})
z={'scope':'actual DATA cone FF edges with both endpoints macro-adjacent; not full source placement','tested':n,'FF_center_budget_um':399,'max_tested_distance_um':round(maxdist,6),'failures':len(bad),'unplaced_predecessor_edges':unplaced};(o/'FF_EDGE_SCREEN.json').write_text(json.dumps(z,indent=2)+'\n');print(z)
with gzip.open(o/'FF_EDGE_FAILURES.json.gz','wt')as f:json.dump(bad,f)
