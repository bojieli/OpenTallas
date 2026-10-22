import odb,json,sys
bdb=odb.dbDatabase.create();odb.read_db(bdb,sys.argv[1]);b=bdb.getChip().getBlock();u=b.getDbUnitsPerMicron();r=json.load(open(sys.argv[2]));obs=[]
for inst in b.getInsts():
 bb=inst.getBBox()
 if (bb.xMax()-bb.xMin())/u>40 and (bb.yMax()-bb.yMin())/u>40:obs.append(dict(name=inst.getName(),master=inst.getMaster().getName(),box=[v/u for v in (bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax())]))
for row in r['over_reach_branches']:
 inst=b.findInst(row['driver'][0]);seen=set();rootpin=row['driver'][1]
 while inst and inst.getMaster().getName().startswith(('BUFx','INVx')):
  if inst.getName() in seen:break
  seen.add(inst.getName());ins=[it for it in inst.getITerms() if str(it.getIoType())=='INPUT' and str(it.getMTerm().getSigType()) not in ('POWER','GROUND')]
  if len(ins)!=1 or not ins[0].getNet():break
  drv=[it for it in ins[0].getNet().getITerms() if str(it.getIoType())=='OUTPUT']
  if len(drv)!=1:break
  it=drv[0];inst=it.getInst();rootpin=it.getMTerm().getName();rootnet=it.getNet().getName()
 row['root_pin']=rootpin;row['root_net']=rootnet
 a,z=row['driver'][2],row['sink'][2];x0,x1=sorted([a[0],z[0]]);y0,y1=sorted([a[1],z[1]])
 row['bbox_obstructions']=[o for o in obs if o['box'][0]<x1 and o['box'][2]>x0 and o['box'][1]<y1 and o['box'][3]>y0]
r['obstacles']=obs;json.dump(r,open(sys.argv[3],'w'),indent=1);print('CAUSES',len(r['over_reach_branches']),len(obs))
