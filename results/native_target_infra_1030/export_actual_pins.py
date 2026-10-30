import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);p.add_argument('--plan',required=True);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();dbu=b.getDbUnitsPerMicron();plan=json.load(open(a.plan))
names=('cland_tstart_in','cland_tstart_out','cland_raw_reset_out','cland_raw_reset_in')
start=plan.get('clock',{}).get('landing_network',{}).get('start_tree',{});required=list(start.get('uses',[]))
rs=start.get('reset_source')
if rs:required.append(rs)
want={}
for row in required:want.setdefault(row['part'],set()).add(row['pin'])
rows=[];missing=[];counts=Counter();seen=set()
for inst in b.getInsts():
 for name in sorted(set(names)|want.get(inst.getName(),set())):
  it=inst.findITerm(name)
  if not it:missing.append([inst.getName(),name]);continue
  shapes=[];sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(inst.getOrient())];ox,oy=inst.getOrigin()
  for mp in it.getMTerm().getMPins():
   for s in mp.getGeometry():
    layer=s.getTechLayer()
    if not layer or layer.getRoutingLevel()<=0:continue
    xx=sorted([ox+sx*s.xMin(),ox+sx*s.xMax()]);yy=sorted([oy+sy*s.yMin(),oy+sy*s.yMax()]);shapes.append(dict(layer=layer.getName(),rect_um=[xx[0]/dbu,yy[0]/dbu,xx[1]/dbu,yy[1]/dbu]))
  if not shapes:raise ValueError('native START pin lacks actual routing metal '+inst.getName()+'/'+name)
  ok,x,y=it.getAvgXY()
  if not ok:raise ValueError('native START pin lacks coordinate '+inst.getName()+'/'+name)
  rows.append(dict(part=inst.getName(),pin=name,master=inst.getMaster().getName(),io=str(it.getMTerm().getIoType()),net=it.getNet().getName() if it.getNet() else None,xy_um=[x/dbu,y/dbu],shapes=shapes))
  counts[name]+=1;seen.add((inst.getName(),name))
uses=plan.get('clock',{}).get('landing_network',{}).get('start_tree',{}).get('uses',[])
missing_declared=[u for u in uses if (u['part'],u['pin']) not in seen]
missing_reset_source=rs if rs and (rs['part'],rs['pin']) not in seen else None
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
receipt=dict(schema='opentallas.native_start_endpoints.v1',scope='Read-only actual native target START/reset pin geometry; no RTL/provider/clock/timing qualification',source=a.odb,source_sha256=hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),plan=a.plan,plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),instances=len(list(b.getInsts())),pins=len(rows),counts=dict(counts),missing_declared=missing_declared,missing_reset_source=missing_reset_source,declared_uses=len(uses),missing_optional_or_undeclared=len(missing))
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(out/'endpoints.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'missing.json').write_text(json.dumps(missing)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='missing_declared'},sort_keys=True));print('MISSING_DECLARED',len(missing_declared))
