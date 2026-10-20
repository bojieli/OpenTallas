import odb,sys,json,hashlib,collections
from pathlib import Path
p,out=map(Path,sys.argv[1:]);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();rows=[]
for n in b.getNets():
 if str(n.getSigType()) not in ['POWER','GROUND']:continue
 wires=list(n.getSWires());layers=collections.Counter();vias=0;shapes=0
 for w in wires:
  for box in w.getWires():
   shapes+=1
   if box.isVia():vias+=1
   else:
    layer=box.getTechLayer();layers[layer.getName() if layer else 'UNKNOWN']+=1
 terms=[{'name':t.getName(),'sigtype':str(t.getSigType()),'pins':len(list(t.getBPins()))} for t in n.getBTerms()]
 rows.append({'net':n.getName(),'sigtype':str(n.getSigType()),'native_iterms':len(list(n.getITerms())),'special_wires':len(wires),'shape_count':shapes,'via_shape_count':vias,'metal_shapes_by_layer':dict(layers),'bterms':terms})
status='PASS' if all(any(r['sigtype']==s and r['special_wires'] and r['shape_count'] and r['native_iterms'] for r in rows) for s in ['POWER','GROUND']) else 'FAIL'
out.write_text(json.dumps({'status':status,'scope':'Actual final ODB both POWER/GROUND special-wire grids and net-terminal membership. This is metadata/shape existence, not electrical resistance/short/via-connectivity qualification.','odb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'grids':rows},indent=2)+'\n');print(status,[(r['net'],r['shape_count'],r['via_shape_count']) for r in rows])
if status!='PASS':raise RuntimeError('native PG grids absent')
