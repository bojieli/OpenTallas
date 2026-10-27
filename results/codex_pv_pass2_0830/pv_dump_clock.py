import odb,json,re
from pathlib import Path
r=odb.dbDatabase.create();odb.read_db(r,str(next(Path('/work/run/results/asap7').glob('*/base/3_place.odb'))));b=r.getChip().getBlock();u=b.getDbUnitsPerMicron();s=[];obs=[];pg=[];cells=[]
for i in b.getInsts():
 m=i.getMaster();n=m.getName();bb=i.getBBox()
 if re.match(r'^(DFF|DHL|DLL|SDF|ASYNC)',n):
  cp=i.findITerm('CLK')
  if cp is None:raise RuntimeError('missingCLK '+i.getName())
  s.append(i.getName()+'/CLK')
 if i.isFixed(): obs.append([bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u,i.getName()])
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):
  for sw in n.getSWires():
   for q in sw.getWires():
    if q.isVia():continue
    if q.getTechLayer().getName()=='M5':pg.append([q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u])
root=r.findMaster('BUFx4_ASAP7_75t_R');print('ROOT_MASTER',root.getWidth()/u,root.getHeight()/u)
out=dict(root_master_um=[root.getWidth()/u,root.getHeight()/u],sinks=sorted(s),fixed=obs,pg_M5=pg,rootclock=b.findBTerm('clk').getNet().getName())
open('/work/pv_clock_census.json','w').write(json.dumps(out,indent=1)+'\n')
print('PV_CLOCK_CENSUS',len(s),len(obs),len(pg))
