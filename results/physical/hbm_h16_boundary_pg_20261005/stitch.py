import odb,json,hashlib
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/baseline/pdn_finite_selected.odb');b=D.getChip().getBlock();t=D.getTech();u=b.getDbUnitsPerMicron();m2=t.findLayer('M2');m3=t.findLayer('M3');vss=b.findNet('VSS')
via=next(v for v in t.getVias() if v.getBottomLayer().getName()=='M2' and v.getTopLayer().getName()=='M3')
other=[]
for n in b.getNets():
 if n.getName()=='VSS':continue
 for sw in n.getSWires():
  for q in sw.getWires():
   if q.isVia():
    v=q.getTechVia() or q.getBlockVia();x,y=q.getViaXY()
    for z in v.getBoxes():
     if z.getTechLayer()==m3:other.append([x+z.xMin(),y+z.yMin(),x+z.xMax(),y+z.yMax()])
   elif q.getTechLayer()==m3:other.append([q.xMin(),q.yMin(),q.xMax(),q.yMax()])
grid=b.findTrackGrid(m3);xs=list(grid.getGridX())
assert xs,'Actual M3 routing grid absent'
def hit(a,c):return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]
patches=[];sw=odb.dbSWire_create(vss,'ROUTED')
for lo,hi in [(304830,347976),(652806,695952),(1000782,1043928),(1348758,1349082)]:
 choices=[x for x in xs if lo+45<=x<=hi-45 and not any(hit([x-45-48,18-48,x+45+48,558+48],r) for r in other)]
 assert choices,('No finite legal M3 bridge location',lo,hi)
 x=choices[len(choices)//2]
 odb.dbSBox_create(sw,m2,x-45,-9,x+45,81,'STRIPE')
 odb.dbSBox_create(sw,m3,x-45,18,x+45,558,'STRIPE')
 for y in (36,540):odb.dbSBox_create(sw,via,x,y,'STRIPE')
 patches.append(dict(x_um=x/u,lower_M2_bbox_um=[(x-45)/u,-.009,(x+45)/u,.081],M3_bbox_um=[(x-45)/u,.018,(x+45)/u,.558],via_centers_um=[[x/u,.036],[x/u,.54]],native_tech_via=via.getName()))
odb.write_db(D,'/output/stitched.odb');Path('/output/geometry.json').write_text(json.dumps(dict(patches=patches,other_net_M3_clearance_um=.048,actual_native_M3_grid=True,VDD_unchanged=True,upper_M6_M9_unchanged=True),indent=2)+'\n');print(json.dumps(patches))
