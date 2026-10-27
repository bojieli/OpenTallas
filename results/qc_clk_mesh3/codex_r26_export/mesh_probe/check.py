import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'/w/encoded.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
n=b.findNet('ck_mesh_explicit');assert n is not None,'mesh source net renamed by alias linking'
w=n.getWire();assert w is not None
pins=sorted(it.getInst().getName()+'/'+it.getMTerm().getName() for it in n.getITerms())
assert pins==['ckt_2_0/Y','ckt_3_0/Y'],pins
ports=sorted(p.getName() for p in n.getBTerms());assert ports==['msh_t_0','msh_t_1'],ports
itr=odb.dbWirePathItr();itr.begin(w);pa=odb.dbWirePath();ps=odb.dbWirePathShape();length=0.;vias=0;widths=set()
while itr.getNextPath(pa):
 while itr.getNextShape(ps):
  sh=ps.shape
  if sh.isVia():
   v=sh.getTechVia() or sh.getVia()
   if v.getBottomLayer().getName()=='M8':vias+=1
  elif sh.getTechLayer().getName() in ('M8','M9'):
   dx,dy=sh.getDX(),sh.getDY();length+=(max(dx,dy)-min(dx,dy))/u;widths.add(round(min(dx,dy)/u,4))
# 266.24um planned mesh plus the explicitly modelled short driver pin-access jogs.
assert vias==4,vias
assert length>=266.24-1e-6,(length,widths)
r=dict(verdict='PASS',pins=pins,ports=ports,vias=vias,wire_um=round(length,6),planned_mesh_um=266.24,widths=sorted(widths))
open('/w/result.json','w').write(json.dumps(r,indent=1));print('V2_MESH_ODB_READBACK',json.dumps(r))
