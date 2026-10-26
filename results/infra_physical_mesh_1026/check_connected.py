import odb,json
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/work/mesh_before.odb');b=D.getChip().getBlock()
rect=lambda o:(o.xMin(),o.yMin(),o.xMax(),o.yMax())
all_nodes=[];results={}
for name in ['ck_mesh','VDD','VSS']:
 n=b.findNet(name);nodes=[]
 for s in n.getSWires():
  for v in s.getWires():
   if v.isVia():
    x,y=v.getViaXY();shapes=[(q.getTechLayer().getName(),(q.xMin()+x,q.yMin()+y,q.xMax()+x,q.yMax()+y)) for q in v.getTechVia().getBoxes() if q.getTechLayer().getRoutingLevel()>0]
   else:shapes=[(v.getTechLayer().getName(),rect(v))]
   nodes.append(('route',shapes))
 for i in n.getITerms():
  x,y=i.getInst().getLocation();shapes=[]
  for p in i.getMTerm().getMPins():
   for q in p.getGeometry():
    shapes.append((q.getTechLayer().getName(),(q.xMin()+x,q.yMin()+y,q.xMax()+x,q.yMax()+y)))
  nodes.append((i.getInst().getName()+'.'+i.getMTerm().getName(),shapes))
 for t in n.getBTerms():nodes.append(('PORT:'+t.getName(),[(q.getTechLayer().getName(),rect(q)) for p in t.getBPins() for q in p.getBoxes()]))
 parent=list(range(len(nodes)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def hit(a,z):return a[0]<=z[2] and z[0]<=a[2] and a[1]<=z[3] and z[1]<=a[3]
 for i in range(len(nodes)):
  for j in range(i):
   if any(la==lb and hit(a,z) for la,a in nodes[i][1] for lb,z in nodes[j][1]):parent[find(i)]=find(j)
 comps={find(i) for i in range(len(nodes))}
 assert len(comps)==1,(name,len(comps))
 results[name]={'physical_3d_components':len(comps),'terminals':len(n.getITerms())+len(n.getBTerms()),'route_objects':len(nodes)-len(n.getITerms())-len(n.getBTerms()),'verdict':'CONNECTED'}
 all_nodes += [(name,l,r) for _label,ss in nodes for l,r in ss]
shorts=[]
for i,(a,l,r) in enumerate(all_nodes):
 for z,k,s in all_nodes[:i]:
  if a!=z and l==k and hit(r,s):shorts.append((a,z,l,r,s))
assert not shorts,shorts[:5]
Path('/work/connected_3d.json').write_text(json.dumps({'nets':results,'same_layer_cross_net_overlaps':len(shorts),'verdict':'CONNECTED_NO_CROSS_NET_OVERLAPS','scope':'geometric routing/via/terminal connectivity; no extraction/timing/IR/DRC signoff'},indent=2)+'\n')
print('ACTUAL_MESH_PG_3D_CONNECTED',results)
