"""Read native ODB connectivity/placement; export macro signal pins and their net endpoints."""
import json,os,hashlib
from pathlib import Path
import odb
p=Path(os.environ['MC_ODB']); db=odb.dbDatabase.create();odb.read_db(db,str(p)); b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def box(r):return [r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
macros={i.getName():i for i in b.getInsts() if i.getMaster().isBlock()}; nets={n.getName():n for n in b.getNets() if n.getSigType() not in ('POWER','GROUND')}
rows=[]
for name,n in sorted(nets.items()):
 pts=[]
 for it in n.getITerms():
  xy=it.getAvgXY();i=it.getInst()
  if xy[0]:pts.append(dict(inst=i.getName(),master=i.getMaster().getName(),macro=i.getName() in macros,pin=it.getMTerm().getName(),xy_um=[xy[1]/u,xy[2]/u]))
 for bt in n.getBTerms():
  for bp in bt.getBPins():
   for q in bp.getBoxes():pts.append(dict(port=bt.getName(),macro=False,xy_um=[(q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u]))
 rows.append(dict(net=name,endpoints=pts))
r=dict(schema='opentallas.macro_native_nets.v2',odb=str(p),odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),outline_um=box(b.getDieArea()),macros=[dict(name=i.getName(),master=i.getMaster().getName(),orient=str(i.getOrient()),rect_um=box(i.getBBox())) for i in macros.values()],nets=rows)
Path(os.environ['MC_OUT']).write_text(json.dumps(r,separators=(',',':'))+'\n');print('EXPORTED',len(macros),'macros',len(rows),'signal nets',os.environ['MC_OUT'])
