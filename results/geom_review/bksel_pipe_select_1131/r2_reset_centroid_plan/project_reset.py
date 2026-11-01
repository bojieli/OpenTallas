from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'geometry_tools_main'))
import geom_rules as g
p=Path(__file__).resolve().parent;D=g.Design(p/'geom.tsv');load=json.loads((p/'reset_loads.json').read_text());s=json.loads((p/'reset_site_plan.json').read_text());src=load['source']['id'];pred=load['predecessor']['id'];t=s['proposed']['centre_um'];pre=load['predecessor']['xy'];old=D.cells[src];D.cells[src]=old[:2]+tuple(s['proposed']['bbox_um'])+old[6:]
xy=lambda i:list(g.ctr(D.cells[i]));md=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
seen=set();edges=[];stack=[src];direct=[]
while stack:
 a=stack.pop()
 if a in seen:continue
 seen.add(a)
 for n in D.drives.get(a,[]):
  for z in D.nets[n][2]:
   if z[0]!='i' or z[2]:continue
   b=z[1];e={'driver':D.cells[a][6],'driver_xy':xy(a),'capture':D.cells[b][6],'capture_xy':xy(b),'distance_um':md(xy(a),xy(b))};edges.append(e)
   if a==src:direct.append(e)
   if D.kind(b) in 'BLK':stack.append(b)
o={'scope':'PROPOSED only; R2 own existing internal FF move; no ODB changed','target_xy':t,'predecessor_xy':pre,'predecessor_register_hop':md(t,pre),'all_reset_tree_edges':len(edges),'max_reset_tree_edge':max(edges,key=lambda z:z['distance_um']),'max_all_reset_captures':max(md(t,x['xy']) for x in load['captures']),'direct_outgoing':direct,'projected_global_r2r':g.r2r_metrics(D)}
(p/'reset_legal_projection.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps(o,indent=2))
