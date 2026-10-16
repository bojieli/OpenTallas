exec(open('/audit.py').read().split("out={'dbu'")[0])
n=0
for t in b.getBTerms():
 if t.getSigType() in ['POWER','GROUND']:continue
 for bp in t.getBPins():
  for bx in list(bp.getBoxes()):
   l=bx.getTechLayer();a=[bx.xMin(),bx.yMin(),bx.xMax(),bx.yMax()]
   if l.getName()=='M5':a[0]+=12;a[2]+=12
   elif l.getName()=='M4':a[1]+=12;a[3]+=12
   else:continue
   odb.dbBox.destroy(bx);odb.dbBox.create(bp,l,*a);n+=1
print('shifted',n);odb.write_db(db,'/diag/shift.odb')
