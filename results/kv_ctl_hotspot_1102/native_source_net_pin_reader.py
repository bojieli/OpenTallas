import odb,os,json,gzip,re,hashlib
from pathlib import Path
out=Path('/out');p=Path(os.environ['ODB']);db=odb.dbDatabase.create();db=odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();skip=set();masters={}
for i in b.getInsts():
 m=i.getMaster();mn=m.getName()
 if re.match(r'^(TAPCELL|FILLER|FILL|DECAP)',mn):skip.add(i.getId());continue
 if mn in masters:continue
 ps={}
 for mt in m.getMTerms():
  rects=[]
  for mp in mt.getMPins():
   for g in mp.getGeometry():
    tl=g.getTechLayer()
    if tl is not None:rects.append(dict(layer=tl.getName(),rect_dbu=[g.xMin(),g.yMin(),g.xMax(),g.yMax()]))
  ps[mt.getName()]=dict(io=str(mt.getIoType()),sig=str(mt.getSigType()),rectangles=rects)
 masters[mn]=dict(width_dbu=m.getWidth(),height_dbu=m.getHeight(),is_macro=m.isBlock(),pins=ps)
(out/'master_pin_shapes.json').write_text(json.dumps(dict(dbu=u,masters=masters),separators=(',',':')))
pks={bt.getName():k for k,bt in enumerate(b.getBTerms())};nidx=0
with gzip.open(out/'native_nets.jsonl.gz','wt') as f:
 for n in b.getNets():
  sg=str(n.getSigType())
  if sg in ['POWER','GROUND']:continue
  dr=[];sk=[]
  for it in n.getITerms():
   i=it.getInst();iid=i.getId()
   if iid in skip:continue
   mt=it.getMTerm();isout=it.isOutputSignal();clock=str(mt.getSigType())=='CLOCK' or re.match(r'^(CLK|CK|GCLK)$',mt.getName());e=dict(ref='i'+str(iid)+('c' if clock and not isout else ''),inst=i.getName(),master=i.getMaster().getName(),pin=mt.getName())
   (dr if isout else sk).append(e)
  for bt in n.getBTerms():
   e=dict(ref='p'+str(pks[bt.getName()]),pin=bt.getName(),inst=None)
   (dr if str(bt.getIoType())=='INPUT' and not dr else sk).append(e)
  if not sk:continue
  f.write(json.dumps(dict(index=nidx,native_id=n.getId(),name=n.getName(),sig=sg,drivers=dr,sinks=sk),separators=(',',':'))+'\n');nidx+=1
(out/'reader_receipt.json').write_text(json.dumps(dict(status='READ_ONLY_NATIVE_SOURCE_NET_PIN_DUMP',ODB=str(p),ODB_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),net_records=nidx,master_types=len(masters),dbu=u),indent=2)+'\n');print('NATIVE_NET_PIN_DUMP_PASS',nidx,len(masters))
