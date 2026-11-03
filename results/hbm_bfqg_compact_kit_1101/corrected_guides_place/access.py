import os,json,collections
from pathlib import Path
import odb

db=odb.dbDatabase.create();odb.read_db(db,os.environ['ODB']);b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron()
def box(q):return [q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
def overlap(a,c):return min(a[2],c[2])>max(a[0],c[0]) and min(a[3],c[3])>max(a[1],c[1])
pg=[];via_count=0
for n in b.getNets():
 if str(n.getSigType()) not in ['POWER','GROUND']:continue
 for sw in n.getSWires():
  for s in sw.getWires():
   if s.isVia():via_count+=1;continue
   tl=s.getTechLayer()
   if tl is not None:pg.append((tl.getName(),box(s),n.getName()))
insts=list(b.getInsts());out=[]
for i in insts:
 m=i.getMaster()
 if not m.isBlock():continue
 bb=box(i.getBBox());orient=str(i.getOrient());w,h=m.getWidth()/u,m.getHeight()/u
 if orient not in ['R0','MY']:raise ValueError('unexpected native orientation')
 def transform(r):
  q=box(r)
  if orient=='MY':q=[w-q[2],q[1],w-q[0],q[3]]
  return [bb[0]+q[0],bb[1]+q[1],bb[0]+q[2],bb[1]+q[3]]
 faces=collections.Counter();groups=collections.defaultdict(collections.Counter);pins=[];overlaps=[]
 for mt in m.getMTerms():
  if str(mt.getSigType()) in ['POWER','GROUND']:continue
  name=mt.getName();prefix=name.split('[')[0];rs=[]
  for mp in mt.getMPins():
   for geom in mp.getGeometry():
    layer=geom.getTechLayer().getName();r=transform(geom);rs.append((layer,r))
  if not rs:continue
  layer,r=rs[0];x=(r[0]+r[2])/2;face='W' if abs(x-bb[0])<.1 else 'E' if abs(x-bb[2])<.1 else 'INTERIOR'
  faces[face]+=1;groups[prefix][face]+=1
  if prefix in ['rd_out','wd_in','w_mask_in','clk']:pins.append(dict(name=name,face=face,layer=layer,box_um=r))
  for layer,r in rs:
   for pl,pr,pn in pg:
    if pl==layer and overlap(r,pr):overlaps.append(dict(pin=name,layer=layer,PG_net=pn,PG_box_um=pr,pin_box_um=r))
 near={}
 for face in ['W','E']:
  for category in ['active','tap_endcap']:
   candidates=[]
   for j in insts:
    jm=j.getMaster();jn=jm.getName()
    if jm.isBlock() or jm.isFiller():continue
    tap=jn.startswith(('TAPCELL','ENDCAP'))
    if tap!=(category=='tap_endcap'):continue
    r=box(j.getBBox())
    if r[3]<=bb[1] or r[1]>=bb[3]:continue
    gap=bb[0]-r[2] if face=='W' else r[0]-bb[2]
    if gap>=0:candidates.append((gap,j.getName(),jn,r))
   candidates.sort(key=lambda x:x[0]);near[face+'_'+category]=[dict(gap_um=round(g,6),instance=n,master=mn,box_um=r) for g,n,mn,r in candidates[:3]]
 obs=[]
 for ob in m.getObstructions():
  tl=ob.getTechLayer()
  if tl is not None:obs.append(dict(layer=tl.getName(),local_box_um=box(ob)))
 out.append(dict(instance=i.getName(),master=m.getName(),box_um=bb,orient=orient,signal_clock_pins=sum(faces.values()),faces=dict(faces),port_groups={k:dict(v) for k,v in groups.items()},selected_pin_shapes=pins,OBS=obs,nearest_bodies=near,same_layer_PG_pin_bbox_overlap_count=len(overlaps),same_layer_PG_pin_bbox_overlap_sample=overlaps[:8]))
tracks=[]
for tg in b.getTrackGrids():
 if tg.getTechLayer().getName() not in ['M1','M2','M3','M4','M5']:continue
 r=dict(layer=tg.getTechLayer().getName(),X=[],Y=[])
 for axis in ['X','Y']:
  for k in range(getattr(tg,'getNumGridPatterns'+axis)()):r[axis].append(list(getattr(tg,'getGridPattern'+axis)(k)))
 tracks.append(r)
result=dict(scope='Read-only actual macro/STD/TAP/PG lower-layer geometry; not pin-access DRC/GRT proof',source_ODB=os.environ['ODB'],dbu_per_um=u,macros=out,tracks_DBU=tracks,PG_metal_boxes=len(pg),PG_vias_not_expanded=via_count,limitations=['bbox overlap is not full DRC','PG via enclosure not expanded','pin-access legal points NOT RUN','no universal STD4.32 keepout inferred'])
Path(os.environ['OUT']).write_text(json.dumps(result,indent=1)+'\n');print('ACTUAL_MACRO_ACCESS_GEOMETRY',len(out),'macros','PGmetal',len(pg))
