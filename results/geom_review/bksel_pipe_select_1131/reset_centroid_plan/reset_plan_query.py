import odb,json,math
from pathlib import Path
p=Path('/work');db=odb.read_db(odb.dbDatabase.create(),str(p/'3_place.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
src=b.findInst(r'u_c.rst_s\[1\]$_DFF_PN0_');pred=b.findInst(r'u_c.rst_s\[0\]$_DFF_PN0_');assert src and pred
bb=lambda x:[x.getBBox().xMin(),x.getBBox().yMin(),x.getBBox().xMax(),x.getBBox().yMax()]
def info(i):
 return {'name':i.getName(),'master':i.getMaster().getName(),'bbox_um':[a/u for a in bb(i)],'orient':str(i.getOrient()),'placement_status':str(i.getPlacementStatus()),'terms':[{'pin':t.getMTerm().getName(),'io':str(t.getIoType()),'net':t.getNet().getName() if t.getNet() else None,'drivers':[{'inst':s.getInst().getName(),'pin':s.getMTerm().getName()} for s in t.getNet().getITerms() if str(s.getIoType())=='OUTPUT'] if t.getNet() else []} for t in i.getITerms()]}
origin=info(src);data=[t for t in src.getITerms() if t.getMTerm().getName()=='D'];assert len(data)==1
chain=[];net=data[0].getNet();visited=set();found=False
while net and net.getId() not in visited:
 visited.add(net.getId());ds=[t for t in net.getITerms() if str(t.getIoType())=='OUTPUT'];assert len(ds)==1,('D net drivers',net.getName(),len(ds))
 t=ds[0];i=t.getInst();chain.append({'net':net.getName(),'driver':i.getName(),'master':i.getMaster().getName(),'pin':t.getMTerm().getName()})
 if i==pred:found=True;break
 assert i.getMaster().getName().startswith(('BUF','INV')),('nonbuffer in predecessor chain',chain)
 inputs=[z for z in i.getITerms() if str(z.getIoType())=='INPUT' and str(z.getSigType())!='POWER' and str(z.getSigType())!='GROUND'];assert len(inputs)==1
 net=inputs[0].getNet()
assert found,chain
load=json.loads((p/'reset_loads.json').read_text());tx,ty=[a*u for a in load['all_captures']['centroid']];w=src.getMaster().getWidth();h=src.getMaster().getHeight()
insts=[bb(i) for i in b.getInsts() if i!=src];rows=[]
for r in b.getRows():
 rbb=bb(r)
 if rbb[3]-rbb[1]!=h or str(r.getOrient())!=str(src.getOrient()):continue
 rows.append((abs((rbb[1]+h/2)-ty),r,rbb))
rows.sort(key=lambda z:z[0]);best=None
for _,r,rb in rows[:30]:
 x0,y0,x1,y1=rb;site=r.getSite().getWidth();ints=sorted((max(x0,a),min(x1,c)) for a,z,c,d in insts if z<y1 and d>y0 and a<x1 and c>x0);cur=x0;gaps=[]
 for a,c in ints:
  if a>cur:gaps.append((cur,a))
  cur=max(cur,c)
 if cur<x1:gaps.append((cur,x1))
 for a,c in gaps:
  lo=x0+math.ceil((a-x0)/site)*site;hi=x0+math.floor((c-w-x0)/site)*site
  if hi<lo:continue
  x=min(hi,max(lo,x0+round((tx-w/2-x0)/site)*site));y=y0
  score=abs(x+w/2-tx)+abs(y+h/2-ty)
  if best is None or score<best['distance_centroid_dbu']:
   ov=sum(a<x+w and c>x and z<y+h and d>y for a,z,c,d in insts)
   best={'location_dbu':[x,y],'bbox_um':[x/u,y/u,(x+w)/u,(y+h)/u],'centre_um':[(x+w/2)/u,(y+h/2)/u],'orient':str(r.getOrient()),'row':r.getName(),'row_bbox_um':[v/u for v in rb],'site_width_um':site/u,'overlaps':ov,'distance_centroid_dbu':score}
assert best and best['overlaps']==0
out={'scope':'Read-only exact DB connectivity and proposed existing-cell vacant row/site; no ODB changed','db_units':u,'source':origin,'predecessor':info(pred),'D_from_predecessor':True,'predecessor_buffer_chain':chain,'all_loads':{k:v for k,v in load.items() if k not in ['captures','over405_names']},'proposed':best}
(p/'reset_site_plan.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
