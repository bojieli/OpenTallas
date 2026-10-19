import odb,json,sys,hashlib
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock()
def direction(x):return str(x.getIoType()).lower()
cells={};masters={}
for i in b.getInsts():
 m=i.getMaster(); n=m.getName();masters[n]={p.getName():{'direction':direction(p),'signal_type':str(p.getSigType())} for p in m.getMTerms()}
 cells[i.getName()]={'type':n,'port_directions':{p.getMTerm().getName():direction(p) for p in i.getITerms()},'connections':{p.getMTerm().getName():[p.getNet().getId()] if p.getNet() else [] for p in i.getITerms()},'pin_signal_types':{p.getMTerm().getName():str(p.getMTerm().getSigType()) for p in i.getITerms()}}
ports={p.getName():{'direction':direction(p),'bits':[p.getNet().getId()] if p.getNet() else [],'signal_type':str(p.getSigType())} for p in b.getBTerms()}
j={'schema':'opentallas.raw_odb_connectivity.v1','source_odb':str(src),'source_odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'no_exclusions':True,'modules':{b.getName():{'ports':ports,'cells':cells,'net_metadata':{str(n.getId()):{'name':n.getName(),'signal_type':str(n.getSigType())} for n in b.getNets()}}},'native_master_pins':masters}
(out/'raw.json').write_text(json.dumps(j,separators=(',',':'))+'\n');print(json.dumps({'schema':j['schema'],'odb_sha256':j['source_odb_sha256'],'cells':len(cells),'ports':len(ports),'nets':len(b.getNets()),'masters':len(masters)}))

positions={'units':b.getDbUnitsPerMicron(),'insts':{i.getName():{'master':i.getMaster().getName(),'bbox':list(i.getBBox().get()) if hasattr(i.getBBox(),'get') else [i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax()]} for i in b.getInsts()}}
(out/'positions.json').write_text(json.dumps(positions))
