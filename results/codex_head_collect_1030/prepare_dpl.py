import os,json,math
from pathlib import Path
import odb
db=odb.dbDatabase.create();db=odb.read_db(db,os.environ['INPUT_ODB']);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();moves=json.load(open('/lane/hb4_pinfix_moves.json'));fixed=[]
for i in b.getInsts():
 if i.getName() in moves:continue
 if i.getMaster().isBlock() or i.getPlacementStatus() in ('FIRM','LOCKED','COVER'):
  q=i.getBBox();fixed.append((q.xMin(),q.yMin(),q.xMax(),q.yMax()))
rows=[]
for r in b.getRows():
 x,y=r.getOrigin();s=r.getSite();rows.append((x,y,s.getWidth(),s.getHeight(),r.getOrient()))
placed=[]
for name,xy in moves.items():
 i=b.findInst(name)
 if i is None:raise ValueError('missing exact ring slot '+name)
 m=i.getMaster();w,h=m.getWidth(),m.getHeight();tx,ty=[int(v*u) for v in xy];chosen=None
 for ox,oy,sw,rh,orient in sorted(rows,key=lambda r:abs(r[1]-ty)):
  if abs(oy-ty)>15*u:continue
  for delta in sorted(range(-int(15*u/sw),int(15*u/sw)+1),key=abs):
   x=ox+round((tx-ox)/sw)*sw+delta*sw;y=oy;rect=(x,y,x+w,y+h);core=b.getCoreArea()
   if x<core.xMin() or x+w>core.xMax() or y<core.yMin() or y+h>core.yMax():continue
   if any(x<r[2] and r[0]<x+w and y<r[3] and r[1]<y+h for r in fixed):continue
   chosen=(x,y,orient,rect);break
  if chosen:break
 if chosen is None:raise ValueError('no macro/TAP-clear row at input slot '+name)
 x,y,orient,rect=chosen;i.setPlacementStatus('PLACED');i.setOrient(orient);i.setLocation(x,y);i.setPlacementStatus('FIRM');fixed.append(rect);placed.append(dict(name=name,master=m.getName(),xy_um=[x/u,y/u],orient=orient))
odb.write_db(db,'/out/pre_dpl.odb');Path('/out/slot_fit.json').write_text(json.dumps(dict(verdict='PASS',moved=len(placed),added_cycles=0,slots=placed),indent=1)+'\n');print('EXACT_SLOT_FIT',len(placed))
