"""Read-only saved-ODB whole-instance PG census, no connects or writes to the database."""
import os,json,collections,gzip,hashlib
from pathlib import Path
import odb
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB']);b=D.getChip().getBlock();baseline=set()
baseline={line.rstrip('\n') for line in gzip.open(os.environ['BASE_NAMES'],'rt')}
expected={'POWER':os.environ['POWER_NET'],'GROUND':os.environ['GROUND_NET']};counts=collections.Counter();bad=[];born=collections.Counter();wrong=[]
for i in b.getInsts():
 m=i.getMaster();cl='macro'if m.isBlock()else('tap'if m.getName().startswith('TAPCELL')else'std');fresh=i.getName().replace('\\','')not in baseline
 if fresh:born[cl]+=1
 for mt in m.getMTerms():
  sig=str(mt.getSigType())
  if sig not in('POWER','GROUND'):continue
  counts[(cl,sig,'terms')]+=1;t=i.findITerm(mt.getName());n=t.getNet()if t else None;ok=bool(n)and str(n.getSigType())==sig and n.getName()==expected[sig]
  if n and (str(n.getSigType())!=sig or n.getName()!=expected[sig]):wrong.append([i.getName(),mt.getName(),n.getName(),expected[sig]])
  counts[(cl,sig,'connected'if ok else'unbound_or_wrong_type')]+=1
  if not ok:bad.append(dict(inst=i.getName(),master=m.getName(),pin=mt.getName(),sigtype=sig,net=n.getName()if n else None,net_type=str(n.getSigType())if n else None,new_instance=fresh,bbox_dbu=[i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax()]))
# This full native snapshot also defines any later PG-only repair guard.
rect=lambda q:[q.xMin(),q.yMin(),q.xMax(),q.yMax()]
cellmeta=[]
for i in b.getInsts():cellmeta.append([i.getName(),i.getMaster().getName(),rect(i.getBBox()),list(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus()),bool(i.isDoNotTouch())])
rows=[[r.getName(),rect(r.getBBox()),list(r.getOrigin()),str(r.getOrient()),r.getSite().getName()]for r in b.getRows()]
pins=[[bt.getName(),str(bt.getIoType()),str(bt.getSigType()),bt.getNet().getName()if bt.getNet()else None,[[str(bp.getPlacementStatus()),[[q.getTechLayer().getName(),rect(q)]for q in bp.getBoxes()if q.getTechLayer()]]for bp in bt.getBPins()]]for bt in b.getBTerms()]
clockpins=[]
for i in b.getInsts():
 if not (i.getMaster().isBlock() or i.getMaster().getName().startswith(('DFFHQN','DFFASRHQN'))):continue
 for t in i.getITerms():
  mt=t.getMTerm()
  if not t.isInputSignal():continue
  if str(mt.getSigType())!='CLOCK' and mt.getName().lower()not in('clk','ck','clock','clkn','clk_n'):continue
  success,x,y=t.getAvgXY()
  clockpins.append(dict(inst=i.getName(),master=i.getMaster().getName(),pin=mt.getName(),master_sigtype=str(mt.getSigType()),net=t.getNet().getName()if t.getNet()else None,net_sigtype=str(t.getNet().getSigType())if t.getNet()else None,xy_dbu=[x,y],AvgXY_ok=bool(success),macro=i.getMaster().isBlock()))
Path(os.environ['OUT']).with_name('actual_clock_pins.json').write_text(json.dumps(clockpins))
netmeta=[];pgmeta=[]
for n in b.getNets():
 sig=str(n.getSigType())
 if sig not in('POWER','GROUND'):
  netmeta.append([n.getName(),sig,bool(n.isDoNotTouch()),sorted([t.getInst().getName(),t.getMTerm().getName()]for t in n.getITerms()),sorted(bt.getName()for bt in n.getBTerms())])
 else:
  for sw in n.getSWires():
   for q in sw.getWires():
    v=(q.getTechVia()or q.getBlockVia())if q.isVia()else None
    pgmeta.append([n.getName(),str(sw.getWireType()),bool(q.isVia()),v.getName()if v else None,q.getTechLayer().getName()if q.getTechLayer()else None,rect(q)])
snapshot={'cells':sorted(cellmeta),'rows':sorted(rows),'pins':sorted(pins),'nonPG_nets':sorted(netmeta),'PG_shapes':sorted(pgmeta)}
hashpart=lambda x:hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()
guard={k:{'count':len(v),'sha256':hashpart(v)}for k,v in snapshot.items()}
out=Path(os.environ['OUT']);gzip.open(str(out)+'.native_snapshot.json.gz','wt').write(json.dumps(snapshot,separators=(',',':')))
out.write_text(json.dumps(dict(scope='READ_ONLY_NATIVE_WHOLE_INSTANCE_PG',odb=os.environ['ODB'],dbu_per_um=b.getDbUnitsPerMicron(),counts={'|'.join(k):v for k,v in counts.items()},new_instance_counts=dict(born),guard=guard,expected_PG_nets=expected,wrong_domain_terms=len(wrong),wrong_domain_witnesses=wrong[:20],bad_terms=len(bad),bad_new_terms=sum(r['new_instance']for r in bad),witnesses=bad[:30]),indent=2)+'\n');gzip.open(str(out)+'.all_bad.json.gz','wt').write(json.dumps(bad));print(out.read_text())
