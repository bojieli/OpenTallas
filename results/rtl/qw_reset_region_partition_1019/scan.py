"""Read-only native reset interface and selected parent connectivity extraction."""
import json,pathlib,hashlib
import odb
P=pathlib.Path('/work')
def load(path):
 d=odb.dbDatabase.create();odb.read_db(d,str(path));return d,d.getChip().getBlock()
def point(t,u):
 b=t.getBBox();return [(b.xMin()+b.xMax())/2/u,(b.yMin()+b.yMax())/2/u]
def term(t,u):
 return dict(inst=t.getInst().getName(),master=t.getInst().getMaster().getName(),pin=t.getMTerm().getName(),io=str(t.getIoType()),signal=str(t.getSigType()),xy=point(t,u))
out={}
for name in ['qfd_rst_rep','qfd_rst_rep_p8']:
 path=P/(name+'.odb');d,b=load(path);u=b.getDbUnitsPerMicron()
 ports={t.getName():dict(io=str(t.getIoType()),net=t.getNet().getName() if t.getNet() else None) for t in b.getBTerms()}
 cells=[]
 for i in b.getInsts():
  if 'DFF' not in i.getMaster().getName(): continue
  cells.append(dict(name=i.getName(),master=i.getMaster().getName(),pins=[dict(term(t,u),net=t.getNet().getName() if t.getNet() else None) for t in i.getITerms() if str(t.getSigType()) not in ['POWER','GROUND']]))
 out[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),ports=ports,capture_cells=cells,die=[v/u for v in [b.getDieArea().xMin(),b.getDieArea().yMin(),b.getDieArea().xMax(),b.getDieArea().yMax()]],signal_nets=[dict(name=n.getName(),ports=[t.getName() for t in n.getBTerms()],pins=[term(t,u) for t in n.getITerms()]) for n in b.getNets() if str(n.getSigType()) not in ['POWER','GROUND']])
(P/'native_leaf.json').write_text(json.dumps(out,indent=1))
d,b=load('/original/floorplan_ck.odb');u=b.getDbUnitsPerMicron();sel=json.loads((P/'selected.json').read_text()); names={k.rsplit('/',1)[0] for k in sel}; ins={}
nets={}
for name in sorted(names):
 i=b.findInst(name)
 tr=i.getTransform();offset=tr.getOffset()
 ins[name]=dict(master=i.getMaster().getName(),orientation=str(i.getOrient()),origin=list(i.getOrigin()),transform_offset=list(offset),units=u,pins=[dict(term(t,u),net=t.getNet().getName() if t.getNet() else None) for t in i.getITerms()])
 for t in i.getITerms():
  n=t.getNet()
  if not n or str(n.getSigType()) in ['CLOCK','POWER','GROUND'] or t.getMTerm().getName()=='clk':continue
  nets[n.getName()]=dict(pins=[term(q,u) for q in n.getITerms()],ports=[q.getName() for q in n.getBTerms()])
(P/'parent_native.json').write_text(json.dumps(dict(instances=ins,nets=nets),indent=1))
print('SCAN_DONE',len(ins),len(nets),{k:len(v['capture_cells']) for k,v in out.items()},flush=True)
