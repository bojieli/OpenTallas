import odb,json,math,re,hashlib
from pathlib import Path
from collections import deque
odbpath=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/3_place.odb'))
h=hashlib.sha256()
with odbpath.open('rb') as f:
 for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
db=odb.dbDatabase.create();odb.read_db(db,str(odbpath));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def xy(term):
 if hasattr(term,'getAvgXY'):
  a=term.getAvgXY()
  if len(a)==3 and a[0]:return a[1]/u,a[2]/u
  if len(a)==2:return a[0]/u,a[1]/u
 if hasattr(term,'getBPins'):
  boxes=[x for p in term.getBPins() for x in p.getBoxes()]
  if boxes:return sum((r.xMin()+r.xMax())/2/u for r in boxes)/len(boxes),sum((r.yMin()+r.yMax())/2/u for r in boxes)/len(boxes)
 raise ValueError('missing exact pin geometry '+term.getName())
def trans(i):
 name=i.getMaster().getName();return bool(re.match(r'^(BUF|INV)',name))
def name(t):return (t.getInst().getName()+'/'+t.getMTerm().getName()) if hasattr(t,'getInst') else 'PORT:'+t.getName()
clock=set();todo=[t.getNet() for t in b.getBTerms() if t.getName() in ['ck_core','ck_phy_fam']]
while todo:
 n=todo.pop()
 if n is None or n.getId() in clock:continue
 clock.add(n.getId())
 for t in n.getITerms():
  if str(t.getMTerm().getIoType())=='INPUT' and trans(t.getInst()):todo += [z.getNet() for z in t.getInst().getITerms() if str(z.getMTerm().getIoType())=='OUTPUT']
rows=[];missing=[];count=0
for n in b.getNets():
 if str(n.getSigType()) in ['POWER','GROUND','CLOCK'] or n.getId() in clock:continue
 ds=[t for t in n.getITerms() if str(t.getMTerm().getIoType())=='OUTPUT' and not trans(t.getInst()) and not re.match(r'^(TIE|LOGIC[01])',t.getInst().getMaster().getName())]+[t for t in n.getBTerms() if str(t.getIoType())=='INPUT']
 for d in ds:
  dp=xy(d);todo=[n];seen=set();ends=[]
  while todo:
   q=todo.pop()
   if q.getId() in seen:continue
   seen.add(q.getId())
   for z in q.getITerms():
    if str(z.getMTerm().getIoType())!='INPUT':continue
    if trans(z.getInst()):todo += [v.getNet() for v in z.getInst().getITerms() if str(v.getMTerm().getIoType())=='OUTPUT' and v.getNet()]
    else:ends.append(z)
   ends += [z for z in q.getBTerms() if str(z.getIoType())=='OUTPUT']
  for z in ends:
   zp=xy(z);dist=abs(dp[0]-zp[0])+abs(dp[1]-zp[1]);count+=1
   if dist>405:rows.append(dict(net=n.getName(),driver=name(d),sink=name(z),driver_xy=dp,sink_xy=zp,manhattan_um=dist))
rows.sort(key=lambda x:x['manhattan_um'],reverse=True)
r=dict(schema='opentallas.placed_transparent_net_reach.v1',stage='PRE_CTS_DIAGNOSTIC3_place.odb',odb_sha256=h.hexdigest(),scope='each nonclock/nontie signal driver to terminal sinks through BUF/INV; not a complete STA path-distance proof',threshold_um=405,checked_pairs=count,violations=len(rows),violating_pairs=rows,clock_nets_excluded=len(clock),pass_net_reach=not rows)
Path('/out/native_reach.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!="violating_pairs"}))
