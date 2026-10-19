import json,gzip,collections
from openroad import Design,Tech
tech=Tech();D=Design(tech);D.evalTclString('read_db /data/eclock_control16_sramclk_hold_final_ff.odb');b=D.getBlock();u=b.getDbUnitsPerMicron();dbt=b.getDataBase().getTech()
def box(s):return [s.xMin()/u,s.yMin()/u,s.xMax()/u,s.yMax()/u]
tracks={}
for g in b.getTrackGrids():
 l=g.getTechLayer();tracks[l.getName()]={'direction':l.getDirection(),'width_um':l.getWidth()/u,'pitch_um':l.getPitch()/u,'x_patterns_dbu':[list(g.getGridPatternX(i)) for i in range(g.getNumGridPatternsX())],'y_patterns_dbu':[list(g.getGridPatternY(i)) for i in range(g.getNumGridPatternsY())]}
pg=[]
for n in b.getNets():
 if n.getSigType() not in ['POWER','GROUND']:continue
 for sw in n.getSWires():
  for s in sw.getWires():
   if s.isVia():
    for sh in s.getViaBoxes([]):
     l=sh.getTechLayer()
     if l and l.getRoutingLevel()>0:pg.append([n.getName(),l.getName(),'actual_via_enclosure',*box(sh)])
   else:
    l=s.getTechLayer()
    if l and l.getRoutingLevel()>0:pg.append([n.getName(),l.getName(),'actual_wire',*box(s)])
macros=[]
for i in b.getInsts():
 m=i.getMaster()
 if not m.isBlock():continue
 pins=[]
 for it in i.getITerms():
  mt=it.getMTerm()
  if mt.getSigType() in ['POWER','GROUND']:continue
  pins.append({'pin':mt.getName(),'direction':mt.getIoType(),'net':it.getNet().getName() if it.getNet() else None})
 macros.append({'instance':i.getName(),'master':m.getName(),'orientation':i.getOrient(),'bbox_um':box(i.getBBox()),'pins':pins})
r={'schema':'actual-final-ODB-static-macro-escape-inventory','adoption':False,'route_proof':False,'dbu_per_um':u,'tracks':tracks,'macro_pin_nets':macros,'actual_pdn_routing_shapes':pg,'pg_shape_count_by_layer':dict(collections.Counter(x[1] for x in pg)),'note':'Actual PG via enclosures expanded by OpenDB; no routing or DRC proof. Includes every routing-layer special wire/enclosure in final copied database.'}
with gzip.open('/data/d2d_actual_macro_escape_inventory.json.gz','wt') as f:json.dump(r,f,separators=(',',':'))
print('ACTUAL_MACRO_ESCAPE_INVENTORY macrocount',len(macros),'PGshapes',len(pg),'layers',r['pg_shape_count_by_layer'],'new_route',False)
