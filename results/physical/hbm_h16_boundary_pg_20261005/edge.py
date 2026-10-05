import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/baseline/pdn_finite_selected.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
for n in b.getNets():
 if n.getName() not in ('VSS','VDD'):continue
 for sw in n.getSWires():
  for q in sw.getWires():
   if q.isVia():
    v=q.getTechVia() or q.getBlockVia();x,y=q.getViaXY()
    for z in v.getBoxes():
     l=z.getTechLayer()
     if l and l.getName() in ('M2','M3','M4','M5'):
      a=[x+z.xMin(),y+z.yMin(),x+z.xMax(),y+z.yMax()]
      if a[2]>1348600 and a[0]<1349400 and a[1]<1000:print(n.getName(),v.getName(),l.getName(),a)
   else:
    a=[q.xMin(),q.yMin(),q.xMax(),q.yMax()];l=q.getTechLayer()
    if l and l.getName() in ('M2','M3','M4','M5') and a[2]>1348600 and a[0]<1349400 and a[1]<1000:print(n.getName(),l.getName(),a)
print('M3grid',[x for x in b.findTrackGrid(D.getTech().findLayer('M3')).getGridX() if x>1348500])
