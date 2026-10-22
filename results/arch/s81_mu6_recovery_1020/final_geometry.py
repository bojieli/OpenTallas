import odb,json,sys,os
odbp=os.environ['AUDIT_ODB']; out=os.environ.get('AUDIT_OUT','/audit/final_geometry.json'); db=odb.dbDatabase.create(); odb.read_db(db,odbp); b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron()
pg=[]; longest=[]; missing=[]; macro=[]; protected=[]
for i in b.getInsts():
 if i.getMaster().isBlock(): macro.append(i.getName())
 for t in i.getITerms():
  if t.getSigType() in ('POWER','GROUND') and not t.getNet(): missing.append(i.getName()+'/'+t.getMTerm().getName()); protected.append(dict(inst=i.getName(),pin=t.getMTerm().getName(),master=i.getMaster().getName(),placement=str(i.getPlacementStatus()),dont_touch=i.isDoNotTouch()))
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'): continue
 pts=[]
 for t in n.getITerms():
  ok,x,y=t.getAvgXY()
  if ok: pts.append((x/u,y/u))
 for t in n.getBTerms():
  for bp in t.getBPins():
   for bx in bp.getBoxes(): pts.append(((bx.xMin()+bx.xMax())/2/u,(bx.yMin()+bx.yMax())/2/u))
 if len(pts)>1:
  d=max(x+y for x,y in pts)-min(x+y for x,y in pts); d=max(d,max(x-y for x,y in pts)-min(x-y for x,y in pts))
  if d>405: longest.append(dict(net=n.getName(),max_pair_manhattan_um=d,endpoints=len(pts),clock=n.getSigType()=='CLOCK'))
json.dump(dict(schema='opentallas.readonly.final_geometry.v1',odb=odbp,pg_unbound_iterms=missing,pg_unbound_details=protected,macro_count=len(macro),macros=macro,over405=sorted(longest,key=lambda x:-x['max_pair_manhattan_um']),reach_scope='direct-net endpoint max Manhattan, includes all signal/clock nets; transparent cone reach and detailed-route length not established'),open(out,'w'),indent=2)
print('FINAL_GEOMETRY',len(missing),'PG_UNBOUND',len(longest),'OVER405')
