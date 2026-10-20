import odb,os,json,hashlib,collections
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron()
def xy(t):
 v=t.getAvgXY();assert v[0];return (v[1]/scale,v[2]/scale,t.getInst().getName()+'/'+t.getMTerm().getName())
def compress(pts):
 if not pts:return ()
 return tuple(f(pts,key=lambda p:sx*p[0]+sy*p[1]) for sx,sy in [(1,1),(1,-1)] for f in [min,max])
nets={n.getId():n for n in b.getNets() if str(n.getSigType()) not in ('POWER','GROUND','CLOCK')};orig={};successors=collections.defaultdict(set);ops=[];sinks=[];seqmasters=collections.Counter()
def seed(n,pt):
 if n and n.getId() in nets:orig[n.getId()]=compress(list(orig.get(n.getId(),()))+[pt])
for inst in b.getInsts():
 master=inst.getMaster().getName();seq=('DFF' in master.upper() or 'SRAM' in master.upper() or inst.getMaster().isBlock());ins=[];outs=[]
 if seq:seqmasters[master]+=1
 for t in inst.getITerms():
  n=t.getNet()
  if not n or n.getId() not in nets:continue
  direction=str(t.getIoType())
  if direction=='OUTPUT':
   if seq:seed(n,xy(t))
   else:outs.append(n.getId())
  elif direction=='INPUT':
   if seq:sinks.append((n.getId(),xy(t)))
   else:ins.append(n.getId())
 if not seq and outs:
  idx=len(ops);ops.append((ins,outs))
  for i in ins:successors[i].add(idx)
for t in b.getBTerms():
 n=t.getNet()
 if not n or n.getId() not in nets:continue
 for pin in t.getBPins():
  for box in pin.getBoxes():
   pt=((box.xMin()+box.xMax())/2/scale,(box.yMin()+box.yMax())/2/scale,'PORT/'+t.getName())
   if str(t.getIoType())=='INPUT':seed(n,pt)
   elif str(t.getIoType())=='OUTPUT':sinks.append((n.getId(),pt))
queue=collections.deque(orig);pending=set(orig);updates=0
while queue:
 n=queue.popleft();pending.discard(n)
 for op in successors[n]:
  ins,outs=ops[op];pts=compress([pt for i in ins for pt in orig.get(i,())])
  if not pts:continue
  for out in outs:
   val=compress(list(orig.get(out,()))+list(pts))
   if val!=orig.get(out):
    orig[out]=val;updates+=1
    if out not in pending:queue.append(out);pending.add(out)
rows=[];unreached=[]
for net,sink in sinks:
 if net not in orig:unreached.append(dict(net=nets[net].getName(),sink=sink));continue
 source=max(orig[net],key=lambda p:abs(p[0]-sink[0])+abs(p[1]-sink[1]));dist=abs(source[0]-sink[0])+abs(source[1]-sink[1]);rows.append(dict(um=round(dist,6),source=source,sink=sink,net=nets[net].getName()))
rows.sort(key=lambda r:r['um'],reverse=True)
d=dict(schema='opentallas.placed_sequential_reach.v1',scope='conservative source to capture Manhattan displacement through all combinational pins, buffers transparent; SRAM and DFF are sequential cuts; PG/CLOCK excluded',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sequential_masters=dict(seqmasters),checked_capture_pins=len(rows),unreached_capture_pins=unreached,max_um=rows[0]['um'],over405_count=sum(r['um']>405 for r in rows),over405=[r for r in rows if r['um']>405],top=rows[:100],updates=updates)
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(d,indent=2)+'\n');print({k:v for k,v in d.items() if k not in ('unreached_capture_pins','over405','top')})
