import odb,json,math,bisect
from pathlib import Path
p=Path('/work');db=odb.dbDatabase.create();odb.read_db(db,str(p/'run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base/5_1_grt.odb'));b=db.getChip().getBlock();u=db.getTech().getDbUnitsPerMicron();master=db.findMaster('BUFx2_ASAP7_75t_R');assert master
w,h=master.getWidth(),master.getHeight();rows=[];insts=list(b.getInsts())
for row in b.getRows():
 rr=row.getBBox();site=row.getSite()
 if site.getHeight()!=h:continue
 rx,ry=rr.xMin(),rr.yMin();step=row.getSpacing();n=row.getSiteCount()
 if not step:step=site.getWidth()
 cap=n-math.ceil(w/step)+1
 if cap>0:rows.append(dict(x=rx,y=ry,step=step,n=n,orient=str(row.getOrient()),free=[(0,n)]))
rows.sort(key=lambda r:(r['y'],r['x']))
# Subtract actual occupied boxes, including physical fillers/taps, from each row.
for r in rows:
 blocked=[]
 for i in insts:
  q=i.getBBox()
  if q.yMin()>=r['y']+h or q.yMax()<=r['y']:continue
  lo=max(0,math.floor((q.xMin()-r['x'])/r['step']));hi=min(r['n'],math.ceil((q.xMax()-r['x'])/r['step']))
  if hi>lo:blocked.append((lo,hi))
 blocked.sort();free=[];end=0
 for lo,hi in blocked:
  if lo>end:free.append((end,lo))
  end=max(end,hi)
 if end<r['n']:free.append((end,r['n']))
 r['free']=free

def site_at(tx,ty):
 best=None
 for k,r in enumerate(rows):
  need=math.ceil(w/r['step']);target=(tx-r['x'])/r['step']
  for j,(lo,hi)in enumerate(r['free']):
   if hi-lo<need:continue
   ix=max(lo,min(hi-need,round(target)));x=r['x']+ix*r['step'];y=r['y']
   rank=(abs(x+w/2-tx)+abs(y+h/2-ty),y,x)
   if best is None or rank<best[0]:best=(rank,k,j,ix,need)
 assert best,'no free row site'
 rank,k,j,ix,need=best;r=rows[k];lo,hi=r['free'].pop(j)
 if ix>lo:r['free'].append((lo,ix))
 if ix+need<hi:r['free'].append((ix+need,hi))
 r['free'].sort();return dict(x=r['x']+ix*r['step'],y=r['y'],orient=r['orient'],displacement_dbu=rank[0])

def follow(net):
 todo=[net];seen=set();got=[];logic=[]
 while todo:
  n=todo.pop()
  if n.getId()in seen:continue
  seen.add(n.getId())
  for it in n.getITerms():
   if not it.isInputSignal():continue
   i=it.getInst();m=i.getMaster()
   if 'BUF' in m.getName()or 'INV' in m.getName():
    for o in i.getITerms():
     if o.isOutputSignal()and o.getNet():todo.append(o.getNet())
   elif m.isSequential():got.append((i.getName(),it.getMTerm().getName()))
   else:logic.append((i.getName(),it.getMTerm().getName()))
 return sorted(set(got)),logic
ports=sorted((t for t in b.getBTerms()if t.getName().startswith('in_d[')or t.getName()in ('in_v','in_v[0]')),key=lambda t:t.getName());assert len(ports)==1025,len(ports)
records=[]
for k,t in enumerate(ports):
 net=t.getNet();loads=[it for it in net.getITerms()if it.isInputSignal()];assert len(loads)==1,(t.getName(),len(loads));q=loads[0].getBBox();tx=(q.xMin()+q.xMax())/2;ty=(q.yMin()+q.yMax())/2
 captures,logic=follow(net);assert len(captures)==1 and not logic,(t.getName(),captures,logic)
 if t.getName().startswith('in_d['):assert captures[0][1]=='D',(t.getName(),captures)
 cells=[dict(name=f'phy_input_delay_{k}_{s}',net=f'phy_input_delay_n{k}_{s}',**site_at(tx,ty))for s in range(2)]
 records.append(dict(port=t.getName(),net=net.getName(),loads=[(it.getInst().getName(),it.getMTerm().getName())for it in loads],capture=captures[0],cells=cells))
original=[dict(name=i.getName(),box=[i.getBBox().xMin()/u,i.getBBox().yMin()/u,i.getBBox().xMax()/u,i.getBBox().yMax()/u])for i in insts]
out=dict(master=master.getName(),dbu=u,cell_size=[w/u,h/u],inputs=len(records),new_cells=2*len(records),max_displacement_um=max(c['displacement_dbu']/u for r in records for c in r['cells']),added_cell_area_um2=2*len(records)*w*h/u**2,records=records,original=original)
json.dump(out,open('/work/phy_delay_plan.json','w'),indent=1);print('PHY_INPUT_DELAY_PLAN',{k:v for k,v in out.items()if k not in ('records','original')})
