import odb,json,math
from pathlib import Path
r=Path('/work');out=Path('/out');db=odb.read_db(odb.dbDatabase.create(),str(r/'run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def box(o):
 q=o.getBBox();return [q.xMin(),q.yMin(),q.xMax(),q.yMax()]
def inf(i):return {'name':i.getName(),'master':i.getMaster().getName(),'bbox_um':[v/u for v in box(i)],'orient':str(i.getOrient()),'status':str(i.getPlacementStatus())}
a=b.findInst('wire19249');z=b.findInst('wire19380');up=b.findInst('wire11825');assert a and z and up
assert a.getMaster()==z.getMaster() and a.getMaster().getName()=='BUFx16f_ASAP7_75t_R'
def loads(i):return [t for t in i.findITerm('Y').getNet().getITerms() if str(t.getIoType())=='INPUT']
assert [t.getInst() for t in loads(a)]==[z]
assert [t.getInst() for t in loads(up)]==[a]
ls=loads(z);assert len(ls)==5
pin=lambda t:[v/u for v in t.getAvgXY()[1:]]
xy=[pin(t) for t in ls];tx=sum(v[0] for v in xy)/5;ty=sum(v[1] for v in xy)/5
macros=[i for i in b.getInsts() if i.getMaster().isBlock()];assert len(macros)==1
mb=box(macros[0]);halo=4.32*u;hb=[mb[0]-halo,mb[1]-halo,mb[2]+halo,mb[3]+halo]
assert all(y*u<hb[1] for x,y in xy)
rects=[box(i) for i in b.getInsts() if i not in (a,z)]+[hb]
rects += [box(q) for q in b.getBlockages()]
plans=[]
def vacancy(i,target,bounds):
 w=i.getMaster().getWidth();h=i.getMaster().getHeight();xwant,ywant=[v*u for v in target];best=None
 rows=[q for q in b.getRows() if box(q)[3]-box(q)[1]==h and str(q.getOrient())==str(i.getOrient())]
 rows.sort(key=lambda q:abs(box(q)[1]+h/2-ywant))
 for row in rows[:40]:
  x0,y0,x1,y1=box(row);site=row.getSite().getWidth();cy=(y0+h/2)/u
  if not bounds[1]<=cy<=bounds[3]:continue
  ints=sorted((max(x0,v[0]),min(x1,v[2])) for v in rects if v[1]<y1 and v[3]>y0 and v[0]<x1 and v[2]>x0)
  cur=x0;gaps=[]
  for lo,hi in ints:
   if lo>cur:gaps.append((cur,lo))
   cur=max(cur,hi)
  if cur<x1:gaps.append((cur,x1))
  for lo,hi in gaps:
   lo=max(lo,bounds[0]*u-w/2);hi=min(hi,bounds[2]*u+w/2)
   left=x0+math.ceil((lo-x0)/site)*site;right=x0+math.floor((hi-w-x0)/site)*site
   if right<left:continue
   x=min(right,max(left,x0+round((xwant-w/2-x0)/site)*site));y=y0
   score=abs(x+w/2-xwant)+abs(y+h/2-ywant)
   if best is None or score<best['score_dbu']:
    assert not any(v[0]<x+w and v[2]>x and v[1]<y+h and v[3]>y for v in rects)
    best={'location_dbu':[x,y],'centre_um':[(x+w/2)/u,(y+h/2)/u],'bbox_um':[x/u,y/u,(x+w)/u,(y+h)/u],'row':row.getName(),'orient':str(row.getOrient()),'overlaps':0,'score_dbu':score}
 assert best,('no vacant site in measured corridor',i.getName(),target,bounds)
 rects.append([v*u for v in best['bbox_um']]);return best
# Existing upstream buffer stays north. Split the shortest west-halo detour
# between the two existing downstream buffers; no database is mutated.
west=min(37.5,hb[0]/u-a.getMaster().getWidth()/u/2-.54)
relay_y=34.55
for i,target,bounds in [(a,[west,relay_y],[32,27,hb[0]/u-a.getMaster().getWidth()/u/2-.27,hb[1]/u-a.getMaster().getHeight()/u/2-.27]),(z,[tx,ty],[tx-6,ty-4,tx+6,min(ty+4,hb[1]/u-z.getMaster().getHeight()/u/2-.27)])]:
 plans.append({'source':inf(i),'target_um':target,'proposed':vacancy(i,target,bounds)})
d={'scope':'READ-ONLY PREPARED two-existing-buffer macro-detour relay; no ODB/cells/logic/cycles/clock/constraint change','inst_count':len(b.getInsts()),'net_count':len(b.getNets()),'db_units':u,'upstream_fixed':inf(up),'macro':inf(macros[0]),'declared_halo_um':4.32,'routing_layers':['M2','M3','M4','M5'],'halo_bbox_um':[v/u for v in hb],'loads':[{'inst':t.getInst().getName(),'pin':t.getMTerm().getName(),'xy_um':pin(t)} for t in ls],'load_centroid_um':[tx,ty],'plans':plans,'timing':'NOT MEASURED; fresh actual TT/FF+DRV required, no DRT release'}
(out/'data_relay_plan1418.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
