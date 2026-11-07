import openroad as ora,json,sys
from pathlib import Path
tech=ora.Tech();design=ora.Design(tech);design.readDb(sys.argv[1]);b=design.getBlock();u=b.getDbUnitsPerMicron();d={'u':u,'cells':[],'macros':[],'pins':[],'clock':[]}
for i in b.getInsts():
 if 'FILLER' in i.getMaster().getName().upper() or 'DECAP' in i.getMaster().getName().upper():continue
 bb=i.getBBox();row=[i.getName(),bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u]
 d['macros' if i.getMaster().isBlock() else 'cells'].append(row)
for p in b.getBTerms():
 for bp in p.getBPins():
  for x in bp.getBoxes():d['pins'].append([p.getName(),(x.xMin()+x.xMax())/(2*u),(x.yMin()+x.yMax())/(2*u)])
for n in b.getNets():
 if n.getSigType()!='CLOCK':continue
 pts=[]
 for it in n.getITerms():
  z=it.getInst().getBBox();pts.append([(z.xMin()+z.xMax())/(2*u),(z.yMin()+z.yMax())/(2*u)])
 if len(pts)>1:d['clock'].append([n.getName(),pts])
Path(sys.argv[2]).write_text(json.dumps(d))
