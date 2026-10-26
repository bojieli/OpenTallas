import odb,json,os,hashlib
p=os.environ['HROW_ODB'];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();ps={}
for t in b.getBTerms():
 boxes=[dict(layer=x.getTechLayer().getName(),rect_um=[x.xMin()/u,x.yMin()/u,x.xMax()/u,x.yMax()/u]) for p in t.getBPins() for x in p.getBoxes()]
 if boxes:ps[t.getName()]=dict(direction=str(t.getIoType()),boxes=boxes)
a=b.getDieArea();d=dict(schema='opentallas.actual_cts_pins.v1',odb_source=os.environ['HROW_SOURCE'],odb_sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),outline_um=[a.xMax()/u,a.yMax()/u],pins=ps,status='Actual CTS pins; routed abstract and timing qualification pending')
open('/out/pins.json','w').write(json.dumps(d,indent=1)+'\n')
