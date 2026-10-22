"""Repair measured controller RRD branches around their actual body corner.
Run in OpenROAD Python; writes a NEW ODB. Buffers only, no protocol edges.
Input cause report pins each exact net/driver/sink and original launch class.
"""
import odb,json,sys,math,collections
src,report,out,receipt=sys.argv[1:]
db=odb.dbDatabase.create();odb.read_db(db,src);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
d=json.load(open(report));todo=[r for r in d['over_reach_branches'] if r['upstream_launch'][-1][1]=='dsfd_ctrl_rg3']
assert len(todo)==86 and all(r['root_pin'].startswith('rrd[') for r in todo)
master=db.findMaster('BUFx8_ASAP7_75t_R');w,h=master.getWidth(),master.getHeight()
row=b.getRows()[0];rx,ry=row.getOrigin();site=row.getSite();sw,rh=site.getWidth(),site.getHeight()
# Only this bounded controller band is modified. Exact existing cell boxes are
# indexed; candidate sites must avoid every existing body, cell and blockage.
boxes=[];buckets=collections.defaultdict(list);bucket=int(20*u)
def add_box(q):
 k=len(boxes);boxes.append(q)
 for x in range(q[0]//bucket,q[2]//bucket+1):
  for y in range(q[1]//bucket,q[3]//bucket+1):buckets[x,y].append(k)
def overlap(q):
 seen=set()
 for x in range(q[0]//bucket,q[2]//bucket+1):
  for y in range(q[1]//bucket,q[3]//bucket+1):
   for k in buckets.get((x,y),[]):
    if k in seen:continue
    seen.add(k);z=boxes[k]
    if q[0]<z[2] and q[2]>z[0] and q[1]<z[3] and q[3]>z[1]:return True
 return False
for inst in b.getInsts():
 bb=inst.getBBox();q=(bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax())
 if q[3]>=1200*u and q[1]<=1900*u and q[2]>=12000*u and q[0]<=21500*u:add_box(q)
for bk in b.getBlockages():
 if bk.isSoft():continue
 bb=bk.getBBox();add_box((bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()))
def place(x,y):
 sx=round((x*u-w/2-rx)/sw);sy=round((y*u-h/2-ry)/rh)
 # Same-row/site legality; bounded 12um search, with no overlap waiver.
 for radius in range(0,45):
  for dy in range(-radius,radius+1):
   for dx in ((-radius,radius) if abs(dy)<radius else range(-radius,radius+1)):
    q=(rx+(sx+dx)*sw,ry+(sy+dy)*rh,rx+(sx+dx)*sw+w,ry+(sy+dy)*rh+h)
    if not overlap(q):add_box(q);return q[:2]
 raise RuntimeError('No legal site within bounded corner reservation')
def xy(it):
 ok,x,y=it.getAvgXY();assert ok;return x/u,y/u
records=[];count=0
for r in todo:
 drv=b.findInst(r['driver'][0]).findITerm(r['driver'][1]);sink=b.findInst(r['sink'][0]).findITerm(r['sink'][1]);net=drv.getNet();assert net==sink.getNet() and net.getName()==r['net']
 a,z=xy(drv),xy(sink);body=next(o for o in r['bbox_obstructions'] if o['name']==r['upstream_launch'][-1][0]);x0,y0,x1,y1=body['box']
 # Route outside the real controller rectangle. The measured failures have
 # one endpoint on E and one on N; fail closed if that source geometry changes.
 assert (a[0]>=x1 and z[1]>=y1) or (z[0]>=x1 and a[1]>=y1),(r['net'],a,z,body)
 corner=(max(a[0],z[0],x1+8),max(a[1],z[1],y1+8))
 path=[a,(corner[0],a[1]),corner,(z[0],corner[1]),z]
 points=[]
 for p,q in zip(path,path[1:]):
  length=abs(p[0]-q[0])+abs(p[1]-q[1]);n=max(1,math.ceil(length/120))
  points.extend((p[0]+(q[0]-p[0])*j/n,p[1]+(q[1]-p[1])*j/n) for j in range(1,n+1))
 points=points[:-1];prev=net;cells=[];sink.disconnect()
 for x,y in points:
  if cells and abs(x-cells[-1][1][0])+abs(y-cells[-1][1][1])<2:continue
  loc=place(x,y);count+=1;name=f'ctrlcorner_{count}';assert not b.findInst(name)
  inst=odb.dbInst_create(b,master,name);inst.setLocation(*loc);inst.setPlacementStatus('PLACED');inst.setOrient('R0')
  ni=next(it for it in inst.getITerms() if str(it.getIoType())=='INPUT');no=next(it for it in inst.getITerms() if str(it.getIoType())=='OUTPUT')
  ni.connect(prev);nn=odb.dbNet_create(b,name+'_y');no.connect(nn);prev=nn;cells.append((name,xy(no)))
 sink.connect(prev);last=a;segments=[]
 for name,_ in cells:
  inst=b.findInst(name);ni=next(it for it in inst.getITerms() if str(it.getIoType())=='INPUT');no=next(it for it in inst.getITerms() if str(it.getIoType())=='OUTPUT');p=xy(ni);segments.append(abs(last[0]-p[0])+abs(last[1]-p[1]));last=xy(no)
 segments.append(abs(last[0]-z[0])+abs(last[1]-z[1]));assert max(segments)<=160,(r['net'],segments)
 records.append(dict(net=r['net'],root_net=r['root_net'],root_pin=r['root_pin'],obstruction=body,old_um=r['manhattan_um'],new_max_um=max(segments),buffers=len(cells)))
odb.write_db(db,out);json.dump(dict(source_odb=src,verdict='PASS',branches=len(records),buffers=count,added_protocol_edges=0,all_new_sites_nonoverlapping=True,records=records),open(receipt,'w'),indent=1);print('CTRL_CORNER_REPAIR_PASS',len(records),count)
