import odb,json,re
from pathlib import Path
r=odb.dbDatabase.create();odb.read_db(r,str(next(Path('/work/run/results/asap7').glob('*/base/4_cts.odb'))));b=r.getChip().getBlock();u=b.getDbUnitsPerMicron();edges=[];sinks=[];bufs=[]
def xy(i):
 q=i.getBBox();return [(q.xMin()+q.xMax())/2/u,(q.yMin()+q.yMax())/2/u]
for n in b.getNets():
 if n.getSigType()!='CLOCK':continue
 d=n.getFirstOutput()
 if not d:continue
 src=d.getInst();sp=xy(src)
 for t in n.getITerms():
  i=t.getInst()
  if i==src:continue
  if t.getMTerm().getIoType()!='INPUT':continue
  mn=i.getMaster().getName()
  if re.match(r'^(BUF|INV|CK)',mn):edges.append([sp,xy(i)]);bufs.append(xy(i))
  elif t.getMTerm().getName()=='CLK':sinks.append(xy(i))
i=b.findInst('mp_pv_entry_trunk');assert i and i.getMaster().getName()=='BUFx4_ASAP7_75t_R';q=i.getBBox()
root=dict(name=i.getName(),master=i.getMaster().getName(),status=str(i.getPlacementStatus()),rect=[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u])
assert root['rect']==[86.238,86.4,86.616,86.67],root
out=dict(root=root,edges=edges,clock_buffers=bufs,clock_sinks=sinks)
open('/work/pv_cts_tree.json','w').write(json.dumps(out)+'\n');print('PV_CTS_TREE',root,'edges',len(edges),'sink_loads',len(sinks))
