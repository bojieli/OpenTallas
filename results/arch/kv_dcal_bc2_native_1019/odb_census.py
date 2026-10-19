import odb,json,sys,hashlib
from collections import Counter
base=sys.argv[1];out=sys.argv[2];result={}
for stage in ['1_synth','6_final']:
 db=odb.dbDatabase.create();odb.read_db(db,base+'/'+stage+'.odb');b=db.getChip().getBlock();insts=list(b.getInsts());nets=[]
 for n in b.getNets():
  if str(n.getSigType()) in ('POWER','GROUND','CLOCK'):continue
  its=list(n.getITerms());drivers=[i for i in its if str(i.getIoType())=='OUTPUT'];loads=[i for i in its if str(i.getIoType())=='INPUT'];ports=[p.getName() for p in n.getBTerms()]
  if not drivers and not ports: continue
  if loads and all(i.getMTerm().getName().upper() in ('CLK','CK','CP') for i in loads):continue
  nets.append(dict(net=n.getName(),loads=len(loads),drivers=[dict(inst=i.getInst().getName(),master=i.getInst().getMaster().getName(),pin=i.getMTerm().getName()) for i in drivers],ports=ports,sinks=[i.getInst().getName()+'/'+i.getMTerm().getName() for i in loads]))
 ffs=[i for i in insts if 'DFF' in i.getMaster().getName()]
 result[stage]=dict(odb_sha256=hashlib.sha256(open(base+'/'+stage+'.odb','rb').read()).hexdigest(),ff_count=len(ffs),functional_master_counts=dict(Counter(i.getMaster().getName() for i in insts if not any(k in i.getMaster().getName().upper() for k in ['FILL','TAP','DECAP']))),over32=sorted([n for n in nets if n['loads']>32],key=lambda n:-n['loads']),max_loads=max(n['loads'] for n in nets),die_area=[b.getDieArea().xMin(),b.getDieArea().yMin(),b.getDieArea().xMax(),b.getDieArea().yMax()],dbu=b.getDbUnitsPerMicron())
 if stage=='6_final':
  pins=[]
  for p in b.getBTerms():
   rects=[box for bp in p.getBPins() for box in bp.getBoxes()];pins.append(dict(name=p.getName(),direction=str(p.getIoType()),rects=[[x.xMin(),x.yMin(),x.xMax(),x.yMax()] for x in rects]))
  result[stage]['pins']=pins
open(out,'w').write(json.dumps(result,indent=2)+'\n');print(json.dumps({s:dict(ff_count=a['ff_count'],max_loads=a['max_loads'],over32=[dict(net=n['net'],loads=n['loads'],drivers=n['drivers']) for n in a['over32']]) for s,a in result.items()},indent=2))
