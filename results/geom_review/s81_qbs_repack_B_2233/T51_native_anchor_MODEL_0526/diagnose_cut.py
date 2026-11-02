from pathlib import Path
import sys,json,collections,math
R=Path(__file__).parent;sys.path.insert(0,str(R/'tools'));import geom_rules as G
D=G.Design(R/'inputs/geom.tsv');T=json.load(open(R/'targets.json'));old=dict(D.cells)
for cid,c in list(D.cells.items()):
 if c[6]in T:
  a=list(c);a[2:6]=[v/1000 for v in T[c[6]]['bbox_dbu']];D.cells[cid]=tuple(a)
ycut=967.5;xband=[60,70];ans=[];classes=collections.Counter();total=0
for ni,(sig,dr,sk)in enumerate(D.nets):
 if sig=='CLOCK':continue
 refs=([dr]if dr else[])+sk;points=[];meta=[]
 for ref in refs:
  if ref[0]=='p':
   p=D.pin_by_k.get(ref[1])
   if p:points.append((p['x'],p['y']));meta.append(dict(name=p['name'],kind='P',xy=points[-1],moved=False))
  elif ref[1]in D.cells:
   c=D.cells[ref[1]];points.append(G.ctr(c));meta.append(dict(name=c[6],kind=c[0],xy=points[-1],moved=c[6]in T))
 if len(points)<2:continue
 if not min(p[1]for p in points)<ycut<max(p[1]for p in points):continue
 x0=math.floor(min(p[0]for p in points));x1=math.floor(max(p[0]for p in points));hit=max(0,min(69,x1)-max(60,x0)+1)
 if not hit:continue
 weight=hit/(x1-x0+1);total+=weight;moved=[p for p in meta if p['moved']];comb=[p for p in meta if p['kind']in('B','L','K')]
 if moved and comb:cl='moved_FF_to_original_comb'
 elif moved:cl='moved_FF_without_comb'
 else:cl='unchanged_net'
 classes[cl]+=weight
 ans.append(dict(geom_net_index=ni,column_crossing_weight=weight,classification=cl,bbox=[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)],endpoints=meta))
ans.sort(key=lambda x:-x['column_crossing_weight']);counter=collections.Counter()
for q in ans:
 for p in q['endpoints']:
  if p['kind']in('B','L','K'):counter['ft2_cland_comb'if p['name'].startswith('u_bound.u_cland_ft2_i/')else'other_comb']+=q['column_crossing_weight']
out=dict(scope='exact projected native net-box contribution decomposition; no route/newvariant/physicalchange',column_um=xband,horizontal_cut_y_um=ycut,total_crossing_weight=total,uniform_M2M7_column_capacity=481.8,reconstructed_col_util=total/481.8,weighted_classes=dict(classes),weighted_comb_endpoint_ownership=dict(counter),crossing_nets=len(ans),top_witnesses=ans[:12],moved_class_count=sum(x['classification']!='unchanged_net'for x in ans))
(R/'projected_cut_diagnosis.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items()if k!='top_witnesses'})
