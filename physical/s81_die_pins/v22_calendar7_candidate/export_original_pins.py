import hashlib,json,odb
from pathlib import Path
p=Path('/db/3_2_place_iop.odb');db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron();die=b.getDieArea();w=(die.xMax()-die.xMin())/u;h=(die.yMax()-die.yMin())/u
rows=[]
for t in b.getBTerms():
 if str(t.getSigType()) in ['POWER','GROUND']:continue
 boxes=[x for p in t.getBPins() for x in p.getBoxes()]
 assert len(boxes)==1,(t.getName(),len(boxes))
 r=boxes[0];x=(r.xMin()+r.xMax())/(2*u);y=(r.yMin()+r.yMax())/(2*u)
 distances={'W':abs(x),'E':abs(w-x),'S':abs(y),'N':abs(h-y)};face=min(distances,key=distances.get)
 assert distances[face]<.3,(t.getName(),x,y)
 rows.append(dict(pin=t.getName().replace('\\',''),direction=str(t.getIoType()),face=face,layer=r.getTechLayer().getName(),x_um=x,y_um=y,box_um=[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]))
out=dict(schema='opentallas.actual_odb_pins.v1',source_odb=str(p),source_odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),dbu=u,block=b.getName(),outline_um=[w,h],pins=sorted(rows,key=lambda x:x['pin']))
Path('/out/original_actual_pins.json').write_text(json.dumps(out,indent=1)+'\n')
print('EXPORTED_ACTUAL_PINS',len(rows),w,h)
