import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/baseline/pdn_finite_selected.odb');b=D.getChip().getBlock();t=D.getTech()
for v in list(t.getVias())+list(b.getVias()):
 if v.getBottomLayer().getName()=='M1' and v.getTopLayer().getName()=='M2':
  print('VIA12',v.getName(),[(z.getTechLayer().getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()) for z in v.getBoxes()])
vss=b.findNet('VSS');c=0
for sw in vss.getSWires():
 for q in sw.getWires():
  if not q.isVia() and q.getTechLayer().getName()=='M1' and q.yMin()<20:
   print('GROUND_M1',q.xMin(),q.yMin(),q.xMax(),q.yMax());c+=1
print('ground_m1_count',c)
