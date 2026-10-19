import odb,json,hashlib,collections,math
from pathlib import Path
base=Path('/work/results/asap7/opentallas_ot_s81sl_ve_asap7_ref_gate/base')
f=base/'5_1_grt.odb';db=odb.dbDatabase.create();odb.read_db(db,str(f));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def itname(t):return t.getInst().getName()+'/'+t.getMTerm().getName()
def role(m):return 'ff' if 'DFF' in m.upper() else 'macro' if m.startswith('ot_') else 'comb'
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
  name=itname(t);entry=dict(pin=name,master=mn,role=rr,signal=str(t.getSigType()),xy=loc(t),net=n.getName())
  if str(t.getIoType())=='OUTPUT':drivers[name]=entry;outs[name]=n.getName();oo.append(name)
  else:sinks[n.getName()].append(entry);ins.append(name)
 if mn.startswith(('BUF','INV')):
  for t in ins:trans[t]=oo
for t in b.getBTerms():
 n=t.getNet()
 if not n or str(t.getSigType()) in ('POWER','GROUND'):continue
 box=t.getBBox();entry=dict(pin='PORT/'+t.getName(),master=None,role='input' if str(t.getIoType())=='INPUT' else 'output',signal=str(t.getSigType()),xy=[(box.xMin()+box.xMax())/2/u,(box.yMin()+box.yMax())/2/u],net=n.getName())
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
Path('/work/endpoint_master_contacts.json').write_text(json.dumps(masters,indent=2)+'\n')
rows=[]
for name,d in drivers.items():
 if d['master'] and d['master'].startswith(('BUF','INV')):continue
 stack=[outs[name]];seen=set();end={}
 while stack:
  net=stack.pop()
  if net in seen:continue
  seen.add(net)
  for s in sinks[net]:
   if s['pin'] in trans:stack.extend(outs[x] for x in trans[s['pin']])
   else:end[s['pin']]=s
 reach=max((abs(d['xy'][0]-s['xy'][0])+abs(d['xy'][1]-s['xy'][1]) for s in end.values()),default=0)
 rows.append(dict(driver=d,count=len(end),reach_um=reach,sinks=list(end.values())))
summary=dict(odb=str(f),odb_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),roots=len(rows),roles=dict(collections.Counter(r['driver']['role'] for r in rows)),max_count_by_role={r:max(x['count'] for x in rows if x['driver']['role']==r) for r in set(x['driver']['role'] for x in rows)},over32_nonclock=[dict(driver=r['driver'],count=r['count'],reach_um=r['reach_um']) for r in rows if r['count']>32 and r['driver']['signal']!='CLOCK' and r['driver']['pin'] not in ('PORT/ck','PORT/clk')],over405_nonclock=sum(r['reach_um']>405 for r in rows if r['driver']['signal']!='CLOCK' and r['driver']['pin'] not in ('PORT/ck','PORT/clk')),macros=len(mac),macro_masters=dict(collections.Counter(x['master'] for x in mac)),scope='Exact saved GRT ODB, uncapped logical sink pins through BUF/INV; Manhattan endpoint reach is a geometric lower bound, not stage path or routed wire length; macro contacts report MPin objects, not detailed escape/PG connectivity qualification')
import gzip
with gzip.open('/work/endpoint_roots.json.gz','wt') as z:z.write(json.dumps(rows,separators=(',',':'))+'\n')
Path('/work/endpoint_macros.json').write_text(json.dumps(mac,indent=2)+'\n');Path('/work/endpoint_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='over32_nonclock'},indent=2));print('OVER32',len(summary['over32_nonclock']))
