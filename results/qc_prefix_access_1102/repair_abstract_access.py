"""Correct abstract island origin/centre representation; never move clock cells.
Input remains immutable. Only generated stand-in M1-M3 OBS and M7 PG cuts change.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--tree',required=True);p.add_argument('--plan',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args()
sys.path.insert(0,a.tools)
import schema as S,die_trial as D
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
P=S.Plan(S.load(Path(a.plan)),Path(a.plan));t=json.loads(Path(a.tree).read_text())
# Native producer places each R0 CKINV16 at its lower-left. island_windows
# consumes centres. Preserve every actual home and use true body centres ONLY
# for the abstract reservations. Sizes are from the failed native census.
body=(1.62,.27)
sites=[((float(x)+body[0]/2,float(y)+body[1]/2),'native_body_center:'+n,body) for n,(x,y) in t['sites'].items()]
iw,irec=D.island_windows(P,sites)
db=odb.dbDatabase.create();odb.read_db(db,a.input);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();tech=db.getTech()
def rect(box):return [box.xMin(),box.yMin(),box.xMax(),box.yMax()]
def shapes(mt):return sorted((sh.getTechLayer().getName(),*rect(sh)) for mp in mt.getMPins() for sh in mp.getGeometry() if sh.getTechLayer())
def protected():
 h=hashlib.sha256()
 def put(x):h.update((json.dumps(x,separators=(',',':'))+'\n').encode())
 for i in sorted(b.getInsts(),key=lambda i:i.getName()):put(['I',i.getName(),i.getMaster().getName(),list(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus())])
 for n in sorted(b.getNets(),key=lambda n:n.getName()):put(['N',n.getName(),str(n.getSigType()),n.isSpecial(),sorted((x.getInst().getName(),x.getMTerm().getName()) for x in n.getITerms()),sorted(x.getName() for x in n.getBTerms())])
 seen=set()
 for i in b.getInsts():
  m=i.getMaster()
  if m.getName() in seen:continue
  seen.add(m.getName())
  for mt in m.getMTerms():
   if str(mt.getSigType()) not in ('POWER','GROUND'):put(['PIN',m.getName(),mt.getName(),str(mt.getIoType()),str(mt.getSigType()),shapes(mt)])
  put(['HIGHOBS',m.getName(),sorted((x.getTechLayer().getName(),*rect(x)) for x in m.getObstructions() if x.getTechLayer() and x.getTechLayer().getRoutingLevel()>3)])
 return h.hexdigest()
before=protected();groups={}
for pn,part in P.parts.items():
 i=b.findInst(pn);assert i is not None,('missing part',pn)
 m=i.getMaster();assert m.isBlock(),('not abstract block',pn)
 row=groups.setdefault(m.getName(),{'master':m,'types':set(),'holes':set(),'width':m.getWidth()/u,'height':m.getHeight()/u})
 row['types'].add(part['type']);row['holes'].update(tuple(x) for x in iw.get(part['type'],[]))
records=[]
for name,row in sorted(groups.items()):
 m=row['master'];w,h=row['width'],row['height'];holes=sorted(row['holes'])
 if not holes:continue
 old=[x for x in m.getObstructions() if x.getTechLayer() and x.getTechLayer().getRoutingLevel() in (1,2,3)]
 for x in old:odb.dbBox.destroy(x)
 free=D.rect_minus(w,h,holes)
 for ln in ('M1','M2','M3'):
  layer=tech.findLayer(ln);assert layer is not None
  for rr in free:odb.dbBox.create(m,layer,*[round(v*u) for v in rr])
 for net,j in [('VDD',0),('VSS',1)]:
  mt=m.findMTerm(net);assert mt is not None,(name,net)
  ports=list(mt.getMPins());assert len(ports)==1,(name,net,len(ports))
  mp=ports[0]
  for x in list(mp.getGeometry()):
   assert x.getTechLayer().getName()=='M7',(name,net,'unexpected PG layer')
   odb.dbBox.destroy(x)
  c=4.128+j*(.288+.096);layer=tech.findLayer('M7')
  while c+.144<w:
   for rr in D._cut_vertical((c-.144,0.,c+.144,h),holes):odb.dbBox.create(mp,layer,*[round(v*u) for v in rr])
   c+=8.64
 records.append({'master':name,'types':sorted(row['types']),'islands':len(holes),'old_M1_M3_boxes':len(old),'new_M1_M3_boxes':3*len(free)})
after=protected();assert before==after,'protected native cells/nets/endpoint geometry/higher OBS changed'
odb.write_db(db,str(out/'clock_native.odb'))
r={'scope':'Generated abstract reservations only; origin-to-body-centre correction, no native clock home/graph/port change; no routing/STA/PG qualification','input':a.input,'native_clock_cells':len(t['sites']),'protected_before':before,'protected_after':after,'centre_offset_um':[body[0]/2,body[1]/2],'island_in_core':sum(bool(h['in_core']) for r in irec for h in r['parts']),'changed_masters':len(records),'records':records}
(out/'repair.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='records'}))
