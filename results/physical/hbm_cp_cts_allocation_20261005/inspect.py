import odb,json,collections
D=odb.dbDatabase.create();odb.read_db(D,'/output/clock_membership.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();outside=[];clock=[];other=collections.Counter();area=collections.Counter()
for i in b.getInsts():
 n=i.getName();m=i.getMaster();g=i.getGroup();box=i.getBBox();r=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u]
 if n.startswith(('clkbuf_','clkload')):
  clock.append(dict(name=n,bbox=r,group=None if g is None else g.getName(),area=m.getWidth()*m.getHeight()/u**2))
  if r[0]<17.28 or r[1]<17.28 or r[2]>60.48 or r[3]>56.16:outside.append(n)
 if g is None and not i.isFixed():other[m.getName()]+=1;area[m.getName()]+=m.getWidth()*m.getHeight()/u**2
groups={};violations=[]
for i in b.getInsts():
 g=i.getGroup()
 if g is None:continue
 gn=g.getName();m=i.getMaster();v=groups.setdefault(gn,dict(count=0,area_um2=0));v['count']+=1;v['area_um2']+=m.getWidth()*m.getHeight()/u**2
 box=i.getBBox();r=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u];bounds=[17.28,17.28,60.48,56.16] if gn=='cp_body' else [17.28,56.16,22.464,60.48]
 if any([r[0]<bounds[0]-1e-6,r[1]<bounds[1]-1e-6,r[2]>bounds[2]+1e-6,r[3]>bounds[3]+1e-6]):violations.append(i.getName())
x=dict(groups=groups,all_group_containment_violations=violations,clock_count=len(clock),clock_area=sum(z['area'] for z in clock),clock_outside_finite_body=outside,clock_cells=clock,other_ungrouped_masters=dict(other),other_ungrouped_area=dict(area));open('/output/legality.json','w').write(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k!='clock_cells'}))
