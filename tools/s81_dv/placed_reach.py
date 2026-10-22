#!/usr/bin/env python3
"""Read actual ODB pin coordinates; never infer reach from displacement.
Run with OpenROAD's Python environment. Does not change the database.
"""
import sys,json,heapq,time
import odb
odb_path,skip_path,out_path=sys.argv[1:4]
db=odb.dbDatabase.create();odb.read_db(db,odb_path)
b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
skip=set(open(skip_path).read().splitlines())
top=[];over_reach=[];counts=dict(nets=0,branches=0,over160=0,over405=0,ambiguous_drivers=0,missing_pin_xy=0,top_port_nets=0,skipped=0)
def xy(p):
 a=p.getAvgXY()
 if len(a)==3:
  ok,x,y=a
  return (x/u,y/u) if ok else None
 return tuple(v/u for v in a)
for net in b.getNets():
 name=net.getName()
 if name in skip or str(net.getSigType()) in ('POWER','GROUND','CLOCK'):
  counts['skipped']+=1;continue
 if net.getBTerms():counts['top_port_nets']+=1;continue
 terms=list(net.getITerms());drivers=[p for p in terms if str(p.getIoType())=='OUTPUT'];loads=[p for p in terms if str(p.getIoType())=='INPUT']
 if not loads:continue
 if len(drivers)!=1:counts['ambiguous_drivers']+=1;continue
 driver=drivers[0];a=xy(driver)
 if a is None:counts['missing_pin_xy']+=1;continue
 counts['nets']+=1
 for sink in loads:
  z=xy(sink)
  if z is None:counts['missing_pin_xy']+=1;continue
  distance=abs(a[0]-z[0])+abs(a[1]-z[1]);counts['branches']+=1
  counts['over160']+=distance>160;counts['over405']+=distance>405
  row=dict(net=name,driver=[driver.getInst().getName(),driver.getMTerm().getName(),list(a)],sink=[sink.getInst().getName(),sink.getMTerm().getName(),list(z)],driver_master=driver.getInst().getMaster().getName(),sink_master=sink.getInst().getMaster().getName(),manhattan_um=round(distance,4))
  if distance > 405: over_reach.append(row)
  key=(distance,counts['branches'],row)
  if len(top)<100:heapq.heappush(top,key)
  elif distance>top[0][0]:heapq.heapreplace(top,key)
def upstream(inst_name):
 inst=b.findInst(inst_name);seen=set();h=[]
 while inst and len(h)<512:
  name=inst.getName();master=inst.getMaster().getName();h.append([name,master])
  if name in seen:break
  seen.add(name)
  if not master.startswith(('BUFx','INVx')):break
  ins=[it for it in inst.getITerms() if str(it.getIoType())=='INPUT' and str(it.getMTerm().getSigType()) not in ('POWER','GROUND')]
  if len(ins)!=1 or not ins[0].getNet():break
  drv=[it for it in ins[0].getNet().getITerms() if str(it.getIoType())=='OUTPUT']
  if len(drv)!=1:break
  inst=drv[0].getInst()
 return h
for row in over_reach:
 row['upstream_launch']=upstream(row['driver'][0])
report=dict(over_reach_branches=over_reach,schema='opentallas.s81.actual_placed_reach.v1',source_odb=odb_path,scope='Actual ODB pin-to-pin branches; buffer segments when present. Ideal top ports and declared global distribution skipped.',counts=counts,max_um=top[-1][0] if False else max((v[0] for v in top),default=0),top=[v[2] for v in sorted(top,reverse=True)],physical_reach_verdict='FAIL' if counts['over405'] else 'PASS')
open(out_path,'w').write(json.dumps(report,indent=1)+'\n')
print('ACTUAL_PLACED_REACH',report['physical_reach_verdict'],counts,'max_um',report['max_um'])
