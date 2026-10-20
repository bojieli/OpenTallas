import odb,json,hashlib,collections,math,os
from pathlib import Path
base=Path('/out')
f=base/'stage_assigned.odb';db=odb.dbDatabase.create();odb.read_db(db,str(f));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def itname(t):return t.getInst().getName()+'/'+t.getMTerm().getName()
def role(m):return 'ff' if 'DFF' in m.upper() else 'macro' if m.startswith('ot_') else 'comb'
boxes=json.loads(Path('/src/physical/ref_tile/dsdv_mu_hwin_c21j/native_box_proof.json').read_text())['boxes']
def term_box(t):
 i=t.getInst();m=i.getMaster()
 if m.isBlock():
  x,y=loc(t);return[x,y,x,y]
 g=i.getGroup()
 if not g or not g.getName().startswith('ot_hj_'):raise RuntimeError('missing native source owner '+i.getName())
 return boxes[g.getName()[6:]]
def distance(a,b):return max(abs(a[0]-b[2]),abs(a[2]-b[0]))+max(abs(a[1]-b[3]),abs(a[3]-b[1]))
def loc(t):
 bb=t.getBBox();return [(bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u]
outs={};sinks=collections.defaultdict(list);drivers={};trans={};mac=[]
for i in b.getInsts():
 m=i.getMaster();mn=m.getName();rr=role(mn)
 if m.isBlock():
  bb=i.getBBox();mac.append(dict(name=i.getName(),master=mn,bbox=[v/u for v in [bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]],pins=[dict(name=t.getMTerm().getName(),direction=str(t.getIoType()),signal=str(t.getSigType()),rectangles=len(t.getMTerm().getMPins())) for t in i.getITerms()]))
 ins=[];oo=[]
 for t in i.getITerms():
  n=t.getNet()
  if not n or str(t.getSigType()) in ('POWER','GROUND'):continue
  name=itname(t);entry=dict(pin=name,master=mn,role=rr,signal=str(t.getSigType()),xy=loc(t),box=term_box(t),net=n.getName())
  if str(t.getIoType())=='OUTPUT':drivers[name]=entry;outs[name]=n.getName();oo.append(name)
  else:sinks[n.getName()].append(entry);ins.append(name)
 if mn.startswith(('BUF','INV')):
  for t in ins:trans[t]=oo
for t in b.getBTerms():
 n=t.getNet()
 if not n or str(t.getSigType()) in ('POWER','GROUND'):continue
 box=t.getBBox();entry=dict(pin='PORT/'+t.getName(),master=None,role='input' if str(t.getIoType())=='INPUT' else 'output',signal=str(t.getSigType()),xy=[(box.xMin()+box.xMax())/2/u,(box.yMin()+box.yMax())/2/u],net=n.getName(),box=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u])
 if str(t.getIoType())=='INPUT':drivers[entry['pin']]=entry;outs[entry['pin']]=n.getName()
 else:sinks[n.getName()].append(entry)
masters={}
for i in b.getInsts():
 m=i.getMaster()
 if not m.isBlock() or m.getName() in masters:continue
 pins=[]
 for mt in m.getMTerms():
  rect=[]
  for mp in mt.getMPins():
   for g in mp.getGeometry():
    rect.append(dict(layer=g.getTechLayer().getName(),bbox=[v/u for v in [g.xMin(),g.yMin(),g.xMax(),g.yMax()]]))
  pins.append(dict(name=mt.getName(),signal=str(mt.getSigType()),rectangles=rect))
 masters[m.getName()]=dict(width_um=m.getWidth()/u,height_um=m.getHeight()/u,pins=pins)
Path('/out/endpoint_master_contacts.json').write_text(json.dumps(masters,indent=2)+'\n')
rows=[]
for name,d in drivers.items():
 if d['master'] and d['master'].startswith(('BUF','INV','TIE')):continue
 stack=[outs[name]];seen=set();end={}
 while stack:
  net=stack.pop()
  if net in seen:continue
  seen.add(net)
  for s in sinks[net]:
   if s['pin'] in trans:stack.extend(outs[x] for x in trans[s['pin']])
   else:end[s['pin']]=s
 reach=max((distance(d['box'],s['box']) for s in end.values()),default=0)
 rows.append(dict(driver=d,count=len(end),reach_um=reach,sinks=list(end.values())))
summary=dict(odb=str(f),odb_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),roots=len(rows),roles=dict(collections.Counter(r['driver']['role'] for r in rows)),max_count_by_role={r:max(x['count'] for x in rows if x['driver']['role']==r) for r in set(x['driver']['role'] for x in rows)},over32_nonclock=[dict(driver=r['driver'],count=r['count'],reach_um=r['reach_um']) for r in rows if r['count']>32 and r['driver']['signal']!='CLOCK' and r['driver']['pin']!='PORT/ck'],over405_nonclock=sum(r['reach_um']>405 for r in rows if r['driver']['signal']!='CLOCK' and r['driver']['pin']!='PORT/ck'),macros=len(mac),macro_masters=dict(collections.Counter(x['master'] for x in mac)),scope='Actual preGPL stage source graph after exact BUF/TIE filtering and all new birth ownership; conservative assigned whole-cell boxes versus actual unchanged fixed macro pin centers and placed port bounding boxes; no placed standard-cell timing/clock/PG qualification')
Path('/out/endpoint_roots.json').write_text(json.dumps(rows,separators=(',',':'))+'\n');Path('/out/endpoint_macros.json').write_text(json.dumps(mac,indent=2)+'\n');Path('/out/endpoint_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='over32_nonclock'},indent=2));print('OVER32',len(summary['over32_nonclock']))

checked=0;worst=None;bad=[]
for r in rows:
 if r['driver']['signal']=='CLOCK' or r['driver']['pin']=='PORT/ck':continue
 for q in r['sinks']:
  dist=distance(r['driver']['box'],q['box']);checked+=1
  item=dict(driver=r['driver'],sink=q,reach_um=dist)
  if worst is None or dist>worst['reach_um']:worst=item
  if dist>405.000001:bad.append(item)
proof=dict(schema='opentallas.native_stage_box_bound.v1',odb_sha256=summary['odb_sha256'],checked_endpoint_pairs=checked,worst=worst,over405=bad,scope=summary['scope'])
Path('/out/stage_endpoint_box_bound.json').write_text(json.dumps(proof,indent=1)+'\n')
print('STAGE_BOX_BOUND',checked,worst and worst['reach_um'],'over405',len(bad))
assert not bad
