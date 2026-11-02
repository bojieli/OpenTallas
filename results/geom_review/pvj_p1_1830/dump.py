import odb,csv,json,collections
from pathlib import Path
P=Path('/out');db=odb.dbDatabase.create();odb.read_db(db,'/input/run/results/asap7/hc_ot_qwen_tp8_pv_join_t__172_8x172_8/base/5_route.odb');b=db.getChip().getBlock();u=float(b.getDbUnitsPerMicron())
def box(r):return [r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
member={};regions=[]
for g in b.getGroups():
 r=g.getRegion()
 if r is None:continue
 insts=list(g.getInsts());name=g.getName()
 for i in insts:member[i.getId()]=name
 rects=[box(q) for q in r.getBoundaries()]
 area=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/u**2 for i in insts)
 regions.append(dict(name=name,type=str(g.getType()),region_type=str(r.getRegionType()),rects=rects,members=len(insts),member_master_area_um2=area,statuses=dict(collections.Counter(str(i.getPlacementStatus()) for i in insts))))
with (P/'placed.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['kind','name','master','x','y','w','h','status','region'])
 for i in b.getInsts():
  m=i.getMaster();n=m.getName();r=box(i.getBBox());k='macro' if m.isBlock() else 'tap' if n.startswith(('TAP','FILL','DECAP')) else 'ff' if n.startswith(('DFF','SDF')) else 'logic'
  w.writerow([k,i.getName(),n,r[0],r[1],r[2]-r[0],r[3]-r[1],str(i.getPlacementStatus()),member.get(i.getId(),'')])
rows=[]
for r in b.getRows():
 x,y=r.getOrigin();s=r.getSite();rows.append([x/u,y/u,s.getWidth()/u,s.getHeight()/u,r.getSiteCount(),str(r.getOrient())])
(P/'regions.json').write_text(json.dumps(dict(scope='READ_ONLY_PV_P1_ROUTE_CHECKPOINT_NO_STA_OR_PLACEMENT',die=box(b.getDieArea()),core=box(b.getCoreArea()),regions=regions,rows=rows),indent=1)+'\n')
print('PV_P1_ODB_READ_ONLY_DUMP',len(list(b.getInsts())),len(regions),len(rows),flush=True)
