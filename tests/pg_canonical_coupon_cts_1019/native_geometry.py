"""Read-only complete native master/ITerm and PG metal/contact census."""
import odb,json,sys,hashlib
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock()
def box(r):return [r.xMin(),r.yMin(),r.xMax(),r.yMax()]
def overlap(a,c):return max(a[0],c[0])<min(a[2],c[2]) and max(a[1],c[1])<min(a[3],c[3])
pg=[];native=[];rows=[box(r.getBBox()) for r in b.getRows()];cells=[];terms=[]
for i in b.getInsts():
 m=i.getMaster();it={t.getMTerm().getName():t for t in i.getITerms()}
 assert set(it)=={t.getName() for t in m.getMTerms()}
 cells.append({'name':i.getName(),'master':m.getName(),'xy':list(i.getLocation()),'orient':str(i.getOrient()),'bbox':box(i.getBBox()),'status':str(i.getPlacementStatus())})
 for mt in m.getMTerms():
  t=it[mt.getName()];assert str(t.getSigType())==str(mt.getSigType())
  entry={'instance':i.getName(),'master':m.getName(),'pin':mt.getName(),'role':str(mt.getSigType()),'net':t.getNet().getName() if t.getNet() else None,'geometry':[]}
  for p in mt.getMPins():
   for g in p.getGeometry():
    assert not g.isVia()
    # Use the native returned Rect type (the image exposes two Python Rect wrappers).
    r=g.getBox();i.getTransform().apply(r)
    entry['geometry'].append({'layer':g.getTechLayer().getName(),'box':box(r)})
  terms.append(entry)
  if entry['role'] in ('POWER','GROUND'):pg.append(entry)
shapes=[];via_count=0
for n in b.getNets():
 if str(n.getSigType()) not in ('POWER','GROUND'):continue
 for w in n.getSWires():
  for s in w.getWires():
   if s.isVia():
    v=s.getTechVia() or s.getBlockVia();assert v
    x,y=s.getViaXY();via_count+=1
    for g in v.getBoxes():shapes.append({'net':n.getName(),'layer':g.getTechLayer().getName(),'box':[g.xMin()+x,g.yMin()+y,g.xMax()+x,g.yMax()+y],'via':via_count})
   else:shapes.append({'net':n.getName(),'layer':s.getTechLayer().getName(),'box':box(s),'via':None})
shorts=[]
for k,a in enumerate(shapes):
 for c in shapes[k+1:]:
  if a['net']!=c['net'] and a['layer']==c['layer'] and overlap(a['box'],c['box']):shorts.append([a,c])
missing_contacts=[];wrong_contacts=[];contacts=0
for t in pg:
 for g in t['geometry']:
  hits=[s for s in shapes if s['layer']==g['layer'] and overlap(s['box'],g['box'])]
  if not any(s['net']==t['net'] for s in hits):missing_contacts.append({'term':t,'shape':g})
  else:contacts+=1
  for s in hits:
   if t['net'] is not None and s['net']!=t['net']:wrong_contacts.append({'term':t,'shape':s})
pins=[]
for t in b.getBTerms():
 for p in t.getBPins():
  for s in p.getBoxes():pins.append({'name':t.getName(),'role':str(t.getSigType()),'net':t.getNet().getName() if t.getNet() else None,'layer':s.getTechLayer().getName(),'box':box(s)})
j={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'dbu':b.getDbUnitsPerMicron(),'rows':rows,'cells':cells,'terms':terms,'pins':pins,'pg_shapes':shapes,'pg_via_count':via_count,'pg_terms':len(pg),'pg_unbound':[t for t in pg if t['net'] is None],'pg_contact_rectangles':contacts,'pg_missing_contact_rectangles':missing_contacts,'pg_cross_net_short_shapes':shorts,'pg_wrong_pin_contacts':wrong_contacts,'limitation':'Complete native master/ITerm and per-rectangle intersection census. Rooted conductor reachability and native DRC are separate, not inferred from intersection.'}
(out/'native_geometry.json').write_text(json.dumps(j,separators=(',',':'))+'\n')
print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in j.items() if k not in ('limitation',)}))
