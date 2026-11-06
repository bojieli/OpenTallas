import odb,json,re,math,os
from pathlib import Path
r=Path('/out');base=next(Path('/kit/run/results/asap7').glob('*/base'));db=odb.dbDatabase.create();odb.read_db(db,str(base/'6_final.odb'));b=db.getChip().getBlock();u=b.getDefUnits()
report=Path('/probe/final_negative_hold.rpt').read_text();targets=re.findall(r'^Endpoint: (.+)$',report,re.M);assert len(targets)==4
norm=lambda s:s.replace('\\','')
insts={norm(i.getName()):i for i in b.getInsts()};master=db.findMaster('HB4xp67_ASAP7_75t_R');assert master
bw,bh=master.getWidth(),master.getHeight()
def box(i):
 q=i.getBBox();return (q.xMin(),q.yMin(),q.xMax(),q.yMax())
def filler(i):return i.getMaster().getType()=='CORE_SPACER' and all(t.getSigType() in ('POWER','GROUND') for t in i.getITerms())
occupied=[(box(i),i.getName(),i.getMaster().getName()) for i in b.getInsts() if not filler(i)]
rows=[]
for row in b.getRows():
 q=row.getBBox();spacing=row.getSpacing() or row.getSite().getWidth()
 if q.yMax()-q.yMin()>=bh:rows.append((q.xMin(),q.yMin(),q.xMax(),q.yMax(),spacing,row.getOrient()))
proposals=[]
for index,name in enumerate(targets):
 i=insts[norm(name)];dst=i.findITerm('D');assert dst and dst.getNet();cap=box(i);cx=(cap[0]+cap[2])/2;cy=(cap[1]+cap[3])/2
 local=[v for v in occupied if v[0][0]<cx+20*u and v[0][2]>cx-20*u and v[0][1]<cy+20*u and v[0][3]>cy-20*u]
 best=None
 for x0,y0,x1,y1,step,orient in rows:
  if abs(y0+bh/2-cy)>20*u or x1<cx-20*u or x0>cx+20*u:continue
  blocks=sorted((max(x0,q[0]),min(x1,q[2])) for q,_,_ in local if q[1]<y0+bh and q[3]>y0 and q[0]<x1 and q[2]>x0)
  cursor=x0;gaps=[]
  for lo,hi in blocks:
   if lo>cursor:gaps.append((cursor,lo))
   cursor=max(cursor,hi)
  if cursor<x1:gaps.append((cursor,x1))
  for lo,hi in gaps:
   mn=math.ceil((lo-x0)/step);mx=math.floor((hi-bw-x0)/step)
   if mn>mx:continue
   n=min(mx,max(mn,round((cx-bw/2-x0)/step)));x=x0+n*step;cost=abs(x+bw/2-cx)+abs(y0+bh/2-cy)
   candidate=(cost,x,y0,orient)
   if best is None or cost<best[0]:best=candidate
 assert best,'No local legal gap within20um'
 _,x,y,orient=best;newbox=(x,y,x+bw,y+bh);newname=f'codex_exact_hold_{index}'
 proposals.append(dict(endpoint=i.getName()+'/D',capture=i.getName(),old_net=dst.getNet().getName(),new_instance=newname,master=master.getName(),location_dbu=[x,y],orient=orient,bbox_dbu=list(newbox),capture_bbox_dbu=list(cap),distance_um=best[0]/u,driver_pins=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in dst.getNet().getITerms() if t.getIoType()=='OUTPUT']))
 occupied.append((newbox,newname,master.getName()))
macros=[{'name':i.getName(),'rect_dbu':list(box(i))} for i in b.getInsts() if i.getMaster().isBlock()]
scene=[]
for q,name,mname in occupied:
 if any(q[0]<p['capture_bbox_dbu'][2]+3*u and q[2]>p['capture_bbox_dbu'][0]-3*u and q[1]<p['capture_bbox_dbu'][3]+3*u and q[3]>p['capture_bbox_dbu'][1]-3*u for p in proposals):scene.append({'bbox_dbu':list(q),'name':name,'master':mname})
out=dict(scope='EXACT_FOUR_DATA_HOLD_PROPOSAL_NO_CLOCK_OR_OLD_CELL_MOVE',dbu=u,side=os.environ['SIDE'],source_odb=str(base/'6_final.odb'),master_size_um=[bw/u,bh/u],added_cells=4,added_cycles=0,proposals=proposals,macros=macros,local_cells=scene,outline_dbu=[b.getDieArea().xMax(),b.getDieArea().yMax()])
(r/'proposal.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('macros','local_cells')},indent=2))
