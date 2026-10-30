import json,pathlib,odb
K=pathlib.Path('/kit');db=odb.dbDatabase.create();odb.read_db(db,str(next(K.glob('run/results/asap7/*/base/3_2_place_iop.odb'))));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();R=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
masters={}
for name in ['BUFx12f_ASAP7_75t_R','BUFx4_ASAP7_75t_R']:
 m=db.findMaster(name);pins={}
 for term in m.getMTerms():
  shapes=[]
  for mp in term.getMPins():
   for g in mp.getGeometry():
    layer=g.getTechLayer();shapes.append(dict(layer=layer.getName()if layer else'VIA',rect=R(g)))
  pins[term.getName()]=shapes
 masters[name]=dict(size=[m.getWidth()/u,m.getHeight()/u],pins=pins)
pg=[]
for net in b.getNets():
 if str(net.getSigType())not in('POWER','GROUND'):continue
 for sw in net.getSWires():
  for g in sw.getWires():
   x0,y0,x1,y1=R(g)
   if x1<97 or x0>110 or y1<58 or y0>72:continue
   layer=g.getTechLayer();pg.append(dict(net=net.getName(),layer=layer.getName()if layer else'VIA',rect=[x0,y0,x1,y1]))
pathlib.Path('/out/pin_pg.json').write_text(json.dumps(dict(masters=masters,nearby_special_PG=pg),indent=1)+'\n');print('ACTUAL_PIN_PG',list(masters),len(pg),'nearbyPGshapes')
