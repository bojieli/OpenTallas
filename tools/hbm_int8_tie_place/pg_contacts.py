import odb,json,sys
from collections import defaultdict
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,sys.argv[1]);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();rails=defaultdict(list);vias=defaultdict(int)
for nn in ('VDD','VSS'):
 n=b.findNet(nn)
 for sw in n.getSWires():
  for s in sw.getWires():
   if s.isVia():vias[nn]+=1;continue
   layer=s.getTechLayer().getName()
   if layer=='M1':
    for k in range(s.yMin()//270,s.yMax()//270+1):rails[nn,k].append((s.xMin(),s.yMin(),s.xMax(),s.yMax()))
missing=[];checked=0;ties_checked=0
for i in b.getInsts():
 for pin in ('VDD','VSS'):
  it=i.findITerm(pin);hit=False
  if it and it.getNet() and it.getNet().getName()==pin:
   for mp in it.getMTerm().getMPins():
    for g in mp.getGeometry():
     if g.getTechLayer().getName()!='M1':continue
     bb=i.getBBox();o=str(i.getOrient());assert o in ('R0','MX','MY','R180'),o
     x0,x1=g.xMin(),g.xMax();y0,y1=g.yMin(),g.yMax();W=i.getMaster().getWidth();H=i.getMaster().getHeight()
     if o in ('MY','R180'):x0,x1=W-x1,W-x0
     if o in ('MX','R180'):y0,y1=H-y1,H-y0
     rect=odb.Rect(bb.xMin()+x0,bb.yMin()+y0,bb.xMin()+x1,bb.yMin()+y1)
     for k in range(rect.yMin()//270,rect.yMax()//270+1):
      for x,y,X,Y in rails[pin,k]:
       if max(x,rect.xMin())<min(X,rect.xMax()) and max(y,rect.yMin())<min(Y,rect.yMax()):hit=True
  checked+=1
  if i.getMaster().getName().startswith('TIE'):ties_checked+=1
  if not hit:missing.append(dict(instance=i.getName(),master=i.getMaster().getName(),pin=pin))
result=dict(scope='actual transformed M1 PG pin geometry versus same-net connected M1 rails',checked=checked,tie_contacts_checked=ties_checked,missing=missing,grid_vias=dict(vias),verdict='PASS' if not missing and all(vias[x]>0 for x in ('VDD','VSS')) else 'PG_OPEN')
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='missing'}))
