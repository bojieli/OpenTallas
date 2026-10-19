import odb,json,pathlib,collections
r=pathlib.Path('/run');db=odb.dbDatabase.create();odb.read_db(db,str(r/'placed.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();out={'units':u,'die':[b.getDieArea().xMin(),b.getDieArea().yMin(),b.getDieArea().xMax(),b.getDieArea().yMax()],'cells':{},'ports':{},'rows':[],'nets':{}}
for row in b.getRows():
 box=row.getBBox();out['rows'].append([box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u])
for i in b.getInsts():
 box=i.getBBox();pins={}
 for t in i.getITerms():
  ok,x,y=t.getAvgXY();pins[t.getMTerm().getName()]=[x/u,y/u] if ok else [(box.xMin()+box.xMax())/2/u,(box.yMin()+box.yMax())/2/u]
 out['cells'][i.getName()]={'master':i.getMaster().getName(),'bbox':[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u],'pins':pins,'status':i.getPlacementStatus(),'block':i.getMaster().isBlock()}
for t in b.getBTerms():
 boxes=[z for p in t.getBPins() for z in p.getBoxes()];out['ports'][t.getName()]={'direction':t.getIoType(),'boxes':[[z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u] for z in boxes],'layers':[z.getTechLayer().getName() for z in boxes]}
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):continue
 out['nets'][n.getName()]={'cells':[[t.getInst().getName(),t.getMTerm().getName(),t.getIoType()] for t in n.getITerms()],'ports':[t.getName() for t in n.getBTerms()]}
(r/'placed_geometry.json').write_text(json.dumps(out));print('extracted',len(out['cells']),len(out['ports']),len(out['rows']))

import hashlib
base=odb.dbDatabase.create();odb.read_db(base,str(r/'floorplan.odb'));bb=base.getChip().getBlock()
def graph(block):
 return {'cells':sorted((i.getName(),i.getMaster().getName()) for i in block.getInsts()),'nets':sorted((n.getName(),sorted((t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()),sorted(t.getName() for t in n.getBTerms())) for n in block.getNets())}
source_graph=graph(bb);placed_graph=graph(b);assert source_graph==placed_graph,'placement changed source connectivity/master/instance'
receipt={'source_odb_sha256':hashlib.sha256((r/'floorplan.odb').read_bytes()).hexdigest(),'placement_odb_sha256':hashlib.sha256((r/'placed.odb').read_bytes()).hexdigest(),'identical_native_graph':True,'canonical_graph_sha256':hashlib.sha256(json.dumps(source_graph,sort_keys=True).encode()).hexdigest()}
(r/'native_graph_receipt.json').write_text(json.dumps(receipt,indent=2));print(receipt)
